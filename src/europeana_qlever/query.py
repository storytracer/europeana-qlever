"""SPARQL query generation for Europeana EDM metadata exports.

Central types:

- :class:`Query` — a named SPARQL query that generates query text on demand.
- :class:`QueryFilters` — filter parameters that express themselves as SPARQL.
- :class:`QueryRegistry` — builds and holds all :class:`Query` objects.
- :class:`SparqlHelpers` — reusable SPARQL fragment generators for EDM patterns.

All queries are generated from the LinkML schema — scan and summary exports
read their SPARQL patterns from class annotations; entity and base-table
exports use generic generators driven by class attributes.
"""

from __future__ import annotations

import textwrap
from collections.abc import Callable
from dataclasses import dataclass, field

from .schema_loader import (
    prefixes as edm_prefixes,
    entity_classes,
    entity_class_uri,
    entity_core_fields,
    entity_id_column,
    entity_link_property_details,
    entity_prefixes,
    export_classes,
    item_fields,
    slot_curie,
)
from .rights import sparql_reuse_level_bind, sparql_reuse_level_filter


# ---------------------------------------------------------------------------
# SparqlHelpers — reusable SPARQL fragment generators
# ---------------------------------------------------------------------------

class SparqlHelpers:
    """Stateless SPARQL fragment generators for EDM triple patterns."""

    @staticmethod
    def prefix_block(needed: set[str]) -> str:
        """Generate SPARQL PREFIX declarations for the given namespace keys."""
        pfx = edm_prefixes()
        return "\n".join(
            f"PREFIX {p}: <{pfx[p]}>"
            for p in sorted(needed) if p in pfx
        )

    @staticmethod
    def provider_proxy(item: str = "?item", proxy: str = "?proxy") -> str:
        return (
            f"{proxy} ore:proxyFor {item} .\n"
            f'  FILTER NOT EXISTS {{ {proxy} edm:europeanaProxy "true" . }}'
        )

    @staticmethod
    def europeana_proxy(item: str = "?item", eproxy: str = "?eProxy") -> str:
        return (
            f"{eproxy} ore:proxyFor {item} .\n"
            f'  {eproxy} edm:europeanaProxy "true" .'
        )

    @staticmethod
    def aggregation(item: str = "?item", agg: str = "?agg") -> str:
        return f"{agg} edm:aggregatedCHO {item} ."

    @staticmethod
    def europeana_aggregation(item: str = "?item", eagg: str = "?eAgg") -> str:
        return (
            f"{eagg} edm:aggregatedCHO {item} .\n"
            f"  {eagg} a edm:EuropeanaAggregation ."
        )

    @staticmethod
    def quote(value: str) -> str:
        """Escape a string for use inside a SPARQL literal."""
        return value.replace("\\", "\\\\").replace('"', '\\"')


# Shorthand used throughout the SPARQL generators.
S = SparqlHelpers


# ---------------------------------------------------------------------------
# QueryFilters — filter parameters that express themselves as SPARQL
# ---------------------------------------------------------------------------

@dataclass
class QueryFilters:
    """Parameters for filtering SPARQL query results."""

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
    limit: int | None = None
    offset: int | None = None

    def to_sparql(
        self,
        *,
        country_var: str = "?country",
        type_var: str = "?type",
        rights_var: str = "?rights",
        institution_var: str = "?dataProvider",
        aggregator_var: str = "?provider",
        completeness_var: str = "?completeness",
        year_var: str | None = None,
        language_var: str | None = None,
        dataset_var: str | None = None,
    ) -> str:
        """Generate SPARQL FILTER clauses from these parameters."""
        clauses: list[str] = []

        if self.countries:
            vals = ", ".join(f'"{S.quote(c)}"' for c in self.countries)
            clauses.append(f"FILTER({country_var} IN ({vals}))")

        if self.types:
            vals = ", ".join(f'"{S.quote(t)}"' for t in self.types)
            clauses.append(f"FILTER({type_var} IN ({vals}))")

        if self.rights:
            vals = ", ".join(f"<{u}>" for u in self.rights)
            clauses.append(f"FILTER({rights_var} IN ({vals}))")
        elif self.reuse_level:
            clauses.append(sparql_reuse_level_filter(self.reuse_level, rights_var))

        if self.institutions:
            vals = ", ".join(f'"{S.quote(p)}"' for p in self.institutions)
            clauses.append(f"FILTER({institution_var} IN ({vals}))")

        if self.aggregators:
            vals = ", ".join(f'"{S.quote(a)}"' for a in self.aggregators)
            clauses.append(f"FILTER({aggregator_var} IN ({vals}))")

        if self.min_completeness is not None:
            clauses.append(
                f"FILTER(xsd:integer({completeness_var}) >= {self.min_completeness})"
            )

        if year_var:
            if self.year_from is not None:
                clauses.append(f"FILTER(xsd:integer({year_var}) >= {self.year_from})")
            if self.year_to is not None:
                clauses.append(f"FILTER(xsd:integer({year_var}) <= {self.year_to})")

        if language_var and self.languages:
            vals = ", ".join(f'"{S.quote(lang)}"' for lang in self.languages)
            clauses.append(f"FILTER({language_var} IN ({vals}))")

        if dataset_var and self.dataset_names:
            vals = ", ".join(f'"{S.quote(d)}"' for d in self.dataset_names)
            clauses.append(f"FILTER({dataset_var} IN ({vals}))")

        return "\n  ".join(clauses)

    def limit_clause(self) -> str:
        """Generate SPARQL LIMIT/OFFSET clause."""
        parts: list[str] = []
        if self.limit is not None:
            parts.append(f"LIMIT {self.limit}")
        if self.offset is not None:
            parts.append(f"OFFSET {self.offset}")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Query — a named SPARQL query
# ---------------------------------------------------------------------------

@dataclass
class Query:
    """A named SPARQL query that generates query text on demand.

    The *_build* callable receives optional :class:`QueryFilters` and
    returns a SPARQL string.  Call :meth:`sparql` to invoke it.
    """

    name: str
    description: str
    _build: Callable[[QueryFilters | None], str] = field(repr=False)

    def sparql(self, filters: QueryFilters | None = None) -> str:
        """Generate SPARQL for this query, optionally applying *filters*."""
        return self._build(filters)

    @classmethod
    def from_sparql_string(cls, name: str, text: str) -> Query:
        """Create a Query from a raw SPARQL string (e.g. a .sparql file)."""
        return cls(name=name, description="Custom query", _build=lambda _f, _s=text: _s)



# ---------------------------------------------------------------------------
# QueryRegistry — builds and holds all Query objects
# ---------------------------------------------------------------------------

class QueryRegistry:
    """Builds and holds all :class:`Query` objects.

    All queries are discovered from schema annotations.  No per-query
    methods — the generation engine dispatches by ``export_type``.
    """

    def __init__(self) -> None:
        self._queries: dict[str, Query] = self._build()

    @property
    def queries(self) -> dict[str, Query]:
        """All registered queries (copy)."""
        return dict(self._queries)

    def get(self, name: str) -> Query:
        """Look up a single query by name."""
        return self._queries[name]

    # -------------------------------------------------------------------
    # Registry construction — schema-driven
    # -------------------------------------------------------------------

    def _build(self) -> dict[str, Query]:
        q = Query
        queries: dict[str, Query] = {}

        for export_name, info in export_classes().items():
            et = info.export_type

            if et == "composite":
                # Composite exports (items_resolved) have no SPARQL query
                continue

            if et == "entity":
                # Entity exports use the existing generic generators
                etype = export_name.rsplit("_", 1)[0]  # agents_core → agents
                if export_name.endswith("_core"):
                    queries[export_name] = q(
                        export_name,
                        info.cls_name + ": core single-valued properties",
                        lambda f, _et=etype: self._entity_core(_et, f),
                    )
                elif export_name.endswith("_links"):
                    queries[export_name] = q(
                        export_name,
                        info.cls_name + ": multi-valued link properties",
                        lambda f, _et=etype: self._entity_links(_et, f),
                    )
                continue

            if et == "base_table":
                # Base table exports use the existing pattern-based generators
                for col_name, attr in item_fields().items():
                    if attr.annotations.get("base_table") != export_name:
                        continue
                    pattern = attr.annotations.get("query_pattern")
                    curie = slot_curie("Item", col_name)
                    proxy_source = attr.annotations.get("proxy_source", "provider")
                    if pattern == "lang_tagged":
                        queries[export_name] = q(
                            export_name,
                            f"All {col_name} values with language tags",
                            lambda f, _c=curie, _ps=proxy_source: self._items_lang_tagged(_c, _ps, f),
                        )
                    elif pattern == "iri_or_literal":
                        queries[export_name] = q(
                            export_name,
                            f"{col_name.replace('_', ' ').title()} values per item with IRI flag",
                            lambda f, _c=curie, _cn=col_name, _ps=proxy_source: self._items_iri_or_literal(_c, _cn, _ps, f),
                        )
                    elif pattern == "simple_literal":
                        queries[export_name] = q(
                            export_name,
                            f"{col_name.replace('_', ' ').title()} values per item",
                            lambda f, _c=curie, _cn=col_name, _ps=proxy_source: self._items_simple_literal(_c, _cn, _ps, f),
                        )
                    break
                continue

            if et == "summary":
                # Summary exports: SPARQL is assembled from schema annotations
                queries[export_name] = q(
                    export_name,
                    info.cls_name + ": " + (
                        next(iter(info.attributes)).replace("_", " ") + " summary"
                        if info.attributes else "summary"
                    ),
                    lambda f, _info=info: self._generate_summary_query(_info, f),
                )
                continue

            if et == "scan":
                # Scan exports: SPARQL pattern + per-column bindings from schema
                queries[export_name] = q(
                    export_name,
                    info.cls_name + ": flat scan",
                    lambda f, _info=info: self._generate_scan_query(_info, f),
                )
                continue

        return queries

    # -------------------------------------------------------------------
    # Generic SPARQL generators — driven by schema annotations
    # -------------------------------------------------------------------

    def _generate_summary_query(
        self, info, filters: QueryFilters | None = None,
    ) -> str:
        """Generate a GROUP BY summary query from schema annotations."""
        f = filters or QueryFilters()
        annots = info.annotations
        pfx_str = annots.get("required_prefixes", "edm")
        pfx_set = {p.strip() for p in pfx_str.split(",") if p.strip()}

        # Read the base WHERE pattern from schema
        pattern = annots.get("sparql_pattern", "").strip()
        # Substitute reuse_bind placeholder if present
        if "{reuse_bind}" in pattern:
            pattern = pattern.replace("{reuse_bind}", sparql_reuse_level_bind())

        # Build SELECT and GROUP BY from attribute annotations
        select_parts: list[str] = []
        group_by_parts: list[str] = []

        for attr_name, attr in info.attributes.items():
            agg = attr.annotations.get("aggregation", "")
            is_group = attr.annotations.get("group_by", "") == "true"
            if is_group:
                select_parts.append(f"?{attr_name}")
                group_by_parts.append(f"?{attr_name}")
            elif agg:
                select_parts.append(f"({agg} AS ?{attr_name})")

        order_by = annots.get("order_by", "")

        select_str = " ".join(select_parts)
        group_str = " ".join(group_by_parts)

        result = f"{S.prefix_block(pfx_set)}\n"
        result += f"SELECT {select_str}\n"
        result += f"WHERE {{\n  {pattern}\n}}\n"
        if group_str:
            result += f"GROUP BY {group_str}\n"
        if order_by:
            result += f"ORDER BY {order_by}\n"
        result += f.limit_clause()
        return result.strip()

    def _generate_scan_query(
        self, info, filters: QueryFilters | None = None,
    ) -> str:
        """Generate a flat scan query from schema annotations."""
        f = filters or QueryFilters()
        annots = info.annotations
        pfx_str = annots.get("required_prefixes", "edm")
        pfx_set = {p.strip() for p in pfx_str.split(",") if p.strip()}

        # Read the base WHERE pattern from schema
        pattern = annots.get("sparql_pattern", "").strip()

        # Substitute filter placeholder if present
        supports_filters = annots.get("supports_filters", "") == "true"
        if supports_filters and "{filters}" in pattern:
            pattern = pattern.replace("{filters}", f.to_sparql())

        # Build SELECT variables and OPTIONAL clauses from attribute bindings
        select_vars: list[str] = []
        optional_clauses: list[str] = []

        for attr_name, attr in info.attributes.items():
            binding = attr.annotations.get("sparql_binding", "")
            if not binding:
                # Simple variable — just add to SELECT
                select_vars.append(f"?{attr_name}")
            elif binding.startswith("?"):
                # Direct variable reference
                select_vars.append(binding)
            elif binding.strip().startswith("OPTIONAL"):
                # OPTIONAL clause — add variable to SELECT and clause to WHERE
                select_vars.append(f"?{attr_name}")
                optional_clauses.append(binding.strip())
            else:
                # Multi-line binding (e.g., OPTIONAL + BIND)
                select_vars.append(f"?{attr_name}")
                optional_clauses.append(binding.strip())

        select_str = " ".join(select_vars)
        opt_str = "\n  ".join(optional_clauses)

        result = f"{S.prefix_block(pfx_set)}\n"
        result += f"SELECT {select_str}\n"
        result += f"WHERE {{\n  {pattern}\n"
        if opt_str:
            result += f"  {opt_str}\n"
        result += "}\n"
        result += f.limit_clause()
        return result.strip()

    # -------------------------------------------------------------------
    # Entity core/links generators — already generic
    # -------------------------------------------------------------------

    def _entity_core(self, entity_type: str, filters: QueryFilters | None = None) -> str:
        """Generate core export query for any entity type from schema."""
        f = filters or QueryFilters()
        id_col = entity_id_column(entity_type)
        class_uri = entity_class_uri(entity_type)
        pfx_needed = entity_prefixes(entity_type)
        core = entity_core_fields(entity_type)

        select_vars = [f"?{id_col}", "?pref_label", "?pref_label_lang"]
        select_vars.extend(f"?{name}" for name in core)

        optionals = []
        for name, attr in core.items():
            if attr.slot_uri:
                optionals.append(
                    f"OPTIONAL {{ ?{id_col} {attr.slot_uri} ?{name} }}"
                )

        return textwrap.dedent(f"""\
            {S.prefix_block(pfx_needed)}
            SELECT {' '.join(select_vars)}
            WHERE {{
              ?{id_col} a {class_uri} ;
                     skos:prefLabel ?pref_label .
              BIND(LANG(?pref_label) AS ?pref_label_lang)
              {"".join(chr(10) + "  " + opt for opt in optionals)}
            }}
            {f.limit_clause()}
        """).strip()

    def _entity_links(self, entity_type: str, filters: QueryFilters | None = None) -> str:
        """Generate links export query for any entity type from schema."""
        f = filters or QueryFilters()
        id_col = entity_id_column(entity_type)
        class_uri = entity_class_uri(entity_type)
        pfx_needed = entity_prefixes(entity_type)
        link_props = entity_link_property_details(entity_type)

        unions = []
        for lp in link_props:
            lang_bind = 'BIND(LANG(?value) AS ?lang)' if lp.has_lang else 'BIND("" AS ?lang)'
            unions.append(
                f'{{\n    ?{id_col} {lp.curie} ?value .\n'
                f'    BIND("{lp.name}" AS ?property)\n'
                f'    {lang_bind}\n  }}'
            )

        union_block = " UNION ".join(unions)
        return textwrap.dedent(f"""\
            {S.prefix_block(pfx_needed)}
            SELECT ?{id_col} ?property ?value ?lang
            WHERE {{
              ?{id_col} a {class_uri} .
              {union_block}
            }}
            {f.limit_clause()}
        """).strip()

    # -------------------------------------------------------------------
    # Multi-valued item query templates — driven from schema
    # -------------------------------------------------------------------

    def _items_lang_tagged(
        self, curie: str, proxy_source: str, filters: QueryFilters | None = None,
    ) -> str:
        f = filters or QueryFilters()
        local = curie.split(":")[1] if ":" in curie else curie
        prefix_keys = {"dc", "edm", "ore"}
        if proxy_source == "europeana":
            proxy_block = S.europeana_proxy()
            proxy_var = "?eProxy"
        else:
            proxy_block = S.provider_proxy()
            proxy_var = "?proxy"
        return textwrap.dedent(f"""\
            {S.prefix_block(prefix_keys)}
            SELECT ?item ?{local} ?lang
            WHERE {{
              {proxy_block}
              {proxy_var} {curie} ?{local} .
              BIND(LANG(?{local}) AS ?lang)
            }}
            {f.limit_clause()}
        """).strip()

    def _items_iri_or_literal(
        self, curie: str, col_name: str, proxy_source: str,
        filters: QueryFilters | None = None,
    ) -> str:
        f = filters or QueryFilters()
        stem = col_name.rstrip("s")
        val_var = f"{stem}_value"
        prefix_keys = {"dc", "edm", "ore"}
        if proxy_source == "europeana":
            proxy_block = S.europeana_proxy()
            proxy_var = "?eProxy"
        else:
            proxy_block = S.provider_proxy()
            proxy_var = "?proxy"
        raw_var = f"?_{stem[0]}v"
        return textwrap.dedent(f"""\
            {S.prefix_block(prefix_keys)}
            SELECT ?item (STR({raw_var}) AS ?{val_var}) (isIRI({raw_var}) AS ?is_iri)
            WHERE {{
              {proxy_block}
              {proxy_var} {curie} {raw_var} .
            }}
            {f.limit_clause()}
        """).strip()

    def _items_simple_literal(
        self, curie: str, col_name: str, proxy_source: str,
        filters: QueryFilters | None = None,
    ) -> str:
        f = filters or QueryFilters()
        sparql_var_name = col_name.rstrip("s") if col_name != "dc_rights" else "dc_rights"
        prefix_keys = {"dc", "edm", "ore"}
        if proxy_source == "europeana":
            proxy_block = S.europeana_proxy()
            proxy_var = "?eProxy"
        else:
            proxy_block = S.provider_proxy()
            proxy_var = "?proxy"
        return textwrap.dedent(f"""\
            {S.prefix_block(prefix_keys)}
            SELECT ?item ?{sparql_var_name}
            WHERE {{
              {proxy_block}
              {proxy_var} {curie} ?{sparql_var_name} .
            }}
            {f.limit_clause()}
        """).strip()
