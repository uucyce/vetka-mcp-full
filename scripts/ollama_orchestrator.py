#!/usr/bin/env python3
"""
VETKA Ollama Orchestrator — Autonomous Task Loop for Local Models

Connects local Ollama models to the VETKA task board via REST API.
Gives 24/7 autonomy: when you sleep, local models work.

Flow:
    1. Fetch pending tasks (filtered by allowed_tools=local_ollama or unfiltered)
    2. Claim a task via REST
    3. Build prompt from task context (title + description + hints)
    4. Call Ollama generate API
    5. Write result to file (if task has allowed_paths)
    6. Complete task via REST

Usage:
    python3 scripts/ollama_orchestrator.py                          # single run
    python3 scripts/ollama_orchestrator.py --loop                   # continuous (work cycle)
    python3 scripts/ollama_orchestrator.py --loop --interval 300    # every 5 min
    python3 scripts/ollama_orchestrator.py --model gemma3:12b       # specific model
    python3 scripts/ollama_orchestrator.py --dry-run                # show what would happen
    python3 scripts/ollama_orchestrator.py --status                 # show Ollama + task board status

MARKER_201.OLLAMA_ORCH
@phase: 201
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

LOG_FORMAT = "%(asctime)s [OLLAMA] %(levelname)s %(message)s"
logger = logging.getLogger("vetka.ollama_orchestrator")

# Defaults
DEFAULT_MODEL = "qwen2.5:7b"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_TASKBOARD_URL = "http://localhost:5001"
AGENT_NAME = "ollama-worker"
AGENT_TYPE = "local_ollama"
MAX_PROMPT_TOKENS = 4000
MAX_RESPONSE_TOKENS = 2000


# ---------------------------------------------------------------------------
# HTTP helpers (no external deps — stdlib only)
# ---------------------------------------------------------------------------

def _http_post(url: str, data: dict, timeout: float = 120.0) -> dict:
    """POST JSON, return parsed response. Uses urllib (no httpx/requests needed)."""
    import urllib.request
    import urllib.error

    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}: {error_body[:500]}", "status_code": e.code}
    except Exception as e:
        return {"error": str(e)}


def _http_get(url: str, timeout: float = 10.0) -> dict:
    """GET JSON."""
    import urllib.request
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Ollama API
# ---------------------------------------------------------------------------

def ollama_generate(prompt: str, model: str = DEFAULT_MODEL,
                    ollama_url: str = DEFAULT_OLLAMA_URL,
                    max_tokens: int = MAX_RESPONSE_TOKENS) -> dict:
    """Call Ollama generate API. Returns {response, model, duration_s}."""
    result = _http_post(
        f"{ollama_url}/api/generate",
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        },
        timeout=300.0,  # local models can be slow
    )
    if "error" in result:
        return result

    return {
        "response": result.get("response", ""),
        "model": result.get("model", model),
        "duration_s": round(result.get("total_duration", 0) / 1e9, 1),
        "eval_count": result.get("eval_count", 0),
    }


def ollama_status(ollama_url: str = DEFAULT_OLLAMA_URL) -> dict:
    """Check Ollama status and loaded models."""
    tags = _http_get(f"{ollama_url}/api/tags")
    if "error" in tags:
        return {"status": "offline", "error": tags["error"]}

    models = [m["name"] for m in tags.get("models", [])]
    return {"status": "online", "models": models, "count": len(models)}


# ---------------------------------------------------------------------------
# Task Board REST API
# ---------------------------------------------------------------------------

def taskboard_list_pending(tb_url: str = DEFAULT_TASKBOARD_URL,
                           project_id: str = "") -> List[dict]:
    """Fetch pending tasks suitable for local models."""
    url = f"{tb_url}/api/taskboard/list?status=pending&limit=50"
    result = _http_get(url)
    if "error" in result:
        logger.warning("Task board list failed: %s", result["error"])
        return []

    tasks = result.get("tasks", [])

    # Filter: prefer tasks with allowed_tools including local_ollama,
    # or tasks with no allowed_tools restriction (open to all)
    suitable = []
    for t in tasks:
        allowed = t.get("allowed_tools", [])
        if not allowed or AGENT_TYPE in allowed:
            suitable.append(t)

    # Filter by project if specified
    if project_id:
        project_id_lower = project_id.lower()
        suitable = [t for t in suitable if
                    (t.get("project_id") or "").lower() == project_id_lower]

    return suitable


def taskboard_claim(task_id: str, tb_url: str = DEFAULT_TASKBOARD_URL) -> dict:
    """Claim a task via REST (legacy path — /api/tasks/{id}/claim)."""
    return _http_post(
        f"{tb_url}/api/tasks/{task_id}/claim",
        {"agent_name": AGENT_NAME, "agent_type": AGENT_TYPE},
    )


def taskboard_complete(task_id: str, commit_message: str,
                       tb_url: str = DEFAULT_TASKBOARD_URL) -> dict:
    """Complete a task via REST (legacy path — /api/tasks/{id}/complete)."""
    return _http_post(
        f"{tb_url}/api/tasks/{task_id}/complete",
        {
            "commit_hash": f"ollama-{int(time.time())}",
            "commit_message": commit_message,
            "branch": "local/ollama",
            "agent_name": AGENT_NAME,
        },
    )


def taskboard_get(task_id: str, tb_url: str = DEFAULT_TASKBOARD_URL) -> dict:
    """Get full task details."""
    result = _http_get(f"{tb_url}/api/taskboard/{task_id}")
    if "error" in result:
        return result
    return result.get("task", result)


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------

def build_prompt(task: dict) -> str:
    """Build a structured prompt from task context."""
    parts = []
    parts.append("You are an AI agent working on the VETKA project task board.")
    parts.append("Complete the following task. Be concise and precise.")
    parts.append("")
    parts.append(f"## Task: {task.get('title', 'Unknown')}")
    parts.append("")

    desc = task.get("description", "")
    if desc:
        parts.append(f"## Description\n{desc[:1500]}")
        parts.append("")

    hints = task.get("implementation_hints", "")
    if hints:
        parts.append(f"## Implementation Hints\n{hints[:500]}")
        parts.append("")

    paths = task.get("allowed_paths", [])
    if paths:
        parts.append(f"## Files to modify\n" + "\n".join(f"- {p}" for p in paths))
        parts.append("")

    contract = task.get("completion_contract", [])
    if contract:
        parts.append("## Acceptance criteria")
        for c in contract:
            parts.append(f"- {c}")
        parts.append("")

    phase_type = task.get("phase_type", "build")
    parts.append(f"## Task type: {phase_type}")
    parts.append("")
    parts.append("Respond with your analysis and solution. If the task requires code changes, provide the code.")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Task Selection
# ---------------------------------------------------------------------------

def select_task(tasks: List[dict]) -> Optional[dict]:
    """Select best task for local model. Prefers: low complexity, research/fix type."""
    if not tasks:
        return None

    # Score tasks
    scored = []
    for t in tasks:
        score = 0
        cx = t.get("complexity", "medium")
        if cx == "low":
            score += 3
        elif cx == "medium":
            score += 1
        # high = 0

        pt = t.get("phase_type", "build")
        if pt == "research":
            score += 3  # research = best fit for LLMs
        elif pt == "fix":
            score += 1

        pri = t.get("priority", 3)
        score += max(0, 5 - pri)  # higher priority = higher score

        scored.append((score, t))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


# ---------------------------------------------------------------------------
# Main Work Cycle
# ---------------------------------------------------------------------------

def work_cycle(model: str = DEFAULT_MODEL,
               ollama_url: str = DEFAULT_OLLAMA_URL,
               tb_url: str = DEFAULT_TASKBOARD_URL,
               project_id: str = "",
               dry_run: bool = False) -> dict:
    """Execute one work cycle: find task → claim → solve → complete."""

    # 1. Check Ollama
    status = ollama_status(ollama_url)
    if status["status"] != "online":
        return {"success": False, "reason": f"Ollama offline: {status.get('error', '?')}"}

    if model not in status.get("models", []):
        return {"success": False, "reason": f"Model {model} not available. Have: {status['models'][:5]}"}

    # 2. Fetch tasks
    tasks = taskboard_list_pending(tb_url, project_id)
    if not tasks:
        return {"success": False, "reason": "No suitable pending tasks"}

    logger.info("Found %d suitable tasks", len(tasks))

    # 3. Select best task
    task = select_task(tasks)
    if not task:
        return {"success": False, "reason": "No task selected"}

    task_id = task["id"]
    logger.info("Selected: [%s] %s (pri=%s, cx=%s, type=%s)",
                task_id, task["title"][:60], task.get("priority"),
                task.get("complexity"), task.get("phase_type"))

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "task_id": task_id,
            "title": task["title"],
            "prompt_preview": build_prompt(task)[:500],
        }

    # 4. Get full task details
    full_task = taskboard_get(task_id, tb_url)

    # 5. Claim
    claim_result = taskboard_claim(task_id, tb_url)
    if claim_result.get("error") or claim_result.get("status_code", 200) >= 400:
        return {"success": False, "reason": f"Claim failed: {claim_result}"}

    logger.info("Claimed task %s", task_id)

    # 6. Build prompt and generate
    prompt = build_prompt(full_task)
    logger.info("Generating with %s (prompt: %d chars)...", model, len(prompt))

    gen_start = time.time()
    gen_result = ollama_generate(prompt, model=model, ollama_url=ollama_url)
    gen_elapsed = time.time() - gen_start

    if "error" in gen_result:
        logger.error("Generation failed: %s", gen_result["error"])
        return {"success": False, "reason": f"Generation failed: {gen_result['error']}",
                "task_id": task_id}

    response = gen_result["response"]
    logger.info("Generated %d chars in %.1fs (model: %s)",
                len(response), gen_elapsed, gen_result.get("model", model))

    # 7. Save response as artifact
    artifact_dir = PROJECT_ROOT / "data" / "ollama_artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"{task_id}_{int(time.time())}.md"
    artifact_content = (
        f"# Ollama Response: {task.get('title', task_id)}\n"
        f"**Model:** {gen_result.get('model', model)}\n"
        f"**Duration:** {gen_result.get('duration_s', '?')}s\n"
        f"**Task:** {task_id}\n"
        f"**Timestamp:** {datetime.now(timezone.utc).isoformat()}\n\n"
        f"---\n\n{response}\n"
    )
    artifact_path.write_text(artifact_content)
    logger.info("Artifact saved: %s", artifact_path)

    # 8. Complete task
    commit_msg = (
        f"ollama({gen_result.get('model', model)}): "
        f"{task.get('title', task_id)[:80]}"
    )
    complete_result = taskboard_complete(task_id, commit_msg, tb_url)

    return {
        "success": True,
        "task_id": task_id,
        "title": task.get("title", ""),
        "model": gen_result.get("model", model),
        "duration_s": gen_result.get("duration_s"),
        "response_length": len(response),
        "artifact": str(artifact_path),
        "complete_result": complete_result,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def show_status(ollama_url: str, tb_url: str):
    """Show Ollama and task board status."""
    print("=== Ollama Status ===")
    status = ollama_status(ollama_url)
    if status["status"] == "online":
        print(f"  Status: online ({status['count']} models)")
        for m in status["models"][:10]:
            print(f"    - {m}")
        if status["count"] > 10:
            print(f"    ... and {status['count'] - 10} more")
    else:
        print(f"  Status: OFFLINE ({status.get('error', '?')})")

    print("\n=== Task Board Status ===")
    tasks = taskboard_list_pending(tb_url)
    print(f"  Suitable pending tasks: {len(tasks)}")
    for t in tasks[:5]:
        print(f"    [{t.get('id', '?')}] {t.get('title', '?')[:60]}")
    if len(tasks) > 5:
        print(f"    ... and {len(tasks) - 5} more")


def main():
    parser = argparse.ArgumentParser(
        description="VETKA Ollama Orchestrator — local model task automation"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="Ollama API URL")
    parser.add_argument("--tb-url", default=DEFAULT_TASKBOARD_URL, help="Task board API URL")
    parser.add_argument("--project", default="", help="Filter by project_id")
    parser.add_argument("--loop", action="store_true", help="Continuous work cycle")
    parser.add_argument("--interval", type=int, default=300, help="Loop interval in seconds (default: 300)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen, don't execute")
    parser.add_argument("--status", action="store_true", help="Show Ollama + task board status")
    parser.add_argument("--max-tasks", type=int, default=0, help="Max tasks per loop session (0=unlimited)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    if args.status:
        show_status(args.ollama_url, args.tb_url)
        return

    tasks_done = 0

    if args.loop:
        logger.info("Starting continuous work cycle (model=%s, interval=%ds)", args.model, args.interval)
        while True:
            result = work_cycle(
                model=args.model,
                ollama_url=args.ollama_url,
                tb_url=args.tb_url,
                project_id=args.project,
                dry_run=args.dry_run,
            )
            if result.get("success"):
                tasks_done += 1
                logger.info(
                    "Task %d done: %s (%.1fs, %d chars)",
                    tasks_done,
                    result.get("task_id", "?"),
                    result.get("duration_s", 0),
                    result.get("response_length", 0),
                )
                if args.max_tasks and tasks_done >= args.max_tasks:
                    logger.info("Max tasks reached (%d), stopping", args.max_tasks)
                    break
                # If task completed, immediately look for next one (no interval)
                continue
            else:
                logger.info("No work: %s. Sleeping %ds...", result.get("reason", "?"), args.interval)
                time.sleep(args.interval)
    else:
        result = work_cycle(
            model=args.model,
            ollama_url=args.ollama_url,
            tb_url=args.tb_url,
            project_id=args.project,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
