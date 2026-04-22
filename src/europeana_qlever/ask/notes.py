"""Structured EDM domain knowledge for NL query agents.

Single source of truth for Europeana Data Model semantics.  Each note has
language-agnostic EDM knowledge plus optional DuckDB and SPARQL patterns.

- :func:`render_duckdb_notes` produces the system-prompt notes for
  :class:`~europeana_qlever.ask.parquet.AskParquet`.
- :func:`render_sparql_notes` produces the note list for GRASP's
  ``europeana-notes.json``.
- :func:`export_grasp_notes` writes the JSON file directly.

Notes marked ``# -- Schema-derived --`` are generated from
``edm_parquet.yaml`` via :func:`_schema_derived_notes`.
"""

from __future__ import annotations

import json
from collections import defaultdict
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


def _column_types_note() -> EdmNote:
    """Derive the column_types note from Item fields in the schema."""
    groups: dict[str, list[str]] = defaultdict(list)
    for name, attr in schema_loader.item_fields().items():
        if not attr.multivalued:
            continue
        type_str = schema_loader._DUCKDB_LIST_TYPE.get(attr.range or "string", "LIST<VARCHAR>")
        desc = f" ({attr.description})" if attr.description else ""
        groups[type_str].append(f"{name}{desc}")

    lines = ["MULTI-VALUED COLUMN TYPES:"]
    for type_str, cols in groups.items():
        lines.append(f"- {type_str}: {', '.join(cols)}")

    return EdmNote(
        topic="column_types",
        edm_knowledge="Multi-valued properties use typed list columns.",
        duckdb_pattern="\n".join(lines),
    )


def _contextual_entities_note() -> EdmNote:
    """Derive the contextual_entities note from entity exports in the schema."""
    exports = schema_loader.export_classes()
    entity_types = schema_loader.entity_classes()

    duckdb_parts: list[str] = []
    sparql_parts: list[str] = []

    for cls_name in entity_types:
        annots = schema_loader._annots(schema_loader.schema_view().get_class(cls_name))
        core_name = annots.get("export_name_core", "")
        links_name = annots.get("export_name_links", "")
        id_col = annots.get("id_column", cls_name.lower())

        if not core_name:
            continue

        # Core fields
        core_info = exports.get(core_name)
        core_fields = [
            n for n in (core_info.attributes if core_info else {})
            if n not in (id_col, "pref_label", "pref_label_lang")
            and not (core_info and core_info.attributes[n].identifier)
        ]

        # Link properties
        link_props = schema_loader.entity_link_property_details(cls_name)
        link_names = [lp.name for lp in link_props]

        plural = cls_name.lower() + "s" if not cls_name.lower().endswith("s") else cls_name.lower()
        duckdb_parts.append(
            f"{core_name}: one row per prefLabel per {cls_name.lower()}. "
            f"Columns: {id_col}, pref_label, pref_label_lang"
            + (f", {', '.join(core_fields)}" if core_fields else "")
            + "."
        )
        duckdb_parts.append(
            f"{links_name}: multi-valued properties in long format "
            f"({id_col}, property, value, lang). "
            f"Properties: {', '.join(link_names)}."
        )

    # SPARQL entity patterns
    for cls_name in entity_types:
        cls = schema_loader.schema_view().get_class(cls_name)
        if cls and cls.class_uri:
            core_fields = schema_loader.entity_core_fields(cls_name)
            field_uris = [a.slot_uri for a in core_fields.values() if a.slot_uri]
            sparql_parts.append(
                f"{cls.class_uri}: skos:prefLabel (language-tagged)"
                + (f", {', '.join(field_uris)}" if field_uris else "")
                + "."
            )

    return EdmNote(
        topic="contextual_entities",
        edm_knowledge=(
            f"Entity tables: {', '.join(a.get('export_name_core', '') for c in entity_types for a in [schema_loader._annots(schema_loader.schema_view().get_class(c))])}.\n"
            "One row per prefLabel variant. Use for entity-level analysis."
        ),
        duckdb_pattern=(
            "\n".join(duckdb_parts)
            + "\nJoin subjects.uri with concept column in concepts_core for entity-level analysis."
            "\nJoin creators.uri/contributors.uri with agent column in agents_core."
        ),
        sparql_pattern=(
            "All entities have skos:prefLabel (language-tagged) and owl:sameAs (URI).\n"
            + "\n".join(sparql_parts)
        ),
    )


def _sparql_prefixes_note() -> EdmNote:
    """Derive the sparql_prefixes note from schema prefix declarations."""
    pfx = schema_loader.prefixes()
    lines = [f"PREFIX {k}: <{v}>" for k, v in sorted(pfx.items())]
    # Add the view prefix which isn't in the schema but is needed for queries
    lines.append("PREFIX view: <https://qlever.cs.uni-freiburg.de/materializedView/>")
    return EdmNote(
        topic="sparql_prefixes",
        edm_knowledge="Standard RDF prefix declarations for Europeana queries.",
        sparql_pattern="\n".join(lines),
    )


def _schema_derived_notes() -> list[EdmNote]:
    """Return all notes that are generated from the schema."""
    return [
        _column_types_note(),
        _contextual_entities_note(),
        _sparql_prefixes_note(),
    ]


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
- Unnest uses the subquery form — DuckDB does NOT support `UNNEST(col) AS t(field1, field2)`
  to name struct fields. Put UNNEST in a subquery and access fields via the alias.
- titles, descriptions — STRUCT<value VARCHAR, lang VARCHAR>:
    SELECT t.value, t.lang
    FROM (SELECT UNNEST(titles) AS t FROM items)
    WHERE t.value IS NOT NULL
- subjects, dc_types, formats — STRUCT<label VARCHAR, uri VARCHAR>:
    SELECT d.label, d.uri
    FROM (SELECT UNNEST(dc_types) AS d FROM items)
    WHERE d.label IS NOT NULL
- creators, contributors, publishers — STRUCT<name VARCHAR, uri VARCHAR>:
    SELECT c.name, c.uri
    FROM (SELECT UNNEST(creators) AS c FROM items)
    WHERE c.name IS NOT NULL
- Keep item column alongside unnest when you need to count items:
    SELECT COUNT(DISTINCT item)
    FROM (SELECT item, UNNEST(subjects) AS s FROM items)
    WHERE s.label = 'Painting'
- UNNEST WITH OTHER COLUMNS — put the UNNEST **and every scalar column you need**
  in the SAME inner SELECT. Do NOT reference items_resolved again on the outside:
    SELECT d.label, file_bytes, width, height
    FROM (
      SELECT UNNEST(dc_types) AS d, file_bytes, width, height
      FROM items_resolved
      WHERE file_bytes IS NOT NULL
    )
    WHERE d.label IS NOT NULL
  Filter scalars early (inside the inner SELECT) — it runs before UNNEST explodes
  the rows, which is dramatically faster on 66M items.
- DO NOT write any of these — they are cartesian joins / invalid syntax that
  will either run forever or fail:
    FROM items_resolved, (SELECT UNNEST(dc_types) AS d FROM items_resolved) t  -- cross join
    FROM items_resolved, LATERAL (SELECT * FROM UNNEST(dc_types)) AS d(label, uri)  -- wrong syntax
    FROM items_resolved, UNNEST(dc_types) AS d                                  -- struct fields unreachable
- Filter within a list (lambda struct field access works here):
    list_filter(titles, x -> x.lang = 'en')          -- value/lang struct
    list_filter(subjects, x -> x.label IS NOT NULL)  -- label/uri struct
    list_filter(creators, x -> x.name IS NOT NULL)   -- name/uri struct
- Check list containment:
    list_has_any(list_transform(dc_types, x -> LOWER(x.label)), ['preserved specimen'])
- Count list elements: LEN(subjects)
- Check non-empty: LEN(titles) > 0 (NOT: titles IS NOT NULL, which only checks for NULL not empty)""",
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

    # -- Schema-derived: column types --
    _column_types_note(),

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

    # -- Schema-derived: contextual entities --
    _contextual_entities_note(),

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

    # -- Schema-derived: SPARQL prefixes --
    _sparql_prefixes_note(),
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
