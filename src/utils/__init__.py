"""
VETKA Utils Package.

Utility modules for security, monitoring, configuration, and logging.

@status: active
@phase: 96
@depends: unified_key_manager, metrics_collector, quiet_logger, embedding_service
@used_by: src.api, src.orchestration, src.agents
"""

# Phase 57.12: Use UnifiedKeyManager directly
from .unified_key_manager import UnifiedKeyManager, get_key_manager
# Backwards compatibility alias
SecureKeyManager = UnifiedKeyManager
from .metrics_collector import MetricsCollector, get_metrics_collector
from .quiet_logger import QuietLogger, RateLimitedLogger, log_once
from .embedding_service import EmbeddingService, get_embedding_service, get_embedding
from .chat_utils import (
    detect_response_type,
    get_agent_model_name,
)
from .model_utils import (
    get_model_for_task,
    is_model_banned,
    get_model_config,
    MODEL_CONFIG,
)
from .qdrant_utils import (
    get_qdrant_host,
    get_qdrant_port,
    get_qdrant_url,
)
# FIX_97.1: Consolidated token estimation
from .token_utils import estimate_tokens

__all__ = [
    'SecureKeyManager',
    'get_key_manager',
    'MetricsCollector',
    'get_metrics_collector',
    'QuietLogger',
    'RateLimitedLogger',
    'log_once',
    'EmbeddingService',
    'get_embedding_service',
    'get_embedding',
    # chat_utils
    'detect_response_type',
    'get_agent_model_name',
    # model_utils (Phase 38.1)
    'get_model_for_task',
    'is_model_banned',
    'get_model_config',
    'MODEL_CONFIG',
    # qdrant_utils (Phase 38.1)
    'get_qdrant_host',
    'get_qdrant_port',
    'get_qdrant_url',
    # token_utils (FIX_97.1)
    'estimate_tokens',
]
