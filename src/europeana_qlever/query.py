"""Dynamic SPARQL query generator for Europeana EDM metadata exports.

Generates parameterised SPARQL queries for exporting Europeana data as
Parquet files. Replaces the former static .sparql files with a programmatic
``QueryBuilder`` that supports filters, language priority, and reusable
SPARQL fragments.
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
    # AI dataset queries
    "items_enriched": (
        "Fully denormalized one-row-per-item export with parallel English and "
        "vernacular title/description columns, resolved entity labels, and "
        "GROUP_CONCAT for multi-valued properties"
    ),
    "text_corpus": (
        "NLP training corpus with parallel English and vernacular title/description "
        "columns, filtered to items that have a title"
    ),
    "image_metadata": "Computer vision training: IMAGE items with technical metadata from web resources",
    "entity_links": "owl:sameAs cross-reference table for contextual entities",
    "temporal_coverage": "Items with normalised edm:year from the Europeana proxy",
    # Analytics queries
    "open_reusable_inventory": "Rights category × type × country cross-tab with item counts",
    "media_availability": "Items with/without edm:isShownBy by type and rights category",
    "mime_type_distribution": "MIME type counts by edm:type and rights category",
    "image_resolution_profile": "Width, height, bytes, and colour depth for open IMAGE items",
    "language_distribution": "Language × type × rights category distribution with counts",
    "language_coverage_by_country": "Fraction of items with dc:language per country",
    "multilingual_metadata": "Items with titles in more than one language",
    "temporal_distribution": "Item counts by edm:year × type × rights category",
    "date_metadata_quality": "Completeness of edm:year vs dc:date vs missing",
    "provider_landscape": "Provider-level stats: item count, average completeness, by type and rights",
    "entity_linked_providers": "Data providers whose items have Wikidata-linked creators",
    "entity_graph_summary": "Counts of agents, places, concepts, and timespans with Wikidata links",
    "vocabulary_sources": "Concept distribution across skos:inScheme vocabularies",
    "geolocated_places": "Places with coordinates and linked item counts",
    "text_items_by_country_language": "TEXT items with open rights by country and language",
    "text_genre_distribution": "dc:type value distribution for TEXT items (books, newspapers, etc.)",
    "iiif_availability": "Items with IIIF manifests (svcs:has_service) by provider",
    "image_subject_domains": "Subject and dc:type distribution for open IMAGE items",
    "audiovisual_inventory": "SOUND and VIDEO items with technical metadata",
    "text_richness": "Items with both title and description (minimum text training viability)",
    "provenance_completeness": "Coverage of dataProvider, provider, and datasetName per country",
    "entity_sameAs_sources": "owl:sameAs link distribution by authority (Wikidata, VIAF, GND, etc.)",
    "three_d_inventory": "All 3D items with metadata",
    "quality_tier_distribution": "Completeness score × type × country × rights category",
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
            f'  FILTER NOT EXISTS {{ {proxy} edm:europeanaProxy "true" }}'
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
        """Bind the item's vernacular language from dc:language."""
        return f"OPTIONAL {{ {proxy_var} dc:language ?_vernacularLang }}"

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

        # 4. Wildcard fallback
        any_var = f"?_{base_name}_any"
        parts.append(f"OPTIONAL {{ {subject_var} {prop_uri} {any_var} }}")
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

        # Wildcard
        any_var = f"?_{base}_any"
        parts.append(f"OPTIONAL {{ {subject_var} {prop_uri} {any_var} }}")
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
    # AI dataset queries
    # -----------------------------------------------------------------------

    def items_enriched(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({
            "dc", "dcterms", "edm", "ore", "skos", "owl", "xsd",
        })
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        sep = self.separator
        filter_block = self._build_filters(f, year_var="?_year")
        limit_block = self._limit_offset(f)
        extras = self._extra_langs(f)

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

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item
              {title_cols}
              {desc_cols}
              (GROUP_CONCAT(DISTINCT ?_creator; SEPARATOR="{sep}") AS ?creators)
              (GROUP_CONCAT(DISTINCT ?_creatorURI; SEPARATOR="{sep}") AS ?creator_uris)
              (GROUP_CONCAT(DISTINCT ?_subject; SEPARATOR="{sep}") AS ?subjects)
              (GROUP_CONCAT(DISTINCT ?_date; SEPARATOR="{sep}") AS ?dates)
              (GROUP_CONCAT(DISTINCT ?_year; SEPARATOR="{sep}") AS ?years)
              (SAMPLE(?_type) AS ?type)
              (GROUP_CONCAT(DISTINCT ?_language; SEPARATOR="{sep}") AS ?languages)
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
              {proxy}
              {vernacular}
              ?proxy edm:type ?_type .
              {title_fragment}
              {desc_fragment}
              OPTIONAL {{
                ?proxy dc:creator ?_creatorRef . FILTER(isIRI(?_creatorRef))
                {creator_label_indented}
                BIND(STR(?_creatorRef) AS ?_creatorURI)
              }}
              OPTIONAL {{ ?proxy dc:creator ?_creatorLit . FILTER(isLiteral(?_creatorLit)) }}
              BIND(COALESCE(?_creatorLabel, ?_creatorLit, STR(?_creatorRef)) AS ?_creator)
              OPTIONAL {{ ?proxy dc:subject ?_subject }}
              OPTIONAL {{ ?proxy dc:date ?_date }}
              OPTIONAL {{ ?proxy dc:language ?_language }}
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
              {filter_block}
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

    def open_reusable_inventory(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ore", "xsd"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        rights_bind = self._rights_category_bind()
        filter_block = self._build_filters(f)
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?rights_category ?type ?country (COUNT(?item) AS ?count)
            WHERE {{
              {proxy}
              ?proxy edm:type ?type .
              {agg}
              ?agg edm:rights ?rights .
              {eagg}
              ?eAgg edm:country ?country .
              {rights_bind}
              {filter_block}
            }}
            GROUP BY ?rights_category ?type ?country
            ORDER BY ?rights_category ?type ?country
            {limit_block}
        """).strip()

    def media_availability(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ore", "xsd"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        rights_bind = self._rights_category_bind()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?type ?rights_category
                   (COUNT(?item) AS ?total)
                   (SUM(IF(BOUND(?media), 1, 0)) AS ?with_media)
            WHERE {{
              {proxy}
              ?proxy edm:type ?type .
              {agg}
              ?agg edm:rights ?rights .
              OPTIONAL {{ ?agg edm:isShownBy ?media }}
              {rights_bind}
            }}
            GROUP BY ?type ?rights_category
            ORDER BY ?type ?rights_category
            {limit_block}
        """).strip()

    def mime_type_distribution(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ebucore", "ore", "xsd"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        rights_bind = self._rights_category_bind()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?type ?rights_category ?mime (COUNT(?item) AS ?count)
            WHERE {{
              {proxy}
              ?proxy edm:type ?type .
              {agg}
              ?agg edm:rights ?rights ;
                   edm:isShownBy ?url .
              ?url ebucore:hasMimeType ?mime .
              {rights_bind}
            }}
            GROUP BY ?type ?rights_category ?mime
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def image_resolution_profile(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ebucore", "ore"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ?url ?width ?height ?bytes
            WHERE {{
              {proxy}
              ?proxy edm:type ?type .
              FILTER(?type = "IMAGE")
              {agg}
              ?agg edm:rights ?rights ;
                   edm:isShownBy ?url .
              FILTER(STRSTARTS(STR(?rights), "http://creativecommons.org/publicdomain/") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by/4") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by/3") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by/2") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by/1") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by-sa/"))
              OPTIONAL {{ ?url ebucore:width ?width }}
              OPTIONAL {{ ?url ebucore:height ?height }}
              OPTIONAL {{ ?url ebucore:fileByteSize ?bytes }}
            }}
            {limit_block}
        """).strip()

    def language_distribution(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore", "xsd"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        rights_bind = self._rights_category_bind()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?language ?type ?rights_category (COUNT(?item) AS ?count)
            WHERE {{
              {proxy}
              ?proxy edm:type ?type ;
                     dc:language ?language .
              {agg}
              ?agg edm:rights ?rights .
              {rights_bind}
            }}
            GROUP BY ?language ?type ?rights_category
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def language_coverage_by_country(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?country
                   (COUNT(?item) AS ?total)
                   (SUM(IF(BOUND(?lang), 1, 0)) AS ?with_language)
            WHERE {{
              {proxy}
              OPTIONAL {{ ?proxy dc:language ?lang }}
              {agg}
              {eagg}
              ?eAgg edm:country ?country .
            }}
            GROUP BY ?country
            ORDER BY ?country
            {limit_block}
        """).strip()

    def multilingual_metadata(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore", "xsd"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        filter_block = self._build_filters(f)
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ?country ?type (COUNT(DISTINCT LANG(?title)) AS ?title_languages)
            WHERE {{
              {proxy}
              ?proxy dc:title ?title ;
                     edm:type ?type .
              {agg}
              {eagg}
              ?eAgg edm:country ?country .
              {filter_block}
            }}
            GROUP BY ?item ?country ?type
            HAVING (COUNT(DISTINCT LANG(?title)) > 1)
            ORDER BY DESC(?title_languages)
            {limit_block}
        """).strip()

    def temporal_distribution(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ore", "xsd"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        rights_bind = self._rights_category_bind()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?year ?type ?rights_category (COUNT(?item) AS ?count)
            WHERE {{
              {proxy}
              ?proxy edm:type ?type .
              ?eProxy ore:proxyFor ?item .
              ?eProxy edm:europeanaProxy "true" .
              ?eProxy edm:year ?year .
              {agg}
              ?agg edm:rights ?rights .
              {rights_bind}
            }}
            GROUP BY ?year ?type ?rights_category
            ORDER BY ?year ?type
            {limit_block}
        """).strip()

    def date_metadata_quality(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?country ?type
                   (COUNT(?item) AS ?total)
                   (SUM(IF(BOUND(?dcDate), 1, 0)) AS ?has_dc_date)
                   (SUM(IF(BOUND(?year), 1, 0)) AS ?has_edm_year)
            WHERE {{
              {proxy}
              ?proxy edm:type ?type .
              OPTIONAL {{ ?proxy dc:date ?dcDate }}
              OPTIONAL {{
                ?eProxy ore:proxyFor ?item .
                ?eProxy edm:europeanaProxy "true" .
                ?eProxy edm:year ?year .
              }}
              {agg}
              {eagg}
              ?eAgg edm:country ?country .
            }}
            GROUP BY ?country ?type
            ORDER BY ?country ?type
            {limit_block}
        """).strip()

    def provider_landscape(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ore", "xsd"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        rights_bind = self._rights_category_bind()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?dataProvider ?type ?rights_category ?country
                   (COUNT(?item) AS ?count)
                   (AVG(xsd:integer(?completeness)) AS ?avg_completeness)
            WHERE {{
              {proxy}
              ?proxy edm:type ?type .
              {agg}
              ?agg edm:rights ?rights ;
                   edm:dataProvider ?dataProvider .
              {eagg}
              ?eAgg edm:country ?country ;
                    edm:completeness ?completeness .
              {rights_bind}
            }}
            GROUP BY ?dataProvider ?type ?rights_category ?country
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def entity_linked_providers(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore", "owl", "skos"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?dataProvider (COUNT(DISTINCT ?item) AS ?items)
                   (COUNT(DISTINCT ?wd) AS ?wikidata_creators)
            WHERE {{
              {proxy}
              ?proxy dc:creator ?creator . FILTER(isIRI(?creator))
              ?creator owl:sameAs ?wd .
              FILTER(STRSTARTS(STR(?wd), "http://www.wikidata.org/entity/"))
              {agg}
              ?agg edm:dataProvider ?dataProvider .
            }}
            GROUP BY ?dataProvider
            ORDER BY DESC(?items)
            {limit_block}
        """).strip()

    def entity_graph_summary(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "skos", "owl"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?entity_type
                   (COUNT(DISTINCT ?entity) AS ?total)
                   (COUNT(DISTINCT ?wd_entity) AS ?with_wikidata)
            WHERE {{
              VALUES (?cls ?entity_type) {{
                (edm:Agent "agent")
                (edm:Place "place")
                (skos:Concept "concept")
                (edm:TimeSpan "timespan")
              }}
              ?entity a ?cls .
              OPTIONAL {{
                ?entity owl:sameAs ?wd .
                FILTER(STRSTARTS(STR(?wd), "http://www.wikidata.org/entity/"))
                BIND(?entity AS ?wd_entity)
              }}
            }}
            GROUP BY ?entity_type
            {limit_block}
        """).strip()

    def vocabulary_sources(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"skos"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?scheme (COUNT(DISTINCT ?concept) AS ?count)
            WHERE {{
              ?concept a skos:Concept ;
                       skos:inScheme ?scheme .
            }}
            GROUP BY ?scheme
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def geolocated_places(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "skos", "wgs84_pos", "owl"})
        limit_block = self._limit_offset(f)
        extras = self._extra_langs(f)

        name_resolve = self._lang_resolve_entity(
            "skos:prefLabel", "?place", "?name", extra_langs=extras,
        )

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?place ?name ?lat ?lon ?wikidata
            WHERE {{
              ?place a edm:Place ;
                     wgs84_pos:lat ?lat ;
                     wgs84_pos:long ?lon .
              {name_resolve}
              OPTIONAL {{
                ?place owl:sameAs ?wikidata .
                FILTER(STRSTARTS(STR(?wikidata), "http://www.wikidata.org/entity/"))
              }}
            }}
            {limit_block}
        """).strip()

    def text_items_by_country_language(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore", "xsd"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?country ?language (COUNT(?item) AS ?count)
            WHERE {{
              {proxy}
              ?proxy edm:type ?type ;
                     dc:language ?language .
              FILTER(?type = "TEXT")
              {agg}
              ?agg edm:rights ?rights .
              FILTER(STRSTARTS(STR(?rights), "http://creativecommons.org/publicdomain/") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by/4") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by/3") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by/2") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by/1") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by-sa/"))
              {eagg}
              ?eAgg edm:country ?country .
            }}
            GROUP BY ?country ?language
            ORDER BY ?country DESC(?count)
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
              ?proxy edm:type ?type .
              FILTER(?type = "TEXT")
              ?proxy dc:type ?dcType .
            }}
            GROUP BY ?dcType
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def iiif_availability(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "svcs"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?dataProvider (COUNT(DISTINCT ?item) AS ?iiif_items)
            WHERE {{
              ?agg edm:aggregatedCHO ?item ;
                   edm:dataProvider ?dataProvider ;
                   edm:isShownBy ?url .
              ?url svcs:has_service ?service .
            }}
            GROUP BY ?dataProvider
            ORDER BY DESC(?iiif_items)
            {limit_block}
        """).strip()

    def image_subject_domains(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?subject (COUNT(?item) AS ?count)
            WHERE {{
              {proxy}
              ?proxy edm:type ?type .
              FILTER(?type = "IMAGE")
              ?proxy dc:subject ?subject .
              {agg}
              ?agg edm:rights ?rights .
              FILTER(STRSTARTS(STR(?rights), "http://creativecommons.org/publicdomain/") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by/4") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by/3") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by/2") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by/1") ||
                     STRSTARTS(STR(?rights), "http://creativecommons.org/licenses/by-sa/"))
            }}
            GROUP BY ?subject
            ORDER BY DESC(?count)
            {limit_block}
        """).strip()

    def audiovisual_inventory(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ebucore", "ore"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ?title ?type ?rights ?country ?dataProvider
                   ?url ?mime ?bytes
            WHERE {{
              {proxy}
              ?proxy dc:title ?title ;
                     edm:type ?type .
              FILTER(?type = "SOUND" || ?type = "VIDEO")
              {agg}
              ?agg edm:rights ?rights ;
                   edm:dataProvider ?dataProvider .
              OPTIONAL {{
                ?agg edm:isShownBy ?url .
                OPTIONAL {{ ?url ebucore:hasMimeType ?mime }}
                OPTIONAL {{ ?url ebucore:fileByteSize ?bytes }}
              }}
              {eagg}
              ?eAgg edm:country ?country .
            }}
            {limit_block}
        """).strip()

    def text_richness(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ore"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?country ?type
                   (COUNT(?item) AS ?total)
                   (SUM(IF(BOUND(?desc), 1, 0)) AS ?with_description)
            WHERE {{
              {proxy}
              ?proxy dc:title ?title ;
                     edm:type ?type .
              OPTIONAL {{ ?proxy dc:description ?desc }}
              {agg}
              {eagg}
              ?eAgg edm:country ?country .
            }}
            GROUP BY ?country ?type
            ORDER BY ?country ?type
            {limit_block}
        """).strip()

    def provenance_completeness(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm"})
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?country
                   (COUNT(?item) AS ?total)
                   (SUM(IF(BOUND(?dataProvider), 1, 0)) AS ?has_data_provider)
                   (SUM(IF(BOUND(?provider), 1, 0)) AS ?has_provider)
                   (SUM(IF(BOUND(?datasetName), 1, 0)) AS ?has_dataset_name)
            WHERE {{
              {agg}
              OPTIONAL {{ ?agg edm:dataProvider ?dataProvider }}
              OPTIONAL {{ ?agg edm:provider ?provider }}
              {eagg}
              ?eAgg edm:country ?country .
              OPTIONAL {{ ?eAgg edm:datasetName ?datasetName }}
            }}
            GROUP BY ?country
            ORDER BY ?country
            {limit_block}
        """).strip()

    def entity_sameAs_sources(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "skos", "owl"})
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?entity_type ?authority (COUNT(DISTINCT ?entity) AS ?count)
            WHERE {{
              VALUES (?cls ?entity_type) {{
                (edm:Agent "agent")
                (edm:Place "place")
                (skos:Concept "concept")
                (edm:TimeSpan "timespan")
              }}
              ?entity a ?cls ;
                      owl:sameAs ?sameAs .
              BIND(
                IF(STRSTARTS(STR(?sameAs), "http://www.wikidata.org/"), "wikidata",
                IF(STRSTARTS(STR(?sameAs), "http://viaf.org/"), "viaf",
                IF(STRSTARTS(STR(?sameAs), "http://d-nb.info/"), "gnd",
                IF(STRSTARTS(STR(?sameAs), "http://dbpedia.org/"), "dbpedia",
                IF(STRSTARTS(STR(?sameAs), "http://id.loc.gov/"), "loc",
                IF(STRSTARTS(STR(?sameAs), "http://data.bnf.fr/"), "bnf",
                   "other"))))))
                AS ?authority
              )
            }}
            GROUP BY ?entity_type ?authority
            ORDER BY ?entity_type DESC(?count)
            {limit_block}
        """).strip()

    def three_d_inventory(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"dc", "edm", "ebucore", "ore"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        filter_block = self._build_filters(f)
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?item ?title ?rights ?country ?dataProvider
                   ?url ?mime
            WHERE {{
              {proxy}
              ?proxy dc:title ?title ;
                     edm:type ?type .
              FILTER(?type = "3D")
              {agg}
              ?agg edm:rights ?rights ;
                   edm:dataProvider ?dataProvider .
              OPTIONAL {{
                ?agg edm:isShownBy ?url .
                OPTIONAL {{ ?url ebucore:hasMimeType ?mime }}
              }}
              {eagg}
              ?eAgg edm:country ?country .
              {filter_block}
            }}
            {limit_block}
        """).strip()

    def quality_tier_distribution(self, filters: QueryFilters | None = None) -> str:
        f = filters or QueryFilters()
        prefixes = self._prefix_block({"edm", "ore", "xsd"})
        proxy = self._provider_proxy()
        agg = self._aggregation()
        eagg = self._europeana_aggregation()
        rights_bind = self._rights_category_bind()
        limit_block = self._limit_offset(f)

        return textwrap.dedent(f"""\
            {prefixes}
            SELECT ?completeness ?type ?country ?rights_category
                   (COUNT(?item) AS ?count)
            WHERE {{
              {proxy}
              ?proxy edm:type ?type .
              {agg}
              ?agg edm:rights ?rights .
              {eagg}
              ?eAgg edm:country ?country ;
                    edm:completeness ?completeness .
              {rights_bind}
            }}
            GROUP BY ?completeness ?type ?country ?rights_category
            ORDER BY ?completeness ?type ?country
            {limit_block}
        """).strip()

    # -----------------------------------------------------------------------
    # Registry methods
    # -----------------------------------------------------------------------

    def all_base_queries(self, filters: QueryFilters | None = None) -> dict[str, str]:
        return {
            "core_metadata": self.core_metadata(filters),
            "web_resources": self.web_resources(filters),
            "rights_providers": self.rights_providers(filters),
            "agents": self.agents(filters),
            "places": self.places(filters),
            "concepts": self.concepts(filters),
            "timespans": self.timespans(filters),
        }

    def all_ai_queries(self, filters: QueryFilters | None = None) -> dict[str, str]:
        return {
            "items_enriched": self.items_enriched(filters),
            "text_corpus": self.text_corpus(filters),
            "image_metadata": self.image_metadata(filters),
            "entity_links": self.entity_links(filters=filters),
            "temporal_coverage": self.temporal_coverage(filters),
        }

    def all_analytics_queries(self, filters: QueryFilters | None = None) -> dict[str, str]:
        return {
            "open_reusable_inventory": self.open_reusable_inventory(filters),
            "media_availability": self.media_availability(filters),
            "mime_type_distribution": self.mime_type_distribution(filters),
            "image_resolution_profile": self.image_resolution_profile(filters),
            "language_distribution": self.language_distribution(filters),
            "language_coverage_by_country": self.language_coverage_by_country(filters),
            "multilingual_metadata": self.multilingual_metadata(filters),
            "temporal_distribution": self.temporal_distribution(filters),
            "date_metadata_quality": self.date_metadata_quality(filters),
            "provider_landscape": self.provider_landscape(filters),
            "entity_linked_providers": self.entity_linked_providers(filters),
            "entity_graph_summary": self.entity_graph_summary(filters),
            "vocabulary_sources": self.vocabulary_sources(filters),
            "geolocated_places": self.geolocated_places(filters),
            "text_items_by_country_language": self.text_items_by_country_language(filters),
            "text_genre_distribution": self.text_genre_distribution(filters),
            "iiif_availability": self.iiif_availability(filters),
            "image_subject_domains": self.image_subject_domains(filters),
            "audiovisual_inventory": self.audiovisual_inventory(filters),
            "text_richness": self.text_richness(filters),
            "provenance_completeness": self.provenance_completeness(filters),
            "entity_sameAs_sources": self.entity_sameAs_sources(filters),
            "three_d_inventory": self.three_d_inventory(filters),
            "quality_tier_distribution": self.quality_tier_distribution(filters),
        }

    def all_queries(self, filters: QueryFilters | None = None) -> dict[str, str]:
        result: dict[str, str] = {}
        result.update(self.all_base_queries(filters))
        result.update(self.all_ai_queries(filters))
        result.update(self.all_analytics_queries(filters))
        return result

    def describe(self, query_name: str) -> str:
        return _DESCRIPTIONS.get(query_name, f"No description available for '{query_name}'")
