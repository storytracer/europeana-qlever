"""GRASP benchmark — run test questions and analyze responses.

Sends natural-language questions to the GRASP NL-to-SPARQL server
over WebSocket, displays per-step agent traces live with spinners
and elapsed time, and streams results to a JSONL file.

Questions are loaded from grasp/benchmark.yml by default, or from a
positional argument.

Usage:
    uv run python grasp/benchmark.py
    uv run python grasp/benchmark.py questions.yml
    uv run python grasp/benchmark.py --timeout 120
    uv run python grasp/benchmark.py --question 5
    uv run python grasp/benchmark.py --overwrite
    uv run python grasp/benchmark.py --retry-failed
    uv run python grasp/benchmark.py --with-rationale
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
from rich.live import Live
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRASP_WS_URL = "ws://localhost:6789/live"
BENCHMARK_PATH = Path(__file__).parent / "benchmark.yml"

console = Console()

# ---------------------------------------------------------------------------
# Dataclasses
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
# Style maps
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

# ---------------------------------------------------------------------------
# Pure functions — loading, parsing, grading
# ---------------------------------------------------------------------------

_SERVER_ERROR_PHRASES = [
    "503 server error",
    "502 server error",
    "(read timeout=",
    "(connect timeout=",
    "403 client error",
]


def _derive_paths(questions_file: Path) -> tuple[Path, Path]:
    """Derive report and config paths from the questions file."""
    stem = questions_file.stem
    parent = questions_file.parent
    return (
        parent / f"{stem}-results.jsonl",
        parent / f"{stem}-config.json",
    )


def load_questions(path: Path, with_rationale: bool = False) -> list[str]:
    with open(path) as f:
        raw = yaml.safe_load(f)
    entries = raw["questions"] if isinstance(raw, dict) else raw
    out = []
    for q in entries:
        if isinstance(q, dict):
            text = q["question"]
            if with_rationale and q.get("rationale"):
                text += f"\n\nContext: {q['rationale']}"
            out.append(text)
        else:
            out.append(q)
    return out


def load_existing_results(report_path: Path) -> dict[int, dict]:
    results: dict[int, dict] = {}
    if report_path.exists():
        for line in report_path.read_text().splitlines():
            if not (line := line.strip()):
                continue
            try:
                r = json.loads(line)
                results[r["number"]] = r
            except (json.JSONDecodeError, KeyError):
                continue
    return results


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


def _parse_step(msg: dict, ts: float) -> Step:
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
            comp_tok = usage.get("completion_tokens", 0)
            prompt_tok = usage.get("prompt_tokens", 0)
            reason_tok = usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
            cached_tok = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
        return Step(
            type="model", timestamp=round(ts, 2), reasoning=reasoning,
            completion_tokens=comp_tok, prompt_tokens=prompt_tok,
            reasoning_tokens=reason_tok, cached_prompt_tokens=cached_tok,
        )
    if msg_type == "tool":
        return Step(
            type="tool", timestamp=round(ts, 2),
            tool=msg.get("name"), tool_args=msg.get("args"),
            tool_result=msg.get("result"),
        )
    return Step(type=msg_type, timestamp=round(ts, 2))


def enrich_steps_with_tokens(steps: list[Step], data: dict) -> None:
    messages = data.get("messages", [])
    model_steps = [s for s in steps if s.type == "model"]
    usage_entries = [
        msg["content"]["usage"]
        for msg in messages
        if isinstance(msg.get("content"), dict) and "usage" in msg["content"]
    ]
    for step, usage in zip(model_steps, usage_entries):
        if step.completion_tokens == 0:
            step.completion_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)
            step.prompt_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
            out_d = usage.get("output_tokens_details", {}) or usage.get("completion_tokens_details", {})
            in_d = usage.get("input_tokens_details", {}) or usage.get("prompt_tokens_details", {})
            step.reasoning_tokens = out_d.get("reasoning_tokens", 0)
            step.cached_prompt_tokens = in_d.get("cached_tokens", 0)


def grade_response(data: dict) -> str:
    if data.get("error"):
        err = str(data["error"])
        if "timeout" in err.lower() or "timed out" in err.lower():
            return "TIMEOUT"
        return "SERVER_ERROR" if is_server_error(err) else "ERROR"
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
    enrich_steps_with_tokens(steps, data)
    output = data.get("output") or {}
    return BenchmarkResult(
        number=idx + 1,
        question=question,
        grade=grade_response(data),
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
# Display helpers
# ---------------------------------------------------------------------------


def _format_tool_args(tool: str | None, args: dict | None) -> str | None:
    """Extract a one-line summary of tool arguments."""
    if not args:
        return None
    if tool and "search" in tool:
        keys = ("query", "entity", "property")
    elif tool == "list":
        keys = ("subject", "property", "object")
    else:
        return None
    parts = [f"{k}: {args[k]}" for k in keys if args.get(k)]
    return ", ".join(parts) if parts else None


def display_step(step: Step) -> None:
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
        console.print(f"  [dim]{ts}[/]  [{style}]{step.tool or '?'}[/]")

        if step.tool == "execute" and step.tool_args and step.tool_args.get("sparql"):
            console.print()
            console.print(Syntax(step.tool_args["sparql"], "sparql", theme="monokai", padding=(0, 1, 0, 9)))
            console.print()

        summary = _format_tool_args(step.tool, step.tool_args)
        if summary:
            console.print(f"          {summary}")

        if step.tool_result:
            console.print()
            for line in step.tool_result.split("\n"):
                console.print(f"          {line}")
            console.print()

    elif step.type in ("input", "system"):
        console.print(f"  [dim]{ts}[/]  [dim]{step.type}[/]")

    elif step.type == "output":
        console.print(f"  [dim]{ts}[/]  [bold green]output[/]")


def display_result_footer(r: BenchmarkResult) -> None:
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
        console.print("\n[bold]Final SPARQL:[/]")
        console.print(Syntax(r.sparql, "sparql", theme="monokai", padding=(0, 0)))
    if r.result:
        console.print(f"\n[bold]Result:[/]\n{r.result}")
    if r.error:
        err_str = r.error if isinstance(r.error, str) else json.dumps(r.error, indent=2)
        console.print(f"\n[bold red]Error:[/]\n{err_str}")
    console.print()


def display_summary(results: list[BenchmarkResult], total_wall: float = 0, *, with_rationale: bool = False) -> None:
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
        table.add_row(
            str(r.number), r.question,
            Text(r.grade, style=GRADE_STYLE.get(r.grade, "")),
            f"{r.elapsed:.1f}s", str(r.total_steps), str(r.execute_calls),
            str(r.search_calls), f"{r.total_tokens:,}", f"{r.total_reasoning_tokens:,}",
        )
    console.print(table)

    n = len(results)
    grades = [r.grade for r in results]
    passed = grades.count("PASS")
    total_time = sum(r.elapsed for r in results)
    total_tokens = sum(r.total_tokens for r in results)
    total_reasoning = sum(r.total_reasoning_tokens for r in results)
    total_exec = sum(r.execute_calls for r in results)
    total_steps = sum(r.total_steps for r in results)
    times = sorted(r.elapsed for r in results)

    console.print()
    console.print(f"  Pass rate:      {passed}/{n} ({100 * passed / n:.0f}%)")
    for g in ("EMPTY", "TIMEOUT", "SERVER_ERROR", "ERROR", "SPARQL_ERROR", "NO_ANSWER"):
        if c := grades.count(g):
            console.print(f"  {g}:{' ' * (14 - len(g))}{c}/{n}")
    console.print(f"  Total time:     {total_time:.0f}s (avg {total_time / n:.1f}s, wall {total_wall:.0f}s)")
    console.print(f"  Total tokens:   {total_tokens:,} ({total_reasoning:,} reasoning)")
    console.print(f"  Total steps:    {total_steps} (avg {total_steps / n:.1f})")
    console.print(f"  SPARQL execs:   {total_exec} (avg {total_exec / n:.1f})")
    console.print(f"  Time p50/p90:   {times[len(times) // 2]:.1f}s / {times[int(len(times) * 0.9)]:.1f}s")
    console.print(f"  Rationale:      {'yes' if with_rationale else 'no'}")
    console.print()


# ---------------------------------------------------------------------------
# Async core — server config + websocket streaming
# ---------------------------------------------------------------------------


async def save_server_config(ws_url: str, config_path: Path, *, with_rationale: bool = False) -> dict:
    http_base = ws_url.replace("ws://", "http://").replace("/live", "")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{http_base}/config", timeout=5)
    config = resp.json()
    config["with_rationale"] = with_rationale
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    return config


async def _tick_spinner(spinner: Spinner, t0_question: float, t0_total: float) -> None:
    """Background task that updates the spinner's elapsed-time text."""
    while True:
        q_elapsed = time.time() - t0_question
        total_elapsed = time.time() - t0_total
        spinner.update(text=f"[dim]{q_elapsed:.1f}s  (total {total_elapsed:.0f}s)[/]")
        await asyncio.sleep(0.1)


async def run_question(
    ws_url: str, question: str, timeout: float, t0_total: float,
) -> tuple[dict, list[Step], float]:
    """Stream a question over WebSocket, displaying steps live under a spinner."""
    payload = json.dumps({
        "task": "sparql-qa",
        "input": question,
        "knowledge_graphs": ["europeana"],
    })
    steps: list[Step] = []
    t0 = time.time()
    deadline = t0 + timeout
    final_data: dict = {"error": "no output received", "output": None}
    ack = json.dumps({})

    spinner = Spinner("dots", text="[dim]connecting...[/]", style="blue")
    ticker = asyncio.create_task(_tick_spinner(spinner, t0, t0_total))

    try:
        with Live(spinner, console=console, transient=True, refresh_per_second=10):
            try:
                async with websockets.connect(ws_url, close_timeout=5) as ws:
                    await ws.send(payload)

                    while True:
                        remaining = deadline - time.time()
                        if remaining <= 0:
                            raise asyncio.TimeoutError()

                        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                        msg = json.loads(raw)

                        if "error" in msg and isinstance(msg["error"], str):
                            final_data = {"error": msg["error"], "output": None}
                            break

                        step = _parse_step(msg, time.time() - t0)
                        steps.append(step)
                        display_step(step)

                        if msg.get("type") == "output":
                            final_data = msg
                            await ws.send(ack)
                            break

                        await ws.send(ack)

            except asyncio.TimeoutError:
                final_data = {"error": "timeout", "output": None}
            except Exception as e:
                final_data = {"error": str(e), "output": None}
    finally:
        ticker.cancel()
        try:
            await ticker
        except asyncio.CancelledError:
            pass

    return final_data, steps, time.time() - t0


# ---------------------------------------------------------------------------
# Async main
# ---------------------------------------------------------------------------


async def run_benchmark() -> None:
    parser = argparse.ArgumentParser(description="GRASP benchmark")
    parser.add_argument("questions_file", nargs="?", default=None,
                        help="YAML question file (default: benchmark.yml)")
    parser.add_argument("--timeout", type=float, default=180.0,
                        help="Total timeout per question in seconds (default: 180)")
    parser.add_argument("--question", type=int, default=None,
                        help="Run only question N (1-indexed)")
    parser.add_argument("--url", default=GRASP_WS_URL, help="GRASP WebSocket URL")
    parser.add_argument("--overwrite", action="store_true",
                        help="Overwrite results file instead of appending")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Re-run questions that previously failed (timeout, server error)")
    parser.add_argument("--with-rationale", action="store_true",
                        help="Include rationale context in prompts sent to the server")
    args = parser.parse_args()

    # Resolve question file and derived paths
    if args.questions_file is not None:
        questions_path = Path(args.questions_file).resolve()
    else:
        questions_path = BENCHMARK_PATH
    report_path, config_path = _derive_paths(questions_path)

    all_questions = load_questions(questions_path, with_rationale=args.with_rationale)

    # Check server reachability and save config
    try:
        config = await save_server_config(
            args.url, config_path, with_rationale=args.with_rationale,
        )
        model = config.get("model", "unknown")
    except Exception:
        console.print("[red]ERROR: GRASP server not reachable[/]")
        sys.exit(1)

    # Load existing results for skip/retry logic
    existing: dict[int, dict] = {}
    if not args.overwrite and not args.question:
        existing = load_existing_results(report_path)

    # Select questions to run
    if args.question is not None:
        idx = args.question - 1
        if idx < 0 or idx >= len(all_questions):
            console.print(f"[red]Question number must be 1-{len(all_questions)}[/]")
            sys.exit(1)
        questions = [(idx, all_questions[idx])]
    else:
        questions = list(enumerate(all_questions))

    # Filter based on existing results
    skip_count = retry_count = 0
    if existing and not args.question:
        filtered = []
        for idx, q in questions:
            prev = existing.get(idx + 1)
            if prev is None:
                filtered.append((idx, q))
            elif args.retry_failed and is_retriable(prev):
                filtered.append((idx, q))
                retry_count += 1
            else:
                skip_count += 1
        questions = filtered

    # Banner
    console.print(f"\n[bold blue]GRASP Benchmark[/]")
    console.print(f"  Model: {model}")
    console.print(f"  Questions: {questions_path}")
    console.print(f"  Running {len(questions)} question(s) against {args.url}")
    console.print(f"  Timeout: {args.timeout}s per question")
    console.print(f"  Rationale: {'included in prompts' if args.with_rationale else 'off'}")
    console.print(f"  Results: {report_path} ({'overwrite' if args.overwrite else 'append'})")
    if skip_count:
        console.print(f"  Skipping {skip_count} already-completed question(s)")
    if retry_count:
        console.print(f"  Retrying {retry_count} previously-failed question(s)")
    console.print()

    # Run questions, streaming results to JSONL
    results: list[BenchmarkResult] = []
    results_file = open(report_path, "w" if args.overwrite else "a")
    t0_total = time.time()

    try:
        for idx, q in questions:
            console.rule(f"[bold]\\[{idx + 1}/{len(all_questions)}] {q}[/]")

            data, steps, elapsed = await run_question(args.url, q, args.timeout, t0_total)
            r = build_result(idx, q, data, steps, elapsed)
            results.append(r)

            display_result_footer(r)

            results_file.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
            results_file.flush()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted — saving partial results[/]")
    finally:
        results_file.close()
        total_wall = time.time() - t0_total

    if len(results) > 1:
        display_summary(results, total_wall, with_rationale=args.with_rationale)

    console.print(f"  Results saved to {report_path}")
    console.print(f"  Config saved to {config_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    asyncio.run(run_benchmark())


if __name__ == "__main__":
    main()
