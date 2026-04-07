"""AskParquet — NL→DuckDB agent over Parquet exports.

Uses OpenAI-compatible function calling (nemotron-3-nano via local VLLM) with a multi-step agent loop.
The LLM can list tables, inspect schemas, run SQL, and self-correct on
errors until it produces an answer.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx

from ..constants import (
    ASK_MAX_RESULT_ROWS,
    ASK_MAX_STEPS,
    ASK_MODEL,
    ASK_TEMPERATURE,
)
from ..schema_loader import parquet_schema_description
from . import AskBackend, AskResult, AskStep, display_step
from .notes import render_duckdb_notes
from .store import ParquetStore


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


def _build_system_prompt(store: ParquetStore) -> str:
    """Assemble the system prompt with schema and domain notes."""
    schema = parquet_schema_description()
    notes = render_duckdb_notes()
    filter_note = ""
    if store.filters and not store.filters.is_empty():
        filter_note = (
            f"\nNOTE: The items_resolved table has been pre-filtered to: "
            f"{store.filters.description()}. All queries on items_resolved "
            f"already have this filter applied."
        )
    return _SYSTEM_PROMPT_TEMPLATE.format(
        schema=schema,
        notes=notes,
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
            "parameters": {"type": "object", "properties": {}, "required": []},
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
                        "description": "Name of the table to describe",
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
                    "sql": {"type": "string", "description": "DuckDB SQL query"},
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
                        "description": "The final SQL query that produced the answer",
                    },
                    "answer_text": {
                        "type": "string",
                        "description": "Natural language answer with key numbers and findings",
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


def _tool_list_tables(store: ParquetStore) -> str:
    lines: list[str] = []
    for name, path in sorted(store.tables.items()):
        try:
            count = store.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            cols = store.execute(f"SELECT * FROM {name} LIMIT 0").description
            col_names = [c[0] for c in cols]
            lines.append(f"  {name}: {count:,} rows, columns: {', '.join(col_names)}")
        except Exception as e:
            lines.append(f"  {name}: error — {e}")
    return "Available tables:\n" + "\n".join(lines)


def _tool_describe_table(store: ParquetStore, table_name: str) -> str:
    if table_name not in store.tables:
        return f"Unknown table '{table_name}'. Available: {', '.join(sorted(store.tables))}"
    try:
        cols = store.execute(f"DESCRIBE {table_name}").fetchall()
        lines = [f"Schema for {table_name}:"]
        for col_name, col_type, *_ in cols:
            lines.append(f"  {col_name}: {col_type}")
        sample = store.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchdf()
        lines.append(f"\nSample rows (5):\n{sample.to_string()}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error describing {table_name}: {e}"


def _tool_execute_sql(store: ParquetStore, sql: str) -> str:
    try:
        result = store.execute(sql)
        rows = result.fetchmany(ASK_MAX_RESULT_ROWS)
        col_names = [desc[0] for desc in result.description]
        if not rows:
            return f"Query returned 0 rows.\nColumns: {', '.join(col_names)}"
        lines = [" | ".join(col_names)]
        lines.append(" | ".join("---" for _ in col_names))
        for row in rows:
            lines.append(" | ".join(_format_cell(v) for v in row))
        footer = f"\n({len(rows)} rows shown"
        if len(rows) == ASK_MAX_RESULT_ROWS:
            footer += f", may be truncated at {ASK_MAX_RESULT_ROWS}"
        footer += ")"
        return "\n".join(lines) + footer
    except Exception as e:
        return f"SQL error: {e}"


def _format_cell(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, float):
        return str(int(value)) if value == int(value) else f"{value:.4f}"
    if isinstance(value, list):
        return f"[{len(value)} items]" if len(value) > 3 else str(value)
    return str(value)


# ---------------------------------------------------------------------------
# OpenAI API
# ---------------------------------------------------------------------------


def _get_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    # Fallback: check grasp/.env (legacy location)
    for candidate in (
        Path(__file__).parent.parent.parent.parent / "grasp" / ".env",
        Path.home() / ".env",
    ):
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip("'\"")
                    if key:
                        return key
    raise RuntimeError(
        "OPENAI_API_KEY not found. Set it as an environment variable."
    )


def _call_openai(
    messages: list[dict],
    *,
    model: str = ASK_MODEL,
    temperature: float = ASK_TEMPERATURE,
) -> dict:
    api_key = _get_api_key()
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
        resp = client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "tools": _TOOL_DEFINITIONS,
                "temperature": temperature,
            },
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# AskParquet backend
# ---------------------------------------------------------------------------


class AskParquet(AskBackend):
    """NL→DuckDB agent over Parquet exports using OpenAI function calling."""

    name = "parquet"

    def __init__(
        self,
        store: ParquetStore,
        *,
        model: str = ASK_MODEL,
        max_steps: int = ASK_MAX_STEPS,
    ) -> None:
        self._store = store
        self._model = model
        self._max_steps = max_steps

    async def ask(
        self,
        question: str,
        *,
        timeout: float = 180.0,
        verbose: bool = False,
    ) -> AskResult:
        """Run the agent loop for a question."""
        from .. import display
        from rich.live import Live
        from rich.spinner import Spinner
        from rich.text import Text

        t0 = time.perf_counter()
        console = display.console

        if not self._store.tables:
            return AskResult(
                question=question,
                backend=self.name,
                error="No Parquet files found in exports directory.",
            )

        system_prompt = _build_system_prompt(self._store)
        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        result = AskResult(question=question, backend=self.name)
        all_steps: list[AskStep] = []

        try:
            with Live(console=console, refresh_per_second=4) as live:
                step = 0
                while step < self._max_steps:
                    step += 1
                    live.update(Spinner("dots", text=f"Step {step}: thinking…"))

                    response = _call_openai(messages, model=self._model)
                    choice = response["choices"][0]
                    message = choice["message"]
                    messages.append(message)

                    tool_calls = message.get("tool_calls")
                    if not tool_calls:
                        content = message.get("content", "")
                        if content:
                            result.answer = content
                        all_steps.append(AskStep(
                            type="model",
                            timestamp=time.perf_counter() - t0,
                        ))
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

                        if fn_name == "answer":
                            result.query = fn_args.get("sql", "")
                            result.answer = fn_args.get("answer_text", "")
                            all_steps.append(AskStep(
                                type="tool",
                                timestamp=time.perf_counter() - t0,
                                tool="answer",
                                tool_args=fn_args,
                            ))
                            live.update(Text(""))
                            result.steps = all_steps
                            result.elapsed = time.perf_counter() - t0
                            return result

                        live.update(Spinner("dots", text=f"Step {step}: {fn_name}()"))
                        tool_result = self._execute_tool(fn_name, fn_args)

                        ask_step = AskStep(
                            type="tool",
                            timestamp=time.perf_counter() - t0,
                            tool=fn_name,
                            tool_args=fn_args,
                            tool_result=tool_result,
                        )
                        all_steps.append(ask_step)

                        if verbose:
                            live.update(Text(""))
                            display_step(ask_step)

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": tool_result,
                        })

                if result.answer is None:
                    result.error = f"Reached maximum of {self._max_steps} steps without an answer."

        except Exception as e:
            result.error = str(e)

        result.steps = all_steps
        result.elapsed = time.perf_counter() - t0
        return result

    def _execute_tool(self, name: str, args: dict) -> str:
        if name == "list_tables":
            return _tool_list_tables(self._store)
        elif name == "describe_table":
            return _tool_describe_table(self._store, args.get("table_name", ""))
        elif name == "execute_sql":
            return _tool_execute_sql(self._store, args.get("sql", ""))
        return f"Unknown tool: {name}"
