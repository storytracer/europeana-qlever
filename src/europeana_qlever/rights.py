"""Authoritative registry of Europeana-accepted rights statement URIs.

Generates all valid Creative Commons license/public-domain URIs from the
Europeana spec, plus RightsStatements.org entries. Each URI is paired with
an SPDX-style identifier and a reuse level ("open", "restricted", "prohibited").

SPDX identifiers are validated against the ``license-expression`` package's
SPDX symbol catalog where possible; ported CC variants not in the SPDX list
use the same naming convention (e.g. ``CC-BY-SA-3.0-AU``).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from license_expression import Licensing

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RightsStatement:
    uri: str
    identifier: str
    reuse_level: str  # "open", "restricted", or "prohibited"


REUSE_LEVELS: list[str] = ["open", "restricted", "prohibited"]

# ---------------------------------------------------------------------------
# CC URI generation data — from the Europeana spec
# ---------------------------------------------------------------------------

# License properties common to all versions (except v1.0 swap, handled below).
_CC_PROPERTIES: list[str] = [
    "by", "by-sa", "by-nd", "by-nc", "by-nc-sa", "by-nc-nd",
]

# v1.0 used "by-nd-nc" instead of "by-nc-nd".
_CC_V1_PROPERTIES: list[str] = [
    "by", "by-sa", "by-nd", "by-nc", "by-nc-sa", "by-nd-nc",
]

# Version → accepted ports (None = generic / unported).
_VERSION_PORTS: dict[str, list[str | None]] = {
    "1.0": [None, "fi", "il", "nl"],
    "2.0": [
        None, "au", "at", "be", "br", "ca", "cl", "hr", "uk",
        "fr", "de", "it", "jp", "nl", "pl", "kr", "es", "tw",
    ],
    "2.1": ["au", "es", "jp"],
    "2.5": [
        None, "ar", "au", "br", "bg", "ca", "cn", "co", "hr", "dk",
        "hu", "in", "il", "it", "mk", "my", "mt", "mx", "nl", "pe",
        "pl", "pt", "scotland", "si", "za", "es", "se", "ch", "tw",
    ],
    "3.0": [
        None, "au", "at", "br", "cl", "cn", "cr", "hr", "cz", "ec",
        "eg", "ee", "fr", "de", "gr", "gt", "hk", "igo", "ie", "it",
        "lu", "nl", "nz", "no", "ph", "pl", "pt", "pr", "ro", "rs",
        "sg", "za", "es", "ch", "tw", "th", "ug", "us", "ve", "vn",
    ],
    "4.0": [None],
}

# Maps URI license-properties segment → canonical SPDX component.
# Notably, v1.0's "by-nd-nc" maps to the standard "BY-NC-ND" ordering.
_PROPERTY_TO_SPDX: dict[str, str] = {
    "by": "BY",
    "by-sa": "BY-SA",
    "by-nd": "BY-ND",
    "by-nc": "BY-NC",
    "by-nc-sa": "BY-NC-SA",
    "by-nc-nd": "BY-NC-ND",
    "by-nd-nc": "BY-NC-ND",
}

# Open license properties (all versions/ports are "open").
_OPEN_PROPERTIES: frozenset[str] = frozenset({"by", "by-sa"})

# ---------------------------------------------------------------------------
# RightsStatements.org — static entries
# ---------------------------------------------------------------------------

_RIGHTSSTATEMENTS: list[tuple[str, str, str]] = [
    # (URI suffix after vocab/, identifier, reuse_level)
    ("NoC-NC/1.0/",    "NoC-NC-1.0",    "restricted"),
    ("NoC-OKLR/1.0/",  "NoC-OKLR-1.0",  "restricted"),
    ("InC/1.0/",       "InC-1.0",       "prohibited"),
    ("InC-EDU/1.0/",   "InC-EDU-1.0",   "restricted"),
    ("InC-OW-EU/1.0/", "InC-OW-EU-1.0", "prohibited"),
    ("CNE/1.0/",       "CNE-1.0",       "prohibited"),
    ("NKC/1.0/",       "NKC-1.0",       "prohibited"),
    ("UND/1.0/",       "UND-1.0",       "prohibited"),
]

_RS_BASE = "http://rightsstatements.org/vocab/"

# ---------------------------------------------------------------------------
# SPDX identifier helpers
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _spdx_symbols() -> dict[str, str]:
    """Load SPDX symbol keys from license-expression, keyed by uppercase."""
    from license_expression import get_spdx_licensing

    licensing: Licensing = get_spdx_licensing()
    return {k.upper(): k for k in licensing.known_symbols}


def _cc_license_identifier(properties: str, version: str, port: str | None) -> str:
    """Build an SPDX-style identifier for a CC license URI."""
    spdx_prop = _PROPERTY_TO_SPDX[properties]
    parts = ["CC", spdx_prop, version]
    if port is not None:
        parts.append(port.upper())
    candidate = "-".join(parts)

    # Check against canonical SPDX symbols
    symbols = _spdx_symbols()
    canonical = symbols.get(candidate.upper())
    return canonical if canonical is not None else candidate


def _cc_publicdomain_identifier(tool: str) -> str:
    """Return the SPDX identifier for a CC public domain tool."""
    if tool == "zero":
        return "CC0-1.0"
    if tool == "mark":
        return "CC-PDDC"
    raise ValueError(f"Unknown public domain tool: {tool}")


# ---------------------------------------------------------------------------
# Registry construction
# ---------------------------------------------------------------------------


def _build_registry() -> dict[str, RightsStatement]:
    """Build the complete rights statement registry."""
    registry: dict[str, RightsStatement] = {}

    # --- CC licenses ---
    for version, ports in _VERSION_PORTS.items():
        properties_list = _CC_V1_PROPERTIES if version == "1.0" else _CC_PROPERTIES
        for properties in properties_list:
            for port in ports:
                if port is None:
                    uri = f"http://creativecommons.org/licenses/{properties}/{version}/"
                else:
                    uri = f"http://creativecommons.org/licenses/{properties}/{version}/{port}/"

                # Reuse level: normalise v1.0's by-nd-nc to canonical form
                canonical = properties if properties != "by-nd-nc" else "by-nc-nd"
                reuse_level = "open" if canonical in ("by", "by-sa") else "restricted"

                identifier = _cc_license_identifier(properties, version, port)
                registry[uri] = RightsStatement(uri, identifier, reuse_level)

    # --- CC public domain tools ---
    for tool in ("zero", "mark"):
        uri = f"http://creativecommons.org/publicdomain/{tool}/1.0/"
        identifier = _cc_publicdomain_identifier(tool)
        registry[uri] = RightsStatement(uri, identifier, "open")

    # --- RightsStatements.org ---
    for suffix, identifier, reuse_level in _RIGHTSSTATEMENTS:
        uri = f"{_RS_BASE}{suffix}"
        registry[uri] = RightsStatement(uri, identifier, reuse_level)

    return registry


# Module-level singleton — built once on first import.
RIGHTS_REGISTRY: dict[str, RightsStatement] = _build_registry()

# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------


def uris_for_reuse_level(level: str) -> list[str]:
    """Return all URIs classified at the given reuse level."""
    if level not in REUSE_LEVELS:
        raise ValueError(f"Unknown reuse level {level!r}; valid: {REUSE_LEVELS}")
    return [rs.uri for rs in RIGHTS_REGISTRY.values() if rs.reuse_level == level]


def identifier_for_uri(uri: str) -> str:
    """Return the SPDX-style identifier for a rights URI, or 'Other' if unknown."""
    rs = RIGHTS_REGISTRY.get(uri)
    return rs.identifier if rs is not None else "Other"


def reuse_level_for_uri(uri: str) -> str:
    """Return the reuse level for a rights URI, or 'prohibited' if unknown."""
    rs = RIGHTS_REGISTRY.get(uri)
    return rs.reuse_level if rs is not None else "prohibited"


def generic_rights() -> list[RightsStatement]:
    """Return only unported/generic CC URIs plus all RightsStatements.org entries.

    Useful for SPARQL BINDs where enumerating all ~600 URIs is impractical.
    """
    result: list[RightsStatement] = []
    for rs in RIGHTS_REGISTRY.values():
        uri = rs.uri
        if uri.startswith(_RS_BASE):
            result.append(rs)
        elif uri.startswith("http://creativecommons.org/publicdomain/"):
            result.append(rs)
        elif uri.startswith("http://creativecommons.org/licenses/"):
            # Generic = exactly 6 slashes (scheme + empty + domain + licenses + props + version + trailing)
            # e.g. http://creativecommons.org/licenses/by/4.0/ has 6 slashes
            # Ported adds one more: .../by/4.0/au/ has 7 slashes
            if uri.count("/") == 6:
                result.append(rs)
    return result
