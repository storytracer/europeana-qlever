"""Shared DuckDB engine over exported Parquet files.

Provides a :class:`ParquetStore` that registers every ``*.parquet`` file
under the exports directory as a DuckDB view, applies
:class:`ReportFilters` to ``merged_items``, and creates convenience
views (``items``, ``orgs``) used by reports and the NL agent.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from ..report import ReportFilters


class ParquetStore:
    """DuckDB connection over exported Parquet files.

    On construction, discovers all ``*.parquet`` files in *exports_dir*,
    registers each as a DuckDB view named after its stem, and optionally
    applies a :class:`ReportFilters` WHERE clause to ``merged_items``.

    Convenience views:

    - ``items`` — alias for ``merged_items`` (back-compat for reports)
    - ``orgs`` — English-preferred organisation names from
      ``values_foaf_Organization`` (one row per organisation URI)
    """

    def __init__(
        self,
        exports_dir: Path,
        *,
        filters: ReportFilters | None = None,
        memory_limit: str = "4GB",
    ) -> None:
        self._exports_dir = exports_dir
        self._filters = filters
        self._memory_limit = memory_limit
        self._con = duckdb.connect()
        self._tables: dict[str, Path] = {}
        self._setup()

    def _setup(self) -> None:
        self._con.execute(f"SET memory_limit = '{self._memory_limit}'")

        for pq_file in sorted(self._exports_dir.glob("*.parquet")):
            name = pq_file.stem
            # Skip dotfiles and any intermediate directory contents
            if name.startswith("."):
                continue
            path_str = str(pq_file)

            if (
                name == "merged_items"
                and self._filters
                and not self._filters.is_empty()
            ):
                where = self._filters.to_duckdb_where()
                self._con.execute(
                    f'CREATE VIEW "{name}" AS '
                    f"SELECT * FROM read_parquet('{path_str}') {where}"
                )
            else:
                self._con.execute(
                    f'CREATE VIEW "{name}" AS '
                    f"SELECT * FROM read_parquet('{path_str}')"
                )
            self._tables[name] = pq_file

        # Back-compat alias for reports / agent: items → merged_items.
        if "merged_items" in self._tables:
            self._con.execute(
                "CREATE VIEW items AS SELECT * FROM merged_items"
            )

        # Organisation names — English-preferred.
        if "values_foaf_Organization" in self._tables:
            self._con.execute("""
                CREATE VIEW orgs AS
                SELECT k_iri AS k_iri,
                       COALESCE(
                           MAX(v_skos_prefLabel) FILTER (WHERE x_prefLabel_lang = 'en'),
                           MAX(v_skos_prefLabel)
                       ) AS name,
                       MAX(v_edm_country) AS country,
                       MAX(v_edm_acronym) AS acronym
                FROM values_foaf_Organization
                GROUP BY k_iri
            """)
        else:
            self._con.execute(
                "CREATE VIEW orgs AS "
                "SELECT NULL::VARCHAR AS k_iri, NULL::VARCHAR AS name, "
                "NULL::VARCHAR AS country, NULL::VARCHAR AS acronym "
                "WHERE false"
            )

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        return self._con

    @property
    def tables(self) -> dict[str, Path]:
        return dict(self._tables)

    @property
    def filters(self) -> ReportFilters | None:
        return self._filters

    @property
    def exports_dir(self) -> Path:
        return self._exports_dir

    def execute(self, sql: str):
        return self._con.execute(sql)

    def close(self) -> None:
        self._con.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
