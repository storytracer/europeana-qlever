"""Query performance analysis via QLever runtime information.

Sends SPARQL queries to QLever requesting JSON responses with execution
tree metadata, then renders a Markdown report identifying bottlenecks.
The report is designed to be pasted into a Claude Code prompt for
further diagnosis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from . import display


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class OperationNode:
    """A single node in the QLever query execution tree."""

    description: str
    time_ms: float
    result_rows: int
    result_cols: int
    estimated_size: int
    estimated_cost: float
    cache_status: str
    status: str
    details: dict
    children: list[OperationNode] = field(default_factory=list)


@dataclass
class QueryAnalysis:
    """Parsed analysis result for a single query."""

    name: str
    sparql: str
    description: str
    total_time: str
    compute_time: str
    planning_time_ms: float | None
    index_scans_planning_ms: float | None
    result_size: int
    columns: list[str]
    tree: OperationNode | None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# HTTP request
# ---------------------------------------------------------------------------

def run_analysis(
    query: str,
    qlever_url: str,
    timeout: int,
    *,
    send: int = 0,
) -> dict:
    """POST a SPARQL query to QLever and return the JSON response with
    runtime information.

    *send* controls how many result rows QLever transfers back (0 means
    metadata only).
    """
    response = httpx.post(
        qlever_url,
        data={"query": query, "send": str(send), "timeout": f"{timeout}s"},
        headers={"Accept": "application/qlever-results+json"},
        timeout=httpx.Timeout(timeout + 120, connect=30),
    )
    if response.status_code != 200:
        body = response.text[:2000]
        raise RuntimeError(
            f"QLever returned {response.status_code}:\n{body}"
        )
    return response.json()


# ---------------------------------------------------------------------------
# Execution tree parsing
# ---------------------------------------------------------------------------

def parse_tree(node: dict) -> OperationNode:
    """Recursively parse a QLever ``query_execution_tree`` node."""
    cache_status = node.get("cache_status", "")
    if not cache_status:
        cache_status = "cached_not_pinned" if node.get("was_cached") else "computed"

    if cache_status == "computed" or not node.get("was_cached", True):
        time_ms = node.get("operation_time", 0)
    else:
        time_ms = node.get("original_operation_time", node.get("operation_time", 0))

    children = [parse_tree(c) for c in node.get("children", [])]

    return OperationNode(
        description=node.get("description", ""),
        time_ms=float(time_ms),
        result_rows=int(node.get("result_rows", 0)),
        result_cols=int(node.get("result_cols", 0)),
        estimated_size=int(node.get("estimated_size", 0)),
        estimated_cost=float(node.get("estimated_operation_cost", 0)),
        cache_status=cache_status,
        status=node.get("status", ""),
        details=node.get("details", {}),
        children=children,
    )


def flatten_tree(
    node: OperationNode, depth: int = 0,
) -> list[tuple[int, OperationNode]]:
    """Depth-first flattening of the execution tree.

    Returns ``(depth, node)`` pairs suitable for table rendering.
    """
    result: list[tuple[int, OperationNode]] = [(depth, node)]
    for child in node.children:
        result.extend(flatten_tree(child, depth + 1))
    return result


# ---------------------------------------------------------------------------
# LIMIT injection
# ---------------------------------------------------------------------------

_LIMIT_RE = re.compile(r"\bLIMIT\s+(\d+)", re.IGNORECASE)


def inject_limit(sparql: str, limit: int) -> str:
    """Inject or tighten a LIMIT clause in a SPARQL query.

    If the query already has a LIMIT that is smaller or equal, it is kept.
    If the query has a larger LIMIT, it is replaced.  If there is no LIMIT,
    one is appended.
    """
    match = _LIMIT_RE.search(sparql)
    if match:
        existing = int(match.group(1))
        if existing <= limit:
            return sparql
        return sparql[:match.start()] + f"LIMIT {limit}" + sparql[match.end():]
    return sparql.rstrip() + f"\nLIMIT {limit}\n"


# ---------------------------------------------------------------------------
# Single-query analysis
# ---------------------------------------------------------------------------

def analyze_query(
    name: str,
    sparql: str,
    description: str,
    qlever_url: str,
    timeout: int,
    *,
    send: int = 0,
) -> QueryAnalysis:
    """Run a single query and return a ``QueryAnalysis``."""
    try:
        data = run_analysis(sparql, qlever_url, timeout, send=send)
    except Exception as exc:
        return QueryAnalysis(
            name=name,
            sparql=sparql,
            description=description,
            total_time="",
            compute_time="",
            planning_time_ms=None,
            index_scans_planning_ms=None,
            result_size=0,
            columns=[],
            tree=None,
            error=str(exc),
        )

    time_info = data.get("time", {})
    rt = data.get("runtimeInformation", {})
    meta = rt.get("meta", {})
    tree_data = rt.get("query_execution_tree")

    tree = parse_tree(tree_data) if tree_data else None

    warnings: list[str] = []
    if tree:
        for idx, (depth, op) in enumerate(flatten_tree(tree), 1):
            if op.result_rows > 0 and op.estimated_size > 0:
                ratio = op.estimated_size / op.result_rows
                if ratio > 10 or ratio < 0.1:
                    warnings.append(
                        f"Operation #{idx} \"{op.description}\": "
                        f"estimated {op.estimated_size} rows, "
                        f"got {op.result_rows} ({ratio:.1f}x off)"
                    )

    return QueryAnalysis(
        name=name,
        sparql=sparql,
        description=description,
        total_time=str(time_info.get("total", "")),
        compute_time=str(time_info.get("computeResult", "")),
        planning_time_ms=meta.get("time_query_planning"),
        index_scans_planning_ms=meta.get("time_index_scans_query_planning"),
        result_size=int(data.get("resultsize", 0)),
        columns=data.get("selected", []),
        tree=tree,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Multi-query orchestrator
# ---------------------------------------------------------------------------

def analyze_all(
    queries: dict[str, str],
    qlever_url: str,
    timeout: int,
    *,
    send: int = 0,
    limit: int = 1000,
    describe_fn=None,
) -> list[QueryAnalysis]:
    """Analyze multiple queries sequentially, returning a list of results.

    Each query gets a LIMIT injected (via *limit*) to keep test runs fast.
    *describe_fn* should be a callable ``(name) -> str`` for descriptions.
    """
    results: list[QueryAnalysis] = []
    columns = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
    ]

    with Progress(*columns, console=display.console) as progress:
        task = progress.add_task("Analyzing queries…", total=len(queries))
        for name, sparql in queries.items():
            progress.update(task, description=f"Analyzing {name}…")
            limited = inject_limit(sparql, limit)
            desc = describe_fn(name) if describe_fn else ""
            result = analyze_query(
                name, limited, desc, qlever_url, timeout, send=send,
            )
            results.append(result)
            progress.advance(task)

    return results


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def _fmt_ratio(estimated: int, actual: int) -> str:
    """Format the estimated/actual ratio with a warning flag if off."""
    if actual == 0 or estimated == 0:
        return "—"
    ratio = estimated / actual
    flag = " ⚠" if ratio > 10 or ratio < 0.1 else ""
    if ratio >= 100:
        return f"{ratio:.0f}×{flag}"
    return f"{ratio:.1f}×{flag}"


def render_markdown(
    analyses: list[QueryAnalysis],
    qlever_url: str,
    limit: int,
) -> str:
    """Render a full Markdown performance report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines: list[str] = [
        "# QLever Query Performance Analysis",
        "",
        f"Generated: {now} | Server: {qlever_url} | Test LIMIT: {limit}",
        "",
    ]

    for qa in analyses:
        lines.append("---")
        lines.append("")
        lines.append(f"## {qa.name}")
        if qa.description:
            lines.append(f"> {qa.description}")
        lines.append("")

        if qa.error:
            lines.append(f"**Error:** {qa.error}")
            lines.append("")
            lines.append("### SPARQL")
            lines.append("```sparql")
            lines.append(qa.sparql)
            lines.append("```")
            lines.append("")
            continue

        # Timing table
        lines.append("### Timing")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total | {qa.total_time} |")
        lines.append(f"| Compute | {qa.compute_time} |")
        planning = f"{qa.planning_time_ms:.0f} ms" if qa.planning_time_ms is not None else "N/A"
        lines.append(f"| Query planning | {planning} |")
        idx_planning = (
            f"{qa.index_scans_planning_ms:.0f} ms"
            if qa.index_scans_planning_ms is not None
            else "N/A"
        )
        lines.append(f"| Index scans (planning) | {idx_planning} |")
        cols = len(qa.columns)
        lines.append(f"| Result size | {qa.result_size:,} rows × {cols} cols |")
        lines.append("")

        # Execution tree table
        if qa.tree:
            flat = flatten_tree(qa.tree)
            lines.append("### Execution Tree")
            lines.append("")
            lines.append(
                "| # | Dp | Operation | Time (ms) | Rows | Estimated | Ratio | Cache | Status |"
            )
            lines.append(
                "|---:|---:|-----------|----------:|-----:|----------:|------:|-------|--------|"
            )
            for idx, (depth, op) in enumerate(flat, 1):
                indent = "\u00a0\u00a0" * depth  # non-breaking spaces for depth
                ratio = _fmt_ratio(op.estimated_size, op.result_rows)
                lines.append(
                    f"| {idx} | {depth} | {indent}{op.description} "
                    f"| {op.time_ms:.0f} | {op.result_rows:,} "
                    f"| {op.estimated_size:,} | {ratio} "
                    f"| {op.cache_status} | {op.status} |"
                )
            lines.append("")

            # Top 5 slowest
            sorted_ops = sorted(flat, key=lambda x: x[1].time_ms, reverse=True)
            total_ms = qa.tree.time_ms or 1
            lines.append("### Top 5 Slowest Operations")
            for rank, (depth, op) in enumerate(sorted_ops[:5], 1):
                pct = op.time_ms / total_ms * 100
                lines.append(
                    f"{rank}. **{op.description}** — "
                    f"{op.time_ms:.0f} ms ({pct:.0f}% of root)"
                )
            lines.append("")

        # Warnings
        if qa.warnings:
            lines.append("### Warnings")
            for w in qa.warnings:
                lines.append(f"- ⚠ {w}")
            lines.append("")

        # SPARQL
        lines.append("### SPARQL")
        lines.append("```sparql")
        lines.append(qa.sparql)
        lines.append("```")
        lines.append("")

    return "\n".join(lines)
