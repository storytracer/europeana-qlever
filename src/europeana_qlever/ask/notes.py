"""Structured EDM domain knowledge for NL query agents.

Single source of truth for Europeana Data Model semantics.  Each note has
language-agnostic EDM knowledge plus optional DuckDB and SPARQL patterns.

- :func:`render_duckdb_notes` produces the system-prompt notes for
  :class:`~europeana_qlever.ask.parquet.AskParquet`.
- :func:`render_sparql_notes` produces the note list for GRASP's
  ``europeana-notes.json``.
- :func:`export_grasp_notes` writes the JSON file directly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EdmNote:
    """A single domain knowledge note."""

    topic: str
    edm_knowledge: str
    duckdb_pattern: str = ""
    sparql_pattern: str = ""


# ---------------------------------------------------------------------------
# The note registry — shared EDM knowledge
# ---------------------------------------------------------------------------

EDM_NOTES: list[EdmNote] = [
    # -- Struct access (DuckDB only) --
    EdmNote(
        topic="struct_list_access",
        edm_knowledge="Multi-valued properties are stored as nested lists with struct fields.",
        duckdb_pattern="""\
STRUCT LIST ACCESS PATTERNS:
- Unnest struct lists: SELECT t.value, t.lang FROM items_resolved, UNNEST(titles) AS t(value, lang)
- Filter within a list: list_filter(titles, x -> x.lang = 'en')
- Check list containment: list_has_any(list_transform(dc_types, x -> LOWER(x.label)), ['preserved specimen'])
- Count list elements: LEN(subjects)
- Check non-empty: LEN(titles) > 0 (NOT: titles IS NOT NULL, which only checks for NULL not empty)
- Count distinct after unnest: SELECT COUNT(DISTINCT item) FROM items_resolved, UNNEST(...)""",
    ),

    # -- Reuse levels --
    EdmNote(
        topic="reuse_levels",
        edm_knowledge="""\
Rights are classified into open/restricted/closed/unknown reuse levels.
Open: CC0, PDM, CC-BY, CC-BY-SA (~580 URI variants).
Restricted: CC licenses with -nc or -nd, plus NoC-NC, NoC-OKLR, InC-EDU.
Prohibited: everything else (InC, CNE, InC-OW-EU, NKC, UND).""",
        duckdb_pattern="""\
reuse_level column = 'open' / 'restricted' / 'closed' / 'unknown'.
"Openly-reusable" means reuse_level = 'open'.
Specific rights URIs in the rights column:
  PDM: http://creativecommons.org/publicdomain/mark/1.0/
  CC0: http://creativecommons.org/publicdomain/zero/1.0/
  All public domain: rights LIKE 'http://creativecommons.org/publicdomain/%'""",
        sparql_pattern="""\
For open-reuse filtering, ALWAYS use the open-items materialized view — never STRSTARTS/STR patterns.
PREFIX view: <https://qlever.cs.uni-freiburg.de/materializedView/>
SERVICE view:open-items { [ view:column-item ?item ; view:column-type ?type ] }
PREFIX view: must ALWAYS be declared. Omit FILTER for all types.""",
    ),

    # -- Column types (DuckDB only) --
    EdmNote(
        topic="column_types",
        edm_knowledge="Multi-valued properties use typed list columns.",
        duckdb_pattern="""\
MULTI-VALUED COLUMN TYPES:
- LIST<STRUCT<value VARCHAR, lang VARCHAR>>: titles, descriptions (text with language tags)
- LIST<STRUCT<label VARCHAR, uri VARCHAR>>: subjects, dc_types, formats (entity labels with URIs)
- LIST<STRUCT<name VARCHAR, uri VARCHAR>>: creators, contributors, publishers (agent names with URIs)
- LIST<VARCHAR>: dates, languages, identifiers, dc_rights
- LIST<VARCHAR>: years (string representations of integer years)""",
    ),

    # -- Type vs dc:type --
    EdmNote(
        topic="type_vs_dc_type",
        edm_knowledge="""\
edm:type is a controlled enum with exactly 5 uppercase values: IMAGE, TEXT, SOUND, VIDEO, 3D.
dc:type is free-text from providers with millions of values like 'photograph', 'Preserved Specimen'.
Never confuse them.""",
        duckdb_pattern="type column (VARCHAR) is edm:type. dc_types (LIST<STRUCT<label,uri>>) is dc:type.",
        sparql_pattern="""\
edm:type is on the Europeana proxy with exactly 5 uppercase values.
dc:type is on the provider proxy with free-text values.
?eProxy edm:europeanaProxy "true" . ?eProxy edm:type ?type .""",
    ),

    # -- Content availability --
    EdmNote(
        topic="content_availability",
        edm_knowledge="""\
is_shown_by = direct content URL (downloadable digital object).
is_shown_at = landing page at provider website.
has_iiif = whether any web resource has a IIIF image service.
width/height = pixel dimensions (NULL if not reported by provider).""",
        duckdb_pattern='An item "has content" if is_shown_by IS NOT NULL.',
        sparql_pattern="""\
edm:isShownBy and edm:isShownAt are on ore:Aggregation.
?agg edm:aggregatedCHO ?item . ?agg edm:isShownBy ?url .""",
    ),

    # -- Country and institution --
    EdmNote(
        topic="country_institution",
        edm_knowledge="""\
country = providing country (string like 'Netherlands', 'France').
institution = data provider organisation URI.
aggregator = aggregator organisation URI.
edm:country is ONLY on edm:EuropeanaAggregation, not on ore:Aggregation.""",
        duckdb_pattern="""\
Join with institutions table for human-readable names:
SELECT COALESCE(n.name, i.institution) AS provider, COUNT(*) AS cnt
FROM items_resolved i LEFT JOIN institutions n ON i.institution = n.org
GROUP BY 1 ORDER BY cnt DESC""",
        sparql_pattern="""\
?eAgg edm:aggregatedCHO ?item . ?eAgg a edm:EuropeanaAggregation . ?eAgg edm:country ?country .
edm:dataProvider is a literal on ore:Aggregation: ?agg edm:dataProvider ?dp .""",
    ),

    # -- Specimen exclusion --
    EdmNote(
        topic="specimen_exclusion",
        edm_knowledge="""\
Natural history specimens dominate open images (~10.8M items).
Exclude via dc:type labels containing 'Preserved Specimen', 'biological specimen', or 'herbarium'.""",
        duckdb_pattern="""\
NOT list_has_any(list_transform(dc_types, x -> LOWER(x.label)), \
['preserved specimen', 'biological specimen', 'herbarium'])""",
        sparql_pattern="""\
FILTER NOT EXISTS {
  ?proxy dc:type ?dctype .
  FILTER(CONTAINS(LCASE(STR(?dctype)), "preserved specimen") || ...)
}""",
    ),

    # -- Performance --
    EdmNote(
        topic="performance",
        edm_knowledge="The dataset has ~66M items / ~5B triples. Efficiency matters.",
        duckdb_pattern="""\
DuckDB handles 66M rows efficiently in columnar mode.
Avoid SELECT * — always specify columns. Use LIMIT during exploration.
UNNEST on large lists can produce billions of rows — add WHERE clauses early.
For counting items with a property, prefer LEN(column) > 0 over UNNEST + COUNT(DISTINCT).""",
        sparql_pattern="""\
For open-reuse filtering, ALWAYS use the open-items materialized view.
Never use nested BIND/IF to classify the full 66M-item dataset.
Run separate COUNT queries per category. Always use LIMIT for exploratory queries.
Always COUNT(DISTINCT ?item) — items have multiple proxies and entity links.""",
    ),

    # -- Language tags --
    EdmNote(
        topic="language_tags",
        edm_knowledge="""\
Titles and descriptions carry language tags (e.g. 'en', 'de', 'fr').
Empty string '' means no language tag was provided.
The languages column (dc:language) is different from title/description language tags.""",
        duckdb_pattern="""\
titles and descriptions have a lang field in their struct.
Empty string '' means untagged. NULL and '' are different.""",
        sparql_pattern="""\
LANG(?title) returns the tag. FILTER(LANG(?title) = "en") restricts to English.
STR(?title) strips the tag for string comparison.
FILTER(LANG(?label) = "en" || LANG(?label) = "") gets English or untagged.""",
    ),

    # -- Century bucketing (DuckDB only) --
    EdmNote(
        topic="century_bucketing",
        edm_knowledge="edm:year values are strings representing integer years.",
        duckdb_pattern="""\
years contains string values (e.g. '1850', '2001').
Cast to integer for arithmetic: CAST(y AS INTEGER).
Bucket: CASE WHEN CAST(y AS INTEGER) < 1500 THEN 'before 1500' WHEN ... END""",
        sparql_pattern="""\
edm:year is a string on the Europeana proxy. Cast to integer:
FILTER(xsd:integer(?year) >= 1800 && xsd:integer(?year) <= 1900)""",
    ),

    # -- Data limitations --
    EdmNote(
        topic="data_limitations",
        edm_knowledge="""\
items_resolved has ONE row per item with at most ONE is_shown_by URL. It does NOT
contain per-item web resource counts or edm:hasView links. The web_resources table
also only has the edm:isShownBy resource, not additional edm:hasView resources.
Proxy-level detail is flattened: titles/descriptions come from the provider proxy;
years come from the Europeana proxy. There is no fulltext or OCR content.""",
        duckdb_pattern="""\
If a question asks about data not available in these tables (e.g. edm:hasView counts),
say so clearly rather than giving a misleading answer based on different columns.""",
        sparql_pattern="""\
edm:hasView links are available in the RDF graph but not in the Parquet exports.
The full proxy structure (provider vs Europeana) is available in SPARQL.""",
    ),

    # -- EDM core model (SPARQL only) --
    EdmNote(
        topic="edm_core_model",
        edm_knowledge="""\
Metadata is NOT on edm:ProvidedCHO directly. Querying ?item dc:title ?t returns nothing.
Metadata flows through ore:Proxy (descriptive) and ore:Aggregation (rights, URLs).
Each item has TWO proxies and at least two aggregations.""",
        sparql_pattern="""\
Never query dc:title, dc:creator, or any descriptive property directly on the item URI.
Always use a proxy pattern: ?proxy ore:proxyFor ?item .""",
    ),

    # -- Provider proxy (SPARQL only) --
    EdmNote(
        topic="provider_proxy",
        edm_knowledge="""\
The provider proxy carries original descriptive metadata as literals:
dc:title, dc:creator, dc:subject, dc:date, dc:description, dc:type, dc:language,
dc:format, dc:identifier, dc:publisher, dc:contributor, dc:rights.""",
        sparql_pattern="""\
?proxy ore:proxyFor ?item .
FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" . }
?proxy dc:title ?title .
All are multivalued, most are language-tagged literals.""",
    ),

    # -- Europeana proxy (SPARQL only) --
    EdmNote(
        topic="europeana_proxy",
        edm_knowledge="""\
The Europeana proxy carries normalised/enriched fields:
edm:type (enum), edm:year (string). Also carries enriched entity URIs for
dc:creator, dc:contributor, dc:subject, dcterms:spatial.""",
        sparql_pattern="""\
?eProxy ore:proxyFor ?item .
?eProxy edm:europeanaProxy "true" .
Entity URIs from search_entity are on the EUROPEANA PROXY (not provider proxy).""",
    ),

    # -- Aggregation (SPARQL only) --
    EdmNote(
        topic="aggregation",
        edm_knowledge="""\
ore:Aggregation carries rights, data supply chain, and digital object URLs:
edm:rights (URI), edm:dataProvider, edm:provider, edm:isShownBy, edm:isShownAt,
edm:hasView (multivalued), edm:object.""",
        sparql_pattern="""\
?agg edm:aggregatedCHO ?item .
CRITICAL: edm:rights is ONLY reliable on ore:Aggregation.
edm:EuropeanaAggregation has a copy but it is incomplete.""",
    ),

    # -- Contextual entities --
    EdmNote(
        topic="contextual_entities",
        edm_knowledge="""\
Entity tables: agents_core, concepts_core, places_core, timespans_core.
One row per prefLabel variant. Use for entity-level analysis
(e.g. "how many concepts have labels in 10+ languages").
Entity links tables have same_as, alt_label, exact_match, broader, narrower, etc.""",
        duckdb_pattern="""\
Join subjects.uri with concept column in concepts_core for entity-level analysis.
Join creators.uri/contributors.uri with agent column in agents_core.""",
        sparql_pattern="""\
All entities have skos:prefLabel (language-tagged) and owl:sameAs (URI).
edm:Agent: rdaGr2:dateOfBirth, rdaGr2:dateOfDeath, rdaGr2:gender.
edm:Place: wgs84_pos:lat, wgs84_pos:long. skos:Concept: skos:broader, skos:narrower.""",
    ),

    # -- Materialized views (SPARQL only) --
    EdmNote(
        topic="materialized_views",
        edm_knowledge="""\
The open-items QLever materialized view precomputes all items with open reuse rights
joined with edm:type. Columns: item, type, rights, dummy.""",
        sparql_pattern="""\
PREFIX view: <https://qlever.cs.uni-freiburg.de/materializedView/>
SERVICE view:open-items { [ view:column-item ?item ; view:column-type ?type ] }
FILTER(?type = "IMAGE")
Join with proxy/aggregation patterns as usual for descriptive/technical metadata.
For country: ?eAgg edm:aggregatedCHO ?item . ?eAgg a edm:EuropeanaAggregation . ?eAgg edm:country ?country .""",
    ),

    # -- URI vs literal (SPARQL only) --
    EdmNote(
        topic="uri_vs_literal",
        edm_knowledge="""\
dc:creator, dc:subject, dcterms:spatial can be a literal (provider proxy) or a URI
pointing to a contextual entity (Europeana proxy). Use isIRI(?val) to distinguish.""",
        sparql_pattern="""\
On the Europeana proxy, these are entity URIs; on the provider proxy, free-text strings.
edm:dataProvider and edm:country are literal strings, not URIs.
edm:rights is always a URI. dc:rights is a free-text literal.""",
    ),

    # -- Common prefixes (SPARQL only) --
    EdmNote(
        topic="sparql_prefixes",
        edm_knowledge="Standard RDF prefix declarations for Europeana queries.",
        sparql_pattern="""\
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX edm: <http://www.europeana.eu/schemas/edm/>
PREFIX ore: <http://www.openarchives.org/ore/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX rdaGr2: <http://rdvocab.info/ElementsGr2/>
PREFIX ebucore: <https://www.ebu.ch/metadata/ontologies/ebucore/ebucore#>
PREFIX wgs84_pos: <http://www.w3.org/2003/01/geo/wgs84_pos#>
PREFIX view: <https://qlever.cs.uni-freiburg.de/materializedView/>""",
    ),
]


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_duckdb_notes() -> str:
    """Render domain notes for the DuckDB/Parquet ask agent system prompt."""
    sections: list[str] = []
    idx = 1
    for note in EDM_NOTES:
        if not note.duckdb_pattern and not note.edm_knowledge:
            continue
        # Include notes that have DuckDB patterns or are general knowledge
        # Skip SPARQL-only notes (no DuckDB pattern and topic is SPARQL-specific)
        if not note.duckdb_pattern and note.sparql_pattern and not note.edm_knowledge.strip():
            continue

        parts: list[str] = []
        if note.edm_knowledge:
            parts.append(note.edm_knowledge)
        if note.duckdb_pattern:
            parts.append(note.duckdb_pattern)

        body = "\n".join(parts)
        sections.append(f"{idx}. {note.topic.upper().replace('_', ' ')}:\n   {body}")
        idx += 1

    return "## Domain knowledge for querying Europeana Parquet exports\n\n" + "\n\n".join(sections)


def render_sparql_notes() -> list[str]:
    """Render domain notes as a list of strings for GRASP's notes JSON."""
    notes: list[str] = []
    for note in EDM_NOTES:
        if not note.sparql_pattern:
            continue
        parts: list[str] = []
        if note.edm_knowledge:
            parts.append(note.edm_knowledge)
        parts.append(note.sparql_pattern)
        notes.append("\n".join(parts))
    return notes


def export_grasp_notes(path: Path) -> None:
    """Write ``europeana-notes.json`` for the GRASP server."""
    notes = render_sparql_notes()
    path.write_text(json.dumps(notes, indent=2, ensure_ascii=False) + "\n")
