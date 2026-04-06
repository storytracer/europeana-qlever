# /// script
# requires-python = ">=3.11"
# ///
"""Sync qlever-docs from upstream into docs/qlever/docs/.

Usage:
    uv run scripts/update-qlever-docs.py
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

REPO_URL = "https://github.com/qlever-dev/qlever-docs"
REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "docs" / "qlever" / "docs"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["git", "clone", "--depth", "1", REPO_URL, tmp],
            check=True,
        )
        if TARGET.exists():
            shutil.rmtree(TARGET)
        TARGET.mkdir(parents=True)
        for md in (Path(tmp) / "docs").rglob("*.md"):
            dest = TARGET / md.relative_to(Path(tmp) / "docs")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(md, dest)

    print(f"Updated qlever docs in {TARGET.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
