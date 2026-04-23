"""Croissant metadata generation for exported Parquet files.

Generates a ``croissant.json`` file alongside the Parquet exports using
the ``mlcroissant`` library.  All table and column metadata is derived
from the LinkML schema and — for list/struct columns — from the
exported Parquet file itself.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import mlcroissant as mlc
import pyarrow as pa
import pyarrow.parquet as pq

from . import __version__, display
from .schema_loader import export_classes, schema_view


# ---------------------------------------------------------------------------
# Range → Croissant DataType mapping
# ---------------------------------------------------------------------------

_CROISSANT_DTYPE: dict[str, mlc.DataType] = {
    "string": mlc.DataType.TEXT,
    "uri": mlc.DataType.URL,
    "integer": mlc.DataType.INTEGER,
    "float": mlc.DataType.FLOAT,
    "boolean": mlc.DataType.BOOL,
    "ReuseLevel": mlc.DataType.TEXT,
    "RightsFamily": mlc.DataType.TEXT,
    "EntityClass": mlc.DataType.TEXT,
    "Authority": mlc.DataType.TEXT,
}


# Struct-type sub-field definitions (for merged_items list-of-struct columns).
_STRUCT_SUBFIELDS: dict[str, list[tuple[str, str, mlc.DataType]]] = {
    "LangValueX": [
        ("x_value", "Text value.", mlc.DataType.TEXT),
        ("x_value_lang", "Language tag (e.g. 'en', 'de', '' for untagged).", mlc.DataType.TEXT),
    ],
    "LabeledEntityX": [
        ("x_value", "Raw value (IRI or literal string).", mlc.DataType.TEXT),
        ("x_label", "Resolved entity label (falls back to x_value).", mlc.DataType.TEXT),
        ("x_value_is_iri", "Whether x_value is an IRI.", mlc.DataType.BOOL),
    ],
    "NamedEntityX": [
        ("x_value", "Raw value (IRI or literal string).", mlc.DataType.TEXT),
        ("x_name", "Resolved display name (falls back to x_value).", mlc.DataType.TEXT),
        ("x_value_is_iri", "Whether x_value is an IRI.", mlc.DataType.BOOL),
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1_048_576), b""):
            h.update(chunk)
    return h.hexdigest()


def _croissant_dtype(range_name: str | None) -> mlc.DataType:
    return _CROISSANT_DTYPE.get(range_name or "string", mlc.DataType.TEXT)


def _pa_to_croissant_dtype(pa_field: pa.Field) -> mlc.DataType:
    """Infer a Croissant DataType from a PyArrow field."""
    pa_str = str(pa_field.type)
    if "int" in pa_str:
        return mlc.DataType.INTEGER
    if "float" in pa_str or "double" in pa_str:
        return mlc.DataType.FLOAT
    if "bool" in pa_str:
        return mlc.DataType.BOOL
    return mlc.DataType.TEXT


def _build_fields_from_schema(
    ctx: mlc.Context, record_id: str, file_object_id: str, attrs: dict
) -> list[mlc.Field]:
    """Build Croissant Fields from LinkML class attributes (alphabetical)."""
    fields: list[mlc.Field] = []
    for col_name in sorted(attrs.keys()):
        attr = attrs[col_name]
        field_id = f"{record_id}/{col_name}"
        struct_defs = _STRUCT_SUBFIELDS.get(attr.range or "")

        if attr.multivalued and struct_defs:
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


def _build_fields_from_parquet(
    ctx: mlc.Context, record_id: str, file_object_id: str, parquet_path: Path
) -> list[mlc.Field]:
    """Build Croissant Fields by inspecting the Parquet schema directly."""
    pq_schema = pq.read_schema(parquet_path)
    fields: list[mlc.Field] = []
    for pq_field in pq_schema:
        fields.append(mlc.Field(
            ctx=ctx,
            id=f"{record_id}/{pq_field.name}",
            name=pq_field.name,
            description=pq_field.name,
            data_types=[_pa_to_croissant_dtype(pq_field)],
            source=mlc.Source(
                ctx=ctx,
                file_object=file_object_id,
                extract=mlc.Extract(column=pq_field.name),
            ),
        ))
    return fields


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------


def generate_croissant(exports_dir: Path) -> Path:
    """Generate ``croissant.json`` describing all exported Parquet files."""
    ctx = mlc.Context()
    distributions: list[mlc.FileObject] = []
    record_sets: list[mlc.RecordSet] = []

    # Enumerate every final export from the schema, in deterministic order.
    exports = export_classes()
    ordered_names = sorted(exports.keys())

    for table_name in ordered_names:
        parquet_path = exports_dir / f"{table_name}.parquet"
        if not parquet_path.exists():
            continue

        info = exports[table_name]
        cls = schema_view().get_class(info.cls_name)
        table_desc = (cls.description or "").strip() if cls else ""

        file_obj_id = f"{table_name}-parquet"

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

        # For tables with declared attributes (all except links_union),
        # build from the schema so list/struct columns are properly
        # typed.  links_union tables have a fixed 5-column schema —
        # build from the Parquet directly.
        if info.export_type == "links_union":
            fields = _build_fields_from_parquet(ctx, table_name, file_obj_id, parquet_path)
        else:
            fields = _build_fields_from_schema(ctx, table_name, file_obj_id, info.attributes)

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
            "Covers the full Europeana Data Model with class boundaries "
            "preserved in raw values_*/links_* tables, and a denormalized "
            "merged_items table for user-friendly analysis."
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
