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


def merged_fields() -> dict[str, AttributeInfo]:
    """All MergedItems class attributes (the ``merged_items`` schema)."""
    return class_attributes("MergedItems")


def group_fields() -> dict[str, AttributeInfo]:
    """All GroupItems class attributes (the ``group_items`` schema)."""
    return class_attributes("GroupItems")


# Back-compat alias — some older code may still reference item_fields().
item_fields = merged_fields


# ---------------------------------------------------------------------------
# Export class discovery
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExportClassInfo:
    """Metadata for a single export discovered from schema annotations."""

    cls_name: str
    table_name: str
    export_type: str  # "values", "links_union", "links_scan", "merged", "group", "map"
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

    A ``links_union`` table (like ``links_ore_Proxy``) has many link
    properties; each becomes its own intermediate SPARQL scan, producing
    a Parquet with the same 5-column shape. The final ``links_union``
    Parquet is a UNION ALL over all scans for that table.
    """

    parent_table: str           # e.g. "links_ore_Proxy"
    scan_name: str              # e.g. "links_ore_Proxy__dc_subject"
    curie: str                  # e.g. "dc:subject"
    property_uri: str           # full URI
    property_column: str        # e.g. "v_dc_subject" — goes into x_property
    subject_base_pattern: str   # SPARQL pattern that binds ?k_iri
    required_prefixes: list[str]


def link_properties(table_name: str) -> list[tuple[str, str]]:
    """Return (curie, v_column_name) pairs for a links_union table."""
    info = export_classes().get(table_name)
    if info is None or info.export_type != "links_union":
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
        if info.export_type != "links_union":
            continue
        subject_pattern = info.annotations.get("subject_base_pattern", "").strip()
        required_pfx = _parse_csv(info.annotations.get("required_prefixes", ""))
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
        if info.export_type in ("values", "links_union")
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
def authority_patterns() -> dict[str, str]:
    """Return authority name → URI prefix mapping."""
    annots = _annots(schema_view().schema)
    raw = annots.get("authority_patterns", "")
    result: dict[str, str] = {}
    for pair in _parse_csv(raw):
        if "=" not in pair:
            continue
        name, prefix = pair.split("=", 1)
        result[name.strip()] = prefix.strip()
    return result


def authority_sql(value_column: str = "x_value") -> str:
    """Generate a DuckDB ``CASE/WHEN`` for authority classification."""
    patterns = authority_patterns()
    clauses = [
        f"WHEN STARTS_WITH({value_column}, '{prefix}') THEN '{name}'"
        for name, prefix in patterns.items()
    ]
    lines = "\n          ".join(clauses)
    return f"""CASE
          {lines}
          ELSE 'other'
        END"""


# ---------------------------------------------------------------------------
# Filterable fields — derived from MergedItems
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FilterFieldInfo:
    """Metadata for a single filterable MergedItems field."""

    name: str
    column: str
    filter_style: str
    data_type: str
    multivalued: bool
    required: bool
    struct_field: str | None = None


# Struct types whose searchable key is inside the struct.
_STRUCT_LABEL_FIELD: dict[str, str] = {
    "LabeledEntityX": "x_label",
    "NamedEntityX": "x_name",
    "LangValueX": "x_value",
}


@functools.cache
def filterable_fields() -> dict[str, FilterFieldInfo]:
    """Return all non-identifier MergedItems fields with inferred filter styles."""
    result: dict[str, FilterFieldInfo] = {}
    for name, attr in merged_fields().items():
        if attr.identifier:
            continue
        if attr.multivalued:
            if attr.range in _STRUCT_LABEL_FIELD:
                style = "list_struct"
            else:
                style = "list_contains"
        elif attr.range == "boolean":
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
            struct_field=_STRUCT_LABEL_FIELD.get(attr.range or ""),
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
        if rng == "LangValueX":
            return pa.list_(pa.struct([
                ("x_value", pa.string()),
                ("x_value_lang", pa.string()),
            ]))
        if rng == "LabeledEntityX":
            return pa.list_(pa.struct([
                ("x_value", pa.string()),
                ("x_label", pa.string()),
                ("x_value_is_iri", pa.bool_()),
            ]))
        if rng == "NamedEntityX":
            return pa.list_(pa.struct([
                ("x_value", pa.string()),
                ("x_name", pa.string()),
                ("x_value_is_iri", pa.bool_()),
            ]))
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

    if info.export_type == "links_union":
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
    "LangValueX": "LIST<STRUCT<x_value VARCHAR, x_value_lang VARCHAR>>",
    "LabeledEntityX": "LIST<STRUCT<x_value VARCHAR, x_label VARCHAR, x_value_is_iri BOOLEAN>>",
    "NamedEntityX": "LIST<STRUCT<x_value VARCHAR, x_name VARCHAR, x_value_is_iri BOOLEAN>>",
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

    # --- merged_items ---
    lines.append("## Table: merged_items")
    lines.append(
        "One row per cultural heritage item (~66M rows). Joins proxies, "
        "aggregations, primary web resource; resolves entity labels; "
        "aggregates multi-valued properties. This is the main table for "
        "most analytical questions."
    )
    lines.append("")
    lines.append("Columns (alphabetical):")
    for name, attr in _sorted_attributes(merged_fields()):
        type_str = _duckdb_type_str(attr.range, attr.multivalued)
        desc = f" — {attr.description}" if attr.description else ""
        lines.append(f"  {name} ({type_str}){desc}")
    lines.append("")

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
        if info.export_type not in ("values", "links_union"):
            continue
        lines.append(f"### {info.table_name}")
        cls = schema_view().get_class(info.cls_name)
        if cls and cls.description:
            lines.append(cls.description.strip())
        if info.export_type == "links_union":
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


# ---------------------------------------------------------------------------
# Parquet file validation
# ---------------------------------------------------------------------------


def validate_against_parquet(parquet_path: Path) -> tuple[set[str], set[str]]:
    """Compare the MergedItems schema against an actual Parquet file."""
    import pyarrow.parquet as pq

    schema_cols = set(merged_fields().keys())
    pq_schema = pq.read_schema(parquet_path)
    parquet_cols = set(pq_schema.names)
    missing = schema_cols - parquet_cols
    extra = parquet_cols - schema_cols
    return missing, extra
