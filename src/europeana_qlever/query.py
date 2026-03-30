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

from .constants import (
    EDM_PREFIXES,
    OPEN_RIGHTS_URIS,
    PERMISSION_RIGHTS_URIS,
    RESTRICTED_RIGHTS_URIS,
    SEPARATOR,
)


# ---------------------------------------------------------------------------
# QuerySpec — unified descriptor for simple and composite exports
# ---------------------------------------------------------------------------

@dataclass
class QuerySpec:
    """Specification for a single export.

    Simple SPARQL exports have *sparql* set and *compose_sql* ``None``.
    Composite exports (e.g. ``items_enriched``) have *compose_sql* set,
    *sparql* ``None``, and *depends_on* listing the required base tables.
    """

    name: str
    sparql: str | None = None
    compose_sql: str | None = None
    depends_on: list[str] = field(default_factory=list)
    description: str = ""

    @property
    def is_composite(self) -> bool:
        return self.compose_sql is not None


# ---------------------------------------------------------------------------
# Filter dataclass
# ---------------------------------------------------------------------------

@dataclass
class QueryFilters:
    """Parameters for filtering SPARQL query results."""

    countries: list[str] | None = None
    types: list[str] | None = None
    rights: list[str] | None = None
    rights_category: str | None = None
    providers: list[str] | None = None
    min_completeness: int | None = None
    year_from: int | None = None
    year_to: int | None = None
    languages: list[str] | None = None      # Additional languages beyond English + vernacular
    dataset_names: list[str] | None = None
    limit: int | None = None
    offset: int | None = None


# ---------------------------------------------------------------------------
# Query descriptions
# ---------------------------------------------------------------------------

_DESCRIPTIONS: dict[str, str] = {
    # Base queries
    "core_metadata": "Core item metadata: title, creator, date, type, subject, language, rights, country, data provider",
    "web_resources": "Digital representation URLs with MIME type, dimensions, and file size",
    "rights_providers": "Item-level rights statements with provider, country, and completeness score",
    "agents": "People and organisations with multilingual labels, birth/death dates, profession, and Wikidata links",
    "places": "Locations with multilingual labels, coordinates, and Wikidata links",
    "concepts": "SKOS concepts with hierarchy, scheme, and cross-scheme matches",
    "timespans": "Time periods with multilingual labels, begin/end dates, and Wikidata links",
    # Component queries (building blocks for composite exports)
    "items_core": "One row per item: type, rights, country, data provider, and single-valued aggregation properties",
    "items_titles": "All title values with language tags (multi-row per item)",
    "items_descriptions": "All description values with language tags (multi-row per item)",
    "items_subjects": "Subject values per item (multi-row)",
    "items_dates": "Date values per item (multi-row)",
    "items_languages": "Language codes per item (multi-row)",
    "items_years": "Normalised edm:year values from Europeana proxy (multi-row per item)",
    "items_creators": "Creator URIs and literals per item with IRI flag (multi-row)",
    # AI dataset queries
    "items_enriched": (
        "Fully denormalized one-row-per-item export with parallel English and "
        "vernacular title/description columns, resolved entity labels, and "
        "multi-valued properties — composed via DuckDB from component tables"
    ),
    "text_corpus": (
        "NLP training corpus with parallel English and vernacular title/description "
        "columns, filtered to items that have a title"
    ),
    "image_metadata": "Computer vision training: IMAGE items with technical metadata from web resources",
    "entity_links": "owl:sameAs cross-reference table for contextual entities",
    "temporal_coverage": "Items with normalised edm:year from the Europeana proxy",
    # Analytics queries — designed for fast interactive execution in QLever UI
    "items_by_type": "Item counts grouped by edm:type",
    "items_by_country": "Item counts grouped by country",
    "items_by_type_and_country": "Item counts grouped by edm:type and country",
    "items_by_provider": "Item counts grouped by data provider",
    "items_by_language": "Item counts grouped by edm:language",
    "mime_type_distribution": "Item counts grouped by MIME type and edm:type",
    "items_by_year": "Item counts grouped by edm:year",
    "geolocated_places": "Places with coordinates",
    "text_genre_distribution": "dc:type value distribution for TEXT items (books, newspapers, etc.)",
    "iiif_availability": "Items with IIIF manifests (svcs:has_service) by provider",
}


# ---------------------------------------------------------------------------
# QueryBuilder
# ---------------------------------------------------------------------------

class QueryBuilder:
    """Generates SPARQL queries for Europeana EDM metadata exports."""

    def __init__(
        self,
        languages: list[str] | None = None,
        separator: str = SEPARATOR,
    ) -> None:
        """
        Parameters
        ----------
        languages
            Additional languages to query beyond English and the item's
            vernacular. For example, ``["fr", "de"]`` produces extra columns
            ``title_fr``, ``title_de`` and adds them to the COALESCE chain.
        separator
            Delimiter for GROUP_CONCAT multi-valued columns.
        """
        self.extra_languages = languages or []
        self.separator = separator

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

    def _rights_category_bind(
        self, rights_var: str = "?rights", out_var: str = "?rights_category"
    ) -> str:
        return textwrap.dedent(f"""\
            BIND(
              IF(STRSTARTS(STR({rights_var}), "http://creativecommons.org/publicdomain/") ||
                 STRSTARTS(STR({rights_var}), "http://creativecommons.org/licenses/by/4") ||
                 STRSTARTS(STR({rights_var}), "http://creativecommons.org/licenses/by/3") ||
                 STRSTARTS(STR({rights_var}), "http://creativecommons.org/licenses/by/2") ||
                 STRSTARTS(STR({rights_var}), "http://creativecommons.org/licenses/by/1") ||
                 STRSTARTS(STR({rights_var}), "http://creativecommons.org/licenses/by-sa/"),
                 "open",
              IF(CONTAINS(STR({rights_var}), "-nc") || CONTAINS(STR({rights_var}), "-nd") ||
                 STR({rights_var}) = "http://rightsstatements.org/vocab/NoC-NC/1.0/" ||
                 STR({rights_var}) = "http://rightsstatements.org/vocab/NoC-OKLR/1.0/" ||
                 STR({rights_var}) = "http://rightsstatements.org/vocab/InC-EDU/1.0/",
                 "restricted",
                 "permission"))
              AS {out_var}
            )""")

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
        elif f.rights_category:
            uris = self._rights_category_uris(f.rights_category)
            vals = ", ".join(f"<{u}>" for u in uris)
            clauses.append(f"FILTER({rights_var} IN ({vals}))")

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

    def _core_subquery(
        self,
        filters: QueryFilters | None = None,
        *,
        extra_select: str = "",
        extra_body: str = "",
    ) -> str:
        """Inner subquery: identify items with single-valued properties.

        Materialises a compact result (one row per item) with mandatory
        and single-valued optional properties.  The outer query can then
        add language resolution and multi-valued properties on the
        already-bound ``?item`` / ``?proxy`` without re-joining the full
        graph.

        *extra_select* and *extra_body* allow callers to inject additional
        SELECT variables or WHERE patterns.
        """
        f = filters or QueryFilters()
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        filter_block = self._build_filters(
            f,
            type_var="?_type",
            rights_var="?_rights",
            provider_var="?_dataProvider",
            country_var="?_country",
            completeness_var="?_completeness",
            year_var="?_year",
        )

        return textwrap.dedent(f"""\
            {{
              SELECT ?item ?proxy ?_type ?_rights ?_dataProvider ?_country
                     ?_completeness ?_isShownAt ?_isShownBy ?_preview
                     ?_landingPage ?_datasetName ?_year{extra_select}
              WHERE {{
                {proxy}
                ?proxy edm:type ?_type .
                {agg}
                ?agg edm:rights ?_rights ;
                     edm:dataProvider ?_dataProvider .
                OPTIONAL {{ ?agg edm:isShownAt ?_isShownAt }}
                OPTIONAL {{ ?agg edm:isShownBy ?_isShownBy }}
                {eagg}
                ?eAgg edm:country ?_country .
                OPTIONAL {{ ?eAgg edm:completeness ?_completeness }}
                OPTIONAL {{ ?eAgg edm:preview ?_preview }}
                OPTIONAL {{ ?eAgg edm:landingPage ?_landingPage }}
                OPTIONAL {{ ?eAgg edm:datasetName ?_datasetName }}
                OPTIONAL {{
                  ?eProxy ore:proxyFor ?item .
                  ?eProxy edm:europeanaProxy "true" .
                  ?eProxy edm:year ?_year .
                }}
                {extra_body}
                {filter_block}
              }}
            }}""")

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

    # -- Entity resolution ---------------------------------------------------

    def _resolve_entity(
        self,
        prop_uri: str,
        subject_var: str,
        label_var: str,
        uri_var: str,
        wd_var: str,
        entity_class: str,
        extra_langs: list[str] | None = None,
    ) -> str:
        """Generate IRI/literal branching + label resolution for entity refs.

        Uses _lang_resolve_entity for the skos:prefLabel lookup.
        """
        ref_var = f"{label_var}Ref"
        lbl_var = f"{label_var}Lbl"
        lit_var = f"{label_var}Lit"

        # Build entity label resolution inside the OPTIONAL
        label_resolve = self._lang_resolve_entity(
            "skos:prefLabel", ref_var, lbl_var, extra_langs=extra_langs,
        )
        # Indent label_resolve for nesting inside OPTIONAL
        label_lines = label_resolve.replace("\n  ", "\n    ")

        return textwrap.dedent(f"""\
            OPTIONAL {{ {subject_var} {prop_uri} {ref_var} . FILTER(isIRI({ref_var}))
              {label_lines}
              OPTIONAL {{ {ref_var} owl:sameAs {wd_var} . FILTER(STRSTARTS(STR({wd_var}), "http://www.wikidata.org/entity/")) }}
              BIND({ref_var} AS {uri_var})
            }}
            OPTIONAL {{ {subject_var} {prop_uri} {lit_var} . FILTER(isLiteral({lit_var})) }}
            BIND(COALESCE({lbl_var}, {lit_var}, STR({ref_var})) AS {label_var})""")

    def _quote(self, value: str) -> str:
        """Escape a string for use inside a SPARQL literal."""
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _rights_category_uris(self, category: str) -> list[str]:
        """Map a category name to its URI list."""
        mapping = {
            "open": OPEN_RIGHTS_URIS,
            "restricted": RESTRICTED_RIGHTS_URIS,
            "permission": PERMISSION_RIGHTS_URIS,
        }
        return mapping.get(category, [])

    # -----------------------------------------------------------------------
    # Base queries (replace the 6 static .sparql files + 1 new)
    # -----------------------------------------------------------------------

    def core_metadata(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "dcterms", "edm", "ore", "xsd"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        filter_block = self._build_filters(f)
        limit_block = self._limit_offset(f)
        extras = self._extra_langs(f)

        vernacular = self._bind_vernacular()
        title_fragment, title_vars = self._lang_resolve_item(
            "dc:title", "?proxy", "title", extra_langs=extras,
        )

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ({title_vars["resolved"]} AS ?title) ?creator ?date ?type ?subject ?language
                   ?rights ?country ?dataProvider
            WHERE {{
              {proxy}
              {vernacular}
              ?proxy edm:type ?type .
              {title_fragment}
              OPTIONAL {{ ?proxy dc:creator ?creator }}
              OPTIONAL {{ ?proxy dc:date ?date }}
              OPTIONAL {{ ?proxy dc:subject ?subject }}
              OPTIONAL {{ ?proxy dc:language ?language }}
              {agg}
              ?agg edm:rights ?rights ;
                   edm:dataProvider ?dataProvider .
              {eagg}
              ?eAgg edm:country ?country .
              {filter_block}
            }}
            {limit_block}
        """).strip()

    def web_resources(self, filters: QueryFilters | None = None) -> str:
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

    def rights_providers(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "xsd"})
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        filter_block = self._build_filters(f)
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ?rights ?dataProvider ?provider ?country ?completeness
            WHERE {{
              {agg}
              ?agg edm:rights ?rights ;
                   edm:dataProvider ?dataProvider ;
                   edm:provider ?provider .
              {eagg}
              ?eAgg edm:country ?country ;
                    edm:completeness ?completeness .
              {filter_block}
            }}
            {limit_block}
        """).strip()

    def agents(self, filters: QueryFilters | None = None) -> str:
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

    def places(self, filters: QueryFilters | None = None) -> str:
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

    def concepts(self, filters: QueryFilters | None = None) -> str:
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

    def timespans(self, filters: QueryFilters | None = None) -> str:
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

    # -----------------------------------------------------------------------
    # Component queries — building blocks for composite exports
    #
    # Each is a flat, simple SPARQL scan with no GROUP BY and minimal
    # OPTIONALs. QLever executes these in minutes over 66M items.
    # DuckDB then joins the resulting Parquet files to produce the
    # final denormalized exports.
    # -----------------------------------------------------------------------

    def items_core(self, filters: QueryFilters | None = None) -> str:
        """One row per item with single-valued properties.

        Uses subquery materialization: the mandatory joins (proxy ×
        aggregation × europeana aggregation) are computed first in an
        inner SELECT, then OPTIONALs are applied on the already-bound
        ``?agg`` / ``?eAgg`` variables. This prevents QLever from
        running out of query memory when processing 66M items.
        """
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ore", "xsd"})
        proxy = self._provider_proxy()
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
                  {proxy}
                  ?proxy edm:type ?type .
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

    def items_titles(self, filters: QueryFilters | None = None) -> str:
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

    def items_descriptions(self, filters: QueryFilters | None = None) -> str:
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

    def items_subjects(self, filters: QueryFilters | None = None) -> str:
        """Subject values per item — multi-row."""
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore"})
        proxy = self._provider_proxy()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ?subject
            WHERE {{
              {proxy}
              ?proxy dc:subject ?subject .
            }}
            {limit_block}
        """).strip()

    def items_dates(self, filters: QueryFilters | None = None) -> str:
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

    def items_languages(self, filters: QueryFilters | None = None) -> str:
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

    def items_years(self, filters: QueryFilters | None = None) -> str:
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

    def items_creators(self, filters: QueryFilters | None = None) -> str:
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

    # -----------------------------------------------------------------------
    # AI dataset queries
    # -----------------------------------------------------------------------

    def _pre_aggregate(
        self,
        subject_var: str,
        prop_uri: str,
        out_var: str,
        separator: str,
    ) -> str:
        """Pre-aggregate a multi-valued property via GROUP_CONCAT subquery.

        Returns an OPTIONAL subquery that produces one pre-concatenated
        row per subject, preventing row multiplication in the outer query.
        """
        inner = f"?__pa_{out_var.lstrip('?')}"
        return (
            f"OPTIONAL {{ SELECT {subject_var} "
            f'(GROUP_CONCAT(DISTINCT {inner}; SEPARATOR="{separator}") AS {out_var}) '
            f"WHERE {{ {subject_var} {prop_uri} {inner} }} "
            f"GROUP BY {subject_var} }}"
        )

    def items_enriched(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({
            "dc", "dcterms", "edm", "ore", "skos", "owl", "xsd",
        })
        sep = self.separator
        limit_block = self._limit_offset(f)
        extras = self._extra_langs(f)

        # Phase 1: core subquery materialises items with single-valued props
        core = self._core_subquery(f)

        # Phase 2: language resolution on already-bound ?proxy
        vernacular = self._bind_vernacular()
        title_fragment, title_vars = self._lang_resolve_item(
            "dc:title", "?proxy", "title", extra_langs=extras,
        )
        desc_fragment, desc_vars = self._lang_resolve_item(
            "dc:description", "?proxy", "desc", extra_langs=extras,
        )

        # Build SELECT columns for title
        title_select = [
            f"(SAMPLE({title_vars['resolved']}) AS ?title)",
            f"(SAMPLE({title_vars['en']}) AS ?title_en)",
            f"(SAMPLE({title_vars['native']}) AS ?title_native)",
            f"(SAMPLE({title_vars['native_lang']}) AS ?title_native_lang)",
        ]
        for lang in extras:
            safe = lang.replace("-", "_")
            title_select.append(f"(SAMPLE({title_vars[lang]}) AS ?title_{safe})")

        # Build SELECT columns for description
        desc_select = [
            f"(SAMPLE({desc_vars['resolved']}) AS ?description)",
            f"(SAMPLE({desc_vars['en']}) AS ?description_en)",
            f"(SAMPLE({desc_vars['native']}) AS ?description_native)",
            f"(SAMPLE({desc_vars['native_lang']}) AS ?description_native_lang)",
        ]
        for lang in extras:
            safe = lang.replace("-", "_")
            desc_select.append(f"(SAMPLE({desc_vars[lang]}) AS ?description_{safe})")

        title_cols = "\n  ".join(title_select)
        desc_cols = "\n  ".join(desc_select)

        # Creator entity resolution with language chain
        creator_label_resolve = self._lang_resolve_entity(
            "skos:prefLabel", "?_creatorRef", "?_creatorLabel", extra_langs=extras,
        )
        creator_label_indented = creator_label_resolve.replace("\n  ", "\n    ")

        # Pre-aggregate multi-valued properties in subqueries to prevent
        # row multiplication in the outer GROUP BY.
        subjects_agg = self._pre_aggregate("?proxy", "dc:subject", "?_subjects", sep)
        dates_agg = self._pre_aggregate("?proxy", "dc:date", "?_dates", sep)
        languages_agg = self._pre_aggregate("?proxy", "dc:language", "?_languages", sep)
        years_agg = (
            "OPTIONAL { SELECT ?item "
            f'(GROUP_CONCAT(DISTINCT ?__pa_year; SEPARATOR="{sep}") AS ?_years) '
            "WHERE { ?__eP ore:proxyFor ?item . "
            '?__eP edm:europeanaProxy "true" . '
            "?__eP edm:year ?__pa_year . } "
            "GROUP BY ?item }"
        )

        # Creator pre-aggregation: resolve labels inside the subquery,
        # then GROUP_CONCAT the results.
        creators_agg = textwrap.dedent(f"""\
            OPTIONAL {{ SELECT ?proxy
              (GROUP_CONCAT(DISTINCT ?__cr_label; SEPARATOR="{sep}") AS ?_creators)
              (GROUP_CONCAT(DISTINCT ?__cr_uri; SEPARATOR="{sep}") AS ?_creator_uris)
            WHERE {{
              {{
                ?proxy dc:creator ?__cr_ref . FILTER(isIRI(?__cr_ref))
                {creator_label_indented}
                BIND(STR(?__cr_ref) AS ?__cr_uri)
                BIND(COALESCE(?_creatorLabel, STR(?__cr_ref)) AS ?__cr_label)
              }} UNION {{
                ?proxy dc:creator ?__cr_lit . FILTER(isLiteral(?__cr_lit))
                BIND(STR(?__cr_lit) AS ?__cr_label)
              }}
            }} GROUP BY ?proxy }}""")

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item
              {title_cols}
              {desc_cols}
              (SAMPLE(?_creators) AS ?creators)
              (SAMPLE(?_creator_uris) AS ?creator_uris)
              (SAMPLE(?_subjects) AS ?subjects)
              (SAMPLE(?_dates) AS ?dates)
              (SAMPLE(?_years) AS ?years)
              (SAMPLE(?_type) AS ?type)
              (SAMPLE(?_languages) AS ?languages)
              (SAMPLE(?_country) AS ?country)
              (SAMPLE(?_dataProvider) AS ?data_provider)
              (SAMPLE(?_rights) AS ?rights)
              (SAMPLE(?_completeness) AS ?completeness)
              (SAMPLE(?_isShownAt) AS ?is_shown_at)
              (SAMPLE(?_isShownBy) AS ?is_shown_by)
              (SAMPLE(?_preview) AS ?preview)
              (SAMPLE(?_landingPage) AS ?landing_page)
              (SAMPLE(?_datasetName) AS ?dataset_name)
            WHERE {{
              {core}
              {vernacular}
              {title_fragment}
              {desc_fragment}
              {creators_agg}
              {subjects_agg}
              {dates_agg}
              {languages_agg}
              {years_agg}
            }}
            GROUP BY ?item
            {limit_block}
        """).strip()

    def text_corpus(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore", "xsd"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        filter_block = self._build_filters(f)
        limit_block = self._limit_offset(f)
        extras = self._extra_langs(f)

        vernacular = self._bind_vernacular()
        title_fragment, title_vars = self._lang_resolve_item(
            "dc:title", "?proxy", "title", extra_langs=extras,
        )
        desc_fragment, desc_vars = self._lang_resolve_item(
            "dc:description", "?proxy", "desc", extra_langs=extras,
        )

        # Build extra title columns
        extra_title_cols = ""
        for lang in extras:
            safe = lang.replace("-", "_")
            extra_title_cols += f"\n       {title_vars[lang]} AS ?title_{safe}"

        # Build extra desc columns
        extra_desc_cols = ""
        for lang in extras:
            safe = lang.replace("-", "_")
            extra_desc_cols += f"\n       {desc_vars[lang]} AS ?description_{safe}"

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item
                   ({title_vars["resolved"]} AS ?title)
                   ({title_vars["en"]} AS ?title_en)
                   ({title_vars["native"]} AS ?title_native)
                   ({title_vars["native_lang"]} AS ?title_native_lang){extra_title_cols}
                   ({desc_vars["resolved"]} AS ?description)
                   ({desc_vars["en"]} AS ?description_en)
                   ({desc_vars["native"]} AS ?description_native)
                   ({desc_vars["native_lang"]} AS ?description_native_lang){extra_desc_cols}
                   ?language ?type ?rights ?country ?dataProvider
            WHERE {{
              {proxy}
              {vernacular}
              ?proxy edm:type ?type .
              {title_fragment}
              FILTER(BOUND({title_vars["resolved"]}))
              {desc_fragment}
              OPTIONAL {{ ?proxy dc:language ?language }}
              {agg}
              ?agg edm:rights ?rights ;
                   edm:dataProvider ?dataProvider .
              {eagg}
              ?eAgg edm:country ?country .
              {filter_block}
            }}
            {limit_block}
        """).strip()

    def image_metadata(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ebucore", "ore", "xsd"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        filter_block = self._build_filters(f)
        limit_block = self._limit_offset(f)
        extras = self._extra_langs(f)

        vernacular = self._bind_vernacular()
        title_fragment, title_vars = self._lang_resolve_item(
            "dc:title", "?proxy", "title", extra_langs=extras,
        )

        # Build extra title columns for SELECT
        extra_title_cols = ""
        for lang in extras:
            safe = lang.replace("-", "_")
            extra_title_cols += f"\n       {title_vars[lang]} AS ?title_{safe}"

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item
                   ({title_vars["resolved"]} AS ?title)
                   ({title_vars["en"]} AS ?title_en)
                   ({title_vars["native"]} AS ?title_native)
                   ({title_vars["native_lang"]} AS ?title_native_lang){extra_title_cols}
                   ?rights ?country ?dataProvider
                   ?url ?mime ?width ?height ?bytes
            WHERE {{
              {proxy}
              {vernacular}
              ?proxy edm:type ?type .
              FILTER(?type = "IMAGE")
              {title_fragment}
              {agg}
              ?agg edm:rights ?rights ;
                   edm:dataProvider ?dataProvider ;
                   edm:isShownBy ?url .
              OPTIONAL {{ ?url ebucore:hasMimeType ?mime }}
              OPTIONAL {{ ?url ebucore:width ?width }}
              OPTIONAL {{ ?url ebucore:height ?height }}
              OPTIONAL {{ ?url ebucore:fileByteSize ?bytes }}
              {eagg}
              ?eAgg edm:country ?country .
              {filter_block}
            }}
            {limit_block}
        """).strip()

    def entity_links(
        self, entity_type: str = "agent", filters: QueryFilters | None = None
    ) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "skos", "owl"})
        limit_block = self._limit_offset(f)
        extras = self._extra_langs(f)

        type_map = {
            "agent": "edm:Agent",
            "place": "edm:Place",
            "concept": "skos:Concept",
            "timespan": "edm:TimeSpan",
        }
        rdf_type = type_map.get(entity_type, "edm:Agent")

        label_resolve = self._lang_resolve_entity(
            "skos:prefLabel", "?entity", "?label", extra_langs=extras,
        )

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?entity ?label ?sameAs
            WHERE {{
              ?entity a {rdf_type} ;
                      owl:sameAs ?sameAs .
              {label_resolve}
            }}
            {limit_block}
        """).strip()

    def temporal_coverage(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore", "xsd"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        filter_block = self._build_filters(f, year_var="?year")
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ?year ?type ?rights ?country ?dataProvider
            WHERE {{
              {proxy}
              ?proxy edm:type ?type .
              ?eProxy ore:proxyFor ?item .
              ?eProxy edm:europeanaProxy "true" .
              ?eProxy edm:year ?year .
              {agg}
              ?agg edm:rights ?rights ;
                   edm:dataProvider ?dataProvider .
              {eagg}
              ?eAgg edm:country ?country .
              {filter_block}
            }}
            {limit_block}
        """).strip()

    # -----------------------------------------------------------------------
    # Analytics queries
    # -----------------------------------------------------------------------

    def items_by_type(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ore"})
        proxy = self._provider_proxy()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?type (COUNT(?item) AS ?count)
            WHERE {{
              {proxy}
              ?proxy edm:type ?type .
            }}
            GROUP BY ?type
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def items_by_country(self, filters: QueryFilters | None = None) -> str:
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

    def items_by_type_and_country(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ore"})
        proxy = self._provider_proxy()
        eagg = self._europeana_aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?type ?country (COUNT(?item) AS ?count)
            WHERE {{
              {proxy}
              ?proxy edm:type ?type .
              {eagg}
              ?eAgg edm:country ?country .
            }}
            GROUP BY ?type ?country
            ORDER BY ?type DESC(?count)
            {limit_block}
        """).strip()

    def items_by_provider(self, filters: QueryFilters | None = None) -> str:
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

    def items_by_language(self, filters: QueryFilters | None = None) -> str:
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

    def mime_type_distribution(self, filters: QueryFilters | None = None) -> str:
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

    def items_by_year(self, filters: QueryFilters | None = None) -> str:
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

    def geolocated_places(self, filters: QueryFilters | None = None) -> str:
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

    def text_genre_distribution(self, filters: QueryFilters | None = None) -> str:
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

    def iiif_availability(self, filters: QueryFilters | None = None) -> str:
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
    # Registry methods
    #
    # Return ``dict[str, QuerySpec]`` for unified handling of simple
    # SPARQL exports and composite DuckDB exports.
    # -----------------------------------------------------------------------

    def _spec(self, name: str, sparql: str) -> QuerySpec:
        """Wrap a simple SPARQL query as a QuerySpec."""
        return QuerySpec(
            name=name,
            sparql=sparql,
            description=_DESCRIPTIONS.get(name, ""),
        )

    def all_base_queries(self, filters: QueryFilters | None = None) -> dict[str, QuerySpec]:
        return {
            n: self._spec(n, m(filters))
            for n, m in [
                ("core_metadata", self.core_metadata),
                ("web_resources", self.web_resources),
                ("rights_providers", self.rights_providers),
                ("agents", self.agents),
                ("places", self.places),
                ("concepts", self.concepts),
                ("timespans", self.timespans),
            ]
        }

    def all_component_queries(self, filters: QueryFilters | None = None) -> dict[str, QuerySpec]:
        """Component queries: building blocks for composite exports."""
        return {
            n: self._spec(n, m(filters))
            for n, m in [
                ("items_core", self.items_core),
                ("items_titles", self.items_titles),
                ("items_descriptions", self.items_descriptions),
                ("items_subjects", self.items_subjects),
                ("items_dates", self.items_dates),
                ("items_languages", self.items_languages),
                ("items_years", self.items_years),
                ("items_creators", self.items_creators),
            ]
        }

    def all_ai_queries(self, filters: QueryFilters | None = None) -> dict[str, QuerySpec]:
        from .compose import items_enriched_sql

        component_names = list(self.all_component_queries(filters))
        # agents is needed for creator label resolution
        depends = component_names + ["agents"]

        specs: dict[str, QuerySpec] = {
            "items_enriched": QuerySpec(
                name="items_enriched",
                compose_sql=items_enriched_sql(
                    separator=self.separator,
                    extra_languages=self.extra_languages,
                ),
                depends_on=depends,
                description=_DESCRIPTIONS.get("items_enriched", ""),
            ),
        }
        for n, m in [
            ("text_corpus", self.text_corpus),
            ("image_metadata", self.image_metadata),
            ("entity_links", lambda f: self.entity_links(filters=f)),
            ("temporal_coverage", self.temporal_coverage),
        ]:
            specs[n] = self._spec(n, m(filters))
        return specs

    def all_analytics_queries(self, filters: QueryFilters | None = None) -> dict[str, QuerySpec]:
        return {
            n: self._spec(n, m(filters))
            for n, m in [
                ("items_by_type", self.items_by_type),
                ("items_by_country", self.items_by_country),
                ("items_by_type_and_country", self.items_by_type_and_country),
                ("items_by_provider", self.items_by_provider),
                ("items_by_language", self.items_by_language),
                ("mime_type_distribution", self.mime_type_distribution),
                ("items_by_year", self.items_by_year),
                ("geolocated_places", self.geolocated_places),
                ("text_genre_distribution", self.text_genre_distribution),
                ("iiif_availability", self.iiif_availability),
            ]
        }

    def all_queries(self, filters: QueryFilters | None = None) -> dict[str, QuerySpec]:
        result: dict[str, QuerySpec] = {}
        result.update(self.all_base_queries(filters))
        result.update(self.all_ai_queries(filters))
        result.update(self.all_analytics_queries(filters))
        return result

    def describe(self, query_name: str) -> str:
        return _DESCRIPTIONS.get(query_name, f"No description available for '{query_name}'")
