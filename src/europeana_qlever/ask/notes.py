"""Structured EDM domain knowledge for NL query agents.

Single source of truth for Europeana Data Model semantics.  Each note
has language-agnostic EDM knowledge plus optional DuckDB and SPARQL
patterns.

- :func:`render_duckdb_notes` produces the system-prompt notes for
  :class:`~europeana_qlever.ask.parquet.AskParquet`.
- :func:`render_sparql_notes` produces the note list for GRASP's
  ``europeana-notes.json``.
- :func:`export_grasp_notes` writes the JSON file directly.

All DuckDB column references target the new table architecture:

- ``merged_items``       — one row per CHO (denormalized)
- ``group_items``        — one row per CHO, scalar columns only (fast GROUP BY)
- ``values_*`` / ``links_*`` — raw tables preserving EDM class boundaries
- ``map_rights`` / ``map_sameAs`` / ``map_cho_entities`` — lookup tables

Column prefixes: ``k_`` (key), ``v_`` (raw EDM property, directly from
the RDF), ``x_`` (extracted / computed / resolved).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from europeana_qlever import schema_loader


@dataclass(frozen=True)
class EdmNote:
    """A single domain knowledge note."""

    topic: str
    edm_knowledge: str
    duckdb_pattern: str = ""
    sparql_pattern: str = ""


# ---------------------------------------------------------------------------
# Schema-derived notes
# ---------------------------------------------------------------------------


def _sparql_prefixes_note() -> EdmNote:
    pfx = schema_loader.prefixes()
    lines = [f"PREFIX {k}: <{v}>" for k, v in sorted(pfx.items())]
    lines.append("PREFIX view: <https://qlever.cs.uni-freiburg.de/materializedView/>")
    return EdmNote(
        topic="sparql_prefixes",
        edm_knowledge="Standard RDF prefix declarations for Europeana queries.",
        sparql_pattern="\n".join(lines),
    )


# ---------------------------------------------------------------------------
# The note registry
# ---------------------------------------------------------------------------


EDM_NOTES: list[EdmNote] = [
    # -- Table architecture --
    EdmNote(
        topic="table_architecture",
        edm_knowledge="""\
The export has three tiers of tables:
  merged_items   — one row per CHO. Joins proxies, aggregations, primary
                   web resource. Has resolved entity labels and list/struct
                   columns. Best for detailed per-item questions.
  group_items    — one row per CHO, but only scalar categorical/boolean/
                   integer columns. Use for fast GROUP BY analytics
                   (counts by country × type × reuse level, etc.).
  values_* / links_* — raw EDM tables. values_* have scalar columns;
                   links_* are long-format (k_iri, x_property, x_value,
                   x_value_is_iri, x_value_lang).
Map tables (map_rights, map_sameAs, map_cho_entities) are lookups.""",
        duckdb_pattern="""\
CHOOSING A TABLE:
- Counts / distributions across merged_items fields → group_items
  (no UNNEST, no struct access, scans are 30-100x faster)
- Per-item titles/subjects/creators → merged_items
- Rights family/label lookup → JOIN merged_items.v_edm_rights = map_rights.k_iri
- All items referencing a specific Agent/Place/Concept IRI →
  map_cho_entities (avoid UNNEST on x_dc_subject for this)
- Entity deep-dive (prefLabels, sameAs, broader/narrower) → values_* / links_*""",
    ),

    # -- Column-prefix convention --
    EdmNote(
        topic="column_prefixes",
        edm_knowledge="""\
Column names carry a prefix that signals their role:
  k_  key / foreign key (e.g. k_iri, k_iri_cho)
  v_  scalar EDM property, directly from the RDF (e.g. v_dc_title,
      v_edm_country, v_ebucore_fileByteSize)
  x_  extracted / computed / resolved / aggregated (e.g. x_reuse_level,
      x_dc_subject as list<struct>, x_title)
Column names mechanically derive from the EDM CURIE: dc:subject →
v_dc_subject, ebucore:fileByteSize → v_ebucore_fileByteSize.""",
        duckdb_pattern="""\
In merged_items, the list / struct-list columns are x_ prefixed because
they are aggregated from the links_ore_Proxy table (which stores raw
multi-valued properties in long format).""",
    ),

    # -- Struct access (DuckDB only) --
    EdmNote(
        topic="struct_list_access",
        edm_knowledge="Multi-valued properties in merged_items are nested lists with struct fields.",
        duckdb_pattern="""\
STRUCT LIST ACCESS PATTERNS in merged_items:

  x_dc_title, x_dc_description — LIST<STRUCT<x_value, x_value_lang>>:
    SELECT t.x_value, t.x_value_lang
    FROM (SELECT UNNEST(x_dc_title) AS t FROM merged_items)
    WHERE t.x_value IS NOT NULL

  x_dc_subject, x_dc_type, x_dc_format, x_edm_hasType, x_dcterms_spatial
    — LIST<STRUCT<x_value, x_label, x_value_is_iri>>:
    SELECT s.x_label, s.x_value
    FROM (SELECT UNNEST(x_dc_subject) AS s FROM merged_items)
    WHERE s.x_label IS NOT NULL

  x_dc_creator, x_dc_contributor, x_dc_publisher
    — LIST<STRUCT<x_value, x_name, x_value_is_iri>>:
    SELECT c.x_name, c.x_value
    FROM (SELECT UNNEST(x_dc_creator) AS c FROM merged_items)
    WHERE c.x_name IS NOT NULL

  x_dc_date, x_dc_identifier, x_dc_language, x_dc_rights, x_edm_year
    — LIST<VARCHAR>:
    SELECT y FROM (SELECT UNNEST(x_edm_year) AS y FROM merged_items)

KEEP k_iri ALONGSIDE UNNEST when you need to count items:
    SELECT COUNT(DISTINCT k_iri)
    FROM (SELECT k_iri, UNNEST(x_dc_subject) AS s FROM merged_items)
    WHERE s.x_label = 'Painting'

UNNEST WITH OTHER COLUMNS — put the UNNEST and every scalar column you
need in the SAME inner SELECT; do NOT reference merged_items again on the
outside:
    SELECT s.x_label, v_ebucore_fileByteSize, v_ebucore_width, v_ebucore_height
    FROM (
      SELECT UNNEST(x_dc_type) AS s,
             v_ebucore_fileByteSize, v_ebucore_width, v_ebucore_height
      FROM merged_items
      WHERE v_ebucore_fileByteSize IS NOT NULL
    )
    WHERE s.x_label IS NOT NULL

DO NOT write any of these — they are cartesian joins / invalid syntax:
    FROM merged_items, (SELECT UNNEST(x_dc_type) AS s FROM merged_items) t  -- cross join
    FROM merged_items, LATERAL (SELECT * FROM UNNEST(x_dc_type)) AS d(x_label, x_value)  -- wrong syntax
    FROM merged_items, UNNEST(x_dc_type) AS d  -- struct fields unreachable

FILTER within a list (lambda access works here):
    list_filter(x_dc_title,    x -> x.x_value_lang = 'en')
    list_filter(x_dc_subject,  x -> x.x_label IS NOT NULL)
    list_filter(x_dc_creator,  x -> x.x_name IS NOT NULL)

CHECK list containment (no UNNEST needed):
    list_has_any(list_transform(x_dc_type, x -> x.x_value),
                 ['http://vocab.getty.edu/aat/300046300'])
    list_has_any(list_transform(x_dc_subject, x -> LOWER(x.x_label)),
                 ['painting'])

Count list length: LEN(x_dc_subject)
Non-empty check:  LEN(x_dc_title) > 0

NEVER use EXISTS with UNNEST — DuckDB cannot resolve the UNNEST alias
inside EXISTS. Use list_has_any instead.""",
    ),

    # -- Reuse levels --
    EdmNote(
        topic="reuse_levels",
        edm_knowledge="""\
Rights are classified into open / restricted / prohibited reuse levels.
Open: CC0, PDM, CC-BY, CC-BY-SA.
Restricted: CC licenses with -nc or -nd, plus NoC-NC, NoC-OKLR, InC-EDU.
Prohibited: InC, CNE, InC-OW-EU, NKC, UND, and unknown URIs.""",
        duckdb_pattern="""\
x_reuse_level column in merged_items and group_items has values
'open' / 'restricted' / 'prohibited'.

Specific rights URIs live in v_edm_rights. For the family (cc0, cc-by,
rs-inc, etc.) and a human-readable label, JOIN with map_rights:
    SELECT m.x_family, COUNT(*) AS n
    FROM group_items g JOIN map_rights m ON g.v_edm_rights = m.k_iri
    WHERE g.v_edm_type = 'IMAGE'
    GROUP BY m.x_family
    ORDER BY n DESC""",
        sparql_pattern="""\
For open-reuse filtering, ALWAYS use the open-items materialized view.
PREFIX view: <https://qlever.cs.uni-freiburg.de/materializedView/>
SERVICE view:open-items { [ view:column-item ?item ; view:column-type ?type ] }""",
    ),

    # -- edm:type vs dc:type --
    EdmNote(
        topic="type_vs_dc_type",
        edm_knowledge="""\
edm:type is a controlled enum with 5 uppercase values: IMAGE, TEXT, SOUND,
VIDEO, 3D.  dc:type is free-text from providers with millions of values
like 'photograph', 'Preserved Specimen'.  Never confuse them.""",
        duckdb_pattern="""\
v_edm_type (VARCHAR) in merged_items / group_items is edm:type.
x_dc_type (LIST<STRUCT<x_value, x_label, x_value_is_iri>>) in merged_items
is dc:type (resolved).""",
        sparql_pattern="""\
edm:type is on the Europeana proxy with exactly 5 uppercase values.
dc:type is on the provider proxy with free-text values.
?eProxy edm:europeanaProxy "true" . ?eProxy edm:type ?type .""",
    ),

    # -- Content availability --
    EdmNote(
        topic="content_availability",
        edm_knowledge="""\
v_edm_isShownBy = direct content URL (downloadable digital object).
v_edm_isShownAt = landing page at provider website.
x_has_iiif = whether the primary web resource exposes a IIIF service.
v_ebucore_width / v_ebucore_height = pixel dimensions (NULL if unknown).""",
        duckdb_pattern="""\
An item "has content" if v_edm_isShownBy IS NOT NULL (or use
x_has_content_url = true in group_items, which is exactly this check).""",
        sparql_pattern="""\
edm:isShownBy and edm:isShownAt are on ore:Aggregation.
?agg edm:aggregatedCHO ?item . ?agg edm:isShownBy ?url .""",
    ),

    # -- Country and institution --
    EdmNote(
        topic="country_institution",
        edm_knowledge="""\
v_edm_country = providing country (string like 'Netherlands', 'France').
v_edm_dataProvider = data provider organisation URI (in merged_items and
group_items). x_dataProvider_name is the resolved English-preferred name.
v_edm_provider = aggregator URI; x_provider_name is the resolved name.
edm:country is ONLY on edm:EuropeanaAggregation, not on ore:Aggregation.""",
        duckdb_pattern="""\
For human-readable institution names, use x_dataProvider_name directly
from merged_items. Or query values_foaf_Organization directly:
    SELECT COALESCE(MAX(v_skos_prefLabel)
                    FILTER (WHERE x_prefLabel_lang = 'en'),
                    MAX(v_skos_prefLabel)) AS name
    FROM values_foaf_Organization
    WHERE k_iri = '<some-org-uri>'
    GROUP BY k_iri""",
        sparql_pattern="""\
?eAgg edm:aggregatedCHO ?item . ?eAgg a edm:EuropeanaAggregation . ?eAgg edm:country ?country .
edm:dataProvider is a literal on ore:Aggregation: ?agg edm:dataProvider ?dp .""",
    ),

    # -- Specimen exclusion --
    EdmNote(
        topic="specimen_exclusion",
        edm_knowledge="""\
Natural-history specimens dominate open images (~10.8M items).
Exclude via dc:type labels containing 'Preserved Specimen',
'biological specimen', or 'herbarium'.""",
        duckdb_pattern="""\
NOT list_has_any(list_transform(x_dc_type, x -> LOWER(x.x_label)),
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
- Prefer group_items over merged_items for GROUP BY questions: no UNNEST,
  no struct access, no list columns. Scans run in seconds instead of
  minutes.
- Prefer map_cho_entities over UNNEST on x_dc_subject when finding all
  items referencing a given entity IRI.
- Never SELECT *. Always specify columns.
- Filter early (inside inner SELECT) before UNNEST explodes rows.
- For counting items that satisfy some per-value predicate, prefer
  list_has_any over UNNEST + COUNT(DISTINCT).""",
        sparql_pattern="""\
For open-reuse filtering, ALWAYS use the open-items materialized view.
Never use nested BIND/IF to classify 66M items.
Always COUNT(DISTINCT ?item) — items have multiple proxies and entity links.""",
    ),

    # -- Language tags --
    EdmNote(
        topic="language_tags",
        edm_knowledge="""\
x_dc_title and x_dc_description carry language tags in x_value_lang
('en', 'de', 'fr', …). Empty string '' means no language tag was set.
The x_dc_language list (dc:language) is distinct from title/description
language tags.""",
        duckdb_pattern="""\
x_dc_title and x_dc_description have an x_value_lang field inside the
struct. Empty string '' means untagged. NULL and '' are different.""",
        sparql_pattern="""\
LANG(?title) returns the tag. FILTER(LANG(?title) = "en") restricts to English.
STR(?title) strips the tag for string comparison.
FILTER(LANG(?label) = "en" || LANG(?label) = "") gets English or untagged.""",
    ),

    # -- Century bucketing --
    EdmNote(
        topic="century_bucketing",
        edm_knowledge="edm:year values are strings representing integer years.",
        duckdb_pattern="""\
x_edm_year is LIST<VARCHAR> — cast individual values to INTEGER.
    SELECT AVG(CAST(y AS INTEGER))
    FROM (SELECT UNNEST(x_edm_year) AS y FROM merged_items)
    WHERE y SIMILAR TO '[0-9]+'
Bucket by century: CASE WHEN CAST(y AS INTEGER) < 1500 THEN 'before 1500' ... END""",
        sparql_pattern="""\
edm:year is a string on the Europeana proxy. Cast to integer:
FILTER(xsd:integer(?year) >= 1800 && xsd:integer(?year) <= 1900)""",
    ),

    # -- Raw-layer / class boundaries --
    EdmNote(
        topic="raw_layer",
        edm_knowledge="""\
The raw layer preserves EDM class boundaries:
  values_edm_ProvidedCHO, values_ore_Proxy, values_ore_Aggregation,
  values_edm_EuropeanaAggregation, values_edm_WebResource,
  values_edm_Agent, values_edm_Place, values_skos_Concept,
  values_edm_TimeSpan, values_foaf_Organization, values_svcs_Service,
  values_cc_License, values_edm_PersistentIdentifier,
  values_edm_PersistentIdentifierScheme.
Each has a paired links_* table (long format) with columns
(k_iri, x_property, x_value, x_value_is_iri, x_value_lang).

Proxy → CHO join: values_ore_Proxy.k_iri_cho is the FK to the CHO.
Aggregation → CHO join: values_ore_Aggregation.k_iri_cho is the FK.
WebResource → CHO join: values_edm_WebResource.k_iri_cho (filled in by
    the aggregation link during export).
Service → WebResource: values_svcs_Service.k_iri_webresource.""",
        duckdb_pattern="""\
Entity prefLabel resolution (English preferred):
    SELECT k_iri,
           COALESCE(MAX(v_skos_prefLabel) FILTER (WHERE x_prefLabel_lang = 'en'),
                    MAX(v_skos_prefLabel)) AS label
    FROM values_edm_Agent GROUP BY k_iri

Agent owl:sameAs links (via long-format links table):
    SELECT k_iri, x_value AS same_as_iri
    FROM links_edm_Agent
    WHERE x_property = 'v_owl_sameAs'""",
    ),

    # -- Entity → CHO navigation via map_cho_entities --
    EdmNote(
        topic="map_cho_entities",
        edm_knowledge="""\
map_cho_entities pre-joins CHOs to the contextual entities they
reference via provider-proxy properties whose value is an IRI.
Much faster than UNNEST-ing x_dc_subject / x_dc_creator etc. when
searching by entity IRI.""",
        duckdb_pattern="""\
-- All CHOs referencing a specific Wikidata entity:
SELECT COUNT(DISTINCT k_iri_cho)
FROM map_cho_entities
WHERE k_iri_entity = 'http://www.wikidata.org/entity/Q42'

-- Top concepts used as subjects, with item counts:
SELECT c.v_skos_prefLabel AS concept, m.k_iri_entity AS concept_iri, n AS n_items
FROM (
    SELECT k_iri_entity, COUNT(DISTINCT k_iri_cho) AS n
    FROM map_cho_entities
    WHERE x_entity_class = 'skos_Concept' AND x_property = 'v_dc_subject'
    GROUP BY k_iri_entity
) m
JOIN values_skos_Concept c ON m.k_iri_entity = c.k_iri
WHERE c.x_prefLabel_lang = 'en'
ORDER BY n DESC LIMIT 20""",
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

    # -- Provider proxy --
    EdmNote(
        topic="provider_proxy",
        edm_knowledge="""\
The provider proxy carries original descriptive metadata as literals:
dc:title, dc:creator, dc:subject, dc:date, dc:description, dc:type,
dc:language, dc:format, dc:identifier, dc:publisher, dc:contributor,
dc:rights.""",
        sparql_pattern="""\
?proxy ore:proxyFor ?item .
FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" . }
?proxy dc:title ?title .
All are multivalued, most are language-tagged literals.""",
    ),

    # -- Europeana proxy --
    EdmNote(
        topic="europeana_proxy",
        edm_knowledge="""\
The Europeana proxy carries normalised/enriched fields:
edm:type (enum), edm:year (string). Also carries enriched entity URIs
for dc:creator, dc:contributor, dc:subject, dcterms:spatial.""",
        sparql_pattern="""\
?eProxy ore:proxyFor ?item .
?eProxy edm:europeanaProxy "true" .
Entity URIs from search_entity are on the EUROPEANA PROXY.""",
    ),

    # -- Aggregation (SPARQL) --
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

    # -- Materialized views (SPARQL only) --
    EdmNote(
        topic="materialized_views",
        edm_knowledge="""\
The open-items QLever materialized view precomputes all items with
open reuse rights joined with edm:type.""",
        sparql_pattern="""\
PREFIX view: <https://qlever.cs.uni-freiburg.de/materializedView/>
SERVICE view:open-items { [ view:column-item ?item ; view:column-type ?type ] }
FILTER(?type = "IMAGE")""",
    ),

    # -- Schema-derived: SPARQL prefixes --
    _sparql_prefixes_note(),
]


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_duckdb_notes() -> str:
    """Render domain notes for the DuckDB / Parquet ask agent system prompt."""
    sections: list[str] = []
    idx = 1
    for note in EDM_NOTES:
        if not note.duckdb_pattern and not note.edm_knowledge:
            continue
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
    """Render domain notes as strings for GRASP's notes JSON."""
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
