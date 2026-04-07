"""Schema loader — programmatic access to the EDM Parquet LinkML schema.

Provides a cached :class:`~linkml_runtime.utils.schemaview.SchemaView`
singleton and convenience accessors for prefixes, class attributes,
SPARQL variable mappings, entity link properties, reuse-level patterns,
and authority patterns.

All EDM property URIs, column names, and pipeline metadata are derived
from ``schema/edm_parquet.yaml`` — nothing is hardcoded here.
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

# Prefixes that are part of LinkML infrastructure, not EDM data.
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
    """Expand a CURIE like ``dc:title`` to a full URI, or return as-is."""
    if curie is None:
        return None
    pfx = prefixes()
    if ":" in curie:
        prefix, local = curie.split(":", 1)
        if prefix in pfx:
            return pfx[prefix] + local
    return curie


def compact_uri(full_uri: str) -> str | None:
    """Compact a full URI to a CURIE like ``dc:title``, or ``None`` if no match."""
    pfx = prefixes()
    for prefix, ns in pfx.items():
        if full_uri.startswith(ns):
            return f"{prefix}:{full_uri[len(ns):]}"
    return None


def prefix_of(full_uri: str) -> str | None:
    """Return the prefix key for a full URI, e.g. ``'dc'`` for a dc:title URI."""
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


def item_fields() -> dict[str, AttributeInfo]:
    """All Item class attributes (the ``items_resolved`` schema)."""
    return class_attributes("Item")


def entity_classes() -> list[str]:
    """Return the four contextual entity class names."""
    return ["Agent", "Concept", "Place", "TimeSpan"]


# ---------------------------------------------------------------------------
# SPARQL variable ↔ column name mapping
# ---------------------------------------------------------------------------


def sparql_var(cls_name: str, column: str) -> str:
    """Get the SPARQL ``?variable`` name for a column.

    Returns the ``sparql_variable`` annotation if set, otherwise the
    column name itself.
    """
    attrs = class_attributes(cls_name)
    if column not in attrs:
        return column
    return attrs[column].annotations.get("sparql_variable", column)


def column_name(cls_name: str, sparql_variable: str) -> str:
    """Reverse lookup: SPARQL variable → canonical column name."""
    attrs = class_attributes(cls_name)
    for attr_name, attr in attrs.items():
        if attr.annotations.get("sparql_variable") == sparql_variable:
            return attr_name
    # If no annotation overrides, the sparql var IS the column name
    if sparql_variable in attrs:
        return sparql_variable
    return sparql_variable


def slot_uri(cls_name: str, column: str) -> str | None:
    """Return the full RDF property URI for a column, or ``None``."""
    attrs = class_attributes(cls_name)
    if column not in attrs:
        return None
    return _expand_uri(attrs[column].slot_uri)


def slot_curie(cls_name: str, column: str) -> str | None:
    """Return the CURIE form of a column's slot_uri (e.g. ``dc:title``).

    Useful for embedding directly in SPARQL queries that have PREFIX
    declarations.
    """
    attrs = class_attributes(cls_name)
    if column not in attrs:
        return None
    return attrs[column].slot_uri


def is_multivalued(cls_name: str, column: str) -> bool:
    """Check if a column is a list-typed field."""
    attrs = class_attributes(cls_name)
    return attrs[column].multivalued if column in attrs else False


def is_computed(cls_name: str, column: str) -> bool:
    """Check if a column is derived (not directly from RDF)."""
    attrs = class_attributes(cls_name)
    if column not in attrs:
        return False
    return attrs[column].annotations.get("computed") == "true"


def base_table(cls_name: str, column: str) -> str | None:
    """Return the component export Parquet name for a multi-valued column."""
    attrs = class_attributes(cls_name)
    if column not in attrs:
        return None
    return attrs[column].annotations.get("base_table")


# ---------------------------------------------------------------------------
# Entity link properties
# ---------------------------------------------------------------------------


_ENTITY_NAME_MAP = {
    "agents": "Agent", "concepts": "Concept",
    "places": "Place", "timespans": "TimeSpan",
}


def _entity_cls_name(entity_type: str) -> str:
    """Normalise entity type to class name (e.g. ``"agents"`` → ``"Agent"``)."""
    return _ENTITY_NAME_MAP.get(entity_type, entity_type)


@dataclass(frozen=True)
class LinkProperty:
    """A link property with its name, full URI, CURIE, and lang-tag flag."""
    name: str
    uri: str
    curie: str
    has_lang: bool


@functools.cache
def entity_link_property_details(entity_type: str) -> list[LinkProperty]:
    """Return link property details for an entity type.

    Parses the ``link_properties`` class annotation.  The ``+lang`` suffix
    on a CURIE indicates the property value carries a language tag.
    """
    cls_name = _entity_cls_name(entity_type)
    sv = schema_view()
    cls = sv.get_class(cls_name)
    if cls is None:
        raise ValueError(f"Unknown entity type: {entity_type!r}")

    raw = _annots(cls).get("link_properties", "")
    result: list[LinkProperty] = []
    for pair in raw.split(","):
        pair = pair.strip()
        if "=" not in pair:
            continue
        name, curie_raw = pair.split("=", 1)
        curie_raw = curie_raw.strip()
        has_lang = curie_raw.endswith("+lang")
        curie = curie_raw.removesuffix("+lang")
        uri = _expand_uri(curie) or curie
        result.append(LinkProperty(
            name=name.strip(), uri=uri, curie=curie, has_lang=has_lang,
        ))
    return result


@functools.cache
def entity_link_properties(entity_type: str) -> dict[str, str]:
    """Return normalized name → full RDF URI for an entity type's link properties.

    Entity type can be a class name (``"Agent"``) or a lowercase plural
    (``"agents"``).
    """
    return {lp.name: lp.uri for lp in entity_link_property_details(entity_type)}


def entity_id_column(entity_type: str) -> str:
    """Return the identifier column name for an entity class (e.g. ``'agent'``)."""
    cls_name = _entity_cls_name(entity_type)
    sv = schema_view()
    cls = sv.get_class(cls_name)
    if cls is None:
        raise ValueError(f"Unknown entity type: {entity_type!r}")
    return _annots(cls).get("id_column", cls_name.lower())


def entity_class_uri(entity_type: str) -> str:
    """Return the class URI CURIE for an entity type (e.g. ``'edm:Agent'``)."""
    cls_name = _entity_cls_name(entity_type)
    sv = schema_view()
    cls = sv.get_class(cls_name)
    if cls is None:
        raise ValueError(f"Unknown entity type: {entity_type!r}")
    return cls.class_uri


def entity_core_fields(entity_type: str) -> dict[str, AttributeInfo]:
    """Return non-identifier, non-pref_label_lang fields for an entity type.

    These are the fields used in OPTIONAL clauses of entity core queries.
    Excludes the identifier column and pref_label (which are required) and
    pref_label_lang (which is derived via BIND).
    """
    cls_name = _entity_cls_name(entity_type)
    attrs = class_attributes(cls_name)
    skip = {entity_id_column(entity_type), "pref_label", "pref_label_lang"}
    return {k: v for k, v in attrs.items() if k not in skip}


def entity_prefixes(entity_type: str) -> set[str]:
    """Return the set of namespace prefix keys needed to query an entity type.

    Includes prefixes for the class URI, core field slot_uris, and link
    property CURIEs.
    """
    cls_name = _entity_cls_name(entity_type)
    result: set[str] = set()

    # Class URI prefix
    sv = schema_view()
    cls = sv.get_class(cls_name)
    if cls and cls.class_uri and ":" in cls.class_uri:
        result.add(cls.class_uri.split(":")[0])

    # Always need skos for prefLabel
    result.add("skos")

    # Core field prefixes
    for attr in class_attributes(cls_name).values():
        if attr.slot_uri and ":" in attr.slot_uri:
            result.add(attr.slot_uri.split(":")[0])

    # Link property prefixes
    for lp in entity_link_property_details(entity_type):
        if ":" in lp.curie:
            result.add(lp.curie.split(":")[0])

    return result


# ---------------------------------------------------------------------------
# Reuse level patterns
# ---------------------------------------------------------------------------


@functools.cache
def reuse_level_patterns() -> dict[str, list[str]]:
    """Return reuse level → list of URI prefixes/exact URIs.

    Structure::

        {
            "open": ["http://creativecommons.org/publicdomain/", ...],
            "restricted_prefixes": ["http://creativecommons.org/licenses/"],
            "restricted_uris": ["http://rightsstatements.org/vocab/NoC-NC/1.0/", ...],
        }
    """
    annots = _annots(schema_view().schema)
    def _split(key: str) -> list[str]:
        return [s.strip() for s in annots.get(key, "").split(",") if s.strip()]

    return {
        "open": _split("reuse_level_open_prefixes"),
        "restricted_prefixes": _split("reuse_level_restricted_prefixes"),
        "restricted_uris": _split("reuse_level_restricted_uris"),
    }


def reuse_level_sql(rights_column: str = "rights") -> str:
    """Generate a DuckDB ``CASE/WHEN`` expression for reuse level classification."""
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
    """Return authority name → URI prefix mapping for entity sameAs classification."""
    annots = _annots(schema_view().schema)
    raw = annots.get("authority_patterns", "")
    result: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if "=" not in pair:
            continue
        name, prefix = pair.split("=", 1)
        result[name.strip()] = prefix.strip()
    return result


def authority_sql(value_column: str = "value") -> str:
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
# Filterable fields
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FilterFieldInfo:
    """Metadata for a single filterable Item field.

    Filter style is inferred from the schema field's range and
    multivalued flag:

    - ``in_list`` — scalar string/enum/uri: ``col IN (...)``
    - ``eq`` — single-value enum (ReuseLevel): ``col = '...'``
    - ``bool`` — boolean: ``col = true``
    - ``range`` — integer: ``col >= N`` / ``col <= N``
    - ``list_contains`` — LIST<VARCHAR>: ``list_has_any(col, [...])``
    - ``list_struct`` — LIST<STRUCT>: label-based search inside structs
    """

    name: str
    column: str
    filter_style: str
    data_type: str
    multivalued: bool
    required: bool
    struct_field: str | None = None


# Struct types whose inner ``label`` / ``name`` field is the searchable key.
_STRUCT_LABEL_FIELD: dict[str, str] = {
    "LabeledEntity": "label",
    "NamedEntity": "name",
    "LangValue": "value",
}


@functools.cache
def filterable_fields() -> dict[str, FilterFieldInfo]:
    """Return all non-identifier Item fields with inferred filter styles.

    Every Item column is filterable.  The filter style is derived from
    the field's range and multivalued flag — no schema annotations needed.
    """
    result: dict[str, FilterFieldInfo] = {}
    for name, attr in item_fields().items():
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
# Parquet validation
# ---------------------------------------------------------------------------


def validate_against_parquet(parquet_path: Path) -> tuple[set[str], set[str]]:
    """Compare schema Item columns against an actual Parquet file.

    Returns ``(missing_in_parquet, extra_in_parquet)`` — both empty if
    the schema and file match perfectly.
    """
    import pyarrow.parquet as pq

    schema_cols = set(item_fields().keys())
    pq_schema = pq.read_schema(parquet_path)
    parquet_cols = set(pq_schema.names)

    missing = schema_cols - parquet_cols
    extra = parquet_cols - schema_cols
    return missing, extra


# ---------------------------------------------------------------------------
# EDM base schema access
# ---------------------------------------------------------------------------


@functools.cache
def edm_class_properties(cls_name: str) -> dict[str, AttributeInfo]:
    """Return all properties for an EDM base class (from edm.yaml).

    This provides access to the *full* EDM model, not just the export
    projection.  Use this as a "menu" when designing new exports.
    """
    sv = schema_view()
    # Look up the class from the imported edm.yaml schema
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
# Export class discovery — reads export_type / export_name annotations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExportClassInfo:
    """Metadata for a single export discovered from schema annotations."""

    cls_name: str
    export_name: str
    export_type: str  # "scan", "summary", "composite", "entity"
    export_sets: list[str]
    attributes: dict[str, AttributeInfo]
    annotations: dict[str, str]


@functools.cache
def export_classes() -> dict[str, ExportClassInfo]:
    """Discover all export classes from schema annotations.

    Returns a dict mapping export_name → ExportClassInfo.
    Entity classes produce two entries (``*_core`` and ``*_links``).
    """
    sv = schema_view()
    result: dict[str, ExportClassInfo] = {}
    for cls_name in sv.all_classes():
        cls = sv.get_class(cls_name)
        annots = _annots(cls)
        et = annots.get("export_type", "")
        if not et:
            continue

        sets_str = annots.get("export_sets", "")
        sets = [s.strip() for s in sets_str.split(",") if s.strip()]

        attrs = class_attributes(cls_name)

        if et == "entity":
            # Entity classes produce two exports: *_core and *_links
            for suffix in ("core", "links"):
                en = annots.get(f"export_name_{suffix}", "")
                if en:
                    result[en] = ExportClassInfo(
                        cls_name=cls_name,
                        export_name=en,
                        export_type=et,
                        export_sets=sets,
                        attributes=attrs,
                        annotations=annots,
                    )
        else:
            en = annots.get("export_name", "")
            if en:
                result[en] = ExportClassInfo(
                    cls_name=cls_name,
                    export_name=en,
                    export_type=et,
                    export_sets=sets,
                    attributes=attrs,
                    annotations=annots,
                )

    # Also register base table exports driven by Item field annotations
    for col_name, attr in item_fields().items():
        bt = attr.annotations.get("base_table")
        if bt and bt not in result:
            result[bt] = ExportClassInfo(
                cls_name="Item",
                export_name=bt,
                export_type="base_table",
                export_sets=["pipeline", "items"],
                attributes=item_fields(),
                annotations={"query_pattern": attr.annotations.get("query_pattern", "")},
            )

    return result


@functools.cache
def export_sets() -> dict[str, list[str]]:
    """Build export sets from schema annotations.

    Returns a dict mapping set name → list of export names.
    """
    sets: dict[str, list[str]] = {}
    for en, info in export_classes().items():
        for s in info.export_sets:
            sets.setdefault(s, []).append(en)
    # Sort each set for deterministic ordering
    return {k: sorted(v) for k, v in sets.items()}


def export_sparql_pattern(export_name: str) -> str | None:
    """Return the SPARQL WHERE pattern for an export, or None."""
    info = export_classes().get(export_name)
    if info is None:
        return None
    return info.annotations.get("sparql_pattern")


# ---------------------------------------------------------------------------
# PyArrow schema generation — fully derived from schema annotations
# ---------------------------------------------------------------------------

# Range → PyArrow type mappings (module-level for reuse)
_PA_SCALAR: dict[str, str] = {
    "string": "string",
    "uri": "string",
    "integer": "int64",
    "float": "float64",
    "boolean": "bool_",
    "timestamp": "timestamp_ms_utc",
    "EdmType": "string",
    "ReuseLevel": "string",
}

_PA_MULTIVALUED: dict[str, str] = {
    "LangValue": "list_struct_value_lang",
    "LabeledEntity": "list_struct_label_uri",
    "NamedEntity": "list_struct_name_uri",
    "string": "list_string",
}


def _pa_type(range_name: str | None, multivalued: bool):
    """Convert a LinkML range + multivalued flag to a PyArrow type."""
    import pyarrow as pa

    rng = range_name or "string"
    if multivalued:
        key = _PA_MULTIVALUED.get(rng, "list_string")
        if key == "list_struct_value_lang":
            return pa.list_(pa.struct([("value", pa.string()), ("lang", pa.string())]))
        if key == "list_struct_label_uri":
            return pa.list_(pa.struct([("label", pa.string()), ("uri", pa.string())]))
        if key == "list_struct_name_uri":
            return pa.list_(pa.struct([("name", pa.string()), ("uri", pa.string())]))
        return pa.list_(pa.string())
    type_name = _PA_SCALAR.get(rng, "string")
    if type_name == "timestamp_ms_utc":
        return pa.timestamp("ms", tz="UTC")
    return getattr(pa, type_name)()


@functools.cache
def pyarrow_schema(export_name: str):
    """Return a static ``pyarrow.Schema`` for the given export.

    Derives schemas from schema class annotations.  Covers all registered
    exports.  Raises ``KeyError`` if the export is unknown.
    """
    import pyarrow as pa

    info = export_classes().get(export_name)
    if info is None:
        raise KeyError(f"Unknown export: {export_name!r}")

    # --- composite (items_resolved) ---
    if info.export_type == "composite":
        fields = item_fields()
        return pa.schema([
            pa.field(n, _pa_type(a.range, a.multivalued))
            for n, a in fields.items()
        ])

    # --- base_table (items_titles, items_subjects, etc.) ---
    if info.export_type == "base_table":
        # Derive from the Item field that has this base_table
        for name, attr in item_fields().items():
            if attr.annotations.get("base_table") == export_name:
                pattern = attr.annotations.get("query_pattern", "")
                curie = slot_curie("Item", name)
                local = curie.split(":")[1] if curie and ":" in curie else name
                if pattern == "lang_tagged":
                    return pa.schema([
                        pa.field("item", pa.string()),
                        pa.field(local, pa.string()),
                        pa.field("lang", pa.string()),
                    ])
                elif pattern == "iri_or_literal":
                    stem = name.rstrip("s")
                    return pa.schema([
                        pa.field("item", pa.string()),
                        pa.field(f"{stem}_value", pa.string()),
                        pa.field("is_iri", pa.bool_()),
                    ])
                elif pattern == "simple_literal":
                    var_name = name.rstrip("s") if name != "dc_rights" else "dc_rights"
                    return pa.schema([
                        pa.field("item", pa.string()),
                        pa.field(var_name, pa.string()),
                    ])

    # --- entity (*_core, *_links) ---
    if info.export_type == "entity":
        id_col = info.annotations.get("id_column", "id")
        if export_name.endswith("_links"):
            return pa.schema([
                pa.field(id_col, pa.string()),
                pa.field("property", pa.string()),
                pa.field("value", pa.string()),
                pa.field("lang", pa.string()),
            ])
        else:
            # *_core: id + pref_label + pref_label_lang + core fields
            cols = [pa.field(id_col, pa.string())]
            cols.append(pa.field("pref_label", pa.string()))
            cols.append(pa.field("pref_label_lang", pa.string()))
            for fname, fattr in info.attributes.items():
                if fname in (id_col, "pref_label", "pref_label_lang"):
                    continue
                if fattr.identifier:
                    continue
                cols.append(pa.field(fname, _pa_type(fattr.range, fattr.multivalued)))
            return pa.schema(cols)

    # --- scan and summary: derive from class attributes ---
    cols = []
    for attr_name, attr in info.attributes.items():
        agg = attr.annotations.get("aggregation", "")
        if agg:
            # Aggregation column: use the attribute name and derive type
            cols.append(pa.field(attr_name, _pa_type(attr.range, attr.multivalued)))
        else:
            cols.append(pa.field(attr_name, _pa_type(attr.range, attr.multivalued)))
    return pa.schema(cols)


# ---------------------------------------------------------------------------
# Parquet schema description for NL→DuckDB agent
# ---------------------------------------------------------------------------

# Human-readable type strings for LLM consumption
_DUCKDB_TYPE: dict[str, str] = {
    "string": "VARCHAR",
    "uri": "VARCHAR",
    "integer": "INTEGER",
    "float": "DOUBLE",
    "boolean": "BOOLEAN",
    "timestamp": "TIMESTAMP",
    "EdmType": "VARCHAR",
    "ReuseLevel": "VARCHAR",
}

_DUCKDB_LIST_TYPE: dict[str, str] = {
    "LangValue": "LIST<STRUCT<value VARCHAR, lang VARCHAR>>",
    "LabeledEntity": "LIST<STRUCT<label VARCHAR, uri VARCHAR>>",
    "NamedEntity": "LIST<STRUCT<name VARCHAR, uri VARCHAR>>",
    "string": "LIST<VARCHAR>",
    "integer": "LIST<INTEGER>",
}

def _duckdb_type_str(range_name: str | None, multivalued: bool) -> str:
    """Convert a LinkML range + multivalued flag to a DuckDB type string."""
    rng = range_name or "string"
    if multivalued:
        return _DUCKDB_LIST_TYPE.get(rng, "LIST<VARCHAR>")
    return _DUCKDB_TYPE.get(rng, "VARCHAR")


def parquet_schema_description() -> str:
    """Auto-generate an LLM-friendly description of exported Parquet tables.

    Used by the ``ask`` command to build the system prompt for the
    NL→DuckDB agent.  Describes ``items_resolved`` in detail and lists
    available entity tables.
    """
    lines: list[str] = []

    # --- items_resolved ---
    lines.append("## Table: items_resolved")
    lines.append("One row per cultural heritage item (~66M rows).")
    lines.append("This is the main table for most analytical questions.")
    lines.append("")
    lines.append("Columns:")
    for col_name, attr in item_fields().items():
        type_str = _duckdb_type_str(attr.range, attr.multivalued)
        desc_part = f" — {attr.description}" if attr.description else ""
        lines.append(f"  {col_name} ({type_str}){desc_part}")
    lines.append("")

    # --- entity tables ---
    for etype in ("agents", "concepts", "places", "timespans"):
        core_name = f"{etype}_core"
        links_name = f"{etype}_links"
        info = export_classes().get(core_name)
        if info is None:
            continue
        id_col = info.annotations.get("id_column", "id")

        lines.append(f"## Table: {core_name}")
        lines.append(
            f"One row per skos:prefLabel variant per {etype[:-1]}. "
            f"Use for entity-level analysis."
        )
        lines.append(f"  {id_col} (VARCHAR) — entity URI")
        lines.append("  pref_label (VARCHAR) — skos:prefLabel value")
        lines.append("  pref_label_lang (VARCHAR) — language tag of prefLabel")
        # Add core-specific fields beyond the standard three
        for fname, fattr in info.attributes.items():
            if fname in (id_col, "pref_label", "pref_label_lang") or fattr.identifier:
                continue
            type_str = _duckdb_type_str(fattr.range, fattr.multivalued)
            lines.append(f"  {fname} ({type_str})")
        lines.append("")

        lines.append(f"## Table: {links_name}")
        lines.append(
            f"Multi-valued and linked properties for {etype} in long format."
        )
        lines.append(f"  {id_col} (VARCHAR) — entity URI")
        lines.append("  property (VARCHAR) — property name: same_as, alt_label, exact_match, broader, narrower, etc.")
        lines.append("  value (VARCHAR) — property value (URI or literal)")
        lines.append("  lang (VARCHAR) — language tag (if applicable)")
        lines.append("")

    # --- institutions ---
    lines.append("## Table: institutions")
    lines.append("Organisation names. Join with items_resolved on institution or aggregator URI.")
    lines.append("  org (VARCHAR) — organisation URI")
    lines.append("  name (VARCHAR) — display name")
    lines.append("  lang (VARCHAR) — language of the name")
    lines.append("")

    # --- summary tables ---
    lines.append("## Summary tables")
    lines.append(
        "Pre-aggregated tables for common analytical queries. "
        "Prefer these over scanning items_resolved when they fit the question."
    )
    lines.append("")
    for eci in sorted(export_classes().values(), key=lambda e: e.export_name):
        if eci.export_type != "summary":
            continue
        desc = eci.annotations.get("description", "") or ""
        # Get description from the schema class itself
        cls = schema_view().get_class(eci.cls_name)
        if cls and cls.description:
            desc = cls.description.strip()
        lines.append(f"### {eci.export_name}")
        if desc:
            lines.append(desc)
        lines.append("Columns:")
        for col_name, attr in eci.attributes.items():
            if attr.identifier:
                continue
            type_str = _duckdb_type_str(attr.range, attr.multivalued)
            desc_part = f" — {attr.description}" if attr.description else ""
            lines.append(f"  {col_name} ({type_str}){desc_part}")
        lines.append("")

    return "\n".join(lines)
