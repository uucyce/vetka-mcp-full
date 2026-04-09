"""
VETKA User Message Handler - Main Orchestrator

@file user_message_handler.py
@status ACTIVE
@phase Phase 64.5 - God Object Split Complete
@lastUpdate 2026-01-17

User Message Socket.IO handler for python-socketio AsyncServer.
This is the main orchestration handler that coordinates:
- @mention parsing
- Direct model calls (via chat_handler.py)
- Streaming responses (via streaming_handler.py)
- Hostess routing (via workflow_handler.py)
- Agent chain calls PM → Dev → QA

Phase 64 Split:
- message_utils.py: format_history_for_prompt, build_pinned_context
- streaming_handler.py: stream_response (token streaming)
- chat_handler.py: detect_provider, build_model_prompt, model calls
- workflow_handler.py: agent chain, summary, emit helpers

Module Dependencies:
- src.api.handlers.message_utils (pure functions)
- src.api.handlers.streaming_handler (streaming)
- src.api.handlers.chat_handler (model calls)
- src.api.handlers.workflow_handler (workflow logic)
- src.api.handlers.handler_utils (context, persistence)
"""

import time
import json
import asyncio
import uuid
import logging  # MARKER_116_CLEANUP
import base64
import re

from src.utils.chat_utils import detect_response_type, get_agent_model_name

# MARKER_116_CLEANUP: Logger for debug output
logger = logging.getLogger(__name__)


def extract_semantic_key(message_text: str, fallback: str = "chat") -> str:
    """
    Extract semantic key from message for chat naming.

    Args:
        message_text: User message text
        fallback: Fallback key if extraction fails

    Returns:
        Semantic key like 'fix_bug_report' (max 30 chars)
    """
    words = message_text.strip().split()[:5]
    noise_words = {'the', 'a', 'an', 'is', 'are', 'what', 'how', 'can', 'do',
                   'does', 'in', 'on', 'at', 'как', 'что', 'в'}
    key_words = [w.lower() for w in words if w.lower() not in noise_words]
    semantic_key = '_'.join(key_words[:3])[:30] or fallback
    return semantic_key if semantic_key else fallback


# Phase 114.8: Pre-fetch tools before streaming
def _format_search_results_for_stream(results: list) -> str:
    """
    Format hybrid search results for system prompt injection in streaming.
    Phase 114.8: Converts search result dicts into readable context
    so streaming models can reference REAL codebase data.

    Args:
        results: List of search result dicts from HybridSearchService.search()

    Returns:
        Formatted string for system prompt injection
    """
    if not results:
        return ""

    formatted_parts = []
    for i, result in enumerate(results[:5], 1):
        path = result.get("path", result.get("file_path", "unknown"))
        score = result.get("rrf_score", result.get("score", 0))
        snippet = result.get("content", "")[:400]
        formatted_parts.append(
            f"### Result {i}: `{path}` (score: {score:.3f})\n```\n{snippet}\n```"
        )

    return "\n\n".join(formatted_parts)


def _should_attempt_tools_in_stream(user_text: str) -> bool:
    """
    Lightweight intent gate to avoid unnecessary pre-stream tool round trips.
    """
    text = (user_text or "").lower()
    keywords = (
        "show", "focus", "navigate", "find", "search", "grep", "tree", "file",
        "open", "where", "scan", "index", "dependency", "dependencies", "import",
        "покажи", "найди", "фокус", "поиск", "зависим", "файл", "индекс",
    )
    return any(k in text for k in keywords)


def register_user_message_handler(sio, app=None):
    """Register the user_message Socket.IO handler."""

    # ========================================
    # Phase 57.9: Session state for pending API keys
    # Tracks pending_key per session for Hostess learn flow
    # ========================================
    pending_api_keys = {}  # {sid: {'key': 'xxx', 'timestamp': time.time()}}
    # S6.4: lightweight in-process prosody memory by model identity.
    solo_prosody_memory: dict[str, dict] = {}
    # Serializes solo Qwen synth requests to reduce local model overload/500s.
    solo_qwen_tts_lock = asyncio.Lock()
    # Latest voice generation sequence per socket session (drop stale background jobs).
    voice_generation_seq: dict[str, int] = {}
    # Prevent duplicate voice generation jobs for the same assistant message id.
    voice_jobs_inflight: set[str] = set()

    # ========================================
    # Phase 44.6: DIRECT IMPORTS (no god object)
    # All imports are from their source modules
    # ========================================

    # Parse @mentions
    from src.agents.agentic_tools import parse_mentions

    # Phase 53: Per-session chat registry
    from src.chat.chat_registry import ChatRegistry, Message
    from src.voice.voice_assignment_registry import get_voice_assignment_registry
    from src.voice.emotion_prosody import infer_and_map_prosody
    from src.voice.qwen_voice_catalog import normalize_qwen_voice_id
    from src.api.routes.voice_storage_routes import normalize_qwen_audio_payload, store_voice_audio_bytes
    from src.services.progressive_tts_service import ProgressiveTtsService

    # Phase 46: Streaming support (HOST_HAS_OLLAMA needed for streaming decision)
    from src.elisya.api_aggregator_v3 import HOST_HAS_OLLAMA

    # Phase 93.3: Unified LLM calls via provider_registry
    from src.elisya.provider_registry import (
        call_model_v2,
        call_model_v2_stream,
        Provider,
        XaiKeysExhausted,
    )
    from src.elisya.capability_matrix import (
        build_capability_snapshot,
        resolve_tool_execution_mode,
    )

    # Handler utilities (context, persistence, keys)
    from src.api.handlers.handler_utils import (
        sync_get_rich_context,
        format_context_for_agent,
        save_chat_message,
        get_agents,
        get_openrouter_key,
        rotate_openrouter_key,
        HOSTESS_AVAILABLE,
        ROLE_PROMPTS_AVAILABLE,
    )

    # Phase 51.1: Chat History Integration
    from src.chat.chat_history_manager import get_chat_history_manager

    # Phase 51.4: Message Surprise - CAM event emission
    from src.orchestration.cam_event_handler import emit_cam_event
    from src.orchestration.context_packer import get_context_packer

    # Phase 64.1: Extracted pure utility functions
    from .message_utils import (
        format_history_for_prompt,
        load_pinned_file_content,
        build_pinned_context,
    )

    # Phase 64.2: Extracted streaming handler
    from .streaming_handler import stream_response

    # Phase 64.3: Extracted chat helpers
    from .chat_handler import (
        ModelProvider,
        detect_provider,
        is_local_ollama_model,
        build_model_prompt,
        build_web_context_summary,
        get_agent_short_name,
        emit_stream_wrapper,
    )

    # Phase 64.4: Extracted workflow helpers
    from .workflow_handler import (
        generate_simple_summary,
        parse_llm_summary,
        build_summary_prompt,
        determine_agents_to_call,
        get_max_tokens_for_agent,
        build_agent_response_dict,
        emit_hostess_response,
        emit_agent_response,
        emit_summary_response,
        emit_quick_actions,
    )

    # PHASE 64.1: Old function definitions removed (115 lines deleted)
    # Functions moved to message_utils.py:
    #   - format_history_for_prompt()
    #   - load_pinned_file_content()
    #   - build_pinned_context()
    #
    # PHASE 64.2: stream_response() moved to streaming_handler.py

    # Role prompts and artifacts
    from src.agents.role_prompts import build_full_prompt
    from src.utils.artifact_extractor import (
        extract_artifacts,
        extract_qa_score,
        extract_qa_verdict,
    )

    # Hostess agent
    from src.agents.hostess_agent import get_hostess

    # Phase 55.1: MCP session init
    from src.mcp.tools.session_tools import vetka_session_init

    # Hostess context builder (optional, may fail)
    def get_hostess_context_builder():
        """Get HostessContextBuilder for rich context (Phase 44)."""
        try:
            from src.orchestration.hostess_context_builder import (
                get_hostess_context_builder as _get_builder,
            )

            return _get_builder()
        except Exception:
            return None

    async def _run_pre_stream_tool_phase(
        *,
        sio,
        sid: str,
        msg_id: str,
        requested_model: str,
        detected_provider,
        model_prompt: str,
        prefetch_context: str,
    ):
        """
        Execute one non-stream tool-calling phase, emit tool_* events,
        and return a compact result summary for follow-up streamed answer.
        """
        from src.agents.tools import get_tools_for_agent
        from src.tools import SafeToolExecutor, ToolCall

        model_tools = get_tools_for_agent("Dev")
        if not model_tools:
            return []

        tool_system = "You can call tools when needed. Return tool calls if required."
        if prefetch_context:
            tool_system += (
                "\n\n## Pre-fetched Codebase Search Results\n"
                + prefetch_context
            )

        pre_messages = [
            {"role": "system", "content": tool_system},
            {"role": "user", "content": model_prompt},
        ]
        pre_result = await call_model_v2(
            messages=pre_messages,
            model=requested_model,
            provider=detected_provider,
            source=None,
            temperature=0.2,
            tools=model_tools,
        )
        message_data = pre_result.get("message", {}) if isinstance(pre_result, dict) else {}
        tool_calls = message_data.get("tool_calls", []) or []
        if not tool_calls:
            return []

        executor = SafeToolExecutor()
        tool_results = []
        for idx, tc in enumerate(tool_calls[:8]):
            func = tc.get("function", {}) if isinstance(tc, dict) else {}
            tool_name = str(func.get("name", "") or "").strip()
            raw_args = func.get("arguments", {}) if isinstance(func, dict) else {}
            if isinstance(raw_args, str):
                try:
                    tool_args = json.loads(raw_args)
                except Exception:
                    tool_args = {}
            elif isinstance(raw_args, dict):
                tool_args = raw_args
            else:
                tool_args = {}
            if not tool_name:
                continue

            await sio.emit(
                "tool_start",
                {
                    "id": msg_id,
                    "index": idx,
                    "tool": tool_name,
                    "args": tool_args,
                },
                to=sid,
            )

            call = ToolCall(
                tool_name=tool_name,
                arguments=tool_args,
                agent_type="Dev",
                call_id=f"stream_pre_{idx}_{tool_name}",
            )
            result_obj = await executor.execute(call)
            result_payload = {
                "tool": tool_name,
                "args": tool_args,
                "success": bool(result_obj.success),
                "result": result_obj.result if result_obj.success else None,
                "error": result_obj.error if not result_obj.success else None,
            }
            tool_results.append(result_payload)

            await sio.emit(
                "tool_result" if result_obj.success else "tool_error",
                {
                    "id": msg_id,
                    "index": idx,
                    "tool": tool_name,
                    "success": bool(result_obj.success),
                    "result": result_obj.result if result_obj.success else None,
                    "error": result_obj.error if not result_obj.success else None,
                },
                to=sid,
            )

        return tool_results

    @sio.on("user_message")
    async def handle_user_message(sid, data):
        """
        REFACTORED: Real LLM responses using agent.call_llm() with Elisya context.

        Flow:
        1. Get file context via Elisya
        2. Get agent instances
        3. For each agent (PM, Dev, QA):
           - Build system + user prompts
           - Call agent.call_llm() for REAL LLM response
           - Emit response to client
        """
        # Phase 45: Debug logging
        print(f"\n{'=' * 50}")
        print(f"[USER_MESSAGE] Received from {sid}")
        print(f"[USER_MESSAGE] Data keys: {list(data.keys()) if data else 'NO DATA'}")
        print(f"[USER_MESSAGE] Data: {data}")
        print(f"{'=' * 50}\n")

        # Phase 44.6: All imports are now at function scope (above)
        # No more lazy imports or get_*() wrappers needed

        client_id = sid[:8]
        text = data.get("text", "").strip()
        node_id = data.get("node_id", "root")
        raw_node_path = data.get("node_path", "unknown")

        # Phase 51.1 Fix: Normalize path to prevent duplicate chats
        if raw_node_path not in ("unknown", "root", ""):
            from pathlib import Path

            try:
                node_path = str(Path(raw_node_path).resolve())
            except Exception:
                node_path = raw_node_path
        else:
            node_path = raw_node_path

        # Phase 48.1: Model routing from client
        requested_model = data.get("model")
        # Phase 111.9: Source for multi-provider routing (poe, polza, openrouter, etc.)
        model_source = data.get("model_source")
        # Phase 111.10.2: DEBUG - trace model_source
        logger.debug(f"[DEBUG_SOURCE] model={requested_model}, model_source={model_source}")  # MARKER_116_CLEANUP

        # Phase 61: Pinned files for multi-file context
        pinned_files = data.get("pinned_files", [])
        # MARKER_156.S5_SOLO_STORAGE: Optional message contract fields for voice/text persistence.
        message_type = str(data.get("message_type", "text") or "text").strip().lower()
        message_metadata = data.get("message_metadata") if isinstance(data.get("message_metadata"), dict) else {}
        voice_t0 = time.perf_counter() if message_type == "voice" else None
        request_voice_seq = None
        if message_type == "voice":
            request_voice_seq = int(voice_generation_seq.get(sid, 0) or 0) + 1
            voice_generation_seq[sid] = request_voice_seq
            print(
                f"[MARKER_156.VOICE.S6_TRACE_T0_USER_SEND] sid={sid} seq={request_voice_seq} chat_id={data.get('chat_id')} model={data.get('model')} source={data.get('model_source')}"
            )
            logger.info(
                "[MARKER_156.VOICE.S6_TRACE_T0_USER_SEND] sid=%s seq=%s chat_id=%s model=%s source=%s",
                sid,
                request_voice_seq,
                data.get("chat_id"),
                data.get("model"),
                data.get("model_source"),
            )

        # [PHASE71-M1] Phase 71: Viewport context for spatial awareness
        viewport_context = data.get("viewport_context", None)
        # MARKER_140.WEB_CTX_INGEST: Optional live web page context from frontend
        web_context = data.get("web_context", None)

        # FIX_109.4: Accept chat_id from frontend for unified ID system (like groups)
        # This allows MCP to interact with solo chats using the same ID
        client_chat_id = data.get("chat_id", None)
        if client_chat_id:
            logger.debug(f"[FIX_109.4] Using client-provided chat_id: {client_chat_id}")  # MARKER_116_CLEANUP

        # MARKER_109_14: Accept display_name from frontend (priority: pinned > node > keywords)
        client_display_name = data.get("display_name", None)
        if client_display_name:
            logger.debug(f"[MARKER_109_14] Using client-provided display_name: {client_display_name}")  # MARKER_116_CLEANUP

        # Save request timestamp (all responses use same timestamp)
        request_node_id = node_id
        request_timestamp = time.time()

        print(
            f"\n[SOCKET] User message from {client_id}: {text[:50]}... (node: {node_path}, message_type: {message_type})"
        )

        # Phase 61: Log pinned files
        if pinned_files:
            print(f"[PHASE_61] Pinned files: {len(pinned_files)} files")

        # Phase 71: Log viewport context
        if viewport_context:
            print(
                f"[PHASE_71] Viewport context: {viewport_context.get('total_pinned', 0)} pinned, {viewport_context.get('total_visible', 0)} visible, zoom ~{viewport_context.get('zoom_level', 0)}"
            )
        if web_context and web_context.get("url"):
            print(f"[MARKER_140] Live web context: {web_context.get('url')}")

        # Phase 53: Get per-session chat manager and set context
        chat_manager = ChatRegistry.get_manager(sid)
        if node_path and node_path not in ("unknown", "root"):
            chat_manager.set_context(node_path)

        # Phase 53: Add user message to session history
        chat_manager.add_message(
            Message(role="user", content=text, node_path=node_path)
        )

        def _language_for_text(text_value: str) -> str:
            return "ru" if re.search(r"[А-Яа-яЁё]", text_value or "") else "en"

        def _waveform_from_audio(audio_bytes: bytes, points: int = 64) -> list[float]:
            if not audio_bytes:
                return []
            # Prefer real PCM amplitude extraction for WAV.
            try:
                import io
                import wave
                import struct

                with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
                    n_channels = wav.getnchannels()
                    sample_width = wav.getsampwidth()
                    n_frames = wav.getnframes()
                    raw = wav.readframes(n_frames)

                if sample_width not in (1, 2) or not raw:
                    raise ValueError("unsupported wav format")

                if sample_width == 2:
                    fmt = f"<{len(raw) // 2}h"
                    samples = struct.unpack(fmt, raw)
                    max_abs = 32767.0
                    values = [abs(s) / max_abs for s in samples]
                else:
                    values = [abs(b - 128) / 128.0 for b in raw]

                if n_channels > 1:
                    mono = []
                    for i in range(0, len(values), n_channels):
                        chunk = values[i:i + n_channels]
                        if chunk:
                            mono.append(sum(chunk) / len(chunk))
                    values = mono

                step = max(1, len(values) // points)
                out: list[float] = []
                for i in range(0, len(values), step):
                    chunk = values[i:i + step]
                    if not chunk:
                        continue
                    out.append(round(max(chunk), 4))
                    if len(out) >= points:
                        break
                return out
            except Exception:
                # Fallback amplitude approximation for unknown formats.
                length = len(audio_bytes)
                step = max(1, length // points)
                out: list[float] = []
                for i in range(0, length, step):
                    chunk = audio_bytes[i:i + step]
                    if not chunk:
                        continue
                    mean_val = sum(chunk) / len(chunk)
                    out.append(round(abs(mean_val - 128.0) / 128.0, 4))
                    if len(out) >= points:
                        break
                return out

        def _apply_voice_response_contract(prompt: str, user_text: str) -> str:
            """
            Voice mode response policy:
            - bounded token budget
            - plain speakable text (no markdown/tables/JSON)
            - emotion/prosody is handled server-side, model should focus on semantic answer
            """
            if not prompt:
                return prompt
            # Keep voice replies shorter to reduce TTS latency in solo mode.
            max_tokens = 90 if len(user_text or "") < 220 else 140
            policy = (
                "\n\n[VOICE_MODE_POLICY]\n"
                f"- Keep answer concise: <= {max_tokens} tokens.\n"
                "- Output plain natural text for TTS. No markdown lists/tables/code fences/JSON.\n"
                "- Never say that you cannot answer by voice; voice rendering is handled by the system.\n"
                "- Do not print emotion tags; prosody/emotion is applied by server tools.\n"
                "- If clarification needed, ask one short follow-up question.\n"
            )
            return f"{prompt}{policy}"

        async def _synthesize_qwen_and_store(
            *,
            text_value: str,
            speaker: str,
            prosody: dict | None = None,
            msg_id: str | None = None,
            trace_t0: float | None = None,
        ) -> dict:
            """
            S6.2 strict path: Qwen local TTS only (no provider fallback).
            Returns audio metadata contract for chat message.
            """
            text_clean = (text_value or "").strip()
            if not text_clean:
                return {
                    "format": None,
                    "duration_ms": None,
                    "waveform": [],
                    "storage_id": None,
                    "url": None,
                }

            try:
                if request_voice_seq is not None and voice_generation_seq.get(sid) != request_voice_seq:
                    print(f"[SOLO_VOICE_S6_2] drop stale tts msg_id={msg_id} sid={sid} seq={request_voice_seq}")
                    return {
                        "format": None,
                        "duration_ms": None,
                        "waveform": [],
                        "storage_id": None,
                        "url": None,
                    }
                import httpx
                from src.voice.tts_engine import estimate_audio_duration
                from src.voice.tts_server_manager import is_tts_running, start_tts_server

                language = _language_for_text(text_clean)
                prosody_payload = prosody if isinstance(prosody, dict) else {}
                logger.info(
                    "[MARKER_156.VOICE.S6_TRACE_T2_TTS_START] msg_id=%s len=%s speaker=%s t_since_t0_ms=%.1f",
                    msg_id or "n/a",
                    len(text_clean),
                    speaker,
                    ((time.perf_counter() - trace_t0) * 1000.0) if trace_t0 else -1.0,
                )
                print(
                    f"[MARKER_156.VOICE.S6_TRACE_T2_TTS_START] msg_id={msg_id or 'n/a'} len={len(text_clean)} speaker={speaker}"
                )
                if not is_tts_running():
                    start_tts_server(wait_ready=True, timeout=60.0)
                resolved_speaker = normalize_qwen_voice_id(speaker or "ryan", default="ryan")
                async with solo_qwen_tts_lock:
                    async with httpx.AsyncClient(timeout=90.0) as client:
                        health = await client.get("http://127.0.0.1:5003/health", timeout=3.0)
                        if health.status_code != 200:
                            logger.warning("[SOLO_VOICE_S6_2] Qwen TTS health check failed: %s", health.status_code)
                        payload = {
                            "text": text_clean,
                            "language": language,
                            "speaker": resolved_speaker,
                            # S6.4: optional fields for future TTS server prosody support.
                            "speed": prosody_payload.get("speed"),
                            "pitch": prosody_payload.get("pitch"),
                            "energy": prosody_payload.get("energy"),
                            "pause_profile": prosody_payload.get("pause_profile"),
                        }
                        tts_resp = None
                        for attempt in range(2):
                            try:
                                tts_resp = await client.post(
                                    "http://127.0.0.1:5003/tts/generate",
                                    json=payload,
                                    timeout=30.0,
                                )
                                tts_resp.raise_for_status()
                                break
                            except Exception as inner_exc:
                                if attempt == 1:
                                    raise
                                logger.warning("[SOLO_VOICE_S6_2] qwen generate retry: %r", inner_exc)
                                if not is_tts_running():
                                    start_tts_server(wait_ready=True, timeout=45.0)

                payload = tts_resp.json() if tts_resp.content else {}
                audio_b64 = payload.get("audio") if isinstance(payload, dict) else None
                if not audio_b64:
                    logger.warning("[SOLO_VOICE_S6_2] Empty audio from Qwen TTS")
                    return {
                        "format": None,
                        "duration_ms": None,
                        "waveform": [],
                        "storage_id": None,
                        "url": None,
                    }

                audio_bytes = base64.b64decode(audio_b64)
                if not audio_bytes:
                    return {
                        "format": None,
                        "duration_ms": None,
                        "waveform": [],
                        "storage_id": None,
                        "url": None,
                    }
                audio_bytes, normalized_content_type, normalized_ext = normalize_qwen_audio_payload(audio_bytes)

                estimated_duration_ms = int(max(0.6, estimate_audio_duration(text_clean)) * 1000)
                storage_meta = store_voice_audio_bytes(
                    audio_bytes,
                    content_type=normalized_content_type,
                    ext_hint=normalized_ext,
                    duration_ms=estimated_duration_ms,
                )
                logger.info(
                    "[MARKER_156.VOICE.S6_TRACE_T4_STORAGE_DONE] msg_id=%s storage_id=%s format=%s duration_ms=%s t_since_t0_ms=%.1f",
                    msg_id or "n/a",
                    storage_meta.get("storage_id"),
                    storage_meta.get("format") or normalized_ext,
                    storage_meta.get("duration_ms") or estimated_duration_ms,
                    ((time.perf_counter() - trace_t0) * 1000.0) if trace_t0 else -1.0,
                )
                print(
                    f"[MARKER_156.VOICE.S6_TRACE_T4_STORAGE_DONE] msg_id={msg_id or 'n/a'} storage_id={storage_meta.get('storage_id')} format={storage_meta.get('format') or normalized_ext}"
                )
                return {
                    "format": storage_meta.get("format") or normalized_ext,
                    "duration_ms": storage_meta.get("duration_ms") or estimated_duration_ms,
                    "waveform": _waveform_from_audio(audio_bytes, points=64),
                    "storage_id": storage_meta.get("storage_id"),
                    "url": storage_meta.get("url"),
                }
            except Exception as exc:
                logger.warning("[SOLO_VOICE_S6_2] qwen synth/store failed: %r", exc, exc_info=True)
                print(f"[SOLO_VOICE_S6_2] qwen synth/store failed: {exc!r}")
                return {
                    "format": None,
                    "duration_ms": None,
                    "waveform": [],
                    "storage_id": None,
                    "url": None,
                }

        async def _emit_progressive_voice_chunks(
            *,
            msg_id: str,
            voice_id: str,
            full_text: str,
            prosody: dict | None,
            trace_t0: float | None,
        ) -> str | None:
            if not full_text.strip():
                return None
            language = _language_for_text(full_text)
            service = ProgressiveTtsService()
            generation_id = str(uuid.uuid4())
            seq_count = 0
            total_duration = 0
            checksum = ""
            await sio.emit(
                "chat_voice_stream_start",
                {
                    "message_id": msg_id,
                    "generation_id": generation_id,
                    "voice_id": voice_id,
                    "model": model_name,
                    "agent": agent_short_name,
                    "tts_provider": voice_meta.get("tts_provider"),
                    "model_identity_key": voice_meta.get("model_identity_key"),
                },
                to=sid,
            )
            try:
                async for chunk in service.stream_sentences(
                    full_text,
                    speaker=voice_id or "ryan",
                    language=language,
                    prosody=prosody,
                ):
                    checksum = chunk.get("checksum", checksum)
                    total_duration += int(chunk.get("duration_ms") or 0)
                    seq_count = max(seq_count, int(chunk.get("seq", 0)))
                    await sio.emit(
                        "chat_voice_stream_chunk",
                        {
                            "message_id": msg_id,
                            "generation_id": generation_id,
                            "seq": chunk.get("seq"),
                            "audio": chunk.get("audio_b64"),
                            "duration_ms": chunk.get("duration_ms"),
                            "checksum": chunk.get("checksum"),
                            "is_final": chunk.get("is_final", False),
                        },
                        to=sid,
                    )
                await sio.emit(
                    "chat_voice_stream_end",
                    {
                        "message_id": msg_id,
                        "generation_id": generation_id,
                        "total_seq": seq_count + 1,
                        "total_duration_ms": total_duration,
                        "final_checksum": checksum,
                    },
                    to=sid,
                )
            except Exception as exc:
                logger.warning("[SOLO_VOICE_S6_2] progressive stream failed: %s", exc)
            return generation_id

        async def _emit_solo_voice_message(
            *,
            msg_id: str,
            agent_name: str,
            model_name: str,
            provider_name: str,
            model_source_name: str | None,
            full_text: str,
            trace_t0: float | None = None,
        ) -> dict:
            """MARKER_156.S6_1_SOLO_VOICE_EVENT: Final solo voice contract over socket."""
            if request_voice_seq is not None and voice_generation_seq.get(sid) != request_voice_seq:
                print(f"[SOLO_VOICE_S6_2] skip stale emit msg_id={msg_id} sid={sid} seq={request_voice_seq}")
                return {}
            provider_key = str(provider_name or "unknown").strip().lower() or "unknown"
            model_key = str(model_name or "unknown").strip() or "unknown"
            identity_key = f"{provider_key}:{model_key}"
            voice_meta = {
                "voice_id": None,
                "tts_provider": "qwen",
                "model_identity_key": identity_key,
            }
            emotion_snapshot: dict = {}
            prosody_snapshot: dict = {}
            audio_meta = {
                "format": None,
                "duration_ms": None,
                "waveform": [],
                "storage_id": None,
                "url": None,
            }
            try:
                assignment = await get_voice_assignment_registry().get_or_assign(
                    provider=provider_key,
                    model_id=model_key,
                    tts_provider="qwen",
                )
                if isinstance(assignment, dict):
                    voice_meta = {
                        "voice_id": assignment.get("voice_id"),
                        "tts_provider": assignment.get("tts_provider") or "qwen",
                        "model_identity_key": assignment.get("model_identity_key") or identity_key,
                        "persona_tag": assignment.get("persona_tag"),
                    }
            except Exception as exc:
                logger.warning("[SOLO_VOICE_S6_2] voice assignment failed for %s: %s", identity_key, exc)

            try:
                inference = infer_and_map_prosody(
                    full_text,
                    previous_prosody=solo_prosody_memory.get(identity_key),
                )
                emotion_snapshot = inference.get("emotion", {}) if isinstance(inference, dict) else {}
                prosody_snapshot = inference.get("prosody", {}) if isinstance(inference, dict) else {}
                if prosody_snapshot:
                    solo_prosody_memory[identity_key] = dict(prosody_snapshot)
            except Exception as exc:
                logger.warning("[SOLO_VOICE_S6_4] emotion inference failed for %s: %s", identity_key, exc)

            await _emit_progressive_voice_chunks(
                msg_id=msg_id,
                voice_id=str(voice_meta.get("voice_id") or "ryan"),
                full_text=full_text,
                prosody=prosody_snapshot,
                trace_t0=trace_t0,
            )

            audio_meta = await _synthesize_qwen_and_store(
                text_value=full_text,
                speaker=str(voice_meta.get("voice_id") or "ryan"),
                prosody=prosody_snapshot,
                msg_id=msg_id,
                trace_t0=trace_t0,
            )

            await sio.emit(
                "chat_voice_message",
                {
                    "id": msg_id,
                    "agent": agent_name,
                    "model": model_name,
                    "full_message": full_text,
                    "metadata": {
                        "model": model_name,
                        "model_source": model_source_name,
                        "model_provider": provider_key,
                        "voice": voice_meta,
                        "audio": audio_meta,
                        "emotion": emotion_snapshot,
                        "prosody": prosody_snapshot,
                    },
                },
                to=sid,
            )
            logger.info(
                "[MARKER_156.VOICE.S6_TRACE_T5_UI_BUBBLE_EMIT] msg_id=%s storage_id=%s t_since_t0_ms=%.1f",
                msg_id,
                (audio_meta or {}).get("storage_id"),
                ((time.perf_counter() - trace_t0) * 1000.0) if trace_t0 else -1.0,
            )
            print(
                f"[MARKER_156.VOICE.S6_TRACE_T5_UI_BUBBLE_EMIT] msg_id={msg_id} storage_id={(audio_meta or {}).get('storage_id')}"
            )
            return {
                "voice": voice_meta,
                "audio": audio_meta,
                "emotion": emotion_snapshot,
                "prosody": prosody_snapshot,
            }

        def _schedule_solo_voice_message(
            *,
            msg_id: str,
            agent_name: str,
            model_name: str,
            provider_name: str,
            model_source_name: str | None,
            full_text: str,
        ) -> None:
            async def _job() -> None:
                if msg_id in voice_jobs_inflight:
                    print(f"[SOLO_VOICE_S6_2] skip duplicate bg job msg_id={msg_id}")
                    return
                voice_jobs_inflight.add(msg_id)
                try:
                    if request_voice_seq is not None and voice_generation_seq.get(sid) != request_voice_seq:
                        print(f"[SOLO_VOICE_S6_2] skip stale bg job msg_id={msg_id} sid={sid} seq={request_voice_seq}")
                        return
                    print(f"[MARKER_156.VOICE.S6_TRACE_BG_JOB_START] msg_id={msg_id}")
                    await asyncio.wait_for(
                        _emit_solo_voice_message(
                            msg_id=msg_id,
                            agent_name=agent_name,
                            model_name=model_name,
                            provider_name=provider_name,
                            model_source_name=model_source_name,
                            full_text=full_text,
                            trace_t0=voice_t0,
                        ),
                        timeout=45.0,
                    )
                    print(f"[MARKER_156.VOICE.S6_TRACE_BG_JOB_DONE] msg_id={msg_id}")
                except asyncio.TimeoutError:
                    print(f"[SOLO_VOICE_S6_2] async emit timeout msg_id={msg_id}")
                except Exception as exc:
                    logger.warning("[SOLO_VOICE_S6_2] async emit failed msg_id=%s err=%r", msg_id, exc, exc_info=True)
                    print(f"[SOLO_VOICE_S6_2] async emit failed msg_id={msg_id} err={exc!r}")
                finally:
                    voice_jobs_inflight.discard(msg_id)

            asyncio.create_task(_job())
        if requested_model:
            print(f"[SOCKET] Model override: {requested_model}")

        if not text:
            await sio.emit("agent_error", {"error": "Empty message"}, to=sid)
            return

        # ========================================
        # PHASE 48.1: MODEL DIRECTORY ROUTING
        # Phase 48.2: Fixed to use SecureKeyManager
        # Phase 60.4: Fixed to route local Ollama models correctly
        # If client selected a specific model, route directly
        # ========================================
        # MARKER_94.5_SOLO_ENTRY: Solo chat entry point

        # Phase 55.1: MCP session init (fire-and-forget, non-blocking)
        async def _bg_session_init():
            try:
                session = await asyncio.wait_for(
                    vetka_session_init(user_id=sid, group_id=None, compress=False),
                    timeout=1.0
                )
                print(f"   [MCP] Solo session initialized: {session.get('session_id')}")
            except asyncio.TimeoutError:
                print(f"   ⚠️ MCP session init timeout (1s)")
            except Exception as e:
                print(f"   ⚠️ MCP session init failed: {e}")
        asyncio.create_task(_bg_session_init())

        if requested_model:
            print(f"[MODEL_DIRECTORY] Direct model call: {requested_model}")

            # Phase 64.3: Use extracted helper for model detection
            is_local_ollama = is_local_ollama_model(requested_model)

            # Emit routing status
            await sio.emit(
                "agent_message",
                {
                    "agent": "Hostess",
                    "model": "routing",
                    "content": f"Routing to **{requested_model}**{'  (local)' if is_local_ollama else ''}...",
                    "text": f"Routing to **{requested_model}**{'  (local)' if is_local_ollama else ''}...",
                    "node_id": request_node_id,
                    "node_path": node_path,
                    "timestamp": request_timestamp,
                    "response_type": "status",
                    "force_artifact": False,
                },
                to=sid,
            )

            # Phase 60.4: Handle local Ollama models
            if is_local_ollama:
                try:
                    import ollama
                    import uuid as uuid_module

                    print(f"[MODEL_DIRECTORY] Calling Ollama: {requested_model}")

                    # Phase 51.1: Load chat history
                    chat_history = get_chat_history_manager()
                    # MARKER_CHAT_NAMING: Solo chat uses semantic key instead of structured display_name
                    # Current: generate_semantic_key() creates chat identifier like 'fix_bug_report', stored as file_path
                    # Expected: Pass message text as display_name and set context_type='topic' for semantic chats
                    # Fix: Pass display_name parameter to get_or_create_chat() with semantic_key, keep file_path as 'unknown'
                    def generate_semantic_key(message_text: str, node_path: str) -> str:
                        """Extract semantic key from message content (topic/intent)"""
                        # Get first 3-5 words, remove noise words, limit to 30 chars
                        words = message_text.strip().split()[:5]
                        noise_words = {'the', 'a', 'an', 'is', 'are', 'what', 'how', 'can', 'do', 'does', 'in', 'on', 'at'}
                        key_words = [w.lower() for w in words if w.lower() not in noise_words]
                        semantic_key = '_'.join(key_words[:3])[:30] or "chat"
                        # Fallback to node_path if semantic key is empty
                        return semantic_key if semantic_key else node_path

                    # MARKER_109_14: Prefer client_display_name
                    semantic_chat_key = client_display_name or generate_semantic_key(text, node_path)
                    chat_id = chat_history.get_or_create_chat(
                        'unknown',
                        context_type='topic',
                        display_name=semantic_chat_key,
                        chat_id=client_chat_id  # MARKER_115_BUG1: Chat hygiene fix
                    )
                    history_messages = chat_history.get_chat_messages(chat_id)
                    history_context = format_history_for_prompt(
                        history_messages, max_messages=10
                    )

                    print(
                        f"[PHASE_51.1] Loaded {len(history_messages)} history messages for {node_path}"
                    )

                    # Get file context
                    rich_context = sync_get_rich_context(node_path)
                    if rich_context.get("error"):
                        context_for_model = (
                            f"File: {node_path}\nStatus: {rich_context['error']}"
                        )
                    else:
                        context_for_model = format_context_for_agent(
                            rich_context, "generic"
                        )

                    # Phase 67: Build pinned files context with smart selection
                    packer = get_context_packer()
                    packed = await packer.pack(
                        user_query=text,
                        pinned_files=pinned_files,
                        viewport_context=viewport_context,
                        session_id=sid,
                        model_name=requested_model,
                        user_id="default",
                        zoom_level=float((viewport_context or {}).get("zoom_level", 1.0) or 1.0),
                    )
                    pinned_context = packed.pinned_context
                    viewport_summary = packed.viewport_summary
                    web_context_summary = build_web_context_summary(web_context)

                    # Phase 73: Build JSON dependency context for AI agents
                    # Packed JSON context + optional JEPA semantic core (Phase 157.1)
                    json_context = packed.json_context + packed.jepa_context

                    # Phase 64.5: Save user message BEFORE model call
                    # Phase 74: Pass pinned_files for group chat context
                    save_chat_message(
                        node_path,
                        {
                            "role": "user",
                            "text": text,
                            "node_id": node_id,
                            "model_source": model_source,
                            "message_type": message_type,
                            "metadata": message_metadata,
                        },  # MARKER_115_BUG3
                        pinned_files=pinned_files,
                        chat_id=client_chat_id,
                    )

                    # Phase 64.3: Use extracted helper for prompt building
                    # Phase 71: Added viewport_summary parameter
                    # Phase 73: Added json_context parameter
                    model_prompt = build_model_prompt(
                        text,
                        context_for_model,
                        pinned_context,
                        history_context,
                        viewport_summary,
                        json_context,
                        web_context_summary,
                    )
                    if message_type == "voice":
                        model_prompt = _apply_voice_response_contract(model_prompt, text)

                    agent_short_name = get_agent_short_name(requested_model)
                    msg_id = str(uuid_module.uuid4())

                    # Emit stream start
                    await sio.emit(
                        "stream_start",
                        {
                            "id": msg_id,
                            "agent": agent_short_name,
                            "model": requested_model,
                            "tool_execution_mode": "disabled_stream",
                        },
                        to=sid,
                    )

                    # Phase 93.3: Use unified call_model_v2 instead of direct ollama.chat
                    full_response = ""
                    tokens_output = 0

                    try:
                        response = await call_model_v2(
                            messages=[{"role": "user", "content": model_prompt}],
                            model=requested_model,
                            provider=Provider.OLLAMA,
                        )
                        full_response = response.get("message", {}).get("content", "")
                    except Exception as model_err:
                        print(f"[MODEL_DIRECTORY] call_model_v2 error: {model_err}")
                        full_response = f"Error: {str(model_err)[:200]}"

                    tokens_output = len(full_response.split())

                    print(
                        f"[MODEL_DIRECTORY] Ollama complete: {len(full_response)} chars"
                    )

                    # Emit stream end
                    await sio.emit(
                        "stream_end",
                        {
                            "id": msg_id,
                            "full_message": full_response,
                            "metadata": {
                                "tokens_output": tokens_output,
                                "tokens_input": len(model_prompt.split()),
                                "model": requested_model,
                                "agent": agent_short_name,
                            },
                        },
                        to=sid,
                    )

                    voice_assistant_metadata = None
                    if message_type == "voice":
                        logger.info(
                            "[MARKER_156.VOICE.S6_TRACE_T1_LLM_STREAM_END] msg_id=%s t_since_t0_ms=%.1f",
                            msg_id,
                            ((time.perf_counter() - voice_t0) * 1000.0) if voice_t0 else -1.0,
                        )
                        print(f"[MARKER_156.VOICE.S6_TRACE_T1_LLM_STREAM_END] msg_id={msg_id}")
                        _schedule_solo_voice_message(
                            msg_id=msg_id,
                            agent_name=agent_short_name,
                            model_name=requested_model,
                            provider_name=Provider.OLLAMA.value,
                            model_source_name=model_source,
                            full_text=full_response,
                        )

                    # Save to chat history
                    # Phase 74: Pass pinned_files for group chat context
                    # MARKER_CHAT_HISTORY_ATTRIBUTION: Model attribution fix - IMPLEMENTED
                    save_chat_message(
                        node_path,
                        {
                            "role": "assistant",
                            "agent": requested_model,
                            "model": requested_model,
                            "model_provider": "ollama",  # Provider for Ollama local models
                            "model_source": model_source,  # MARKER_115_BUG3
                            "text": full_response,
                            "node_id": node_id,
                            "message_type": "voice" if message_type == "voice" else "text",
                            "metadata": {
                                "model": requested_model,
                                "model_source": model_source,
                                "model_provider": "ollama",
                                **(voice_assistant_metadata or {}),
                            } if message_type == "voice" else {},
                        },
                        pinned_files=pinned_files,
                        chat_id=client_chat_id,
                    )

                    # Phase 51.4: Emit message_sent event for surprise calculation
                    try:
                        await emit_cam_event(
                            "message_sent",
                            {
                                "chat_id": chat_id,
                                "content": full_response,
                                "role": "assistant",
                            },
                            source="ollama_direct_call",
                        )
                    except Exception as cam_err:
                        print(f"[CAM] Message event error (non-critical): {cam_err}")

                    print(f"[MODEL_DIRECTORY] Ollama direct call complete")
                    return  # Early return

                except Exception as e:
                    print(f"[MODEL_DIRECTORY] Ollama error: {e}")
                    import traceback

                    traceback.print_exc()
                    await sio.emit(
                        "chat_response",
                        {
                            "message": f"Error calling Ollama model {requested_model}: {str(e)[:200]}",
                            "agent": "System",
                            "model": "error",
                        },
                        to=sid,
                    )
                    return

            # Phase 93.3: Unified model handling via provider_registry
            try:
                import uuid

                print(f"[MODEL_DIRECTORY] Using provider_registry for {requested_model}")

                # Phase 51.1: Load chat history
                # MARKER_CHAT_NAMING: Fix 1/6 - Use semantic key for chat naming
                # FIX_109.4: Pass client_chat_id for unified ID system
                # MARKER_109_14: Prefer client_display_name (has pinned/node priority)
                chat_history = get_chat_history_manager()
                chat_display_name = client_display_name or extract_semantic_key(text)
                chat_id = chat_history.get_or_create_chat(
                    'unknown',
                    context_type='topic',
                    display_name=chat_display_name,
                    chat_id=client_chat_id  # FIX_109.4: Use client-provided ID if available
                )
                history_messages = chat_history.get_chat_messages(chat_id)
                history_context = format_history_for_prompt(
                    history_messages, max_messages=10
                )

                print(
                    f"[PHASE_51.1] Loaded {len(history_messages)} history messages for {node_path}"
                )

                # Get file context
                rich_context = sync_get_rich_context(node_path)
                if rich_context.get("error"):
                    context_for_model = (
                        f"File: {node_path}\nStatus: {rich_context['error']}"
                    )
                else:
                    context_for_model = format_context_for_agent(
                        rich_context, "generic"
                    )

                # Phase 67: Build pinned files context with smart selection
                packer = get_context_packer()
                packed = await packer.pack(
                    user_query=text,
                    pinned_files=pinned_files,
                    viewport_context=viewport_context,
                    session_id=sid,
                    model_name=requested_model,
                    user_id="default",
                    zoom_level=float((viewport_context or {}).get("zoom_level", 1.0) or 1.0),
                )
                pinned_context = packed.pinned_context
                viewport_summary = packed.viewport_summary
                web_context_summary = build_web_context_summary(web_context)

                # Phase 73: Build JSON dependency context for AI agents
                # Packed JSON context + optional JEPA semantic core (Phase 157.1)
                json_context = packed.json_context + packed.jepa_context

                # Phase 64.5: Save user message BEFORE model call
                # Phase 74: Pass pinned_files for group chat context
                save_chat_message(
                    node_path,
                    {
                        "role": "user",
                        "text": text,
                        "node_id": node_id,
                        "model_source": model_source,
                        "message_type": message_type,
                        "metadata": message_metadata,
                    },  # MARKER_115_BUG3
                    pinned_files=pinned_files,
                    chat_id=client_chat_id,
                )

                # ============ PHASE 114.8.1: MGC-CACHED PRE-FETCH BEFORE STREAM ============
                # Async pre-fetch semantic search with MGC cache (Multi-Generational)
                # Pattern: mgc.get_or_compute(key, async_fn) → cache HIT = 0ms, MISS = hybrid search
                # handle_user_message is async — await works directly, no ThreadPool needed
                prefetch_context = ""
                try:
                    from src.search.hybrid_search import get_hybrid_search
                    from src.memory.mgc_cache import get_mgc_cache

                    hybrid = get_hybrid_search()
                    mgc = get_mgc_cache()
                    semantic_query = text[:200] if text else "project overview"
                    cache_key = f"stream_prefetch:{semantic_query[:100]}"

                    # Proper async compute_fn (no lambda — must be Awaitable)
                    async def _compute_search():
                        return await hybrid.search(
                            query=semantic_query,
                            limit=5,
                            mode="hybrid",
                            collection="leaf",
                            skip_cache=False,
                        )

                    # MGC: cache HIT → instant (0ms), MISS → hybrid search (~50-100ms)
                    search_response = await mgc.get_or_compute(
                        key=cache_key,
                        compute_fn=_compute_search,
                        size_bytes=1024,  # ~1KB estimated result size
                    )

                    if isinstance(search_response, dict) and search_response.get("count", 0) > 0:
                        prefetch_context = _format_search_results_for_stream(
                            search_response["results"]
                        )
                        print(f"[PHASE_114.8.1] MGC {'HIT' if search_response.get('cache_hit') else 'MISS'} | "
                              f"{search_response['count']} results "
                              f"({search_response.get('timing_ms', 0):.0f}ms) for: {semantic_query[:50]}")
                    else:
                        print(f"[PHASE_114.8.1] No pre-fetch results for: {semantic_query[:50]}")
                except Exception as prefetch_err:
                    print(f"[PHASE_114.8] Pre-fetch failed (non-fatal): {prefetch_err}")
                # ============ END PHASE 114.8.1 MGC PRE-FETCH ============

                # Phase 64.3: Use extracted helper for prompt building
                # Phase 71: Added viewport_summary parameter
                # Phase 73: Added json_context parameter
                model_prompt = build_model_prompt(
                    text,
                    context_for_model,
                    pinned_context,
                    history_context,
                    viewport_summary,
                    json_context,
                    web_context_summary,
                )
                if message_type == "voice":
                    model_prompt = _apply_voice_response_contract(model_prompt, text)

                # Phase 93.3: Streaming via provider_registry
                agent_short_name = get_agent_short_name(requested_model)
                msg_id = str(uuid.uuid4())

                full_response = ""
                tokens_output = 0
                detected_provider = None
                capability_snapshot = None
                tool_execution_mode = "disabled_stream"

                try:
                    # Phase 93.3: Detect provider from model name (XAI/Grok support)
                    # Phase 111.9: Use model_source for multi-provider routing
                    from src.elisya.provider_registry import ProviderRegistry
                    detected_provider = ProviderRegistry.detect_provider(requested_model, source=model_source)
                    provider_instance = ProviderRegistry().get(detected_provider)
                    capability_snapshot = build_capability_snapshot(
                        model=requested_model,
                        provider_name=detected_provider.value,
                        provider_instance=provider_instance,
                        model_source=model_source,
                    )
                    wants_tools = _should_attempt_tools_in_stream(text)
                    tool_results = []
                    tool_execution_mode = resolve_tool_execution_mode(
                        wants_tools=wants_tools,
                        snapshot=capability_snapshot,
                        tools_executed=False,
                    )

                    if wants_tools and capability_snapshot.tool_calling and not capability_snapshot.tool_calling_in_stream:
                        try:
                            tool_results = await _run_pre_stream_tool_phase(
                                sio=sio,
                                sid=sid,
                                msg_id=msg_id,
                                requested_model=requested_model,
                            detected_provider=detected_provider,
                            model_prompt=model_prompt,
                            prefetch_context=prefetch_context,
                            )
                            tool_execution_mode = resolve_tool_execution_mode(
                                wants_tools=wants_tools,
                                snapshot=capability_snapshot,
                                tools_executed=bool(tool_results),
                            )
                        except Exception as tool_phase_err:
                            print(f"[MODEL_DIRECTORY] Pre-stream tool phase error: {tool_phase_err}")

                    # Emit stream start
                    await sio.emit(
                        "stream_start",
                        {
                            "id": msg_id,
                            "agent": agent_short_name,
                            "model": requested_model,
                            "model_source": model_source,
                            "tool_execution_mode": tool_execution_mode,
                            "capability_snapshot": capability_snapshot.to_dict(),
                        },
                        to=sid,
                    )

                    # MARKER_152.CLEANUP: Removed stream_meta telemetry + preflight tool exec
                    # G14 implementation: tools can run in pre-stream phase when stream tool-loop unavailable.
                    stream_system_prompt = "You are a VETKA AI agent with access to project context.\n\n"

                    if prefetch_context:
                        stream_system_prompt += (
                            "## Pre-fetched Codebase Search Results\n"
                            "The following results were found by searching the codebase "
                            "for the user's query. Reference them in your answer:\n\n"
                            + prefetch_context + "\n\n"
                        )

                    if tool_results:
                        formatted = []
                        for tr in tool_results[:8]:
                            if tr.get("success"):
                                formatted.append(
                                    f"- {tr.get('tool')}: success, result={str(tr.get('result'))[:600]}"
                                )
                            else:
                                formatted.append(
                                    f"- {tr.get('tool')}: error={str(tr.get('error'))[:200]}"
                                )
                        stream_system_prompt += (
                            "## Executed Tool Results (pre-stream phase)\n"
                            + "\n".join(formatted)
                            + "\n\n"
                        )

                    stream_system_prompt += (
                        "When responding, reference the pre-fetched codebase results above if relevant. "
                        "Provide clear, helpful answers based on the project context. "
                        "If no tool result section is present, do not claim that tools were executed."
                    )

                    stream_messages = [
                        {"role": "system", "content": stream_system_prompt},
                        {"role": "user", "content": model_prompt},
                    ]

                    # Use unified streaming (MARKER_152.CLEANUP: removed stream_event_cb noise)
                    async for token in call_model_v2_stream(
                        messages=stream_messages,
                        model=requested_model,
                        provider=detected_provider,
                        source=model_source,
                        temperature=0.7,
                    ):
                        if token:
                            full_response += token
                            tokens_output += 1
                            # Emit token to UI
                            await sio.emit(
                                "stream_token",
                                {"id": msg_id, "token": token},
                                to=sid,
                            )

                except XaiKeysExhausted:
                    # Phase 111.9: NO FALLBACK - user should change provider manually
                    print(f"[MODEL_DIRECTORY] XAI keys exhausted - NO FALLBACK")
                    full_response = "❌ XAI API keys exhausted. Please select a different provider or model."

                except Exception as stream_err:
                    print(f"[MODEL_DIRECTORY] Streaming error: {stream_err}")
                    full_response = f"Error: {str(stream_err)[:200]}"

                print(
                    f"[MODEL_DIRECTORY] Complete: {len(full_response)} chars, {tokens_output} tokens"
                )

                # Emit stream end
                await sio.emit(
                    "stream_end",
                    {
                        "id": msg_id,
                        "full_message": full_response,
                        "metadata": {
                            "tokens_output": tokens_output,
                                "tokens_input": len(model_prompt.split()),
                                "model": requested_model,
                                "agent": agent_short_name,
                                "tool_execution_mode": tool_execution_mode,
                                "capability_snapshot": capability_snapshot.to_dict() if capability_snapshot else {},
                            },
                        },
                        to=sid,
                    )

                voice_assistant_metadata = None
                if message_type == "voice":
                    logger.info(
                        "[MARKER_156.VOICE.S6_TRACE_T1_LLM_STREAM_END] msg_id=%s t_since_t0_ms=%.1f",
                        msg_id,
                        ((time.perf_counter() - voice_t0) * 1000.0) if voice_t0 else -1.0,
                    )
                    print(f"[MARKER_156.VOICE.S6_TRACE_T1_LLM_STREAM_END] msg_id={msg_id}")
                    _schedule_solo_voice_message(
                        msg_id=msg_id,
                        agent_name=agent_short_name,
                        model_name=requested_model,
                        provider_name=detected_provider.value if detected_provider else "unknown",
                        model_source_name=model_source,
                        full_text=full_response,
                    )

                # Save to chat history
                # Phase 74: Pass pinned_files for group chat context
                # MARKER_CHAT_HISTORY_ATTRIBUTION: Model attribution fix
                save_chat_message(
                    node_path,
                    {
                        "role": "assistant",
                        "agent": requested_model,
                        "model": requested_model,
                        "model_provider": detected_provider.value if detected_provider else "unknown",  # Provider from detection
                        "model_source": model_source,  # MARKER_115_BUG3
                        "text": full_response,
                        "node_id": node_id,
                        "message_type": "voice" if message_type == "voice" else "text",
                        "metadata": {
                            "model": requested_model,
                            "model_source": model_source,
                            "model_provider": detected_provider.value if detected_provider else "unknown",
                            **(voice_assistant_metadata or {}),
                        } if message_type == "voice" else {},
                    },
                    pinned_files=pinned_files,
                    chat_id=client_chat_id,
                )

                # Phase 51.4: Emit message_sent event for surprise calculation
                # MARKER_CHAT_NAMING: Fix 2/6 - Use semantic key for chat naming
                # FIX_109.4: Pass client_chat_id for unified ID system
                # MARKER_109_14: Prefer client_display_name
                try:
                    chat_history = get_chat_history_manager()
                    chat_display_name = client_display_name or extract_semantic_key(text)
                    chat_id = chat_history.get_or_create_chat(
                        'unknown',
                        context_type='topic',
                        display_name=chat_display_name,
                        chat_id=client_chat_id  # FIX_109.4
                    )
                    await emit_cam_event(
                        "message_sent",
                        {
                            "chat_id": chat_id,
                            "content": full_response,
                            "role": "assistant",
                        },
                        source="direct_model_call",
                    )
                except Exception as cam_err:
                    print(f"[CAM] Message event error (non-critical): {cam_err}")

                print(f"[MODEL_DIRECTORY] Direct model call complete")
                return  # Early return - skip agent chain!

            except Exception as e:
                print(f"[MODEL_DIRECTORY] Error: {e}")
                import traceback

                traceback.print_exc()
                await sio.emit(
                    "chat_response",
                    {
                        "message": f"Error calling {requested_model}: {str(e)[:200]}",
                        "agent": "System",
                        "model": "error",
                    },
                    to=sid,
                )
                return

        # ========================================
        # PHASE J-K: @MENTION PARSING
        # ========================================
        parsed_mentions = parse_mentions(text)
        clean_text = parsed_mentions["clean_message"]

        if parsed_mentions["mentions"]:
            print(
                f"[MENTIONS] Found: {[m['alias'] for m in parsed_mentions['mentions']]}"
            )
            print(
                f"[MENTIONS] Mode: {parsed_mentions['mode']}, Clean text: {clean_text[:50]}..."
            )

            # MARKER_117_3B: Check for system commands BEFORE model routing
            # @dragon, @doctor, @help etc. → dispatch to Mycelium pipeline
            try:
                from src.api.handlers.group_message_handler import MCP_AGENTS, HEARTBEAT_AGENTS
                mention_target = parsed_mentions["mentions"][0]["target"].lower()

                # Resolve alias (e.g., @help → doctor, @doc → doctor)
                resolved_agent = None
                if mention_target in MCP_AGENTS:
                    resolved_agent = mention_target
                else:
                    for _aid, _info in MCP_AGENTS.items():
                        if mention_target in _info.get("aliases", []):
                            resolved_agent = _aid
                            break

                if resolved_agent and resolved_agent in HEARTBEAT_AGENTS:
                    print(f"[MENTIONS] Phase 117.3b: System command @{mention_target} → @{resolved_agent} (solo chat)")

                    # MARKER_118.6: Notify user via chat_response (visible in ChatPanel)
                    await sio.emit("chat_response", {
                        "message": f"\U0001f525 @{resolved_agent} activated. Pipeline starting...",
                        "agent": resolved_agent,
                        "model": "system",
                    }, to=sid)

                    # Dispatch pipeline in background
                    # MARKER_117.7A: Pass client_chat_id so pipeline can emit progress to chat
                    # MARKER_118.7: Error callback — don't swallow exceptions silently
                    _dragon_task = asyncio.create_task(_dispatch_solo_system_command(
                        sio=sio,
                        sid=sid,
                        agent_id=resolved_agent,
                        content=text,
                        chat_id=client_chat_id,
                    ))

                    def _on_dragon_done(t):
                        exc = t.exception()
                        if exc:
                            logger.error(f"[SOLO_SYSTEM_CMD] Background task @{resolved_agent} failed: {exc}")

                    _dragon_task.add_done_callback(_on_dragon_done)
                    return  # Skip normal model routing
            except ImportError:
                pass  # Graceful fallback if group_message_handler unavailable

            # If specific model mentioned, use it directly (NOT agent)
            if parsed_mentions["mode"] == "single" and parsed_mentions["models"]:
                model_to_use = parsed_mentions["models"][0]
                is_ollama = model_to_use.startswith("ollama:")

                print(f"[MENTIONS] Direct MODEL call: {model_to_use}")

                # Emit routing status
                routing_text = f"Routing to **{model_to_use}**..."
                await sio.emit(
                    "agent_message",
                    {
                        "agent": "Hostess",
                        "model": "routing",
                        "content": routing_text,  # Phase 44.6
                        "text": routing_text,
                        "node_id": request_node_id,
                        "node_path": node_path,
                        "timestamp": request_timestamp,
                        "response_type": "status",
                        "force_artifact": False,
                    },
                    to=sid,
                )

                # ========================================
                # PHASE L: DIRECT MODEL CALL (bypass agents)
                # ========================================
                try:
                    # Phase 51.1: Load chat history
                    # MARKER_CHAT_NAMING: Fix 3/6 - Use semantic key for chat naming
                    # FIX_109.4: Pass client_chat_id for unified ID system
                    # MARKER_109_14: Prefer client_display_name
                    chat_history = get_chat_history_manager()
                    chat_display_name = client_display_name or extract_semantic_key(text)
                    chat_id = chat_history.get_or_create_chat(
                        'unknown',
                        context_type='topic',
                        display_name=chat_display_name,
                        chat_id=client_chat_id  # FIX_109.4
                    )
                    history_messages = chat_history.get_chat_messages(chat_id)
                    history_context = format_history_for_prompt(
                        history_messages, max_messages=10
                    )

                    print(
                        f"[PHASE_51.1] @mention call: Loaded {len(history_messages)} history messages"
                    )

                    # Get file context for the model
                    rich_context = sync_get_rich_context(node_path)
                    if rich_context.get("error"):
                        context_for_model = (
                            f"File: {node_path}\nStatus: {rich_context['error']}"
                        )
                    else:
                        context_for_model = format_context_for_agent(
                            rich_context, "generic"
                        )

                    # Phase 67: Build pinned files context with smart selection
                    packer = get_context_packer()
                    packed = await packer.pack(
                        user_query=clean_text,
                        pinned_files=pinned_files,
                        viewport_context=viewport_context,
                        session_id=sid,
                        model_name=model_to_use,
                        user_id="default",
                        zoom_level=float((viewport_context or {}).get("zoom_level", 1.0) or 1.0),
                    )
                    pinned_context = packed.pinned_context
                    viewport_summary = packed.viewport_summary
                    web_context_summary = build_web_context_summary(web_context)

                    # Phase 73: Build JSON dependency context for AI agents
                    # Packed JSON context + optional JEPA semantic core (Phase 157.1)
                    json_context = packed.json_context + packed.jepa_context

                    # Phase 64.5: Save user message BEFORE model call
                    # Phase 74: Pass pinned_files for group chat context
                    save_chat_message(
                        node_path,
                        {
                            "role": "user",
                            "text": text,  # Original text (with @mention)
                            "model_source": model_source,  # MARKER_115_BUG3
                            "node_id": node_id,
                        },
                        pinned_files=pinned_files,
                        chat_id=client_chat_id,
                    )

                    # Phase 64.3: Use extracted helper for prompt building
                    # Phase 71: Added viewport_summary parameter
                    # Phase 73: Added json_context parameter
                    model_prompt = build_model_prompt(
                        clean_text,
                        context_for_model,
                        pinned_context,
                        history_context,
                        viewport_summary,
                        json_context,
                        web_context_summary,
                    )
                    if message_type == "voice":
                        model_prompt = _apply_voice_response_contract(model_prompt, clean_text)

                    # Call the model directly
                    if is_ollama:
                        # Ollama model (e.g., ollama:qwen2:7b)
                        ollama_model = model_to_use.replace("ollama:", "")
                        print(f"[DIRECT] Calling Ollama: {ollama_model}")

                        # Phase 22: Get tools for direct model calls
                        from src.agents.tools import get_tools_for_agent
                        from src.tools import SafeToolExecutor, ToolCall

                        model_tools = get_tools_for_agent("Dev")  # Dev has most tools
                        print(f"[DIRECT] Tools available: {len(model_tools)}")

                        # Build messages with tool guidance
                        # MARKER_114.7b_OLLAMA_TOOL_NAMES: Updated to match registry names (Phase 114)
                        tool_system = """You have access to tools. Use them when appropriate:
- vetka_camera_focus: Move 3D camera to show user specific files/folders. USE THIS when asked to show/navigate/focus on something.
- vetka_search_semantic: Search codebase by meaning (Qdrant vector search)
- get_tree_context: Get file structure and dependencies
- search_codebase: Search by text/regex pattern
- vetka_edit_artifact: Create code artifacts for review

When user asks to "show", "focus", "navigate to" a file - USE vetka_camera_focus tool!
When user asks about code - USE vetka_search_semantic or read_code_file!"""

                        messages_with_tools = [
                            {"role": "system", "content": tool_system},
                            {"role": "user", "content": model_prompt},
                        ]

                        # Phase 93.3: Use call_model_v2 with tools instead of direct ollama.chat
                        ollama_response = await call_model_v2(
                            messages=messages_with_tools,
                            model=ollama_model,
                            provider=Provider.OLLAMA,
                            tools=model_tools,
                        )

                        # Phase 22: Handle tool calls from Ollama
                        # Phase 93.3: Adapted for call_model_v2 dict response format
                        response_text = None
                        message_data = ollama_response.get("message", {})
                        tool_calls = message_data.get("tool_calls", [])

                        if tool_calls:
                            print(f"[DIRECT] Tool calls received: {len(tool_calls)}")
                            executor = SafeToolExecutor()
                            tool_results = []

                            for tc in tool_calls:
                                # Handle both dict and object formats
                                if isinstance(tc, dict):
                                    func_name = tc.get("function", {}).get("name", "")
                                    func_args = tc.get("function", {}).get("arguments", {})
                                else:
                                    func_name = tc.function.name
                                    func_args = tc.function.arguments
                                print(f"[DIRECT] Executing: {func_name}({func_args})")

                                call = ToolCall(
                                    tool_name=func_name,
                                    arguments=func_args,
                                    agent_type="Dev",
                                    call_id=f"direct_{func_name}",
                                )
                                result = await executor.execute(call)

                                tool_results.append(
                                    {
                                        "tool": func_name,
                                        "args": func_args,
                                        "success": result.success,
                                        "result": result.result,
                                        "error": result.error,
                                    }
                                )
                                print(f"[DIRECT] Result: success={result.success}")

                            # Build response with tool execution info
                            if tool_results:
                                tool_summary = "\n".join(
                                    [
                                        f"* {tr['tool']}({tr['args']}) -> {tr['result'].get('message', 'done') if tr['success'] else tr['error']}"
                                        for tr in tool_results
                                    ]
                                )
                                response_text = f"Executed tools:\n{tool_summary}"

                                # If camera_focus was called, add friendly message
                                # MARKER_114.7d: Check both old and new name for compatibility
                                camera_calls = [
                                    tr
                                    for tr in tool_results
                                    if tr["tool"] in ("vetka_camera_focus", "camera_focus")
                                ]
                                if camera_calls:
                                    target = camera_calls[0]["args"].get(
                                        "target", "unknown"
                                    )
                                    response_text = f"Camera focused on: **{target}**\n\nThe 3D view should now be showing this location."

                        if response_text is None:
                            # No tool calls, get text response
                            # Phase 93.3: call_model_v2 returns dict format
                            response_text = message_data.get("content", "No response")
                    else:
                        # Phase 93.3: Use call_model_v2 for OpenRouter/XAI/POLZA models
                        print(f"[DIRECT] Calling via provider_registry: {model_to_use}")

                        # MARKER_FALLBACK_TOOLS: Get tools for non-Ollama models - IMPLEMENTED
                        from src.agents.tools import get_tools_for_agent
                        model_tools = get_tools_for_agent("Dev")  # Dev has most tools
                        print(f"[DIRECT] Tools available: {len(model_tools)}")

                        # MARKER_109_6_TOOL_GUIDANCE: Add tool guidance system message for ALL models
                        # MARKER_114.7c: Updated tool names to match registry (Phase 114)
                        tool_system = """You have access to tools. Use them when appropriate:
- vetka_camera_focus: Move 3D camera to show user specific files/folders. USE THIS when asked to show/navigate/focus on something.
- vetka_search_semantic: Search codebase by meaning/concept (Qdrant vector search)
- search_codebase: Search by text/regex pattern
- get_tree_context: Get file structure and dependencies
- read_code_file: Read file contents
- vetka_edit_artifact: Create code artifacts for review
- arc_suggest: Get creative suggestions for workflow improvements

When user asks to "show", "focus", "navigate to" a file - USE vetka_camera_focus tool!
When user asks about code - USE vetka_search_semantic or read_code_file!"""

                        try:
                            # Auto-detect provider using explicit source when available.
                            from src.elisya.provider_registry import ProviderRegistry
                            detected_provider = ProviderRegistry.detect_provider(
                                model_to_use, source=model_source
                            )

                            # Build messages with tool guidance (like Ollama path)
                            messages_with_tools = [
                                {"role": "system", "content": tool_system},
                                {"role": "user", "content": model_prompt},
                            ]

                            result = await call_model_v2(
                                messages=messages_with_tools,
                                model=model_to_use,
                                provider=detected_provider,
                                source=model_source,
                                temperature=0.7,
                                tools=model_tools,
                            )

                            # Handle tool calls for non-Ollama models
                            message_data = result.get("message", {})
                            tool_calls = message_data.get("tool_calls", [])

                            if tool_calls:
                                print(f"[DIRECT] Tool calls received: {len(tool_calls)}")
                                from src.tools import SafeToolExecutor, ToolCall
                                executor = SafeToolExecutor()
                                tool_results = []

                                for tc in tool_calls:
                                    # Handle both dict and object formats
                                    if isinstance(tc, dict):
                                        func = tc.get("function", {})
                                        tool_name = func.get("name", "unknown")
                                        try:
                                            tool_args = json.loads(func.get("arguments", "{}"))
                                        except:
                                            tool_args = {}
                                    else:
                                        tool_name = tc.function.name
                                        try:
                                            tool_args = json.loads(tc.function.arguments)
                                        except:
                                            tool_args = {}

                                    print(f"[DIRECT] Executing tool: {tool_name}({tool_args})")
                                    tool_call = ToolCall(name=tool_name, arguments=tool_args)
                                    result_obj = await executor.execute(tool_call)
                                    tool_results.append({
                                        "tool": tool_name,
                                        "result": result_obj.result if result_obj.success else result_obj.error
                                    })

                                # Format tool results for response
                                response_text = "Tool results:\n" + "\n".join(
                                    f"- {r['tool']}: {str(r['result'])[:500]}" for r in tool_results
                                )
                            else:
                                response_text = message_data.get("content", "No response")

                        except XaiKeysExhausted:
                            # Phase 111.10: NO FALLBACK between providers
                            # User should change provider manually
                            print(f"[DIRECT] XAI keys exhausted - NO FALLBACK")
                            response_text = "❌ XAI API keys exhausted. Please select a different provider or model."

                        except Exception as model_err:
                            print(f"[DIRECT] Model call error: {model_err}")
                            response_text = f"Error calling {model_to_use}: {str(model_err)[:100]}"

                    print(f"[DIRECT] Got response: {len(response_text)} chars")

                    # Emit the response
                    agent_short_name = model_to_use.split("/")[-1].split(":")[-1]
                    await sio.emit(
                        "agent_message",
                        {
                            "agent": agent_short_name,
                            "model": model_to_use,
                            "content": response_text,  # Phase 44.6: Frontend expects 'content'
                            "text": response_text,  # Backwards compatibility
                            "node_id": request_node_id,
                            "node_path": node_path,
                            "timestamp": request_timestamp,
                            "response_type": detect_response_type(response_text),
                            "force_artifact": len(response_text) > 800,
                        },
                        to=sid,
                    )

                    # Phase 44.6: Emit chat_response for chat panel
                    await sio.emit(
                        "chat_response",
                        {
                            "message": response_text,
                            "agent": agent_short_name,
                            "model": model_to_use,
                            "workflow_id": f"direct_{request_timestamp}",
                        },
                        to=sid,
                    )

                    # Save to chat history
                    # Phase 74: Pass pinned_files for group chat context
                    # MARKER_CHAT_HISTORY_ATTRIBUTION: Model attribution fix - IMPLEMENTED
                    save_chat_message(
                        node_path,
                        {
                            "role": "assistant",
                            "agent": model_to_use,
                            "model": model_to_use,
                            "model_provider": detected_provider.value if 'detected_provider' in locals() and detected_provider else "ollama",  # Provider from detection or default to ollama
                            "model_source": model_source,  # MARKER_115_BUG3
                            "text": response_text,
                            "node_id": node_id,
                        },
                        pinned_files=pinned_files,
                        chat_id=client_chat_id,
                    )

                    # Phase 51.4: Emit message_sent event for surprise calculation
                    # MARKER_CHAT_NAMING: Fix 4/6 - Use semantic key for chat naming
                    # FIX_109.4: Pass client_chat_id for unified ID system
                    # MARKER_109_14: Prefer client_display_name
                    try:
                        chat_history = get_chat_history_manager()
                        chat_display_name = client_display_name or extract_semantic_key(text)
                        chat_id = chat_history.get_or_create_chat(
                            'unknown',
                            context_type='topic',
                            display_name=chat_display_name,
                            chat_id=client_chat_id  # FIX_109.4
                        )
                        await emit_cam_event(
                            "message_sent",
                            {
                                "chat_id": chat_id,
                                "content": response_text,
                                "role": "assistant",
                            },
                            source="@mention_call",
                        )
                    except Exception as cam_err:
                        print(f"[CAM] Message event error (non-critical): {cam_err}")

                    print(f"[DIRECT] Direct model call complete")
                    return  # Early return - skip agent chain!

                except Exception as e:
                    print(f"[DIRECT] Error calling model: {e}")
                    error_msg = f"Error calling {model_to_use}: {str(e)[:200]}"
                    await sio.emit(
                        "agent_message",
                        {
                            "agent": "System",
                            "model": "error",
                            "content": error_msg,  # Phase 44.6
                            "text": error_msg,
                            "node_id": request_node_id,
                            "node_path": node_path,
                            "timestamp": request_timestamp,
                            "response_type": "error",
                            "force_artifact": False,
                        },
                        to=sid,
                    )
                    # Phase 44.6: Also emit chat_response for error
                    await sio.emit(
                        "chat_response",
                        {"message": error_msg, "agent": "System", "model": "error"},
                        to=sid,
                    )
                    return

        # Phase H: Save user message to chat history
        # Phase 74: Pass pinned_files for group chat context
        save_chat_message(
            node_path,
            {
                "role": "user",
                "text": text,
                "node_id": node_id,
                "model_source": model_source,
                "message_type": message_type,
                "metadata": message_metadata,
            },  # MARKER_115_BUG3
            pinned_files=pinned_files,
            chat_id=client_chat_id,
        )

        # Phase 51.4: Emit message_sent event for surprise calculation
        # MARKER_CHAT_NAMING: Fix 5/6 - Use semantic key for chat naming
        # MARKER_109_14: Prefer client_display_name
        try:
            chat_history = get_chat_history_manager()
            chat_display_name = client_display_name or extract_semantic_key(text)
            chat_id = chat_history.get_or_create_chat(
                'unknown',
                context_type='topic',
                display_name=chat_display_name,
                chat_id=client_chat_id  # MARKER_115_BUG1: Chat hygiene fix
            )
            await emit_cam_event(
                "message_sent",
                {"chat_id": chat_id, "content": text, "role": "user"},
                source="user_input",
            )
        except Exception as cam_err:
            print(f"[CAM] Message event error (non-critical): {cam_err}")

        # ========================================
        # PHASE E: HOSTESS AGENT ROUTING DECISION
        # Phase 44: Now uses rich context from HostessContextBuilder
        # ========================================
        hostess_decision = None
        if HOSTESS_AVAILABLE:
            try:
                hostess = get_hostess()

                # Phase 44: Build rich context for smarter routing
                context_builder = get_hostess_context_builder()
                if context_builder:
                    rich_context = context_builder.build_context(
                        message=text,
                        file_path=node_path,
                        conversation_id=client_id,
                        node_id=node_id,
                    )
                    print(
                        f"[HOSTESS] Rich context: file={rich_context.get('has_file_context')}, semantic={rich_context.get('has_semantic_context')}"
                    )
                else:
                    # Fallback to basic context
                    rich_context = {"node_path": node_path, "client_id": client_id}

                # Phase 57.9: Check if user is responding to pending key question
                if sid in pending_api_keys:
                    pending = pending_api_keys[sid]
                    pending_key = pending.get("key")
                    # Check if message looks like a provider name (short, no key pattern)
                    text_lower = text.strip().lower()
                    is_provider_response = (
                        len(text_lower) < 50
                        and not text_lower.startswith("sk-")
                        and not text_lower.startswith("aiza")
                        and "-" not in text_lower[:10]  # Not a key pattern
                    )

                    if pending_key and is_provider_response:
                        # User is telling us the provider name!
                        provider_name = (
                            text.strip()
                            .replace("@hostess", "")
                            .replace("@Hostess", "")
                            .strip()
                        )
                        print(
                            f"[HOSTESS] 🔑 User provided provider '{provider_name}' for pending key"
                        )

                        # Remove from pending
                        del pending_api_keys[sid]

                        # Call learn_api_key directly
                        try:
                            from src.elisya.key_learner import get_key_learner

                            learner = get_key_learner()
                            success, message = learner.learn_key_type(
                                pending_key, provider_name, save_key=True
                            )

                            if success:
                                response_text = f"✅ Learned {provider_name} key pattern! Key saved to config."
                            else:
                                response_text = f"Could not learn key: {message}"

                            await sio.emit(
                                "agent_message",
                                {
                                    "agent": "Hostess",
                                    "model": "qwen2.5:0.5b",
                                    "content": response_text,
                                    "text": response_text,
                                    "node_id": request_node_id,
                                    "node_path": node_path,
                                    "timestamp": request_timestamp,
                                    "response_type": "text",
                                    "force_artifact": False,
                                },
                                to=sid,
                            )
                            await sio.emit(
                                "chat_response",
                                {
                                    "message": response_text,
                                    "agent": "Hostess",
                                    "model": "qwen2.5:0.5b",
                                },
                                to=sid,
                            )

                            # Emit key_learned event
                            if success:
                                await sio.emit(
                                    "key_learned",
                                    {
                                        "provider": provider_name,
                                        "success": True,
                                        "message": response_text,
                                    },
                                    to=sid,
                                )

                            return
                        except Exception as e:
                            print(f"[HOSTESS] Error learning key: {e}")
                            # Continue to normal flow

                hostess_decision = hostess.process(text, context=rich_context)
                print(
                    f"[HOSTESS] Decision: {hostess_decision['action']} (confidence: {hostess_decision['confidence']:.2f})"
                )

                # Handle quick answers
                if hostess_decision["action"] == "quick_answer":
                    print(f"[HOSTESS] Responding directly to user")
                    quick_answer_text = hostess_decision["result"]
                    await sio.emit(
                        "agent_message",
                        {
                            "agent": "Hostess",
                            "model": "qwen2.5:0.5b",
                            "content": quick_answer_text,  # Phase 44.6
                            "text": quick_answer_text,
                            "node_id": request_node_id,
                            "node_path": node_path,
                            "timestamp": request_timestamp,
                            "response_type": "text",
                            "force_artifact": False,
                        },
                        to=sid,
                    )
                    # Phase 44.6: Emit chat_response
                    await sio.emit(
                        "chat_response",
                        {
                            "message": quick_answer_text,
                            "agent": "Hostess",
                            "model": "qwen2.5:0.5b",
                        },
                        to=sid,
                    )
                    return

                # Handle clarification requests
                elif hostess_decision["action"] == "clarify":
                    print(f"[HOSTESS] Asking for clarification")
                    options_text = ""
                    if hostess_decision.get("options"):
                        options_text = "\n\nOptions:\n" + "\n".join(
                            [f"* {opt}" for opt in hostess_decision["options"]]
                        )

                    clarify_text = hostess_decision["result"] + options_text
                    await sio.emit(
                        "agent_message",
                        {
                            "agent": "Hostess",
                            "model": "qwen2.5:0.5b",
                            "content": clarify_text,  # Phase 44.6
                            "text": clarify_text,
                            "node_id": request_node_id,
                            "node_path": node_path,
                            "timestamp": request_timestamp,
                            "response_type": "clarification",
                            "force_artifact": False,
                        },
                        to=sid,
                    )
                    # Phase 44.6: Emit chat_response
                    await sio.emit(
                        "chat_response",
                        {
                            "message": clarify_text,
                            "agent": "Hostess",
                            "model": "qwen2.5:0.5b",
                        },
                        to=sid,
                    )
                    return

                # Handle single agent calls
                elif hostess_decision["action"] == "agent_call":
                    print(
                        f"[HOSTESS] Routing to single agent: {hostess_decision['agent']}"
                    )
                    # Will handle this below after getting agents

                # Handle chain calls (full PM->Dev->QA)
                elif hostess_decision["action"] == "chain_call":
                    print(f"[HOSTESS] Routing to full agent chain")
                    # Will handle this below after getting agents

                # Handle search requests
                elif hostess_decision["action"] == "search":
                    print(
                        f"[HOSTESS] Routing to knowledge search: {hostess_decision['query']}"
                    )
                    search_text = f"[Search] Looking for: {hostess_decision['query']}\n\n(Search feature coming soon)"
                    await sio.emit(
                        "agent_message",
                        {
                            "agent": "Hostess",
                            "model": "qwen2.5:0.5b",
                            "content": search_text,  # Phase 44.6
                            "text": search_text,
                            "response_type": "text",
                        },
                        to=sid,
                    )
                    # Phase 44.6: Emit chat_response
                    await sio.emit(
                        "chat_response",
                        {
                            "message": search_text,
                            "agent": "Hostess",
                            "model": "qwen2.5:0.5b",
                        },
                        to=sid,
                    )
                    return

                # Handle camera focus requests
                elif hostess_decision["action"] == "camera_focus":
                    target = hostess_decision.get("target", "overview")
                    zoom = hostess_decision.get("zoom", "medium")
                    highlight = hostess_decision.get("highlight", True)
                    print(f"[HOSTESS] Camera focus: target={target}, zoom={zoom}")

                    # Emit camera control event
                    await sio.emit(
                        "camera_control",
                        {
                            "action": "focus",
                            "target": target,
                            "zoom": zoom,
                            "highlight": highlight,
                            "animate": True,
                        },
                        to=sid,
                    )

                    # Also send confirmation message
                    camera_text = f"Camera focused on: `{target}`..."
                    await sio.emit(
                        "agent_message",
                        {
                            "agent": "Hostess",
                            "model": "qwen2.5:0.5b",
                            "content": camera_text,  # Phase 44.6
                            "text": camera_text,
                            "response_type": "text",
                            "force_artifact": False,
                        },
                        to=sid,
                    )
                    # Phase 44.6: Emit chat_response
                    await sio.emit(
                        "chat_response",
                        {
                            "message": camera_text,
                            "agent": "Hostess",
                            "model": "qwen2.5:0.5b",
                        },
                        to=sid,
                    )
                    return

            except Exception as e:
                print(f"[HOSTESS] Error in decision: {e}, continuing with default flow")
                hostess_decision = None

        # ========================================
        # STEP 1: Get file context via Elisya (Task 3)
        # ========================================
        print(f"[Elisya] Reading rich context for {node_path}...")

        rich_context = sync_get_rich_context(node_path)

        if rich_context.get("error"):
            print(f"[Elisya] {rich_context['error']}")
            context_for_llm = (
                f"File: {node_path}\nStatus: Not accessible ({rich_context['error']})"
            )
            file_available = False
        else:
            file_content = rich_context.get("file_content", "")
            summary = f"Lines: {rich_context['file_metadata'].get('lines', 'N/A')} | Size: {rich_context['file_metadata'].get('size', 'N/A')} bytes"

            print(f"[Elisya] Got rich context: {summary}")
            file_available = True

            context_for_llm = format_context_for_agent(rich_context, "generic")

        # ========================================
        # STEP 2: Get agent instances
        # ========================================
        agents = get_agents()

        if not agents:
            print("[AGENTS] No agents available, falling back to template responses")
            for agent_name in ["PM", "Dev", "QA"]:
                fallback_text = f"[Fallback] I'm {agent_name}. Agents not initialized."
                await sio.emit(
                    "agent_message",
                    {
                        "agent": agent_name,
                        "model": "fallback",
                        "content": fallback_text,  # Phase 44.6
                        "text": fallback_text,
                        "node_id": request_node_id,
                        "node_path": node_path,
                        "timestamp": request_timestamp,
                        "context_provided": file_available,
                        "response_type": "text",
                        "force_artifact": False,
                    },
                    to=sid,
                )
                # Phase 44.6: Emit chat_response
                await sio.emit(
                    "chat_response",
                    {
                        "message": fallback_text,
                        "agent": agent_name,
                        "model": "fallback",
                    },
                    to=sid,
                )
            return

        # ========================================
        # STEP 3: Generate responses (all agents or specific one)
        # ========================================
        responses = []

        # Determine which agents to call based on Hostess decision
        agents_to_call = ["PM", "Dev", "QA"]  # Default: full chain
        single_mode = False

        # ========================================
        # PHASE 53: @MENTION TAKES PRIORITY!
        # Phase 57.9: @hostess uses Hostess routing, not agents loop
        # ========================================
        if parsed_mentions.get("mode") == "agents" and parsed_mentions.get("agents"):
            mention_agents = parsed_mentions["agents"]

            # Phase 57.9: If @hostess is mentioned, let Hostess process (she's not in agents dict)
            if "Hostess" in mention_agents:
                # Remove Hostess from list, let her decide routing
                mention_agents = [a for a in mention_agents if a != "Hostess"]
                if not mention_agents:
                    # Only @hostess was mentioned - use Hostess decision
                    print(f"[ROUTING] 🎯 @hostess DIRECT - using Hostess routing")
                    # hostess_decision already set above, continue to elif
                else:
                    # @hostess + other agents - call other agents
                    agents_to_call = mention_agents
                    single_mode = len(agents_to_call) == 1
                    print(f"[ROUTING] 🎯 @mention + @hostess: calling {agents_to_call}")
                    hostess_decision = None
            else:
                agents_to_call = mention_agents
                single_mode = len(agents_to_call) == 1
                print(
                    f"[ROUTING] 🎯 @mention DIRECT CALL: {agents_to_call} (bypassing Hostess)"
                )
                hostess_decision = None

        if hostess_decision:
            action = hostess_decision.get("action", "")

            if action == "quick_answer":
                agents_to_call = []
                print(f"[ROUTING] Quick answer - no agents needed")

            elif action == "show_file":
                agents_to_call = ["Dev"]
                single_mode = True
                print(f"[ROUTING] Show file - Dev only")

            elif action == "agent_call":
                specific_agent = hostess_decision.get("agent", "Dev")
                agents_to_call = [specific_agent]
                single_mode = True
                print(f"[ROUTING] Single agent: {specific_agent}")

            elif action == "chain_call":
                agents_to_call = ["PM", "Dev", "QA"]
                single_mode = False
                print(f"[ROUTING] Full chain: PM -> Dev -> QA")

            elif action == "clarify":
                agents_to_call = []
                print(f"[ROUTING] Clarification - no agents needed")

            elif action == "search":
                agents_to_call = []
                print(f"[ROUTING] Search - no agents needed")

            # Phase 57.9: API Key handling actions
            elif action == "ask_provider":
                # Hostess is asking user what service the key is for
                agents_to_call = []
                print(
                    f"[ROUTING] ask_provider - saving pending key for session {sid[:8]}"
                )

                # Save the pending key for when user responds with provider name
                pending_key = hostess_decision.get("pending_key")
                if pending_key:
                    pending_api_keys[sid] = {
                        "key": pending_key,
                        "timestamp": time.time(),
                    }
                    print(
                        f"[ROUTING] Saved pending key (prefix: {pending_key[:10]}...) for session {sid[:8]}"
                    )

                # Emit Hostess's question to user
                hostess_response = hostess_decision.get(
                    "result", "I don't recognize this key. What service is it for?"
                )
                await sio.emit(
                    "agent_message",
                    {
                        "agent": "Hostess",
                        "model": "qwen2.5:0.5b",
                        "content": hostess_response,
                        "text": hostess_response,
                        "node_id": request_node_id,
                        "node_path": node_path,
                        "timestamp": request_timestamp,
                        "response_type": "text",
                        "force_artifact": False,
                    },
                    to=sid,
                )
                await sio.emit(
                    "chat_response",
                    {
                        "message": hostess_response,
                        "agent": "Hostess",
                        "model": "qwen2.5:0.5b",
                    },
                    to=sid,
                )
                return

            elif action in (
                "save_api_key",
                "learn_api_key",
                "analyze_unknown_key",
                "get_api_key_status",
            ):
                agents_to_call = []
                print(f"[ROUTING] API Key action '{action}' - Hostess handled it")

                # Hostess already executed the tool, emit her response
                hostess_response = hostess_decision.get(
                    "result", "API key operation completed."
                )
                await sio.emit(
                    "agent_message",
                    {
                        "agent": "Hostess",
                        "model": "qwen2.5:0.5b",
                        "content": hostess_response,
                        "text": hostess_response,
                        "node_id": request_node_id,
                        "node_path": node_path,
                        "timestamp": request_timestamp,
                        "response_type": "text",
                        "force_artifact": False,
                    },
                    to=sid,
                )
                await sio.emit(
                    "chat_response",
                    {
                        "message": hostess_response,
                        "agent": "Hostess",
                        "model": "qwen2.5:0.5b",
                    },
                    to=sid,
                )
                return

            else:
                # Phase 57.9: Unknown Hostess action - let Hostess respond directly
                agents_to_call = []
                print(f"[ROUTING] Unknown action '{action}' - Hostess will respond")

                # Phase 57.9: Emit Hostess response for unknown actions
                hostess_response = hostess_decision.get(
                    "result",
                    f"I received your request but I'm not sure how to handle '{action}'. Can you please clarify?",
                )
                await sio.emit(
                    "agent_message",
                    {
                        "agent": "Hostess",
                        "model": "qwen2.5:0.5b",
                        "content": hostess_response,
                        "text": hostess_response,
                        "node_id": request_node_id,
                        "node_path": node_path,
                        "timestamp": request_timestamp,
                        "response_type": "text",
                        "force_artifact": False,
                    },
                    to=sid,
                )
                await sio.emit(
                    "chat_response",
                    {
                        "message": hostess_response,
                        "agent": "Hostess",
                        "model": "qwen2.5:0.5b",
                    },
                    to=sid,
                )
                return

        # ========================================
        # PHASE 17-J: CHAIN CONTEXT PASSING
        # ========================================
        previous_outputs = {}
        all_artifacts = []

        for agent_name in agents_to_call:
            if agent_name not in agents:
                continue

            agent_config = agents[agent_name]
            agent_instance = agent_config["instance"]
            system_prompt = agent_config["system_prompt"]

            if not agent_instance:
                print(f"[Agent] {agent_name}: Instance is None")
                continue

            print(f"[Agent] {agent_name}: Generating LLM response...")

            try:
                # ========================================
                # PHASE 17-J: BUILD PROMPT WITH CHAIN CONTEXT
                # Phase 67: Include pinned files context with smart selection
                # ========================================
                # Phase 67: Build pinned context with user query for relevance ranking
                agent_pinned_context = (
                    build_pinned_context(pinned_files, user_query=text)
                    if pinned_files
                    else ""
                )

                if ROLE_PROMPTS_AVAILABLE:
                    full_prompt = build_full_prompt(
                        agent_type=agent_name,
                        user_message=text,
                        file_context=context_for_llm,
                        previous_outputs=previous_outputs,
                        pinned_context=agent_pinned_context,
                    )
                    max_tokens = 999999  # Phase 92.4: Unlimited responses
                    print(
                        f"[Agent] {agent_name}: Using Phase 17-J chain-aware prompt (pinned: {len(pinned_files)} files)"
                    )
                else:
                    # Phase 61: Include pinned context in fallback prompt
                    full_prompt = f"""
{system_prompt}

{context_for_llm}

{agent_pinned_context}---
USER QUESTION: {text}
---

Provide your {agent_name} analysis:
"""
                    max_tokens = 999999  # Phase 92.4: Unlimited responses

                # Phase 46: Try streaming for single agent mode (first agent)
                use_streaming = single_mode and HOST_HAS_OLLAMA and len(responses) == 0

                if use_streaming:
                    # Stream response for better UX
                    print(f"[Agent] {agent_name}: Using streaming mode")
                    model_for_stream = (
                        get_agent_model_name(agent_instance)
                        if agent_instance
                        else "qwen2.5vl:3b"
                    )
                    response_text, token_count = await stream_response(
                        sio,
                        sid,
                        full_prompt,
                        agent_name,
                        model_for_stream,
                        request_node_id,
                        node_path,
                    )
                    print(f"[Agent] {agent_name}: Streamed {token_count} tokens")
                else:
                    # MARKER_SOLO_ORCHESTRATOR FIX: Route through orchestrator for CAM/metrics/tools - IMPLEMENTED
                    # Run sync LLM call in executor (non-streaming)
                    from src.orchestration.orchestrator_with_elisya import OrchestratorWithElisya

                    try:
                        # Get or create orchestrator instance
                        orchestrator = OrchestratorWithElisya()

                        # Extract model name from agent instance
                        model_name = get_agent_model_name(agent_instance) if agent_instance else "auto"

                        # Call through orchestrator for full CAM/semantic integration
                        result = await orchestrator.call_agent(
                            agent_type=agent_name,
                            model_id=model_name,
                            prompt=full_prompt,
                            context={"file_path": node_path} if node_path and node_path not in ("unknown", "root") else {}
                        )

                        response_text = result.get("output", "")
                        if result.get("status") == "error":
                            error_msg = result.get("error", "Unknown error")
                            print(f"[Agent] {agent_name}: Orchestrator error - {error_msg}")
                            response_text = f"[{agent_name}] Error: {error_msg}"

                    except Exception as orch_err:
                        # Fallback to direct call if orchestrator fails
                        print(f"[Agent] {agent_name}: Orchestrator failed, using direct call - {orch_err}")
                        loop = asyncio.get_event_loop()
                        response_text = await loop.run_in_executor(
                            None,
                            lambda: agent_instance.call_llm(
                                prompt=full_prompt, max_tokens=max_tokens
                            ),
                        )

                    # Handle if response is dict
                    if isinstance(response_text, dict):
                        response_text = response_text.get(
                            "response", response_text.get("content", str(response_text))
                        )

                response_text = (
                    str(response_text)
                    if response_text
                    else f"[{agent_name}] No response generated"
                )

                print(f"[Agent] {agent_name}: Generated {len(response_text)} chars")

                # ========================================
                # PHASE 17-J: SAVE OUTPUT FOR NEXT AGENT
                # ========================================
                previous_outputs[agent_name] = response_text

                # ========================================
                # PHASE 17-J: EXTRACT ARTIFACTS FROM DEV
                # ========================================
                if agent_name == "Dev" and ROLE_PROMPTS_AVAILABLE:
                    artifacts = extract_artifacts(response_text, agent_name)
                    if artifacts:
                        all_artifacts.extend(artifacts)
                        print(f"[Agent] Dev: Extracted {len(artifacts)} artifact(s)")
                        for artifact in artifacts:
                            print(
                                f"         -> {artifact['filename']} ({artifact['lines']} lines)"
                            )

                # ========================================
                # PHASE 17-J: EXTRACT QA SCORE
                # ========================================
                if agent_name == "QA" and ROLE_PROMPTS_AVAILABLE:
                    qa_score = extract_qa_score(response_text)
                    qa_verdict = extract_qa_verdict(response_text)
                    if qa_score is not None:
                        print(
                            f"[Agent] QA: Score: {qa_score:.2f}/1.0, Verdict: {qa_verdict or 'N/A'}"
                        )

            except Exception as e:
                print(f"[Agent] {agent_name}: LLM error - {e}")
                response_text = f"[{agent_name}] Sorry, I encountered an error generating the response: {str(e)[:200]}"

            model_name = (
                get_agent_model_name(agent_instance) if agent_instance else "unknown"
            )

            responses.append(
                {
                    "agent": agent_name,
                    "model": model_name,
                    "text": response_text,
                    "node_id": request_node_id,
                    "node_path": node_path,
                    "timestamp": request_timestamp,
                }
            )

        # ========================================
        # STEP 4: Emit ALL responses to client
        # Phase 44.6: Fixed to emit both agent_message and chat_response
        # ========================================
        for i, resp in enumerate(responses):
            if i > 0:
                await asyncio.sleep(0.15)

            response_type = detect_response_type(resp["text"])
            force_artifact = len(resp["text"]) > 800

            # Emit agent_message (for 3D panel - expects 'content')
            await sio.emit(
                "agent_message",
                {
                    "agent": resp["agent"],
                    "model": resp["model"],
                    "content": resp[
                        "text"
                    ],  # Phase 44.6: Frontend expects 'content' not 'text'
                    "text": resp["text"],  # Keep for backwards compatibility
                    "node_id": resp["node_id"],
                    "node_path": resp["node_path"],
                    "timestamp": resp["timestamp"],
                    "context_provided": file_available,
                    "response_type": response_type,
                    "force_artifact": force_artifact,
                },
                to=sid,
            )

            # Phase 44.6: Emit chat_response (for chat panel - expects 'message')
            await sio.emit(
                "chat_response",
                {
                    "message": resp["text"],  # Frontend expects 'message' field
                    "agent": resp["agent"],
                    "model": resp["model"],
                    "workflow_id": f"chat_{request_timestamp}",
                },
                to=sid,
            )

            # Phase 53: Add agent response to per-session history
            chat_manager.add_message(
                Message(
                    role="assistant",
                    content=resp["text"],
                    agent=resp["agent"],
                    node_path=node_path,
                )
            )

            # Phase 74: Pass pinned_files for group chat context
            save_chat_message(
                node_path,
                {
                    "role": "agent",
                    "agent": resp["agent"],
                    "model": resp["model"],
                    "model_source": resp.get("model_source", model_source),  # MARKER_115_BUG3: fallback to outer scope
                    "text": resp["text"],
                    "node_id": resp["node_id"],
                },
                pinned_files=pinned_files,
                chat_id=client_chat_id,
            )

            # Phase 51.4: Emit message_sent event for surprise calculation
            # MARKER_CHAT_NAMING: Fix 6/6 - Use semantic key for chat naming
            # MARKER_109_14: Prefer client_display_name
            try:
                chat_history = get_chat_history_manager()
                chat_display_name = client_display_name or extract_semantic_key(text)
                chat_id = chat_history.get_or_create_chat(
                    'unknown',
                    context_type='topic',
                    display_name=chat_display_name,
                    chat_id=client_chat_id  # MARKER_115_BUG1: Chat hygiene fix
                )
                await emit_cam_event(
                    "message_sent",
                    {"chat_id": chat_id, "content": resp["text"], "role": "assistant"},
                    source=f"agent_chain_{resp['agent']}",
                )
            except Exception as cam_err:
                print(f"[CAM] Message event error (non-critical): {cam_err}")

            print(f"[SOCKET] Sent {resp['agent']} response ({len(resp['text'])} chars)")

        print(f"[SOCKET] All {len(responses)} agent responses sent")

        # ========================================
        # PHASE 17-J: LOG EXTRACTED ARTIFACTS
        # ========================================
        if all_artifacts:
            print(
                f"[ARTIFACT] Extracted {len(all_artifacts)} artifact(s) from Dev response:"
            )
            for artifact in all_artifacts:
                print(
                    f"         -> {artifact['filename']} ({artifact['language']}, {artifact['lines']} lines)"
                )

        # ========================================
        # STEP 5: Generate summary for multi-agent chains
        # ========================================
        if not single_mode and len(responses) > 1:

            def generate_simple_summary(responses: list) -> str:
                """Simple summary without LLM - clean English output"""
                parts = []
                for resp in responses:
                    response = resp["text"]
                    agent = resp["agent"]
                    first_sentence = response.split(".")[0].strip()
                    if first_sentence and not first_sentence.endswith((".", "!", "?")):
                        first_sentence += "."
                    parts.append(f"**{agent}**: {first_sentence}")
                return "**Team Summary:**\n" + "\n".join(parts)

            print(f"[SOCKET] Generating summary for multi-agent chain...")
            try:
                summary_text = "\n\n".join(
                    [
                        f"**{resp['agent']}**: {resp['text'][:300]}..."
                        for resp in responses
                    ]
                )

                summary_prompt = f"""Based on the team's analysis:

{summary_text}

Write a brief summary (3-4 sentences) covering:
- Main recommendations
- Key risks
- Action items

IMPORTANT: Return ONLY plain text. Do NOT use JSON format. Do NOT use markdown code blocks."""

                def parse_llm_summary(response_text: str) -> str:
                    """Safely parse LLM response, handling JSON and text"""
                    if not response_text:
                        return "Unable to generate summary"

                    text = str(response_text).strip()

                    if not text.startswith("{"):
                        return text

                    try:
                        import re

                        json_match = re.search(r"\{[^{}]*\}", text)
                        if json_match:
                            data = json.loads(json_match.group())
                            return data.get(
                                "summary", data.get("text", data.get("content", text))
                            )
                    except:
                        pass

                    try:
                        first_line = text.split("\n")[0]
                        if first_line.startswith("{"):
                            data = json.loads(first_line)
                            return data.get("summary", data.get("text", str(data)))
                    except:
                        pass

                    return text

                agents = get_agents()
                if agents and agents.get("Dev"):
                    loop = asyncio.get_event_loop()
                    summary_response = await loop.run_in_executor(
                        None,
                        lambda: agents["Dev"]["instance"].call_llm(
                            prompt=summary_prompt, max_tokens=200
                        ),
                    )

                    if isinstance(summary_response, dict):
                        summary_response = summary_response.get(
                            "response",
                            summary_response.get("content", str(summary_response)),
                        )

                    summary_text = parse_llm_summary(summary_response)
                else:
                    summary_text = (
                        f"Summary of {len(responses)} agent analyses completed."
                    )

                await sio.emit(
                    "agent_message",
                    {
                        "agent": "Summary",
                        "model": "auto",
                        "content": summary_text,  # Phase 44.6
                        "text": summary_text,
                        "node_id": request_node_id,
                        "node_path": node_path,
                        "timestamp": request_timestamp,
                        "response_type": "summary",
                        "force_artifact": False,
                    },
                    to=sid,
                )
                # Phase 44.6: Emit chat_response for summary
                await sio.emit(
                    "chat_response",
                    {"message": summary_text, "agent": "Summary", "model": "auto"},
                    to=sid,
                )

                print(f"[SOCKET] Summary generated ({len(summary_text)} chars)")

                await asyncio.sleep(0.2)
                await sio.emit(
                    "quick_actions",
                    {
                        "node_path": node_path,
                        "agent": "Summary",
                        "options": [
                            {"label": "Accept", "action": "accept", "emoji": "check"},
                            {"label": "Refine", "action": "refine", "emoji": "edit"},
                            {"label": "Reject", "action": "reject", "emoji": "x"},
                        ],
                    },
                    to=sid,
                )
            except Exception as e:
                print(
                    f"[SOCKET] Error generating summary: {e}, attempting simple fallback"
                )

                summary_text = generate_simple_summary(responses)

                await sio.emit(
                    "agent_message",
                    {
                        "agent": "Summary",
                        "model": "fallback",
                        "content": summary_text,  # Phase 44.6
                        "text": summary_text,
                        "node_id": request_node_id,
                        "node_path": node_path,
                        "timestamp": request_timestamp,
                        "response_type": "summary",
                        "force_artifact": False,
                    },
                    to=sid,
                )
                # Phase 44.6: Emit chat_response for fallback summary
                await sio.emit(
                    "chat_response",
                    {"message": summary_text, "agent": "Summary", "model": "fallback"},
                    to=sid,
                )

        # ========================================
        # STEP 6: Emit quick actions for single mode
        # ========================================
        if single_mode and len(responses) > 0:
            print(f"[SOCKET] Emitting quick actions for single agent response")
            await sio.emit(
                "quick_actions",
                {
                    "node_path": node_path,
                    "agent": responses[0]["agent"],
                    "options": [
                        {
                            "label": "Details",
                            "action": "detailed_analysis",
                            "emoji": "search",
                        },
                        {"label": "Improve", "action": "improve", "emoji": "edit"},
                        {"label": "Tests", "action": "run_tests", "emoji": "test"},
                        {
                            "label": "Full Team",
                            "action": "full_chain",
                            "emoji": "users",
                        },
                    ],
                },
                to=sid,
            )

        # ========================================
        # Phase 51.3: Event-Driven CAM for Single Agent Calls
        # ========================================
        if all_artifacts and len(all_artifacts) > 0:
            try:
                # Import event-driven CAM handler
                from src.orchestration.cam_event_handler import emit_artifact_event

                print(
                    f"[CAM] Single agent produced {len(all_artifacts)} artifact(s), emitting events..."
                )

                # Emit CAM event for each artifact
                for artifact in all_artifacts:
                    artifact_path = artifact.get("filename", "unknown")
                    artifact_content = artifact.get("code", "")
                    source_agent = artifact.get("agent", "Dev")  # Fallback to Dev

                    # Emit artifact event (replaces 30+ lines of direct CAM calls)
                    await emit_artifact_event(
                        artifact_path=artifact_path,
                        artifact_content=artifact_content,
                        source_agent=source_agent,
                    )

                print(f"[CAM] Single agent CAM events emitted")

            except Exception as cam_error:
                print(f"[CAM] Single agent CAM error (non-critical): {cam_error}")

        print(f"[SOCKET] Processing complete\n")


# MARKER_117_3B: Solo chat system command dispatch
# MARKER_117.7A: Added chat_id parameter to pass client_chat_id for pipeline progress
async def _dispatch_solo_system_command(sio, sid: str, agent_id: str, content: str, chat_id: str = None):
    """
    Phase 117.3b: Dispatch system command from solo chat to Mycelium pipeline.

    Unlike group dispatch, solo chat streams results via SocketIO to=sid
    instead of HTTP POST to group endpoint.

    Args:
        chat_id: Optional client-provided chat_id for pipeline progress emission (MARKER_117.7A)
    """
    import re as _re

    # Extract task text (remove @mention prefix)
    task_text = _re.sub(r"@\w+\s*", "", content, count=1).strip()
    if not task_text:
        task_text = f"General {agent_id} diagnostic requested"

    from src.api.handlers.group_message_handler import _SYSTEM_COMMAND_PHASES
    phase_type = _SYSTEM_COMMAND_PHASES.get(agent_id, "build")

    print(f"[SOLO_SYSTEM_CMD] @{agent_id} | phase={phase_type} | task={task_text[:80]}")

    try:
        from src.orchestration.agent_pipeline import AgentPipeline

        # MARKER_117.8A: Pass sio+sid for SocketIO direct emit (non-blocking)
        # Previously: sync httpx.Client(5s) × 20 emits = VETKA freeze
        # Now: async sio.emit() → instant, no blocking
        pipeline = AgentPipeline(chat_id=chat_id, sio=sio, sid=sid)
        result = await pipeline.execute(task_text, phase_type)

        # Build expanded report
        completed = result.get("results", {}).get("subtasks_completed", "?") if result else "?"
        total = result.get("results", {}).get("subtasks_total", "?") if result else "?"
        status = result.get("status", "unknown") if result else "unknown"

        report_lines = [f"\u2705 @{agent_id} complete: {completed}/{total} subtasks ({status})"]

        # Add subtask details
        subtasks = result.get("subtasks", []) if result else []
        for i, st in enumerate(subtasks[:5]):  # Max 5 subtasks in report
            s_icon = "\u2705" if st.get("status") == "done" else "\u274c"
            marker = st.get("marker") or f"step_{i+1}"
            desc = st.get("description", "")[:80]
            report_lines.append(f"  {s_icon} {marker}: {desc}")
            if st.get("result"):
                preview = str(st["result"])[:150].replace('\n', ' ')
                report_lines.append(f"     \u2514 {preview}")

        # MARKER_118.6: Use chat_response so ChatPanel renders the final report
        await sio.emit("chat_response", {
            "message": "\n".join(report_lines),
            "agent": agent_id,
            "model": "system",
        }, to=sid)

    except Exception as e:
        print(f"[SOLO_SYSTEM_CMD] @{agent_id} failed: {e}")
        # MARKER_118.6: Error also via chat_response for visibility
        await sio.emit("chat_response", {
            "message": f"\u274c @{agent_id} failed: {str(e)[:200]}",
            "agent": agent_id,
            "model": "system",
        }, to=sid)
