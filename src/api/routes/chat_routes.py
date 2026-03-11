"""
VETKA Chat Routes - FastAPI Version

@file chat_routes.py
@status ACTIVE
@phase Phase 39.5
@lastAudit 2026-01-05

Chat API routes - THE BIG ONE!
Migrated from src/server/routes/chat_routes.py (Flask Blueprint)

Endpoints:
- GET /api/chat/history - Get chat history for a node
- POST /api/chat/clear-history - Clear chat history for a node
- POST /api/chat - Universal Chat API endpoint (THE MAIN ONE!)

Changes from Flask version:
- Blueprint -> APIRouter
- request.get_json() -> Pydantic BaseModel
- request.args.get() -> Query()
- current_app.config -> request.app.state
- return jsonify({}) -> return {}
- def -> async def
"""

import os
import time
import uuid
import json
import hashlib
import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List


router = APIRouter(prefix="/api", tags=["chat"])


# ============================================================
# PYDANTIC MODELS
# ============================================================


class ChatRequest(BaseModel):
    """Main chat request - THE BIG ONE."""

    message: str
    conversation_id: Optional[str] = None
    model_override: Optional[str] = None
    model_source: Optional[str] = None  # Phase 111.9: Source for multi-provider routing (poe, polza, etc.)
    system_prompt: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 999999
    node_id: Optional[str] = None
    node_path: Optional[str] = None
    file_path: Optional[str] = None


class ClearHistoryRequest(BaseModel):
    """Request to clear chat history."""

    path: str


class QuickChatRequest(BaseModel):
    """
    Lightweight MCC chat contract.
    Used by MiniChat quick path.
    """

    message: str
    role: str = "architect"
    user_id: str = "danila"
    context: Dict[str, Any] = {}


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def _get_chat_components(request: Request) -> dict:
    """Get chat-related components from app state (DI pattern)."""
    flask_config = getattr(request.app.state, "flask_config", {})
    return {
        "get_memory_manager": flask_config.get("get_memory_manager"),
        "get_orchestrator": flask_config.get("get_orchestrator"),
        "get_hostess": flask_config.get("get_hostess"),
        "get_model_for_task": flask_config.get("get_model_for_task"),
        "is_model_banned": flask_config.get("is_model_banned"),
        "model_router": flask_config.get("model_router"),
        "api_gateway": flask_config.get("api_gateway"),
        "qdrant_manager": flask_config.get("qdrant_manager"),
        "CHAT_HISTORY_DIR": flask_config.get("CHAT_HISTORY_DIR"),
        # Feature flags
        "ELISYA_ENABLED": flask_config.get("ELISYA_ENABLED", False),
        "PARALLEL_MODE": flask_config.get("PARALLEL_MODE", False),
        "HOSTESS_AVAILABLE": flask_config.get("HOSTESS_AVAILABLE", False),
        # "API_GATEWAY_AVAILABLE": flask_config.get("API_GATEWAY_AVAILABLE", False),  # REMOVED: Phase 95
        "MODEL_ROUTER_V2_AVAILABLE": flask_config.get(
            "MODEL_ROUTER_V2_AVAILABLE", False
        ),
        "QDRANT_AUTO_RETRY_AVAILABLE": flask_config.get(
            "QDRANT_AUTO_RETRY_AVAILABLE", False
        ),
    }


def _get_chat_history_file(chat_dir: Path, node_path: str) -> Path:
    """Get chat history file path for a node."""
    if not chat_dir:
        chat_dir = Path("data/chat_history")
        chat_dir.mkdir(parents=True, exist_ok=True)
    path_hash = hashlib.md5(node_path.encode()).hexdigest()[:16]
    return chat_dir / f"{path_hash}.json"


def _load_chat_history(chat_dir: Path, node_path: str) -> list:
    """Load chat history for a specific node."""
    file = _get_chat_history_file(chat_dir, node_path)
    if file.exists():
        try:
            return json.loads(file.read_text())
        except Exception as e:
            print(f"  [Chat] Error loading history: {e}")
            return []
    return []


def _normalize_guidance_context(context: Dict[str, Any]) -> Dict[str, Any]:
    focus = dict(context or {})
    nav_level = str(focus.get("nav_level") or focus.get("navLevel") or "").strip().lower() or "roadmap"
    node_kind = str(focus.get("node_kind") or focus.get("nodeKind") or "").strip().lower()
    graph_kind = str(focus.get("graph_kind") or focus.get("graphKind") or "").strip().lower()
    role = str(focus.get("role") or "").strip().lower()
    task_id = str(focus.get("task_id") or focus.get("taskId") or "").strip()
    label = str(
        focus.get("label")
        or task_id
        or focus.get("node_id")
        or focus.get("nodeId")
        or "project"
    ).strip()
    task_drill_state = str(focus.get("task_drill_state") or focus.get("taskDrillState") or "").strip().lower()
    node_drill_state = str(focus.get("roadmap_node_drill_state") or focus.get("roadmapNodeDrillState") or "").strip().lower()
    workflow_inline = bool(focus.get("workflow_inline_expanded") or focus.get("workflowInlineExpanded"))
    node_inline = bool(focus.get("roadmap_node_inline_expanded") or focus.get("roadmapNodeInlineExpanded"))
    chat_scope = str(focus.get("chat_scope") or focus.get("chatScope") or "").strip().lower()
    # MARKER_164.P4.WINDOW_FOCUS_BACKEND_NORMALIZATION.V1:
    # Normalize focused mini-window to let guidance branch on UI window intent.
    window_focus = str(focus.get("window_focus") or focus.get("windowFocus") or "").strip().lower()
    window_focus_state = str(
        focus.get("window_focus_state") or focus.get("windowFocusState") or ""
    ).strip().lower()
    workflow_id = str(focus.get("workflow_id") or focus.get("workflowId") or "").strip()
    team_profile = str(focus.get("team_profile") or focus.get("teamProfile") or "").strip()
    workflow_family = str(focus.get("workflow_family") or focus.get("workflowFamily") or "").strip().lower()
    if not workflow_family:
        joined = f"{team_profile} {workflow_id}".lower().strip()
        if "g3" in joined:
            workflow_family = "g3"
        elif "ralph" in joined:
            workflow_family = "ralph_loop"
        elif "openhands" in joined:
            workflow_family = "openhands"
        elif team_profile.lower().startswith("titan"):
            workflow_family = "titans"
        elif team_profile.lower().startswith("dragon"):
            workflow_family = "dragons"
        elif joined:
            workflow_family = "custom"
        else:
            workflow_family = "bmad"
    workflow_family_hint = {
        "dragons": "Dragons (faster/cheaper)",
        "titans": "Titans (smarter/costlier)",
        "g3": "G3 (critic+coder)",
        "ralph_loop": "Ralph loop (single-agent)",
        "openhands": "OpenHands-collab",
        "bmad": "BMAD/default",
        "custom": "custom workflow",
    }.get(workflow_family, workflow_family)
    return {
        "focus": focus,
        "nav_level": nav_level,
        "node_kind": node_kind,
        "graph_kind": graph_kind,
        "role": role,
        "task_id": task_id,
        "label": label,
        "task_drill_state": task_drill_state,
        "node_drill_state": node_drill_state,
        "workflow_inline": workflow_inline,
        "node_inline": node_inline,
        "chat_scope": chat_scope,
        "window_focus": window_focus,
        "window_focus_state": window_focus_state,
        "workflow_family_hint": workflow_family_hint,
    }


def _resolve_architect_guidance_scope(normalized: Dict[str, Any]) -> str:
    """
    MARKER_164.P1.PROJECT_ARCH_GUIDANCE_BIND.V1
    MARKER_164.P1.TASK_ARCH_GUIDANCE_BIND.V1
    Resolve architect guidance scope (project vs task) from normalized UI context.
    """
    node_kind = str(normalized.get("node_kind") or "")
    graph_kind = str(normalized.get("graph_kind") or "")
    nav_level = str(normalized.get("nav_level") or "")
    task_id = str(normalized.get("task_id") or "")
    task_drill_state = str(normalized.get("task_drill_state") or "")
    workflow_inline = bool(normalized.get("workflow_inline"))
    chat_scope = str(normalized.get("chat_scope") or "")
    if (
        chat_scope == "task"
        or node_kind == "task"
        or graph_kind == "project_task"
        or bool(task_id)
        or task_drill_state == "expanded"
        or workflow_inline
        or nav_level == "workflow"
    ):
        return "task_architect"
    return "project_architect"


def _build_role_aware_instruction_packet(role: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    MARKER_164.P1.SHARED_ROLE_AWARE_INSTRUCTION_CORE.V1
    Shared UI-state-driven instruction core for MYCO and architect quick chat.
    """
    normalized = _normalize_guidance_context(context)
    nav_level = normalized["nav_level"]
    node_kind = normalized["node_kind"]
    graph_kind = normalized["graph_kind"]
    role_key = normalized["role"]
    task_drill_state = normalized["task_drill_state"]
    node_drill_state = normalized["node_drill_state"]
    workflow_inline = normalized["workflow_inline"]
    node_inline = normalized["node_inline"]
    window_focus = normalized["window_focus"]
    window_focus_state = normalized["window_focus_state"]
    workflow_family_hint = normalized["workflow_family_hint"]
    # MARKER_164.P4.WINDOW_FOCUS_ROLE_PACKET_ACTIONS.V1:
    # Window-focus actions override generic node/drill actions for MYCO+architect quick guidance.
    if window_focus == "balance":
        next_actions = [
            f"balance window {window_focus_state or 'focused'}",
            "choose active API key (★) and provider/model",
            "confirm cost + in/out limits before run",
        ]
    elif window_focus == "stats":
        next_actions = [
            f"stats window {window_focus_state or 'focused'}",
            "inspect diagnostics + success/cost",
            "apply model/task correction then rerun",
        ]
    elif window_focus == "tasks":
        next_actions = [
            f"tasks window {window_focus_state or 'focused'}",
            "select active task and start/stop/retry",
            "monitor heartbeat and status transitions",
        ]
    elif window_focus == "context":
        next_actions = [
            f"context window {window_focus_state or 'focused'}",
            "inspect role/model/prompt and node details",
            "update model then run/retry from Tasks",
        ]
    elif window_focus == "chat":
        next_actions = [
            f"chat window {window_focus_state or 'focused'}",
            "ask architect/MYCO for concrete next step",
            "execute action from Tasks/Context",
        ]
    elif (task_drill_state == "expanded" and nav_level == "roadmap") or workflow_inline:
        if node_kind == "agent":
            if role_key == "architect":
                next_actions = [
                    "define/adjust subtasks",
                    f"pick team workflow ({workflow_family_hint})",
                    "run/start from Tasks and watch stream",
                ]
            elif role_key == "coder":
                next_actions = [
                    "open Context and verify coder model/prompt",
                    "run/retry coder from Tasks",
                    "inspect artifacts then send to verifier",
                ]
            elif role_key in {"verifier", "eval"}:
                next_actions = [
                    "open Context and check quality criteria",
                    "run verify/eval stage",
                    "on fail send retry to coder from Tasks",
                ]
            else:
                next_actions = [
                    "open Context for this agent",
                    "check model/prompt",
                    "run/retry from Tasks panel",
                ]
        else:
            next_actions = [
                "select agent node in workflow",
                f"choose team workflow ({workflow_family_hint})",
                "run/start or retry from Tasks panel",
            ]
    elif (node_drill_state == "expanded" and nav_level == "roadmap") or node_inline:
        next_actions = [
            "double-click deeper",
            "select task node in this module",
            "create task here from Tasks panel",
        ]
    elif nav_level == "workflow":
        next_actions = [
            "select agent node",
            "inspect stream/artifacts",
            "adjust model in Context if needed",
        ]
    elif node_kind == "task" or graph_kind == "project_task":
        next_actions = [
            f"task scope detected ({workflow_family_hint})",
            "press Enter to open workflow",
            "run/start from Tasks or switch team profile",
        ]
    elif node_kind == "agent":
        next_actions = [
            f"agent scope detected ({role_key or 'agent'})",
            "open Context and inspect model/prompt",
            "run/retry from Tasks panel",
        ]
    elif nav_level in {"tasks", "roadmap"}:
        next_actions = [
            "select node or task",
            "drill into workflow",
            "ask for dependency map",
        ]
    else:
        next_actions = [
            "select focus node",
            "ask MYCO for next action",
            "open Context for details",
        ]
    architect_scope = _resolve_architect_guidance_scope(normalized)
    return {
        "normalized": normalized,
        "architect_scope": architect_scope,
        "next_actions": next_actions,
        "workflow_family_hint": workflow_family_hint,
        "top_tools_hint": "Context model/prompt | Tasks run/retry | Stats diagnostics | Balance key/model",
    }


def _build_architect_quick_system_prompt(context: Dict[str, Any]) -> str:
    packet = _build_role_aware_instruction_packet("architect", context)
    normalized = packet["normalized"]
    scope = packet["architect_scope"]
    scope_label = "task architect" if scope == "task_architect" else "project architect"
    next_actions = packet["next_actions"]
    tools_hint = packet["top_tools_hint"]
    # MARKER_164.P1.CONTEXT_TOOLS_HINT_INJECTION.V1
    # Inject context-tool hints into architect quick-chat system prompt.
    return (
        f"You are {scope_label} in MYCELIUM.\n"
        f"Current view: {normalized['nav_level']}; node: {normalized['node_kind'] or 'project'}; "
        f"workflow family: {packet['workflow_family_hint']}.\n"
        f"Prioritize next actions in this order: {next_actions[0]} -> {next_actions[1]} -> {next_actions[2]}.\n"
        f"Always include concrete UI step hints using these tools: {tools_hint}.\n"
        "Answer concise, operational, and context-aware."
    )


def _build_myco_quick_reply(
    message: str,
    payload: Dict[str, Any],
    context: Dict[str, Any],
    retrieval: Optional[Dict[str, Any]] = None,
) -> str:
    """
    MARKER_162.P3.MYCO.JEPA_GEMMA_LOCAL_FASTPATH.V1
    MARKER_162.P3.P2.MYCO.ORCHESTRATION_SNAPSHOT.V1
    Lightweight MYCO response builder with hidden memory payload.
    """
    focus = dict(context or {})
    label = str(
        focus.get("label")
        or focus.get("task_id")
        or focus.get("taskId")
        or focus.get("node_id")
        or focus.get("nodeId")
        or "project"
    )
    user_name = str(payload.get("user_name") or payload.get("user_id") or "operator")
    active_project_id = str(payload.get("active_project_id") or "")
    recent = payload.get("recent_tasks_by_project") or {}
    active_recent = recent.get(active_project_id) if isinstance(recent, dict) and active_project_id else None
    active_recent = active_recent if isinstance(active_recent, list) else []
    active_task = active_recent[0] if active_recent else {}
    active_task_title = str(active_task.get("title") or "").strip()
    fastpath = payload.get("fastpath") or {}
    fast_mode = str(fastpath.get("mode") or "local")
    hidden = payload.get("hidden_index") or {}
    indexed_sources = int(hidden.get("source_count") or 0)
    orchestration = payload.get("orchestration") or {}
    multitask = orchestration.get("multitask") if isinstance(orchestration, dict) else {}
    multitask = multitask if isinstance(multitask, dict) else {}
    digest = orchestration.get("digest") if isinstance(orchestration, dict) else {}
    digest = digest if isinstance(digest, dict) else {}
    mt_active = int(multitask.get("active") or 0)
    mt_queued = int(multitask.get("queued") or 0)
    mt_done = int(multitask.get("done") or 0)
    mt_failed = int(multitask.get("failed") or 0)
    mt_cap = int(multitask.get("max_concurrent") or 0)
    mt_autodispatch = bool(multitask.get("auto_dispatch", False))
    mt_phase = str(multitask.get("phase") or "").strip()
    digest_phase = str(digest.get("phase") or "").strip()
    digest_summary = str(digest.get("summary") or digest.get("status") or "").strip()

    retrieval_obj = dict(retrieval or {})
    refs = retrieval_obj.get("items") if isinstance(retrieval_obj.get("items"), list) else []
    refs = refs[:2]
    ref_line = ""
    if refs:
        ref_names = ", ".join(
            str(r.get("source_path") or "").split("/")[-1]
            for r in refs
            if str(r.get("source_path") or "").strip()
        )
        if ref_names:
            ref_line = f"- hidden refs: {ref_names}\n"

    packet = _build_role_aware_instruction_packet("helper_myco", focus)
    normalized = packet["normalized"]
    nav_level = normalized["nav_level"]
    node_kind = normalized["node_kind"]
    role = normalized["role"]
    workflow_family_hint = packet["workflow_family_hint"]
    next_actions = packet["next_actions"]
    tools_hint = packet["top_tools_hint"]

    prompt = str(message or "").strip()
    if prompt.lower() in {"?", "/myco", "/help myco", "help"}:
        digest_line = f"- digest phase: {digest_phase}" if digest_phase else "- digest phase: n/a"
        return (
            f"MYCO {user_name}, quick guide:\n"
            f"- focus: {label}\n"
            f"- nav: {nav_level or 'n/a'}\n"
            f"- node: {node_kind or 'n/a'}"
            + (f" ({role})" if role else "")
            + "\n"
            f"- workflow family: {workflow_family_hint}\n"
            f"- mode: {fast_mode}\n"
            f"- multitask: active {mt_active} · queued {mt_queued} · done {mt_done}\n"
            f"- multitask errors: failed {mt_failed}\n"
            f"- multitask cfg: cap {mt_cap or 'n/a'} · auto_dispatch {'on' if mt_autodispatch else 'off'} · board phase {mt_phase or 'n/a'}\n"
            f"{digest_line}\n"
            f"{ref_line}"
            f"- hidden memory sources: {indexed_sources}\n"
            f"- tools: {tools_hint}\n"
            f"- next: {next_actions[0]} -> {next_actions[1]} -> {next_actions[2]}"
        )

    task_line = f"- active task: {active_task_title}" if active_task_title else "- active task: not pinned"
    digest_line = (
        f"- digest: phase {digest_phase} ({digest_summary})"
        if digest_phase and digest_summary
        else (f"- digest: phase {digest_phase}" if digest_phase else "- digest: n/a")
    )
    return (
        f"MYCO {user_name}, context loaded.\n"
        f"- focus: {label}\n"
        f"- nav: {nav_level or 'n/a'}\n"
        f"- node: {node_kind or 'n/a'}"
        + (f" ({role})" if role else "")
        + "\n"
        f"- workflow family: {workflow_family_hint}\n"
        f"{task_line}\n"
        f"- multitask: active {mt_active} · queued {mt_queued} · done {mt_done} · failed {mt_failed}\n"
        f"- multitask cfg: cap {mt_cap or 'n/a'} · auto_dispatch {'on' if mt_autodispatch else 'off'} · board phase {mt_phase or 'n/a'}\n"
        f"{digest_line}\n"
        f"{ref_line}"
        f"- project: {active_project_id or 'n/a'}\n"
        f"- hidden memory index: {indexed_sources} sources\n"
        f"- tools: {tools_hint}\n"
        f"- options: {next_actions[0]} | {next_actions[1]} | {next_actions[2]}\n"
        f"- tell me: explain node / plan next action / map dependencies"
    )


# ============================================================
# ROUTES
# ============================================================


@router.get("/chat/history")
async def get_chat_history(
    path: str = Query(..., description="Node path"), request: Request = None
):
    """
    Get chat history for a specific node.

    Returns history with message count.
    """
    components = _get_chat_components(request)
    chat_dir = components.get("CHAT_HISTORY_DIR")

    history = _load_chat_history(chat_dir, path)
    print(f"  [Chat] Loading history for '{path}': {len(history)} messages")

    return {
        "success": True,
        "history": history,
        "node_path": path,
        "count": len(history),
    }


@router.post("/chat/clear-history")
async def clear_chat_history(req: ClearHistoryRequest, request: Request):
    """
    Clear chat history for a specific node.
    """
    try:
        components = _get_chat_components(request)
        chat_dir = components.get("CHAT_HISTORY_DIR")

        file = _get_chat_history_file(chat_dir, req.path)
        if file.exists():
            file.unlink()
            return {"success": True, "message": "History cleared"}
        else:
            return {"success": True, "message": "No history to clear"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/quick")
async def api_chat_quick(req: QuickChatRequest, request: Request):
    """
    MARKER_162.P3.MYCO.JEPA_GEMMA_LOCAL_FASTPATH.V1
    MARKER_162.P3.MYCO.ENGRAM_USER_TASK_MEMORY.V1
    Lightweight chat endpoint for MCC MiniChat.
    """
    msg = str(req.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="message is required")

    role = str(req.role or "architect").strip().lower()
    context = dict(req.context or {})
    helper_mode = str(context.get("helper_mode") or context.get("helperMode") or "").strip().lower()
    is_myco = role == "helper_myco" or helper_mode in {"passive", "active"} or msg.lower() in {"?", "/myco", "/help myco", "help"}

    if is_myco:
        try:
            from src.services.project_config import ProjectConfig
            from src.services.myco_memory_bridge import (
                build_myco_memory_payload,
                persist_myco_runtime_facts,
                retrieve_myco_hidden_context,
            )
            from src.orchestration.context_packer import get_context_packer

            cfg = ProjectConfig.load()
            persist_myco_runtime_facts(
                user_id=str(req.user_id or "danila"),
                user_name=str((context or {}).get("user_name") or ""),
                active_project_id=str(getattr(cfg, "project_id", "") or ""),
                focus=context,
            )
            payload = build_myco_memory_payload(
                user_id=str(req.user_id or "danila"),
                active_project_id=str(getattr(cfg, "project_id", "") or ""),
                focus=context,
            )

            # Optional JEPA summary signal from context packer when prompt/context is verbose.
            retrieval = retrieve_myco_hidden_context(
                # MARKER_162.P4.P3.MYCO.RAG_STATE_KEY_ENRICHMENT.V1:
                # Enrich retrieval query with UI state key so guidance docs are retrieved by scenario.
                query=" ".join(
                    [
                        msg,
                        str(context.get("nav_level") or context.get("navLevel") or ""),
                        str(context.get("task_drill_state") or context.get("taskDrillState") or ""),
                        str(context.get("roadmap_node_drill_state") or context.get("roadmapNodeDrillState") or ""),
                        str(context.get("node_kind") or context.get("nodeKind") or ""),
                        str(context.get("graph_kind") or context.get("graphKind") or ""),
                        str(context.get("workflow_family") or context.get("workflowFamily") or ""),
                        str(context.get("workflow_id") or context.get("workflowId") or ""),
                        str(context.get("role") or ""),
                        str(context.get("window_focus") or context.get("windowFocus") or ""),
                        str(context.get("window_focus_state") or context.get("windowFocusState") or ""),
                    ]
                ).strip(),
                focus=context,
                top_k=3,
                min_score=0.22,
            )
            packed: Dict[str, Any] = {}
            try:
                packer = get_context_packer()
                packed = packer.pack_context(
                    user_message=msg,
                    context_data={
                        "myco_focus": context,
                        "myco_payload": {
                            "user_name": payload.get("user_name"),
                            "active_project_id": payload.get("active_project_id"),
                            "recent_tasks_by_project": payload.get("recent_tasks_by_project"),
                            "orchestration": payload.get("orchestration"),
                            "hidden_refs": retrieval.get("items"),
                        },
                    },
                    max_context_chars=2200,
                ) or {}
            except Exception:
                packed = {}

            response = _build_myco_quick_reply(msg, payload, context, retrieval)
            return {
                "success": True,
                "status": "ok",
                "reply": response,
                "response": response,
                "role": "helper_myco",
                "mode": "local_fastpath",
                "fastpath": payload.get("fastpath"),
                "hidden_index": payload.get("hidden_index"),
                "retrieval": retrieval,
                "packed_meta": packed.get("meta", {}),
                "marker": "MARKER_162.P3.MYCO.JEPA_GEMMA_LOCAL_FASTPATH.V1",
            }
        except Exception as e:
            return {
                "success": True,
                "status": "fallback",
                "reply": f"MYCO helper fallback: {str(e)[:160]}",
                "response": f"MYCO helper fallback: {str(e)[:160]}",
                "role": "helper_myco",
                "mode": "fallback",
            }

    # Architect quick path: lightweight single-turn model for MiniChat.
    try:
        from src.elisya.provider_registry import call_model_v2

        result = await call_model_v2(
            messages=[
                {"role": "system", "content": _build_architect_quick_system_prompt(context)},
                {"role": "user", "content": msg},
            ],
            model="grok-fast-4.1",
            source="polza",
            max_tokens=500,
            temperature=0.4,
        )

        reply = ""
        if isinstance(result, dict):
            message = result.get("message", {})
            if isinstance(message, dict):
                reply = str(message.get("content") or "").strip()
            elif isinstance(message, str):
                reply = message.strip()
        elif isinstance(result, str):
            reply = result.strip()

        if not reply:
            raise RuntimeError("empty quick chat reply")

        return {
            "success": True,
            "status": "ok",
            "reply": reply,
            "response": reply,
            "role": "assistant",
            "model": "grok-fast-4.1",
            "provider": "polza",
            "mode": "single_turn",
        }
    except Exception:
        return {
            "success": True,
            "status": "fallback",
            "reply": "Backend model unavailable",
            "response": "Backend model unavailable",
            "role": "assistant",
            "mode": "fallback",
        }


@router.post("/chat")
async def api_chat(req: ChatRequest, request: Request):
    """
    Universal Chat API endpoint - THE BIG ONE!

    Handles:
    1. Hostess routing (decides which agent/model)
    2. Agent orchestration (PM -> Architect -> Dev -> QA)
    3. Memory persistence (triple write)
    4. Evaluation scoring
    5. Response generation

    Flow:
    User Message -> Hostess Decision ->
    If simple: Direct LLM response
    If complex: Orchestrator workflow
    -> EvalAgent scoring -> Memory save -> Response
    """
    try:
        # === PHASE 80.3: MCP AGENT HANDLING ===
        # MCP agents are external - forward to team messaging
        if req.model_override and req.model_override.startswith("mcp/"):
            agent_id = req.model_override.replace("mcp/", "")
            conversation_id = req.conversation_id or str(uuid.uuid4())

            # Forward to team messages for Claude Code / Browser Haiku
            from src.api.routes.debug_routes import team_messages, KNOWN_AGENTS

            agent_info = KNOWN_AGENTS.get(agent_id, {})
            agent_name = agent_info.get("name", agent_id)

            # Add message to team buffer
            team_messages.append(
                {
                    "id": str(uuid.uuid4()),
                    "from": "user",
                    "to": agent_id,
                    "message": req.message,
                    "conversation_id": conversation_id,
                    "timestamp": time.time(),
                    "node_path": req.node_path,
                    "pending": True,
                }
            )

            # Keep buffer reasonable
            if len(team_messages) > 100:
                team_messages.pop(0)

            print(f"  [MCP] Message forwarded to {agent_name} via team messaging")

            # Return stub response
            if agent_id == "claude_code":
                stub_response = (
                    f"📨 Сообщение отправлено в **{agent_name}**.\n\n"
                    "Claude Code работает через MCP в терминале.\n"
                    "Проверьте терминал для ответа или используйте:\n"
                    "```\ncurl http://localhost:8000/api/debug/team-messages\n```"
                )
            elif agent_id == "browser_haiku":
                stub_response = (
                    f"📨 Сообщение отправлено в **{agent_name}**.\n\n"
                    "Browser Haiku работает в Chrome Console.\n"
                    "Используйте `vetkaAPI.getTeamMessages()` в консоли браузера."
                )
            else:
                stub_response = (
                    f"📨 Сообщение отправлено агенту **{agent_name}**.\n\n"
                    "MCP агенты работают вне VETKA. Проверьте соответствующий интерфейс."
                )

            return {
                "conversation_id": conversation_id,
                "response": stub_response,
                "model": req.model_override,
                "provider": "mcp",
                "processing_time_ms": 0,
                "agent": agent_name,
                "action": "mcp_forward",
                "mcp_pending": True,
                "timestamp": time.time(),
            }

        # Get components via DI
        components = _get_chat_components(request)
        get_memory_manager = components["get_memory_manager"]
        get_orchestrator = components["get_orchestrator"]
        get_hostess = components.get("get_hostess")
        get_model_for_task = components.get("get_model_for_task")
        is_model_banned = components.get("is_model_banned")
        model_router = components.get("model_router")
        api_gateway = components.get("api_gateway")
        qdrant_manager = components.get("qdrant_manager")

        # Feature flags
        ELISYA_ENABLED = components.get("ELISYA_ENABLED", False)
        PARALLEL_MODE = components.get("PARALLEL_MODE", False)
        HOSTESS_AVAILABLE = components.get("HOSTESS_AVAILABLE", False)
        # API_GATEWAY_AVAILABLE = components.get("API_GATEWAY_AVAILABLE", False)  # REMOVED: Phase 95
        MODEL_ROUTER_V2_AVAILABLE = components.get("MODEL_ROUTER_V2_AVAILABLE", False)
        QDRANT_AUTO_RETRY_AVAILABLE = components.get(
            "QDRANT_AUTO_RETRY_AVAILABLE", False
        )

        # Import EvalAgent
        from src.agents.eval_agent import EvalAgent

        # Extract parameters
        user_message = req.message.strip()
        conversation_id = req.conversation_id or str(uuid.uuid4())
        model_override = req.model_override
        model_source = req.model_source  # Phase 111.10: Multi-provider routing
        system_prompt = req.system_prompt
        temperature = req.temperature
        max_tokens = req.max_tokens
        node_id = req.node_id
        node_path = req.node_path
        file_path = req.file_path

        # Build user_data for orchestrator
        user_data = None
        if node_id or node_path or file_path or model_source:
            user_data = {
                "node_id": node_id,
                "node_path": node_path or file_path,
                "file_path": file_path or node_path,
                "model_source": model_source,  # Phase 111.10
            }

        # Validate
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")

        if len(user_message) > 10000:
            raise HTTPException(
                status_code=400, detail="Message too long (max 10000 chars)"
            )

        print(f"\n{'=' * 70}")
        print(f"  [Chat] REQUEST: {conversation_id}")
        print(f"  [Chat] Message: {user_message[:100]}...")
        if user_data:
            print(f"  [Chat] Node: {user_data.get('node_path', 'unknown')}")
        print(f"{'=' * 70}")

        # Get managers
        memory = get_memory_manager() if get_memory_manager else None
        orchestrator = get_orchestrator() if get_orchestrator else None
        eval_agent = EvalAgent(memory_manager=memory) if memory else None

        # ============ UNIFIED MODEL ROUTING ============
        if get_model_for_task:
            selected_model = model_override or get_model_for_task("default", "cheap")
        else:
            selected_model = model_override or "deepseek/deepseek-chat"
        provider_info = {}

        # Check if model is banned
        if is_model_banned and is_model_banned(selected_model):
            print(f"  [Chat] Model {selected_model} is BANNED! Using deepseek instead.")
            selected_model = (
                get_model_for_task("default", "cheap")
                if get_model_for_task
                else "deepseek/deepseek-chat"
            )

        if MODEL_ROUTER_V2_AVAILABLE and model_router:
            try:
                complexity = "MEDIUM" if len(user_message.split()) > 20 else "LOW"
                routed_model, metadata = model_router.select_model("chat", complexity)
                if routed_model and (
                    not is_model_banned or not is_model_banned(routed_model)
                ):
                    selected_model = routed_model
                    provider_info = metadata or {}
                elif routed_model and is_model_banned and is_model_banned(routed_model):
                    print(
                        f"  [Chat] Router suggested banned model {routed_model}, using cheap default"
                    )
                print(f"  [Chat] Model Router v2 selected: {selected_model}")
            except Exception as e:
                print(f"  [Chat] Model Router error (using fallback): {e}")

        # Prepare context
        context = {
            "conversation_id": conversation_id,
            "user_message": user_message,
            "model": selected_model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "system_prompt": system_prompt or "You are a helpful AI assistant.",
            "timestamp": time.time(),
        }

        # ============ HOSTESS ROUTING ============
        hostess_decision = None
        hostess_start = time.time()

        if HOSTESS_AVAILABLE and get_hostess:
            try:
                hostess = get_hostess()
                hostess_decision = hostess.process(
                    user_message,
                    context={
                        "node_path": node_path,
                        "conversation_id": conversation_id,
                    },
                )
                hostess_time_ms = (time.time() - hostess_start) * 1000
                print(
                    f"  [Hostess] Decision: {hostess_decision['action']} (confidence: {hostess_decision['confidence']:.2f}, {hostess_time_ms:.0f}ms)"
                )

                # Handle quick_answer - respond immediately
                if hostess_decision["action"] == "quick_answer":
                    print(f"  [Hostess] Quick answer - bypassing orchestrator")
                    return {
                        "conversation_id": conversation_id,
                        "response": hostess_decision.get("result", ""),
                        "model": "hostess-qwen",
                        "provider": "ollama-local",
                        "processing_time_ms": round(hostess_time_ms, 2),
                        "eval_score": None,
                        "eval_feedback": None,
                        "metrics": {
                            "input_tokens": len(user_message.split()),
                            "output_tokens": len(
                                hostess_decision.get("result", "").split()
                            ),
                            "agent_scores": {
                                "hostess": hostess_decision.get("confidence", 0.9)
                            },
                        },
                        "agent": "Hostess",
                        "action": "quick_answer",
                        "timestamp": time.time(),
                    }

                # Handle clarify
                elif hostess_decision["action"] == "clarify":
                    print(f"  [Hostess] Clarification needed")
                    options_text = ""
                    if hostess_decision.get("options"):
                        options_text = "\n\nOptions:\n" + "\n".join(
                            [f"- {opt}" for opt in hostess_decision["options"]]
                        )

                    return {
                        "conversation_id": conversation_id,
                        "response": hostess_decision.get("result", "") + options_text,
                        "model": "hostess-qwen",
                        "provider": "ollama-local",
                        "processing_time_ms": round(hostess_time_ms, 2),
                        "needs_clarification": True,
                        "options": hostess_decision.get("options", []),
                        "agent": "Hostess",
                        "action": "clarify",
                        "timestamp": time.time(),
                    }

                # Handle search
                elif hostess_decision["action"] == "search":
                    query = hostess_decision.get("query", user_message)
                    print(f"  [Hostess] Search request: {query[:50]}...")

                    search_results = []
                    try:
                        if memory:
                            search_results = memory.semantic_search(query, limit=50)
                    except Exception as se:
                        print(f"  [Hostess] Search error: {se}")

                    if search_results:
                        result_text = f"Found {len(search_results)} results:\n\n"
                        for i, r in enumerate(search_results[:3], 1):
                            result_text += (
                                f"{i}. {r.get('title', r.get('path', 'Unknown'))}\n"
                            )
                            result_text += f"   {r.get('snippet', r.get('content', '')[:100])}...\n\n"
                    else:
                        result_text = f"No results found for: {query}"

                    return {
                        "conversation_id": conversation_id,
                        "response": result_text,
                        "model": "hostess-qwen",
                        "provider": "ollama-local",
                        "processing_time_ms": round(
                            (time.time() - hostess_start) * 1000, 2
                        ),
                        "agent": "Hostess",
                        "action": "search",
                        "search_results": search_results[:5] if search_results else [],
                        "timestamp": time.time(),
                    }

                # Handle show_file
                elif hostess_decision["action"] == "show_file":
                    file_to_show = hostess_decision.get("file_path", node_path)
                    print(f"  [Hostess] Show file: {file_to_show}")

                    file_content = ""
                    try:
                        if file_to_show and os.path.exists(file_to_show):
                            with open(file_to_show, "r", encoding="utf-8") as f:
                                file_content = f.read(10000)
                    except Exception as fe:
                        file_content = f"Error reading file: {fe}"

                    return {
                        "conversation_id": conversation_id,
                        "response": f"```\n{file_content}\n```"
                        if file_content
                        else f"File not found: {file_to_show}",
                        "model": "hostess-qwen",
                        "provider": "ollama-local",
                        "processing_time_ms": round(
                            (time.time() - hostess_start) * 1000, 2
                        ),
                        "agent": "Hostess",
                        "action": "show_file",
                        "file_path": file_to_show,
                        "timestamp": time.time(),
                    }

                # agent_call and chain_call continue to orchestrator
                elif hostess_decision["action"] == "agent_call":
                    print(
                        f"  [Hostess] Single agent: {hostess_decision.get('agent', 'Dev')} - continuing to orchestrator"
                    )

                elif hostess_decision["action"] == "chain_call":
                    print(
                        f"  [Hostess] Full chain requested - continuing to orchestrator"
                    )

            except Exception as he:
                print(f"  [Hostess] Error: {he}, continuing with orchestrator")
                hostess_decision = None

        # ============ PARALLEL AGENT PROCESSING ============
        agent_response = None
        processing_time = 0
        agent_scores = {}

        if ELISYA_ENABLED and PARALLEL_MODE and orchestrator:
            try:
                start_time = time.time()

                # Execute through orchestrator with parallel agents
                workflow_id = conversation_id
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: asyncio.run(
                        orchestrator.execute_full_workflow_streaming(
                            user_message, workflow_id, user_data=user_data
                        )
                    ),
                )

                processing_time = time.time() - start_time
                agent_response = result.get("dev_result", {}).get(
                    "content", ""
                ) or result.get("pm_result", {}).get("content", "")
                agent_scores = {
                    "pm": result.get("pm_score", 0),
                    "dev": result.get("dev_score", 0),
                    "qa": result.get("qa_score", 0),
                    "eval": result.get("eval_score", 0),
                }

                print(
                    f"  [Chat] Parallel orchestrator processed in {processing_time:.2f}s"
                )

            except Exception as e:
                print(f"  [Chat] Parallel orchestrator error: {e}")
                agent_response = None

        # Fallback: Direct API call via API Gateway or Ollama
        if not agent_response:
            start_time = time.time()

            try:
                # REMOVED: API Gateway v2 (Phase 95) - replaced by direct_api_calls.py
                # if API_GATEWAY_AVAILABLE and api_gateway:
                #     try:
                #         print(f"  [Chat] Calling API Gateway v2...")
                #         full_prompt = (
                #             f"{context['system_prompt']}\n\nUser: {user_message}"
                #         )
                #         api_result = api_gateway.call_model(
                #             task_type="chat", prompt=full_prompt, complexity="MEDIUM"
                #         )
                #         if api_result.success:
                #             agent_response = api_result.response
                #             print(
                #                 f"  [Chat] API Gateway v2 response received ({api_result.model})"
                #             )
                #         else:
                #             print(f"  [Chat] API Gateway v2 failed: {api_result.error}")
                #             agent_response = None
                #     except Exception as api_err:
                #         print(f"  [Chat] API Gateway v2 error: {api_err}")
                #         agent_response = None

                # Fallback to Ollama (now primary fallback)
                if not agent_response:
                    try:
                        print(f"  [Chat] Calling Ollama fallback...")
                        import ollama

                        ollama_response = ollama.chat(
                            model="qwen2:7b",
                            messages=[
                                {"role": "system", "content": context["system_prompt"]},
                                {"role": "user", "content": user_message},
                            ],
                            stream=False,
                        )
                        agent_response = ollama_response.get("message", {}).get(
                            "content", ""
                        )
                        print(f"  [Chat] Ollama response received")
                    except Exception as ollama_err:
                        print(f"  [Chat] Ollama error: {ollama_err}")
                        agent_response = f"[Fallback] Unable to process (tried API Gateway and Ollama)"

                processing_time = time.time() - start_time

            except Exception as e:
                print(f"  [Chat] All API fallbacks failed: {e}")
                agent_response = f"[Error] Could not process: {str(e)[:100]}"
                processing_time = time.time() - start_time

        # ============ MEMORY PERSISTENCE (TRIPLE WRITE) ============
        conversation_entry = {
            "conversation_id": conversation_id,
            "role": "user",
            "content": user_message,
            "model": selected_model,
            "timestamp": context["timestamp"],
            "metadata": {
                "source": "api_chat",
                "processing_time": processing_time,
                "provider": provider_info.get("provider", "unknown"),
            },
        }

        response_entry = {
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": agent_response or "(No response)",
            "model": selected_model,
            "timestamp": time.time(),
            "metadata": {
                "source": "api_chat",
                "processing_time": processing_time,
                "agent_scores": agent_scores,
            },
        }

        # Save to memory (Weaviate)
        if memory:
            try:
                memory.triple_write({**conversation_entry, "type": "conversation"})
                memory.triple_write({**response_entry, "type": "conversation"})
                print(f"  [Chat] Saved to Weaviate + ChangeLog (triple_write)")
            except Exception as e:
                print(f"  [Chat] Weaviate save error: {e}")

        # Save to Qdrant if available
        if QDRANT_AUTO_RETRY_AVAILABLE and qdrant_manager:
            try:
                qdrant_manager.add_conversation_vector(
                    conversation_id=conversation_id,
                    user_message=user_message,
                    response=agent_response or "",
                    model=selected_model,
                    agent_scores=agent_scores,
                )
                print(f"  [Chat] Saved to Qdrant")
            except Exception as e:
                print(f"  [Chat] Qdrant save error: {e}")

        # ============ EVALAGENT SCORING ============
        eval_score = None
        eval_feedback = {}

        if eval_agent:
            try:
                eval_result = eval_agent.evaluate(
                    original_task=user_message,
                    agent_output=agent_response or "",
                    agent_name="chat",
                    complexity="MEDIUM",
                )
                eval_score = eval_result.get("score", 0)
                eval_feedback = eval_result.get(
                    "feedback", eval_result.get("reasoning", "")
                )
                print(f"  [Chat] EvalAgent score: {eval_score:.2f}/10")
            except Exception as e:
                print(f"  [Chat] EvalAgent error: {e}")

        # ============ RESPONSE ASSEMBLY ============
        api_response = {
            "conversation_id": conversation_id,
            "response": agent_response or "(Processing error)",
            "model": selected_model,
            "provider": provider_info.get("provider", "unknown"),
            "processing_time_ms": round(processing_time * 1000, 2),
            "eval_score": round(eval_score, 2) if eval_score is not None else None,
            "eval_feedback": eval_feedback,
            "metrics": {
                "input_tokens": len(user_message.split()),
                "output_tokens": len((agent_response or "").split()),
                "agent_scores": agent_scores,
            },
            "timestamp": time.time(),
        }

        print(f"\n  [Chat] RESPONSE: {conversation_id}")
        print(f"     Model: {selected_model}")
        print(f"     Time: {processing_time * 1000:.1f}ms")
        eval_score_display = f"{eval_score:.2f}" if eval_score is not None else "N/A"
        print(f"     Score: {eval_score_display}")
        print(f"{'=' * 70}\n")

        return api_response

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        error_msg = str(e)
        print(f"\n  [Chat] ERROR: {error_msg}")
        print(traceback.format_exc())
        print(f"{'=' * 70}\n")
        raise HTTPException(status_code=500, detail=error_msg)
