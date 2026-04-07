"""Unified benchmark runner for NL query backends.

Runs test questions from ``benchmark.yml`` through any
:class:`~europeana_qlever.ask.AskBackend` (parquet, sparql, or both),
grades results, displays progress, and streams results to JSONL.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml
from rich.table import Table
from rich.text import Text

from .. import display
from . import GRADE_STYLE, AskBackend, AskResult, display_result

# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

BENCHMARK_PATH = Path(__file__).parent / "benchmark.yml"


def load_questions(
    path: Path | None = None, *, with_rationale: bool = False
) -> list[dict]:
    """Load questions from a YAML file.

    Returns a list of dicts with ``question`` (and optionally ``rationale``).
    """
    path = path or BENCHMARK_PATH
    with open(path) as f:
        raw = yaml.safe_load(f)
    entries = raw["questions"] if isinstance(raw, dict) else raw
    out: list[dict] = []
    for q in entries:
        if isinstance(q, dict):
            text = q["question"]
            if with_rationale and q.get("rationale"):
                text += f"\n\nContext: {q['rationale']}"
            out.append({"question": text, "rationale": q.get("rationale", "")})
        else:
            out.append({"question": q, "rationale": ""})
    return out


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

_SERVER_ERROR_PHRASES = [
    "503 server error", "502 server error",
    "(read timeout=", "(connect timeout=", "403 client error",
]


def grade_result(result: AskResult) -> str:
    """Grade an AskResult into PASS/EMPTY/TIMEOUT/ERROR/NO_ANSWER."""
    if result.error:
        err = result.error.lower()
        if "timeout" in err or "timed out" in err:
            return "TIMEOUT"
        if any(phrase in err for phrase in _SERVER_ERROR_PHRASES):
            return "SERVER_ERROR"
        return "ERROR"
    if result.answer:
        return "PASS"
    return "NO_ANSWER"


def is_retriable(grade: str, error: str | None) -> bool:
    """Check if a result grade is worth retrying."""
    if grade == "TIMEOUT":
        return True
    if grade in ("ERROR", "SERVER_ERROR") and error:
        lower = error.lower()
        if any(p in lower for p in _SERVER_ERROR_PHRASES):
            return True
    return False


# ---------------------------------------------------------------------------
# Benchmark result
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkResult:
    """A graded benchmark result wrapping an AskResult."""

    number: int
    question: str
    backend: str
    grade: str
    elapsed: float
    answer: str | None = None
    query: str | None = None
    result_text: str | None = None
    error: str | None = None
    total_steps: int = 0
    total_tokens: int = 0

    @classmethod
    def from_ask_result(cls, number: int, result: AskResult) -> BenchmarkResult:
        total_tokens = sum(
            s.completion_tokens + s.prompt_tokens for s in result.steps
        )
        return cls(
            number=number,
            question=result.question,
            backend=result.backend,
            grade=grade_result(result),
            elapsed=round(result.elapsed, 1),
            answer=result.answer,
            query=result.query,
            result_text=result.result_text,
            error=result.error,
            total_steps=len(result.steps),
            total_tokens=total_tokens,
        )


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


def display_result_footer(r: BenchmarkResult) -> None:
    """Print a compact result summary line."""
    console = display.console
    grade_text = Text(r.grade, style=GRADE_STYLE.get(r.grade, ""))
    console.print(
        "  ", grade_text,
        f"  {r.elapsed:.1f}s  "
        f"{r.total_steps} steps  "
        f"{r.total_tokens:,} tok",
        sep="",
    )
    if r.answer:
        console.print(f"\n[bold]Answer:[/]\n{r.answer}")
    if r.query:
        label = "SQL" if r.backend == "parquet" else "SPARQL"
        console.print(f"\n[bold]Final {label}:[/]")
        console.print(f"[cyan]{r.query}[/cyan]")
    if r.result_text:
        console.print(f"\n[bold]Result:[/]\n{r.result_text}")
    if r.error:
        console.print(f"\n[bold red]Error:[/]\n{r.error}")
    console.print()


def display_summary(
    results: list[BenchmarkResult], total_wall: float = 0,
) -> None:
    """Print a summary table of all benchmark results."""
    console = display.console
    console.rule("[bold]Summary[/]")

    table = Table(show_header=True, header_style="bold", padding=(0, 1))
    table.add_column("#", justify="right", width=3)
    table.add_column("Backend", width=7)
    table.add_column("Question", no_wrap=False)
    table.add_column("Grade", justify="center", width=12)
    table.add_column("Time", justify="right", width=6)
    table.add_column("Steps", justify="right", width=5)
    table.add_column("Tokens", justify="right", width=8)

    for r in results:
        table.add_row(
            str(r.number),
            r.backend,
            r.question[:60] + ("…" if len(r.question) > 60 else ""),
            Text(r.grade, style=GRADE_STYLE.get(r.grade, "")),
            f"{r.elapsed:.1f}s",
            str(r.total_steps),
            f"{r.total_tokens:,}",
        )
    console.print(table)

    n = len(results)
    if n == 0:
        return
    grades = [r.grade for r in results]
    passed = grades.count("PASS")
    total_time = sum(r.elapsed for r in results)
    total_tokens = sum(r.total_tokens for r in results)

    console.print()
    console.print(f"  Pass rate:      {passed}/{n} ({100 * passed / n:.0f}%)")
    for g in ("EMPTY", "TIMEOUT", "SERVER_ERROR", "ERROR", "SPARQL_ERROR", "SQL_ERROR", "NO_ANSWER"):
        if c := grades.count(g):
            console.print(f"  {g}:{' ' * (14 - len(g))}{c}/{n}")
    console.print(f"  Total time:     {total_time:.0f}s (avg {total_time / n:.1f}s, wall {total_wall:.0f}s)")
    console.print(f"  Total tokens:   {total_tokens:,}")
    console.print()


# ---------------------------------------------------------------------------
# Existing results (for skip/retry logic)
# ---------------------------------------------------------------------------


def load_existing_results(path: Path) -> dict[int, dict]:
    """Load previously saved JSONL results, keyed by question number."""
    results: dict[int, dict] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if not (line := line.strip()):
                continue
            try:
                r = json.loads(line)
                results[r["number"]] = r
            except (json.JSONDecodeError, KeyError):
                continue
    return results


# ---------------------------------------------------------------------------
# Benchmark orchestrator
# ---------------------------------------------------------------------------


class Benchmark:
    """Runs questions through one or more AskBackends and saves results.

    Args:
        questions: list of question dicts (from :func:`load_questions`)
        backends: list of :class:`AskBackend` instances to benchmark
        output_dir: directory for JSONL result files
    """

    def __init__(
        self,
        questions: list[dict],
        backends: list[AskBackend],
        output_dir: Path,
        *,
        timeout: float = 180.0,
        verbose: bool = False,
    ) -> None:
        self._questions = questions
        self._backends = backends
        self._output_dir = output_dir
        self._timeout = timeout
        self._verbose = verbose

    async def run(
        self,
        *,
        question_number: int | None = None,
        retry_failed: bool = False,
        overwrite: bool = False,
    ) -> list[BenchmarkResult]:
        """Run the benchmark and return results."""
        import asyncio

        console = display.console
        self._output_dir.mkdir(parents=True, exist_ok=True)
        all_results: list[BenchmarkResult] = []
        t0_total = time.time()

        for backend in self._backends:
            results_path = self._output_dir / f"benchmark-{backend.name}.jsonl"

            # Load existing for skip/retry
            existing: dict[int, dict] = {}
            if not overwrite and question_number is None:
                existing = load_existing_results(results_path)

            # Select questions
            if question_number is not None:
                idx = question_number - 1
                if idx < 0 or idx >= len(self._questions):
                    console.print(
                        f"[red]Question number must be 1-{len(self._questions)}[/]"
                    )
                    continue
                pairs = [(idx, self._questions[idx])]
            else:
                pairs = list(enumerate(self._questions))

            # Filter based on existing
            skip_count = retry_count = 0
            if existing and question_number is None:
                filtered = []
                for idx, q in pairs:
                    prev = existing.get(idx + 1)
                    if prev is None:
                        filtered.append((idx, q))
                    elif retry_failed and is_retriable(
                        prev.get("grade", ""), prev.get("error")
                    ):
                        filtered.append((idx, q))
                        retry_count += 1
                    else:
                        skip_count += 1
                pairs = filtered

            # Banner
            console.print(f"\n[bold blue]Benchmark: {backend.name}[/]")
            console.print(f"  Running {len(pairs)} question(s), timeout {self._timeout}s")
            if skip_count:
                console.print(f"  Skipping {skip_count} already-completed")
            if retry_count:
                console.print(f"  Retrying {retry_count} previously-failed")
            console.print()

            # Run questions
            results_file = open(results_path, "w" if overwrite else "a")
            backend_results: list[BenchmarkResult] = []

            try:
                for idx, q in pairs:
                    question_text = q["question"]
                    console.rule(
                        f"[bold]\\[{idx + 1}/{len(self._questions)}] "
                        f"{question_text[:80]}[/]"
                    )

                    result = await backend.ask(
                        question_text,
                        timeout=self._timeout,
                        verbose=self._verbose,
                    )

                    br = BenchmarkResult.from_ask_result(idx + 1, result)
                    backend_results.append(br)
                    all_results.append(br)

                    display_result_footer(br)

                    results_file.write(
                        json.dumps(asdict(br), ensure_ascii=False) + "\n"
                    )
                    results_file.flush()

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted — saving partial results[/]")
            finally:
                results_file.close()

            if len(backend_results) > 1:
                total_wall = time.time() - t0_total
                display_summary(backend_results, total_wall)

            console.print(f"  Results saved to {results_path}")

        return all_results
