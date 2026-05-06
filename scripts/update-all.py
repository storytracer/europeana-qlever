# /// script
# requires-python = ">=3.11"
# ///
"""Run every ``scripts/update-*.py`` in dependency order.

Useful as a one-shot refresh of all locally-vendored upstream artifacts:
QLever docs, Europeana KB, EDM schema (with its ontology cache), and the
Metis vocabulary registry.

Order matters slightly: ``update-edm-schema.py`` reads files in
``references/ontologies/`` that other scripts may also touch, so it runs
last to pick up the freshest inputs.

Usage:
    uv run scripts/update-all.py            # run everything
    uv run scripts/update-all.py --skip metis-vocabularies qlever-docs
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent

# Listed in the order we want them to run.
SCRIPTS: list[str] = [
    "update-qlever-docs.py",
    "update-europeana-docs.py",
    "update-metis-vocabularies.py",
    "update-edm-schema.py",
]


def short_name(filename: str) -> str:
    """Strip ``update-`` prefix and ``.py`` suffix for CLI matching."""
    return filename.removeprefix("update-").removesuffix(".py")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip",
        nargs="+",
        default=[],
        metavar="NAME",
        help="One or more script short names to skip "
             f"(choices: {', '.join(short_name(s) for s in SCRIPTS)}).",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        default=None,
        metavar="NAME",
        help="Run only the named scripts; mutually exclusive with --skip.",
    )
    args = parser.parse_args()

    if args.only and args.skip:
        parser.error("--only and --skip cannot be combined.")

    selected: list[str] = []
    for script in SCRIPTS:
        name = short_name(script)
        if args.only is not None and name not in args.only:
            continue
        if name in args.skip:
            continue
        selected.append(script)

    if not selected:
        print("No scripts selected; nothing to do.")
        return 0

    print(f"Running {len(selected)} update script(s):")
    for script in selected:
        print(f"  - {script}")
    print()

    failures: list[str] = []
    for script in selected:
        path = SCRIPTS_DIR / script
        print(f"=== {script} ===")
        result = subprocess.run(["uv", "run", str(path)], cwd=REPO_ROOT)
        if result.returncode != 0:
            failures.append(script)
            print(f"  FAILED with exit code {result.returncode}")
        print()

    if failures:
        print(f"FAILED: {len(failures)} script(s) — {', '.join(failures)}")
        return 1

    print(f"OK: all {len(selected)} script(s) completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
