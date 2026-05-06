# /// script
# requires-python = ">=3.11"
# ///
"""Sync metis-vocabularies from upstream into references/vocabularies/metis-vocabularies/.

Europeana's Metis enrichment pipeline uses a registry of authority vocabularies
(Wikidata, GND, VIAF, Getty AAT/TGN/ULAN, GeoNames, etc.) defined in the
europeana/metis-vocabularies repository. Each vocabulary has a YAML metadata
file declaring its URI prefixes, entity types, and an XSL mapping to convert
external RDF into EDM contextual classes.

This script mirrors the upstream resources directory locally so the rest of the
codebase can:
- discover canonical authority URI prefixes (``schema_loader.metis_vocabularies``)
- audit how many of Europeana's known vocabularies appear in our exports
- (eventually) re-run XSL transforms for federation top-up

Only the contents of ``src/main/resources/`` are copied; the upstream Maven layout is
flattened. The XSL mappings are kept alongside the YAML metadata files because they
encode which RDF properties Metis extracts per vocabulary.

Usage:
    uv run scripts/update-metis-vocabularies.py
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

REPO_URL = "https://github.com/europeana/metis-vocabularies"
REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "references" / "vocabularies" / "metis-vocabularies"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["git", "clone", "--depth", "1", REPO_URL, tmp],
            check=True,
        )
        source = Path(tmp) / "src" / "main" / "resources"
        if not source.is_dir():
            raise SystemExit(
                f"Expected {source} in upstream repo; layout may have changed."
            )
        if TARGET.exists():
            shutil.rmtree(TARGET)
        shutil.copytree(source, TARGET)

    yml_count = len(list(TARGET.rglob("*.yml")))
    xsl_count = len(list(TARGET.rglob("*.xsl")))
    print(
        f"Updated metis-vocabularies in {TARGET.relative_to(REPO_ROOT)} "
        f"({yml_count} metadata files, {xsl_count} XSL mappings)"
    )


if __name__ == "__main__":
    main()
