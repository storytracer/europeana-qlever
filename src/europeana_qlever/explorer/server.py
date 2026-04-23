"""Minimal threaded HTTP server for the DuckDB-WASM explorer.

Serves two roots on a single port:

- ``/``       → bundled static SPA (``explorer/static/``)
- ``/data/``  → the user's local exports directory, so DuckDB-WASM can fetch
                Parquet files over HTTP with Range requests.

All responses carry permissive CORS headers and ``Accept-Ranges: bytes``.
The stdlib :class:`http.server.SimpleHTTPRequestHandler` does **not** honour
``Range`` requests out of the box — it always sends the full file with a 200
response — so we re-implement ``send_head`` to emit ``206 Partial Content``
and override ``copyfile`` to stop after the byte count requested.
"""

from __future__ import annotations

import http.server
import os
import re
import socket
import socketserver
import urllib.parse
from http import HTTPStatus
from pathlib import Path


_DATA_PREFIX = "/data/"
_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


class ExplorerHandler(http.server.SimpleHTTPRequestHandler):
    """Dispatches ``/`` to the static SPA and ``/data/`` to the exports dir,
    with CORS + full HTTP Range support."""

    # Class attributes populated by make_handler()
    static_root: Path = Path(".")
    data_root: Path = Path(".")

    # --- CORS + range advertisement ---------------------------------------

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Range, Content-Type")
        self.send_header(
            "Access-Control-Expose-Headers",
            "Accept-Ranges, Content-Range, Content-Length",
        )
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler style)
        self.send_response(204)
        self.end_headers()

    # --- routing ----------------------------------------------------------

    def translate_path(self, path: str) -> str:
        trimmed = path.split("?", 1)[0].split("#", 1)[0]
        trimmed = urllib.parse.unquote(trimmed)

        if trimmed.startswith(_DATA_PREFIX):
            rel = trimmed[len(_DATA_PREFIX):]
            return str(_safe_join(self.data_root, rel))

        rel = trimmed.lstrip("/")
        if rel in ("", "/"):
            rel = "index.html"
        return str(_safe_join(self.static_root, rel))

    # --- Range-aware send_head --------------------------------------------
    #
    # Structure mirrors the stdlib SimpleHTTPRequestHandler.send_head but
    # parses the Range header and emits a 206 with Content-Range when the
    # client asks for a slice. self._range_length is consumed by copyfile()
    # below to cap the bytes actually written to the socket.

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            # Redirect to trailing-slash form, then serve index.html like the
            # stdlib does.
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith("/"):
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + "/", parts[3], parts[4])
                self.send_header("Location", urllib.parse.urlunsplit(new_parts))
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            for candidate in ("index.html", "index.htm"):
                p = os.path.join(path, candidate)
                if os.path.exists(p):
                    path = p
                    break
            else:
                # Intentionally 404 on directory listings — the explorer
                # doesn't want browsable indexes into the exports dir.
                self.send_error(HTTPStatus.NOT_FOUND, "Not found")
                return None

        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return None

        try:
            fs = os.fstat(f.fileno())
            size = fs.st_size
            ctype = self.guess_type(path)

            range_hdr = self.headers.get("Range")
            start, end, status = 0, size - 1, HTTPStatus.OK

            if range_hdr and size > 0:
                m = _RANGE_RE.match(range_hdr.strip())
                if not m:
                    self._send_range_not_satisfiable(f, size)
                    return None
                s_str, e_str = m.group(1), m.group(2)
                if s_str == "" and e_str == "":
                    self._send_range_not_satisfiable(f, size)
                    return None
                if s_str == "":
                    # Suffix form: bytes=-N → last N bytes.
                    n = int(e_str)
                    if n == 0:
                        self._send_range_not_satisfiable(f, size)
                        return None
                    start = max(0, size - n)
                    end = size - 1
                else:
                    start = int(s_str)
                    end = int(e_str) if e_str else size - 1
                end = min(end, size - 1)
                if start >= size or start > end:
                    self._send_range_not_satisfiable(f, size)
                    return None
                status = HTTPStatus.PARTIAL_CONTENT

            length = end - start + 1
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(length))
            self.send_header(
                "Last-Modified", self.date_time_string(int(fs.st_mtime))
            )
            if status == HTTPStatus.PARTIAL_CONTENT:
                self.send_header(
                    "Content-Range", f"bytes {start}-{end}/{size}"
                )
            self.end_headers()

            if start > 0:
                f.seek(start)
            # Consumed by copyfile() below.
            self._range_length = length
            return f
        except BaseException:
            f.close()
            raise

    def _send_range_not_satisfiable(self, f, size: int) -> None:
        f.close()
        self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
        self.send_header("Content-Range", f"bytes */{size}")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def copyfile(self, source, outputfile) -> None:  # type: ignore[override]
        # HEAD responses never call copyfile (stdlib does_HEAD discards the
        # file). For GET, copy at most self._range_length bytes.
        limit = getattr(self, "_range_length", None)
        if limit is None:
            super().copyfile(source, outputfile)
            return
        remaining = limit
        chunk_size = 64 * 1024
        while remaining > 0:
            buf = source.read(min(chunk_size, remaining))
            if not buf:
                break
            outputfile.write(buf)
            remaining -= len(buf)

    # --- quieter logs -----------------------------------------------------

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        import sys
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


def _safe_join(root: Path, rel: str) -> Path:
    """Resolve ``rel`` under ``root`` and refuse paths that escape ``root``."""
    candidate = (root / rel).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return root_resolved
    return candidate


def make_handler(static_root: Path, data_root: Path) -> type[ExplorerHandler]:
    """Build an :class:`ExplorerHandler` subclass bound to the given roots."""

    class _Bound(ExplorerHandler):
        pass

    _Bound.static_root = static_root
    _Bound.data_root = data_root
    return _Bound


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Threaded so range requests for a big Parquet don't block the SPA."""

    daemon_threads = True
    allow_reuse_address = True


def find_free_port(start: int, attempts: int = 20) -> int:
    """Return the first free port in [start, start+attempts)."""
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise OSError(
        f"No free port in range {start}..{start + attempts - 1}"
    )


def serve(
    static_root: Path,
    data_root: Path,
    port: int,
) -> ThreadedServer:
    """Create (but do not block on) a server. Caller runs ``serve_forever``."""
    handler = make_handler(static_root, data_root)
    return ThreadedServer(("127.0.0.1", port), handler)
