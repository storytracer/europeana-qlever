"""SPARQL-based report against a live QLever server.

Runs summary queries against the QLever SPARQL endpoint to produce a
lightweight report without needing exported Parquet files. Complements
the DuckDB-based report (:mod:`report`) which requires items_resolved.parquet.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx

from . import display
from .export import ExportRegistry, QueryExport
from .report import Report


def _run_query(sparql: str, qlever_url: str, timeout: int) -> list[dict]:
    """Execute a SPARQL query and return results as a list of dicts."""
    resp = httpx.post(
        qlever_url,
        data={"query": sparql, "action": "tsv_export"},
        timeout=httpx.Timeout(timeout + 30, connect=30),
    )
    resp.raise_for_status()

    lines = resp.text.strip().split("\n")
    if len(lines) < 2:
        return []
    headers = [h.lstrip("?") for h in lines[0].split("\t")]
    rows = []
    for line in lines[1:]:
        cells = line.split("\t")
        rows.append(dict(zip(headers, cells)))
    return rows


def run_sparql_report(
    *,
    qlever_url: str,
    timeout: int,
    output_dir: Path,
) -> Report:
    """Run summary SPARQL queries and produce a Markdown report."""
    from . import __version__

    output_dir.mkdir(parents=True, exist_ok=True)

    registry = ExportRegistry()
    data: dict = {}
    sections = 0

    # Summary queries to run
    summary_queries = [
        "items_by_type",
        "items_by_country",
        "items_by_reuse_level",
        "items_by_rights_uri",
        "items_by_language",
        "items_by_year",
    ]

    display.console.print("[bold]Running SPARQL report…[/bold]")

    for qname in summary_queries:
        try:
            export = registry.get(qname)
        except KeyError:
            continue
        if not isinstance(export, QueryExport):
            continue

        display.console.print(f"  [dim]{qname}[/dim]")
        t0 = time.perf_counter()
        try:
            rows = _run_query(export.sparql, qlever_url, timeout)
            elapsed = time.perf_counter() - t0
            data[qname] = {
                "rows": rows,
                "row_count": len(rows),
                "elapsed_s": round(elapsed, 2),
            }
            sections += 1
        except Exception as exc:
            display.console.print(f"    [red]Failed: {exc}[/red]")
            data[qname] = {"error": str(exc)}

    # Metadata
    data["_meta"] = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version": __version__,
        "qlever_url": qlever_url,
        "mode": "sparql",
    }

    # Render markdown
    md_lines = ["# Europeana SPARQL Report\n"]
    meta = data["_meta"]
    md_lines.append(f"**Generated:** {meta['timestamp']}")
    md_lines.append(f"**Endpoint:** {meta['qlever_url']}\n")

    for qname in summary_queries:
        if qname not in data or "error" in data[qname]:
            continue
        section = data[qname]
        md_lines.append(f"## {qname.replace('_', ' ').title()}\n")
        md_lines.append(f"*{section['row_count']} rows in {section['elapsed_s']}s*\n")
        rows = section["rows"]
        if rows:
            headers = list(rows[0].keys())
            md_lines.append("| " + " | ".join(headers) + " |")
            md_lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for row in rows[:50]:  # cap at 50 rows
                md_lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
        md_lines.append("")

    # Write outputs
    json_path = output_dir / "report_sparql.json"
    md_path = output_dir / "report_sparql.md"

    json_path.write_text(json.dumps(data, indent=2, default=str))
    md_path.write_text("\n".join(md_lines) + "\n")

    display.console.print(f"\n[green]SPARQL report complete ({sections} sections)[/green]")
    display.console.print(f"  JSON: {json_path}")
    display.console.print(f"  Markdown: {md_path}")

    return Report(
        json_path=json_path,
        markdown_path=md_path,
        sections_computed=sections,
        data=data,
    )
