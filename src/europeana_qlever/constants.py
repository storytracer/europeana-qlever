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
ANALYSIS_SUBDIR = "analysis"

# ---------------------------------------------------------------------------
# QLever defaults
# ---------------------------------------------------------------------------
QLEVER_PORT = 7001
QLEVER_UI_PORT = 7000
QLEVER_QUERY_TIMEOUT = 3600  # Per-query timeout in seconds (1 hour)
EUROPEANA_PROXY_URI_PREFIX = "http://data.europeana.eu/proxy/europeana/"

# Access token for QLever privileged operations (materialized views, updates)
QLEVER_ACCESS_TOKEN = "europeana-qlever"

# Materialized view names (QLever ≥ 0.5.37)
VIEW_OPEN_ITEMS = "open-items"

# Language resolution strategy:
# - Entity labels (agents, concepts): English preferred, fallback to any available.
# - Item titles/descriptions: exported as LIST<STRUCT<value, lang>> with all languages.
# - The --language CLI flag filters items by dc:language (SPARQL FILTER), not label resolution.

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
