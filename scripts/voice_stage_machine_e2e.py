#!/usr/bin/env python3
"""
Phase 157.3.1 Jarvis stage-machine full socket E2E benchmark.

Measures real runtime path through:
jarvis_listen_start -> jarvis_listen_stop(transcript_hint) ->
jarvis_response(filler/real) -> jarvis_audio -> jarvis_state(idle)

Outputs:
- docs/157_ph/benchmarks/phase157_stage_machine_e2e_<ts>.json
- docs/157_ph/benchmarks/phase157_stage_machine_e2e_<ts>.csv
- docs/157_ph/benchmarks/phase157_stage_machine_e2e_<ts>.md
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import socketio
except Exception as e:  # pragma: no cover
    raise SystemExit(f"python-socketio not available: {e}")

BENCH_DIR = Path("docs/157_ph/benchmarks")


@dataclass
class E2ERow:
    prompt_id: str
    run_index: int
    success: bool
    error: str | None
    ttfr_filler_ms: float | None
    ttfr_response_ms: float | None
    ttfa_audio_ms: float | None
    t_idle_ms: float | None
    response_status: str | None
    stage_sequence: str
    response_preview: str
    timestamp: str


class JarvisE2EProbe:
    def __init__(self, url: str, user_id: str, timeout_sec: float) -> None:
        self.url = url
        self.user_id = user_id
        self.timeout_sec = timeout_sec
        self.sio = socketio.AsyncClient(reconnection=False, logger=False, engineio_logger=False)
        self.events: list[tuple[float, str, dict[str, Any]]] = []
        self._wire_handlers()

    def _wire_handlers(self) -> None:
        @self.sio.on("jarvis_state")
        async def _on_state(data):
            self.events.append((time.perf_counter(), "jarvis_state", data or {}))

        @self.sio.on("jarvis_response")
        async def _on_response(data):
            self.events.append((time.perf_counter(), "jarvis_response", data or {}))

        @self.sio.on("jarvis_audio")
        async def _on_audio(data):
            self.events.append((time.perf_counter(), "jarvis_audio", data or {}))

        @self.sio.on("jarvis_stage")
        async def _on_stage(data):
            self.events.append((time.perf_counter(), "jarvis_stage", data or {}))

        @self.sio.on("jarvis_error")
        async def _on_error(data):
            self.events.append((time.perf_counter(), "jarvis_error", data or {}))

    async def connect(self) -> None:
        await self.sio.connect(self.url, transports=["websocket"], wait_timeout=10)

    async def close(self) -> None:
        if self.sio.connected:
            await self.sio.disconnect()

    async def run_one(self, prompt_id: str, prompt_text: str, run_index: int) -> E2ERow:
        self.events = []
        start = time.perf_counter()

        ctx = {
            "viewport_context": {
                "total_visible": 6,
                "total_pinned": 3,
                "zoom_level": 2.0,
            },
            "pinned_files": [
                {"path": "docs/157_ph/MARKER_157_ABBREVIATIONS_RUNTIME_MAP_2026-03-01.md", "name": "abbr"},
                {"path": "docs/157_ph/MARKER_157_MEMORY_FLOW_AUDIT_2026-03-01.md", "name": "mem_flow"},
            ],
            "open_chat_context": {
                "chat_id": "benchmark-chat",
                "messages": [{"role": "user", "content": "test context"}],
            },
            "cam_context": {"source": "stage_machine_e2e"},
        }

        await self.sio.emit("jarvis_listen_start", {"user_id": self.user_id, **ctx})
        await asyncio.sleep(0.08)
        await self.sio.emit(
            "jarvis_listen_stop",
            {"user_id": self.user_id, "transcript_hint": prompt_text, **ctx},
        )

        got_idle = False
        while (time.perf_counter() - start) < self.timeout_sec:
            await asyncio.sleep(0.05)
            for ts, ev, payload in self.events:
                if ev == "jarvis_state" and str(payload.get("state")) == "idle" and ts >= start:
                    got_idle = True
            if got_idle:
                break

        ttfr_filler_ms = None
        ttfr_response_ms = None
        ttfa_audio_ms = None
        t_idle_ms = None
        response_status = None
        response_preview = ""
        stage_sequence: list[str] = []
        error = None

        for ts, ev, payload in self.events:
            delta = (ts - start) * 1000.0
            if ev == "jarvis_error" and error is None:
                error = str(payload.get("error") or "jarvis_error")
            if ev == "jarvis_stage":
                stage = str(payload.get("stage") or "")
                if stage:
                    stage_sequence.append(stage)
            if ev == "jarvis_response":
                status = str(payload.get("status") or "")
                text = str(payload.get("text") or "").strip()
                if status == "filler" and ttfr_filler_ms is None:
                    ttfr_filler_ms = round(delta, 2)
                elif status != "filler" and ttfr_response_ms is None:
                    ttfr_response_ms = round(delta, 2)
                    response_status = status
                    response_preview = text[:160]
            if ev == "jarvis_audio" and ttfa_audio_ms is None:
                ttfa_audio_ms = round(delta, 2)
            if ev == "jarvis_state" and str(payload.get("state")) == "idle" and t_idle_ms is None:
                t_idle_ms = round(delta, 2)

        success = bool(ttfr_response_ms is not None and (ttfa_audio_ms is not None or t_idle_ms is not None))
        if not success and error is None and (time.perf_counter() - start) >= self.timeout_sec:
            error = f"timeout>{self.timeout_sec}s"

        return E2ERow(
            prompt_id=prompt_id,
            run_index=run_index,
            success=success,
            error=error,
            ttfr_filler_ms=ttfr_filler_ms,
            ttfr_response_ms=ttfr_response_ms,
            ttfa_audio_ms=ttfa_audio_ms,
            t_idle_ms=t_idle_ms,
            response_status=response_status,
            stage_sequence=" > ".join(stage_sequence),
            response_preview=response_preview,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


def _default_prompts() -> list[tuple[str, str]]:
    return [
        ("short", "Привет, ты тут?"),
        ("context", "Коротко: что сейчас главное в этой фазе и какие 2 шага дальше?"),
        ("deep", "Сделай подробный анализ архитектуры stage-machine и предложи план улучшений."),
    ]


def _percent(v: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * v / total, 2)


def _median(values: list[float | None]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    nums.sort()
    n = len(nums)
    if n % 2 == 1:
        return round(nums[n // 2], 2)
    return round((nums[n // 2 - 1] + nums[n // 2]) / 2.0, 2)


def _write_outputs(rows: list[E2ERow]) -> tuple[Path, Path, Path]:
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = BENCH_DIR / f"phase157_stage_machine_e2e_{ts}.json"
    csv_path = BENCH_DIR / f"phase157_stage_machine_e2e_{ts}.csv"
    md_path = BENCH_DIR / f"phase157_stage_machine_e2e_{ts}.md"

    payload = {
        "summary": {
            "runs": len(rows),
            "success_runs": sum(1 for r in rows if r.success),
            "success_rate": _percent(sum(1 for r in rows if r.success), len(rows)),
            "ttfr_filler_ms_p50": _median([r.ttfr_filler_ms for r in rows]),
            "ttfr_response_ms_p50": _median([r.ttfr_response_ms for r in rows]),
            "ttfa_audio_ms_p50": _median([r.ttfa_audio_ms for r in rows]),
            "t_idle_ms_p50": _median([r.t_idle_ms for r in rows]),
        },
        "rows": [asdict(r) for r in rows],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = list(asdict(rows[0]).keys()) if rows else [
            "prompt_id", "run_index", "success", "error", "ttfr_filler_ms", "ttfr_response_ms",
            "ttfa_audio_ms", "t_idle_ms", "response_status", "stage_sequence", "response_preview", "timestamp"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    summary = payload["summary"]
    lines = [
        "# Phase 157 Stage-Machine Full E2E",
        "",
        "## Summary",
        f"- Runs: {summary['runs']}",
        f"- Success runs: {summary['success_runs']} ({summary['success_rate']}%)",
        f"- TTFR filler p50: {summary['ttfr_filler_ms_p50']} ms",
        f"- TTFR response p50: {summary['ttfr_response_ms_p50']} ms",
        f"- TTFA audio p50: {summary['ttfa_audio_ms_p50']} ms",
        f"- Idle return p50: {summary['t_idle_ms_p50']} ms",
        "",
        "## Runs",
    ]
    for r in rows:
        lines.extend(
            [
                f"- `{r.prompt_id}#{r.run_index}` success={r.success}",
                f"  - filler={r.ttfr_filler_ms} ms, response={r.ttfr_response_ms} ms, audio={r.ttfa_audio_ms} ms, idle={r.t_idle_ms} ms",
                f"  - stage: {r.stage_sequence or '[none]'}",
                f"  - status: {r.response_status or '[none]'}",
                f"  - preview: `{r.response_preview or '[empty]'}`",
                f"  - error: `{r.error}`" if r.error else "",
            ]
        )
    md_path.write_text("\n".join(x for x in lines if x is not None), encoding="utf-8")

    return json_path, csv_path, md_path


async def _amain(args: argparse.Namespace) -> int:
    probe = JarvisE2EProbe(url=args.url, user_id=args.user_id, timeout_sec=args.timeout_sec)

    try:
        await probe.connect()
    except Exception as e:
        print(json.dumps({"error": f"connect_failed: {e}", "url": args.url}, ensure_ascii=False, indent=2))
        return 2

    rows: list[E2ERow] = []
    prompts = _default_prompts()
    try:
        for prompt_id, prompt_text in prompts:
            for idx in range(1, max(1, args.runs_per_prompt) + 1):
                rows.append(await probe.run_one(prompt_id, prompt_text, idx))
                await asyncio.sleep(0.2)
    finally:
        await probe.close()

    json_path, csv_path, md_path = _write_outputs(rows)
    print(
        json.dumps(
            {
                "summary": {
                    "runs": len(rows),
                    "success": sum(1 for r in rows if r.success),
                    "ttfr_response_ms_p50": _median([r.ttfr_response_ms for r in rows]),
                    "ttfa_audio_ms_p50": _median([r.ttfa_audio_ms for r in rows]),
                },
                "json": str(json_path),
                "csv": str(csv_path),
                "md": str(md_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Phase 157 stage-machine full socket e2e")
    p.add_argument("--url", default=os.environ.get("JARVIS_BENCH_URL", "http://127.0.0.1:5001"))
    p.add_argument("--user-id", default=os.environ.get("JARVIS_BENCH_USER", "default_user"))
    p.add_argument("--runs-per-prompt", type=int, default=int(os.environ.get("JARVIS_BENCH_RUNS", "1")))
    p.add_argument("--timeout-sec", type=float, default=float(os.environ.get("JARVIS_BENCH_TIMEOUT", "45")))
    args = p.parse_args()
    return asyncio.run(_amain(args))


if __name__ == "__main__":
    raise SystemExit(main())
