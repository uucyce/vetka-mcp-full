"""
VETKA FastAPI Dependency Injection

@file dependencies.py
@status ACTIVE
@phase Phase 39
@description FastAPI dependency injection - replaces Flask's current_app.config pattern
@lastAudit 2026-01-05

Usage:
    from src.dependencies import get_memory_manager, get_model_router

    @app.get("/api/example")
    async def example(
        memory: MemoryManager = Depends(get_memory_manager),
        router: ModelRouter = Depends(get_model_router)
    ):
        # Use memory and router...
        pass
"""

from fastapi import Request, HTTPException, Depends
from typing import Optional, Any, Callable


# ============================================================
# REQUIRED DEPENDENCIES (raise 503 if not available)
# ============================================================

def get_memory_manager(request: Request):
    """
    Get memory manager from app state.
    Required dependency - raises 503 if not available.
    """
    manager = getattr(request.app.state, 'memory_manager', None)
    if not manager:
        # Try to get from components_init
        from src.initialization.components_init import get_memory_manager as _get_mm
        manager = _get_mm()
    if not manager:
        raise HTTPException(status_code=503, detail="Memory manager not available")
    return manager


def get_orchestrator(request: Request):
    """
    Get orchestrator from app state.
    Required dependency - raises 503 if not available.
    """
    orch = getattr(request.app.state, 'orchestrator', None)
    if not orch:
        from src.initialization.components_init import get_orchestrator as _get_orch
        orch = _get_orch()
    if not orch:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    return orch


def get_eval_agent(request: Request):
    """
    Get eval agent from app state.
    Required dependency - raises 503 if not available.
    """
    agent = getattr(request.app.state, 'eval_agent', None)
    if not agent:
        from src.initialization.components_init import get_eval_agent as _get_eval
        agent = _get_eval()
    if not agent:
        raise HTTPException(status_code=503, detail="Eval agent not available")
    return agent


# ============================================================
# OPTIONAL DEPENDENCIES (return None if not available)
# ============================================================

def get_model_router(request: Request) -> Optional[Any]:
    """
    Get model router from app state.
    Optional dependency - returns None if not available.
    """
    if not getattr(request.app.state, 'MODEL_ROUTER_V2_AVAILABLE', False):
        return None
    return getattr(request.app.state, 'model_router', None)


def get_metrics_engine(request: Request) -> Optional[Any]:
    """
    Get metrics engine from app state.
    Optional dependency - returns None if not available.
    """
    if not getattr(request.app.state, 'METRICS_AVAILABLE', False):
        return None
    return getattr(request.app.state, 'metrics_engine', None)


# REMOVED: Phase 95 - api_gateway replaced by direct_api_calls.py
# def get_api_gateway(request: Request) -> Optional[Any]:
#     """
#     Get API gateway from app state.
#     Optional dependency - returns None if not available.
#     """
#     if not getattr(request.app.state, 'API_GATEWAY_AVAILABLE', False):
#         return None
#     return getattr(request.app.state, 'api_gateway', None)


def get_qdrant_manager(request: Request) -> Optional[Any]:
    """
    Get Qdrant manager from app state.
    Optional dependency - returns None if not available.
    """
    if not getattr(request.app.state, 'QDRANT_AUTO_RETRY_AVAILABLE', False):
        return None
    return getattr(request.app.state, 'qdrant_manager', None)


def get_feedback_loop(request: Request) -> Optional[Any]:
    """
    Get feedback loop from app state.
    Optional dependency - returns None if not available.
    """
    if not getattr(request.app.state, 'FEEDBACK_LOOP_V2_AVAILABLE', False):
        return None
    return getattr(request.app.state, 'feedback_loop', None)


def get_smart_learner(request: Request) -> Optional[Any]:
    """
    Get smart learner from app state.
    Optional dependency - returns None if not available.
    """
    if not getattr(request.app.state, 'SMART_LEARNER_AVAILABLE', False):
        return None
    return getattr(request.app.state, 'smart_learner', None)


def get_hope_enhancer(request: Request) -> Optional[Any]:
    """
    Get HOPE enhancer from app state.
    Optional dependency - returns None if not available.
    """
    if not getattr(request.app.state, 'HOPE_ENHANCER_AVAILABLE', False):
        return None
    return getattr(request.app.state, 'hope_enhancer', None)


def get_embeddings_projector(request: Request) -> Optional[Any]:
    """
    Get embeddings projector from app state.
    Optional dependency - returns None if not available.
    """
    if not getattr(request.app.state, 'EMBEDDINGS_PROJECTOR_AVAILABLE', False):
        return None
    return getattr(request.app.state, 'embeddings_projector', None)


def get_student_level_system(request: Request) -> Optional[Any]:
    """
    Get student level system from app state.
    Optional dependency - returns None if not available.
    """
    if not getattr(request.app.state, 'STUDENT_SYSTEM_AVAILABLE', False):
        return None
    return getattr(request.app.state, 'student_level_system', None)


def get_promotion_engine(request: Request) -> Optional[Any]:
    """
    Get promotion engine from app state.
    Optional dependency - returns None if not available.
    """
    if not getattr(request.app.state, 'STUDENT_SYSTEM_AVAILABLE', False):
        return None
    return getattr(request.app.state, 'promotion_engine', None)


def get_learner_agent(request: Request) -> Optional[Any]:
    """
    Get learner agent from app state.
    Optional dependency - returns None if not available.
    """
    if not getattr(request.app.state, 'LEARNER_AVAILABLE', False):
        return None
    return getattr(request.app.state, 'learner_agent', None)


def get_executor(request: Request) -> Optional[Any]:
    """
    Get thread pool executor from app state.
    Optional dependency - returns None if not available.
    """
    return getattr(request.app.state, 'executor', None)


# MARKER_115_DEPS: Chat history manager dependency
def get_chat_history_manager(request: Request) -> Optional[Any]:
    """
    Get chat history manager.
    MARKER_115_DEPS: Added for Flask cleanup preparation.
    """
    manager = getattr(request.app.state, 'chat_history_manager', None)
    if not manager:
        try:
            from src.chat.chat_history_manager import get_chat_history_manager as _get_chm
            manager = _get_chm()
        except ImportError:
            pass
    return manager


# MARKER_115_DEPS: Hostess agent dependency
def get_hostess(request: Request) -> Optional[Any]:
    """
    Get Hostess agent instance.
    MARKER_115_DEPS: Added for Flask cleanup preparation.
    Note: Hostess is not initialized in components_init, so this looks for it in app.state.
    """
    hostess = getattr(request.app.state, 'hostess', None)
    if not hostess:
        try:
            from src.agents.hostess_agent import HostessAgent
            # Try to initialize with default settings
            hostess = HostessAgent()
        except Exception:
            pass
    return hostess


# MARKER_115_DEPS: Model utility function dependencies
def get_model_for_task(request: Request) -> Optional[callable]:
    """
    Get model_for_task utility function.
    MARKER_115_DEPS: Added for Flask cleanup preparation.
    Returns a callable that takes (task_type, tier) and returns model string.
    """
    # Check if it's stored in flask_config compatibility layer
    flask_config = getattr(request.app.state, 'flask_config', {})
    func = flask_config.get('get_model_for_task')
    if func:
        return func

    # Otherwise, import from model_utils
    try:
        from src.utils.model_utils import get_model_for_task as _get_model
        return _get_model
    except ImportError:
        return None


# MARKER_115_DEPS: Model ban check dependency
def is_model_banned(request: Request) -> Optional[callable]:
    """
    Get is_model_banned utility function.
    MARKER_115_DEPS: Added for Flask cleanup preparation.
    Returns a callable that takes (model) and returns bool.
    """
    # Check if it's stored in flask_config compatibility layer
    flask_config = getattr(request.app.state, 'flask_config', {})
    func = flask_config.get('is_model_banned')
    if func:
        return func

    # Otherwise, import from model_utils
    try:
        from src.utils.model_utils import is_model_banned as _is_banned
        return _is_banned
    except ImportError:
        return None


# ============================================================
# COMPONENT STATUS DEPENDENCY
# ============================================================

def get_component_status(request: Request) -> dict:
    """
    Get status of all components.
    Useful for health checks and debugging.
    MARKER_115_DEPS: Updated to include new dependencies.
    """
    return {
        'metrics_available': getattr(request.app.state, 'METRICS_AVAILABLE', False),
        'model_router_available': getattr(request.app.state, 'MODEL_ROUTER_V2_AVAILABLE', False),
        # 'api_gateway_available': getattr(request.app.state, 'API_GATEWAY_AVAILABLE', False),  # REMOVED: Phase 95
        'qdrant_available': getattr(request.app.state, 'QDRANT_AUTO_RETRY_AVAILABLE', False),
        'feedback_loop_available': getattr(request.app.state, 'FEEDBACK_LOOP_V2_AVAILABLE', False),
        'smart_learner_available': getattr(request.app.state, 'SMART_LEARNER_AVAILABLE', False),
        'hope_enhancer_available': getattr(request.app.state, 'HOPE_ENHANCER_AVAILABLE', False),
        'embeddings_projector_available': getattr(request.app.state, 'EMBEDDINGS_PROJECTOR_AVAILABLE', False),
        'student_system_available': getattr(request.app.state, 'STUDENT_SYSTEM_AVAILABLE', False),
        'learner_available': getattr(request.app.state, 'LEARNER_AVAILABLE', False),
        'elisya_enabled': getattr(request.app.state, 'ELISYA_ENABLED', False),
        'parallel_mode': getattr(request.app.state, 'PARALLEL_MODE', False),
        # MARKER_115_DEPS: New component status checks
        'chat_history_manager_available': getattr(request.app.state, 'chat_history_manager', None) is not None,
        'hostess_available': getattr(request.app.state, 'hostess', None) is not None,
    }


# ============================================================
# FACTORY FOR OPTIONAL COMPONENT DEPENDENCIES
# ============================================================

def get_optional_component(name: str) -> Callable:
    """
    Factory function for optional component dependencies.

    Usage:
        @app.get("/api/example")
        async def example(
            kg_builder = Depends(get_optional_component('kg_builder'))
        ):
            if kg_builder:
                # Use it
                pass
    """
    def _get(request: Request) -> Optional[Any]:
        return getattr(request.app.state, name, None)
    return _get


# ============================================================
# FLASK CONFIG COMPATIBILITY
# ============================================================

def get_flask_config(request: Request) -> dict:
    """
    Get Flask-style config dict for compatibility during migration.
    This allows existing code that expects current_app.config to work.
    """
    return getattr(request.app.state, 'flask_config', {})
