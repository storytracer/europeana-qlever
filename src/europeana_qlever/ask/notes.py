"""Structured EDM domain knowledge for NL query agents.

Single source of truth for Europeana Data Model semantics.  Each note
has language-agnostic EDM knowledge plus optional DuckDB and SPARQL
patterns.

- :func:`render_duckdb_notes` produces the system-prompt notes for
  :class:`~europeana_qlever.ask.parquet.AskParquet`.
- :func:`render_sparql_notes` produces the note list for GRASP's
  ``europeana-notes.json``.
- :func:`export_grasp_notes` writes the JSON file directly.

All DuckDB column references target:

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
The export has three kinds of tables:
  group_items    — one row per CHO, scalar categorical / boolean /
                   integer columns only (v_edm_country, v_edm_type,
                   x_reuse_level, x_has_iiif, x_primary_language, …).
                   Use for fast GROUP BY analytics.
  values_* / links_* — raw EDM tables. values_* have scalar columns
                   (one row per entity); links_* are long-format (one
                   row per value, columns k_iri, x_property, x_value,
                   x_value_is_iri, x_value_lang). Most multi-valued
                   descriptive metadata lives in links_ore_Proxy.
  map_*          — lookup / navigation: map_rights (rights URI →
                   family/label/reuse_level), map_sameAs (entity
                   sameAs links), map_cho_entities (pre-joined CHO →
                   contextual entity references).""",
        duckdb_pattern="""\
CHOOSING A TABLE:
- Counts / distributions by country, type, reuse level, language → group_items
- All items referencing a specific Agent/Place/Concept IRI → map_cho_entities
- Rights family/label lookup → JOIN group_items.v_edm_rights = map_rights.k_iri
- Per-item titles / subjects / creators / dates → links_ore_Proxy filtered
  by x_property (e.g. 'v_dc_title'), joined to values_ore_Proxy to reach the
  CHO URI
- Entity deep-dive (prefLabels, sameAs, broader/narrower) → values_* / links_*
  for the entity class""",
    ),

    # -- Column-prefix convention --
    EdmNote(
        topic="column_prefixes",
        edm_knowledge="""\
Column names carry a prefix that signals their role:
  k_  key / foreign key (e.g. k_iri, k_iri_cho, k_iri_entity)
  v_  scalar EDM property, directly from the RDF (e.g. v_dc_title,
      v_edm_country, v_ebucore_fileByteSize)
  x_  extracted / computed / resolved / aggregated (e.g. x_reuse_level,
      x_rights_family, x_label)
Column names mechanically derive from the EDM CURIE: dc:subject →
v_dc_subject, ebucore:fileByteSize → v_ebucore_fileByteSize.""",
    ),

    # -- Proxy → CHO navigation --
    EdmNote(
        topic="proxy_cho_join",
        edm_knowledge="""\
Descriptive metadata (titles, creators, subjects, dates, etc.) is NOT
stored on edm:ProvidedCHO directly. It lives on ore:Proxy. Each CHO has
two proxies: a provider proxy (original metadata, in links_ore_Proxy
with proxy_type filtered via values_ore_Proxy) and a Europeana proxy
(normalised/enriched, e.g. edm:type, edm:year).

To pull provider-side descriptive properties for CHOs, join through
values_ore_Proxy.k_iri_cho.""",
        duckdb_pattern="""\
PROVIDER-PROXY TITLES PER CHO:
    SELECT p.k_iri_cho AS cho, l.x_value AS title, l.x_value_lang AS lang
    FROM links_ore_Proxy l
    JOIN values_ore_Proxy p ON l.k_iri = p.k_iri
    WHERE l.x_property = 'v_dc_title'
      AND (p.v_edm_europeanaProxy IS NULL OR p.v_edm_europeanaProxy != 'true')

EUROPEANA-PROXY edm:year (one row per value):
    SELECT p.k_iri_cho AS cho, l.x_value AS year
    FROM links_ore_Proxy l
    JOIN values_ore_Proxy p ON l.k_iri = p.k_iri
    WHERE l.x_property = 'v_edm_year' AND p.v_edm_europeanaProxy = 'true'

Tip: filter l.x_property BEFORE joining — the Hive partition prunes the
scan to a single file.""",
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
group_items.x_reuse_level is the pre-computed classification
('open' / 'restricted' / 'prohibited'). The specific rights URI is in
group_items.v_edm_rights.

For the rights family (cc0, cc-by, rs-inc, …) and a human label, JOIN
with map_rights:
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
v_edm_type (VARCHAR) in group_items is edm:type (the enum).
dc:type values live in links_ore_Proxy with x_property = 'v_dc_type' — one
row per value, potentially an IRI (x_value_is_iri=true) or a free-text
literal. Resolve IRIs to human labels via values_skos_Concept.""",
        sparql_pattern="""\
edm:type is on the Europeana proxy with exactly 5 uppercase values.
dc:type is on the provider proxy with free-text values.
?eProxy edm:europeanaProxy "true" . ?eProxy edm:type ?type .""",
    ),

    # -- Content availability --
    EdmNote(
        topic="content_availability",
        edm_knowledge="""\
edm:isShownBy is the direct content URL (downloadable digital object).
edm:isShownAt is the landing page at the provider website.
Both live on ore:Aggregation.
WebResource rows carry technical metadata (dimensions, MIME type,
file size). IIIF service presence is flagged by group_items.x_has_iiif.""",
        duckdb_pattern="""\
"Has content" is x_has_content_url = true in group_items (equivalent to
v_edm_isShownBy IS NOT NULL on the aggregation).

WebResource scalars keyed by content URL:
    SELECT k_iri AS content_url, v_ebucore_hasMimeType, v_ebucore_width,
           v_ebucore_height, v_ebucore_fileByteSize
    FROM values_edm_WebResource""",
        sparql_pattern="""\
edm:isShownBy and edm:isShownAt are on ore:Aggregation.
?agg edm:aggregatedCHO ?item . ?agg edm:isShownBy ?url .""",
    ),

    # -- Country and institution --
    EdmNote(
        topic="country_institution",
        edm_knowledge="""\
v_edm_country = providing country (string like 'Netherlands', 'France').
v_edm_dataProvider = data provider organisation URI (in group_items).
v_edm_provider = aggregator URI.
edm:country is ONLY on edm:EuropeanaAggregation, not on ore:Aggregation.""",
        duckdb_pattern="""\
For human-readable institution names, query values_foaf_Organization:
    SELECT k_iri,
           COALESCE(MAX(v_skos_prefLabel) FILTER (WHERE x_prefLabel_lang = 'en'),
                    MAX(v_skos_prefLabel)) AS name
    FROM values_foaf_Organization
    WHERE k_iri = '<some-org-uri>'
    GROUP BY k_iri

Items per country × provider:
    SELECT v_edm_country, v_edm_dataProvider, COUNT(*) AS n
    FROM group_items GROUP BY 1, 2 ORDER BY n DESC""",
        sparql_pattern="""\
?eAgg edm:aggregatedCHO ?item . ?eAgg a edm:EuropeanaAggregation . ?eAgg edm:country ?country .
edm:dataProvider is a literal on ore:Aggregation: ?agg edm:dataProvider ?dp .""",
    ),

    # -- Specimen exclusion --
    EdmNote(
        topic="specimen_exclusion",
        edm_knowledge="""\
Natural-history specimens dominate open images (~10.8M items).
Exclude via dc:type literals containing 'Preserved Specimen',
'biological specimen', or 'herbarium'.""",
        duckdb_pattern="""\
CHOs whose provider-proxy dc:type literal matches one of the
specimen keywords (so you can anti-join):
    SELECT DISTINCT p.k_iri_cho
    FROM links_ore_Proxy l
    JOIN values_ore_Proxy p ON l.k_iri = p.k_iri
    WHERE l.x_property = 'v_dc_type'
      AND NOT l.x_value_is_iri
      AND regexp_matches(LOWER(l.x_value),
          '(preserved specimen|biological specimen|herbarium)')""",
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
- Prefer group_items for any question that fits its scalar columns —
  scans run in seconds.
- Prefer map_cho_entities over links_ore_Proxy when searching by a
  specific entity IRI (agent/place/concept/timespan).
- links_ore_Proxy is Hive-partitioned on x_property. Filter
  l.x_property = 'v_dc_XXX' FIRST — DuckDB prunes to a single file.
- Never SELECT *. Always specify columns.
- COUNT(DISTINCT p.k_iri_cho) when counting items through a proxy or
  links join — proxies and entity links can fan out.""",
        sparql_pattern="""\
For open-reuse filtering, ALWAYS use the open-items materialized view.
Never use nested BIND/IF to classify 66M items.
Always COUNT(DISTINCT ?item) — items have multiple proxies and entity links.""",
    ),

    # -- Language tags --
    EdmNote(
        topic="language_tags",
        edm_knowledge="""\
Title and description literals carry language tags via
links_ore_Proxy.x_value_lang ('en', 'de', 'fr', …). Empty string ''
means no language tag was set. The dc:language property (stored as
x_property = 'v_dc_language' in links_ore_Proxy) is distinct from
title/description language tags.""",
        duckdb_pattern="""\
English-preferred titles per CHO:
    SELECT p.k_iri_cho,
           COALESCE(MAX(l.x_value) FILTER (WHERE l.x_value_lang = 'en'),
                    MAX(l.x_value)) AS title
    FROM links_ore_Proxy l
    JOIN values_ore_Proxy p ON l.k_iri = p.k_iri
    WHERE l.x_property = 'v_dc_title'
      AND (p.v_edm_europeanaProxy IS NULL OR p.v_edm_europeanaProxy != 'true')
    GROUP BY p.k_iri_cho""",
        sparql_pattern="""\
LANG(?title) returns the tag. FILTER(LANG(?title) = "en") restricts to English.
STR(?title) strips the tag for string comparison.
FILTER(LANG(?label) = "en" || LANG(?label) = "") gets English or untagged.""",
    ),

    # -- edm:year bucketing --
    EdmNote(
        topic="year_bucketing",
        edm_knowledge="edm:year values are strings representing integer years.",
        duckdb_pattern="""\
edm:year lives on the Europeana proxy in links_ore_Proxy:
    SELECT AVG(CAST(l.x_value AS INTEGER))
    FROM links_ore_Proxy l
    JOIN values_ore_Proxy p ON l.k_iri = p.k_iri
    WHERE l.x_property = 'v_edm_year'
      AND p.v_edm_europeanaProxy = 'true'
      AND l.x_value SIMILAR TO '[0-9]+'
Bucket by century: CASE WHEN CAST(x_value AS INTEGER) < 1500 THEN 'before 1500' ... END""",
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
WebResource → Aggregation: values_ore_Aggregation.v_edm_isShownBy =
    values_edm_WebResource.k_iri (URL).
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
Much faster than filtering links_ore_Proxy by x_value when searching
by entity IRI.""",
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
open reuse rights (CC0, PDM, CC-BY, CC-BY-SA) joined with edm:type.

ONLY use this view when the user's question explicitly scopes to open
access — words like "open", "open rights", "open access", "reusable",
"CC0/CC-BY/PDM", or "freely licensed". For any other question (general
counts, type filters, content searches) DO NOT use this view: it
silently restricts the answer to the open-rights subset and gives the
wrong total. Filter edm:type via the Europeana proxy instead.

QLever column-order constraint (when the view is appropriate): a
SERVICE block on a materialized view cannot bind a later column to a
constant while an earlier column is unbound. So you CANNOT inline
view:column-type as "IMAGE" while view:column-item is a variable —
QLever rejects with "When setting the second column of a materialized
view to a fixed value, the first column must also be fixed." Use
FILTER on the variable instead.""",
        sparql_pattern="""\
PREFIX view: <https://qlever.cs.uni-freiburg.de/materializedView/>

# Correct (only when the user asked for open / reusable items):
SERVICE view:open-items { [ view:column-item ?item ; view:column-type ?type ] }
FILTER(?type = "IMAGE")

# WRONG (rejected by QLever — column-item unbound while column-type fixed):
# SERVICE view:open-items {
#   [ view:column-item ?item ; view:column-type "IMAGE" ]
# }""",
    ),

    # -- Full-text literal scanning at scale (SPARQL only) --
    EdmNote(
        topic="literal_scan",
        edm_knowledge="""\
CONTAINS / REGEX / LCASE on free-text literals (dc:description,
dc:title, …) scans every literal in the index. With ~66M items and
billions of literals this WILL time out unless the candidate set is
narrowed first.""",
        sparql_pattern="""\
Narrow the candidate set BEFORE the literal scan with a selective
structural pattern — Europeana-proxy edm:type, a country, a specific
entity IRI. Add view:open-items ONLY if the user asked for open /
reusable items (otherwise it silently drops the closed-rights subset
from the answer).

Do NOT add a LANG filter unless the user's question specifies a
language — it changes the answer by silently dropping items whose
literal carries a different language tag. When the user does specify a
language, include "" alongside the target tag so untagged literals are
not also dropped: FILTER(LANG(?x) = "en" || LANG(?x) = "")

# Bad — full literal scan, will time out:
?proxy dc:description ?desc .
FILTER(CONTAINS(LCASE(STR(?desc)), "teapot"))

# Good — narrow first via the Europeana proxy's edm:type, then scan
# the filtered subset. No open-items (the question is not scoped to
# open items). No LANG filter (no language was specified).
?eProxy ore:proxyFor ?item ; edm:europeanaProxy "true" ; edm:type "IMAGE" .
?proxy ore:proxyFor ?item .
FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" }
?proxy dc:description ?desc .
FILTER(CONTAINS(LCASE(STR(?desc)), "teapot"))""",
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
