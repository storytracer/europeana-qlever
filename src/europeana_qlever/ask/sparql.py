"""AskSPARQL — NL→SPARQL agent over QLever via GRASP WebSocket.

Wraps the GRASP agent protocol: sends a natural-language question over
WebSocket, streams step-by-step agent traces (model reasoning, entity
search, SPARQL execution), and returns an :class:`AskResult`.

Requires a running GRASP server (``grasp serve``) and QLever endpoint.
"""

from __future__ import annotations

import asyncio
import json
import time

from . import AskBackend, AskResult, AskStep, display_step


# ---------------------------------------------------------------------------
# GRASP response grading
# ---------------------------------------------------------------------------

_SERVER_ERROR_PHRASES = [
    "503 server error",
    "502 server error",
    "(read timeout=",
    "(connect timeout=",
    "403 client error",
]


def _is_server_error(message: str | None) -> bool:
    if message is None:
        return False
    lower = message.lower()
    return any(phrase in lower for phrase in _SERVER_ERROR_PHRASES)


def _grade_grasp_response(data: dict) -> str:
    """Grade a GRASP response into PASS/EMPTY/TIMEOUT/ERROR/etc."""
    if data.get("error"):
        err = str(data["error"])
        if "timeout" in err.lower() or "timed out" in err.lower():
            return "TIMEOUT"
        return "SERVER_ERROR" if _is_server_error(err) else "ERROR"
    output = data.get("output") or {}
    if output.get("type") == "error":
        return "SPARQL_ERROR"
    if output.get("type") == "answer":
        result = output.get("result", "")
        if result.startswith("Got 0 rows"):
            return "EMPTY"
        if result:
            return "PASS"
    return "NO_ANSWER"


# ---------------------------------------------------------------------------
# Step parsing
# ---------------------------------------------------------------------------


def _parse_grasp_step(msg: dict, ts: float) -> AskStep:
    """Parse a GRASP WebSocket message into an AskStep."""
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
            reason_tok = (
                usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
            )
            cached_tok = (
                usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
            )
        return AskStep(
            type="model",
            timestamp=round(ts, 2),
            reasoning=reasoning,
            completion_tokens=comp_tok,
            prompt_tokens=prompt_tok,
            reasoning_tokens=reason_tok,
            cached_prompt_tokens=cached_tok,
        )

    if msg_type == "tool":
        return AskStep(
            type="tool",
            timestamp=round(ts, 2),
            tool=msg.get("name"),
            tool_args=msg.get("args"),
            tool_result=msg.get("result"),
        )

    return AskStep(type=msg_type, timestamp=round(ts, 2))


# ---------------------------------------------------------------------------
# AskSPARQL backend
# ---------------------------------------------------------------------------


class AskSPARQL(AskBackend):
    """NL→SPARQL agent over QLever via GRASP WebSocket."""

    name = "sparql"

    def __init__(self, ws_url: str = "ws://localhost:6789/live") -> None:
        self._ws_url = ws_url

    async def ask(
        self,
        question: str,
        *,
        timeout: float = 180.0,
        verbose: bool = False,
    ) -> AskResult:
        """Send a question to GRASP and stream the agent trace."""
        import websockets
        from rich.live import Live
        from rich.spinner import Spinner

        from .. import display

        console = display.console
        t0 = time.time()
        deadline = t0 + timeout
        steps: list[AskStep] = []
        final_data: dict = {"error": "no output received", "output": None}
        ack = json.dumps({})

        payload = json.dumps({
            "task": "sparql-qa",
            "input": question,
            "knowledge_graphs": ["europeana"],
        })

        spinner = Spinner("dots", text="[dim]connecting…[/]", style="blue")

        async def tick_spinner() -> None:
            while True:
                elapsed = time.time() - t0
                spinner.update(text=f"[dim]{elapsed:.1f}s[/]")
                await asyncio.sleep(0.1)

        ticker = asyncio.create_task(tick_spinner())

        try:
            with Live(spinner, console=console, transient=True, refresh_per_second=10):
                try:
                    async with websockets.connect(
                        self._ws_url, close_timeout=5
                    ) as ws:
                        await ws.send(payload)

                        while True:
                            remaining = deadline - time.time()
                            if remaining <= 0:
                                raise asyncio.TimeoutError()

                            raw = await asyncio.wait_for(
                                ws.recv(), timeout=remaining
                            )
                            msg = json.loads(raw)

                            if "error" in msg and isinstance(msg["error"], str):
                                final_data = {"error": msg["error"], "output": None}
                                break

                            step = _parse_grasp_step(msg, time.time() - t0)
                            steps.append(step)

                            if verbose:
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

        elapsed = time.time() - t0
        output = final_data.get("output") or {}

        return AskResult(
            question=question,
            backend=self.name,
            answer=output.get("answer"),
            query=output.get("sparql"),
            result_text=output.get("result"),
            steps=steps,
            elapsed=elapsed,
            error=final_data.get("error") if final_data.get("error") else None,
        )
