"""
Elisya - Context Management System for VETKA

@file __init__.py
@status active
@phase 96
@depends state.py, middleware.py, semantic_path.py, model_router_v2.py, key_manager.py
@used_by orchestrator_with_elisya.py, initialization modules

Exports:
- ElisyaState, FewShotExample (state management)
- ElisyaMiddleware, MiddlewareConfig, LODLevel, ContextAction (middleware)
- SemanticPathGenerator, PathComponent, get_path_generator (semantic paths)
- ModelRouter, Provider, TaskType, ModelConfig (model routing)
- KeyManager, ProviderType, APIKeyRecord (API key management)
"""

from .state import ElisyaState, FewShotExample
from .middleware import ElisyaMiddleware, LODLevel, MiddlewareConfig, ContextAction
from .semantic_path import SemanticPathGenerator, PathComponent, get_path_generator
from .model_router_v2 import ModelRouter, Provider, TaskType, ModelConfig
from .key_manager import KeyManager, ProviderType, APIKeyRecord

__all__ = [
    # State
    "ElisyaState",
    "FewShotExample",
    # Middleware
    "ElisyaMiddleware",
    "MiddlewareConfig",
    "LODLevel",
    "ContextAction",
    # Semantic Path
    "SemanticPathGenerator",
    "PathComponent",
    "get_path_generator",
    # Model Router
    "ModelRouter",
    "Provider",
    "TaskType",
    "ModelConfig",
    # Key Manager
    "KeyManager",
    "ProviderType",
    "APIKeyRecord",
]

__version__ = "0.1.0"
__author__ = "VETKA Phase 7 Team"
