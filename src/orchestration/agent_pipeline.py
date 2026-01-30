"""Agent Pipeline - Fractal task orchestration for VETKA.

Implements fractal task decomposition:
Task -> Subtasks -> Sub-searches (with auto-trigger on "?")

On any unclear step, automatically triggers Grok researcher to enrich context,
then passes enriched context to coder/executor.

@status: active
@phase: 102
@depends: src/mcp/tools/llm_call_tool.py, src/mcp/tools/session_tools.py, src/mcp/tools/compound_tools.py
@used_by: src/mcp/vetka_mcp_bridge.py
"""

import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# MARKER_102.1_START: Pipeline storage paths
TASKS_FILE = Path(__file__).parent.parent.parent / "data" / "pipeline_tasks.json"
PROMPTS_FILE = Path(__file__).parent.parent.parent / "data" / "templates" / "pipeline_prompts.json"
# MARKER_102.1_END


@dataclass
class Subtask:
    """Subtask with optional research trigger"""
    description: str
    needs_research: bool = False
    question: Optional[str] = None
    context: Optional[Dict] = None
    result: Optional[str] = None
    status: str = "pending"  # pending, researching, executing, done, failed
    marker: Optional[str] = None


@dataclass
class PipelineTask:
    """Main task with fractal subtasks"""
    task_id: str
    task: str
    phase_type: str  # research, fix, build
    status: str = "pending"
    subtasks: List[Subtask] = None
    timestamp: float = 0
    results: Optional[Dict] = None

    def __post_init__(self):
        if self.subtasks is None:
            self.subtasks = []
        if self.timestamp == 0:
            self.timestamp = time.time()


class AgentPipeline:
    """
    Fractal pipeline: Task -> Subtasks -> Sub-searches

    Auto-triggers Grok researcher on any "?" or needs_research=True.
    """

    def __init__(self):
        self.llm_tool = None  # Lazy load
        self._load_prompts()

    def _load_prompts(self):
        """Load prompt templates"""
        if PROMPTS_FILE.exists():
            self.prompts = json.loads(PROMPTS_FILE.read_text())
        else:
            # MARKER_102.2_START: Default prompts
            self.prompts = {
                "architect": {
                    "system": """You are a task architect for VETKA project.
Break down the task into clear subtasks.
For any unclear part, mark it with needs_research=true and add a question.

Respond in STRICT JSON format:
{
    "subtasks": [
        {
            "description": "what to do",
            "needs_research": false,
            "question": null,
            "marker": "MARKER_102.X"
        },
        {
            "description": "unclear part",
            "needs_research": true,
            "question": "What is the best approach for X?",
            "marker": "MARKER_102.Y"
        }
    ],
    "execution_order": "sequential" or "parallel",
    "estimated_complexity": "low|medium|high"
}"""
                },
                "researcher": {
                    "system": """You are a deep researcher for VETKA project.
Research the question thoroughly. Provide actionable insights.

Respond in STRICT JSON format:
{
    "insights": ["key finding 1", "key finding 2"],
    "actionable_steps": [
        {"step": "description", "needs_code": true, "marker": "MARKER_102.X"}
    ],
    "enriched_context": "key facts and recommendations for the coder",
    "confidence": 0.9,
    "further_questions": ["optional follow-up if confidence < 0.7"]
}"""
                },
                "coder": {
                    "system": """You are a coder for VETKA project.
Implement the subtask using provided context.
Always add MARKERs to your code.
Follow existing patterns in the codebase.

Respond with implementation plan or code."""
                }
            }
            # MARKER_102.2_END

    def _get_llm_tool(self):
        """Lazy load LLM tool to avoid circular imports"""
        if self.llm_tool is None:
            try:
                from src.mcp.tools.llm_call_tool import LLMCallTool
                self.llm_tool = LLMCallTool()
            except ImportError:
                logger.warning("LLMCallTool not available, using fallback")
                self.llm_tool = None
        return self.llm_tool

    # MARKER_102.17_START: Robust JSON extraction from LLM responses
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response with multiple fallbacks.
        Handles: raw JSON, markdown code blocks, JSON embedded in prose.
        """
        import re

        if not text or not text.strip():
            return {}

        text = text.strip()

        # Try 1: Direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try 2: Extract from ```json ... ``` block
        json_block = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_block:
            try:
                return json.loads(json_block.group(1))
            except json.JSONDecodeError:
                pass

        # Try 3: Extract from ``` ... ``` block
        code_block = re.search(r'```\s*([\s\S]*?)\s*```', text)
        if code_block:
            try:
                return json.loads(code_block.group(1))
            except json.JSONDecodeError:
                pass

        # Try 4: Find JSON object in text (greedy match from { to })
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # Try 5: Find JSON starting from first {
        first_brace = text.find('{')
        if first_brace != -1:
            try:
                return json.loads(text[first_brace:])
            except json.JSONDecodeError:
                pass

        logger.warning(f"[Pipeline] Could not extract JSON from: {text[:100]}...")
        raise json.JSONDecodeError("No valid JSON found", text, 0)
    # MARKER_102.17_END

    # MARKER_102.3_START: Task storage
    def _load_tasks(self) -> Dict[str, Any]:
        """Load tasks from JSON storage"""
        if TASKS_FILE.exists():
            return json.loads(TASKS_FILE.read_text())
        return {}

    def _save_tasks(self, tasks: Dict[str, Any]):
        """Save tasks to JSON storage"""
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        TASKS_FILE.write_text(json.dumps(tasks, indent=2, default=str))

    def _update_task(self, task: PipelineTask):
        """Update single task in storage"""
        tasks = self._load_tasks()
        tasks[task.task_id] = asdict(task)
        self._save_tasks(tasks)

    # MARKER_102.20_START: Public status method
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a pipeline task by ID"""
        tasks = self._load_tasks()
        return tasks.get(task_id)

    def get_recent_tasks(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most recent tasks"""
        tasks = self._load_tasks()
        sorted_tasks = sorted(
            tasks.values(),
            key=lambda t: t.get("timestamp", 0),
            reverse=True
        )
        return sorted_tasks[:limit]
    # MARKER_102.20_END
    # MARKER_102.3_END

    # MARKER_102.4_START: Core pipeline methods
    async def execute(self, task: str, phase_type: str = "research") -> Dict[str, Any]:
        """
        Execute fractal pipeline.

        Args:
            task: Task description
            phase_type: "research" | "fix" | "build"

        Returns:
            Pipeline results with all subtask outcomes
        """
        # Create task
        task_id = f"task_{int(time.time())}"
        pipeline_task = PipelineTask(
            task_id=task_id,
            task=task,
            phase_type=phase_type,
            status="planning"
        )
        self._update_task(pipeline_task)

        logger.info(f"[Pipeline] Starting {phase_type} pipeline for: {task[:50]}...")

        try:
            # Phase 1: Architect breaks down task
            plan = await self._architect_plan(task, phase_type)
            pipeline_task.subtasks = [
                Subtask(**st) if isinstance(st, dict) else st
                for st in plan.get("subtasks", [])
            ]
            pipeline_task.status = "executing"
            self._update_task(pipeline_task)

            # Phase 2: Execute each subtask (with research triggers)
            for i, subtask in enumerate(pipeline_task.subtasks):
                logger.info(f"[Pipeline] Subtask {i+1}/{len(pipeline_task.subtasks)}: {subtask.description[:40]}...")

                # Auto-trigger research on "?"
                if subtask.needs_research and subtask.question:
                    subtask.status = "researching"
                    self._update_task(pipeline_task)

                    research = await self._research(subtask.question)
                    subtask.context = research

                    # Recursive: if researcher has further questions with low confidence
                    if research.get("confidence", 1.0) < 0.7:
                        for fq in research.get("further_questions", [])[:2]:  # Max 2 recursions
                            sub_research = await self._research(fq)
                            if subtask.context.get("enriched_context"):
                                subtask.context["enriched_context"] += f"\n\nFollow-up ({fq}):\n{sub_research.get('enriched_context', '')}"

                # Execute subtask
                subtask.status = "executing"
                self._update_task(pipeline_task)

                result = await self._execute_subtask(subtask, phase_type)
                subtask.result = result
                subtask.status = "done"
                self._update_task(pipeline_task)

            # Phase 3: Compile results
            pipeline_task.status = "done"
            pipeline_task.results = {
                "plan": plan,
                "subtasks_completed": len([s for s in pipeline_task.subtasks if s.status == "done"]),
                "subtasks_total": len(pipeline_task.subtasks),
                "execution_order": plan.get("execution_order", "sequential")
            }
            self._update_task(pipeline_task)

            logger.info(f"[Pipeline] Completed: {pipeline_task.results['subtasks_completed']}/{pipeline_task.results['subtasks_total']} subtasks")

            return asdict(pipeline_task)

        except Exception as e:
            logger.error(f"[Pipeline] Failed: {e}")
            pipeline_task.status = "failed"
            pipeline_task.results = {"error": str(e)}
            self._update_task(pipeline_task)
            return asdict(pipeline_task)
    # MARKER_102.4_END

    # MARKER_102.5_START: Architect planning
    async def _architect_plan(self, task: str, phase_type: str) -> Dict[str, Any]:
        """
        Architect breaks down task into subtasks.
        Marks unclear parts with needs_research=True.
        """
        tool = self._get_llm_tool()
        if not tool:
            # Fallback: simple breakdown
            return {
                "subtasks": [{"description": task, "needs_research": True, "question": f"How to approach: {task}?", "marker": "MARKER_102.1"}],
                "execution_order": "sequential",
                "estimated_complexity": "medium"
            }

        prompt = self.prompts["architect"]
        # MARKER_102.13: Read model from prompts config (default: OpenRouter)
        model = prompt.get("model", "anthropic/claude-sonnet-4")
        temperature = prompt.get("temperature", 0.3)

        # LLMCallTool.execute is synchronous
        result = tool.execute({
            "model": model,
            "messages": [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": f"Phase type: {phase_type}\n\nTask to break down:\n{task}"}
            ],
            "temperature": temperature,
            "max_tokens": 2000
        })

        # MARKER_102.16_START: Parse JSON response with robust extraction
        try:
            # LLMCallTool returns: {"success": bool, "result": {"content": str, ...}, "error": str}
            if not result.get("success"):
                logger.warning(f"[Pipeline] Architect LLM call failed: {result.get('error')}")
                raise ValueError(result.get("error", "Unknown error"))

            response_text = result.get("result", {}).get("content", "{}")
            plan = self._extract_json(response_text)

            # Validate required fields
            if "subtasks" not in plan:
                plan["subtasks"] = [{"description": task, "needs_research": True, "marker": "MARKER_102.1"}]
            if "execution_order" not in plan:
                plan["execution_order"] = "sequential"
            if "estimated_complexity" not in plan:
                plan["estimated_complexity"] = "medium"

            logger.info(f"[Pipeline] Architect plan: {len(plan.get('subtasks', []))} subtasks, {plan.get('execution_order')}")
            return plan

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[Pipeline] Failed to parse architect response: {e}")
            return {
                "subtasks": [{"description": task, "needs_research": True, "question": task, "marker": "MARKER_102.1"}],
                "execution_order": "sequential",
                "estimated_complexity": "medium"
            }
    # MARKER_102.16_END
    # MARKER_102.5_END

    # MARKER_102.6_START: Grok researcher
    async def _research(self, question: str) -> Dict[str, Any]:
        """
        Grok researcher - triggered on any "?" or needs_research.
        Returns structured insights with confidence score.
        """
        tool = self._get_llm_tool()
        if not tool:
            return {
                "insights": ["Research unavailable - LLM tool not loaded"],
                "actionable_steps": [],
                "enriched_context": question,
                "confidence": 0.5
            }

        prompt = self.prompts["researcher"]
        # MARKER_102.13: Read model from prompts config (default: OpenRouter)
        model = prompt.get("model", "x-ai/grok-4")
        temperature = prompt.get("temperature", 0.3)

        logger.info(f"[Pipeline] Researching: {question[:50]}...")

        # LLMCallTool.execute is synchronous
        result = tool.execute({
            "model": model,
            "messages": [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": f"Research this for VETKA project:\n\n{question}"}
            ],
            "temperature": temperature,
            "max_tokens": 1500,
            "inject_context": {
                "semantic_query": question,
                "semantic_limit": 5,
                "include_prefs": True,
                "compress": True
            }
        })

        # MARKER_102.18_START: Parse researcher JSON with robust extraction
        try:
            if not result.get("success"):
                logger.warning(f"[Pipeline] Researcher LLM call failed: {result.get('error')}")
                raise ValueError(result.get("error", "Unknown error"))

            response_text = result.get("result", {}).get("content", "{}")
            research = self._extract_json(response_text)

            # Validate and set defaults
            if "insights" not in research:
                research["insights"] = ["No specific insights"]
            if "enriched_context" not in research:
                research["enriched_context"] = response_text[:500]
            if "confidence" not in research:
                research["confidence"] = 0.7

            logger.info(f"[Pipeline] Research confidence: {research.get('confidence', 'N/A')}")
            return research

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[Pipeline] Failed to parse researcher response: {e}")
            # Fallback: use raw text as enriched context
            raw_content = result.get("result", {}).get("content", question) if result.get("success") else question
            return {
                "insights": ["See enriched_context"],
                "actionable_steps": [],
                "enriched_context": raw_content[:500] if raw_content else question,
                "confidence": 0.6
            }
    # MARKER_102.18_END
    # MARKER_102.6_END

    # MARKER_102.7_START: Subtask execution
    async def _execute_subtask(self, subtask: Subtask, phase_type: str) -> str:
        """
        Execute a single subtask with context from research.

        For research phase: returns summary
        For fix/build phases: returns code/implementation plan
        """
        tool = self._get_llm_tool()
        if not tool:
            return f"Execution skipped (no LLM): {subtask.description}"

        # Build context from research
        context_parts = []
        if subtask.context:
            if subtask.context.get("enriched_context"):
                context_parts.append(f"Research context:\n{subtask.context['enriched_context']}")
            if subtask.context.get("actionable_steps"):
                steps = "\n".join([f"- {s.get('step', s)}" for s in subtask.context["actionable_steps"]])
                context_parts.append(f"Actionable steps:\n{steps}")

        context_str = "\n\n".join(context_parts) if context_parts else "No additional context."

        # MARKER_102.13: Select model from prompts config based on phase
        # fix/build -> coder (Claude), research -> researcher (Grok)
        if phase_type in ["fix", "build"]:
            prompt = self.prompts.get("coder", {})
        else:
            prompt = self.prompts.get("researcher", {})

        model = prompt.get("model", "anthropic/claude-sonnet-4")
        temperature = prompt.get("temperature", 0.4)
        system_prompt = prompt.get("system", "Execute the subtask. Be concise.")

        # LLMCallTool.execute is synchronous
        result = tool.execute({
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""
Phase type: {phase_type}
Subtask: {subtask.description}
Marker: {subtask.marker or 'MARKER_102.X'}

{context_str}

Execute this subtask. Provide clear output."""}
            ],
            "temperature": temperature,
            "max_tokens": 2000
        })

        return result.get("response", "No response")
    # MARKER_102.7_END


# MARKER_102.8_START: Convenience functions
async def spawn_pipeline(task: str, phase_type: str = "research") -> Dict[str, Any]:
    """
    Convenience function for MCP tool.

    Usage:
        result = await spawn_pipeline("Implement UI artifacts for VetkaTree", "build")
    """
    pipeline = AgentPipeline()
    return await pipeline.execute(task, phase_type)


def get_pipeline_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get status of a pipeline task"""
    if TASKS_FILE.exists():
        tasks = json.loads(TASKS_FILE.read_text())
        return tasks.get(task_id)
    return None


def list_pipeline_tasks(limit: int = 10) -> List[Dict[str, Any]]:
    """List recent pipeline tasks"""
    if TASKS_FILE.exists():
        tasks = json.loads(TASKS_FILE.read_text())
        sorted_tasks = sorted(tasks.values(), key=lambda x: x.get("timestamp", 0), reverse=True)
        return sorted_tasks[:limit]
    return []
# MARKER_102.8_END
