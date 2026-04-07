"""GRASP benchmark — run test questions and analyze responses.

Sends natural-language questions to the GRASP NL-to-SPARQL server
over WebSocket, displays per-step agent traces live as they stream in,
and saves results to a JSONL file.

Questions are loaded from grasp/benchmark.yml.

Usage:
    uv run python grasp/benchmark.py
    uv run python grasp/benchmark.py --timeout 120
    uv run python grasp/benchmark.py --question 5
    uv run python grasp/benchmark.py --overwrite
    uv run python grasp/benchmark.py --retry-failed
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx
import websockets
import yaml
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

GRASP_WS_URL = "ws://localhost:6789/live"
BENCHMARK_PATH = Path(__file__).parent / "benchmark.yml"
REPORT_PATH = Path(__file__).parent / "benchmark-results.jsonl"
CONFIG_PATH = Path(__file__).parent / "benchmark-config.json"

console = Console()


def load_questions() -> list[str]:
    """Load questions from benchmark.yml."""
    data = yaml.safe_load(BENCHMARK_PATH.read_text())
    return data["questions"]


def load_existing_results() -> dict[int, dict]:
    """Load existing results keyed by question number (1-indexed)."""
    results: dict[int, dict] = {}
    if REPORT_PATH.exists():
        for line in REPORT_PATH.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                results[r["number"]] = r
            except (json.JSONDecodeError, KeyError):
                continue
    return results


def save_server_config() -> dict:
    """Fetch and save the GRASP server config for reproducibility."""
    http_base = GRASP_WS_URL.replace("ws://", "http://").replace("/live", "")
    resp = httpx.get(f"{http_base}/config", timeout=5)
    config = resp.json()
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    return config


# ---------------------------------------------------------------------------
# Server error detection (adopted from GRASP's is_server_error)
# ---------------------------------------------------------------------------

_SERVER_ERROR_PHRASES = [
    "503 server error",
    "502 server error",
    "(read timeout=",
    "(connect timeout=",
    "403 client error",
]


def is_server_error(message: str | None) -> bool:
    if message is None:
        return False
    lower = message.lower()
    return any(phrase in lower for phrase in _SERVER_ERROR_PHRASES)


def is_retriable(result: dict) -> bool:
    grade = result.get("grade", "")
    if grade == "TIMEOUT":
        return True
    if grade in ("ERROR", "SERVER_ERROR"):
        error = result.get("error")
        if isinstance(error, str) and is_server_error(error):
            return True
        if isinstance(error, dict) and is_server_error(error.get("content")):
            return True
    for step in result.get("steps", []):
        tool_result = step.get("tool_result")
        if isinstance(tool_result, str) and is_server_error(tool_result):
            return True
    return False


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Step:
    type: str
    timestamp: float
    reasoning: str | None = None
    tool: str | None = None
    tool_args: dict | None = None
    tool_result: str | None = None
    completion_tokens: int = 0
    prompt_tokens: int = 0
    reasoning_tokens: int = 0
    cached_prompt_tokens: int = 0


@dataclass
class BenchmarkResult:
    number: int
    question: str
    grade: str
    elapsed: float
    answer: str | None = None
    sparql: str | None = None
    result: str | None = None
    error: str | None = None
    steps: list[Step] = field(default_factory=list)
    total_steps: int = 0
    execute_calls: int = 0
    search_calls: int = 0
    total_tokens: int = 0
    total_reasoning_tokens: int = 0


# ---------------------------------------------------------------------------
# Live step display — printed as each WebSocket message arrives
# ---------------------------------------------------------------------------

GRADE_STYLE = {
    "PASS": "bold green",
    "EMPTY": "bold yellow",
    "TIMEOUT": "bold red",
    "ERROR": "bold red",
    "SERVER_ERROR": "bold red",
    "SPARQL_ERROR": "bold red",
    "NO_ANSWER": "bold magenta",
}

TOOL_STYLE = {
    "search_entity": "cyan",
    "search_property": "cyan",
    "search_property_of_entity": "cyan",
    "search_object_of_property": "cyan",
    "list": "cyan",
    "execute": "yellow",
    "answer": "green",
    "cancel": "red",
}


def display_step(step: Step) -> None:
    """Print a single step to the terminal immediately."""
    ts = f"{step.timestamp:6.1f}s"

    if step.type == "model":
        tok_parts = [f"{step.completion_tokens} compl"]
        if step.reasoning_tokens:
            tok_parts.append(f"{step.reasoning_tokens} reasoning")
        if step.cached_prompt_tokens:
            tok_parts.append(f"{step.cached_prompt_tokens} cached")
        console.print(f"  [dim]{ts}[/]  [bold blue]model[/]  [dim]{', '.join(tok_parts)}[/]")
        if step.reasoning:
            console.print()
            for line in step.reasoning.split("\n"):
                console.print(f"          {line}")
            console.print()

    elif step.type == "tool":
        style = TOOL_STYLE.get(step.tool, "")
        label = step.tool or "?"
        console.print(f"  [dim]{ts}[/]  [{style}]{label}[/]")

        if step.tool == "execute" and step.tool_args:
            sparql = step.tool_args.get("sparql", "")
            if sparql:
                console.print()
                console.print(Syntax(sparql, "sparql", theme="monokai", padding=(0, 1, 0, 9)))
                console.print()

        if step.tool and "search" in step.tool and step.tool_args:
            parts = []
            for k in ("query", "entity", "property"):
                v = step.tool_args.get(k)
                if v:
                    parts.append(f"{k}: {v}")
            if parts:
                console.print(f"          {', '.join(parts)}")

        if step.tool == "list" and step.tool_args:
            parts = []
            for k in ("subject", "property", "object"):
                v = step.tool_args.get(k)
                if v:
                    parts.append(f"{k}: {v}")
            if parts:
                console.print(f"          {', '.join(parts)}")

        if step.tool_result:
            console.print()
            for line in step.tool_result.split("\n"):
                console.print(f"          {line}")
            console.print()

    elif step.type == "output":
        console.print(f"  [dim]{ts}[/]  [bold green]output[/]")

    elif step.type in ("input", "system"):
        console.print(f"  [dim]{ts}[/]  [dim]{step.type}[/]")


# ---------------------------------------------------------------------------
# GRASP interaction — streams steps live via display_step
# ---------------------------------------------------------------------------


def _parse_step(msg: dict, ts: float) -> Step:
    """Parse a single WebSocket message into a Step."""
    msg_type = msg.get("type", "unknown")

    if msg_type == "model":
        content = msg.get("content")
        reasoning = None
        comp_tok = prompt_tok = reason_tok = cached_tok = 0
        if isinstance(content, str):
            reasoning = content
        elif isinstance(content, dict):
            reasoning = content.get("message")
            usage = content.get("usage", {})
            comp_details = usage.get("completion_tokens_details", {})
            prompt_details = usage.get("prompt_tokens_details", {})
            comp_tok = usage.get("completion_tokens", 0)
            prompt_tok = usage.get("prompt_tokens", 0)
            reason_tok = comp_details.get("reasoning_tokens", 0)
            cached_tok = prompt_details.get("cached_tokens", 0)
        return Step(
            type="model", timestamp=round(ts, 2), reasoning=reasoning,
            completion_tokens=comp_tok, prompt_tokens=prompt_tok,
            reasoning_tokens=reason_tok, cached_prompt_tokens=cached_tok,
        )
    elif msg_type == "tool":
        return Step(
            type="tool", timestamp=round(ts, 2),
            tool=msg.get("name"), tool_args=msg.get("args"),
            tool_result=msg.get("result"),
        )
    elif msg_type == "output":
        return Step(type="output", timestamp=round(ts, 2))
    else:
        return Step(type=msg_type, timestamp=round(ts, 2))


async def run_question_ws(ws_url: str, question: str, timeout: float) -> tuple[dict, list[Step]]:
    """Send a question via WebSocket, displaying and collecting steps live."""
    payload = {
        "task": "sparql-qa",
        "input": question,
        "knowledge_graphs": ["europeana"],
    }
    steps: list[Step] = []
    t0 = time.time()
    deadline = t0 + timeout
    final_data: dict = {"error": "no output received", "output": None}

    try:
        async with websockets.connect(ws_url, close_timeout=5) as ws:
            await ws.send(json.dumps(payload))

            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise asyncio.TimeoutError()
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                ts = time.time() - t0
                msg = json.loads(raw)

                if "error" in msg and isinstance(msg["error"], str):
                    final_data = {"error": msg["error"], "output": None}
                    break

                step = _parse_step(msg, ts)
                steps.append(step)
                display_step(step)

                if msg.get("type") == "output":
                    final_data = msg
                    await ws.send(json.dumps({}))
                    break

                await ws.send(json.dumps({}))

    except asyncio.TimeoutError:
        final_data = {"error": "timeout", "output": None}
    except Exception as e:
        final_data = {"error": str(e), "output": None}

    return final_data, steps


def run_question(ws_url: str, question: str, timeout: float) -> tuple[dict, list[Step]]:
    """Sync wrapper around the async WebSocket call."""
    return asyncio.run(run_question_ws(ws_url, question, timeout))


def enrich_steps_with_tokens(steps: list[Step], data: dict) -> None:
    """Back-fill token usage from the final output's messages into model steps."""
    messages = data.get("messages", [])
    model_steps = [s for s in steps if s.type == "model"]
    usage_entries = []
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, dict) and "usage" in content:
            usage_entries.append(content["usage"])
    for step, usage in zip(model_steps, usage_entries):
        if step.completion_tokens == 0:
            step.completion_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)
            step.prompt_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
            out_details = usage.get("output_tokens_details", {}) or usage.get("completion_tokens_details", {})
            in_details = usage.get("input_tokens_details", {}) or usage.get("prompt_tokens_details", {})
            step.reasoning_tokens = out_details.get("reasoning_tokens", 0)
            step.cached_prompt_tokens = in_details.get("cached_tokens", 0)


def grade_response(data: dict) -> str:
    if "error" in data and data["error"]:
        err = str(data["error"])
        if "timeout" in err.lower() or "timed out" in err.lower():
            return "TIMEOUT"
        if is_server_error(err):
            return "SERVER_ERROR"
        return "ERROR"
    o = data.get("output") or {}
    if o.get("type") == "error":
        return "SPARQL_ERROR"
    if o.get("type") == "answer":
        result = o.get("result", "")
        if result.startswith("Got 0 rows"):
            return "EMPTY"
        if result:
            return "PASS"
    return "NO_ANSWER"


def build_result(idx: int, question: str, data: dict, steps: list[Step], elapsed: float) -> BenchmarkResult:
    g = grade_response(data)
    output = data.get("output") or {}
    enrich_steps_with_tokens(steps, data)

    return BenchmarkResult(
        number=idx + 1,
        question=question,
        grade=g,
        elapsed=round(elapsed, 1),
        answer=output.get("answer"),
        sparql=output.get("sparql"),
        result=output.get("result"),
        error=data.get("error"),
        steps=steps,
        total_steps=len(steps),
        execute_calls=sum(1 for s in steps if s.tool == "execute"),
        search_calls=sum(1 for s in steps if s.tool and "search" in s.tool),
        total_tokens=sum(s.completion_tokens + s.prompt_tokens for s in steps),
        total_reasoning_tokens=sum(s.reasoning_tokens for s in steps),
    )


# ---------------------------------------------------------------------------
# Post-question display — shown after WebSocket completes
# ---------------------------------------------------------------------------


def display_result_footer(r: BenchmarkResult) -> None:
    """Print grade, answer, final SPARQL, and result after steps are already shown."""
    grade_text = Text(r.grade, style=GRADE_STYLE.get(r.grade, ""))

    console.print(
        "  ", grade_text,
        f"  {r.elapsed:.1f}s  "
        f"{r.total_steps} steps  "
        f"{r.execute_calls} exec  "
        f"{r.search_calls} search  "
        f"{r.total_tokens:,} tok  "
        f"({r.total_reasoning_tokens:,} reasoning)",
        sep="",
    )

    if r.answer:
        console.print(f"\n[bold]Answer:[/]\n{r.answer}")

    if r.sparql:
        console.print(f"\n[bold]Final SPARQL:[/]")
        console.print(Syntax(r.sparql, "sparql", theme="monokai", padding=(0, 0)))

    if r.result:
        console.print(f"\n[bold]Result:[/]\n{r.result}")

    if r.error:
        err_str = r.error if isinstance(r.error, str) else json.dumps(r.error, indent=2)
        console.print(f"\n[bold red]Error:[/]\n{err_str}")

    console.print()


def display_summary(results: list[BenchmarkResult]) -> None:
    console.rule("[bold]Summary[/]")

    table = Table(show_header=True, header_style="bold", padding=(0, 1))
    table.add_column("#", justify="right", width=3)
    table.add_column("Question", no_wrap=False)
    table.add_column("Grade", justify="center", width=12)
    table.add_column("Time", justify="right", width=6)
    table.add_column("Steps", justify="right", width=5)
    table.add_column("Exec", justify="right", width=4)
    table.add_column("Search", justify="right", width=6)
    table.add_column("Tokens", justify="right", width=8)
    table.add_column("Reason", justify="right", width=7)

    for r in results:
        grade_text = Text(r.grade, style=GRADE_STYLE.get(r.grade, ""))
        table.add_row(
            str(r.number),
            r.question,
            grade_text,
            f"{r.elapsed:.1f}s",
            str(r.total_steps),
            str(r.execute_calls),
            str(r.search_calls),
            f"{r.total_tokens:,}",
            f"{r.total_reasoning_tokens:,}",
        )

    console.print(table)

    grades = [r.grade for r in results]
    n = len(results)
    passed = grades.count("PASS")
    total_time = sum(r.elapsed for r in results)
    total_tokens = sum(r.total_tokens for r in results)
    total_reasoning = sum(r.total_reasoning_tokens for r in results)
    total_exec = sum(r.execute_calls for r in results)
    total_steps = sum(r.total_steps for r in results)

    console.print()
    console.print(f"  Pass rate:      {passed}/{n} ({100 * passed / n:.0f}%)")
    for g in ["EMPTY", "TIMEOUT", "SERVER_ERROR", "ERROR", "SPARQL_ERROR", "NO_ANSWER"]:
        c = grades.count(g)
        if c:
            console.print(f"  {g}:{' ' * (14 - len(g))}{c}/{n}")
    console.print(f"  Total time:     {total_time:.0f}s (avg {total_time / n:.1f}s)")
    console.print(f"  Total tokens:   {total_tokens:,} ({total_reasoning:,} reasoning)")
    console.print(f"  Total steps:    {total_steps} (avg {total_steps / n:.1f})")
    console.print(f"  SPARQL execs:   {total_exec} (avg {total_exec / n:.1f})")

    times = sorted(r.elapsed for r in results)
    console.print(f"  Time p50/p90:   {times[len(times) // 2]:.1f}s / {times[int(len(times) * 0.9)]:.1f}s")
    console.print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="GRASP benchmark")
    parser.add_argument("--timeout", type=float, default=180.0,
                        help="Total timeout per question in seconds (default: 180)")
    parser.add_argument("--question", type=int, default=None,
                        help="Run only question N (1-indexed)")
    parser.add_argument("--url", default=GRASP_WS_URL,
                        help="GRASP WebSocket URL")
    parser.add_argument("--overwrite", action="store_true",
                        help="Overwrite results file instead of appending")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Re-run questions that previously failed (timeout, server error)")
    args = parser.parse_args()

    all_questions = load_questions()

    # Check server and save config
    try:
        config = save_server_config()
        model = config.get("model", "unknown")
    except Exception:
        console.print("[red]ERROR: GRASP server not reachable[/]")
        sys.exit(1)

    # Load existing results for skip/retry logic
    existing: dict[int, dict] = {}
    if not args.overwrite and not args.question:
        existing = load_existing_results()

    # Select questions
    if args.question is not None:
        idx = args.question - 1
        if idx < 0 or idx >= len(all_questions):
            console.print(f"[red]Question number must be 1-{len(all_questions)}[/]")
            sys.exit(1)
        questions = [(idx, all_questions[idx])]
    else:
        questions = list(enumerate(all_questions))

    # Filter based on existing results
    skip_count = 0
    retry_count = 0
    if existing and not args.question:
        filtered = []
        for idx, q in questions:
            num = idx + 1
            prev = existing.get(num)
            if prev is None:
                filtered.append((idx, q))
            elif args.retry_failed and is_retriable(prev):
                filtered.append((idx, q))
                retry_count += 1
            else:
                skip_count += 1
        questions = filtered

    # Open results file
    results_file = open(REPORT_PATH, "w" if args.overwrite else "a")

    console.print(f"\n[bold blue]GRASP Benchmark[/]")
    console.print(f"  Model: {model}")
    console.print(f"  Running {len(questions)} question(s) against {args.url}")
    console.print(f"  Timeout: {args.timeout}s per question")
    console.print(f"  Results: {REPORT_PATH} ({'overwrite' if args.overwrite else 'append'})")
    if skip_count:
        console.print(f"  Skipping {skip_count} already-completed question(s)")
    if retry_count:
        console.print(f"  Retrying {retry_count} previously-failed question(s)")
    console.print()

    results: list[BenchmarkResult] = []

    for idx, q in questions:
        # Print header before the question starts — steps stream below it
        console.rule(f"[bold]\\[{idx + 1}/{len(all_questions)}] {q}[/]")

        t0 = time.time()
        data, steps = run_question(args.url, q, timeout=args.timeout)
        elapsed = time.time() - t0

        r = build_result(idx, q, data, steps, elapsed)
        results.append(r)

        # Print footer (grade, answer, final SPARQL) after steps are done
        display_result_footer(r)

        # Stream to JSONL
        results_file.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
        results_file.flush()

    results_file.close()

    if len(results) > 1:
        display_summary(results)

    console.print(f"  Results saved to {REPORT_PATH}")
    console.print(f"  Config saved to {CONFIG_PATH}")


if __name__ == "__main__":
    main()
