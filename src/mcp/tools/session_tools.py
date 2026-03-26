"""MCP Session Tools - Fat session initialization with ELISION compression.

Provides tools for efficient session bootstrapping with compressed context:
- vetka_session_init: Initialize MCP session with fat context (user preferences, CAM activations, recent states)
- vetka_session_status: Get current session status and validity

These tools enable AI agents to efficiently bootstrap sessions with
compressed user preferences, recent states, and CAM activations.
Uses ELISION compression to reduce token usage by 40-60%.

Features:
- AURA user preference loading (hot RAM cache + cold Qdrant)
- MCP state manager integration for persistence
- JARVIS prompt enricher for context compression
- Async/sync execution support

@status: active
@phase: 108
@depends: src/mcp/tools/base_tool.py, src/memory/aura_store.py, src/mcp/state/mcp_state_manager.py, src/memory/jarvis_prompt_enricher.py
@used_by: src/mcp/vetka_mcp_bridge.py, src/mcp/tools/__init__.py

MARKER_MCP_CHAT_READY: Phase 108.1 - Unified MCP-Chat ID linking
- session_init accepts chat_id parameter (optional)
- If provided: session_id = chat_id (link to existing chat)
- If not provided: creates new chat, uses its ID as session_id
- Result: Every MCP session linked to VETKA chat for persistent context

MARKER_109_1_VIEWPORT_INJECT: Phase 109.1 - Dynamic Context Injection
- include_viewport now ACTUALLY builds viewport summary (was dead code)
- include_pinned now ACTUALLY builds pinned files context (was dead code)
- Added context_dag support for Jarvis super-agent integration
- Hyperlinks format: [→ label] for lazy loading via MCP tools
"""

from typing import Dict, Any, Optional
import time
import asyncio
import logging
import json as _json  # MARKER_181.5.4: Prevent shadowing in async call chain
from pathlib import Path
from .base_tool import BaseMCPTool


class _JepaCacheHit(Exception):
    """MARKER_199.JEPA_TTL: Sentinel to skip JEPA computation when cache is warm."""

    pass


logger = logging.getLogger(__name__)


# Project digest path (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DIGEST_PATH = PROJECT_ROOT / "data" / "project_digest.json"


def load_project_digest() -> Optional[Dict[str, Any]]:
    """
    Load project digest for agent context initialization.

    Returns condensed project state including:
    - Current phase number and status
    - Key achievements and pending items
    - System status (Qdrant collections, MCP)
    - Agent instructions

    Returns None if digest not found or invalid.
    """
    try:
        if DIGEST_PATH.exists():
            with open(DIGEST_PATH, "r") as f:
                digest = _json.load(f)

            # Return condensed version for MCP context
            # MARKER_187.7: Include full agent_focus for per-agent filtering downstream
            return {
                "phase": digest.get("current_phase", {}),
                "summary": digest.get("summary", {}).get("headline", ""),
                "achievements": digest.get("summary", {}).get("key_achievements", [])[
                    :5
                ],
                "pending": digest.get("summary", {}).get("pending_items", [])[:3],
                "system": digest.get("system_status", {}),
                "instructions": digest.get("agent_instructions", {}),
                "last_updated": digest.get("last_updated"),
                "recent_fixes": [
                    f.get("id") for f in digest.get("recent_fixes", [])[:5]
                ],
                "agent_focus": digest.get("agent_focus", {}),
            }
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# MARKER_195.2.4: Emotion display helpers
# ---------------------------------------------------------------------------


def _compute_mood_label(tool_emotions: Dict[str, Dict[str, float]]) -> str:
    """Derive a single mood label from per-tool emotions.

    Priority: cautious > wary > confident > exploratory > balanced.
    """
    if not tool_emotions:
        return "balanced"
    n = len(tool_emotions)
    avg_curiosity = sum(e.get("curiosity", 0) for e in tool_emotions.values()) / n
    avg_trust = sum(e.get("trust", 0) for e in tool_emotions.values()) / n
    avg_caution = sum(e.get("caution", 0) for e in tool_emotions.values()) / n

    if avg_caution > 0.6:
        return "cautious"
    if avg_trust < 0.3:
        return "wary"
    if avg_trust > 0.7:
        return "confident"
    if avg_curiosity > 0.6:
        return "exploratory"
    return "balanced"


def _generate_emotion_summary(tool_emotions: Dict[str, Dict[str, float]]) -> str:
    """Build a short human-readable summary of emotion state."""
    if not tool_emotions:
        return ""
    parts = []
    high_curiosity = [
        t for t, e in tool_emotions.items() if e.get("curiosity", 0) > 0.7
    ]
    low_trust = [t for t, e in tool_emotions.items() if e.get("trust", 0) < 0.3]
    high_caution = [t for t, e in tool_emotions.items() if e.get("caution", 0) > 0.6]

    if high_curiosity:
        parts.append(f"High curiosity for {len(high_curiosity)} tool(s)")
    if low_trust:
        names = ", ".join(low_trust[:3])
        parts.append(f"Low trust for {names}")
    if high_caution:
        parts.append(f"High caution for {len(high_caution)} tool(s)")

    return ". ".join(parts) + "." if parts else "Balanced emotional state."


class SessionInitTool(BaseMCPTool):
    """Initialize MCP session with fat context and ELISION compression."""

    @property
    def name(self) -> str:
        return "vetka_session_init"

    @property
    def description(self) -> str:
        return (
            "Initialize MCP session with fat context including PROJECT DIGEST. "
            "Returns: current phase info, key achievements, pending items, system status, "
            "user preferences from AURA, recent states, and CAM activations. "
            "Returns compressed context via ELISION for efficient LLM consumption. "
            "IMPORTANT: Call this at the start of EVERY conversation to get project state!"
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "User identifier (default: 'default')",
                    "default": "default",
                },
                "group_id": {
                    "type": "string",
                    "description": "Group chat ID if in group context (optional)",
                },
                "chat_id": {
                    "type": "string",
                    "description": "Chat ID to link session with existing chat (optional, Phase 108.1)",
                },
                "include_viewport": {
                    "type": "boolean",
                    "description": "Include 3D viewport context if available",
                    "default": True,
                },
                "include_pinned": {
                    "type": "boolean",
                    "description": "Include pinned files context",
                    "default": True,
                },
                "compress": {
                    "type": "boolean",
                    "description": "Apply ELISION compression to context",
                    "default": True,
                },
                "max_context_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens for context (default: 4000)",
                    "default": 4000,
                },
                "role": {
                    "type": "string",
                    "description": "Agent callsign (e.g. Alpha, Beta, Zeta). If provided, session is bound to this role and task board is unlocked. If omitted, falls back to branch detection.",
                },
            },
            "required": [],
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute synchronously by running async in event loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create future for async execution
                future = asyncio.ensure_future(self._execute_async(arguments))
                # Can't await in sync context, return pending status
                return {
                    "success": True,
                    "result": {
                        "status": "initializing",
                        "message": "Session initialization started asynchronously",
                    },
                }
            else:
                return loop.run_until_complete(self._execute_async(arguments))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self._execute_async(arguments))

    async def _execute_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async implementation of session initialization."""
        # MARKER_191.5: user_id resolution chain: arg > env > fallback
        import os

        user_id = (
            arguments.get("user_id") or os.environ.get("VETKA_USER_ID") or "danila"
        )
        group_id = arguments.get("group_id")
        chat_id = arguments.get("chat_id")  # MARKER_108_1: Unified MCP-Chat ID
        include_viewport = arguments.get("include_viewport", True)
        include_pinned = arguments.get("include_pinned", True)
        compress = arguments.get("compress", True)
        max_context_tokens = arguments.get("max_context_tokens", 4000)
        role_name = arguments.get("role")  # MARKER_196.1.3: explicit role declaration

        # MARKER_108_1: Unified MCP-Chat ID
        # If chat_id provided, use it as session_id
        # If not, create new chat and use its ID
        if chat_id:
            session_id = chat_id
            linked_to_existing = True
        else:
            # Create new VETKA chat and use its ID as session_id
            try:
                from src.chat.chat_history_manager import get_chat_history_manager

                chat_mgr = get_chat_history_manager()
                # Create chat with MCP context
                new_chat_id = chat_mgr.get_or_create_chat(
                    file_path="unknown",
                    context_type="topic",
                    topic="MCP Session",
                    display_name=f"MCP {user_id[:8]}",
                )
                session_id = new_chat_id
                chat_id = new_chat_id
                linked_to_existing = False
            except Exception as e:
                # Fallback to old session_id format if chat creation fails
                session_id = (
                    f"session_{user_id}_{group_id or 'solo'}_{int(time.time())}"
                )
                chat_id = None
                linked_to_existing = False
                print(f"[SessionInit] Failed to create chat, using session_id: {e}")

        context = {
            "session_id": session_id,
            "chat_id": chat_id,  # MARKER_108_1: Unified ID
            "linked": chat_id is not None,  # MARKER_108_1: Link status
            "linked_to_existing": linked_to_existing,
            "user_id": user_id,
            "group_id": group_id,
            "initialized": True,
            "initialized_at": time.time(),
        }

        # Load project digest for agent context
        project_digest = load_project_digest()
        if project_digest:
            context["project_digest"] = project_digest
            context["current_phase"] = project_digest.get("phase", {})
            # Add agent instructions to top-level for easy access
            if project_digest.get("instructions"):
                context["agent_instructions"] = project_digest["instructions"]
            # MARKER_187.7: Per-agent focus — extract only this agent's section
            agent_focus_all = project_digest.get("agent_focus", {})
            if agent_focus_all:
                context["_all_agent_focus"] = agent_focus_all  # full map for debug

        # MARKER_199.PARALLEL_IO: Run independent I/O tasks concurrently
        # Previously these were 4 sequential awaits (~400-1500ms total).
        # Now they run in parallel — total time = max(individual times).

        async def _load_aura_prefs():
            """MARKER_191.5: Get user preferences from AURA with auto-bootstrap."""
            try:
                from src.memory.aura_store import get_aura_store
                from src.memory.user_memory import create_user_preferences

                aura = get_aura_store()
                prefs = aura.get_user_preferences(user_id)
                if not prefs:
                    prefs = create_user_preferences(user_id)
                    aura.set_preference(
                        agent_type="default",
                        user_id=user_id,
                        category="communication_style",
                        key="preferred_language",
                        value="ru",
                    )
                    prefs = aura.get_user_preferences(user_id)
                    logger.info(
                        f"[session_init] Auto-bootstrapped AURA profile for user_id={user_id}"
                    )
                result = {"user_id": prefs.user_id, "has_preferences": True}
                if hasattr(prefs, "communication_style"):
                    result["communication_style"] = getattr(
                        prefs.communication_style, "__dict__", {}
                    )
                if hasattr(prefs, "viewport_patterns"):
                    result["viewport_patterns"] = getattr(
                        prefs.viewport_patterns, "__dict__", {}
                    )
                return result
            except Exception as e:
                return {"user_id": user_id, "has_preferences": False, "_error": str(e)}

        async def _load_mcp_states():
            try:
                from src.mcp.state import get_mcp_state_manager

                mcp_mgr = get_mcp_state_manager()
                recent = await mcp_mgr.get_all_states(limit=10)
                return {"count": len(recent), "ids": list(recent.keys())[:5]}
            except Exception as e:
                return {"_error": str(e)}

        async def _load_viewport():
            if not include_viewport:
                return None
            try:
                viewport_context = await self._get_viewport_context(session_id)
                if viewport_context:
                    from src.api.handlers.message_utils import build_viewport_summary

                    viewport_summary = build_viewport_summary(viewport_context)
                    if viewport_summary:
                        return {
                            "summary": viewport_summary,
                            "viewport": {
                                "zoom": viewport_context.get("zoom_level", 1),
                                "visible_count": len(
                                    viewport_context.get("viewport_nodes", [])
                                ),
                                "pinned_count": len(
                                    viewport_context.get("pinned_nodes", [])
                                ),
                                "hyperlink": "[→ viewport] vetka_get_viewport_detail",
                            },
                        }
            except Exception as e:
                return {"_error": str(e)}
            return None

        async def _load_pinned():
            if not include_pinned:
                return None
            try:
                pinned_files = await self._get_pinned_files(session_id, chat_id)
                if pinned_files:
                    from src.api.handlers.message_utils import build_pinned_context

                    pinned_context = build_pinned_context(pinned_files, max_files=5)
                    if pinned_context:
                        return {
                            "context": pinned_context,
                            "pinned": {
                                "count": len(pinned_files),
                                "files": [
                                    pf.get("name", pf.get("path", ""))
                                    for pf in pinned_files[:5]
                                ],
                                "hyperlink": "[→ pins] vetka_get_pinned_files",
                            },
                        }
            except Exception as e:
                return {"_error": str(e)}
            return None

        aura_result, mcp_result, viewport_result, pinned_result = await asyncio.gather(
            _load_aura_prefs(),
            _load_mcp_states(),
            _load_viewport(),
            _load_pinned(),
            return_exceptions=True,
        )

        # Unpack AURA
        if isinstance(aura_result, dict):
            err = aura_result.pop("_error", None)
            comm_style = aura_result.pop("communication_style", None)
            vp_patterns = aura_result.pop("viewport_patterns", None)
            context["user_preferences"] = aura_result
            if comm_style:
                context["communication_style"] = comm_style
            if vp_patterns:
                context["viewport_patterns"] = vp_patterns
            if err:
                context["user_preferences_error"] = err
        else:
            context["user_preferences"] = {"user_id": user_id, "has_preferences": False}

        # Unpack MCP states
        if isinstance(mcp_result, dict) and "_error" not in mcp_result:
            context["recent_states_count"] = mcp_result["count"]
            context["recent_state_ids"] = mcp_result["ids"]
        elif isinstance(mcp_result, dict):
            context["recent_states_error"] = mcp_result["_error"]

        # Unpack viewport
        if isinstance(viewport_result, dict) and "_error" not in viewport_result:
            context["viewport_summary"] = viewport_result.get("summary")
            context["viewport"] = viewport_result.get("viewport")
        elif isinstance(viewport_result, dict):
            context["viewport_error"] = viewport_result["_error"]

        # Unpack pinned
        if isinstance(pinned_result, dict) and "_error" not in pinned_result:
            context["pinned_context"] = pinned_result.get("context")
            context["pinned"] = pinned_result.get("pinned")
        elif isinstance(pinned_result, dict):
            context["pinned_error"] = pinned_result["_error"]

        # MARKER_197.ELISION: compression was computing compressed_str but never applying it.
        # Removed the misleading compression metadata block — it was reporting fake savings.
        # Real token reduction comes from stripping bloat keys below (MARKER_197.SLIM).

        # Save session state — fire and forget (not needed for current session response)
        # MARKER_199.PARALLEL_IO: moved from blocking await to background task
        try:
            from src.mcp.state import get_mcp_state_manager

            mcp = get_mcp_state_manager()
            asyncio.ensure_future(mcp.save_state(session_id, context, ttl_seconds=3600))
            context["persisted"] = True
        except Exception as e:
            context["persisted"] = False
            context["persist_error"] = str(e)

        # MARKER_178.1.1: Load active tasks from TaskBoard
        try:
            from src.orchestration.task_board import get_task_board

            board = get_task_board()
            # MARKER_181.5.6: Fixed list_tasks() → get_queue() (method was renamed)
            pending = board.get_queue(status="pending")
            in_progress = board.get_queue(status="in_progress")
            # MARKER_186.4: Count tasks awaiting merge (done_worktree)
            done_worktree = board.get_queue(status="done_worktree")
            # MARKER_196.QA: QA pipeline status counts
            need_qa = board.get_queue(status="need_qa")
            verified = board.get_queue(status="verified")
            needs_fix = board.get_queue(status="needs_fix")
            claimed = board.get_queue(status="claimed")
            context["task_board_summary"] = {
                "pending_count": len(pending),
                "in_progress_count": len(in_progress),
                "claimed_count": len(claimed),
                "done_worktree_count": len(done_worktree),
                "need_qa_count": len(need_qa),
                "verified_count": len(verified),
                "needs_fix_count": len(needs_fix),
                "top_pending": [
                    {
                        "task_id": t.get("task_id", "?"),
                        "title": t.get("title", "")[:60],
                        "priority": t.get("priority", 5),
                    }
                    for t in pending[:5]
                ],
                "in_progress": [
                    {
                        "task_id": t.get("task_id", "?"),
                        "title": t.get("title", "")[:60],
                        "assigned_to": t.get("assigned_to", ""),
                    }
                    for t in in_progress[:5]
                ],
                "awaiting_merge": [
                    {
                        "task_id": t.get("task_id", "?"),
                        "title": t.get("title", "")[:60],
                        "assigned_to": t.get("assigned_to", ""),
                    }
                    for t in done_worktree[:5]
                ],
                "qa_queue": [
                    {
                        "task_id": t.get("task_id", "?"),
                        "title": t.get("title", "")[:60],
                        "assigned_to": t.get("assigned_to", ""),
                    }
                    for t in need_qa[:5]
                ],
            }
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"TaskBoard load failed: {e}")

        # MARKER_ZETA.DOC_SNIPPETS: Inject doc snippets for top pending tasks
        try:
            from src.mcp.tools.task_board_tools import _load_docs_content_sync

            top_doc_hints = []
            for t in pending[:3] if pending else []:
                # Only load if task has docs defined
                if t.get("architecture_docs") or t.get("recon_docs"):
                    snippet = _load_docs_content_sync(t, budget=500, per_doc=500)
                    if snippet:
                        # Extract just the content, strip DOCS header/footer
                        lines = snippet.strip().split("\n")
                        content_lines = [
                            l for l in lines if not l.startswith("---") and l.strip()
                        ]
                        brief = "\n".join(content_lines[:6])  # First 6 lines max
                        if brief:
                            top_doc_hints.append(
                                f"[{t.get('task_id', '?')}] {t.get('title', '')[:50]}: {brief[:200]}"
                            )
            if top_doc_hints:
                context.setdefault("context_hints", []).extend(top_doc_hints)
        except Exception:
            pass  # Doc injection optional — don't block session_init

        # MARKER_187.2: semantic_recall — inject past learnings from Qdrant
        try:
            from src.orchestration.resource_learnings import get_learnings_for_architect

            # Build query from digest + top pending task
            tb = context.get("task_board_summary", {})
            digest_summary = context.get("project_digest", {}).get("summary", "")
            top_task = (
                (tb.get("top_pending") or [{}])[0].get("title", "")
                if tb.get("top_pending")
                else ""
            )
            in_prog = (
                (tb.get("in_progress") or [{}])[0].get("title", "")
                if tb.get("in_progress")
                else ""
            )
            query_parts = [p for p in [digest_summary, top_task, in_prog] if p]
            if query_parts:
                recall_query = " | ".join(query_parts)
                lessons = await get_learnings_for_architect(recall_query, limit=5)
                if lessons:
                    context["semantic_lessons"] = lessons
        except Exception:
            pass  # Qdrant unavailable — graceful fallback, no block

        # MARKER_ZETA.F4.ENGRAM: Inject ENGRAM learnings into session_init
        try:
            from src.memory.engram_cache import get_engram_cache

            _engram = get_engram_cache()
            _engram_ctx = {}
            # Danger entries — permanent, critical anti-patterns
            _dangers = _engram.get_danger_entries()
            if _dangers:
                _engram_ctx["dangers"] = [
                    {"key": e.key, "value": e.value[:200], "hits": e.hit_count}
                    for e in _dangers[:5]
                ]
            # Architecture principles — permanent learnings
            _arch = _engram.get_all_by_category("architecture")
            if _arch:
                _engram_ctx["architecture"] = [
                    {"key": e.key, "value": e.value[:200], "hits": e.hit_count}
                    for e in _arch[:5]
                ]
            # Top patterns by hit_count — most validated learnings
            _patterns = _engram.get_all_by_category("pattern")
            if _patterns:
                _patterns_sorted = sorted(
                    _patterns, key=lambda x: x.hit_count, reverse=True
                )
                _engram_ctx["patterns"] = [
                    {"key": e.key, "value": e.value[:200], "hits": e.hit_count}
                    for e in _patterns_sorted[:5]
                ]
            if _engram_ctx:
                _engram_ctx["stats"] = _engram.stats()
                context["engram_learnings"] = _engram_ctx
        except Exception:
            pass  # ENGRAM errors never block session init

        # MARKER_199.DIGEST: Hot ideas + new tools surface in session_init
        # Sources: ENGRAM debrief::idea entries ranked by hit_count,
        # tool_catalog.json tools with 0 CORTEX records = undiscovered.
        try:
            _digest = {}

            # 1. HOT IDEAS — debrief ideas from ENGRAM, ranked by hit_count
            _engram_for_digest = _engram if "_engram" in dir() else None
            if _engram_for_digest is None:
                from src.memory.engram_cache import get_engram_cache
                _engram_for_digest = get_engram_cache()
            _all_patterns = _engram_for_digest.get_all_by_category("pattern")
            _ideas = [e for e in _all_patterns if "::debrief::idea::" in e.key]
            if _ideas:
                _ideas.sort(key=lambda x: x.hit_count, reverse=True)
                _digest["hot_ideas"] = [
                    {"key": e.key[:80], "value": e.value[:120], "hits": e.hit_count}
                    for e in _ideas[:5]
                ]

            # 2. NEW TOOLS — tools in catalog but never seen by CORTEX
            try:
                from src.services.reflex_feedback import get_reflex_feedback as _get_fb
                _fb_digest = _get_fb()
                _fb_summary = _fb_digest.get_feedback_summary()
                _known_tools = set((_fb_summary.get("per_tool") or {}).keys())

                _catalog_path = Path(__file__).parent.parent.parent.parent / "data" / "reflex" / "tool_catalog.json"
                if _catalog_path.exists():
                    import json as _json_digest
                    _catalog = _json_digest.loads(_catalog_path.read_text())
                    _catalog_tools = [t["tool_id"] for t in _catalog.get("tools", [])]
                    _new_tools = [t for t in _catalog_tools if t not in _known_tools]
                    if _new_tools:
                        _digest["new_tools"] = _new_tools[:10]
            except Exception:
                pass  # New tools discovery is best-effort

            if _digest:
                context["digest"] = _digest
        except Exception:
            pass  # Digest never blocks session init

        # MARKER_198.P3.JEPA_LENS: JEPA-driven relevance ranking for session context
        # Replaces naive top-N with cosine-ranked items from ENGRAM + tasks + lessons.
        # Feature-flag: VETKA_SESSION_JEPA_LENS_ENABLE (default: true)
        # MARKER_199.JEPA_TTL: Cache JEPA lens results per role — embeddings for same
        # agent don't change within a session. Saves ~1-3s per init.
        try:
            import os as _os

            if _os.environ.get("VETKA_SESSION_JEPA_LENS_ENABLE", "1") != "0":
                import time as _time

                _jepa_start = _time.monotonic()
                _JEPA_TIMEOUT = 1.5  # seconds
                _JEPA_TTL = 300  # 5 min cache

                # Check TTL cache first (keyed by role callsign)
                _jepa_cache_key = f"jepa_lens_{_role.callsign if _role else 'unknown'}"
                if not hasattr(SessionInitTool, "_jepa_cache"):
                    SessionInitTool._jepa_cache = {}
                _cached = SessionInitTool._jepa_cache.get(_jepa_cache_key)
                if _cached and (_time.monotonic() - _cached.get("_ts", 0)) < _JEPA_TTL:
                    context["jepa_session_lens"] = _cached["data"]
                    context["jepa_session_lens"]["cached"] = True
                    raise _JepaCacheHit()  # skip to except

                from src.services.mcc_jepa_adapter import embed_texts_for_overlay

                # Build intent query from role + phase + top pending tasks
                _intent_parts = []
                if _role:
                    _intent_parts.append(f"role:{_role.callsign} domain:{_role.domain}")
                _phase_info = context.get("current_phase", {})
                if _phase_info:
                    _intent_parts.append(
                        f"phase:{_phase_info.get('number', '?')} {_phase_info.get('name', '')}"
                    )
                _tbs = context.get("tbs") or context.get("task_board_summary", {})
                _top_tasks = _tbs.get("top_pending", [])
                for _t in _top_tasks[:5]:
                    _intent_parts.append(_t.get("title", "")[:80])
                _intent = (
                    " | ".join(_intent_parts) if _intent_parts else "general session"
                )

                # Build corpus: ENGRAM entries + semantic lessons + top tasks
                _corpus = []
                _corpus_labels = []

                # ENGRAM dangers/architecture/patterns
                _el = context.get("engram_learnings") or context.get("el", {})
                for _cat in ("dangers", "architecture", "patterns"):
                    for _entry in _el.get(_cat) or []:
                        _val = _entry.get("value", "")
                        if _val:
                            _corpus.append(f"[{_cat}] {_val[:200]}")
                            _corpus_labels.append(
                                f"engram.{_cat}.{_entry.get('key', '?')[:40]}"
                            )

                # MARKER_198.P3.L2: Structured Qdrant L2 search (replaces string-split)
                try:
                    from src.orchestration.resource_learnings import get_learning_store

                    _l2_store = get_learning_store()
                    _l2_results = _l2_store.search_learnings_sync(
                        query=_intent,
                        limit=15,
                    )
                    for _lr in _l2_results:
                        _l2_text = _lr.get("text", "")
                        if _l2_text and len(_l2_text) > 10:
                            _l2_cat = _lr.get("category", "unknown")
                            _corpus.append(f"[{_l2_cat}] {_l2_text[:200]}")
                            _corpus_labels.append(f"qdrant_l2.{_l2_cat}")
                except Exception:
                    # Fallback to old string-split if Qdrant unavailable
                    _sl = context.get("semantic_lessons", "")
                    if isinstance(_sl, str) and _sl:
                        for _line in _sl.strip().split("\n"):
                            _line = _line.strip("- ").strip()
                            if _line and len(_line) > 10:
                                _corpus.append(_line[:200])
                                _corpus_labels.append("qdrant_l2")

                # Top pending tasks
                for _t in _top_tasks[:10]:
                    _title = _t.get("title", "")
                    if _title:
                        _corpus.append(f"[task] {_title[:120]}")
                        _corpus_labels.append(f"task.{_t.get('tid', '?')}")

                if _corpus and len(_corpus) >= 3:
                    # Embed intent + corpus together, intent is index 0
                    _all_texts = [_intent] + _corpus
                    _result = embed_texts_for_overlay(_all_texts, target_dim=128)

                    if _result.vectors and len(_result.vectors) == len(_all_texts):
                        _intent_vec = _result.vectors[0]
                        # Cosine rank corpus against intent
                        _scored = []
                        for _i, (_vec, _label, _text) in enumerate(
                            zip(_result.vectors[1:], _corpus_labels, _corpus)
                        ):
                            _dot = sum(
                                float(_intent_vec[j]) * float(_vec[j])
                                for j in range(len(_intent_vec))
                            )
                            _na = (
                                sum(
                                    float(_intent_vec[j]) ** 2
                                    for j in range(len(_intent_vec))
                                )
                                ** 0.5
                            )
                            _nb = (
                                sum(
                                    float(_vec[j]) ** 2 for j in range(len(_intent_vec))
                                )
                                ** 0.5
                            )
                            _sim = (
                                float(_dot / (_na * _nb))
                                if _na > 1e-12 and _nb > 1e-12
                                else 0.0
                            )
                            _scored.append(
                                {
                                    "label": _label,
                                    "text": _text[:120],
                                    "score": round(_sim, 4),
                                }
                            )

                        _scored.sort(key=lambda x: x["score"], reverse=True)
                        _elapsed = _time.monotonic() - _jepa_start

                        _lens_data = {
                            "intent": _intent[:200],
                            "top_items": _scored[:15],
                            "corpus_size": len(_corpus),
                            "provider_mode": _result.provider_mode,
                            "elapsed_ms": round(_elapsed * 1000),
                            "marker": "MARKER_198.P3.JEPA_LENS",
                        }
                        context["jepa_session_lens"] = _lens_data
                        # MARKER_199.JEPA_TTL: Save to cache
                        SessionInitTool._jepa_cache[_jepa_cache_key] = {
                            "data": _lens_data,
                            "_ts": _time.monotonic(),
                        }
        except _JepaCacheHit:
            pass  # Cache hit — context already populated
        except Exception:
            pass  # JEPA lens never blocks session init

        # MARKER_ZETA.F4.MGC: Inject MGC cache status into session_init
        try:
            from src.memory.mgc_cache import get_mgc_cache

            _mgc = get_mgc_cache()
            _mgc_stats = _mgc.get_stats()
            if _mgc_stats:
                context["mgc_status"] = {
                    "gen0_size": _mgc_stats.get("gen0_size", 0),
                    "hit_rate": _mgc_stats.get("hit_rate", 0),
                    "gen0_hit_rate": _mgc_stats.get("gen0_hit_rate", 0),
                    "total_hits": sum(
                        _mgc_stats.get(k, 0) for k in ("gen0", "gen1", "gen2")
                    ),
                    "misses": _mgc_stats.get("misses", 0),
                    "evictions": _mgc_stats.get("evictions", 0),
                }
        except Exception:
            pass  # MGC errors never block session init

        # MARKER_178.1.2: Recent commits
        try:
            import subprocess

            result = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                capture_output=True,
                text=True,
                timeout=3,
                cwd=str(Path(__file__).resolve().parent.parent.parent.parent),
            )
            if result.returncode == 0:
                context["recent_commits"] = result.stdout.strip().split("\n")[:5]
        except Exception:
            pass

        # MARKER_178.1.3: Capability manifest
        try:
            from src.mcp.tools.capability_broker import build_manifest

            manifest = build_manifest()
            context["capabilities"] = {
                "transports": [
                    {
                        "kind": t.kind.value,
                        "status": t.status.value,
                        "capabilities": t.capabilities,
                    }
                    for t in manifest.transports
                ],
                "recommended": manifest.recommended,
            }
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Capability manifest failed: {e}")

        # MARKER_198.P0.1: Load STM snapshot from disk so previous session's context
        # reaches REFLEX scoring.  Failures are silently ignored — session_init must
        # never be blocked by memory subsystem errors.
        _stm_items_for_reflex: list = []
        try:
            from src.memory.stm_buffer import get_stm_buffer

            _stm = get_stm_buffer()
            _stm.load_from_disk()
            _stm_items_for_reflex = [e.content for e in _stm.get_context(max_items=5)]
        except Exception:
            pass  # STM load errors never block session init

        # MARKER_172.P4.IP6 + MARKER_186.3 + MARKER_193.2: REFLEX session recommendations
        # Enhanced with agent_type inference for agent-aware scoring
        # MARKER_193.2: Now also injects reflex_warnings + blocked_tools from Guard
        try:
            from src.services.reflex_integration import reflex_session

            # MARKER_186.3: Infer agent_type from user_id or environment
            agent_type = context.get("_agent_type", "")
            if not agent_type:
                uid = context.get("user_id", "default")
                if "opus" in uid.lower() or "claude" in uid.lower():
                    agent_type = "claude_code"
                elif "cursor" in uid.lower():
                    agent_type = "cursor"
                elif "codex" in uid.lower():
                    agent_type = "codex"
                else:
                    # Default: assume Claude Code when called via MCP
                    agent_type = "claude_code"
            # MARKER_191.3: Extract current task for task-aware reflex scoring
            current_task = None
            tb = context.get("task_board_summary", {})
            in_prog = tb.get("in_progress", [])
            if in_prog:
                current_task = in_prog[0]
            elif tb.get("top_pending"):
                current_task = tb["top_pending"][0]
            reflex_recs = reflex_session(
                context,
                agent_type=agent_type,
                current_task=current_task,
                stm_items=_stm_items_for_reflex,  # MARKER_198.P0.1: disk-loaded STM
            )
            if reflex_recs:
                context["reflex_recommendations"] = reflex_recs
        except Exception:
            pass  # REFLEX errors never block session init

        # MARKER_193.2: Inject reflex_warnings and blocked_tools from Guard
        try:
            from src.services.reflex_guard import get_feedback_guard, GuardContext

            guard = get_feedback_guard()
            guard_ctx = GuardContext(
                agent_type=agent_type,
                phase_type=context.get("current_phase", {}).get("status", ""),
                project_id="",
            )
            active_dangers = guard.get_active_dangers(
                agent_type=agent_type,
                phase_type=guard_ctx.phase_type,
            )
            if active_dangers:
                context["reflex_warnings"] = [
                    {
                        "tool_pattern": d.tool_pattern,
                        "reason": d.reason,
                        "severity": d.severity,
                        "source": d.source,
                    }
                    for d in active_dangers
                ]
                context["blocked_tools"] = [
                    d.tool_pattern for d in active_dangers if d.severity == "block"
                ]
        except Exception:
            pass  # Guard errors never block session init

        # MARKER_187.7: Inject per-agent focus after agent_type is resolved
        if agent_type and context.get("_all_agent_focus"):
            my_focus = context["_all_agent_focus"].get(agent_type)
            if my_focus:
                context["my_focus"] = my_focus

        # MARKER_194.1: Claimed tasks overlay — show other agents' active work
        try:
            from src.orchestration.task_board import get_task_board

            _board = get_task_board()
            claimed_tasks = _board.get_queue(status="claimed")
            other_agents_work = []
            for t in claimed_tasks:
                t_agent_type = t.get("agent_type", "")
                # Skip current agent's own tasks
                if t_agent_type == agent_type:
                    continue
                other_agents_work.append(
                    {
                        "agent": t.get("assigned_to", t_agent_type or "unknown"),
                        "task_id": t.get("task_id", t.get("id", "?")),
                        "title": t.get("title", "")[:60],
                        "allowed_paths": t.get("allowed_paths", []),
                        "claimed_at": t.get("assigned_at", ""),
                    }
                )
            if other_agents_work:
                context["other_agents"] = other_agents_work
        except Exception:
            pass  # Never break session_init

        # MARKER_194.2: Conflict radar REMOVED (MARKER_193.8)
        # Was dumping full git log --name-only → 3.5MB in session_init response.
        # project_digest.agent_focus.hot_files already covers this info compactly.

        # MARKER_178.4.12: REFLEX report — last match_rates + feedback summary
        try:
            from src.services.reflex_feedback import ReflexFeedback

            fb = ReflexFeedback()
            summary = fb.get_feedback_summary()
            if summary and summary.get("total_entries", 0) > 0:
                context["reflex_report"] = {
                    "total_entries": summary["total_entries"],
                    "success_rate": summary.get("success_rate", 0),
                    "useful_rate": summary.get("useful_rate", 0),
                    "verified_rate": summary.get("verified_rate", 0),
                    "top_tools": list(summary.get("per_tool", {}).keys())[:5],
                }
        except Exception:
            pass  # REFLEX report never blocks session init

        # MARKER_195.6.INIT: Tool Freshness Watchdog — auto-scan for code changes
        try:
            from src.services.tool_source_watch import get_tool_source_watch

            watch = get_tool_source_watch()
            freshness_events = watch.scan_all()
            if freshness_events:
                context["freshness_events"] = [e.to_dict() for e in freshness_events]
                # Also enrich reflex_report with freshness info
                report = context.get("reflex_report", {})
                report["freshened_tools"] = [e.tool_id for e in freshness_events]
                context["reflex_report"] = report
            # Always report recently-updated tools (from previous sessions too)
            recently_updated = watch.get_recently_updated()
            if recently_updated:
                report = context.get("reflex_report", {})
                report["recently_updated_tools"] = recently_updated
                context["reflex_report"] = report
        except Exception:
            pass  # Freshness never blocks session init

        # MARKER_195.2.4: REFLEX Emotions — agent mood + per-tool emotions
        try:
            from src.services.reflex_emotions import get_reflex_emotions, EmotionContext

            emo_engine = get_reflex_emotions()
            # Gather per-tool emotions for tools already in reflex_recommendations
            recs = context.get("reflex_recommendations", [])
            tool_emotions: Dict[str, Dict[str, float]] = {}
            for rec in recs[
                :3
            ]:  # MARKER_197.SLIM: Limit to top 3 tools (matches reflex top_n=3)
                tid = rec.get("tool_id", "") if isinstance(rec, dict) else ""
                if not tid:
                    continue
                breakdown = emo_engine.get_modifier_breakdown(tid)
                tool_emotions[tid] = {
                    "curiosity": breakdown["curiosity"],
                    "trust": breakdown["trust"],
                    "caution": breakdown["caution"],
                    "modifier": breakdown["modifier"],
                }
            if tool_emotions:
                mood = _compute_mood_label(tool_emotions)
                summary = _generate_emotion_summary(tool_emotions)
                context["reflex_emotions"] = {
                    "agent_mood": mood,
                    "tool_emotions": tool_emotions,
                    "emotion_summary": summary,
                }
        except Exception:
            pass  # Emotion errors never block session init

        # MARKER_195.5: Protocol status in session_init
        try:
            from src.services.session_tracker import get_session_tracker

            _pt_tracker = get_session_tracker()
            _pt_sid = context.get("session_id", "default")
            _pt_tracker.record_action(_pt_sid, "vetka_session_init", {})
            _pt_session = _pt_tracker.get_session(_pt_sid)
            context["protocol_status"] = {
                "session_init": True,
                "task_board_checked": _pt_session.task_board_checked,
                "task_claimed": _pt_session.task_claimed,
                "claimed_task_id": _pt_session.claimed_task_id,
                "files_read": len(_pt_session.files_read),
                "files_edited": len(_pt_session.files_edited),
                "protocol_checklist": [
                    {"step": "session_init", "done": True},
                    {
                        "step": "task_board_check",
                        "done": _pt_session.task_board_checked,
                    },
                    {"step": "claim_task", "done": _pt_session.task_claimed},
                ],
            }
        except Exception:
            pass  # Protocol status never blocks session init

        # MARKER_ZETA.INT + MARKER_196.1.3: Role context from Agent Registry
        # Priority: explicit role= param > branch detection fallback
        try:
            from src.services.agent_registry import get_agent_registry
            import subprocess as _sp

            _reg = get_agent_registry()
            _role = None
            _role_source = None  # "explicit" or "branch_detection"

            # MARKER_196.1.3: Explicit role= parameter (preferred path)
            if role_name:
                _role = _reg.get_by_callsign(role_name)
                if _role:
                    _role_source = "explicit"
                else:
                    # Invalid role name — return error with available roles
                    context["role_error"] = {
                        "message": f"Unknown role: '{role_name}'",
                        "available_roles": _reg.list_callsigns(),
                    }

            # Fallback: branch detection (backward-compatible, no role= provided)
            if not _role and not role_name:
                import os

                _detect_cwd = os.environ.get("VETKA_MCP_CWD") or os.getcwd()
                _branch_result = _sp.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    cwd=_detect_cwd,
                )
                _current_branch = (
                    _branch_result.stdout.strip()
                    if _branch_result.returncode == 0
                    else ""
                )

                if _current_branch == "main" or not _current_branch:
                    _toplevel = _sp.run(
                        ["git", "rev-parse", "--show-toplevel"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        cwd=_detect_cwd,
                    )
                    _toplevel_path = (
                        _toplevel.stdout.strip() if _toplevel.returncode == 0 else ""
                    )
                    if _toplevel_path and "worktrees" in _toplevel_path:
                        _wt_name = Path(_toplevel_path).name
                        for _r in _reg.roles:
                            if _r.worktree == _wt_name:
                                _current_branch = _r.branch
                                break

                _role = _reg.get_by_branch(_current_branch) if _current_branch else None
                if _role:
                    _role_source = "branch_detection"

            # Always expose available roles for discoverability
            if not _role:
                context["available_roles"] = _reg.list_callsigns()

            if _role:
                _role_ctx = {
                    "callsign": _role.callsign,
                    "domain": _role.domain,
                    "pipeline_stage": _role.pipeline_stage,  # MARKER_196.1.3
                    "role_title": _role.role_title,
                    "branch": _role.branch,
                    "worktree": _role.worktree,
                    "owned_paths": list(_role.owned_paths),
                    "blocked_paths": list(_role.blocked_paths),
                    "role_source": _role_source,  # "explicit" or "branch_detection"
                }

                # Workflow hints based on domain
                if _role.domain == "architect":
                    _role_ctx["workflow_hints"] = [
                        "Create CUT tasks with role= and domain= fields (see agent_registry.yaml)",
                        "Workflow patterns: Solo / G3 / Ralph Loop / Mycelium Pipeline / Commander Fleet / Sous-Chef",
                        "Merge ritual: pre-check → merge → vite build → promote_to_main",
                        "Wave-based: 1-2 tasks per agent per wave, merge between waves",
                    ]
                elif _role.domain == "qa":
                    _role_ctx["workflow_hints"] = [
                        "Run tests: node node_modules/@playwright/test/cli.js test (NOT npx playwright)",
                        "3-tier strategy: DOM-only / store-based / backend-integrated",
                        "data-testid convention: cut-editor-layout, cut-timeline-track-view, cut-timeline-clip-{id}",
                    ]
                else:
                    _role_ctx["workflow_hints"] = [
                        f"You own {_role.domain} domain — only touch files in owned_paths",
                        f"Always pass branch={_role.branch} to task_board action=complete",
                        "Write experience report before session end",
                    ]

                # Shared zones relevant to this role
                _shared = [
                    {"file": z.file, "owners": z.owners, "protocol": z.protocol}
                    for z in _reg.shared_zones
                    if _role.callsign in z.owners
                ]
                if _shared:
                    _role_ctx["shared_zones"] = _shared

                context["role_context"] = _role_ctx

                # MARKER_196.2.1: Bind role to session for auto-attribution
                try:
                    from src.services.session_tracker import get_session_tracker

                    _role_tracker = get_session_tracker()
                    _role_tracker.set_role(context.get("session_id", "default"), _role)
                except Exception:
                    pass  # Role binding never blocks session init

                # MARKER_ZETA.F4.PREDECESSOR: Removed — _get_predecessor_advice
                # was deleted in ZETA-SLIM3. Predecessor context now comes from
                # semantic_lessons (Qdrant L2) and ENGRAM patterns above.

                # MARKER_195.22 + MARKER_196.2.3: Auto-regenerate CLAUDE.md by role callsign.
                # Triggered by role (explicit or branch-detected), not by git branch.
                # Writes to both worktree and ~/.claude/projects/ (dual-write).
                try:
                    from src.tools.generate_claude_md import write_claude_md

                    write_claude_md(_role.callsign, registry=_reg)
                    logger.debug(
                        f"[SessionInit] Auto-regenerated CLAUDE.md for {_role.callsign}"
                    )
                except Exception as _gen_err:
                    logger.debug(
                        f"[SessionInit] CLAUDE.md regen failed (non-fatal): {_gen_err}"
                    )

        except Exception:
            pass  # Role context never blocks session init

        # MARKER_178.1.4: Build actionable next_steps from context
        try:
            next_steps = []

            # From tasks
            tb = context.get("task_board_summary", {})
            if tb.get("pending_count", 0) > 0:
                # MARKER_178.5.2: Reference both task board tools (primary + fallback)
                next_steps.append(
                    f"{tb['pending_count']} pending tasks -> mycelium_task_board action=list (or vetka_task_board as fallback)"
                )
            if tb.get("in_progress_count", 0) > 0:
                items = ", ".join(
                    t["title"][:30] for t in tb.get("in_progress", [])[:2]
                )
                next_steps.append(f"In progress: {items}")
            # MARKER_186.4: Warn about tasks awaiting merge
            if tb.get("done_worktree_count", 0) > 0:
                next_steps.append(
                    f"⚠️ {tb['done_worktree_count']} tasks done on worktree branches, awaiting merge → vetka_task_board action=merge_request"
                )
            if tb.get("need_qa_count", 0) > 0:
                next_steps.append(
                    f"🔍 {tb['need_qa_count']} tasks awaiting QA → vetka_task_board action=verify"
                )
            if tb.get("needs_fix_count", 0) > 0:
                next_steps.append(
                    f"⚠️ {tb['needs_fix_count']} tasks failed QA, need fix"
                )

            # MARKER_199.DEBRIEF: Warn about tasks closed without debrief
            try:
                skipped = board.get_debrief_skipped_tasks(limit=5)
                if skipped:
                    agents = set(s.get("assigned_to", "?") for s in skipped)
                    next_steps.append(
                        f"DEBRIEF SKIPPED: {len(skipped)} tasks auto-closed without Q1-Q3 debrief "
                        f"(agents: {', '.join(agents)}). Use action=debrief_skipped to see list."
                    )
            except Exception:
                pass

            # From REFLEX
            recs = context.get("reflex_recommendations", [])
            if recs:
                top = recs[0] if isinstance(recs[0], dict) else {}
                tool_name = top.get("tool_id", "")
                reason = top.get("reason", "")
                if tool_name:
                    next_steps.append(f"REFLEX suggests: {tool_name} ({reason})")

            # From commits staleness
            commits = context.get("recent_commits", [])
            if not commits:
                next_steps.append("No recent commits found — check git status")

            if next_steps:
                context["next_steps"] = next_steps
        except Exception:
            pass

        # MARKER_197.SLIM: Remove non-essential sections for coding agents
        # These belong to JARVIS/VETKA personal assistant, not coding tools
        for _slim_key in [
            "reflex_emotions",  # JARVIS emotion layer, not for coders
            "_all_agent_focus",  # debug only
            "mgc_status",  # internal cache diagnostics
            "compression",  # metadata about itself, circular
            "recent_states_count",  # MCP state meta
            "recent_state_ids",  # MCP state meta
            "recent_commits",  # already in gitStatus system-reminder
            "viewport_summary",  # 3D viewport, not for coding
            "viewport",  # 3D viewport, not for coding
            "viewport_patterns",  # 3D viewport preferences
            "communication_style",  # AURA personal assistant layer
        ]:
            context.pop(_slim_key, None)

        # MARKER_198.P0.5: Apply ELISION L2 compression to session_init response
        try:
            from src.memory.elision import get_elision_compressor

            compressor = get_elision_compressor()
            # Compress the context dict — replaces verbose keys with short abbreviations
            context_str = _json.dumps(context, default=str)
            compressed = compressor.compress(context_str, level=2)
            if compressed and compressed.compressed:
                # Parse back to dict for MCP response
                compressed_context = _json.loads(compressed.compressed)
                legend = compressed.legend
                compressed_context["_elision"] = {
                    "level": 2,
                    "ratio": compressed.compression_ratio,
                    "legend": dict(list(legend.items())[:10]) if legend else {},
                }
                context = compressed_context
        except Exception:
            pass  # Compression is best-effort, never blocks session_init

        # MARKER_198.P0.1: Persist STM snapshot so the next session can restore it.
        # Called here (end of session_init) to capture any entries added during
        # the current init flow before returning to the caller.
        try:
            from src.memory.stm_buffer import get_stm_buffer

            get_stm_buffer().save_to_disk()
        except Exception:
            pass  # STM save errors never block session init

        # MARKER_198.MEM_HEALTH: Memory subsystem health dashboard
        try:
            memory_health = {}

            # AURA
            try:
                from src.memory.aura_store import get_aura_store

                aura = get_aura_store()
                aura_entries = (
                    len(aura._preferences) if hasattr(aura, "_preferences") else 0
                )
                memory_health["aura"] = {
                    "entries": aura_entries,
                    "status": "ok" if aura_entries > 0 else "cold",
                }
            except Exception:
                memory_health["aura"] = {"status": "error"}

            # ENGRAM L1
            try:
                from src.memory.engram_cache import get_engram_cache

                engram = get_engram_cache()
                all_entries = engram.get_all()
                danger_count = len(engram.get_danger_entries())
                memory_health["engram_l1"] = {
                    "entries": len(all_entries),
                    "danger": danger_count,
                    "status": "ok" if len(all_entries) > 0 else "cold",
                }
            except Exception:
                memory_health["engram_l1"] = {"status": "error"}

            # CORTEX / REFLEX
            try:
                from src.services.reflex_feedback import get_reflex_feedback

                fb = get_reflex_feedback()
                summary = fb.get_feedback_summary()
                memory_health["cortex"] = {
                    "entries": summary.get("total_entries", 0),
                    "success_rate": round(summary.get("success_rate", 0), 3),
                    "status": "ok" if summary.get("total_entries", 0) > 10 else "cold",
                }
            except Exception:
                memory_health["cortex"] = {"status": "error"}

            # STM
            try:
                from src.memory.stm_buffer import get_stm_buffer

                stm = get_stm_buffer()
                stm_count = len(stm.items) if hasattr(stm, "items") else 0
                memory_health["stm"] = {
                    "items": stm_count,
                    "status": "ok" if stm_count > 0 else "cold",
                }
            except Exception:
                memory_health["stm"] = {"status": "error"}

            # Resource Learnings (Qdrant L2)
            try:
                from src.orchestration.resource_learnings import get_learning_store

                store = get_learning_store()
                stats = store.get_stats()
                memory_health["qdrant_l2"] = {
                    "source": stats.get("source", "unknown"),
                    "count": stats.get("count", 0),
                    "status": "ok" if stats.get("count", 0) > 0 else "cold",
                }
            except Exception:
                memory_health["qdrant_l2"] = {"status": "error"}

            # Bridge hooks
            try:
                from src.mcp.bridge_hooks import get_hook_stats

                hooks = get_hook_stats()
                memory_health["bridge_hooks"] = {
                    "pre": hooks.get("pre_hooks", 0),
                    "post": hooks.get("post_hooks", 0),
                    "status": "ok"
                    if hooks.get("post_hooks", 0) > 0
                    else "not_registered",
                }
            except Exception:
                memory_health["bridge_hooks"] = {"status": "error"}

            context["memory_health"] = memory_health
        except Exception:
            pass  # Memory health never blocks session_init

        return {"success": True, "result": context}

    async def _get_viewport_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        MARKER_109_1_VIEWPORT_INJECT: Get viewport context from various sources.

        Tries in order:
        1. MCP state manager (if client synced viewport)
        2. CAM engine viewport patterns
        3. Default empty context
        """
        try:
            # Try MCP state first (client may have synced viewport)
            from src.mcp.state import get_mcp_state_manager

            mcp = get_mcp_state_manager()
            state = await mcp.get_state(session_id)
            if state and "viewport" in state:
                return state["viewport"]

            # Try CAM engine viewport patterns
            try:
                from src.orchestration.cam_engine import get_cam_engine

                cam = get_cam_engine()
                if hasattr(cam, "get_viewport_state"):
                    return cam.get_viewport_state()
            except Exception:
                pass

            # Return minimal context if nothing available
            return {
                "zoom_level": 1,
                "viewport_nodes": [],
                "pinned_nodes": [],
                "camera_position": {"x": 0, "y": 0, "z": 100},
            }
        except Exception as e:
            print(f"[SessionInit] Viewport context error: {e}")
            return None

    async def _get_pinned_files(self, session_id: str, chat_id: Optional[str]) -> list:
        """
        MARKER_109_1_VIEWPORT_INJECT: Get pinned files from chat history or CAM.

        Sources:
        1. Chat history manager (if chat_id provided)
        2. CAM pinned nodes
        3. MCP state (if client synced pins)
        """
        pinned = []

        try:
            # Try chat history manager first
            if chat_id:
                from src.chat.chat_history_manager import get_chat_history_manager

                chat_mgr = get_chat_history_manager()
                if hasattr(chat_mgr, "get_pinned_files"):
                    chat_pinned = chat_mgr.get_pinned_files(chat_id)
                    if chat_pinned:
                        pinned.extend(chat_pinned)

            # Try CAM pinned nodes
            try:
                from src.orchestration.cam_engine import get_cam_engine

                cam = get_cam_engine()
                if hasattr(cam, "get_pinned_nodes"):
                    cam_pinned = cam.get_pinned_nodes()
                    for node in cam_pinned:
                        if isinstance(node, dict):
                            pinned.append(node)
                        else:
                            pinned.append(
                                {"path": str(node), "name": str(node).split("/")[-1]}
                            )
            except Exception:
                pass

            # Try MCP state
            if not pinned:
                from src.mcp.state import get_mcp_state_manager

                mcp = get_mcp_state_manager()
                state = await mcp.get_state(session_id)
                if state and "pinned_files" in state:
                    pinned.extend(state["pinned_files"])

        except Exception as e:
            print(f"[SessionInit] Pinned files error: {e}")

        return pinned


class SessionStatusTool(BaseMCPTool):
    """Get current MCP session status."""

    @property
    def name(self) -> str:
        return "vetka_session_status"

    @property
    def description(self) -> str:
        return (
            "Get current MCP session status. "
            "Returns session data, expiration time, and recent activity. "
            "Use to check if session is still valid or needs refresh."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID to check status for",
                }
            },
            "required": ["session_id"],
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute synchronously by running async in event loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Return sync-compatible result
                return {
                    "success": True,
                    "result": {
                        "status": "checking",
                        "session_id": arguments.get("session_id"),
                        "message": "Status check initiated",
                    },
                }
            else:
                return loop.run_until_complete(self._execute_async(arguments))
        except RuntimeError:
            return asyncio.run(self._execute_async(arguments))

    async def _execute_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async implementation of session status check."""
        session_id = arguments.get("session_id")

        if not session_id:
            return {"success": False, "error": "session_id is required"}

        try:
            from src.mcp.state import get_mcp_state_manager

            mcp = get_mcp_state_manager()
            state = await mcp.get_state(session_id)

            if state:
                return {
                    "success": True,
                    "result": {
                        "exists": True,
                        "session_id": session_id,
                        "session": state,
                        "age_seconds": time.time()
                        - state.get("initialized_at", time.time()),
                    },
                }
            else:
                return {
                    "success": True,
                    "result": {
                        "exists": False,
                        "session_id": session_id,
                        "message": "Session not found or expired",
                    },
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Convenience functions for direct import
async def vetka_session_init(
    user_id: str = "default",
    group_id: Optional[str] = None,
    chat_id: Optional[str] = None,  # MARKER_108_1: Chat ID parameter
    include_viewport: bool = True,
    include_pinned: bool = True,
    compress: bool = True,
    max_context_tokens: int = 4000,
    role: str = None,  # MARKER_198.P0.7: Accept explicit role parameter (avoids failed first call)
) -> Dict[str, Any]:
    """
    Initialize MCP session with fat context.

    Convenience wrapper for SessionInitTool.

    MARKER_108_1: Phase 108.1 - Unified MCP-Chat ID
    If chat_id provided, links session to existing VETKA chat.
    If not, creates new chat and returns its ID as session_id.

    MARKER_198.P0.7: Accept explicit role= parameter so agents can call
    vetka_session_init(role="Zeta") without an unexpected keyword argument crash.
    Role lookup via agent_registry happens inside _execute_async; branch detection
    is the fallback when role is not provided.
    """
    tool = SessionInitTool()
    return await tool._execute_async(
        {
            "user_id": user_id,
            "group_id": group_id,
            "chat_id": chat_id,  # MARKER_108_1: Pass chat_id
            "include_viewport": include_viewport,
            "include_pinned": include_pinned,
            "compress": compress,
            "max_context_tokens": max_context_tokens,
            "role": role,  # MARKER_198.P0.7: Forward role to SessionInitTool._execute_async
        }
    )


async def vetka_session_status(session_id: str) -> Dict[str, Any]:
    """
    Get current session status.

    Convenience wrapper for SessionStatusTool.
    """
    tool = SessionStatusTool()
    return await tool._execute_async({"session_id": session_id})


def register_session_tools(tool_list: list):
    """
    Register session tools with a tool registry list.

    Args:
        tool_list: List to append tool instances to
    """
    tool_list.extend([SessionInitTool(), SessionStatusTool()])
