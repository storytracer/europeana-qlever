"""NL→DuckDB agent for querying exported Parquet files.

Multi-step agent loop using OpenAI function calling (gpt-4.1-mini).
The LLM can list tables, inspect schemas, run SQL, and self-correct
on errors — analogous to GRASP's NL→SPARQL agent but targeting DuckDB
over Parquet exports.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import httpx

from . import display
from .constants import (
    ASK_MAX_RESULT_ROWS,
    ASK_MAX_STEPS,
    ASK_MODEL,
    ASK_TEMPERATURE,
)
from .report import ReportFilters
from .schema_loader import parquet_schema_description


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class AskResult:
    """Result of an ``ask`` session."""

    question: str
    answer: str | None = None
    sql: str | None = None
    result_text: str | None = None
    steps: int = 0
    elapsed: float = 0.0
    error: str | None = None
    messages: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Domain notes — DuckDB patterns for EDM Parquet data
# ---------------------------------------------------------------------------

_DOMAIN_NOTES = """\
## Domain knowledge for querying Europeana Parquet exports

1. STRUCT LIST ACCESS PATTERNS:
   - Unnest struct lists: SELECT t.value, t.lang FROM items_resolved, UNNEST(titles) AS t(value, lang)
   - Filter within a list: list_filter(titles, x -> x.lang = 'en')
   - Check list containment: list_has_any(list_transform(dc_types, x -> LOWER(x.label)), ['preserved specimen'])
   - Count list elements: LEN(subjects)
   - Check if list is non-empty: LEN(titles) > 0  (NOT: titles IS NOT NULL, which only checks for NULL not empty)
   - To count distinct items after unnesting: SELECT COUNT(DISTINCT item) FROM items_resolved, UNNEST(...)

2. REUSE LEVELS:
   - reuse_level column = 'open' / 'restricted' / 'closed' / 'unknown'
   - "Openly-reusable" means reuse_level = 'open'
   - Specific rights URIs are in the rights column:
     - Public Domain Mark: http://creativecommons.org/publicdomain/mark/1.0/
     - CC0: http://creativecommons.org/publicdomain/zero/1.0/
     - CC-BY: starts with http://creativecommons.org/licenses/by/
     - All public domain: rights LIKE 'http://creativecommons.org/publicdomain/%'

3. MULTI-VALUED COLUMN TYPES:
   - LIST<STRUCT<value, lang>>: titles, descriptions (text with language tags)
   - LIST<STRUCT<label, uri>>: subjects, dc_types, formats (entity labels with URIs)
   - LIST<STRUCT<name, uri>>: creators, contributors, publishers (agent names with URIs)
   - LIST<VARCHAR>: dates, languages, identifiers, dc_rights
   - LIST<VARCHAR>: years (stored as strings representing integer years)

4. EDM TYPE vs DC:TYPE:
   - type column = edm:type enum with exactly 5 values: IMAGE, TEXT, SOUND, VIDEO, 3D
   - dc_types = LIST of free-text type labels from providers (e.g. 'Photograph', 'Preserved Specimen')
   - Always use type column for high-level media type filtering

5. CONTENT AVAILABILITY:
   - is_shown_by = direct content URL (image/video/audio file)
   - is_shown_at = landing page at provider website
   - has_iiif = true if any web resource has a IIIF image service
   - width, height = pixel dimensions (NULL if not reported by provider)
   - An item "has content" if is_shown_by IS NOT NULL

6. COUNTRY AND INSTITUTION:
   - country = providing country (string like 'Netherlands', 'France')
   - institution = data provider organisation URI
   - aggregator = aggregator organisation URI
   - Join with institutions table for human-readable names:
     SELECT COALESCE(n.name, i.institution) AS provider, COUNT(*) AS cnt
     FROM items_resolved i LEFT JOIN institutions n ON i.institution = n.org
     GROUP BY 1 ORDER BY cnt DESC

7. SPECIMEN EXCLUSION:
   - Natural history specimens dominate open images (~10.8M items)
   - To exclude: NOT list_has_any(list_transform(dc_types, x -> LOWER(x.label)), ['preserved specimen', 'biological specimen', 'herbarium'])

8. PERFORMANCE TIPS:
   - DuckDB handles 66M rows efficiently in columnar mode
   - Avoid SELECT * — always specify columns
   - Use LIMIT during exploration
   - UNNEST on large lists can produce billions of rows — add WHERE clauses early
   - For counting items with a property, prefer LEN(column) > 0 over UNNEST + COUNT(DISTINCT)

9. LANGUAGE TAGS:
   - titles and descriptions have a lang field (e.g. 'en', 'de', 'fr', '' for untagged)
   - Empty string '' means no language tag was provided
   - languages column is a LIST<VARCHAR> of dc:language codes (different from title/description language tags)

10. CENTURY BUCKETING:
    - years contains string values representing years (e.g. '1850', '2001')
    - Cast to integer for arithmetic: CAST(y AS INTEGER)
    - Bucket with CASE: CASE WHEN CAST(y AS INTEGER) < 1500 THEN 'before 1500' WHEN ... END
"""


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_TEMPLATE = """\
You are a data analyst querying Europeana cultural heritage metadata.
The data is exported as Parquet files queryable via DuckDB SQL.

{schema}

{notes}

## Instructions
- Use the tools to explore the data and answer the user's question.
- Write DuckDB SQL to query the data. DuckDB syntax, not PostgreSQL or MySQL.
- If a query fails, read the error message and fix the SQL.
- When you have the answer, call the answer tool with the final SQL and a natural language summary.
- Be precise with numbers. Report exact counts, not approximations.
- For distributions, use clear range labels and order results logically.
{filter_note}"""


def _build_system_prompt(filters: ReportFilters | None) -> str:
    """Assemble the system prompt with schema and domain notes."""
    schema = parquet_schema_description()
    filter_note = ""
    if filters and not filters.is_empty():
        filter_note = (
            f"\nNOTE: The items_resolved table has been pre-filtered to: "
            f"{filters.description()}. All queries on items_resolved "
            f"already have this filter applied."
        )
    return _SYSTEM_PROMPT_TEMPLATE.format(
        schema=schema,
        notes=_DOMAIN_NOTES,
        filter_note=filter_note,
    )


# ---------------------------------------------------------------------------
# OpenAI function calling tool definitions
# ---------------------------------------------------------------------------

_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": (
                "List all available Parquet tables with row counts and column summaries. "
                "Call this first to understand what data is available."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_table",
            "description": (
                "Show the full column schema and 5 sample rows for a table. "
                "Use this to understand column types and data patterns before writing SQL."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to describe (e.g. 'items_resolved', 'concepts_core')",
                    },
                },
                "required": ["table_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "description": (
                "Execute a DuckDB SQL query over the Parquet data. "
                "Returns up to 50 rows. Reports errors verbatim for self-correction."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "DuckDB SQL query to execute",
                    },
                },
                "required": ["sql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "answer",
            "description": (
                "Submit the final answer. Call this when you have enough information "
                "to answer the user's question."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "The final SQL query that produced the answer (may be empty if no SQL was needed)",
                    },
                    "answer_text": {
                        "type": "string",
                        "description": "Natural language answer to the user's question, including key numbers and findings",
                    },
                },
                "required": ["sql", "answer_text"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _tool_list_tables(con: duckdb.DuckDBPyConnection, tables: dict[str, str]) -> str:
    """List available tables with row counts."""
    lines: list[str] = []
    for name, path in sorted(tables.items()):
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            cols = con.execute(f"SELECT * FROM {name} LIMIT 0").description
            col_names = [c[0] for c in cols]
            lines.append(f"  {name}: {count:,} rows, columns: {', '.join(col_names)}")
        except Exception as e:
            lines.append(f"  {name}: error reading — {e}")
    return "Available tables:\n" + "\n".join(lines)


def _tool_describe_table(
    con: duckdb.DuckDBPyConnection, table_name: str, tables: dict[str, str]
) -> str:
    """Describe a table's schema and show sample rows."""
    if table_name not in tables:
        return f"Unknown table '{table_name}'. Available: {', '.join(sorted(tables))}"

    try:
        # Column types
        cols = con.execute(f"DESCRIBE {table_name}").fetchall()
        lines = [f"Schema for {table_name}:"]
        for col_name, col_type, *_ in cols:
            lines.append(f"  {col_name}: {col_type}")

        # Sample rows
        sample = con.execute(
            f"SELECT * FROM {table_name} LIMIT 5"
        ).fetchdf()
        lines.append(f"\nSample rows (5):\n{sample.to_string()}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error describing {table_name}: {e}"


def _tool_execute_sql(con: duckdb.DuckDBPyConnection, sql: str) -> str:
    """Execute SQL and return formatted results."""
    try:
        result = con.execute(sql)
        rows = result.fetchmany(ASK_MAX_RESULT_ROWS)
        col_names = [desc[0] for desc in result.description]

        if not rows:
            return f"Query returned 0 rows.\nColumns: {', '.join(col_names)}"

        # Format as a markdown-ish table
        lines = [" | ".join(col_names)]
        lines.append(" | ".join("---" for _ in col_names))
        for row in rows:
            lines.append(" | ".join(_format_cell(v) for v in row))

        total_count = len(rows)
        footer = f"\n({total_count} rows shown"
        if total_count == ASK_MAX_RESULT_ROWS:
            footer += f", result may be truncated at {ASK_MAX_RESULT_ROWS}"
        footer += ")"
        return "\n".join(lines) + footer
    except Exception as e:
        return f"SQL error: {e}"


def _format_cell(value) -> str:
    """Format a single cell value for display."""
    if value is None:
        return "NULL"
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return f"{value:.4f}"
    if isinstance(value, list):
        if len(value) > 3:
            return f"[{len(value)} items]"
        return str(value)
    return str(value)


# ---------------------------------------------------------------------------
# OpenAI API calls via httpx
# ---------------------------------------------------------------------------


def _get_api_key() -> str:
    """Resolve OpenAI API key from environment or grasp/.env file."""
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key

    # Try grasp/.env as fallback
    env_path = Path(__file__).parent.parent.parent / "grasp" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("'\"")
                if key:
                    return key

    raise RuntimeError(
        "OPENAI_API_KEY not found. Set it as an environment variable "
        "or in grasp/.env"
    )


def _call_openai(
    messages: list[dict],
    *,
    model: str = ASK_MODEL,
    temperature: float = ASK_TEMPERATURE,
) -> dict:
    """Synchronous OpenAI chat completions call with function calling."""
    api_key = _get_api_key()

    payload = {
        "model": model,
        "messages": messages,
        "tools": _TOOL_DEFINITIONS,
        "temperature": temperature,
    }

    with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Agent engine
# ---------------------------------------------------------------------------


class AskEngine:
    """Multi-step NL→DuckDB agent.

    Creates a DuckDB connection with all available Parquet files registered
    as views, then runs an agent loop where the LLM can inspect schemas,
    execute SQL, and self-correct until it produces an answer.
    """

    def __init__(
        self,
        exports_dir: Path,
        *,
        filters: ReportFilters | None = None,
        model: str = ASK_MODEL,
        max_steps: int = ASK_MAX_STEPS,
        verbose: bool = False,
        memory_limit: str = "4GB",
    ) -> None:
        self._exports_dir = exports_dir
        self._filters = filters
        self._model = model
        self._max_steps = max_steps
        self._verbose = verbose
        self._memory_limit = memory_limit

    def ask(self, question: str) -> AskResult:
        """Run the agent loop for a question."""
        t0 = time.perf_counter()

        # Set up DuckDB with Parquet views
        con = duckdb.connect()
        con.execute(f"SET memory_limit = '{self._memory_limit}'")
        tables = self._register_tables(con)

        if not tables:
            return AskResult(
                question=question,
                error="No Parquet files found in exports directory.",
            )

        system_prompt = _build_system_prompt(self._filters)
        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        result = AskResult(question=question)

        try:
            self._run_loop(con, tables, messages, result)
        except Exception as e:
            result.error = str(e)
        finally:
            con.close()

        result.elapsed = time.perf_counter() - t0
        result.messages = messages
        return result

    def _register_tables(self, con: duckdb.DuckDBPyConnection) -> dict[str, str]:
        """Register all Parquet files as DuckDB views. Returns name→path mapping."""
        tables: dict[str, str] = {}

        for pq_file in sorted(self._exports_dir.glob("*.parquet")):
            name = pq_file.stem
            path_str = str(pq_file)

            # Apply filters only to items_resolved
            if name == "items_resolved" and self._filters and not self._filters.is_empty():
                where = self._filters.to_duckdb_where()
                con.execute(
                    f"CREATE VIEW {name} AS "
                    f"SELECT * FROM read_parquet('{path_str}') {where}"
                )
            else:
                con.execute(
                    f"CREATE VIEW {name} AS "
                    f"SELECT * FROM read_parquet('{path_str}')"
                )
            tables[name] = path_str

        return tables

    def _run_loop(
        self,
        con: duckdb.DuckDBPyConnection,
        tables: dict[str, str],
        messages: list[dict],
        result: AskResult,
    ) -> None:
        """Execute the agent loop until answer() is called or max steps reached."""
        from rich.live import Live
        from rich.spinner import Spinner
        from rich.text import Text

        console = display.console
        step = 0

        with Live(console=console, refresh_per_second=4) as live:
            while step < self._max_steps:
                step += 1
                result.steps = step

                live.update(Spinner("dots", text=f"Step {step}: thinking…"))

                response = _call_openai(messages, model=self._model)
                choice = response["choices"][0]
                message = choice["message"]

                # Append assistant message to conversation
                messages.append(message)

                # Check for tool calls
                tool_calls = message.get("tool_calls")
                if not tool_calls:
                    # No tool calls — LLM responded with text
                    content = message.get("content", "")
                    if content:
                        result.answer = content
                    live.update(Text(""))
                    break

                for tc in tool_calls:
                    fn_name = tc["function"]["name"]
                    fn_args_str = tc["function"]["arguments"]
                    tc_id = tc["id"]

                    try:
                        fn_args = json.loads(fn_args_str)
                    except json.JSONDecodeError:
                        fn_args = {}

                    # Handle answer tool — terminates the loop
                    if fn_name == "answer":
                        result.sql = fn_args.get("sql", "")
                        result.answer = fn_args.get("answer_text", "")
                        live.update(Text(""))
                        return

                    # Execute other tools
                    live.update(
                        Spinner("dots", text=f"Step {step}: {fn_name}()")
                    )
                    tool_result = self._execute_tool(
                        fn_name, fn_args, con, tables
                    )

                    if self._verbose:
                        self._print_step(step, fn_name, fn_args, tool_result)

                    # Append tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": tool_result,
                    })

            # Max steps reached without answer
            if result.answer is None:
                result.error = f"Reached maximum of {self._max_steps} steps without an answer."

    def _execute_tool(
        self,
        name: str,
        args: dict,
        con: duckdb.DuckDBPyConnection,
        tables: dict[str, str],
    ) -> str:
        """Dispatch a tool call and return the result string."""
        if name == "list_tables":
            return _tool_list_tables(con, tables)
        elif name == "describe_table":
            return _tool_describe_table(con, args.get("table_name", ""), tables)
        elif name == "execute_sql":
            return _tool_execute_sql(con, args.get("sql", ""))
        else:
            return f"Unknown tool: {name}"

    def _print_step(
        self,
        step: int,
        fn_name: str,
        fn_args: dict,
        tool_result: str,
    ) -> None:
        """Print verbose step information."""
        console = display.console
        console.print(f"\n[dim]─── Step {step}: {fn_name} ───[/dim]")
        if fn_name == "execute_sql":
            sql = fn_args.get("sql", "")
            console.print(f"[cyan]{sql}[/cyan]")
        elif fn_name == "describe_table":
            console.print(f"[cyan]describe_table({fn_args.get('table_name', '')})[/cyan]")
        # Show truncated result
        if len(tool_result) > 500:
            console.print(f"[dim]{tool_result[:500]}…[/dim]")
        else:
            console.print(f"[dim]{tool_result}[/dim]")


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def display_result(result: AskResult) -> None:
    """Pretty-print the agent result."""
    console = display.console

    if result.error:
        console.print(f"\n[red]Error: {result.error}[/red]")
        return

    console.print()
    if result.answer:
        console.print(f"[bold green]Answer:[/bold green] {result.answer}")

    if result.sql:
        console.print(f"\n[dim]SQL:[/dim]")
        console.print(f"[cyan]{result.sql}[/cyan]")

    console.print(
        f"\n[dim]({result.steps} steps, {result.elapsed:.1f}s)[/dim]"
    )


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------


def run_ask(
    *,
    exports_dir: Path,
    question: str,
    filters: ReportFilters | None = None,
    model: str = ASK_MODEL,
    max_steps: int = ASK_MAX_STEPS,
    verbose: bool = False,
    memory_limit: str = "4GB",
) -> AskResult:
    """Run the NL→DuckDB agent and display results."""
    engine = AskEngine(
        exports_dir,
        filters=filters,
        model=model,
        max_steps=max_steps,
        verbose=verbose,
        memory_limit=memory_limit,
    )
    result = engine.ask(question)
    display_result(result)
    return result
