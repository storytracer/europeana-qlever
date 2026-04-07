"""Unified natural-language querying over Europeana data.

Provides a common interface (:class:`AskBackend`) with pluggable backends:

- :class:`~europeana_qlever.ask.parquet.AskParquet` — NL→DuckDB over Parquet
  exports using OpenAI function calling (offline, no servers needed).
- :class:`~europeana_qlever.ask.sparql.AskSPARQL` — NL→SPARQL over QLever
  via the GRASP WebSocket agent (requires running QLever + GRASP servers).

Both return :class:`AskResult` with the same fields, enabling unified
benchmarking and display.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .. import display


# ---------------------------------------------------------------------------
# Step and result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AskStep:
    """A single agent step (model reasoning or tool call)."""

    type: str  # "model", "tool", "input", "system", "output"
    timestamp: float = 0.0
    reasoning: str | None = None
    tool: str | None = None
    tool_args: dict | None = None
    tool_result: str | None = None
    # Token tracking
    completion_tokens: int = 0
    prompt_tokens: int = 0
    reasoning_tokens: int = 0
    cached_prompt_tokens: int = 0


@dataclass
class AskResult:
    """Result of running a single question through any backend."""

    question: str
    backend: str  # "parquet" or "sparql"
    answer: str | None = None
    query: str | None = None  # SQL (parquet) or SPARQL (sparql)
    result_text: str | None = None
    steps: list[AskStep] = field(default_factory=list)
    elapsed: float = 0.0
    error: str | None = None


# ---------------------------------------------------------------------------
# Abstract backend
# ---------------------------------------------------------------------------


class AskBackend(ABC):
    """Abstract base for NL query backends."""

    name: str

    @abstractmethod
    async def ask(
        self,
        question: str,
        *,
        timeout: float = 180.0,
        verbose: bool = False,
    ) -> AskResult:
        """Translate a natural language question and return the result."""
        ...


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

# Tool name → Rich style mapping (used by both backends)
TOOL_STYLE = {
    # Parquet tools
    "list_tables": "cyan",
    "describe_table": "cyan",
    "execute_sql": "yellow",
    "answer": "green",
    # SPARQL/GRASP tools
    "search_entity": "cyan",
    "search_property": "cyan",
    "search_property_of_entity": "cyan",
    "search_object_of_property": "cyan",
    "list": "cyan",
    "execute": "yellow",
    "cancel": "red",
}

GRADE_STYLE = {
    "PASS": "bold green",
    "EMPTY": "bold yellow",
    "TIMEOUT": "bold red",
    "ERROR": "bold red",
    "SERVER_ERROR": "bold red",
    "SPARQL_ERROR": "bold red",
    "SQL_ERROR": "bold red",
    "NO_ANSWER": "bold magenta",
}


def display_step(step: AskStep) -> None:
    """Print a single agent step to the console."""
    console = display.console
    ts = f"{step.timestamp:6.1f}s"

    if step.type == "model":
        tok_parts = []
        if step.completion_tokens:
            tok_parts.append(f"{step.completion_tokens} compl")
        if step.reasoning_tokens:
            tok_parts.append(f"{step.reasoning_tokens} reasoning")
        if step.cached_prompt_tokens:
            tok_parts.append(f"{step.cached_prompt_tokens} cached")
        tok_str = f"  [dim]{', '.join(tok_parts)}[/]" if tok_parts else ""
        console.print(f"  [dim]{ts}[/]  [bold blue]model[/]{tok_str}")
        if step.reasoning:
            console.print()
            for line in step.reasoning.split("\n"):
                console.print(f"          {line}")
            console.print()

    elif step.type == "tool":
        style = TOOL_STYLE.get(step.tool or "", "")
        console.print(f"  [dim]{ts}[/]  [{style}]{step.tool or '?'}[/]")

        # Show SQL/SPARQL for execute tools
        if step.tool in ("execute_sql", "execute") and step.tool_args:
            query = step.tool_args.get("sql") or step.tool_args.get("sparql")
            if query:
                console.print(f"\n[cyan]{query}[/cyan]\n")

        # Show search tool summaries
        if step.tool and "search" in step.tool and step.tool_args:
            parts = [
                f"{k}: {v}"
                for k in ("query", "entity", "property")
                if (v := step.tool_args.get(k))
            ]
            if parts:
                console.print(f"          {', '.join(parts)}")

        # Show truncated result
        if step.tool_result:
            text = step.tool_result
            if len(text) > 500:
                text = text[:500] + "…"
            console.print()
            for line in text.split("\n"):
                console.print(f"          {line}")
            console.print()

    elif step.type in ("input", "system"):
        console.print(f"  [dim]{ts}[/]  [dim]{step.type}[/]")

    elif step.type == "output":
        console.print(f"  [dim]{ts}[/]  [bold green]output[/]")


def display_result(result: AskResult) -> None:
    """Pretty-print an AskResult to the console."""
    console = display.console

    if result.error:
        console.print(f"\n[red]Error: {result.error}[/red]")
        if not result.answer:
            return

    console.print()
    if result.answer:
        console.print(f"[bold green]Answer:[/bold green] {result.answer}")

    if result.query:
        label = "SQL" if result.backend == "parquet" else "SPARQL"
        console.print(f"\n[dim]{label}:[/dim]")
        console.print(f"[cyan]{result.query}[/cyan]")

    if result.result_text:
        console.print(f"\n[dim]Result:[/dim]\n{result.result_text}")

    console.print(
        f"\n[dim]({len(result.steps)} steps, {result.elapsed:.1f}s, {result.backend})[/dim]"
    )
