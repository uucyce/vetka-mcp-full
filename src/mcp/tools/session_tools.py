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
            with open(DIGEST_PATH, 'r') as f:
                digest = _json.load(f)

            # Return condensed version for MCP context
            # MARKER_187.7: Include full agent_focus for per-agent filtering downstream
            return {
                "phase": digest.get("current_phase", {}),
                "summary": digest.get("summary", {}).get("headline", ""),
                "achievements": digest.get("summary", {}).get("key_achievements", [])[:5],
                "pending": digest.get("summary", {}).get("pending_items", [])[:3],
                "system": digest.get("system_status", {}),
                "instructions": digest.get("agent_instructions", {}),
                "last_updated": digest.get("last_updated"),
                "recent_fixes": [f.get("id") for f in digest.get("recent_fixes", [])[:5]],
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
    high_curiosity = [t for t, e in tool_emotions.items() if e.get("curiosity", 0) > 0.7]
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
                    "default": "default"
                },
                "group_id": {
                    "type": "string",
                    "description": "Group chat ID if in group context (optional)"
                },
                "chat_id": {
                    "type": "string",
                    "description": "Chat ID to link session with existing chat (optional, Phase 108.1)"
                },
                "include_viewport": {
                    "type": "boolean",
                    "description": "Include 3D viewport context if available",
                    "default": True
                },
                "include_pinned": {
                    "type": "boolean",
                    "description": "Include pinned files context",
                    "default": True
                },
                "compress": {
                    "type": "boolean",
                    "description": "Apply ELISION compression to context",
                    "default": True
                },
                "max_context_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens for context (default: 4000)",
                    "default": 4000
                }
            },
            "required": []
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
                        "message": "Session initialization started asynchronously"
                    }
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
        user_id = arguments.get("user_id") or os.environ.get("VETKA_USER_ID") or "danila"
        group_id = arguments.get("group_id")
        chat_id = arguments.get("chat_id")  # MARKER_108_1: Unified MCP-Chat ID
        include_viewport = arguments.get("include_viewport", True)
        include_pinned = arguments.get("include_pinned", True)
        compress = arguments.get("compress", True)
        max_context_tokens = arguments.get("max_context_tokens", 4000)

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
                    display_name=f"MCP {user_id[:8]}"
                )
                session_id = new_chat_id
                chat_id = new_chat_id
                linked_to_existing = False
            except Exception as e:
                # Fallback to old session_id format if chat creation fails
                session_id = f"session_{user_id}_{group_id or 'solo'}_{int(time.time())}"
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

        # MARKER_191.5: Get user preferences from AURA with auto-bootstrap
        try:
            from src.memory.aura_store import get_aura_store
            from src.memory.user_memory import create_user_preferences
            aura = get_aura_store()
            prefs = aura.get_user_preferences(user_id)
            if not prefs:
                # Auto-bootstrap: create default profile for new user
                prefs = create_user_preferences(user_id)
                aura.set_preference(
                    agent_type="default", user_id=user_id,
                    category="communication_style", key="preferred_language",
                    value="ru"
                )
                prefs = aura.get_user_preferences(user_id)
                logger.info(f"[session_init] Auto-bootstrapped AURA profile for user_id={user_id}")
            # Convert UserPreferences dataclass to dict safely
            context["user_preferences"] = {
                "user_id": prefs.user_id,
                "has_preferences": True
            }
            # Add key preference categories if available
            if hasattr(prefs, 'communication_style'):
                context["communication_style"] = getattr(prefs.communication_style, '__dict__', {})
            if hasattr(prefs, 'viewport_patterns'):
                context["viewport_patterns"] = getattr(prefs.viewport_patterns, '__dict__', {})
        except Exception as e:
            context["user_preferences"] = {"user_id": user_id, "has_preferences": False}
            context["user_preferences_error"] = str(e)

        # Get recent MCP states
        try:
            from src.mcp.state import get_mcp_state_manager
            mcp = get_mcp_state_manager()
            recent = await mcp.get_all_states(limit=10)
            context["recent_states_count"] = len(recent)
            context["recent_state_ids"] = list(recent.keys())[:5]
        except Exception as e:
            context["recent_states_error"] = str(e)

        # MARKER_109_1_VIEWPORT_INJECT: Build viewport context if requested
        if include_viewport:
            try:
                # Try to get viewport data from CAM engine or state
                viewport_context = await self._get_viewport_context(session_id)
                if viewport_context:
                    from src.api.handlers.message_utils import build_viewport_summary
                    viewport_summary = build_viewport_summary(viewport_context)
                    if viewport_summary:
                        context["viewport_summary"] = viewport_summary
                        context["viewport"] = {
                            "zoom": viewport_context.get("zoom_level", 1),
                            "visible_count": len(viewport_context.get("viewport_nodes", [])),
                            "pinned_count": len(viewport_context.get("pinned_nodes", [])),
                            "hyperlink": "[→ viewport] vetka_get_viewport_detail"
                        }
            except Exception as e:
                context["viewport_error"] = str(e)

        # MARKER_109_1_VIEWPORT_INJECT: Build pinned files context if requested
        if include_pinned:
            try:
                pinned_files = await self._get_pinned_files(session_id, chat_id)
                if pinned_files:
                    from src.api.handlers.message_utils import build_pinned_context
                    pinned_context = build_pinned_context(pinned_files, max_files=5)
                    if pinned_context:
                        context["pinned_context"] = pinned_context
                        context["pinned"] = {
                            "count": len(pinned_files),
                            "files": [pf.get("name", pf.get("path", "")) for pf in pinned_files[:5]],
                            "hyperlink": "[→ pins] vetka_get_pinned_files"
                        }
            except Exception as e:
                context["pinned_error"] = str(e)

        # Apply ELISION compression if requested
        if compress:
            try:
                from src.memory.jarvis_prompt_enricher import JARVISPromptEnricher
                enricher = JARVISPromptEnricher()
                original_size = len(str(context))
                compressed_str = enricher.compress_context(context)
                compressed_size = len(compressed_str)
                context["compression"] = {
                    "enabled": True,
                    "original_size": original_size,
                    "compressed_size": compressed_size,
                    "ratio": round(original_size / max(compressed_size, 1), 2)
                }
            except Exception as e:
                context["compression"] = {"enabled": False, "error": str(e)}

        # Save session state for later retrieval
        try:
            from src.mcp.state import get_mcp_state_manager
            mcp = get_mcp_state_manager()
            await mcp.save_state(session_id, context, ttl_seconds=3600)
            context["persisted"] = True
        except Exception as e:
            context["persisted"] = False
            context["persist_error"] = str(e)

        # MARKER_178.1.1: Load active tasks from TaskBoard
        try:
            from src.orchestration.task_board import TaskBoard, TASK_BOARD_FILE
            board = TaskBoard(TASK_BOARD_FILE)
            # MARKER_181.5.6: Fixed list_tasks() → get_queue() (method was renamed)
            pending = board.get_queue(status="pending")
            in_progress = board.get_queue(status="in_progress")
            # MARKER_186.4: Count tasks awaiting merge (done_worktree)
            done_worktree = board.get_queue(status="done_worktree")
            context["task_board_summary"] = {
                "pending_count": len(pending),
                "in_progress_count": len(in_progress),
                "done_worktree_count": len(done_worktree),
                "top_pending": [{"task_id": t.get("task_id", "?"), "title": t.get("title", "")[:60], "priority": t.get("priority", 5)} for t in pending[:5]],
                "in_progress": [{"task_id": t.get("task_id", "?"), "title": t.get("title", "")[:60], "assigned_to": t.get("assigned_to", "")} for t in in_progress[:5]],
                "awaiting_merge": [{"task_id": t.get("task_id", "?"), "title": t.get("title", "")[:60], "assigned_to": t.get("assigned_to", "")} for t in done_worktree[:5]]
            }
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"TaskBoard load failed: {e}")

        # MARKER_187.2: semantic_recall — inject past learnings from Qdrant
        try:
            from src.orchestration.resource_learnings import get_learnings_for_architect
            # Build query from digest + top pending task
            tb = context.get("task_board_summary", {})
            digest_summary = context.get("project_digest", {}).get("summary", "")
            top_task = (tb.get("top_pending") or [{}])[0].get("title", "") if tb.get("top_pending") else ""
            in_prog = (tb.get("in_progress") or [{}])[0].get("title", "") if tb.get("in_progress") else ""
            query_parts = [p for p in [digest_summary, top_task, in_prog] if p]
            if query_parts:
                recall_query = " | ".join(query_parts)
                lessons = await get_learnings_for_architect(recall_query, limit=5)
                if lessons:
                    context["semantic_lessons"] = lessons
        except Exception:
            pass  # Qdrant unavailable — graceful fallback, no block

        # MARKER_178.1.2: Recent commits
        try:
            import subprocess
            result = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                capture_output=True, text=True, timeout=3,
                cwd=str(Path(__file__).resolve().parent.parent.parent.parent)
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
                    {"kind": t.kind.value, "status": t.status.value, "capabilities": t.capabilities}
                    for t in manifest.transports
                ],
                "recommended": manifest.recommended
            }
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Capability manifest failed: {e}")

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
            reflex_recs = reflex_session(context, agent_type=agent_type, current_task=current_task)
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
                    {"tool_pattern": d.tool_pattern, "reason": d.reason,
                     "severity": d.severity, "source": d.source}
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
            from src.orchestration.task_board import TaskBoard, TASK_BOARD_FILE
            _board = TaskBoard(TASK_BOARD_FILE)
            claimed_tasks = _board.get_queue(status="claimed")
            other_agents_work = []
            for t in claimed_tasks:
                t_agent_type = t.get("agent_type", "")
                # Skip current agent's own tasks
                if t_agent_type == agent_type:
                    continue
                other_agents_work.append({
                    "agent": t.get("assigned_to", t_agent_type or "unknown"),
                    "task_id": t.get("task_id", t.get("id", "?")),
                    "title": t.get("title", "")[:60],
                    "allowed_paths": t.get("allowed_paths", []),
                    "claimed_at": t.get("assigned_at", ""),
                })
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
            for rec in recs[:10]:  # Limit to top 10 tools
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
                    {"step": "task_board_check", "done": _pt_session.task_board_checked},
                    {"step": "claim_task", "done": _pt_session.task_claimed},
                ],
            }
        except Exception:
            pass  # Protocol status never blocks session init

        # MARKER_ZETA.INT: Role context from Agent Registry
        try:
            from src.services.agent_registry import get_agent_registry
            import subprocess as _sp

            _reg = get_agent_registry()

            # MARKER_195.22: Detect branch from WORKTREE, not main repo.
            # MCP subprocess is launched from worktree cwd by Claude Code.
            # Try multiple detection strategies:
            # 1. git branch from initial cwd (worktree) via VETKA_MCP_CWD env
            # 2. git branch from current os.getcwd()
            # 3. Fallback: git branch from main repo (returns "main")
            import os
            _detect_cwd = os.environ.get("VETKA_MCP_CWD") or os.getcwd()
            _branch_result = _sp.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, timeout=5,
                cwd=_detect_cwd,
            )
            _current_branch = _branch_result.stdout.strip() if _branch_result.returncode == 0 else ""

            # If cwd detection returned main, try worktree detection via git-dir
            if _current_branch == "main" or not _current_branch:
                # Check if cwd is inside a worktree
                _toplevel = _sp.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    capture_output=True, text=True, timeout=5,
                    cwd=_detect_cwd,
                )
                _toplevel_path = _toplevel.stdout.strip() if _toplevel.returncode == 0 else ""
                if _toplevel_path and "worktrees" in _toplevel_path:
                    # Extract worktree name → look up branch in registry
                    _wt_name = Path(_toplevel_path).name
                    for _r in _reg.roles:
                        if _r.worktree == _wt_name:
                            _current_branch = _r.branch
                            break

            _role = _reg.get_by_branch(_current_branch) if _current_branch else None

            if _role:
                _role_ctx = {
                    "callsign": _role.callsign,
                    "domain": _role.domain,
                    "role_title": _role.role_title,
                    "branch": _role.branch,
                    "worktree": _role.worktree,
                    "owned_paths": list(_role.owned_paths),
                    "blocked_paths": list(_role.blocked_paths),
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

                # MARKER_195.22: Auto-regenerate CLAUDE.md for this role on every session_init.
                # Prevents stale files from merge overwrites — the #1 recurring bug (5 days running).
                # Writes to both worktree and ~/.claude/projects/ (dual-write).
                try:
                    from src.tools.generate_claude_md import write_claude_md
                    write_claude_md(_role.callsign, registry=_reg)
                    logger.debug(f"[SessionInit] Auto-regenerated CLAUDE.md for {_role.callsign}")
                except Exception as _gen_err:
                    logger.debug(f"[SessionInit] CLAUDE.md regen failed (non-fatal): {_gen_err}")

        except Exception:
            pass  # Role context never blocks session init

        # MARKER_178.1.4: Build actionable next_steps from context
        try:
            next_steps = []

            # From tasks
            tb = context.get("task_board_summary", {})
            if tb.get("pending_count", 0) > 0:
                # MARKER_178.5.2: Reference both task board tools (primary + fallback)
                next_steps.append(f"{tb['pending_count']} pending tasks -> mycelium_task_board action=list (or vetka_task_board as fallback)")
            if tb.get("in_progress_count", 0) > 0:
                items = ", ".join(t["title"][:30] for t in tb.get("in_progress", [])[:2])
                next_steps.append(f"In progress: {items}")
            # MARKER_186.4: Warn about tasks awaiting merge
            if tb.get("done_worktree_count", 0) > 0:
                next_steps.append(f"⚠️ {tb['done_worktree_count']} tasks done on worktree branches, awaiting merge → vetka_task_board action=merge_request")

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

        return {
            "success": True,
            "result": context
        }

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
                if hasattr(cam, 'get_viewport_state'):
                    return cam.get_viewport_state()
            except Exception:
                pass

            # Return minimal context if nothing available
            return {
                "zoom_level": 1,
                "viewport_nodes": [],
                "pinned_nodes": [],
                "camera_position": {"x": 0, "y": 0, "z": 100}
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
                if hasattr(chat_mgr, 'get_pinned_files'):
                    chat_pinned = chat_mgr.get_pinned_files(chat_id)
                    if chat_pinned:
                        pinned.extend(chat_pinned)

            # Try CAM pinned nodes
            try:
                from src.orchestration.cam_engine import get_cam_engine
                cam = get_cam_engine()
                if hasattr(cam, 'get_pinned_nodes'):
                    cam_pinned = cam.get_pinned_nodes()
                    for node in cam_pinned:
                        if isinstance(node, dict):
                            pinned.append(node)
                        else:
                            pinned.append({"path": str(node), "name": str(node).split("/")[-1]})
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
                    "description": "Session ID to check status for"
                }
            },
            "required": ["session_id"]
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
                        "message": "Status check initiated"
                    }
                }
            else:
                return loop.run_until_complete(self._execute_async(arguments))
        except RuntimeError:
            return asyncio.run(self._execute_async(arguments))

    async def _execute_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async implementation of session status check."""
        session_id = arguments.get("session_id")

        if not session_id:
            return {
                "success": False,
                "error": "session_id is required"
            }

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
                        "age_seconds": time.time() - state.get("initialized_at", time.time())
                    }
                }
            else:
                return {
                    "success": True,
                    "result": {
                        "exists": False,
                        "session_id": session_id,
                        "message": "Session not found or expired"
                    }
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Convenience functions for direct import
async def vetka_session_init(
    user_id: str = "default",
    group_id: Optional[str] = None,
    chat_id: Optional[str] = None,  # MARKER_108_1: Chat ID parameter
    include_viewport: bool = True,
    include_pinned: bool = True,
    compress: bool = True,
    max_context_tokens: int = 4000
) -> Dict[str, Any]:
    """
    Initialize MCP session with fat context.

    Convenience wrapper for SessionInitTool.

    MARKER_108_1: Phase 108.1 - Unified MCP-Chat ID
    If chat_id provided, links session to existing VETKA chat.
    If not, creates new chat and returns its ID as session_id.
    """
    tool = SessionInitTool()
    return await tool._execute_async({
        "user_id": user_id,
        "group_id": group_id,
        "chat_id": chat_id,  # MARKER_108_1: Pass chat_id
        "include_viewport": include_viewport,
        "include_pinned": include_pinned,
        "compress": compress,
        "max_context_tokens": max_context_tokens
    })


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
    tool_list.extend([
        SessionInitTool(),
        SessionStatusTool()
    ])
