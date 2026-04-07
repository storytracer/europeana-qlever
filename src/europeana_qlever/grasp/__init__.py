"""GRASP resource files for the Europeana QLever integration.

This package bundles the static resource files needed by the GRASP
NL→SPARQL server (SPARQL templates, prefix mappings) as package data.
Runtime configuration (``europeana-grasp.yaml``, ``europeana-notes.json``,
search indices) is generated into the work directory by the
``write-grasp-config`` and ``grasp-setup`` CLI commands.
"""

from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent


def resource_path(name: str) -> Path:
    """Return the path to a bundled GRASP resource file.

    Available resources:

    - ``prefixes.json``
    - ``europeana-entity.sparql``
    - ``europeana-property.sparql``
    - ``entities-info.sparql``
    - ``properties-info.sparql``
    """
    path = _DIR / name
    if not path.exists():
        raise FileNotFoundError(f"GRASP resource not found: {name}")
    return path
