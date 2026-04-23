"""Authoritative registry of Europeana-accepted rights statement URIs.

Generates all valid Creative Commons license/public-domain URIs from the
Europeana spec, plus RightsStatements.org entries.  Each URI is paired with
a short identifier (extracted from the URI path) and a reuse level
("open", "restricted", "prohibited").

The classification rules are defined once and exposed as both Python
look-ups and SPARQL fragment generators so that ``query.py`` never
duplicates them.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

REUSE_LEVELS: list[str] = ["open", "restricted", "prohibited"]


@dataclass(frozen=True)
class RightsStatement:
    uri: str
    identifier: str
    reuse_level: str  # "open" | "restricted" | "prohibited"


# ---------------------------------------------------------------------------
# URI prefixes — used for both Python classification and SPARQL generation
# ---------------------------------------------------------------------------

_CC_LICENSE_PREFIX = "http://creativecommons.org/licenses/"
_CC_PD_PREFIX = "http://creativecommons.org/publicdomain/"
_RS_BASE = "http://rightsstatements.org/vocab/"

# CC license properties whose URIs are classified "open".
_OPEN_CC_PREFIXES = (
    f"{_CC_LICENSE_PREFIX}by/",
    f"{_CC_LICENSE_PREFIX}by-sa/",
)

# RightsStatements.org URIs classified "restricted".
_RESTRICTED_RS_URIS = (
    f"{_RS_BASE}NoC-NC/1.0/",
    f"{_RS_BASE}NoC-OKLR/1.0/",
    f"{_RS_BASE}InC-EDU/1.0/",
)

# RightsStatements.org URIs classified "prohibited".
_PROHIBITED_RS_URIS = (
    f"{_RS_BASE}InC/1.0/",
    f"{_RS_BASE}InC-OW-EU/1.0/",
    f"{_RS_BASE}CNE/1.0/",
    f"{_RS_BASE}NKC/1.0/",
    f"{_RS_BASE}UND/1.0/",
)

# ---------------------------------------------------------------------------
# CC URI generation data — from the Europeana spec
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Identifier extraction — mechanical transformation of URI path segments
# ---------------------------------------------------------------------------


def _identifier_from_uri(uri: str) -> str:
    """Extract a short identifier from a rights URI.

    CC licenses:      ``.../licenses/by-sa/3.0/au/`` → ``CC-BY-SA-3.0-AU``
    CC public domain: ``.../publicdomain/zero/1.0/``  → ``CC-PD-ZERO-1.0``
    RightsStatements: ``.../vocab/InC/1.0/``          → ``InC-1.0``
    """
    for prefix, id_prefix in (
        (_CC_LICENSE_PREFIX, "CC-"),
        (_CC_PD_PREFIX, "CC-PD-"),
        (_RS_BASE, ""),
    ):
        if uri.startswith(prefix):
            tail = uri[len(prefix):].rstrip("/")
            parts = tail.split("/")
            if prefix == _RS_BASE:
                return "-".join(parts)
            return id_prefix + "-".join(p.upper() for p in parts)
    return "Other"


# ---------------------------------------------------------------------------
# Reuse-level classification — single source of truth
# ---------------------------------------------------------------------------


def _classify(uri: str) -> str:
    """Classify a rights URI into a reuse level."""
    if uri.startswith(_CC_PD_PREFIX):
        return "open"
    if any(uri.startswith(p) for p in _OPEN_CC_PREFIXES):
        return "open"
    if uri.startswith(_CC_LICENSE_PREFIX):
        return "restricted"
    if uri in _RESTRICTED_RS_URIS:
        return "restricted"
    return "prohibited"


# ---------------------------------------------------------------------------
# Registry construction
# ---------------------------------------------------------------------------


def _build_registry() -> dict[str, RightsStatement]:
    """Build the complete rights statement registry."""
    registry: dict[str, RightsStatement] = {}

    # CC licenses
    for version, ports in _VERSION_PORTS.items():
        props = _CC_V1_PROPERTIES if version == "1.0" else _CC_PROPERTIES
        for prop in props:
            for port in ports:
                if port is None:
                    uri = f"{_CC_LICENSE_PREFIX}{prop}/{version}/"
                else:
                    uri = f"{_CC_LICENSE_PREFIX}{prop}/{version}/{port}/"
                registry[uri] = RightsStatement(uri, _identifier_from_uri(uri), _classify(uri))

    # CC public domain tools
    for tool in ("zero", "mark"):
        uri = f"{_CC_PD_PREFIX}{tool}/1.0/"
        registry[uri] = RightsStatement(uri, _identifier_from_uri(uri), _classify(uri))

    # RightsStatements.org
    for rs_uri in _RESTRICTED_RS_URIS + _PROHIBITED_RS_URIS:
        registry[rs_uri] = RightsStatement(rs_uri, _identifier_from_uri(rs_uri), _classify(rs_uri))

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
    """Return the short identifier for a rights URI, or 'Other' if unknown."""
    rs = RIGHTS_REGISTRY.get(uri)
    return rs.identifier if rs is not None else "Other"


def reuse_level_for_uri(uri: str) -> str:
    """Return the reuse level for a rights URI, or 'prohibited' if unknown."""
    rs = RIGHTS_REGISTRY.get(uri)
    return rs.reuse_level if rs is not None else "prohibited"


def generic_rights() -> list[RightsStatement]:
    """Return only unported/generic CC URIs plus all RightsStatements.org entries.

    Useful for SPARQL BINDs where enumerating all ~580 URIs is impractical.
    A generic CC URI has no port segment, i.e. exactly 6 slashes.
    """
    return [
        rs for rs in RIGHTS_REGISTRY.values()
        if not rs.uri.startswith(_CC_LICENSE_PREFIX) or rs.uri.count("/") == 6
    ]


# ---------------------------------------------------------------------------
# SPARQL fragment generators
#
# These translate the classification rules into SPARQL expressions so
# that query.py doesn't have to hard-code URI patterns.
# ---------------------------------------------------------------------------


def sparql_reuse_level_bind(rights_var: str = "?rights", out_var: str = "?reuse_level") -> str:
    """SPARQL BIND that classifies a rights URI into a reuse level."""
    rv = f"STR({rights_var})"
    open_cond = _sparql_open_condition(rv)
    restricted_cond = _sparql_restricted_condition(rv)
    return textwrap.dedent(f"""\
        BIND(
          IF({open_cond}, "open",
          IF({restricted_cond}, "restricted",
             "prohibited"))
          AS {out_var}
        )""")


def sparql_reuse_level_filter(level: str, rights_var: str = "?rights") -> str:
    """SPARQL FILTER that selects URIs matching a single reuse level."""
    rv = f"STR({rights_var})"
    if level == "open":
        return f"FILTER({_sparql_open_condition(rv)})"
    if level == "restricted":
        return f"FILTER({_sparql_restricted_condition(rv)})"
    # prohibited = NOT open AND NOT restricted
    return f"FILTER(!({_sparql_open_condition(rv)}) && !({_sparql_restricted_condition(rv)}))"


def sparql_identifier_bind(rights_var: str = "?rights", out_var: str = "?rights_id") -> str:
    """SPARQL BIND that maps generic/unported rights URIs to short identifiers."""
    entries = generic_rights()
    expr = '"Other"'
    for rs in reversed(entries):
        expr = f'IF(STR({rights_var}) = "{rs.uri}", "{rs.identifier}", {expr})'
    return f"BIND({expr} AS {out_var})"


# -- shared SPARQL condition fragments ------------------------------------

def _sparql_open_condition(rv: str) -> str:
    """SPARQL boolean expression that is true for "open" rights URIs."""
    prefixes = [_CC_PD_PREFIX] + list(_OPEN_CC_PREFIXES)
    return " || ".join(f'STRSTARTS({rv}, "{p}")' for p in prefixes)


def _sparql_restricted_condition(rv: str) -> str:
    """SPARQL boolean expression that is true for "restricted" rights URIs."""
    # CC licenses containing -nc or -nd in the URI path
    cc = 'CONTAINS({rv}, "-nc") || CONTAINS({rv}, "-nd")'.format(rv=rv)
    # RightsStatements.org restricted entries
    rs = " || ".join(f'{rv} = "{u}"' for u in _RESTRICTED_RS_URIS)
    return f"{cc} || {rs}"


# ---------------------------------------------------------------------------
# Rights family classification — for map_rights.x_family / group_items.x_rights_family
# ---------------------------------------------------------------------------

# Order matters: more specific patterns first. Classifier returns the family
# for the first matching rule.  Each entry is (match_kind, pattern, family)
# where match_kind is "prefix" or "exact".
_FAMILY_RULES: list[tuple[str, str, str]] = [
    ("prefix", f"{_CC_PD_PREFIX}zero/", "cc0"),
    ("prefix", f"{_CC_PD_PREFIX}mark/", "pdm"),
    ("prefix", f"{_CC_LICENSE_PREFIX}by-nc-nd/", "cc-by-nc-nd"),
    ("prefix", f"{_CC_LICENSE_PREFIX}by-nd-nc/", "cc-by-nc-nd"),
    ("prefix", f"{_CC_LICENSE_PREFIX}by-nc-sa/", "cc-by-nc-sa"),
    ("prefix", f"{_CC_LICENSE_PREFIX}by-nc/", "cc-by-nc"),
    ("prefix", f"{_CC_LICENSE_PREFIX}by-nd/", "cc-by-nd"),
    ("prefix", f"{_CC_LICENSE_PREFIX}by-sa/", "cc-by-sa"),
    ("prefix", f"{_CC_LICENSE_PREFIX}by/", "cc-by"),
    ("exact", f"{_RS_BASE}InC/1.0/", "rs-inc"),
    ("exact", f"{_RS_BASE}InC-EDU/1.0/", "rs-inc"),
    ("exact", f"{_RS_BASE}InC-OW-EU/1.0/", "rs-inc"),
    ("exact", f"{_RS_BASE}NoC-NC/1.0/", "rs-noc"),
    ("exact", f"{_RS_BASE}NoC-OKLR/1.0/", "rs-noc"),
    ("exact", f"{_RS_BASE}CNE/1.0/", "cnb"),
    ("exact", f"{_RS_BASE}NKC/1.0/", "rs-other"),
    ("exact", f"{_RS_BASE}UND/1.0/", "rs-other"),
    ("prefix", _RS_BASE, "rs-other"),
]  # type: ignore[list-item]

_LABEL_BASE: dict[str, str] = {
    "cc0": "Public Domain Dedication (CC0)",
    "pdm": "Public Domain Mark",
    "cc-by": "Attribution (CC BY)",
    "cc-by-sa": "Attribution-ShareAlike (CC BY-SA)",
    "cc-by-nd": "Attribution-NoDerivs (CC BY-ND)",
    "cc-by-nc": "Attribution-NonCommercial (CC BY-NC)",
    "cc-by-nc-sa": "Attribution-NonCommercial-ShareAlike (CC BY-NC-SA)",
    "cc-by-nc-nd": "Attribution-NonCommercial-NoDerivs (CC BY-NC-ND)",
    "rs-inc": "In Copyright (RightsStatements.org)",
    "rs-noc": "No Copyright — Non-Commercial Use Only (RightsStatements.org)",
    "rs-other": "RightsStatements.org (other)",
    "cnb": "Copyright Not Evaluated / Non-Commercial Basis",
    "orphan": "Orphan Work",
    "unknown": "Unknown",
}


def family_for_uri(uri: str) -> str:
    """Classify a rights URI into a family code (cc0, cc-by, rs-inc, etc.)."""
    if not uri:
        return "unknown"
    for kind, pattern, fam in _FAMILY_RULES:
        if kind == "prefix" and uri.startswith(pattern):
            return fam
        if kind == "exact" and uri == pattern:
            return fam
    return "unknown"


def label_for_uri(uri: str) -> str:
    """Return a human-readable label for a rights URI."""
    fam = family_for_uri(uri)
    base = _LABEL_BASE.get(fam, _LABEL_BASE["unknown"])
    # Try to append the version (e.g. "4.0", "3.0 IT") for CC licenses.
    if uri.startswith(_CC_LICENSE_PREFIX):
        tail = uri[len(_CC_LICENSE_PREFIX):].rstrip("/")
        parts = tail.split("/")
        if len(parts) >= 2:
            version = parts[1]
            port = parts[2].upper() if len(parts) >= 3 else ""
            suffix = f" {version}"
            if port:
                suffix += f" ({port})"
            return base + suffix
    if uri.startswith(_CC_PD_PREFIX):
        tail = uri[len(_CC_PD_PREFIX):].rstrip("/")
        parts = tail.split("/")
        if len(parts) >= 2:
            return base + f" {parts[1]}"
    return base


# ---------------------------------------------------------------------------
# DuckDB CASE expression generators for family / label / is_open
# ---------------------------------------------------------------------------


def _sql_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def duckdb_family_case(rights_column: str = "v_edm_rights") -> str:
    """Generate a DuckDB CASE expression that classifies a rights URI → family."""
    lines: list[str] = []
    for kind, pattern, fam in _FAMILY_RULES:
        if kind == "prefix":
            lines.append(
                f"    WHEN STARTS_WITH({rights_column}, {_sql_quote(pattern)}) THEN {_sql_quote(fam)}"
            )
        else:
            lines.append(
                f"    WHEN {rights_column} = {_sql_quote(pattern)} THEN {_sql_quote(fam)}"
            )
    body = "\n".join(lines)
    return f"CASE\n{body}\n    ELSE 'unknown'\n  END"


def duckdb_is_open_case(rights_column: str = "v_edm_rights") -> str:
    """Generate a DuckDB boolean expression that is true for 'open' rights URIs."""
    opens = [_CC_PD_PREFIX] + list(_OPEN_CC_PREFIXES)
    parts = [
        f"STARTS_WITH({rights_column}, {_sql_quote(p)})" for p in opens
    ]
    return "(" + " OR ".join(parts) + ")"


def duckdb_label_case(rights_column: str = "v_edm_rights") -> str:
    """Generate a DuckDB CASE that resolves a rights URI to a short label.

    For variant-heavy families (CC licenses), the label is computed from
    the URI itself (family base + version + port) rather than enumerating
    every one of ~580 URIs.  For fixed RightsStatements.org URIs the
    label is resolved exactly.
    """
    lines: list[str] = []
    # Exact-match RightsStatements.org URIs — known labels.
    for kind, pattern, fam in _FAMILY_RULES:
        if kind != "exact":
            continue
        label = label_for_uri(pattern)
        lines.append(
            f"    WHEN {rights_column} = {_sql_quote(pattern)} THEN {_sql_quote(label)}"
        )
    # CC0
    lines.append(
        f"    WHEN STARTS_WITH({rights_column}, {_sql_quote(_CC_PD_PREFIX + 'zero/')}) "
        f"THEN 'Public Domain Dedication (CC0)'"
    )
    lines.append(
        f"    WHEN STARTS_WITH({rights_column}, {_sql_quote(_CC_PD_PREFIX + 'mark/')}) "
        f"THEN 'Public Domain Mark'"
    )
    # CC licenses — build label from family base + version from URI path
    cc_families = [
        ("by-nc-nd", "Attribution-NonCommercial-NoDerivs (CC BY-NC-ND)"),
        ("by-nd-nc", "Attribution-NonCommercial-NoDerivs (CC BY-NC-ND)"),
        ("by-nc-sa", "Attribution-NonCommercial-ShareAlike (CC BY-NC-SA)"),
        ("by-nc",    "Attribution-NonCommercial (CC BY-NC)"),
        ("by-nd",    "Attribution-NoDerivs (CC BY-ND)"),
        ("by-sa",    "Attribution-ShareAlike (CC BY-SA)"),
        ("by",       "Attribution (CC BY)"),
    ]
    for sub, label in cc_families:
        prefix = _CC_LICENSE_PREFIX + sub + "/"
        lines.append(
            f"    WHEN STARTS_WITH({rights_column}, {_sql_quote(prefix)}) "
            f"THEN {_sql_quote(label)}"
        )
    body = "\n".join(lines)
    return f"CASE\n{body}\n    ELSE 'Unknown'\n  END"
