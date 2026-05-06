"""Schema loader — programmatic access to the EDM Parquet LinkML schema.

Provides a cached :class:`~linkml_runtime.utils.schemaview.SchemaView`
singleton and convenience accessors for prefixes, table definitions,
SPARQL generation helpers, PyArrow schemas, and rights / authority
classification SQL.

All table names, column names, SPARQL patterns, and pipeline metadata
are derived from ``schema/edm_parquet.yaml`` — nothing is hardcoded here.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from pathlib import Path

from linkml_runtime.utils.schemaview import SchemaView


# ---------------------------------------------------------------------------
# Schema location
# ---------------------------------------------------------------------------

_SCHEMA_PATH = Path(__file__).parent / "schema" / "edm_parquet.yaml"


# ---------------------------------------------------------------------------
# Cached SchemaView singleton
# ---------------------------------------------------------------------------


@functools.cache
def schema_view() -> SchemaView:
    """Return a cached :class:`SchemaView` over the EDM Parquet schema."""
    return SchemaView(str(_SCHEMA_PATH))


# ---------------------------------------------------------------------------
# Prefix helpers
# ---------------------------------------------------------------------------

_INTERNAL_PREFIXES = frozenset({"linkml", "edm_parquet"})


@functools.cache
def prefixes() -> dict[str, str]:
    """Return EDM namespace prefix → URI mapping from the schema."""
    sv = schema_view()
    return {
        p.prefix_prefix: p.prefix_reference
        for p in sv.schema.prefixes.values()
        if p.prefix_prefix not in _INTERNAL_PREFIXES
    }


# ---------------------------------------------------------------------------
# Attribute info
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttributeInfo:
    """Condensed metadata for a single class attribute."""

    name: str
    slot_uri: str | None
    range: str | None
    multivalued: bool
    required: bool
    identifier: bool
    description: str | None = None
    annotations: dict[str, str] = field(default_factory=dict)


def _annots(obj: object) -> dict[str, str]:
    """Extract annotation key→value dict from a LinkML element."""
    raw = getattr(obj, "annotations", None) or {}
    return {
        k: (v.value if hasattr(v, "value") else str(v))
        for k, v in raw.items()
    }


def _expand_uri(curie: str | None) -> str | None:
    """Expand a CURIE like ``dc:title`` to a full URI."""
    if curie is None:
        return None
    pfx = prefixes()
    if ":" in curie:
        prefix, local = curie.split(":", 1)
        if prefix in pfx:
            return pfx[prefix] + local
    return curie


def compact_uri(full_uri: str) -> str | None:
    """Compact a full URI to a CURIE, or ``None`` if no prefix matches."""
    pfx = prefixes()
    for prefix, ns in pfx.items():
        if full_uri.startswith(ns):
            return f"{prefix}:{full_uri[len(ns):]}"
    return None


def prefix_of(full_uri: str) -> str | None:
    """Return the prefix key for a full URI (e.g. ``'dc'`` for dc:title)."""
    pfx = prefixes()
    for prefix, ns in pfx.items():
        if full_uri.startswith(ns):
            return prefix
    return None


# ---------------------------------------------------------------------------
# Class attribute accessors
# ---------------------------------------------------------------------------


@functools.cache
def class_attributes(cls_name: str) -> dict[str, AttributeInfo]:
    """Return all attributes for a schema class as :class:`AttributeInfo` dicts."""
    sv = schema_view()
    cls = sv.get_class(cls_name)
    if cls is None:
        raise ValueError(f"Unknown schema class: {cls_name!r}")
    result: dict[str, AttributeInfo] = {}
    for attr_name, attr in cls.attributes.items():
        result[attr_name] = AttributeInfo(
            name=attr_name,
            slot_uri=attr.slot_uri,
            range=attr.range,
            multivalued=bool(attr.multivalued),
            required=bool(attr.required),
            identifier=bool(attr.identifier),
            description=attr.description or None,
            annotations=_annots(attr),
        )
    return result


def group_fields() -> dict[str, AttributeInfo]:
    """All GroupItems class attributes (the ``group_items`` schema)."""
    return class_attributes("GroupItems")


# ---------------------------------------------------------------------------
# Export class discovery
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExportClassInfo:
    """Metadata for a single export discovered from schema annotations."""

    cls_name: str
    table_name: str
    export_type: str  # "values", "links", "links_scan", "merged", "group", "map"
    export_sets: list[str]
    class_uri: str | None
    attributes: dict[str, AttributeInfo]
    annotations: dict[str, str]


def _parse_csv(value: str) -> list[str]:
    return [s.strip() for s in (value or "").replace("\n", " ").split(",") if s.strip()]


@functools.cache
def _discovered_export_classes() -> dict[str, ExportClassInfo]:
    """Discover all export classes from the LinkML schema (finals only)."""
    sv = schema_view()
    result: dict[str, ExportClassInfo] = {}
    for cls_name in sv.all_classes():
        cls = sv.get_class(cls_name)
        annots = _annots(cls)
        et = annots.get("export_type", "")
        if not et:
            continue
        table_name = annots.get("table_name", "")
        if not table_name:
            continue
        sets = _parse_csv(annots.get("export_sets", ""))
        attrs = class_attributes(cls_name)
        result[table_name] = ExportClassInfo(
            cls_name=cls_name,
            table_name=table_name,
            export_type=et,
            export_sets=sets,
            class_uri=cls.class_uri,
            attributes=attrs,
            annotations=annots,
        )
    return result


def export_classes() -> dict[str, ExportClassInfo]:
    """Return all *final* export classes (keyed by table name).

    Does NOT include synthetic links_scan intermediates.  Use
    :func:`links_scan_entries` to enumerate those.
    """
    return dict(_discovered_export_classes())


@dataclass(frozen=True)
class LinkScanEntry:
    """Metadata for one synthetic per-property links_scan export.

    A ``links`` table (like ``links_ore_Proxy``) has many link
    properties; each becomes its own per-property SPARQL scan, written
    to a Hive-partitioned directory (``<table>/x_property=<col>/data.parquet``)
    with the same 5-column shape. Readers see the directory as one
    logical table via DuckDB's ``hive_partitioning=true``.
    """

    parent_table: str           # e.g. "links_ore_Proxy"
    scan_name: str              # e.g. "links_ore_Proxy__dc_subject"
    curie: str                  # e.g. "dc:subject"
    property_uri: str           # full URI
    property_column: str        # e.g. "v_dc_subject" — goes into x_property
    subject_base_pattern: str   # SPARQL pattern that binds ?k_iri
    required_prefixes: list[str]
    sample_subject_variable: str | None = None   # e.g. "_cho" — for sample-items SERVICE injection


def link_properties(table_name: str) -> list[tuple[str, str]]:
    """Return (curie, v_column_name) pairs for a links table."""
    info = export_classes().get(table_name)
    if info is None or info.export_type != "links":
        return []
    raw = info.annotations.get("link_properties", "")
    out: list[tuple[str, str]] = []
    for curie in _parse_csv(raw):
        if ":" not in curie:
            continue
        pfx, local = curie.split(":", 1)
        out.append((curie, f"v_{pfx}_{local}"))
    return out


def links_scan_entries() -> dict[str, LinkScanEntry]:
    """Enumerate all synthetic per-property links_scan exports across all tables."""
    result: dict[str, LinkScanEntry] = {}
    for info in export_classes().values():
        if info.export_type != "links":
            continue
        subject_pattern = info.annotations.get("subject_base_pattern", "").strip()
        required_pfx = _parse_csv(info.annotations.get("required_prefixes", ""))
        sample_var = info.annotations.get("sample_subject_variable", "").strip() or None
        for curie, col in link_properties(info.table_name):
            pfx, local = curie.split(":", 1)
            scan_name = f"{info.table_name}__{pfx}_{local}"
            extra_pfx = set(required_pfx)
            extra_pfx.add(pfx)
            result[scan_name] = LinkScanEntry(
                parent_table=info.table_name,
                scan_name=scan_name,
                curie=curie,
                property_uri=_expand_uri(curie) or curie,
                property_column=col,
                subject_base_pattern=subject_pattern,
                required_prefixes=sorted(extra_pfx),
                sample_subject_variable=sample_var,
            )
    return result


def depends_on(table_name: str) -> list[str]:
    """Return the declared dependencies for an export (empty if none)."""
    info = export_classes().get(table_name)
    if info is None:
        return []
    return _parse_csv(info.annotations.get("depends_on", ""))


@functools.cache
def export_sets() -> dict[str, list[str]]:
    """Build export sets → [table_name] mapping from schema annotations.

    Only final exports are enumerated; the synthetic links_scan
    intermediates are pulled in via dependency resolution at runtime.
    """
    sets: dict[str, list[str]] = {}
    for info in export_classes().values():
        for s in info.export_sets:
            sets.setdefault(s, []).append(info.table_name)
    return {k: sorted(v) for k, v in sets.items()}


def raw_tables() -> list[str]:
    """Return all 30 raw (values_* + links_*) table names."""
    return sorted([
        info.table_name
        for info in export_classes().values()
        if info.export_type in ("values", "links")
    ])


# ---------------------------------------------------------------------------
# Reuse level patterns (preserved from prior schema)
# ---------------------------------------------------------------------------


@functools.cache
def reuse_level_patterns() -> dict[str, list[str]]:
    """Return reuse-level → list of URI prefixes/exact URIs."""
    annots = _annots(schema_view().schema)

    def _split(key: str) -> list[str]:
        return _parse_csv(annots.get(key, ""))

    return {
        "open": _split("reuse_level_open_prefixes"),
        "restricted_prefixes": _split("reuse_level_restricted_prefixes"),
        "restricted_uris": _split("reuse_level_restricted_uris"),
    }


def reuse_level_sql(rights_column: str = "v_edm_rights") -> str:
    """Generate a DuckDB ``CASE/WHEN`` expression for reuse-level classification."""
    patterns = reuse_level_patterns()
    clauses: list[str] = []
    for prefix in patterns["open"]:
        clauses.append(f"WHEN STARTS_WITH({rights_column}, '{prefix}') THEN 'open'")
    for prefix in patterns["restricted_prefixes"]:
        clauses.append(f"WHEN STARTS_WITH({rights_column}, '{prefix}') THEN 'restricted'")
    for uri in patterns["restricted_uris"]:
        clauses.append(f"WHEN {rights_column} = '{uri}' THEN 'restricted'")
    lines = "\n      ".join(clauses)
    return f"CASE\n      {lines}\n      ELSE 'prohibited'\n    END"


# ---------------------------------------------------------------------------
# Authority patterns
# ---------------------------------------------------------------------------


@functools.cache
def metis_vocabularies() -> dict[str, "MetisVocabulary"]:
    """Load Metis vocabulary metadata from references/vocabularies/metis-vocabularies/.

    The Metis enrichment pipeline (europeana/metis-vocabularies) defines
    one YAML metadata file per authoritative vocabulary it dereferences.
    Each file declares the URI ``paths`` Metis recognises plus entity
    types, examples, and content-negotiation hints. We adopt this as the
    source of truth for "is this URI an authority Europeana knows about?".

    Returns a mapping from short name (filename stem) to :class:`MetisVocabulary`.
    """
    import yaml

    root = (
        Path(__file__).resolve().parent.parent.parent
        / "references" / "vocabularies" / "metis-vocabularies" / "vocabularies"
    )
    if not root.is_dir():
        raise RuntimeError(
            f"Metis vocabularies not found at {root}. "
            "Run scripts/update-metis-vocabularies.py to vendor them."
        )

    # Metis splits some vocabularies across multiple YAML files when one
    # logical vocabulary needs different XSL transforms per entity type
    # (e.g. mimo.yml lives under both agent/ and concept/ because MIMO
    # has Agent-typed and Concept-typed entities with different mappings).
    # For URI classification we don't care about the XSL split — they're
    # the same authority — so we merge entries that share a filename stem,
    # taking the union of paths and types and the longest common name
    # prefix as the display name.
    stem_groups: dict[str, list[tuple[Path, dict]]] = {}
    for path in sorted(root.rglob("*.yml")):
        with path.open() as f:
            raw = yaml.safe_load(f)
        if not isinstance(raw, dict) or "paths" not in raw:
            continue
        stem_groups.setdefault(path.stem, []).append((path, raw))

    out: dict[str, MetisVocabulary] = {}
    for name, group in stem_groups.items():
        merged_types: list[str] = []
        merged_paths: list[str] = []
        display_names: list[str] = []
        for _, raw in group:
            display_names.append(str(raw.get("name", name)))
            t = raw.get("types") or []
            if isinstance(t, str):
                t = [t]
            for v in t:
                if v not in merged_types:
                    merged_types.append(v)
            p = raw.get("paths") or []
            if isinstance(p, str):
                p = [p]
            for v in p:
                if v not in merged_paths:
                    merged_paths.append(v)
        out[name] = MetisVocabulary(
            name=name,
            display_name=_common_name(display_names),
            types=tuple(merged_types),
            paths=tuple(merged_paths),
        )
    return out


def _common_name(names: list[str]) -> str:
    """Pick a representative display name from one or more variants.

    For a single name, return it unchanged. For multiple, return the
    longest shared prefix split on " - " (e.g. "MIMO - Persons" and
    "MIMO - General Concepts" → "MIMO"); fall back to the first name
    if no shared prefix exists.
    """
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    parts_per_name = [n.split(" - ") for n in names]
    common: list[str] = []
    for fragments in zip(*parts_per_name):
        if all(f == fragments[0] for f in fragments):
            common.append(fragments[0])
        else:
            break
    return " - ".join(common) if common else names[0]


@dataclass(frozen=True)
class MetisVocabulary:
    """One row from the Metis vocabulary registry."""

    name: str
    display_name: str
    types: tuple[str, ...]
    paths: tuple[str, ...]


def well_formed_sql(value_column: str = "x_value") -> str:
    """Generate a DuckDB BOOLEAN expression for basic LOD-URI hygiene.

    True when the value passes our syntactic checks: HTTP(S) scheme,
    well-formed authority component, no embedded whitespace, no
    obvious template-substitution artefacts (e.g. unexpanded ``$N``
    placeholders left in the IRI).

    This is *not* RFC 3987 IRI grammar — just enough to rule out
    obviously broken values that should never participate in
    authority classification.
    """
    return (
        "("
        f"{value_column} IS NOT NULL "
        f"AND {value_column} <> '' "
        f"AND NOT regexp_matches({value_column}, '\\s') "
        f"AND NOT regexp_matches({value_column}, '\\$\\d') "
        f"AND regexp_matches({value_column}, '^https?://[a-zA-Z0-9.-]+/')"
        ")"
    )


def _metis_path_to_prefix_check(path: str, value_column: str) -> str:
    """Produce a SQL expression that matches *value_column* against a Metis path.

    Metis paths are recorded with a specific scheme (some HTTP, some
    HTTPS — inconsistently). To honour Metis as the source of truth for
    the host + path while accepting either scheme on the data side,
    we strip the scheme from the Metis path and emit a regex check.
    """
    import re

    stripped = re.sub(r"^https?://", "", path)
    # Escape regex metacharacters in the host/path portion.
    escaped = re.escape(stripped)
    pattern = f"^https?://{escaped}"
    return f"regexp_matches({value_column}, '{pattern}')"


def metis_known_sql(value_column: str = "x_value") -> str:
    """Generate a DuckDB BOOLEAN expression: does *value_column* match any Metis vocabulary?

    True when the IRI's prefix matches at least one path in the Metis
    registry (with scheme tolerance). Honest framing: we recognise the
    vocabulary, we have *not* probed the URL for resolvability.

    Should be combined with :func:`well_formed_sql` — a malformed IRI
    may coincidentally pass the regex.
    """
    paths = [p for v in metis_vocabularies().values() for p in v.paths]
    if not paths:
        return "FALSE"
    clauses = [_metis_path_to_prefix_check(p, value_column) for p in paths]
    return "(" + " OR ".join(clauses) + ")"


def authority_sql(value_column: str = "x_value") -> str:
    """Generate a DuckDB ``CASE/WHEN`` returning the matching Metis vocabulary name.

    Returns the vocabulary's short name (e.g. ``'wikidata'``, ``'aat'``,
    ``'gnd'``) when the IRI matches one of its paths. Multiple paths
    per vocabulary are OR'd. Callers should gate the result on
    ``well_formed_sql() AND metis_known_sql()`` and emit ``NULL`` when
    either is false.
    """
    vocabs = metis_vocabularies()
    clauses: list[str] = []
    for vocab in vocabs.values():
        per_vocab = [
            _metis_path_to_prefix_check(p, value_column) for p in vocab.paths
        ]
        if not per_vocab:
            continue
        match = "(" + " OR ".join(per_vocab) + ")"
        clauses.append(f"WHEN {match} THEN '{vocab.name}'")
    if not clauses:
        return "NULL"
    lines = "\n          ".join(clauses)
    return f"""CASE
          {lines}
          ELSE NULL
        END"""


# ---------------------------------------------------------------------------
# Filterable fields — derived from GroupItems
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FilterFieldInfo:
    """Metadata for a single filterable GroupItems field."""

    name: str
    column: str
    filter_style: str
    data_type: str
    multivalued: bool
    required: bool
    struct_field: str | None = None


@functools.cache
def filterable_fields() -> dict[str, FilterFieldInfo]:
    """Return all non-identifier GroupItems fields with inferred filter styles.

    group_items is scalar-only (no list or struct columns), so every
    filterable field resolves to ``bool`` / ``range`` / ``eq`` /
    ``in_list`` depending on the LinkML range.
    """
    result: dict[str, FilterFieldInfo] = {}
    for name, attr in group_fields().items():
        if attr.identifier:
            continue
        if attr.range == "boolean":
            style = "bool"
        elif attr.range == "integer":
            style = "range"
        elif attr.range == "ReuseLevel":
            style = "eq"
        else:
            style = "in_list"
        result[name] = FilterFieldInfo(
            name=name,
            column=name,
            filter_style=style,
            data_type=attr.range or "string",
            multivalued=attr.multivalued,
            required=attr.required,
            struct_field=None,
        )
    return result


# ---------------------------------------------------------------------------
# PyArrow schema generation
# ---------------------------------------------------------------------------

_PA_SCALAR: dict[str, str] = {
    "string": "string",
    "uri": "string",
    "integer": "int64",
    "float": "float64",
    "boolean": "bool_",
    "timestamp": "timestamp_ms_utc",
    "ReuseLevel": "string",
    "RightsFamily": "string",
    "EntityClass": "string",
    "Authority": "string",
}


def _pa_type(range_name: str | None, multivalued: bool):
    """Convert a LinkML range + multivalued flag to a PyArrow type."""
    import pyarrow as pa

    rng = range_name or "string"
    if multivalued:
        return pa.list_(pa.string())
    type_name = _PA_SCALAR.get(rng, "string")
    if type_name == "timestamp_ms_utc":
        return pa.timestamp("ms", tz="UTC")
    return getattr(pa, type_name)()


def _sorted_attributes(attrs: dict[str, AttributeInfo]) -> list[tuple[str, AttributeInfo]]:
    """Alphabetically sort attributes by name (identifier comes first by prefix)."""
    return sorted(attrs.items(), key=lambda kv: kv[0])


# Links tables share a fixed 5-column schema.
def _links_pa_schema():
    import pyarrow as pa

    return pa.schema([
        pa.field("k_iri", pa.string()),
        pa.field("x_property", pa.string()),
        pa.field("x_value", pa.string()),
        pa.field("x_value_is_iri", pa.bool_()),
        pa.field("x_value_lang", pa.string()),
    ])


@functools.cache
def pyarrow_schema(export_name: str):
    """Return a static ``pyarrow.Schema`` for the given export name.

    Accepts final table names and synthetic links_scan names.
    Raises :class:`KeyError` for unknown exports.
    """
    import pyarrow as pa

    # Synthetic per-property links_scan intermediates: same 5-column shape
    # as the final links_* table.
    scans = links_scan_entries()
    if export_name in scans:
        return _links_pa_schema()

    info = export_classes().get(export_name)
    if info is None:
        raise KeyError(f"Unknown export: {export_name!r}")

    if info.export_type == "links":
        return _links_pa_schema()

    # values / merged / group / map — derive from attributes, alphabetical.
    fields = [
        pa.field(name, _pa_type(attr.range, attr.multivalued))
        for name, attr in _sorted_attributes(info.attributes)
    ]
    return pa.schema(fields)


# ---------------------------------------------------------------------------
# Human-readable DuckDB type strings (for NL agent schema description)
# ---------------------------------------------------------------------------

_DUCKDB_TYPE: dict[str, str] = {
    "string": "VARCHAR",
    "uri": "VARCHAR",
    "integer": "INTEGER",
    "float": "DOUBLE",
    "boolean": "BOOLEAN",
    "timestamp": "TIMESTAMP",
    "ReuseLevel": "VARCHAR",
    "RightsFamily": "VARCHAR",
    "EntityClass": "VARCHAR",
    "Authority": "VARCHAR",
}

_DUCKDB_LIST_TYPE: dict[str, str] = {
    "string": "LIST<VARCHAR>",
    "integer": "LIST<INTEGER>",
}


def _duckdb_type_str(range_name: str | None, multivalued: bool) -> str:
    rng = range_name or "string"
    if multivalued:
        return _DUCKDB_LIST_TYPE.get(rng, "LIST<VARCHAR>")
    return _DUCKDB_TYPE.get(rng, "VARCHAR")


# ---------------------------------------------------------------------------
# Parquet schema description for NL→DuckDB agent
# ---------------------------------------------------------------------------


def parquet_schema_description() -> str:
    """Auto-generate an LLM-friendly description of the exported Parquet tables."""
    lines: list[str] = []

    # --- group_items ---
    lines.append("## Table: group_items")
    lines.append(
        "One row per CHO. Only scalar categorical/boolean/integer columns "
        "— NO list or struct types. Ideal for fast GROUP BY analytics."
    )
    lines.append("Columns:")
    for name, attr in _sorted_attributes(group_fields()):
        type_str = _duckdb_type_str(attr.range, attr.multivalued)
        desc = f" — {attr.description}" if attr.description else ""
        lines.append(f"  {name} ({type_str}){desc}")
    lines.append("")

    # --- raw values_ / links_ tables ---
    lines.append("## Raw tables (values_* and links_*)")
    lines.append(
        "The raw layer preserves EDM class boundaries. values_* are wide "
        "(one row per entity, only k_ and v_ columns). links_* are long "
        "(one row per value; k_iri, x_property, x_value, x_value_is_iri, "
        "x_value_lang)."
    )
    lines.append("")
    for info in sorted(export_classes().values(), key=lambda e: e.table_name):
        if info.export_type not in ("values", "links"):
            continue
        lines.append(f"### {info.table_name}")
        cls = schema_view().get_class(info.cls_name)
        if cls and cls.description:
            lines.append(cls.description.strip())
        if info.export_type == "links":
            curies = [c for c, _ in link_properties(info.table_name)]
            lines.append("Columns: k_iri, x_property, x_value, x_value_is_iri, x_value_lang.")
            lines.append(
                f"x_property values (as v_namespace_local strings): "
                f"{', '.join(c.replace(':', '_') for c in curies) or '—'}."
            )
        else:
            for name, attr in _sorted_attributes(info.attributes):
                type_str = _duckdb_type_str(attr.range, attr.multivalued)
                desc = f" — {attr.description}" if attr.description else ""
                lines.append(f"  {name} ({type_str}){desc}")
        lines.append("")

    # --- map_* tables ---
    lines.append("## Map tables (map_*)")
    for info in sorted(export_classes().values(), key=lambda e: e.table_name):
        if info.export_type != "map":
            continue
        lines.append(f"### {info.table_name}")
        cls = schema_view().get_class(info.cls_name)
        if cls and cls.description:
            lines.append(cls.description.strip())
        lines.append("Columns:")
        for name, attr in _sorted_attributes(info.attributes):
            type_str = _duckdb_type_str(attr.range, attr.multivalued)
            desc = f" — {attr.description}" if attr.description else ""
            lines.append(f"  {name} ({type_str}){desc}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# EDM base schema access (imported edm.yaml)
# ---------------------------------------------------------------------------


@functools.cache
def edm_class_properties(cls_name: str) -> dict[str, AttributeInfo]:
    """Return all properties for an EDM base class (from edm.yaml)."""
    sv = schema_view()
    cls = sv.get_class(cls_name)
    if cls is None:
        raise ValueError(f"Unknown EDM class: {cls_name!r}")
    result: dict[str, AttributeInfo] = {}
    for attr_name, attr in cls.attributes.items():
        result[attr_name] = AttributeInfo(
            name=attr_name,
            slot_uri=attr.slot_uri,
            range=attr.range,
            multivalued=bool(attr.multivalued),
            required=bool(attr.required),
            identifier=bool(attr.identifier),
            description=attr.description or None,
            annotations=_annots(attr),
        )
    return result


