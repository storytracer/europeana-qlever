"""DuckDB composition SQL for the europeana-qlever export pipeline.

Composable exports (``merged``, ``group``, ``map``) are built from raw
Parquet files (values_*, links_*/Hive-partitioned) via a sequence of
DuckDB ``ComposeStep``s.  The final step of each export is written to
Parquet via a COPY wrapper by :class:`~.export.ExportPipeline`.

SQL templates use ``{exports_dir}`` — the absolute path to the exports
directory — replaced at execution time.
"""

from __future__ import annotations

from dataclasses import dataclass

from .rights import duckdb_family_case, duckdb_is_open_case, duckdb_label_case
from .schema_loader import (
    authority_sql,
    export_classes,
    reuse_level_sql,
)


# ---------------------------------------------------------------------------
# ComposeStep
# ---------------------------------------------------------------------------


@dataclass
class ComposeStep:
    """A single step in a multi-step DuckDB composition."""

    name: str
    sql: str
    is_final: bool = False


def _links_read(table_name: str) -> str:
    """DuckDB expression reading a Hive-partitioned links directory."""
    return (
        f"read_parquet('{{exports_dir}}/{table_name}/**/*.parquet', "
        f"hive_partitioning=true)"
    )


# ---------------------------------------------------------------------------
# merged_items — the flagship denormalized CHO export
# ---------------------------------------------------------------------------


# Multi-valued aggregation rules for merged_items.  Each entry:
#   (merged_col, source_property, proxy_type, struct_kind, label_table)
# where struct_kind is one of:
#   "lang"     — LIST<STRUCT<x_value, x_value_lang>>
#   "labeled"  — LIST<STRUCT<x_value, x_label, x_value_is_iri>>
#   "named"    — LIST<STRUCT<x_value, x_name, x_value_is_iri>>
#   "simple"   — LIST<VARCHAR>
# label_table is the temp table used to resolve IRI → label.  None for
# simple/lang kinds.
_AGG_RULES: list[tuple[str, str, str, str, str | None]] = [
    # LangValue (no resolution)
    ("x_dc_title",       "v_dc_title",       "provider",  "lang",    None),
    ("x_dc_description", "v_dc_description", "provider",  "lang",    None),

    # LabeledEntity (resolve against concepts / places)
    ("x_dc_subject",     "v_dc_subject",     "provider",  "labeled", "labels_concept"),
    ("x_dc_type",        "v_dc_type",        "provider",  "labeled", "labels_concept"),
    ("x_dc_format",      "v_dc_format",      "provider",  "labeled", "labels_concept"),
    ("x_edm_hasType",    "v_edm_hasType",    "provider",  "labeled", "labels_concept"),
    ("x_dcterms_spatial","v_dcterms_spatial","provider",  "labeled", "labels_place"),

    # NamedEntity (resolve against agents)
    ("x_dc_creator",     "v_dc_creator",     "provider",  "named",   "labels_agent"),
    ("x_dc_contributor", "v_dc_contributor", "provider",  "named",   "labels_agent"),
    ("x_dc_publisher",   "v_dc_publisher",   "provider",  "named",   "labels_agent"),

    # Simple lists
    ("x_dc_date",        "v_dc_date",        "provider",  "simple",  None),
    ("x_dc_identifier",  "v_dc_identifier",  "provider",  "simple",  None),
    ("x_dc_language",    "v_dc_language",    "provider",  "simple",  None),
    ("x_dc_rights",      "v_dc_rights",      "provider",  "simple",  None),
    ("x_edm_year",       "v_edm_year",       "europeana", "simple",  None),
]


def _entity_label_step(
    temp_name: str, source_parquet: str, label_col: str = "v_skos_prefLabel"
) -> ComposeStep:
    """Build an IRI → English-preferred label map from a values_* entity table."""
    return ComposeStep(
        name=temp_name,
        sql=(
            f"CREATE TEMP TABLE {temp_name} AS\n"
            f"SELECT k_iri,\n"
            f"       COALESCE(\n"
            f"           MAX({label_col}) FILTER (WHERE x_prefLabel_lang = 'en'),\n"
            f"           MAX({label_col})\n"
            f"       ) AS label\n"
            f"FROM read_parquet('{{exports_dir}}/{source_parquet}.parquet')\n"
            f"GROUP BY k_iri"
        ),
    )


def _agg_step(
    merged_col: str,
    source_property: str,
    proxy_type: str,
    struct_kind: str,
    label_table: str | None,
    *,
    chunk_filter: bool = False,
) -> ComposeStep:
    """Build one aggregation temp table for a multi-valued merged_items column.

    When ``chunk_filter`` is True, the step is written with
    ``CREATE OR REPLACE`` so it can be rebuilt per chunk; narrowing to
    the current chunk cascades through the already-filtered
    ``proxy_cho`` temp table.
    """
    temp_name = f"agg_{merged_col}"
    proxy_filter = f"pc.proxy_type = '{proxy_type}'"
    create = "CREATE OR REPLACE TEMP TABLE" if chunk_filter else "CREATE TEMP TABLE"

    if struct_kind == "lang":
        agg_expr = (
            "LIST({x_value: l.x_value, x_value_lang: l.x_value_lang}) "
            f"AS {merged_col}"
        )
        join_label = ""
    elif struct_kind == "labeled":
        assert label_table
        agg_expr = (
            "LIST({"
            "x_value: l.x_value, "
            f"x_label: COALESCE(lab.label, l.x_value), "
            "x_value_is_iri: l.x_value_is_iri"
            "}) "
            f"AS {merged_col}"
        )
        join_label = (
            f"LEFT JOIN {label_table} lab ON l.x_value_is_iri AND l.x_value = lab.k_iri"
        )
    elif struct_kind == "named":
        assert label_table
        agg_expr = (
            "LIST({"
            "x_value: l.x_value, "
            f"x_name: COALESCE(lab.label, l.x_value), "
            "x_value_is_iri: l.x_value_is_iri"
            "}) "
            f"AS {merged_col}"
        )
        join_label = (
            f"LEFT JOIN {label_table} lab ON l.x_value_is_iri AND l.x_value = lab.k_iri"
        )
    elif struct_kind == "simple":
        agg_expr = f"LIST(l.x_value) AS {merged_col}"
        join_label = ""
    else:
        raise ValueError(f"Unknown struct kind: {struct_kind!r}")

    sql = (
        f"{create} {temp_name} AS\n"
        f"SELECT pc.k_iri_cho AS k_iri,\n"
        f"       {agg_expr}\n"
        f"FROM {_links_read('links_ore_Proxy')} l\n"
        f"JOIN proxy_cho pc ON l.k_iri = pc.k_iri\n"
        f"{join_label}\n"
        f"WHERE l.x_property = '{source_property}' AND {proxy_filter}\n"
        f"GROUP BY pc.k_iri_cho"
    )
    return ComposeStep(name=temp_name, sql=sql)


_PROVIDER_AGG_COLS = [
    "v_edm_dataProvider",
    "v_edm_isShownAt",
    "v_edm_isShownBy",
    "v_edm_object",
    "v_edm_provider",
    "v_edm_rights",
]


_EUROPEANA_AGG_COLS = [
    "v_edm_completeness",
    "v_edm_country",
    "v_edm_datasetName",
    "v_edm_landingPage",
    "v_edm_preview",
]


def _provider_agg_step(*, chunk_filter: bool = False) -> ComposeStep:
    """Collapse values_ore_Aggregation to one row per CHO.

    A CHO may have multiple ore:Aggregations (different providers) or
    the upstream SPARQL scan may emit duplicate rows due to
    multi-valued property cross-products. ``DISTINCT ON (k_iri_cho)``
    picks a deterministic representative (the one with the
    lexicographically smallest aggregation IRI) so downstream JOINs
    cannot fan out.
    """
    create = "CREATE OR REPLACE TEMP TABLE" if chunk_filter else "CREATE TEMP TABLE"
    chunk_join = (
        "SEMI JOIN chunk_chos cc ON a.k_iri_cho = cc.k_iri\n"
        if chunk_filter else ""
    )
    cols = ",\n       ".join(f"a.{c} AS {c}" for c in _PROVIDER_AGG_COLS)
    sql = (
        f"{create} provider_agg AS\n"
        "SELECT DISTINCT ON (a.k_iri_cho)\n"
        "       a.k_iri_cho AS k_iri,\n"
        f"       {cols}\n"
        "FROM read_parquet('{exports_dir}/values_ore_Aggregation.parquet') a\n"
        f"{chunk_join}"
        "ORDER BY a.k_iri_cho, a.k_iri"
    )
    return ComposeStep(name="provider_agg", sql=sql)


def _europeana_agg_step(*, chunk_filter: bool = False) -> ComposeStep:
    """Collapse values_edm_EuropeanaAggregation to one row per CHO.

    Same rationale as ``provider_agg``: guarantees 1:1 cardinality
    with the CHO base so downstream LEFT JOINs cannot produce
    duplicate rows.
    """
    create = "CREATE OR REPLACE TEMP TABLE" if chunk_filter else "CREATE TEMP TABLE"
    chunk_join = (
        "SEMI JOIN chunk_chos cc ON e.k_iri_cho = cc.k_iri\n"
        if chunk_filter else ""
    )
    cols = ",\n       ".join(f"e.{c} AS {c}" for c in _EUROPEANA_AGG_COLS)
    sql = (
        f"{create} europeana_agg AS\n"
        "SELECT DISTINCT ON (e.k_iri_cho)\n"
        "       e.k_iri_cho AS k_iri,\n"
        f"       {cols}\n"
        "FROM read_parquet('{exports_dir}/values_edm_EuropeanaAggregation.parquet') e\n"
        f"{chunk_join}"
        "ORDER BY e.k_iri_cho, e.k_iri"
    )
    return ComposeStep(name="europeana_agg", sql=sql)


def _primary_wr_step() -> ComposeStep:
    """Web-resource scalars for each CHO's primary WR.

    Reads from the already-1:1 ``provider_agg`` temp table so the join
    through ``v_edm_isShownBy`` is guaranteed at most one row per CHO.
    A defensive ``DISTINCT ON (k_iri)`` wrapper collapses any duplicate
    WebResource rows that might slip through from upstream.
    """
    wr_cols = [
        "v_ebucore_audioChannelNumber", "v_ebucore_bitRate", "v_ebucore_duration",
        "v_ebucore_fileByteSize", "v_ebucore_frameRate", "v_ebucore_hasMimeType",
        "v_ebucore_height", "v_ebucore_orientation", "v_ebucore_sampleRate",
        "v_ebucore_sampleSize", "v_ebucore_width",
        "v_edm_codecName", "v_edm_hasColorSpace",
        "v_edm_pointCount", "v_edm_polygonCount", "v_edm_spatialResolution",
        "v_edm_vertexCount",
        "v_schema_digitalSourceType",
    ]
    select_cols = ",\n       ".join(f"wr.{c} AS {c}" for c in wr_cols)
    sql = (
        "CREATE TEMP TABLE primary_wr AS\n"
        f"SELECT DISTINCT ON (pa.k_iri)\n"
        f"       pa.k_iri AS k_iri,\n"
        f"       {select_cols},\n"
        f"       (svc.k_iri_webresource IS NOT NULL) AS x_has_iiif\n"
        "FROM provider_agg pa\n"
        "JOIN read_parquet('{exports_dir}/values_edm_WebResource.parquet') wr\n"
        "     ON pa.v_edm_isShownBy = wr.k_iri\n"
        "LEFT JOIN (\n"
        "    SELECT DISTINCT k_iri_webresource\n"
        "    FROM read_parquet('{exports_dir}/values_svcs_Service.parquet')\n"
        ") svc ON wr.k_iri = svc.k_iri_webresource\n"
        "ORDER BY pa.k_iri, wr.k_iri"
    )
    return ComposeStep(name="primary_wr", sql=sql)


def _proxy_cho_step(*, chunk_filter: bool = False) -> ComposeStep:
    """Map proxy URIs → (CHO URI, provider|europeana) for joining with links_ore_Proxy.

    When ``chunk_filter`` is True, rows are narrowed to proxies whose CHO
    lies in the current ``chunk_chos`` temp table; this cascades through
    every downstream agg_* step without further changes.
    """
    if chunk_filter:
        sql = (
            "CREATE OR REPLACE TEMP TABLE proxy_cho AS\n"
            "SELECT p.k_iri, p.k_iri_cho,\n"
            "       CASE WHEN p.v_edm_europeanaProxy = 'true' THEN 'europeana' ELSE 'provider' END AS proxy_type\n"
            "FROM read_parquet('{exports_dir}/values_ore_Proxy.parquet') p\n"
            "SEMI JOIN chunk_chos cc ON p.k_iri_cho = cc.k_iri"
        )
    else:
        sql = (
            "CREATE TEMP TABLE proxy_cho AS\n"
            "SELECT k_iri, k_iri_cho,\n"
            "       CASE WHEN v_edm_europeanaProxy = 'true' THEN 'europeana' ELSE 'provider' END AS proxy_type\n"
            "FROM read_parquet('{exports_dir}/values_ore_Proxy.parquet')"
        )
    return ComposeStep(name="proxy_cho", sql=sql)


def _cho_numbered_step() -> ComposeStep:
    """Full CHO list with a stable ROW_NUMBER. Built once per chunked run."""
    sql = (
        "CREATE TEMP TABLE cho_numbered AS\n"
        "SELECT k_iri, ROW_NUMBER() OVER () AS rn\n"
        "FROM read_parquet('{exports_dir}/values_edm_ProvidedCHO.parquet')"
    )
    return ComposeStep(name="cho_numbered", sql=sql)


def _chunk_chos_step() -> ComposeStep:
    """CHO IRIs for the current chunk. ``{chunk_start}`` / ``{chunk_end}``
    are substituted by the execution layer per iteration."""
    sql = (
        "CREATE OR REPLACE TEMP TABLE chunk_chos AS\n"
        "SELECT k_iri FROM cho_numbered\n"
        "WHERE rn > {chunk_start} AND rn <= {chunk_end}"
    )
    return ComposeStep(name="chunk_chos", sql=sql)


def _provider_proxy_scalars_step(*, chunk_filter: bool = False) -> ComposeStep:
    create = "CREATE OR REPLACE TEMP TABLE" if chunk_filter else "CREATE TEMP TABLE"
    chunk_join = (
        "SEMI JOIN chunk_chos cc ON p.k_iri_cho = cc.k_iri\n"
        if chunk_filter else ""
    )
    sql = (
        f"{create} provider_proxy_scalars AS\n"
        "SELECT p.k_iri_cho AS k_iri,\n"
        "       MAX(p.v_edm_currentLocation) AS v_edm_currentLocation\n"
        "FROM read_parquet('{exports_dir}/values_ore_Proxy.parquet') p\n"
        f"{chunk_join}"
        "WHERE p.v_edm_europeanaProxy IS NULL OR p.v_edm_europeanaProxy != 'true'\n"
        "GROUP BY p.k_iri_cho"
    )
    return ComposeStep(name="provider_proxy_scalars", sql=sql)


def _europeana_proxy_scalars_step(*, chunk_filter: bool = False) -> ComposeStep:
    create = "CREATE OR REPLACE TEMP TABLE" if chunk_filter else "CREATE TEMP TABLE"
    chunk_join = (
        "SEMI JOIN chunk_chos cc ON p.k_iri_cho = cc.k_iri\n"
        if chunk_filter else ""
    )
    sql = (
        f"{create} europeana_proxy_scalars AS\n"
        "SELECT p.k_iri_cho AS k_iri, MAX(p.v_edm_type) AS v_edm_type\n"
        "FROM read_parquet('{exports_dir}/values_ore_Proxy.parquet') p\n"
        f"{chunk_join}"
        "WHERE p.v_edm_europeanaProxy = 'true'\n"
        "GROUP BY p.k_iri_cho"
    )
    return ComposeStep(name="europeana_proxy_scalars", sql=sql)


def _merged_items_select_parts() -> list[str]:
    """Ordered SELECT column expressions for the merged_items assembly SQL.

    Column aliases reference JOIN aliases used consistently by both the
    one-shot temp-table path and the range-chunked intermediates path:
    ``cho``, ``agg``, ``eagg``, ``primary_wr``, ``provider_proxy_scalars``,
    ``europeana_proxy_scalars``, ``labels_org_dp``, ``labels_org_prov``,
    and one ``agg_{col}`` per multi-valued rule.
    """
    agg_columns = [merged_col for merged_col, _, _, _, _ in _AGG_RULES]

    # Title/description helpers — first English-preferred value
    title_expr = (
        "COALESCE("
        "(list_filter(agg_x_dc_title.x_dc_title, x -> x.x_value_lang = 'en')[1]).x_value, "
        "(agg_x_dc_title.x_dc_title[1]).x_value"
        ") AS x_title"
    )
    title_lang_expr = (
        "COALESCE("
        "(list_filter(agg_x_dc_title.x_dc_title, x -> x.x_value_lang = 'en')[1]).x_value_lang, "
        "(agg_x_dc_title.x_dc_title[1]).x_value_lang"
        ") AS x_title_lang"
    )
    desc_expr = (
        "COALESCE("
        "(list_filter(agg_x_dc_description.x_dc_description, x -> x.x_value_lang = 'en')[1]).x_value, "
        "(agg_x_dc_description.x_dc_description[1]).x_value"
        ") AS x_description"
    )
    desc_lang_expr = (
        "COALESCE("
        "(list_filter(agg_x_dc_description.x_dc_description, x -> x.x_value_lang = 'en')[1]).x_value_lang, "
        "(agg_x_dc_description.x_dc_description[1]).x_value_lang"
        ") AS x_description_lang"
    )

    select_parts: list[str] = []

    select_parts.append("cho.k_iri AS k_iri")

    wr_scalars = [
        "v_ebucore_audioChannelNumber", "v_ebucore_bitRate", "v_ebucore_duration",
        "v_ebucore_fileByteSize", "v_ebucore_frameRate", "v_ebucore_hasMimeType",
        "v_ebucore_height", "v_ebucore_orientation", "v_ebucore_sampleRate",
        "v_ebucore_sampleSize", "v_ebucore_width",
        "v_edm_codecName",
    ]
    for c in wr_scalars:
        select_parts.append(f"primary_wr.{c} AS {c}")

    select_parts.append("eagg.v_edm_completeness AS v_edm_completeness")
    select_parts.append("eagg.v_edm_country AS v_edm_country")
    select_parts.append(
        "provider_proxy_scalars.v_edm_currentLocation AS v_edm_currentLocation"
    )
    select_parts.append("agg.v_edm_dataProvider AS v_edm_dataProvider")
    select_parts.append("eagg.v_edm_datasetName AS v_edm_datasetName")
    select_parts.append("primary_wr.v_edm_hasColorSpace AS v_edm_hasColorSpace")
    select_parts.append("agg.v_edm_isShownAt AS v_edm_isShownAt")
    select_parts.append("agg.v_edm_isShownBy AS v_edm_isShownBy")
    select_parts.append("eagg.v_edm_landingPage AS v_edm_landingPage")
    select_parts.append("agg.v_edm_object AS v_edm_object")
    select_parts.append("primary_wr.v_edm_pointCount AS v_edm_pointCount")
    select_parts.append("primary_wr.v_edm_polygonCount AS v_edm_polygonCount")
    select_parts.append("eagg.v_edm_preview AS v_edm_preview")
    select_parts.append("agg.v_edm_provider AS v_edm_provider")
    select_parts.append("agg.v_edm_rights AS v_edm_rights")
    select_parts.append("primary_wr.v_edm_spatialResolution AS v_edm_spatialResolution")
    select_parts.append("europeana_proxy_scalars.v_edm_type AS v_edm_type")
    select_parts.append("primary_wr.v_edm_vertexCount AS v_edm_vertexCount")
    select_parts.append("primary_wr.v_schema_digitalSourceType AS v_schema_digitalSourceType")

    select_parts.append("labels_org_dp.label AS x_dataProvider_name")

    for col in agg_columns:
        select_parts.append(f"agg_{col}.{col} AS {col}")

    select_parts.append(desc_expr)
    select_parts.append(desc_lang_expr)
    select_parts.append("COALESCE(primary_wr.x_has_iiif, false) AS x_has_iiif")
    select_parts.append(
        "CASE WHEN primary_wr.v_ebucore_width IS NOT NULL "
        "AND primary_wr.v_ebucore_height IS NOT NULL "
        "THEN primary_wr.v_ebucore_width * primary_wr.v_ebucore_height / 1000000.0 END "
        "AS x_megapixels"
    )
    select_parts.append("labels_org_prov.label AS x_provider_name")
    select_parts.append(f"{reuse_level_sql('agg.v_edm_rights')} AS x_reuse_level")
    select_parts.append(title_expr)
    select_parts.append(title_lang_expr)

    def _col_name(line: str) -> str:
        if " AS " in line:
            return line.rsplit(" AS ", 1)[1].strip()
        return line

    select_parts.sort(key=_col_name)
    return select_parts


def _merged_items_joins(source) -> str:
    """LEFT JOIN clauses for merged_items, using a source resolver.

    ``source(name)`` returns the SQL fragment for a logical table —
    either a bare temp-table name (one-shot path) or a
    ``read_parquet('{intermediates_dir}/X.parquet')`` expression
    (range-chunked path).
    """
    agg_columns = [merged_col for merged_col, _, _, _, _ in _AGG_RULES]
    lines = [
        f"LEFT JOIN {source('provider_agg')} agg ON agg.k_iri = cho.k_iri",
        f"LEFT JOIN {source('europeana_agg')} eagg ON eagg.k_iri = cho.k_iri",
        f"LEFT JOIN {source('primary_wr')} primary_wr ON primary_wr.k_iri = cho.k_iri",
        f"LEFT JOIN {source('provider_proxy_scalars')} provider_proxy_scalars "
        f"ON provider_proxy_scalars.k_iri = cho.k_iri",
        f"LEFT JOIN {source('europeana_proxy_scalars')} europeana_proxy_scalars "
        f"ON europeana_proxy_scalars.k_iri = cho.k_iri",
        f"LEFT JOIN {source('labels_org')} labels_org_dp "
        f"ON labels_org_dp.k_iri = agg.v_edm_dataProvider",
        f"LEFT JOIN {source('labels_org')} labels_org_prov "
        f"ON labels_org_prov.k_iri = agg.v_edm_provider",
    ]
    for col in agg_columns:
        lines.append(
            f"LEFT JOIN {source('agg_' + col)} agg_{col} "
            f"ON agg_{col}.k_iri = cho.k_iri"
        )
    return "\n".join(lines)


def _merged_items_final_step() -> ComposeStep:
    """Final assembly step for the one-shot (temp-table) merged_items path."""
    select_str = ",\n  ".join(_merged_items_select_parts())
    joins = _merged_items_joins(lambda name: name)  # logical name == temp table
    final_sql = (
        f"SELECT\n  {select_str}\n"
        "FROM read_parquet('{exports_dir}/values_edm_ProvidedCHO.parquet') cho\n"
        f"{joins}"
    )
    return ComposeStep(name="merged_items_final", sql=final_sql, is_final=True)


# ---------------------------------------------------------------------------
# merged_items — range-chunked composition via on-disk intermediates
# ---------------------------------------------------------------------------


@dataclass
class MergedItemsPrepareSpec:
    """One Phase-A intermediate for range-chunked merged_items composition.

    ``sql`` is a standalone SELECT body (no CREATE/COPY wrapper). The
    runner wraps it in ``COPY (...) TO '{intermediates_dir}/{filename}'``
    and executes in its own DuckDB connection so memory is released
    between steps. SQL may reference ``{exports_dir}`` (raw values_* /
    links_* reads) and ``{intermediates_dir}`` (previously-written
    intermediates).
    """

    name: str
    filename: str
    sql: str


def _prepare_label_sql(
    source_parquet: str, label_col: str = "v_skos_prefLabel"
) -> str:
    return (
        "SELECT k_iri,\n"
        f"       COALESCE(\n"
        f"           MAX({label_col}) FILTER (WHERE x_prefLabel_lang = 'en'),\n"
        f"           MAX({label_col})\n"
        "       ) AS label\n"
        f"FROM read_parquet('{{exports_dir}}/{source_parquet}.parquet')\n"
        "GROUP BY k_iri"
    )


def _prepare_proxy_cho_sql() -> str:
    return (
        "SELECT k_iri, k_iri_cho,\n"
        "       CASE WHEN v_edm_europeanaProxy = 'true' "
        "THEN 'europeana' ELSE 'provider' END AS proxy_type\n"
        "FROM read_parquet('{exports_dir}/values_ore_Proxy.parquet')"
    )


def _prepare_provider_agg_sql() -> str:
    cols = ",\n       ".join(f"a.{c} AS {c}" for c in _PROVIDER_AGG_COLS)
    return (
        "SELECT DISTINCT ON (a.k_iri_cho)\n"
        "       a.k_iri_cho AS k_iri,\n"
        f"       {cols}\n"
        "FROM read_parquet('{exports_dir}/values_ore_Aggregation.parquet') a\n"
        "ORDER BY a.k_iri_cho, a.k_iri"
    )


def _prepare_europeana_agg_sql() -> str:
    cols = ",\n       ".join(f"e.{c} AS {c}" for c in _EUROPEANA_AGG_COLS)
    return (
        "SELECT DISTINCT ON (e.k_iri_cho)\n"
        "       e.k_iri_cho AS k_iri,\n"
        f"       {cols}\n"
        "FROM read_parquet('{exports_dir}/values_edm_EuropeanaAggregation.parquet') e\n"
        "ORDER BY e.k_iri_cho, e.k_iri"
    )


_WR_SCALAR_COLS = [
    "v_ebucore_audioChannelNumber", "v_ebucore_bitRate", "v_ebucore_duration",
    "v_ebucore_fileByteSize", "v_ebucore_frameRate", "v_ebucore_hasMimeType",
    "v_ebucore_height", "v_ebucore_orientation", "v_ebucore_sampleRate",
    "v_ebucore_sampleSize", "v_ebucore_width",
    "v_edm_codecName", "v_edm_hasColorSpace",
    "v_edm_pointCount", "v_edm_polygonCount", "v_edm_spatialResolution",
    "v_edm_vertexCount",
    "v_schema_digitalSourceType",
]


def _prepare_primary_wr_sql() -> str:
    select_cols = ",\n       ".join(f"wr.{c} AS {c}" for c in _WR_SCALAR_COLS)
    return (
        "SELECT DISTINCT ON (pa.k_iri)\n"
        "       pa.k_iri AS k_iri,\n"
        f"       {select_cols},\n"
        "       (svc.k_iri_webresource IS NOT NULL) AS x_has_iiif\n"
        "FROM read_parquet('{intermediates_dir}/provider_agg.parquet') pa\n"
        "JOIN read_parquet('{exports_dir}/values_edm_WebResource.parquet') wr\n"
        "     ON pa.v_edm_isShownBy = wr.k_iri\n"
        "LEFT JOIN (\n"
        "    SELECT DISTINCT k_iri_webresource\n"
        "    FROM read_parquet('{exports_dir}/values_svcs_Service.parquet')\n"
        ") svc ON wr.k_iri = svc.k_iri_webresource\n"
        "ORDER BY pa.k_iri, wr.k_iri"
    )


def _prepare_provider_proxy_scalars_sql() -> str:
    return (
        "SELECT k_iri_cho AS k_iri,\n"
        "       MAX(v_edm_currentLocation) AS v_edm_currentLocation\n"
        "FROM read_parquet('{exports_dir}/values_ore_Proxy.parquet')\n"
        "WHERE v_edm_europeanaProxy IS NULL OR v_edm_europeanaProxy != 'true'\n"
        "GROUP BY k_iri_cho\n"
        "ORDER BY k_iri"
    )


def _prepare_europeana_proxy_scalars_sql() -> str:
    return (
        "SELECT k_iri_cho AS k_iri,\n"
        "       MAX(v_edm_type) AS v_edm_type\n"
        "FROM read_parquet('{exports_dir}/values_ore_Proxy.parquet')\n"
        "WHERE v_edm_europeanaProxy = 'true'\n"
        "GROUP BY k_iri_cho\n"
        "ORDER BY k_iri"
    )


def _prepare_agg_sql(
    merged_col: str,
    source_property: str,
    proxy_type: str,
    struct_kind: str,
    label_table: str | None,
) -> str:
    """Phase-A multi-valued aggregation over a single links_ore_Proxy x_property."""
    proxy_filter = f"pc.proxy_type = '{proxy_type}'"

    if struct_kind == "lang":
        agg_expr = (
            "LIST({x_value: l.x_value, x_value_lang: l.x_value_lang}) "
            f"AS {merged_col}"
        )
        join_label = ""
    elif struct_kind == "labeled":
        assert label_table
        agg_expr = (
            "LIST({"
            "x_value: l.x_value, "
            "x_label: COALESCE(lab.label, l.x_value), "
            "x_value_is_iri: l.x_value_is_iri"
            "}) "
            f"AS {merged_col}"
        )
        join_label = (
            f"LEFT JOIN read_parquet('{{intermediates_dir}}/{label_table}.parquet') lab "
            f"ON l.x_value_is_iri AND l.x_value = lab.k_iri"
        )
    elif struct_kind == "named":
        assert label_table
        agg_expr = (
            "LIST({"
            "x_value: l.x_value, "
            "x_name: COALESCE(lab.label, l.x_value), "
            "x_value_is_iri: l.x_value_is_iri"
            "}) "
            f"AS {merged_col}"
        )
        join_label = (
            f"LEFT JOIN read_parquet('{{intermediates_dir}}/{label_table}.parquet') lab "
            f"ON l.x_value_is_iri AND l.x_value = lab.k_iri"
        )
    elif struct_kind == "simple":
        agg_expr = f"LIST(l.x_value) AS {merged_col}"
        join_label = ""
    else:
        raise ValueError(f"Unknown struct kind: {struct_kind!r}")

    return (
        "SELECT pc.k_iri_cho AS k_iri,\n"
        f"       {agg_expr}\n"
        f"FROM {_links_read('links_ore_Proxy')} l\n"
        f"JOIN read_parquet('{{intermediates_dir}}/proxy_cho.parquet') pc "
        f"ON l.k_iri = pc.k_iri\n"
        f"{join_label}\n"
        f"WHERE l.x_property = '{source_property}' AND {proxy_filter}\n"
        "GROUP BY pc.k_iri_cho\n"
        "ORDER BY k_iri"
    )


def merged_items_prepare_specs() -> list[MergedItemsPrepareSpec]:
    """Ordered prepare specs for merged_items Phase A.

    Each spec produces one sorted-by-k_iri Parquet in the intermediates
    directory, consumed by subsequent specs and by the Phase-B chunk
    SELECT. Order matters: ``primary_wr`` depends on
    ``provider_agg.parquet``; every ``agg_x_*`` step depends on
    ``proxy_cho.parquet`` and, for labeled/named kinds, on the
    corresponding ``labels_*.parquet``.

    Sort order rationale: scalar rollups and multi-valued aggregations
    are sorted by ``k_iri`` (= ``k_iri_cho``) so Phase B range-filter
    predicates (``cho.k_iri BETWEEN ...``) propagate to Parquet row-
    group pruning for all per-CHO sources. Label maps and ``proxy_cho``
    are not filtered by CHO range in Phase B, so they are left
    unsorted.
    """
    specs: list[MergedItemsPrepareSpec] = []

    for temp_name, source_parquet in [
        ("labels_agent",   "values_edm_Agent"),
        ("labels_concept", "values_skos_Concept"),
        ("labels_place",   "values_edm_Place"),
        ("labels_org",     "values_foaf_Organization"),
    ]:
        specs.append(MergedItemsPrepareSpec(
            name=temp_name,
            filename=f"{temp_name}.parquet",
            sql=_prepare_label_sql(source_parquet),
        ))

    specs.append(MergedItemsPrepareSpec(
        name="proxy_cho",
        filename="proxy_cho.parquet",
        sql=_prepare_proxy_cho_sql(),
    ))
    specs.append(MergedItemsPrepareSpec(
        name="provider_agg",
        filename="provider_agg.parquet",
        sql=_prepare_provider_agg_sql(),
    ))
    specs.append(MergedItemsPrepareSpec(
        name="europeana_agg",
        filename="europeana_agg.parquet",
        sql=_prepare_europeana_agg_sql(),
    ))
    specs.append(MergedItemsPrepareSpec(
        name="primary_wr",
        filename="primary_wr.parquet",
        sql=_prepare_primary_wr_sql(),
    ))
    specs.append(MergedItemsPrepareSpec(
        name="provider_proxy_scalars",
        filename="provider_proxy_scalars.parquet",
        sql=_prepare_provider_proxy_scalars_sql(),
    ))
    specs.append(MergedItemsPrepareSpec(
        name="europeana_proxy_scalars",
        filename="europeana_proxy_scalars.parquet",
        sql=_prepare_europeana_proxy_scalars_sql(),
    ))

    for rule in _AGG_RULES:
        merged_col, source_property, proxy_type, struct_kind, label_table = rule
        specs.append(MergedItemsPrepareSpec(
            name=f"agg_{merged_col}",
            filename=f"agg_{merged_col}.parquet",
            sql=_prepare_agg_sql(
                merged_col, source_property, proxy_type, struct_kind, label_table,
            ),
        ))

    return specs


def merged_items_chunk_sql() -> str:
    """SELECT template for one range-chunked merged_items assembly.

    Placeholders (substituted by the runner):
      - ``{exports_dir}`` — absolute path of the exports directory
      - ``{intermediates_dir}`` — absolute path of the intermediates dir
      - ``{range_predicate}`` — ``cho.k_iri >= '...' AND cho.k_iri < '...'``
        (or ``cho.k_iri >= '...'`` for the final chunk).

    The filter on ``cho.k_iri`` propagates to every sorted
    per-CHO-keyed intermediate via DuckDB's equi-join filter inference,
    pruning Parquet row groups. ``labels_org`` is joined on a different
    column and is read in full (tiny).
    """
    select_str = ",\n  ".join(_merged_items_select_parts())
    joins = _merged_items_joins(
        lambda name: f"read_parquet('{{intermediates_dir}}/{name}.parquet')"
    )
    return (
        f"SELECT\n  {select_str}\n"
        "FROM read_parquet('{exports_dir}/values_edm_ProvidedCHO.parquet') cho\n"
        f"{joins}\n"
        "WHERE {range_predicate}\n"
        "ORDER BY cho.k_iri"
    )


def merged_items_steps() -> list[ComposeStep]:
    """Return the full one-shot compose sequence for merged_items.

    Backwards-compatible path used when chunking is disabled. Omits
    ``cho_numbered`` / ``chunk_chos`` and builds every temp table with
    the CHO-wide (unfiltered) body.
    """
    steps: list[ComposeStep] = []

    # 1. Entity label maps (English preferred)
    steps.append(_entity_label_step("labels_agent",   "values_edm_Agent"))
    steps.append(_entity_label_step("labels_concept", "values_skos_Concept"))
    steps.append(_entity_label_step("labels_place",   "values_edm_Place"))
    steps.append(_entity_label_step("labels_org",     "values_foaf_Organization"))

    # 2. Proxy-CHO mapping (used by all multi-valued aggregations)
    steps.append(_proxy_cho_step())

    # 3. Per-property aggregations
    for rule in _AGG_RULES:
        steps.append(_agg_step(*rule))

    # 4. Pre-aggregate Aggregation + EuropeanaAggregation to 1 row per CHO
    #    (prevents join-explosion; primary_wr reads from provider_agg).
    steps.append(_provider_agg_step())
    steps.append(_europeana_agg_step())

    # 5. Primary web resource + IIIF flag
    steps.append(_primary_wr_step())

    # 6. Provider-proxy and Europeana-proxy scalar helpers
    steps.append(_provider_proxy_scalars_step())
    steps.append(_europeana_proxy_scalars_step())

    # 7. Final assembly
    steps.append(_merged_items_final_step())
    return steps


# ---------------------------------------------------------------------------
# group_items — categorical dimensions and boolean flags
# ---------------------------------------------------------------------------


def _provider_proxy_properties_step(*, chunk_filter: bool = False) -> ComposeStep:
    """(CHO, x_property) pairs observed on the provider proxy.

    Narrowing cascades through the already-filtered ``proxy_cho`` temp
    table when running under chunk mode; only ``CREATE OR REPLACE``
    wrapping is needed here.
    """
    create = "CREATE OR REPLACE TEMP TABLE" if chunk_filter else "CREATE TEMP TABLE"
    sql = (
        f"{create} provider_proxy_properties AS\n"
        "SELECT DISTINCT pc.k_iri_cho AS k_iri, l.x_property\n"
        f"FROM {_links_read('links_ore_Proxy')} l\n"
        "JOIN proxy_cho pc ON l.k_iri = pc.k_iri\n"
        "WHERE pc.proxy_type = 'provider'"
    )
    return ComposeStep(name="provider_proxy_properties", sql=sql)


def _primary_language_step(*, chunk_filter: bool = False) -> ComposeStep:
    """First dc:language per CHO from the provider proxy."""
    create = "CREATE OR REPLACE TEMP TABLE" if chunk_filter else "CREATE TEMP TABLE"
    sql = (
        f"{create} primary_language AS\n"
        "SELECT pc.k_iri_cho AS k_iri,\n"
        "       MIN(l.x_value) AS lang\n"
        f"FROM {_links_read('links_ore_Proxy')} l\n"
        "JOIN proxy_cho pc ON l.k_iri = pc.k_iri\n"
        "WHERE pc.proxy_type = 'provider' AND l.x_property = 'v_dc_language'\n"
        "GROUP BY pc.k_iri_cho"
    )
    return ComposeStep(name="primary_language", sql=sql)


def _group_items_final_step(*, chunk_filter: bool = False) -> ComposeStep:
    """Build the final assembly step for group_items.

    When ``chunk_filter`` is True, narrows the CHO base via a
    ``SEMI JOIN chunk_chos`` so each chunk writes only its slice.
    """
    select_parts = [
        "cho.k_iri AS k_iri",
        "eagg.v_edm_completeness AS v_edm_completeness",
        "eagg.v_edm_country AS v_edm_country",
        "agg.v_edm_dataProvider AS v_edm_dataProvider",
        "agg.v_edm_provider AS v_edm_provider",
        "europeana_proxy_scalars.v_edm_type AS v_edm_type",
        "(agg.v_edm_isShownBy IS NOT NULL) AS x_has_content_url",
        "(hc.k_iri IS NOT NULL) AS x_has_creator",
        "(hd.k_iri IS NOT NULL) AS x_has_description",
        "COALESCE(primary_wr.x_has_iiif, false) AS x_has_iiif",
        "(hs.k_iri IS NOT NULL) AS x_has_subject",
        "primary_language.lang AS x_primary_language",
        f"{reuse_level_sql('agg.v_edm_rights')} AS x_reuse_level",
        f"{duckdb_family_case('agg.v_edm_rights')} AS x_rights_family",
    ]
    select_parts.sort(key=lambda s: s.rsplit(" AS ", 1)[1] if " AS " in s else s)
    select_str = ",\n  ".join(select_parts)

    chunk_join = (
        "SEMI JOIN chunk_chos cc ON cho.k_iri = cc.k_iri\n"
        if chunk_filter else ""
    )

    final_sql = (
        f"SELECT\n  {select_str}\n"
        "FROM read_parquet('{exports_dir}/values_edm_ProvidedCHO.parquet') cho\n"
        f"{chunk_join}"
        "LEFT JOIN provider_agg agg ON agg.k_iri = cho.k_iri\n"
        "LEFT JOIN europeana_agg eagg ON eagg.k_iri = cho.k_iri\n"
        "LEFT JOIN europeana_proxy_scalars ON europeana_proxy_scalars.k_iri = cho.k_iri\n"
        "LEFT JOIN primary_wr ON primary_wr.k_iri = cho.k_iri\n"
        "LEFT JOIN primary_language ON primary_language.k_iri = cho.k_iri\n"
        "LEFT JOIN (SELECT k_iri FROM provider_proxy_properties "
        "WHERE x_property = 'v_dc_creator') hc ON hc.k_iri = cho.k_iri\n"
        "LEFT JOIN (SELECT k_iri FROM provider_proxy_properties "
        "WHERE x_property = 'v_dc_description') hd ON hd.k_iri = cho.k_iri\n"
        "LEFT JOIN (SELECT k_iri FROM provider_proxy_properties "
        "WHERE x_property = 'v_dc_subject') hs ON hs.k_iri = cho.k_iri"
    )

    return ComposeStep(name="group_items_final", sql=final_sql, is_final=True)


def group_items_shared_steps() -> list[ComposeStep]:
    """CHO-independent steps for group_items chunked runs.

    ``provider_agg`` / ``europeana_agg`` / ``primary_wr`` read the raw
    Aggregation / EuropeanaAggregation / WebResource Parquets which
    don't depend on ``chunk_chos``; materializing them once avoids N
    redundant full-file scans across the chunk loop.
    """
    return [
        _cho_numbered_step(),
        _provider_agg_step(),
        _europeana_agg_step(),
        _primary_wr_step(),
    ]


def group_items_chunk_steps() -> list[ComposeStep]:
    """Per-chunk steps for group_items: only the temp tables that
    actually depend on the chunk slice are rebuilt via
    ``CREATE OR REPLACE TEMP TABLE``.
    """
    return [
        _chunk_chos_step(),
        _proxy_cho_step(chunk_filter=True),
        _provider_proxy_properties_step(chunk_filter=True),
        _primary_language_step(chunk_filter=True),
        _europeana_proxy_scalars_step(chunk_filter=True),
        _group_items_final_step(chunk_filter=True),
    ]


def group_items_steps() -> list[ComposeStep]:
    """Return the full one-shot compose sequence for group_items.

    Backwards-compatible path used when chunking is disabled.
    """
    return [
        _proxy_cho_step(),
        _provider_agg_step(),
        _europeana_agg_step(),
        _primary_wr_step(),
        _provider_proxy_properties_step(),
        _primary_language_step(),
        _europeana_proxy_scalars_step(),
        _group_items_final_step(),
    ]


# ---------------------------------------------------------------------------
# map_rights
# ---------------------------------------------------------------------------


def map_rights_steps() -> list[ComposeStep]:
    """Return compose steps for map_rights."""
    sql = (
        "SELECT k_iri,\n"
        f"  {reuse_level_sql('k_iri')} AS x_category,\n"
        f"  {duckdb_family_case('k_iri')} AS x_family,\n"
        f"  {duckdb_is_open_case('k_iri')} AS x_is_open,\n"
        f"  {duckdb_label_case('k_iri')} AS x_label\n"
        "FROM (\n"
        "  SELECT DISTINCT v_edm_rights AS k_iri\n"
        "  FROM read_parquet('{exports_dir}/values_ore_Aggregation.parquet')\n"
        "  WHERE v_edm_rights IS NOT NULL\n"
        ")"
    )
    return [ComposeStep(name="map_rights_final", sql=sql, is_final=True)]


# ---------------------------------------------------------------------------
# map_sameAs
# ---------------------------------------------------------------------------


def map_sameAs_steps() -> list[ComposeStep]:
    """Return compose steps for map_sameAs."""
    source_tables = [
        ("links_edm_Agent", "edm_Agent"),
        ("links_edm_Place", "edm_Place"),
        ("links_skos_Concept", "skos_Concept"),
        ("links_edm_TimeSpan", "edm_TimeSpan"),
    ]
    auth_case = authority_sql("x_value")
    unions = []
    for table, ecls in source_tables:
        unions.append(
            f"SELECT k_iri, x_value AS v_owl_sameAs,\n"
            f"       {auth_case} AS x_authority,\n"
            f"       '{ecls}' AS x_entity_class\n"
            f"FROM {_links_read(table)}\n"
            f"WHERE x_property = 'v_owl_sameAs'"
        )
    sql = "\nUNION ALL\n".join(unions)
    select_parts = [
        "k_iri",
        "v_owl_sameAs",
        "x_authority",
        "x_entity_class",
    ]
    wrapped = (
        "SELECT "
        + ", ".join(sorted(select_parts))
        + "\nFROM (\n"
        + sql
        + "\n)"
    )
    return [ComposeStep(name="map_sameAs_final", sql=wrapped, is_final=True)]


# ---------------------------------------------------------------------------
# map_cho_entities
# ---------------------------------------------------------------------------


def map_cho_entities_steps() -> list[ComposeStep]:
    """Map CHOs → contextual entities referenced via the provider proxy."""
    steps: list[ComposeStep] = []

    # All entity IRIs unioned together with their source class
    steps.append(ComposeStep(
        name="entity_iris",
        sql=(
            "CREATE TEMP TABLE entity_iris AS\n"
            "SELECT DISTINCT k_iri, 'edm_Agent' AS x_entity_class\n"
            "  FROM read_parquet('{exports_dir}/values_edm_Agent.parquet')\n"
            "UNION ALL\n"
            "SELECT DISTINCT k_iri, 'edm_Place'\n"
            "  FROM read_parquet('{exports_dir}/values_edm_Place.parquet')\n"
            "UNION ALL\n"
            "SELECT DISTINCT k_iri, 'skos_Concept'\n"
            "  FROM read_parquet('{exports_dir}/values_skos_Concept.parquet')\n"
            "UNION ALL\n"
            "SELECT DISTINCT k_iri, 'edm_TimeSpan'\n"
            "  FROM read_parquet('{exports_dir}/values_edm_TimeSpan.parquet')"
        ),
    ))

    # Proxy → CHO mapping
    steps.append(_proxy_cho_step())

    final_sql = (
        "SELECT DISTINCT\n"
        "  pc.k_iri_cho AS k_iri_cho,\n"
        "  l.x_value AS k_iri_entity,\n"
        "  e.x_entity_class AS x_entity_class,\n"
        "  l.x_property AS x_property\n"
        f"FROM {_links_read('links_ore_Proxy')} l\n"
        "JOIN proxy_cho pc ON l.k_iri = pc.k_iri\n"
        "JOIN entity_iris e ON l.x_value = e.k_iri\n"
        "WHERE l.x_value_is_iri"
    )
    steps.append(ComposeStep(name="map_cho_entities_final", sql=final_sql, is_final=True))
    return steps


# ---------------------------------------------------------------------------
# Registry dispatcher
# ---------------------------------------------------------------------------


def compose_steps_for(table_name: str) -> list[ComposeStep]:
    """Return the ComposeStep list for a composable export, or ``[]``."""
    info = export_classes().get(table_name)
    if info is None:
        return []
    et = info.export_type
    if et == "merged" and table_name == "merged_items":
        return merged_items_steps()
    if et == "group" and table_name == "group_items":
        return group_items_steps()
    if et == "map":
        if table_name == "map_rights":
            return map_rights_steps()
        if table_name == "map_sameAs":
            return map_sameAs_steps()
        if table_name == "map_cho_entities":
            return map_cho_entities_steps()
    return []


def chunked_compose_steps_for(
    table_name: str,
) -> tuple[list[ComposeStep], list[ComposeStep]] | None:
    """Return ``(shared, per_chunk)`` step lists for a chunkable composite,
    or ``None`` if ``table_name`` does not support chunked composition.

    Shared steps are built once per run and reused across chunks;
    per-chunk steps are rebuilt with ``CREATE OR REPLACE TEMP TABLE``
    for each ``chunk_chos`` slice.

    Note: ``merged_items`` uses its own range-chunked path with on-disk
    intermediates instead (see :func:`merged_items_prepare_specs` and
    :func:`merged_items_chunk_sql`), dispatched directly from
    ``ExportPipeline`` — it does not appear here.
    """
    if table_name == "group_items":
        return group_items_shared_steps(), group_items_chunk_steps()
    return None
