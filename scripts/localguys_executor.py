#!/usr/bin/env python3
"""
Localguys Step Executor — Bridge between Localguys orchestration and Ollama.

Takes a localguys run (created via `localguys run <method> --task <id>`)
and executes it step by step: model selection → prompt → Ollama → artifact → advance.

Usage:
    # Create run first, then execute:
    python3 scripts/localguys.py run g3 --task tb_xxx
    python3 scripts/localguys_executor.py --run-id lg_run_xxx

    # Or one-shot: create + execute:
    python3 scripts/localguys_executor.py --task tb_xxx --method g3

    # Dry run (show prompts, don't call Ollama):
    python3 scripts/localguys_executor.py --run-id lg_run_xxx --dry-run

MARKER_201.LOCALGUYS_EXECUTOR
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
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

LOG_FORMAT = "%(asctime)s [LG-EXEC] %(levelname)s %(message)s"
logger = logging.getLogger("vetka.localguys_executor")

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MCC_URL = "http://localhost:5001/api/mcc"


# ---------------------------------------------------------------------------
# HTTP helpers (reused from ollama_orchestrator)
# ---------------------------------------------------------------------------

def _http_post(url: str, data: dict, timeout: float = 120.0) -> dict:
    import urllib.request, urllib.error
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:500]}", "status_code": e.code}
    except Exception as e:
        return {"error": str(e)}


def _http_get(url: str, timeout: float = 10.0) -> dict:
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def _http_put(url: str, data: dict, timeout: float = 30.0) -> dict:
    import urllib.request, urllib.error
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                headers={"Content-Type": "application/json"}, method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:500]}", "status_code": e.code}
    except Exception as e:
        return {"error": str(e)}


def _http_patch(url: str, data: dict, timeout: float = 15.0) -> dict:
    import urllib.request, urllib.error
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                headers={"Content-Type": "application/json"}, method="PATCH")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:500]}", "status_code": e.code}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Model selection (hardcoded from Model Matrix — no async dependency)
# ---------------------------------------------------------------------------

ROLE_MODEL_MAP = {
    "scout":      "qwen2.5:7b",
    "coder":      "qwen2.5:7b",
    "architect":  "qwen3:8b",
    "researcher": "qwen2.5:7b",
    "verifier":   "deepseek-r1:8b",
    "approval":   "phi4-mini:latest",
    "router":     "phi4-mini:latest",
    "operator":   "qwen2.5:7b",
}

STEP_ROLE_MAP = {
    "recon":     "scout",
    "research":  "researcher",
    "plan":      "architect",
    "decompose": "operator",   # no LLM — pure code step
    "execute":   "coder",
    "verify":    "verifier",
    "review":    "verifier",
    "approve":   "approval",
    "finalize":  "coder",
}

STEP_ARTIFACT_MAP = {
    "recon":     "facts.json",
    "research":  "research.json",
    "plan":      "plan.json",
    "decompose": "subtasks.json",
    "execute":   "patch.diff",
    "verify":    "test_output.txt",
    "review":    "review.json",
    "approve":   "approval.json",
    "finalize":  "final_report.json",
}

# Steps for the decompose-only workflow
DECOMPOSE_STEPS = ["recon", "plan", "decompose"]

MAX_CHILD_TASKS = 7


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

STEP_PROMPTS = {
    "recon": """You are a code scout analyzing a task. Produce a JSON object (facts.json) with:
- "affected_files": list of file paths likely involved
- "dependencies": what this task depends on
- "risks": potential issues
- "scope_estimate": "low" | "medium" | "high"

Task: {title}
Description: {description}
Allowed paths: {allowed_paths}

Respond with ONLY valid JSON, no markdown fences.""",

    "research": """You are a researcher. Based on the task and recon facts, produce research.json with:
- "findings": list of relevant discoveries
- "references": relevant code patterns or docs
- "recommendation": suggested approach

Task: {title}
Facts: {prev_artifacts}

Respond with ONLY valid JSON.""",

    "plan": """You are a software architect. Based on the facts, produce plan.json with:
- "approach": high-level strategy (1-3 sentences)
- "steps": ordered list of implementation steps (strings)
- "files_to_modify": list of objects with "path" and "change" fields

Facts: {prev_artifacts}
Task: {title}

Respond with ONLY valid JSON.""",

    "execute": """You are a coder. Implement the plan as a unified diff.
Work ONLY within these paths: {allowed_paths}
Be minimal and precise. Output a valid unified diff format.

Plan: {prev_artifacts}
Task: {title}
Description: {description}""",

    "verify": """You are a code verifier. Review the patch for correctness.
Produce a test report (plain text) with:
- PASS/FAIL for each check
- Overall verdict: PASS or FAIL

Checks:
1. Syntax valid?
2. Matches the plan?
3. Within allowed paths?
4. No obvious bugs?
5. No security issues?

Patch:
{prev_artifacts}""",

    "review": """You are a senior code reviewer. Produce review.json with:
- "verdict": "approve" | "request_changes" | "reject"
- "comments": list of review comments (strings)
- "quality_score": 1-10

Patch:
{prev_artifacts}

Facts: {context}

Respond with ONLY valid JSON.""",

    "approve": """You are an approval gate. Based on the review, produce approval.json with:
- "approved": true | false
- "reason": explanation

Review: {prev_artifacts}

Respond with ONLY valid JSON.""",

    "finalize": """Produce final_report.json summarizing this run:
- "task_id": "{task_id}"
- "run_id": "{run_id}"
- "steps_completed": list of step names
- "artifacts_produced": list of artifact names
- "verdict": overall outcome
- "models_used": object mapping step to model name

Previous artifacts summary: {prev_artifacts}

Respond with ONLY valid JSON.""",
}

# Decomposition-optimized plan prompt (used when method == "decompose")
DECOMPOSE_PLAN_PROMPT = """You are a task decomposer. Break this task into atomic sub-tasks.

RULES — each sub-task MUST:
- Touch exactly 1 file
- Be completable in under 50 lines of code
- Have a clear, testable outcome
- Be independent (no ordering dependencies if possible)

Produce a JSON object with:
- "approach": 1-2 sentence strategy
- "steps": list of objects, each with:
  - "description": what to do (imperative verb, specific)
  - "file": exact file path to modify
  - "complexity": "low" or "medium"
  - "test_hint": how to verify this sub-task works

IMPORTANT: Maximum {max_steps} sub-tasks. If task is simple, 1-2 is fine.

Task: {title}
Description: {description}
Known files: {allowed_paths}
Recon facts: {prev_artifacts}

Respond with ONLY valid JSON, no markdown fences."""


# ---------------------------------------------------------------------------
# Core executor
# ---------------------------------------------------------------------------

class StepExecutor:
    """Executes localguys runs step by step via Ollama."""

    def __init__(self, mcc_url: str = DEFAULT_MCC_URL,
                 ollama_url: str = DEFAULT_OLLAMA_URL,
                 dry_run: bool = False):
        self.mcc_url = mcc_url
        self.ollama_url = ollama_url
        self.dry_run = dry_run
        self._artifacts_cache: Dict[str, str] = {}  # step → content
        self._models_used: Dict[str, str] = {}  # step → model

    def get_run(self, run_id: str) -> Optional[dict]:
        result = _http_get(f"{self.mcc_url}/localguys-runs/{run_id}")
        if "error" in result:
            logger.error("Failed to get run %s: %s", run_id, result["error"])
            return None
        return result.get("run", result)

    def get_task_run(self, task_id: str) -> Optional[dict]:
        result = _http_get(f"{self.mcc_url}/tasks/{task_id}/localguys-run")
        if "error" in result:
            return None
        return result.get("run", result)

    def create_run(self, task_id: str, method: str) -> Optional[dict]:
        # MARKER_201.CREATE_RUN: send workflow_family so server can resolve the contract.
        # Previously sent {"method": method} which the server ignores — causing
        # "Workflow contract core_library not found" when task has no workflow_family field.
        family = method if method.endswith("_localguys") else f"{method}_localguys"
        result = _http_post(
            f"{self.mcc_url}/tasks/{task_id}/localguys-run",
            {"workflow_family": family},
        )
        if "error" in result or not result.get("success"):
            logger.error("Failed to create run: %s", result)
            return None
        return result

    def signal_advance(self, run_id: str, step: str, role: str,
                       model_id: str, status: str = "running") -> dict:
        payload = {
            "status": status,
            "current_step": step,
            "active_role": role,
            "model_id": model_id,
            "metadata": {"turn_increment": 1},
        }
        return _http_patch(f"{self.mcc_url}/localguys-runs/{run_id}", payload)

    def upload_artifact(self, run_id: str, artifact_name: str, content: str) -> dict:
        return _http_put(
            f"{self.mcc_url}/localguys-runs/{run_id}/artifacts/{artifact_name}",
            {"content": content},
        )

    def ollama_generate(self, prompt: str, model: str, max_tokens: int = 2000) -> dict:
        result = _http_post(
            f"{self.ollama_url}/api/generate",
            {"model": model, "prompt": prompt, "stream": False,
             "options": {"num_predict": max_tokens}},
            timeout=300.0,
        )
        if "error" in result:
            return result
        raw = result.get("response", "")
        # MARKER_201.THINK_STRIP: deepseek-r1 and other thinking models wrap output
        # in <think>...</think> tags. Extract content after </think> first;
        # if empty (pure thinking mode), fall back to the content inside <think>.
        import re as _re
        _think_match = _re.search(r"<think>(.*?)</think>(.*)", raw, _re.DOTALL)
        if _think_match:
            after = _think_match.group(2).strip()
            inside = _think_match.group(1).strip()
            raw = after if after else inside
        return {
            "response": raw,
            "model": result.get("model", model),
            "duration_s": round(result.get("total_duration", 0) / 1e9, 1),
        }

    def select_model(self, role: str) -> str:
        return ROLE_MODEL_MAP.get(role, "qwen2.5:7b")

    def create_child_tasks(self, plan_json: str, parent_task: dict) -> List[dict]:
        """Parse plan.json and create child tasks on task board via REST.

        Returns list of created task dicts.
        """
        # Parse plan
        try:
            plan = json.loads(plan_json)
        except json.JSONDecodeError:
            logger.error("Failed to parse plan.json — not valid JSON")
            return []

        steps = plan.get("steps", [])
        if not steps:
            logger.warning("Plan has no steps — nothing to decompose")
            return []

        # Cap at MAX_CHILD_TASKS
        if len(steps) > MAX_CHILD_TASKS:
            logger.info("Capping %d steps to %d", len(steps), MAX_CHILD_TASKS)
            steps = steps[:MAX_CHILD_TASKS]

        parent_id = parent_task.get("id", parent_task.get("task_id", ""))
        parent_project = parent_task.get("project_id", "CUT")
        parent_priority = parent_task.get("priority", 3)
        parent_phase_type = parent_task.get("phase_type", "build")

        # Task board REST URL (not MCC — direct task board)
        tb_base = self.mcc_url.replace("/api/mcc", "/api/tasks")

        created = []
        for i, step in enumerate(steps):
            # Handle both dict and string steps
            if isinstance(step, str):
                desc = step
                file_path = ""
                test_hint = ""
                cx = "low"
            else:
                desc = step.get("description", f"Step {i+1}")
                file_path = step.get("file", "")
                test_hint = step.get("test_hint", "")
                cx = step.get("complexity", "low")

            child_body = {
                "title": f"[AUTO] {desc}",
                "description": f"Sub-task of {parent_id}. {desc}",
                "phase_type": parent_phase_type,
                "priority": parent_priority,
                "complexity": cx,
                "project_id": parent_project,
                "allowed_tools": ["local_ollama"],
                "parent_task_id": parent_id,
                "implementation_hints": test_hint,
                "tags": ["auto-decomposed", "local-ready"],
            }
            if file_path:
                child_body["allowed_paths"] = [file_path]

            result = _http_post(tb_base, child_body)
            if result.get("error"):
                logger.warning("Failed to create child task %d: %s", i+1, result["error"])
            else:
                child_id = result.get("task_id", result.get("id", "?"))
                logger.info("  Created child [%d/%d]: %s — %s",
                            i+1, len(steps), child_id, desc[:60])
                created.append({"task_id": child_id, "description": desc, "file": file_path})

        return created

    def build_prompt(self, step: str, task: dict, run_id: str,
                     method: str = "") -> str:
        # Use decompose-optimized plan prompt when decomposing
        if step == "plan" and method == "decompose":
            template = DECOMPOSE_PLAN_PROMPT
        else:
            template = STEP_PROMPTS.get(step, STEP_PROMPTS["recon"])

        # Collect previous artifacts as context
        prev = ""
        if step == "plan" and "recon" in self._artifacts_cache:
            prev = self._artifacts_cache["recon"][:3000]
        elif step == "execute" and "plan" in self._artifacts_cache:
            prev = self._artifacts_cache["plan"][:3000]
        elif step == "verify" and "execute" in self._artifacts_cache:
            prev = self._artifacts_cache["execute"][:3000]
        elif step == "review":
            parts = []
            if "execute" in self._artifacts_cache:
                parts.append(self._artifacts_cache["execute"][:2000])
            prev = "\n---\n".join(parts)
        elif step == "approve" and "review" in self._artifacts_cache:
            prev = self._artifacts_cache["review"][:2000]
        elif step == "finalize":
            summary_parts = []
            for s, c in self._artifacts_cache.items():
                summary_parts.append(f"[{s}]: {c[:200]}")
            prev = "\n".join(summary_parts)
        elif step == "research" and "recon" in self._artifacts_cache:
            prev = self._artifacts_cache["recon"][:3000]

        allowed_paths = ", ".join(task.get("allowed_paths", []) or ["(any)"])

        return template.format(
            title=task.get("title", "Unknown"),
            description=(task.get("description", "") or "")[:1500],
            allowed_paths=allowed_paths,
            prev_artifacts=prev,
            context=prev,
            task_id=task.get("id", "?"),
            run_id=run_id,
            max_steps=MAX_CHILD_TASKS,
        )

    def execute_run(self, run_id: str, method: str = "") -> dict:
        """Execute all remaining steps in a run."""
        run = self.get_run(run_id)
        if not run:
            return {"success": False, "error": f"Run {run_id} not found"}

        task = run.get("task_snapshot", {})
        self._method = method or run.get("workflow_family", "").replace("_localguys", "")

        steps = run.get("contract", {}).get("steps", [])
        if not steps:
            if self._method == "decompose":
                steps = DECOMPOSE_STEPS
            else:
                steps = ["recon", "plan", "execute", "verify", "review", "finalize"]

        current_step = run.get("current_step", "recon")
        status = run.get("status", "queued")

        if status in ("done", "blocked", "failed"):
            return {"success": False, "error": f"Run already in terminal state: {status}"}

        # Find starting index
        try:
            start_idx = steps.index(current_step)
        except ValueError:
            start_idx = 0

        logger.info("Executing run %s: %d steps from '%s'", run_id, len(steps) - start_idx, current_step)

        results = []
        for i in range(start_idx, len(steps)):
            step = steps[i]
            next_step = steps[i + 1] if i + 1 < len(steps) else None
            role = STEP_ROLE_MAP.get(step, "coder")
            model = self.select_model(role)
            artifact_name = STEP_ARTIFACT_MAP.get(step, f"{step}_output.txt")

            logger.info("[%d/%d] Step: %s | Role: %s | Model: %s | Artifact: %s",
                        i + 1, len(steps), step, role, model, artifact_name)

            # Build prompt (pass method for decompose-optimized plan prompt)
            prompt = self.build_prompt(step, task, run_id, method=self._method)

            if self.dry_run:
                if step == "decompose":
                    logger.info("[DRY RUN] DECOMPOSE: would create child tasks from plan.json")
                else:
                    logger.info("[DRY RUN] Prompt (%d chars):\n%s", len(prompt), prompt[:500])
                results.append({"step": step, "dry_run": True, "prompt_length": len(prompt)})
                continue

            # === DECOMPOSE STEP: no LLM, create child tasks ===
            if step == "decompose":
                plan_content = self._artifacts_cache.get("plan", "")
                if not plan_content:
                    logger.error("Cannot decompose: no plan.json artifact")
                    results.append({"step": step, "error": "no plan artifact"})
                    continue

                # Anti-recursion: check if parent task is already auto-decomposed
                parent_tags = task.get("tags", []) or []
                if "auto-decomposed" in parent_tags:
                    logger.info("  Skipping decompose — task is already auto-decomposed (anti-recursion)")
                    subtasks_json = json.dumps({"skipped": True, "reason": "anti-recursion"})
                else:
                    children = self.create_child_tasks(plan_content, task)
                    subtasks_json = json.dumps({
                        "parent_task_id": task.get("id", ""),
                        "children_created": len(children),
                        "children": children,
                    }, indent=2)
                    logger.info("  Decomposed into %d child tasks", len(children))

                self._artifacts_cache[step] = subtasks_json
                self._models_used[step] = "none (code step)"

                # Upload subtasks.json artifact
                self.upload_artifact(run_id, artifact_name, subtasks_json)

                results.append({
                    "step": step,
                    "model": "none",
                    "duration_s": 0,
                    "response_length": len(subtasks_json),
                    "artifact": artifact_name,
                    "children_created": len(children) if "children" in dir() else 0,
                })
                # Advance to next step or done
                if next_step:
                    next_role = STEP_ROLE_MAP.get(next_step, "coder")
                    next_model = self.select_model(next_role)
                    self.signal_advance(run_id, next_step, next_role, next_model, status="running")
                else:
                    self.signal_advance(run_id, step, role, model, status="done")
                    logger.info("Decomposition complete!")
                continue

            # === NORMAL STEP: call Ollama ===

            # Signal: starting this step
            sig = self.signal_advance(run_id, step, role, model, status="running")
            if sig.get("error"):
                logger.warning("Signal advance failed: %s", sig["error"])

            # Call Ollama
            gen_start = time.time()
            gen_result = self.ollama_generate(prompt, model)
            gen_elapsed = time.time() - gen_start

            if "error" in gen_result:
                logger.error("Ollama failed on step %s: %s", step, gen_result["error"])
                self.signal_advance(run_id, step, role, model, status="failed")
                return {
                    "success": False,
                    "error": f"Ollama failed on step {step}: {gen_result['error']}",
                    "steps_completed": [r["step"] for r in results],
                }

            response = gen_result["response"]
            logger.info("  Generated %d chars in %.1fs", len(response), gen_elapsed)

            # Cache artifact content
            self._artifacts_cache[step] = response
            self._models_used[step] = gen_result.get("model", model)

            # Upload artifact
            upload = self.upload_artifact(run_id, artifact_name, response)
            if upload.get("error"):
                logger.warning("Artifact upload failed: %s", upload["error"])
                # Continue anyway — artifact might still be written

            # Advance to next step (or finalize)
            if next_step:
                next_role = STEP_ROLE_MAP.get(next_step, "coder")
                next_model = self.select_model(next_role)
                self.signal_advance(run_id, next_step, next_role, next_model, status="running")
            else:
                # Last step — signal done
                done_sig = self.signal_advance(run_id, step, role, model, status="done")
                if done_sig.get("error") and "required_artifact_missing" in str(done_sig.get("error", "")):
                    logger.warning("Completion blocked: missing artifacts. Status: blocked")
                else:
                    logger.info("Run completed!")

            results.append({
                "step": step,
                "model": gen_result.get("model", model),
                "duration_s": round(gen_elapsed, 1),
                "response_length": len(response),
                "artifact": artifact_name,
            })

        total_duration = sum(r.get("duration_s", 0) for r in results)
        return {
            "success": True,
            "run_id": run_id,
            "steps_completed": len(results),
            "total_duration_s": round(total_duration, 1),
            "results": results,
            "models_used": self._models_used,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Localguys Step Executor")
    parser.add_argument("--run-id", help="Execute existing run")
    parser.add_argument("--task", help="Task ID (creates run if --method given)")
    parser.add_argument("--method", default="g3",
                        help="Workflow method: g3, research, quickfix, docs, decompose (default: g3)")
    parser.add_argument("--mcc-url", default=DEFAULT_MCC_URL, help="MCC API URL")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="Ollama API URL")
    parser.add_argument("--dry-run", action="store_true", help="Show prompts without calling Ollama")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    executor = StepExecutor(
        mcc_url=args.mcc_url,
        ollama_url=args.ollama_url,
        dry_run=args.dry_run,
    )

    run_id = args.run_id

    if not run_id and args.task:
        # Check for existing run
        existing = executor.get_task_run(args.task)
        if existing and existing.get("status") not in ("done", "blocked", "failed"):
            run_id = existing.get("run_id")
            logger.info("Found existing run %s (status: %s)", run_id, existing.get("status"))
        else:
            # Create new run. For decompose, create as g3 (registered family) but override steps
            create_method = "g3" if args.method == "decompose" else args.method
            logger.info("Creating run: method=%s (create_as=%s), task=%s", args.method, create_method, args.task)
            create_result = executor.create_run(args.task, create_method)
            if not create_result:
                print(json.dumps({"success": False, "error": "Failed to create run"}))
                return
            run_id = create_result.get("run_id")
            logger.info("Created run %s", run_id)

    if not run_id:
        parser.error("Either --run-id or --task is required")

    result = executor.execute_run(run_id, method=args.method)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
