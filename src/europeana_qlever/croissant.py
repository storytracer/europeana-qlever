"""Croissant metadata generation for exported Parquet files.

Generates a `croissant.json` file alongside the Parquet exports using the
`mlcroissant` library.  All table/column metadata is derived from the
LinkML schema (``edm_parquet.yaml``).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import mlcroissant as mlc

from . import __version__,  display
from .schema_loader import export_classes, item_fields


# ---------------------------------------------------------------------------
# Range → Croissant DataType mapping
# ---------------------------------------------------------------------------

_CROISSANT_DTYPE: dict[str, mlc.DataType] = {
    "string": mlc.DataType.TEXT,
    "uri": mlc.DataType.URL,
    "integer": mlc.DataType.INTEGER,
    "float": mlc.DataType.FLOAT,
    "boolean": mlc.DataType.BOOL,
    "EdmType": mlc.DataType.TEXT,
    "ReuseLevel": mlc.DataType.TEXT,
}

# Struct types → sub-field definitions
_STRUCT_SUBFIELDS: dict[str, list[tuple[str, str, mlc.DataType]]] = {
    # range → [(field_name, description, data_type), ...]
    "LangValue": [
        ("value", "Text value.", mlc.DataType.TEXT),
        ("lang", "Language tag (e.g. 'en', 'de', '' for untagged).", mlc.DataType.TEXT),
    ],
    "LabeledEntity": [
        ("label", "Resolved entity label.", mlc.DataType.TEXT),
        ("uri", "Entity URI.", mlc.DataType.URL),
    ],
    "NamedEntity": [
        ("name", "Resolved display name.", mlc.DataType.TEXT),
        ("uri", "Entity URI (NULL for literal-only values).", mlc.DataType.URL),
    ],
}


# ---------------------------------------------------------------------------
# Table descriptions for exports not covered by Item schema
# ---------------------------------------------------------------------------

_TABLE_DESCRIPTIONS: dict[str, str] = {
    "agents_core": "Contextual agent entities (persons and organisations) with preferred labels.",
    "agents_links": "Multi-valued and linked properties for agents (sameAs, altLabel, etc.).",
    "concepts_core": "Contextual concept entities (subjects, types) with preferred labels.",
    "concepts_links": "Multi-valued and linked properties for concepts.",
    "places_core": "Contextual place entities with preferred labels and coordinates.",
    "places_links": "Multi-valued and linked properties for places.",
    "timespans_core": "Contextual timespan entities with preferred labels.",
    "timespans_links": "Multi-valued and linked properties for timespans.",
    "institutions": "Organisation names, countries, and roles.",
    "web_resources": "Web resource metadata (MIME type, dimensions, IIIF) per item.",
}


# ---------------------------------------------------------------------------
# SHA-256 helper
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1_048_576), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Field builders
# ---------------------------------------------------------------------------

def _croissant_dtype(range_name: str | None) -> mlc.DataType:
    """Map a LinkML range to a Croissant DataType."""
    return _CROISSANT_DTYPE.get(range_name or "string", mlc.DataType.TEXT)


def _build_item_fields(
    ctx: mlc.Context,
    file_object_id: str,
) -> list[mlc.Field]:
    """Build Croissant Field nodes for items_resolved from the schema."""
    fields: list[mlc.Field] = []
    record_id = "items_resolved"

    for col_name, attr in item_fields().items():
        field_id = f"{record_id}/{col_name}"
        struct_defs = _STRUCT_SUBFIELDS.get(attr.range or "")

        if attr.multivalued and struct_defs:
            # Nested struct list → parent field with sub_fields
            sub_fields = [
                mlc.Field(
                    ctx=ctx,
                    id=f"{field_id}/{sf_name}",
                    name=sf_name,
                    description=sf_desc,
                    data_types=[sf_dtype],
                    source=mlc.Source(
                        ctx=ctx,
                        file_object=file_object_id,
                        extract=mlc.Extract(column=f"{col_name}/{sf_name}"),
                    ),
                )
                for sf_name, sf_desc, sf_dtype in struct_defs
            ]
            fields.append(mlc.Field(
                ctx=ctx,
                id=field_id,
                name=col_name,
                description=attr.description or col_name,
                data_types=[mlc.DataType.TEXT],
                repeated=True,
                source=mlc.Source(
                    ctx=ctx,
                    file_object=file_object_id,
                    extract=mlc.Extract(column=col_name),
                ),
                sub_fields=sub_fields,
            ))
        elif attr.multivalued:
            # Simple list
            fields.append(mlc.Field(
                ctx=ctx,
                id=field_id,
                name=col_name,
                description=attr.description or col_name,
                data_types=[_croissant_dtype(attr.range)],
                repeated=True,
                source=mlc.Source(
                    ctx=ctx,
                    file_object=file_object_id,
                    extract=mlc.Extract(column=col_name),
                ),
            ))
        else:
            # Scalar
            fields.append(mlc.Field(
                ctx=ctx,
                id=field_id,
                name=col_name,
                description=attr.description or col_name,
                data_types=[_croissant_dtype(attr.range)],
                source=mlc.Source(
                    ctx=ctx,
                    file_object=file_object_id,
                    extract=mlc.Extract(column=col_name),
                ),
            ))

    return fields


def _build_simple_fields(
    ctx: mlc.Context,
    record_id: str,
    file_object_id: str,
    parquet_path: Path,
) -> list[mlc.Field]:
    """Build Croissant Field nodes for a non-Item table by reading its Parquet schema."""
    import pyarrow.parquet as pq

    pq_schema = pq.read_schema(parquet_path)
    fields: list[mlc.Field] = []

    # Try to get schema descriptions from export_classes
    info = export_classes().get(record_id)
    attr_map = info.attributes if info else {}

    for pq_field in pq_schema:
        col_name = pq_field.name
        attr = attr_map.get(col_name)
        desc = (attr.description if attr and attr.description else col_name)

        # Infer Croissant DataType from PyArrow type
        pa_str = str(pq_field.type)
        if "int" in pa_str:
            dtype = mlc.DataType.INTEGER
        elif "float" in pa_str or "double" in pa_str:
            dtype = mlc.DataType.FLOAT
        elif "bool" in pa_str:
            dtype = mlc.DataType.BOOL
        else:
            dtype = mlc.DataType.TEXT

        fields.append(mlc.Field(
            ctx=ctx,
            id=f"{record_id}/{col_name}",
            name=col_name,
            description=desc,
            data_types=[dtype],
            source=mlc.Source(
                ctx=ctx,
                file_object=file_object_id,
                extract=mlc.Extract(column=col_name),
            ),
        ))

    return fields


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------

# Tables to include in Croissant (in display order)
_CROISSANT_TABLES = [
    "items_resolved",
    "agents_core", "agents_links",
    "concepts_core", "concepts_links",
    "places_core", "places_links",
    "timespans_core", "timespans_links",
    "institutions",
    "web_resources",
]


def generate_croissant(exports_dir: Path) -> Path:
    """Generate ``croissant.json`` from exported Parquet files.

    Reads the LinkML schema for column metadata and the Parquet files for
    checksums and column schemas.  Returns the path to the generated file.
    """
    ctx = mlc.Context()
    distributions: list[mlc.FileObject] = []
    record_sets: list[mlc.RecordSet] = []

    for table_name in _CROISSANT_TABLES:
        parquet_path = exports_dir / f"{table_name}.parquet"
        if not parquet_path.exists():
            continue

        file_obj_id = f"{table_name}-parquet"
        table_desc = _TABLE_DESCRIPTIONS.get(table_name, "")

        # For items_resolved, use the Item class description from schema
        if table_name == "items_resolved":
            info = export_classes().get("items_resolved")
            table_desc = (
                "Fully resolved one-row-per-item export. "
                "The flagship denormalized Parquet with all metadata, "
                "entity labels, and web resource info per item."
            )

        display.console.print(f"  [dim]{table_name}[/dim]: computing checksum…")
        sha = _sha256(parquet_path)
        size_bytes = parquet_path.stat().st_size

        distributions.append(mlc.FileObject(
            ctx=ctx,
            id=file_obj_id,
            name=f"{table_name}.parquet",
            content_url=f"{table_name}.parquet",
            encoding_formats=[mlc.EncodingFormat.PARQUET],
            description=table_desc,
            sha256=sha,
            content_size=f"{size_bytes} B",
        ))

        # Build fields
        if table_name == "items_resolved":
            fields = _build_item_fields(ctx, file_obj_id)
        else:
            fields = _build_simple_fields(
                ctx, table_name, file_obj_id, parquet_path
            )

        record_sets.append(mlc.RecordSet(
            ctx=ctx,
            id=table_name,
            name=table_name,
            description=table_desc,
            fields=fields,
        ))

    metadata = mlc.Metadata(
        ctx=ctx,
        name="europeana-edm-exports",
        description=(
            "Europeana EDM cultural heritage metadata (~66M items) "
            "exported as Parquet files from the QLever SPARQL engine. "
            "Covers the full Europeana Data Model: items with titles, "
            "descriptions, subjects, creators, rights, and contextual "
            "entities (agents, concepts, places, timespans)."
        ),
        url="https://github.com/storytracer/europeana-qlever",
        license="https://creativecommons.org/publicdomain/zero/1.0/",
        version=__version__,
        date_published=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        distribution=distributions,
        record_sets=record_sets,
    )

    output_path = exports_dir / "croissant.json"
    jsonld = metadata.to_json()
    output_path.write_text(json.dumps(jsonld, indent=2, ensure_ascii=False, default=str))

    display.console.print(
        f"[green]Croissant metadata written to {output_path}[/green]"
    )
    return output_path
