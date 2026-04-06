"""DuckDB composition SQL for hybrid SPARQL/DuckDB export pipeline.

Phase 1 exports simple, flat SPARQL scans to Parquet "base tables".
Phase 2 (this module) generates DuckDB SQL that reads those Parquet files,
joins them, resolves entity URIs to labels, aggregates multi-valued
properties into native LIST/STRUCT types, and writes the final
denormalized Parquet export.

SQL templates use ``{exports_dir}`` as a placeholder — replaced at
execution time with the actual path to the exports directory.

All column names, aggregation patterns, and entity resolution are derived
from the LinkML schema via :mod:`schema_loader`.
"""

from __future__ import annotations

from dataclasses import dataclass

from .schema_loader import (
    item_fields,
    reuse_level_sql,
    sparql_var,
)


@dataclass
class ComposeStep:
    """A single step in a multi-step DuckDB composition."""

    name: str
    sql: str
    is_final: bool = False

    # Placeholder used in SQL templates — replaced at execution time.
    _DIR = "{exports_dir}"

    @staticmethod
    def items_resolved_steps() -> list[ComposeStep]:
        """Return ``items_resolved`` as discrete composition steps.

        Each step creates a DuckDB temp table.  The final step is a SELECT
        (not a CREATE) intended to be wrapped in a COPY statement by the caller.

        Steps are generated from the schema's multi-valued Item fields using
        their ``query_pattern``, ``base_table``, and ``entity_resolved``
        annotations.
        """
        _DIR = ComposeStep._DIR
        steps: list[ComposeStep] = []

        # Collect multi-valued fields from schema, grouped by pattern
        fields = item_fields()

        # We need entity label tables (agent_labels, concept_labels) before
        # the entity-resolved aggregation steps.
        entity_label_tables: set[str] = set()
        for _col_name, attr in fields.items():
            if attr.multivalued and attr.annotations.get("entity_resolved"):
                entity_label_tables.add(attr.annotations["entity_resolved"])

        # Generate entity label tables (concept_labels, agent_labels)
        if "concepts" in entity_label_tables:
            steps.append(ComposeStep("concept_labels", f"""\
CREATE TEMP TABLE concept_labels AS
    SELECT concept,
           COALESCE(
               MAX(pref_label) FILTER (WHERE pref_label_lang = 'en'),
               FIRST(pref_label)
           ) AS label
    FROM read_parquet('{_DIR}/concepts_core.parquet')
    GROUP BY concept"""))

        if "agents" in entity_label_tables:
            steps.append(ComposeStep("agent_labels", f"""\
CREATE TEMP TABLE agent_labels AS
    SELECT agent,
           COALESCE(
               MAX(pref_label) FILTER (WHERE pref_label_lang = 'en'),
               FIRST(pref_label)
           ) AS label
    FROM read_parquet('{_DIR}/agents_core.parquet')
    GROUP BY agent"""))

        # Aggregation join aliases for the final SELECT
        agg_joins: list[tuple[str, str, str]] = []  # (table_alias, col_name, alias_letter)

        # Track generated agg table names for the final join
        # Each entry: (agg_table_name, col_name)
        agg_tables: list[tuple[str, str]] = []

        # Entity label column mapping
        _entity_label_col = {"agents": "agent", "concepts": "concept"}
        # Entity label struct key mapping (agents->name, concepts->label)
        _entity_struct_map = {"agents": "name", "concepts": "label"}

        for col_name, attr in fields.items():
            if not attr.multivalued:
                continue
            pattern = attr.annotations.get("query_pattern")
            bt = attr.annotations.get("base_table")
            if not pattern or not bt:
                continue

            entity_resolved = attr.annotations.get("entity_resolved")
            range_type = attr.range
            agg_name = f"{col_name}_agg"

            if pattern == "lang_tagged":
                # LangValue: LIST<STRUCT<value, lang>>
                # The value variable in the Parquet is the CURIE local name
                curie = attr.slot_uri or ""
                val_var = curie.split(":")[1] if ":" in curie else col_name.rstrip("s")
                steps.append(ComposeStep(agg_name, f"""\
CREATE TEMP TABLE {agg_name} AS
    SELECT item,
           LIST({{value: NULLIF({val_var}, ''), lang: NULLIF(lang, '')}}) AS {col_name}
    FROM read_parquet('{_DIR}/{bt}.parquet')
    GROUP BY item"""))
                agg_tables.append((agg_name, col_name))

            elif pattern == "iri_or_literal" and entity_resolved:
                # Entity-resolved: needs a map table + agg
                stem = col_name.rstrip("s")
                val_var = f"{stem}_value"
                entity_id = _entity_label_col.get(entity_resolved, entity_resolved.rstrip("s"))
                label_table = f"{entity_resolved.rstrip('s')}_labels"
                struct_key = _entity_struct_map.get(entity_resolved, "label")
                map_name = f"{stem}_map"

                # Map step: resolve unique IRI values to labels
                steps.append(ComposeStep(map_name, f"""\
CREATE TEMP TABLE {map_name} AS
    SELECT s.uri, COALESCE(a.label, s.uri) AS label
    FROM (
        SELECT DISTINCT {val_var} AS uri
        FROM read_parquet('{_DIR}/{bt}.parquet')
        WHERE is_iri
    ) s
    LEFT JOIN {label_table} a ON s.uri = a.{entity_id}"""))

                # Agg step: LIST<STRUCT<{struct_key}, uri>>
                steps.append(ComposeStep(agg_name, f"""\
CREATE TEMP TABLE {agg_name} AS
    SELECT
        s.item,
        LIST({{
            {struct_key}: COALESCE(m.label, s.{val_var}),
            uri: CASE WHEN s.is_iri THEN s.{val_var} END
        }}) AS {col_name}
    FROM read_parquet('{_DIR}/{bt}.parquet') s
    LEFT JOIN {map_name} m ON s.{val_var} = m.uri
    GROUP BY s.item"""))
                agg_tables.append((agg_name, col_name))

            elif pattern == "simple_literal":
                # Simple LIST<VARCHAR>
                sparql_name = col_name.rstrip("s") if col_name != "dc_rights" else "dc_rights"
                steps.append(ComposeStep(agg_name, f"""\
CREATE TEMP TABLE {agg_name} AS
    SELECT item, LIST({sparql_name}) AS {col_name}
    FROM read_parquet('{_DIR}/{bt}.parquet')
    GROUP BY item"""))
                agg_tables.append((agg_name, col_name))

        # Web resource aggregation
        steps.append(ComposeStep("wr_agg", f"""\
CREATE TEMP TABLE wr_agg AS
    SELECT
        item,
        FIRST(mime) AS mime_type,
        FIRST(TRY_CAST(width AS INTEGER)) AS width,
        FIRST(TRY_CAST(height AS INTEGER)) AS height,
        FIRST(TRY_CAST(bytes AS BIGINT)) AS file_bytes,
        BOOL_OR(has_service) AS has_iiif
    FROM read_parquet('{_DIR}/web_resources.parquet')
    GROUP BY item"""))

        # Build the final SELECT from schema
        select_parts = ["i.item"]

        # Generate unique aliases for all agg tables
        aliases = _make_aliases([col for _, col in agg_tables])

        # Multi-valued columns from agg tables
        for agg_name, col_name in agg_tables:
            alias = aliases[col_name]
            select_parts.append(f"{alias}.{col_name}")

        # Scalar columns from items_core
        scalar_cols = []
        for col_name, attr in fields.items():
            if attr.multivalued or attr.identifier or attr.annotations.get("computed") == "true":
                continue
            if attr.annotations.get("rdf_source") == "web_resource":
                continue  # handled by wr_agg
            sv = sparql_var("Item", col_name)
            if sv != col_name:
                # Column in Parquet uses the sparql_variable name, alias to schema name
                scalar_cols.append(f"NULLIF(i.{sv}, '') AS {col_name}")
            else:
                scalar_cols.append(f"i.{col_name}")

        select_parts.extend(scalar_cols)

        # Reuse level — computed from rights using schema patterns
        reuse_sql = reuse_level_sql("i.rights")
        select_parts.append(f"{reuse_sql} AS reuse_level")

        # Web resource columns — derived from Item fields with rdf_source=web_resource
        for col_name, attr in fields.items():
            if attr.annotations.get("rdf_source") == "web_resource":
                select_parts.append(f"wr.{col_name}")

        # Build JOIN clauses
        join_parts = []
        for agg_name, col_name in agg_tables:
            alias = aliases[col_name]
            join_parts.append(f"LEFT JOIN {agg_name} {alias} USING (item)")
        join_parts.append("LEFT JOIN wr_agg wr USING (item)")

        select_str = ",\n    ".join(select_parts)
        join_str = "\n".join(join_parts)

        steps.append(ComposeStep("join_and_write", f"""\
SELECT
    {select_str}
FROM read_parquet('{_DIR}/items_core.parquet') i
{join_str}""", is_final=True))

        return steps


def _make_aliases(col_names: list[str]) -> dict[str, str]:
    """Generate unique short SQL aliases for a list of column names."""
    aliases: dict[str, str] = {}
    used: set[str] = {"i", "wr"}  # reserved for items_core and web resources
    for col in col_names:
        # Try progressively longer prefixes until unique
        for length in range(3, len(col) + 1):
            candidate = col[:length]
            if candidate not in used:
                aliases[col] = candidate
                used.add(candidate)
                break
        else:
            aliases[col] = col
    return aliases
