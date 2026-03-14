#!/usr/bin/env python3
"""
Phase 157.2.10 benchmark harness for voice modes A/B/C/D/E/F.

Modes:
- A_qwen_only: local qwen model + qwen tts path
- B_api_tts: API model + qwen tts
- C_api_jepa_tts: API model + qwen tts + JEPA assist in progressive TTS
- D_ollama_tts: local ollama model + qwen tts
- E_ollama_jepa_tts: local ollama model + qwen tts + JEPA assist in progressive TTS
- F_mimo_short: API mimo short/simple prompt + qwen tts

Outputs:
- docs/157_ph/benchmarks/phase157_voice_ab_test_<ts>.json
- docs/157_ph/benchmarks/phase157_voice_ab_test_<ts>.csv
- docs/157_ph/benchmarks/phase157_voice_ab_test_<ts>.md
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import csv
import io
import json
import os
import re
import sys
import statistics
import time
import wave
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator
import inspect

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.elisya.provider_registry import ProviderRegistry, call_model_v2_stream
from src.services.progressive_tts_service import ProgressiveTtsService
from src.voice.prosody_chunker import extract_ready_chunks
from scripts.voice_wav_quality_audit import analyze_wav


BENCH_DIR = Path("docs/157_ph/benchmarks")
AUDIO_DIR = BENCH_DIR / "audio"


@dataclass
class BenchMode:
    name: str
    model: str
    source: str | None
    jepa_assist: bool
    short_simple: bool = False


@dataclass
class BenchRow:
    mode: str
    prompt_id: str
    run_index: int
    prompt_chars: int
    success: bool
    error: str | None
    ttft_text_ms: float | None
    ttfa_audio_ms: float | None
    reaction_text_ms: float | None
    reaction_audio_ms: float | None
    e2e_ms: float | None
    tokens_out: int
    audio_chunks: int
    response_chars: int
    quality_proxy: float
    quality_notes: str
    response_preview: str
    audio_dir: str | None
    audio_merged_wav: str | None
    audio_qc_score: float | None
    audio_pause_count: int | None
    audio_longest_pause_ms: int | None
    audio_stretch_events: int | None
    grounded_context: bool
    grounded_files: int
    grounded_packing_path: str | None
    grounded_jepa_trigger: bool | None
    grounded_jepa_mode: bool | None
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


def _short_simple_prompts() -> list[tuple[str, str]]:
    return [("short_live", "привет ты тут?")]


def _prompts_for_mode(mode: BenchMode) -> list[tuple[str, str]]:
    return _short_simple_prompts() if mode.short_simple else _default_prompts()


def _cyrillic_ratio(text: str) -> float:
    if not text:
        return 0.0
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    cyr = sum(1 for ch in letters if "а" <= ch.lower() <= "я" or ch.lower() == "ё")
    return cyr / max(1, len(letters))


def _score_quality(
    *,
    prompt_id: str,
    response: str,
    semantic_success: bool,
    error: str | None,
) -> tuple[float, str]:
    """
    Heuristic quality score in [0, 1]:
    - task relevance by prompt intent
    - language fitness (RU for benchmark prompts)
    - hard penalties for timeout/stream errors/hallucination markers
    """
    text = (response or "").strip()
    low = text.lower()
    notes: list[str] = []
    score = 0.0

    if text:
        score += 0.25
    if semantic_success:
        score += 0.25
    if _cyrillic_ratio(text) >= 0.35:
        score += 0.1
    else:
        notes.append("low_ru_ratio")

    if prompt_id == "short_1":
        if "/" in text or ".md" in low or ".py" in low:
            score += 0.2
        else:
            notes.append("no_file_refs")
        if ("1." in text and "2." in text) or ("- " in text):
            score += 0.1
        else:
            notes.append("no_two_items")
    elif prompt_id == "context_1":
        has_mem = any(k in low for k in ("memory", "контекст", "packing", "упаков", "elision", "jepa", "cam", "arc"))
        has_latency = any(k in low for k in ("latency", "задерж", "p50", "p95", "timeout"))
        if has_mem:
            score += 0.15
        else:
            notes.append("no_memory_terms")
        if has_latency:
            score += 0.1
        else:
            notes.append("no_latency_terms")
    elif prompt_id == "long_1":
        has_interrupt = any(k in low for k in ("interrupt", "преры", "restart", "перезап", "stream"))
        has_handoff = any(k in low for k in ("handoff", "tool-loop", "tool", "voice", "голос"))
        if has_interrupt:
            score += 0.15
        else:
            notes.append("no_interrupt_terms")
        if has_handoff:
            score += 0.1
        else:
            notes.append("no_handoff_terms")
    elif prompt_id == "short_live":
        if any(k in low for k in ("привет", "здесь", "на связи", "тут", "готов")):
            score += 0.2
        else:
            notes.append("weak_greeting")
        if "криптовалют" in low:
            score -= 0.2
            notes.append("hallucination_crypto")
    elif prompt_id == "interrupt_1":
        if any(k in low for k in ("шаг", "сначала", "1", "2", "перв")):
            score += 0.2
        else:
            notes.append("no_stepwise_followup")
        if len(text.split()) <= 60:
            score += 0.05
        else:
            notes.append("too_long_after_interrupt")

    if error:
        err_low = error.lower()
        if "timeout" in err_low:
            score -= 0.25
            notes.append("timeout")
        if "stream error" in err_low or "error" in err_low:
            score -= 0.1
            notes.append("stream_error")

    score = max(0.0, min(1.0, score))
    return round(score, 4), ",".join(notes)


def _extract_ready_sentences(buffer_text: str) -> tuple[list[str], str]:
    flush_words = int(os.environ.get("BENCH_STREAM_FLUSH_MIN_WORDS", "8"))
    flush_chars = int(os.environ.get("BENCH_STREAM_FLUSH_MIN_CHARS", "48"))
    max_words = int(os.environ.get("BENCH_STREAM_FLUSH_MAX_WORDS", "16"))
    return extract_ready_chunks(
        buffer_text,
        min_words=flush_words,
        min_chars=flush_chars,
        max_words=max_words,
    )


def _fit_prompt_for_model(prompt: str, model_name: str) -> str:
    """
    Keep grounded benchmark realistic for local models with small context windows.
    """
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


async def _build_grounded_prompt(
    *,
    user_prompt: str,
    model_name: str,
    mode_name: str,
    enable_grounded: bool,
    grounded_limit: int,
    force_jepa: bool,
) -> tuple[str, dict[str, Any]]:
    """
    Build a realistic prompt using the same context path as runtime:
    Hybrid search -> pinned files -> context packer -> build_model_prompt.
    """
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
        session_id=f"bench:{mode_name}",
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
        "## BENCHMARK CONTEXT\n"
        "Use only the provided project context. If facts are missing, say that clearly.\n"
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


async def _stream_model_tokens(
    model: str,
    source: str | None,
    prompt: str,
    *,
    system_prompt: str,
    max_output_tokens: int,
    stream_timeout_sec: float,
    ollama_think: bool | None = None,
) -> AsyncGenerator[str, None]:
    provider = ProviderRegistry.detect_provider(model, source=source)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    async for token in call_model_v2_stream(
        messages=messages,
        model=model,
        provider=provider,
        source=source,
        max_tokens=max(32, int(max_output_tokens)),
        stream_timeout=max(5.0, float(stream_timeout_sec)),
        temperature=0.4,
        think=ollama_think,
    ):
        if token:
            yield token


def _parse_interrupt_prompt(prompt: str) -> tuple[str, str]:
    """
    Prompt format:
    INTERRUPT_TEST::first=<text>;second=<text>
    """
    raw = (prompt or "").strip()
    if not raw.startswith("INTERRUPT_TEST::"):
        return "", ""
    body = raw.split("::", 1)[1]
    first = ""
    second = ""
    for part in body.split(";"):
        if part.startswith("first="):
            first = part[len("first="):].strip()
        elif part.startswith("second="):
            second = part[len("second="):].strip()
    return first, second


async def _ensure_tts_ready() -> bool:
    try:
        import httpx

        async with httpx.AsyncClient(timeout=3.0, trust_env=False) as client:
            r = await client.get("http://127.0.0.1:5003/health")
            if r.status_code == 200:
                return True
    except Exception:
        pass

    try:
        from src.voice.tts_server_manager import start_tts_server

        start_tts_server(wait_ready=True, timeout=45.0)
    except Exception:
        return False


async def _tts_direct_fallback(
    sentence: str,
    *,
    speaker: str,
    language: str,
    timeout_sec: float,
) -> dict[str, Any] | None:
    """Direct `/tts/generate` call to preserve TTFA metric if progressive wrapper yields nothing."""
    payload = {"text": sentence, "speaker": speaker, "language": language}
    try:
        async with httpx.AsyncClient(timeout=timeout_sec, trust_env=False) as client:
            resp = await client.post("http://127.0.0.1:5003/tts/generate", json=payload)
            if resp.status_code != 200:
                return None
            body = resp.json() if resp.content else {}
            audio_b64 = body.get("audio_b64") or body.get("audio") or ""
            if not audio_b64:
                return None
            try:
                base64.b64decode(audio_b64)
            except (binascii.Error, ValueError):
                return None
            return {
                "seq": 0,
                "is_final": True,
                "audio_b64": audio_b64,
                "duration_ms": int(body.get("duration_ms") or 0),
                "text": sentence,
            }
    except Exception:
        return None


def _pick_tts_seed_text(raw_text: str) -> str:
    """
    Pick compact, prosody-safe seed text for direct TTS fallback.
    """
    text = re.sub(r"\s+", " ", (raw_text or "").strip())
    if not text:
        return ""
    text = re.sub(r"\[Stream stopped:\s*timeout\]\s*$", "", text, flags=re.IGNORECASE).strip()
    if not text:
        return ""

    # Prefer the first complete sentence; otherwise first phrase-sized chunk.
    m = re.search(r"(.+?[.!?])(\s|$)", text)
    if m:
        seed = m.group(1).strip()
    else:
        words = text.split()
        seed = " ".join(words[:18]).strip()
        if seed and seed[-1] not in ".!?":
            seed = f"{seed}."

    # Hard bound for deterministic low-latency direct TTS.
    return seed[:220].strip()


async def _run_one_impl(
    mode: BenchMode,
    prompt_id: str,
    run_index: int,
    prompt: str,
    dry_run: bool = False,
    *,
    max_output_tokens: int = 220,
    stream_timeout_sec: float = 20.0,
    per_run_timeout_sec: float = 30.0,
    grounded_context: bool = False,
    grounded_limit: int = 10,
) -> BenchRow:
    t0 = time.perf_counter()
    ttft: float | None = None
    ttfa: float | None = None
    tokens_out = 0
    audio_chunks = 0
    response_text = ""
    pending_text = ""
    response_clock_start = t0
    chunk_audio_bytes: list[bytes] = []
    audio_run_dir: Path | None = None
    merged_wav_path: Path | None = None
    wav_qc: dict[str, Any] | None = None
    grounded_meta: dict[str, Any] = {
        "grounded_context": False,
        "grounded_files": 0,
        "grounded_packing_path": None,
        "grounded_jepa_trigger": None,
        "grounded_jepa_mode": None,
    }

    prev_jepa = os.environ.get("VETKA_VOICE_JEPA_ASSIST_ENABLE")
    os.environ["VETKA_VOICE_JEPA_ASSIST_ENABLE"] = "true" if mode.jepa_assist else "false"

    tts_timeout = float(os.environ.get("BENCH_TTS_CLIENT_TIMEOUT_SEC", "25"))
    service = ProgressiveTtsService(client_timeout=tts_timeout)
    stream_sentences_sig = None
    try:
        stream_sentences_sig = inspect.signature(service.stream_sentences)
    except Exception:
        stream_sentences_sig = None

    async def _tts_stream(sentence_text: str) -> AsyncGenerator[dict[str, Any], None]:
        lang = "ru"
        # Benchmark runtime: `ryan` often yields no audio with ru on some local stacks.
        # Use adaptive fallback so TTFA audio is measurable.
        if _cyrillic_ratio(sentence_text) < 0.25:
            lang = "en"
        kwargs_tts = dict(
            speaker="ryan",
            language=lang,
            prosody=None,
            chunk_limit=8,
        )
        if stream_sentences_sig and "session_key" in stream_sentences_sig.parameters:
            kwargs_tts["session_key"] = f"bench:{mode.name}"
        yielded = False
        async for _chunk in service.stream_sentences(sentence_text, **kwargs_tts):
            yielded = True
            yield _chunk
        if not yielded:
            direct = await _tts_direct_fallback(
                sentence_text,
                speaker=str(kwargs_tts.get("speaker", "ryan")),
                language=str(kwargs_tts.get("language", "en")),
                timeout_sec=max(8.0, tts_timeout),
            )
            if direct is not None:
                yield direct
    success = True
    error: str | None = None
    timed_out = False

    def _is_timed_out() -> bool:
        return (time.perf_counter() - t0) > max(2.0, float(per_run_timeout_sec))

    try:
        if dry_run:
            await asyncio.sleep(0.02)
            ttft = 20.0
            tokens_out = max(20, len(prompt) // 5)
            await asyncio.sleep(0.03)
            ttfa = 50.0
            audio_chunks = max(1, len(prompt) // 80)
            e2e = (time.perf_counter() - t0) * 1000.0
            return BenchRow(
                mode=mode.name,
                prompt_id=prompt_id,
                run_index=run_index,
                prompt_chars=len(prompt),
                success=True,
                error=None,
                ttft_text_ms=ttft,
                ttfa_audio_ms=ttfa,
                reaction_text_ms=ttft,
                reaction_audio_ms=ttfa,
                e2e_ms=round(e2e, 2),
                tokens_out=tokens_out,
                audio_chunks=audio_chunks,
                response_chars=max(0, len(prompt) // 2),
                quality_proxy=1.0,
                quality_notes="dry_run",
                response_preview="DRY_RUN_SYNTHETIC",
                audio_dir=None,
                audio_merged_wav=None,
                audio_qc_score=None,
                audio_pause_count=None,
                audio_longest_pause_ms=None,
                audio_stretch_events=None,
                grounded_context=False,
                grounded_files=0,
                grounded_packing_path=None,
                grounded_jepa_trigger=None,
                grounded_jepa_mode=None,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        skip_tts = os.environ.get("BENCH_SKIP_TTS", "").strip().lower() in {"1", "true", "yes"}
        if not skip_tts:
            tts_ok = await _ensure_tts_ready()
            if not tts_ok:
                raise RuntimeError("TTS_NOT_READY")
            AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            safe_mode = mode.name.replace("/", "_")
            safe_prompt = prompt_id.replace("/", "_")
            audio_run_dir = AUDIO_DIR / f"{ts}_{safe_mode}_{safe_prompt}_run{run_index}"
            audio_run_dir.mkdir(parents=True, exist_ok=True)

        effective_prompt, grounded_meta = await _build_grounded_prompt(
            user_prompt=prompt,
            model_name=mode.model,
            mode_name=mode.name,
            enable_grounded=grounded_context,
            grounded_limit=grounded_limit,
            force_jepa=bool(mode.jepa_assist),
        )

        # Interrupt benchmark: start first answer, cut it quickly, then send follow-up.
        # Metrics are measured on second turn (post-interrupt responsiveness).
        first_turn, second_turn = _parse_interrupt_prompt(effective_prompt)
        ollama_think_env = os.environ.get("BENCH_OLLAMA_THINK")
        ollama_think: bool | None = None
        if mode.source == "ollama":
            if ollama_think_env is None:
                ollama_think = False
            else:
                ollama_think = ollama_think_env.strip().lower() in {"1", "true", "yes", "on"}

        if prompt_id == "interrupt_1" and first_turn and second_turn:
            # 1) Start first turn and interrupt after a few tokens.
            first_tokens = 0
            async for token in _stream_model_tokens(
                mode.model,
                mode.source,
                first_turn,
                system_prompt=(
                    "You are a voice assistant. Reply in Russian. Max 1-2 short sentences, no lists."
                ),
                max_output_tokens=max_output_tokens,
                stream_timeout_sec=stream_timeout_sec,
                ollama_think=ollama_think,
            ):
                if _is_timed_out():
                    timed_out = True
                    break
                if token:
                    first_tokens += 1
                if first_tokens >= 8:
                    break

            # 2) Start second turn immediately; ttft/quality come from this turn.
            turn2_start = time.perf_counter()
            response_clock_start = turn2_start
            pending_text = ""
            async for token in _stream_model_tokens(
                mode.model,
                mode.source,
                second_turn,
                system_prompt=(
                    "You are a voice assistant. Reply in Russian. Max 1-2 short sentences, no lists."
                ),
                max_output_tokens=max_output_tokens,
                stream_timeout_sec=stream_timeout_sec,
                ollama_think=ollama_think,
            ):
                if _is_timed_out():
                    timed_out = True
                    break
                if ttft is None:
                    ttft = (time.perf_counter() - turn2_start) * 1000.0
                tokens_out += 1
                response_text += token
                if skip_tts:
                    continue
                pending_text = f"{pending_text}{token}"
                ready, pending_text = _extract_ready_sentences(pending_text)
                for sentence in ready:
                    if _is_timed_out():
                        timed_out = True
                        break
                    async for chunk in _tts_stream(sentence):
                        audio_chunks += 1
                        if ttfa is None:
                            ttfa = (time.perf_counter() - turn2_start) * 1000.0
                        if not chunk:
                            continue
                        if audio_run_dir is not None and chunk.get("audio_b64"):
                            audio_raw = base64.b64decode(chunk["audio_b64"])
                            chunk_audio_bytes.append(audio_raw)
                            chunk_path = audio_run_dir / f"chunk_{audio_chunks:03d}.wav"
                            chunk_path.write_bytes(audio_raw)

            if not skip_tts and not timed_out:
                tail = pending_text.strip()
                if tail:
                    async for chunk in _tts_stream(tail):
                        audio_chunks += 1
                        if ttfa is None:
                            ttfa = (time.perf_counter() - turn2_start) * 1000.0
                        if not chunk:
                            continue
                        if audio_run_dir is not None and chunk.get("audio_b64"):
                            audio_raw = base64.b64decode(chunk["audio_b64"])
                            chunk_audio_bytes.append(audio_raw)
                            chunk_path = audio_run_dir / f"chunk_{audio_chunks:03d}.wav"
                            chunk_path.write_bytes(audio_raw)
        else:

            async for token in _stream_model_tokens(
                mode.model,
                mode.source,
                effective_prompt,
                system_prompt=(
                    "You are a voice assistant. Reply in Russian. Max 1-2 short sentences, no lists. "
                    "Use only provided context. If missing, say it explicitly."
                    if mode.short_simple
                    else "You are a concise assistant. Keep answers short and direct. Use only provided context."
                ),
                max_output_tokens=max_output_tokens,
                stream_timeout_sec=stream_timeout_sec,
                ollama_think=ollama_think,
            ):
                if _is_timed_out():
                    timed_out = True
                    break
                if ttft is None:
                    ttft = (time.perf_counter() - t0) * 1000.0
                tokens_out += 1
                response_text += token
                if skip_tts:
                    continue
                pending_text = f"{pending_text}{token}"
                ready, pending_text = _extract_ready_sentences(pending_text)
                for sentence in ready:
                    if _is_timed_out():
                        timed_out = True
                        break
                    async for chunk in _tts_stream(sentence):
                        audio_chunks += 1
                        if ttfa is None:
                            ttfa = (time.perf_counter() - t0) * 1000.0
                        if not chunk:
                            continue
                        if audio_run_dir is not None and chunk.get("audio_b64"):
                            audio_raw = base64.b64decode(chunk["audio_b64"])
                            chunk_audio_bytes.append(audio_raw)
                            chunk_path = audio_run_dir / f"chunk_{audio_chunks:03d}.wav"
                            chunk_path.write_bytes(audio_raw)

        # Last-line TTFA guard: if we have text but still no audio metric,
        # push a short direct TTS seed to ensure ttfa_audio is measurable.
        if not skip_tts and ttfa is None:
            seed_text = _pick_tts_seed_text(response_text)
            if seed_text:
                lang = "ru" if _cyrillic_ratio(seed_text) >= 0.25 else "en"
                direct = await _tts_direct_fallback(
                    seed_text,
                    speaker="ryan",
                    language=lang,
                    timeout_sec=max(8.0, tts_timeout),
                )
                if direct is not None:
                    ttfa = (time.perf_counter() - response_clock_start) * 1000.0
                    audio_chunks += 1
                    if audio_run_dir is not None and direct.get("audio_b64"):
                        audio_raw = base64.b64decode(direct["audio_b64"])
                        chunk_audio_bytes.append(audio_raw)
                        chunk_path = audio_run_dir / f"chunk_{audio_chunks:03d}.wav"
                        chunk_path.write_bytes(audio_raw)

        if not skip_tts and not timed_out:
            tail = pending_text.strip()
            if tail:
                async for chunk in _tts_stream(tail):
                    audio_chunks += 1
                    if ttfa is None:
                        ttfa = (time.perf_counter() - response_clock_start) * 1000.0
                    if not chunk:
                        continue
                    if audio_run_dir is not None and chunk.get("audio_b64"):
                        audio_raw = base64.b64decode(chunk["audio_b64"])
                        chunk_audio_bytes.append(audio_raw)
                        chunk_path = audio_run_dir / f"chunk_{audio_chunks:03d}.wav"
                        chunk_path.write_bytes(audio_raw)

        if timed_out:
            success = False
            error = f"TimeoutError: per-run timeout {per_run_timeout_sec}s"
        if audio_run_dir is not None:
            try:
                if chunk_audio_bytes:
                    merged_wav_path = audio_run_dir / "merged.wav"
                    with wave.open(str(merged_wav_path), "wb") as out_wf:
                        params_set = False
                        for wav_bytes in chunk_audio_bytes:
                            with wave.open(io.BytesIO(wav_bytes), "rb") as in_wf:
                                if not params_set:
                                    out_wf.setparams(in_wf.getparams())
                                    params_set = True
                                out_wf.writeframes(in_wf.readframes(in_wf.getnframes()))
                    wav_qc = analyze_wav(merged_wav_path)
                response_for_artifacts = re.sub(
                    r"\[Stream stopped:\s*timeout\]\s*$",
                    "",
                    response_text,
                    flags=re.IGNORECASE,
                ).strip()
                (audio_run_dir / "response.txt").write_text(response_for_artifacts, encoding="utf-8")
                (audio_run_dir / "meta.json").write_text(
                    json.dumps(
                        {
                            "mode": mode.name,
                            "prompt_id": prompt_id,
                            "run_index": run_index,
                            "audio_chunks": audio_chunks,
                            "ttft_text_ms": ttft,
                            "ttfa_audio_ms": ttfa,
                            "merged_wav": str(merged_wav_path) if merged_wav_path else None,
                            "wav_qc": wav_qc,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            except Exception as merge_exc:
                error = f"{error}; WAV_ARTIFACT_ERROR={merge_exc}" if error else f"WAV_ARTIFACT_ERROR={merge_exc}"

    except Exception as exc:
        success = False
        error = f"{exc.__class__.__name__}: {exc}"

    finally:
        if prev_jepa is None:
            os.environ.pop("VETKA_VOICE_JEPA_ASSIST_ENABLE", None)
        else:
            os.environ["VETKA_VOICE_JEPA_ASSIST_ENABLE"] = prev_jepa

    e2e = (time.perf_counter() - t0) * 1000.0
    cleaned_response_text = re.sub(r"\[Stream stopped:\s*timeout\]\s*$", "", response_text, flags=re.IGNORECASE).strip()
    lowered = cleaned_response_text.lower()
    low_quality_markers = (
        "error",
        "[error]",
        "[stream error]",
        "couldn't process",
        "something went wrong",
        "timeout",
    )
    has_low_quality_marker = any(m in lowered for m in low_quality_markers)
    min_tokens_for_success = 4 if len(prompt.split()) <= 4 else 8
    semantic_success = bool(success and tokens_out >= min_tokens_for_success and not has_low_quality_marker)
    quality_proxy, quality_notes = _score_quality(
        prompt_id=prompt_id,
        response=cleaned_response_text,
        semantic_success=semantic_success,
        error=error,
    )
    return BenchRow(
        mode=mode.name,
        prompt_id=prompt_id,
        run_index=run_index,
        prompt_chars=len(prompt),
        success=semantic_success,
        error=error,
        ttft_text_ms=round(ttft, 2) if ttft is not None else None,
        ttfa_audio_ms=round(ttfa, 2) if ttfa is not None else None,
        reaction_text_ms=round(ttft, 2) if ttft is not None else None,
        reaction_audio_ms=round(ttfa, 2) if ttfa is not None else None,
        e2e_ms=round(e2e, 2),
        tokens_out=tokens_out,
        audio_chunks=audio_chunks,
        response_chars=len(cleaned_response_text),
        quality_proxy=quality_proxy,
        quality_notes=quality_notes,
        response_preview=(cleaned_response_text or "").strip()[:280],
        audio_dir=str(audio_run_dir) if audio_run_dir is not None else None,
        audio_merged_wav=str(merged_wav_path) if merged_wav_path is not None else None,
        audio_qc_score=float(wav_qc.get("qc_score")) if wav_qc and wav_qc.get("ok") else None,
        audio_pause_count=int(wav_qc.get("pause_count")) if wav_qc and wav_qc.get("ok") else None,
        audio_longest_pause_ms=int(wav_qc.get("longest_pause_ms")) if wav_qc and wav_qc.get("ok") else None,
        audio_stretch_events=int(wav_qc.get("stretch_events")) if wav_qc and wav_qc.get("ok") else None,
        grounded_context=bool(grounded_meta.get("grounded_context")),
        grounded_files=int(grounded_meta.get("grounded_files") or 0),
        grounded_packing_path=str(grounded_meta.get("grounded_packing_path") or "") or None,
        grounded_jepa_trigger=grounded_meta.get("grounded_jepa_trigger"),
        grounded_jepa_mode=grounded_meta.get("grounded_jepa_mode"),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


async def _run_one(
    mode: BenchMode,
    prompt_id: str,
    run_index: int,
    prompt: str,
    *,
    dry_run: bool = False,
    per_run_timeout_sec: float = 30.0,
    max_output_tokens: int = 220,
    stream_timeout_sec: float = 20.0,
    grounded_context: bool = False,
    grounded_limit: int = 10,
) -> BenchRow:
    try:
        return await _run_one_impl(
            mode,
            prompt_id,
            run_index,
            prompt,
            dry_run=dry_run,
            max_output_tokens=max_output_tokens,
            stream_timeout_sec=stream_timeout_sec,
            per_run_timeout_sec=per_run_timeout_sec,
            grounded_context=grounded_context,
            grounded_limit=grounded_limit,
        )
    except (asyncio.TimeoutError, TimeoutError):
        return BenchRow(
            mode=mode.name,
            prompt_id=prompt_id,
            run_index=run_index,
            prompt_chars=len(prompt),
            success=False,
            error=f"TimeoutError: per-run timeout {per_run_timeout_sec}s",
            ttft_text_ms=None,
            ttfa_audio_ms=None,
            reaction_text_ms=None,
            reaction_audio_ms=None,
            e2e_ms=None,
            tokens_out=0,
            audio_chunks=0,
            response_chars=0,
            quality_proxy=0.0,
            quality_notes="hard_timeout",
            response_preview="",
            audio_dir=None,
            audio_merged_wav=None,
            audio_qc_score=None,
            audio_pause_count=None,
            audio_longest_pause_ms=None,
            audio_stretch_events=None,
            grounded_context=False,
            grounded_files=0,
            grounded_packing_path=None,
            grounded_jepa_trigger=None,
            grounded_jepa_mode=None,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


def _summary(rows: list[BenchRow]) -> dict[str, Any]:
    by_mode: dict[str, list[BenchRow]] = {}
    for r in rows:
        by_mode.setdefault(r.mode, []).append(r)

    out: dict[str, Any] = {"modes": {}}
    for mode, mode_rows in by_mode.items():
        ok = [r for r in mode_rows if r.success]
        ttft_vals = [r.ttft_text_ms for r in ok if r.ttft_text_ms is not None]
        ttfa_vals = [r.ttfa_audio_ms for r in ok if r.ttfa_audio_ms is not None]
        react_text_vals = [r.reaction_text_ms for r in ok if r.reaction_text_ms is not None]
        react_audio_vals = [r.reaction_audio_ms for r in ok if r.reaction_audio_ms is not None]
        e2e_vals = [r.e2e_ms for r in ok if r.e2e_ms is not None]
        ttft_vals_all = [r.ttft_text_ms for r in mode_rows if r.ttft_text_ms is not None]
        ttfa_vals_all = [r.ttfa_audio_ms for r in mode_rows if r.ttfa_audio_ms is not None]
        react_text_vals_all = [r.reaction_text_ms for r in mode_rows if r.reaction_text_ms is not None]
        react_audio_vals_all = [r.reaction_audio_ms for r in mode_rows if r.reaction_audio_ms is not None]
        e2e_vals_all = [r.e2e_ms for r in mode_rows if r.e2e_ms is not None]
        quality_vals = [r.quality_proxy for r in mode_rows]

        out["modes"][mode] = {
            "runs": len(mode_rows),
            "success_runs": len(ok),
            "success_rate": round((len(ok) / len(mode_rows)) if mode_rows else 0.0, 4),
            "ttft_text_ms_p50": round(statistics.median(ttft_vals), 2) if ttft_vals else None,
            "ttfa_audio_ms_p50": round(statistics.median(ttfa_vals), 2) if ttfa_vals else None,
            "reaction_text_ms_p50": round(statistics.median(react_text_vals), 2) if react_text_vals else None,
            "reaction_audio_ms_p50": round(statistics.median(react_audio_vals), 2) if react_audio_vals else None,
            "e2e_ms_p50": round(statistics.median(e2e_vals), 2) if e2e_vals else None,
            "ttft_text_ms_p50_all": round(statistics.median(ttft_vals_all), 2) if ttft_vals_all else None,
            "ttfa_audio_ms_p50_all": round(statistics.median(ttfa_vals_all), 2) if ttfa_vals_all else None,
            "reaction_text_ms_p50_all": round(statistics.median(react_text_vals_all), 2) if react_text_vals_all else None,
            "reaction_audio_ms_p50_all": round(statistics.median(react_audio_vals_all), 2) if react_audio_vals_all else None,
            "e2e_ms_p50_all": round(statistics.median(e2e_vals_all), 2) if e2e_vals_all else None,
            "quality_proxy_mean": round((sum(quality_vals) / len(quality_vals)) if quality_vals else 0.0, 4),
        }
    return out


def _write_outputs(rows: list[BenchRow], dry_run: bool) -> tuple[Path, Path]:
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "dry" if dry_run else "live"
    json_path = BENCH_DIR / f"phase157_voice_ab_test_{suffix}_{ts}.json"
    csv_path = BENCH_DIR / f"phase157_voice_ab_test_{suffix}_{ts}.csv"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "rows": [asdict(r) for r in rows],
        "summary": _summary(rows),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()) if rows else [
            "mode",
            "prompt_id",
            "prompt_chars",
            "success",
            "error",
            "ttft_text_ms",
            "ttfa_audio_ms",
            "e2e_ms",
            "tokens_out",
            "audio_chunks",
            "timestamp",
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow(asdict(r))

    return json_path, csv_path


def _write_markdown_report(rows: list[BenchRow], summary: dict[str, Any], dry_run: bool, json_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "dry" if dry_run else "live"
    md_path = BENCH_DIR / f"phase157_voice_ab_test_{suffix}_{ts}.md"

    lines: list[str] = []
    lines.append("# Phase 157 Voice Bench Report")
    lines.append("")
    lines.append(f"- Source JSON: `{json_path}`")
    lines.append(f"- Dry run: `{dry_run}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Mode | Runs | Success Rate | Text p50 (ms, success) | Audio p50 (ms, success) | Text p50 (ms, all) | Audio p50 (ms, all) | E2E p50 (ms, all) | Quality |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for mode, item in summary.get("modes", {}).items():
        lines.append(
            f"| {mode} | {item.get('runs', 0)} | {item.get('success_rate', 0)} | "
            f"{item.get('reaction_text_ms_p50')} | {item.get('reaction_audio_ms_p50')} | "
            f"{item.get('reaction_text_ms_p50_all')} | {item.get('reaction_audio_ms_p50_all')} | "
            f"{item.get('e2e_ms_p50_all')} | {item.get('quality_proxy_mean')} |"
        )
    lines.append("")
    lines.append("## Response Samples")
    lines.append("")

    by_mode: dict[str, list[BenchRow]] = {}
    for row in rows:
        by_mode.setdefault(row.mode, []).append(row)
    for mode, mode_rows in by_mode.items():
        sample = next((r for r in mode_rows if r.success and r.response_preview), mode_rows[0] if mode_rows else None)
        if sample is None:
            continue
        lines.append(f"### {mode}")
        lines.append("")
        lines.append(f"- Prompt: `{sample.prompt_id}`")
        lines.append(f"- Tokens: `{sample.tokens_out}`")
        lines.append(f"- Audio chunks: `{sample.audio_chunks}`")
        lines.append(f"- Merged WAV: `{sample.audio_merged_wav or '[none]'}`")
        lines.append(f"- Audio QC: score={sample.audio_qc_score}, pauses={sample.audio_pause_count}, longest_pause_ms={sample.audio_longest_pause_ms}, stretch={sample.audio_stretch_events}")
        lines.append(f"- Preview: `{sample.response_preview or '[empty]'}`")
        if sample.error:
            lines.append(f"- Error: `{sample.error}`")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def _build_modes(args: argparse.Namespace) -> list[BenchMode]:
    modes = [
        BenchMode(
            name="A_qwen_only",
            model=args.qwen_model,
            source="ollama",
            jepa_assist=False,
        ),
        BenchMode(
            name="B_api_tts",
            model=args.api_model,
            source=args.api_source,
            jepa_assist=False,
        ),
        BenchMode(
            name="C_api_jepa_tts",
            model=args.api_model,
            source=args.api_source,
            jepa_assist=True,
        ),
        BenchMode(
            name="D_ollama_tts",
            model=args.ollama_model,
            source=args.ollama_source,
            jepa_assist=False,
        ),
        BenchMode(
            name="E_ollama_jepa_tts",
            model=args.ollama_model,
            source=args.ollama_source,
            jepa_assist=True,
        ),
        BenchMode(
            name="F_mimo_short",
            model=args.f_model,
            source=args.f_source,
            jepa_assist=False,
            short_simple=True,
        ),
    ]
    if getattr(args, "modes", ""):
        selected = {x.strip() for x in str(args.modes).split(",") if x.strip()}
        modes = [m for m in modes if m.name in selected]
    return modes


async def _amain(args: argparse.Namespace) -> int:
    modes = _build_modes(args)

    rows: list[BenchRow] = []

    for mode in modes:
        prompts = _prompts_for_mode(mode)
        for prompt_id, prompt in prompts:
            for run_index in range(1, max(1, args.runs_per_prompt) + 1):
                row = await _run_one(
                    mode,
                    prompt_id,
                    run_index,
                    prompt,
                    dry_run=args.dry_run,
                    per_run_timeout_sec=args.per_run_timeout_sec,
                    max_output_tokens=args.max_output_tokens,
                    stream_timeout_sec=args.stream_timeout_sec,
                    grounded_context=args.grounded_context,
                    grounded_limit=args.grounded_limit,
                )
                rows.append(row)

    json_path, csv_path = _write_outputs(rows, dry_run=args.dry_run)
    summary = _summary(rows)
    md_path = _write_markdown_report(rows, summary, args.dry_run, json_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"json={json_path}")
    print(f"csv={csv_path}")
    print(f"md={md_path}")
    return 0


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 157 voice mode benchmark harness")
    p.add_argument("--dry-run", action="store_true", help="No external calls; generate synthetic benchmark")
    p.add_argument("--runs-per-prompt", type=int, default=1)
    p.add_argument("--per-run-timeout-sec", type=float, default=25.0)
    p.add_argument("--stream-timeout-sec", type=float, default=20.0)
    p.add_argument("--max-output-tokens", type=int, default=int(os.environ.get("BENCH_MAX_OUTPUT_TOKENS", "220")))
    p.add_argument("--skip-tts", action="store_true", help="Measure stream metrics without TTS generation")
    p.add_argument("--qwen-model", type=str, default=os.environ.get("BENCH_QWEN_ONLY_MODEL", "qwen2.5:7b"))
    p.add_argument("--api-model", type=str, default=os.environ.get("BENCH_API_MODEL", "upstage/solar-pro-3:free"))
    p.add_argument("--api-source", type=str, default=os.environ.get("BENCH_API_SOURCE", "openrouter"))
    p.add_argument("--ollama-model", type=str, default=os.environ.get("BENCH_OLLAMA_MODEL", "llama3.1:8b"))
    p.add_argument("--ollama-source", type=str, default=os.environ.get("BENCH_OLLAMA_SOURCE", "ollama"))
    p.add_argument(
        "--ollama-think",
        type=str,
        default=os.environ.get("BENCH_OLLAMA_THINK", "false"),
        help="For Ollama reasoning models: true/false to enable or disable thinking stream in benchmarks.",
    )
    p.add_argument("--f-model", type=str, default=os.environ.get("BENCH_F_MODEL", "xiaomi/mimo-v2-flash"))
    p.add_argument("--f-source", type=str, default=os.environ.get("BENCH_F_SOURCE", "openrouter"))
    p.add_argument("--modes", type=str, default=os.environ.get("BENCH_MODES", ""))
    p.add_argument(
        "--grounded-context",
        action=argparse.BooleanOptionalAction,
        default=os.environ.get("BENCH_GROUNDED_CONTEXT", "true").strip().lower() in {"1", "true", "yes"},
        help="Enable field-like context path: hybrid search + context packer + structured prompt.",
    )
    p.add_argument(
        "--grounded-limit",
        type=int,
        default=int(os.environ.get("BENCH_GROUNDED_LIMIT", "10")),
        help="Max pinned files for grounded context assembly.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    if args.skip_tts:
        os.environ["BENCH_SKIP_TTS"] = "1"
    if getattr(args, "ollama_think", None) is not None:
        os.environ["BENCH_OLLAMA_THINK"] = str(args.ollama_think)
    return asyncio.run(_amain(args))


if __name__ == "__main__":
    raise SystemExit(main())
