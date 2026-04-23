"""Threaded HTTP server for the DuckDB-backed explorer.

Serves the bundled single-page app at ``/`` and exposes JSON POST
endpoints that a :class:`ExplorerEngine` answers directly against a local
DuckDB connection:

- ``POST /api/schema``     → column list + total-row count + numeric ranges
- ``POST /api/summary``    → filtered count, chart bars, distinct-count cards
- ``POST /api/top-values`` → facet values for a column
- ``POST /api/sample``     → N random rows matching filters
- ``POST /api/labels``     → resolve organisation IRIs to skos:prefLabel

All user-supplied values are bound as DuckDB parameters. Column identifiers
are whitelisted against the schema before being spliced into SQL.
"""

from __future__ import annotations

import http.server
import json
import socket
import socketserver
import threading
import traceback
import urllib.parse
from http import HTTPStatus
from pathlib import Path
from typing import Any

import duckdb


# ---------------------------------------------------------------------------
# DuckDB engine
# ---------------------------------------------------------------------------

_MAX_BODY_BYTES = 1_000_000
_CHART_LIMIT = 30
_MAX_LABEL_LOOKUP = 1_000

# Columns whose values are organisation IRIs that can be resolved to
# human-readable labels via the values_foaf_Organization parquet.
_LABEL_RESOLVABLE_COLUMNS = ("v_edm_dataProvider", "v_edm_provider")


class ExplorerEngine:
    """Holds the long-lived DuckDB connection and answers API requests."""

    def __init__(
        self,
        parquet: str,
        *,
        memory_limit: str = "4GB",
        threads: int = 2,
        organizations_parquet: str | None = None,
    ) -> None:
        self.lock = threading.Lock()
        self.con = duckdb.connect()
        self.con.execute(f"SET memory_limit = '{memory_limit}'")
        self.con.execute(f"SET threads = {int(threads)}")
        # DuckDB doesn't accept parameters in DDL — escape quotes manually.
        # The source string is either a resolved local path or a --data-url
        # supplied by the CLI user; neither is untrusted in the usual sense.
        escaped = parquet.replace("'", "''")
        self.con.execute(
            f"CREATE VIEW items AS SELECT * FROM read_parquet('{escaped}')"
        )

        schema_rows = self.con.execute(
            "DESCRIBE SELECT * FROM items LIMIT 0"
        ).fetchall()
        self.columns: list[dict[str, Any]] = []
        for row in schema_rows:
            name, ctype = row[0], str(row[1]).upper()
            self.columns.append({
                "name": name,
                "type": ctype,
                "category": _categorize(name, ctype),
            })
        self.column_set = {c["name"]: c for c in self.columns}

        self.total_count = int(
            self.con.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        )

        self._load_numeric_ranges()

        self.label_columns: list[str] = []
        if organizations_parquet:
            escaped_orgs = organizations_parquet.replace("'", "''")
            self.con.execute(
                "CREATE VIEW organizations AS "
                f"SELECT * FROM read_parquet('{escaped_orgs}')"
            )
            self.label_columns = [
                c for c in _LABEL_RESOLVABLE_COLUMNS if c in self.column_set
            ]

    # -- startup ---------------------------------------------------------

    def _load_numeric_ranges(self) -> None:
        numerics = [c for c in self.columns if c["category"] == "numeric"]
        if not numerics:
            return
        selects = []
        for i, c in enumerate(numerics):
            q = f'"{c["name"]}"'
            selects.append(f"MIN({q}) AS mn{i}")
            selects.append(f"MAX({q}) AS mx{i}")
        row = self.con.execute(
            f"SELECT {', '.join(selects)} FROM items"
        ).fetchone()
        for i, c in enumerate(numerics):
            c["min"] = _to_num(row[i * 2])
            c["max"] = _to_num(row[i * 2 + 1])

    # -- filter → SQL -----------------------------------------------------

    def _build_where(self, filters: dict | None) -> tuple[str, list]:
        parts: list[str] = []
        params: list = []
        for col, f in (filters or {}).items():
            if col not in self.column_set or not isinstance(f, dict):
                continue  # silently drop unknown / malformed filters
            q = f'"{col}"'
            kind = f.get("kind")
            if kind == "in":
                values = f.get("values") or []
                if not isinstance(values, list) or not values:
                    continue
                parts.append(f"{q} IN ({', '.join(['?'] * len(values))})")
                params.extend(values)
            elif kind == "bool":
                parts.append(f"{q} = ?")
                params.append(bool(f.get("value")))
            elif kind == "range":
                mn, mx = f.get("min"), f.get("max")
                if mn is not None:
                    parts.append(f"{q} >= ?")
                    params.append(mn)
                if mx is not None:
                    parts.append(f"{q} <= ?")
                    params.append(mx)
        where = ("WHERE " + " AND ".join(parts)) if parts else ""
        return where, params

    # -- endpoints -------------------------------------------------------

    def schema_payload(self) -> dict:
        return {
            "total": self.total_count,
            "columns": self.columns,
            "label_columns": list(self.label_columns),
        }

    def resolve_labels(self, values: list[str]) -> dict:
        if not self.label_columns:
            return {"labels": {}}
        iris = [v for v in values if isinstance(v, str) and v]
        if not iris:
            return {"labels": {}}
        if len(iris) > _MAX_LABEL_LOOKUP:
            iris = iris[:_MAX_LABEL_LOOKUP]
        # Dedupe while preserving order.
        seen: dict[str, None] = {}
        for v in iris:
            seen.setdefault(v, None)
        unique = list(seen.keys())
        placeholders = ", ".join(["?"] * len(unique))
        # Prefer English labels, then unspecified language, then anything else.
        sql = (
            "SELECT k_iri, ARG_MIN(v_skos_prefLabel, "
            "CASE WHEN x_prefLabel_lang = 'en' THEN 0 "
            "WHEN COALESCE(x_prefLabel_lang, '') = '' THEN 1 "
            "ELSE 2 END) AS label "
            f"FROM organizations WHERE k_iri IN ({placeholders}) "
            "GROUP BY k_iri"
        )
        with self.lock:
            rows = self.con.execute(sql, unique).fetchall()
        return {"labels": {iri: label for iri, label in rows if label}}

    def summary(self, filters: dict, group_by: str) -> dict:
        if group_by not in self.column_set:
            raise ValueError(f"unknown group_by column: {group_by}")
        where, params = self._build_where(filters)
        gb = f'"{group_by}"'

        country_col = (
            "v_edm_country" if "v_edm_country" in self.column_set else None
        )
        provider_col = (
            "v_edm_dataProvider"
            if "v_edm_dataProvider" in self.column_set
            else None
        )

        summary_selects = ["COUNT(*) AS filtered"]
        if country_col:
            summary_selects.append(
                f'approx_count_distinct("{country_col}") AS countries'
            )
        if provider_col:
            summary_selects.append(
                f'approx_count_distinct("{provider_col}") AS providers'
            )

        with self.lock:
            summary_row = self.con.execute(
                f"SELECT {', '.join(summary_selects)} FROM items {where}",
                params,
            ).fetchone()
            chart_rows = self.con.execute(
                f"SELECT {gb} AS v, COUNT(*) AS n "
                f"FROM items {where} "
                f"GROUP BY 1 ORDER BY 2 DESC LIMIT {_CHART_LIMIT}",
                params,
            ).fetchall()

        filtered = int(summary_row[0])
        idx = 1
        countries = int(summary_row[idx]) if country_col else None
        if country_col:
            idx += 1
        providers = int(summary_row[idx]) if provider_col else None

        return {
            "filtered": filtered,
            "chart": [
                {"value": _json_scalar(v), "count": int(n)}
                for v, n in chart_rows
            ],
            "countries": countries,
            "providers": providers,
        }

    def top_values(
        self, col: str, filters: dict, limit: int = 200
    ) -> dict:
        if col not in self.column_set:
            raise ValueError(f"unknown column: {col}")
        limit = max(1, min(int(limit), 1000))
        where, params = self._build_where(filters)
        q = f'"{col}"'
        predicate = f"{q} IS NOT NULL"
        if where:
            full_where = f"{where} AND {predicate}"
        else:
            full_where = f"WHERE {predicate}"

        with self.lock:
            rows = self.con.execute(
                f"SELECT {q} AS v, COUNT(*) AS n "
                f"FROM items {full_where} "
                f"GROUP BY 1 ORDER BY 2 DESC LIMIT ?",
                params + [limit + 1],  # +1 to detect truncation
            ).fetchall()

        truncated = len(rows) > limit
        rows = rows[:limit]
        return {
            "values": [
                {"value": _json_scalar(v), "count": int(n)} for v, n in rows
            ],
            "truncated": truncated,
        }

    def sample(self, filters: dict, n: int = 10) -> dict:
        n = max(1, min(int(n), 1000))
        where, params = self._build_where(filters)
        # USING SAMPLE applied to `items` directly samples BEFORE the WHERE,
        # so a selective filter would yield an empty result. Wrap in a
        # subquery so the reservoir samples from the filtered stream.
        sql = (
            f"SELECT * FROM (SELECT * FROM items {where}) "
            f"USING SAMPLE {n} ROWS"
        )
        with self.lock:
            cur = self.con.execute(sql, params)
            rows = cur.fetchall()
            col_names = [d[0] for d in cur.description]
        return {
            "rows": [
                {c: _json_scalar(v) for c, v in zip(col_names, row)}
                for row in rows
            ]
        }

    def close(self) -> None:
        with self.lock:
            self.con.close()


def _categorize(name: str, ctype: str) -> str:
    if name.startswith("k_"):
        return "skip"
    if ctype == "BOOLEAN":
        return "boolean"
    if any(tok in ctype for tok in ("INT", "DOUBLE", "FLOAT", "REAL", "DECIMAL")):
        return "numeric"
    if ctype.startswith("VARCHAR") or ctype in ("STRING", "TEXT"):
        return "categorical"
    return "skip"


def _json_scalar(v):
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


def _to_num(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return int(v)
    return float(v)


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------


class ExplorerHandler(http.server.SimpleHTTPRequestHandler):
    """Serves static assets for ``/`` and JSON for ``/api/*`` POSTs."""

    # Bound per-server by make_handler().
    static_root: Path = Path(".")
    engine: ExplorerEngine | None = None

    # --- CORS -------------------------------------------------------------

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    # --- static routing ---------------------------------------------------

    def translate_path(self, path: str) -> str:
        trimmed = path.split("?", 1)[0].split("#", 1)[0]
        trimmed = urllib.parse.unquote(trimmed)
        rel = trimmed.lstrip("/")
        if rel in ("", "/"):
            rel = "index.html"
        return str(_safe_join(self.static_root, rel))

    # --- API dispatch -----------------------------------------------------

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        handler = _API.get(path)
        if handler is None:
            self.send_error(HTTPStatus.NOT_FOUND, f"Unknown endpoint: {path}")
            return

        length = int(self.headers.get("Content-Length") or 0)
        if length > _MAX_BODY_BYTES:
            self.send_error(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Body too large"
            )
            return

        try:
            raw = self.rfile.read(length) if length else b""
            body = json.loads(raw) if raw else {}
            if not isinstance(body, dict):
                raise ValueError("body must be a JSON object")
            if self.engine is None:
                raise RuntimeError("engine not initialised")
            result = handler(self.engine, body)
            payload = json.dumps(result, default=_json_scalar).encode("utf-8")
        except json.JSONDecodeError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return
        except ValueError as e:
            self.send_error(HTTPStatus.BAD_REQUEST, str(e))
            return
        except Exception as e:
            traceback.print_exc()
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    # --- quieter logs -----------------------------------------------------

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        import sys
        sys.stderr.write(
            "%s - %s\n" % (self.address_string(), format % args)
        )


# ---------------------------------------------------------------------------
# API handlers
# ---------------------------------------------------------------------------


def _schema(engine: ExplorerEngine, body: dict) -> dict:
    return engine.schema_payload()


def _summary(engine: ExplorerEngine, body: dict) -> dict:
    group_by = body.get("group_by")
    if not group_by or not isinstance(group_by, str):
        raise ValueError("missing group_by")
    filters = body.get("filters") or {}
    if not isinstance(filters, dict):
        raise ValueError("filters must be an object")
    return engine.summary(filters, group_by)


def _top_values(engine: ExplorerEngine, body: dict) -> dict:
    col = body.get("col")
    if not col or not isinstance(col, str):
        raise ValueError("missing col")
    filters = body.get("filters") or {}
    if not isinstance(filters, dict):
        raise ValueError("filters must be an object")
    limit = body.get("limit") or 200
    return engine.top_values(col, filters, int(limit))


def _sample(engine: ExplorerEngine, body: dict) -> dict:
    filters = body.get("filters") or {}
    if not isinstance(filters, dict):
        raise ValueError("filters must be an object")
    n = body.get("n") or 10
    return engine.sample(filters, int(n))


def _labels(engine: ExplorerEngine, body: dict) -> dict:
    values = body.get("values") or []
    if not isinstance(values, list):
        raise ValueError("values must be an array")
    return engine.resolve_labels(values)


_API = {
    "/api/schema": _schema,
    "/api/summary": _summary,
    "/api/top-values": _top_values,
    "/api/sample": _sample,
    "/api/labels": _labels,
}


# ---------------------------------------------------------------------------
# Path safety + server wiring
# ---------------------------------------------------------------------------


def _safe_join(root: Path, rel: str) -> Path:
    candidate = (root / rel).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return root_resolved
    return candidate


def make_handler(
    static_root: Path, engine: ExplorerEngine
) -> type[ExplorerHandler]:
    class _Bound(ExplorerHandler):
        pass

    _Bound.static_root = static_root
    _Bound.engine = engine
    return _Bound


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def find_free_port(start: int, attempts: int = 20) -> int:
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise OSError(f"No free port in range {start}..{start + attempts - 1}")


def serve(
    static_root: Path,
    engine: ExplorerEngine,
    port: int,
) -> ThreadedServer:
    handler = make_handler(static_root, engine)
    return ThreadedServer(("127.0.0.1", port), handler)
