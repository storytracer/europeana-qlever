"""Shared Rich console and display helpers for narrow-terminal support.

Set ``EUROPEANA_QLEVER_WIDTH`` env var or pass ``--width`` to the CLI
to force a fixed console width (e.g. 50 for phone in portrait mode).
"""

from __future__ import annotations

import os
from pathlib import Path

from rich.console import Console

# Default: env var → int, else None (Rich auto-detects)
_width: int | None = None
_env = os.environ.get("EUROPEANA_QLEVER_WIDTH")
if _env:
    try:
        _width = int(_env)
    except ValueError:
        pass

console = Console(width=_width)


def set_width(w: int) -> None:
    """Replace the shared console with one using the given fixed width."""
    global console
    console = Console(width=w)


def is_narrow() -> bool:
    """True when the console is 60 columns or fewer."""
    return (console.width or 80) <= 60


def short_path(p: Path, max_parts: int = 2) -> str:
    """Shorten a path to its last *max_parts* components when narrow."""
    if is_narrow() and len(p.parts) > max_parts:
        return str(Path("…", *p.parts[-max_parts:]))
    return str(p)
