"""
VETKA Component Initialization Module.

Initializes all system components with proper error handling and graceful degradation.
Components are stored as module-level globals for singleton access.

Usage (FastAPI):
    from src.initialization.components_init import initialize_all_components

    components = initialize_all_components(mock_app, socketio=None, debug=False)
    # Access via: components.get('orchestrator'), etc.

MARKER: CLEANUP41_FLASK_REMOVED - Flask imports removed (Phase 41)

@status: active
@phase: 96
@depends: logging_setup, dependency_check, threading, atexit, concurrent.futures
@used_by: main.py, singletons
"""

import os
import time
import threading
import atexit
from typing import Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

from .logging_setup import LOGGER
from .dependency_check import (
    verify_dependencies,
    check_vetka_modules,
    get_qdrant_host
)


# ============ GLOBAL SINGLETON INSTANCES ============
# These are the actual component instances

orchestrator = None
memory_manager = None
eval_agent = None
metrics_engine = None
model_router = None
# api_gateway = None  # REMOVED: Phase 95 - replaced by direct_api_calls.py
llm_executor_bridge = None
qdrant_manager = None
feedback_loop = None
smart_learner = None
hope_enhancer = None
embeddings_projector = None
student_level_system = None
promotion_engine = None
simpo_loop = None
learner_agent = None
executor = None

# Thread locks for singleton initialization
_ORCHESTRATOR_LOCK = threading.Lock()
_MEMORY_MANAGER_LOCK = threading.Lock()
_EVAL_AGENT_LOCK = threading.Lock()

# Initialization flags
_orchestrator_initialized = False
_components_initialized = False

# ============ AVAILABILITY FLAGS ============
ELISYA_ENABLED = False
PARALLEL_MODE = False
METRICS_AVAILABLE = False
MODEL_ROUTER_V2_AVAILABLE = False
# API_GATEWAY_AVAILABLE = False  # REMOVED: Phase 95 - replaced by direct_api_calls.py
QDRANT_AUTO_RETRY_AVAILABLE = False
FEEDBACK_LOOP_V2_AVAILABLE = False
LEARNER_AVAILABLE = False
SMART_LEARNER_AVAILABLE = False
HOPE_ENHANCER_AVAILABLE = False
EMBEDDINGS_PROJECTOR_AVAILABLE = False
STUDENT_SYSTEM_AVAILABLE = False

# ============ SOCKETIO REFERENCE ============
_socketio = None

# ============ APP CONFIG REFERENCE ============
# Stores app.config dict for get_orchestrator() (replaces Flask current_app)
_app_config = None


def _shutdown_executor():
    """Gracefully shutdown executor on app termination"""
    global executor
    if executor:
        print("\n⏹  Shutting down ThreadPoolExecutor...")
        executor.shutdown(wait=True)
        print("✅ ThreadPoolExecutor shut down")


def initialize_all_components(
    app,
    socketio,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Initialize ALL VETKA components.

    This function:
    1. Verifies dependencies
    2. Initializes each component with error handling
    3. Sets up graceful degradation for missing components
    4. Returns a dict of all initialized components

    Args:
        app: Flask application instance
        socketio: python-socketio AsyncServer
        debug: Enable debug mode

    Returns:
        Dict with all component instances and availability flags
    """
    global _socketio, _components_initialized, _app_config
    global orchestrator, memory_manager, eval_agent
    global metrics_engine, model_router  # api_gateway removed Phase 95
    global llm_executor_bridge, qdrant_manager, feedback_loop
    global smart_learner, hope_enhancer, embeddings_projector
    global student_level_system, promotion_engine, simpo_loop
    global learner_agent, executor
    global ELISYA_ENABLED, PARALLEL_MODE
    global METRICS_AVAILABLE, MODEL_ROUTER_V2_AVAILABLE  # API_GATEWAY_AVAILABLE removed Phase 95
    global QDRANT_AUTO_RETRY_AVAILABLE, FEEDBACK_LOOP_V2_AVAILABLE
    global LEARNER_AVAILABLE, SMART_LEARNER_AVAILABLE
    global HOPE_ENHANCER_AVAILABLE, EMBEDDINGS_PROJECTOR_AVAILABLE
    global STUDENT_SYSTEM_AVAILABLE

    if _components_initialized:
        LOGGER.warning("Components already initialized, skipping re-initialization")
        return _get_components_dict()

    _socketio = socketio
    _app_config = app.config  # Store app.config for get_orchestrator()

    # ============ VERIFY DEPENDENCIES ============
    dep_status = verify_dependencies(verbose=True)
    modules = dep_status['modules']

    # ============ THREAD POOL EXECUTOR ============
    executor = ThreadPoolExecutor(max_workers=4)
    atexit.register(_shutdown_executor)
    print("✅ ThreadPoolExecutor initialized (4 workers)")

    # ============ ORCHESTRATOR CLASS ============
    AgentOrchestrator = None
    if modules.get('orchestrator_elisya', {}).get('available'):
        AgentOrchestrator = modules['orchestrator_elisya']['class']
        ELISYA_ENABLED = modules['orchestrator_elisya'].get('fallback') is None
        PARALLEL_MODE = modules['orchestrator_elisya'].get('parallel', False)
    else:
        print("❌ CRITICAL: No orchestrator available!")

    # ============ PHASE 7.8 INITIALIZATION ============

    # Initialize Metrics Engine
    if modules.get('metrics_engine', {}).get('available'):
        try:
            init_metrics = modules['metrics_engine']['init']
            metrics_engine = init_metrics(max_history=500, window_size=100)

            # MARKER: FIX1_SOCKETIO_EMIT_PHASE40 - FIXED
            # Register Socket.IO callback for real-time updates
            def emit_metrics_to_ui(event_type: str, data: dict):
                try:
                    # Check if socketio is available (None in FastAPI mode)
                    if socketio is not None:
                        socketio.emit(event_type, data)
                except Exception:
                    pass  # Silent fail - metrics UI updates are non-critical

            metrics_engine.register_callback(emit_metrics_to_ui)
            METRICS_AVAILABLE = True
            print("✅ Metrics Engine initialized with Socket.IO callback")
        except Exception as e:
            print(f"⚠️  Metrics Engine initialization failed: {e}")
            METRICS_AVAILABLE = False

    # Initialize Model Router v2
    if modules.get('model_router', {}).get('available'):
        try:
            init_model_router = modules['model_router']['init']
            model_router = init_model_router(redis_host='localhost', redis_port=6379)
            MODEL_ROUTER_V2_AVAILABLE = True
            print("✅ Model Router v2 initialized")
        except Exception as e:
            print(f"⚠️  Model Router v2 initialization failed (Redis fallback): {e}")
            MODEL_ROUTER_V2_AVAILABLE = False

    # REMOVED: API Gateway v2 initialization (Phase 95)
    # Replaced by direct_api_calls.py - no longer needs initialization
    # if modules.get('api_gateway', {}).get('available'):
    #     try:
    #         init_api_gateway = modules['api_gateway']['init']
    #         api_gateway = init_api_gateway(model_router_v2=model_router, timeout=10)
    #         API_GATEWAY_AVAILABLE = True
    #         print("✅ API Gateway v2 initialized with automatic failover")
    #     except Exception as e:
    #         print(f"⚠️  API Gateway v2 initialization failed: {e}")
    #         API_GATEWAY_AVAILABLE = False

    # Initialize LLM Executor Bridge
    try:
        from src.elisya.llm_executor_bridge import init_llm_executor_bridge
        llm_executor_bridge = init_llm_executor_bridge(model_router, None)  # api_gateway removed Phase 95
        if llm_executor_bridge:
            print("✅ LLM Executor Bridge initialized")
    except ImportError:
        pass
    except Exception as e:
        print(f"⚠️  LLM Executor Bridge initialization failed: {e}")

    # Initialize Qdrant Auto-Retry
    if modules.get('qdrant_auto_retry', {}).get('available'):
        try:
            # MARKER: FIX1_QDRANT_CALLBACK_PHASE40 - FIXED
            def on_qdrant_connected():
                print("🎉 Qdrant is now connected! VetkaTree available.")
                if METRICS_AVAILABLE and metrics_engine:
                    metrics_engine.record_event("qdrant_connected", {"status": "connected"})
                # Check if socketio is available (None in FastAPI mode)
                if socketio is not None:
                    try:
                        socketio.emit('qdrant_connected', {
                            'status': 'connected',
                            'timestamp': time.time()
                        })
                    except Exception as e:
                        print(f"⚠️  Callback error: {e}")

            print("\n🔌 QDRANT CONNECTION INITIALIZATION...")
            detected_host = get_qdrant_host()
            print(f"   Auto-detected Qdrant host: {detected_host}")

            init_qdrant = modules['qdrant_auto_retry']['init']
            qdrant_manager = init_qdrant(
                host=detected_host,
                port=6333,
                max_retries=5,
                on_connected=on_qdrant_connected
            )
            QDRANT_AUTO_RETRY_AVAILABLE = True
            print("✅ Qdrant Auto-Retry started (background)")
        except Exception as e:
            print(f"⚠️  Qdrant Auto-Retry initialization failed: {e}")
            QDRANT_AUTO_RETRY_AVAILABLE = False

    # Phase 55.1: Initialize MCP maintenance scheduler
    try:
        from src.mcp.state import get_mcp_state_manager
        import asyncio
        mcp_state = get_mcp_state_manager()

        async def maintenance_cycle():
            """Run maintenance tasks every 24 hours."""
            while True:
                await asyncio.sleep(86400)  # 24 hours
                try:
                    deleted = await mcp_state.delete_expired_states()
                    print(f"   🧹 Maintenance: deleted {deleted} expired MCP states")
                except Exception as e:
                    print(f"   ⚠️ Maintenance failed: {e}")

        # Start maintenance in background
        def run_maintenance():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(maintenance_cycle())

        maintenance_thread = threading.Thread(target=run_maintenance, daemon=True)
        maintenance_thread.start()
        print("   • MCP Maintenance: scheduler started (24h cycle)")

    except Exception as e:
        print(f"   ⚠️ MCP maintenance init failed: {e}")

    # Initialize Feedback Loop v2
    if modules.get('feedback_loop', {}).get('available'):
        try:
            init_feedback = modules['feedback_loop']['init']
            feedback_loop = init_feedback()
            FEEDBACK_LOOP_V2_AVAILABLE = True
            print("✅ Feedback Loop v2 initialized")
        except Exception as e:
            print(f"⚠️  Feedback Loop v2 initialization failed: {e}")
            FEEDBACK_LOOP_V2_AVAILABLE = False

    # ============ PHASE 8.0 INITIALIZATION ============
    print("\n🚀 PHASE 8.0 COMPONENTS INITIALIZATION...")

    # Initialize SmartLearner
    if modules.get('smart_learner', {}).get('available'):
        try:
            available_models = []
            try:
                import ollama
                models_response = ollama.list()
                available_models = [m.get('name', '') for m in models_response.get('models', [])]
            except Exception:
                pass

            factory = modules['smart_learner']['factory']
            smart_learner = factory(
                available_models=available_models,
                use_api_fallback=True
            )
            SMART_LEARNER_AVAILABLE = True
            print(f"✅ SmartLearner initialized ({len(available_models)} local models)")
        except Exception as e:
            print(f"⚠️  SmartLearner initialization failed: {e}")
            SMART_LEARNER_AVAILABLE = False

    # Initialize HOPEEnhancer
    if modules.get('hope_enhancer', {}).get('available'):
        try:
            factory = modules['hope_enhancer']['factory']
            hope_enhancer = factory(api_client=None, use_api_fallback=True)
            HOPE_ENHANCER_AVAILABLE = True
            print("✅ HOPEEnhancer initialized (hierarchical analysis)")
        except Exception as e:
            print(f"⚠️  HOPEEnhancer initialization failed: {e}")
            HOPE_ENHANCER_AVAILABLE = False

    # Initialize EmbeddingsProjector
    if modules.get('embeddings_projector', {}).get('available'):
        try:
            factory = modules['embeddings_projector']['factory']
            embeddings_projector = factory(method="PCA", n_components=3)
            EMBEDDINGS_PROJECTOR_AVAILABLE = True
            print("✅ EmbeddingsProjector initialized (PCA 3D)")
        except Exception as e:
            print(f"⚠️  EmbeddingsProjector initialization failed: {e}")
            EMBEDDINGS_PROJECTOR_AVAILABLE = False

    # ============ PHASE 9.0 INITIALIZATION ============
    print("\n🎓 PHASE 9.0 STUDENT SYSTEM INITIALIZATION...")

    if modules.get('student_system', {}).get('available'):
        try:
            # Create Student Level System
            from src.agents.student_level_system import student_level_system_factory
            from src.orchestration.student_promotion_engine import student_promotion_engine_factory
            from src.orchestration.simpo_training_loop import simpo_training_loop_factory

            student_level_system = student_level_system_factory(memory_manager=None)
            print("✅ StudentLevelSystem initialized (6 levels: NOVICE → SPECIALIST)")

            promotion_engine = student_promotion_engine_factory(
                level_system=student_level_system,
                smart_learner=smart_learner if SMART_LEARNER_AVAILABLE else None,
                eval_agent=None,
                memory_manager=None
            )
            print("✅ PromotionEngine initialized")

            simpo_loop = simpo_training_loop_factory(beta=0.2)
            print("✅ SimPOTrainingLoop initialized (β=0.2)")

            # Auto-register default students
            default_students = [
                ("deepseek", "DeepSeek-LLM", "deepseek-llm:7b"),
                ("qwen", "Qwen2", "qwen2:7b"),
                ("llama", "Llama3.1", "llama3.1:8b"),
            ]
            for student_id, name, model in default_students:
                try:
                    promotion_engine.register_student(student_id, name, model)
                except Exception:
                    pass

            STUDENT_SYSTEM_AVAILABLE = True
            print(f"✅ Registered {len(default_students)} default students")

        except Exception as e:
            print(f"⚠️  Phase 9.0 initialization failed: {e}")
            STUDENT_SYSTEM_AVAILABLE = False

    # MARKER: FIX2_LEARNER_INIT_PHASE40 - FIXED
    # ============ LEARNER INITIALIZATION (Phase 7.9) ============
    learner_module_available = modules.get('learner_factory', {}).get('available', False)
    print(f"\n🎓 LEARNER INITIALIZATION (module available: {learner_module_available})...")

    if learner_module_available:
        try:
            from src.agents.learner_factory import LearnerFactory
            from src.orchestration.memory_manager import MemoryManager
            from src.agents.eval_agent import EvalAgent

            LEARNER_TYPE = os.getenv('LEARNER_TYPE', 'qwen')
            LEARNER_CONFIG = {
                'pixtral': {'model_path': os.path.expanduser(os.getenv('PIXTRAL_PATH', '~/pixtral-12b'))},
                'qwen': {'model': os.getenv('QWEN_MODEL', 'qwen2:7b')}
            }

            temp_memory = MemoryManager()
            temp_eval = EvalAgent(memory_manager=temp_memory)
            config = LEARNER_CONFIG.get(LEARNER_TYPE, {})

            try:
                learner_agent = LearnerFactory.create(
                    LEARNER_TYPE,
                    memory_manager=temp_memory,
                    eval_agent=temp_eval,
                    **config
                )
                LEARNER_AVAILABLE = True
                print(f"✅ Learner: {LEARNER_TYPE.upper()} ({learner_agent.model_name})")
            except Exception as inner_e:
                print(f"   Primary learner failed: {inner_e}, trying fallback...")
                try:
                    learner_agent = LearnerFactory.create(
                        'qwen',
                        memory_manager=temp_memory,
                        eval_agent=temp_eval,
                        **LEARNER_CONFIG.get('qwen', {})
                    )
                    LEARNER_AVAILABLE = True
                    print(f"✅ Learner: Qwen fallback ({learner_agent.model_name})")
                except Exception as fallback_e:
                    print(f"   Fallback also failed: {fallback_e}")
                    LEARNER_AVAILABLE = False
                    learner_agent = None

        except Exception as e:
            print(f"⚠️  Learner initialization failed: {e}")
            LEARNER_AVAILABLE = False
            learner_agent = None
    else:
        print("   ⚠️ Learner module not available")
        LEARNER_AVAILABLE = False
        learner_agent = None

    print(f"   LEARNER_AVAILABLE = {LEARNER_AVAILABLE}")

    # Store the AgentOrchestrator class for later use
    app.config['AGENT_ORCHESTRATOR_CLASS'] = AgentOrchestrator

    # PHASE 47: Initialize agents (PM, Dev, QA, Architect)
    print("\n🤖 PHASE 47: AGENT INITIALIZATION...")
    initialize_agents()

    _components_initialized = True
    print("\n✅ All components initialized successfully")

    return _get_components_dict()


def _get_components_dict() -> Dict[str, Any]:
    """Return dict of all components and flags"""
    return {
        'orchestrator': orchestrator,
        'memory_manager': memory_manager,
        'eval_agent': eval_agent,
        'metrics_engine': metrics_engine,
        'model_router': model_router,
        # 'api_gateway': api_gateway,  # REMOVED: Phase 95
        'llm_executor_bridge': llm_executor_bridge,
        'qdrant_manager': qdrant_manager,
        'feedback_loop': feedback_loop,
        'smart_learner': smart_learner,
        'hope_enhancer': hope_enhancer,
        'embeddings_projector': embeddings_projector,
        'student_level_system': student_level_system,
        'promotion_engine': promotion_engine,
        'simpo_loop': simpo_loop,
        'learner_agent': learner_agent,
        'executor': executor,
        # Availability flags
        'ELISYA_ENABLED': ELISYA_ENABLED,
        'PARALLEL_MODE': PARALLEL_MODE,
        'METRICS_AVAILABLE': METRICS_AVAILABLE,
        'MODEL_ROUTER_V2_AVAILABLE': MODEL_ROUTER_V2_AVAILABLE,
        # 'API_GATEWAY_AVAILABLE': API_GATEWAY_AVAILABLE,  # REMOVED: Phase 95
        'QDRANT_AUTO_RETRY_AVAILABLE': QDRANT_AUTO_RETRY_AVAILABLE,
        'FEEDBACK_LOOP_V2_AVAILABLE': FEEDBACK_LOOP_V2_AVAILABLE,
        'LEARNER_AVAILABLE': LEARNER_AVAILABLE,
        'SMART_LEARNER_AVAILABLE': SMART_LEARNER_AVAILABLE,
        'HOPE_ENHANCER_AVAILABLE': HOPE_ENHANCER_AVAILABLE,
        'EMBEDDINGS_PROJECTOR_AVAILABLE': EMBEDDINGS_PROJECTOR_AVAILABLE,
        'STUDENT_SYSTEM_AVAILABLE': STUDENT_SYSTEM_AVAILABLE,
        'AGENTS_AVAILABLE': AGENTS_AVAILABLE,
    }


# ============ SINGLETON GETTERS ============
# These provide thread-safe access to component instances

def get_orchestrator():
    """
    Get or create orchestrator with SocketIO (GLOBAL SINGLETON).
    Thread-safe with double-checked locking.
    """
    global orchestrator, _orchestrator_initialized

    if orchestrator is not None:
        return orchestrator

    with _ORCHESTRATOR_LOCK:
        if orchestrator is not None:
            return orchestrator

        # MARKER: CLEANUP41_NO_FLASK_CURRENT_APP - Use stored class instead
        if not _orchestrator_initialized and _app_config:
            AgentOrchestrator = _app_config.get('AGENT_ORCHESTRATOR_CLASS')
            if AgentOrchestrator:
                orchestrator = AgentOrchestrator(socketio=_socketio, use_parallel=True)
                _orchestrator_initialized = True

        return orchestrator


def get_memory_manager():
    """
    Get or create memory manager (GLOBAL SINGLETON).
    Thread-safe with double-checked locking.
    """
    global memory_manager

    if memory_manager is not None:
        return memory_manager

    with _MEMORY_MANAGER_LOCK:
        if memory_manager is not None:
            return memory_manager

        from src.orchestration.memory_manager import MemoryManager
        memory_manager = MemoryManager()
        return memory_manager


def get_eval_agent():
    """
    Get or create EvalAgent instance (GLOBAL SINGLETON).
    Thread-safe with double-checked locking.
    """
    global eval_agent

    if eval_agent is not None:
        return eval_agent

    with _EVAL_AGENT_LOCK:
        if eval_agent is not None:
            return eval_agent

        from src.agents.eval_agent import EvalAgent
        mem = get_memory_manager()

        model = "deepseek-coder:6.7b"
        if MODEL_ROUTER_V2_AVAILABLE and model_router:
            try:
                selected_model, metadata = model_router.select_model("eval_scoring", "MEDIUM")
                if selected_model:
                    model = selected_model
            except Exception:
                pass

        eval_agent = EvalAgent(model=model, memory_manager=mem)
        return eval_agent


def get_metrics_engine():
    """Get metrics engine instance"""
    return metrics_engine


def get_model_router():
    """Get model router instance"""
    return model_router


# REMOVED: Phase 95 - api_gateway replaced by direct_api_calls.py
# def get_api_gateway():
#     """Get API gateway instance"""
#     return api_gateway


def get_smart_learner():
    """Get smart learner instance"""
    return smart_learner


def get_hope_enhancer():
    """Get HOPE enhancer instance"""
    return hope_enhancer


def get_embeddings_projector():
    """Get embeddings projector instance"""
    return embeddings_projector


def get_student_level_system():
    """Get student level system instance"""
    return student_level_system


def get_promotion_engine():
    """Get promotion engine instance"""
    return promotion_engine


def get_learner_agent():
    """Get learner agent instance"""
    return learner_agent


def get_executor():
    """Get thread pool executor instance"""
    return executor


def get_socketio():
    """Get SocketIO instance"""
    return _socketio


def get_qdrant_manager():
    """
    Get Qdrant manager instance (Phase 80.17).

    Used by file_watcher for lazy fetch of qdrant_client
    to fix the singleton caching bug where watcher was
    initialized before Qdrant connected.

    Returns:
        QdrantAutoRetry instance or None if not available
    """
    return qdrant_manager


# ============ PHASE 47: AGENT INITIALIZATION ============
AGENTS_AVAILABLE = False


def initialize_agents() -> bool:
    """
    Initialize PM/Dev/QA/Architect agents and register them.
    Called after main component initialization.

    Returns:
        True if agents initialized successfully
    """
    global AGENTS_AVAILABLE

    try:
        from src.agents.vetka_pm import VETKAPMAgent
        from src.agents.vetka_dev import VETKADevAgent
        from src.agents.vetka_qa import VETKAQAAgent
        from src.agents.vetka_architect import VETKAArchitectAgent
        from src.api.handlers.handler_utils import set_agents

        agents_dict = {
            'PM': {
                'instance': VETKAPMAgent(),
                'system_prompt': 'You are PM Agent. Plan tasks, analyze requirements, manage project scope.'
            },
            'Dev': {
                'instance': VETKADevAgent(),
                'system_prompt': 'You are Dev Agent. Write code, implement features, fix bugs.'
            },
            'QA': {
                'instance': VETKAQAAgent(),
                'system_prompt': 'You are QA Agent. Test code, find bugs, ensure quality.'
            },
            'Architect': {
                'instance': VETKAArchitectAgent(),
                'system_prompt': 'You are Architect Agent. Design systems, review architecture, ensure scalability.'
            },
        }

        set_agents(agents_dict)
        AGENTS_AVAILABLE = True
        print("✅ Agents initialized: PM, Dev, QA, Architect")
        return True

    except Exception as e:
        print(f"⚠️ Agent initialization failed: {e}")
        AGENTS_AVAILABLE = False
        return False


def get_agents_available() -> bool:
    """Check if agents are available"""
    return AGENTS_AVAILABLE
