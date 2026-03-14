#!/usr/bin/env python3
"""
Phase 157.3.1 speculative voice benchmark harness.

Purpose:
- Benchmark draft->target speculative pairing for Jarvis voice path.
- Export decision-grade metrics for acceptance/correction and reaction latency.

Outputs:
- docs/157_ph/benchmarks/phase157_speculative_pair_<ts>.json
- docs/157_ph/benchmarks/phase157_speculative_pair_<ts>.csv
- docs/157_ph/benchmarks/phase157_speculative_pair_<ts>.md
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import inspect
import json
import os
import re
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.elisya.provider_registry import ProviderRegistry, call_model_v2_stream
from src.voice.prosody_chunker import extract_ready_chunks


BENCH_DIR = Path("docs/157_ph/benchmarks")


@dataclass
class SpecRow:
    pair_name: str
    prompt_id: str
    run_index: int
    draft_model: str
    target_model: str
    draft_source: str | None
    target_source: str | None
    success: bool
    error: str | None
    draft_ttft_ms: float | None
    target_ttft_ms: float | None
    draft_first_chunk_ms: float | None
    target_first_chunk_ms: float | None
    ttft_gain_ms: float | None
    target_reaction_text_ms: float | None
    target_reaction_audio_ready_ms: float | None
    acceptance_rate: float
    correction_rate: float
    compared_tokens: int
    draft_tokens_out: int
    target_tokens_out: int
    target_response_chars: int
    grounded_context: bool
    grounded_files: int
    grounded_packing_path: str | None
    grounded_jepa_trigger: bool | None
    grounded_jepa_mode: bool | None
    target_preview: str
    timestamp: str


def _default_prompts() -> list[tuple[str, str]]:
    return [
        (
            "short_1",
            "На основе переданного контекста назови 2 конкретных файла и по 1 фразе, зачем каждый нужен. "
            "Если фактов нет — так и скажи.",
        ),
        (
            "context_1",
            "На основе контекста дай короткий план (3 пункта) как улучшить memory context packing в VETKA "
            "без регрессий в latency. Без общих фраз.",
        ),
        (
            "long_1",
            "Объясни пошагово interrupt + restart stream protocol и влияние на voice handoff/tool-loop transparency, "
            "ссылаясь на контекст. Если в контексте этого нет — прямо укажи это.",
        ),
        (
            "interrupt_1",
            "INTERRUPT_TEST::first=Начни объяснять как устроен context packing в VETKA подробно.;"
            "second=Стоп, коротко: назови 2 шага что делать сначала.",
        ),
    ]


def _fit_prompt_for_model(prompt: str, model_name: str) -> str:
    text = (prompt or "").strip()
    if not text:
        return text
    is_local = "/" not in (model_name or "")
    if not is_local:
        return text
    budget = max(800, int(os.environ.get("BENCH_LOCAL_PROMPT_CHAR_BUDGET", "3200")))
    if len(text) <= budget:
        return text
    head = max(400, int(budget * 0.6))
    tail = max(200, budget - head - 64)
    return f"{text[:head]}\n\n...[LOCAL_PROMPT_TRUNCATED]...\n\n{text[-tail:]}"


def _parse_interrupt_prompt(prompt: str) -> tuple[str, str]:
    raw = (prompt or "").strip()
    if not raw.startswith("INTERRUPT_TEST::"):
        return "", ""
    body = raw.split("::", 1)[1]
    first, second = "", ""
    for part in body.split(";"):
        if part.startswith("first="):
            first = part[len("first=") :].strip()
        elif part.startswith("second="):
            second = part[len("second=") :].strip()
    return first, second


async def _build_grounded_prompt(
    *,
    user_prompt: str,
    model_name: str,
    pair_name: str,
    enable_grounded: bool,
    grounded_limit: int,
    force_jepa: bool,
) -> tuple[str, dict[str, Any]]:
    meta: dict[str, Any] = {
        "grounded_context": False,
        "grounded_files": 0,
        "grounded_packing_path": None,
        "grounded_jepa_trigger": None,
        "grounded_jepa_mode": None,
    }
    if not enable_grounded:
        return user_prompt, meta

    try:
        from src.search.hybrid_search import get_hybrid_search
        from src.orchestration.context_packer import get_context_packer
        from src.api.handlers.chat_handler import build_model_prompt
    except Exception:
        return user_prompt, meta

    try:
        svc = get_hybrid_search()
        hs = await svc.search(query=user_prompt, limit=max(grounded_limit * 3, 30), mode="hybrid")
    except Exception:
        return user_prompt, meta

    seen: set[str] = set()
    pinned_files: list[dict[str, Any]] = []
    for item in hs.get("results", []):
        raw_path = str(item.get("path") or "").strip()
        if not raw_path:
            continue
        p = Path(raw_path)
        if not p.exists() or not p.is_file():
            continue
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        pinned_files.append(
            {
                "path": key,
                "name": p.name,
                "node_id": key,
                "type": "file",
                "score": float(item.get("score", 0.0) or 0.0),
            }
        )
        if len(pinned_files) >= max(1, grounded_limit):
            break

    if not pinned_files:
        return user_prompt, meta

    viewport_context = {
        "visible_nodes": [
            {
                "path": pf["path"],
                "distance_to_camera": float(80 + idx * 15),
                "lod_level": 6 if idx < 5 else 7,
                "is_pinned": True,
                "is_center": idx == 0,
            }
            for idx, pf in enumerate(pinned_files)
        ],
        "total_visible": len(pinned_files),
        "total_pinned": len(pinned_files),
        "zoom_level": 2.0,
    }

    packer = get_context_packer()
    pack_kwargs = dict(
        user_query=user_prompt,
        pinned_files=pinned_files,
        viewport_context=viewport_context,
        session_id=f"spec_bench:{pair_name}",
        model_name=model_name,
        user_id="benchmark",
        zoom_level=2.0,
    )
    try:
        if "force_jepa" in inspect.signature(packer.pack).parameters:
            pack_kwargs["force_jepa"] = force_jepa
    except Exception:
        pass

    packed = await packer.pack(**pack_kwargs)

    context_for_model = (
        "## SPECULATIVE BENCHMARK CONTEXT\n"
        "Use only provided project context. If facts are missing, say that clearly."
    )
    effective_prompt = build_model_prompt(
        text=user_prompt,
        context_for_model=context_for_model,
        pinned_context=packed.pinned_context,
        history_context="",
        viewport_summary=packed.viewport_summary,
        json_context=packed.json_context + packed.jepa_context,
        web_context_summary="",
    )

    trace = packed.trace or {}
    meta.update(
        {
            "grounded_context": True,
            "grounded_files": len(pinned_files),
            "grounded_packing_path": str(trace.get("packing_path") or ""),
            "grounded_jepa_trigger": bool(trace.get("jepa_trigger")) if "jepa_trigger" in trace else None,
            "grounded_jepa_mode": bool(trace.get("jepa_mode")) if "jepa_mode" in trace else None,
        }
    )
    return _fit_prompt_for_model(effective_prompt, model_name), meta


def _normalize_tokens(text: str) -> list[str]:
    if not text:
        return []
    return re.findall(r"[\w\-]+", text.lower(), flags=re.UNICODE)


def _compare_prefix(draft_text: str, target_text: str, window: int = 48) -> tuple[float, float, int]:
    dt = _normalize_tokens(draft_text)
    tt = _normalize_tokens(target_text)
    n = min(len(dt), len(tt), max(1, window))
    if n <= 0:
        return 0.0, 1.0, 0
    matches = 0
    for i in range(n):
        if dt[i] == tt[i]:
            matches += 1
    acc = matches / n
    return round(acc, 4), round(1.0 - acc, 4), n


async def _stream_collect(
    *,
    model: str,
    source: str | None,
    prompt: str,
    system_prompt: str,
    max_output_tokens: int,
    stream_timeout_sec: float,
    per_run_timeout_sec: float,
) -> dict[str, Any]:
    provider = ProviderRegistry.detect_provider(model, source=source)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    t0 = time.perf_counter()
    ttft: float | None = None
    first_chunk: float | None = None
    tokens_out = 0
    out = ""
    pending = ""
    timed_out = False
    error: str | None = None

    think: bool | None = None
    if source == "ollama":
        think = False

    try:
        async for token in call_model_v2_stream(
            messages=messages,
            model=model,
            provider=provider,
            source=source,
            max_tokens=max(32, int(max_output_tokens)),
            stream_timeout=max(5.0, float(stream_timeout_sec)),
            temperature=0.4,
            think=think,
        ):
            now = time.perf_counter()
            if (now - t0) > max(2.0, float(per_run_timeout_sec)):
                timed_out = True
                break
            if token:
                tokens_out += 1
                out += token
                if ttft is None:
                    ttft = (now - t0) * 1000.0
                pending = f"{pending}{token}"
                ready, pending = extract_ready_chunks(pending, min_words=8, min_chars=48, max_words=16)
                if ready and first_chunk is None:
                    first_chunk = (now - t0) * 1000.0
    except Exception as e:
        error = f"{type(e).__name__}: {e}"

    if first_chunk is None and out.strip():
        first_chunk = (time.perf_counter() - t0) * 1000.0

    if timed_out and not error:
        error = f"TimeoutError: per-run timeout {per_run_timeout_sec}s"

    return {
        "ttft_ms": round(ttft, 2) if ttft is not None else None,
        "first_chunk_ms": round(first_chunk, 2) if first_chunk is not None else None,
        "tokens_out": tokens_out,
        "text": out.strip(),
        "error": error,
        "timed_out": timed_out,
    }


async def _run_one(
    *,
    pair_name: str,
    prompt_id: str,
    run_index: int,
    prompt: str,
    draft_model: str,
    target_model: str,
    draft_source: str | None,
    target_source: str | None,
    max_output_tokens: int,
    stream_timeout_sec: float,
    per_run_timeout_sec: float,
    grounded_context: bool,
    grounded_limit: int,
    force_jepa: bool,
) -> SpecRow:
    err: str | None = None

    effective_prompt, grounded_meta = await _build_grounded_prompt(
        user_prompt=prompt,
        model_name=target_model,
        pair_name=pair_name,
        enable_grounded=grounded_context,
        grounded_limit=grounded_limit,
        force_jepa=force_jepa,
    )

    first_turn, second_turn = _parse_interrupt_prompt(effective_prompt)
    request_prompt = second_turn if (prompt_id == "interrupt_1" and second_turn) else effective_prompt

    system_prompt = (
        "You are a voice assistant. Reply in Russian. Max 1-2 short sentences, no lists. "
        "Use only provided context. If missing, say it explicitly."
    )

    draft_task = asyncio.create_task(
        _stream_collect(
            model=draft_model,
            source=draft_source,
            prompt=request_prompt,
            system_prompt=system_prompt,
            max_output_tokens=max(48, int(max_output_tokens // 2)),
            stream_timeout_sec=stream_timeout_sec,
            per_run_timeout_sec=per_run_timeout_sec,
        )
    )
    target_task = asyncio.create_task(
        _stream_collect(
            model=target_model,
            source=target_source,
            prompt=request_prompt,
            system_prompt=system_prompt,
            max_output_tokens=max_output_tokens,
            stream_timeout_sec=stream_timeout_sec,
            per_run_timeout_sec=per_run_timeout_sec,
        )
    )

    draft_res, target_res = await asyncio.gather(draft_task, target_task)

    acceptance_rate, correction_rate, compared_tokens = _compare_prefix(
        draft_res.get("text", ""),
        target_res.get("text", ""),
        window=48,
    )

    draft_ttft = draft_res.get("ttft_ms")
    target_ttft = target_res.get("ttft_ms")
    ttft_gain = None
    if draft_ttft is not None and target_ttft is not None:
        ttft_gain = round(target_ttft - draft_ttft, 2)

    target_text = target_res.get("text", "")
    success = bool(target_text and not target_res.get("error"))
    if draft_res.get("error") or target_res.get("error"):
        err = f"draft={draft_res.get('error')}; target={target_res.get('error')}"

    return SpecRow(
        pair_name=pair_name,
        prompt_id=prompt_id,
        run_index=run_index,
        draft_model=draft_model,
        target_model=target_model,
        draft_source=draft_source,
        target_source=target_source,
        success=success,
        error=err,
        draft_ttft_ms=draft_ttft,
        target_ttft_ms=target_ttft,
        draft_first_chunk_ms=draft_res.get("first_chunk_ms"),
        target_first_chunk_ms=target_res.get("first_chunk_ms"),
        ttft_gain_ms=ttft_gain,
        target_reaction_text_ms=target_ttft,
        target_reaction_audio_ready_ms=target_res.get("first_chunk_ms"),
        acceptance_rate=acceptance_rate,
        correction_rate=correction_rate,
        compared_tokens=compared_tokens,
        draft_tokens_out=int(draft_res.get("tokens_out") or 0),
        target_tokens_out=int(target_res.get("tokens_out") or 0),
        target_response_chars=len(target_text),
        grounded_context=bool(grounded_meta.get("grounded_context")),
        grounded_files=int(grounded_meta.get("grounded_files") or 0),
        grounded_packing_path=grounded_meta.get("grounded_packing_path"),
        grounded_jepa_trigger=grounded_meta.get("grounded_jepa_trigger"),
        grounded_jepa_mode=grounded_meta.get("grounded_jepa_mode"),
        target_preview=(target_text or "")[:280],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _build_summary(rows: list[SpecRow]) -> dict[str, Any]:
    ok = [r for r in rows if r.success]

    def p50(vals: list[float | None]) -> float | None:
        clean = [float(v) for v in vals if v is not None]
        if not clean:
            return None
        return round(statistics.median(clean), 2)

    return {
        "runs": len(rows),
        "success_runs": len(ok),
        "success_rate": round(len(ok) / len(rows), 4) if rows else 0.0,
        "draft_ttft_p50_ms": p50([r.draft_ttft_ms for r in ok]),
        "target_ttft_p50_ms": p50([r.target_ttft_ms for r in ok]),
        "target_audio_ready_p50_ms": p50([r.target_reaction_audio_ready_ms for r in ok]),
        "ttft_gain_p50_ms": p50([r.ttft_gain_ms for r in ok]),
        "acceptance_rate_mean": round(sum(r.acceptance_rate for r in ok) / len(ok), 4) if ok else 0.0,
        "correction_rate_mean": round(sum(r.correction_rate for r in ok) / len(ok), 4) if ok else 0.0,
        "compared_tokens_mean": round(sum(r.compared_tokens for r in ok) / len(ok), 2) if ok else 0.0,
    }


def _write_csv(path: Path, rows: list[SpecRow]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))


def _write_md(path: Path, rows: list[SpecRow], summary: dict[str, Any], pair_name: str) -> None:
    lines = [
        f"# Phase 157.3.1 Speculative Pair Benchmark ({pair_name})",
        "",
        "## Summary",
        "",
        f"- Runs: {summary.get('runs')}",
        f"- Success runs: {summary.get('success_runs')}",
        f"- Success rate: {summary.get('success_rate')}",
        f"- Draft TTFT p50: {summary.get('draft_ttft_p50_ms')} ms",
        f"- Target TTFT p50: {summary.get('target_ttft_p50_ms')} ms",
        f"- Target audio-ready p50: {summary.get('target_audio_ready_p50_ms')} ms",
        f"- TTFT gain p50 (target-draft): {summary.get('ttft_gain_p50_ms')} ms",
        f"- Acceptance mean: {summary.get('acceptance_rate_mean')}",
        f"- Correction mean: {summary.get('correction_rate_mean')}",
        "",
        "## Rows",
        "",
        "| prompt_id | run | success | draft_ttft | target_ttft | target_audio_ready | acceptance | correction | compared_tokens |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| `{r.prompt_id}` | {r.run_index} | `{r.success}` | {r.draft_ttft_ms} | {r.target_ttft_ms} | "
            f"{r.target_reaction_audio_ready_ms} | {r.acceptance_rate} | {r.correction_rate} | {r.compared_tokens} |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")


async def _amain(args: argparse.Namespace) -> int:
    pair_name = args.pair_name or f"{args.draft_model}__{args.target_model}"
    rows: list[SpecRow] = []

    for prompt_id, prompt in _default_prompts():
        for run_index in range(1, max(1, args.runs_per_prompt) + 1):
            row = await _run_one(
                pair_name=pair_name,
                prompt_id=prompt_id,
                run_index=run_index,
                prompt=prompt,
                draft_model=args.draft_model,
                target_model=args.target_model,
                draft_source=args.draft_source,
                target_source=args.target_source,
                max_output_tokens=args.max_output_tokens,
                stream_timeout_sec=args.stream_timeout_sec,
                per_run_timeout_sec=args.per_run_timeout_sec,
                grounded_context=args.grounded_context,
                grounded_limit=args.grounded_limit,
                force_jepa=args.force_jepa,
            )
            rows.append(row)

    summary = _build_summary(rows)

    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = BENCH_DIR / f"phase157_speculative_pair_{ts}"

    out_json = prefix.with_suffix(".json")
    out_csv = prefix.with_suffix(".csv")
    out_md = prefix.with_suffix(".md")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pair_name": pair_name,
        "draft_model": args.draft_model,
        "target_model": args.target_model,
        "rows": [asdict(r) for r in rows],
        "summary": summary,
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(out_csv, rows)
    _write_md(out_md, rows, summary, pair_name)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"json={out_json}")
    print(f"csv={out_csv}")
    print(f"md={out_md}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 157.3.1 speculative pair benchmark")
    parser.add_argument("--pair-name", default="")
    parser.add_argument("--draft-model", default="gemma3:1b")
    parser.add_argument("--target-model", default="llama3.2:3b")
    parser.add_argument("--draft-source", default="ollama")
    parser.add_argument("--target-source", default="ollama")
    parser.add_argument("--runs-per-prompt", type=int, default=1)
    parser.add_argument("--per-run-timeout-sec", type=float, default=45.0)
    parser.add_argument("--stream-timeout-sec", type=float, default=35.0)
    parser.add_argument("--max-output-tokens", type=int, default=96)
    parser.add_argument("--grounded-context", action="store_true", default=False)
    parser.add_argument("--grounded-limit", type=int, default=10)
    parser.add_argument("--force-jepa", action="store_true", default=False)
    args = parser.parse_args()

    return asyncio.run(_amain(args))


if __name__ == "__main__":
    raise SystemExit(main())
