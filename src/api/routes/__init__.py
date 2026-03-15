"""
VETKA API Routes - FastAPI Router Aggregator

@file routes/__init__.py
@status ACTIVE
@phase Phase 108.4
@lastAudit 2026-02-02

Aggregates all FastAPI routers for registration with the main app.
ALL REST ROUTES MIGRATED!

Total: 25+ routers, 75+ endpoints (Phase 136: unified search + artifacts API)
"""

from importlib import import_module
from typing import Dict, List, Tuple
import os

from fastapi import APIRouter, FastAPI

_ROUTER_SPECS: List[Tuple[str, str, str]] = [
    ("config_router", ".config_routes", "router"),
    ("metrics_router", ".metrics_routes", "router"),
    ("files_router", ".files_routes", "router"),
    ("tree_router", ".tree_routes", "router"),
    ("eval_router", ".eval_routes", "router"),
    ("semantic_router", ".semantic_routes", "router"),
    ("chat_router", ".chat_routes", "router"),
    ("chat_history_router", ".chat_history_routes", "router"),
    ("knowledge_router", ".knowledge_routes", "router"),
    ("ocr_router", ".ocr_routes", "router"),
    ("file_ops_router", ".file_ops_routes", "router"),
    ("triple_write_router", ".triple_write_routes", "router"),
    ("workflow_router", ".workflow_routes", "router"),
    ("embeddings_router", ".embeddings_routes", "router"),
    ("health_router", ".health_routes", "router"),
    ("watcher_router", ".watcher_routes", "router"),
    ("model_router", ".model_routes", "router"),
    ("group_router", ".group_routes", "router"),
    ("debug_router", ".debug_routes", "router"),
    ("cam_router", ".cam_routes", "router"),
    ("activity_router", ".activity_routes", "router"),
    ("task_router", ".task_routes", "router"),
    ("tracker_router", ".task_tracker_routes", "router"),
    ("feedback_router", ".feedback_routes", "router"),
    ("dag_router", ".dag_routes", "router"),
    ("unified_search_router", ".unified_search_routes", "router"),
    ("artifact_router", ".artifact_routes", "router"),
    ("pipeline_config_router", ".pipeline_config_routes", "router"),
    ("connectors_router", ".connectors_routes", "router"),
    ("workflow_template_router", ".workflow_template_routes", "router"),
    ("architect_chat_router", ".architect_chat_routes", "router"),
    ("analytics_router", ".analytics_routes", "router"),
    ("mcc_router", ".mcc_routes", "router"),
    ("voice_storage_router", ".voice_storage_routes", "router"),
    ("cut_router", ".cut_routes", "router"),
    ("reflex_router", ".reflex_routes", "router"),
    ("actions_router", ".actions_routes", "router"),  # MARKER_183.5
    ("pipeline_history_router", ".pipeline_history", "router"),  # MARKER_183.11
]

_ROUTER_MAP: Dict[str, Tuple[str, str]] = {
    name: (module_name, attr_name) for name, module_name, attr_name in _ROUTER_SPECS
}



def _load_router(name: str) -> APIRouter:
    module_name, attr_name = _ROUTER_MAP[name]
    module = import_module(module_name, __name__)
    router = getattr(module, attr_name)
    globals()[name] = router
    return router



def __getattr__(name: str):
    if name in _ROUTER_MAP:
        return _load_router(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")



def get_all_routers() -> List[APIRouter]:
    """
    Get all API routers for registration.

    Returns:
        List of APIRouter instances to register with the app.
    """
    return [_load_router(name) for name, _, _ in _ROUTER_SPECS]



def register_all_routers(app: FastAPI) -> None:
    """
    Register all routers with FastAPI app.

    Args:
        app: FastAPI application instance
    """
    routers = get_all_routers()

    for router in routers:
        app.include_router(router)

    opencode_bridge_enabled = os.getenv("OPENCODE_BRIDGE_ENABLED", "false").lower() == "true"

    if opencode_bridge_enabled:
        try:
            from src.opencode_bridge.routes import router as bridge_router

            app.include_router(bridge_router, prefix="/api/bridge", tags=["OpenCode Bridge"])
            print("✅ [Phase 90.X] OpenCode Bridge registered on /api/bridge/*")
        except ImportError as e:
            print(f"⚠️  [Phase 90.X] OpenCode Bridge import failed: {e}")
        except Exception as e:
            print(f"❌ [Phase 90.X] OpenCode Bridge registration error: {e}")
    else:
        print("ℹ️  [Phase 90.X] OpenCode Bridge disabled (set OPENCODE_BRIDGE_ENABLED=true to enable)")

    print(f"  [API] Registered {len(routers)} FastAPI routers (Phase 108.4: +1 activity feed)")


__all__ = [
    "get_all_routers",
    "register_all_routers",
    *[name for name, _, _ in _ROUTER_SPECS],
]
