# /// script
# requires-python = ">=3.11"
# ///
"""Generate GRASP domain notes from the EDM base schema (edm.yaml).

Reads class/property definitions via schema_loader.edm_class_properties()
and produces grasp/europeana-notes.json — a JSON array of strings that
GRASP injects into the LLM system prompt.

Usage:
    uv run grasp/generate-notes.py
"""

from __future__ import annotations

import json
from pathlib import Path

from linkml_runtime.utils.schemaview import SchemaView

from europeana_qlever.query import SparqlHelpers
from europeana_qlever.rights import (
    _CC_PD_PREFIX,
    _OPEN_CC_PREFIXES,
    _RESTRICTED_RS_URIS,
)

# Load edm.yaml directly — not via schema_loader which loads edm_parquet.yaml
# where export classes shadow the full base classes.
_EDM_SCHEMA = Path(__file__).resolve().parent.parent / "src" / "europeana_qlever" / "schema" / "edm.yaml"
_sv = SchemaView(str(_EDM_SCHEMA))

# ---------------------------------------------------------------------------
# Europeana proxy properties — these are on the Europeana proxy, not the
# provider proxy.  This is an EDM spec rule, not encoded in edm.yaml.
# ---------------------------------------------------------------------------

EUROPEANA_PROXY_PROPERTIES = {
    "edm:europeanaProxy",
    "edm:type",
    "edm:year",
}

# Properties where the Europeana enrichment pipeline adds entity URIs
# to the Europeana proxy (in addition to provider proxy literals).
ENRICHED_PROPERTIES = {
    "dc:creator",
    "dc:contributor",
    "dc:subject",
    "dcterms:spatial",
}

# Properties on edm:EuropeanaAggregation (subclass of ore:Aggregation,
# not a separate class in edm.yaml).
EUROPEANA_AGGREGATION_PROPERTIES = {
    "edm:country",
    "edm:completeness",
    "edm:preview",
    "edm:landingPage",
    "edm:datasetName",
    "edm:language",
}

# ---------------------------------------------------------------------------
# EdmType enum values (from edm.yaml)
# ---------------------------------------------------------------------------

EDM_TYPES = ["IMAGE", "TEXT", "SOUND", "VIDEO", "3D"]


def _prop_line(curie: str, *, range_: str, multivalued: bool) -> str:
    """Format a single property description."""
    parts = [curie]
    if range_ == "uri":
        parts.append("(URI)")
    else:
        parts.append(f"({range_})")
    if multivalued:
        parts.append("[multivalued]")
    return " ".join(parts)


def _class_props(cls_name: str) -> dict[str, dict]:
    """Get properties for a class from edm.yaml, keyed by slot_uri CURIE."""
    cls = _sv.get_class(cls_name)
    if cls is None:
        raise ValueError(f"Unknown EDM class: {cls_name!r}")
    result = {}
    for attr in cls.attributes.values():
        if attr.slot_uri:
            result[attr.slot_uri] = {
                "range": attr.range or "string",
                "multivalued": bool(attr.multivalued),
            }
    return result


def generate_notes() -> list[str]:
    notes: list[str] = []

    # =======================================================================
    # Section 1: Core EDM Model
    # =======================================================================

    notes.append(
        "Europeana uses the EDM (Europeana Data Model). "
        "Metadata is NOT stored directly on the item (edm:ProvidedCHO). "
        "It flows through proxies (ore:Proxy) and aggregations (ore:Aggregation)."
    )

    notes.append(
        "Each item has TWO proxies: "
        "(1) the PROVIDER PROXY with original metadata from the data provider, "
        "(2) the EUROPEANA PROXY with normalised/enriched metadata from Europeana. "
        "The Europeana enrichment pipeline also adds entity URIs "
        "(for dc:creator, dc:subject, dc:contributor, dcterms:spatial) "
        "to the Europeana proxy."
    )

    # =======================================================================
    # Section 2: SPARQL Pattern Definitions
    # =======================================================================

    notes.append(
        "PROVIDER PROXY pattern (for original descriptive metadata): "
        + SparqlHelpers.provider_proxy()
    )

    notes.append(
        "EUROPEANA PROXY pattern (for edm:type, edm:year, enriched entity URIs): "
        + SparqlHelpers.europeana_proxy()
    )

    notes.append(
        "AGGREGATION pattern (for edm:rights, edm:dataProvider, edm:provider, URLs): "
        + SparqlHelpers.aggregation()
    )

    notes.append(
        "EUROPEANA AGGREGATION pattern (for edm:country, edm:completeness, edm:datasetName): "
        + SparqlHelpers.europeana_aggregation()
    )

    notes.append(
        "WEB RESOURCE pattern (for MIME type, dimensions, file size): "
        "?agg edm:aggregatedCHO ?item . ?agg edm:hasView ?wr ."
    )

    # =======================================================================
    # Section 3: Property → Pattern Map (from edm.yaml classes)
    # =======================================================================

    # --- Proxy properties ---
    proxy_props = _class_props("Proxy")
    provider_lines = []
    europeana_lines = []

    for curie, info in sorted(proxy_props.items()):
        line = _prop_line(curie, range_=info["range"], multivalued=info["multivalued"])
        if curie in EUROPEANA_PROXY_PROPERTIES:
            europeana_lines.append(line)
        else:
            provider_lines.append(line)

    notes.append(
        "Properties on the PROVIDER PROXY (?proxy): "
        + ", ".join(provider_lines)
        + "."
    )

    notes.append(
        "Properties on the EUROPEANA PROXY (?eProxy): "
        + ", ".join(europeana_lines)
        + ". PLUS enriched entity URIs for: "
        + ", ".join(sorted(ENRICHED_PROPERTIES))
        + " (use Europeana proxy when searching by entity URI from search_entity)."
    )

    # --- Aggregation properties ---
    agg_props = _class_props("Aggregation")
    agg_lines = []

    for curie, info in sorted(agg_props.items()):
        agg_lines.append(
            _prop_line(curie, range_=info["range"], multivalued=info["multivalued"])
        )

    notes.append(
        "Properties on the AGGREGATION (?agg): "
        + ", ".join(agg_lines)
        + "."
    )

    # EuropeanaAggregation is a subclass not in edm.yaml — hardcode its properties
    eagg_lines = [
        "edm:country (string)", "edm:completeness (string)",
        "edm:preview (URI)", "edm:landingPage (URI)",
        "edm:datasetName (string)", "edm:language (string)",
    ]
    notes.append(
        "Properties on the EUROPEANA AGGREGATION (?eAgg): "
        + ", ".join(eagg_lines)
        + "."
    )

    # --- WebResource properties ---
    wr_props = _class_props("WebResource")
    wr_lines = [
        _prop_line(curie, range_=info["range"], multivalued=info["multivalued"])
        for curie, info in sorted(wr_props.items())
    ]

    notes.append(
        "Properties on WEB RESOURCES (?wr): "
        + ", ".join(wr_lines)
        + "."
    )

    # =======================================================================
    # Section 4: Entity Classes (from edm.yaml)
    # =======================================================================

    for cls_name, cls_uri in [
        ("Agent", "edm:Agent"),
        ("Place", "edm:Place"),
        ("Concept", "skos:Concept"),
        ("TimeSpan", "edm:TimeSpan"),
    ]:
        props = _class_props(cls_name)
        prop_list = ", ".join(
            _prop_line(curie, range_=info["range"], multivalued=info["multivalued"])
            for curie, info in sorted(props.items())
        )
        notes.append(f"{cls_uri} properties: {prop_list}.")

    notes.append(
        "foaf:Organization properties (from EDM.md, not in edm.yaml): "
        "skos:prefLabel, edm:acronym, edm:country, edm:language, "
        "edm:europeanaRole, edm:heritageDomain, foaf:logo, owl:sameAs."
    )

    # =======================================================================
    # Section 5: Value Type Rules
    # =======================================================================

    notes.append(
        "edm:type on the Europeana proxy is a string literal with exactly these values: "
        + ", ".join(f'"{t}"' for t in EDM_TYPES)
        + ". Use edm:type for broad media type filtering."
    )

    notes.append(
        "dc:type on the provider proxy is free-text with millions of distinct values "
        "(e.g. 'Preserved Specimen', 'photograph', 'newspaper'). "
        "dc:type ≠ edm:type."
    )

    notes.append(
        "edm:rights is a URI on the ore:Aggregation "
        "(NOT on edm:EuropeanaAggregation — that has a different, incomplete copy). "
        "Always use the aggregation pattern for rights queries."
    )

    notes.append("edm:dataProvider and edm:country are literal strings, not URIs.")

    notes.append(
        "edm:year is on the Europeana proxy as a string. "
        "Cast with xsd:integer for range filters: "
        "FILTER(xsd:integer(?year) >= 1800 && xsd:integer(?year) <= 1900)."
    )

    # =======================================================================
    # Section 6: Rights Classification (from rights.py)
    # =======================================================================

    open_prefixes = [_CC_PD_PREFIX] + list(_OPEN_CC_PREFIXES)
    notes.append(
        "Rights classification — Open reuse URIs start with: "
        + " OR ".join(f'"{p}"' for p in open_prefixes)
        + ". Filter with STRSTARTS(STR(?rights), ...) || clauses."
    )

    notes.append(
        "Restricted reuse: other CC licenses (URI contains '-nc' or '-nd'). "
        "Also: "
        + ", ".join(_RESTRICTED_RS_URIS)
        + "."
    )

    notes.append(
        "Prohibited reuse: everything else, including "
        "http://rightsstatements.org/vocab/InC/1.0/ (In Copyright), "
        "http://rightsstatements.org/vocab/CNE/1.0/ (Copyright Not Evaluated), "
        "and other rightsstatements.org URIs."
    )

    # =======================================================================
    # Section 7: Query Rules
    # =======================================================================

    notes.append("Always COUNT DISTINCT ?item — items have multiple proxies and entity links.")

    notes.append(
        "Entity URIs (from search_entity) are on the EUROPEANA PROXY. "
        "To find items by entity URI: "
        "?eProxy ore:proxyFor ?item . "
        '?eProxy edm:europeanaProxy "true" . '
        "?eProxy dc:subject <concept-uri> ."
    )

    notes.append(
        "Text search on literals (e.g. title contains 'astronomy'): "
        "use the PROVIDER PROXY. "
        "?proxy ore:proxyFor ?item . "
        'FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" . } '
        "?proxy dc:title ?title . "
        'FILTER(CONTAINS(LCASE(STR(?title)), "astronomy")).'
    )

    notes.append(
        "For classification queries (e.g. reuse level distribution), "
        "do NOT use nested BIND/IF over the full dataset — it will time out. "
        "Run separate COUNT queries per category instead."
    )

    notes.append(
        "Items can have multiple values for dc:title, dc:creator, dc:subject, "
        "dc:date, dc:language, etc. Use DISTINCT in SELECT."
    )

    notes.append(
        "Never query dc:title or dc:creator directly on the item URI — "
        "they are on the proxy. Always use a proxy pattern."
    )

    return notes


if __name__ == "__main__":
    notes = generate_notes()
    out = Path(__file__).parent / "europeana-notes.json"
    out.write_text(json.dumps(notes, indent=2, ensure_ascii=False) + "\n")
    print(f"Generated {len(notes)} notes → {out}")
