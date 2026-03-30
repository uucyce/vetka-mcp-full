#!/usr/bin/env python3
"""
MARKER_201.LOCAL_LOOP — Unified autonomous local model loop.

One command for 24/7 local AI work:
    python3 scripts/local_loop.py --loop --interval 300

Merges: ollama_orchestrator.py + localguys_executor.py + decomposer
into a single poll → assess → decompose/execute → verify → complete loop.

Architecture:
    1. Poll TaskBoard for pending local-compatible tasks
    2. Assess complexity (simple vs complex)
    3. Complex → decompose via qwen3:8b → child tasks in board
    4. Simple → 6-step pipeline (recon/plan/execute/verify/review/finalize)
    5. Quality gate (phi4-mini scores 1-10, < 4 → needs_fix)
    6. Complete task → next

[task:tb_1774785690_87579_1]
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Config ────────────────────────────────────────────────────────────

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_API_URL = "http://localhost:5001"
MAX_RESPONSE_TOKENS = 2000
MAX_CHILD_TASKS = 7
QUALITY_THRESHOLD = 4  # phi4-mini score below this → needs_fix

# Model-to-role mapping
ROLE_MODEL = {
    "scout": "qwen2.5:7b",
    "coder": "qwen2.5:7b",
    "architect": "qwen3:8b",
    "researcher": "qwen2.5:7b",
    "verifier": "deepseek-r1:8b",
    "approval": "phi4-mini:latest",
    "router": "phi4-mini:latest",
    "operator": "qwen2.5:7b",
}

# Step → role → model chain
STEP_ROLE = {
    "recon": "scout",
    "plan": "architect",
    "execute": "coder",
    "verify": "verifier",
    "review": "verifier",
    "finalize": "coder",
    "decompose": "operator",
}

# Step → artifact filename
STEP_ARTIFACT = {
    "recon": "facts.json",
    "plan": "plan.json",
    "execute": "patch.diff",
    "verify": "test_output.txt",
    "review": "review.json",
    "finalize": "final_report.json",
    "decompose": "subtasks.json",
}

LOG_FMT = "%(asctime)s [LOCAL-LOOP] %(levelname)s %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
log = logging.getLogger("local_loop")


# ── HTTP helpers (stdlib only) ────────────────────────────────────────

def _http(method: str, url: str, data: dict = None, timeout: float = 120.0) -> dict:
    """Unified HTTP helper. Returns parsed JSON or {error: ...}."""
    try:
        body = json.dumps(data).encode() if data else None
        req = Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode()[:500]
        except Exception:
            pass
        return {"error": f"HTTP {e.code}: {err_body}", "status_code": e.code}
    except (URLError, OSError, json.JSONDecodeError) as e:
        return {"error": str(e)}


def http_get(url, timeout=10.0):
    return _http("GET", url, timeout=timeout)


def http_post(url, data, timeout=120.0):
    return _http("POST", url, data, timeout)


def http_put(url, data, timeout=30.0):
    return _http("PUT", url, data, timeout)


def http_patch(url, data, timeout=15.0):
    return _http("PATCH", url, data, timeout)


# ── Ollama ────────────────────────────────────────────────────────────

def ollama_generate(prompt: str, model: str, ollama_url: str,
                    max_tokens: int = MAX_RESPONSE_TOKENS) -> dict:
    """Call Ollama generate endpoint. Returns {response, model, duration_s}."""
    result = http_post(f"{ollama_url}/api/generate", {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }, timeout=300.0)

    if "error" in result:
        return result

    response_text = result.get("response", "")
    # MARKER_201.THINK_PARSE: Extract content from <think> tags if response is empty
    # (deepseek-r1 puts everything in <think>...</think>)
    if not response_text.strip() and "response" in result:
        import re
        think_match = re.search(r"<think>(.*?)</think>", result.get("response", ""), re.DOTALL)
        if think_match:
            response_text = think_match.group(1).strip()

    duration = result.get("total_duration", 0) / 1e9  # nanoseconds → seconds
    return {
        "response": response_text,
        "model": model,
        "duration_s": round(duration, 1),
    }


def ollama_check(ollama_url: str) -> bool:
    """Check Ollama is online."""
    result = http_get(f"{ollama_url}/api/tags", timeout=5.0)
    return "error" not in result


# ── TaskBoard REST API ────────────────────────────────────────────────

class TaskBoardClient:
    """REST client for TaskBoard + MCC localguys API."""

    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")
        self.tb_url = f"{self.api_url}/api/taskboard"
        self.tasks_url = f"{self.api_url}/api/tasks"
        self.mcc_url = f"{self.api_url}/api/mcc"

    def list_pending(self, project_id: str = "", limit: int = 50) -> list:
        """Get pending tasks compatible with local models."""
        url = f"{self.tb_url}/list?status=pending&limit={limit}"
        if project_id:
            url += f"&project_id={project_id}"
        result = http_get(url)
        if "error" in result:
            log.warning(f"list_pending failed: {result['error']}")
            return []
        tasks = result.get("tasks", [])
        # Filter: only local-compatible (no tool restriction or local_ollama allowed)
        return [
            t for t in tasks
            if not t.get("allowed_tools")
            or "local_ollama" in t.get("allowed_tools", [])
        ]

    def get_task(self, task_id: str) -> dict:
        return http_get(f"{self.tb_url}/{task_id}")

    def claim(self, task_id: str) -> dict:
        return http_post(f"{self.tasks_url}/{task_id}/claim", {
            "agent_name": "local-loop",
            "agent_type": "local_ollama",
        })

    def complete(self, task_id: str, commit_message: str) -> dict:
        return http_post(f"{self.tasks_url}/{task_id}/complete", {
            "commit_hash": f"local-{int(time.time())}",
            "commit_message": commit_message,
            "branch": "local/loop",
            "agent_name": "local-loop",
        })

    def update_status(self, task_id: str, status: str) -> dict:
        return http_post(f"{self.tb_url}/{task_id}/update", {
            "status": status,
        })

    def create_run(self, task_id: str, method: str = "g3") -> dict:
        return http_post(f"{self.mcc_url}/tasks/{task_id}/localguys-run", {
            "method": method,
        })

    def get_run(self, run_id: str) -> dict:
        return http_get(f"{self.mcc_url}/localguys-runs/{run_id}")

    def signal_advance(self, run_id: str, step: str, role: str,
                       model_id: str, status: str = "running") -> dict:
        return http_patch(f"{self.mcc_url}/localguys-runs/{run_id}", {
            "status": status,
            "current_step": step,
            "active_role": role,
            "model_id": model_id,
            "metadata": {"turn_increment": 1},
        })

    def upload_artifact(self, run_id: str, name: str, content: str) -> dict:
        return http_put(f"{self.mcc_url}/localguys-runs/{run_id}/artifacts/{name}", {
            "content": content,
        })

    def create_child_task(self, task_data: dict) -> dict:
        return http_post(f"{self.tasks_url}", task_data)


# ── Complexity Assessment ─────────────────────────────────────────────

def assess_complexity(task: dict) -> str:
    """Assess if a task is simple (direct execute) or complex (needs decompose).

    Returns: 'simple' or 'complex'
    """
    # Explicit complexity field
    cx = task.get("complexity", "medium")
    if cx == "high":
        return "complex"
    if cx == "low":
        return "simple"

    # Heuristics for medium
    desc = task.get("description", "")
    title = task.get("title", "")
    paths = task.get("allowed_paths", [])

    # Multi-file → complex
    if len(paths) > 3:
        return "complex"

    # Long description → complex
    if len(desc) > 1000:
        return "complex"

    # Phase type hints
    pt = task.get("phase_type", "")
    if pt in ("research", "test"):
        return "simple"
    if pt == "build" and len(paths) > 2:
        return "complex"

    # Keywords suggesting complexity
    complex_keywords = ["architecture", "refactor", "multi-file", "redesign", "migration"]
    text = f"{title} {desc}".lower()
    if any(kw in text for kw in complex_keywords):
        return "complex"

    return "simple"


# ── Task Selection ────────────────────────────────────────────────────

def select_task(tasks: list) -> dict | None:
    """Score and select the best task for local execution."""
    if not tasks:
        return None

    def score(t):
        s = 0
        cx = t.get("complexity", "medium")
        if cx == "low":
            s += 3
        elif cx == "medium":
            s += 1
        pt = t.get("phase_type", "")
        if pt == "research":
            s += 3
        elif pt in ("fix", "test"):
            s += 2
        elif pt == "build":
            s += 1
        s += max(0, 5 - t.get("priority", 3))
        # Prefer tasks already decomposed (auto-decomposed children are simple)
        if "auto-decomposed" in t.get("tags", []):
            s += 4
        return s

    tasks_sorted = sorted(tasks, key=score, reverse=True)
    return tasks_sorted[0]


# ── Prompt Templates ──────────────────────────────────────────────────

STEP_PROMPTS = {
    "recon": """You are a scout analyzing a code task.
Task: {title}
Description: {description}

Analyze the task and produce a JSON document with:
- "files_involved": list of files that need changes
- "current_state": what exists now
- "gaps": what's missing
- "risks": potential issues
- "estimated_steps": number of atomic changes needed

Output ONLY valid JSON.""",

    "plan": """You are an architect creating an implementation plan.
Task: {title}
Description: {description}

Recon findings:
{prev_artifact}

Create a step-by-step plan as JSON:
- "steps": list of {{"step": N, "action": "...", "file": "...", "details": "..."}}
- "models_needed": which models for each step
- "test_strategy": how to verify

Output ONLY valid JSON.""",

    "execute": """You are a coder implementing a plan.
Task: {title}
{hints}

Plan:
{prev_artifact}

Write the code changes as a unified diff (patch.diff format).
Include file paths, line numbers, and context.
Output ONLY the diff.""",

    "verify": """You are a verifier checking code changes.
Task: {title}

Code changes:
{prev_artifact}

Check for:
1. Syntax errors
2. Logic bugs
3. Missing edge cases
4. Security issues

Output a verification report as JSON:
- "passed": true/false
- "issues": list of issues found
- "severity": "none"/"low"/"medium"/"high"

Output ONLY valid JSON.""",

    "review": """You are a reviewer providing feedback on code changes.
Task: {title}

Code changes:
{prev_artifact}

Provide a code review as JSON:
- "quality_score": 1-10
- "suggestions": list of improvement suggestions
- "approved": true/false
- "summary": one-paragraph assessment

Output ONLY valid JSON.""",

    "finalize": """You are finalizing a completed task.
Task: {title}

All artifacts produced:
{prev_artifact}

Create a final report as JSON:
- "summary": what was done
- "files_changed": list
- "tests_status": pass/fail/skipped
- "quality_score": 1-10
- "ready_for_merge": true/false

Output ONLY valid JSON.""",
}

DECOMPOSE_PROMPT = """You are a task architect. Break this complex task into 3-7 small atomic sub-tasks
that a 7B parameter model can handle individually.

Task: {title}
Description: {description}
{hints}

Recon findings:
{prev_artifact}

Output a JSON array of sub-tasks:
[
  {{
    "title": "short title",
    "description": "what to do",
    "file_path": "path/to/file (if applicable)",
    "phase_type": "fix|build|test|research",
    "complexity": "low",
    "priority": 2
  }}
]

Rules:
- Each sub-task must be completable in ONE file change
- Max 7 sub-tasks
- Include implementation hints in description
- Output ONLY valid JSON array."""

QUALITY_GATE_PROMPT = """Rate the quality of this AI-generated work output on a scale of 1-10.

Task: {title}
Final report:
{artifact}

Scoring criteria:
- 1-3: Garbage, wrong approach, hallucinated
- 4-5: Partially useful but needs significant rework
- 6-7: Decent, minor issues
- 8-10: Good quality, ready for review

Output ONLY a single integer (1-10)."""


# ── Pipeline Executor ─────────────────────────────────────────────────

class LocalLoop:
    """Unified local model execution loop."""

    def __init__(self, api_url: str, ollama_url: str, dry_run: bool = False):
        self.tb = TaskBoardClient(api_url)
        self.ollama_url = ollama_url
        self.dry_run = dry_run
        self._artifacts: dict[str, str] = {}
        self._stats = {"tasks_completed": 0, "tasks_decomposed": 0, "tasks_failed": 0}

    def _model_for_step(self, step: str) -> str:
        role = STEP_ROLE.get(step, "coder")
        return ROLE_MODEL.get(role, "qwen2.5:7b")

    def _build_prompt(self, step: str, task: dict, is_decompose: bool = False) -> str:
        """Build prompt for a step, injecting previous artifact."""
        title = task.get("title", "")
        desc = task.get("description", "")[:1500]
        hints = ""
        if task.get("implementation_hints"):
            hints = f"Implementation hints:\n{task['implementation_hints'][:500]}"

        prev = ""
        if step == "plan" and "recon" in self._artifacts:
            prev = self._artifacts["recon"][:2000]
        elif step == "execute" and "plan" in self._artifacts:
            prev = self._artifacts["plan"][:2000]
        elif step == "verify" and "execute" in self._artifacts:
            prev = self._artifacts["execute"][:3000]
        elif step == "review" and "execute" in self._artifacts:
            prev = self._artifacts["execute"][:3000]
        elif step == "finalize":
            prev = "\n---\n".join(
                f"[{k}]: {v[:200]}" for k, v in self._artifacts.items()
            )

        if step == "plan" and is_decompose:
            template = DECOMPOSE_PROMPT
        else:
            template = STEP_PROMPTS.get(step, STEP_PROMPTS["execute"])

        return template.format(
            title=title, description=desc, hints=hints, prev_artifact=prev,
        )

    def _quality_gate(self, task: dict) -> int:
        """Run phi4-mini quality gate. Returns score 1-10."""
        final = self._artifacts.get("finalize", self._artifacts.get("review", ""))
        if not final:
            return 5  # no artifact → neutral

        prompt = QUALITY_GATE_PROMPT.format(
            title=task.get("title", ""),
            artifact=final[:2000],
        )
        result = ollama_generate(prompt, "phi4-mini:latest", self.ollama_url, max_tokens=10)
        if "error" in result:
            log.warning(f"Quality gate failed: {result['error']}")
            return 5  # fail-open

        response = result.get("response", "").strip()
        # Extract first integer from response
        for ch in response:
            if ch.isdigit():
                score = int(ch)
                if 1 <= score <= 10:
                    return score
        return 5

    def execute_pipeline(self, task: dict) -> dict:
        """Execute 6-step pipeline on a simple task."""
        task_id = task.get("id", task.get("task_id", "unknown"))
        title = task.get("title", "")
        self._artifacts.clear()

        log.info(f"Pipeline start: {task_id} — {title[:60]}")

        # Try to create a MCC run (non-fatal if it fails)
        run_id = None
        run_result = self.tb.create_run(task_id, "g3")
        if run_result and "error" not in run_result:
            run_id = run_result.get("run", {}).get("id") or run_result.get("run_id")
            log.info(f"MCC run created: {run_id}")

        steps = ["recon", "plan", "execute", "verify", "review", "finalize"]
        results = []
        total_start = time.time()

        for i, step in enumerate(steps, 1):
            model = self._model_for_step(step)
            role = STEP_ROLE.get(step, "coder")
            artifact_name = STEP_ARTIFACT.get(step, f"{step}.txt")

            log.info(f"  [{i}/{len(steps)}] {step:10s} | {model:20s} | ...", )

            # Signal MCC (non-fatal)
            if run_id:
                self.tb.signal_advance(run_id, step, role, model)

            # Build prompt and generate
            prompt = self._build_prompt(step, task)
            step_start = time.time()

            if self.dry_run:
                response_text = f"[DRY-RUN] Would generate with {model}"
                duration = 0.0
            else:
                gen = ollama_generate(prompt, model, self.ollama_url)
                if "error" in gen:
                    log.error(f"  Step {step} failed: {gen['error']}")
                    results.append({"step": step, "error": gen["error"]})
                    continue
                response_text = gen.get("response", "")
                duration = gen.get("duration_s", 0)

            self._artifacts[step] = response_text

            # Upload artifact to MCC (non-fatal)
            if run_id and not self.dry_run:
                self.tb.upload_artifact(run_id, artifact_name, response_text)

            log.info(f"  [{i}/{len(steps)}] {step:10s} | {model:20s} | {duration}s | {len(response_text)} chars")
            results.append({
                "step": step,
                "model": model,
                "duration_s": duration,
                "chars": len(response_text),
            })

        total_duration = round(time.time() - total_start, 1)

        # Signal done (non-fatal)
        if run_id:
            self.tb.signal_advance(run_id, "done", "operator", "local-loop", status="done")

        # Save artifact locally
        artifacts_dir = PROJECT_ROOT / "data" / "ollama_artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifacts_dir / f"{task_id}_{int(time.time())}_pipeline.json"
        artifact_path.write_text(json.dumps({
            "task_id": task_id,
            "title": title,
            "artifacts": {k: v[:500] for k, v in self._artifacts.items()},
            "results": results,
            "total_duration_s": total_duration,
        }, indent=2, ensure_ascii=False))

        return {
            "success": True,
            "task_id": task_id,
            "steps_completed": len([r for r in results if "error" not in r]),
            "total_duration_s": total_duration,
            "artifact_path": str(artifact_path),
            "run_id": run_id,
        }

    def execute_decompose(self, task: dict) -> dict:
        """Decompose a complex task into child tasks."""
        task_id = task.get("id", task.get("task_id", "unknown"))
        title = task.get("title", "")
        self._artifacts.clear()

        log.info(f"Decompose start: {task_id} — {title[:60]}")

        # Anti-recursion: skip if already decomposed
        if "auto-decomposed" in task.get("tags", []):
            log.info(f"Skip: {task_id} already auto-decomposed")
            return {"success": True, "task_id": task_id, "skipped": True, "reason": "already decomposed"}

        total_start = time.time()

        # Step 1: Recon
        log.info("  [1/3] recon ...")
        prompt = self._build_prompt("recon", task)
        if not self.dry_run:
            gen = ollama_generate(prompt, "qwen2.5:7b", self.ollama_url)
            self._artifacts["recon"] = gen.get("response", "") if "error" not in gen else ""
        else:
            self._artifacts["recon"] = "[DRY-RUN]"

        # Step 2: Plan-as-decompose
        log.info("  [2/3] plan (decompose) ...")
        prompt = self._build_prompt("plan", task, is_decompose=True)
        if not self.dry_run:
            gen = ollama_generate(prompt, "qwen3:8b", self.ollama_url, max_tokens=3000)
            plan_text = gen.get("response", "") if "error" not in gen else ""
        else:
            plan_text = '[{"title":"[DRY-RUN] sub-task","description":"test","phase_type":"fix","complexity":"low","priority":3}]'
        self._artifacts["plan"] = plan_text

        # Step 3: Create child tasks
        log.info("  [3/3] creating child tasks ...")
        children = []
        try:
            # Extract JSON array from response (may have markdown fences)
            plan_clean = plan_text.strip()
            if "```" in plan_clean:
                # Extract from code fence
                import re
                match = re.search(r"```(?:json)?\s*(.*?)```", plan_clean, re.DOTALL)
                if match:
                    plan_clean = match.group(1).strip()

            subtasks = json.loads(plan_clean)
            if not isinstance(subtasks, list):
                subtasks = [subtasks]
            subtasks = subtasks[:MAX_CHILD_TASKS]

            parent_project = task.get("project_id", "CUT")

            for st in subtasks:
                if self.dry_run:
                    children.append({"title": st.get("title", ""), "dry_run": True})
                    continue

                child_data = {
                    "title": f"[AUTO] {st.get('title', 'sub-task')}",
                    "description": st.get("description", ""),
                    "phase_type": st.get("phase_type", "fix"),
                    "priority": st.get("priority", 3),
                    "complexity": st.get("complexity", "low"),
                    "project_id": parent_project,
                    "allowed_tools": ["local_ollama"],
                    "parent_task_id": task_id,
                    "implementation_hints": st.get("description", ""),
                    "tags": ["auto-decomposed", "local-ready"],
                }
                if st.get("file_path"):
                    child_data["allowed_paths"] = [st["file_path"]]

                result = self.tb.create_child_task(child_data)
                child_id = result.get("task_id", result.get("id", "?"))
                children.append({"id": child_id, "title": st.get("title", "")})
                log.info(f"    Child: {child_id} — {st.get('title', '')[:50]}")

        except (json.JSONDecodeError, KeyError) as e:
            log.error(f"Failed to parse decompose output: {e}")
            return {"success": False, "task_id": task_id, "error": f"parse error: {e}"}

        total_duration = round(time.time() - total_start, 1)
        log.info(f"Decompose done: {len(children)} children in {total_duration}s")

        return {
            "success": True,
            "task_id": task_id,
            "children": children,
            "total_duration_s": total_duration,
        }

    def work_cycle(self, project_id: str = "") -> dict:
        """Single work cycle: find task → assess → execute/decompose → complete."""
        # Check Ollama
        if not ollama_check(self.ollama_url):
            return {"success": False, "error": "Ollama offline"}

        # Get pending tasks
        tasks = self.tb.list_pending(project_id)
        if not tasks:
            return {"success": False, "no_work": True}

        # Select best task
        task_summary = select_task(tasks)
        if not task_summary:
            return {"success": False, "no_work": True}

        task_id = task_summary.get("id", task_summary.get("task_id"))
        log.info(f"Selected: {task_id} — {task_summary.get('title', '')[:60]}")

        # Fetch full task
        full_task = self.tb.get_task(task_id)
        if "error" in full_task:
            log.error(f"Failed to fetch task: {full_task['error']}")
            return {"success": False, "error": full_task["error"]}

        task = full_task.get("task", full_task)

        # Assess complexity
        complexity = assess_complexity(task)
        log.info(f"Complexity: {complexity}")

        if self.dry_run:
            return {
                "success": True, "dry_run": True,
                "task_id": task_id, "complexity": complexity,
                "title": task.get("title", ""),
            }

        # Claim
        claim_result = self.tb.claim(task_id)
        if "error" in claim_result:
            log.warning(f"Claim failed: {claim_result['error']} — skipping")
            return {"success": False, "error": f"claim failed: {claim_result['error']}"}

        # Execute based on complexity
        if complexity == "complex":
            result = self.execute_decompose(task)
            if result.get("success"):
                self._stats["tasks_decomposed"] += 1
                # Complete the parent with decompose note
                children_count = len(result.get("children", []))
                self.tb.complete(task_id, f"Decomposed into {children_count} sub-tasks by local-loop")
        else:
            result = self.execute_pipeline(task)
            if result.get("success"):
                # Quality gate
                score = self._quality_gate(task)
                log.info(f"Quality score: {score}/10 (threshold: {QUALITY_THRESHOLD})")

                if score < QUALITY_THRESHOLD:
                    log.warning(f"Quality too low ({score}) — marking needs_fix")
                    self.tb.update_status(task_id, "needs_fix")
                    self._stats["tasks_failed"] += 1
                    result["quality_score"] = score
                    result["quality_rejected"] = True
                else:
                    self._stats["tasks_completed"] += 1
                    self.tb.complete(task_id,
                        f"Completed by local-loop pipeline (quality: {score}/10)")
                    result["quality_score"] = score
            else:
                self._stats["tasks_failed"] += 1

        return result

    def run_loop(self, interval: int = 300, project_id: str = "",
                 max_tasks: int = 0) -> None:
        """Continuous loop: work → sleep → repeat."""
        log.info(f"Loop started | interval={interval}s | project={project_id or 'all'}")
        log.info(f"Ollama: {self.ollama_url} | API: {self.tb.api_url}")

        task_count = 0
        while True:
            try:
                result = self.work_cycle(project_id)

                if result.get("no_work"):
                    log.info(f"No work. Sleeping {interval}s... "
                             f"(done={self._stats['tasks_completed']}, "
                             f"decomposed={self._stats['tasks_decomposed']}, "
                             f"failed={self._stats['tasks_failed']})")
                    time.sleep(interval)
                    continue

                if result.get("success"):
                    task_count += 1
                    log.info(f"Task #{task_count} done: {result.get('task_id')} "
                             f"({result.get('total_duration_s', 0)}s)")

                    if max_tasks and task_count >= max_tasks:
                        log.info(f"Max tasks ({max_tasks}) reached. Stopping.")
                        break

                    # Immediate retry — more work might be waiting
                    time.sleep(2)
                else:
                    log.warning(f"Cycle failed: {result.get('error', 'unknown')}")
                    time.sleep(30)  # short backoff on error

            except KeyboardInterrupt:
                log.info("Interrupted by user. Stopping.")
                break
            except Exception as e:
                log.error(f"Unexpected error: {e}", exc_info=True)
                time.sleep(60)

        log.info(f"Loop ended. Stats: {self._stats}")


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Unified local model loop — 24/7 autonomous task execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Single task:
  python3 scripts/local_loop.py

  # Continuous loop (check every 5 min):
  python3 scripts/local_loop.py --loop --interval 300

  # Dry run (no execution):
  python3 scripts/local_loop.py --dry-run

  # Filter by project:
  python3 scripts/local_loop.py --loop --project CUT

  # Stop after 10 tasks:
  python3 scripts/local_loop.py --loop --max-tasks 10
""",
    )
    parser.add_argument("--loop", action="store_true", help="Continuous mode")
    parser.add_argument("--interval", type=int, default=300,
                        help="Seconds between polls when idle (default: 300)")
    parser.add_argument("--project", default="", help="Filter by project_id")
    parser.add_argument("--api-url", default=DEFAULT_API_URL,
                        help=f"VETKA API URL (default: {DEFAULT_API_URL})")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL,
                        help=f"Ollama URL (default: {DEFAULT_OLLAMA_URL})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without executing")
    parser.add_argument("--max-tasks", type=int, default=0,
                        help="Stop after N tasks (0 = unlimited)")
    parser.add_argument("--status", action="store_true",
                        help="Show system status and exit")

    args = parser.parse_args()

    if args.status:
        online = ollama_check(args.ollama_url)
        print(f"Ollama: {'ONLINE' if online else 'OFFLINE'} ({args.ollama_url})")
        api_health = http_get(f"{args.api_url}/api/health", timeout=5.0)
        print(f"API:    {'ONLINE' if 'error' not in api_health else 'OFFLINE'} ({args.api_url})")
        tb = TaskBoardClient(args.api_url)
        pending = tb.list_pending(args.project)
        print(f"Tasks:  {len(pending)} pending (local-compatible)")
        if pending:
            for t in pending[:5]:
                cx = t.get("complexity", "?")
                print(f"  [{cx:6s}] {t.get('id', '?')[:20]} — {t.get('title', '')[:50]}")
        return

    loop = LocalLoop(args.api_url, args.ollama_url, dry_run=args.dry_run)

    if args.loop:
        loop.run_loop(
            interval=args.interval,
            project_id=args.project,
            max_tasks=args.max_tasks,
        )
    else:
        result = loop.work_cycle(args.project)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
