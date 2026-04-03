"""Dynamic SPARQL query generator for Europeana EDM metadata exports.

Generates parameterised SPARQL queries for exporting Europeana data as
Parquet files. Replaces the former static .sparql files with a programmatic
``QueryBuilder`` that supports filters, language priority, and reusable
SPARQL fragments.

The hybrid export pipeline uses ``QuerySpec`` to describe both simple
SPARQL exports and composite DuckDB exports that join multiple base
table Parquet files.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field

from .constants import EDM_PREFIXES
from .rights import sparql_reuse_level_bind, sparql_reuse_level_filter


# ---------------------------------------------------------------------------
# QuerySpec — unified descriptor for simple and composite exports
# ---------------------------------------------------------------------------

@dataclass
class QuerySpec:
    """Specification for a single export.

    Simple SPARQL exports have *sparql* set.  Composite exports (e.g.
    ``items_enriched``) have *compose_steps* set, *sparql* ``None``,
    and *depends_on* listing the required base tables.  Each step is
    executed individually with per-step progress logging.
    """

    name: str
    sparql: str | None = None
    compose_steps: list | None = None
    depends_on: list[str] = field(default_factory=list)
    description: str = ""

    @property
    def is_composite(self) -> bool:
        return self.compose_steps is not None

    @property
    def query_sets(self) -> list[str]:
        """Names of all query sets this spec belongs to."""
        return [qs.name for qs in QUERY_SETS.values() if self.name in qs.members]


# ---------------------------------------------------------------------------
# QuerySet — named, non-exclusive collection of queries
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class QuerySet:
    """A named collection of queries.  Queries can belong to multiple sets."""

    name: str
    description: str
    members: tuple[str, ...]

    def resolve(self, registry: dict[str, QuerySpec]) -> dict[str, QuerySpec]:
        """Return the subset of *registry* matching this set's members."""
        return {n: registry[n] for n in self.members if n in registry}


# ---------------------------------------------------------------------------
# Filter dataclass
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
    languages: list[str] | None = None      # Additional languages beyond English + vernacular
    dataset_names: list[str] | None = None
    limit: int | None = None
    offset: int | None = None


# ---------------------------------------------------------------------------
# Query set definitions
# ---------------------------------------------------------------------------

QUERY_SETS: dict[str, QuerySet] = {
    "pipeline": QuerySet(
        "pipeline",
        "Full Parquet export pipeline (standalone + component + composite)",
        (
            "web_resources",
            "agents", "places", "concepts", "timespans",
            "items_core", "items_titles", "items_descriptions",
            "items_subjects", "items_dates", "items_languages",
            "items_years", "items_creators",
            "items_enriched",
        ),
    ),
    "summary": QuerySet(
        "summary",
        "Dataset statistics — GROUP BY / COUNT aggregates",
        (
            "items_by_country", "items_by_language", "items_by_provider",
            "items_by_type", "items_by_type_and_country",
            "items_by_type_and_language", "items_by_year",
            "items_by_rights_uri", "items_by_reuse_level",
            "mime_type_distribution", "geolocated_places",
            "iiif_availability", "texts_by_type",
        ),
    ),
    "items": QuerySet(
        "items",
        "All item-related queries",
        (
            "items_core", "items_titles", "items_descriptions",
            "items_subjects", "items_dates", "items_languages",
            "items_years", "items_creators", "items_enriched",
            "web_resources",
            "items_by_country", "items_by_language", "items_by_provider",
            "items_by_type", "items_by_type_and_country",
            "items_by_type_and_language", "items_by_year",
            "items_by_rights_uri", "items_by_reuse_level",
            "iiif_availability", "mime_type_distribution", "texts_by_type",
        ),
    ),
    "entities": QuerySet(
        "entities",
        "Contextual entity queries (agents, places, concepts, timespans)",
        ("agents", "places", "concepts", "timespans", "geolocated_places"),
    ),
    "rights": QuerySet(
        "rights",
        "Rights and licensing queries",
        ("items_by_rights_uri", "items_by_reuse_level"),
    ),
}


# ---------------------------------------------------------------------------
# QueryBuilder
# ---------------------------------------------------------------------------

class QueryBuilder:
    """Generates SPARQL queries for Europeana EDM metadata exports.

    Instantiate with optional ``extra_languages`` for label resolution.
    Access queries via :meth:`all_queries` or :meth:`queries_for_set`.
    """

    def __init__(self, extra_languages: list[str] | None = None) -> None:
        self.extra_languages: list[str] = extra_languages or []

    # -----------------------------------------------------------------------
    # Private helpers — SPARQL fragment generators
    # -----------------------------------------------------------------------

    def _prefix_block(self, needed: set[str]) -> str:
        lines = [
            f"PREFIX {p}: <{EDM_PREFIXES[p]}>"
            for p in sorted(needed)
            if p in EDM_PREFIXES
        ]
        return "\n".join(lines)

    def _provider_proxy(self, item: str = "?item", proxy: str = "?proxy") -> str:
        return (
            f"{proxy} ore:proxyFor {item} .\n"
            f'  FILTER NOT EXISTS {{ {proxy} edm:europeanaProxy "true" . }}'
        )

    def _europeana_proxy(self, item: str = "?item", eproxy: str = "?eProxy") -> str:
        return (
            f"{eproxy} ore:proxyFor {item} .\n"
            f'  {eproxy} edm:europeanaProxy "true" .'
        )

    def _aggregation(self, item: str = "?item", agg: str = "?agg") -> str:
        return f"{agg} edm:aggregatedCHO {item} ."

    def _europeana_aggregation(self, item: str = "?item", eagg: str = "?eAgg") -> str:
        return (
            f"{eagg} edm:aggregatedCHO {item} .\n"
            f"  {eagg} a edm:EuropeanaAggregation ."
        )

    def _build_filters(
        self,
        f: QueryFilters,
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
        clauses: list[str] = []

        if f.countries:
            vals = ", ".join(f'"{self._quote(c)}"' for c in f.countries)
            clauses.append(f"FILTER({country_var} IN ({vals}))")

        if f.types:
            vals = ", ".join(f'"{self._quote(t)}"' for t in f.types)
            clauses.append(f"FILTER({type_var} IN ({vals}))")

        if f.rights:
            vals = ", ".join(f"<{u}>" for u in f.rights)
            clauses.append(f"FILTER({rights_var} IN ({vals}))")
        elif f.reuse_level:
            clauses.append(
                sparql_reuse_level_filter(f.reuse_level, rights_var)
            )

        if f.providers:
            vals = ", ".join(f'"{self._quote(p)}"' for p in f.providers)
            clauses.append(f"FILTER({provider_var} IN ({vals}))")

        if f.min_completeness is not None:
            clauses.append(
                f"FILTER(xsd:integer({completeness_var}) >= {f.min_completeness})"
            )

        if year_var:
            if f.year_from is not None:
                clauses.append(
                    f"FILTER(xsd:integer({year_var}) >= {f.year_from})"
                )
            if f.year_to is not None:
                clauses.append(
                    f"FILTER(xsd:integer({year_var}) <= {f.year_to})"
                )

        if language_var and f.languages:
            vals = ", ".join(f'"{self._quote(l)}"' for l in f.languages)
            clauses.append(f"FILTER({language_var} IN ({vals}))")

        if dataset_var and f.dataset_names:
            vals = ", ".join(f'"{self._quote(d)}"' for d in f.dataset_names)
            clauses.append(f"FILTER({dataset_var} IN ({vals}))")

        return "\n  ".join(clauses)

    def _limit_offset(self, f: QueryFilters) -> str:
        parts: list[str] = []
        if f.limit is not None:
            parts.append(f"LIMIT {f.limit}")
        if f.offset is not None:
            parts.append(f"OFFSET {f.offset}")
        return "\n".join(parts)

    # -- Language resolution helpers -----------------------------------------

    def _extra_langs(self, filters: QueryFilters | None) -> list[str]:
        """Return effective extra languages, preferring filter override."""
        if filters and filters.languages:
            return list(filters.languages)
        return list(self.extra_languages)

    def _bind_vernacular(self, proxy_var: str = "?proxy") -> str:
        """Bind the item's vernacular language from dc:language.

        Uses a SAMPLE subquery to pick exactly one language per item,
        preventing row multiplication when dc:language is multi-valued.
        """
        return (
            f"OPTIONAL {{ SELECT {proxy_var} (SAMPLE(?__vl) AS ?_vernacularLang) "
            f"WHERE {{ {proxy_var} dc:language ?__vl }} "
            f"GROUP BY {proxy_var} }}"
        )

    def _lang_resolve_item(
        self,
        prop_uri: str,
        subject_var: str,
        base_name: str,
        extra_langs: list[str] | None = None,
        vernacular_var: str = "?_vernacularLang",
    ) -> tuple[str, dict[str, str]]:
        """Generate parallel language columns for an item-level property.

        Returns (sparql_fragment, var_map) where var_map maps logical names
        to SPARQL variable names:
            "resolved", "en", "native", "native_lang", and any extras.
        """
        langs = extra_langs if extra_langs is not None else self.extra_languages
        parts: list[str] = []
        coalesce_vars: list[str] = []
        var_map: dict[str, str] = {}

        # 1. English
        en_var = f"?_{base_name}_en"
        parts.append(f'OPTIONAL {{ {subject_var} {prop_uri} {en_var} . FILTER(LANG({en_var}) = "en") }}')
        coalesce_vars.append(en_var)
        var_map["en"] = en_var

        # 2. Vernacular (item's own language)
        native_var = f"?_{base_name}_native"
        native_lang_var = f"?_{base_name}_native_lang"
        parts.append(
            f"OPTIONAL {{ {subject_var} {prop_uri} {native_var} . "
            f"FILTER(LANG({native_var}) = {vernacular_var}) }}"
        )
        parts.append(f"BIND(LANG({native_var}) AS {native_lang_var})")
        coalesce_vars.append(native_var)
        var_map["native"] = native_var
        var_map["native_lang"] = native_lang_var

        # 3. Extra languages
        for lang in langs:
            safe = lang.replace("-", "_")
            v = f"?_{base_name}_{safe}"
            parts.append(f'OPTIONAL {{ {subject_var} {prop_uri} {v} . FILTER(LANG({v}) = "{lang}") }}')
            coalesce_vars.append(v)
            var_map[lang] = v

        # 4. Wildcard fallback — SAMPLE subquery to prevent row multiplication
        any_var = f"?_{base_name}_any"
        inner_var = f"?__any_{base_name}"
        parts.append(
            f"OPTIONAL {{ SELECT {subject_var} (SAMPLE({inner_var}) AS {any_var}) "
            f"WHERE {{ {subject_var} {prop_uri} {inner_var} }} "
            f"GROUP BY {subject_var} }}"
        )
        coalesce_vars.append(any_var)

        # Resolved column
        resolved_var = f"?_{base_name}_resolved"
        coalesce = ", ".join(coalesce_vars)
        parts.append(f"BIND(COALESCE({coalesce}) AS {resolved_var})")
        var_map["resolved"] = resolved_var

        return "\n  ".join(parts), var_map

    def _lang_resolve_entity(
        self,
        prop_uri: str,
        subject_var: str,
        output_var: str,
        extra_langs: list[str] | None = None,
    ) -> str:
        """Language resolution for entity labels: en → extras → any.

        No vernacular concept for entities. Returns SPARQL fragment ending
        with a BIND to output_var.
        """
        langs = extra_langs if extra_langs is not None else self.extra_languages
        parts: list[str] = []
        coalesce_vars: list[str] = []
        base = output_var.lstrip("?")

        # English
        en_var = f"?_{base}_en"
        parts.append(f'OPTIONAL {{ {subject_var} {prop_uri} {en_var} . FILTER(LANG({en_var}) = "en") }}')
        coalesce_vars.append(en_var)

        # Extras
        for lang in langs:
            safe = lang.replace("-", "_")
            v = f"?_{base}_{safe}"
            parts.append(f'OPTIONAL {{ {subject_var} {prop_uri} {v} . FILTER(LANG({v}) = "{lang}") }}')
            coalesce_vars.append(v)

        # Wildcard — SAMPLE subquery to prevent row multiplication
        any_var = f"?_{base}_any"
        inner_var = f"?__any_{base}"
        parts.append(
            f"OPTIONAL {{ SELECT {subject_var} (SAMPLE({inner_var}) AS {any_var}) "
            f"WHERE {{ {subject_var} {prop_uri} {inner_var} }} "
            f"GROUP BY {subject_var} }}"
        )
        coalesce_vars.append(any_var)

        parts.append(f"BIND(COALESCE({', '.join(coalesce_vars)}) AS {output_var})")
        return "\n  ".join(parts)

    def _quote(self, value: str) -> str:
        """Escape a string for use inside a SPARQL literal."""
        return value.replace("\\", "\\\\").replace('"', '\\"')

    # -----------------------------------------------------------------------
    # SPARQL query generators (private — accessed via all_queries registry)
    # -----------------------------------------------------------------------

    def _web_resources(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ebucore"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ?url ?mime ?width ?height ?bytes
            WHERE {{
              ?agg edm:aggregatedCHO ?item ;
                   edm:isShownBy ?url .
              OPTIONAL {{ ?url ebucore:hasMimeType ?mime }}
              OPTIONAL {{ ?url ebucore:width ?width }}
              OPTIONAL {{ ?url ebucore:height ?height }}
              OPTIONAL {{ ?url ebucore:fileByteSize ?bytes }}
            }}
            {limit_block}
        """).strip()

    def _agents(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "skos", "rdaGr2", "owl"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
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
            {limit_block}
        """).strip()

    def _places(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "skos", "wgs84_pos", "owl"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
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
            {limit_block}
        """).strip()

    def _concepts(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"skos", "owl"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?concept ?label ?lang ?scheme ?broader ?exactMatch
            WHERE {{
              ?concept a skos:Concept ;
                       skos:prefLabel ?label .
              BIND(LANG(?label) AS ?lang)
              OPTIONAL {{ ?concept skos:inScheme ?scheme }}
              OPTIONAL {{ ?concept skos:broader ?broader }}
              OPTIONAL {{ ?concept skos:exactMatch ?exactMatch }}
            }}
            {limit_block}
        """).strip()

    def _timespans(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "skos", "owl"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
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
            {limit_block}
        """).strip()

    def _items_by_rights_uri(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?rights (COUNT(?item) AS ?count)
            WHERE {{
              ?agg edm:aggregatedCHO ?item ;
                   edm:rights ?rights .
            }}
            GROUP BY ?rights
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def _items_by_reuse_level(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm"})
        reuse_bind = sparql_reuse_level_bind()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?reuse_level (COUNT(?item) AS ?count)
            WHERE {{
              ?agg edm:aggregatedCHO ?item ;
                   edm:rights ?rights .
              {reuse_bind}
            }}
            GROUP BY ?reuse_level
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()


    def _items_core(self, filters: QueryFilters | None = None) -> str:
        """One row per item with single-valued properties.

        Uses subquery materialization: the mandatory joins (proxy ×
        aggregation × europeana aggregation) are computed first in an
        inner SELECT, then OPTIONALs are applied on the already-bound
        ``?agg`` / ``?eAgg`` variables. This prevents QLever from
        running out of query memory when processing 66M items.
        """
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ore", "xsd"})
        eproxy = self._europeana_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        filter_block = self._build_filters(f)
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ?type ?rights ?country ?dataProvider
                   ?isShownAt ?isShownBy ?preview ?landingPage
                   ?datasetName ?completeness
            WHERE {{
              {{
                SELECT ?item ?agg ?eAgg ?type ?rights ?dataProvider ?country
                WHERE {{
                  {eproxy}
                  ?eProxy edm:type ?type .
                  {agg}
                  ?agg edm:rights ?rights ;
                       edm:dataProvider ?dataProvider .
                  {eagg}
                  ?eAgg edm:country ?country .
                  {filter_block}
                }}
              }}
              OPTIONAL {{ ?agg edm:isShownAt ?isShownAt }}
              OPTIONAL {{ ?agg edm:isShownBy ?isShownBy }}
              OPTIONAL {{ ?eAgg edm:completeness ?completeness }}
              OPTIONAL {{ ?eAgg edm:preview ?preview }}
              OPTIONAL {{ ?eAgg edm:landingPage ?landingPage }}
              OPTIONAL {{ ?eAgg edm:datasetName ?datasetName }}
            }}
            {limit_block}
        """).strip()

    def _items_titles(self, filters: QueryFilters | None = None) -> str:
        """All title values with language tags — multi-row per item."""
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore"})
        proxy = self._provider_proxy()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ?title ?lang
            WHERE {{
              {proxy}
              ?proxy dc:title ?title .
              BIND(LANG(?title) AS ?lang)
            }}
            {limit_block}
        """).strip()

    def _items_descriptions(self, filters: QueryFilters | None = None) -> str:
        """All description values with language tags — multi-row per item."""
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore"})
        proxy = self._provider_proxy()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ?description ?lang
            WHERE {{
              {proxy}
              ?proxy dc:description ?description .
              BIND(LANG(?description) AS ?lang)
            }}
            {limit_block}
        """).strip()

    def _items_subjects(self, filters: QueryFilters | None = None) -> str:
        """Subject values per item with IRI flag — multi-row.

        Subjects can be literal strings (``"Painting"``) or concept URIs
        (``http://data.europeana.eu/concept/...``).  The ``is_iri`` flag
        allows the composition step to resolve URIs to human-readable labels.
        """
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore"})
        proxy = self._provider_proxy()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item (STR(?_sv) AS ?subject_value) (isIRI(?_sv) AS ?is_iri)
            WHERE {{
              {proxy}
              ?proxy dc:subject ?_sv .
            }}
            {limit_block}
        """).strip()

    def _items_dates(self, filters: QueryFilters | None = None) -> str:
        """Date values per item — multi-row."""
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore"})
        proxy = self._provider_proxy()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ?date
            WHERE {{
              {proxy}
              ?proxy dc:date ?date .
            }}
            {limit_block}
        """).strip()

    def _items_languages(self, filters: QueryFilters | None = None) -> str:
        """Language codes per item — multi-row."""
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore"})
        proxy = self._provider_proxy()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ?language
            WHERE {{
              {proxy}
              ?proxy dc:language ?language .
            }}
            {limit_block}
        """).strip()

    def _items_years(self, filters: QueryFilters | None = None) -> str:
        """Normalised edm:year from the Europeana proxy — multi-row per item."""
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ore"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ?year
            WHERE {{
              ?eProxy ore:proxyFor ?item .
              ?eProxy edm:europeanaProxy "true" .
              ?eProxy edm:year ?year .
            }}
            {limit_block}
        """).strip()

    def _items_creators(self, filters: QueryFilters | None = None) -> str:
        """Creator URIs and literals per item with IRI flag — multi-row."""
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore"})
        proxy = self._provider_proxy()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item (STR(?_cv) AS ?creator_value) (isIRI(?_cv) AS ?is_iri)
            WHERE {{
              {proxy}
              ?proxy dc:creator ?_cv .
            }}
            {limit_block}
        """).strip()


    def _items_by_type(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ore"})
        eproxy = self._europeana_proxy()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?type (COUNT(?item) AS ?count)
            WHERE {{
              {eproxy}
              ?eProxy edm:type ?type .
            }}
            GROUP BY ?type
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def _items_by_country(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?country (COUNT(?item) AS ?count)
            WHERE {{
              ?eAgg edm:aggregatedCHO ?item .
              ?eAgg a edm:EuropeanaAggregation .
              ?eAgg edm:country ?country .
            }}
            GROUP BY ?country
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def _items_by_type_and_country(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ore"})
        eproxy = self._europeana_proxy()
        eagg = self._europeana_aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?type ?country (COUNT(?item) AS ?count)
            WHERE {{
              {eproxy}
              ?eProxy edm:type ?type .
              {eagg}
              ?eAgg edm:country ?country .
            }}
            GROUP BY ?type ?country
            ORDER BY ?type DESC(?count)
            {limit_block}
        """).strip()

    def _items_by_provider(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "skos"})
        agg = self._aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?dataProvider
                   (SAMPLE(?enName) AS ?providerName_en)
                   (SAMPLE(?anyName) AS ?providerName)
                   (COUNT(?item) AS ?count)
            WHERE {{
              {agg}
              ?agg edm:dataProvider ?dataProvider .
              OPTIONAL {{ ?dataProvider skos:prefLabel ?enName . FILTER(LANG(?enName) = "en") }}
              OPTIONAL {{ ?dataProvider skos:prefLabel ?anyName }}
            }}
            GROUP BY ?dataProvider
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def _items_by_language(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm"})
        eagg = self._europeana_aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?language (COUNT(?item) AS ?count)
            WHERE {{
              {eagg}
              ?eAgg edm:language ?language .
            }}
            GROUP BY ?language
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def _items_by_type_and_language(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ore"})
        eproxy = self._europeana_proxy()
        eagg = self._europeana_aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?type ?language (COUNT(?item) AS ?count)
            WHERE {{
              {eproxy}
              ?eProxy edm:type ?type .
              {eagg}
              ?eAgg edm:language ?language .
            }}
            GROUP BY ?type ?language
            ORDER BY ?type DESC(?count)
            {limit_block}
        """).strip()

    def _mime_type_distribution(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ebucore"})
        agg = self._aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?mime (COUNT(?item) AS ?count)
            WHERE {{
              {agg}
              ?agg edm:isShownBy ?url .
              ?url ebucore:hasMimeType ?mime .
            }}
            GROUP BY ?mime
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def _items_by_year(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ore"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?year (COUNT(?item) AS ?count)
            WHERE {{
              ?eProxy ore:proxyFor ?item .
              ?eProxy edm:europeanaProxy "true" .
              ?eProxy edm:year ?year .
            }}
            GROUP BY ?year
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def _geolocated_places(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "skos", "wgs84_pos"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?place ?name ?lat ?lon
            WHERE {{
              ?place a edm:Place ;
                     wgs84_pos:lat ?lat ;
                     wgs84_pos:long ?lon ;
                     skos:prefLabel ?name .
              FILTER(LANG(?name) = "en")
            }}
            {limit_block}
        """).strip()

    def _texts_by_type(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore"})
        proxy = self._provider_proxy()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?dcType (COUNT(?item) AS ?count)
            WHERE {{
              {proxy}
              ?proxy edm:type "TEXT" .
              ?proxy dc:type ?dcType .
            }}
            GROUP BY ?dcType
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def _iiif_availability(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "skos", "svcs"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?dataProvider
                   (SAMPLE(?enName) AS ?providerName_en)
                   (SAMPLE(?anyName) AS ?providerName)
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
            {limit_block}
        """).strip()

    # -----------------------------------------------------------------------
    # Registry — single source of truth for (name, description, method)
    # -----------------------------------------------------------------------

    _QUERIES: tuple[tuple[str, str, str], ...] = (
        # Pipeline — standalone exports
        ("web_resources",
         "Digital representation URLs with MIME type, dimensions, and file size",
         "_web_resources"),
        ("agents",
         "People and organisations with multilingual labels, birth/death dates, profession, and Wikidata links",
         "_agents"),
        ("places",
         "Locations with multilingual labels, coordinates, and Wikidata links",
         "_places"),
        ("concepts",
         "SKOS concepts with hierarchy, scheme, and cross-scheme matches",
         "_concepts"),
        ("timespans",
         "Time periods with multilingual labels, begin/end dates, and Wikidata links",
         "_timespans"),
        # Pipeline — component exports (building blocks for items_enriched)
        ("items_core",
         "One row per item: type, rights, country, data provider, and single-valued aggregation properties",
         "_items_core"),
        ("items_titles",
         "All title values with language tags (multi-row per item)",
         "_items_titles"),
        ("items_descriptions",
         "All description values with language tags (multi-row per item)",
         "_items_descriptions"),
        ("items_subjects",
         "Subject values per item (multi-row)",
         "_items_subjects"),
        ("items_dates",
         "Date values per item (multi-row)",
         "_items_dates"),
        ("items_languages",
         "Language codes per item (multi-row)",
         "_items_languages"),
        ("items_years",
         "Normalised edm:year values from Europeana proxy (multi-row per item)",
         "_items_years"),
        ("items_creators",
         "Creator URIs and literals per item with IRI flag (multi-row)",
         "_items_creators"),
        # Summary queries
        ("items_by_country",
         "Item counts grouped by country",
         "_items_by_country"),
        ("items_by_language",
         "Item counts grouped by edm:language",
         "_items_by_language"),
        ("items_by_provider",
         "Item counts grouped by data provider",
         "_items_by_provider"),
        ("items_by_type",
         "Item counts grouped by edm:type",
         "_items_by_type"),
        ("items_by_type_and_country",
         "Item counts grouped by edm:type and country",
         "_items_by_type_and_country"),
        ("items_by_type_and_language",
         "Item counts grouped by edm:type and edm:language",
         "_items_by_type_and_language"),
        ("items_by_year",
         "Item counts grouped by edm:year",
         "_items_by_year"),
        ("items_by_rights_uri",
         "Item counts grouped by rights URI",
         "_items_by_rights_uri"),
        ("items_by_reuse_level",
         "Item counts grouped by reuse level (open, restricted, prohibited)",
         "_items_by_reuse_level"),
        ("geolocated_places",
         "Places with coordinates",
         "_geolocated_places"),
        ("iiif_availability",
         "Items with IIIF manifests (svcs:has_service) by provider",
         "_iiif_availability"),
        ("mime_type_distribution",
         "Item counts grouped by MIME type and edm:type",
         "_mime_type_distribution"),
        ("texts_by_type",
         "dc:type value distribution for TEXT items (books, newspapers, etc.)",
         "_texts_by_type"),
    )

    def all_queries(self, filters: QueryFilters | None = None) -> dict[str, QuerySpec]:
        """Return all registered queries as a flat dict."""
        from .compose import items_enriched_steps

        specs: dict[str, QuerySpec] = {}
        for name, description, method_name in self._QUERIES:
            specs[name] = QuerySpec(
                name=name,
                description=description,
                sparql=getattr(self, method_name)(filters),
            )

        specs["items_enriched"] = QuerySpec(
            name="items_enriched",
            description=(
                "Fully denormalized one-row-per-item export with parallel English and "
                "vernacular title/description columns, resolved entity labels, and "
                "multi-valued properties — composed via DuckDB from component tables"
            ),
            compose_steps=items_enriched_steps(),
            depends_on=[
                "items_core", "items_titles", "items_descriptions",
                "items_subjects", "items_dates", "items_languages",
                "items_years", "items_creators", "agents", "concepts",
            ],
        )

        return specs
