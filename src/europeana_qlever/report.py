"""DuckDB analytics over exported Parquet files for quality/coverage assessment.

Runs entirely offline — no QLever server needed.  Reads ``items_resolved.parquet``
and entity ``*_core`` / ``*_links`` Parquets to produce JSON + Markdown reports.

Filtering is schema-driven: :class:`ReportFilters` accepts any Item field name
from the LinkML schema and generates the appropriate DuckDB SQL using metadata
from :func:`~europeana_qlever.schema_loader.filterable_fields`.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import httpx

from . import display
from .schema_loader import authority_sql, entity_id_column, filterable_fields


# ---------------------------------------------------------------------------
# Report result
# ---------------------------------------------------------------------------

@dataclass
class Report:
    """Result of a report run."""

    json_path: Path = Path()
    markdown_path: Path = Path()
    sections_computed: int = 0
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Schema-driven report filters
# ---------------------------------------------------------------------------

# Regex for tokenising a filter expression: key>=val, key<=val, key=val, or key
_TOKEN_RE = re.compile(r"(\w+)\s*(>=|<=|=)\s*(\S+)")


class ReportFilters:
    """Schema-driven filter set for DuckDB report queries.

    Every non-identifier Item field in the LinkML schema is filterable.
    The SQL generation style (``IN``, ``=``, ``>=``, ``list_has_any``, …)
    is inferred from the field's range and multivalued flag via
    :func:`~europeana_qlever.schema_loader.filterable_fields`.

    Parse from a CLI string::

        ReportFilters.parse("country=NL,FR type=IMAGE has_iiif completeness>=5")

    Merge two instances (``other`` wins for scalar conflicts)::

        merged = base.merge(other)
    """

    def __init__(
        self,
        conditions: dict[str, list[str]] | None = None,
        *,
        booleans: dict[str, bool] | None = None,
        ranges: dict[str, dict[str, int]] | None = None,
    ) -> None:
        self._conditions: dict[str, list[str]] = dict(conditions or {})
        self._booleans: dict[str, bool] = dict(booleans or {})
        self._ranges: dict[str, dict[str, int]] = dict(ranges or {})

    @classmethod
    def parse(cls, text: str) -> ReportFilters:
        """Parse a filter string into a :class:`ReportFilters`.

        Syntax (space-separated tokens)::

            country=NL,FR           # in_list / eq / list_contains / list_struct
            reuse_level=open        # eq
            has_iiif                # boolean flag
            completeness>=5         # range (min)
            width<=1000             # range (max)

        Raises :class:`click.BadParameter` for unknown field names.
        """
        import click

        specs = filterable_fields()
        conditions: dict[str, list[str]] = {}
        booleans: dict[str, bool] = {}
        ranges: dict[str, dict[str, int]] = {}

        for token in text.split():
            m = _TOKEN_RE.fullmatch(token)
            if m:
                key, op, raw_val = m.group(1), m.group(2), m.group(3)
                field_name = _resolve_key(key, specs)
                spec = specs[field_name]
                if op in (">=", "<=") and spec.filter_style == "range":
                    bound = "min" if op == ">=" else "max"
                    ranges.setdefault(field_name, {})[bound] = int(raw_val)
                else:
                    conditions[field_name] = raw_val.split(",")
            else:
                # Bare token → boolean flag
                field_name = _resolve_key(token, specs)
                booleans[field_name] = True

        return cls(conditions=conditions, booleans=booleans, ranges=ranges)

    def merge(self, other: ReportFilters) -> ReportFilters:
        """Merge two filter sets.  ``other`` wins for scalar conflicts."""
        conditions = dict(self._conditions)
        for k, v in other._conditions.items():
            if k in conditions:
                conditions[k] = list(dict.fromkeys(conditions[k] + v))
            else:
                conditions[k] = v

        booleans = {**self._booleans, **other._booleans}

        ranges = {}
        for k in set(self._ranges) | set(other._ranges):
            merged = {**self._ranges.get(k, {}), **other._ranges.get(k, {})}
            ranges[k] = merged

        return ReportFilters(conditions=conditions, booleans=booleans, ranges=ranges)

    def is_empty(self) -> bool:
        return not self._conditions and not self._booleans and not self._ranges

    def to_duckdb_where(self) -> str:
        """Generate a DuckDB ``WHERE`` clause from these filters."""
        specs = filterable_fields()
        clauses: list[str] = []

        for field_name, values in self._conditions.items():
            spec = specs.get(field_name)
            if spec is None:
                continue
            col = spec.column
            if spec.filter_style == "eq":
                clauses.append(f"{col} = '{values[0]}'")
            elif spec.filter_style == "in_list":
                vals = ", ".join(f"'{v}'" for v in values)
                clauses.append(f"{col} IN ({vals})")
            elif spec.filter_style == "list_contains":
                vals = ", ".join(f"'{v}'" for v in values)
                clauses.append(f"list_has_any({col}, [{vals}])")
            elif spec.filter_style == "list_struct":
                vals = ", ".join(f"'{v}'" for v in values)
                sf = spec.struct_field
                clauses.append(
                    f"len(list_filter({col}, x -> x.{sf} IN ({vals}))) > 0"
                )

        for field_name, flag in self._booleans.items():
            spec = specs.get(field_name)
            if spec is None or spec.filter_style != "bool":
                continue
            clauses.append(f"{spec.column} = {'true' if flag else 'false'}")

        for field_name, bounds in self._ranges.items():
            spec = specs.get(field_name)
            if spec is None or spec.filter_style != "range":
                continue
            col = spec.column
            if "min" in bounds:
                clauses.append(f"{col} >= {bounds['min']}")
            if "max" in bounds:
                clauses.append(f"{col} <= {bounds['max']}")

        return ("WHERE " + " AND ".join(clauses)) if clauses else ""

    def description(self) -> str:
        """Human-readable description of active filters."""
        parts: list[str] = []
        for k, v in self._conditions.items():
            parts.append(f"{k}={','.join(v)}")
        for k, v in self._booleans.items():
            parts.append(k if v else f"!{k}")
        for k, bounds in self._ranges.items():
            for op, val in bounds.items():
                parts.append(f"{k}>={val}" if op == "min" else f"{k}<={val}")
        return "; ".join(parts) if parts else "all"

    def slice_name(self) -> str:
        """Filename-safe identifier for the filter set."""
        parts: list[str] = []
        for k, v in self._conditions.items():
            parts.extend(val.lower() for val in v)
        for k in self._booleans:
            parts.append(k)
        for k, bounds in self._ranges.items():
            for op, val in bounds.items():
                parts.append(f"{k}_{op}{val}")
        return "_".join(parts) if parts else "all"


def _resolve_key(key: str, specs: dict) -> str:
    """Resolve a filter key name to a schema field name.

    Accepts the exact field name or common singular/plural aliases.
    """
    import click

    # Alias map: singular → plural (schema field names are mostly plural
    # for list fields and singular for scalars).
    _ALIASES: dict[str, str] = {
        "country": "country",
        "countries": "country",
        "type": "type",
        "types": "type",
        "aggregator": "aggregator",
        "aggregators": "aggregator",
        "institution": "institution",
        "institutions": "institution",
        "language": "languages",
        "dataset": "dataset_name",
        "datasets": "dataset_name",
        "subject": "subjects",
        "dc_type": "dc_types",
        "format": "formats",
        "creator": "creators",
        "contributor": "contributors",
        "publisher": "publishers",
        "title": "titles",
        "description": "descriptions",
        "date": "dates",
        "year": "years",
        "identifier": "identifiers",
    }

    if key in specs:
        return key
    resolved = _ALIASES.get(key)
    if resolved and resolved in specs:
        return resolved
    valid = ", ".join(sorted(specs.keys()))
    raise click.BadParameter(
        f"Unknown filter field {key!r}. Valid fields: {valid}"
    )


# ---------------------------------------------------------------------------
# ExportReport — DuckDB over Parquet
# ---------------------------------------------------------------------------

class ExportReport:
    """DuckDB analytics over exported Parquet files.

    Runs entirely offline — no QLever server needed.  Reads
    ``items_resolved.parquet`` and entity ``*_core`` / ``*_links``
    Parquets to produce JSON + Markdown reports.
    """

    def __init__(
        self,
        *,
        exports_dir: Path,
        output_dir: Path,
        filters: ReportFilters | None = None,
        probe_urls: bool = False,
        sample_size: int = 1000,
        memory_limit: str = "4GB",
    ) -> None:
        self._exports_dir = exports_dir
        self._output_dir = output_dir
        self._filters = filters or ReportFilters()
        self._probe_urls = probe_urls
        self._sample_size = sample_size
        self._memory_limit = memory_limit

    # -- public API --

    def run(self) -> Report:
        from . import __version__

        resolved_path = self._exports_dir / "items_resolved.parquet"
        if not resolved_path.exists():
            display.console.print(
                f"[red]items_resolved.parquet not found in {self._exports_dir}[/red]\n"
                "Run the full export pipeline first."
            )
            raise SystemExit(1)

        self._output_dir.mkdir(parents=True, exist_ok=True)

        con = duckdb.connect()
        con.execute(f"SET memory_limit = '{self._memory_limit}'")

        where = self._filters.to_duckdb_where()
        con.execute(f"""
            CREATE VIEW items AS
            SELECT * FROM read_parquet('{resolved_path}')
            {where}
        """)

        institutions_path = self._exports_dir / "institutions.parquet"
        if institutions_path.exists():
            con.execute(f"""
                CREATE VIEW org_names AS
                SELECT org,
                       COALESCE(
                           MAX(name) FILTER (WHERE lang = 'en'),
                           MAX(name)
                       ) AS name
                FROM read_parquet('{institutions_path}')
                GROUP BY org
            """)
        else:
            con.execute(
                "CREATE VIEW org_names AS "
                "SELECT NULL::VARCHAR AS org, NULL::VARCHAR AS name WHERE false"
            )

        data: dict = {}
        sections = 0

        display.console.print("[bold]Running report…[/bold]")

        display.console.print("  [dim]Section 1: Volume and composition[/dim]")
        data["volume"] = self._section_volume(con)
        sections += 1

        display.console.print("  [dim]Section 2: Rights distribution[/dim]")
        data["rights"] = self._section_rights(con)
        sections += 1

        display.console.print("  [dim]Section 3: Language coverage[/dim]")
        data["language"] = self._section_language(con)
        sections += 1

        display.console.print("  [dim]Section 4: Metadata completeness[/dim]")
        data["completeness"] = self._section_completeness(con)
        sections += 1

        display.console.print("  [dim]Section 5: Entity enrichment[/dim]")
        entity_data = self._section_entities(con)
        if entity_data:
            data["entities"] = entity_data
            sections += 1
        else:
            display.console.print("    Skipped (no entity Parquets found)")

        display.console.print("  [dim]Section 6: Content accessibility[/dim]")
        data["content"] = self._section_content(con)
        sections += 1

        if self._probe_urls:
            display.console.print(
                f"  [dim]Section 7: URL liveness (sampling {self._sample_size} URLs)[/dim]"
            )
            urls = [
                row[0] for row in con.execute(
                    f"SELECT is_shown_by FROM items WHERE is_shown_by IS NOT NULL "
                    f"ORDER BY RANDOM() LIMIT {self._sample_size}"
                ).fetchall()
            ]
            if urls:
                data["url_liveness"] = asyncio.run(
                    _probe_urls(urls, self._sample_size)
                )
                sections += 1
            else:
                display.console.print("    No URLs to probe")

        con.close()

        slice_id = self._filters.slice_name()
        data["_meta"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "version": __version__,
            "filter": self._filters.description(),
            "items_resolved_path": str(resolved_path),
            "items_resolved_size_mb": round(resolved_path.stat().st_size / 1e6, 1),
        }

        json_path = self._output_dir / f"report_{slice_id}.json"
        md_path = self._output_dir / f"report_{slice_id}.md"

        json_path.write_text(json.dumps(data, indent=2, default=str))
        md_path.write_text(_render_export_markdown(data))

        display.console.print(f"\n[green]Report complete ({sections} sections)[/green]")
        display.console.print(f"  JSON: {json_path}")
        display.console.print(f"  Markdown: {md_path}")

        return Report(
            json_path=json_path,
            markdown_path=md_path,
            sections_computed=sections,
            data=data,
        )

    # -- section helpers --

    @staticmethod
    def _section_volume(con: duckdb.DuckDBPyConnection) -> dict:
        total = con.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        by_type = con.execute(
            "SELECT type, COUNT(*) AS cnt FROM items GROUP BY type ORDER BY cnt DESC"
        ).fetchall()
        by_country = con.execute(
            "SELECT country, COUNT(*) AS cnt FROM items GROUP BY country ORDER BY cnt DESC LIMIT 20"
        ).fetchall()
        by_institution = con.execute("""
            SELECT COALESCE(n.name, i.institution) AS institution, COUNT(*) AS cnt
            FROM items i LEFT JOIN org_names n ON i.institution = n.org
            GROUP BY 1 ORDER BY cnt DESC LIMIT 20
        """).fetchall()
        by_aggregator = con.execute("""
            SELECT COALESCE(n.name, i.aggregator) AS aggregator, COUNT(*) AS cnt
            FROM items i LEFT JOIN org_names n ON i.aggregator = n.org
            GROUP BY 1 ORDER BY cnt DESC LIMIT 20
        """).fetchall()
        dataset_count = con.execute(
            "SELECT COUNT(DISTINCT dataset_name) FROM items WHERE dataset_name IS NOT NULL"
        ).fetchone()[0]
        by_dc_type = con.execute("""
            SELECT d.label AS dc_type, COUNT(*) AS cnt
            FROM (SELECT UNNEST(dc_types) AS d FROM items)
            WHERE d.label IS NOT NULL
            GROUP BY d.label ORDER BY cnt DESC LIMIT 20
        """).fetchall()
        by_format = con.execute("""
            SELECT f.label AS fmt, COUNT(*) AS cnt
            FROM (SELECT UNNEST(formats) AS f FROM items)
            WHERE f.label IS NOT NULL
            GROUP BY f.label ORDER BY cnt DESC LIMIT 20
        """).fetchall()

        return {
            "total_items": total,
            "by_type": [{"type": t, "count": c, "pct": round(c / total * 100, 2) if total else 0} for t, c in by_type],
            "top_20_countries": [{"country": t, "count": c, "pct": round(c / total * 100, 2) if total else 0} for t, c in by_country],
            "top_20_institutions": [{"institution": str(t), "count": c, "pct": round(c / total * 100, 2) if total else 0} for t, c in by_institution],
            "top_20_aggregators": [{"aggregator": str(a), "count": c, "pct": round(c / total * 100, 2) if total else 0} for a, c in by_aggregator],
            "distinct_datasets": dataset_count,
            "top_20_dc_types": [{"dc_type": t, "count": c, "pct": round(c / total * 100, 2) if total else 0} for t, c in by_dc_type],
            "top_20_formats": [{"format": f, "count": c, "pct": round(c / total * 100, 2) if total else 0} for f, c in by_format],
        }

    @staticmethod
    def _section_rights(con: duckdb.DuckDBPyConnection) -> dict:
        total = con.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        by_level = con.execute(
            "SELECT reuse_level, COUNT(*) AS cnt FROM items GROUP BY reuse_level ORDER BY cnt DESC"
        ).fetchall()
        by_uri = con.execute(
            "SELECT rights, COUNT(*) AS cnt FROM items GROUP BY rights ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        return {
            "by_reuse_level": [{"level": l, "count": c, "pct": round(c / total * 100, 2) if total else 0} for l, c in by_level],
            "top_10_rights_uris": [{"uri": u, "count": c, "pct": round(c / total * 100, 2) if total else 0} for u, c in by_uri],
        }

    @staticmethod
    def _section_language(con: duckdb.DuckDBPyConnection) -> dict:
        total = con.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        by_lang = con.execute("""
            SELECT lang, COUNT(*) AS cnt
            FROM (SELECT UNNEST(languages) AS lang FROM items)
            GROUP BY lang ORDER BY cnt DESC LIMIT 30
        """).fetchall()
        has_titled = con.execute(
            "SELECT COUNT(*) FROM items WHERE titles IS NOT NULL AND LEN(titles) > 0"
        ).fetchone()[0]
        has_described = con.execute(
            "SELECT COUNT(*) FROM items WHERE descriptions IS NOT NULL AND LEN(descriptions) > 0"
        ).fetchone()[0]
        avg_title_langs = con.execute("""
            SELECT AVG(LEN(titles)) FROM items WHERE titles IS NOT NULL AND LEN(titles) > 0
        """).fetchone()[0]
        avg_desc_langs = con.execute("""
            SELECT AVG(LEN(descriptions)) FROM items WHERE descriptions IS NOT NULL AND LEN(descriptions) > 0
        """).fetchone()[0]
        return {
            "top_30_languages": [{"language": l, "count": c, "pct": round(c / total * 100, 2) if total else 0} for l, c in by_lang],
            "pct_with_title": round(has_titled / total * 100, 2) if total else 0,
            "pct_with_description": round(has_described / total * 100, 2) if total else 0,
            "avg_title_variants": round(avg_title_langs, 2) if avg_title_langs else 0,
            "avg_description_variants": round(avg_desc_langs, 2) if avg_desc_langs else 0,
        }

    @staticmethod
    def _section_completeness(con: duckdb.DuckDBPyConnection) -> dict:
        total = con.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        by_score = con.execute("""
            SELECT completeness, COUNT(*) AS cnt
            FROM items
            GROUP BY completeness ORDER BY completeness
        """).fetchall()
        fields = con.execute("""
            SELECT
                COUNT(*) FILTER (WHERE titles IS NOT NULL AND LEN(titles) > 0) AS has_title,
                COUNT(*) FILTER (WHERE descriptions IS NOT NULL AND LEN(descriptions) > 0) AS has_description,
                COUNT(*) FILTER (WHERE creators IS NOT NULL AND LEN(creators) > 0) AS has_creator,
                COUNT(*) FILTER (WHERE contributors IS NOT NULL AND LEN(contributors) > 0) AS has_contributor,
                COUNT(*) FILTER (WHERE publishers IS NOT NULL AND LEN(publishers) > 0) AS has_publisher,
                COUNT(*) FILTER (WHERE subjects IS NOT NULL AND LEN(subjects) > 0) AS has_subject,
                COUNT(*) FILTER (WHERE dc_types IS NOT NULL AND LEN(dc_types) > 0) AS has_dc_type,
                COUNT(*) FILTER (WHERE formats IS NOT NULL AND LEN(formats) > 0) AS has_format,
                COUNT(*) FILTER (WHERE dates IS NOT NULL AND LEN(dates) > 0) AS has_date,
                COUNT(*) FILTER (WHERE years IS NOT NULL AND LEN(years) > 0) AS has_year,
                COUNT(*) FILTER (WHERE languages IS NOT NULL AND LEN(languages) > 0) AS has_language,
                COUNT(*) FILTER (WHERE identifiers IS NOT NULL AND LEN(identifiers) > 0) AS has_identifier,
                COUNT(*) FILTER (WHERE dc_rights IS NOT NULL AND LEN(dc_rights) > 0) AS has_dc_rights,
                COUNT(*) FILTER (WHERE is_shown_by IS NOT NULL) AS has_content_url,
                COUNT(*) FILTER (WHERE has_iiif) AS has_iiif
            FROM items
        """).fetchone()
        field_names = [
            "has_title", "has_description", "has_creator",
            "has_contributor", "has_publisher",
            "has_subject", "has_dc_type", "has_format",
            "has_date", "has_year", "has_language",
            "has_identifier", "has_dc_rights",
            "has_content_url", "has_iiif",
        ]
        return {
            "by_completeness_score": [
                {"score": str(s), "count": c, "pct": round(c / total * 100, 2) if total else 0}
                for s, c in by_score
            ],
            "field_coverage": {
                name: round(val / total * 100, 2) if total else 0
                for name, val in zip(field_names, fields)
            },
        }

    def _section_entities(self, con: duckdb.DuckDBPyConnection) -> dict | None:
        entity_types = {
            etype: (
                entity_id_column(etype),
                f"{etype}_core.parquet",
                f"{etype}_links.parquet",
            )
            for etype in ("agents", "places", "concepts", "timespans")
        }

        data: dict = {}
        any_found = False
        auth_sql = authority_sql()

        for etype, (id_col, core_file, links_file) in entity_types.items():
            core_path = self._exports_dir / core_file
            links_path = self._exports_dir / links_file

            if not core_path.exists():
                continue
            any_found = True
            entry: dict = {}

            total = con.execute(
                f"SELECT COUNT(DISTINCT {id_col}) FROM read_parquet('{core_path}')"
            ).fetchone()[0]
            entry["total_entities"] = total

            avg_labels = con.execute(
                f"SELECT AVG(cnt) FROM (SELECT COUNT(*) AS cnt FROM read_parquet('{core_path}') GROUP BY {id_col})"
            ).fetchone()[0]
            entry["avg_pref_label_variants"] = round(avg_labels, 2) if avg_labels else 0

            if links_path.exists():
                linked = con.execute(f"""
                    SELECT COUNT(DISTINCT {id_col})
                    FROM read_parquet('{links_path}')
                    WHERE property = 'same_as'
                """).fetchone()[0]
                entry["entities_with_same_as"] = linked
                entry["same_as_coverage_pct"] = round(linked / total * 100, 2) if total else 0

                authorities = con.execute(f"""
                    SELECT
                        {auth_sql} AS authority,
                        COUNT(DISTINCT {id_col}) AS entities_linked,
                        COUNT(*) AS total_links
                    FROM read_parquet('{links_path}')
                    WHERE property = 'same_as'
                    GROUP BY authority ORDER BY entities_linked DESC
                """).fetchall()
                entry["authority_links"] = [
                    {"authority": a, "entities_linked": el, "total_links": tl}
                    for a, el, tl in authorities
                ]

                alt_count = con.execute(f"""
                    SELECT COUNT(DISTINCT {id_col})
                    FROM read_parquet('{links_path}')
                    WHERE property = 'alt_label'
                """).fetchone()[0]
                entry["alt_label_coverage_pct"] = round(alt_count / total * 100, 2) if total else 0

                if etype == "concepts":
                    for prop in ("exact_match", "broader", "narrower"):
                        prop_count = con.execute(f"""
                            SELECT COUNT(DISTINCT {id_col})
                            FROM read_parquet('{links_path}')
                            WHERE property = '{prop}'
                        """).fetchone()[0]
                        entry[f"{prop}_coverage_pct"] = round(prop_count / total * 100, 2) if total else 0

            if etype == "concepts":
                top_subjects = con.execute("""
                    SELECT s.label AS subj, s.uri AS uri, COUNT(*) AS cnt
                    FROM (SELECT UNNEST(subjects) AS s FROM items)
                    WHERE s.label IS NOT NULL
                    GROUP BY s.label, s.uri ORDER BY cnt DESC LIMIT 20
                """).fetchall()
                entry["top_20_subjects"] = [
                    {"subject": s, "uri": u, "count": c}
                    for s, u, c in top_subjects
                ]

            data[etype] = entry

        return data if any_found else None

    @staticmethod
    def _section_content(con: duckdb.DuckDBPyConnection) -> dict:
        row = con.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE is_shown_by IS NOT NULL) AS has_direct_url,
                COUNT(*) FILTER (WHERE is_shown_at IS NOT NULL) AS has_landing_page,
                COUNT(*) FILTER (WHERE preview IS NOT NULL) AS has_thumbnail,
                COUNT(*) FILTER (WHERE has_iiif) AS has_iiif_service,
                COUNT(*) FILTER (WHERE mime_type IS NOT NULL) AS has_mime_type
            FROM items
        """).fetchone()
        total = row[0]
        labels = ["has_direct_url", "has_landing_page", "has_thumbnail", "has_iiif_service", "has_mime_type"]
        content: dict = {"total": total}
        for i, label in enumerate(labels, 1):
            content[label] = row[i]
            content[f"{label}_pct"] = round(row[i] / total * 100, 2) if total else 0

        mime_dist = con.execute("""
            SELECT mime_type, COUNT(*) AS cnt
            FROM items WHERE mime_type IS NOT NULL
            GROUP BY mime_type ORDER BY cnt DESC LIMIT 15
        """).fetchall()
        content["mime_distribution"] = [{"mime_type": m, "count": c} for m, c in mime_dist]

        return content


# ---------------------------------------------------------------------------
# URL liveness prober (used by ExportReport)
# ---------------------------------------------------------------------------

async def _probe_urls(urls: list[str], sample_size: int) -> dict:
    """Async HTTP HEAD probe of URLs with rate limiting."""
    results: dict[str, int] = {}
    response_times: list[float] = []
    semaphore = asyncio.Semaphore(10)

    async def probe_one(client: httpx.AsyncClient, url: str) -> None:
        try:
            t0 = time.perf_counter()
            resp = await client.head(url, follow_redirects=True)
            elapsed = time.perf_counter() - t0
            response_times.append(elapsed)
            code = str(resp.status_code)
            results[code] = results.get(code, 0) + 1
        except httpx.TimeoutException:
            results["timeout"] = results.get("timeout", 0) + 1
        except httpx.ConnectError:
            results["connection_error"] = results.get("connection_error", 0) + 1
        except Exception:
            results["other_error"] = results.get("other_error", 0) + 1

    async def throttled_probe(client: httpx.AsyncClient, url: str) -> None:
        async with semaphore:
            await probe_one(client, url)
            await asyncio.sleep(0.02)

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        tasks = [throttled_probe(client, url) for url in urls[:sample_size]]
        await asyncio.gather(*tasks)

    ok_count = sum(v for k, v in results.items() if k.startswith("2"))
    total_probed = sum(results.values())

    return {
        "sample_size": total_probed,
        "status_distribution": results,
        "median_response_time": round(sorted(response_times)[len(response_times) // 2], 3) if response_times else None,
        "harvestability_rate_pct": round(ok_count / total_probed * 100, 2) if total_probed else 0,
    }


# ---------------------------------------------------------------------------
# Markdown renderer (ExportReport)
# ---------------------------------------------------------------------------

def _render_export_markdown(data: dict) -> str:
    """Render export report data as a Markdown document."""
    lines: list[str] = []
    lines.append(f"# Europeana Report")
    meta = data.get("_meta", {})
    lines.append(f"\n**Generated:** {meta.get('timestamp', 'N/A')}")
    lines.append(f"**Filter:** {meta.get('filter', 'all')}")
    lines.append("")

    # 1. Volume
    if "volume" in data:
        v = data["volume"]
        lines.append("## 1. Volume and Composition")
        lines.append(f"\n**Total items:** {v['total_items']:,}")
        lines.append(f"**Distinct datasets:** {v['distinct_datasets']:,}")
        lines.append("\n### By Type\n")
        lines.append("| Type | Count | % |")
        lines.append("|------|------:|--:|")
        for row in v["by_type"]:
            lines.append(f"| {row['type']} | {row['count']:,} | {row['pct']}% |")
        lines.append("\n### Top 20 Countries\n")
        lines.append("| Country | Count | % |")
        lines.append("|---------|------:|--:|")
        for row in v["top_20_countries"]:
            lines.append(f"| {row['country']} | {row['count']:,} | {row['pct']}% |")
        if v.get("top_20_institutions"):
            lines.append("\n### Top 20 Institutions\n")
            lines.append("| Institution | Count | % |")
            lines.append("|-------------|------:|--:|")
            for row in v["top_20_institutions"]:
                lines.append(f"| {row['institution']} | {row['count']:,} | {row['pct']}% |")
        if v.get("top_20_aggregators"):
            lines.append("\n### Top 20 Aggregators\n")
            lines.append("| Aggregator | Count | % |")
            lines.append("|------------|------:|--:|")
            for row in v["top_20_aggregators"]:
                lines.append(f"| {row['aggregator']} | {row['count']:,} | {row['pct']}% |")
        if v.get("top_20_dc_types"):
            lines.append("\n### Top 20 dc:type\n")
            lines.append("| dc:type | Count | % |")
            lines.append("|---------|------:|--:|")
            for row in v["top_20_dc_types"]:
                lines.append(f"| {row['dc_type']} | {row['count']:,} | {row['pct']}% |")
        if v.get("top_20_formats"):
            lines.append("\n### Top 20 dc:format\n")
            lines.append("| dc:format | Count | % |")
            lines.append("|-----------|------:|--:|")
            for row in v["top_20_formats"]:
                lines.append(f"| {row['format']} | {row['count']:,} | {row['pct']}% |")
        lines.append("")

    # 2. Rights
    if "rights" in data:
        r = data["rights"]
        lines.append("## 2. Rights Distribution")
        lines.append("\n### By Reuse Level\n")
        lines.append("| Level | Count | % |")
        lines.append("|-------|------:|--:|")
        for row in r["by_reuse_level"]:
            lines.append(f"| **{row['level']}** | {row['count']:,} | {row['pct']}% |")
        lines.append("\n### Top 10 Rights URIs\n")
        lines.append("| URI | Count | % |")
        lines.append("|-----|------:|--:|")
        for row in r["top_10_rights_uris"]:
            lines.append(f"| {row['uri']} | {row['count']:,} | {row['pct']}% |")
        lines.append("")

    # 3. Language
    if "language" in data:
        la = data["language"]
        lines.append("## 3. Language Coverage")
        lines.append(f"\n- Items with title: **{la['pct_with_title']}%**")
        lines.append(f"- Items with description: **{la['pct_with_description']}%**")
        lines.append(f"- Avg title language variants: **{la['avg_title_variants']}**")
        lines.append(f"- Avg description variants: **{la['avg_description_variants']}**")
        lines.append("\n### Top 30 Languages\n")
        lines.append("| Language | Count | % |")
        lines.append("|----------|------:|--:|")
        for row in la["top_30_languages"]:
            lines.append(f"| {row['language']} | {row['count']:,} | {row['pct']}% |")
        lines.append("")

    # 4. Completeness
    if "completeness" in data:
        co = data["completeness"]
        lines.append("## 4. Metadata Completeness")
        lines.append("\n### Completeness Score Distribution\n")
        lines.append("| Score | Count | % |")
        lines.append("|------:|------:|--:|")
        for row in co["by_completeness_score"]:
            lines.append(f"| {row['score']} | {row['count']:,} | {row['pct']}% |")
        lines.append("\n### Field Coverage\n")
        lines.append("| Field | Coverage % |")
        lines.append("|-------|----------:|")
        for fname, pct in co["field_coverage"].items():
            lines.append(f"| {fname} | {pct}% |")
        lines.append("")

    # 5. Entities
    if "entities" in data and data["entities"]:
        lines.append("## 5. Entity Enrichment")
        for etype, edata in data["entities"].items():
            lines.append(f"\n### {etype.title()}")
            lines.append(f"\n- Total entities: **{edata['total_entities']:,}**")
            lines.append(f"- Avg prefLabel variants: **{edata['avg_pref_label_variants']}**")
            if "same_as_coverage_pct" in edata:
                lines.append(f"- owl:sameAs coverage: **{edata['same_as_coverage_pct']}%**")
            if "alt_label_coverage_pct" in edata:
                lines.append(f"- altLabel coverage: **{edata['alt_label_coverage_pct']}%**")
            if "authority_links" in edata and edata["authority_links"]:
                lines.append("\n| Authority | Entities Linked | Total Links |")
                lines.append("|-----------|---------------:|------------:|")
                for a in edata["authority_links"]:
                    lines.append(f"| {a['authority']} | {a['entities_linked']:,} | {a['total_links']:,} |")
            for prop in ("exact_match", "broader", "narrower"):
                key = f"{prop}_coverage_pct"
                if key in edata:
                    lines.append(f"- {prop} coverage: **{edata[key]}%**")
            if "top_20_subjects" in edata and edata["top_20_subjects"]:
                lines.append("\n### Top 20 Subjects (in items)\n")
                lines.append("| Subject | URI | Count |")
                lines.append("|---------|-----|------:|")
                for row in edata["top_20_subjects"]:
                    uri = f"[{row['uri']}]({row['uri']})" if row['uri'] else ''
                    lines.append(f"| {row['subject']} | {uri} | {row['count']:,} |")
        lines.append("")

    # 6. Content
    if "content" in data:
        ct = data["content"]
        lines.append("## 6. Content Accessibility")
        lines.append(f"\n- Has direct URL: **{ct['has_direct_url_pct']}%**")
        lines.append(f"- Has landing page: **{ct['has_landing_page_pct']}%**")
        lines.append(f"- Has thumbnail: **{ct['has_thumbnail_pct']}%**")
        lines.append(f"- Has IIIF service: **{ct['has_iiif_service_pct']}%**")
        lines.append(f"- Has MIME type: **{ct['has_mime_type_pct']}%**")
        if ct.get("mime_distribution"):
            lines.append("\n### MIME Type Distribution (Top 15)\n")
            lines.append("| MIME Type | Count |")
            lines.append("|-----------|------:|")
            for row in ct["mime_distribution"]:
                lines.append(f"| {row['mime_type']} | {row['count']:,} |")
        lines.append("")

    # 7. URL Liveness
    if "url_liveness" in data:
        ul = data["url_liveness"]
        lines.append("## 7. URL Liveness")
        lines.append(f"\n- Sample size: **{ul['sample_size']}**")
        if ul["median_response_time"]:
            lines.append(f"- Median response time: **{ul['median_response_time']}s**")
        lines.append(f"- Harvestability rate: **{ul['harvestability_rate_pct']}%**")
        lines.append("\n| Status | Count |")
        lines.append("|--------|------:|")
        for status, count in sorted(ul["status_distribution"].items()):
            lines.append(f"| {status} | {count} |")
        lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Convenience entry point for cli.py
# ---------------------------------------------------------------------------

def run_report(
    *,
    exports_dir: Path,
    output_dir: Path,
    filters: ReportFilters | None = None,
    probe_urls: bool = False,
    sample_size: int = 1000,
    memory_limit: str = "4GB",
) -> Report:
    """Run DuckDB analytics and produce JSON + Markdown reports."""
    return ExportReport(
        exports_dir=exports_dir,
        output_dir=output_dir,
        filters=filters,
        probe_urls=probe_urls,
        sample_size=sample_size,
        memory_limit=memory_limit,
    ).run()
