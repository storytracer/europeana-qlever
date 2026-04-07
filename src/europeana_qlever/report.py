"""Composable report system over Europeana data.

Reports are assembled from YAML question files in
``{work_dir}/reports/questions/``.  Each YAML file defines a section with
questions.  Questions can carry a pre-defined ``query`` (executed directly
via DuckDB) or be answered by the ask agent (NL→SQL or NL→SPARQL).

Filtering is schema-driven: :class:`ReportFilters` accepts any Item field
name from the LinkML schema and generates the appropriate DuckDB SQL using
metadata from :func:`~europeana_qlever.schema_loader.filterable_fields`.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import httpx
import yaml

from . import display
from .schema_loader import filterable_fields


# ---------------------------------------------------------------------------
# Report result
# ---------------------------------------------------------------------------

@dataclass
class Report:
    """Result of a report run."""

    json_path: Path = field(default_factory=Path)
    markdown_path: Path = field(default_factory=Path)
    sections_computed: int = 0
    questions_computed: int = 0
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Report question / section dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ReportQuestion:
    """A single report question loaded from YAML."""

    id: str
    question: str
    backend: str  # "parquet" or "sparql"
    section_id: str = ""
    query: str | None = None  # pre-defined SQL/SPARQL (static execution)
    rationale: str | None = None


@dataclass
class ReportSection:
    """A section of the report containing related questions."""

    id: str
    name: str
    description: str
    questions: list[ReportQuestion] = field(default_factory=list)


@dataclass
class ReportQuestionResult:
    """Result of a single report question."""

    id: str
    section_id: str
    question: str
    backend: str
    answer: str | None = None
    query: str | None = None
    result_text: str | None = None
    elapsed: float = 0.0
    steps: int = 0
    error: str | None = None


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------

def load_report_sections(questions_dir: Path) -> list[ReportSection]:
    """Discover and parse all ``.yml`` files in *questions_dir*.

    Each YAML file defines one :class:`ReportSection`.  The file stem
    becomes the section ID.  Files are sorted by name for deterministic
    ordering.
    """
    sections: list[ReportSection] = []
    files = sorted(questions_dir.glob("*.yml"))
    for path in files:
        with open(path) as f:
            raw = yaml.safe_load(f)
        section_id = path.stem
        section = ReportSection(
            id=section_id,
            name=raw.get("name", section_id),
            description=raw.get("description", ""),
        )
        for q in raw.get("questions", []):
            section.questions.append(ReportQuestion(
                id=q["id"],
                question=q.get("question", q["id"]),
                backend=q.get("backend", "parquet"),
                section_id=section_id,
                query=q.get("query"),
                rationale=q.get("rationale"),
            ))
        sections.append(section)
    return sections


def select_questions(
    sections: list[ReportSection],
    *,
    section_ids: list[str] | None = None,
    question_ids: list[str] | None = None,
) -> list[ReportSection]:
    """Filter sections/questions by CLI selection (union semantics).

    Returns sections pruned to only matching questions, dropping
    empty sections.  If both are ``None``, returns all sections unchanged.
    """
    if section_ids is None and question_ids is None:
        return sections

    selected_sections = set(section_ids or [])
    selected_questions = set(question_ids or [])

    result: list[ReportSection] = []
    for section in sections:
        if section.id in selected_sections:
            result.append(section)
        elif selected_questions:
            kept = [q for q in section.questions if q.id in selected_questions]
            if kept:
                result.append(ReportSection(
                    id=section.id,
                    name=section.name,
                    description=section.description,
                    questions=kept,
                ))
    return result


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
# Static query execution — format DuckDB result as Markdown table
# ---------------------------------------------------------------------------

def _format_result_table(result: duckdb.DuckDBPyRelation) -> str:
    """Format a DuckDB query result as a Markdown table."""
    columns = result.columns
    types = result.types
    rows = result.fetchall()
    if not rows:
        return "_No results._"

    # Format cell values
    def fmt(val: object, dtype: str) -> str:
        if val is None:
            return ""
        if isinstance(val, float):
            # Keep precision from query (already rounded in most cases)
            if val == int(val):
                return f"{int(val):,}"
            return f"{val:,.2f}"
        if isinstance(val, int):
            return f"{val:,}"
        return str(val)

    str_rows = [[fmt(v, str(t)) for v, t in zip(row, types)] for row in rows]

    # Column widths
    widths = [len(c) for c in columns]
    for row in str_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    # Build table
    lines: list[str] = []
    header = "| " + " | ".join(c.ljust(w) for c, w in zip(columns, widths)) + " |"
    sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    lines.append(header)
    lines.append(sep)
    for row in str_rows:
        line = "| " + " | ".join(cell.ljust(w) for cell, w in zip(row, widths)) + " |"
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report runner
# ---------------------------------------------------------------------------

async def run_report(
    *,
    exports_dir: Path,
    questions_dir: Path,
    output_dir: Path,
    filters: ReportFilters | None = None,
    section_ids: list[str] | None = None,
    question_ids: list[str] | None = None,
    probe_urls: bool = False,
    sample_size: int = 1000,
    memory_limit: str = "4GB",
    model: str | None = None,
    max_steps: int | None = None,
    grasp_url: str = "ws://localhost:6789/live",
    verbose: bool = False,
    timeout: float = 180.0,
) -> Report:
    """Run the report by dispatching questions to static SQL or ask backends."""
    from .ask import AskResult
    from .ask.store import ParquetStore

    console = display.console

    # -- load and filter questions -------------------------------------------
    if not questions_dir.exists() or not list(questions_dir.glob("*.yml")):
        console.print(
            "[red]No question files found.[/red] "
            f"Expected YAML files in {questions_dir}\n"
            "Run [bold]write-report-config[/bold] to generate defaults."
        )
        return Report()

    all_sections = load_report_sections(questions_dir)
    sections = select_questions(
        all_sections,
        section_ids=section_ids,
        question_ids=question_ids,
    )
    if not sections:
        console.print("[yellow]No questions matched the selection.[/yellow]")
        return Report()

    total_questions = sum(len(s.questions) for s in sections)
    has_agent_questions = any(
        q.query is None for s in sections for q in s.questions
    )
    has_sparql = any(
        q.backend == "sparql" for s in sections for q in s.questions
    )

    console.print(
        f"Running report: {total_questions} questions across "
        f"{len(sections)} sections"
    )

    # -- create backends -----------------------------------------------------
    store = ParquetStore(
        exports_dir, filters=filters, memory_limit=memory_limit,
    )

    parquet_backend = None
    sparql_backend = None

    if has_agent_questions:
        from .ask.parquet import AskParquet
        kwargs: dict = {"store": store}
        if model:
            kwargs["model"] = model
        if max_steps:
            kwargs["max_steps"] = max_steps
        parquet_backend = AskParquet(**kwargs)

    if has_sparql:
        from .ask.sparql import AskSPARQL
        sparql_backend = AskSPARQL(ws_url=grasp_url)

    # -- run questions -------------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)
    results_by_section: dict[str, list[ReportQuestionResult]] = {}
    question_counter = 0

    try:
        for section in sections:
            console.print(f"\n[bold]{section.name}[/bold]")
            section_results: list[ReportQuestionResult] = []

            for q in section.questions:
                question_counter += 1
                label = f"  [{question_counter}/{total_questions}] {q.question}"
                t0 = time.perf_counter()

                if q.query:
                    # Static execution — run pre-defined SQL directly
                    try:
                        console.print(f"{label} [dim](static)[/dim]")
                        rel = store.connection.execute(q.query)
                        result_text = _format_result_table(rel)
                        elapsed = time.perf_counter() - t0
                        section_results.append(ReportQuestionResult(
                            id=q.id,
                            section_id=q.section_id,
                            question=q.question,
                            backend=q.backend,
                            query=q.query.strip(),
                            result_text=result_text,
                            elapsed=elapsed,
                        ))
                        console.print(f"    [green]done[/green] ({elapsed:.1f}s)")
                    except Exception as exc:
                        elapsed = time.perf_counter() - t0
                        section_results.append(ReportQuestionResult(
                            id=q.id,
                            section_id=q.section_id,
                            question=q.question,
                            backend=q.backend,
                            query=q.query.strip(),
                            error=str(exc),
                            elapsed=elapsed,
                        ))
                        console.print(f"    [red]error:[/red] {exc}")
                else:
                    # Agent execution — NL question via ask backend
                    console.print(f"{label} [dim](agent)[/dim]")
                    backend = (
                        sparql_backend
                        if q.backend == "sparql"
                        else parquet_backend
                    )
                    if backend is None:
                        section_results.append(ReportQuestionResult(
                            id=q.id,
                            section_id=q.section_id,
                            question=q.question,
                            backend=q.backend,
                            error=f"No {q.backend} backend available",
                            elapsed=0.0,
                        ))
                        console.print(f"    [red]no backend[/red]")
                        continue

                    prompt = q.question
                    if q.rationale:
                        prompt += f"\n\nContext: {q.rationale}"
                    # For SPARQL with filters, prepend filter context
                    if (
                        q.backend == "sparql"
                        and filters
                        and not filters.is_empty()
                    ):
                        prompt = (
                            f"Restrict your analysis to items matching: "
                            f"{filters.description()}. {prompt}"
                        )

                    ask_result: AskResult = await backend.ask(
                        prompt, timeout=timeout, verbose=verbose,
                    )
                    elapsed = time.perf_counter() - t0
                    section_results.append(ReportQuestionResult(
                        id=q.id,
                        section_id=q.section_id,
                        question=q.question,
                        backend=q.backend,
                        answer=ask_result.answer,
                        query=ask_result.query,
                        result_text=ask_result.result_text,
                        elapsed=elapsed,
                        steps=len(ask_result.steps),
                        error=ask_result.error,
                    ))
                    if ask_result.error:
                        console.print(f"    [red]error:[/red] {ask_result.error}")
                    else:
                        console.print(f"    [green]done[/green] ({elapsed:.1f}s)")

            results_by_section[section.id] = section_results

        # -- URL probing (special section) -----------------------------------
        url_liveness_data: dict | None = None
        if probe_urls:
            console.print("\n[bold]URL Liveness[/bold]")
            urls = store.connection.execute(
                "SELECT is_shown_by FROM items "
                "WHERE is_shown_by IS NOT NULL "
                "ORDER BY random() "
                f"LIMIT {sample_size}"
            ).fetchall()
            url_list = [row[0] for row in urls]
            if url_list:
                url_liveness_data = await _probe_urls(url_list, sample_size)
                console.print(
                    f"  Probed {url_liveness_data['sample_size']} URLs — "
                    f"harvestability {url_liveness_data['harvestability_rate_pct']}%"
                )
            else:
                console.print("  [yellow]No is_shown_by URLs found.[/yellow]")

    finally:
        store.close()

    # -- assemble output data ------------------------------------------------
    filter_desc = filters.description() if filters else "all"
    slice_id = filters.slice_name() if filters else "all"

    data: dict = {
        "_meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "filter": filter_desc,
            "questions_dir": str(questions_dir),
            "total_questions": question_counter,
            "total_elapsed": round(
                sum(
                    r.elapsed
                    for results in results_by_section.values()
                    for r in results
                ),
                2,
            ),
        },
        "sections": [
            {
                "id": section.id,
                "name": section.name,
                "questions": [
                    {
                        k: v
                        for k, v in asdict(r).items()
                        if v is not None
                    }
                    for r in results_by_section.get(section.id, [])
                ],
            }
            for section in sections
        ],
    }
    if url_liveness_data:
        data["url_liveness"] = url_liveness_data

    # -- write output files --------------------------------------------------
    json_path = output_dir / f"report_{slice_id}.json"
    md_path = output_dir / f"report_{slice_id}.md"

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    md_text = _render_report_markdown(data)
    with open(md_path, "w") as f:
        f.write(md_text)

    console.print(
        f"\n[green]Report complete "
        f"({len(sections)} sections, {question_counter} questions)[/green]"
    )
    console.print(f"  JSON: {json_path}")
    console.print(f"  Markdown: {md_path}")

    return Report(
        json_path=json_path,
        markdown_path=md_path,
        sections_computed=len(sections),
        questions_computed=question_counter,
        data=data,
    )


# ---------------------------------------------------------------------------
# URL liveness prober
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
# Markdown renderer
# ---------------------------------------------------------------------------

def _render_report_markdown(data: dict) -> str:
    """Render the report as a Markdown document."""
    lines: list[str] = []
    meta = data.get("_meta", {})

    lines.append("# Europeana Report")
    lines.append(f"\n**Generated:** {meta.get('timestamp', 'N/A')}")
    lines.append(f"**Filter:** {meta.get('filter', 'all')}")
    lines.append("")

    for i, section in enumerate(data.get("sections", []), 1):
        lines.append(f"## {i}. {section['name']}")
        lines.append("")

        for qr in section.get("questions", []):
            lines.append(f"### {qr['question']}")
            lines.append("")

            if qr.get("error"):
                lines.append(f"> **Error:** {qr['error']}")
                lines.append("")
                continue

            # NL answer from agent
            if qr.get("answer"):
                lines.append(qr["answer"])
                lines.append("")

            # Result table
            if qr.get("result_text") and qr["result_text"] != "_No results._":
                lines.append(qr["result_text"])
                lines.append("")

            # Query in collapsible block
            if qr.get("query"):
                lang = "sparql" if qr.get("backend") == "sparql" else "sql"
                lines.append("<details>")
                lines.append(f"<summary>Query ({qr.get('backend', 'sql')})</summary>")
                lines.append("")
                lines.append(f"```{lang}")
                lines.append(qr["query"])
                lines.append("```")
                lines.append("")
                lines.append("</details>")
                lines.append("")

    # URL liveness section
    if "url_liveness" in data:
        ul = data["url_liveness"]
        lines.append("## URL Liveness")
        lines.append(f"\n- Sample size: **{ul['sample_size']}**")
        if ul.get("median_response_time"):
            lines.append(f"- Median response time: **{ul['median_response_time']}s**")
        lines.append(f"- Harvestability rate: **{ul['harvestability_rate_pct']}%**")
        lines.append("\n| Status | Count |")
        lines.append("|--------|------:|")
        for status, count in sorted(ul.get("status_distribution", {}).items()):
            lines.append(f"| {status} | {count} |")
        lines.append("")

    return "\n".join(lines) + "\n"
