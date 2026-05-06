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
    metis_known_sql,
    reuse_level_sql,
    well_formed_sql,
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
# Shared CHO-keyed rollups — used by group_items and map_cho_entities
# ---------------------------------------------------------------------------


# Trimmed to columns actually consumed downstream — every additional
# column inflates the resident size of the 60M-row provider_agg /
# europeana_agg temp tables, which dominates DuckDB's working set
# during chunked group_items composition.
_PROVIDER_AGG_COLS = [
    "v_edm_dataProvider",
    "v_edm_isShownBy",
    "v_edm_provider",
    "v_edm_rights",
]


_EUROPEANA_AGG_COLS = [
    "v_edm_country",
    "v_edm_datasetName",
    "v_edm_language",
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


def _publishing_tier_step(*, chunk_filter: bool = False) -> ComposeStep:
    """Europeana publishing-framework tier URIs per CHO.

    Sourced from values_publishing_tier (EuropeanaAggregation →
    dqv:hasQualityAnnotation → oa:hasBody, see EDM.md §3.6). The
    upstream SPARQL is already 1:1 per CHO so no collapsing is
    needed. Built per-chunk in chunked mode (the full ~32M-row table
    would otherwise sit alongside provider_agg / europeana_agg /
    primary_wr in DuckDB memory and tip the working set over the
    budget); built once in one-shot mode.
    """
    create = "CREATE OR REPLACE TEMP TABLE" if chunk_filter else "CREATE TEMP TABLE"
    chunk_join = (
        "SEMI JOIN chunk_chos cc ON t.k_iri = cc.k_iri"
        if chunk_filter else ""
    )
    sql = (
        f"{create} publishing_tier AS\n"
        "SELECT t.k_iri AS k_iri,\n"
        "       t.x_content_tier_uri AS x_content_tier_uri,\n"
        "       t.x_metadata_tier_uri AS x_metadata_tier_uri\n"
        "FROM read_parquet('{exports_dir}/values_publishing_tier.parquet') t"
        + (f"\n{chunk_join}" if chunk_join else "")
    )
    return ComposeStep(name="publishing_tier", sql=sql)


def _primary_wr_step(*, chunk_filter: bool = False) -> ComposeStep:
    """Primary WebResource ``x_has_iiif`` flag per CHO.

    Reads from the already-1:1 ``provider_agg`` temp table so the join
    through ``v_edm_isShownBy`` is guaranteed at most one row per CHO.
    A defensive ``DISTINCT ON (k_iri)`` wrapper collapses any duplicate
    WebResource rows that might slip through from upstream. Only the
    boolean flag is projected — the WebResource scalar columns aren't
    consumed by group_items and were inflating the resident temp table
    by ~25 GB on the full dataset. In chunked mode this rebuilds per
    chunk (provider_agg is itself chunk-filtered) so the working set
    stays small.
    """
    create = "CREATE OR REPLACE TEMP TABLE" if chunk_filter else "CREATE TEMP TABLE"
    sql = (
        f"{create} primary_wr AS\n"
        "SELECT DISTINCT ON (pa.k_iri)\n"
        "       pa.k_iri AS k_iri,\n"
        "       (svc.k_iri_webresource IS NOT NULL) AS x_has_iiif\n"
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



# ---------------------------------------------------------------------------
# group_items — categorical dimensions and boolean flags
# ---------------------------------------------------------------------------


_PROVIDER_PROXY_HAS_PROPS = ("v_dc_creator", "v_dc_description", "v_dc_subject")


def _provider_proxy_properties_step(*, chunk_filter: bool = False) -> ComposeStep:
    """(CHO, x_property) pairs observed on the provider proxy.

    Reads only the three Hive partitions whose presence powers the
    downstream ``x_has_creator`` / ``x_has_description`` / ``x_has_subject``
    booleans, instead of scanning every links_ore_Proxy partition.
    """
    create = "CREATE OR REPLACE TEMP TABLE" if chunk_filter else "CREATE TEMP TABLE"
    unions = "\nUNION ALL\n".join(
        f"SELECT k_iri, '{p}' AS x_property "
        f"FROM read_parquet('{{exports_dir}}/links_ore_Proxy/x_property={p}/**/*.parquet')"
        for p in _PROVIDER_PROXY_HAS_PROPS
    )
    sql = (
        f"{create} provider_proxy_properties AS\n"
        "SELECT DISTINCT pc.k_iri_cho AS k_iri, l.x_property\n"
        f"FROM (\n{unions}\n) l\n"
        "JOIN proxy_cho pc ON l.k_iri = pc.k_iri\n"
        "WHERE pc.proxy_type = 'provider'"
    )
    return ComposeStep(name="provider_proxy_properties", sql=sql)


def _group_items_final_step(*, chunk_filter: bool = False) -> ComposeStep:
    """Build the final assembly step for group_items.

    When ``chunk_filter`` is True, narrows the CHO base via a
    ``SEMI JOIN chunk_chos`` so each chunk writes only its slice.
    """
    select_parts = [
        "cho.k_iri AS k_iri",
        "eagg.v_edm_country AS v_edm_country",
        "agg.v_edm_dataProvider AS v_edm_dataProvider",
        "eagg.v_edm_datasetName AS v_edm_datasetName",
        "agg.v_edm_provider AS v_edm_provider",
        "europeana_proxy_scalars.v_edm_type AS v_edm_type",
        "(agg.v_edm_isShownBy IS NOT NULL) AS x_has_content_url",
        "(hc.k_iri IS NOT NULL) AS x_has_creator",
        "(hd.k_iri IS NOT NULL) AS x_has_description",
        "COALESCE(primary_wr.x_has_iiif, false) AS x_has_iiif",
        "(hs.k_iri IS NOT NULL) AS x_has_subject",
        "eagg.v_edm_language AS x_primary_language",
        f"{reuse_level_sql('agg.v_edm_rights')} AS x_reuse_level",
        f"{duckdb_family_case('agg.v_edm_rights')} AS x_rights_family",
        "TRY_CAST(REGEXP_EXTRACT(tier.x_content_tier_uri, 'contentTier([0-9])$', 1) AS INTEGER) AS x_content_tier",
        "NULLIF(REGEXP_EXTRACT(tier.x_metadata_tier_uri, 'metadataTier([0A-C])$', 1), '') AS x_metadata_tier",
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
        "LEFT JOIN publishing_tier tier ON tier.k_iri = cho.k_iri\n"
        "LEFT JOIN europeana_proxy_scalars ON europeana_proxy_scalars.k_iri = cho.k_iri\n"
        "LEFT JOIN primary_wr ON primary_wr.k_iri = cho.k_iri\n"
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

    Only ``cho_numbered`` is truly chunk-independent (it provides the
    stable ROW_NUMBER → chunk-window mapping). All other temp tables
    that previously lived here (``provider_agg`` / ``europeana_agg`` /
    ``primary_wr``) are now built per-chunk: their ``DISTINCT ON``
    sorts on the full 60M-row aggregation tables exceeded DuckDB's
    memory budget even at 32 GB, and the per-chunk redundant Parquet
    reads are cheap by comparison.
    """
    return [
        _cho_numbered_step(),
    ]


def group_items_chunk_steps() -> list[ComposeStep]:
    """Per-chunk steps for group_items: only the temp tables that
    actually depend on the chunk slice are rebuilt via
    ``CREATE OR REPLACE TEMP TABLE``.
    """
    return [
        _chunk_chos_step(),
        _provider_agg_step(chunk_filter=True),
        _europeana_agg_step(chunk_filter=True),
        _primary_wr_step(chunk_filter=True),
        _proxy_cho_step(chunk_filter=True),
        _publishing_tier_step(chunk_filter=True),
        _provider_proxy_properties_step(chunk_filter=True),
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
        _publishing_tier_step(),
        _primary_wr_step(),
        _provider_proxy_properties_step(),
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
    well_formed_expr = well_formed_sql("x_value")
    metis_known_expr = metis_known_sql("x_value")
    auth_case = authority_sql("x_value")
    unions = []
    for table, ecls in source_tables:
        unions.append(
            f"SELECT k_iri,\n"
            f"       x_value AS v_owl_sameAs,\n"
            f"       {well_formed_expr} AS x_well_formed,\n"
            f"       {metis_known_expr} AS x_metis_known,\n"
            f"       CASE WHEN {well_formed_expr} AND {metis_known_expr}\n"
            f"            THEN {auth_case}\n"
            f"            ELSE NULL END AS x_authority,\n"
            f"       '{ecls}' AS x_entity_class\n"
            f"FROM {_links_read(table)}\n"
            f"WHERE x_property = 'v_owl_sameAs'"
        )
    sql = "\nUNION ALL\n".join(unions)
    select_parts = [
        "k_iri",
        "v_owl_sameAs",
        "x_well_formed",
        "x_metis_known",
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
# map_edm_entities — Europeana enrichment edges
# ---------------------------------------------------------------------------


_EDM_ENTITY_NAMESPACE_PREFIX = "http://data.europeana.eu/"


def map_edm_entities_steps() -> list[ComposeStep]:
    """Return compose steps for map_edm_entities.

    The Europeana-curated subset of ``map_cho_entities``: only edges
    whose entity IRI lives under one of the four
    ``data.europeana.eu/{agent,place,concept,timespan}/`` namespaces.
    Provider-local entity URIs that appear in ``map_cho_entities`` but
    aren't reconciled to Europeana's collection are excluded — they
    aren't enrichment, just unresolved identifiers.

    Deduplicated on (k_iri_cho, k_iri_entity, x_entity_class) so a CHO
    referencing the same entity through multiple proxy properties
    counts once.
    """
    sql = (
        "SELECT DISTINCT k_iri_cho, k_iri_entity, x_entity_class\n"
        "FROM read_parquet('{exports_dir}/map_cho_entities.parquet')\n"
        f"WHERE k_iri_entity LIKE '{_EDM_ENTITY_NAMESPACE_PREFIX}%'"
    )
    return [ComposeStep(name="map_edm_entities_final", sql=sql, is_final=True)]


# ---------------------------------------------------------------------------
# explorer_edm_entities — UI-optimised edges with inline English label
# ---------------------------------------------------------------------------


_EDM_ENTITY_NAMESPACES = {
    # class enum value → IRI prefix of Europeana's curated entity collection.
    # Used to filter values_<class> reads to only Europeana-curated entities
    # (mirrors the broader filter applied in map_edm_entities).
    "edm_Agent":    "http://data.europeana.eu/agent/",
    "edm_Place":    "http://data.europeana.eu/place/",
    "skos_Concept": "http://data.europeana.eu/concept/",
    "edm_TimeSpan": "http://data.europeana.eu/timespan/",
}


def explorer_edm_entities_steps() -> list[ComposeStep]:
    """Return compose steps for explorer_edm_entities.

    Builds on top of ``map_edm_entities`` (already filtered to
    Europeana-curated entities and deduplicated) by joining each
    (CHO, entity) edge with the entity's English prefLabel from
    ``values_<class>``. ``COALESCE`` substitutes ``k_iri_entity`` when
    no English label exists so ``x_label`` is never NULL — downstream
    UI consumers can render it directly.
    """
    label_select = (
        "SELECT k_iri,\n"
        "       MAX(CASE WHEN x_prefLabel_lang = 'en' "
        "THEN v_skos_prefLabel END) AS x_label_en\n"
        "FROM read_parquet('{{exports_dir}}/values_{cls}.parquet')\n"
        "WHERE k_iri LIKE '{prefix}%'\n"
        "GROUP BY k_iri"
    )
    labels_sql = "\nUNION ALL\n".join(
        label_select.format(cls=c, prefix=p)
        for c, p in _EDM_ENTITY_NAMESPACES.items()
    )
    return [
        ComposeStep(
            name="entity_labels",
            sql=f"CREATE TEMP TABLE entity_labels AS\n{labels_sql}",
        ),
        ComposeStep(
            name="explorer_edm_entities_final",
            is_final=True,
            sql=(
                "SELECT m.k_iri_cho, m.k_iri_entity, m.x_entity_class,\n"
                "       COALESCE(l.x_label_en, m.k_iri_entity) AS x_label\n"
                "FROM read_parquet('{exports_dir}/map_edm_entities.parquet') m\n"
                "LEFT JOIN entity_labels l ON l.k_iri = m.k_iri_entity\n"
                # Sort so Parquet row-group min/max stats prune by class
                # and entity — every facet query filters on these.
                "ORDER BY m.x_entity_class, m.k_iri_entity"
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# explorer_<class> — per-class slices of explorer_edm_entities
# ---------------------------------------------------------------------------


_EXPLORER_PER_CLASS_TABLES = {
    # Parquet table_name → entity-class enum value
    "explorer_topics":  "skos_Concept",
    "explorer_agents":  "edm_Agent",
    "explorer_places":  "edm_Place",
    "explorer_periods": "edm_TimeSpan",
}


def _explorer_per_class_steps(class_value: str) -> list[ComposeStep]:
    """One-step compose for a per-class slice of explorer_edm_entities.

    Drops the redundant ``x_entity_class`` column (the file name encodes
    the class) and sorts by ``k_iri_entity`` so subsequent filtered
    facet queries get row-group pruning.
    """
    sql = (
        "SELECT k_iri_cho, k_iri_entity, x_label\n"
        "FROM read_parquet('{exports_dir}/explorer_edm_entities.parquet')\n"
        f"WHERE x_entity_class = '{class_value}'\n"
        "ORDER BY k_iri_entity"
    )
    return [ComposeStep(name="explorer_per_class_final", sql=sql, is_final=True)]


# ---------------------------------------------------------------------------
# explorer_facet_top_n — precomputed top-N per class for instant cold open
# ---------------------------------------------------------------------------


_EXPLORER_FACET_TOP_N_LIMIT = 500


def explorer_facet_top_n_steps() -> list[ComposeStep]:
    """Return compose steps for explorer_facet_top_n.

    Aggregates explorer_edm_entities to one row per (class, entity)
    with `x_item_count` and a per-class `x_rank`. Keeps only the top
    `_EXPLORER_FACET_TOP_N_LIMIT` entities per class — enough to fill
    the initial CategoricalFacet render without the explorer having
    to run a live aggregation when no other filters are active.
    """
    sql = (
        "WITH ranked AS (\n"
        "  SELECT x_entity_class,\n"
        "         k_iri_entity,\n"
        "         ANY_VALUE(x_label) AS x_label,\n"
        "         COUNT(*) AS x_item_count,\n"
        "         ROW_NUMBER() OVER (\n"
        "           PARTITION BY x_entity_class\n"
        "           ORDER BY COUNT(*) DESC\n"
        "         ) AS x_rank\n"
        "  FROM read_parquet('{exports_dir}/explorer_edm_entities.parquet')\n"
        "  GROUP BY 1, 2\n"
        ")\n"
        "SELECT x_entity_class, x_rank, k_iri_entity, x_label, x_item_count\n"
        "FROM ranked\n"
        f"WHERE x_rank <= {_EXPLORER_FACET_TOP_N_LIMIT}\n"
        "ORDER BY x_entity_class, x_rank"
    )
    return [ComposeStep(name="explorer_facet_top_n_final", sql=sql, is_final=True)]


# ---------------------------------------------------------------------------
# Registry dispatcher
# ---------------------------------------------------------------------------


def compose_steps_for(table_name: str) -> list[ComposeStep]:
    """Return the ComposeStep list for a composable export, or ``[]``."""
    info = export_classes().get(table_name)
    if info is None:
        return []
    et = info.export_type
    if et == "group" and table_name == "group_items":
        return group_items_steps()
    if et == "map":
        if table_name == "map_rights":
            return map_rights_steps()
        if table_name == "map_sameAs":
            return map_sameAs_steps()
        if table_name == "map_cho_entities":
            return map_cho_entities_steps()
        if table_name == "map_edm_entities":
            return map_edm_entities_steps()
        if table_name == "explorer_edm_entities":
            return explorer_edm_entities_steps()
        if table_name in _EXPLORER_PER_CLASS_TABLES:
            return _explorer_per_class_steps(
                _EXPLORER_PER_CLASS_TABLES[table_name]
            )
        if table_name == "explorer_facet_top_n":
            return explorer_facet_top_n_steps()
    return []


def chunked_compose_steps_for(
    table_name: str,
) -> tuple[list[ComposeStep], list[ComposeStep]] | None:
    """Return ``(shared, per_chunk)`` step lists for a chunkable composite,
    or ``None`` if ``table_name`` does not support chunked composition.

    Shared steps are built once per run and reused across chunks;
    per-chunk steps are rebuilt with ``CREATE OR REPLACE TEMP TABLE``
    for each ``chunk_chos`` slice.
    """
    if table_name == "group_items":
        return group_items_shared_steps(), group_items_chunk_steps()
    return None
