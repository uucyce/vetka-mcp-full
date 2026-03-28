"""
Task Board MCP Tools — Phase 121

Three MCP tools for managing the Task Board:
1. vetka_task_board  — CRUD + list + summary + claim + complete
2. vetka_task_dispatch — dispatch tasks to pipeline
3. vetka_task_import — import from todo files

@status: active
@phase: 121
@depends: src/orchestration/task_board.py
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("VETKA_MCP")


# MARKER_191.7: Resolve project root for doc file reading
def _resolve_project_root() -> Path:
    """Find the main repo root for resolving doc paths."""
    env_root = os.environ.get("VETKA_MAIN_REPO")
    if env_root and Path(env_root).is_dir():
        return Path(env_root)
    # __file__ = src/mcp/tools/task_board_tools.py → 4 levels up to project root
    return Path(__file__).resolve().parent.parent.parent.parent


_PROJECT_ROOT = _resolve_project_root()


# MARKER_ZETA.DOCS_CACHE: Simple TTL cache for doc file reads
import time
import hashlib

_doc_cache: Dict[str, tuple] = {}  # key → (content_str, timestamp)
_DOC_CACHE_TTL = 300  # 5 minutes
_DOC_CACHE_MAX = 64


def _cache_key(doc_ref: str) -> str:
    """Stable cache key from doc path."""
    return hashlib.md5(doc_ref.encode()).hexdigest()[:12]


def _read_doc_cached(doc_ref: str, max_chars: int) -> Optional[str]:
    """Read doc file with TTL cache. Returns content or None."""
    key = _cache_key(doc_ref)
    now = time.time()

    # Check cache
    if key in _doc_cache:
        content, ts = _doc_cache[key]
        if now - ts < _DOC_CACHE_TTL:
            return content[:max_chars] if max_chars else content

    # Cache miss — read from disk
    full_path = _PROJECT_ROOT / doc_ref
    if not full_path.exists():
        full_path = _PROJECT_ROOT / doc_ref.lstrip("/")
    if not full_path.exists():
        return None

    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    # Evict if cache full
    if len(_doc_cache) >= _DOC_CACHE_MAX:
        oldest_key = min(_doc_cache, key=lambda k: _doc_cache[k][1])
        _doc_cache.pop(oldest_key, None)

    _doc_cache[key] = (content, now)
    return content[:max_chars] if max_chars else content


def _load_docs_content_sync(
    task: Dict[str, Any],
    budget: int = 8192,  # MARKER_197.SLIM: Reduced from 65536 to 8192 to cut token bloat
    per_doc: int = 4096,  # MARKER_197.SLIM: Reduced from 16384 to 4096 to cut token bloat
) -> str:
    """MARKER_191.7: Read architecture_docs + recon_docs file contents synchronously.

    MARKER_ZETA.ELISION: Applies ELISION L2 compression when total content > 4000 chars
    (mirrors async _inject_docs_content behavior in task_board.py).

    MARKER_ZETA.DOCS_CACHE: Uses TTL cache to avoid repeated disk reads.

    Used by claim/get actions to inject doc content into MCP response.
    MCP agents (Claude Code, Desktop, Cursor) don't go through dispatch_task,
    so they need docs content at claim/get time.

    Args:
        task: Task dict with architecture_docs/recon_docs fields
        budget: Total chars budget (default 8KB)
        per_doc: Per-document char cap (default 4KB)

    Returns:
        Formatted docs string, or empty string if no docs
    """
    doc_paths = []
    for field in ("architecture_docs", "recon_docs"):
        for doc_ref in task.get(field) or []:
            doc_ref = str(doc_ref).strip()
            if doc_ref:
                doc_paths.append((field, doc_ref))

    if not doc_paths:
        return ""

    sections = []
    total_chars = 0
    docs_included = 0
    docs_skipped = []

    for field, doc_ref in doc_paths:
        if total_chars >= budget:
            docs_skipped.append(doc_ref)
            continue

        content = _read_doc_cached(doc_ref, per_doc)
        if content is None:
            docs_skipped.append(f"{doc_ref} (not found)")
            continue

        # Truncate if read returned full content and it's long
        if len(content) > per_doc:
            content = (
                content[:per_doc] + f"\n... [truncated, {len(content)} total chars]"
            )

        remaining = budget - total_chars
        if len(content) > remaining:
            content = content[:remaining] + "\n... [budget exceeded]"

        sections.append(f"### {doc_ref} ({field})\n{content}")
        total_chars += len(content)
        docs_included += 1

    if not sections:
        return ""

    # MARKER_ZETA.ELISION: Apply ELISION L2 compression when content is large
    docs_text = "\n\n".join(sections)
    compressed = False
    try:
        if total_chars > 4000:
            from src.memory.elision import compress_context

            result = compress_context(docs_text, level=2)
            if result.get("compressed"):
                ratio = result.get("ratio", 1.0)
                if ratio > 1.1:
                    docs_text = result["compressed"]
                    compressed = True
                    logger.info(f"[TaskBoard] Sync docs compressed: ratio={ratio:.2f}")
    except Exception:
        pass  # ELISION optional, proceed with raw text

    header = f"--- DOCS ({docs_included} files"
    if docs_skipped:
        header += f", {len(docs_skipped)} skipped"
    if compressed:
        header += ", ELISION L2"
    header += ") ---\n"
    footer = "\n--- END DOCS ---"

    return header + docs_text + footer


# MARKER_200.ELISION_LIST: Lightweight field renaming for list responses
# Applied at dict level (no JSON serialization overhead)
_LIST_FIELD_MAP = {
    "title": "t",
    "status": "s",
    "priority": "pri",
    "phase_type": "pt",
    "complexity": "cx",
    "project_id": "pid",
    "assigned_tier": "tier",
    "assigned_to": "at",
    "source": "src",
    "role": "rl",
    "returned": "ret",
    "truncated": "trunc",
    "my_tasks": "mine",
    "other_tasks": "others",
    "my_count": "mc",
    "other_count": "oc",
    "my_role": "mr",
    "project_resolve": "pr",
}

# Reverse legend for agent decoding
_LIST_ELISION_LEGEND = {v: k for k, v in _LIST_FIELD_MAP.items()}


def _elision_rename_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Rename task fields using ELISION map + strip empty values."""
    out = {}
    for k, v in task.items():
        # Strip None, empty strings, empty lists
        if v is None or v == "" or v == []:
            continue
        new_key = _LIST_FIELD_MAP.get(k, k)
        out[new_key] = v
    return out


def _elision_compress_list(result: Dict[str, Any]) -> Dict[str, Any]:
    """Apply ELISION field renaming to task_board list response.

    Compresses task entries by renaming verbose keys (title→t, status→s, etc.)
    and stripping empty fields. Adds _elision legend (used keys only).
    """
    used_abbrevs = set()
    out = {}
    for k, v in result.items():
        new_key = _LIST_FIELD_MAP.get(k, k)
        if new_key != k:
            used_abbrevs.add(new_key)
        if k in ("tasks", "my_tasks", "other_tasks"):
            compressed_tasks = []
            for t in v:
                ct = _elision_rename_task(t)
                used_abbrevs.update(
                    ak for ak in ct if ak in _LIST_ELISION_LEGEND
                )
                compressed_tasks.append(ct)
            out[new_key] = compressed_tasks
        elif isinstance(v, dict) and k == "project_resolve":
            out[new_key] = v
        elif v is None or v == "" or v == []:
            continue
        else:
            out[new_key] = v
    # Only include actually-used abbreviations in legend
    out["_el"] = {a: _LIST_ELISION_LEGEND[a] for a in sorted(used_abbrevs)}
    return out


# ==========================================
# Tool 1: vetka_task_board (CRUD + list)
# ==========================================

TASK_BOARD_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            # MARKER_130.C16B: Added claim, complete, active_agents actions
            # MARKER_186.4: Added promote_to_main — transitions done_worktree → done_main
            # MARKER_195.20: Added verify — QA gate (done_worktree → verified/needs_fix)
            "enum": [
                "add",
                "list",
                "get",
                "update",
                "remove",
                "summary",
                "claim",
                "complete",
                "active_agents",
                "merge_request",
                "promote_to_main",
                "request_qa",
                "verify",
                "close",
                "bulk_close",
                "stale_check",
                "batch_merge",
                "search_fts",
                "debrief_skipped",
                "backfill_fts",
                "context_packet",
                "notify",
                "notifications",
                "ack_notifications",
            ],
            "description": "Operation to perform",
        },
        # For "add":
        "title": {"type": "string", "description": "Task title (required for add)"},
        "description": {
            "type": "string",
            "description": "Detailed task description — free text for context, problem statement, approach",
        },
        "profile": {
            "type": "string",
            "enum": ["p6"],
            "description": "Task intake profile with protocol defaults",
        },
        "priority": {
            "type": "number",
            "description": "1=critical, 2=high, 3=medium, 4=low, 5=someday",
        },
        "phase_type": {
            "type": "string",
            "enum": ["build", "fix", "research", "test"],
            "description": "Task type",
        },
        "complexity": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Estimated complexity",
        },
        "preset": {"type": "string", "description": "Pipeline preset override"},
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Tags for categorization",
        },
        "dependencies": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Task IDs that must complete first",
        },
        "project_id": {
            "type": "string",
            "description": "Logical project ID. For add: assigns project. For list: smart filter — case-insensitive, RU keyboard layout auto-fix, prefix autocomplete (e.g. 'c'→'cut', 'СГЕ'→'CUT').",
        },
        "project_lane": {
            "type": "string",
            "description": "Specific multitask lane/MCC tab identifier",
        },
        "architecture_docs": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Architecture docs linked to the task",
        },
        "recon_docs": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Recon docs linked to the task",
        },
        # MARKER_191.6: Structured task fields — discoverable by agents at tool discovery time
        "allowed_paths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Target files/directories this task should modify. Also serves as ownership guard — agent should not touch files outside this list. Example: ['src/orchestration/task_board.py', 'src/mcp/tools/']",
        },
        "completion_contract": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Acceptance criteria checklist. Each item = one verifiable condition the agent must satisfy. Example: ['API returns 200 on valid input', 'unit tests pass', 'no console errors in browser']",
        },
        "implementation_hints": {
            "type": "string",
            "description": "Algorithm hints, approach notes, or technical guidance for the implementing agent. Free text. Example: 'Use re.search with word boundary, not substring match. Check _commit_matches_task for the pattern.'",
        },
        # MARKER_ZETA.D4: Agent role/domain binding fields
        "role": {
            "type": "string",
            "description": "Agent callsign from agent_registry.yaml: Alpha, Beta, Gamma, Delta, Commander",
        },
        "domain": {
            "type": "string",
            "description": "Task domain from agent_registry.yaml: engine, media, ux, qa, architect",
        },
        "closure_tests": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Shell commands required for closure proof. Example: ['python -m pytest tests/test_task_board.py -v', 'python -c \"import ast; ast.parse(open(f).read())\"']",
        },
        "closure_files": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Files allowed for scoped auto-commit at task completion. If set, only these files are staged.",
        },
        # MARKER_130.C16B: Agent assignment fields
        "assigned_to": {
            "type": "string",
            "description": "Agent name: opus, cursor, dragon, grok",
        },
        "agent_type": {
            "type": "string",
            "description": "Agent type: claude_code, cursor, mycelium, grok, human",
        },
        # For "get", "update", "remove", "claim", "complete":
        "task_id": {
            "type": "string",
            "description": "Task ID (required for get/update/remove/claim/complete)",
        },
        # For "update":
        "status": {
            "type": "string",
            "enum": [
                "pending",
                "queued",
                "claimed",
                "running",
                "done",
                "done_worktree",
                "need_qa",
                "done_main",
                "failed",
                "cancelled",
                "verified",
                "needs_fix",
            ],
        },
        # For "verify":
        "verdict": {
            "type": "string",
            "enum": ["pass", "fail"],
            "description": "QA verdict for action=verify: pass → verified, fail → needs_fix",
        },
        "skip_qa": {
            "type": "boolean",
            "description": "Emergency bypass for QA gate in promote_to_main. Use only when QA is unavailable and merge is urgent. Logged as warning.",
        },
        "verified_by": {
            "type": "string",
            "description": "Agent performing verification (default: Delta)",
        },
        "notes": {
            "type": "string",
            "description": "Verification notes (for verify action)",
        },
        # For "list":
        "filter_status": {
            "type": "string",
            "description": "Filter by status (optional for list)",
        },
        "limit": {
            "type": "number",
            "description": "Max tasks to return in list (default: 40, max: 100)",
        },
        # MARKER_190.DOC_GATE: Force-create task without docs (bypass doc gate)
        "force_no_docs": {
            "type": "boolean",
            "description": "Bypass doc requirement gate. Use only when truly no relevant docs exist.",
        },
        # For "update" / "complete":
        "branch_name": {
            "type": "string",
            "description": "Git branch name (e.g. claude/cut-engine). Saved on complete, needed by merge_request.",
        },
        "commit_hash": {
            "type": "string",
            "description": "Git commit hash (for complete/promote_to_main)",
        },
        "commit_message": {
            "type": "string",
            "description": "Commit message (for complete)",
        },
        # MARKER_186.4: Branch name for worktree-aware completion
        "branch": {
            "type": "string",
            "description": "Git branch name (for complete). If on worktree branch, status=done_worktree. If omitted, auto-detects.",
        },
        # MARKER_188.2: Worktree path for auto-commit from worktree context
        "worktree_path": {
            "type": "string",
            "description": "Absolute path to worktree root. Required for auto-commit when agent runs in a worktree.",
        },
        # MARKER_192.2: execution_mode — controls closure proof requirements
        "execution_mode": {
            "type": "string",
            "enum": ["pipeline", "manual"],
            "description": "Closure proof mode. 'pipeline' = full proof (pipeline_success + verifier + tests). 'manual' = relaxed (commit_hash only). Auto-inferred from agent_type if omitted.",
        },
        # MARKER_196.6.1: Debrief answers captured in action=complete
        "q1_bugs": {
            "type": "string",
            "description": "Debrief Q1: What bugs did you notice? (optional, for action=complete)",
        },
        "q2_worked": {
            "type": "string",
            "description": "Debrief Q2: What unexpectedly worked? (optional, for action=complete)",
        },
        "q3_idea": {
            "type": "string",
            "description": "Debrief Q3: What idea came to mind? (optional, for action=complete)",
        },
        # MARKER_191.16: close / bulk_close fields
        "reason": {
            "type": "string",
            "description": "Reason for closing (for close/bulk_close): already_implemented, duplicate, obsolete, research_done, cancelled",
        },
        "task_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of task IDs (for bulk_close or bulk complete via action=complete)",
        },
        # MARKER_198.STALE: stale_check parameters
        "auto_close": {
            "type": "boolean",
            "description": "For stale_check: if true, auto-close tasks with score >= 0.8. Default false (dry run).",
        },
        # MARKER_198.MERGE: merge_request strategy
        "strategy": {
            "type": "string",
            "enum": ["cherry-pick", "merge", "squash"],
            "description": "Merge strategy for merge_request. 'cherry-pick' (default): per-commit. 'merge': git merge --no-ff (handles feature branches). 'squash': single squash commit.",
        },
        # MARKER_199.FTS5: search_fts parameters
        "query": {
            "type": "string",
            "description": 'FTS5 search query for action=search_fts. Supports: AND, OR, phrase "...", prefix*',
        },
        # MARKER_200.AGENT_WAKE: Notification parameters
        "target_role": {
            "type": "string",
            "description": "Target agent callsign for action=notify (e.g. 'Alpha', 'Commander')",
        },
        "source_role": {
            "type": "string",
            "description": "Source agent callsign for action=notify",
        },
        "message": {
            "type": "string",
            "description": "Notification message text for action=notify",
        },
        "ntype": {
            "type": "string",
            "description": "Notification type: task_verified, task_needs_fix, ready_to_merge, task_completed, custom",
        },
        "unread_only": {
            "type": "boolean",
            "description": "For action=notifications: only return unread (default true)",
        },
        "notification_ids": {
            "description": "For action=ack_notifications: specific notification IDs to mark as read",
            "items": {"type": "string"},
            "type": "array",
        },
    },
    "required": ["action"],
}


def _suggest_docs_for_title(title: str, limit: int = 5) -> list:
    """MARKER_190.DOC_GATE: Search docs/ for files matching task title keywords.

    Returns list of relative doc paths ranked by relevance.

    Strategy priority:
    1. vetka_search_semantic (REST call to localhost:5001) — our own RRF/hybrid stack
    2. Fallback: keyword glob search in docs/ by filename — zero dependencies
    """
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[3]
    docs_dir = project_root / "docs"
    if not docs_dir.exists():
        return []

    # Strategy 1: vetka_search_semantic via REST (same as MCP tool uses)
    try:
        import urllib.request
        import urllib.parse
        import json as _json

        params = urllib.parse.urlencode(
            {"q": title, "limit": limit * 4, "mode": "hybrid"}
        )
        url = f"http://localhost:5001/api/search/hybrid?{params}"
        req = urllib.request.Request(url, method="GET")
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read().decode("utf-8"))

        results = data.get("results", [])
        if results:
            suggestions = []
            for item in results:
                path = item.get("path") or item.get("file_path", "")
                if not path:
                    continue
                try:
                    rel = str(Path(path).relative_to(project_root))
                except ValueError:
                    rel = path
                if rel.startswith("docs/") and rel.endswith(".md"):
                    suggestions.append(rel)
                if len(suggestions) >= limit:
                    break
            if suggestions:
                logger.debug(
                    f"[DocGate] vetka_search found {len(suggestions)} docs for: {title[:50]}"
                )
                hybrid_results = suggestions
            else:
                hybrid_results = []
    except Exception as e:
        logger.debug(f"[DocGate] vetka_search unavailable ({e}), falling back to glob")
        hybrid_results = []

    # Strategy 2: keyword glob search in docs/ (complements hybrid with filename matching)
    import re

    keywords = [w.lower() for w in re.split(r"[\s:_\-—/]+", title) if len(w) >= 3]
    stop_words = {
        "bug",
        "fix",
        "arch",
        "the",
        "for",
        "and",
        "with",
        "new",
        "add",
        "test",
        "task",
        "при",
        "что",
        "как",
        "это",
        "все",
        "нет",
        "без",
        "или",
        "показывают",
        "одно",
    }
    keywords = [k for k in keywords if k not in stop_words]

    if not keywords:
        return []

    suggestions = []
    for md_file in sorted(
        docs_dir.rglob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        name_lower = md_file.name.lower() + " " + md_file.parent.name.lower()
        score = sum(1 for k in keywords if k in name_lower)
        if score > 0:
            try:
                rel = str(md_file.relative_to(project_root))
            except ValueError:
                rel = str(md_file)
            suggestions.append((score, rel))

    suggestions.sort(key=lambda x: x[0], reverse=True)
    glob_results = [path for _, path in suggestions[:limit]]

    # Merge: glob first (exact filename match), then hybrid (semantic), deduplicate
    seen = set()
    merged = []
    for path in glob_results + hybrid_results:
        if path not in seen:
            seen.add(path)
            merged.append(path)
    return merged[:limit]


def handle_task_board(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle vetka_task_board MCP tool calls.

    CRUD + list + summary operations on the task board.
    """
    from src.orchestration.task_board import get_task_board
    from src.services.roadmap_task_sync import apply_task_profile_defaults

    action = arguments.get("action")
    if not action:
        return {"success": False, "error": "action is required"}

    # MARKER_195.6: Record task_board action for protocol tracking
    # MARKER_195.21: Use consistent session_id (was hardcoded "mcp_default", debrief read "default")
    # MARKER_198.ROLE: Aligned fallback to "default" — session_init stores role on "default",
    # so task_board must look it up on the same key.
    _tracker_sid = arguments.get("session_id") or "default"
    try:
        from src.services.session_tracker import get_session_tracker

        get_session_tracker().record_action(
            _tracker_sid,
            "vetka_task_board",
            {"action": action, "task_id": arguments.get("task_id", "")},
        )
    except Exception:
        pass

    board = get_task_board()

    # MARKER_196.2.2: Auto-attribution from session role
    # If session_init(role=X) was called, auto-fill role/domain/branch fields.
    # Uses setdefault — explicit arguments always take precedence.
    _session_role = None
    try:
        from src.services.session_tracker import get_session_tracker

        _session_role = get_session_tracker().get_role(_tracker_sid)
    except Exception:
        pass

    if _session_role and action in ("claim", "complete", "add"):
        if action == "claim":
            arguments.setdefault("assigned_to", _session_role["callsign"])
            arguments.setdefault("role", _session_role["callsign"])
        if action == "complete":
            arguments.setdefault("branch", _session_role["branch"])
        if action == "add":
            arguments.setdefault("role", _session_role["callsign"])
            arguments.setdefault("domain", _session_role["domain"])

    # MARKER_198.ROLE: Fallback — if session role lookup failed but explicit role= was passed,
    # use it for assigned_to on claim. Prevents "unknown" when session tracker has no binding.
    if (
        action == "claim"
        and arguments.get("role")
        and arguments.get("assigned_to", "unknown") == "unknown"
    ):
        arguments["assigned_to"] = arguments["role"]

    if action == "add":
        title = arguments.get("title")
        if not title:
            return {"success": False, "error": "title is required for add"}
        payload = dict(arguments)
        payload["source"] = "mcp"

        # MARKER_190.DOC_GATE: Universal doc requirement for all task types
        # Every task must have at least one architecture_doc or recon_doc.
        # If missing: search docs/ by title, suggest matches, REJECT until attached.
        # force_no_docs=true bypasses (for truly novel tasks with no prior docs).
        # MARKER_195.3: phase_type-aware — research/test auto-exempt (they create docs, not consume them).
        arch_docs = [
            d for d in (payload.get("architecture_docs") or []) if str(d).strip()
        ]
        recon_docs = [d for d in (payload.get("recon_docs") or []) if str(d).strip()]
        force_no_docs = bool(payload.pop("force_no_docs", False))
        phase_type = payload.get("phase_type", "")
        doc_exempt_types = ("research", "test")

        if not arch_docs and not recon_docs and phase_type not in doc_exempt_types:
            # Build search query from title + tags for better relevance
            tags = payload.get("tags") or []
            search_query = title + " " + " ".join(str(t) for t in tags)
            suggested = _suggest_docs_for_title(search_query)

            if not force_no_docs:
                return {
                    "success": False,
                    "error": "DOC_GATE: Task requires at least one architecture_doc or recon_doc. "
                    "Attach a doc or pass force_no_docs=true to bypass.",
                    "doc_gate": True,
                    "suggested_docs": suggested,
                    "hint": "Re-call with architecture_docs=[...] or recon_docs=[...] from suggestions above. "
                    "Use force_no_docs=true ONLY if no relevant docs exist. "
                    "Note: phase_type=research and phase_type=test are auto-exempt.",
                }
            # MARKER_196.DOCGATE: Strict mode — block force_no_docs for fix/build
            # when suggested_docs clearly shows relevant docs exist.
            # Agent must attach docs, not bypass.
            if suggested and len(suggested) >= 2 and phase_type in ("fix", "build"):
                return {
                    "success": False,
                    "error": f"DOC_GATE STRICT: force_no_docs rejected — {len(suggested)} relevant docs found. "
                    "For fix/build tasks, attach at least one doc from the list below.",
                    "doc_gate": True,
                    "strict_mode": True,
                    "suggested_docs": suggested,
                    "hint": "Re-call with architecture_docs=[...] or recon_docs=[...]. "
                    "force_no_docs is only allowed when suggested_docs is empty or has <2 matches.",
                }
            # Allow bypass for tasks with 0-1 weak matches
            if suggested:
                logger.warning(
                    "[DOC_GATE] force_no_docs accepted (weak match) for '%s': %s",
                    title,
                    suggested[:3],
                )

        try:
            payload = apply_task_profile_defaults(payload)
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        try:
            task_id = board.add_task(
                title=title,
                description=payload.get("description", ""),
                priority=int(payload.get("priority", 3)),
                phase_type=payload.get("phase_type", "build"),
                complexity=payload.get("complexity", "medium"),
                preset=payload.get("preset"),
                tags=payload.get("tags"),
                dependencies=payload.get("dependencies"),
                source=payload.get("source", "mcp"),
                project_id=payload.get("project_id"),
                project_lane=payload.get("project_lane"),
                architecture_docs=payload.get("architecture_docs"),
                recon_docs=payload.get("recon_docs"),
                protocol_version=payload.get("protocol_version"),
                require_closure_proof=bool(payload.get("require_closure_proof")),
                closure_tests=payload.get("closure_tests"),
                closure_files=payload.get("closure_files"),
                task_origin=payload.get("task_origin"),
                workflow_selection_origin=payload.get("workflow_selection_origin"),
                completion_contract=payload.get("completion_contract"),
                allowed_paths=payload.get("allowed_paths"),
                implementation_hints=payload.get("implementation_hints"),
                depends_on_docs=payload.get("depends_on_docs"),
                execution_mode=payload.get("execution_mode"),
                role=payload.get("role"),  # MARKER_ZETA.D4
                domain=payload.get("domain"),  # MARKER_ZETA.D4
            )
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        result = {
            "success": True,
            "task_id": task_id,
            "message": f"Task '{title}' added",
        }
        # MARKER_196.DOCGATE: Surface warnings if force_no_docs was used
        _dg_warnings = payload.get("_doc_gate_warnings")
        if _dg_warnings:
            result["doc_gate_warning"] = _dg_warnings[0]

        # MARKER_199.CONTRACT: API Contract Guard — detect path overlap with active tasks
        # When parallel tasks share allowed_paths, they risk API drift (different method names).
        # Surface a warning so Commander can provide a Protocol contract.
        # MARKER_201.SHARED_ZONES: Suppress warning for naturally shared files (App.tsx,
        # task_board.py, package.json etc.) registered in agent_registry.yaml shared_zones.
        new_paths = payload.get("allowed_paths") or []
        if new_paths:
            try:
                # Load shared_zone file basenames to suppress false-positive overlap warnings
                _shared_zone_files: set = set()
                try:
                    from src.services.agent_registry import get_agent_registry
                    _reg = get_agent_registry()
                    _shared_zone_files = {zone.file for zone in _reg.shared_zones}
                except Exception:
                    pass

                # Only warn about exclusive paths (not registered shared_zones)
                exclusive_paths = [
                    p for p in new_paths
                    if not any(
                        p == sz or p.endswith("/" + sz) or sz.endswith("/" + p.split("/")[-1])
                        for sz in _shared_zone_files
                    )
                ]

                overlapping = board.find_tasks_by_changed_files(exclusive_paths) if exclusive_paths else []
                # Exclude the task we just created
                overlapping = [t for t in overlapping if t.get("id") != task_id]
                if overlapping:
                    overlap_titles = [
                        f"{t['id']}: {t.get('title', '')[:50]}" for t in overlapping[:5]
                    ]
                    result["api_contract_warning"] = {
                        "message": (
                            f"PATH OVERLAP: {len(overlapping)} active task(s) share allowed_paths with this task. "
                            "Risk of API drift if parallel agents use different method names. "
                            "Consider adding a Python Protocol stub to implementation_hints."
                        ),
                        "overlapping_tasks": overlap_titles,
                        "shared_paths": [
                            p
                            for p in exclusive_paths
                            if any(
                                any(
                                    p.startswith(ap) or ap.startswith(p)
                                    for ap in (t.get("allowed_paths") or [])
                                )
                                for t in overlapping
                            )
                        ][:10],
                    }
            except Exception:
                pass  # Contract guard is advisory, never blocks

        return result

    elif action == "list":
        filter_status = arguments.get("filter_status")
        tasks = board.get_queue(status=filter_status)
        # MARKER_191.16: Smart project_id filter — case-insensitive, RU layout fix, prefix match
        filter_project = str(arguments.get("project_id") or "").strip()
        project_resolve = None
        if filter_project:
            tasks, project_resolve = board.filter_tasks_by_project(
                tasks, filter_project
            )
        # MARKER_189.13 + MARKER_191.4: Dynamic limit; no limit when filtering by project
        total = len(tasks)
        if filter_project and not arguments.get("limit"):
            # Filtered query without explicit limit → return all matches
            page = tasks
        else:
            max_limit = min(int(arguments.get("limit") or 40), 100)
            page = tasks[:max_limit]

        # MARKER_198.JEPA_TASK_LENS: Re-rank tasks by semantic relevance to agent role
        if _session_role and len(page) >= 3:
            try:
                import os as _os

                if _os.environ.get("VETKA_TASK_JEPA_RANK", "1") != "0":
                    from src.services.mcc_jepa_adapter import embed_texts_for_overlay

                    _role_intent = f"role:{_session_role['callsign']} domain:{_session_role.get('domain', '')} {_session_role.get('role_title', '')}"
                    _task_texts = [
                        f"{t.get('title', '')} {t.get('description', '')[:100]}"
                        for t in page
                    ]
                    _all = [_role_intent] + _task_texts
                    _emb = embed_texts_for_overlay(_all, target_dim=128)
                    if _emb.vectors and len(_emb.vectors) == len(_all):
                        _iv = _emb.vectors[0]
                        _scores = []
                        for _idx, _tv in enumerate(_emb.vectors[1:]):
                            _dot = sum(
                                float(_iv[j]) * float(_tv[j]) for j in range(len(_iv))
                            )
                            _na = (
                                sum(float(_iv[j]) ** 2 for j in range(len(_iv))) ** 0.5
                            )
                            _nb = (
                                sum(float(_tv[j]) ** 2 for j in range(len(_iv))) ** 0.5
                            )
                            _sim = (
                                _dot / (_na * _nb)
                                if _na > 1e-12 and _nb > 1e-12
                                else 0.0
                            )
                            _scores.append((_idx, _sim))
                        # Stable sort: primary=relevance score desc, secondary=original priority asc
                        _scores.sort(
                            key=lambda x: (-x[1], page[x[0]].get("priority", 5))
                        )
                        page = [page[_idx] for _idx, _ in _scores]
            except Exception:
                pass  # JEPA task lens never blocks list

        # MARKER_198.ROLE: Personalized list — own tasks first, others collapsed
        # Determine current agent's callsign from session or explicit role= argument
        _my_callsign = None
        if _session_role:
            _my_callsign = _session_role["callsign"]
        if not _my_callsign and arguments.get("role"):
            _my_callsign = arguments["role"]

        if _my_callsign:
            _my_callsign_lower = _my_callsign.lower()
            my_tasks = []
            other_tasks = []
            for t in page:
                is_mine = (t.get("role") or "").lower() == _my_callsign_lower or (
                    t.get("assigned_to") or ""
                ).lower() == _my_callsign_lower
                if is_mine:
                    my_tasks.append(t)
                else:
                    other_tasks.append(t)
            # Full detail for own tasks
            my_tasks_out = [
                {
                    "id": t["id"],
                    "title": t["title"],
                    "priority": t["priority"],
                    "status": t["status"],
                    "phase_type": t["phase_type"],
                    "complexity": t["complexity"],
                    "source": t.get("source", ""),
                    "assigned_tier": t.get("assigned_tier"),
                    "project_id": t.get("project_id", ""),
                    "role": t.get("role", ""),
                    "assigned_to": t.get("assigned_to", ""),
                }
                for t in my_tasks
            ]
            # Collapsed for others — title truncated, fewer fields
            other_tasks_out = [
                {
                    "id": t["id"],
                    "title": t["title"][:60] + ("..." if len(t["title"]) > 60 else ""),
                    "priority": t["priority"],
                    "status": t["status"],
                    "role": t.get("role", ""),
                }
                for t in other_tasks
            ]
            result = {
                "success": True,
                "count": total,
                "returned": len(page),
                "truncated": total > len(page),
                "my_role": _my_callsign,
                "my_tasks": my_tasks_out,
                "my_count": len(my_tasks_out),
                "other_tasks": other_tasks_out,
                "other_count": len(other_tasks_out),
            }
        else:
            result = {
                "success": True,
                "count": total,
                "returned": len(page),
                "truncated": total > len(page),
                "tasks": [
                    {
                        "id": t["id"],
                        "title": t["title"],
                        "priority": t["priority"],
                        "status": t["status"],
                        "phase_type": t["phase_type"],
                        "complexity": t["complexity"],
                        "source": t.get("source", ""),
                        "assigned_tier": t.get("assigned_tier"),
                        "project_id": t.get("project_id", ""),
                    }
                    for t in page
                ],
            }

        if project_resolve:
            result["project_resolve"] = project_resolve

        # MARKER_200.ELISION_LIST: Compress list response to save tokens
        result = _elision_compress_list(result)
        return result

    elif action == "get":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for get"}
        task = board.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        # MARKER_191.7: Auto-inject docs content for MCP agents
        docs = _load_docs_content_sync(task)
        result = {"success": True, "task": task}
        if docs:
            result["docs_content"] = docs
        return result

    # MARKER_199.MCC: context_packet — resolve task into MCC-ready packet for local models
    elif action == "context_packet":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for context_packet"}
        packet = board.get_context_packet(task_id)
        if not packet:
            return {"success": False, "error": f"Task {task_id} not found"}
        return {"success": True, "context_packet": packet}

    elif action == "update":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for update"}

        # Collect updatable fields
        updates = {}
        for field in [
            "title",
            "description",
            "priority",
            "phase_type",
            "complexity",
            "preset",
            "status",
            "tags",
            "dependencies",
            "project_id",
            "project_lane",
            "architecture_docs",
            "recon_docs",
            "closure_tests",
            "closure_files",
            "allowed_paths",
            "completion_contract",
            "implementation_hints",
            "role",
            "domain",
            "branch_name",
        ]:
            if field in arguments and arguments[field] is not None:
                updates[field] = arguments[field]

        # MARKER_195.20e: Map branch → branch_name (MCP param name vs DB field name)
        if "branch_name" not in updates and arguments.get("branch"):
            updates["branch_name"] = arguments["branch"]

        if not updates:
            return {"success": False, "error": "No fields to update"}

        ok = board.update_task(task_id, **updates)
        # MARKER_195.22: Include error context when update fails
        result = {"success": ok, "updated_fields": list(updates.keys())}
        if not ok:
            task_exists = board.get_task(task_id)
            if not task_exists:
                result["error"] = f"Task {task_id} not found"
            else:
                result["error"] = (
                    f"update_task returned False (possible invalid status or phase_type)"
                )
        return result

    elif action == "remove":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for remove"}
        ok = board.remove_task(task_id)
        return {
            "success": ok,
            "message": f"Task {task_id} removed" if ok else f"Task {task_id} not found",
        }

    elif action == "summary":
        summary = board.get_board_summary()
        return {"success": True, **summary}

    # MARKER_130.C16B: claim action
    # MARKER_191.7: Enhanced claim — returns full task + docs content
    elif action == "claim":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for claim"}
        agent_name = arguments.get("assigned_to", "unknown")
        agent_type = arguments.get("agent_type", "unknown")
        result = board.claim_task(task_id, agent_name, agent_type)
        # Inject full task + docs on successful claim
        if result.get("success"):
            task = board.get_task(task_id)
            if task:
                result["task"] = task
                docs = _load_docs_content_sync(task)
                if docs:
                    result["docs_content"] = docs

                # MARKER_199.CLAIM_MEMORY: Inject similar completed tasks + Qdrant learnings
                # Agent sees predecessor approaches at the right moment — claim time.
                try:
                    import re as _re_claim
                    _clean = _re_claim.sub(r'[^\w\s]', '', task.get("title", ""))
                    _words = _clean.split()[:5]
                    if _words:
                        _fts_hits = board.search_fts(" ".join(_words), limit=8)
                        _similar = []
                        for _h in _fts_hits:
                            if _h.get("task_id") == task_id:
                                continue
                            _st = board.get_task(_h["task_id"])
                            if _st and _st.get("status") in ("done", "done_main", "done_worktree", "verified"):
                                _similar.append({
                                    "task_id": _h["task_id"],
                                    "title": _st.get("title", "")[:80],
                                    "commit_message": (_st.get("commit_message") or "")[:120],
                                    "assigned_to": _st.get("assigned_to", ""),
                                })
                                if len(_similar) >= 3:
                                    break
                        if _similar:
                            result["similar_completed"] = _similar
                except Exception:
                    pass  # Claim-time memory is best-effort

                # Qdrant L2 learnings related to this task
                try:
                    from src.orchestration.resource_learnings import get_learning_store
                    _l2 = get_learning_store()
                    _query = task.get("title", "") + " " + (task.get("description", "")[:200])
                    _learnings = _l2.search_learnings_sync(query=_query, limit=3)
                    if _learnings:
                        result["related_learnings"] = [
                            {"text": lr.get("text", "")[:150], "category": lr.get("category", "")}
                            for lr in _learnings
                        ]
                except Exception:
                    pass  # L2 learnings are best-effort

            # MARKER_200.STM_AUTOSAVE: Persist STM on claim (session milestone)
            try:
                from src.memory.stm_buffer import get_stm_buffer
                _stm = get_stm_buffer()
                if len(_stm) > 0:
                    _stm.save_to_disk()
                    logger.debug(f"[TaskBoard] STM auto-saved on claim: {len(_stm)} entries")
            except Exception:
                pass  # STM save is best-effort

        return result

    # MARKER_181.4: complete action — unified pipeline
    # MARKER_186.4: worktree-aware completion — detect branch, set done_worktree/done_main
    # Flow: agent → complete → detect branch → auto-commit (scoped) → digest → close task
    elif action == "complete":
        # MARKER_191.19: Bulk complete — multiple task_ids in one commit
        task_ids = arguments.get("task_ids", [])
        if task_ids and len(task_ids) > 1:
            # Bulk mode: complete multiple tasks with a single commit hash
            commit_hash = arguments.get("commit_hash")
            commit_message = arguments.get("commit_message")
            branch = arguments.get("branch")
            results = []
            for tid in task_ids:
                task = board.get_task(tid)
                if not task:
                    results.append(
                        {"task_id": tid, "success": False, "error": "not found"}
                    )
                    continue
                r = board.complete_task(
                    tid,
                    commit_hash or "",
                    commit_message or f"bulk complete {len(task_ids)} tasks",
                    branch=branch,
                )
                results.append({"task_id": tid, "success": r.get("success", False)})
            completed_count = sum(1 for r in results if r.get("success"))
            return {
                "success": True,
                "completed_count": completed_count,
                "total": len(task_ids),
                "results": results,
                "commit_hash": commit_hash,
            }

        # Original single task_id path continues...
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for complete"}

        task = board.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        commit_hash = arguments.get("commit_hash")
        commit_message = arguments.get("commit_message")

        # MARKER_186.4: Detect current git branch for worktree-aware status
        # MARKER_188.2: Use worktree_path as cwd for git operations
        # MARKER_188.3: Auto-infer worktree_path from branch= if not explicit
        worktree_path = arguments.get("worktree_path")
        current_branch = arguments.get("branch")

        # Auto-detect worktree_path from branch name (claude/<name> → .claude/worktrees/<name>)
        if (
            not worktree_path
            and current_branch
            and current_branch.startswith("claude/")
        ):
            from pathlib import Path

            _main_root = Path(__file__).resolve().parents[3]
            wt_name = current_branch.split("/", 1)[1]
            candidate = _main_root / ".claude" / "worktrees" / wt_name
            if candidate.exists():
                worktree_path = str(candidate)
                logger.info(
                    f"[TaskBoard] Auto-detected worktree_path from branch: {worktree_path}"
                )

        # MARKER_197: _detect_git_branch() removed — branch comes from session role (196.2.2)
        # Fallback: AgentRegistry auto-infer below

        # MARKER_195.22: Auto-infer branch from task metadata via AgentRegistry
        # Prevents merge_request failures due to missing branch_name.
        # Tries: role field → assigned_to → callsign prefix in title (ALPHA-P1: ...)
        if not current_branch or current_branch == "main":
            try:
                from src.services.agent_registry import get_agent_registry

                registry = get_agent_registry()
                _candidates = [
                    task.get("role", ""),
                    task.get("assigned_to", ""),
                ]
                # Extract callsign from title prefix: "ALPHA-P1: ..." → "Alpha"
                _title = task.get("title", "")
                _title_prefix = _title.split("-")[0].split(":")[0].split(" ")[0].strip()
                if _title_prefix and len(_title_prefix) <= 10:
                    _candidates.append(_title_prefix)

                for _cand in _candidates:
                    if not _cand or _cand.lower() in ("unknown", ""):
                        continue
                    agent_role = registry.get_by_callsign(_cand)
                    if agent_role and agent_role.branch and agent_role.branch != "main":
                        current_branch = agent_role.branch
                        logger.info(
                            f"[TaskBoard] Auto-inferred branch={current_branch} from '{_cand}'"
                        )
                        break
            except Exception as e:
                logger.debug(f"[TaskBoard] Branch inference from registry failed: {e}")

        # MARKER_192.2: execution_mode override for manual agents
        exec_mode = arguments.get("execution_mode")

        # MARKER_196.3.1: Ownership validation (soft mode)
        # Compare changed files against role.owned_paths from session.
        # Soft mode: warn in result, don't block.
        _ownership_warnings = []
        if _session_role:
            try:
                from src.services.agent_registry import get_agent_registry

                _ow_reg = get_agent_registry()
                _ow_role = _ow_reg.get_by_callsign(_session_role["callsign"])
                if _ow_role:
                    import subprocess as _ow_sp

                    _ow_cwd = worktree_path or str(Path(__file__).resolve().parents[3])
                    _ow_diff = _ow_sp.run(
                        ["git", "diff", "--name-only", "--cached"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        cwd=_ow_cwd,
                    )
                    # Also check unstaged
                    _ow_diff2 = _ow_sp.run(
                        ["git", "diff", "--name-only"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        cwd=_ow_cwd,
                    )
                    _changed = set()
                    if _ow_diff.returncode == 0:
                        _changed.update(
                            f.strip() for f in _ow_diff.stdout.splitlines() if f.strip()
                        )
                    if _ow_diff2.returncode == 0:
                        _changed.update(
                            f.strip()
                            for f in _ow_diff2.stdout.splitlines()
                            if f.strip()
                        )

                    for _cf in _changed:
                        _result = _ow_reg.validate_file_ownership(
                            _ow_role.callsign, _cf
                        )
                        if _result.is_blocked:
                            _ownership_warnings.append(
                                f"BLOCKED: {_cf} (pattern: {_result.matched_blocked_pattern})"
                            )
                        elif not _result.is_owned and not _result.shared_zone:
                            _ownership_warnings.append(f"NOT_OWNED: {_cf}")

                    if _ownership_warnings:
                        logger.warning(
                            "[TaskBoard] Ownership warnings for %s: %s",
                            _ow_role.callsign,
                            _ownership_warnings,
                        )
            except Exception:
                pass  # Ownership check never blocks completion

        # Case A: agent already committed — just close
        # MARKER_195.20: Pass worktree_path for branch auto-detection fallback
        if commit_hash:
            result = board.complete_task(
                task_id,
                commit_hash,
                commit_message,
                branch=current_branch,
                worktree_path=worktree_path,
                execution_mode=exec_mode,
            )
            if _ownership_warnings:
                result["ownership_warnings"] = _ownership_warnings
                # MARKER_197.OWNERSHIP: Flag cross-domain + alert Commander
                _flag_cross_domain_violations(
                    board,
                    task_id,
                    task,
                    _ownership_warnings,
                    agent_callsign=_session_role.get("callsign", "")
                    if _session_role
                    else "",
                )
            _inject_debrief(result, arguments)
            return result

        # MARKER_182.7: Try Verifier merge if run_id is available (Phase 182+ path)
        task_result = task.get("result") or {}
        run_id = task_result.get("run_id") if isinstance(task_result, dict) else None
        session_id = (
            task_result.get("session_id") if isinstance(task_result, dict) else None
        )

        if run_id and run_id.startswith("run_"):
            try:
                import asyncio
                from src.orchestration.agent_pipeline import AgentPipeline

                merge_result = asyncio.get_event_loop().run_until_complete(
                    AgentPipeline.verify_and_merge(
                        run_id=run_id,
                        task_id=task_id,
                        session_id=session_id,
                        commit_message=commit_message,
                    )
                )
                if merge_result.get("success") and merge_result.get("commit_hash"):
                    # Verifier merge succeeded — close task
                    result = board.complete_task(
                        task_id,
                        merge_result["commit_hash"],
                        merge_result.get("commit_message"),
                        branch=current_branch,
                        worktree_path=worktree_path,
                        execution_mode=exec_mode,
                    )
                    result["verifier_merge"] = merge_result
                    _inject_debrief(result, arguments)
                    return result
                # If no commit_hash but success (nothing to commit) — fall through to legacy
                if merge_result.get("success"):
                    logger.info(
                        f"[TaskBoard] Verifier merge: {merge_result.get('note', 'nothing to merge')}"
                    )
                else:
                    logger.warning(
                        f"[TaskBoard] Verifier merge failed: {merge_result.get('error')}, falling back to legacy"
                    )
            except Exception as vm_err:
                logger.warning(
                    f"[TaskBoard] Verifier merge exception (falling back): {vm_err}"
                )

        # Case B/C: no commit yet — try auto-commit (legacy path)
        # MARKER_188.2: Pass worktree_path for correct cwd in git operations
        # MARKER_195.22: Pass closure_files from MCP arguments (overrides task.closure_files)
        mcp_closure_files = arguments.get("closure_files")
        auto = _try_auto_commit(
            task_id,
            task,
            commit_message,
            cwd=worktree_path,
            override_closure_files=mcp_closure_files,
        )

        # If commit failed or scoping rejected files → do NOT close task
        # MARKER_195.22: Also catch attempted=False + success=False (allowed_paths mismatch)
        if not auto.get("success") and auto.get("error"):
            return {
                "success": False,
                "error": f"Auto-commit failed: {auto.get('error', 'unknown')}. Task NOT closed.",
                "task_id": task_id,
                "auto_commit": auto,
            }

        # Double-close protection: GitCommitTool._auto_complete_tasks() may
        # have already closed this task via [task:tb_xxxx] in commit message
        task_refreshed = board.get_task(task_id)
        if task_refreshed and task_refreshed.get("status", "").startswith("done"):
            _auto_result = {
                "success": True,
                "task_id": task_id,
                "commit_hash": auto.get("hash"),
                "note": "auto-closed by commit pipeline",
                "auto_commit": auto,
            }
            _inject_debrief(_auto_result, arguments)
            return _auto_result

        # Close task (commit succeeded or nothing to commit)
        result = board.complete_task(
            task_id,
            auto.get("hash"),
            auto.get("message"),
            branch=current_branch,
            worktree_path=worktree_path,
            execution_mode=exec_mode,
        )
        result["auto_commit"] = auto

        # MARKER_196.3.1: Attach ownership warnings to result
        if _ownership_warnings:
            result["ownership_warnings"] = _ownership_warnings
            # MARKER_197.OWNERSHIP: Flag cross-domain + alert Commander
            _flag_cross_domain_violations(
                board,
                task_id,
                task,
                _ownership_warnings,
                agent_callsign=_session_role.get("callsign", "")
                if _session_role
                else "",
            )

        # MARKER_195.21: Debrief injection via extracted function (was inline, bypassed on 3 paths)
        _inject_debrief(result, arguments)

        # MARKER_200.CHECKPOINT: Persist session state on complete
        try:
            from src.services.session_tracker import get_session_tracker
            _ck_tracker = get_session_tracker()
            _ck_tracker.save_checkpoint(
                _tracker_sid,
                task_title=task.get("title") if task else None,
                decisions=arguments.get("decisions"),
            )
        except Exception:
            pass  # Checkpoint is best-effort

        return result

    # MARKER_130.C16B: active_agents action
    elif action == "active_agents":
        agents = board.get_active_agents()
        return {"success": True, "agents": agents, "count": len(agents)}

    # MARKER_184.5 + MARKER_198.MERGE: merge_request with strategy param
    elif action == "merge_request":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for merge_request"}
        strategy = arguments.get("strategy")  # None = use task default or "cherry-pick"

        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(
                        asyncio.run, board.merge_request(task_id, strategy=strategy)
                    ).result()
            else:
                result = loop.run_until_complete(
                    board.merge_request(task_id, strategy=strategy)
                )
            return result
        except Exception as e:
            return {"success": False, "error": f"merge_request failed: {e}"}

    # MARKER_195.20c: promote_to_main — delegates to merge_request for real merge
    elif action == "promote_to_main":
        task_id = arguments.get("task_id")
        if not task_id:
            return {
                "success": False,
                "error": "task_id is required for promote_to_main",
            }
        merge_commit_hash = arguments.get("commit_hash")
        role = arguments.get("role", "")
        skip_qa = arguments.get("skip_qa", False)
        return board.promote_to_main(task_id, merge_commit_hash, role=role, skip_qa=skip_qa)

    # MARKER_196.QA: request_qa — move done_worktree → need_qa
    elif action == "request_qa":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for request_qa"}
        task = board.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        if task["status"] != "done_worktree":
            return {
                "success": False,
                "error": f"Task {task_id} is '{task['status']}', expected done_worktree",
            }
        board.update_task(
            task_id,
            status="need_qa",
            _history_event="qa_requested",
            _history_source="task_board",
            _history_reason="QA review requested",
            _history_agent_name=arguments.get("assigned_to", ""),
        )
        return {
            "success": True,
            "task_id": task_id,
            "status": "need_qa",
            "message": "Task moved to QA queue",
        }

    # MARKER_195.20: QA Gate — verify a done_worktree task before merge
    elif action == "verify":
        task_id = arguments.get("task_id")
        verdict = arguments.get("verdict")  # "pass" or "fail"
        if not task_id or not verdict:
            return {
                "success": False,
                "error": "task_id and verdict ('pass' or 'fail') required for verify",
            }
        notes = arguments.get("notes", "")
        verified_by = arguments.get("verified_by", arguments.get("assigned_to", ""))
        return board.verify_task(task_id, verdict, notes, verified_by)

    # MARKER_191.16: close — close task without git commit, with a reason field
    elif action == "close":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for close"}
        reason = arguments.get("reason", "closed")
        task = board.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        updated = board.update_task(
            task_id,
            status="done_main",
            _history_event="closed",
            _history_source="task_board_close",
            _history_reason=reason,
        )
        if updated:
            return {
                "success": True,
                "task_id": task_id,
                "status": "done_main",
                "closed": True,
                "reason": reason,
            }
        return {"success": False, "error": f"Failed to close task {task_id}"}

    # MARKER_191.16: bulk_close — close multiple tasks at once without git commit
    elif action == "bulk_close":
        task_ids = arguments.get("task_ids", [])
        if not task_ids:
            return {
                "success": False,
                "error": "task_ids list is required for bulk_close",
            }
        reason = arguments.get("reason", "bulk_closed")
        results = []
        for tid in task_ids:
            task = board.get_task(tid)
            if not task:
                results.append({"task_id": tid, "success": False, "error": "not found"})
                continue
            updated = board.update_task(
                tid,
                status="done_main",
                _history_event="closed",
                _history_source="task_board_bulk_close",
                _history_reason=reason,
            )
            results.append({"task_id": tid, "success": bool(updated)})
        closed_count = sum(1 for r in results if r.get("success"))
        return {
            "success": True,
            "closed_count": closed_count,
            "total": len(task_ids),
            "results": results,
        }

    # MARKER_198.STALE: Stale detection — find pending tasks already implemented
    elif action == "stale_check":
        limit = int(arguments.get("limit", 50))
        auto_close = arguments.get("auto_close", False)
        if isinstance(auto_close, str):
            auto_close = auto_close.lower() in ("true", "1", "yes")
        return board.stale_check(limit=limit, auto_close=auto_close)

    # MARKER_199.BATCH: Batch merge — merge multiple done_worktree tasks in one call
    elif action == "batch_merge":
        task_ids = arguments.get("task_ids", [])
        strategy = arguments.get("strategy")
        if not task_ids:
            # Auto-collect all done_worktree tasks if no IDs specified
            done_wt = board.get_queue(status="done_worktree")
            task_ids = [t["id"] for t in done_wt]
            if not task_ids:
                return {
                    "success": True,
                    "message": "No done_worktree tasks to merge",
                    "merged_count": 0,
                }

        results = []
        merged = 0
        failed = 0
        import asyncio

        for tid in task_ids:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        merge_result = pool.submit(
                            asyncio.run, board.merge_request(tid, strategy=strategy)
                        ).result()
                else:
                    merge_result = loop.run_until_complete(
                        board.merge_request(tid, strategy=strategy)
                    )
                results.append({"task_id": tid, **merge_result})
                if merge_result.get("success"):
                    merged += 1
                else:
                    failed += 1
            except Exception as e:
                results.append({"task_id": tid, "success": False, "error": str(e)})
                failed += 1

        return {
            "success": True,
            "merged_count": merged,
            "failed_count": failed,
            "total": len(task_ids),
            "results": results,
        }

    # MARKER_199.FTS5: Full-text search across tasks
    elif action == "search_fts":
        query = arguments.get("query", "")
        if not query:
            return {"success": False, "error": "query is required for search_fts"}
        limit = int(arguments.get("limit", 20))
        results = board.search_fts(query, limit)
        return {
            "success": True,
            "results": results,
            "count": len(results),
            "query": query,
        }

    elif action == "backfill_fts":
        board = _get_board()
        count = board._backfill_fts()
        return {
            "success": True,
            "indexed": count,
            "message": f"FTS5 index rebuilt: {count} tasks indexed",
        }

    elif action == "backfill_fts":
        board = _get_board()
        count = board._backfill_fts()
        return {"success": True, "indexed": count, "message": f"FTS5 index rebuilt: {count} tasks indexed"}

    # MARKER_199.DEBRIEF: List tasks auto-closed without debrief
    elif action == "debrief_skipped":
        limit = int(arguments.get("limit", 10))
        skipped = board.get_debrief_skipped_tasks(limit)
        return {"success": True, "skipped": skipped, "count": len(skipped)}

    # ── MARKER_200.AGENT_WAKE: Notification inbox ──────────

    elif action == "notify":
        target_role = arguments.get("target_role") or arguments.get("role")
        message = arguments.get("message", "")
        if not target_role or not message:
            return {"success": False, "error": "notify requires target_role and message"}
        return board.notify(
            target_role,
            message,
            ntype=arguments.get("ntype", "custom"),
            source_role=arguments.get("source_role", arguments.get("assigned_to", "")),
            task_id=arguments.get("task_id", ""),
        )

    elif action == "notifications":
        role = arguments.get("role", "") or arguments.get("target_role", "")
        if not role:
            return {"success": False, "error": "notifications requires role"}
        unread_only = arguments.get("unread_only", True)
        if isinstance(unread_only, str):
            unread_only = unread_only.lower() not in ("false", "0", "no")
        limit = int(arguments.get("limit", 20))
        notifs = board.get_notifications(role, unread_only=unread_only, limit=limit)
        return {"success": True, "notifications": notifs, "count": len(notifs), "role": role}

    elif action == "ack_notifications":
        role = arguments.get("role", "") or arguments.get("target_role", "")
        if not role:
            return {"success": False, "error": "ack_notifications requires role"}
        notif_ids = arguments.get("notification_ids")
        if isinstance(notif_ids, str):
            notif_ids = [n.strip() for n in notif_ids.split(",") if n.strip()]
        return board.ack_notifications(role, notification_ids=notif_ids)

    else:
        return {"success": False, "error": f"Unknown action: {action}"}


def _inject_debrief(result: dict, arguments: dict) -> None:
    """MARKER_195.22: Always inject debrief questions on successful complete.

    Previous version (195.21) depended on session_tracker state which breaks
    on worktrees (MCP subprocess starts before code update, singleton resets
    on reload, etc.). Simplified: always inject. Agent decides whether to answer.
    """
    if not result.get("success"):
        return
    result["debrief_requested"] = True
    result["debrief_questions"] = {
        "q1_bugs": (
            "What's broken? Bugs you noticed — including outside your zone. "
            "Stale code, broken tools, bad process that everyone walks past?"
        ),
        "q2_worked": (
            "What unexpectedly worked? A workaround or pattern worth making standard?"
        ),
        "q3_idea": (
            "What idea came to mind that nobody asked about? "
            "What would you do with 2 more hours?"
        ),
    }

    # MARKER_200.DECISIONS: Route explicit decisions to ENGRAM L1 (permanent, category=architecture)
    # Replaces HERMES LLM-based "Key Decisions" extraction — zero LLM cost.
    _decisions = arguments.get("decisions")
    if _decisions and isinstance(_decisions, list):
        try:
            from src.memory.engram_cache import get_engram_cache
            from src.services.session_tracker import get_session_tracker

            _engram = get_engram_cache()
            _d_sid = arguments.get("session_id") or "default"
            _d_role = get_session_tracker().get_role(_d_sid)
            _d_callsign = (_d_role or {}).get("callsign", arguments.get("role", "unknown"))
            _d_domain = (_d_role or {}).get("domain", arguments.get("domain", "unknown"))
            _d_task_id = arguments.get("task_id") or result.get("task_id", "")

            for i, decision in enumerate(_decisions):
                if not isinstance(decision, str) or not decision.strip():
                    continue
                _d_key = f"{_d_callsign}::decision::{_d_domain}::{_d_task_id}"
                if len(_decisions) > 1:
                    _d_key += f"::{i}"
                _engram.put(
                    key=_d_key,
                    value=decision.strip()[:300],
                    category="architecture",
                    match_count=0,
                )
            result["decisions_captured"] = len([d for d in _decisions if isinstance(d, str) and d.strip()])
        except Exception:
            pass  # Decision capture is best-effort

    # MARKER_196.6.3: Passive metrics — auto-create ExperienceReport without agent input
    # Collects: session role, tasks completed, files touched, CORTEX tool stats.
    # Even if agent never answers debrief Qs, we get a baseline report.
    # MARKER_199.PERF: Fire-and-forget in daemon thread — debrief pipeline has sync HTTP
    # calls to Ollama+Qdrant (~300-2500ms) that should never block action=complete response.
    # MARKER_199.DAEMON_ISOLATE: Pre-fetch task metadata in main thread so daemon
    # never touches task_board. Prevents SQLite lock contention on shared singleton.
    import threading

    _task_meta_prefetch = None
    task_id = arguments.get("task_id") or result.get("task_id", "")
    if task_id:
        try:
            from src.orchestration.task_board import get_task_board
            _tb = get_task_board()
            _task_meta_prefetch = _tb.get_task(task_id)
        except Exception:
            pass

    def _bg_passive_report():
        try:
            _create_passive_experience_report(arguments, result, _task_meta_prefetch)
        except Exception as e:
            logger.warning("[Debrief] passive report failed (non-fatal): %s", e)

    threading.Thread(target=_bg_passive_report, daemon=True, name="debrief-passive").start()
    result["passive_report"] = True  # optimistic — thread will log if it fails

    # MARKER_200.STM_AUTOSAVE: Persist STM on complete (session milestone)
    try:
        from src.memory.stm_buffer import get_stm_buffer
        _stm = get_stm_buffer()
        if len(_stm) > 0:
            _stm.save_to_disk()
            logger.debug(f"[TaskBoard] STM auto-saved on complete: {len(_stm)} entries")
    except Exception:
        pass  # STM save is best-effort

    # MARKER_200.W0.4: Write CORTEX top tools to AURA as tool_usage_patterns.
    # REFLEX signal 4 (weight 0.07) reads user_preferences.tool_usage_patterns
    # but nothing ever wrote to it — signal was always zero.
    try:
        from src.services.reflex_feedback import get_feedback_store
        from src.memory.aura_store import get_aura_store
        _fb = get_feedback_store()
        _summary = _fb.get_feedback_summary()
        _per_tool = _summary.get("per_tool", {})
        if _per_tool:
            _top_tools = sorted(
                _per_tool.keys(),
                key=lambda t: _per_tool[t].get("count", 0),
                reverse=True,
            )[:5]
            _aura = get_aura_store()
            _aura.set_preference(
                agent_type="default",
                user_id="default",
                category="tool_usage_patterns",
                key="frequent_tools",
                value=_top_tools,
                confidence=0.8,
            )
            logger.debug(f"[TaskBoard] AURA tool_usage_patterns updated: {_top_tools}")
    except Exception:
        pass  # AURA write is best-effort


def _create_passive_experience_report(
    arguments: dict, result: dict, task_meta: dict = None,
) -> bool:
    """MARKER_196.6.3 / MARKER_198.DEBRIEF: Auto-create ExperienceReport from passive session data.

    Collects metrics without requiring agent input:
    - Role/domain from session tracker
    - Task ID from completion
    - Files touched from session tracker
    - CORTEX tool success rates from REFLEX

    Fix 3/4 (MARKER_198.DEBRIEF): agent callsign resolution priority:
      1. session tracker role_callsign (if session_init was called in this process lifetime)
      2. arguments["assigned_to"] (passed by agent on action=complete)
      3. task["assigned_to"] from the board (survives process restarts — stored on disk)
      4. "unknown" as final fallback

    MARKER_199.DAEMON_ISOLATE: task_meta is pre-fetched by caller in main thread.
    This function MUST NOT import or access TaskBoard — it runs in a daemon thread
    and would cause SQLite lock contention on the shared singleton connection.

    Returns True if report was created.
    """
    import time as _t
    from datetime import datetime, timezone

    _tracker_sid = arguments.get("session_id") or "mcp_default"
    task_id = arguments.get("task_id") or result.get("task_id", "")

    # Get session state
    from src.services.session_tracker import get_session_tracker

    tracker = get_session_tracker()
    session = tracker.get_session(_tracker_sid)

    # MARKER_198.DEBRIEF Fix 3/4: Resolve callsign with board task as fallback.
    # Session tracker role is lost on subprocess restart — task.assigned_to persists on disk.
    # MARKER_199.DAEMON_ISOLATE: task_meta pre-fetched by caller, no TaskBoard access here.
    task_assigned_to = ""
    if task_meta:
        task_assigned_to = task_meta.get("assigned_to", "") or ""

    callsign = (
        session.role_callsign
        or arguments.get("assigned_to")
        or task_assigned_to
        or "unknown"
    )
    domain = session.role_domain or ""
    branch = session.role_branch or arguments.get("branch") or ""

    # Build passive report
    from src.services.experience_report import ExperienceReport, get_experience_store

    # MARKER_196.6.1 / MARKER_198.DEBRIEF Fix 4/4: Collect debrief answers from arguments.
    # q1_bugs → lessons + bugs_found (also directly routed to CORTEX below)
    # q2_worked → lessons (what worked / patterns)
    # q3_idea → recommendations
    q1 = arguments.get("q1_bugs") or arguments.get("q1") or ""
    q2 = arguments.get("q2_worked") or arguments.get("q2") or ""
    q3 = arguments.get("q3_idea") or arguments.get("q3") or ""

    lessons = []
    recommendations = []
    bugs = []
    if q1:
        bugs.append({"description": q1, "source": "debrief_q1"})
        lessons.append(f"[BUG] {q1}")
    if q2:
        lessons.append(f"[WORKED] {q2}")
    if q3:
        recommendations.append(q3)

    report = ExperienceReport(
        session_id=_tracker_sid,
        agent_callsign=callsign,
        domain=domain,
        branch=branch,
        timestamp=datetime.now(timezone.utc).isoformat(),
        tasks_completed=[task_id] if task_id else [],
        files_touched=list(session.files_edited)[:20],  # cap
        commits=session.tasks_completed,
        lessons_learned=lessons,
        recommendations=recommendations,
        bugs_found=bugs,
    )

    # Enrich with CORTEX tool stats
    try:
        from src.services.reflex_feedback import get_reflex_feedback
        fb = get_reflex_feedback()
        summary = fb.get_feedback_summary()
        if summary and summary.get("total_entries", 0) > 0:
            report.reflex_summary = {
                "total_entries": summary["total_entries"],
                "success_rate": summary.get("success_rate", 0),
                "useful_rate": summary.get("useful_rate", 0),
                "top_tools": list(summary.get("per_tool", {}).keys())[:5],
            }
    except Exception:
        pass

    store = get_experience_store()
    store.submit(report)

    # MARKER_198.P1.7: Direct Qdrant L2 ingest — debrief + experience → Qdrant.
    # This is the missing link: MCP path never called resource_learnings.
    # Flow: debrief text → sync Gemma embedding → Qdrant L2 upsert → fallback to JSON.
    # ENGRAM L2→L1 auto-promotion (P0.4) triggers on search via get_learnings_for_architect().
    try:
        from src.orchestration.resource_learnings import get_learning_store

        _l2_store = get_learning_store()
        _files = list(session.files_edited)[:20]
        _stored_ids = []

        # Get task metadata for richer learning context
        # MARKER_199.DAEMON_ISOLATE: use pre-fetched task_meta, no TaskBoard access
        # MARKER_199.DAEMON_ISOLATE: use pre-fetched task_meta, no TaskBoard access
        _task_title = ""
        _task_desc = ""
        if task_meta:
            _task_title = task_meta.get("title", "")
            _task_desc = task_meta.get("description", "")

        # 1. Co-change pattern learning (which files change together)
        if _files and len(_files) >= 2:
            _dirs = set()
            for _f in _files[:10]:
                _parts = Path(_f).parts
                if len(_parts) >= 2:
                    _dirs.add(
                        _parts[-2] if _parts[-2] != "src" else "/".join(_parts[-3:-1])
                    )
            if _dirs:
                _cochange_text = (
                    f"Files that change together for '{_task_title[:50]}': "
                    f"{', '.join(f[:60] for f in _files[:5])}. "
                    f"Directories involved: {', '.join(_dirs)}."
                )
                _pid = _l2_store.store_learning_sync(
                    text=_cochange_text,
                    category="pattern",
                    run_id=_tracker_sid,
                    task_id=task_id,
                    session_id=_tracker_sid,
                    files=_files[:10],
                    metadata={"source": "mcp_complete", "agent": callsign},
                )
                if _pid:
                    _stored_ids.append(_pid)

        # 2. Task completion pattern
        if _task_title and _files:
            _completion_text = (
                f"Task '{_task_title[:60]}' completed by {callsign}, "
                f"modifying {len(_files)} files. "
                f"Approach: {_task_desc[:100] if _task_desc else 'MCP agent pipeline'}."
            )
            _pid = _l2_store.store_learning_sync(
                text=_completion_text,
                category="optimization",
                run_id=_tracker_sid,
                task_id=task_id,
                session_id=_tracker_sid,
                files=_files[:5],
                metadata={"source": "mcp_complete", "agent": callsign},
            )
            if _pid:
                _stored_ids.append(_pid)

        # 3. Debrief answers as individual Qdrant L2 learnings
        if q1:
            _pid = _l2_store.store_learning_sync(
                text=f"[BUG] {q1}",
                category="pitfall",
                task_id=task_id,
                session_id=_tracker_sid,
                files=_files[:5],
                metadata={"source": "debrief_q1", "agent": callsign},
            )
            if _pid:
                _stored_ids.append(_pid)
        if q2:
            _pid = _l2_store.store_learning_sync(
                text=f"[WORKED] {q2}",
                category="pattern",
                task_id=task_id,
                session_id=_tracker_sid,
                files=_files[:5],
                metadata={"source": "debrief_q2", "agent": callsign},
            )
            if _pid:
                _stored_ids.append(_pid)
        if q3:
            _pid = _l2_store.store_learning_sync(
                text=f"[IDEA] {q3}",
                category="architecture",
                task_id=task_id,
                session_id=_tracker_sid,
                files=_files[:5],
                metadata={"source": "debrief_q3", "agent": callsign},
            )
            if _pid:
                _stored_ids.append(_pid)

        if _stored_ids:
            logger.info(
                f"[P1.7] Qdrant L2 ingest: {len(_stored_ids)} learnings for task {task_id} "
                f"(agent={callsign})"
            )
    except Exception as e:
        logger.warning(f"[P1.7] Qdrant L2 ingest failed (non-blocking): {e}")

    # MARKER_198.DEBRIEF Fix 4/4: Direct CORTEX/ENGRAM routing for q1/q2/q3.
    # smart_debrief._route_to_memory() uses regex triggers — short answers with no
    # keywords skip all branches and fall through to CORTEX general fallback ONLY IF
    # no other branch fired. Ensure debrief answers ALWAYS reach memory regardless
    # of whether regex patterns match.
    #
    # Routing contract:
    #   q1_bugs  → CORTEX (tool failure patterns) + ENGRAM (danger entry)
    #   q2_worked → ENGRAM (pattern/architecture entry)
    #   q3_idea   → ENGRAM (pattern entry)
    if q1 or q2 or q3:
        try:
            from src.services.reflex_feedback import get_reflex_feedback
            from src.memory.engram_cache import get_engram_cache

            fb = get_reflex_feedback()
            engram = get_engram_cache()
            _agent_tag = callsign or "unknown"
            _domain_tag = domain or "research"
            _session_tag = _tracker_sid

            if q1:
                # q1_bugs → CORTEX: record as negative signal for __debrief_bug__ pseudo-tool
                try:
                    fb.record(
                        tool_id="__debrief_bug__",
                        success=False,
                        useful=False,
                        phase_type=_domain_tag,
                        agent_role=_agent_tag,
                        execution_time_ms=0.0,
                        subtask_id=task_id,
                        extra={
                            "source": "debrief_q1",
                            "text": q1[:300],
                            "agent": _agent_tag,
                        },
                    )
                except Exception:
                    pass
                # q1_bugs → ENGRAM: danger/anti-pattern entry
                try:
                    engram.put(
                        key=f"{_agent_tag}::debrief::bug::{_session_tag}",
                        value=q1[:500],
                        category="danger",
                        source_learning_id=f"debrief_q1:{_session_tag}",
                        match_count=0,
                    )
                except Exception:
                    pass

            if q2:
                # q2_worked → ENGRAM: architecture/pattern entry
                try:
                    engram.put(
                        key=f"{_agent_tag}::debrief::worked::{_session_tag}",
                        value=q2[:500],
                        category="architecture",
                        source_learning_id=f"debrief_q2:{_session_tag}",
                        match_count=0,
                    )
                except Exception:
                    pass

            if q3:
                # q3_idea → ENGRAM: pattern/idea entry
                try:
                    engram.put(
                        key=f"{_agent_tag}::debrief::idea::{_session_tag}",
                        value=q3[:500],
                        category="pattern",
                        source_learning_id=f"debrief_q3:{_session_tag}",
                        match_count=0,
                    )
                except Exception:
                    pass
        except Exception:
            pass  # Direct routing never blocks completion

    return True


# MARKER_197: _detect_git_branch() removed — branch now comes from session role (196.2.2)
# plus AgentRegistry auto-infer in complete action. No subprocess git calls needed.


def _flag_cross_domain_violations(
    board, task_id: str, task: dict, ownership_warnings: list, agent_callsign: str = ""
) -> None:
    """MARKER_197.OWNERSHIP: Record ownership violations in task history + alert Commander.

    Called after task completion when ownership_warnings is non-empty.
    Two effects:
    1. Appends an 'ownership_violation' event to the completed task's status_history
    2. Creates a P2 alert task assigned to Commander for review

    Never raises — violations are informational, not blocking.
    """
    if not ownership_warnings:
        return

    try:
        # 1. Record in task history
        board._append_history(
            task,
            event="ownership_violation",
            status=task.get("status", "done_worktree"),
            agent_name=agent_callsign or task.get("assigned_to", "unknown"),
            source="ownership_guard",
            reason=f"{len(ownership_warnings)} file(s) outside owned paths",
            extra={"warnings": ownership_warnings[:20]},  # cap at 20 to avoid bloat
        )
        board._save()

        # 2. Create Commander alert task
        alert_title = f"OWNERSHIP-ALERT: {agent_callsign or 'agent'} touched {len(ownership_warnings)} cross-domain file(s) in {task_id}"
        board.add_task(
            title=alert_title,
            description=(
                f"Agent '{agent_callsign}' completed task '{task.get('title', task_id)}' "
                f"but modified files outside their owned_paths.\n\n"
                f"Violations:\n" + "\n".join(f"- {w}" for w in ownership_warnings[:20])
            ),
            priority=2,
            phase_type="fix",
            project_id=task.get("project_id", "CUT"),
            tags=["ownership-alert", "cross-domain", "auto-generated"],
            role="Commander",
            domain="architect",
        )
        logger.warning(
            "[TaskBoard] OWNERSHIP ALERT: %s violated %d path(s) in %s — Commander task created",
            agent_callsign,
            len(ownership_warnings),
            task_id,
        )
    except Exception as e:
        logger.debug("[TaskBoard] Cross-domain flagging failed (non-critical): %s", e)


def _try_auto_commit(
    task_id: str,
    task: dict,
    commit_message: str = None,
    cwd: str = None,
    override_closure_files: list = None,
) -> dict:
    """MARKER_181.4: Auto-commit via GitCommitTool.execute().
    MARKER_188.2: Accept cwd override for worktree auto-commit.
    MARKER_195.22: Accept override_closure_files from MCP arguments.

    Same pattern as run_closure_protocol (task_board.py:1103).
    GitCommitTool.execute() IS the full pipeline: stage → commit → digest → auto-close.

    Scoped staging priority: override_closure_files > task.closure_files > allowed_paths > all dirty.
    Never git add -A.

    Returns: {attempted, success, hash, message, error, note}
    """
    import subprocess
    from pathlib import Path

    # MARKER_199.ALREADY_CLOSED: Skip auto-commit if task was already closed
    # (e.g., by vetka_git_commit post-hook). Prevents dirty-files error on re-complete.
    task_status = task.get("status", "")
    if task_status.startswith("done") or task_status in ("verified", "cancelled"):
        return {"attempted": False, "success": True, "hash": task.get("commit_hash"),
                "note": f"task already {task_status}, skip auto-commit"}

    PROJECT_ROOT = Path(cwd) if cwd else Path(__file__).resolve().parents[3]

    # MARKER_178.FIX_INDEXLOCK: Clean stale index.lock before git operations
    # After a failed commit, index.lock can remain and block all git operations
    try:
        git_dir_result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if git_dir_result.returncode == 0:
            git_dir = Path(git_dir_result.stdout.strip())
            if not git_dir.is_absolute():
                git_dir = PROJECT_ROOT / git_dir
            lock_file = git_dir / "index.lock"
            if lock_file.exists():
                # Check if lock is stale (older than 60 seconds)
                import time

                lock_age = time.time() - lock_file.stat().st_mtime
                if lock_age > 60:
                    lock_file.unlink()
                    logger.warning(
                        f"[TaskBoard] Removed stale index.lock (age: {lock_age:.0f}s)"
                    )
                else:
                    return {
                        "attempted": False,
                        "success": False,
                        "error": f"Git index.lock exists (age: {lock_age:.0f}s). Another git operation in progress.",
                    }
    except Exception:
        pass  # Non-fatal — proceed with commit attempt

    # 1. Check if there are changes to commit
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as e:
        return {
            "attempted": False,
            "success": False,
            "error": f"git status failed: {e}",
        }

    if not status.stdout.strip():
        # Case C: nothing to commit — OK for research tasks
        return {
            "attempted": False,
            "success": True,
            "hash": None,
            "message": None,
            "note": "nothing to commit",
        }

    # 2. Determine scoped files (NOT git add -A)
    # MARKER_195.22: Scoped staging — override > task.closure_files > allowed_paths > all dirty
    closure_files = [
        str(p)
        for p in (override_closure_files or task.get("closure_files") or [])
        if str(p).strip()
    ]
    allowed_paths = [
        str(p) for p in (task.get("allowed_paths") or []) if str(p).strip()
    ]

    # Parse ALL dirty files from porcelain
    all_changed = []
    for line in status.stdout.splitlines():
        if len(line) > 3:
            filepath = line[3:].split(" -> ")[-1].strip()
            if filepath:
                all_changed.append(filepath)

    if closure_files:
        # Explicit closure_files — use as-is (may include files not in porcelain)
        pass
    elif allowed_paths:
        # MARKER_195.22: Filter dirty files by allowed_paths prefixes
        # allowed_paths can be files ("src/foo.py") or dirs ("src/mcp/tools/")
        def _matches_allowed(fpath):
            for ap in allowed_paths:
                if fpath == ap or fpath.startswith(ap.rstrip("/") + "/"):
                    return True
            return False

        closure_files = [f for f in all_changed if _matches_allowed(f)]
        if not closure_files:
            # allowed_paths set but no dirty files match — warn, don't grab everything
            return {
                "attempted": False,
                "success": False,
                "error": f"No dirty files match allowed_paths {allowed_paths}. "
                f"Dirty files: {all_changed[:10]}. "
                "Set closure_files explicitly or update allowed_paths.",
            }
    else:
        # No scope at all — fallback to all dirty, but log warning
        closure_files = all_changed
        if len(all_changed) > 5:
            logger.warning(
                f"[TaskBoard] _try_auto_commit: no closure_files/allowed_paths for task {task_id}, "
                f"staging ALL {len(all_changed)} dirty files. Consider setting allowed_paths on task."
            )

    # MARKER_200.NEVER_STAGE: Filter out generated artifacts that must never be committed.
    # CLAUDE.md is auto-regenerated by generate_claude_md.py on every session_init.
    # Once tracked, .gitignore cannot protect it — this is the hard exclusion gate.
    _NEVER_STAGE = {"CLAUDE.md", ".agent_lock"}
    _before = len(closure_files)
    closure_files = [f for f in closure_files if Path(f).name not in _NEVER_STAGE]
    if len(closure_files) < _before:
        logger.info(
            "[TaskBoard] NEVER_STAGE: filtered %d artifact(s) from staging",
            _before - len(closure_files),
        )

    if not closure_files:
        return {
            "attempted": False,
            "success": True,
            "hash": None,
            "note": "no changed files found",
        }

    # 3. Build commit message with [task:tb_xxxx]
    task_title = task.get("title", "task")
    auto_msg = commit_message or f"complete: {task_title} [task:{task_id}]"
    if f"[task:{task_id}]" not in auto_msg:
        auto_msg += f" [task:{task_id}]"

    # 4. GitCommitTool.execute() — the ACTUAL pipeline
    try:
        from src.mcp.tools.git_tool import GitCommitTool

        tool = GitCommitTool()
        exec_args = {
            "message": auto_msg,
            "files": closure_files,
            "dry_run": False,
            "auto_push": False,
        }
        if cwd:
            exec_args["cwd"] = cwd
        result = tool.execute(exec_args)
    except Exception as e:
        logger.error(f"[TaskBoard] _try_auto_commit failed: {e}")
        return {"attempted": True, "success": False, "error": str(e)[:200]}

    if not result.get("success"):
        error = result.get("error", "unknown")
        if "nothing to commit" in str(error).lower():
            return {
                "attempted": False,
                "success": True,
                "hash": None,
                "note": "nothing to commit",
            }
        return {
            "attempted": True,
            "success": False,
            "error": error,
            "message": auto_msg,
        }

    result_data = result.get("result", {})
    logger.info(f"[TaskBoard] Auto-commit {result_data.get('hash')}: {auto_msg[:60]}")
    return {
        "attempted": True,
        "success": True,
        "hash": result_data.get("hash"),
        "message": auto_msg,
    }


# ==========================================
# Tool 2: vetka_task_dispatch
# ==========================================

TASK_DISPATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {
            "type": "string",
            "description": "Task ID to dispatch. If omitted, dispatches highest-priority task.",
        },
        "chat_id": {
            "type": "string",
            "description": "Chat ID for progress streaming (optional)",
        },
    },
}


async def handle_task_dispatch(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle vetka_task_dispatch MCP tool calls.

    Dispatches a task (or next available) to the Mycelium pipeline.
    """
    from src.orchestration.task_board import get_task_board

    board = get_task_board()
    task_id = arguments.get("task_id")
    chat_id = arguments.get("chat_id")

    if task_id:
        result = await board.dispatch_task(task_id, chat_id=chat_id)
    else:
        result = await board.dispatch_next(chat_id=chat_id)

    return result


# ==========================================
# Tool 3: vetka_task_import
# ==========================================

TASK_IMPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {"type": "string", "description": "Path to todo file to import"},
        "source_tag": {
            "type": "string",
            "description": "Source tag for imported tasks (e.g., 'dragon_todo', 'titan_todo')",
        },
    },
    "required": ["file_path"],
}


def handle_task_import(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle vetka_task_import MCP tool calls.

    Imports tasks from a todo text file into the task board.
    """
    from src.orchestration.task_board import get_task_board

    file_path = arguments.get("file_path")
    if not file_path:
        return {"success": False, "error": "file_path is required"}

    source_tag = arguments.get("source_tag", "imported")
    board = get_task_board()
    count = board.import_from_todo(file_path, source_tag)

    return {
        "success": count > 0,
        "imported_count": count,
        "file": file_path,
        "source_tag": source_tag,
        "total_tasks": len(board.tasks),
    }
