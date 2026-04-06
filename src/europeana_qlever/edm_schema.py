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
