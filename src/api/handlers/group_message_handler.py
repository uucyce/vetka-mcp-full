"""
Group Message Socket.IO Handler with Streaming Support

@file group_message_handler.py
@status ACTIVE
@phase Phase 80.13 - MCP @mention Routing
@lastUpdate 2026-01-22

Handles:
- Group message routing with @mentions
- Streaming responses from AI agents (via orchestrator)
- Multi-agent conversations in groups
- Full Elisya context integration
- Phase 57.8: Hostess as intelligent router for groups
- Phase 80.13: MCP agent @mention routing (browser_haiku, claude_code)

Phase 57.4: Now uses orchestrator.call_agent() instead of direct HTTP.
This gives us: Elisya context, CAM metrics, semantic search, proper key rotation.

Phase 57.8: Hostess now acts as the group router:
- Without @mention: Hostess analyzes and decides who responds
- Simple questions: Hostess answers directly
- Tasks/projects: Hostess delegates to Architect

Phase 80.13: MCP Agent @mention routing:
- When user @mentions browser_haiku or claude_code
- System notifies MCP agent via dedicated mechanism
- MCP agents can respond through debug API endpoints
"""

import asyncio
import os
import uuid
import time
import logging
import json
import re
import base64

logger = logging.getLogger(__name__)

# Global SocketIO reference for tools
_socketio_instance = None


def set_socketio(sio):
    """Set global SocketIO instance for artifact tools."""
    global _socketio_instance
    _socketio_instance = sio


def get_socketio():
    """Get global SocketIO instance."""
    return _socketio_instance


from src.services.group_chat_manager import (
    get_group_chat_manager,
    GroupParticipant,
    GroupRole,
)
from src.initialization.components_init import get_orchestrator
from src.chat.chat_history_manager import get_chat_history_manager
from src.agents.role_prompts import (
    PM_SYSTEM_PROMPT,
    DEV_SYSTEM_PROMPT,
    QA_SYSTEM_PROMPT,
    ARCHITECT_SYSTEM_PROMPT,
    RESEARCHER_SYSTEM_PROMPT,
    get_agent_prompt,
)
from src.voice.voice_assignment_registry import get_voice_assignment_registry

# Phase 55.1: MCP session init
from src.mcp.tools.session_tools import vetka_session_init

# ============================================================================
# PHASE 80.13: MCP AGENT @MENTION ROUTING
# ============================================================================
# MCP agents are external (browser_haiku, claude_code) and not group participants.
# When @mentioned, we notify them via dedicated mechanism.

MCP_AGENTS = {
    "browser_haiku": {
        "name": "Browser Haiku",
        "endpoint": "mcp/browser_haiku",
        "icon": "eye",
        "role": "Tester",
        "aliases": ["browserhaiku", "browser", "haiku"],
    },
    "claude_code": {
        "name": "Claude Code",
        "endpoint": "mcp/claude_code",
        "icon": "terminal",
        "role": "Executor",
        "aliases": ["claudecode", "claude", "code"],
    },
    # MARKER_117_3: System commands — dev tools that auto-dispatch to Mycelium pipeline
    "dragon": {
        "name": "Dragon",
        "endpoint": "mcp/dragon",
        "icon": "flame",
        "role": "Orchestrator",
        "aliases": ["dragon", "mcp/dragon"],
    },
    "doctor": {
        "name": "Doctor",
        "endpoint": "mcp/doctor",
        "icon": "stethoscope",
        "role": "Diagnostic",
        "aliases": ["doctor", "doc", "help", "support", "mcp/doctor"],
    },
    "mycelium": {
        "name": "Mycelium Pipeline",
        "endpoint": "mcp/mycelium",
        "icon": "git-branch",
        "role": "Builder",
        "aliases": ["mycelium", "pipeline", "mcp/pipeline", "mcp/mycelium"],
    },
    # MARKER_117_3_RESERVES: Future system commands (registered to prevent Ollama hijack)
    "grok": {
        "name": "Grok Detective",
        "endpoint": "mcp/grok",
        "icon": "search",
        "role": "Investigator",
        "aliases": ["grok", "detective", "mcp/grok"],
    },
    "haiku_scout": {
        "name": "Haiku Scout",
        "endpoint": "mcp/haiku_scout",
        "icon": "zap",
        "role": "Recon",
        "aliases": ["haiku_scout", "scout", "mcp/haiku_scout"],
    },
    "opus": {
        "name": "Opus All-Stars",
        "endpoint": "mcp/opus",
        "icon": "star",
        "role": "Dream Team",
        "aliases": ["opus", "all-stars", "dreamteam", "mcp/opus"],
    },
    "gemini": {
        "name": "Gemini Heavy",
        "endpoint": "mcp/gemini",
        "icon": "rocket",
        "role": "Heavy Lifter",
        "aliases": ["gemini", "heavy", "mcp/gemini"],
    },
}

# MARKER_117_3: Agents that auto-dispatch to Mycelium pipeline on @mention
HEARTBEAT_AGENTS = {"dragon", "doctor", "mycelium", "pipeline"}  # pipeline kept as alias


def _normalize_agent_role(raw_agent_id: str) -> str:
    role = (raw_agent_id or "").strip().lower().replace("@", "")
    return role or "unknown"


def _language_for_text(text: str) -> str:
    return "ru" if re.search(r"[А-Яа-яЁё]", text or "") else "en"


def _waveform_from_audio(audio_bytes: bytes, points: int = 48) -> list:
    # Coarse waveform proxy from raw bytes for UI timeline preview.
    if not audio_bytes:
        return []
    length = len(audio_bytes)
    step = max(1, length // points)
    out = []
    for i in range(0, length, step):
        chunk = audio_bytes[i : i + step]
        if not chunk:
            continue
        mean_val = sum(chunk) / len(chunk)
        out.append(round(abs(mean_val - 128.0) / 128.0, 4))
        if len(out) >= points:
            break
    return out


async def _resolve_group_voice_assignment(
    *,
    group_id: str,
    agent_id: str,
    model_source: str | None,
    model_id: str | None,
) -> dict:
    """
    Resolve stable voice lock for group+role.
    Returns empty dict on failure.
    """
    try:
        registry = get_voice_assignment_registry()
        role_norm = _normalize_agent_role(agent_id)
        return await registry.get_or_assign_group_role(
            group_id=group_id or "unknown_group",
            role=role_norm,
            provider=model_source or "unknown",
            model_id=model_id or "unknown",
            tts_provider="qwen3",
        )
    except Exception as exc:
        logger.warning("[VOICE_S2] assignment fallback for %s/%s: %s", model_source, model_id, exc)
        return {}


def _build_voice_contract_stub(
    *,
    group_id: str,
    message_id: str,
    agent_id: str,
    model_id: str,
    model_source: str = None,
    full_message: str = "",
) -> dict:
    """
    MARKER_156.VOICE.S1_BACKEND_STUB: Voice message contract payload (S1 scaffold).
    S1 emits schema-complete placeholders before full TTS pipeline lands.
    """
    provider = model_source or "unknown"
    model_identity_key = f"{provider}:{model_id}" if model_id else provider

    return {
        "id": message_id,
        "group_id": group_id,
        "agent_id": agent_id,
        "full_message": full_message,
        "text_preview": (full_message or "")[:160],
        "metadata": {
            "model": model_id,
            "model_source": model_source,
            "voice_contract_version": "s1",
            "voice_enabled": False,
            "voice_reason": "S1_contract_only_no_tts_pipeline",
            "audio": {
                "format": None,
                "duration_ms": None,
                "waveform": [],
                "storage_id": None,
                "url": None,
            },
            "voice": {
                "voice_id": None,
                "tts_provider": None,
                "model_identity_key": model_identity_key,
                "persona_tag": None,
            },
        },
    }


async def _emit_group_voice_contract_stub(
    sio,
    *,
    group_id: str,
    message_id: str,
    agent_id: str,
    model_id: str,
    model_source: str = None,
    full_message: str = "",
):
    from src.voice.tts_engine import (
        get_tts_engine,
        split_into_sentences,
        estimate_audio_duration,
    )

    payload = _build_voice_contract_stub(
        group_id=group_id,
        message_id=message_id,
        agent_id=agent_id,
        model_id=model_id,
        model_source=model_source,
        full_message=full_message,
    )
    # MARKER_156.VOICE.S2_ASSIGNMENT_INTEGRATION: Resolve persistent model->voice identity.
    try:
        assignment = await _resolve_group_voice_assignment(
            group_id=group_id,
            agent_id=agent_id,
            model_source=model_source,
            model_id=model_id,
        )
        if assignment:
            payload["metadata"]["voice"] = {
                "voice_id": assignment.get("voice_id"),
                "tts_provider": assignment.get("tts_provider"),
                "model_identity_key": assignment.get("model_identity_key"),
                "persona_tag": assignment.get("persona_tag"),
            }
            payload["metadata"]["voice_enabled"] = True
            payload["metadata"]["voice_reason"] = "S6_role_voice_locked"
    except Exception as exc:
        logger.warning("[VOICE_S2] assignment fallback for %s/%s: %s", model_source, model_id, exc)

    # MARKER_156.VOICE.S3_TTS_STREAM: Real-time sentence-level TTS stream for group agent output.
    async def _emit_stream_end_with_payload(reason: str):
        await sio.emit(
            "group_voice_stream_end",
            {
                "id": message_id,
                "group_id": group_id,
                "agent_id": agent_id,
                "audio": payload["metadata"].get("audio"),
                "voice": payload["metadata"].get("voice"),
                "text_preview": payload.get("text_preview", ""),
                "reason": reason,
            },
            room=f"group_{group_id}",
        )

    voice_meta = payload["metadata"].get("voice", {}) or {}
    audio_meta = payload["metadata"].get("audio", {}) or {}
    full_text = (full_message or "").strip()
    combined_waveform = []
    total_duration_ms = 0
    final_format = None
    stream_started = False

    if full_text:
        try:
            await sio.emit(
                "group_voice_stream_start",
                {
                    "id": message_id,
                    "group_id": group_id,
                    "agent_id": agent_id,
                    "voice": voice_meta,
                },
                room=f"group_{group_id}",
            )
            stream_started = True

            language = _language_for_text(full_text)
            sentences = split_into_sentences(full_text) or [full_text]
            sentences = [s.strip() for s in sentences if s and s.strip()]

            async with get_tts_engine(primary="qwen3", language=language) as tts_engine:
                for seq, sentence in enumerate(sentences):
                    try:
                        tts_result = await tts_engine.synthesize_with_result(
                            sentence,
                            voice=voice_meta.get("voice_id") or "default",
                        )
                        audio_bytes = tts_result.audio or b""
                        if not audio_bytes:
                            continue

                        sentence_duration_ms = int(estimate_audio_duration(sentence) * 1000)
                        sentence_waveform = _waveform_from_audio(audio_bytes, points=32)

                        total_duration_ms += max(0, sentence_duration_ms)
                        combined_waveform.extend(sentence_waveform[:12])
                        final_format = tts_result.format or final_format
                        voice_meta["tts_provider"] = tts_result.provider or voice_meta.get("tts_provider")

                        await sio.emit(
                            "group_voice_stream_chunk",
                            {
                                "id": message_id,
                                "group_id": group_id,
                                "agent_id": agent_id,
                                "seq": seq,
                                "is_final": False,
                                "audio_chunk_b64": base64.b64encode(audio_bytes).decode("ascii"),
                                "format": tts_result.format,
                                "duration_ms": sentence_duration_ms,
                                "waveform": sentence_waveform,
                            },
                            room=f"group_{group_id}",
                        )
                    except Exception as sentence_exc:
                        logger.warning(
                            "[VOICE_S3] sentence TTS failed for %s/%s: %s",
                            model_source,
                            model_id,
                            sentence_exc,
                        )

            if total_duration_ms > 0:
                payload["metadata"]["voice_enabled"] = True
                payload["metadata"]["voice_reason"] = "S3_tts_stream_ok"
                audio_meta["duration_ms"] = total_duration_ms
                audio_meta["format"] = final_format or audio_meta.get("format") or "wav"
                audio_meta["waveform"] = combined_waveform[:64]
                payload["metadata"]["audio"] = audio_meta
                payload["metadata"]["voice"] = voice_meta
                await _emit_stream_end_with_payload("s3_ok")
            else:
                payload["metadata"]["voice_enabled"] = False
                payload["metadata"]["voice_reason"] = "S3_tts_stream_no_audio"
                await _emit_stream_end_with_payload("s3_no_audio")
        except Exception as stream_exc:
            payload["metadata"]["voice_enabled"] = False
            payload["metadata"]["voice_reason"] = f"S3_tts_stream_error:{type(stream_exc).__name__}"
            logger.warning(
                "[VOICE_S3] stream failed for %s/%s: %s",
                model_source,
                model_id,
                stream_exc,
            )
            if stream_started:
                await _emit_stream_end_with_payload("s3_error")
    else:
        payload["metadata"]["voice_enabled"] = False
        payload["metadata"]["voice_reason"] = "S3_empty_text"
        await _emit_stream_end_with_payload("s3_empty_text")

    await sio.emit("group_voice_message", payload, room=f"group_{group_id}")


def _resolve_voice_reply_policy(group_object, data: dict) -> tuple[str, bool]:
    """
    MARKER_156.VOICE.S5_POLICY_BACKEND: Resolve text/auto/forced policy for group voice replies.
    Returns: (mode, should_emit_voice)
    """
    allowed = {"text_only", "voice_auto", "voice_forced"}
    requested_mode = str(data.get("voice_reply_mode", "")).strip().lower()
    if requested_mode not in allowed:
        requested_mode = None
    voice_input = bool(data.get("voice_input", False))

    if group_object:
        shared = group_object.shared_context if isinstance(group_object.shared_context, dict) else {}
        mode = shared.get("voice_reply_mode", "voice_auto")
        if mode not in allowed:
            mode = "voice_auto"
        if requested_mode:
            mode = requested_mode
            shared["voice_reply_mode"] = mode
            if mode != "voice_auto":
                shared["voice_auto_activated"] = False
        if mode == "voice_auto" and voice_input:
            shared["voice_auto_activated"] = True
        if mode == "voice_auto" and not voice_input:
            shared["voice_auto_activated"] = False
        auto_active = bool(shared.get("voice_auto_activated", False))
        should_emit = mode == "voice_forced" or (mode == "voice_auto" and (voice_input or auto_active))
        return mode, should_emit

    mode = requested_mode or "voice_auto"
    should_emit = mode == "voice_forced" or (mode == "voice_auto" and voice_input)
    return mode, should_emit


async def notify_mcp_agents(
    sio,
    group_id: str,
    group_name: str,
    sender_id: str,
    content: str,
    mentions: list,
    message_id: str,
):
    """
    Phase 80.13: Notify MCP agents when they are @mentioned.

    Emits a socket event 'mcp_mention' that browser extensions can listen to.
    Also stores the mention in debug_routes team_messages for API access.

    Args:
        sio: SocketIO instance
        group_id: Group UUID
        group_name: Group name for context
        sender_id: Who sent the message
        content: Full message content
        mentions: List of mention names extracted from content
        message_id: ID of the original message
    """
    # Find which MCP agents are mentioned
    mentioned_mcp_agents = []

    for mention in mentions:
        mention_lower = mention.lower()

        # Check direct match
        if mention_lower in MCP_AGENTS:
            mentioned_mcp_agents.append(mention_lower)
            continue

        # Check aliases
        for agent_id, agent_info in MCP_AGENTS.items():
            if mention_lower in agent_info.get("aliases", []):
                mentioned_mcp_agents.append(agent_id)
                break

    if not mentioned_mcp_agents:
        return

    print(
        f"[MCP_MENTION] Phase 80.13: Detected MCP agent mentions: {mentioned_mcp_agents}"
    )

    # Build notification payload
    notification = {
        "type": "mcp_mention",
        "group_id": group_id,
        "group_name": group_name,
        "sender_id": sender_id,
        "content": content,
        "message_id": message_id,
        "timestamp": time.time(),
        "mentioned_agents": mentioned_mcp_agents,
    }

    # Emit socket event for each mentioned MCP agent
    for agent_id in mentioned_mcp_agents:
        agent_info = MCP_AGENTS[agent_id]

        # Emit targeted event
        await sio.emit(
            "mcp_mention",
            {
                **notification,
                "target_agent": agent_id,
                "agent_name": agent_info["name"],
                "agent_role": agent_info["role"],
            },
            namespace="/",
        )

        print(
            f"[MCP_MENTION] Notified {agent_info['name']} of @mention in {group_name}"
        )

    # Store in team_messages buffer for API access
    try:
        from src.api.routes.debug_routes import team_messages, KNOWN_AGENTS

        for agent_id in mentioned_mcp_agents:
            agent_info = MCP_AGENTS[agent_id]

            msg = {
                "id": f"mcp_{message_id}_{agent_id}",
                "timestamp": time.time(),
                "sender": sender_id,
                "sender_info": {"name": sender_id, "icon": "user", "role": "User"},
                "to": agent_id,
                "to_info": {
                    "name": agent_info["name"],
                    "icon": agent_info["icon"],
                    "role": agent_info["role"],
                },
                "message": content,
                "priority": "normal",
                "context": {
                    "group_id": group_id,
                    "group_name": group_name,
                    "message_id": message_id,
                    "type": "group_mention",
                },
                "pending": True,
                "read": False,
            }

            team_messages.append(msg)

            # Keep buffer limited (max 100)
            if len(team_messages) > 100:
                team_messages[:] = team_messages[-100:]

    except ImportError as e:
        print(f"[MCP_MENTION] Could not import debug_routes: {e}")
    except Exception as e:
        print(f"[MCP_MENTION] Error storing message: {e}")

    # MARKER_117_3: Auto-dispatch system commands to Mycelium pipeline
    for agent_id in mentioned_mcp_agents:
        if agent_id in HEARTBEAT_AGENTS:
            print(f"[MCP_MENTION] Phase 117.3: Auto-dispatching @{agent_id} to Mycelium pipeline (chat={group_id[:8]}...)")
            asyncio.create_task(_dispatch_system_command(
                agent_id=agent_id,
                chat_id=group_id,
                content=content,
                message_id=message_id,
                sender_id=sender_id,
            ))


# MARKER_117_3: System command dispatch
# Phase type mapping for system commands
_SYSTEM_COMMAND_PHASES = {
    "dragon": "build",
    "doctor": "research",
    "pipeline": "build",
}

# MARKER_124.2A: Interactive task intake — pending intakes per chat
_PENDING_INTAKES: dict = {}  # chat_id → {"agent_id", "task_text", "sender_id", "created_at"}
_INTAKE_TIMEOUT_SEC = 60  # Auto-queue after 60s with no reply


# MARKER_125.1C: Doctor triage — analyze task abstraction before dispatch
# MARKER_127.4A: Show triage progress step-by-step in chat
# MARKER_127.4C: Quick-action buttons after triage
async def _doctor_triage(chat_id: str, task_text: str, sender_id: str):
    """Doctor analyzes task abstraction/complexity, routes accordingly.

    MARKER_127.4A: Shows step-by-step progress in chat before dispatch.
    MARKER_127.4C: Offers quick-action buttons for user choice.

    Concrete tasks → show analysis → offer dispatch or queue
    Abstract tasks → show analysis → hold for human approval
    """
    import json as _json
    import httpx

    # MARKER_127.4A: Helper to emit doctor messages
    async def _emit_doctor_msg(content: str, msg_type: str = "system"):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"http://localhost:5001/api/debug/mcp/groups/{chat_id}/send",
                    json={"agent_id": "doctor", "content": content, "message_type": msg_type}
                )
        except Exception:
            pass

    # Step 1: Show "analyzing" message
    await _emit_doctor_msg("Analyzing task...")

    try:
        # Load Doctor prompt
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "data", "templates", "pipeline_prompts.json"
        )
        with open(prompts_path) as f:
            prompts = _json.load(f)

        doctor_prompt = prompts.get("doctor", {})
        if not doctor_prompt:
            logger.warning("[DOCTOR] No doctor prompt found, falling back to intake")
            await _send_intake_prompt(chat_id, "doctor", task_text, sender_id)
            return

        # Quick LLM call for triage (cheap model — Haiku)
        from src.tools.llm_call_tool import LLMCallTool
        llm = LLMCallTool()
        result = llm.call(
            model=doctor_prompt.get("model", "anthropic/claude-haiku-4.5"),
            system=doctor_prompt["system"],
            user=f"Task to analyze:\n{task_text}",
            temperature=doctor_prompt.get("temperature", 0.2),
        )

        response_text = result.get("result", {}).get("content", "{}")

        # Parse JSON from response
        import re as _re
        json_match = _re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            triage = _json.loads(json_match.group())
        else:
            triage = {"abstraction": "moderate", "routing": "dispatch"}

    except Exception as e:
        logger.error(f"[DOCTOR] Triage failed: {e}, falling back to intake")
        await _emit_doctor_msg(f"Triage failed: {e}. Falling back to intake.")
        await _send_intake_prompt(chat_id, "doctor", task_text, sender_id)
        return

    # Extract triage results
    abstraction = triage.get("abstraction", "moderate")
    routing = triage.get("routing", "dispatch")
    reformulated = triage.get("reformulated_task", task_text)
    complexity = triage.get("complexity", "moderate")
    suggested_phase = triage.get("suggested_phase", "build")
    suggested_team = triage.get("suggested_team", "dragon_silver")
    tags = triage.get("tags", ["doctor"])
    reasoning = triage.get("reasoning", "")
    estimated_subtasks = triage.get("estimated_subtasks", 3)
    key_files = triage.get("key_files", [])

    # MARKER_127.4A: Step 2 — Show analysis results
    analysis_msg = (
        f"Abstraction: **{abstraction}**\n"
        f"Reformulated: _{reformulated[:150]}_\n"
        f"Suggested: `{suggested_team}` ({suggested_phase})"
    )
    if estimated_subtasks:
        analysis_msg += f" | ~{estimated_subtasks} subtasks"
    if key_files:
        analysis_msg += f"\nKey files: `{', '.join(key_files[:3])}`"
    await _emit_doctor_msg(analysis_msg)

    from src.orchestration.task_board import get_task_board
    board = get_task_board()

    if routing == "hold" or abstraction == "abstract":
        # ABSTRACT → TaskBoard with hold status, wait for human approve
        task_id = board.add_task(
            title=reformulated[:100],
            description=f"Original: {task_text}\n\nReformulated: {reformulated}\n\nKey files: {key_files}",
            priority=3,
            phase_type=suggested_phase,
            preset=suggested_team,
            source="doctor_triage",
            tags=tags + ["hold", "needs-approve"],
            source_group_id=chat_id,  # MARKER_152.3: Task provenance
        )
        board.update_task(task_id, status="hold")

        # MARKER_127.4A: Show hold message with approve instructions
        await _emit_doctor_msg(
            f"Task is **abstract** — needs clarification.\n"
            f"Added `{task_id}` to hold.\n\n"
            f"Reply `approve {task_id}` to dispatch."
        )

    else:
        # CONCRETE/MODERATE → add to board, show quick-actions
        task_id = board.add_task(
            title=reformulated[:100],
            description=f"Original: {task_text}\n\nReformulated: {reformulated}\n\nKey files: {key_files}",
            priority=3,
            phase_type=suggested_phase,
            preset=suggested_team,
            source="doctor_triage",
            tags=tags + ["triage-pending"],
            source_group_id=chat_id,  # MARKER_152.3: Task provenance
        )

        # Store pending task for quick-action handling
        _DOCTOR_PENDING_TASKS[chat_id] = {
            "task_id": task_id,
            "team": suggested_team,
            "phase": suggested_phase,
            "timestamp": time.time()
        }

        # MARKER_127.4C: Show quick-action prompt
        await _emit_doctor_msg(
            f"Task `{task_id}` ready.\n\n"
            f"**Quick actions:**\n"
            f"`1d` — Run now ({suggested_team})\n"
            f"`2d` — Queue (priority 2)\n"
            f"`h` — Hold for review"
        )
# MARKER_125.1C_END


# MARKER_127.4C: Pending tasks awaiting quick-action
_DOCTOR_PENDING_TASKS: dict = {}


async def _handle_doctor_quick_action(chat_id: str, action: str) -> bool:
    """Handle doctor quick-action commands (1d, 2d, h).

    MARKER_127.4C: Quick dispatch/queue/hold after triage.

    Returns True if handled, False if not a quick-action.
    """
    import httpx

    pending = _DOCTOR_PENDING_TASKS.get(chat_id)
    if not pending:
        return False

    # Check if pending task is stale (>5 min)
    if time.time() - pending.get("timestamp", 0) > 300:
        del _DOCTOR_PENDING_TASKS[chat_id]
        return False

    action = action.strip().lower()
    task_id = pending["task_id"]

    from src.orchestration.task_board import get_task_board
    board = get_task_board()

    async def _emit_msg(content: str):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"http://localhost:5001/api/debug/mcp/groups/{chat_id}/send",
                    json={"agent_id": "doctor", "content": content, "message_type": "system"}
                )
        except Exception:
            pass

    if action == "1d":
        # Run now — dispatch immediately
        board.update_task(task_id, status="pending")
        del _DOCTOR_PENDING_TASKS[chat_id]

        await _emit_msg(f"Dispatching `{task_id}` now...")

        try:
            dispatched = await board.dispatch_next(chat_id=chat_id)
            if dispatched:
                logger.info(f"[DOCTOR] Quick-dispatched task {task_id}")
        except Exception as e:
            logger.error(f"[DOCTOR] Quick-dispatch failed: {e}")
        return True

    elif action == "2d":
        # Queue — set priority 2, don't dispatch
        board.update_task(task_id, status="pending", priority=2)
        del _DOCTOR_PENDING_TASKS[chat_id]
        await _emit_msg(f"Queued `{task_id}` with priority 2.")
        return True

    elif action == "h":
        # Hold — set hold status
        board.update_task(task_id, status="hold")
        board.update_task(task_id, tags=["hold", "needs-approve"])
        del _DOCTOR_PENDING_TASKS[chat_id]
        await _emit_msg(f"Holding `{task_id}`. Reply `approve {task_id}` when ready.")
        return True

    return False


async def _handle_approve_hold(chat_id: str, task_id: str) -> bool:
    """Approve a hold task and dispatch it.

    MARKER_125.1C: When user types 'approve tb_xxx', move task from hold → pending → dispatch.
    """
    from src.orchestration.task_board import get_task_board
    board = get_task_board()
    task = board.tasks.get(task_id)

    if not task:
        return False

    if task.get("status") != "hold":
        return False

    # Move from hold → pending (dispatchable)
    board.update_task(task_id, status="pending")

    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"http://localhost:5001/api/debug/mcp/groups/{chat_id}/send",
                json={
                    "agent_id": "doctor",
                    "content": (
                        f"✅ Задача `{task_id}` одобрена!\n"
                        f"🚀 Диспатчу: **{task.get('title', '?')[:150]}**\n"
                        f"Команда: `{task.get('preset', 'dragon_silver')}` | Фаза: `{task.get('phase_type', 'build')}`"
                    ),
                    "message_type": "system",
                }
            )
    except Exception:
        pass

    # Dispatch the approved task
    try:
        result = await board.dispatch_task(task_id, chat_id=chat_id)
        logger.info(f"[DOCTOR] Approved and dispatched hold task {task_id}: {result.get('success')}")
    except Exception as e:
        logger.error(f"[DOCTOR] Dispatch after approve failed: {e}")

    return True


async def _send_intake_prompt(chat_id: str, agent_id: str, task_text: str, sender_id: str):
    """Send interactive urgency/team prompt to chat instead of immediate dispatch."""
    import httpx

    _PENDING_INTAKES[chat_id] = {
        "agent_id": agent_id,
        "task_text": task_text,
        "sender_id": sender_id,
        "created_at": time.time(),
    }

    prompt_msg = (
        f"📋 New task from {sender_id}:\n"
        f"**{task_text[:200]}**\n\n"
        f"⏰ Urgency:\n"
        f"  `1` — Now (immediate pipeline)\n"
        f"  `2` — Queue (heartbeat, priority order)\n\n"
        f"🐉 Team:\n"
        f"  `d` — Dragon (code/build)\n"
        f"  `t` — Titan (research/analysis)\n\n"
        f"Reply: `1d` = now+dragon, `2t` = queue+titan, `1t` = now+titan, `2d` = queue+dragon\n"
        f"_(auto-queue as `2d` in 60s if no reply)_"
    )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"http://localhost:5001/api/debug/mcp/groups/{chat_id}/send",
                json={
                    "agent_id": agent_id,
                    "content": prompt_msg,
                    "message_type": "system",
                }
            )
    except Exception as e:
        logger.warning(f"[INTAKE] Failed to send prompt: {e}")

    # Schedule auto-timeout
    async def _auto_timeout():
        await asyncio.sleep(_INTAKE_TIMEOUT_SEC)
        if chat_id in _PENDING_INTAKES:
            logger.info(f"[INTAKE] Auto-timeout for {chat_id}, defaulting to 2d (queue+dragon)")
            await handle_intake_reply(chat_id, "2d")

    asyncio.create_task(_auto_timeout())


async def handle_intake_reply(chat_id: str, reply_text: str) -> bool:
    """Handle intake reply (e.g., '1d', '2t'). Returns True if intake was handled."""
    pending = _PENDING_INTAKES.pop(chat_id, None)
    if not pending:
        return False

    reply = reply_text.strip().lower()
    urgency = "now" if "1" in reply else "queue"
    team = "titan" if "t" in reply else "dragon"

    agent_id = pending["agent_id"]
    task_text = pending["task_text"]
    sender_id = pending["sender_id"]

    phase_type = _SYSTEM_COMMAND_PHASES.get(agent_id, "build")
    if team == "titan":
        phase_type = "research" if agent_id == "doctor" else "build"

    import httpx

    if urgency == "now":
        # Immediate pipeline execution
        preset = "titan_core" if team == "titan" else "dragon_silver"

        # MARKER_176.6: Also track in MCC task board (same as "queue" path)
        # Previously "now" path executed pipeline without board entry — invisible to MCC
        from src.orchestration.task_board import get_task_board
        board = get_task_board()
        board_task_id = board.add_task(
            title=task_text[:100],
            description=task_text,
            priority=1,  # High — user chose "now"
            phase_type=phase_type,
            preset=preset,
            status="in_progress",  # Already dispatching
            source=f"intake_{agent_id}_now",
            tags=[team, agent_id, "immediate"],
            source_group_id=chat_id,
        )
        logger.info(f"[INTAKE] MARKER_176.6: Now task tracked in board as {board_task_id}")
        # MARKER_176.6_END

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"http://localhost:5001/api/debug/mcp/groups/{chat_id}/send",
                    json={
                        "agent_id": agent_id,
                        "content": (
                            f"🔥 Dispatching NOW with {'⚡ Titan' if team == 'titan' else '🐉 Dragon'}!\n"
                            f"Task: {task_text[:200]}"
                        ),
                        "message_type": "system",
                    }
                )
        except Exception:
            pass

        from src.orchestration.agent_pipeline import AgentPipeline
        pipeline = AgentPipeline(chat_id=chat_id, preset=preset)

        try:
            result = await pipeline.execute(task_text, phase_type)
            completed = result.get("results", {}).get("subtasks_completed", "?")
            total = result.get("results", {}).get("subtasks_total", "?")
            logger.info(f"[INTAKE] Now dispatch done: {completed}/{total}")
        except Exception as e:
            logger.error(f"[INTAKE] Now dispatch failed: {e}")
    else:
        # Queue via TaskBoard
        from src.orchestration.task_board import get_task_board
        board = get_task_board()
        preset = "titan_core" if team == "titan" else "dragon_silver"
        task_id = board.add_task(
            title=task_text[:100],
            description=task_text,
            priority=3,  # Medium — user can reprioritize in Task Board UI
            phase_type=phase_type,
            preset=preset,
            source=f"intake_{agent_id}",
            tags=[team, agent_id],
            source_group_id=chat_id,  # MARKER_152.3: Task provenance
        )

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"http://localhost:5001/api/debug/mcp/groups/{chat_id}/send",
                    json={
                        "agent_id": agent_id,
                        "content": (
                            f"📥 Task queued as `{task_id}` with {'⚡ Titan' if team == 'titan' else '🐉 Dragon'}\n"
                            f"Priority: P3 (medium) — edit in Task Board (Cmd+Shift+D)\n"
                            f"Task: {task_text[:150]}"
                        ),
                        "message_type": "system",
                    }
                )
        except Exception:
            pass

        # MARKER_124.3C: Auto-dispatch queued task if board has capacity
        try:
            dispatched = await board.dispatch_next(chat_id=chat_id)
            if dispatched:
                logger.info(f"[INTAKE] Auto-dispatched task {dispatched.get('task_id', '?')} from queue")
        except Exception as e:
            logger.debug(f"[INTAKE] Auto-dispatch skipped: {e}")
        # MARKER_124.3C_END

    return True


def has_pending_intake(chat_id: str) -> bool:
    """Check if chat has a pending intake prompt (for message interception)."""
    pending = _PENDING_INTAKES.get(chat_id)
    if not pending:
        return False
    # Check timeout
    if time.time() - pending["created_at"] > _INTAKE_TIMEOUT_SEC + 5:
        _PENDING_INTAKES.pop(chat_id, None)
        return False
    return True


async def _dispatch_system_command(
    agent_id: str,
    chat_id: str,
    content: str,
    message_id: str,
    sender_id: str,
):
    """
    Phase 117.3 + 124.2A: Dispatch system command to Mycelium pipeline.

    Called automatically when @dragon, @doctor, or @pipeline is mentioned
    in any group chat. Now uses interactive intake flow — asks urgency and team
    before dispatching.

    Args:
        agent_id: System command name (dragon, doctor, pipeline)
        chat_id: Group chat ID — pipeline will stream results here
        content: Full message content with @mention
        message_id: Source message ID
        sender_id: Who sent the command
    """
    import re as _re

    # Extract task text: remove the @mention prefix
    task_text = _re.sub(
        r"@\w+\s*",
        "",
        content,
        count=1
    ).strip()

    if not task_text:
        task_text = f"General {agent_id} task requested by {sender_id}"

    # MARKER_124.2A: Interactive intake — ask urgency and team before dispatch
    print(
        f"[SYSTEM_CMD] Phase 124.2A: Interactive intake for @{agent_id}\n"
        f"  Task: {task_text[:100]}\n"
        f"  Chat: {chat_id[:12]}...\n"
        f"  Sender: {sender_id}"
    )

    # MARKER_125.1C: Doctor gets triage instead of standard intake
    if agent_id in ("doctor", "doc", "help", "support"):
        await _doctor_triage(chat_id, task_text, sender_id)
        return

    await _send_intake_prompt(chat_id, agent_id, task_text, sender_id)
    return  # Wait for user reply via handle_intake_reply()
    # MARKER_124.2A_END — old direct dispatch code below kept for reference

    phase_type = _SYSTEM_COMMAND_PHASES.get(agent_id, "build")

    try:
        from src.orchestration.agent_pipeline import AgentPipeline

        # Notify chat that pipeline is starting
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"http://localhost:5001/api/debug/mcp/groups/{chat_id}/send",
                json={
                    "agent_id": agent_id,
                    "content": (
                        f"\U0001f525 @{agent_id} activated by {sender_id}\n"
                        f"Phase: `{phase_type}` | Task: {task_text[:200]}\n"
                        f"Pipeline starting..."
                    ),
                    "message_type": "system"
                }
            )

        # Execute pipeline — results stream to THIS chat
        pipeline = AgentPipeline(chat_id=chat_id)
        result = await pipeline.execute(task_text, phase_type)

        # Report completion — pipeline's _emit_to_chat already sent expanded report
        completed = result.get("results", {}).get("subtasks_completed", "?") if result else "?"
        total = result.get("results", {}).get("subtasks_total", "?") if result else "?"
        print(f"[SYSTEM_CMD] @{agent_id} completed: {completed}/{total}")

    except Exception as e:
        print(f"[SYSTEM_CMD] @{agent_id} failed: {e}")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"http://localhost:5001/api/debug/mcp/groups/{chat_id}/send",
                    json={
                        "agent_id": agent_id,
                        "content": f"\u274c @{agent_id} failed: {str(e)[:200]}",
                        "message_type": "error"
                    }
                )
        except Exception:
            pass


# ============================================================================
# PHASE 57.8: HOSTESS ROUTER
# ============================================================================


async def route_through_hostess(
    sio, manager, orchestrator, group_id: str, group: dict, sender_id: str, content: str
) -> dict:
    """
    Route message through Hostess for intelligent dispatch.
    Phase 57.8: Hostess as the group orchestrator.

    Returns:
        dict with:
        - 'handled': True if Hostess answered directly
        - 'delegate_to': agent name if delegation needed
        - 'response': Hostess's message (if any)
    """
    print(f"[GROUP_HOSTESS] Analyzing message for intelligent routing...")

    # Build context for Hostess
    recent_messages = manager.get_messages(group_id, limit=5)
    participants_list = [
        p.get("display_name") for p in group.get("participants", {}).values()
    ]

    hostess_prompt = f"""You are the Hostess - the orchestrator of a group chat with AI agents.

## GROUP: {group.get("name", "Unknown")}
## PARTICIPANTS: {", ".join(participants_list)}

## RECENT CONVERSATION:
{chr(10).join([f"[{m.get('sender_id')}]: {m.get('content', '')[:150]}" for m in recent_messages[-5:]])}

## USER MESSAGE:
{content}

## YOUR TASK:
Analyze this message and decide:

1. If it's a SIMPLE QUESTION (greeting, clarification, quick answer about the group or project):
   - Answer it yourself briefly and helpfully
   - Return: {{"action": "answer", "response": "your brief answer"}}

2. If it's a TASK/PROJECT (needs planning, coding, implementation, architecture):
   - Delegate to @Architect who will coordinate the team
   - Return: {{"action": "delegate", "to": "Architect", "reason": "brief reason why this needs the team"}}

3. If it's a RESEARCH question (needs investigation, deep analysis, code review):
   - Delegate to @Researcher if available, otherwise @Architect
   - Return: {{"action": "delegate", "to": "Researcher", "reason": "brief reason"}}

4. If it's CODE/IMPLEMENTATION request (write code, fix bug, implement feature):
   - Delegate to @Dev for direct implementation
   - Return: {{"action": "delegate", "to": "Dev", "reason": "brief reason"}}

5. If it's a REVIEW/TEST request:
   - Delegate to @QA
   - Return: {{"action": "delegate", "to": "QA", "reason": "brief reason"}}

Be smart about this. Simple greetings like "Hello" or "What can you do?" should be answered by you.
Complex requests like "Build a calculator" need the Architect.

Respond ONLY with valid JSON. No other text."""

    try:
        # Call Hostess via orchestrator
        result = await asyncio.wait_for(
            orchestrator.call_agent(
                agent_type="Hostess",
                model_id="qwen2:7b",  # Fast local model
                prompt=hostess_prompt,
                context={"group_id": group_id, "is_routing": True},
            ),
            timeout=30.0,  # 30 second timeout for routing
        )

        response_text = ""
        if isinstance(result, dict):
            response_text = result.get("output", "") or result.get("response", "")
        else:
            response_text = str(result)

        print(f"[GROUP_HOSTESS] Raw response: {response_text[:200]}...")

        # Parse JSON response
        json_match = re.search(r"\{[^{}]*\}", response_text, re.DOTALL)
        if json_match:
            try:
                decision = json.loads(json_match.group())
                action = decision.get("action", "answer")

                if action == "answer":
                    # Hostess answers directly
                    answer = decision.get("response", response_text)

                    # Emit Hostess response
                    msg_id = str(uuid.uuid4())
                    await sio.emit(
                        "group_stream_start",
                        {
                            "id": msg_id,
                            "group_id": group_id,
                            "agent_id": "@Hostess",
                            "model": "qwen2:7b",
                        },
                        room=f"group_{group_id}",
                    )

                    await sio.emit(
                        "group_stream_end",
                        {
                            "id": msg_id,
                            "group_id": group_id,
                            "agent_id": "@Hostess",
                            "full_message": answer,
                            "metadata": {"model": "qwen2:7b", "agent_type": "Hostess"},
                        },
                        room=f"group_{group_id}",
                    )
                    await _emit_group_voice_contract_stub(
                        sio,
                        group_id=group_id,
                        message_id=msg_id,
                        agent_id="@Hostess",
                        model_id="qwen2:7b",
                        full_message=answer,
                    )

                    # Store message
                    await manager.send_message(
                        group_id=group_id,
                        sender_id="@Hostess",
                        content=answer,
                        message_type="response",
                    )

                    print(f"[GROUP_HOSTESS] Answered directly: {len(answer)} chars")
                    return {"handled": True, "delegate_to": None, "response": answer}

                elif action == "delegate":
                    # Hostess delegates to another agent
                    delegate_to = decision.get("to", "Architect")
                    reason = decision.get("reason", "Task requires specialist")

                    # Emit Hostess delegation message
                    delegation_msg = f"This needs the team's expertise. {reason}\n\nHanding off to @{delegate_to}..."

                    msg_id = str(uuid.uuid4())
                    await sio.emit(
                        "group_stream_end",
                        {
                            "id": msg_id,
                            "group_id": group_id,
                            "agent_id": "@Hostess",
                            "full_message": delegation_msg,
                            "metadata": {"model": "qwen2:7b", "agent_type": "Hostess"},
                        },
                        room=f"group_{group_id}",
                    )
                    await _emit_group_voice_contract_stub(
                        sio,
                        group_id=group_id,
                        message_id=msg_id,
                        agent_id="@Hostess",
                        model_id="qwen2:7b",
                        full_message=delegation_msg,
                    )

                    await manager.send_message(
                        group_id=group_id,
                        sender_id="@Hostess",
                        content=delegation_msg,
                        message_type="system",
                    )

                    print(f"[GROUP_HOSTESS] Delegating to {delegate_to}: {reason}")
                    return {
                        "handled": False,
                        "delegate_to": delegate_to,
                        "response": delegation_msg,
                    }

            except json.JSONDecodeError as je:
                print(f"[GROUP_HOSTESS] JSON parse error: {je}")

        # Fallback: if parsing fails, delegate to Architect
        print(f"[GROUP_HOSTESS] Parsing failed, defaulting to Architect delegation")
        return {"handled": False, "delegate_to": "Architect", "response": None}

    except asyncio.TimeoutError:
        print(f"[GROUP_HOSTESS] Timeout, defaulting to Architect")
        return {"handled": False, "delegate_to": "Architect", "response": None}
    except Exception as e:
        print(f"[GROUP_HOSTESS] Error: {e}")
        import traceback

        traceback.print_exc()
        return {"handled": False, "delegate_to": "Architect", "response": None}


async def post_hostess_summary(
    sio,
    manager,
    orchestrator,
    group_id: str,
    group: dict,
    original_content: str,
    previous_outputs: dict,
) -> None:
    """
    Post a summary from Hostess after all agents have responded.
    Phase 57.8: Hostess closes the loop with a helpful summary.
    """
    if len(previous_outputs) < 2:
        # Only summarize when multiple agents responded
        return

    try:
        # Build summary context
        outputs_summary = "\n\n".join(
            [
                f"**{agent_name}**: {output[:300]}..."
                for agent_name, output in previous_outputs.items()
            ]
        )

        summary_prompt = f"""The team has completed their work on the user's request. Provide a brief, helpful summary.

## ORIGINAL REQUEST:
{original_content}

## TEAM RESPONSES:
{outputs_summary}

## YOUR TASK:
1. Summarize what was accomplished (2-3 sentences max)
2. Highlight any key deliverables or artifacts
3. Mention next steps if relevant
4. Keep it SHORT and actionable

Respond naturally as the helpful Hostess. No JSON needed."""

        result = await asyncio.wait_for(
            orchestrator.call_agent(
                agent_type="Hostess",
                model_id="qwen2:7b",
                prompt=summary_prompt,
                context={"group_id": group_id, "is_summary": True},
            ),
            timeout=30.0,
        )

        summary_text = ""
        if isinstance(result, dict):
            summary_text = result.get("output", "") or result.get("response", "")
        else:
            summary_text = str(result)

        if summary_text and len(summary_text) > 20:
            # Clean up any JSON artifacts
            summary_text = re.sub(r"\{[^}]+\}", "", summary_text).strip()

            if summary_text:
                final_msg = f"**Summary**\n\n{summary_text}"

                msg_id = str(uuid.uuid4())
                await sio.emit(
                    "group_stream_end",
                    {
                        "id": msg_id,
                        "group_id": group_id,
                        "agent_id": "@Hostess",
                        "full_message": final_msg,
                        "metadata": {
                            "model": "qwen2:7b",
                            "agent_type": "Hostess",
                            "is_summary": True,
                        },
                    },
                    room=f"group_{group_id}",
                )
                await _emit_group_voice_contract_stub(
                    sio,
                    group_id=group_id,
                    message_id=msg_id,
                    agent_id="@Hostess",
                    model_id="qwen2:7b",
                    full_message=final_msg,
                )

                await manager.send_message(
                    group_id=group_id,
                    sender_id="@Hostess",
                    content=final_msg,
                    message_type="system",
                )

                print(f"[GROUP_HOSTESS] Posted summary: {len(summary_text)} chars")

    except Exception as e:
        print(f"[GROUP_HOSTESS] Summary failed: {e}")


# ============================================================================
# MAIN HANDLER REGISTRATION
# ============================================================================


def register_group_message_handler(sio, app=None):
    """Register group chat Socket.IO handlers.

    Phase 57.4: Uses orchestrator for LLM calls instead of direct HTTP.
    Phase 57.8: Hostess as intelligent router + summary provider.
    """
    # Store SocketIO reference for artifact tools
    set_socketio(sio)

    @sio.on("join_group")
    async def handle_join_group(sid, data):
        """Handle client joining a group room."""
        group_id = data.get("group_id")
        if group_id:
            # Join Socket.IO room for this group
            await sio.enter_room(sid, f"group_{group_id}")
            print(f"[GROUP] Client {sid[:8]} joined group room: {group_id}")
            await sio.emit("group_joined_ack", {"group_id": group_id}, to=sid)

    @sio.on("leave_group")
    async def handle_leave_group(sid, data):
        """Handle client leaving a group room."""
        group_id = data.get("group_id")
        if group_id:
            await sio.leave_room(sid, f"group_{group_id}")
            print(f"[GROUP] Client {sid[:8]} left group room: {group_id}")

    @sio.on("group_message")
    async def handle_group_message(sid, data):
        """
        # MARKER_94.6_MESSAGE_BROADCAST: Group message broadcasting
        Handle group message with streaming response.
        Phase 57: Smart key rotation with 24h cooldown markers.

        Expected data:
        - group_id: Group UUID
        - sender_id: "user" or agent_id
        - content: Message text (may contain @mentions)
        """
        # MARKER_94.5_GROUP_ENTRY: Group chat entry point
        print(f"\n{'=' * 50}")
        print(f"[GROUP_MESSAGE] Received from {sid}")
        print(f"[GROUP_MESSAGE] Data: {data}")
        print(f"{'=' * 50}\n")

        group_id = data.get("group_id")
        sender_id = data.get("sender_id", "user")
        content = data.get("content", "").strip()
        reply_to_id = data.get("reply_to_id") or data.get("reply_to")  # Phase 80.7: Message ID being replied to
        pinned_files = data.get(
            "pinned_files", []
        )  # Phase 80.11: Pinned files for context
        model_source = data.get("model_source")  # Phase 111.11

        # Phase 55.1: MCP group session init (fire-and-forget, non-blocking)
        async def _bg_session_init():
            try:
                session = await asyncio.wait_for(
                    vetka_session_init(
                        user_id=sender_id, group_id=group_id, compress=False
                    ),
                    timeout=1.0,
                )
                print(
                    f"   [MCP] Group session initialized: {session.get('session_id')}"
                )
            except asyncio.TimeoutError:
                print(f"   ⚠️ MCP session init timeout (1s)")
            except Exception as e:
                print(f"   ⚠️ MCP group session init failed: {e}")

        asyncio.create_task(_bg_session_init())

        if not group_id or not content:
            await sio.emit(
                "group_error", {"error": "Missing group_id or content"}, to=sid
            )
            return

        manager = get_group_chat_manager()
        group = manager.get_group(group_id)
        # Phase 80.28: Get Group object for smart reply decay
        group_object = manager.get_group_object(group_id)
        voice_reply_mode, should_emit_voice = _resolve_voice_reply_policy(group_object, data)

        if not group:
            await sio.emit(
                "group_error", {"error": f"Group not found: {group_id}"}, to=sid
            )
            return

        # Store user message in group (Phase 80.11: Include pinned_files in metadata)
        # Phase 111.17: Include reply metadata for group chat reply UI
        message_metadata = {}
        message_metadata["voice_reply_mode"] = voice_reply_mode
        message_metadata["voice_input"] = bool(data.get("voice_input", False))
        if pinned_files:
            message_metadata["pinned_files"] = pinned_files
        if reply_to_id:
            message_metadata["in_reply_to"] = reply_to_id
            # Get preview of replied-to message for UI display
            replied_msg = None
            for msg in manager.get_messages(group_id, limit=100):
                if msg.get("id") == reply_to_id:
                    replied_msg = msg
                    break
            if replied_msg:
                message_metadata["reply_to_preview"] = {
                    "id": reply_to_id,
                    "role": replied_msg.get("sender_id") == "user"
                    and "user"
                    or "assistant",
                    "agent": replied_msg.get("sender_id")
                    if replied_msg.get("sender_id") != "user"
                    else None,
                    "model": replied_msg.get("metadata", {}).get("model"),
                    "text_preview": replied_msg.get("content", "")[:100],
                    "timestamp": replied_msg.get("created_at", ""),
                }

        user_message = await manager.send_message(
            group_id=group_id,
            sender_id=sender_id,
            content=content,
            message_type="chat",
            metadata=message_metadata if message_metadata else None,
        )

        if not user_message:
            await sio.emit("group_error", {"error": "Failed to store message"}, to=sid)
            return

        # Broadcast user message to group room
        await sio.emit(
            "group_message", user_message.to_dict(), room=f"group_{group_id}"
        )

        # MARKER_108_3_SOCKETIO_UPDATE: Phase 108.3 - Real-time chat node updates
        # Emit chat_node_update for opacity animation when user sends message
        from datetime import datetime

        await sio.emit(
            "chat_node_update",
            {
                "chat_id": group_id,
                "decay_factor": 1.0,  # Just updated = fully opaque
                "last_activity": datetime.now().isoformat(),
                "message_count": len(manager.get_messages(group_id, limit=1000)),
            },
            room=f"group_{group_id}",
        )

        # Phase 80.28: Increment decay counter on user messages (for smart reply)
        if sender_id == "user" and group_object:
            group_object.last_responder_decay += 1
            print(
                f"[GROUP_DEBUG] Phase 80.28: User message, decay now {group_object.last_responder_decay}"
            )

        # MARKER_125.1C: Handle "approve tb_xxx" for Doctor hold tasks
        if sender_id == "user" and content.strip().lower().startswith("approve "):
            approve_task_id = content.strip().split(maxsplit=1)[1].strip()
            if approve_task_id.startswith("tb_"):
                handled = await _handle_approve_hold(group_id, approve_task_id)
                if handled:
                    return  # Don't process as normal message

        # MARKER_127.4C: Handle doctor quick-action commands (1d, 2d, h)
        if sender_id == "user" and content.strip().lower() in ("1d", "2d", "h"):
            handled = await _handle_doctor_quick_action(group_id, content)
            if handled:
                return  # Don't process as normal message

        # MARKER_124.2A: Check for pending intake reply before normal routing
        if sender_id == "user" and has_pending_intake(group_id):
            # Short replies like "1d", "2t", "1t", "2d" are intake responses
            if len(content.strip()) <= 5 and any(c in content for c in "12"):
                print(f"[INTAKE] Intercepting intake reply: '{content.strip()}' in {group_id[:8]}...")
                handled = await handle_intake_reply(group_id, content)
                if handled:
                    return  # Don't process as normal message

        # Phase 80.13: Check for MCP agent @mentions and notify them
        # MCP agents (browser_haiku, claude_code) are not in participants
        # but can be @mentioned and notified via socket events
        mentions = (
            user_message.mentions
            if hasattr(user_message, "mentions")
            # MARKER_108_ROUTING_FIX_4: Support hyphenated model names
            else re.findall(r"@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)", content)
        )
        if mentions:
            await notify_mcp_agents(
                sio=sio,
                group_id=group_id,
                group_name=group.get("name", "Unknown Group"),
                sender_id=sender_id,
                content=content,
                mentions=mentions,
                message_id=user_message.id,
            )

        # Phase 74.8: Save user message to chat_history
        # MARKER_109_13: Use group_id as stable key to prevent duplicate chats
        try:
            chat_history = get_chat_history_manager()
            group_name = group.get("name", f"Group {group_id[:8]}")
            # Find or create chat by group_id (stable key) instead of display_name
            chat_id = chat_history.get_or_create_chat(
                file_path=group_id, context_type="group", display_name=group_name,  # MARKER_117.6B: was "unknown"
                group_id=group_id  # MARKER_109_13: Stable key for deduplication!
            )
            chat_history.add_message(
                chat_id,
                {
                    "role": "user",
                    "content": content,
                    "agent": sender_id,
                    "metadata": {"group_id": group_id},
                },
            )
        except Exception as chat_err:
            print(f"[GROUP_CHAT] Error saving to chat_history: {chat_err}")

        # Phase 57.4: Get orchestrator for proper LLM routing
        orchestrator = get_orchestrator()
        if not orchestrator:
            print(f"[GROUP_ERROR] Orchestrator is None! Cannot call agents.")
            await sio.emit(
                "group_error", {"error": "Orchestrator not initialized"}, to=sid
            )
            return
        print(f"[GROUP_DEBUG] Orchestrator loaded: {type(orchestrator).__name__}")

        # Phase 80.7: Find original agent if this is a reply
        # MARKER_108_ROUTING_FIX_2: Handle MCP agent replies
        reply_to_agent = None
        reply_to_mcp_agent = False
        if reply_to_id:
            # Look up the original message to find its sender
            messages = manager.get_messages(group_id, limit=100)
            for msg in messages:
                if msg.get("id") == reply_to_id:
                    original_sender = msg.get("sender_id", "")
                    # Only route to agent replies (not user replies)
                    if original_sender.startswith("@"):
                        reply_to_agent = original_sender
                        # Phase 108: Check if this is MCP agent (claude_code, browser_haiku, etc.)
                        # MCP agents are NOT in participants list
                        mcp_agent_names = [
                            "claude_code",
                            "browser_haiku",
                            "lmstudio",
                            "cursor",
                            "opencode",
                        ]
                        agent_name_lower = original_sender.lower().lstrip("@")
                        if any(
                            mcp_name in agent_name_lower for mcp_name in mcp_agent_names
                        ):
                            reply_to_mcp_agent = True
                            print(
                                f"[GROUP_DEBUG] Phase 108: Reply to MCP agent {reply_to_agent} - skipping group routing"
                            )
                        else:
                            print(
                                f"[GROUP_DEBUG] Phase 80.7: Reply to message {reply_to_id[:8]}... from {reply_to_agent}"
                            )
                    break

        # MARKER_108_ROUTING_FIX_2: If replying to MCP agent, don't route to group agents
        if reply_to_mcp_agent:
            print(
                f"[GROUP_DEBUG] Phase 108: Reply to MCP agent - no group agents invoked"
            )
            return

        # Phase 57.7: Use smart agent selection
        # Phase 80.7: Pass reply_to_agent for proper routing
        # Phase 80.28: Pass group_object for smart reply decay
        participants_to_respond = await manager.select_responding_agents(
            content=content,
            participants=group.get("participants", {}),
            sender_id=sender_id,
            reply_to_agent=reply_to_agent,
            group=group_object,  # Phase 80.28
        )

        # Phase 57.8.2: REMOVED Hostess routing - она слишком медленная для роутинга
        # Hostess теперь только для: камера, навигация, context awareness
        # Вместо этого полагаемся на select_responding_agents + agent-to-agent @mentions

        if not participants_to_respond:
            # Enhanced debug: show why no one responds
            all_participants = [
                (pid, pdata.get("role", "unknown"))
                for pid, pdata in group.get("participants", {}).items()
            ]
            print(f"[GROUP_DEBUG] No agents to respond!")
            print(f"[GROUP_DEBUG] All participants: {all_participants}")
            print(f"[GROUP_DEBUG] Sender ID: {sender_id}")
            return

        print(
            f"[GROUP_DEBUG] Participants to respond: {[p['agent_id'] for p in participants_to_respond]}"
        )

        # Phase 57.7: Track previous outputs for chain context
        previous_outputs = {}

        # Phase 57.8.2: Use while loop to allow dynamic addition of agents via @mentions
        # for loop doesn't see items added during iteration
        processed_idx = 0
        max_agents = 10  # Safety limit to prevent infinite loops

        while (
            processed_idx < len(participants_to_respond) and processed_idx < max_agents
        ):
            participant = participants_to_respond[processed_idx]
            processed_idx += 1

            agent_id = participant["agent_id"]
            model_id = participant["model_id"]
            model_source = participant.get("model_source")  # Phase 111.11

            # Detect provider for model attribution
            from src.elisya.provider_registry import ProviderRegistry

            detected_provider = ProviderRegistry.detect_provider(
                model_id, source=model_source
            )  # Phase 111.11
            provider_name = detected_provider.value if detected_provider else "unknown"

            # MARKER_93.7_REMOVED_OPENROUTER_PREFIX: Phase 93.7 Fix
            # Previously this code added "openrouter/" prefix which broke routing:
            # - "openai/gpt-5.2" -> "openrouter/openai/gpt-5.2" -> Provider.OPENROUTER -> 402
            # Now we let detect_provider work correctly:
            # - "openai/gpt-5.2" -> Provider.OPENAI -> uses OpenAI API directly -> works!
            # The old "fix" was counterproductive because it forced OpenRouter
            # instead of letting the system use the appropriate provider.
            display_name = participant["display_name"]
            role = participant.get("role", "worker")

            # MARKER_94.6_ROLE_ROUTING: Role-based agent routing
            # Map group role to orchestrator agent type
            agent_type_map = {
                "PM": "PM",
                "pm": "PM",
                "Dev": "Dev",
                "dev": "Dev",
                "QA": "QA",
                "qa": "QA",
                "Architect": "Architect",
                "architect": "Architect",
                "Researcher": "Researcher",  # Phase 57.8
                "researcher": "Researcher",
                "admin": "PM",  # Default admin to PM
                "worker": "Dev",  # Default worker to Dev
            }
            agent_type = agent_type_map.get(
                display_name, agent_type_map.get(role, "Dev")
            )

            print(
                f"[GROUP] Calling agent {agent_id} ({model_id}) via orchestrator as {agent_type}..."
            )

            # Emit typing indicator
            await sio.emit(
                "group_typing",
                {"group_id": group_id, "agent_id": agent_id},
                room=f"group_{group_id}",
            )

            # Emit stream start
            msg_id = str(uuid.uuid4())
            await sio.emit(
                "group_stream_start",
                {
                    "id": msg_id,
                    "group_id": group_id,
                    "agent_id": agent_id,
                    "model": model_id,
                    "model_source": model_source,  # Phase 111.11
                },
                room=f"group_{group_id}",
            )

            try:
                # Phase 57.7: Build role-specific prompt with chain context
                system_prompt = get_agent_prompt(agent_type)

                # Build recent messages context
                recent_messages = manager.get_messages(group_id, limit=5)

                # MARKER_109_8_MODEL_IDENTITY: Add model identity to prevent confusion
                # Models need to know WHO they are (Grok was signing as GLM!)
                model_identity = f"""## YOUR IDENTITY
You are **{display_name}** (model: `{model_id}`).
When signing messages, use your ACTUAL name: {display_name}.
Do NOT confuse yourself with other models.
"""

                context_parts = [
                    model_identity,  # MARKER_109_8: Identity first!
                    f"## ROLE\n{system_prompt}\n",
                    f"## GROUP: {group.get('name', 'Team Chat')}\n",
                ]

                # Add chain context if other agents have responded
                if previous_outputs:
                    context_parts.append("## PREVIOUS AGENT OUTPUTS")
                    for agent_name, output in previous_outputs.items():
                        context_parts.append(f"[{agent_name}]: {output[:400]}...")
                    context_parts.append("")

                # Add recent conversation
                context_parts.append("## RECENT CONVERSATION")
                for msg in recent_messages:
                    msg_content = msg.get("content", "")[:200]
                    context_parts.append(f"[{msg.get('sender_id')}]: {msg_content}")

                # MARKER_109_9_REPLY_CONTEXT: Add reply context if this is a reply
                # Kimi K2 identified this gap - agents need to know they're responding to a reply
                if reply_to_id and reply_to_agent:
                    # Find the original message being replied to
                    reply_message_content = None
                    for msg in recent_messages:
                        if msg.get("id") == reply_to_id:
                            reply_message_content = msg.get("content", "")[:300]
                            break

                    if reply_message_content:
                        context_parts.append(f"\n## REPLY CONTEXT")
                        context_parts.append(f"User is replying to **{reply_to_agent}**'s message:")
                        context_parts.append(f'> "{reply_message_content}"')
                        context_parts.append(f"Consider this context when responding.\n")

                # Current request
                context_parts.append(f"\n## CURRENT REQUEST\n{content}")

                # MARKER_114.2_PINNED_IN_GROUP: Add pinned files context to agent prompt
                # Uses same build_pinned_context as solo chat (Phase 67 → 109.7 unified weighting)
                # Sources: Qdrant(40%) + CAM(20%) + Engram(15%) + Viewport(15%) + HOPE(5%) + MGC(5%)
                # MARKER_114.5_AGENT_WEIGHTS: Grok improvement 3 — model_name for dynamic token budget
                if pinned_files:
                    try:
                        from src.api.handlers.message_utils import build_pinned_context
                        pinned_context = build_pinned_context(
                            pinned_files,
                            user_query=content,
                            model_name=model_id,  # MARKER_114.5: dynamic token budget per model
                        )
                        if pinned_context:
                            context_parts.append(pinned_context)
                            print(f"[MARKER_114.2] Added pinned context ({len(pinned_context)} chars, model={model_id}) to group agent prompt")
                    except Exception as pinned_err:
                        print(f"[MARKER_114.2] Pinned context build failed (non-blocking): {pinned_err}")
                # MARKER_114.2_PINNED_IN_GROUP_END

                # Phase 95: ARC Integration - Group Chat Suggestions
                try:
                    from src.agents.arc_solver_agent import ARCSolverAgent

                    # Create ARC solver instance
                    arc_solver = ARCSolverAgent(use_api=False, learner=None)

                    # Build minimal graph data from group context
                    graph_data = {
                        "nodes": [
                            {"id": agent_id, "type": "agent"}
                            for agent_id in group.get("participants", {}).keys()
                        ],
                        "edges": [],
                    }

                    # Get ARC suggestions
                    arc_result = arc_solver.suggest_connections(
                        workflow_id=group_id,
                        graph_data=graph_data,
                        task_context=content,
                        num_candidates=5,
                        min_score=0.5,
                    )

                    # Add top suggestions to context
                    top_suggestions = arc_result.get("top_suggestions", [])
                    if top_suggestions:
                        context_parts.append("\n## ARC SUGGESTED IMPROVEMENTS")
                        for idx, suggestion in enumerate(top_suggestions[:3], 1):
                            score = suggestion.get("score", 0.0)
                            explanation = suggestion.get(
                                "explanation", "No explanation"
                            )
                            context_parts.append(
                                f"{idx}. {explanation} (confidence: {score:.2f})"
                            )
                        print(
                            f"[ARC_GROUP] Added {len(top_suggestions[:3])} suggestions to group context"
                        )
                except Exception as arc_err:
                    # Non-critical: continue even if ARC fails
                    print(f"[ARC_GROUP] ARC integration failed: {arc_err}")

                prompt = "\n".join(context_parts)

                # Phase 57.4: Use orchestrator.call_agent() for proper Elisya integration
                print(
                    f"[GROUP_DEBUG] Calling orchestrator.call_agent('{agent_type}', model='{model_id}')"
                )
                call_start = time.time()

                try:
                    result = await asyncio.wait_for(
                        orchestrator.call_agent(
                            agent_type=agent_type,
                            model_id=model_id,
                            prompt=prompt,
                            context={
                                "group_id": group_id,
                                "group_name": group["name"],
                                "agent_id": agent_id,
                                "display_name": display_name,
                                "model_source": model_source,  # Phase 111.11
                            },
                        ),
                        timeout=120.0,  # 2 minute timeout
                    )
                except asyncio.TimeoutError:
                    print(f"[GROUP_ERROR] Timeout after 120s calling {agent_type}")
                    result = {"status": "error", "error": "Timeout after 120 seconds"}

                call_elapsed = time.time() - call_start
                print(
                    f"[GROUP_DEBUG] call_agent returned in {call_elapsed:.2f}s, status={result.get('status')}"
                )

                if result.get("status") == "done":
                    response_text = result.get("output", "")
                else:
                    response_text = f"[Error: {result.get('error', 'Unknown error')}]"

                print(f"[GROUP_DEBUG] Response length: {len(response_text)} chars")

                # Phase 57.7: Store for chain context (next agents see this output)
                previous_outputs[display_name] = response_text[:500]

                # Store agent response in group
                agent_message = await manager.send_message(
                    group_id=group_id,
                    sender_id=agent_id,
                    content=response_text,
                    message_type="response",
                    metadata={"in_reply_to": user_message.id},
                )

                # Emit stream end with full response
                await sio.emit(
                    "group_stream_end",
                    {
                        "id": msg_id,
                        "group_id": group_id,
                        "agent_id": agent_id,
                        "full_message": response_text,
                        "metadata": {
                            "model": model_id,
                            "agent_type": agent_type,
                            "model_source": model_source,  # Phase 111.11
                        },
                    },
                    room=f"group_{group_id}",
                )
                if should_emit_voice:
                    await _emit_group_voice_contract_stub(
                        sio,
                        group_id=group_id,
                        message_id=msg_id,
                        agent_id=agent_id,
                        model_id=model_id,
                        model_source=model_source,
                        full_message=response_text,
                    )

                # Phase 111.18: Removed redundant group_message emit
                # Agent response is already sent via group_stream_end above
                # Frontend filters out agent messages anyway (sender_id check)

                if agent_message:
                    # MARKER_108_3_SOCKETIO_UPDATE: Phase 108.3 - Real-time chat node updates
                    # Emit chat_node_update when agent responds (activity update)
                    from datetime import datetime

                    await sio.emit(
                        "chat_node_update",
                        {
                            "chat_id": group_id,
                            "decay_factor": 1.0,  # Agent response = activity
                            "last_activity": datetime.now().isoformat(),
                            "message_count": len(
                                manager.get_messages(group_id, limit=1000)
                            ),
                        },
                        room=f"group_{group_id}",
                    )

                # Phase 80.28: Track last responder for smart reply decay
                if group_object and result.get("status") == "done":
                    group_object.last_responder_id = agent_id
                    group_object.last_responder_decay = (
                        0  # Reset decay after successful response
                    )
                    print(
                        f"[GROUP_DEBUG] Phase 80.28: last_responder={agent_id}, decay reset to 0"
                    )

                # Phase 74.8: Save agent response to chat_history
                # MARKER_CHAT_HISTORY_ATTRIBUTION: Model attribution fix - IMPLEMENTED
                # MARKER_109_13: Use group_id for stable lookup
                try:
                    chat_history = get_chat_history_manager()
                    group_name = group.get("name", f"Group {group_id[:8]}")
                    chat_id = chat_history.get_or_create_chat(
                        file_path=group_id,  # MARKER_117.6B: was "unknown"
                        context_type="group",
                        display_name=group_name,
                        group_id=group_id,  # MARKER_109_13: Stable key!
                    )
                    chat_history.add_message(
                        chat_id,
                        {
                            "role": "assistant",
                            "content": response_text,
                            "agent": display_name,
                            "model": model_id,
                            "model_provider": provider_name,  # Provider attribution for model disambiguation
                            "metadata": {
                                "group_id": group_id,
                                "model_source": model_source,  # Phase 111.11
                            },
                        },
                    )
                except Exception as chat_err:
                    print(
                        f"[GROUP_CHAT] Error saving agent response to chat_history: {chat_err}"
                    )

                # MARKER_103.6_START: Auto-stage artifacts from Dev/Architect
                # Staging pattern: Dev generates code → stage in JSON → QA review → apply to disk
                # MARKER_103_ARTIFACT_LINK: Added source_message_id for traceability
                try:
                    # Only stage for code-generating agents
                    if display_name in ["Dev", "Architect", "Coder"]:
                        from src.utils.artifact_extractor import (
                            extract_artifacts,
                            extract_qa_score,
                        )
                        from src.utils.staging_utils import stage_artifacts_batch

                        artifacts = extract_artifacts(response_text, display_name)
                        if artifacts:
                            qa_score = (
                                extract_qa_score(response_text) or 0.5
                            )  # Default moderate

                            staged_ids = stage_artifacts_batch(
                                artifacts=artifacts,
                                qa_score=qa_score,
                                agent=display_name,
                                group_id=group_id,
                                source_message_id=user_message.id,  # Link to source message
                            )

                            if staged_ids:
                                print(
                                    f"[STAGING] {len(staged_ids)} artifacts staged from {display_name}"
                                )

                                # Emit socket event for UI notification
                                await sio.emit(
                                    "artifacts_staged",
                                    {
                                        "group_id": group_id,
                                        "agent": display_name,
                                        "count": len(staged_ids),
                                        "task_ids": staged_ids,
                                        "qa_score": qa_score,
                                    },
                                    room=f"group_{group_id}",
                                )
                except Exception as staging_err:
                    # Graceful degradation - don't block message flow
                    print(f"[STAGING] Error (non-blocking): {staging_err}")
                # MARKER_103.6_END

                # Phase 111.18: Use batch queue instead of per-message upsert
                # Non-blocking queue - messages flushed every 30 seconds
                import uuid as uuid_module

                msg_id = str(uuid_module.uuid4())

                try:
                    from src.memory.qdrant_batch_manager import get_batch_manager

                    batch_mgr = get_batch_manager()
                    await batch_mgr.queue_message(
                        group_id=group_id,
                        message_id=msg_id,
                        sender_id=agent_id,
                        content=response_text,
                        role="assistant",
                        agent=display_name,
                        model=model_id,
                        metadata={
                            "in_reply_to": user_message.id if user_message else None,
                            "model_source": model_source,  # Phase 111.11
                        },
                    )
                except Exception as qdrant_err:
                    print(f"[QDRANT] Queue failed (non-blocking): {qdrant_err}")

                print(f"[GROUP] Agent {agent_id} responded: {len(response_text)} chars")

                # Phase 57.8: Check for @mentions in agent response to trigger other agents
                # MARKER_108_ROUTING_FIX_4: Support hyphenated model names
                agent_mentions = re.findall(
                    r"@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)", response_text
                )
                if agent_mentions:
                    print(
                        f"[GROUP_DEBUG] Agent {display_name} mentioned: {agent_mentions}"
                    )

                    for mentioned_name in agent_mentions:
                        # Skip self-mentions and already-responded agents
                        if mentioned_name.lower() == display_name.lower():
                            continue
                        if mentioned_name in previous_outputs:
                            continue

                        # Find mentioned agent in participants
                        mentioned_participant = None
                        for pid, pdata in group.get("participants", {}).items():
                            pname = pdata.get("display_name", "").lower()
                            agent_id = pdata.get("agent_id", "").lstrip("@").lower()
                            mentioned_lower = mentioned_name.lower()

                            # Strategy 1: Exact display_name match
                            if pname == mentioned_lower:
                                mentioned_participant = pdata
                                break
                            # Strategy 2: Match agent_id
                            if agent_id == mentioned_lower:
                                mentioned_participant = pdata
                                break
                            # Strategy 3: Match display_name prefix (before parentheses)
                            if (
                                "(" in pname
                                and pname.split("(")[0].strip() == mentioned_lower
                            ):
                                mentioned_participant = pdata
                                break

                        if not mentioned_participant:
                            print(
                                f"[GROUP_DEBUG] ⚠️ Agent '{mentioned_name}' NOT FOUND in group participants"
                            )

                        if (
                            mentioned_participant
                            and mentioned_participant.get("role") != "observer"
                        ):
                            # Check if agent is already in queue (by agent_id)
                            already_queued = any(
                                p.get("agent_id")
                                == mentioned_participant.get("agent_id")
                                for p in participants_to_respond
                            )
                            if not already_queued:
                                participants_to_respond.append(mentioned_participant)
                                print(
                                    f"[GROUP_DEBUG] Added {mentioned_name} to responders from agent @mention (queue size: {len(participants_to_respond)})"
                                )

            except Exception as e:
                print(f"[GROUP] Error calling agent {agent_id}: {e}")
                # Emit stream end with error
                await sio.emit(
                    "group_stream_end",
                    {
                        "id": msg_id,
                        "group_id": group_id,
                        "agent_id": agent_id,
                        "full_message": "",
                        "error": str(e)[:100],
                    },
                    room=f"group_{group_id}",
                )
                if should_emit_voice:
                    await _emit_group_voice_contract_stub(
                        sio,
                        group_id=group_id,
                        message_id=msg_id,
                        agent_id=agent_id,
                        model_id=model_id,
                        model_source=model_source,
                        full_message="",
                    )

                error_msg = await manager.send_message(
                    group_id=group_id,
                    sender_id=agent_id,
                    content=f"[Error: {str(e)[:100]}]",
                    message_type="error",
                )
                if error_msg:
                    await sio.emit(
                        "group_message", error_msg.to_dict(), room=f"group_{group_id}"
                    )

        # Phase 57.8.2: REMOVED Hostess summary - она слишком медленная
        # Hostess теперь получает весь контекст пассивно для:
        # - Наведения камеры (camera_focus)
        # - Навигации по дереву
        # - Future: контекст ветки
        # Но НЕ участвует в активной координации

    @sio.on("group_typing")
    async def handle_group_typing(sid, data):
        """Broadcast typing indicator to group."""
        group_id = data.get("group_id")
        agent_id = data.get("agent_id")
        if group_id and agent_id:
            await sio.emit(
                "group_typing",
                {"group_id": group_id, "agent_id": agent_id},
                room=f"group_{group_id}",
                skip_sid=sid,
            )
