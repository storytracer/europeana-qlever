# /// script
# requires-python = ">=3.11"
# dependencies = ["confluence-markdown-exporter"]
# ///
"""Sync Europeana Knowledge Base docs from Confluence into docs/europeana/.

Uses confluence-markdown-exporter (cme) with anonymous access.
Incremental: only pages changed since last run are re-exported,
tracked via docs/europeana/confluence-lock.json.

After export, local attachment references are rewritten to point at
the live Confluence download URLs and the local attachments directory
is deleted (so binary files are never committed to git).

Usage:
    uv run scripts/update-europeana-docs.py
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

SPACE_URL = "https://europeana.atlassian.net/wiki/spaces/EF/overview"
WIKI_BASE = "https://europeana.atlassian.net/wiki"
SPACE_KEY = "EF"
REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "docs" / "europeana"

# Matches local attachment refs like  attachments/uuid.ext  or  ../attachments/uuid.ext
_LOCAL_ATT_RE = re.compile(
    r"(?:\.\./)*(attachments/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.[a-z]+)"
)


def _fetch_attachment_map() -> dict[str, str]:
    """Query the Confluence REST API (anonymous) to build file_id → download URL."""
    mapping: dict[str, str] = {}
    cql = f"type=attachment AND space={SPACE_KEY}"
    url = f"{WIKI_BASE}/rest/api/content/search?cql={urllib.request.quote(cql)}&limit=250&expand=extensions"

    while url:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        for result in data.get("results", []):
            ext = result.get("extensions", {})
            links = result.get("_links", {})
            file_id = ext.get("fileId", "")
            download = links.get("download", "")
            if file_id and download:
                # download is relative like /download/attachments/123/file.png?...
                mapping[file_id] = WIKI_BASE + download

        next_link = data.get("_links", {}).get("next")
        url = (WIKI_BASE + next_link) if next_link else None

    return mapping


def _rewrite_attachments(att_map: dict[str, str]) -> int:
    """Replace local attachment paths with remote Confluence URLs in all markdown files."""
    count = 0
    for md_file in TARGET.rglob("*.md"):
        text = md_file.read_text(encoding="utf-8")

        def _replace(m: re.Match) -> str:
            nonlocal count
            # Extract the file_id (uuid) from the path
            local_path = m.group(1)  # attachments/uuid.ext
            file_id = local_path.split("/")[1].rsplit(".", 1)[0]
            if file_id in att_map:
                count += 1
                return att_map[file_id]
            return m.group(0)

        new_text = _LOCAL_ATT_RE.sub(_replace, text)
        if new_text != text:
            md_file.write_text(new_text, encoding="utf-8")

    return count


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)

    # Write a temporary config file for anonymous access (no credentials).
    config = {
        "export": {
            "log_level": "INFO",
            "skip_unchanged": True,
            "cleanup_stale": True,
            "include_document_title": True,
            "page_breadcrumbs": False,
            "enable_jira_enrichment": False,
            "page_path": "{space_name}/{ancestor_titles}/{page_title}.md",
            "output_path": str(TARGET),
        },
        "connection_config": {
            "max_workers": 20,
        },
        "auth": {
            "confluence": {},
            "jira": {},
        },
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(config, f)
        config_path = f.name

    try:
        env = {**os.environ, "CME_CONFIG_PATH": config_path}
        subprocess.run(
            ["cme", "spaces", SPACE_URL],
            env=env,
            stdin=subprocess.DEVNULL,
            check=True,
        )
    finally:
        Path(config_path).unlink(missing_ok=True)

    # Replace local attachment paths with live Confluence download URLs.
    print("Fetching attachment metadata from Confluence API...")
    att_map = _fetch_attachment_map()
    print(f"  {len(att_map)} attachments indexed")

    replaced = _rewrite_attachments(att_map)
    print(f"  {replaced} local references rewritten to remote URLs")

    # Delete downloaded attachment files — they should not be committed.
    att_dir = TARGET / "Europeana Knowledge Base" / "attachments"
    if att_dir.exists():
        shutil.rmtree(att_dir)
        print(f"  Deleted {att_dir.relative_to(REPO_ROOT)}")

    print(f"Updated Europeana docs in {TARGET.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
