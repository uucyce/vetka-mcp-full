"""
Task Board MCP Tools — Phase 121

Three MCP tools for managing the Task Board:
1. vetka_task_board  — CRUD + list + summary
2. vetka_task_dispatch — dispatch tasks to pipeline
3. vetka_task_import — import from todo files

TODO MARKER_126.11C: Add fourth tool:
4. vetka_task_claim — claim/release tasks for external agents
   - action: "claim" | "release" | "my_tasks"
   - Enables Claude Code, Grok, etc. to claim tasks without Mycelium

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


def _load_docs_content_sync(
    task: Dict[str, Any],
    budget: int = 8192,   # MARKER_197.SLIM: Reduced from 65536 to 8192 to cut token bloat
    per_doc: int = 4096,  # MARKER_197.SLIM: Reduced from 16384 to 4096 to cut token bloat
) -> str:
    """MARKER_191.7: Read architecture_docs + recon_docs file contents synchronously.

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
        for doc_ref in (task.get(field) or []):
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

        full_path = _PROJECT_ROOT / doc_ref
        if not full_path.exists():
            full_path = _PROJECT_ROOT / doc_ref.lstrip("/")
        if not full_path.exists():
            docs_skipped.append(f"{doc_ref} (not found)")
            continue

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            if len(content) > per_doc:
                content = content[:per_doc] + f"\n... [truncated, {len(content)} total chars]"

            remaining = budget - total_chars
            if len(content) > remaining:
                content = content[:remaining] + "\n... [budget exceeded]"

            sections.append(f"### {doc_ref} ({field})\n{content}")
            total_chars += len(content)
            docs_included += 1
        except Exception as e:
            docs_skipped.append(f"{doc_ref} (error: {e})")

    if not sections:
        return ""

    header = f"--- DOCS ({docs_included} files"
    if docs_skipped:
        header += f", {len(docs_skipped)} skipped"
    header += ") ---\n"
    footer = "\n--- END DOCS ---"

    return header + "\n\n".join(sections) + footer


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
            "enum": ["add", "list", "get", "update", "remove", "summary", "claim", "complete", "active_agents", "merge_request", "promote_to_main", "request_qa", "verify"],
            "description": "Operation to perform"
        },
        # For "add":
        "title": {"type": "string", "description": "Task title (required for add)"},
        "description": {"type": "string", "description": "Detailed task description — free text for context, problem statement, approach"},
        "profile": {"type": "string", "enum": ["p6"], "description": "Task intake profile with protocol defaults"},
        "priority": {"type": "number", "description": "1=critical, 2=high, 3=medium, 4=low, 5=someday"},
        "phase_type": {"type": "string", "enum": ["build", "fix", "research", "test"], "description": "Task type"},
        "complexity": {"type": "string", "enum": ["low", "medium", "high"], "description": "Estimated complexity"},
        "preset": {"type": "string", "description": "Pipeline preset override"},
        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
        "dependencies": {"type": "array", "items": {"type": "string"}, "description": "Task IDs that must complete first"},
        "project_id": {"type": "string", "description": "Logical project ID. For add: assigns project. For list: smart filter — case-insensitive, RU keyboard layout auto-fix, prefix autocomplete (e.g. 'c'→'cut', 'СГЕ'→'CUT')."},
        "project_lane": {"type": "string", "description": "Specific multitask lane/MCC tab identifier"},
        "architecture_docs": {"type": "array", "items": {"type": "string"}, "description": "Architecture docs linked to the task"},
        "recon_docs": {"type": "array", "items": {"type": "string"}, "description": "Recon docs linked to the task"},
        # MARKER_191.6: Structured task fields — discoverable by agents at tool discovery time
        "allowed_paths": {"type": "array", "items": {"type": "string"}, "description": "Target files/directories this task should modify. Also serves as ownership guard — agent should not touch files outside this list. Example: ['src/orchestration/task_board.py', 'src/mcp/tools/']"},
        "completion_contract": {"type": "array", "items": {"type": "string"}, "description": "Acceptance criteria checklist. Each item = one verifiable condition the agent must satisfy. Example: ['API returns 200 on valid input', 'unit tests pass', 'no console errors in browser']"},
        "implementation_hints": {"type": "string", "description": "Algorithm hints, approach notes, or technical guidance for the implementing agent. Free text. Example: 'Use re.search with word boundary, not substring match. Check _commit_matches_task for the pattern.'"},
        # MARKER_ZETA.D4: Agent role/domain binding fields
        "role": {"type": "string", "description": "Agent callsign from agent_registry.yaml: Alpha, Beta, Gamma, Delta, Commander"},
        "domain": {"type": "string", "description": "Task domain from agent_registry.yaml: engine, media, ux, qa, architect"},
        "closure_tests": {"type": "array", "items": {"type": "string"}, "description": "Shell commands required for closure proof. Example: ['python -m pytest tests/test_task_board.py -v', 'python -c \"import ast; ast.parse(open(f).read())\"']"},
        "closure_files": {"type": "array", "items": {"type": "string"}, "description": "Files allowed for scoped auto-commit at task completion. If set, only these files are staged."},
        # MARKER_130.C16B: Agent assignment fields
        "assigned_to": {"type": "string", "description": "Agent name: opus, cursor, dragon, grok"},
        "agent_type": {"type": "string", "description": "Agent type: claude_code, cursor, mycelium, grok, human"},
        # For "get", "update", "remove", "claim", "complete":
        "task_id": {"type": "string", "description": "Task ID (required for get/update/remove/claim/complete)"},
        # For "update":
        "status": {"type": "string", "enum": ["pending", "queued", "claimed", "running", "done", "done_worktree", "need_qa", "done_main", "failed", "cancelled", "verified", "needs_fix"]},
        # For "verify":
        "verdict": {"type": "string", "enum": ["pass", "fail"], "description": "QA verdict for action=verify: pass → verified, fail → needs_fix"},
        "verified_by": {"type": "string", "description": "Agent performing verification (default: Delta)"},
        "notes": {"type": "string", "description": "Verification notes (for verify action)"},
        # For "list":
        "filter_status": {"type": "string", "description": "Filter by status (optional for list)"},
        "limit": {"type": "number", "description": "Max tasks to return in list (default: 40, max: 100)"},
        # MARKER_190.DOC_GATE: Force-create task without docs (bypass doc gate)
        "force_no_docs": {"type": "boolean", "description": "Bypass doc requirement gate. Use only when truly no relevant docs exist."},
        # For "update" / "complete":
        "branch_name": {"type": "string", "description": "Git branch name (e.g. claude/cut-engine). Saved on complete, needed by merge_request."},
        "commit_hash": {"type": "string", "description": "Git commit hash (for complete/promote_to_main)"},
        "commit_message": {"type": "string", "description": "Commit message (for complete)"},
        # MARKER_186.4: Branch name for worktree-aware completion
        "branch": {"type": "string", "description": "Git branch name (for complete). If on worktree branch, status=done_worktree. If omitted, auto-detects."},
        # MARKER_188.2: Worktree path for auto-commit from worktree context
        "worktree_path": {"type": "string", "description": "Absolute path to worktree root. Required for auto-commit when agent runs in a worktree."},
        # MARKER_192.2: execution_mode — controls closure proof requirements
        "execution_mode": {"type": "string", "enum": ["pipeline", "manual"], "description": "Closure proof mode. 'pipeline' = full proof (pipeline_success + verifier + tests). 'manual' = relaxed (commit_hash only). Auto-inferred from agent_type if omitted."},
        # MARKER_196.6.1: Debrief answers captured in action=complete
        "q1_bugs": {"type": "string", "description": "Debrief Q1: What bugs did you notice? (optional, for action=complete)"},
        "q2_worked": {"type": "string", "description": "Debrief Q2: What unexpectedly worked? (optional, for action=complete)"},
        "q3_idea": {"type": "string", "description": "Debrief Q3: What idea came to mind? (optional, for action=complete)"},
    },
    "required": ["action"]
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

        params = urllib.parse.urlencode({"q": title, "limit": limit * 4, "mode": "hybrid"})
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
                logger.debug(f"[DocGate] vetka_search found {len(suggestions)} docs for: {title[:50]}")
                hybrid_results = suggestions
            else:
                hybrid_results = []
    except Exception as e:
        logger.debug(f"[DocGate] vetka_search unavailable ({e}), falling back to glob")
        hybrid_results = []

    # Strategy 2: keyword glob search in docs/ (complements hybrid with filename matching)
    import re
    keywords = [w.lower() for w in re.split(r'[\s:_\-—/]+', title) if len(w) >= 3]
    stop_words = {"bug", "fix", "arch", "the", "for", "and", "with", "new", "add", "test", "task",
                   "при", "что", "как", "это", "все", "нет", "без", "или", "показывают", "одно"}
    keywords = [k for k in keywords if k not in stop_words]

    if not keywords:
        return []

    suggestions = []
    for md_file in sorted(docs_dir.rglob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
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
    _tracker_sid = arguments.get("session_id") or "mcp_default"
    try:
        from src.services.session_tracker import get_session_tracker
        get_session_tracker().record_action(
            _tracker_sid, "vetka_task_board",
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
        arch_docs = [d for d in (payload.get("architecture_docs") or []) if str(d).strip()]
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
                    title, suggested[:3],
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
                role=payload.get("role"),        # MARKER_ZETA.D4
                domain=payload.get("domain"),    # MARKER_ZETA.D4
            )
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        result = {"success": True, "task_id": task_id, "message": f"Task '{title}' added"}
        # MARKER_196.DOCGATE: Surface warnings if force_no_docs was used
        _dg_warnings = payload.get("_doc_gate_warnings")
        if _dg_warnings:
            result["doc_gate_warning"] = _dg_warnings[0]
        return result

    elif action == "list":
        filter_status = arguments.get("filter_status")
        tasks = board.get_queue(status=filter_status)
        # MARKER_191.16: Smart project_id filter — case-insensitive, RU layout fix, prefix match
        filter_project = str(arguments.get("project_id") or "").strip()
        project_resolve = None
        if filter_project:
            tasks, project_resolve = board.filter_tasks_by_project(tasks, filter_project)
        # MARKER_189.13 + MARKER_191.4: Dynamic limit; no limit when filtering by project
        total = len(tasks)
        if filter_project and not arguments.get("limit"):
            # Filtered query without explicit limit → return all matches
            page = tasks
        else:
            max_limit = min(int(arguments.get("limit") or 40), 100)
            page = tasks[:max_limit]
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

    elif action == "update":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for update"}

        # Collect updatable fields
        updates = {}
        for field in ["title", "description", "priority", "phase_type", "complexity",
                       "preset", "status", "tags", "dependencies", "project_id",
                       "project_lane", "architecture_docs", "recon_docs",
                       "closure_tests", "closure_files",
                       "allowed_paths", "completion_contract", "implementation_hints",
                       "role", "domain", "branch_name"]:
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
                result["error"] = f"update_task returned False (possible invalid status or phase_type)"
        return result

    elif action == "remove":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for remove"}
        ok = board.remove_task(task_id)
        return {"success": ok, "message": f"Task {task_id} removed" if ok else f"Task {task_id} not found"}

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
        return result

    # MARKER_181.4: complete action — unified pipeline
    # MARKER_186.4: worktree-aware completion — detect branch, set done_worktree/done_main
    # Flow: agent → complete → detect branch → auto-commit (scoped) → digest → close task
    elif action == "complete":
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
        if not worktree_path and current_branch and current_branch.startswith("claude/"):
            from pathlib import Path
            _main_root = Path(__file__).resolve().parents[3]
            wt_name = current_branch.split("/", 1)[1]
            candidate = _main_root / ".claude" / "worktrees" / wt_name
            if candidate.exists():
                worktree_path = str(candidate)
                logger.info(f"[TaskBoard] Auto-detected worktree_path from branch: {worktree_path}")

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
                        logger.info(f"[TaskBoard] Auto-inferred branch={current_branch} from '{_cand}'")
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
                        capture_output=True, text=True, timeout=5, cwd=_ow_cwd,
                    )
                    # Also check unstaged
                    _ow_diff2 = _ow_sp.run(
                        ["git", "diff", "--name-only"],
                        capture_output=True, text=True, timeout=5, cwd=_ow_cwd,
                    )
                    _changed = set()
                    if _ow_diff.returncode == 0:
                        _changed.update(f.strip() for f in _ow_diff.stdout.splitlines() if f.strip())
                    if _ow_diff2.returncode == 0:
                        _changed.update(f.strip() for f in _ow_diff2.stdout.splitlines() if f.strip())

                    for _cf in _changed:
                        _result = _ow_reg.validate_file_ownership(_ow_role.callsign, _cf)
                        if _result.is_blocked:
                            _ownership_warnings.append(f"BLOCKED: {_cf} (pattern: {_result.matched_blocked_pattern})")
                        elif not _result.is_owned and not _result.shared_zone:
                            _ownership_warnings.append(f"NOT_OWNED: {_cf}")

                    if _ownership_warnings:
                        logger.warning(
                            "[TaskBoard] Ownership warnings for %s: %s",
                            _ow_role.callsign, _ownership_warnings,
                        )
            except Exception:
                pass  # Ownership check never blocks completion

        # Case A: agent already committed — just close
        # MARKER_195.20: Pass worktree_path for branch auto-detection fallback
        if commit_hash:
            result = board.complete_task(task_id, commit_hash, commit_message, branch=current_branch, worktree_path=worktree_path, execution_mode=exec_mode)
            if _ownership_warnings:
                result["ownership_warnings"] = _ownership_warnings
                # MARKER_197.OWNERSHIP: Flag cross-domain + alert Commander
                _flag_cross_domain_violations(board, task_id, task, _ownership_warnings, agent_callsign=_session_role.get("callsign", "") if _session_role else "")
            _inject_debrief(result, arguments)
            return result

        # MARKER_182.7: Try Verifier merge if run_id is available (Phase 182+ path)
        task_result = task.get("result") or {}
        run_id = task_result.get("run_id") if isinstance(task_result, dict) else None
        session_id = task_result.get("session_id") if isinstance(task_result, dict) else None

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
                    result = board.complete_task(task_id, merge_result["commit_hash"], merge_result.get("commit_message"), branch=current_branch, worktree_path=worktree_path, execution_mode=exec_mode)
                    result["verifier_merge"] = merge_result
                    _inject_debrief(result, arguments)
                    return result
                # If no commit_hash but success (nothing to commit) — fall through to legacy
                if merge_result.get("success"):
                    logger.info(f"[TaskBoard] Verifier merge: {merge_result.get('note', 'nothing to merge')}")
                else:
                    logger.warning(f"[TaskBoard] Verifier merge failed: {merge_result.get('error')}, falling back to legacy")
            except Exception as vm_err:
                logger.warning(f"[TaskBoard] Verifier merge exception (falling back): {vm_err}")

        # Case B/C: no commit yet — try auto-commit (legacy path)
        # MARKER_188.2: Pass worktree_path for correct cwd in git operations
        # MARKER_195.22: Pass closure_files from MCP arguments (overrides task.closure_files)
        mcp_closure_files = arguments.get("closure_files")
        auto = _try_auto_commit(task_id, task, commit_message, cwd=worktree_path,
                                override_closure_files=mcp_closure_files)

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
        result = board.complete_task(task_id, auto.get("hash"), auto.get("message"), branch=current_branch, worktree_path=worktree_path, execution_mode=exec_mode)
        result["auto_commit"] = auto

        # MARKER_196.3.1: Attach ownership warnings to result
        if _ownership_warnings:
            result["ownership_warnings"] = _ownership_warnings
            # MARKER_197.OWNERSHIP: Flag cross-domain + alert Commander
            _flag_cross_domain_violations(board, task_id, task, _ownership_warnings, agent_callsign=_session_role.get("callsign", "") if _session_role else "")

        # MARKER_195.21: Debrief injection via extracted function (was inline, bypassed on 3 paths)
        _inject_debrief(result, arguments)

        return result

    # MARKER_130.C16B: active_agents action
    elif action == "active_agents":
        agents = board.get_active_agents()
        return {"success": True, "agents": agents, "count": len(agents)}

    # MARKER_184.5: merge_request action — worktree → main merge via TaskBoard
    elif action == "merge_request":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for merge_request"}

        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(
                        asyncio.run, board.merge_request(task_id)
                    ).result()
            else:
                result = loop.run_until_complete(board.merge_request(task_id))
            return result
        except Exception as e:
            return {"success": False, "error": f"merge_request failed: {e}"}

    # MARKER_195.20c: promote_to_main — delegates to merge_request for real merge
    elif action == "promote_to_main":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for promote_to_main"}
        merge_commit_hash = arguments.get("commit_hash")
        role = arguments.get("role", "")
        return board.promote_to_main(task_id, merge_commit_hash, role=role)

    # MARKER_196.QA: request_qa — move done_worktree → need_qa
    elif action == "request_qa":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for request_qa"}
        task = board.get_task(task_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        if task["status"] != "done_worktree":
            return {"success": False, "error": f"Task {task_id} is '{task['status']}', expected done_worktree"}
        board.update_task(
            task_id, status="need_qa",
            _history_event="qa_requested",
            _history_source="task_board",
            _history_reason="QA review requested",
            _history_agent_name=arguments.get("assigned_to", ""),
        )
        return {"success": True, "task_id": task_id, "status": "need_qa", "message": "Task moved to QA queue"}

    # MARKER_195.20: QA Gate — verify a done_worktree task before merge
    elif action == "verify":
        task_id = arguments.get("task_id")
        verdict = arguments.get("verdict")  # "pass" or "fail"
        if not task_id or not verdict:
            return {"success": False, "error": "task_id and verdict ('pass' or 'fail') required for verify"}
        notes = arguments.get("notes", "")
        verified_by = arguments.get("verified_by", arguments.get("assigned_to", ""))
        return board.verify_task(task_id, verdict, notes, verified_by)

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
            "What unexpectedly worked? A workaround or pattern "
            "worth making standard?"
        ),
        "q3_idea": (
            "What idea came to mind that nobody asked about? "
            "What would you do with 2 more hours?"
        ),
    }

    # MARKER_196.6.3: Passive metrics — auto-create ExperienceReport without agent input
    # Collects: session role, tasks completed, files touched, CORTEX tool stats.
    # Even if agent never answers debrief Qs, we get a baseline report.
    try:
        _passive_report_created = _create_passive_experience_report(
            arguments, result,
        )
        if _passive_report_created:
            result["passive_report"] = True
    except Exception:
        pass  # Passive metrics never block completion


def _create_passive_experience_report(arguments: dict, result: dict) -> bool:
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
    task_assigned_to = ""
    if task_id:
        try:
            from src.orchestration.task_board import TaskBoard
            _tb = TaskBoard()
            _task_meta = _tb.get_task(task_id)
            if _task_meta:
                task_assigned_to = _task_meta.get("assigned_to", "") or ""
        except Exception:
            pass

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
        from src.services.reflex_feedback import ReflexFeedback
        fb = ReflexFeedback()
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
        _task_title = ""
        _task_desc = ""
        if task_id:
            try:
                from src.orchestration.task_board import get_task_board as _gtb
                _task_data = _gtb().get_task(task_id)
                if _task_data:
                    _task_title = _task_data.get("title", "")
                    _task_desc = _task_data.get("description", "")
            except Exception:
                pass

        # 1. Co-change pattern learning (which files change together)
        if _files and len(_files) >= 2:
            _dirs = set()
            for _f in _files[:10]:
                _parts = Path(_f).parts
                if len(_parts) >= 2:
                    _dirs.add(_parts[-2] if _parts[-2] != "src" else "/".join(_parts[-3:-1]))
            if _dirs:
                _cochange_text = (
                    f"Files that change together for '{_task_title[:50]}': "
                    f"{', '.join(f[:60] for f in _files[:5])}. "
                    f"Directories involved: {', '.join(_dirs)}."
                )
                _pid = _l2_store.store_learning_sync(
                    text=_cochange_text, category="pattern",
                    run_id=_tracker_sid, task_id=task_id, session_id=_tracker_sid,
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
                text=_completion_text, category="optimization",
                run_id=_tracker_sid, task_id=task_id, session_id=_tracker_sid,
                files=_files[:5],
                metadata={"source": "mcp_complete", "agent": callsign},
            )
            if _pid:
                _stored_ids.append(_pid)

        # 3. Debrief answers as individual Qdrant L2 learnings
        if q1:
            _pid = _l2_store.store_learning_sync(
                text=f"[BUG] {q1}", category="pitfall",
                task_id=task_id, session_id=_tracker_sid, files=_files[:5],
                metadata={"source": "debrief_q1", "agent": callsign},
            )
            if _pid:
                _stored_ids.append(_pid)
        if q2:
            _pid = _l2_store.store_learning_sync(
                text=f"[WORKED] {q2}", category="pattern",
                task_id=task_id, session_id=_tracker_sid, files=_files[:5],
                metadata={"source": "debrief_q2", "agent": callsign},
            )
            if _pid:
                _stored_ids.append(_pid)
        if q3:
            _pid = _l2_store.store_learning_sync(
                text=f"[IDEA] {q3}", category="architecture",
                task_id=task_id, session_id=_tracker_sid, files=_files[:5],
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
                        extra={"source": "debrief_q1", "text": q1[:300], "agent": _agent_tag},
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
            agent_callsign, len(ownership_warnings), task_id,
        )
    except Exception as e:
        logger.debug("[TaskBoard] Cross-domain flagging failed (non-critical): %s", e)


def _try_auto_commit(task_id: str, task: dict, commit_message: str = None, cwd: str = None,
                     override_closure_files: list = None) -> dict:
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

    PROJECT_ROOT = Path(cwd) if cwd else Path(__file__).resolve().parents[3]

    # MARKER_178.FIX_INDEXLOCK: Clean stale index.lock before git operations
    # After a failed commit, index.lock can remain and block all git operations
    try:
        git_dir_result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=5,
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
                    logger.warning(f"[TaskBoard] Removed stale index.lock (age: {lock_age:.0f}s)")
                else:
                    return {"attempted": False, "success": False,
                            "error": f"Git index.lock exists (age: {lock_age:.0f}s). Another git operation in progress."}
    except Exception:
        pass  # Non-fatal — proceed with commit attempt

    # 1. Check if there are changes to commit
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=10,
        )
    except Exception as e:
        return {"attempted": False, "success": False, "error": f"git status failed: {e}"}

    if not status.stdout.strip():
        # Case C: nothing to commit — OK for research tasks
        return {"attempted": False, "success": True, "hash": None, "message": None,
                "note": "nothing to commit"}

    # 2. Determine scoped files (NOT git add -A)
    # MARKER_195.22: Scoped staging — override > task.closure_files > allowed_paths > all dirty
    closure_files = [str(p) for p in (override_closure_files or task.get("closure_files") or []) if str(p).strip()]
    allowed_paths = [str(p) for p in (task.get("allowed_paths") or []) if str(p).strip()]

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
            return {"attempted": False, "success": False,
                    "error": f"No dirty files match allowed_paths {allowed_paths}. "
                             f"Dirty files: {all_changed[:10]}. "
                             "Set closure_files explicitly or update allowed_paths."}
    else:
        # No scope at all — fallback to all dirty, but log warning
        closure_files = all_changed
        if len(all_changed) > 5:
            logger.warning(
                f"[TaskBoard] _try_auto_commit: no closure_files/allowed_paths for task {task_id}, "
                f"staging ALL {len(all_changed)} dirty files. Consider setting allowed_paths on task."
            )

    if not closure_files:
        return {"attempted": False, "success": True, "hash": None,
                "note": "no changed files found"}

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
            return {"attempted": False, "success": True, "hash": None,
                    "note": "nothing to commit"}
        return {"attempted": True, "success": False, "error": error, "message": auto_msg}

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
            "description": "Task ID to dispatch. If omitted, dispatches highest-priority task."
        },
        "chat_id": {
            "type": "string",
            "description": "Chat ID for progress streaming (optional)"
        }
    }
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
        "file_path": {
            "type": "string",
            "description": "Path to todo file to import"
        },
        "source_tag": {
            "type": "string",
            "description": "Source tag for imported tasks (e.g., 'dragon_todo', 'titan_todo')"
        }
    },
    "required": ["file_path"]
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
        "total_tasks": len(board.tasks)
    }
