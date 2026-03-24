"""Shared constants: EDM namespaces, QLever config, directory layout."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Subdirectory names within the work directory
# ---------------------------------------------------------------------------
MERGED_SUBDIR = "ttl-merged"
INDEX_SUBDIR = "index"
EXPORTS_SUBDIR = "exports"

# ---------------------------------------------------------------------------
# QLever defaults
# ---------------------------------------------------------------------------
QLEVER_PORT = 7001
QLEVER_UI_PORT = 7000

# ---------------------------------------------------------------------------
# EDM namespaces — canonical set from the Europeana bulk dumps
# ---------------------------------------------------------------------------
EDM_PREFIXES: dict[str, str] = {
    "cc": "http://creativecommons.org/ns#",
    "dcat": "http://www.w3.org/ns/dcat#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "doap": "http://usefulinc.com/ns/doap#",
    "dqv": "http://www.w3.org/ns/dqv#",
    "ebucore": "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#",
    "edm": "http://www.europeana.eu/schemas/edm/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "odrl": "http://www.w3.org/ns/odrl/2/",
    "ore": "http://www.openarchives.org/ore/terms/",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "rdaGr2": "http://rdvocab.info/ElementsGr2/",
    "schema": "http://schema.org/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "svcs": "http://rdfs.org/sioc/services#",
    "wgs84_pos": "http://www.w3.org/2003/01/geo/wgs84_pos#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}

# ---------------------------------------------------------------------------
# QLever index settings (JSON blob for the Qleverfile)
# ---------------------------------------------------------------------------
QLEVER_INDEX_SETTINGS = {
    "languages-internal": [],
    "prefixes-external": [
        "<http://data.europeana.eu/proxy/",
        "<http://data.europeana.eu/aggregation/",
        "<http://data.europeana.eu/item/",
    ],
    "locale": {
        "language": "en",
        "country": "US",
        "ignore-punctuation": True,
    },
    "ascii-prefixes-only": False,
    "num-triples-per-batch": 5_000_000,
}
