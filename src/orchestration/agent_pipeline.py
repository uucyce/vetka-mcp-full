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


# MARKER_126.5A: Custom exception for pipeline cancellation
class PipelineCancelled(Exception):
    """Raised when pipeline is cancelled via stop button or API."""
    pass


# MARKER_123.1_IMPORT: FC loop for coder function calling
try:
    from src.tools.fc_loop import execute_fc_loop, get_coder_tool_schemas, MAX_FC_TURNS_CODER
    FC_LOOP_AVAILABLE = True
except ImportError:
    FC_LOOP_AVAILABLE = False
    logger.debug("[Pipeline] FC loop not available, coder will use one-shot mode")

# MARKER_104_PARALLEL_1: Semaphore control for parallel pipeline execution
# Phase 104.2: MAX_PARALLEL_PIPELINES controls concurrent subtask execution
# Default: 5 pipelines max to protect M4 Pro from overload (Grok Phase 103 Audit recommendation)
# Override via environment: VETKA_MAX_PARALLEL=10
MAX_PARALLEL_PIPELINES = int(os.getenv("VETKA_MAX_PARALLEL", "5"))

# MARKER_117.5B: Auto context reset threshold to combat drift
# Cursor insight: "Periodic fresh starts to combat drift"
# After this many subtasks, STM is compressed to a summary and reset.
# Prevents context drift in long pipeline runs (10+ subtasks).
MAX_STM_BEFORE_RESET = int(os.getenv("VETKA_STM_RESET_THRESHOLD", "10"))

# MARKER_118.8_PIPELINE_CONSTANTS: Extracted from hardcoded values
PIPELINE_STM_LIMIT = int(os.getenv("VETKA_PIPELINE_STM_LIMIT", "5"))
PIPELINE_ELISION_LEVEL = int(os.getenv("VETKA_PIPELINE_ELISION_LEVEL", "2"))
PIPELINE_COMPRESS_THRESHOLD = int(os.getenv("VETKA_PIPELINE_COMPRESS_THRESHOLD", "1000"))
PIPELINE_TRUNCATE_RESULT = int(os.getenv("VETKA_PIPELINE_TRUNCATE_RESULT", "500"))
PIPELINE_STM_SUMMARY_WINDOW = int(os.getenv("VETKA_PIPELINE_STM_SUMMARY_WINDOW", "3"))
PIPELINE_SUMMARY_TRUNCATE = int(os.getenv("VETKA_PIPELINE_SUMMARY_TRUNCATE", "200"))

# MARKER_122: Feedback loop constants
MAX_CODER_RETRIES = int(os.getenv("VETKA_MAX_CODER_RETRIES", "2"))
MAX_ARCHITECT_REPLANS = int(os.getenv("VETKA_MAX_ARCHITECT_REPLANS", "1"))
VERIFIER_PASS_THRESHOLD = float(os.getenv("VETKA_VERIFIER_PASS_THRESHOLD", "0.75"))
# MARKER_122_END

# MARKER_133.C33B: Per-phase timeouts (seconds) — prevents pipeline hangs
PHASE_TIMEOUTS = {
    "scout": int(os.getenv("VETKA_TIMEOUT_SCOUT", "30")),
    "architect": int(os.getenv("VETKA_TIMEOUT_ARCHITECT", "60")),
    "researcher": int(os.getenv("VETKA_TIMEOUT_RESEARCHER", "45")),
    "coder": int(os.getenv("VETKA_TIMEOUT_CODER", "90")),
    "verifier": int(os.getenv("VETKA_TIMEOUT_VERIFIER", "30")),
}
# MARKER_133.C33B_END

# MARKER_119.2: Import for pipeline-to-STMBuffer bridge
from src.memory.stm_buffer import get_stm_buffer

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
# MARKER_117_2B_SANDBOX: Primary path + TMPDIR fallback for MCP sandbox
TASKS_FILE = Path(__file__).parent.parent.parent / "data" / "pipeline_tasks.json"
_TASKS_FILE_FALLBACK = Path(os.environ.get('TMPDIR', '/tmp')) / "vetka_pipeline_tasks.json"
PROMPTS_FILE = Path(__file__).parent.parent.parent / "data" / "templates" / "pipeline_prompts.json"
# MARKER_117_PRESETS: Presets config file
PRESETS_FILE = Path(__file__).parent.parent.parent / "data" / "templates" / "model_presets.json"
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
    # MARKER_104_STREAM_VISIBILITY: Visibility control for subtasks
    visible: bool = True  # Show progress in UI
    stream_result: bool = True  # Stream completion to chat
    # MARKER_122: Feedback loop fields
    retry_count: int = 0
    # MARKER_127.1A: Changed to Dict to store full verifier result (confidence, passed, issues)
    verifier_feedback: Optional[Dict] = None
    escalated: bool = False


# MARKER_104_STREAM_VISIBILITY: PipelineTask with visibility control
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
    # MARKER_104_STREAM_VISIBILITY: Visibility control for pipeline tasks
    visible_to_user: bool = True  # Show in chat UI
    stream_level: str = "summary"  # "full" | "summary" | "silent"
    highlight_artifacts: bool = True  # Highlight code blocks in output

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

    def __init__(self, chat_id: Optional[str] = None, auto_write: bool = True,
                 provider: Optional[str] = None, preset: Optional[str] = None,
                 sio=None, sid: Optional[str] = None,
                 async_mode: bool = False, http_client=None, ws_broadcaster=None):
        self.llm_tool = None  # Lazy load
        # MARKER_129.4: Async mode for MYCELIUM (native async LLM calls)
        self.async_mode = async_mode
        self._http_client = http_client      # MyceliumHTTPClient for chat relay
        self._ws_broadcaster = ws_broadcaster  # MyceliumWSBroadcaster for DevPanel
        # MARKER_126.5A: Cancellation support — asyncio Event for stop-button
        import asyncio as _asyncio
        self._cancelled = _asyncio.Event()
        self._cancel_reason: str = ""
        # MARKER_117_PROVIDER: Provider override for all pipeline LLM calls
        # If set, all agents use this provider via model_source routing
        self.provider_override = provider
        # MARKER_117_PRESETS: Preset team configuration
        self.preset_name = preset
        self.preset_models: Optional[Dict[str, str]] = None
        # MARKER_117.6C: Track last used model for attribution in chat
        self._last_used_model: str = ""
        # MARKER_126.0A: Pipeline statistics counters
        self._llm_calls: int = 0
        self._tokens_in: int = 0
        self._tokens_out: int = 0
        # MARKER_102.23_START: Short-Term Memory for context passing
        self.stm: List[Dict[str, str]] = []  # Last N subtask results
        self.stm_limit = PIPELINE_STM_LIMIT
        # MARKER_102.23_END
        # MARKER_102.26_START: Progress streaming to chat
        # MARKER_117.8C: No default UUID — None means use sio/sid or skip emit
        self.chat_id = chat_id
        self.progress_hooks: List[Any] = []  # Callback hooks for progress
        # MARKER_117.8A: SocketIO direct emit for solo chats (non-blocking, instant)
        self.sio = sio
        self.sid = sid
        # MARKER_102.26_END
        # MARKER_103.5_START: Auto-write vs staging mode
        # auto_write=True: Immediately write files to disk (default)
        # auto_write=False: Only save to JSON, use retro_apply_myc.py later
        self.auto_write = auto_write
        # MARKER_103.5_END
        # MARKER_104_ELISION_PROMPTS_START: Initialize ELISION compressor
        # ELISION = Efficient Language-Independent Symbolic Inversion of Names
        # Provides 40-60% token savings without semantic loss
        self.elision_compressor = get_elision_compressor()
        self.elision_level = PIPELINE_ELISION_LEVEL
        # MARKER_104_ELISION_PROMPTS_END
        self._load_prompts()
        self._apply_preset()

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
}

IMPORTANT - estimated_complexity determines which team tier handles the task:
- "low": simple tasks, single file, trivial logic → bronze team (fast/cheap models)
- "medium": standard tasks, 2-5 files, moderate logic → silver team (balanced)
- "high": complex tasks, 5+ files, architectural decisions → gold team (best models)
Choose carefully — this directly affects quality and cost of execution."""
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

    # MARKER_117_PRESETS: Apply preset model overrides
    def _apply_preset(self):
        """Load and apply preset team configuration if specified.

        MARKER_117.4A: If preset_name is None, auto-loads default_preset from
        model_presets.json. This ensures @dragon always uses the Asian team
        (dragon_silver) instead of falling back to Claude.
        """
        if not PRESETS_FILE.exists():
            logger.warning(f"[Pipeline] Presets file not found: {PRESETS_FILE}")
            return

        try:
            presets_data = json.loads(PRESETS_FILE.read_text())
        except Exception as e:
            logger.error(f"[Pipeline] Failed to read presets file: {e}")
            return

        # MARKER_117.4A: Auto-load default preset when none specified
        if not self.preset_name:
            self.preset_name = presets_data.get("default_preset")
            if not self.preset_name:
                return
            logger.info(f"[Pipeline] Auto-loaded default preset: '{self.preset_name}'")

        preset = presets_data.get("presets", {}).get(self.preset_name)
        if not preset:
            logger.warning(f"[Pipeline] Preset '{self.preset_name}' not found. Available: {list(presets_data.get('presets', {}).keys())}")
            return

        # Apply model overrides from preset
        # MARKER_119.4: "scout" role now active — pipeline_prompts.json has scout key
        roles = preset.get("roles", {})
        for role_name, model_name in roles.items():
            if role_name in self.prompts:
                self.prompts[role_name]["model"] = model_name
                logger.info(f"[Pipeline] Preset '{self.preset_name}': {role_name} → {model_name}")

        # Apply provider override from preset (if not already set explicitly)
        if not self.provider_override and preset.get("provider"):
            self.provider_override = preset["provider"]
            logger.info(f"[Pipeline] Preset '{self.preset_name}': provider → {self.provider_override}")

        self.preset_models = roles
        logger.info(f"[Pipeline] Applied preset '{self.preset_name}': {preset.get('description', '')}")
    # MARKER_117_PRESETS_END

    # MARKER_133.C33B: Per-phase timeout wrapper
    async def _safe_phase(self, phase_name: str, coro) -> Optional[Any]:
        """Execute pipeline phase with timeout. Returns None on timeout (non-fatal for most phases).

        MARKER_133.C33B: Each phase gets a configurable timeout.
        If exceeded — skip and continue (except architect, which aborts).
        """
        timeout = PHASE_TIMEOUTS.get(phase_name, 60)
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"[Pipeline] Phase '{phase_name}' timed out after {timeout}s — skipping")
            await self._emit_progress("system", f"Phase {phase_name} timed out ({timeout}s) — continuing")
            return None
        except Exception as e:
            logger.error(f"[Pipeline] Phase '{phase_name}' failed: {e}")
            return None
    # MARKER_133.C33B_END

    # MARKER_119.4: Scout role — codebase scan before Architect
    # MARKER_124.7B: Pre-fetch via VetkaSearchCodeTool (ripgrep) before Scout LLM call
    async def _scout_scan(self, task: str, phase_type: str) -> Optional[Dict[str, Any]]:
        """Run scout to gather codebase context before architect planning.

        MARKER_124.7B: Two-step scout:
        1. Pre-fetch: VetkaSearchCodeTool (ripgrep + name filter) → real file list
        2. LLM call: Scout model receives pre-fetched files → produces structured JSON

        Returns structured JSON with context_summary, relevant_files,
        patterns_found, risks, recommendations.
        """
        if "scout" not in self.prompts:
            logger.debug("[Pipeline] Scout role not configured, skipping")
            return None

        tool = self._get_llm_tool()
        if not tool:
            return None

        prompt = self.prompts["scout"]
        model = prompt.get("model", "anthropic/claude-haiku-4.5")
        temperature = prompt.get("temperature", 0.1)

        # MARKER_124.7B: Pre-fetch real files via ripgrep before Scout LLM call
        prefetch_context = await self._scout_prefetch(task)
        # MARKER_128.1A: Store prefetch for project context extraction
        self._last_prefetch_context = prefetch_context

        user_content = f"Phase type: {phase_type}\n\nTask to scout:\n{task}"
        if prefetch_context:
            user_content += f"\n\n--- Code search results (from ripgrep) ---\n{prefetch_context}"

        call_args = {
            "model": model,
            "messages": [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": user_content}
            ],
            "temperature": temperature,
            "max_tokens": 1000,
            "inject_context": {
                "chat_id": self.chat_id,
                "chat_limit": 3,
                "semantic_query": task,
                "semantic_limit": 5,
                "include_prefs": False,
                "compress": True
            }
        }
        if self.provider_override:
            call_args["model_source"] = self.provider_override

        # MARKER_129.4: Dual-mode LLM call (async in MYCELIUM, sync in VETKA)
        if getattr(self, 'async_mode', False):
            result = await tool.execute(call_args)
        else:
            result = tool.execute(call_args)
        self._track_llm_call(result)
        self._last_used_model = result.get("result", {}).get("model", model)

        try:
            if not result.get("success"):
                logger.warning(f"[Pipeline] Scout LLM call failed: {result.get('error')}")
                return None
            response_text = result.get("result", {}).get("content", "{}")
            scout_data = self._extract_json(response_text)
            # MARKER_128.1A: Inject detected project context into scout_data
            # so coder sees "Detected imports: zustand, react, three" in context
            if hasattr(self, '_last_prefetch_context') and self._last_prefetch_context:
                # Extract "--- Project context ---" section if present
                pctx = self._last_prefetch_context
                if "--- Project context ---" in pctx:
                    ctx_line = pctx.split("--- Project context ---\n")[-1].split("\n---")[0].strip()
                    if ctx_line:
                        scout_data["project_context"] = ctx_line
            logger.info(
                f"[Pipeline] Scout found {len(scout_data.get('relevant_files', []))} files, "
                f"{len(scout_data.get('patterns_found', []))} patterns"
            )
            return scout_data
        except Exception as e:
            logger.warning(f"[Pipeline] Scout parse failed (non-fatal): {e}")
            return None

    async def _scout_prefetch(self, task: str) -> Optional[str]:
        """Pre-fetch relevant files + markers + code snippets via VetkaSearchCodeTool.

        MARKER_124.7B: Extracts keywords, runs ripgrep search.
        MARKER_124.8C: Scans found code files for existing MARKER_ tags.
        MARKER_124.9A: Reads file snippets with line numbers so Scout can
        place marker_map entries at exact line positions.
        """
        try:
            from src.tools.registry import VetkaSearchCodeTool
            code_tool = VetkaSearchCodeTool()

            # Extract search terms: filenames, identifiers, keywords
            keywords = self._extract_search_keywords(task)
            if not keywords:
                return None

            all_paths = set()
            code_file_paths = []  # Absolute paths for marker scanning
            results_text = []

            for kw in keywords[:3]:  # Max 3 searches to keep fast
                result = await code_tool.execute(query=kw, limit=5)
                if result.success and result.result:
                    for line in str(result.result).split("\n"):
                        line = line.strip()
                        if line and ("/" in line) and not line.startswith("Code search"):
                            path = line.split(" — ")[0].strip()
                            if path and path not in all_paths:
                                all_paths.add(path)
                                results_text.append(line)
                                # Collect code file paths for marker scanning
                                if any(path.endswith(ext) for ext in ('.ts', '.tsx', '.py', '.rs', '.jsx', '.js')):
                                    abs_path = path
                                    if not path.startswith("/"):
                                        abs_path = f"{code_tool._PROJECT_ROOT}/{path}"
                                    code_file_paths.append(abs_path)

            if not results_text:
                return None

            # MARKER_124.8C: Scan markers in found code files
            marker_section = self._scan_markers_in_files(code_file_paths[:5])

            # MARKER_124.9A: Read file snippets with line numbers for marker placement
            snippet_section = self._read_file_snippets(code_file_paths[:3], max_lines=60)

            # MARKER_128.1A: Detect project context (imports, frameworks) from found files
            project_ctx = self._detect_project_context(code_file_paths)

            output = "\n".join(results_text[:10])
            if project_ctx:
                output += f"\n\n--- Project context ---\n{project_ctx}"
            if marker_section:
                output += f"\n\n--- Existing markers in these files ---\n{marker_section}"
            if snippet_section:
                output += f"\n\n--- Code snippets (with line numbers for marker_map placement) ---\n{snippet_section}"
                output += "\n\nIMPORTANT: Use these line numbers to create your marker_map. " \
                          "Place markers at exact lines where the Coder should INSERT or MODIFY code. " \
                          "The Coder will use vetka_read_file(path, marker='MARKER_SCOUT_X') to jump straight to those locations."

            logger.info(f"[Pipeline] Scout pre-fetch: {len(results_text)} files, "
                        f"{len(marker_section.splitlines()) if marker_section else 0} markers, "
                        f"{len(snippet_section.splitlines()) if snippet_section else 0} snippet lines ({keywords})")
            return output
        except Exception as e:
            logger.debug(f"[Pipeline] Scout pre-fetch failed (non-fatal): {e}")
            return None

    @staticmethod
    def _scan_markers_in_files(file_paths: list) -> str:
        """Scan code files for MARKER_ tags and return summary.

        MARKER_124.8C: Reads first 1000 lines of each file, finds MARKER_
        comments, returns formatted list for Scout LLM context.
        """
        from pathlib import Path
        import re

        marker_lines = []
        for fpath in file_paths:
            p = Path(fpath)
            if not p.exists():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                lines = text.splitlines()[:1000]
                name = p.name
                for i, line in enumerate(lines):
                    # Find MARKER_ tags (both // and # comment styles)
                    match = re.search(r'(?://|#)\s*(MARKER_\S+)', line)
                    if match:
                        marker = match.group(1).rstrip(":")
                        desc = line.strip()[:80]
                        marker_lines.append(f"  {name}:{i+1} — {marker} — {desc}")
            except Exception:
                continue

        return "\n".join(marker_lines[:20]) if marker_lines else ""

    @staticmethod
    def _read_file_snippets(file_paths: list, max_lines: int = 60) -> str:
        """Read first N lines of code files with line numbers for Scout.

        MARKER_124.9A: Scout needs to see actual code with line numbers
        to place marker_map entries at exact positions. Returns numbered
        snippets of the most relevant files (max 3 files, max_lines each).
        """
        from pathlib import Path

        snippets = []
        for fpath in file_paths[:3]:
            p = Path(fpath)
            if not p.exists():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                lines = text.splitlines()
                total = len(lines)
                show_lines = min(max_lines, total)
                numbered = []
                for i in range(show_lines):
                    numbered.append(f"  {i+1:4d} | {lines[i]}")
                snippet = "\n".join(numbered)
                rel_name = p.name
                snippets.append(f"[{rel_name}] ({total} lines total, showing 1-{show_lines})\n{snippet}")
            except Exception:
                continue

        return "\n\n".join(snippets) if snippets else ""

    # MARKER_128.1A: Detect project stack from import statements in found files
    @staticmethod
    def _detect_project_context(file_paths: list) -> str:
        """Detect project stack (imports, frameworks) from code files.

        MARKER_128.1A: Reads import statements from found files to tell
        the coder what frameworks/libraries the project actually uses.
        This prevents the coder from guessing wrong imports (e.g. MobX vs Zustand).
        """
        from pathlib import Path
        import re

        imports_found = set()
        for fpath in file_paths[:5]:
            p = Path(fpath)
            if not p.exists():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
                lines = text.splitlines()[:100]  # First 100 lines enough for imports
                for line in lines:
                    # TypeScript/JavaScript: import ... from '...'
                    m = re.search(r"from\s+['\"]([^'\"]+)['\"]", line)
                    if m:
                        pkg = m.group(1)
                        # Only external packages (not relative ./  ../)
                        if not pkg.startswith(".") and not pkg.startswith("/"):
                            imports_found.add(pkg.split("/")[0])
                    # Python: from ... import ... / import ...
                    m = re.search(r"^(?:from|import)\s+([\w.]+)", line)
                    if m:
                        pkg = m.group(1).split(".")[0]
                        if pkg not in ("src", "os", "sys", "json", "re", "typing", "pathlib", "logging",
                                       "dataclasses", "datetime", "time", "asyncio", "collections"):
                            imports_found.add(pkg)
            except Exception:
                continue

        if not imports_found:
            return ""

        # Format as concise context line
        return f"Detected imports in project files: {', '.join(sorted(imports_found)[:15])}"
    # MARKER_128.1A_END

    @staticmethod
    def _extract_search_keywords(task: str) -> list:
        """Extract filenames and code identifiers from task description.

        MARKER_124.7B: Looks for:
        - Explicit filenames (useStore.ts, ChatPanel.tsx)
        - camelCase/PascalCase identifiers (toggleBookmark, ChatPanel)
        - Quoted terms ('bookmarked', "zustand")
        """
        import re
        keywords = []

        # 1. Explicit file paths/names (e.g., client/src/store/useStore.ts)
        file_patterns = re.findall(r'[\w/.-]+\.(?:ts|tsx|js|jsx|py|rs|css|scss)\b', task)
        for fp in file_patterns:
            name = fp.split("/")[-1]  # Just filename
            if name not in keywords:
                keywords.append(name)

        # 2. CamelCase/PascalCase identifiers (e.g., toggleBookmark, ChatPanel)
        identifiers = re.findall(r'\b[a-z]+(?:[A-Z][a-z]+)+\b', task)  # camelCase
        identifiers += re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', task)  # PascalCase
        for ident in identifiers:
            if ident not in keywords and len(ident) > 3:
                keywords.append(ident)

        # 3. Quoted terms
        quoted = re.findall(r'[\'"]([^"\']{2,30})[\'"]', task)
        for q in quoted:
            if q not in keywords:
                keywords.append(q)

        return keywords[:5]
    # MARKER_119.4_END

    # MARKER_117.4C: Auto-tier resolution
    def _resolve_tier(self, complexity: str) -> Optional[str]:
        """Map architect's estimated_complexity to a dragon tier preset.

        Reads _tier_map from model_presets.json:
        - "low"    → dragon_bronze (fast/cheap)
        - "medium" → dragon_silver (standard)
        - "high"   → dragon_gold  (best models)

        Returns None if no tier mapping found or presets unavailable.
        """
        if not PRESETS_FILE.exists():
            return None
        try:
            data = json.loads(PRESETS_FILE.read_text())
            # MARKER_118.10_TITAN_TIER: Use titan tier map if current preset is a titan
            if self.preset_name and self.preset_name.startswith("titan_"):
                tier_map = data.get("_titan_tier_map", {
                    "low": "titan_lite",
                    "medium": "titan_core",
                    "high": "titan_prime"
                })
            else:
                tier_map = data.get("_tier_map", {
                    "low": "dragon_bronze",
                    "medium": "dragon_silver",
                    "high": "dragon_gold"
                })
            return tier_map.get(complexity)
        except Exception:
            return None
    # MARKER_117.4C_END

    # MARKER_122.1_START: Parallel recon — Scout + Researcher concurrently
    async def _parallel_recon(self, task: str, phase_type: str) -> tuple:
        """Run Scout and Researcher in parallel for initial reconnaissance.

        Returns (scout_context, research_context) — either can be None on failure.
        MARKER_133.C33B: Wrapped with per-phase timeouts.
        """
        try:
            # MARKER_133.C33B: Apply phase timeouts to scout and researcher
            results = await asyncio.gather(
                self._safe_phase("scout", self._scout_scan(task, phase_type)) if "scout" in self.prompts else asyncio.sleep(0),
                self._safe_phase("researcher", self._research(task)),
                return_exceptions=True
            )
            scout_ctx = results[0] if not isinstance(results[0], (Exception, type(None), float)) else None
            research_ctx = results[1] if not isinstance(results[1], (Exception, type(None), float)) else None
            return (scout_ctx, research_ctx)
        except Exception as e:
            logger.warning(f"[Pipeline] Parallel recon failed: {e}")
            return (None, None)
    # MARKER_122.1_END

    # MARKER_122.2_START: Verify subtask after coder execution
    async def _verify_subtask(self, subtask, coder_result: str, phase_type: str) -> Dict[str, Any]:
        """Call verifier model to evaluate coder output.

        Returns:
            {"passed": bool, "issues": [], "suggestions": [], "confidence": float, "severity": "minor"|"major"}
        Graceful degradation: on any failure returns {"passed": True}.
        """
        default_pass = {"passed": True, "issues": [], "suggestions": [], "confidence": 0.5, "severity": "minor"}
        try:
            tool = self._get_llm_tool()
            if not tool or "verifier" not in self.prompts:
                return default_pass

            prompt = self.prompts["verifier"]
            model = prompt.get("model", "anthropic/claude-sonnet-4")
            temperature = prompt.get("temperature", 0.1)

            # MARKER_125.0A: Increased context limit 3000→6000 chars for better verification
            # Also inject original file context if available from Scout report
            coder_output = str(coder_result)[:6000]
            original_context = ""
            if subtask.context and subtask.context.get("scout_report"):
                scout = subtask.context["scout_report"]
                files = scout.get("relevant_files", [])[:3]
                if files:
                    original_context = f"\n\nOriginal target files: {', '.join(files)}"
                marker_map = scout.get("marker_map", [])
                if marker_map and isinstance(marker_map, list):
                    markers = "; ".join(
                        f"{m.get('marker_id', '?')}={m.get('file', '?')}:{m.get('line', '?')} [{m.get('action', '?')}]"
                        for m in marker_map[:3] if isinstance(m, dict)
                    )
                    original_context += f"\nMarker rails: {markers}"

            user_content = (
                f"Phase type: {phase_type}\n\n"
                f"Subtask: {subtask.description}\n\n"
                f"Coder output:\n{coder_output}"
                f"{original_context}"
            )

            call_args = {
                "model": model,
                "messages": [
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": user_content}
                ],
                "temperature": temperature,
                "max_tokens": 1000
            }
            if self.provider_override:
                call_args["model_source"] = self.provider_override

            # MARKER_129.4: Dual-mode LLM call
            if getattr(self, 'async_mode', False):
                result = await tool.execute(call_args)
            else:
                result = tool.execute(call_args)
            self._track_llm_call(result)
            self._last_used_model = result.get("result", {}).get("model", model)

            if not result.get("success"):
                logger.warning(f"[Pipeline] Verifier LLM call failed: {result.get('error')}")
                return default_pass

            response_text = result.get("result", {}).get("content", "{}")
            verification = self._extract_json(response_text)

            # MARKER_127.3: Normalize parsed result — ensure 'passed' field exists
            # If verifier returned partial JSON (e.g. {"severity":"major"} without "passed"),
            # default to False so retry loop catches it
            if "passed" not in verification:
                verification["passed"] = False
                verification.setdefault("issues", []).append("Verifier did not return 'passed' field")
            if "confidence" not in verification:
                verification["confidence"] = 0.3
            if "issues" not in verification:
                verification["issues"] = []

            # Auto-determine severity if not set by model
            if "severity" not in verification:
                issues = verification.get("issues", [])
                confidence = verification.get("confidence", 0.5)
                verification["severity"] = "minor" if len(issues) <= 2 and confidence >= 0.6 else "major"

            # MARKER_125.0B: Confidence gate — auto-fail if confidence below threshold
            # even when model says passed=true (low-confidence passes are unreliable)
            confidence = verification.get("confidence", 0.5)
            if verification.get("passed", False) and confidence < VERIFIER_PASS_THRESHOLD:
                logger.info(
                    f"[Pipeline] Verifier confidence {confidence:.2f} < threshold {VERIFIER_PASS_THRESHOLD} — "
                    f"auto-failing despite passed=true"
                )
                verification["passed"] = False
                verification["issues"].append(
                    f"Low confidence ({confidence:.2f} < {VERIFIER_PASS_THRESHOLD}) — needs closer review"
                )
                verification["severity"] = "minor"  # Don't escalate, just retry

            return verification

        except Exception as e:
            logger.warning(f"[Pipeline] Verifier failed (graceful degradation): {e}")
            return default_pass
    # MARKER_122.2_END

    # MARKER_122.3_START: Retry coder with verifier feedback
    async def _retry_coder(self, subtask, verifier_result: Dict, phase_type: str) -> str:
        """Re-run coder with verifier feedback injected into context."""
        subtask.retry_count += 1
        if subtask.context is None:
            subtask.context = {}

        # Format verifier feedback for coder
        issues = verifier_result.get("issues", [])
        suggestions = verifier_result.get("suggestions", [])
        feedback = f"VERIFIER FEEDBACK (attempt {subtask.retry_count}):\n"
        feedback += f"Issues: {'; '.join(str(i) for i in issues)}\n"
        if suggestions:
            feedback += f"Suggestions: {'; '.join(str(s) for s in suggestions)}\n"
        feedback += f"Previous output was rejected. Fix the issues above."

        subtask.context["verifier_feedback"] = feedback
        # MARKER_127.1A: Store full verifier dict for stats collection
        subtask.verifier_feedback = verifier_result

        await self._emit_progress(
            "@verifier",
            f"⚠️ Issues found, retrying coder (attempt {subtask.retry_count}/{MAX_CODER_RETRIES})",
            model=self._last_used_model
        )

        result = await self._execute_subtask(subtask, phase_type)
        return result
    # MARKER_122.3_END

    # MARKER_122.4_START: Upgrade coder tier on repeated failures
    def _upgrade_coder_tier(self) -> bool:
        """Upgrade coder to higher-tier model when repeated failures occur.

        Upgrade path:
            dragon: bronze → silver → gold
            titan: lite → core → prime
        Returns True if upgrade happened, False if already at max tier.
        """
        upgrade_map = {
            "dragon_bronze": "dragon_silver",
            "dragon_silver": "dragon_gold",
            "titan_lite": "titan_core",
            "titan_core": "titan_prime",
        }
        new_tier = upgrade_map.get(self.preset_name)
        if not new_tier:
            logger.info(f"[Pipeline] Already at max tier ({self.preset_name}), no upgrade possible")
            return False

        old_tier = self.preset_name
        self.preset_name = new_tier
        self._apply_preset()
        logger.info(f"[Pipeline] ⚡ Tier upgrade: {old_tier} → {new_tier}")
        return True
    # MARKER_122.4_END

    # MARKER_122.5_START: Escalate to architect for re-planning
    async def _escalate_to_architect(
        self, task: str, failed_subtasks: list, original_plan: Dict,
        phase_type: str, scout_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Re-plan when verifier reports major issues on subtasks.

        Calls architect with context about what failed and why.
        Returns new plan (same format as _architect_plan).
        """
        # Build failure context
        failure_lines = []
        for s in failed_subtasks:
            desc = s.description if hasattr(s, 'description') else str(s)[:100]
            fb_raw = s.verifier_feedback if hasattr(s, 'verifier_feedback') and s.verifier_feedback else "No feedback"
            fb = str(fb_raw.get("issues", fb_raw)) if isinstance(fb_raw, dict) else str(fb_raw)
            failure_lines.append(f"- {desc[:80]}: {fb[:200]}")

        replan_context = (
            f"IMPORTANT: Previous plan partially failed. Re-plan ONLY the failed subtasks.\n"
            f"Keep successful subtasks as-is.\n\n"
            f"Failed subtasks:\n" + "\n".join(failure_lines)
        )

        await self._emit_progress(
            "@architect",
            f"🔄 Re-planning {len(failed_subtasks)} failed subtasks...",
            model=self.prompts.get("architect", {}).get("model", "")
        )

        try:
            plan = await self._architect_plan(task, phase_type, scout_context=scout_context,
                                               replan_context=replan_context)
            return plan
        except Exception as e:
            logger.warning(f"[Pipeline] Architect re-plan failed: {e}")
            # Fallback: mark failed subtasks as needs_research and return original plan
            for st in original_plan.get("subtasks", []):
                st["needs_research"] = True
            return original_plan
    # MARKER_122.5_END

    # MARKER_118.8_ADAPTIVE_ELISION
    def _get_adaptive_elision_level(self) -> int:
        """Adjust ELISION compression based on STM fill percentage.

        - STM < 30% full -> Level 1 (light compression)
        - STM 30-70%     -> Level 2 (standard)
        - STM > 70%      -> Level 3 (aggressive, vowel skip)
        """
        if not self.stm_limit or self.stm_limit == 0:
            return PIPELINE_ELISION_LEVEL
        fill_ratio = len(self.stm) / self.stm_limit
        if fill_ratio < 0.3:
            return 1
        elif fill_ratio > 0.7:
            return 3
        return 2

    def _get_llm_tool(self):
        """Lazy load LLM tool to avoid circular imports"""
        if self.llm_tool is None:
            try:
                if getattr(self, 'async_mode', False):
                    # MARKER_129.4: Use async LLM tool in MYCELIUM
                    from src.mcp.tools.llm_call_tool_async import LLMCallToolAsync
                    self.llm_tool = LLMCallToolAsync()
                else:
                    from src.mcp.tools.llm_call_tool import LLMCallTool
                    self.llm_tool = LLMCallTool()
            except ImportError:
                logger.warning("LLMCallTool not available, using fallback")
                self.llm_tool = None
        return self.llm_tool

    # MARKER_126.5A: Cancel pipeline from outside (TaskBoard, UI stop button)
    def cancel(self, reason: str = "Cancelled by user"):
        """Signal pipeline to stop after current step."""
        self._cancelled.set()
        self._cancel_reason = reason
        logger.info(f"[Pipeline] Cancel requested: {reason}")

    def _check_cancelled(self):
        """Check if pipeline was cancelled, raise if so."""
        if self._cancelled.is_set():
            raise PipelineCancelled(self._cancel_reason or "Pipeline cancelled")

    # MARKER_126.0A: Track LLM call for stats
    def _track_llm_call(self, result: dict):
        """Increment LLM call counter and extract token usage if available."""
        self._llm_calls += 1
        usage = result.get("result", {}).get("usage", {})
        if usage:
            self._tokens_in += usage.get("prompt_tokens", 0)
            self._tokens_out += usage.get("completion_tokens", 0)

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
    # MARKER_117.8B: Async emit — SocketIO direct for solo, AsyncClient for groups
    # Replaces sync httpx.Client that was BLOCKING the event loop for 5s per emit
    async def _emit_progress(self, role: str, message: str, subtask_idx: int = 0, total: int = 0, model: str = None):
        """
        Emit progress update to VETKA chat.

        MARKER_118.6: Emits 'chat_response' (not legacy 'agent_message') for ChatPanel visibility.
        Two routes (both async, non-blocking):
          1. SocketIO direct (solo chat) — via self.sio.emit("chat_response") → instant
          2. HTTP AsyncClient (group chat) — via POST to group endpoint → async

        Args:
            role: @architect, @researcher, @coder, or @pipeline
            message: Status message
            subtask_idx: Current subtask index (1-based for display)
            total: Total subtasks count
            model: Optional model name for attribution (e.g. "moonshotai/kimi-k2.5")
        """
        try:
            # MARKER_117.6C: Show which model is executing
            model_tag = ""
            if model:
                short_model = model.split("/")[-1] if "/" in model else model
                model_tag = f" ({short_model})"

            # Format progress message
            progress = f"[{subtask_idx}/{total}] " if total > 0 else ""
            full_message = f"{role}{model_tag}: {progress}{message}"

            # MARKER_129.4A: Broadcast to DevPanel via MYCELIUM WebSocket (direct, no relay)
            if getattr(self, '_ws_broadcaster', None):
                try:
                    await self._ws_broadcaster.broadcast({
                        "type": "pipeline_activity",
                        "role": role,
                        "message": message,
                        "model": model or "system",
                        "subtask_idx": subtask_idx,
                        "total": total,
                        "task_id": getattr(self, '_board_task_id', None),
                        "preset": self.preset_name,
                        "timestamp": time.time(),
                    })
                except Exception:
                    pass  # Never fail pipeline on WS broadcast

            # MARKER_129.4B: Chat relay via MYCELIUM HTTP client (→ VETKA ChatPanel)
            if getattr(self, '_http_client', None) and self.chat_id:
                try:
                    await self._http_client.emit_pipeline_progress(
                        self.chat_id, role, full_message, model=model or "system",
                        subtask_idx=subtask_idx, total=total
                    )
                except Exception:
                    pass
                return  # MYCELIUM path done — skip VETKA SocketIO below

            # MARKER_127.2: Broadcast pipeline_activity to ALL connected clients (for DevPanel)
            # This runs BEFORE chat routing so early returns don't skip it
            try:
                if self.sio:
                    await self.sio.emit("pipeline_activity", {
                        "role": role,
                        "message": message,
                        "model": model or "system",
                        "subtask_idx": subtask_idx,
                        "total": total,
                        "task_id": getattr(self, '_board_task_id', None),
                        "preset": self.preset,
                        "timestamp": time.time(),
                    })
            except Exception:
                pass  # Never fail pipeline on broadcast

            # MARKER_118.6: Route 1 — emit "chat_response" so ChatPanel sees it
            # (Was "agent_message" → wrote to legacy messages[], invisible in ChatPanel)
            if self.sio and self.sid:
                await self.sio.emit("chat_response", {
                    "message": full_message,
                    "agent": "pipeline",
                    "model": model or "system",
                }, to=self.sid)
                logger.debug(f"[Pipeline] SIO emit: {full_message[:80]}...")
                return

            # MARKER_117.8B Route 2: HTTP async (group chat — non-blocking)
            if self.chat_id:
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(
                        f"http://localhost:5001/api/debug/mcp/groups/{self.chat_id}/send",
                        json={
                            "agent_id": "pipeline",
                            "content": full_message,
                            "message_type": "system"
                        }
                    )
                    if response.status_code != 200:
                        logger.warning(f"[Pipeline] Emit got status {response.status_code}")
                logger.debug(f"[Pipeline] HTTP emit: {full_message[:80]}...")
                return

            # No sio/sid and no chat_id — skip silently
            logger.debug(f"[Pipeline] No emit target, skip: {role}: {message[:80]}")

        except Exception as e:
            # Don't fail pipeline on emit errors, but log as warning for visibility
            logger.warning(f"[Pipeline] Emit failed (non-fatal): {e}")

        # Call registered hooks
        for hook in self.progress_hooks:
            try:
                hook(role, message, subtask_idx, total)
            except Exception as e:
                logger.debug(f"[Pipeline] Hook error: {e}")
    # MARKER_102.27_END

    # MARKER_104_STREAM_VISIBILITY: Stream event emission with visibility control
    def _emit_stream_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        visibility: str = "summary"
    ):
        """
        Emit event with visibility control for selective streaming.

        Args:
            event_type: Type of event (e.g., "subtask_progress", "artifact_created")
            data: Event data dictionary
            visibility: "full" | "summary" | "silent"
                - full: Emit complete data
                - summary: Compress/summarize data before emit
                - silent: Don't emit at all

        Phase 104.7: Enables selective decompression for visible streams.
        """
        if visibility == "silent":
            logger.debug(f"[Pipeline] Silent event suppressed: {event_type}")
            return  # Don't emit

        if visibility == "summary":
            # Compress/summarize data before emit
            data_str = str(data)
            if len(data_str) > 500:
                data = self._summarize_for_stream(data)

        # Emit to Socket.IO (non-blocking)
        asyncio.create_task(self._emit_to_chat(event_type, data))

    def _summarize_for_stream(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Summarize large data payloads for streaming.

        Args:
            data: Original data dictionary

        Returns:
            Summarized version with truncated values
        """
        summarized = {}

        for key, value in data.items():
            if isinstance(value, str):
                # Truncate long strings
                if len(value) > 200:
                    summarized[key] = value[:200] + f"... [{len(value) - 200} chars truncated]"
                else:
                    summarized[key] = value
            elif isinstance(value, dict):
                # Recursively summarize nested dicts
                if len(str(value)) > 200:
                    summarized[key] = {"_summary": f"Dict with {len(value)} keys", "_keys": list(value.keys())[:5]}
                else:
                    summarized[key] = value
            elif isinstance(value, list):
                # Summarize long lists
                if len(value) > 5:
                    summarized[key] = value[:5] + [f"... +{len(value) - 5} more items"]
                else:
                    summarized[key] = value
            else:
                summarized[key] = value

        summarized["_stream_mode"] = "summary"
        return summarized

    async def _emit_to_chat(self, event_type: str, data: Dict[str, Any]):
        """
        Async emit event to chat.
        MARKER_117.8B: SocketIO direct for solo, HTTP async for groups.
        """
        try:
            # Format stream event as a readable message
            summary = data.get("result", data.get("marker", str(data)))
            if isinstance(summary, str) and len(summary) > 300:
                summary = summary[:300] + "..."
            content = f"[{event_type}] {summary}"

            # MARKER_118.6: Route 1 — emit "chat_response" for ChatPanel visibility
            if self.sio and self.sid:
                await self.sio.emit("chat_response", {
                    "message": content,
                    "agent": "pipeline",
                    "model": "system",
                }, to=self.sid)
                logger.debug(f"[Pipeline] SIO stream event: {event_type}")
                return

            # MARKER_117.8B: Route 2 — HTTP async (group)
            if self.chat_id:
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        f"http://localhost:5001/api/debug/mcp/groups/{self.chat_id}/send",
                        json={
                            "agent_id": "pipeline",
                            "content": content,
                            "message_type": "system"
                        }
                    )
                logger.debug(f"[Pipeline] HTTP stream event: {event_type}")
        except Exception as e:
            # Don't fail pipeline on emit errors
            logger.warning(f"[Pipeline] Stream emit failed (non-fatal): {e}")
    # MARKER_104_STREAM_VISIBILITY_END

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
    # MARKER_117_2B_SANDBOX: Sandbox-safe load/save with TMPDIR fallback
    def _load_tasks(self) -> Dict[str, Any]:
        """Load tasks from JSON storage (tries primary, then TMPDIR fallback)"""
        if TASKS_FILE.exists():
            try:
                return json.loads(TASKS_FILE.read_text())
            except Exception:
                pass
        if _TASKS_FILE_FALLBACK.exists():
            try:
                return json.loads(_TASKS_FILE_FALLBACK.read_text())
            except Exception:
                pass
        return {}

    def _save_tasks(self, tasks: Dict[str, Any]):
        """Save tasks to JSON storage with sandbox-safe fallback"""
        try:
            TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
            TASKS_FILE.write_text(json.dumps(tasks, indent=2, default=str))
        except (PermissionError, OSError) as e:
            # MCP sandbox: project dir is read-only, fall back to TMPDIR
            logger.warning(f"[Pipeline] Sandboxed write blocked, using TMPDIR: {e}")
            try:
                _TASKS_FILE_FALLBACK.write_text(json.dumps(tasks, indent=2, default=str))
                logger.info(f"[Pipeline] Tasks saved to fallback: {_TASKS_FILE_FALLBACK}")
            except Exception as e2:
                logger.error(f"[Pipeline] TMPDIR fallback also failed: {e2}")

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
    # MARKER_104_MEMORY_STM: ELISION compression integration
    def _add_to_stm(self, marker: str, result: str):
        """
        Add subtask result to short-term memory with ELISION compression.

        Phase 104.6: Compress large results to save tokens in context passing.
        - Results > 1000 chars: ELISION Level 2 compression (40-50% savings)
        - Smaller results: truncate to 500 chars

        Args:
            marker: Subtask identifier
            result: Raw subtask result string
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            from src.memory.elision import get_elision_compressor
            compressor = get_elision_compressor()
        except ImportError:
            # Fallback if ELISION not available
            logger.warning("[STM] ELISION import failed, using truncation only")
            self.stm.append({
                "marker": marker,
                "result": result[:PIPELINE_TRUNCATE_RESULT] if result else "",
                "compressed": False
            })
            if len(self.stm) > self.stm_limit:
                self.stm.pop(0)
            return

        result_str = str(result) if result else ""
        original_size = len(result_str)

        # Only compress if result is large enough
        if original_size > PIPELINE_COMPRESS_THRESHOLD:
            try:
                compression = compressor.compress(result_str, level=self._get_adaptive_elision_level())
                stm_entry = {
                    "marker": marker,
                    "result": compression.compressed,
                    "compressed": True,
                    "original_size": compression.original_length,
                    "compressed_size": compression.compressed_length,
                    "compression_ratio": round(compression.compression_ratio, 2),
                    "tokens_saved": compression.tokens_saved_estimate,
                    "level": 2
                }
                logger.debug(
                    f"[STM] Compressed {marker}: {compression.original_length} -> "
                    f"{compression.compressed_length} chars "
                    f"({compression.compression_ratio:.1f}x, "
                    f"~{compression.tokens_saved_estimate} tokens saved)"
                )
            except Exception as e:
                logger.warning(f"[STM] Compression failed for {marker}: {e}, using truncation")
                stm_entry = {
                    "marker": marker,
                    "result": result_str[:PIPELINE_TRUNCATE_RESULT],
                    "compressed": False
                }
        else:
            # Small results: no compression needed
            stm_entry = {
                "marker": marker,
                "result": result_str[:PIPELINE_TRUNCATE_RESULT] if result_str else "",
                "compressed": False
            }

        self.stm.append(stm_entry)

        # Keep only last N entries
        if len(self.stm) > self.stm_limit:
            removed = self.stm.pop(0)
            if removed.get("compressed"):
                logger.debug(f"[STM] Evicted compressed entry {removed['marker']}")

    def _get_stm_summary(self) -> str:
        """
        Get summary of previous subtask results for context injection.

        Phase 104.6: Handles both compressed and uncompressed entries.
        Decompresses as needed for context passing.
        """
        import logging
        logger = logging.getLogger(__name__)

        if not self.stm:
            return ""

        summary_parts = ["Previous results:"]

        # Try to import compressor for decompression
        try:
            from src.memory.elision import get_elision_compressor
            compressor = get_elision_compressor()
        except ImportError:
            compressor = None

        for item in self.stm[-PIPELINE_STM_SUMMARY_WINDOW:]:
            marker = item.get("marker", "unknown")
            result = item.get("result", "")

            # Decompress if needed
            if item.get("compressed") and compressor:
                try:
                    result = compressor.expand(result, item.get("legend", {}))
                    result = result[:PIPELINE_SUMMARY_TRUNCATE]
                except Exception as e:
                    logger.warning(f"[STM] Decompression failed for {marker}: {e}")
                    result = result[:PIPELINE_SUMMARY_TRUNCATE]
            else:
                result = result[:PIPELINE_SUMMARY_TRUNCATE]

            summary_parts.append(f"- [{marker}]: {result}...")

        return "\n".join(summary_parts)

    def _get_stm_memory_stats(self) -> Dict[str, Any]:
        """
        Get STM memory usage statistics.

        Phase 104.6: Track compression metrics for memory efficiency.
        Returns:
            Dict with total size, compressed size, and savings estimate
        """
        total_original = 0
        total_compressed = 0
        num_compressed = 0
        total_tokens_saved = 0

        for item in self.stm:
            if item.get("compressed"):
                total_original += item.get("original_size", 0)
                total_compressed += item.get("compressed_size", 0)
                num_compressed += 1
                total_tokens_saved += item.get("tokens_saved", 0)
            else:
                # Estimate original size from truncated result
                total_original += len(item.get("result", ""))

        return {
            "total_original_size": total_original,
            "total_compressed_size": total_compressed,
            "num_entries": len(self.stm),
            "num_compressed": num_compressed,
            "compression_ratio": (
                round(total_original / total_compressed, 2)
                if total_compressed > 0 else 0.0
            ),
            "tokens_saved_estimate": total_tokens_saved
        }

    def _log_stm_summary(self):
        """Log STM statistics at pipeline completion."""
        stats = self._get_stm_memory_stats()
        if stats["num_entries"] > 0:
            logger.info(
                f"[STM] Pipeline STM Summary: "
                f"{stats['num_entries']} entries, "
                f"{stats['num_compressed']} compressed, "
                f"~{stats['tokens_saved_estimate']} tokens saved "
                f"({stats['compression_ratio']}x compression)"
            )
    # MARKER_102.25_END

    # MARKER_119.2: Pipeline-to-STMBuffer bridge
    def _bridge_to_global_stm(self, task_id: str, phase_type: str):
        """Report pipeline completion summary to global STMBuffer.

        Bridges ephemeral pipeline STM (subtask context passing) with
        persistent STMBuffer (cross-agent conversation continuity).
        Jarvis and other consumers can then see pipeline results.
        """
        if not self.stm:
            return
        try:
            stm = get_stm_buffer()
            markers = [item.get("marker", "?") for item in self.stm]
            previews = []
            for item in self.stm[-3:]:
                r = str(item.get("result", ""))[:100]
                previews.append(f"[{item.get('marker', '?')}]: {r}")
            summary = (
                f"Pipeline {task_id} ({phase_type}): "
                f"{len(self.stm)} subtasks [{', '.join(markers)}]. "
                f"{'; '.join(previews)}"
            )[:500]
            stm.add_message(summary, source="pipeline")
            logger.info(f"[Pipeline] Bridged STM summary to global STMBuffer ({len(summary)} chars)")
        except Exception as e:
            logger.warning(f"[Pipeline] STM bridge failed (non-fatal): {e}")
    # MARKER_119.2_END
    # MARKER_102.3_END

    # MARKER_130.C19D: Language validation — prevent writing JS to .py or Python to .tsx
    def _validate_code_language(self, code: str, filepath: str) -> tuple[bool, str]:
        """
        Validate that code language matches file extension.

        Returns:
            (is_valid, error_message)
        """
        ext = Path(filepath).suffix.lower()

        # Python indicators
        py_indicators = [
            'def ', 'class ', 'import ', 'from ', 'async def ',
            'if __name__', '"""', "'''", 'self.', 'None', 'True', 'False',
            '@property', '@staticmethod', '@classmethod', 'raise ',
        ]

        # JavaScript/TypeScript indicators
        js_indicators = [
            'const ', 'let ', 'var ', 'function ', '=>', 'export ',
            'import {', 'from "', "from '", 'interface ', 'type ',
            'async function', 'await ', 'null', 'undefined', 'true', 'false',
            'React', 'useState', 'useEffect', '// ', '/* ',
        ]

        # Count indicators
        py_score = sum(1 for ind in py_indicators if ind in code)
        js_score = sum(1 for ind in js_indicators if ind in code)

        # Determine detected language
        if py_score > js_score + 2:
            detected = 'python'
        elif js_score > py_score + 2:
            detected = 'javascript'
        else:
            detected = 'ambiguous'

        # Validate against extension
        if ext in ('.py',):
            if detected == 'javascript':
                return False, f"BLOCKED: JS/TS code detected but target is {ext}"
        elif ext in ('.ts', '.tsx', '.js', '.jsx'):
            if detected == 'python':
                return False, f"BLOCKED: Python code detected but target is {ext}"

        return True, ""

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

        # MARKER_133.FIX3: Multi-format code extraction
        # Pattern 1: Standard markdown code blocks: ```[lang]\ncode\n```
        pattern = r'```(?:python|py|javascript|js|typescript|ts|rust|rs|)?\s*\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

        # Pattern 2: "// file: path" format (Qwen-style output)
        # Extract file path AND code that follows
        file_pattern = r'(?://|#)\s*file:\s*([^\s\n]+)\s*\n(.*?)(?=(?://|#)\s*file:|```|$)'
        file_matches = re.findall(file_pattern, content, re.DOTALL | re.IGNORECASE)

        if not matches and not file_matches:
            # Pattern 3: Fallback — if content looks like code (has def/class/import), treat whole thing as code
            code_indicators = ['def ', 'class ', 'import ', 'from ', 'async def ', '@router', '@app']
            if any(indicator in content[:500] for indicator in code_indicators):
                logger.info("[Pipeline] No code blocks found but content looks like code, treating as raw code")
                matches = [content]
            else:
                logger.debug("[Pipeline] No code blocks found in response")
                return files_created

        # Process "// file: path" matches first (they have explicit paths)
        for file_path_match, code_block in file_matches:
            code = code_block.strip()
            if not code or len(code) < 20:
                continue
            filepath = file_path_match.strip()
            # Validate it looks like a real path
            if '.' in filepath and ('/' in filepath or filepath.endswith('.py')):
                self._write_extracted_file(filepath, code, files_created, subtask)

        # Process standard code blocks
        for i, code_block in enumerate(matches):
            code = code_block.strip()
            if not code:
                continue

            # Determine filepath from subtask description or code content
            # e.g., "Create src/voice/config.py" → src/voice/config.py
            filepath = None

            # Try to find path in code itself first (# file: path)
            inline_path = re.search(r'(?://|#)\s*file:\s*([^\s\n]+)', code[:200])
            if inline_path:
                filepath = inline_path.group(1).strip()

            # Then try subtask description
            if not filepath and subtask.description:
                path_match = re.search(
                    r'((?:src|data|client)/[^\s]+?\.(?:py|js|ts|tsx|md|json))',
                    subtask.description,
                    re.IGNORECASE
                )
                if path_match:
                    filepath = path_match.group(1)

            # Then try the LLM content itself for file references
            if not filepath:
                content_path = re.search(
                    r'((?:src|data|client)/[^\s]+?\.(?:py|js|ts|tsx|md|json))',
                    content[:500],
                    re.IGNORECASE
                )
                if content_path:
                    filepath = content_path.group(1)

            # Fallback: Use MARKER or generic name
            if not filepath:
                marker = getattr(subtask, 'marker', f'file_{i+1}')
                # Clean marker for filename
                safe_marker = re.sub(r'[^\w\-_.]', '_', str(marker))
                filepath = f"src/vetka_out/{safe_marker}.py"

            # Ensure directory exists and write file
            try:
                path_obj = Path(filepath)

                # MARKER_130.C19D: Validate code language matches file extension
                is_valid, error_msg = self._validate_code_language(code, filepath)
                if not is_valid:
                    logger.error(f"[Pipeline] {error_msg} for {filepath}")
                    # Save to staging instead of overwriting
                    staging_dir = Path("data/vetka_staging/blocked")
                    staging_dir.mkdir(parents=True, exist_ok=True)
                    staging_path = staging_dir / f"{path_obj.stem}_BLOCKED{path_obj.suffix}"
                    staging_path.write_text(code, encoding='utf-8')
                    logger.warning(f"[Pipeline] Blocked code saved to: {staging_path}")
                    continue  # Skip this file, don't overwrite

                # MARKER_130.C19D: Extra safety — only overwrite files in safe directories
                safe_dirs = ('src/vetka_out', 'data/vetka_staging', 'data/artifacts')
                if path_obj.exists() and not any(str(filepath).startswith(d) for d in safe_dirs):
                    logger.error(f"[Pipeline] BLOCKED: Cannot overwrite existing file {filepath}")
                    staging_dir = Path("data/vetka_staging/blocked")
                    staging_dir.mkdir(parents=True, exist_ok=True)
                    staging_path = staging_dir / f"{path_obj.stem}_WOULD_OVERWRITE{path_obj.suffix}"
                    staging_path.write_text(code, encoding='utf-8')
                    logger.warning(f"[Pipeline] Would-overwrite code saved to: {staging_path}")
                    continue

                path_obj.parent.mkdir(parents=True, exist_ok=True)
                path_obj.write_text(code, encoding='utf-8')
                files_created.append(filepath)
                logger.info(f"[Pipeline] Spawn created: {filepath} ({len(code)} chars)")

                # MARKER_123.1D: Phase 123.1 - Emit glow for pipeline-created files
                try:
                    from src.services.activity_hub import get_activity_hub
                    hub = get_activity_hub()
                    hub.emit_glow_sync(str(path_obj.absolute()), 1.0, "vetka_out:created")
                except Exception:
                    pass  # Non-critical

            except Exception as e:
                logger.error(f"[Pipeline] Failed to write {filepath}: {e}")
                # Fallback to staging directory
                try:
                    fallback_dir = Path("data/vetka_staging")
                    fallback_dir.mkdir(parents=True, exist_ok=True)
                    fallback_path = fallback_dir / Path(filepath).name
                    fallback_path.write_text(code, encoding='utf-8')
                    files_created.append(str(fallback_path))
                    logger.warning(f"[Pipeline] Written to fallback: {fallback_path}")
                except Exception as e2:
                    logger.error(f"[Pipeline] Fallback also failed: {e2}")

        return files_created

    def _write_extracted_file(self, filepath: str, code: str, files_created: List[str], subtask) -> None:
        """MARKER_133.FIX3: Write a single extracted file to disk with safety checks."""
        from pathlib import Path
        try:
            path_obj = Path(filepath)

            # Validate code language
            is_valid, error_msg = self._validate_code_language(code, filepath)
            if not is_valid:
                logger.error(f"[Pipeline] {error_msg} for {filepath}")
                staging_dir = Path("data/vetka_staging/blocked")
                staging_dir.mkdir(parents=True, exist_ok=True)
                staging_path = staging_dir / f"{path_obj.stem}_BLOCKED{path_obj.suffix}"
                staging_path.write_text(code, encoding='utf-8')
                return

            # Safety: existing files outside safe dirs go to staging
            safe_dirs = ('src/vetka_out', 'data/vetka_staging', 'data/artifacts')
            if path_obj.exists() and not any(str(filepath).startswith(d) for d in safe_dirs):
                staging_dir = Path("data/vetka_staging/would_overwrite")
                staging_dir.mkdir(parents=True, exist_ok=True)
                staging_path = staging_dir / f"{path_obj.stem}_NEW{path_obj.suffix}"
                staging_path.write_text(code, encoding='utf-8')
                files_created.append(str(staging_path))
                logger.info(f"[Pipeline] Existing file → staged: {staging_path} ({len(code)} chars)")
                return

            path_obj.parent.mkdir(parents=True, exist_ok=True)
            path_obj.write_text(code, encoding='utf-8')
            files_created.append(filepath)
            logger.info(f"[Pipeline] Created: {filepath} ({len(code)} chars)")

            try:
                from src.services.activity_hub import get_activity_hub
                hub = get_activity_hub()
                hub.emit_glow_sync(str(path_obj.absolute()), 1.0, "vetka_out:created")
            except Exception:
                pass

        except Exception as e:
            logger.error(f"[Pipeline] Failed to write {filepath}: {e}")
            try:
                fallback_dir = Path("data/vetka_staging")
                fallback_dir.mkdir(parents=True, exist_ok=True)
                fallback_path = fallback_dir / Path(filepath).name
                fallback_path.write_text(code, encoding='utf-8')
                files_created.append(str(fallback_path))
            except Exception as e2:
                logger.error(f"[Pipeline] Fallback failed: {e2}")
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

        # MARKER_126.9E: Apply selected key preference if set from UI
        if hasattr(self, 'selected_key') and self.selected_key:
            from src.utils.unified_key_manager import get_key_manager
            km = get_key_manager()
            provider = self.selected_key.get('provider', '')
            key_masked = self.selected_key.get('key_masked', '')
            if provider and key_masked:
                km.set_preferred_key(provider, key_masked)
                logger.info(f"[Pipeline] Using selected key: {provider}/{key_masked[:12]}...")

        # MARKER_102.28_START: Progress emission during execution
        # MARKER_117.6C: Show team composition at pipeline start
        team_info = f"🐉 {self.preset_name or 'default'}"
        if self.preset_models:
            team_names = [m.split("/")[-1] for m in self.preset_models.values()]
            team_info += f" ({' → '.join(team_names)})"
        await self._emit_progress("@mycelium", f"🚀 Starting {phase_type} pipeline | {team_info}")

        try:
            # MARKER_122.1: Phase 0 — Parallel Recon (Scout + Researcher concurrently)
            await self._emit_progress("@mycelium", "🔍 Parallel recon: Scout + Researcher...")
            scout_context, initial_research = await self._parallel_recon(task, phase_type)
            # MARKER_122.5C: Store scout context for subtask injection
            self._scout_context = scout_context
            if scout_context:
                await self._emit_progress(
                    "@scout",
                    f"✅ Found {len(scout_context.get('relevant_files', []))} files, "
                    f"{len(scout_context.get('patterns_found', []))} patterns"
                )
            if initial_research:
                confidence = initial_research.get("confidence", "N/A")
                await self._emit_progress("@researcher", f"✅ Research done (confidence: {confidence})")
            # MARKER_122.1_END

            # Phase 1: Architect breaks down task (with recon context)
            # MARKER_117.6C: Model attribution in progress messages
            architect_model = self.prompts.get("architect", {}).get("model", "")
            await self._emit_progress("@architect", "📋 Breaking down task into subtasks...", model=architect_model)
            # MARKER_133.C33B: Architect phase with timeout — CRITICAL (abort on timeout)
            plan = await self._safe_phase("architect", self._architect_plan(task, phase_type, scout_context=scout_context,
                                               research_context=initial_research))
            # MARKER_133.C33B: If architect timed out, abort pipeline
            if plan is None:
                logger.error("[Pipeline] Architect phase timed out — cannot continue without plan")
                pipeline_task.status = "failed"
                pipeline_task.results = {"error": "Architect phase timed out"}
                self._update_task(pipeline_task)
                return {"success": False, "error": "Architect phase timed out", "task_id": pipeline_task.task_id}
            pipeline_task.subtasks = [
                Subtask(**st) if isinstance(st, dict) else st
                for st in plan.get("subtasks", [])
            ]
            total_subtasks = len(pipeline_task.subtasks)
            await self._emit_progress("@architect", f"✅ Plan ready: {total_subtasks} subtasks", model=self._last_used_model)

            # MARKER_117_2A_FIX_D: Emit architect plan details to chat
            # Previously plan was only saved to pipeline_task.results, invisible in UI
            subtask_list = "\n".join([
                f"  {i+1}. {st.description[:80]}"
                for i, st in enumerate(pipeline_task.subtasks[:8])
            ])
            if total_subtasks > 8:
                subtask_list += f"\n  ... +{total_subtasks - 8} more"
            await self._emit_progress("@architect", f"📋 Plan:\n{subtask_list}")
            pipeline_task.status = "executing"
            self._update_task(pipeline_task)

            # MARKER_117.4C: Auto-tier selection based on architect's complexity estimate
            # Architect (e.g. Kimi K2.5) evaluates complexity → pipeline switches tier
            # for coder/researcher roles. Architect itself always runs on initial preset.
            complexity = plan.get("estimated_complexity", "medium")
            tier_preset = self._resolve_tier(complexity)
            if tier_preset and tier_preset != self.preset_name:
                old_tier = self.preset_name
                self.preset_name = tier_preset
                self._apply_preset()
                await self._emit_progress(
                    "system",
                    f"⚡ Auto-tier: {complexity} complexity → {tier_preset} (was {old_tier})"
                )
            # MARKER_117.4C_END

            # MARKER_118.8_ADAPTIVE_STM: Override stm_limit based on complexity
            try:
                data = json.loads(PRESETS_FILE.read_text())
                stm_window_map = data.get("_stm_window_map", {"low": 3, "medium": 5, "high": 8})
                new_limit = stm_window_map.get(complexity, self.stm_limit)
                if new_limit != self.stm_limit:
                    logger.info(f"[Pipeline] Adaptive STM: {complexity} -> window={new_limit} (was {self.stm_limit})")
                    self.stm_limit = new_limit
            except Exception:
                pass  # Keep default

            # MARKER_122.2: Architect PM Pass — refine plan with research context
            # If initial research confidence is LOW, architect re-evaluates with enriched context
            # MARKER_124.1C: Raised threshold 0.9 → 0.7 — replan only when researcher is truly unsure
            # At 0.9 every pipeline did double-planning (E2E showed confidence=0.85 → wasted replan)
            if initial_research and isinstance(initial_research, dict) and initial_research.get("confidence", 1.0) < 0.7:
                await self._emit_progress("@architect", "📋 PM pass: refining plan with research context...", model=architect_model)
                # MARKER_133.C33B: Architect PM pass with timeout
                refined_plan = await self._safe_phase("architect", self._architect_plan(task, phase_type, scout_context=scout_context,
                                                   research_context=initial_research))
                if refined_plan is None:
                    # PM replan failed, continue with original plan
                    logger.warning("[Pipeline] Architect PM pass timed out — using original plan")
                    await self._emit_progress("system", "Architect PM pass timed out — using original plan")
                else:
                    plan = refined_plan
                    pipeline_task.subtasks = [
                        Subtask(**st) if isinstance(st, dict) else st
                        for st in plan.get("subtasks", [])
                    ]
                    total_subtasks = len(pipeline_task.subtasks)
                    await self._emit_progress("@architect", f"✅ PM refined plan: {total_subtasks} subtasks", model=self._last_used_model)
            # MARKER_122.2_END

            # MARKER_102.24_START: Phase 2 with STM context passing
            # Phase 2: Execute each subtask (with research triggers + STM)
            self.stm = []  # Reset STM for new pipeline
            replan_count = 0  # MARKER_122.4: Track architect re-plans

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

            # MARKER_104_MEMORY_STM: Log memory compression statistics
            self._log_stm_summary()
            # MARKER_119.2: Report pipeline results to global STMBuffer
            self._bridge_to_global_stm(task_id, phase_type)

            # MARKER_121.3: Update Task Board if this was a board-dispatched task
            if hasattr(self, '_board_task_id') and self._board_task_id:
                try:
                    from src.orchestration.task_board import get_task_board
                    from datetime import datetime as _dt
                    board = get_task_board()
                    board.update_task(
                        self._board_task_id,
                        status="done" if pipeline_task.status == "done" else "failed",
                        completed_at=_dt.now().isoformat(),
                        pipeline_task_id=task_id,
                        assigned_tier=self.preset_name,
                        result_summary=str(pipeline_task.results)[:500]
                    )
                    logger.info(f"[Pipeline] Task board updated: {self._board_task_id} → {pipeline_task.status}")
                except Exception as e:
                    logger.debug(f"[Pipeline] Task board update skipped: {e}")
            # MARKER_121.3_END

            # MARKER_117_3B: Expanded final report with subtask details
            report_lines = [
                f"📊 **Pipeline Report** — {completed}/{total} subtasks",
                f"Phase: `{pipeline_task.phase_type}` | Order: `{plan.get('execution_order', 'sequential')}`",
                "",
            ]
            for i, subtask in enumerate(pipeline_task.subtasks or []):
                s_icon = "✅" if subtask.status == "done" else "❌"
                marker = subtask.marker or f"step_{i+1}"
                report_lines.append(f"{s_icon} **{marker}**: {subtask.description[:80]}")
                if subtask.result:
                    preview = str(subtask.result)[:200].replace('\n', ' ')
                    report_lines.append(f"   └ {preview}")
            report_lines.append(f"\n🎉 Pipeline complete!")
            await self._emit_to_chat("@mycelium", "\n".join(report_lines))  # MARKER_120.1: was missing await
            # MARKER_102.28_END

            # MARKER_126.0A: Record pipeline statistics for DevPanel
            try:
                completed_subtasks = [s for s in pipeline_task.subtasks if s.status == "done"]
                verifier_confidences = [
                    s.verifier_feedback.get("confidence", 0)
                    for s in pipeline_task.subtasks
                    if isinstance(getattr(s, "verifier_feedback", None), dict)
                ]
                pipeline_stats = {
                    "preset": self.preset_name or "default",
                    "league": "dragon" if (self.preset_name or "").startswith("dragon") else "titan",
                    "phase_type": phase_type,
                    "subtasks_total": len(pipeline_task.subtasks),
                    "subtasks_completed": len(completed_subtasks),
                    "success": pipeline_task.status == "done",
                    "llm_calls": self._llm_calls,
                    "tokens_in": self._tokens_in,
                    "tokens_out": self._tokens_out,
                    "verifier_avg_confidence": (
                        sum(verifier_confidences) / len(verifier_confidences)
                        if verifier_confidences else 0
                    ),
                    "completed_at": time.time(),
                    "duration_s": round(time.time() - pipeline_task.timestamp, 1),
                }
                # Save to TaskBoard if task has a board ID
                if hasattr(self, '_board_task_id') and self._board_task_id:
                    from src.orchestration.task_board import get_task_board
                    board = get_task_board()
                    board.record_pipeline_stats(self._board_task_id, pipeline_stats)
                # Always store in pipeline_task results
                if pipeline_task.results:
                    pipeline_task.results["stats"] = pipeline_stats
                else:
                    pipeline_task.results = {"stats": pipeline_stats}
                self._update_task(pipeline_task)
                logger.info(f"[Pipeline Stats] {self.preset_name}: {pipeline_stats['subtasks_completed']}/{pipeline_stats['subtasks_total']} done, {pipeline_stats['llm_calls']} LLM calls, {pipeline_stats['duration_s']}s")

                # MARKER_133.HISTORY: Record to pipeline history for observability
                try:
                    from src.api.routes.pipeline_history import append_run
                    append_run(
                        task_id=task_id,
                        task_title=task[:200],
                        preset=self.preset_name or "unknown",
                        phase_type=phase_type,
                        phases_completed=[s.marker for s in pipeline_task.subtasks if s.status == "done"],
                        total_duration_s=pipeline_stats.get("duration_s", 0),
                        eval_score=pipeline_stats.get("verifier_avg_confidence"),
                        status="done" if pipeline_stats.get("success") else "failed",
                        llm_calls=pipeline_stats.get("llm_calls", 0),
                        tokens_in=pipeline_stats.get("tokens_in", 0),
                        tokens_out=pipeline_stats.get("tokens_out", 0),
                        files_created=pipeline_task.results.get("files_created", []) if pipeline_task.results else [],
                        subtasks_completed=pipeline_stats.get("subtasks_completed", 0),
                        subtasks_total=pipeline_stats.get("subtasks_total", 0),
                    )
                except Exception as hist_err:
                    logger.debug(f"[Pipeline History] Failed to record: {hist_err}")

            except Exception as e:
                logger.debug(f"[Pipeline Stats] Failed to record: {e}")
            # MARKER_126.0A_END

            # MARKER_133.TRACKER: Auto-track task completion in digest
            try:
                from src.services.task_tracker import on_task_completed
                await on_task_completed(
                    task_id=task_id,
                    task_title=task[:200],
                    status="done" if pipeline_stats.get("success") else "failed",
                    stats=pipeline_stats,
                    source=f"dragon_{self.preset_name}" if self.preset_name else "dragon",
                )
            except Exception as track_err:
                logger.debug(f"[Pipeline Tracker] Failed: {track_err}")

            # MARKER_134.FEEDBACK_B: Save structured final report for feedback loop
            try:
                from src.services.feedback_service import save_report
                completed = sum(1 for s in pipeline_task.subtasks if s.status == "done")
                total = len(pipeline_task.subtasks)
                issues_found = []
                for s in pipeline_task.subtasks:
                    vf = getattr(s, "verifier_feedback", None)
                    if isinstance(vf, dict) and not vf.get("passed", True):
                        issues_found.append({
                            "type": "verifier_fail",
                            "marker": s.marker or "unknown",
                            "confidence": vf.get("confidence", 0),
                            "issues": vf.get("issues", []),
                            "severity": vf.get("severity", "minor"),
                        })
                final_report = {
                    "run_id": task_id,
                    "task": task[:200],
                    "summary": f"Completed {completed}/{total} subtasks",
                    "quality_score": pipeline_stats.get("verifier_avg_confidence", 0),
                    "issues_found": issues_found,
                    "improvements_for_next_run": [],
                    "files_created": pipeline_task.results.get("files_created", []) if pipeline_task.results else [],
                    "tokens_used": pipeline_stats.get("tokens_in", 0) + pipeline_stats.get("tokens_out", 0),
                    "duration_s": pipeline_stats.get("duration_s", 0),
                    "preset": self.preset_name,
                    "status": "done" if pipeline_stats.get("success") else "failed",
                    "subtasks_total": total,
                    "subtasks_completed": completed,
                    "retries": sum(getattr(s, "retry_count", 0) for s in pipeline_task.subtasks),
                    "tier_upgrades": pipeline_stats.get("tier_upgrades", 0),
                }
                save_report(final_report)
                logger.info(f"[Feedback] Final report saved: {task_id}")
            except Exception as fb_err:
                logger.error(f"[Feedback] Final report save failed: {fb_err}")
            # MARKER_134.FEEDBACK_B_END

            # MARKER_117.5A: Event-driven wakeup after pipeline completion
            # Cursor insight: "Planners should wake when tasks complete"
            # Auto-check chat for follow-up @dragon tasks
            try:
                from src.orchestration.mycelium_heartbeat import on_pipeline_complete
                await on_pipeline_complete(self.chat_id)
            except Exception as e:
                logger.debug(f"[Pipeline] Wakeup hook skipped: {e}")
            # MARKER_117.5A_END

            return asdict(pipeline_task)

        except PipelineCancelled as e:
            # MARKER_126.5C: Graceful cancellation — save progress, emit message
            logger.info(f"[Pipeline] Cancelled: {e}")
            completed_count = len([s for s in pipeline_task.subtasks if s.status == "done"])
            pipeline_task.status = "cancelled"
            pipeline_task.results = {
                "error": f"Cancelled: {e}",
                "subtasks_completed": completed_count,
                "subtasks_total": len(pipeline_task.subtasks),
            }
            self._update_task(pipeline_task)
            self._log_stm_summary()
            self._bridge_to_global_stm(task_id, phase_type)

            # Update TaskBoard if board-dispatched
            if hasattr(self, '_board_task_id') and self._board_task_id:
                try:
                    from src.orchestration.task_board import get_task_board
                    from datetime import datetime as _dt
                    board = get_task_board()
                    board.update_task(self._board_task_id, status="cancelled",
                                     completed_at=_dt.now().isoformat())
                except Exception:
                    pass

            await self._emit_progress("@mycelium", f"⏹ Pipeline cancelled ({completed_count}/{len(pipeline_task.subtasks)} done): {str(e)[:40]}")
            return asdict(pipeline_task)

        except Exception as e:
            logger.error(f"[Pipeline] Failed: {e}")
            pipeline_task.status = "failed"
            pipeline_task.results = {"error": str(e)}
            self._update_task(pipeline_task)

            # MARKER_104_MEMORY_STM: Log memory compression statistics even on failure
            self._log_stm_summary()
            # MARKER_119.2: Report even failed pipeline to global STMBuffer
            self._bridge_to_global_stm(task_id, phase_type)

            await self._emit_progress("@mycelium", f"❌ Pipeline failed: {str(e)[:50]}")
            return asdict(pipeline_task)
    # MARKER_102.4_END

    # MARKER_104_PARALLEL_3: Sequential execution method (STM context passing)
    # MARKER_104_STREAM_VISIBILITY: Added visibility-aware progress emission
    async def _execute_subtasks_sequential(
        self, pipeline_task: PipelineTask, phase_type: str, total_subtasks: int
    ):
        """
        Execute subtasks sequentially (default, safe mode).
        Preserves STM context passing between subtasks.
        Uses visibility flags for selective streaming (Phase 104.7).
        """
        # Get pipeline-level stream visibility
        stream_level = pipeline_task.stream_level

        for i, subtask in enumerate(pipeline_task.subtasks):
            # MARKER_126.5B: Check cancellation before each subtask
            self._check_cancelled()
            logger.info(f"[Pipeline] Subtask {i+1}/{total_subtasks}: {subtask.description[:40]}...")

            # MARKER_104_STREAM_VISIBILITY: Check subtask visibility
            if not subtask.visible:
                logger.debug(f"[Pipeline] Subtask {i+1} hidden (visible=False)")

            # Inject STM context from previous subtasks
            if self.stm:
                stm_summary = self._get_stm_summary()
                if subtask.context is None:
                    subtask.context = {}
                subtask.context["previous_results"] = stm_summary

            # MARKER_122.5D: Inject scout report for coder awareness
            if getattr(self, '_scout_context', None):
                if subtask.context is None:
                    subtask.context = {}
                subtask.context["scout_report"] = self._scout_context

            # Auto-trigger research on needs_research flag
            if subtask.needs_research:
                subtask.status = "researching"
                self._update_task(pipeline_task)

                # Emit progress only if subtask is visible
                # MARKER_117.6C: Model attribution for researcher
                researcher_model = self.prompts.get("researcher", {}).get("model", "")
                if subtask.visible:
                    await self._emit_progress("@researcher", f"🔍 Researching: {subtask.description[:40]}...", i+1, total_subtasks, model=researcher_model)

                # Use description as question if no explicit question
                question = subtask.question or subtask.description
                research = await self._research(question)

                if subtask.context is None:
                    subtask.context = {}
                subtask.context.update(research)

                # MARKER_117_2A_FIX_D: Emit research summary to chat
                # Previously research was only stored in subtask.context, invisible in UI
                if subtask.visible:
                    confidence = research.get("confidence", "N/A")
                    insights = research.get("insights", [])
                    insights_preview = "; ".join(str(ins)[:60] for ins in insights[:3])
                    await self._emit_progress(
                        "@researcher",
                        f"🔍 Research done (confidence: {confidence}): {insights_preview}",
                        i+1, total_subtasks, model=self._last_used_model
                    )

                # Recursive: if researcher has further questions with low confidence
                if research.get("confidence", 1.0) < 0.7:
                    for fq in research.get("further_questions", [])[:2]:  # Max 2 recursions
                        sub_research = await self._research(fq)
                        enriched = subtask.context.get("enriched_context", "")
                        subtask.context["enriched_context"] = enriched + f"\n\nFollow-up ({fq}):\n{sub_research.get('enriched_context', '')}"

            # Execute subtask
            subtask.status = "executing"
            self._update_task(pipeline_task)

            # MARKER_117.6C: Model attribution for coder
            coder_model = self.prompts.get("coder", {}).get("model", "")
            # Emit progress only if subtask is visible
            if subtask.visible:
                await self._emit_progress("@coder", f"⚙️ Executing: {subtask.description[:40]}...", i+1, total_subtasks, model=coder_model)

            # MARKER_133.C33B: Coder phase with timeout
            result = await self._safe_phase("coder", self._execute_subtask(subtask, phase_type))
            if result is None:
                # Coder timed out — mark subtask as failed and continue
                subtask.status = "failed"
                subtask.result = "Coder phase timed out"
                self._update_task(pipeline_task)
                continue

            # MARKER_122.3: Verify-Retry loop (only for fix/build phases)
            if phase_type in ("fix", "build") and "verifier" in self.prompts:
                verifier_model = self.prompts.get("verifier", {}).get("model", "")
                if subtask.visible:
                    await self._emit_progress("@verifier", f"🔎 Verifying: {subtask.marker or f'step_{i+1}'}...", i+1, total_subtasks, model=verifier_model)
                # MARKER_133.C33B: Verifier phase with timeout
                verification = await self._safe_phase("verifier", self._verify_subtask(subtask, result, phase_type))
                if verification is None:
                    # Verifier timed out — assume passed to continue pipeline
                    verification = {"passed": True, "confidence": 0.5, "issues": ["Verifier timed out"]}

                # MARKER_127.3: Default passed=False (not True) — missing field = not passed
                # Also: major severity gets ONE retry before escalation (was: instant break)
                while not verification.get("passed", False) and subtask.retry_count < MAX_CODER_RETRIES:
                    sev = verification.get("severity", "minor")
                    if sev == "major" and subtask.retry_count > 0:
                        # Already retried once for major — now escalate
                        subtask.escalated = True
                        if subtask.visible:
                            await self._emit_progress("@verifier", f"🚨 Major issue after retry — escalating", i+1, total_subtasks)
                        break
                    if sev == "major" and subtask.visible:
                        await self._emit_progress("@verifier", f"⚠️ Major issue — retrying coder once", i+1, total_subtasks)
                    # Retry coder with feedback
                    result = await self._retry_coder(subtask, verification, phase_type)
                    # MARKER_133.C33B: Verifier retry with timeout
                    verification = await self._safe_phase("verifier", self._verify_subtask(subtask, result, phase_type))
                    if verification is None:
                        verification = {"passed": True, "confidence": 0.5, "issues": ["Verifier timed out"]}
                        break  # Exit retry loop on timeout

                # MARKER_122.4: Tier upgrade as last resort
                if not verification.get("passed", False) and subtask.retry_count >= MAX_CODER_RETRIES and not subtask.escalated:
                    if self._upgrade_coder_tier():
                        await self._emit_progress("system", f"⚡ Upgrading coder tier to {self.preset_name}")
                        subtask.retry_count = 0
                        # MARKER_133.C33B: Coder tier upgrade with timeout
                        result = await self._safe_phase("coder", self._execute_subtask(subtask, phase_type))
                        if result is None:
                            result = "Coder phase timed out during tier upgrade"
                        verification = await self._safe_phase("verifier", self._verify_subtask(subtask, result, phase_type))
                        if verification is None:
                            verification = {"passed": True, "confidence": 0.5, "issues": ["Verifier timed out"]}

                # MARKER_127.1A: Store verification dict for stats (confidence collection)
                subtask.verifier_feedback = verification

                # MARKER_134.FEEDBACK_A: Persist verifier feedback if quality < 0.8
                if verification and verification.get("confidence", 1.0) < 0.8:
                    try:
                        from src.services.feedback_service import save_verifier_feedback
                        save_verifier_feedback(
                            task_id=task_id,
                            subtask_marker=subtask.marker or f"step_{i+1}",
                            score=verification.get("confidence", 0),
                            issues=verification.get("issues", []),
                            suggestion="; ".join(str(s) for s in verification.get("suggestions", verification.get("issues", []))),
                            severity=verification.get("severity", "medium"),
                        )
                    except Exception as fb_err:
                        logger.debug(f"[Feedback] Verifier save failed: {fb_err}")
                # MARKER_134.FEEDBACK_A_END

                if subtask.visible:
                    v_icon = "✅" if verification.get("passed", True) else "⚠️"
                    await self._emit_progress("@verifier", f"{v_icon} Verified: confidence={verification.get('confidence', 'N/A')}", i+1, total_subtasks, model=self._last_used_model)
            # MARKER_122.3_END

            subtask.result = result
            subtask.status = "done"

            # Emit completion based on visibility flags
            if subtask.visible:
                await self._emit_progress("@coder", f"✅ Done: {subtask.marker or f'step_{i+1}'}", i+1, total_subtasks, model=self._last_used_model)
                # MARKER_117_2A_FIX_D: Emit coder result preview to chat
                # Previously only marker name was emitted, not the actual result
                if result and isinstance(result, str) and len(result) > 10:
                    result_preview = result[:300].replace('\n', ' ')
                    if len(result) > 300:
                        result_preview += "..."
                    await self._emit_progress("@coder", f"💻 Result: {result_preview}", i+1, total_subtasks)

            # MARKER_104_STREAM_VISIBILITY: Emit stream event with result if stream_result=True
            if subtask.stream_result and pipeline_task.visible_to_user:
                self._emit_stream_event(
                    "subtask_completed",
                    {
                        "subtask_idx": i + 1,
                        "total": total_subtasks,
                        "marker": subtask.marker or f"step_{i+1}",
                        "result": result,
                        "highlight_artifacts": pipeline_task.highlight_artifacts
                    },
                    visibility=stream_level
                )

            # Add to STM for next subtask
            self._add_to_stm(subtask.marker or f"step_{i+1}", result)

            # MARKER_117.5B: Auto context reset to combat drift (Cursor insight)
            # "Periodic fresh starts" — when STM grows beyond threshold,
            # compress to summary and reset. Prevents context drift in long runs.
            if len(self.stm) >= MAX_STM_BEFORE_RESET:
                summary = self._get_stm_summary()
                self.stm = [{
                    "marker": "CONTEXT_RESET",
                    "result": f"[Reset after {MAX_STM_BEFORE_RESET} subtasks] Summary: {summary[:500]}"
                }]
                await self._emit_progress(
                    "system",
                    f"🔄 Context reset after {MAX_STM_BEFORE_RESET} subtasks (anti-drift)"
                )
                logger.info(f"[Pipeline] STM reset after {MAX_STM_BEFORE_RESET} subtasks (anti-drift)")
            # MARKER_117.5B_END

            self._update_task(pipeline_task)

        # MARKER_122.5: Architect escalation for major failures
        escalated = [s for s in pipeline_task.subtasks if getattr(s, 'escalated', False)]
        if escalated and hasattr(self, '_replan_count'):
            pass  # replan_count tracked in execute()
        if escalated:
            replan_count = getattr(pipeline_task, '_replan_count', 0)
            if replan_count < MAX_ARCHITECT_REPLANS:
                pipeline_task._replan_count = replan_count + 1
                await self._emit_progress("@architect", f"🔄 Escalation: re-planning {len(escalated)} failed subtasks...")
                new_plan = await self._escalate_to_architect(
                    pipeline_task.task, escalated, {},
                    phase_type, None
                )
                # Create new subtasks from re-plan and execute them
                new_subtasks = [
                    Subtask(**st) if isinstance(st, dict) else st
                    for st in new_plan.get("subtasks", [])
                ]
                if new_subtasks:
                    # Replace escalated subtasks with new ones
                    for ns in new_subtasks:
                        pipeline_task.subtasks.append(ns)
                    new_total = len(new_subtasks)
                    await self._emit_progress("@architect", f"📋 Re-plan: {new_total} new subtasks")
                    # Execute only new subtasks
                    old_subtasks = pipeline_task.subtasks
                    pipeline_task.subtasks = new_subtasks
                    await self._execute_subtasks_sequential(pipeline_task, phase_type, new_total)
                    pipeline_task.subtasks = old_subtasks + new_subtasks
        # MARKER_122.5_END
    # MARKER_104_PARALLEL_3_END

    # MARKER_104_PARALLEL_4: Parallel execution with asyncio.gather()
    # MARKER_104_STREAM_VISIBILITY: Added visibility-aware progress emission
    async def _execute_subtasks_parallel(
        self, pipeline_task: PipelineTask, phase_type: str, total_subtasks: int
    ):
        """
        Execute subtasks in parallel with semaphore control.

        Phase 104.2: Uses MAX_PARALLEL_PIPELINES to limit concurrency.
        Phase 104.7: Uses visibility flags for selective streaming.
        Note: STM context is not passed between parallel subtasks (by design).
        """
        semaphore = _get_pipeline_semaphore()
        stream_level = pipeline_task.stream_level

        await self._emit_progress(
            "@mycelium",
            f"⚡ Parallel execution mode (max {MAX_PARALLEL_PIPELINES} concurrent)"
        )
        logger.info(f"[Pipeline] Parallel execution with semaphore limit={MAX_PARALLEL_PIPELINES}")

        async def run_subtask_with_limit(idx: int, subtask: Subtask) -> tuple[int, str]:
            """Run single subtask with semaphore limit and visibility control."""
            async with semaphore:
                logger.info(f"[Pipeline] Parallel subtask {idx+1}/{total_subtasks} acquired semaphore")

                # MARKER_104_STREAM_VISIBILITY: Check subtask visibility before emitting
                if subtask.visible:
                    await self._emit_progress("@coder", f"⚙️ [P] Executing: {subtask.description[:35]}...", idx+1, total_subtasks)

                # MARKER_122.5E: Inject scout report for parallel subtasks
                if getattr(self, '_scout_context', None):
                    if subtask.context is None:
                        subtask.context = {}
                    subtask.context["scout_report"] = self._scout_context

                # Auto-trigger research if needed (inside semaphore)
                    subtask.status = "researching"
                    if subtask.visible:
                        await self._emit_progress("@researcher", f"🔍 [P] Researching: {subtask.description[:35]}...", idx+1, total_subtasks)

                    question = subtask.question or subtask.description
                    research = await self._research(question)

                    if subtask.context is None:
                        subtask.context = {}
                    subtask.context.update(research)

                    # MARKER_117_2A_FIX_D: Emit research summary (parallel path)
                    if subtask.visible:
                        confidence = research.get("confidence", "N/A")
                        insights = research.get("insights", [])
                        insights_preview = "; ".join(str(ins)[:60] for ins in insights[:3])
                        await self._emit_progress(
                            "@researcher",
                            f"🔍 [P] Research done (confidence: {confidence}): {insights_preview}",
                            idx+1, total_subtasks
                        )

                    # Recursive research for low confidence
                    if research.get("confidence", 1.0) < 0.7:
                        for fq in research.get("further_questions", [])[:2]:
                            sub_research = await self._research(fq)
                            enriched = subtask.context.get("enriched_context", "")
                            subtask.context["enriched_context"] = enriched + f"\n\nFollow-up ({fq}):\n{sub_research.get('enriched_context', '')}"

                # Execute subtask
                subtask.status = "executing"
                # MARKER_133.C33B: Coder phase with timeout (parallel path)
                result = await self._safe_phase("coder", self._execute_subtask(subtask, phase_type))
                if result is None:
                    subtask.status = "failed"
                    subtask.result = "Coder phase timed out"
                    return (idx, None)

                # MARKER_122.3: Verify-Retry loop (parallel path)
                if phase_type in ("fix", "build") and "verifier" in self.prompts:
                    if subtask.visible:
                        await self._emit_progress("@verifier", f"🔎 [P] Verifying: {subtask.marker or f'step_{idx+1}'}...", idx+1, total_subtasks)
                    # MARKER_133.C33B: Verifier phase with timeout (parallel path)
                    verification = await self._safe_phase("verifier", self._verify_subtask(subtask, result, phase_type))
                    if verification is None:
                        verification = {"passed": True, "confidence": 0.5, "issues": ["Verifier timed out"]}
                    # MARKER_127.3: Default passed=False, major gets one retry (parallel path)
                    while not verification.get("passed", False) and subtask.retry_count < MAX_CODER_RETRIES:
                        sev = verification.get("severity", "minor")
                        if sev == "major" and subtask.retry_count > 0:
                            subtask.escalated = True
                            break
                        result = await self._retry_coder(subtask, verification, phase_type)
                        # MARKER_133.C33B: Verifier retry with timeout (parallel path)
                        verification = await self._safe_phase("verifier", self._verify_subtask(subtask, result, phase_type))
                        if verification is None:
                            verification = {"passed": True, "confidence": 0.5, "issues": ["Verifier timed out"]}
                            break
                    # MARKER_127.1A: Store verification dict for stats (parallel path)
                    subtask.verifier_feedback = verification
                # MARKER_122.3_END

                subtask.result = result
                subtask.status = "done"

                # MARKER_104_STREAM_VISIBILITY: Emit based on visibility flags
                if subtask.visible:
                    await self._emit_progress("@coder", f"✅ [P] Done: {subtask.marker or f'step_{idx+1}'}", idx+1, total_subtasks)
                    # MARKER_117_2A_FIX_D: Emit coder result preview (parallel path)
                    if result and isinstance(result, str) and len(result) > 10:
                        result_preview = result[:300].replace('\n', ' ')
                        if len(result) > 300:
                            result_preview += "..."
                        await self._emit_progress("@coder", f"💻 [P] Result: {result_preview}", idx+1, total_subtasks)

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
                subtask = pipeline_task.subtasks[idx]

                # Add to STM (order may vary in parallel mode)
                self._add_to_stm(subtask.marker or f"step_{idx+1}", result)

                # MARKER_104_STREAM_VISIBILITY: Emit stream event if stream_result=True
                if subtask.stream_result and pipeline_task.visible_to_user:
                    self._emit_stream_event(
                        "subtask_completed",
                        {
                            "subtask_idx": idx + 1,
                            "total": total_subtasks,
                            "marker": subtask.marker or f"step_{idx+1}",
                            "result": result,
                            "highlight_artifacts": pipeline_task.highlight_artifacts,
                            "parallel": True
                        },
                        visibility=stream_level
                    )

        # Update pipeline task state
        self._update_task(pipeline_task)
    # MARKER_104_PARALLEL_5_END

    # MARKER_102.5_START: Architect planning
    async def _architect_plan(self, task: str, phase_type: str, scout_context: Optional[Dict] = None,
                               research_context: Optional[Dict] = None,
                               replan_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Architect breaks down task into subtasks.
        Marks unclear parts with needs_research=True.

        Args:
            scout_context: Optional scout report injected into user message (MARKER_119.4).
            research_context: Optional research results for PM pass (MARKER_122).
            replan_context: Optional failure context for re-planning (MARKER_122).
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
        # MARKER_117_PROVIDER: Pass model_source for provider routing
        # MARKER_117_2B_INJECT: Inject chat context so architect sees recent messages/bugs
        # MARKER_119.4: Build user message with optional scout context
        user_content = f"Phase type: {phase_type}\n\nTask to break down:\n{task}"
        if scout_context:
            scout_summary = json.dumps(scout_context, indent=2)[:800]
            user_content += f"\n\n[Scout Report]\n{scout_summary}"
        # MARKER_122: Inject research context for PM pass
        if research_context and isinstance(research_context, dict):
            research_summary = research_context.get("enriched_context", "")[:600]
            insights = research_context.get("insights", [])
            if research_summary or insights:
                user_content += f"\n\n[Research Results]\n{research_summary}"
                if insights:
                    user_content += f"\nKey insights: {'; '.join(str(i)[:80] for i in insights[:3])}"
        # MARKER_122: Inject replan context for architect escalation
        if replan_context:
            user_content += f"\n\n[Re-plan Context]\n{replan_context[:800]}"

        call_args = {
            "model": model,
            "messages": [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": user_content}
            ],
            "temperature": temperature,
            "max_tokens": 2000,
            "inject_context": {
                "chat_id": self.chat_id,
                "chat_limit": 5,
                "semantic_query": task,
                "semantic_limit": 3,
                "include_prefs": True,
                "compress": True
            }
        }
        if self.provider_override:
            call_args["model_source"] = self.provider_override
        # MARKER_129.4: Dual-mode LLM call
        if getattr(self, 'async_mode', False):
            result = await tool.execute(call_args)
        else:
            result = tool.execute(call_args)
        self._track_llm_call(result)
        # MARKER_117.6C: Track architect model for attribution
        self._last_used_model = result.get("result", {}).get("model", call_args.get("model", ""))

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

        # MARKER_119.7: Pre-fetch web search for researcher context
        web_context = ""
        try:
            from src.mcp.tools.web_search_tool import WebSearchTool
            web_tool = WebSearchTool()
            # MARKER_120.4: Enrich query with tech keywords for better Tavily results
            # Raw VETKA-specific questions return nothing; add technology context
            tech_keywords = self._extract_library_names(question)
            search_query = question[:150]
            if tech_keywords:
                search_query = f"{' '.join(tech_keywords)} {search_query}"
            web_result = web_tool.execute({"query": search_query, "max_results": 3})
            if web_result.get("success"):
                results = web_result.get("result", {}).get("results", [])
                if results:
                    snippets = []
                    for r in results[:3]:
                        snippets.append(f"- {r.get('title', '')} ({r.get('url', '')})\n  {r.get('content', '')[:300]}")
                    web_context = "\n\n[Web Search Results]\n" + "\n".join(snippets)
                    logger.info(f"[Pipeline] Web search: {len(results)} results for researcher")
        except Exception as e:
            logger.debug(f"[Pipeline] Web search skipped: {e}")
        # MARKER_119.7_END

        # LLMCallTool.execute is synchronous
        # MARKER_117_PROVIDER: Pass model_source for provider routing
        user_content = f"Research this for VETKA project:\n\n{question}{web_context}"
        call_args = {
            "model": model,
            "messages": [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": user_content}
            ],
            "temperature": temperature,
            "max_tokens": 1500,
            "inject_context": {
                "chat_id": self.chat_id,
                "chat_limit": 3,
                "semantic_query": question,
                "semantic_limit": 5,
                "include_prefs": True,
                "compress": True
            }
        }
        if self.provider_override:
            call_args["model_source"] = self.provider_override
        # MARKER_129.4: Dual-mode LLM call
        if getattr(self, 'async_mode', False):
            result = await tool.execute(call_args)
        else:
            result = tool.execute(call_args)
        self._track_llm_call(result)
        # MARKER_117.6C: Track researcher model for attribution
        self._last_used_model = result.get("result", {}).get("model", call_args.get("model", ""))

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
            # MARKER_122.5A: Pass STM previous results to coder
            if subtask.context.get("previous_results"):
                context_parts.append(f"Previous subtask results:\n{subtask.context['previous_results']}")
            # MARKER_122.5B: Pass scout report to coder
            if subtask.context.get("scout_report"):
                scout = subtask.context["scout_report"]
                files = ", ".join(scout.get("relevant_files", [])[:5])
                patterns = "; ".join(scout.get("patterns_found", [])[:3])
                # MARKER_128.1B: Inject detected project imports into coder context
                project_ctx = scout.get("project_context", "")
                scout_str = ""
                if project_ctx:
                    scout_str = f"{project_ctx}\n"
                scout_str += f"Project files: {files}"
                if patterns:
                    scout_str += f"\nPatterns to follow: {patterns}"
                # MARKER_124.9B: Format marker_map as rails for coder
                marker_map = scout.get("marker_map", [])
                if marker_map and isinstance(marker_map, list):
                    scout_str += "\n\n🚂 MARKER RAILS (follow these like a GPS):"
                    for m in marker_map[:5]:
                        if isinstance(m, dict):
                            f_path = m.get("file", "?")
                            line = m.get("line", "?")
                            action = m.get("action", "MODIFY")
                            mid = m.get("marker_id", "MARKER_SCOUT_X")
                            desc = m.get("description", "")
                            scout_str += f"\n  📍 {mid}: {f_path}:{line} [{action}] — {desc}"
                    scout_str += "\n\nUse vetka_read_file(file_path, marker='MARKER_SCOUT_X') to jump to each location."
                context_parts.append(f"Scout report:\n{scout_str}")

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

        # MARKER_119.8: Pre-fetch library docs for coder context
        lib_context = ""
        if phase_type in ["fix", "build"]:
            try:
                from src.mcp.tools.library_docs_tool import LibraryDocsTool
                lib_tool = LibraryDocsTool()
                libraries = self._extract_library_names(subtask.description + " " + context_str)
                for lib_name in libraries[:2]:
                    lib_result = lib_tool.execute({"library": lib_name, "topic": subtask.description, "tokens": 2000})
                    if lib_result.get("success"):
                        docs = lib_result.get("result", {}).get("docs", "")
                        if docs:
                            lib_context += f"\n\n[{lib_name} docs]\n{docs[:1500]}"
                            logger.info(f"[Pipeline] Library docs: fetched {lib_name} for coder")
            except Exception as e:
                logger.debug(f"[Pipeline] Library docs skipped: {e}")
        # MARKER_119.8_END

        # MARKER_102.22_START: Fixed LLM call + context passing
        # LLMCallTool.execute is synchronous
        # MARKER_117_PROVIDER: Pass model_source for provider routing
        call_args = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""
Phase type: {phase_type}
Subtask: {subtask.description}
Marker: {subtask.marker or 'MARKER_102.X'}

{context_str}{lib_context}

Execute this subtask. Provide clear, actionable output."""}
            ],
            "temperature": temperature,
            "max_tokens": 2000
        }
        if self.provider_override:
            call_args["model_source"] = self.provider_override
        # MARKER_122.5F: Inject codebase context for coder (semantic search from Qdrant)
        if phase_type in ("fix", "build"):
            call_args["inject_context"] = {
                "semantic_query": subtask.description,
                "semantic_limit": 3,
                "compress": True
            }

        # MARKER_123.1A: Function Calling for coder (async FC loop)
        # Gives coder read-only tools (vetka_read_file, vetka_search_semantic, etc.)
        # so it can read actual file contents before writing code.
        # Falls back to one-shot if FC unavailable or fails.
        if phase_type in ("fix", "build") and FC_LOOP_AVAILABLE:
            try:
                coder_tool_schemas = get_coder_tool_schemas()
                if coder_tool_schemas:
                    fc_result = await execute_fc_loop(
                        model=model,
                        messages=call_args["messages"],
                        tool_schemas=coder_tool_schemas,
                        max_turns=MAX_FC_TURNS_CODER,
                        temperature=temperature,
                        max_tokens=4000,
                        provider_source=self.provider_override,
                        progress_callback=self._emit_progress,
                    )
                    # Track model for attribution
                    self._last_used_model = fc_result.get("model", model)
                    # Log tool usage
                    tool_execs = fc_result.get("tool_executions", [])
                    if tool_execs:
                        files_read = [
                            e["args"].get("file_path", "")
                            for e in tool_execs
                            if e["name"] == "vetka_read_file"
                        ]
                        if files_read:
                            logger.info(f"[Pipeline] Coder FC: read {len(files_read)} files: {', '.join(files_read[:5])}")
                            await self._emit_progress("@coder", f"📖 Read {len(files_read)} files via FC")
                    content = fc_result.get("content", "")
                    if content:
                        logger.info(f"[Pipeline] FC subtask result: {content[:100]}...")
                        # Post-process: extract and write files (same as one-shot path)
                        if phase_type == "build" and "```" in content:
                            if self.auto_write:
                                files_created = self._extract_and_write_files(content, subtask)
                                if files_created:
                                    await self._emit_progress("@coder", f"📁 Created {len(files_created)} files: {', '.join(files_created)}")
                                    content += f"\n\n[Pipeline Note: Created files - {', '.join(files_created)}]"
                            else:
                                await self._emit_progress("@coder", f"📝 Code staged in JSON (auto_write=False)")
                                content += f"\n\n[Pipeline Note: Code staged - use retro_apply_spawn.py to create files]"
                        return content
                    else:
                        logger.warning("[Pipeline] FC returned empty content, falling back to one-shot")
            except Exception as e:
                logger.warning(f"[Pipeline] FC loop failed ({e}), falling back to one-shot")
        # MARKER_123.1A_END

        # Original one-shot path (fallback if FC unavailable/failed)
        # MARKER_129.4: Dual-mode LLM call
        if getattr(self, 'async_mode', False):
            result = await tool.execute(call_args)
        else:
            result = tool.execute(call_args)
        self._track_llm_call(result)
        # MARKER_117.6C: Track coder model for attribution
        self._last_used_model = result.get("result", {}).get("model", call_args.get("model", ""))

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
                            await self._emit_progress("@coder", f"📁 Created {len(files_created)} files: {', '.join(files_created)}")
                            content += f"\n\n[Pipeline Note: Created files - {', '.join(files_created)}]"
                    else:
                        # Staging mode - just log, files stay in JSON for retro_apply
                        await self._emit_progress("@coder", f"📝 Code staged in JSON (auto_write=False)")
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

    # MARKER_119.8_HELPER: Extract library names from task description
    # MARKER_120.2: Enhanced with known frameworks + capitalized name detection
    @staticmethod
    def _extract_library_names(text: str) -> list:
        """Extract library/package names from text for Context7 lookup.

        Looks for patterns like 'import X', 'using X', 'X library',
        and known framework names (React, Three.js, Zustand, etc.).
        Returns up to 5 unique library names, filtering common stopwords.
        """
        import re

        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "is", "it", "this", "that", "with", "from", "as", "by", "be",
            "code", "file", "function", "class", "method", "variable", "project",
            "task", "subtask", "implement", "create", "add", "fix", "update",
            "build", "test", "error", "bug", "feature", "new", "old", "use",
            "using", "import", "module", "package", "library", "framework",
            "vetka", "marker", "phase", "research", "context", "system",
            "check", "look", "find", "should", "must", "need", "make",
            "component", "components", "canvas", "client", "src", "app",
        }

        # Known frameworks/libraries that Context7 has docs for
        known_libs = {
            "react": "react", "vue": "vue", "angular": "angular",
            "svelte": "svelte", "nextjs": "nextjs", "next.js": "nextjs",
            "three.js": "threejs", "threejs": "threejs", "three": "threejs",
            "zustand": "zustand", "redux": "redux", "mobx": "mobx",
            "fastapi": "fastapi", "django": "django", "flask": "flask",
            "express": "express", "nestjs": "nestjs",
            "tailwindcss": "tailwindcss", "tailwind": "tailwindcss",
            "typescript": "typescript", "prisma": "prisma",
            "tauri": "tauri", "electron": "electron",
            "numpy": "numpy", "pandas": "pandas", "pytorch": "pytorch",
            "tensorflow": "tensorflow", "scipy": "scipy",
            "httpx": "httpx", "requests": "requests", "axios": "axios",
            "socketio": "socketio", "socket.io": "socketio",
            "qdrant": "qdrant", "weaviate": "weaviate",
            "ffmpeg": "ffmpeg", "whisper": "whisper",
            "pydantic": "pydantic", "sqlalchemy": "sqlalchemy",
        }

        names = set()
        text_lower = text.lower()

        # Pattern 1: Known framework names (case-insensitive scan)
        for keyword, lib_name in known_libs.items():
            if keyword in text_lower:
                names.add(lib_name)

        # Pattern 2: import X / from X
        for m in re.finditer(r'(?:import|from)\s+([a-zA-Z][a-zA-Z0-9_-]+)', text):
            name = m.group(1).lower().split(".")[0]
            if name not in stopwords and len(name) > 1:
                names.add(name)

        # Pattern 3: using X / with X framework/library
        for m in re.finditer(r'(?:using|with)\s+([a-zA-Z][a-zA-Z0-9_.-]+)\s*(?:library|framework|package|sdk)?', text, re.IGNORECASE):
            name = m.group(1).lower().rstrip(".")
            if name not in stopwords and len(name) > 1:
                names.add(name)

        # Pattern 4: X library/framework/package/docs
        for m in re.finditer(r'([a-zA-Z][a-zA-Z0-9_.-]+)\s+(?:library|framework|package|sdk|docs|documentation|api|hook|hooks|store)', text, re.IGNORECASE):
            name = m.group(1).lower().rstrip(".")
            if name not in stopwords and len(name) > 1:
                names.add(name)

        return list(names)[:5]
    # MARKER_119.8_HELPER_END


# MARKER_102.8_START: Convenience functions
async def mycelium_pipeline(
    task: str,
    phase_type: str = "research",
    chat_id: Optional[str] = None,
    auto_write: bool = True
) -> Dict[str, Any]:
    """
    Mycelium Pipeline for fractal agent execution.

    Args:
        task: Task description
        phase_type: "research" | "fix" | "build"
        chat_id: Optional chat ID for progress streaming
        auto_write: If True, write files immediately. If False, only save to JSON
                   (use retro_apply_spawn.py to create files later)

    Usage:
        # Auto-write mode (default) - files created immediately
        result = await mycelium_pipeline("Implement UI artifacts", "build")

        # Staging mode - files saved to JSON, apply later after review
        result = await mycelium_pipeline("Implement critical feature", "build", auto_write=False)
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
