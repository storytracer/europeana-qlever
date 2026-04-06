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
            annotations=_annots(attr),
        )
    return result


# ---------------------------------------------------------------------------
# PyArrow schema generation
# ---------------------------------------------------------------------------


@functools.cache
def pyarrow_schema(export_name: str):
    """Return a static ``pyarrow.Schema`` for the given export.

    Covers all registered exports: items_resolved, items_core, all
    items_* base tables, entity core/links, web_resources, institutions,
    and summary exports.  Raises ``KeyError`` if the export is unknown.
    """
    import pyarrow as pa

    # --- Range → PyArrow type mappings ---
    _SCALAR: dict[str, pa.DataType] = {
        "string": pa.string(),
        "uri": pa.string(),
        "integer": pa.int64(),
        "float": pa.float64(),
        "boolean": pa.bool_(),
        "EdmType": pa.string(),
        "ReuseLevel": pa.string(),
    }

    _MULTIVALUED: dict[str, pa.DataType] = {
        "LangValue": pa.list_(
            pa.struct([("value", pa.string()), ("lang", pa.string())])
        ),
        "LabeledEntity": pa.list_(
            pa.struct([("label", pa.string()), ("uri", pa.string())])
        ),
        "NamedEntity": pa.list_(
            pa.struct([("name", pa.string()), ("uri", pa.string())])
        ),
        "string": pa.list_(pa.string()),
    }

    def _field_type(attr: AttributeInfo) -> pa.DataType:
        rng = attr.range or "string"
        if attr.multivalued:
            return _MULTIVALUED.get(rng, pa.list_(pa.string()))
        return _SCALAR.get(rng, pa.string())

    # --- 1. items_resolved ---
    if export_name == "items_resolved":
        fields = item_fields()
        return pa.schema([pa.field(n, _field_type(a)) for n, a in fields.items()])

    # --- 2. items_core (scalar Item fields, SPARQL variable names) ---
    if export_name == "items_core":
        fields = item_fields()
        cols = []
        for name, attr in fields.items():
            if attr.multivalued or attr.annotations.get("computed") == "true":
                continue
            # Exclude web_resource-sourced fields (those come from web_resources export)
            if attr.annotations.get("rdf_source") == "web_resource":
                continue
            # In the base table, column names are SPARQL variable names
            col_name = sparql_var("Item", name)
            cols.append(pa.field(col_name, _SCALAR.get(attr.range or "string", pa.string())))
        return pa.schema(cols)

    # --- 3. items_* base tables (derived from query_pattern) ---
    fields = item_fields()
    for name, attr in fields.items():
        bt = attr.annotations.get("base_table")
        if bt == export_name:
            pattern = attr.annotations.get("query_pattern", "")
            # SPARQL variable names follow the query.py conventions:
            curie = slot_curie("Item", name)
            local = curie.split(":")[1] if curie and ":" in curie else name
            if pattern == "lang_tagged":
                # Variable is the DC local name (e.g., 'title' from dc:title)
                return pa.schema([
                    pa.field("item", pa.string()),
                    pa.field(local, pa.string()),
                    pa.field("lang", pa.string()),
                ])
            elif pattern == "iri_or_literal":
                # Variable is {singular}_value (e.g., 'subject_value')
                stem = name.rstrip("s")
                return pa.schema([
                    pa.field("item", pa.string()),
                    pa.field(f"{stem}_value", pa.string()),
                    pa.field("is_iri", pa.bool_()),
                ])
            elif pattern == "simple_literal":
                # Variable is singular form, except dc_rights stays as-is
                var_name = name.rstrip("s") if name != "dc_rights" else "dc_rights"
                return pa.schema([
                    pa.field("item", pa.string()),
                    pa.field(var_name, pa.string()),
                ])

    # --- 4. Entity core exports (*_core) ---
    for etype in entity_classes():
        plural = etype.lower() + "s"
        if export_name == f"{plural}_core":
            id_col = entity_id_column(plural)
            core = entity_core_fields(plural)
            cols = [pa.field(id_col, pa.string())]
            cols.append(pa.field("pref_label", pa.string()))
            cols.append(pa.field("pref_label_lang", pa.string()))
            for fname, fattr in core.items():
                if fname in ("pref_label", "pref_label_lang"):
                    continue
                cols.append(pa.field(fname, _SCALAR.get(fattr.range or "string", pa.string())))
            return pa.schema(cols)

    # --- 5. Entity links exports (*_links) ---
    for etype in entity_classes():
        plural = etype.lower() + "s"
        if export_name == f"{plural}_links":
            id_col = entity_id_column(plural)
            return pa.schema([
                pa.field(id_col, pa.string()),
                pa.field("property", pa.string()),
                pa.field("value", pa.string()),
                pa.field("lang", pa.string()),
            ])

    # --- 6. web_resources ---
    if export_name == "web_resources":
        return pa.schema([
            pa.field("item", pa.string()),
            pa.field("url", pa.string()),
            pa.field("mime", pa.string()),
            pa.field("width", pa.string()),
            pa.field("height", pa.string()),
            pa.field("bytes", pa.string()),
            pa.field("wr_rights", pa.string()),
            pa.field("has_service", pa.bool_()),
        ])

    # --- 7. institutions ---
    if export_name == "institutions":
        return pa.schema([
            pa.field("org", pa.string()),
            pa.field("name", pa.string()),
            pa.field("lang", pa.string()),
            pa.field("acronym", pa.string()),
            pa.field("country", pa.string()),
            pa.field("role", pa.string()),
            pa.field("wikidata", pa.string()),
        ])

    # --- 8. Summary and misc exports ---
    _SUMMARY_SCHEMAS: dict[str, list[tuple[str, pa.DataType]]] = {
        "items_by_country": [("country", pa.string()), ("count", pa.int64())],
        "items_by_type": [("type", pa.string()), ("count", pa.int64())],
        "items_by_type_and_country": [
            ("type", pa.string()), ("country", pa.string()), ("count", pa.int64()),
        ],
        "items_by_type_and_language": [
            ("type", pa.string()), ("language", pa.string()), ("count", pa.int64()),
        ],
        "items_by_language": [("language", pa.string()), ("count", pa.int64())],
        "items_by_institution": [
            ("dataProvider", pa.string()), ("institutionName", pa.string()),
            ("count", pa.int64()),
        ],
        "items_by_aggregator": [
            ("provider", pa.string()), ("aggregatorName", pa.string()),
            ("count", pa.int64()),
        ],
        "items_by_year": [("year", pa.string()), ("count", pa.int64())],
        "items_by_rights_uri": [("rights", pa.string()), ("count", pa.int64())],
        "items_by_reuse_level": [("reuse_level", pa.string()), ("count", pa.int64())],
        "items_by_type_and_reuse_level": [
            ("type", pa.string()), ("reuse_level", pa.string()), ("count", pa.int64()),
        ],
        "items_by_country_and_reuse_level": [
            ("country", pa.string()), ("reuse_level", pa.string()), ("count", pa.int64()),
        ],
        "items_by_language_and_reuse_level": [
            ("language", pa.string()), ("reuse_level", pa.string()), ("count", pa.int64()),
        ],
        "items_by_completeness": [
            ("completeness", pa.int64()), ("type", pa.string()), ("count", pa.int64()),
        ],
        "content_availability": [
            ("type", pa.string()), ("reuse_level", pa.string()),
            ("has_direct_url", pa.bool_()), ("has_iiif", pa.bool_()),
            ("count", pa.int64()),
        ],
        "mime_type_distribution": [("mime", pa.string()), ("count", pa.int64())],
        "geolocated_places": [
            ("place", pa.string()), ("name", pa.string()),
            ("lat", pa.float64()), ("lon", pa.float64()),
        ],
        "iiif_availability": [
            ("dataProvider", pa.string()), ("institutionName", pa.string()),
            ("iiif_items", pa.int64()),
        ],
        "texts_by_type": [("dcType", pa.string()), ("count", pa.int64())],
    }

    if export_name in _SUMMARY_SCHEMAS:
        cols = _SUMMARY_SCHEMAS[export_name]
        return pa.schema([pa.field(n, t) for n, t in cols])

    raise KeyError(f"Unknown export: {export_name!r}")
