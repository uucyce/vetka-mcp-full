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
    budget: int = 65536,
    per_doc: int = 16384,
) -> str:
    """MARKER_191.7: Read architecture_docs + recon_docs file contents synchronously.

    Used by claim/get actions to inject doc content into MCP response.
    MCP agents (Claude Code, Desktop, Cursor) don't go through dispatch_task,
    so they need docs content at claim/get time.

    Args:
        task: Task dict with architecture_docs/recon_docs fields
        budget: Total chars budget (default 64KB)
        per_doc: Per-document char cap (default 16KB)

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
            "enum": ["add", "list", "get", "update", "remove", "summary", "claim", "complete", "active_agents", "merge_request", "promote_to_main", "verify"],
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
        "status": {"type": "string", "enum": ["pending", "queued", "claimed", "running", "done", "done_worktree", "done_main", "failed", "cancelled", "verified", "needs_fix"]},
        # For "verify":
        "verdict": {"type": "string", "enum": ["pass", "fail"], "description": "QA verdict for action=verify: pass → verified, fail → needs_fix"},
        "verified_by": {"type": "string", "description": "Agent performing verification (default: Delta)"},
        "notes": {"type": "string", "description": "Verification notes (for verify action)"},
        # For "list":
        "filter_status": {"type": "string", "description": "Filter by status (optional for list)"},
        "limit": {"type": "number", "description": "Max tasks to return in list (default: 40, max: 100)"},
        # MARKER_190.DOC_GATE: Force-create task without docs (bypass doc gate)
        "force_no_docs": {"type": "boolean", "description": "Bypass doc requirement gate. Use only when truly no relevant docs exist."},
        # For "complete":
        "commit_hash": {"type": "string", "description": "Git commit hash (for complete)"},
        "commit_message": {"type": "string", "description": "Commit message (for complete)"},
        # MARKER_186.4: Branch name for worktree-aware completion
        "branch": {"type": "string", "description": "Git branch name (for complete). If on worktree branch, status=done_worktree. If omitted, auto-detects."},
        # MARKER_188.2: Worktree path for auto-commit from worktree context
        "worktree_path": {"type": "string", "description": "Absolute path to worktree root. Required for auto-commit when agent runs in a worktree."},
        # MARKER_192.2: execution_mode — controls closure proof requirements
        "execution_mode": {"type": "string", "enum": ["pipeline", "manual"], "description": "Closure proof mode. 'pipeline' = full proof (pipeline_success + verifier + tests). 'manual' = relaxed (commit_hash only). Auto-inferred from agent_type if omitted."},
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
    try:
        from src.services.session_tracker import get_session_tracker
        get_session_tracker().record_action(
            "mcp_default", "vetka_task_board",
            {"action": action, "task_id": arguments.get("task_id", "")},
        )
    except Exception:
        pass

    board = get_task_board()

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

        if not arch_docs and not recon_docs and not force_no_docs and phase_type not in doc_exempt_types:
            # Build search query from title + tags for better relevance
            tags = payload.get("tags") or []
            search_query = title + " " + " ".join(str(t) for t in tags)
            suggested = _suggest_docs_for_title(search_query)
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
        return {"success": True, "task_id": task_id, "message": f"Task '{title}' added"}

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
                       "role", "domain"]:
            if field in arguments and arguments[field] is not None:
                updates[field] = arguments[field]

        if not updates:
            return {"success": False, "error": "No fields to update"}

        ok = board.update_task(task_id, **updates)
        return {"success": ok, "updated_fields": list(updates.keys())}

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

        if not current_branch:
            current_branch = _detect_git_branch(cwd=worktree_path)

        # MARKER_192.2: execution_mode override for manual agents
        exec_mode = arguments.get("execution_mode")

        # Case A: agent already committed — just close
        # MARKER_195.20: Pass worktree_path for branch auto-detection fallback
        if commit_hash:
            result = board.complete_task(task_id, commit_hash, commit_message, branch=current_branch, worktree_path=worktree_path, execution_mode=exec_mode)
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
        auto = _try_auto_commit(task_id, task, commit_message, cwd=worktree_path)

        # If commit attempted but FAILED → do NOT close task
        if auto.get("attempted") and not auto.get("success"):
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
            return {
                "success": True,
                "task_id": task_id,
                "commit_hash": auto.get("hash"),
                "note": "auto-closed by commit pipeline",
                "auto_commit": auto,
            }

        # Close task (commit succeeded or nothing to commit)
        result = board.complete_task(task_id, auto.get("hash"), auto.get("message"), branch=current_branch, worktree_path=worktree_path, execution_mode=exec_mode)
        result["auto_commit"] = auto

        # MARKER_ZETA.F1: Smart Debrief — inject questions on task complete
        try:
            from src.services.session_tracker import get_session_tracker
            _db_tracker = get_session_tracker()
            _db_sid = arguments.get("session_id", "default")
            _db_session = _db_tracker.get_session(_db_sid)
            if (
                result.get("success")
                and _db_session.tasks_completed > 0
                and not _db_session.experience_report_submitted
            ):
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
        except Exception:
            pass  # Debrief injection never blocks completion

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

    # MARKER_186.4: promote_to_main — transition done_worktree → done_main after merge
    elif action == "promote_to_main":
        task_id = arguments.get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id is required for promote_to_main"}
        merge_commit_hash = arguments.get("commit_hash")
        return board.promote_to_main(task_id, merge_commit_hash)

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



def _detect_git_branch(cwd: str = None) -> str:
    """MARKER_186.4: Detect current git branch. Works in worktrees.
    MARKER_188.2: Accept cwd override for worktree context.
    MARKER_195.20: Return empty string on failure (not "main") to avoid false done_main.
    """
    import subprocess
    from pathlib import Path
    git_cwd = cwd or str(Path(__file__).resolve().parents[3])
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=git_cwd, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return ""  # MARKER_195.20: empty, not "main" — let complete_task decide safely


def _try_auto_commit(task_id: str, task: dict, commit_message: str = None, cwd: str = None) -> dict:
    """MARKER_181.4: Auto-commit via GitCommitTool.execute().
    MARKER_188.2: Accept cwd override for worktree auto-commit.

    Same pattern as run_closure_protocol (task_board.py:1103).
    GitCommitTool.execute() IS the full pipeline: stage → commit → digest → auto-close.

    Scoped staging: uses task.closure_files if declared, otherwise parses
    git status --porcelain for actual changed files. Never git add -A.

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
    closure_files = [str(p) for p in (task.get("closure_files") or []) if str(p).strip()]

    if not closure_files:
        # Fallback: parse git status --porcelain for actually changed files
        # Format: "XY filename" where XY = 2 status chars + 1 space = 3 char prefix
        # Do NOT strip before slicing — leading space is part of status format
        changed = []
        for line in status.stdout.splitlines():
            if len(line) > 3:
                filepath = line[3:].split(" -> ")[-1].strip()
                if filepath:
                    changed.append(filepath)
        closure_files = changed

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
