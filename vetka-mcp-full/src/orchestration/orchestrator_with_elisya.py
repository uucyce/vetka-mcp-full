"""
VETKA Agent Orchestrator with Elisya Integration

Features:
- Elisya State as shared memory
- Elisya Middleware for context reframing
- ModelRouter for intelligent LLM routing
- KeyManager for API key management
- Parallel execution (Dev || QA)
- M4 Pro protection via semaphore

@status: active
@phase: 96
@depends: src.agents, src.elisya, src.orchestration.services, src.mcp.state
@used_by: main.py, src.api.handlers.chat_handler
"""

import time
import threading
import os
import logging
import asyncio  # Phase 103: for parallel Dev/QA execution
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

from src.agents import VETKAPMAgent, VETKADevAgent, VETKAQAAgent, VETKAArchitectAgent
from src.agents.streaming_agent import StreamingAgent
from src.orchestration.progress_tracker import ProgressTracker
from src.orchestration.memory_manager import MemoryManager
from src.orchestration.query_dispatcher import get_dispatcher, RouteStrategy

# ============ AGENT TOOLS IMPORTS (Phase 17-L) ============
from src.tools import registry, SafeToolExecutor, ToolCall, PermissionLevel
from src.agents.tools import (
    get_tools_for_agent,
    AGENT_TOOL_PERMISSIONS,
)
# Note: CreateArtifactTool removed by Big Pickle in Phase 92

# Phase 80.10: Use Provider Registry for clean provider routing
from src.elisya.provider_registry import (
    call_model_v2,
    Provider,
    ProviderRegistry,
    get_registry,
    XaiKeysExhausted,  # Phase 90.1.4.2: Handle XAI key exhaustion
)

# Keep old call_model as fallback
from src.elisya.api_aggregator_v3 import call_model as call_model_legacy

# ============ CHAIN CONTEXT IMPORTS (Phase 17-K) ============
from src.orchestration.chain_context import ChainContext, create_chain_context

# ============ RESPONSE FORMATTER (Phase 19) ============
from src.orchestration.response_formatter import ResponseFormatter, format_response

# ============ ARC GAP DETECTOR (Phase 99.3) ============
from src.orchestration.arc_gap_detector import detect_conceptual_gaps, get_gap_detector

# ============ ELISYA IMPORTS ============
from src.elisya.state import ElisyaState, ConversationMessage
from src.elisya.middleware import ElisyaMiddleware, MiddlewareConfig

# Phase 80.10: Don't import Provider here - use provider_registry.Provider instead
from src.elisya.model_router_v2 import ModelRouter, TaskType
from src.utils.unified_key_manager import (
    UnifiedKeyManager as KeyManager,
    ProviderType,
    APIKeyRecord,
)
from src.elisya.semantic_path import get_path_generator

# ============ PHASE 55.1: MCP STATE BRIDGE ============
from src.orchestration.services import get_mcp_state_bridge


# ============ PHASE 15-3: RICH CONTEXT INTEGRATION ============
# Import functions from app.main for building rich context
def _get_rich_context_functions():
    """Lazy import to avoid circular dependencies."""
    try:
        from app.main import (
            build_rich_context,
            generate_agent_prompt,
            resolve_node_filepath,
        )

        return build_rich_context, generate_agent_prompt, resolve_node_filepath
    except ImportError as e:
        print(f"⚠️  Could not import rich context functions: {e}")
        return None, None, None


# ============ ARC SOLVER IMPORT ============
from src.agents.arc_solver_agent import create_arc_solver

# ============ PHASE 10 TRANSFORMER IMPORTS ============
from src.transformers.phase9_to_vetka import Phase10Transformer
from src.validators.vetka_validator import VetkaValidator
import json
from pathlib import Path

# === PHASE 55: APPROVAL & FILE LOCKING ===
from src.services.approval_service import get_approval_service, ApprovalStatus
from src.services.file_lock_manager import get_file_lock_manager

# === PHASE 60: LANGGRAPH INTEGRATION ===
# Feature flag controls whether to use LangGraph workflow or legacy orchestrator
# Set to True to enable declarative LangGraph workflow with Phase 29 self-learning
# Phase 60.3: Enabled for testing with environment variable override
FEATURE_FLAG_LANGGRAPH = (
    os.environ.get("VETKA_LANGGRAPH_ENABLED", "true").lower() == "true"
)

# Log feature flag status on module load
print(f"[Phase 60.3] FEATURE_FLAG_LANGGRAPH = {FEATURE_FLAG_LANGGRAPH}")

# ============ SEMAPHORE FOR M4 PRO ============
MAX_CONCURRENT_WORKFLOWS = 2
active_workflows = 0
workflow_lock = threading.Lock()

AGENT_TIMEOUTS = {
    "PM": 30,
    "Architect": 45,
    "Dev": 120,  # Increased from 60 to 120 for complex implementations
    "QA": 40,
    "Merge": 5,
    "Ops": 20,
}


class OrchestratorWithElisya:
    """
    Production orchestrator with full Elisya integration.

    Features:
    - ElisyaState: Shared memory for all agents
    - ElisyaMiddleware: Context reframing per agent
    - ModelRouter: Intelligent LLM selection
    - KeyManager: API key management
    - Parallel execution: Dev & QA simultaneously
    - M4 Pro protection: Semaphore limiting

    SINGLETON: This class uses initialization guard to prevent log flooding.
    Only the first __init__ call performs full initialization with logging.
    """

    # Class-level initialization guard
    _initialized = False
    _init_lock = threading.Lock()

    def __init__(self, socketio=None, sio=None, use_parallel=True):
        """
        Initialize orchestrator with Elisya and refactored services.

        Args:
            socketio: Legacy python-socketio AsyncServer (deprecated parameter name)
            sio: python-socketio AsyncServer instance (Phase 60.2)
            use_parallel: Enable parallel Dev+QA execution
        """
        # Check if this is the first initialization (for logging control)
        with OrchestratorWithElisya._init_lock:
            is_first_init = not OrchestratorWithElisya._initialized
            if is_first_init:
                OrchestratorWithElisya._initialized = True

        # Agents
        self.pm = VETKAPMAgent()
        self.dev = VETKADevAgent()
        self.qa = VETKAQAAgent()
        self.architect = VETKAArchitectAgent()

        # ============ DISPATCHER (Phase B) ============
        # Routes queries to optimal agent chain
        self.dispatcher = get_dispatcher()
        print(f"   • Query Dispatcher: initialized")

        # Socket.IO
        self.socketio = socketio  # Legacy compatibility
        self.sio = sio  # Phase 60.2: python-socketio AsyncServer

        # History
        self.history = []

        # Execution mode
        self.use_parallel = use_parallel
        self._workflow_reflex_runtime_metadata: Dict[str, Any] = {}

        # ============ PHASE 54.1: REFACTORED SERVICES ============
        from src.orchestration.services import (
            APIKeyService,
            MemoryService,
            CAMIntegration,
            VETKATransformerService,
            ElisyaStateService,
            RoutingService,
        )

        # Memory Service (initialize first - others depend on it)
        self.memory_service = MemoryService()
        self.memory = self.memory_service.memory  # Keep backwards compatibility

        # Elisya State Service
        self.elisya_service = ElisyaStateService(memory_manager=self.memory)
        self.middleware = self.elisya_service.middleware  # Backwards compat
        self.path_generator = self.elisya_service.path_generator  # Backwards compat
        self.elisya_states = self.elisya_service.elisya_states  # Backwards compat

        # API Key Service
        self.key_service = APIKeyService()
        self.key_manager = self.key_service.key_manager  # Backwards compat

        # Routing Service
        self.routing_service = RoutingService(default_provider=Provider.OLLAMA)
        self.model_router = self.routing_service.model_router  # Backwards compat
        self.model_routing = {}  # Phase 57.6: Manual model overrides per agent type

        # CAM Integration
        self.cam_service = CAMIntegration(memory_manager=self.memory)
        self._cam_engine = (
            self.cam_service._cam_engine if self.cam_service.is_available() else None
        )

        # VETKA Transformer Service
        self.vetka_service = VETKATransformerService(socketio=socketio)
        self.vetka_transformer = self.vetka_service.vetka_transformer
        self.vetka_validator = self.vetka_service.vetka_validator

        # === PHASE 55: APPROVAL & FILE LOCKING SERVICES ===
        self.approval_service = get_approval_service()
        self.file_lock_manager = get_file_lock_manager()

        # 6. ARC Solver for creative graph transformations
        try:
            self.arc_solver = create_arc_solver(
                memory_manager=self.memory,
                eval_agent=None,  # Will add EvalAgent later if needed
                prefer_api=False,  # Use local Ollama for cost efficiency
            )
            arc_available = True
        except Exception as e:
            if is_first_init:
                print(f"⚠️  ARC Solver init failed: {e}")
            self.arc_solver = None
            arc_available = False

        # === PHASE 76.1: WORKFLOW COUNTER + REPLAY BUFFER ===
        # For LoRA fine-tuning trigger (every 50 workflows or accuracy drop)
        self._workflow_counter = self._load_workflow_counter()
        self._recent_scores: list = []  # Track recent eval scores for accuracy monitoring
        self._replay_buffer = None  # Lazy init

        # Only print initialization summary on first init
        if is_first_init:
            print(
                f"\n✅ Orchestrator with Elisya Integration loaded (Phase 54.1 Refactored)"
            )
            print(f"   • Parallel mode: {use_parallel}")
            print(f"   • Max concurrent: {MAX_CONCURRENT_WORKFLOWS}")
            print(f"   • Services: Memory, Elisya, Keys, Routing, CAM, VETKA")
            print(f"   • ModelRouter: {len(self.model_router.models)} models")
            print(f"   • ARC Solver: {'initialized' if arc_available else 'disabled'}")
            print(f"   • Workflow Counter: {self._workflow_counter} (Phase 76.1)")

    def _load_keys_into_key_manager(self, quiet: bool = False):
        """
        Load API keys from config.json into KeyManager.
        Phase 54.1: Delegated to APIKeyService.

        Args:
            quiet: If True, suppress log output (for repeated initializations)
        """
        # Delegated to APIKeyService - keys already loaded in __init__
        pass

    def _get_or_create_state(self, workflow_id: str, feature: str) -> ElisyaState:
        """Get or create ElisyaState for workflow. Phase 54.1: Delegated to ElisyaStateService."""
        state = self.elisya_service.get_or_create_state(workflow_id, feature)
        # Phase 57.6: Ensure context is never None (fixes slice errors)
        if state.context is None:
            state.context = ""
        if state.raw_context is None:
            state.raw_context = ""
        return state

    def _update_state(self, state: ElisyaState, speaker: str, output: str):
        """Update ElisyaState after agent execution. Phase 54.1: Delegated to ElisyaStateService."""
        return self.elisya_service.update_state(state, speaker, output)

    # ============ PHASE 76.1: WORKFLOW COUNTER FOR LORA TRIGGER ============

    def _load_workflow_counter(self) -> int:
        """
        Load workflow counter from persistent storage.

        Phase 76.1: Counter stored in Qdrant metadata collection.
        Used for LoRA fine-tuning trigger (every 50 workflows).
        """
        try:
            # Try to load from Qdrant metadata
            from src.memory.qdrant_client import get_qdrant_client

            qdrant = get_qdrant_client()

            if qdrant and qdrant.client:
                try:
                    # Check if metadata collection exists
                    collections = qdrant.client.get_collections()
                    existing = {c.name for c in collections.collections}

                    if "vetka_metadata" not in existing:
                        # Create collection
                        from qdrant_client.models import VectorParams, Distance

                        qdrant.client.create_collection(
                            collection_name="vetka_metadata",
                            vectors_config=VectorParams(
                                size=768, distance=Distance.COSINE
                            ),
                        )

                    # Try to retrieve counter
                    results = qdrant.client.retrieve(
                        collection_name="vetka_metadata", ids=["workflow_counter"]
                    )

                    if results:
                        return results[0].payload.get("count", 0)

                except Exception as e:
                    logger.debug(f"[Phase76.1] Counter load from Qdrant failed: {e}")

            # Fallback: Load from config file
            config_path = Path("data/config.json")
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                    return config.get("workflow_counter", 0)

        except Exception as e:
            logger.debug(f"[Phase76.1] Counter load failed: {e}")

        return 0

    def _save_workflow_counter(self, count: int):
        """
        Save workflow counter to persistent storage.

        Phase 76.1: Dual-write to Qdrant + config.json for durability.
        """
        try:
            # Save to Qdrant
            from src.memory.qdrant_client import get_qdrant_client

            qdrant = get_qdrant_client()

            if qdrant and qdrant.client:
                try:
                    from qdrant_client.models import PointStruct

                    point = PointStruct(
                        id="workflow_counter",
                        vector=[0.0] * 768,  # Dummy vector
                        payload={
                            "count": count,
                            "updated_at": datetime.now().isoformat()
                            if "datetime" in dir()
                            else time.time(),
                        },
                    )
                    qdrant.client.upsert(
                        collection_name="vetka_metadata", points=[point]
                    )
                except Exception as e:
                    logger.debug(f"[Phase76.1] Counter save to Qdrant failed: {e}")

            # Also save to config.json as backup
            config_path = Path("data/config.json")
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                config["workflow_counter"] = count
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=2)

        except Exception as e:
            logger.warning(f"[Phase76.1] Counter save failed: {e}")

    def _check_lora_trigger(self) -> bool:
        """
        Check if LoRA fine-tuning should be triggered.

        Phase 76.1: Adaptive trigger from Grok research:
        - Every 50 workflows (baseline)
        - OR accuracy drop >0.1 (adaptive)

        Returns:
            True if LoRA training should be triggered
        """
        # Check counter (every 50 workflows)
        if self._workflow_counter > 0 and self._workflow_counter % 50 == 0:
            logger.info(
                f"[Phase76.1] LoRA trigger: counter reached {self._workflow_counter}"
            )
            return True

        # Check accuracy drop (need at least 10 recent scores)
        if len(self._recent_scores) >= 10:
            recent_avg = sum(self._recent_scores[-10:]) / 10
            # Trigger if average drops below 0.7 (threshold - 0.05 buffer)
            if recent_avg < 0.70:
                logger.info(
                    f"[Phase76.1] LoRA trigger: accuracy drop to {recent_avg:.2f}"
                )
                return True

        return False

    def increment_workflow_counter(self, eval_score: float = 0.0) -> dict:
        """
        Increment workflow counter after successful workflow.

        Phase 76.1: Called after approval_node completes.

        Args:
            eval_score: Final evaluation score (0-1)

        Returns:
            Dict with counter status and trigger info
        """
        # Only count successful workflows (score >= 0.7)
        if eval_score >= 0.7:
            self._workflow_counter += 1
            self._recent_scores.append(eval_score)

            # Keep only last 20 scores
            if len(self._recent_scores) > 20:
                self._recent_scores = self._recent_scores[-20:]

            # Save counter
            self._save_workflow_counter(self._workflow_counter)

            # Check LoRA trigger
            should_trigger = self._check_lora_trigger()

            result = {
                "counter": self._workflow_counter,
                "eval_score": eval_score,
                "recent_avg": sum(self._recent_scores) / len(self._recent_scores)
                if self._recent_scores
                else 0,
                "lora_trigger": should_trigger,
            }

            if should_trigger:
                logger.info(
                    f"[Phase76.1] LoRA trigger activated at workflow {self._workflow_counter}"
                )
                # TODO Phase 76.4: Actually trigger LoRA fine-tuning
                # await self._trigger_lora_training()

            return result

        return {
            "counter": self._workflow_counter,
            "eval_score": eval_score,
            "skipped": True,
            "reason": "score_below_threshold",
        }

    @property
    def replay_buffer(self):
        """
        Lazy initialization of Replay Buffer.

        Phase 76.1: Returns singleton ReplayBuffer instance.
        """
        if self._replay_buffer is None:
            try:
                from src.memory.replay_buffer import get_replay_buffer
                from src.memory.qdrant_client import get_qdrant_client

                qdrant = get_qdrant_client()
                if qdrant and qdrant.client:
                    self._replay_buffer = get_replay_buffer(qdrant.client)
            except Exception as e:
                logger.warning(f"[Phase76.1] ReplayBuffer init failed: {e}")
        return self._replay_buffer

    # ============ EVAL AGENT INTEGRATION (Phase 34) ============

    async def _evaluate_with_eval_agent(
        self, task: str, output: str, context: str = "", complexity: str = "MEDIUM"
    ) -> dict:
        """
        Evaluate agent output using EvalAgent.

        @status ACTIVE
        @calledBy run_workflow (after QA step)
        @lastAudit 2026-01-04

        Args:
            task: Original task description
            output: Agent output to evaluate
            context: Additional context (previous agent outputs)
            complexity: Task complexity (LOW/MEDIUM/HIGH)

        Returns:
            dict with: score (0-1), should_retry (bool), feedback (str)
        """
        try:
            # Lazy import to avoid circular dependencies
            from src.agents.eval_agent import EvalAgent

            if not hasattr(self, "_eval_agent") or self._eval_agent is None:
                self._eval_agent = EvalAgent(memory_manager=self.memory)
                print("   • EvalAgent: initialized")

            # Call evaluate method
            evaluation = self._eval_agent.evaluate(
                task=task, output=output, complexity=complexity, reference=context
            )

            score = evaluation.get("score", 0) if isinstance(evaluation, dict) else 0.5
            print(f"   🎯 EvalAgent score: {score:.2f}")
            return evaluation if isinstance(evaluation, dict) else {"score": score}

        except Exception as e:
            print(f"   ⚠️ EvalAgent evaluation failed: {e}")
            return {
                "score": 0.5,  # Neutral score on failure
                "should_retry": False,
                "feedback": f"Evaluation failed: {str(e)}",
                "error": str(e),
            }

    # ============ CAM ENGINE INTEGRATION (Phase 35) ============

    async def _cam_maintenance_cycle(self) -> dict:
        """
        Background CAM maintenance: prune low-entropy, merge similar subtrees.
        Phase 54.1: Delegated to CAMIntegration service.

        Returns:
            dict with prune_count, merge_count
        """
        return await self.cam_service.maintenance_cycle()

    # ============ ROUTING & KEY MANAGEMENT ============

    def _get_routing_for_task(self, task: str, agent_type: str) -> Dict[str, Any]:
        """Get LLM routing for task. Phase 54.1: Delegated to RoutingService."""
        return self.routing_service.get_routing_for_task(task, agent_type)

    def _inject_api_key(self, routing: Dict[str, Any]) -> Optional[str]:
        """Inject API key for routing. Phase 54.1: Delegated to APIKeyService."""
        provider_name = routing["provider"]
        return self.key_service.get_key(provider_name)

    # ============ SEMAPHORE MANAGEMENT ============

    def _check_semaphore(self, workflow_id: str):
        """Check if we can start a new workflow."""
        global active_workflows

        with workflow_lock:
            if active_workflows >= MAX_CONCURRENT_WORKFLOWS:
                print(
                    f"⏳ [{workflow_id}] Waiting for slot ({active_workflows}/{MAX_CONCURRENT_WORKFLOWS} active)"
                )
                self._emit_status(workflow_id, "orchestrator", "waiting_for_slot")
                return False
            active_workflows += 1
            print(
                f"✅ [{workflow_id}] Acquired slot ({active_workflows}/{MAX_CONCURRENT_WORKFLOWS} active)"
            )
            return True

    def _release_semaphore(self, workflow_id: str):
        """Release workflow slot."""
        global active_workflows

        with workflow_lock:
            active_workflows = max(0, active_workflows - 1)
            print(
                f"🔓 [{workflow_id}] Released slot ({active_workflows}/{MAX_CONCURRENT_WORKFLOWS} active)"
            )

    # ============ SOCKET.IO COMMUNICATION ============

    def _emit_status(self, workflow_id: str, step: str, status: str, **extra):
        """Send Socket.IO status update."""
        if not self.socketio:
            return

        try:
            self.socketio.emit(
                "workflow_status",
                {
                    "workflow_id": workflow_id,
                    "step": step,
                    "status": status,
                    "timestamp": time.time(),
                    **extra,
                },
            )
        except:
            pass

    # ============ PHASE 10 VETKA-JSON TRANSFORMATION ============

    def _collect_infrastructure_data(
        self, workflow_id: str, elisya_state=None
    ) -> Dict[str, Any]:
        """
        Collect data from all infrastructure systems for Phase 10 transformer.
        Phase 54.1: Delegated to VETKATransformerService.
        """
        return self.vetka_service.collect_infrastructure_data(
            workflow_id, elisya_state, self.memory
        )

    def _build_phase9_output(
        self, result: Dict[str, Any], arc_suggestions: list = None, elisya_state=None
    ) -> Dict[str, Any]:
        """
        Build Phase 9 output format for VETKA transformer.
        Phase 54.1: Delegated to VETKATransformerService.
        """
        return self.vetka_service.build_phase9_output(
            result, arc_suggestions, elisya_state, self.memory
        )

    def _transform_and_emit_vetka(
        self, result: Dict[str, Any], arc_suggestions: list = None, elisya_state=None
    ) -> Optional[Dict[str, Any]]:
        """
        Transform workflow result to VETKA-JSON and emit to UI.
        Phase 54.1: Delegated to VETKATransformerService.
        """
        return self.vetka_service.transform_and_emit(
            result, arc_suggestions, elisya_state, self.memory
        )

    # ============ PHASE 15-3: RICH CONTEXT BUILDING ============

    def _build_rich_context_for_workflow(
        self, user_data: Dict[str, Any], feature_request: str
    ) -> Dict[str, Any]:
        """
        Build rich context for agent workflows using Phase 15-3 functions.

        This integrates build_rich_context() from app/main.py into orchestrator workflow,
        providing agents with 2000+ chars of actual file content instead of generic prompts.

        Args:
            user_data: Node data from frontend (node_id, node_path, etc.)
            feature_request: User's text query

        Returns:
            Dict with rich context including file preview, metadata, and related files
        """
        print(f"\n[ORCHESTRATOR] Building rich context for agents...")

        # Try to get rich context functions
        build_rich_context, generate_agent_prompt, resolve_node_filepath = (
            _get_rich_context_functions()
        )

        if not build_rich_context:
            # Fallback if import failed
            print(
                f"[ORCHESTRATOR] ⚠️ Rich context functions not available, using fallback"
            )
            return {
                "preview": f"Working on: {feature_request[:200]}",
                "metadata": {"file_name": "unknown"},
                "related_files": [],
                "total_context_chars": len(feature_request),
                "is_fallback": True,
            }

        # Extract node info from user_data
        node_id = user_data.get("node_id", "unknown")
        node_path = user_data.get("node_path", user_data.get("file_path", "unknown"))

        # Try to load tree data for full node metadata
        import json
        import os

        all_nodes = []
        target_node = None
        actual_path = None

        try:
            tree_file = os.path.join(
                os.path.dirname(__file__), "..", "..", "tree_data.json"
            )
            tree_file = os.path.abspath(tree_file)

            if os.path.exists(tree_file):
                with open(tree_file, "r") as f:
                    tree_data = json.load(f)
                all_nodes = tree_data.get("tree", {}).get("nodes", []) or tree_data.get(
                    "nodes", []
                )
                print(f"[ORCHESTRATOR] Loaded {len(all_nodes)} nodes from tree")

                # Find target node by ID
                for node in all_nodes:
                    if str(node.get("id")) == str(node_id):
                        target_node = node
                        break

                # Resolve full file path
                if target_node:
                    actual_path = resolve_node_filepath(node_id, all_nodes)
        except Exception as e:
            print(f"[ORCHESTRATOR] ⚠️ Error loading tree data: {e}")

        # Build rich context
        if target_node and actual_path:
            try:
                rich_context = build_rich_context(
                    node=target_node,
                    file_path=actual_path,
                    user_question=feature_request,
                )
                print(
                    f"[ORCHESTRATOR] ✅ Rich context ready: {rich_context.get('total_context_chars', 0)} chars"
                )
                rich_context["is_fallback"] = False
                rich_context["node_path"] = node_path
                rich_context["actual_path"] = actual_path
                rich_context["model_source"] = user_data.get(
                    "model_source"
                )  # Phase 111.10
                return rich_context
            except Exception as e:
                print(f"[ORCHESTRATOR] ⚠️ Rich context build failed: {e}")

        # Fallback - try to read file directly if path is provided
        if node_path and os.path.exists(node_path):
            try:
                with open(node_path, "r", encoding="utf-8") as f:
                    content = f.read()  # Read full file for unlimited responses

                rich_context = {
                    "preview": content[:999999],
                    "metadata": {
                        "file_name": os.path.basename(node_path),
                        "file_type": os.path.splitext(node_path)[1],
                    },
                    "related_files": [],
                    "total_context_chars": len(content[:999999]),
                    "is_fallback": True,
                    "node_path": node_path,
                    "model_source": user_data.get("model_source"),  # Phase 111.10
                }
                print(
                    f"[ORCHESTRATOR] ✅ Fallback context ready: {rich_context['total_context_chars']} chars"
                )
                return rich_context
            except Exception as e:
                print(f"[ORCHESTRATOR] ⚠️ Fallback file read failed: {e}")

        # Ultimate fallback
        feature_str = str(feature_request or "")
        return {
            "preview": f"Working on: {feature_str[:500]}",
            "metadata": {"file_name": node_path or "unknown"},
            "related_files": [],
            "total_context_chars": min(len(feature_str), 500),
            "is_fallback": True,
            "node_path": node_path,
            "model_source": user_data.get("model_source"),  # Phase 111.10
        }

    def _format_history_for_prompt(self, messages: list, max_messages: int = 10) -> str:
        """
        Phase 51.1: Format chat history for agent prompts.

        Args:
            messages: List of message dicts from ChatHistoryManager
            max_messages: Maximum number of recent messages to include

        Returns:
            Formatted history string for prompt, or empty string if no history
        """
        if not messages:
            return ""

        # Take last N messages
        recent = messages[-max_messages:] if len(messages) > max_messages else messages

        formatted = "## CONVERSATION HISTORY\n"
        formatted += "(Previous messages in this conversation)\n\n"

        for msg in recent:
            role = msg.get("role", "user").upper()
            content = str(msg.get("content", "") or msg.get("text", "") or "")

            # No truncation - keep full content for unlimited responses
            # Remove character limits for better analysis

            # Include agent name if assistant
            if role == "ASSISTANT":
                agent = msg.get("agent", "Assistant")
                formatted += f"**{agent}**: {content}\n\n"
            else:
                formatted += f"**USER**: {content}\n\n"

        formatted += "---\n\n"
        return formatted

    def _generate_rich_agent_prompt(
        self,
        agent_type: str,
        rich_context: Dict[str, Any],
        user_question: str,
        node_path: str,
    ) -> str:
        """
        Generate context-aware prompts for agents using Phase 15-3 format.

        Args:
            agent_type: 'PM', 'Dev', 'QA', or 'Architect'
            rich_context: Dict from _build_rich_context_for_workflow()
            user_question: User's question
            node_path: Path to file being analyzed

        Returns:
            str: Complete prompt with rich context (2000+ chars)
        """
        # Try to use the generate_agent_prompt from app/main
        _, generate_agent_prompt, _ = _get_rich_context_functions()

        if generate_agent_prompt and not rich_context.get("is_fallback"):
            try:
                return generate_agent_prompt(
                    agent_name=agent_type,
                    rich_context=rich_context,
                    user_question=user_question,
                    node_path=node_path,
                )
            except Exception as e:
                print(f"[ORCHESTRATOR] ⚠️ generate_agent_prompt failed: {e}")

        # Build prompt ourselves
        preview = rich_context.get("preview", "")
        metadata = rich_context.get("metadata", {})
        related_files = rich_context.get("related_files", [])

        # Phase 51.1: Load chat history
        history_context = ""
        try:
            from pathlib import Path
            from src.chat.chat_history_manager import get_chat_history_manager

            # Normalize path
            if node_path and node_path not in ("unknown", "root", ""):
                try:
                    normalized_path = str(Path(node_path).resolve())
                except Exception:
                    normalized_path = node_path
            else:
                normalized_path = node_path

            chat_manager = get_chat_history_manager()
            chat_id = chat_manager.get_or_create_chat(normalized_path)
            history_messages = chat_manager.get_chat_messages(chat_id)
            history_context = self._format_history_for_prompt(
                history_messages, max_messages=10
            )

            print(
                f"[PHASE_51.1] {agent_type} agent: Loaded {len(history_messages)} history messages"
            )
        except Exception as e:
            print(f"[ORCHESTRATOR] History load failed for {agent_type}: {e}")

        # Build related files section
        related_section = ""
        if related_files:
            related_section = "\n\nRelated files in codebase:\n"
            for rf in related_files:
                related_section += f"- {rf.get('name', 'unknown')} (relevance: {rf.get('relevance', 0):.2f})\n"

        # Agent-specific prompts
        prompts = {
            "PM": f"""{history_context}You are the Project Manager analyzing {node_path}.

File Information:
- Type: {metadata.get("file_type", "unknown")}
- Lines: {metadata.get("total_lines", "unknown")}
- Size: {metadata.get("file_size", "unknown")}

File Preview ({len(preview)} chars):
```
{preview}
```
{related_section}

User Question: {user_question}

As Project Manager, provide a strategic analysis focusing on:
- Purpose and scope of this file
- How it fits into the larger project
- Potential impact of changes
- Risk assessment

Keep response under 500 words.""",
            "Dev": f"""{history_context}You are the Developer implementing solutions for {node_path}.

File Information:
- Type: {metadata.get("file_type", "unknown")}
- Lines: {metadata.get("total_lines", "unknown")}

File Content ({len(preview)} chars):
```
{preview}
```
{related_section}

User Question: {user_question}

As Developer, provide a technical analysis with:
- Code structure and patterns
- Implementation details
- Specific code examples if relevant
- Best practices and recommendations

Keep response focused and actionable, under 500 words.""",
            "QA": f"""{history_context}You are the QA Engineer ensuring quality for {node_path}.

File Information:
- Type: {metadata.get("file_type", "unknown")}
- Lines: {metadata.get("total_lines", "unknown")}

File Content ({len(preview)} chars):
```
{preview}
```
{related_section}

User Question: {user_question}

As QA Engineer, provide quality analysis covering:
- Potential issues and edge cases
- Testing requirements
- Code quality observations
- Suggestions for improvement

Keep response practical and specific, under 500 words.""",
            "Architect": f"""{history_context}You are the Software Architect designing the solution for {node_path}.

File Information:
- Type: {metadata.get("file_type", "unknown")}
- Lines: {metadata.get("total_lines", "unknown")}

File Content ({len(preview)} chars):
```
{preview}
```
{related_section}

User Question: {user_question}

As Architect, provide architectural analysis covering:
- System design implications
- Integration points and dependencies
- Scalability considerations
- Design patterns and best practices

Keep response focused and architectural, under 500 words.""",
        }

        return prompts.get(
            agent_type,
            f"""{history_context}Analyzing {node_path}.

Content preview:
{preview}

Question: {user_question}

Please provide a helpful response based on the file content shown above.""",
        )

    # ============ AGENT EXECUTION WITH MIDDLEWARE ============

    async def _call_llm_with_tools_loop(
        self,
        prompt: str,
        agent_type: str,
        model: str,
        system_prompt: str,
        max_tool_turns: int = 5,
        provider: Provider = None,  # Phase 80.10: Explicit provider
        source: str = None,  # Phase 111.9: Source for multi-provider routing
    ) -> Dict[str, Any]:
        """
        Main tool-enabled chat loop using the updated call_model.
        Phase 17-L: Uses agent-specific tool permissions.
        Phase 19: Collects tool results for response formatting.
        Phase 80.10: Uses ProviderRegistry for clean provider routing.
        Phase 111.9: Added source parameter for multi-provider routing.
        """

        # 1. Get agent-specific tool schemas with CAM integration (Phase 76.4)
        tool_schemas = self.get_tools_for_agent(agent_type, scope="default")
        print(
            f"      🔧 {agent_type} has access to {len(tool_schemas)} tools: {AGENT_TOOL_PERMISSIONS.get(agent_type, [])}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        # Phase 80.10: Detect provider if not explicitly passed
        # Phase 111.9: Use source for multi-provider routing
        if provider is None:
            provider = ProviderRegistry.detect_provider(model, source=source)

        # MARKER_173.P6.P9: Workflow-entry REFLEX preflight parity with direct call path.
        try:
            from src.mcp.tools.llm_call_reflex import maybe_apply_reflex_to_direct_tools

            role_map = {
                "PM": "pm",
                "Architect": "architect",
                "Dev": "coder",
                "QA": "qa",
                "Researcher": "researcher",
                "Hostess": "orchestrator",
            }
            phase_map = {
                "PM": "research",
                "Architect": "build",
                "Dev": "build",
                "QA": "test",
                "Researcher": "research",
                "Hostess": "research",
            }
            runtime_meta = dict(getattr(self, "_workflow_reflex_runtime_metadata", {}) or {})
            write_opt_ins = dict(runtime_meta.get("write_opt_ins") or {})
            reflex_args = {
                "model": model,
                "messages": messages,
                "_reflex_phase": phase_map.get(str(agent_type), "build"),
                "_reflex_role": role_map.get(str(agent_type), "coder"),
                "_allow_task_board_writes": bool(write_opt_ins.get("task_board", False)),
                "_allow_edit_file_writes": bool(write_opt_ins.get("edit_file", False)),
            }
            messages, tool_schemas, _reflex_recs, reflex_meta = maybe_apply_reflex_to_direct_tools(
                arguments=reflex_args,
                messages=messages,
                tools=tool_schemas,
                provider_name=provider.value,
            )
            if reflex_meta:
                print(
                    "      [REFLEX WF PRE] "
                    f"enabled={reflex_meta.get('enabled')} "
                    f"phase={reflex_meta.get('phase')} role={reflex_meta.get('role')} "
                    f"original={reflex_meta.get('tool_count_before')} "
                    f"filtered={reflex_meta.get('tool_count_after')} "
                    f"family={runtime_meta.get('workflow_family', '')}"
                )
        except Exception as e:
            print(f"      [REFLEX WF PRE] skipped: {e}")

        # Phase 19: Collect all tool execution results for formatting
        all_tool_executions = []

        print(
            f"      🌐 Using provider: {provider.value} for model: {model} (source={source})"
        )

        # MARKER_111.9_NO_FALLBACK: No automatic fallback between providers
        # Phase 111.9: If provider fails, return error - user changes provider manually
        response = await call_model_v2(
            messages=messages,
            model=model,
            provider=provider,
            source=source,  # Phase 111.9
            tools=tool_schemas,
        )
        # MARKER_111.9_END

        for turn in range(max_tool_turns):
            # Phase 22: Handle both dict and Pydantic object responses from Ollama
            # Ollama returns ChatResponse objects with message.tool_calls
            tool_calls_data = None
            if hasattr(response, "message") and hasattr(response.message, "tool_calls"):
                # Pydantic object from Ollama
                tool_calls_data = response.message.tool_calls
            elif isinstance(response, dict):
                # Dict response (OpenRouter, etc.)
                tool_calls_data = response.get("message", {}).get(
                    "tool_calls"
                ) or response.get("tool_calls")

            if tool_calls_data:
                print(
                    f"      🔧 LLM requested {len(tool_calls_data)} tool call(s) on turn {turn + 1}"
                )

                # Execute tool calls
                executor = SafeToolExecutor()
                tool_results = []

                for i, tool_call_data in enumerate(tool_calls_data):
                    # Phase 22: Handle both Pydantic ToolCall objects and dicts
                    if hasattr(tool_call_data, "function"):
                        # Pydantic ToolCall object from Ollama
                        func_name = tool_call_data.function.name
                        func_args = tool_call_data.function.arguments
                        call_id = getattr(tool_call_data, "id", f"call_{i}")
                    else:
                        # Dict format (OpenRouter, etc.)
                        function = tool_call_data.get("function", tool_call_data)
                        func_name = function.get("name")
                        func_args = function.get("arguments", {})
                        call_id = tool_call_data.get("id", f"call_{i}")

                    print(f"      🔧 Executing tool: {func_name}({func_args})")

                    call = ToolCall(
                        tool_name=func_name,
                        arguments=func_args,
                        agent_type=agent_type,
                        call_id=call_id,
                    )

                    result = await executor.execute(call)

                    # Phase 35: CAM Engine - process new artifact on file writes
                    if (
                        func_name in ("write_file", "create_file", "edit_file")
                        and result.success
                    ):
                        if hasattr(self, "_cam_engine") and self._cam_engine:
                            try:
                                file_path = func_args.get(
                                    "path", func_args.get("file_path", "")
                                )
                                content_preview = str(func_args.get("content", ""))[
                                    :500
                                ]

                                cam_result = await self._cam_engine.handle_new_artifact(
                                    artifact_path=file_path,
                                    metadata={
                                        "type": "code",
                                        "agent": agent_type,
                                        "workflow_id": kwargs.get(
                                            "workflow_id", "unknown"
                                        ),
                                        "content_preview": content_preview,
                                    },
                                )
                                if cam_result:
                                    print(
                                        f"      🌱 CAM: {cam_result.operation_type} for {file_path}"
                                    )
                            except Exception as cam_err:
                                print(f"      ⚠️ CAM processing failed: {cam_err}")

                    # Phase 19: Store tool execution for response formatting
                    all_tool_executions.append(
                        {
                            "name": func_name,
                            "args": func_args,
                            "result": {
                                "success": result.success,
                                "result": result.result,
                                "error": result.error,
                            },
                        }
                    )

                    # Prepare message for LLM
                    tool_results.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": json.dumps(
                                {
                                    "success": result.success,
                                    "result": result.result,
                                    "error": result.error,
                                }
                            ),
                        }
                    )

                # Append tool messages to history (for next LLM turn)
                # Phase 22: Convert Pydantic message to dict if needed
                if hasattr(response, "message") and hasattr(
                    response.message, "model_dump"
                ):
                    msg_dict = response.message.model_dump()
                elif hasattr(response, "message"):
                    msg_dict = {
                        "role": "assistant",
                        "content": response.message.content or "",
                        "tool_calls": tool_calls_data,
                    }
                else:
                    msg_dict = response.get("message", {})
                messages.append(msg_dict)
                messages.extend(tool_results)

                # Call LLM again with tool results
                # Phase 80.10: Use call_model_v2 with explicit provider
                # Phase 111.10: NO FALLBACK between providers - let error propagate
                response = await call_model_v2(
                    messages=messages,  # Full history with tool results
                    model=model,
                    provider=provider,
                    source=source,  # Phase 111.11.2 - preserve source after tool call
                    tools=tool_schemas,
                )
            else:
                # LLM responded with a final message
                break

        # Phase 19: Attach tool executions to response for formatting
        response["_tool_executions"] = all_tool_executions

        return response

    async def _run_agent_with_elisya_async(
        self,
        agent_type: str,
        state: ElisyaState,
        prompt: str,
        **kwargs,  # Agent method arguments, though we are bypassing agent func
    ) -> tuple:
        """
        ASYNC Run LLM call with Elisya middleware and Tool support.
        This function replaces the need for the synchronous agent_func call entirely.
        Phase 19: Now includes response formatting with source citations.
        """
        print(f"\n   → {agent_type} (Async LLM) with Elisya...")

        # Phase 111.10: Extract rich_context from kwargs for model_source
        rich_context = kwargs.get("rich_context")

        # 1. Reframe context (Phase 54.1: Using ElisyaStateService)
        state = self.elisya_service.reframe_context(state, agent_type)

        # 2. Get routing
        # Phase 80.8: Check for manual model override first (from call_agent())
        # MARKER_90.1.4.1_START: Use canonical detect_provider
        if (
            agent_type in self.model_routing
            and self.model_routing[agent_type].get("provider") == "manual"
        ):
            manual_model = self.model_routing[agent_type]["model"]
            # Phase 90.1.4.1: Use canonical detect_provider instead of inline detection
            from src.elisya.provider_registry import ProviderRegistry
            from src.orchestration.services.api_key_service import APIKeyService

            detected_provider = ProviderRegistry.detect_provider(manual_model)
            real_provider = detected_provider.value

            # Phase 111.10.1: NO FALLBACK - error if no XAI key
            if real_provider == "xai":
                if not APIKeyService().get_key("xai"):
                    print(f"      ❌ xai key not found - NO FALLBACK")
                    raise ValueError("XAI API key not configured. Please add XAI key or select a different provider.")

            routing = {"provider": real_provider, "model": manual_model}
            print(
                f"   → Using manual model override: {manual_model} (provider: {real_provider})"
            )
        # MARKER_90.1.4.1_END
        else:
            routing = self._get_routing_for_task(
                str(state.context or "")[:100], agent_type
            )
        model_name = routing["model"]

        # 3. Get API key
        api_key = self._inject_api_key(routing)

        # 4. SET KEY IN ENVIRONMENT FOR LLM CALL (Phase 54.1: Using APIKeyService)
        saved_env = {}
        if api_key:
            saved_env = self.key_service.inject_key_to_env(routing["provider"], api_key)

        # Build agent system prompt with tool guidance
        # Phase 22: Include camera_focus guidance for visual navigation
        # Phase 57.8: Use role-specific prompts from role_prompts.py
        # MARKER_114.5_AUTO_TOOL_GUIDANCE: Enhanced tool guidance with workflow recommendations
        # Grok improvement 1: "В system prompt добавь workflow recommendations"
        tool_guidance = """
## Available Tools (use them proactively!)

### Search & Navigate
- **vetka_search_semantic**: Search codebase by meaning (Qdrant vectors). USE FIRST for any question about code.
- **search_codebase**: Search code by pattern (grep-based). Use for exact matches.
- **get_tree_context**: Get file/folder hierarchy. Use to understand project structure.
- **vetka_camera_focus**: Move 3D camera to show files. USE when discussing code locations.

### Create & Edit
- **vetka_edit_artifact**: Create/edit code artifacts for review (PM/Dev/Architect).

### Recommended Workflow
1. Start with vetka_search_semantic to find relevant context
2. Use get_tree_context to understand file relationships
3. Use vetka_camera_focus to show the user what you found
4. For code changes: use vetka_edit_artifact (creates reviewable artifact)

### Triggers
- "show", "focus on", "navigate to" → vetka_camera_focus
- "find", "search", "where is" → vetka_search_semantic
- "create", "write", "implement" → vetka_edit_artifact
"""
        # Try to get role-specific prompt, fallback to generic
        try:
            from src.agents.role_prompts import get_agent_prompt

            base_prompt = get_agent_prompt(agent_type)
        except ImportError:
            base_prompt = f"You are the {agent_type} agent."

        system_prompt = f"{base_prompt}\n\n{tool_guidance}"

        # Phase 19: Track tool executions for response formatting
        tool_executions = []

        # MARKER_114.4_ELISION_WITH_EXPAND: Compress context with expand support
        # Phase 104 base + Phase 114.4: Save legend for expand, use medium compression
        # Grok feedback: "compression too aggressive, no expand" — fixed here
        compressed_prompt = prompt
        compression_info = None
        _elision_legend = None  # MARKER_114.4: Save legend for potential expand

        if len(str(prompt)) > 5000:  # Only compress large contexts
            try:
                from src.memory.elision import get_elision_compressor

                compressor = get_elision_compressor()
                result = compressor.compress(prompt, level=2)  # Level 2 = safe medium

                # Use compressed version for LLM
                compressed_prompt = result.compressed
                _elision_legend = result.legend  # MARKER_114.4: Save for expand
                compression_info = {
                    "original_size": result.original_length,
                    "compressed_size": result.compressed_length,
                    "ratio": f"{result.compression_ratio:.2f}x",
                    "tokens_saved": result.tokens_saved_estimate,
                    "level": result.level,
                    "legend_keys": len(result.legend) if result.legend else 0,  # MARKER_114.4
                }
                logger.debug(
                    f"[ELISION] Compressed context: {result.original_length} → {result.compressed_length} bytes ({result.compression_ratio:.2f}x, ~{result.tokens_saved_estimate} tokens saved, legend: {len(result.legend) if result.legend else 0} keys)"
                )

                # MARKER_114.4_EXPAND_HINT: Add expand hint to system prompt so agent knows
                # expand is available (Grok requested this feature)
                if result.legend and len(result.legend) > 0:
                    system_prompt += f"\n\nNote: Context was compressed with ELISION level 2 ({len(result.legend)} abbreviations). If you need full detail on any section, mention it and the system will expand."

            except ImportError:
                logger.debug("[ELISION] Compressor not available, using raw context")
                compressed_prompt = prompt
        # MARKER_104_ELISION_INTEGRATION_END

        # 5. Execute LLM call with tool loop
        # Phase 80.10: Convert provider string to Provider enum
        provider_str = routing.get("provider", "ollama")
        try:
            provider_enum = Provider(provider_str.lower())
        except ValueError:
            provider_enum = Provider.OLLAMA  # Fallback

        try:
            # The prompt passed in kwargs is the *rich* prompt
            # MARKER_104_ELISION_INTEGRATION: Use compressed context for LLM
            llm_response = await self._call_llm_with_tools_loop(
                prompt=compressed_prompt,
                agent_type=agent_type,
                model=model_name,
                system_prompt=system_prompt,
                provider=provider_enum,  # Phase 80.10: Pass explicit provider
                source=rich_context.get("model_source")
                if rich_context
                else None,  # Phase 111.10
            )

            # Extract final content from the full response structure
            output = llm_response.get("message", {}).get(
                "content", "No response content."
            )

            # Phase 19: Get tool executions for formatting
            tool_executions = llm_response.get("_tool_executions", [])

            # Phase 19: Format response with source citations
            if tool_executions:
                # Extract sources from semantic search results
                sources = []
                for te in tool_executions:
                    if te.get("name") == "search_semantic":
                        result = te.get("result", {})
                        if result.get("success") and result.get("result"):
                            data = result["result"]
                            if isinstance(data, dict):
                                sources.extend(data.get("results", []))

                # Format the output with sources
                if sources:
                    output = ResponseFormatter.add_source_citations(output, sources)
                    print(f"      📚 Added {len(sources)} source citations")

        except Exception as e:
            print(f"      ❌ {agent_type} LLM/Tool error: {str(e)}")

            # Phase 100.1: Auto-rotate key on auth/rate-limit errors
            # MARKER_102.33_FIX: Extended error detection + fixed ProviderKey -> ProviderType
            error_str = str(e).upper()
            if any(
                code in error_str
                for code in ("401", "402", "403", "429", "OPENROUTER", "EXHAUSTED")
            ):
                from src.utils.unified_key_manager import get_key_manager, ProviderType

                km = get_key_manager()
                km.rotate_to_next()  # No argument needed - rotates OpenRouter by default
                print(f"      🔄 Key rotated due to error, retrying...")
                try:
                    llm_response = await self._call_llm_with_tools_loop(
                        prompt=prompt,
                        agent_type=agent_type,
                        model=model_name,
                        system_prompt=system_prompt,
                        provider=provider_enum,
                        source=rich_context.get("model_source")
                        if rich_context
                        else None,  # Phase 111.10
                    )
                    output = llm_response.get("message", {}).get(
                        "content", "No response content."
                    )
                except Exception as retry_e:
                    print(f"      ❌ Retry also failed: {str(retry_e)}")
                    output = f"Error in {agent_type} LLM/Tool execution: {str(e)}"
            else:
                output = f"Error in {agent_type} LLM/Tool execution: {str(e)}"
        finally:
            # Restore environment (Phase 54.1: Using APIKeyService)
            self.key_service.restore_env(saved_env)

        # 6. Update state
        state = self._update_state(state, agent_type, output)

        print(f"      ✅ {agent_type} completed (Async Tool Flow)")

        return output, state

    # ============ WORKFLOW EXECUTION ============

    async def execute_full_workflow_streaming(
        self,
        feature_request: str,
        workflow_id: str = None,
        use_parallel: bool = None,
        user_data: Dict[str, Any] = None,
    ) -> dict:
        """
        Main entry point for workflow execution.

        Args:
            feature_request: User's text query
            workflow_id: Optional workflow ID (auto-generated if None)
            use_parallel: Whether to use parallel execution
            user_data: Optional node data from frontend for Phase 15-3 rich context
                       Expected keys: node_id, node_path, file_path
        """
        workflow_id = workflow_id or str(uuid.uuid4())[:8]

        # === MARKER-77-01: Phase 77 Memory Sync Check ===
        # Check if filesystem has changed since last sync
        # If significant changes detected, Hostess will ask user for decisions
        if hasattr(self, "memory_sync_engine") and self.memory_sync_engine:
            try:
                await self.memory_sync_engine.check_and_sync()
            except Exception as e:
                logger.warning(f"[Phase 77] Memory sync check failed: {e}")
        # === END MARKER-77-01 ===

        should_use_parallel = (
            use_parallel if use_parallel is not None else self.use_parallel
        )

        # Phase 15-3: Build rich context if user_data provided
        rich_context = None
        if user_data:
            rich_context = self._build_rich_context_for_workflow(
                user_data, feature_request
            )

        if should_use_parallel:
            return await self._execute_parallel(
                feature_request, workflow_id, rich_context=rich_context
            )
        else:
            return await self._execute_sequential(
                feature_request, workflow_id, rich_context=rich_context
            )

    async def _execute_parallel(
        self,
        feature_request: str,
        workflow_id: str,
        rich_context: Dict[str, Any] = None,
        workflow_family: str = "",
        workflow_runtime_metadata: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """
        Parallel execution with Elisya integration and Chain Context Passing.

        Args:
            feature_request: User's text query
            workflow_id: Workflow identifier
            rich_context: Optional Phase 15-3 rich context with file preview and metadata
        """

        self._check_semaphore(workflow_id)
        previous_runtime_metadata = dict(self._workflow_reflex_runtime_metadata or {})
        self._workflow_reflex_runtime_metadata = dict(workflow_runtime_metadata or {})
        if workflow_family:
            self._workflow_reflex_runtime_metadata.setdefault("workflow_family", str(workflow_family))

        # Phase 15-3: Log rich context status
        if rich_context:
            print(
                f"\n[ORCHESTRATOR] ✅ Rich context available: {rich_context.get('total_context_chars', 0)} chars"
            )
            print(
                f"[ORCHESTRATOR]    File: {rich_context.get('metadata', {}).get('file_name', 'unknown')}"
            )
        else:
            print(f"\n[ORCHESTRATOR] ⚠️ No rich context, using feature request only")

        # Initialize ElisyaState
        elisya_state = self._get_or_create_state(workflow_id, feature_request)

        # ✅ Phase 17-K: Initialize Chain Context for PM → Architect → Dev → QA
        chain = create_chain_context(feature_request, workflow_id)
        print(f"\n[CHAIN] 🔗 Chain context created for workflow")

        print("\n" + "=" * 70)
        print(f"🌳 VETKA PARALLEL WORKFLOW WITH ELISYA [{workflow_id}]")
        print(f"🔗 CHAIN CONTEXT: PM → Architect → Dev → QA")
        print("=" * 70)

        result = {
            "workflow_id": workflow_id,
            "feature": feature_request,
            "pm_plan": "",
            "architecture": "",
            "implementation": "",
            "tests": "",
            "status": "complete",
            "error": None,
            "duration": 0,
            "execution_mode": "parallel",
            "elisya_path": elisya_state.semantic_path,
            "metrics": {
                "phases": {},
                "elisya_operations": self.elisya_service.get_operation_stats(),
            },
        }

        start_time = time.time()

        try:
            # ===== PHASE 1: PM =====
            print("\n1️⃣  PM AGENT with Elisya...")
            self._emit_status(workflow_id, "pm", "running")
            phase_start = time.time()

            # Phase 15-3: Generate rich prompt for PM if context available
            pm_prompt = feature_request
            if rich_context and rich_context.get("total_context_chars", 0) > 100:
                pm_prompt = self._generate_rich_agent_prompt(
                    agent_type="PM",
                    rich_context=rich_context,
                    user_question=feature_request,
                    node_path=rich_context.get("node_path", "unknown"),
                )
                print(f"   [PM] Using rich prompt: {len(pm_prompt)} chars")

            elisya_state.speaker = "PM"
            # ✅ PHASE 3: Use the new ASYNC method for tool support
            # Phase 111.10: Pass rich_context for model_source
            pm_result, elisya_state = await self._run_agent_with_elisya_async(
                "PM", elisya_state, pm_prompt, rich_context=rich_context
            )

            # ✅ Phase 17-K: Add PM step to chain context
            chain.add_step(
                agent="PM",
                input_msg=pm_prompt,
                output=pm_result,
                artifacts=[],
                score=None,
            )
            print(f"[CHAIN] ✅ PM step added to chain")

            result["pm_plan"] = pm_result
            result["metrics"]["phases"]["pm"] = time.time() - phase_start
            self._emit_status(workflow_id, "pm", "done")
            self.memory.save_agent_output("PM", pm_result, workflow_id, "planning")
            print(f"   ✅ PM completed in {result['metrics']['phases']['pm']:.1f}s")

            # Phase 55.1: MCP state hook
            try:
                mcp_bridge = get_mcp_state_bridge()
                await mcp_bridge.save_agent_state(
                    workflow_id, "PM", pm_result, elisya_state
                )
            except Exception as e:
                print(f"   ⚠️ MCP PM state save failed: {e}")

            # ===== PHASE 2: ARCHITECT =====
            print("\n2️⃣  ARCHITECT with Elisya...")
            self._emit_status(workflow_id, "architect", "running")
            phase_start = time.time()

            # Phase 15-3: Generate rich prompt for Architect if context available
            architect_prompt = pm_result
            if rich_context and rich_context.get("total_context_chars", 0) > 100:
                architect_prompt = self._generate_rich_agent_prompt(
                    agent_type="Architect",
                    rich_context=rich_context,
                    user_question=feature_request,
                    node_path=rich_context.get("node_path", "unknown"),
                )
                # Include PM's plan in Architect's prompt
                architect_prompt += f"\n\n## PM's Plan:\n{pm_result}"
                print(
                    f"   [Architect] Using rich prompt: {len(architect_prompt)} chars"
                )

            elisya_state.speaker = "Architect"
            # ✅ PHASE 3: Use the new ASYNC method for tool support
            # MARKER_103_CHAIN1: Architect missing from parallel chain with Dev/QA
            architect_result, elisya_state = await self._run_agent_with_elisya_async(
                "Architect", elisya_state, architect_prompt
            )

            result["architecture"] = architect_result
            result["metrics"]["phases"]["architect"] = time.time() - phase_start
            self._emit_status(workflow_id, "architect", "done")
            self.memory.save_agent_output(
                "Architect", architect_result, workflow_id, "design"
            )
            print(
                f"   ✅ Architect completed in {result['metrics']['phases']['architect']:.1f}s"
            )

            # Phase 55.1: MCP state hook
            try:
                mcp_bridge = get_mcp_state_bridge()
                await mcp_bridge.save_agent_state(
                    workflow_id, "Architect", architect_result, elisya_state
                )
            except Exception as e:
                print(f"   ⚠️ MCP Architect state save failed: {e}")

            # ===== PHASE 3: PARALLEL DEV & QA =====
            print("\n3️⃣  DEV & QA with Elisya - PARALLEL EXECUTION...")
            print("   🔄 Starting Dev and QA in parallel...")
            self._emit_status(workflow_id, "dev", "running")
            self._emit_status(workflow_id, "qa", "running")

            phase_start = time.time()

            dev_result = [None]
            qa_result = [None]
            dev_state = [None]
            qa_state = [None]
            dev_error = [None]
            qa_error = [None]

            # Phase 15-3: Pre-generate rich prompts for Dev and QA
            dev_prompt = pm_result
            qa_prompt = feature_request

            if rich_context and rich_context.get("total_context_chars", 0) > 100:
                dev_prompt = self._generate_rich_agent_prompt(
                    agent_type="Dev",
                    rich_context=rich_context,
                    user_question=feature_request,
                    node_path=rich_context.get("node_path", "unknown"),
                )
                dev_prompt += f"\n\n## PM's Plan:\n{pm_result}"
                print(f"   [Dev] Using rich prompt: {len(dev_prompt)} chars")

                qa_prompt = self._generate_rich_agent_prompt(
                    agent_type="QA",
                    rich_context=rich_context,
                    user_question=feature_request,
                    node_path=rich_context.get("node_path", "unknown"),
                )
                print(f"   [QA] Using rich prompt: {len(qa_prompt)} chars")

            # MARKER_103_CHAIN2: FIXED - replaced threading with asyncio.gather()
            # Phase 103: True async parallel execution without event loop conflicts

            async def run_dev_async():
                """Async Dev agent execution."""
                try:
                    print("      → Dev async started")
                    output, state = await self._run_agent_with_elisya_async(
                        "Dev", elisya_state, dev_prompt
                    )
                    print("      ✅ Dev async completed")
                    return ("dev", output, state, None)
                except Exception as e:
                    print(f"      ❌ Dev async error: {e}")
                    return ("dev", None, None, str(e))

            async def run_qa_async():
                """Async QA agent execution."""
                try:
                    print("      → QA async started")
                    output, state = await self._run_agent_with_elisya_async(
                        "QA", elisya_state, qa_prompt
                    )
                    print("      ✅ QA async completed")
                    return ("qa", output, state, None)
                except Exception as e:
                    print(f"      ❌ QA async error: {e}")
                    return ("qa", None, None, str(e))

            # Run both in parallel with asyncio.gather (no threading!)
            dev_qa_results = await asyncio.gather(
                run_dev_async(), run_qa_async(), return_exceptions=True
            )

            # Process results
            for res in dev_qa_results:
                if isinstance(res, Exception):
                    print(f"      ⚠️ Parallel task exception: {res}")
                    continue
                agent_type, output, state, error = res
                if agent_type == "dev":
                    dev_result[0] = output
                    dev_state[0] = state
                    dev_error[0] = error
                elif agent_type == "qa":
                    qa_result[0] = output
                    qa_state[0] = state
                    qa_error[0] = error

            result["implementation"] = dev_result[0] or ""
            result["tests"] = qa_result[0] or ""
            result["metrics"]["phases"]["dev_qa_parallel"] = time.time() - phase_start

            # MARKER_103_CHAIN3: FIXED - merge states instead of overwrite
            # Combine both states: Dev artifacts + QA feedback
            if dev_state[0] and qa_state[0]:
                # Merge: use Dev as base, add QA feedback
                elisya_state = dev_state[0]
                elisya_state.qa_feedback = getattr(qa_state[0], "qa_feedback", None)
                elisya_state.test_results = getattr(qa_state[0], "test_results", None)
            elif dev_state[0]:
                elisya_state = dev_state[0]
            elif qa_state[0]:
                elisya_state = qa_state[0]

            # Phase 55.1: MCP parallel merge hook
            try:
                mcp_bridge = get_mcp_state_bridge()
                await mcp_bridge.merge_parallel_states(
                    workflow_id, dev_state[0], qa_state[0]
                )
            except Exception as e:
                print(f"   ⚠️ MCP parallel merge failed: {e}")

            if dev_error[0]:
                print(f"   ⚠️  Dev error: {dev_error[0]}")
                self._emit_status(workflow_id, "dev", "error", error=dev_error[0])
            else:
                self._emit_status(workflow_id, "dev", "done")
                self.memory.save_agent_output(
                    "Dev", dev_result[0], workflow_id, "implementation"
                )

            if qa_error[0]:
                print(f"   ⚠️  QA error: {qa_error[0]}")
                self._emit_status(workflow_id, "qa", "error", error=qa_error[0])
            else:
                self._emit_status(workflow_id, "qa", "done")
                self.memory.save_agent_output(
                    "QA", qa_result[0], workflow_id, "testing"
                )

            print(
                f"   ✅ Dev & QA completed in {result['metrics']['phases']['dev_qa_parallel']:.1f}s (parallel!)"
            )

            # ===== PHASE 4: MERGE =====
            print("\n4️⃣  MERGE...")
            self._emit_status(workflow_id, "merge", "running")
            phase_start = time.time()

            merged_result = {
                "dev_implementation": dev_result[0] or "",
                "qa_tests": qa_result[0] or "",
            }
            result["metrics"]["phases"]["merge"] = time.time() - phase_start
            self._emit_status(workflow_id, "merge", "done")
            print(
                f"   ✅ Merge completed in {result['metrics']['phases']['merge']:.1f}s"
            )

            # ═══════════════════════════════════════════════════════════════
            # Phase 34: EvalAgent Integration (after QA, before OPS)
            # ═══════════════════════════════════════════════════════════════
            print("\n🎯 EvalAgent: Evaluating workflow output...")
            self._emit_status(workflow_id, "eval", "running")
            phase_start = time.time()

            eval_result = await self._evaluate_with_eval_agent(
                task=feature_request,
                output=f"Implementation:\n{dev_result[0] or ''}\n\nTests:\n{qa_result[0] or ''}",
                context=f"PM Plan: {str(pm_result)[:500] if pm_result else ''}...",
                complexity="MEDIUM",
            )

            result["metrics"]["phases"]["eval"] = time.time() - phase_start

            # Quality gate: log if score < 0.7
            eval_score = eval_result.get("score", 1.0)
            if eval_score < 0.7:
                print(f"   ⚠️ Quality score {eval_score:.2f} < 0.7")
                if eval_result.get("feedback"):
                    print(f"   📝 Feedback: {str(eval_result['feedback'])[:200]}...")
            else:
                print(f"   ✅ Quality gate passed (score: {eval_score:.2f})")

            # Store evaluation in result
            result["evaluation"] = {
                "score": eval_score,
                "feedback": eval_result.get("feedback", ""),
                "passed": eval_score >= 0.7,
            }

            self._emit_status(workflow_id, "eval", "done")
            print(
                f"   ✅ EvalAgent completed in {result['metrics']['phases']['eval']:.1f}s"
            )
            # ═══════════════════════════════════════════════════════════════

            # === PHASE 55: APPROVAL GATE ===
            print("\n🔒 APPROVAL GATE: Requesting user approval...")
            self._emit_status(workflow_id, "approval", "running")
            phase_start = time.time()

            # Collect artifacts from Dev
            artifacts = []
            if dev_result and dev_result[0]:
                artifacts.append(
                    {
                        "type": "implementation",
                        "preview": dev_result[0][:500],
                        "size": len(dev_result[0]),
                    }
                )
            if qa_result and qa_result[0]:
                artifacts.append(
                    {
                        "type": "tests",
                        "preview": qa_result[0][:500],
                        "size": len(qa_result[0]),
                    }
                )

            # Initialize approval variables
            approval_request = None
            approval_decision = None
            approval_status = "not_required"
            approval_reason = ""
            approval_passed = False

            # Request approval if score high enough
            if eval_score >= 0.7:
                approval_request = await self.approval_service.request_approval(
                    workflow_id=workflow_id,
                    artifacts=artifacts,
                    eval_score=eval_score,
                    eval_feedback=eval_result.get("feedback", ""),
                    socketio=self.socketio,
                )

                # Wait for user decision (5 min timeout)
                approval_decision = await self.approval_service.wait_for_decision(
                    approval_request.id, timeout=300
                )

                # MEDIUM BUG #6 FIX: Check for None
                if approval_decision is None:
                    approval_status = "error"
                    approval_reason = "Approval request failed"
                    approval_passed = False
                    print(f"   ❌ Approval request failed")
                elif approval_decision.status == ApprovalStatus.APPROVED:
                    approval_status = "approved"
                    approval_passed = True
                    approval_reason = (
                        approval_decision.decision_reason or "User approved"
                    )
                    print(f"   ✅ Approved by user: {approval_reason}")
                elif approval_decision.status == ApprovalStatus.TIMEOUT:
                    approval_status = "timeout"
                    approval_reason = "User did not respond within 5 minutes"
                    approval_passed = False
                    print(f"   ⏱️  Approval timeout (5 min) - auto-rejected")
                else:  # REJECTED
                    approval_status = "rejected"
                    approval_reason = (
                        approval_decision.decision_reason or "User rejected"
                    )
                    approval_passed = False
                    print(f"   ❌ Rejected by user: {approval_reason}")
            else:
                # Score too low - auto-reject without user approval
                approval_status = "quality_gate_failed"
                approval_reason = f"Score {eval_score:.2f} < 0.7"
                approval_passed = False
                print(f"   ⚠️ Score {eval_score:.2f} < 0.7 - skipping approval")

            result["approval"] = {
                "status": approval_status,
                "passed": approval_passed,
                "reason": approval_reason,
            }
            result["metrics"]["phases"]["approval"] = time.time() - phase_start
            self._emit_status(workflow_id, "approval", "done")

            # If not approved, stop workflow
            if not approval_passed:
                print(f"\n❌ Workflow rejected - stopping execution")
                result["status"] = "rejected"
                self._emit_status(workflow_id, "workflow", "rejected")
                return result

            # ===== PHASE 5: OPS =====
            print("\n5️⃣  OPS - Deployment...")
            self._emit_status(workflow_id, "ops", "running")
            phase_start = time.time()

            ops_result = "Deployment ready"
            result["metrics"]["phases"]["ops"] = time.time() - phase_start
            self._emit_status(workflow_id, "ops", "done")
            print(f"   ✅ Ops completed in {result['metrics']['phases']['ops']:.1f}s")

            result["status"] = "complete"
            result["duration"] = time.time() - start_time

            # ===== AGENT PERFORMANCE METRICS =====
            print("\n📊 AGENT PERFORMANCE METRICS:")
            phases = result["metrics"]["phases"]
            print(f"   PM:        {phases.get('pm', 0):.2f}s")
            print(f"   Architect: {phases.get('architect', 0):.2f}s")
            print(f"   Dev+QA:    {phases.get('dev_qa_parallel', 0):.2f}s (parallel)")
            print(f"   Merge:     {phases.get('merge', 0):.2f}s")
            print(f"   Ops:       {phases.get('ops', 0):.2f}s")
            print(f"   TOTAL:     {result['duration']:.2f}s")

            # Save performance metrics to memory
            try:
                self.memory.triple_write(
                    {
                        "type": "performance_metrics",
                        "workflow_id": workflow_id,
                        "timings": phases,
                        "total_time": result["duration"],
                        "execution_mode": "parallel",
                        "speaker": "orchestrator",
                    }
                )
            except Exception as pm_error:
                print(f"   ⚠️  Could not save performance metrics: {pm_error}")

            # Save workflow result + Elisya state
            self.memory.save_workflow_result(workflow_id, result)
            self.elisya_states[workflow_id] = elisya_state
            print(
                f"[DEBUG-HISTORY] Adding workflow {result.get('workflow_id')} to history"
            )
            self.history.append(result)
            print(f"[DEBUG-HISTORY] History size: {len(self.history)}")

            print("\n" + "=" * 70)
            print(f"✅ WORKFLOW COMPLETE WITH ELISYA [{workflow_id}]")
            print(f"   Total time: {result['duration']:.2f}s")
            print(f"   Semantic path: {elisya_state.semantic_path}")
            print(f"   Messages in history: {len(elisya_state.conversation_history)}")
            print("=" * 70 + "\n")

            # 🎯 EMIT FULL RESULT TO UI VIA SOCKET.IO
            try:
                self.socketio.emit(
                    "workflow_result",
                    {
                        "workflow_id": workflow_id,
                        "feature": result["feature"],
                        "pm_plan": result["pm_plan"],
                        "architecture": result["architecture"],
                        "implementation": result["implementation"],
                        "tests": result["tests"],
                        "status": "complete",
                        "duration": result["duration"],
                        "execution_mode": result["execution_mode"],
                        "elisya_path": result["elisya_path"],
                    },
                )
                print(f"[EMIT] ✅ workflow_result sent to UI for {workflow_id}")
            except Exception as e:
                print(f"[ERROR] Failed to emit result to UI: {e}")

            # 🧠 ARC SOLVER: Generate creative graph transformations
            if self.arc_solver:
                try:
                    print("\n🧠 Generating ARC suggestions...")

                    # Build simple graph from workflow result
                    graph_data = self._build_graph_from_workflow(result)

                    # Generate suggestions
                    arc_result = self.arc_solver.suggest_connections(
                        workflow_id=workflow_id,
                        graph_data=graph_data,
                        task_context=feature_request,
                        num_candidates=5,  # Quick suggestions
                        min_score=0.6,
                    )

                    # Emit to UI
                    if arc_result.get("top_suggestions"):
                        self.socketio.emit(
                            "arc_suggestions",
                            {
                                "workflow_id": workflow_id,
                                "suggestions": arc_result["top_suggestions"][
                                    :3
                                ],  # Top-3
                                "stats": arc_result.get("stats", {}),
                            },
                        )
                        print(
                            f"[EMIT] ✅ arc_suggestions sent ({len(arc_result['top_suggestions'])} suggestions)"
                        )

                except Exception as arc_error:
                    print(f"[WARNING] ARC Solver failed: {arc_error}")

            # 🌳 PHASE 10: Transform to VETKA-JSON and emit to UI
            arc_suggestions_list = []
            if self.arc_solver and "arc_result" in dir() and arc_result:
                arc_suggestions_list = [
                    {
                        "transformation": s.get("connection", ""),
                        "success": s.get("score", 0.5),
                    }
                    for s in arc_result.get("top_suggestions", [])
                ]

            self._transform_and_emit_vetka(result, arc_suggestions_list, elisya_state)

            self._emit_status(
                workflow_id, "workflow", "complete", duration=result["duration"]
            )

            # Phase 51.3: Event-Driven CAM Maintenance
            try:
                from src.orchestration.cam_event_handler import (
                    emit_workflow_complete_event,
                )

                print(f"[CAM] Emitting workflow_completed event for {workflow_id}")
                cam_result = await emit_workflow_complete_event(
                    workflow_id=workflow_id, artifacts=result.get("artifacts", [])
                )

                if cam_result.get("status") == "error":
                    print(
                        f"[CAM] Event error (non-critical): {cam_result.get('error')}"
                    )
                elif cam_result.get("status") == "completed":
                    print(
                        f"[CAM] Maintenance completed: {cam_result.get('pruned', 0)} pruned, {cam_result.get('merged', 0)} merged"
                    )

            except Exception as cam_error:
                print(f"[CAM] Event error (non-critical): {cam_error}")

            # Phase 55.1: MCP workflow complete hook
            try:
                mcp_bridge = get_mcp_state_bridge()
                await mcp_bridge.publish_workflow_complete(
                    workflow_id, result, elisya_state
                )
            except Exception as e:
                print(f"   ⚠️ MCP workflow complete failed: {e}")

        except Exception as e:
            print(f"\n❌ Workflow error: {e}")
            result["status"] = "error"
            result["error"] = str(e)
            result["duration"] = time.time() - start_time
            self.memory.log_error(workflow_id, "Orchestrator", str(e))
            self._emit_status(workflow_id, "workflow", "error", error=str(e))

        finally:
            self._workflow_reflex_runtime_metadata = previous_runtime_metadata
            self._release_semaphore(workflow_id)

        return result

    async def _execute_sequential(
        self,
        feature_request: str,
        workflow_id: str,
        rich_context: Dict[str, Any] = None,
    ) -> dict:
        """
        Sequential execution with Elisya integration.

        Args:
            feature_request: User's text query
            workflow_id: Workflow identifier
            rich_context: Optional Phase 15-3 rich context with file preview and metadata
        """

        # Initialize ElisyaState
        elisya_state = self._get_or_create_state(workflow_id, feature_request)

        # Phase 15-3: Log rich context status
        if rich_context:
            print(
                f"\n[ORCHESTRATOR] ✅ Rich context available: {rich_context.get('total_context_chars', 0)} chars"
            )
            print(
                f"[ORCHESTRATOR]    File: {rich_context.get('metadata', {}).get('file_name', 'unknown')}"
            )
        else:
            print(f"\n[ORCHESTRATOR] ⚠️ No rich context, using feature request only")

        print("\n" + "=" * 70)
        print(f"🌳 VETKA SEQUENTIAL WORKFLOW WITH ELISYA [{workflow_id}]")
        print("=" * 70)

        result = {
            "workflow_id": workflow_id,
            "feature": feature_request,
            "pm_plan": "",
            "architecture": "",
            "implementation": "",
            "tests": "",
            "status": "complete",
            "error": None,
            "duration": 0,
            "execution_mode": "sequential",
            "elisya_path": elisya_state.semantic_path,
            "metrics": {"phases": {}},
        }

        start_time = time.time()

        try:
            # Phase 15-3: Generate rich prompt for PM if context available
            pm_prompt = feature_request
            if rich_context and rich_context.get("total_context_chars", 0) > 100:
                pm_prompt = self._generate_rich_agent_prompt(
                    agent_type="PM",
                    rich_context=rich_context,
                    user_question=feature_request,
                    node_path=rich_context.get("node_path", "unknown"),
                )
                print(f"   [PM] Using rich prompt: {len(pm_prompt)} chars")

            print("\n1️⃣  PM Agent with Elisya...")
            elisya_state.speaker = "PM"
            # ✅ PHASE 3: Use the new ASYNC method for tool support
            pm_plan, elisya_state = await self._run_agent_with_elisya_async(
                "PM", elisya_state, pm_prompt
            )
            result["pm_plan"] = pm_plan

            # Phase 15-3: Generate rich prompt for Architect
            architect_prompt = pm_plan
            if rich_context and rich_context.get("total_context_chars", 0) > 100:
                architect_prompt = self._generate_rich_agent_prompt(
                    agent_type="Architect",
                    rich_context=rich_context,
                    user_question=feature_request,
                    node_path=rich_context.get("node_path", "unknown"),
                )
                architect_prompt += f"\n\n## PM's Plan:\n{pm_plan}"
                print(
                    f"   [Architect] Using rich prompt: {len(architect_prompt)} chars"
                )

            print("\n2️⃣  Architect Agent with Elisya...")
            elisya_state.speaker = "Architect"
            # ✅ PHASE 3: Use the new ASYNC method for tool support
            architecture, elisya_state = await self._run_agent_with_elisya_async(
                "Architect", elisya_state, architect_prompt
            )
            result["architecture"] = architecture

            # Phase 15-3: Generate rich prompt for Dev
            dev_prompt = pm_plan
            if rich_context and rich_context.get("total_context_chars", 0) > 100:
                dev_prompt = self._generate_rich_agent_prompt(
                    agent_type="Dev",
                    rich_context=rich_context,
                    user_question=feature_request,
                    node_path=rich_context.get("node_path", "unknown"),
                )
                dev_prompt += f"\n\n## PM's Plan:\n{pm_plan}"
                print(f"   [Dev] Using rich prompt: {len(dev_prompt)} chars")

            print("\n3️⃣  Dev Agent with Elisya...")
            elisya_state.speaker = "Dev"
            # ✅ PHASE 3: Use the new ASYNC method for tool support
            implementation, elisya_state = await self._run_agent_with_elisya_async(
                "Dev", elisya_state, dev_prompt
            )
            result["implementation"] = implementation

            # Phase 15-3: Generate rich prompt for QA
            qa_prompt = feature_request
            if rich_context and rich_context.get("total_context_chars", 0) > 100:
                qa_prompt = self._generate_rich_agent_prompt(
                    agent_type="QA",
                    rich_context=rich_context,
                    user_question=feature_request,
                    node_path=rich_context.get("node_path", "unknown"),
                )
                print(f"   [QA] Using rich prompt: {len(qa_prompt)} chars")

            print("\n4️⃣  QA Agent with Elisya...")
            elisya_state.speaker = "QA"
            # ✅ PHASE 3: Use the new ASYNC method for tool support
            test_plan, elisya_state = await self._run_agent_with_elisya_async(
                "QA", elisya_state, qa_prompt
            )
            result["tests"] = test_plan

            result["status"] = "complete"
            result["duration"] = time.time() - start_time

            print("\n" + "=" * 70)
            print(f"✅ SEQUENTIAL WORKFLOW COMPLETE WITH ELISYA [{workflow_id}]")
            print(f"   Duration: {result['duration']:.2f}s")
            print(f"   Semantic path: {elisya_state.semantic_path}")
            print("=" * 70 + "\n")

            self.history.append(result)
            self.memory.save_workflow_result(workflow_id, result)
            self.elisya_states[workflow_id] = elisya_state

            # 🌳 PHASE 10: Transform to VETKA-JSON and emit to UI
            self._transform_and_emit_vetka(result, [], elisya_state)

        except Exception as e:
            print(f"\n❌ Workflow error: {e}")
            result["status"] = "error"
            result["error"] = str(e)
            result["duration"] = time.time() - start_time
            self.memory.log_error(workflow_id, "Orchestrator", str(e))

        return result

    # ============ HISTORY & STATISTICS ============

    def get_workflow_history(self, limit: int = 10):
        """Get workflow execution history."""
        return {
            "local_history": self.history[-limit:],
            "weaviate_history": self.memory.get_workflow_history(limit),
        }

    def get_agent_statistics(self):
        """Get statistics about agent performance."""
        return {
            "total_workflows": len(self.history),
            "successful": sum(1 for w in self.history if w.get("status") == "complete"),
            "failed": sum(1 for w in self.history if w.get("status") == "error"),
            "parallel_workflows": sum(
                1 for w in self.history if w.get("execution_mode") == "parallel"
            ),
            "sequential_workflows": sum(
                1 for w in self.history if w.get("execution_mode") == "sequential"
            ),
            "avg_duration": sum(w.get("duration", 0) for w in self.history)
            / max(1, len(self.history)),
            "agents": {
                "pm_stats": self.memory.get_agent_stats("PM"),
                "dev_stats": self.memory.get_agent_stats("Dev"),
                "qa_stats": self.memory.get_agent_stats("QA"),
                "architect_stats": self.memory.get_agent_stats("Architect"),
            },
        }

    # ============ ARC SOLVER HELPERS ============

    def _build_graph_from_workflow(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a simple graph representation from workflow result.

        Converts workflow phases (PM, Architect, Dev, QA) into a node-edge graph
        that ARC Solver can analyze and transform.
        """
        nodes = [
            {"id": "pm", "type": "planning", "name": "PM Agent"},
            {"id": "architect", "type": "design", "name": "Architect Agent"},
            {"id": "dev", "type": "implementation", "name": "Dev Agent"},
            {"id": "qa", "type": "testing", "name": "QA Agent"},
        ]

        edges = [
            {"source": "pm", "target": "architect", "type": "flow"},
            {"source": "architect", "target": "dev", "type": "flow"},
            {"source": "dev", "target": "qa", "type": "flow"},
        ]

        # Add feature-specific nodes if available
        feature = result.get("feature", "")
        if "auth" in feature.lower():
            nodes.append(
                {"id": "auth_service", "type": "service", "name": "Authentication"}
            )
            edges.append(
                {"source": "dev", "target": "auth_service", "type": "implements"}
            )

        if "database" in feature.lower() or "db" in feature.lower():
            nodes.append({"id": "database", "type": "data", "name": "Database"})
            edges.append({"source": "dev", "target": "database", "type": "implements"})

        if "api" in feature.lower():
            nodes.append({"id": "api", "type": "service", "name": "API Service"})
            edges.append({"source": "dev", "target": "api", "type": "implements"})

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "workflow_id": result.get("workflow_id"),
                "feature": feature,
                "execution_mode": result.get("execution_mode"),
            },
        }

    # ============ ELISYA SPECIFIC ENDPOINTS ============

    def get_elisya_state(self, workflow_id: str) -> Optional[Dict]:
        """Get ElisyaState for workflow. Phase 54.1: Delegated to ElisyaStateService."""
        return self.elisya_service.get_state(workflow_id)

    def add_api_key(self, provider: str, key: str) -> Dict[str, Any]:
        """Add API key via chat command. Phase 54.1: Delegated to APIKeyService."""
        return self.key_service.add_key(provider, key)

    def get_model_routing(self, task: str) -> Dict[str, Any]:
        """Get model routing decision for task. Phase 54.1: Delegated to RoutingService."""
        return self.routing_service.get_model_routing(task)

    def list_api_keys(self) -> Dict[str, Any]:
        """List all stored API keys. Phase 54.1: Delegated to APIKeyService."""
        return self.key_service.list_keys()

    # === PHASE 56.2: GROUP CHAT INTEGRATION ===
    async def call_agent(
        self,
        agent_type: str,
        model_id: str,
        prompt: str,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Single-agent execution for GroupChat integration.
        Routes prompt through specified agent with optional model override.

        Args:
            agent_type: 'PM', 'Dev', 'QA', 'Architect'
            model_id: Model identifier (e.g., 'ollama/qwen2:7b')
            prompt: User input
            context: Optional context dict

        Returns:
            {'output': str, 'state': ElisyaState, 'status': 'done'|'error'}
        """
        try:
            # Validate agent type
            # Phase 57.8: Added Hostess and Researcher
            valid_agent_types = [
                "PM",
                "Dev",
                "QA",
                "Architect",
                "Hostess",
                "Researcher",
            ]
            if agent_type not in valid_agent_types:
                logger.warning(f"[Orchestrator] Invalid agent type: {agent_type}")
                return {
                    "output": "",
                    "error": f"Invalid agent type: {agent_type}",
                    "status": "error",
                }

            # Create state for single agent
            import uuid

            workflow_id = str(uuid.uuid4())
            state = self._get_or_create_state(workflow_id, prompt)

            # Phase 111.15: Preserve original context dict for rich_context
            rich_context = context if isinstance(context, dict) else None

            if context:
                # Phase 57.6: Ensure raw_context is always a string (fixes slice error)
                if isinstance(context, dict):
                    # Convert dict to readable string
                    context_parts = [f"{k}: {v}" for k, v in context.items()]
                    state.raw_context = "\n".join(context_parts)
                elif isinstance(context, str):
                    state.raw_context = context
                else:
                    state.raw_context = str(context)

                # FIX_99.3: ARC Gap Detection before agent calls
                # Analyzes context to detect missing connections or patterns
                try:
                    gap_suggestions = await detect_conceptual_gaps(
                        prompt=prompt,
                        context=state.raw_context,
                        memory_manager=self.memory,
                        arc_solver=getattr(self, "_arc_solver", None),
                    )
                    if gap_suggestions:
                        # Inject suggestions into prompt for agent awareness
                        prompt = f"{prompt}\n{gap_suggestions}"
                        logger.debug(f"[ARC_GAP] Injected gap suggestions into prompt")
                except Exception as gap_err:
                    logger.warning(
                        f"[ARC_GAP] Gap detection failed (non-blocking): {gap_err}"
                    )

            # Inject model override if specified
            old_routing = None
            if model_id and model_id != "auto":
                old_routing = self.model_routing.get(agent_type)
                self.model_routing[agent_type] = {
                    "provider": "manual",
                    "model": model_id,
                }

            # MARKER_102.34: Removed nested retry loop (was MARKER_102.32)
            # OpenRouterProvider.call() already handles 13-key rotation internally
            # Nested loops caused "All OpenRouter keys exhausted" error
            try:
                # Run single agent with Elisya integration
                if hasattr(self, "_run_agent_with_elisya_async"):
                    output, updated_state = await self._run_agent_with_elisya_async(
                        agent_type, state, prompt, rich_context=rich_context  # Phase 111.15
                    )
                else:
                    # Fallback to direct agent call
                    output = f"[{agent_type}] {prompt}"
                    updated_state = state

                return {"output": output, "state": updated_state, "status": "done"}

            finally:
                # Restore routing
                if old_routing:
                    self.model_routing[agent_type] = old_routing
                elif model_id and model_id != "auto":
                    # Remove manual override if it was added
                    if agent_type in self.model_routing:
                        if self.model_routing[agent_type].get("provider") == "manual":
                            del self.model_routing[agent_type]

        except Exception as e:
            logger.error(f"[Orchestrator] call_agent failed: {e}")
            return {"output": "", "error": str(e), "status": "error"}

    # === PHASE 60: LANGGRAPH EXECUTION ===

    async def execute_with_langgraph_stream(
        self,
        feature_request: str,
        workflow_id: str = None,
        group_id: str = None,
        participants: list = None,
        lod_level: str = "MEDIUM",
        # Phase 75.5: Spatial context parameters
        viewport_context: Dict[str, Any] = None,
        pinned_files: list = None,
    ):
        """
        Execute workflow using LangGraph with streaming (Phase 60).

        This is the streaming version that yields events from each node.

        Args:
            feature_request: User's request/task description
            workflow_id: Optional workflow identifier
            group_id: Optional group chat ID
            participants: Optional list of agent types
            lod_level: Level of Detail (MICRO/SMALL/MEDIUM/LARGE/EPIC)
            viewport_context: Phase 75.5 - 3D viewport state from frontend
            pinned_files: Phase 75.5 - User-pinned files for context

        Yields:
            Dict events from each node as they complete

        Example:
            async for event in orchestrator.execute_with_langgraph_stream(
                feature_request="Create a calculator"
            ):
                print(f"Node: {list(event.keys())[0]}")
        """
        if not FEATURE_FLAG_LANGGRAPH:
            raise RuntimeError(
                "LangGraph feature flag is disabled. "
                "Set FEATURE_FLAG_LANGGRAPH = True to enable."
            )

        import uuid
        from src.orchestration.langgraph_builder import create_vetka_graph_builder
        from src.orchestration.langgraph_state import create_initial_state

        workflow_id = workflow_id or str(uuid.uuid4())

        logger.info(f"[LangGraph] Starting streaming workflow: {workflow_id}")

        # Create LangGraph builder with event emitter (Phase 60.2)
        builder = create_vetka_graph_builder(
            self,
            use_persistent_checkpointer=True,
            sio=self.sio,  # Phase 60.2: Pass AsyncServer for Socket.IO events
        )

        # Create initial state (Phase 75.5: with spatial context)
        initial_state = create_initial_state(
            workflow_id=workflow_id,
            context=feature_request,
            group_id=group_id,
            participants=participants,
            lod_level=lod_level,
            # Phase 75.5: Pass spatial context through chain
            viewport_context=viewport_context,
            pinned_files=pinned_files,
        )

        config = {"configurable": {"thread_id": workflow_id}}

        # Stream execution with real-time updates
        async for event in builder.stream(initial_state, config):
            # Extract node name and state
            node_name = list(event.keys())[0]
            node_output = event[node_name]

            # Emit to Socket.IO if available
            if self.socketio:
                try:
                    self.socketio.emit(
                        "langgraph_progress",
                        {
                            "workflow_id": workflow_id,
                            "node": node_name,
                            "state": {
                                "current_agent": node_output.get("current_agent", ""),
                                "eval_score": node_output.get("eval_score", 0),
                                "retry_count": node_output.get("retry_count", 0),
                                "next": node_output.get("next", ""),
                            },
                        },
                    )
                except Exception as e:
                    logger.warning(f"[LangGraph] Socket emit failed: {e}")

            yield event

        logger.info(f"[LangGraph] Streaming workflow complete: {workflow_id}")

    async def execute_with_langgraph(
        self,
        feature_request: str,
        workflow_id: str = None,
        group_id: str = None,
        participants: list = None,
        lod_level: str = "MEDIUM",
        # Phase 75.5: Spatial context parameters
        viewport_context: Dict[str, Any] = None,
        pinned_files: list = None,
    ) -> Dict[str, Any]:
        """
        Execute workflow using LangGraph (Phase 60).

        This is the non-streaming version that returns final state.

        Features:
        - Declarative graph-based workflow
        - Phase 29 Self-Learning (EvalAgent → LearnerAgent → Retry)
        - Automatic checkpointing
        - Phase 75.5: Spatial context awareness (viewport + pinned files)

        Args:
            feature_request: User's request/task description
            workflow_id: Optional workflow identifier
            group_id: Optional group chat ID
            participants: Optional list of agent types
            lod_level: Level of Detail (MICRO/SMALL/MEDIUM/LARGE/EPIC)
            viewport_context: Phase 75.5 - 3D viewport state from frontend
            pinned_files: Phase 75.5 - User-pinned files for context

        Returns:
            Final VETKAState dict after workflow completion
        """
        if not FEATURE_FLAG_LANGGRAPH:
            raise RuntimeError(
                "LangGraph feature flag is disabled. "
                "Set FEATURE_FLAG_LANGGRAPH = True to enable."
            )

        import uuid
        from src.orchestration.langgraph_builder import create_vetka_graph_builder
        from src.orchestration.langgraph_state import create_initial_state

        workflow_id = workflow_id or str(uuid.uuid4())

        logger.info(f"[LangGraph] Starting workflow: {workflow_id}")

        # Create LangGraph builder with event emitter (Phase 60.2)
        builder = create_vetka_graph_builder(
            self,
            use_persistent_checkpointer=True,
            sio=self.sio,  # Phase 60.2: Pass AsyncServer for Socket.IO events
        )

        # Create initial state (Phase 75.5: with spatial context)
        initial_state = create_initial_state(
            workflow_id=workflow_id,
            context=feature_request,
            group_id=group_id,
            participants=participants,
            lod_level=lod_level,
            # Phase 75.5: Pass spatial context through chain
            viewport_context=viewport_context,
            pinned_files=pinned_files,
        )

        config = {"configurable": {"thread_id": workflow_id}}

        # Single execution
        result = await builder.invoke(initial_state, config)
        logger.info(
            f"[LangGraph] Workflow complete: {workflow_id}, "
            f"score={result.get('eval_score', 0):.2f}, "
            f"retries={result.get('retry_count', 0)}"
        )
        return result

    async def execute_workflow_auto(
        self,
        feature_request: str,
        workflow_id: str = None,
        use_langgraph: bool = None,
        **kwargs,
    ):
        """
        Automatically choose between LangGraph and legacy orchestrator.

        Args:
            feature_request: User's request
            workflow_id: Optional workflow ID
            use_langgraph: Override flag (None = use global flag)
            **kwargs: Additional arguments passed to workflow

        Returns/Yields:
            Workflow result (format depends on execution mode)
        """
        # Determine which executor to use
        should_use_langgraph = (
            use_langgraph if use_langgraph is not None else FEATURE_FLAG_LANGGRAPH
        )

        if should_use_langgraph:
            logger.info("[Orchestrator] Using LangGraph workflow (Phase 60)")
            return await self.execute_with_langgraph(
                feature_request=feature_request, workflow_id=workflow_id, **kwargs
            )
        else:
            logger.info("[Orchestrator] Using legacy workflow")
            return await self.execute_full_workflow_streaming(
                feature_request=feature_request, workflow_id=workflow_id, **kwargs
            )

    def get_langgraph_status(self) -> Dict[str, Any]:
        """
        Get LangGraph integration status.

        Returns:
            Dict with enabled status and available features
        """
        return {
            "enabled": FEATURE_FLAG_LANGGRAPH,
            "version": "60.1",
            "features": {
                "declarative_workflow": True,
                "self_learning": True,  # Phase 29
                "eval_threshold": 0.75,
                "max_retries": 3,
                "checkpointing": True,
                "streaming": True,
            },
            "nodes": [
                "hostess",
                "architect",
                "pm",
                "dev_qa_parallel",
                "eval",
                "learner",
                "approval",
            ],
        }

    async def dynamic_semantic_search(
        self, query: str, scope: str = "all", limit: int = 10
    ):
        """
        Dynamic semantic search with Engram integration.

        Phase 76.4: Hybrid search that tries Engram O(1) first, then Qdrant with CAM scoring.

        Args:
            query: Search query string
            scope: Search scope ('all', 'engram', 'qdrant', 'memory')
            limit: Maximum number of results

        Returns:
            Dict with search results and source information
        """
        try:
            print(
                f"[CAM_SEARCH] Starting dynamic semantic search for: '{query[:50]}...'"
            )

            # Step 1: Try Engram O(1) lookup first (fastest)
            if scope in ["all", "engram"]:
                try:
                    from src.memory.aura_store import aura_lookup

                    aura_results = await aura_lookup(query)

                    if aura_results and len(aura_results) > 0:
                        print(
                            f"[CAM_SEARCH] Aura O(1) hit: {len(aura_results)} results"
                        )
                        return {
                            "results": aura_results[:limit],
                            "source": "aura_o1",
                            "query": query,
                            "total_found": len(aura_results),
                        }
                except Exception as e:
                    print(f"[CAM_SEARCH] Aura lookup failed: {e}")

            # Step 2: Fallback to Qdrant with CAM pre-filter
            if scope in ["all", "qdrant", "memory"]:
                try:
                    from src.services.qdrant_client import qdrant_search

                    qdrant_results = await qdrant_search(query, limit=limit)

                    if qdrant_results:
                        print(
                            f"[CAM_SEARCH] Qdrant found {len(qdrant_results)} results"
                        )

                        # Step 3: CAM surprise scoring for relevance boosting
                        if self._cam_engine:
                            scored_results = []
                            for result in qdrant_results:
                                content = result.get("content", str(result))
                                try:
                                    surprise = (
                                        await self._cam_engine.calculate_surprise(
                                            content
                                        )
                                    )
                                    result["surprise_score"] = surprise
                                    scored_results.append(result)
                                except Exception as cam_err:
                                    print(
                                        f"[CAM_SEARCH] CAM scoring failed for result: {cam_err}"
                                    )
                                    result["surprise_score"] = 0.5  # Default score
                                    scored_results.append(result)

                            # Step 4: Sort by CAM score + relevance
                            scored_results.sort(
                                key=lambda x: (
                                    x.get("surprise_score", 0) + x.get("score", 0)
                                ),
                                reverse=True,
                            )

                            print(f"[CAM_SEARCH] CAM-enhanced sorting completed")
                            return {
                                "results": scored_results[:limit],
                                "source": "qdrant_cam_hybrid",
                                "query": query,
                                "total_found": len(scored_results),
                            }
                        else:
                            # Fallback without CAM
                            return {
                                "results": qdrant_results[:limit],
                                "source": "qdrant_fallback",
                                "query": query,
                                "total_found": len(qdrant_results),
                            }
                except Exception as e:
                    print(f"[CAM_SEARCH] Qdrant search failed: {e}")

            # Step 5: Ultimate fallback
            print(f"[CAM_SEARCH] All search methods failed, returning empty results")
            return {
                "results": [],
                "source": "failed_fallback",
                "query": query,
                "total_found": 0,
                "error": "All search methods failed",
            }

        except Exception as e:
            print(f"[CAM_SEARCH] Dynamic semantic search failed: {e}")
            return {
                "results": [],
                "source": "error",
                "query": query,
                "total_found": 0,
                "error": str(e),
            }

    # ============ PHASE 76.4: CAM-ENHANCED AGENT TOOLS ============

    def get_tools_for_agent(
        self, agent_type: str, scope: str = "default"
    ) -> List[dict]:
        """
        Get tools for agent with CAM integration.

        Phase 76.4: Enhanced version that adds CAM tools based on agent type and scope.

        Args:
            agent_type: Type of agent ('PM', 'Dev', 'QA', 'Architect', 'Researcher', 'Hostess')
            scope: Scope context ('default', 'analysis', 'engram', 'memory')

        Returns:
            List of tool schemas with CAM tools integrated
        """
        # Get base tools using existing function
        base_tools = get_tools_for_agent(agent_type)

        # Add CAM tools for analysis/memory agents and scopes
        if (
            agent_type in ["analyst", "researcher", "architect"]
            or scope in ["analysis", "engram", "memory"]
            or
            # Also include CAM tools for existing agents that can benefit
            agent_type in ["PM", "Dev", "QA", "Architect", "Researcher", "Hostess"]
        ):
            # Get CAM tool schemas from registry
            cam_tools = []
            cam_tool_names = [
                "calculate_surprise",
                "compress_with_elision",
                "adaptive_memory_sizing",
            ]

            # Filter based on agent permissions
            allowed_tools = AGENT_TOOL_PERMISSIONS.get(agent_type, [])

            for tool_name in cam_tool_names:
                if tool_name in allowed_tools:
                    tool = registry.get(tool_name)
                    if tool:
                        cam_tools.append(tool.to_ollama_schema())
                        print(f"      🔧 Added CAM tool '{tool_name}' for {agent_type}")

            return base_tools + cam_tools

        return base_tools
