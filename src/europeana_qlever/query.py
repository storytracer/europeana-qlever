"""SPARQL query generation for Europeana EDM metadata exports.

Central types:

- :class:`Query` — a named SPARQL query that generates query text on demand.
- :class:`QueryFilters` — filter parameters (currently only ``limit``).
- :class:`QueryRegistry` — builds and holds all :class:`Query` objects.
- :class:`SparqlHelpers` — reusable SPARQL fragment generators.

All queries are derived from the LinkML schema (``edm_parquet.yaml``).
Two export types produce SPARQL:

- ``values``: single SPARQL scan per table, driven by ``sparql_base_pattern``
  and per-attribute ``sparql_binding`` annotations.
- ``links_scan``: synthetic per-property scans for a ``links`` table.
  Each produces rows ``(k_iri, x_property, x_value, x_value_is_iri,
  x_value_lang)`` where ``x_property`` is a bound literal like
  ``"v_dc_subject"``.  Output is written to a Hive partition of the
  parent links directory.
"""

from __future__ import annotations

import textwrap
from collections.abc import Callable
from dataclasses import dataclass, field

from .schema_loader import (
    prefixes as edm_prefixes,
    export_classes,
    links_scan_entries,
    LinkScanEntry,
)


# ---------------------------------------------------------------------------
# SparqlHelpers
# ---------------------------------------------------------------------------


class SparqlHelpers:
    """Stateless SPARQL fragment generators for EDM triple patterns."""

    @staticmethod
    def prefix_block(needed: set[str]) -> str:
        """Generate SPARQL PREFIX declarations for the given namespace keys."""
        pfx = edm_prefixes()
        return "\n".join(
            f"PREFIX {p}: <{pfx[p]}>"
            for p in sorted(needed)
            if p in pfx
        )

    @staticmethod
    def quote(value: str) -> str:
        """Escape a string for use inside a SPARQL literal."""
        return value.replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def sample_service_clause(cho_var: str, view_name: str) -> str:
        """SERVICE block that binds ?<cho_var> to rows from the sample-items view."""
        return (
            f"SERVICE view:{view_name} "
            f"{{ [ view:column-item ?{cho_var} ] }}"
        )


S = SparqlHelpers


# ---------------------------------------------------------------------------
# QueryFilters — LIMIT + OFFSET (full filter support was removed with the
# summary-table restructuring; filters are now applied at the DuckDB layer
# on merged_items / group_items).
# ---------------------------------------------------------------------------


@dataclass
class QueryFilters:
    """Parameters for limiting SPARQL query results.

    The new pipeline applies most filtering (country, type, rights,
    institution, …) at the DuckDB layer on ``merged_items`` / ``group_items``
    rather than at SPARQL-export time.  These fields are accepted for
    CLI back-compat but currently only ``limit`` / ``offset`` are
    respected in the generated SPARQL.
    """

    limit: int | None = None
    offset: int | None = None
    sample_size: int | None = None
    sample_view_name: str = "sample-items"
    # Back-compat fields (accepted but not used during SPARQL generation)
    countries: list[str] | None = None
    types: list[str] | None = None
    rights: list[str] | None = None
    reuse_level: str | None = None
    institutions: list[str] | None = None
    aggregators: list[str] | None = None
    min_completeness: int | None = None
    year_from: int | None = None
    year_to: int | None = None
    languages: list[str] | None = None
    dataset_names: list[str] | None = None

    def limit_clause(self) -> str:
        parts: list[str] = []
        if self.limit is not None:
            parts.append(f"LIMIT {self.limit}")
        if self.offset is not None:
            parts.append(f"OFFSET {self.offset}")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


@dataclass
class Query:
    """A named SPARQL query that generates query text on demand."""

    name: str
    description: str
    _build: Callable[[QueryFilters | None], str] = field(repr=False)

    def sparql(self, filters: QueryFilters | None = None) -> str:
        return self._build(filters)

    @classmethod
    def from_sparql_string(cls, name: str, text: str) -> Query:
        return cls(name=name, description="Custom query", _build=lambda _f, _s=text: _s)


# ---------------------------------------------------------------------------
# QueryRegistry
# ---------------------------------------------------------------------------


class QueryRegistry:
    """Builds and holds all :class:`Query` objects for raw exports.

    One Query per ``values`` table (from ``export_classes()``), plus one
    Query per synthetic links_scan partition (from
    ``links_scan_entries()``).  ``links`` tables (the Hive-partitioned
    directories) themselves have no SPARQL query — they aggregate their
    partition scans.  ``merged``, ``group``, and ``map`` exports are
    composed in DuckDB.
    """

    def __init__(self) -> None:
        self._queries: dict[str, Query] = self._build()

    @property
    def queries(self) -> dict[str, Query]:
        return dict(self._queries)

    def get(self, name: str) -> Query:
        return self._queries[name]

    def _build(self) -> dict[str, Query]:
        queries: dict[str, Query] = {}

        for info in export_classes().values():
            if info.export_type != "values":
                continue
            queries[info.table_name] = Query(
                name=info.table_name,
                description=f"{info.cls_name}: raw scalar properties",
                _build=lambda f, _info=info: self._values_query(_info, f),
            )

        for scan_name, entry in links_scan_entries().items():
            queries[scan_name] = Query(
                name=scan_name,
                description=f"{entry.parent_table}: scan of {entry.curie}",
                _build=lambda f, _e=entry: self._links_scan_query(_e, f),
            )

        return queries

    # -----------------------------------------------------------------
    # values_* SPARQL generator
    # -----------------------------------------------------------------

    def _values_query(self, info, filters: QueryFilters | None) -> str:
        f = filters or QueryFilters()
        annots = info.annotations
        pfx_set = {p.strip() for p in annots.get("required_prefixes", "").split(",") if p.strip()}

        base_pattern = annots.get("sparql_base_pattern", "").strip()
        extra = annots.get("sparql_extra", "").strip()
        sample_cho_var = annots.get("sample_subject_variable", "").strip() or None

        select_parts: list[str] = []
        where_extras: list[str] = []

        for attr_name, attr in info.attributes.items():
            binding = attr.annotations.get("sparql_binding", "").strip()
            if not binding:
                # No binding annotation — assume variable exists from base pattern.
                select_parts.append(f"?{attr_name}")
                continue
            if binding.startswith("OPTIONAL") or binding.startswith("{"):
                select_parts.append(f"?{attr_name}")
                where_extras.append(binding)
            elif " AS " in binding and not binding.startswith("("):
                select_parts.append(f"({binding})")
            elif binding.startswith("("):
                select_parts.append(binding)
            elif binding.startswith("?"):
                select_parts.append(binding)
            else:
                # Multi-line binding (BIND + filter etc.).
                select_parts.append(f"?{attr_name}")
                where_extras.append(binding)

        where_lines: list[str] = []
        tail = ""
        if f.sample_size is not None and sample_cho_var:
            pfx_set.add("view")
            where_lines.append(S.sample_service_clause(sample_cho_var, f.sample_view_name))
        elif f.sample_size is not None:
            # Entity table (no CHO link) — fall back to a plain LIMIT.
            tail = f"LIMIT {f.sample_size}"

        where_lines.append(base_pattern)
        if extra:
            where_lines.append(extra)
        where_lines.extend(where_extras)
        where_body = "\n  ".join(w for w in where_lines if w)

        select_str = " ".join(select_parts)
        if not tail:
            tail = f.limit_clause()

        query = textwrap.dedent(f"""\
            {S.prefix_block(pfx_set)}
            SELECT {select_str}
            WHERE {{
              {where_body}
            }}
            {tail}
        """).strip()
        return query

    # -----------------------------------------------------------------
    # links_scan SPARQL generator (one per property)
    # -----------------------------------------------------------------

    def _links_scan_query(self, entry: LinkScanEntry, filters: QueryFilters | None) -> str:
        f = filters or QueryFilters()
        pfx_set = set(entry.required_prefixes)

        subject_clause = entry.subject_base_pattern or f"?k_iri {entry.curie} ?_raw ."
        property_literal = f'"{entry.property_column}"'

        where_lines: list[str] = []
        tail = ""
        if f.sample_size is not None and entry.sample_subject_variable:
            pfx_set.add("view")
            where_lines.append(
                S.sample_service_clause(entry.sample_subject_variable, f.sample_view_name)
            )
        elif f.sample_size is not None:
            tail = f"LIMIT {f.sample_size}"

        where_lines.append(subject_clause)
        where_lines.append(f"?k_iri {entry.curie} ?_raw .")
        where_body = "\n  ".join(where_lines)

        if not tail:
            tail = f.limit_clause()

        return textwrap.dedent(f"""\
            {S.prefix_block(pfx_set)}
            SELECT ?k_iri ({property_literal} AS ?x_property) (STR(?_raw) AS ?x_value) (isIRI(?_raw) AS ?x_value_is_iri) (LANG(?_raw) AS ?x_value_lang)
            WHERE {{
              {where_body}
            }}
            {tail}
        """).strip()
