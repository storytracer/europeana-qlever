"""Shared DuckDB engine over exported Parquet files.

Provides a :class:`ParquetStore` that registers all Parquet files in the
exports directory as DuckDB views, applies :class:`ReportFilters` to
``items_resolved``, and creates convenience views (``items``, ``org_names``).

Used by :class:`~europeana_qlever.ask.parquet.AskParquet`,
:class:`~europeana_qlever.report.ExportReport`, and
:class:`~europeana_qlever.ask.benchmark.Benchmark`.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from ..report import ReportFilters


class ParquetStore:
    """DuckDB connection over exported Parquet files.

    On construction, discovers all ``*.parquet`` files in *exports_dir*,
    registers each as a DuckDB view named after its stem, and optionally
    applies a :class:`ReportFilters` WHERE clause to ``items_resolved``.

    Also creates:

    - ``items`` — alias for ``items_resolved`` (used by report sections)
    - ``org_names`` — English-preferred organisation names from
      ``institutions.parquet`` (used by report volume section)
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
        """Register Parquet files as views and create convenience aliases."""
        self._con.execute(f"SET memory_limit = '{self._memory_limit}'")

        for pq_file in sorted(self._exports_dir.glob("*.parquet")):
            name = pq_file.stem
            path_str = str(pq_file)

            if (
                name == "items_resolved"
                and self._filters
                and not self._filters.is_empty()
            ):
                where = self._filters.to_duckdb_where()
                self._con.execute(
                    f"CREATE VIEW {name} AS "
                    f"SELECT * FROM read_parquet('{path_str}') {where}"
                )
            else:
                self._con.execute(
                    f"CREATE VIEW {name} AS "
                    f"SELECT * FROM read_parquet('{path_str}')"
                )
            self._tables[name] = pq_file

        # Alias used by report sections (they query FROM items)
        if "items_resolved" in self._tables:
            self._con.execute(
                "CREATE VIEW items AS SELECT * FROM items_resolved"
            )

        # Organisation names convenience view
        if "institutions" in self._tables:
            self._con.execute("""
                CREATE VIEW org_names AS
                SELECT org,
                       COALESCE(
                           MAX(name) FILTER (WHERE lang = 'en'),
                           MAX(name)
                       ) AS name
                FROM institutions
                GROUP BY org
            """)
        else:
            self._con.execute(
                "CREATE VIEW org_names AS "
                "SELECT NULL::VARCHAR AS org, NULL::VARCHAR AS name "
                "WHERE false"
            )

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """The underlying DuckDB connection."""
        return self._con

    @property
    def tables(self) -> dict[str, Path]:
        """Mapping of registered table name → Parquet file path."""
        return dict(self._tables)

    @property
    def filters(self) -> ReportFilters | None:
        """Active filters applied to items_resolved, or None."""
        return self._filters

    @property
    def exports_dir(self) -> Path:
        """The exports directory."""
        return self._exports_dir

    def execute(self, sql: str):
        """Execute a SQL statement."""
        return self._con.execute(sql)

    def close(self) -> None:
        """Close the DuckDB connection."""
        self._con.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
