"""Agent Pipeline - Fractal task orchestration for VETKA.

Implements fractal task decomposition:
Task -> Subtasks -> Sub-searches (with auto-trigger on "?")

On any unclear step, automatically triggers Grok researcher to enrich context,
then passes enriched context to coder/executor.

@status: active
@phase: 104
@depends: src/mcp/tools/llm_call_tool.py, src/mcp/tools/session_tools.py, src/mcp/tools/compound_tools.py
@used_by: src/mcp/vetka_mcp_bridge.py

MARKER_104_ELISION_PROMPTS: ELISION compression integrated for token efficiency
- ELISION = Efficient Language-Independent Symbolic Inversion of Names
- 4 levels: key abbreviation -> path compression -> whitespace -> local dictionary
- 40-60% token savings WITHOUT semantic loss
- Fully reversible with expand() and legend
"""

import json
import time
import logging
import os
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# MARKER_104_PARALLEL_1: Semaphore control for parallel pipeline execution
# Phase 104.2: MAX_PARALLEL_PIPELINES controls concurrent subtask execution
# Default: 5 pipelines max to protect M4 Pro from overload (Grok Phase 103 Audit recommendation)
# Override via environment: VETKA_MAX_PARALLEL=10
MAX_PARALLEL_PIPELINES = int(os.getenv("VETKA_MAX_PARALLEL", "5"))
_pipeline_semaphore: Optional[asyncio.Semaphore] = None


def _get_pipeline_semaphore() -> asyncio.Semaphore:
    """Get or create the pipeline semaphore (must be called in async context)."""
    global _pipeline_semaphore
    if _pipeline_semaphore is None:
        _pipeline_semaphore = asyncio.Semaphore(MAX_PARALLEL_PIPELINES)
        logger.info(f"[Pipeline] Initialized semaphore with MAX_PARALLEL_PIPELINES={MAX_PARALLEL_PIPELINES}")
    return _pipeline_semaphore
# MARKER_104_PARALLEL_1_END

# MARKER_104_ELISION_PROMPTS_START: Import ELISION compression
from src.memory.elision import ElisionCompressor, get_elision_compressor
# MARKER_104_ELISION_PROMPTS_END

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

    def __init__(self, chat_id: Optional[str] = None, auto_write: bool = True):
        self.llm_tool = None  # Lazy load
        # MARKER_102.23_START: Short-Term Memory for context passing
        self.stm: List[Dict[str, str]] = []  # Last N subtask results
        self.stm_limit = 5  # Keep last 5 results
        # MARKER_102.23_END
        # MARKER_102.26_START: Progress streaming to chat
        self.chat_id = chat_id or "5e2198c2-8b1a-45df-807f-5c73c5496aa8"  # Default: Lightning chat
        self.progress_hooks: List[Any] = []  # Callback hooks for progress
        # MARKER_102.26_END
        # MARKER_103.5_START: Auto-write vs staging mode
        # auto_write=True: Immediately write files to disk (default)
        # auto_write=False: Only save to JSON, use retro_apply_spawn.py later
        self.auto_write = auto_write
        # MARKER_103.5_END
        # MARKER_104_ELISION_PROMPTS_START: Initialize ELISION compressor
        # ELISION = Efficient Language-Independent Symbolic Inversion of Names
        # Provides 40-60% token savings without semantic loss
        self.elision_compressor = get_elision_compressor()
        self.elision_level = 2  # Default: key abbreviation + path compression
        # MARKER_104_ELISION_PROMPTS_END
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

    # MARKER_104_ELISION_PROMPTS_START: Context compression method
    def _compress_context(self, context: Any, level: int = None) -> tuple:
        """
        Compress context using ELISION for token efficiency.

        ELISION = Efficient Language-Independent Symbolic Inversion of Names
        - Level 1: Key abbreviation only (safe, reversible)
        - Level 2: Level 1 + path compression
        - Level 3: Level 2 + whitespace removal
        - Level 4: Level 3 + local dictionary

        Args:
            context: Dict, list, or string to compress
            level: Compression level (1-4), defaults to self.elision_level

        Returns:
            Tuple of (compressed_string, legend_dict)

        Example:
            compressed, legend = self._compress_context(large_context, level=2)
            prompt = f"[Context compressed via ELISION. Legend: {legend}]\n{compressed}"
        """
        if context is None:
            return "", {}

        compression_level = level if level is not None else self.elision_level

        try:
            result = self.elision_compressor.compress(context, level=compression_level)
            logger.debug(
                f"[Pipeline] ELISION: {result.original_length} -> {result.compressed_length} chars "
                f"(ratio: {result.compression_ratio:.2f}x, ~{result.tokens_saved_estimate} tokens saved)"
            )
            return result.compressed, result.legend
        except Exception as e:
            logger.warning(f"[Pipeline] ELISION compression failed: {e}, using raw context")
            # Fallback: return original context as string
            if isinstance(context, (dict, list)):
                return json.dumps(context), {}
            return str(context), {}

    def _format_elision_prompt(self, compressed: str, legend: Dict[str, str]) -> str:
        """
        Format compressed context with ELISION awareness note for agent.

        Args:
            compressed: ELISION-compressed context string
            legend: Legend dict for expansion

        Returns:
            Formatted string with ELISION note for the agent
        """
        if not legend:
            # No compression applied, return as-is
            return compressed

        legend_str = ", ".join(f"{k}={v}" for k, v in list(legend.items())[:10])
        if len(legend) > 10:
            legend_str += f", ... (+{len(legend) - 10} more)"

        return f"""[Context compressed via ELISION Level {self.elision_level}. Legend: {legend_str}]
Note: ELISION preserves all semantic meaning. Use expand() mentally if needed.

{compressed}"""
    # MARKER_104_ELISION_PROMPTS_END

    # MARKER_102.27_START: Progress emission to VETKA chat
    def _emit_progress(self, role: str, message: str, subtask_idx: int = 0, total: int = 0):
        """
        Emit progress update to VETKA chat.

        Args:
            role: @architect, @researcher, @coder, or @pipeline
            message: Status message
            subtask_idx: Current subtask index (1-based for display)
            total: Total subtasks count
        """
        try:
            import httpx

            # Format progress message
            progress = f"[{subtask_idx}/{total}] " if total > 0 else ""
            full_message = f"{role}: {progress}{message}"

            # Send to VETKA chat (fire-and-forget, don't block pipeline)
            with httpx.Client(timeout=5.0) as client:
                client.post(
                    "http://localhost:5001/api/chat/send",
                    json={
                        "group_id": self.chat_id,
                        "sender_id": "@pipeline",
                        "content": full_message,
                        "message_type": "system"
                    }
                )
            logger.debug(f"[Pipeline] Emitted: {full_message[:50]}...")
        except Exception as e:
            # Don't fail pipeline on emit errors
            logger.debug(f"[Pipeline] Emit failed (non-fatal): {e}")

        # Call registered hooks
        for hook in self.progress_hooks:
            try:
                hook(role, message, subtask_idx, total)
            except Exception as e:
                logger.debug(f"[Pipeline] Hook error: {e}")
    # MARKER_102.27_END

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

    # MARKER_102.25_START: STM (Short-Term Memory) helpers
    def _add_to_stm(self, marker: str, result: str):
        """Add subtask result to short-term memory"""
        self.stm.append({
            "marker": marker,
            "result": result[:500] if result else ""  # Truncate for efficiency
        })
        # Keep only last N
        if len(self.stm) > self.stm_limit:
            self.stm.pop(0)

    def _get_stm_summary(self) -> str:
        """Get summary of previous subtask results for context injection"""
        if not self.stm:
            return ""

        summary_parts = ["Previous results:"]
        for item in self.stm[-3:]:  # Last 3 for brevity
            summary_parts.append(f"- [{item['marker']}]: {item['result'][:200]}...")

        return "\n".join(summary_parts)
    # MARKER_102.25_END
    # MARKER_102.3_END

    # MARKER_103.4_START: Extract code blocks and write files to disk
    def _extract_and_write_files(self, content: str, subtask: Subtask) -> List[str]:
        """
        Extract code blocks from LLM response and write to disk.

        Spawn agents write ISOLATED modules (src/voice/, src/new_feature/).
        Integration with main VETKA code is done manually after review.

        Args:
            content: LLM response containing code blocks
            subtask: Subtask with description and marker

        Returns:
            List of created file paths
        """
        import re
        from pathlib import Path

        files_created: List[str] = []

        # Pattern to match code blocks: ```[lang]\ncode\n```
        pattern = r'```(?:python|py|javascript|js|typescript|ts|)?\s*\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

        if not matches:
            logger.debug("[Pipeline] No code blocks found in response")
            return files_created

        for i, code_block in enumerate(matches):
            code = code_block.strip()
            if not code:
                continue

            # Determine filepath from subtask description
            # e.g., "Create src/voice/config.py" → src/voice/config.py
            filepath = None
            if subtask.description:
                path_match = re.search(
                    r'(src/[^\s]+?\.(?:py|js|ts|tsx|md|json))',
                    subtask.description,
                    re.IGNORECASE
                )
                if path_match:
                    filepath = path_match.group(1)

            # Fallback: Use MARKER or generic name
            if not filepath:
                marker = getattr(subtask, 'marker', f'file_{i+1}')
                # Clean marker for filename
                safe_marker = re.sub(r'[^\w\-_.]', '_', str(marker))
                filepath = f"src/spawn_output/{safe_marker}.py"

            # Ensure directory exists and write file
            try:
                path_obj = Path(filepath)
                path_obj.parent.mkdir(parents=True, exist_ok=True)
                path_obj.write_text(code, encoding='utf-8')
                files_created.append(filepath)
                logger.info(f"[Pipeline] Spawn created: {filepath} ({len(code)} chars)")

            except Exception as e:
                logger.error(f"[Pipeline] Failed to write {filepath}: {e}")
                # Fallback to staging directory
                try:
                    fallback_dir = Path("data/spawn_staging")
                    fallback_dir.mkdir(parents=True, exist_ok=True)
                    fallback_path = fallback_dir / Path(filepath).name
                    fallback_path.write_text(code, encoding='utf-8')
                    files_created.append(str(fallback_path))
                    logger.warning(f"[Pipeline] Written to fallback: {fallback_path}")
                except Exception as e2:
                    logger.error(f"[Pipeline] Fallback also failed: {e2}")

        return files_created
    # MARKER_103.4_END

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

        # MARKER_102.28_START: Progress emission during execution
        self._emit_progress("@pipeline", f"🚀 Starting {phase_type} pipeline...")

        try:
            # Phase 1: Architect breaks down task
            self._emit_progress("@architect", "📋 Breaking down task into subtasks...")
            plan = await self._architect_plan(task, phase_type)
            pipeline_task.subtasks = [
                Subtask(**st) if isinstance(st, dict) else st
                for st in plan.get("subtasks", [])
            ]
            total_subtasks = len(pipeline_task.subtasks)
            self._emit_progress("@architect", f"✅ Plan ready: {total_subtasks} subtasks")
            pipeline_task.status = "executing"
            self._update_task(pipeline_task)

            # MARKER_102.24_START: Phase 2 with STM context passing
            # Phase 2: Execute each subtask (with research triggers + STM)
            self.stm = []  # Reset STM for new pipeline

            # MARKER_104_PARALLEL_2: Check execution order and branch accordingly
            execution_order = plan.get("execution_order", "sequential")

            if execution_order == "parallel":
                # Phase 104.2: Parallel execution with semaphore control
                await self._execute_subtasks_parallel(
                    pipeline_task, phase_type, total_subtasks
                )
            else:
                # Default: Sequential execution (safe, preserves STM context passing)
                await self._execute_subtasks_sequential(
                    pipeline_task, phase_type, total_subtasks
                )
            # MARKER_104_PARALLEL_2_END
            # MARKER_102.24_END

            # Phase 3: Compile results
            pipeline_task.status = "done"
            pipeline_task.results = {
                "plan": plan,
                "subtasks_completed": len([s for s in pipeline_task.subtasks if s.status == "done"]),
                "subtasks_total": len(pipeline_task.subtasks),
                "execution_order": plan.get("execution_order", "sequential")
            }
            self._update_task(pipeline_task)

            completed = pipeline_task.results['subtasks_completed']
            total = pipeline_task.results['subtasks_total']
            logger.info(f"[Pipeline] Completed: {completed}/{total} subtasks")
            self._emit_progress("@pipeline", f"🎉 Pipeline complete! {completed}/{total} subtasks done")
            # MARKER_102.28_END

            return asdict(pipeline_task)

        except Exception as e:
            logger.error(f"[Pipeline] Failed: {e}")
            pipeline_task.status = "failed"
            pipeline_task.results = {"error": str(e)}
            self._update_task(pipeline_task)
            self._emit_progress("@pipeline", f"❌ Pipeline failed: {str(e)[:50]}")
            return asdict(pipeline_task)
    # MARKER_102.4_END

    # MARKER_104_PARALLEL_3: Sequential execution method (STM context passing)
    async def _execute_subtasks_sequential(
        self, pipeline_task: PipelineTask, phase_type: str, total_subtasks: int
    ):
        """
        Execute subtasks sequentially (default, safe mode).
        Preserves STM context passing between subtasks.
        """
        for i, subtask in enumerate(pipeline_task.subtasks):
            logger.info(f"[Pipeline] Subtask {i+1}/{total_subtasks}: {subtask.description[:40]}...")

            # Inject STM context from previous subtasks
            if self.stm:
                stm_summary = self._get_stm_summary()
                if subtask.context is None:
                    subtask.context = {}
                subtask.context["previous_results"] = stm_summary

            # Auto-trigger research on needs_research flag
            if subtask.needs_research:
                subtask.status = "researching"
                self._update_task(pipeline_task)
                self._emit_progress("@researcher", f"🔍 Researching: {subtask.description[:40]}...", i+1, total_subtasks)

                # Use description as question if no explicit question
                question = subtask.question or subtask.description
                research = await self._research(question)

                if subtask.context is None:
                    subtask.context = {}
                subtask.context.update(research)

                # Recursive: if researcher has further questions with low confidence
                if research.get("confidence", 1.0) < 0.7:
                    for fq in research.get("further_questions", [])[:2]:  # Max 2 recursions
                        sub_research = await self._research(fq)
                        enriched = subtask.context.get("enriched_context", "")
                        subtask.context["enriched_context"] = enriched + f"\n\nFollow-up ({fq}):\n{sub_research.get('enriched_context', '')}"

            # Execute subtask
            subtask.status = "executing"
            self._update_task(pipeline_task)
            self._emit_progress("@coder", f"⚙️ Executing: {subtask.description[:40]}...", i+1, total_subtasks)

            result = await self._execute_subtask(subtask, phase_type)
            subtask.result = result
            subtask.status = "done"
            self._emit_progress("@coder", f"✅ Done: {subtask.marker or f'step_{i+1}'}", i+1, total_subtasks)

            # Add to STM for next subtask
            self._add_to_stm(subtask.marker or f"step_{i+1}", result)

            self._update_task(pipeline_task)
    # MARKER_104_PARALLEL_3_END

    # MARKER_104_PARALLEL_4: Parallel execution with asyncio.gather()
    async def _execute_subtasks_parallel(
        self, pipeline_task: PipelineTask, phase_type: str, total_subtasks: int
    ):
        """
        Execute subtasks in parallel with semaphore control.

        Phase 104.2: Uses MAX_PARALLEL_PIPELINES to limit concurrency.
        Note: STM context is not passed between parallel subtasks (by design).
        """
        semaphore = _get_pipeline_semaphore()
        self._emit_progress(
            "@pipeline",
            f"⚡ Parallel execution mode (max {MAX_PARALLEL_PIPELINES} concurrent)"
        )
        logger.info(f"[Pipeline] Parallel execution with semaphore limit={MAX_PARALLEL_PIPELINES}")

        async def run_subtask_with_limit(idx: int, subtask: Subtask) -> tuple[int, str]:
            """Run single subtask with semaphore limit."""
            async with semaphore:
                logger.info(f"[Pipeline] Parallel subtask {idx+1}/{total_subtasks} acquired semaphore")
                self._emit_progress("@coder", f"⚙️ [P] Executing: {subtask.description[:35]}...", idx+1, total_subtasks)

                # Auto-trigger research if needed (inside semaphore)
                if subtask.needs_research:
                    subtask.status = "researching"
                    self._emit_progress("@researcher", f"🔍 [P] Researching: {subtask.description[:35]}...", idx+1, total_subtasks)

                    question = subtask.question or subtask.description
                    research = await self._research(question)

                    if subtask.context is None:
                        subtask.context = {}
                    subtask.context.update(research)

                    # Recursive research for low confidence
                    if research.get("confidence", 1.0) < 0.7:
                        for fq in research.get("further_questions", [])[:2]:
                            sub_research = await self._research(fq)
                            enriched = subtask.context.get("enriched_context", "")
                            subtask.context["enriched_context"] = enriched + f"\n\nFollow-up ({fq}):\n{sub_research.get('enriched_context', '')}"

                # Execute subtask
                subtask.status = "executing"
                result = await self._execute_subtask(subtask, phase_type)
                subtask.result = result
                subtask.status = "done"

                self._emit_progress("@coder", f"✅ [P] Done: {subtask.marker or f'step_{idx+1}'}", idx+1, total_subtasks)
                logger.info(f"[Pipeline] Parallel subtask {idx+1}/{total_subtasks} completed")

                return (idx, result)

        # Run all subtasks in parallel with gather
        tasks = [
            run_subtask_with_limit(i, subtask)
            for i, subtask in enumerate(pipeline_task.subtasks)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # MARKER_104_PARALLEL_5: Result merging from parallel subtasks
        # Process results and update pipeline task
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"[Pipeline] Parallel subtask failed: {res}")
                # Mark as failed but don't stop other subtasks
            elif isinstance(res, tuple):
                idx, result = res
                # Add to STM (order may vary in parallel mode)
                subtask = pipeline_task.subtasks[idx]
                self._add_to_stm(subtask.marker or f"step_{idx+1}", result)

        # Update pipeline task state
        self._update_task(pipeline_task)
    # MARKER_104_PARALLEL_5_END

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

        # MARKER_102.22_START: Fixed LLM call + context passing
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

Execute this subtask. Provide clear, actionable output."""}
            ],
            "temperature": temperature,
            "max_tokens": 2000
        })

        # Extract content from LLMCallTool response format
        if result.get("success"):
            content = result.get("result", {}).get("content", "")
            if content:
                logger.info(f"[Pipeline] Subtask result: {content[:100]}...")

                # MARKER_103.4_START: Post-process build phase - extract and write files
                # MARKER_103.5: Check auto_write flag
                # auto_write=True: Write files immediately
                # auto_write=False: Only save to JSON (use retro_apply_spawn.py later)
                if phase_type == "build" and "```" in content:
                    if self.auto_write:
                        files_created = self._extract_and_write_files(content, subtask)
                        if files_created:
                            self._emit_progress("@coder", f"📁 Created {len(files_created)} files: {', '.join(files_created)}")
                            content += f"\n\n[Pipeline Note: Created files - {', '.join(files_created)}]"
                    else:
                        # Staging mode - just log, files stay in JSON for retro_apply
                        self._emit_progress("@coder", f"📝 Code staged in JSON (auto_write=False)")
                        content += f"\n\n[Pipeline Note: Code staged - use retro_apply_spawn.py to create files]"
                # MARKER_103.4_END

                return content
            else:
                logger.warning(f"[Pipeline] Subtask returned empty content")
                return "Subtask completed (no content)"
        else:
            error = result.get("error", "Unknown error")
            logger.warning(f"[Pipeline] Subtask LLM call failed: {error}")
            return f"Error: {error}"
    # MARKER_102.22_END
    # MARKER_102.7_END


# MARKER_102.8_START: Convenience functions
async def spawn_pipeline(
    task: str,
    phase_type: str = "research",
    chat_id: Optional[str] = None,
    auto_write: bool = True
) -> Dict[str, Any]:
    """
    Convenience function for MCP tool.

    Args:
        task: Task description
        phase_type: "research" | "fix" | "build"
        chat_id: Optional chat ID for progress streaming
        auto_write: If True, write files immediately. If False, only save to JSON
                   (use retro_apply_spawn.py to create files later)

    Usage:
        # Auto-write mode (default) - files created immediately
        result = await spawn_pipeline("Implement UI artifacts", "build")

        # Staging mode - files saved to JSON, apply later after review
        result = await spawn_pipeline("Implement critical feature", "build", auto_write=False)
        # Then: python scripts/retro_apply_spawn.py --task-filter "critical"
    """
    pipeline = AgentPipeline(chat_id=chat_id, auto_write=auto_write)
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
