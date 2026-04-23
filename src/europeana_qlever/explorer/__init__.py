"""Browser-based DuckDB-WASM explorer over Europeana Parquet exports.

This package ships the static single-page app (``static/index.html``,
``static/app.js``, ``static/style.css``) and a small threaded HTTP server
(``server.py``) that serves the app plus the local exports directory with
CORS + HTTP Range support — the minimum DuckDB-WASM's ``httpfs`` extension
needs to query a Parquet file over HTTP.

The ``europeana-qlever explore`` CLI command launches the server and opens
the browser.
"""

from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent


def static_dir() -> Path:
    """Return the bundled static-assets directory."""
    return _DIR / "static"
