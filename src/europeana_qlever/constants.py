"""Shared constants: EDM namespaces, QLever config, directory layout.

Resource-related constants are prefixed with ``DEFAULT_`` to indicate they
are fallback values — the primary source of truth for resource allocation
is :class:`~europeana_qlever.resources.ResourceBudget`, which computes
values dynamically from detected system resources.
"""

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
QLEVER_QUERY_TIMEOUT = 3600  # Per-query timeout in seconds (1 hour)

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
# Rights URI classification
# ---------------------------------------------------------------------------
OPEN_RIGHTS_URIS: list[str] = [
    "http://creativecommons.org/publicdomain/zero/1.0/",
    "http://creativecommons.org/publicdomain/mark/1.0/",
    "http://creativecommons.org/licenses/by/4.0/",
    "http://creativecommons.org/licenses/by/3.0/",
    "http://creativecommons.org/licenses/by/2.0/",
    "http://creativecommons.org/licenses/by/1.0/",
    "http://creativecommons.org/licenses/by-sa/4.0/",
    "http://creativecommons.org/licenses/by-sa/3.0/",
    "http://creativecommons.org/licenses/by-sa/2.0/",
    "http://creativecommons.org/licenses/by-sa/1.0/",
]

RESTRICTED_RIGHTS_URIS: list[str] = [
    "http://creativecommons.org/licenses/by-nc/4.0/",
    "http://creativecommons.org/licenses/by-nc/3.0/",
    "http://creativecommons.org/licenses/by-nd/4.0/",
    "http://creativecommons.org/licenses/by-nd/3.0/",
    "http://creativecommons.org/licenses/by-nc-sa/4.0/",
    "http://creativecommons.org/licenses/by-nc-sa/3.0/",
    "http://creativecommons.org/licenses/by-nc-nd/4.0/",
    "http://creativecommons.org/licenses/by-nc-nd/3.0/",
    "http://rightsstatements.org/vocab/NoC-NC/1.0/",
    "http://rightsstatements.org/vocab/NoC-OKLR/1.0/",
    "http://rightsstatements.org/vocab/InC-EDU/1.0/",
]

PERMISSION_RIGHTS_URIS: list[str] = [
    "http://rightsstatements.org/vocab/InC/1.0/",
    "http://rightsstatements.org/vocab/InC-OW-EU/1.0/",
    "http://rightsstatements.org/vocab/CNE/1.0/",
]

RIGHTS_LABELS: dict[str, str] = {
    "http://creativecommons.org/publicdomain/zero/1.0/": "CC0",
    "http://creativecommons.org/publicdomain/mark/1.0/": "Public Domain Mark",
    "http://creativecommons.org/licenses/by/4.0/": "CC BY 4.0",
    "http://creativecommons.org/licenses/by-sa/4.0/": "CC BY-SA 4.0",
    "http://creativecommons.org/licenses/by-nc/4.0/": "CC BY-NC 4.0",
    "http://creativecommons.org/licenses/by-nd/4.0/": "CC BY-ND 4.0",
    "http://creativecommons.org/licenses/by-nc-sa/4.0/": "CC BY-NC-SA 4.0",
    "http://creativecommons.org/licenses/by-nc-nd/4.0/": "CC BY-NC-ND 4.0",
    "http://rightsstatements.org/vocab/InC/1.0/": "In Copyright",
    "http://rightsstatements.org/vocab/InC-EDU/1.0/": "In Copyright - Educational",
    "http://rightsstatements.org/vocab/InC-OW-EU/1.0/": "EU Orphan Work",
    "http://rightsstatements.org/vocab/NoC-NC/1.0/": "No Copyright - Non-Commercial",
    "http://rightsstatements.org/vocab/NoC-OKLR/1.0/": "No Copyright - Other Restrictions",
    "http://rightsstatements.org/vocab/CNE/1.0/": "Copyright Not Evaluated",
}

SEPARATOR = " ||| "

# Language resolution strategy:
# - Item properties: English + vernacular (from dc:language) queried in parallel,
#   plus optional user-specified extras, with a wildcard fallback.
# - Entity labels: English + optional extras + wildcard fallback.
# Users add languages via QueryBuilder(languages=[...]) or --language CLI options.

# ---------------------------------------------------------------------------
# Fallback defaults for resource monitoring
#
# These are used when ResourceBudget is not available (e.g., direct function
# calls without CLI context). The primary source of truth is ResourceBudget.
# ---------------------------------------------------------------------------
DEFAULT_MONITOR_INTERVAL_SECONDS = 2.0
DEFAULT_MONITOR_INTERVAL_ACTIVE_SECONDS = 1.0
DEFAULT_MONITOR_WARN_MEMORY_PCT = 80.0
DEFAULT_MONITOR_CRITICAL_MEMORY_PCT = 90.0

# Adaptive throttle defaults (CPU-aware concurrency control)
DEFAULT_CPU_TARGET_PCT = 85.0  # scale down above this
DEFAULT_CPU_LOW_PCT = 65.0  # scale up below this
DEFAULT_THROTTLE_CONSECUTIVE_SAMPLES = 3
DEFAULT_THROTTLE_STEP_DOWN = 2
DEFAULT_THROTTLE_STEP_UP = 2

# ---------------------------------------------------------------------------
# Fallback defaults for merge I/O
# ---------------------------------------------------------------------------
DEFAULT_BULK_READ_SIZE = 262_144  # 256 KB
DEFAULT_COPY_BUF_SIZE = 8_388_608  # 8 MB

# ---------------------------------------------------------------------------
# Fallback defaults for pipeline state and logging
# ---------------------------------------------------------------------------
STATE_FILENAME = "pipeline_state.json"
LOG_FILENAME = "pipeline.log"
DEFAULT_LOG_MAX_BYTES = 50_000_000  # 50 MB
DEFAULT_LOG_BACKUP_COUNT = 3
DEFAULT_EXPORT_MAX_RETRIES = 2
DEFAULT_EXPORT_RETRY_DELAYS = (5, 15)  # seconds between retry attempts

# ---------------------------------------------------------------------------
# QLever index settings (JSON blob for the Qleverfile)
#
# Note: num-triples-per-batch is NOT included here — it is injected
# dynamically by cli.py from ResourceBudget.qlever_triples_per_batch().
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
}
