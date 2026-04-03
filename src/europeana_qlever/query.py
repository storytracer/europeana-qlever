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

from .constants import EDM_PREFIXES
from .rights import sparql_reuse_level_bind, sparql_reuse_level_filter


# ---------------------------------------------------------------------------
# SparqlHelpers — reusable SPARQL fragment generators
# ---------------------------------------------------------------------------

class SparqlHelpers:
    """Stateless SPARQL fragment generators for EDM triple patterns."""

    @staticmethod
    def prefix_block(needed: set[str]) -> str:
        """Generate SPARQL PREFIX declarations for the given namespace keys."""
        return "\n".join(
            f"PREFIX {p}: <{EDM_PREFIXES[p]}>"
            for p in sorted(needed) if p in EDM_PREFIXES
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
    providers: list[str] | None = None
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
        provider_var: str = "?dataProvider",
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

        if self.providers:
            vals = ", ".join(f'"{S.quote(p)}"' for p in self.providers)
            clauses.append(f"FILTER({provider_var} IN ({vals}))")

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
        return {
            # Pipeline — standalone exports
            "web_resources": q("web_resources",
                "Digital representation URLs with MIME type, dimensions, and file size",
                self._web_resources),
            "agents": q("agents",
                "People and organisations with multilingual labels, birth/death dates, profession, and Wikidata links",
                self._agents),
            "places": q("places",
                "Locations with multilingual labels, coordinates, and Wikidata links",
                self._places),
            "concepts": q("concepts",
                "SKOS concepts with hierarchy, scheme, and cross-scheme matches",
                self._concepts),
            "timespans": q("timespans",
                "Time periods with multilingual labels, begin/end dates, and Wikidata links",
                self._timespans),
            "data_providers": q("data_providers",
                "Organisations with multilingual labels, acronym, country, role, and Wikidata links",
                self._data_providers),
            # Pipeline — component exports
            "items_core": q("items_core",
                "One row per item: type, rights, country, data provider, and single-valued aggregation properties",
                self._items_core),
            "items_titles": q("items_titles",
                "All title values with language tags (multi-row per item)",
                self._items_titles),
            "items_descriptions": q("items_descriptions",
                "All description values with language tags (multi-row per item)",
                self._items_descriptions),
            "items_subjects": q("items_subjects",
                "Subject values per item (multi-row)",
                self._items_subjects),
            "items_dates": q("items_dates",
                "Date values per item (multi-row)",
                self._items_dates),
            "items_languages": q("items_languages",
                "Language codes per item (multi-row)",
                self._items_languages),
            "items_years": q("items_years",
                "Normalised edm:year values from Europeana proxy (multi-row per item)",
                self._items_years),
            "items_creators": q("items_creators",
                "Creator URIs and literals per item with IRI flag (multi-row)",
                self._items_creators),
            # Summary queries
            "items_by_country": q("items_by_country",
                "Item counts grouped by country",
                self._items_by_country),
            "items_by_language": q("items_by_language",
                "Item counts grouped by edm:language",
                self._items_by_language),
            "items_by_provider": q("items_by_provider",
                "Item counts grouped by data provider",
                self._items_by_provider),
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
                "Items with IIIF manifests (svcs:has_service) by provider",
                self._iiif_availability),
            "mime_type_distribution": q("mime_type_distribution",
                "Item counts grouped by MIME type and edm:type",
                self._mime_type_distribution),
            "texts_by_type": q("texts_by_type",
                "dc:type value distribution for TEXT items (books, newspapers, etc.)",
                self._texts_by_type),
        }

    # -------------------------------------------------------------------
    # Private SPARQL generators
    # -------------------------------------------------------------------

    def _web_resources(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "ebucore"})}
            SELECT ?item ?url ?mime ?width ?height ?bytes
            WHERE {{
              ?agg edm:aggregatedCHO ?item ;
                   edm:isShownBy ?url .
              OPTIONAL {{ ?url ebucore:hasMimeType ?mime }}
              OPTIONAL {{ ?url ebucore:width ?width }}
              OPTIONAL {{ ?url ebucore:height ?height }}
              OPTIONAL {{ ?url ebucore:fileByteSize ?bytes }}
            }}
            {f.limit_clause()}
        """).strip()

    def _agents(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "skos", "rdaGr2", "owl"})}
            SELECT ?agent ?name ?lang ?birth ?death ?profession ?wikidata
            WHERE {{
              ?agent a edm:Agent ;
                     skos:prefLabel ?name .
              BIND(LANG(?name) AS ?lang)
              OPTIONAL {{ ?agent rdaGr2:dateOfBirth ?birth }}
              OPTIONAL {{ ?agent rdaGr2:dateOfDeath ?death }}
              OPTIONAL {{ ?agent rdaGr2:professionOrOccupation ?profession }}
              OPTIONAL {{
                ?agent owl:sameAs ?wikidata .
                FILTER(STRSTARTS(STR(?wikidata), "http://www.wikidata.org/entity/"))
              }}
            }}
            {f.limit_clause()}
        """).strip()

    def _places(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "skos", "wgs84_pos", "owl"})}
            SELECT ?place ?name ?lang ?lat ?lon ?wikidata
            WHERE {{
              ?place a edm:Place ;
                     skos:prefLabel ?name .
              BIND(LANG(?name) AS ?lang)
              OPTIONAL {{ ?place wgs84_pos:lat ?lat }}
              OPTIONAL {{ ?place wgs84_pos:long ?lon }}
              OPTIONAL {{
                ?place owl:sameAs ?wikidata .
                FILTER(STRSTARTS(STR(?wikidata), "http://www.wikidata.org/entity/"))
              }}
            }}
            {f.limit_clause()}
        """).strip()

    def _concepts(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"skos", "owl"})}
            SELECT ?concept ?label ?lang ?scheme ?broader ?exactMatch
            WHERE {{
              ?concept a skos:Concept ;
                       skos:prefLabel ?label .
              BIND(LANG(?label) AS ?lang)
              OPTIONAL {{ ?concept skos:inScheme ?scheme }}
              OPTIONAL {{ ?concept skos:broader ?broader }}
              OPTIONAL {{ ?concept skos:exactMatch ?exactMatch }}
            }}
            {f.limit_clause()}
        """).strip()

    def _timespans(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "skos", "owl"})}
            SELECT ?timespan ?label ?lang ?begin ?end ?notation ?wikidata
            WHERE {{
              ?timespan a edm:TimeSpan ;
                        skos:prefLabel ?label .
              BIND(LANG(?label) AS ?lang)
              OPTIONAL {{ ?timespan edm:begin ?begin }}
              OPTIONAL {{ ?timespan edm:end ?end }}
              OPTIONAL {{ ?timespan skos:notation ?notation }}
              OPTIONAL {{
                ?timespan owl:sameAs ?wikidata .
                FILTER(STRSTARTS(STR(?wikidata), "http://www.wikidata.org/entity/"))
              }}
            }}
            {f.limit_clause()}
        """).strip()

    def _data_providers(self, filters: QueryFilters | None = None) -> str:
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
            SELECT ?item ?type ?rights ?country ?dataProvider
                   ?isShownAt ?isShownBy ?preview ?landingPage
                   ?datasetName ?completeness
            WHERE {{
              {{
                SELECT ?item ?agg ?eAgg ?type ?rights ?dataProvider ?country
                WHERE {{
                  {S.europeana_proxy()}
                  ?eProxy edm:type ?type .
                  {S.aggregation()}
                  ?agg edm:rights ?rights ;
                       edm:dataProvider ?dataProvider .
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

    def _items_titles(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"dc", "edm", "ore"})}
            SELECT ?item ?title ?lang
            WHERE {{
              {S.provider_proxy()}
              ?proxy dc:title ?title .
              BIND(LANG(?title) AS ?lang)
            }}
            {f.limit_clause()}
        """).strip()

    def _items_descriptions(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"dc", "edm", "ore"})}
            SELECT ?item ?description ?lang
            WHERE {{
              {S.provider_proxy()}
              ?proxy dc:description ?description .
              BIND(LANG(?description) AS ?lang)
            }}
            {f.limit_clause()}
        """).strip()

    def _items_subjects(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"dc", "edm", "ore"})}
            SELECT ?item (STR(?_sv) AS ?subject_value) (isIRI(?_sv) AS ?is_iri)
            WHERE {{
              {S.provider_proxy()}
              ?proxy dc:subject ?_sv .
            }}
            {f.limit_clause()}
        """).strip()

    def _items_dates(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"dc", "edm", "ore"})}
            SELECT ?item ?date
            WHERE {{
              {S.provider_proxy()}
              ?proxy dc:date ?date .
            }}
            {f.limit_clause()}
        """).strip()

    def _items_languages(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"dc", "edm", "ore"})}
            SELECT ?item ?language
            WHERE {{
              {S.provider_proxy()}
              ?proxy dc:language ?language .
            }}
            {f.limit_clause()}
        """).strip()

    def _items_years(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "ore"})}
            SELECT ?item ?year
            WHERE {{
              ?eProxy ore:proxyFor ?item .
              ?eProxy edm:europeanaProxy "true" .
              ?eProxy edm:year ?year .
            }}
            {f.limit_clause()}
        """).strip()

    def _items_creators(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"dc", "edm", "ore"})}
            SELECT ?item (STR(?_cv) AS ?creator_value) (isIRI(?_cv) AS ?is_iri)
            WHERE {{
              {S.provider_proxy()}
              ?proxy dc:creator ?_cv .
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

    def _items_by_provider(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        return textwrap.dedent(f"""\
            {S.prefix_block({"edm", "skos"})}
            SELECT ?dataProvider
                   (SAMPLE(COALESCE(?enName, ?anyName)) AS ?providerName)
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
                   (SAMPLE(COALESCE(?enName, ?anyName)) AS ?providerName)
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
