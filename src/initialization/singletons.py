"""
VETKA Singletons Module.

Re-exports singleton getter functions from components_init for convenience.
All getters are thread-safe with double-checked locking.

Usage:
    from src.initialization.singletons import get_orchestrator, get_memory_manager
    orchestrator = get_orchestrator()

@status: active
@phase: 96
@depends: components_init
@used_by: src.api, src.orchestration, src.agents
"""

from .components_init import (
    # Singleton getters
    get_orchestrator,
    get_memory_manager,
    get_eval_agent,
    get_metrics_engine,
    get_model_router,
    # get_api_gateway,  # REMOVED: Phase 95
    get_smart_learner,
    get_hope_enhancer,
    get_embeddings_projector,
    get_student_level_system,
    get_promotion_engine,
    get_learner_agent,
    get_executor,
    get_socketio,

    # Direct access to instances (use getters when possible)
    orchestrator,
    memory_manager,
    eval_agent,
    metrics_engine,
    model_router,
    # api_gateway,  # REMOVED: Phase 95
    llm_executor_bridge,
    qdrant_manager,
    feedback_loop,
    smart_learner,
    hope_enhancer,
    embeddings_projector,
    student_level_system,
    promotion_engine,
    simpo_loop,
    learner_agent,
    executor,

    # Availability flags
    ELISYA_ENABLED,
    PARALLEL_MODE,
    METRICS_AVAILABLE,
    MODEL_ROUTER_V2_AVAILABLE,
    # API_GATEWAY_AVAILABLE,  # REMOVED: Phase 95
    QDRANT_AUTO_RETRY_AVAILABLE,
    FEEDBACK_LOOP_V2_AVAILABLE,
    LEARNER_AVAILABLE,
    SMART_LEARNER_AVAILABLE,
    HOPE_ENHANCER_AVAILABLE,
    EMBEDDINGS_PROJECTOR_AVAILABLE,
    STUDENT_SYSTEM_AVAILABLE,
)

import time
import threading


# ============ CONNECTION RATE LIMITER ============
# Suppress repeated connect/disconnect spam logging

_CONNECTION_LOG_TIMES = {}  # client_id -> last_log_time
_CONNECTION_LOG_INTERVAL = 5.0  # Log same client at most once every 5 seconds
_CONNECTION_LOG_LOCK = threading.Lock()
_TOTAL_CONNECTIONS = 0
_TOTAL_DISCONNECTIONS = 0


def should_log_connection(client_id: str, event_type: str = "connect") -> bool:
    """
    Rate-limit connection/disconnection logging to prevent spam.
    Returns True if this event should be logged.

    Args:
        client_id: The client identifier
        event_type: Either "connect" or "disconnect"

    Returns:
        True if this event should be logged
    """
    global _TOTAL_CONNECTIONS, _TOTAL_DISCONNECTIONS

    with _CONNECTION_LOG_LOCK:
        if event_type == "connect":
            _TOTAL_CONNECTIONS += 1
        else:
            _TOTAL_DISCONNECTIONS += 1

        key = f"{client_id}:{event_type}"
        now = time.time()
        last_log = _CONNECTION_LOG_TIMES.get(key, 0)

        if now - last_log >= _CONNECTION_LOG_INTERVAL:
            _CONNECTION_LOG_TIMES[key] = now
            return True
        return False


def get_connection_stats() -> dict:
    """
    Get connection statistics.

    Returns:
        Dict with total_connections and total_disconnections
    """
    return {
        'total_connections': _TOTAL_CONNECTIONS,
        'total_disconnections': _TOTAL_DISCONNECTIONS
    }


__all__ = [
    # Getters (preferred)
    'get_orchestrator',
    'get_memory_manager',
    'get_eval_agent',
    'get_metrics_engine',
    'get_model_router',
    # 'get_api_gateway',  # REMOVED: Phase 95
    'get_smart_learner',
    'get_hope_enhancer',
    'get_embeddings_projector',
    'get_student_level_system',
    'get_promotion_engine',
    'get_learner_agent',
    'get_executor',
    'get_socketio',

    # Instances
    'orchestrator',
    'memory_manager',
    'eval_agent',
    'metrics_engine',
    'model_router',
    # 'api_gateway',  # REMOVED: Phase 95
    'llm_executor_bridge',
    'qdrant_manager',
    'feedback_loop',
    'smart_learner',
    'hope_enhancer',
    'embeddings_projector',
    'student_level_system',
    'promotion_engine',
    'simpo_loop',
    'learner_agent',
    'executor',

    # Flags
    'ELISYA_ENABLED',
    'PARALLEL_MODE',
    'METRICS_AVAILABLE',
    'MODEL_ROUTER_V2_AVAILABLE',
    # 'API_GATEWAY_AVAILABLE',  # REMOVED: Phase 95
    'QDRANT_AUTO_RETRY_AVAILABLE',
    'FEEDBACK_LOOP_V2_AVAILABLE',
    'LEARNER_AVAILABLE',
    'SMART_LEARNER_AVAILABLE',
    'HOPE_ENHANCER_AVAILABLE',
    'EMBEDDINGS_PROJECTOR_AVAILABLE',
    'STUDENT_SYSTEM_AVAILABLE',

    # Rate limiter
    'should_log_connection',
    'get_connection_stats',
]
