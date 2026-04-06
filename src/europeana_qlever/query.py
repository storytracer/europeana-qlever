"""SPARQL query generation for Europeana EDM metadata exports.

Central types:

- :class:`Query` — a named SPARQL query that generates query text on demand.
- :class:`QueryFilters` — filter parameters that express themselves as SPARQL.
- :class:`QueryRegistry` — builds and holds all :class:`Query` objects.
- :class:`SparqlHelpers` — reusable SPARQL fragment generators for EDM patterns.
"""

from __future__ import annotations

import textwrap
from collections.abc import Callable
from dataclasses import dataclass, field

from .edm_schema import (
    prefixes as edm_prefixes,
    entity_classes,
    entity_class_uri,
    entity_core_fields,
    entity_id_column,
    entity_link_property_details,
    entity_prefixes,
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

    SPARQL generation methods are private — the public interface is
    :attr:`queries` and :meth:`get`.
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
    # Registry construction
    # -------------------------------------------------------------------

    def _build(self) -> dict[str, Query]:
        q = Query
        queries: dict[str, Query] = {}

        # Pipeline — standalone exports
        queries["web_resources"] = q("web_resources",
            "Digital representations with MIME type, dimensions, file size, rights, and IIIF service detection",
            self._web_resources)

        # Entity exports — generated from schema (core + links per entity type)
        _entity_meta = {
            "agents": ("Agent", "Agents"),
            "places": ("Place", "Places"),
            "concepts": ("Concept", "Concepts"),
            "timespans": ("TimeSpan", "Timespans"),
        }
        for etype, (cls_name, label) in _entity_meta.items():
            queries[f"{etype}_core"] = q(f"{etype}_core",
                f"{label}: prefLabels with core single-valued properties",
                lambda f, _et=etype: self._entity_core(_et, f))
            queries[f"{etype}_links"] = q(f"{etype}_links",
                f"{label}: altLabels, sameAs, and all multi-valued link properties",
                lambda f, _et=etype: self._entity_links(_et, f))

        queries["institutions"] = q("institutions",
            "Organisations with multilingual labels, acronym, country, role, and Wikidata links",
            self._institutions)

        # Pipeline — component exports
        queries["items_core"] = q("items_core",
            "One row per item: type, rights, country, institution, aggregator, and single-valued aggregation properties",
            self._items_core)

        # Multi-valued item queries — generated from schema
        for col_name, attr in item_fields().items():
            if not attr.multivalued:
                continue
            pattern = attr.annotations.get("query_pattern")
            bt = attr.annotations.get("base_table")
            if not pattern or not bt:
                continue
            curie = slot_curie("Item", col_name)
            proxy_source = attr.annotations.get("proxy_source", "provider")
            if pattern == "lang_tagged":
                queries[bt] = q(bt,
                    f"All {col_name} values with language tags (multi-row per item)",
                    lambda f, _c=curie, _ps=proxy_source: self._items_lang_tagged(_c, _ps, f))
            elif pattern == "iri_or_literal":
                queries[bt] = q(bt,
                    f"{col_name.replace('_', ' ').title()} values per item with IRI flag (multi-row)",
                    lambda f, _c=curie, _cn=col_name, _ps=proxy_source: self._items_iri_or_literal(_c, _cn, _ps, f))
            elif pattern == "simple_literal":
                queries[bt] = q(bt,
                    f"{col_name.replace('_', ' ').title()} values per item (multi-row)",
                    lambda f, _c=curie, _cn=col_name, _ps=proxy_source: self._items_simple_literal(_c, _cn, _ps, f))

        # Summary queries
        queries.update({
            "items_by_country": q("items_by_country",
                "Item counts grouped by country",
                self._items_by_country),
            "items_by_language": q("items_by_language",
                "Item counts grouped by edm:language",
                self._items_by_language),
            "items_by_institution": q("items_by_institution",
                "Item counts grouped by institution (edm:dataProvider)",
                self._items_by_institution),
            "items_by_aggregator": q("items_by_aggregator",
                "Item counts grouped by aggregator (edm:provider)",
                self._items_by_aggregator),
            "items_by_type": q("items_by_type",
                "Item counts grouped by edm:type",
                self._items_by_type),
            "items_by_type_and_country": q("items_by_type_and_country",
                "Item counts grouped by edm:type and country",
                self._items_by_type_and_country),
            "items_by_type_and_language": q("items_by_type_and_language",
                "Item counts grouped by edm:type and edm:language",
                self._items_by_type_and_language),
            "items_by_year": q("items_by_year",
                "Item counts grouped by edm:year",
                self._items_by_year),
            "items_by_rights_uri": q("items_by_rights_uri",
                "Item counts grouped by rights URI",
                self._items_by_rights_uri),
            "items_by_reuse_level": q("items_by_reuse_level",
                "Item counts grouped by reuse level (open, restricted, prohibited)",
                self._items_by_reuse_level),
            "items_by_type_and_reuse_level": q("items_by_type_and_reuse_level",
                "Item counts grouped by edm:type and reuse level (open, restricted, prohibited)",
                self._items_by_type_and_reuse_level),
            "items_by_country_and_reuse_level": q("items_by_country_and_reuse_level",
                "Item counts grouped by country and reuse level (open, restricted, prohibited)",
                self._items_by_country_and_reuse_level),
            "items_by_language_and_reuse_level": q("items_by_language_and_reuse_level",
                "Item counts grouped by dc:language and reuse level (open, restricted, prohibited)",
                self._items_by_language_and_reuse_level),
            "items_by_completeness": q("items_by_completeness",
                "Item counts grouped by completeness score (1-10) and edm:type",
                self._items_by_completeness),
            "content_availability": q("content_availability",
                "Item counts by edm:type, reuse level, and content access method (direct URL, IIIF)",
                self._content_availability),
            "geolocated_places": q("geolocated_places",
                "Places with coordinates",
                self._geolocated_places),
            "iiif_availability": q("iiif_availability",
                "Items with IIIF manifests (svcs:has_service) by institution",
                self._iiif_availability),
            "mime_type_distribution": q("mime_type_distribution",
                "Item counts grouped by MIME type and edm:type",
                self._mime_type_distribution),
            "texts_by_type": q("texts_by_type",
                "dc:type value distribution for TEXT items (books, newspapers, etc.)",
                self._texts_by_type),
        })

        return queries

    # -------------------------------------------------------------------
    # Private SPARQL generators
    # -------------------------------------------------------------------

    def _web_resources(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "ebucore", "svcs"})}
            SELECT ?item ?url ?mime ?width ?height ?bytes ?wr_rights ?has_service
            WHERE {{
              ?agg edm:aggregatedCHO ?item ;
                   edm:isShownBy ?url .
              OPTIONAL {{ ?url ebucore:hasMimeType ?mime }}
              OPTIONAL {{ ?url ebucore:width ?width }}
              OPTIONAL {{ ?url ebucore:height ?height }}
              OPTIONAL {{ ?url ebucore:fileByteSize ?bytes }}
              OPTIONAL {{ ?url edm:rights ?wr_rights }}
              OPTIONAL {{ ?url svcs:has_service ?_svc }}
              BIND(BOUND(?_svc) AS ?has_service)
            }}
            {f.limit_clause()}
        """).strip()

    # -- Entity core queries — generic, driven from schema

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

    # -- Entity links queries — generic, driven from schema

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

    # -- Multi-valued item query templates — driven from schema

    def _items_lang_tagged(
        self, curie: str, proxy_source: str, filters: QueryFilters | None = None,
    ) -> str:
        """Template for lang-tagged multi-valued properties (titles, descriptions)."""
        f = filters or QueryFilters()
        # Extract the local name from the CURIE for the variable name
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
        """Template for IRI-or-literal multi-valued properties (subjects, creators, etc.)."""
        f = filters or QueryFilters()
        # Use a column-specific value variable name matching the old convention
        local = curie.split(":")[1] if ":" in curie else curie
        val_var = f"{col_name.rstrip('s')}_value" if not col_name.endswith("s_") else f"{col_name}_value"
        # Fix: subjects → subject_value, creators → creator_value, etc.
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
        """Template for simple literal multi-valued properties (dates, languages, etc.)."""
        f = filters or QueryFilters()
        local = curie.split(":")[1] if ":" in curie else curie
        # The SPARQL variable is the singular form for most, but 'year' for years
        # and 'dc_rights' stays as-is. Use the column name directly since that's
        # what the old code used (date, language, year, identifier, dc_rights).
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

    def _institutions(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "foaf", "skos", "owl"})}
            SELECT ?org ?name ?lang ?acronym ?country ?role ?wikidata
            WHERE {{
              ?org a foaf:Organization ;
                   skos:prefLabel ?name .
              BIND(LANG(?name) AS ?lang)
              OPTIONAL {{ ?org edm:acronym ?acronym }}
              OPTIONAL {{ ?org edm:country ?country }}
              OPTIONAL {{ ?org edm:europeanaRole ?role }}
              OPTIONAL {{
                ?org owl:sameAs ?wikidata .
                FILTER(STRSTARTS(STR(?wikidata), "http://www.wikidata.org/entity/"))
              }}
            }}
            {f.limit_clause()}
        """).strip()

    def _items_by_rights_uri(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm"})}
            SELECT ?rights (COUNT(?item) AS ?count)
            WHERE {{
              ?agg edm:aggregatedCHO ?item ;
                   edm:rights ?rights .
            }}
            GROUP BY ?rights
            ORDER BY DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _items_by_reuse_level(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        reuse_bind = sparql_reuse_level_bind()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm"})}
            SELECT ?reuse_level (COUNT(?item) AS ?count)
            WHERE {{
              ?agg edm:aggregatedCHO ?item ;
                   edm:rights ?rights .
              {reuse_bind}
            }}
            GROUP BY ?reuse_level
            ORDER BY DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _items_by_type_and_reuse_level(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        reuse_bind = sparql_reuse_level_bind()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "ore"})}
            SELECT ?type ?reuse_level (COUNT(?item) AS ?count)
            WHERE {{
              {S.europeana_proxy()}
              ?eProxy edm:type ?type .
              ?agg edm:aggregatedCHO ?item ;
                   edm:rights ?rights .
              {reuse_bind}
            }}
            GROUP BY ?type ?reuse_level
            ORDER BY ?type DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _items_by_country_and_reuse_level(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        reuse_bind = sparql_reuse_level_bind()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm"})}
            SELECT ?country ?reuse_level (COUNT(?item) AS ?count)
            WHERE {{
              ?agg edm:aggregatedCHO ?item ;
                   edm:rights ?rights .
              ?eAgg edm:aggregatedCHO ?item .
              ?eAgg a edm:EuropeanaAggregation .
              ?eAgg edm:country ?country .
              {reuse_bind}
            }}
            GROUP BY ?country ?reuse_level
            ORDER BY ?country DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _items_by_language_and_reuse_level(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        reuse_bind = sparql_reuse_level_bind()
        return textwrap.dedent(f"""\
            {S.prefix_block({"dc", "edm", "ore"})}
            SELECT ?language ?reuse_level (COUNT(?item) AS ?count)
            WHERE {{
              {S.provider_proxy()}
              ?proxy dc:language ?language .
              ?agg edm:aggregatedCHO ?item ;
                   edm:rights ?rights .
              {reuse_bind}
            }}
            GROUP BY ?language ?reuse_level
            ORDER BY ?language DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _items_by_completeness(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "ore"})}
            SELECT ?completeness ?type (COUNT(?item) AS ?count)
            WHERE {{
              {S.europeana_proxy()}
              ?eProxy edm:type ?type .
              {S.europeana_aggregation()}
              ?eAgg edm:completeness ?completeness .
            }}
            GROUP BY ?completeness ?type
            ORDER BY ?completeness ?type
            {f.limit_clause()}
        """).strip()

    def _content_availability(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        reuse_bind = sparql_reuse_level_bind()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "ore", "svcs"})}
            SELECT ?type ?reuse_level
                   ?has_direct_url ?has_iiif
                   (COUNT(?item) AS ?count)
            WHERE {{
              {S.europeana_proxy()}
              ?eProxy edm:type ?type .
              ?agg edm:aggregatedCHO ?item ;
                   edm:rights ?rights .
              {reuse_bind}
              OPTIONAL {{ ?agg edm:isShownBy ?_isb }}
              BIND(BOUND(?_isb) AS ?has_direct_url)
              OPTIONAL {{
                ?agg edm:isShownBy ?_wr .
                ?_wr svcs:has_service ?_svc .
              }}
              BIND(BOUND(?_svc) AS ?has_iiif)
            }}
            GROUP BY ?type ?reuse_level ?has_direct_url ?has_iiif
            ORDER BY ?type ?reuse_level DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _items_core(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "ore", "xsd"})}
            SELECT ?item ?type ?rights ?country ?dataProvider ?provider
                   ?isShownAt ?isShownBy ?preview ?landingPage
                   ?datasetName ?completeness
            WHERE {{
              {{
                SELECT ?item ?agg ?eAgg ?type ?rights ?dataProvider ?provider ?country
                WHERE {{
                  {S.europeana_proxy()}
                  ?eProxy edm:type ?type .
                  {S.aggregation()}
                  ?agg edm:rights ?rights ;
                       edm:dataProvider ?dataProvider ;
                       edm:provider ?provider .
                  {S.europeana_aggregation()}
                  ?eAgg edm:country ?country .
                  {f.to_sparql()}
                }}
              }}
              OPTIONAL {{ ?agg edm:isShownAt ?isShownAt }}
              OPTIONAL {{ ?agg edm:isShownBy ?isShownBy }}
              OPTIONAL {{ ?eAgg edm:completeness ?completeness }}
              OPTIONAL {{ ?eAgg edm:preview ?preview }}
              OPTIONAL {{ ?eAgg edm:landingPage ?landingPage }}
              OPTIONAL {{ ?eAgg edm:datasetName ?datasetName }}
            }}
            {f.limit_clause()}
        """).strip()

    def _items_by_type(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "ore"})}
            SELECT ?type (COUNT(?item) AS ?count)
            WHERE {{
              {S.europeana_proxy()}
              ?eProxy edm:type ?type .
            }}
            GROUP BY ?type
            ORDER BY DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _items_by_country(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm"})}
            SELECT ?country (COUNT(?item) AS ?count)
            WHERE {{
              ?eAgg edm:aggregatedCHO ?item .
              ?eAgg a edm:EuropeanaAggregation .
              ?eAgg edm:country ?country .
            }}
            GROUP BY ?country
            ORDER BY DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _items_by_type_and_country(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "ore"})}
            SELECT ?type ?country (COUNT(?item) AS ?count)
            WHERE {{
              {S.europeana_proxy()}
              ?eProxy edm:type ?type .
              {S.europeana_aggregation()}
              ?eAgg edm:country ?country .
            }}
            GROUP BY ?type ?country
            ORDER BY ?type DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _items_by_institution(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "skos"})}
            SELECT ?dataProvider
                   (SAMPLE(COALESCE(?enName, ?anyName)) AS ?institutionName)
                   (COUNT(DISTINCT ?item) AS ?count)
            WHERE {{
              {S.aggregation()}
              ?agg edm:dataProvider ?dataProvider .
              OPTIONAL {{ ?dataProvider skos:prefLabel ?enName . FILTER(LANG(?enName) = "en") }}
              OPTIONAL {{ ?dataProvider skos:prefLabel ?anyName }}
            }}
            GROUP BY ?dataProvider
            ORDER BY DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _items_by_aggregator(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "skos"})}
            SELECT ?provider
                   (SAMPLE(COALESCE(?enName, ?anyName)) AS ?aggregatorName)
                   (COUNT(DISTINCT ?item) AS ?count)
            WHERE {{
              {S.aggregation()}
              ?agg edm:provider ?provider .
              OPTIONAL {{ ?provider skos:prefLabel ?enName . FILTER(LANG(?enName) = "en") }}
              OPTIONAL {{ ?provider skos:prefLabel ?anyName }}
            }}
            GROUP BY ?provider
            ORDER BY DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _items_by_language(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm"})}
            SELECT ?language (COUNT(?item) AS ?count)
            WHERE {{
              {S.europeana_aggregation()}
              ?eAgg edm:language ?language .
            }}
            GROUP BY ?language
            ORDER BY DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _items_by_type_and_language(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "ore"})}
            SELECT ?type ?language (COUNT(?item) AS ?count)
            WHERE {{
              {S.europeana_proxy()}
              ?eProxy edm:type ?type .
              {S.europeana_aggregation()}
              ?eAgg edm:language ?language .
            }}
            GROUP BY ?type ?language
            ORDER BY ?type DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _mime_type_distribution(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "ebucore"})}
            SELECT ?mime (COUNT(?item) AS ?count)
            WHERE {{
              {S.aggregation()}
              ?agg edm:isShownBy ?url .
              ?url ebucore:hasMimeType ?mime .
            }}
            GROUP BY ?mime
            ORDER BY DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _items_by_year(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "ore"})}
            SELECT ?year (COUNT(?item) AS ?count)
            WHERE {{
              ?eProxy ore:proxyFor ?item .
              ?eProxy edm:europeanaProxy "true" .
              ?eProxy edm:year ?year .
            }}
            GROUP BY ?year
            ORDER BY DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _geolocated_places(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "skos", "wgs84_pos"})}
            SELECT ?place ?name ?lat ?lon
            WHERE {{
              ?place a edm:Place ;
                     wgs84_pos:lat ?lat ;
                     wgs84_pos:long ?lon ;
                     skos:prefLabel ?name .
              FILTER(LANG(?name) = "en")
            }}
            {f.limit_clause()}
        """).strip()

    def _texts_by_type(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"dc", "edm", "ore"})}
            SELECT ?dcType (COUNT(?item) AS ?count)
            WHERE {{
              {S.provider_proxy()}
              ?proxy edm:type "TEXT" .
              ?proxy dc:type ?dcType .
            }}
            GROUP BY ?dcType
            ORDER BY DESC(?count)
            {f.limit_clause()}
        """).strip()

    def _iiif_availability(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "skos", "svcs"})}
            SELECT ?dataProvider
                   (SAMPLE(COALESCE(?enName, ?anyName)) AS ?institutionName)
                   (COUNT(DISTINCT ?item) AS ?iiif_items)
            WHERE {{
              ?agg edm:aggregatedCHO ?item ;
                   edm:dataProvider ?dataProvider ;
                   edm:isShownBy ?url .
              ?url svcs:has_service ?service .
              OPTIONAL {{ ?dataProvider skos:prefLabel ?enName . FILTER(LANG(?enName) = "en") }}
              OPTIONAL {{ ?dataProvider skos:prefLabel ?anyName }}
            }}
            GROUP BY ?dataProvider
            ORDER BY DESC(?iiif_items)
            {f.limit_clause()}
        """).strip()
