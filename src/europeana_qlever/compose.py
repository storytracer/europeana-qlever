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
) -> ComposeStep:
    """Build one aggregation temp table for a multi-valued merged_items column."""
    temp_name = f"agg_{merged_col}"
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
        f"CREATE TEMP TABLE {temp_name} AS\n"
        f"SELECT pc.k_iri_cho AS k_iri,\n"
        f"       {agg_expr}\n"
        f"FROM {_links_read('links_ore_Proxy')} l\n"
        f"JOIN proxy_cho pc ON l.k_iri = pc.k_iri\n"
        f"{join_label}\n"
        f"WHERE l.x_property = '{source_property}' AND {proxy_filter}\n"
        f"GROUP BY pc.k_iri_cho"
    )
    return ComposeStep(name=temp_name, sql=sql)


def _primary_wr_step() -> ComposeStep:
    """Build primary_wr temp table with all web-resource scalar columns and IIIF flag."""
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
        f"SELECT a.k_iri_cho AS k_iri,\n"
        f"       {select_cols},\n"
        f"       (svc.k_iri_webresource IS NOT NULL) AS x_has_iiif\n"
        "FROM read_parquet('{exports_dir}/values_ore_Aggregation.parquet') a\n"
        "JOIN read_parquet('{exports_dir}/values_edm_WebResource.parquet') wr\n"
        "     ON a.v_edm_isShownBy = wr.k_iri\n"
        "LEFT JOIN (\n"
        "    SELECT DISTINCT k_iri_webresource\n"
        "    FROM read_parquet('{exports_dir}/values_svcs_Service.parquet')\n"
        ") svc ON wr.k_iri = svc.k_iri_webresource"
    )
    return ComposeStep(name="primary_wr", sql=sql)


def _proxy_cho_step() -> ComposeStep:
    """Map proxy URIs → (CHO URI, provider|europeana) for joining with links_ore_Proxy."""
    sql = (
        "CREATE TEMP TABLE proxy_cho AS\n"
        "SELECT k_iri, k_iri_cho,\n"
        "       CASE WHEN v_edm_europeanaProxy = 'true' THEN 'europeana' ELSE 'provider' END AS proxy_type\n"
        "FROM read_parquet('{exports_dir}/values_ore_Proxy.parquet')"
    )
    return ComposeStep(name="proxy_cho", sql=sql)


def merged_items_steps() -> list[ComposeStep]:
    """Return the full sequence of compose steps for merged_items."""
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

    # 4. Primary web resource + IIIF flag
    steps.append(_primary_wr_step())

    # 5. Provider-proxy and Europeana-proxy scalar helpers
    steps.append(ComposeStep(
        name="provider_proxy_scalars",
        sql=(
            "CREATE TEMP TABLE provider_proxy_scalars AS\n"
            "SELECT k_iri_cho AS k_iri,\n"
            "       MAX(v_edm_currentLocation) AS v_edm_currentLocation\n"
            "FROM read_parquet('{exports_dir}/values_ore_Proxy.parquet')\n"
            "WHERE v_edm_europeanaProxy IS NULL OR v_edm_europeanaProxy != 'true'\n"
            "GROUP BY k_iri_cho"
        ),
    ))
    steps.append(ComposeStep(
        name="europeana_proxy_scalars",
        sql=(
            "CREATE TEMP TABLE europeana_proxy_scalars AS\n"
            "SELECT k_iri_cho AS k_iri,\n"
            "       MAX(v_edm_type) AS v_edm_type\n"
            "FROM read_parquet('{exports_dir}/values_ore_Proxy.parquet')\n"
            "WHERE v_edm_europeanaProxy = 'true'\n"
            "GROUP BY k_iri_cho"
        ),
    ))

    # 6. Final SELECT — assemble merged_items with all columns alphabetical
    agg_joins = "\n".join(
        f"LEFT JOIN agg_{merged_col} USING (k_iri)"
        for merged_col, _, _, _, _ in _AGG_RULES
    )
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

    # k_iri
    select_parts.append("cho.k_iri AS k_iri")

    # Web-resource scalars (alphabetical order within v_ebucore_* and v_edm_*)
    wr_scalars = [
        "v_ebucore_audioChannelNumber", "v_ebucore_bitRate", "v_ebucore_duration",
        "v_ebucore_fileByteSize", "v_ebucore_frameRate", "v_ebucore_hasMimeType",
        "v_ebucore_height", "v_ebucore_orientation", "v_ebucore_sampleRate",
        "v_ebucore_sampleSize", "v_ebucore_width",
        "v_edm_codecName",
    ]
    for c in wr_scalars:
        select_parts.append(f"primary_wr.{c} AS {c}")

    # v_edm_completeness, v_edm_country  (EuropeanaAggregation)
    select_parts.append("eagg.v_edm_completeness AS v_edm_completeness")
    select_parts.append("eagg.v_edm_country AS v_edm_country")

    # v_edm_currentLocation (provider proxy)
    select_parts.append(
        "provider_proxy_scalars.v_edm_currentLocation AS v_edm_currentLocation"
    )

    # v_edm_dataProvider (Aggregation)
    select_parts.append("agg.v_edm_dataProvider AS v_edm_dataProvider")

    # v_edm_datasetName (EuropeanaAggregation)
    select_parts.append("eagg.v_edm_datasetName AS v_edm_datasetName")

    # v_edm_hasColorSpace (WebResource)
    select_parts.append("primary_wr.v_edm_hasColorSpace AS v_edm_hasColorSpace")

    # v_edm_isShownAt, v_edm_isShownBy (Aggregation)
    select_parts.append("agg.v_edm_isShownAt AS v_edm_isShownAt")
    select_parts.append("agg.v_edm_isShownBy AS v_edm_isShownBy")

    # v_edm_landingPage (EuropeanaAggregation)
    select_parts.append("eagg.v_edm_landingPage AS v_edm_landingPage")

    # v_edm_object (Aggregation)
    select_parts.append("agg.v_edm_object AS v_edm_object")

    # v_edm_pointCount (WebResource)
    select_parts.append("primary_wr.v_edm_pointCount AS v_edm_pointCount")
    select_parts.append("primary_wr.v_edm_polygonCount AS v_edm_polygonCount")

    # v_edm_preview (EuropeanaAggregation)
    select_parts.append("eagg.v_edm_preview AS v_edm_preview")

    # v_edm_provider, v_edm_rights (Aggregation)
    select_parts.append("agg.v_edm_provider AS v_edm_provider")
    select_parts.append("agg.v_edm_rights AS v_edm_rights")

    # v_edm_spatialResolution (WebResource)
    select_parts.append("primary_wr.v_edm_spatialResolution AS v_edm_spatialResolution")

    # v_edm_type (Europeana proxy)
    select_parts.append("europeana_proxy_scalars.v_edm_type AS v_edm_type")

    # v_edm_vertexCount (WebResource)
    select_parts.append("primary_wr.v_edm_vertexCount AS v_edm_vertexCount")

    # v_schema_digitalSourceType (WebResource)
    select_parts.append("primary_wr.v_schema_digitalSourceType AS v_schema_digitalSourceType")

    # --- x_ columns, alphabetical ---
    select_parts.append("labels_org_dp.label AS x_dataProvider_name")

    # All x_dc_* + x_dcterms_* + x_edm_* list columns from agg tables
    for col in agg_columns:
        if col in ("x_dc_title", "x_dc_description"):
            select_parts.append(f"agg_{col}.{col} AS {col}")
        else:
            select_parts.append(f"agg_{col}.{col} AS {col}")

    # x_description + x_description_lang (derived from x_dc_description)
    select_parts.append(desc_expr)
    select_parts.append(desc_lang_expr)

    # x_has_iiif
    select_parts.append("COALESCE(primary_wr.x_has_iiif, false) AS x_has_iiif")

    # x_megapixels
    select_parts.append(
        "CASE WHEN primary_wr.v_ebucore_width IS NOT NULL "
        "AND primary_wr.v_ebucore_height IS NOT NULL "
        "THEN primary_wr.v_ebucore_width * primary_wr.v_ebucore_height / 1000000.0 END "
        "AS x_megapixels"
    )

    # x_provider_name
    select_parts.append("labels_org_prov.label AS x_provider_name")

    # x_reuse_level
    select_parts.append(f"{reuse_level_sql('agg.v_edm_rights')} AS x_reuse_level")

    # x_title / x_title_lang (derived from x_dc_title)
    select_parts.append(title_expr)
    select_parts.append(title_lang_expr)

    # Sort select parts alphabetically by the final column name (after ``AS``).
    def _col_name(line: str) -> str:
        if " AS " in line:
            return line.rsplit(" AS ", 1)[1].strip()
        return line

    select_parts.sort(key=_col_name)

    select_str = ",\n  ".join(select_parts)

    final_sql = (
        f"SELECT\n  {select_str}\n"
        "FROM read_parquet('{exports_dir}/values_edm_ProvidedCHO.parquet') cho\n"
        "LEFT JOIN read_parquet('{exports_dir}/values_ore_Aggregation.parquet') agg\n"
        "  ON agg.k_iri_cho = cho.k_iri\n"
        "LEFT JOIN read_parquet('{exports_dir}/values_edm_EuropeanaAggregation.parquet') eagg\n"
        "  ON eagg.k_iri_cho = cho.k_iri\n"
        "LEFT JOIN primary_wr ON primary_wr.k_iri = cho.k_iri\n"
        "LEFT JOIN provider_proxy_scalars ON provider_proxy_scalars.k_iri = cho.k_iri\n"
        "LEFT JOIN europeana_proxy_scalars ON europeana_proxy_scalars.k_iri = cho.k_iri\n"
        "LEFT JOIN labels_org labels_org_dp ON labels_org_dp.k_iri = agg.v_edm_dataProvider\n"
        "LEFT JOIN labels_org labels_org_prov ON labels_org_prov.k_iri = agg.v_edm_provider\n"
        + "\n".join(
            f"LEFT JOIN agg_{col} ON agg_{col}.k_iri = cho.k_iri"
            for col in agg_columns
        )
    )

    steps.append(ComposeStep(name="merged_items_final", sql=final_sql, is_final=True))
    return steps


# ---------------------------------------------------------------------------
# group_items — categorical dimensions and boolean flags
# ---------------------------------------------------------------------------


def group_items_steps() -> list[ComposeStep]:
    """Return the compose steps for group_items.

    Single-step composite: JOINs values_ore_Aggregation / EuropeanaAgg /
    values_ore_Proxy(europeana), computes boolean EXISTS flags over
    links_ore_Proxy, and classifies rights into reuse_level + family.
    """
    steps: list[ComposeStep] = []

    # Reuse the proxy_cho and primary_wr helpers used by merged_items so
    # the has_iiif flag matches.
    steps.append(_proxy_cho_step())
    steps.append(_primary_wr_step())

    # Boolean "has property X on provider proxy" flags.
    # Build a set of (cho_iri, x_property) pairs once and reuse.
    steps.append(ComposeStep(
        name="provider_proxy_properties",
        sql=(
            "CREATE TEMP TABLE provider_proxy_properties AS\n"
            "SELECT DISTINCT pc.k_iri_cho AS k_iri, l.x_property\n"
            f"FROM {_links_read('links_ore_Proxy')} l\n"
            "JOIN proxy_cho pc ON l.k_iri = pc.k_iri\n"
            "WHERE pc.proxy_type = 'provider'"
        ),
    ))

    # First dc:language per CHO (primary language) from provider proxy.
    steps.append(ComposeStep(
        name="primary_language",
        sql=(
            "CREATE TEMP TABLE primary_language AS\n"
            "SELECT pc.k_iri_cho AS k_iri,\n"
            "       MIN(l.x_value) AS lang\n"
            f"FROM {_links_read('links_ore_Proxy')} l\n"
            "JOIN proxy_cho pc ON l.k_iri = pc.k_iri\n"
            "WHERE pc.proxy_type = 'provider' AND l.x_property = 'v_dc_language'\n"
            "GROUP BY pc.k_iri_cho"
        ),
    ))

    # Europeana-proxy scalars (for v_edm_type).
    steps.append(ComposeStep(
        name="europeana_proxy_scalars",
        sql=(
            "CREATE TEMP TABLE europeana_proxy_scalars AS\n"
            "SELECT k_iri_cho AS k_iri, MAX(v_edm_type) AS v_edm_type\n"
            "FROM read_parquet('{exports_dir}/values_ore_Proxy.parquet')\n"
            "WHERE v_edm_europeanaProxy = 'true'\n"
            "GROUP BY k_iri_cho"
        ),
    ))

    # Final SELECT
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

    final_sql = (
        f"SELECT\n  {select_str}\n"
        "FROM read_parquet('{exports_dir}/values_edm_ProvidedCHO.parquet') cho\n"
        "LEFT JOIN read_parquet('{exports_dir}/values_ore_Aggregation.parquet') agg\n"
        "  ON agg.k_iri_cho = cho.k_iri\n"
        "LEFT JOIN read_parquet('{exports_dir}/values_edm_EuropeanaAggregation.parquet') eagg\n"
        "  ON eagg.k_iri_cho = cho.k_iri\n"
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

    steps.append(ComposeStep(name="group_items_final", sql=final_sql, is_final=True))
    return steps


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
