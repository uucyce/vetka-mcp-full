"""
@file health_routes.py
@status ACTIVE
@phase Phase 43

Deep health check endpoints for VETKA.
Includes basic health, deep component checks, and Kubernetes probes.
"""

from fastapi import APIRouter, Request
from typing import Dict, Any
import time
import asyncio

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health/deep")
async def deep_health(request: Request) -> Dict[str, Any]:
    """
    Deep health check - tests all components.

    Returns detailed status of each component including latency.
    """
    checks = {}
    overall_healthy = True

    # List of components to check with their display names
    components = [
        ('orchestrator', 'OrchestratorWithElisya'),
        ('memory_manager', 'MemoryManager'),
        ('model_router', 'ModelRouter'),
        # ('api_gateway', 'APIGateway'),  # REMOVED: Phase 95 - replaced by direct_api_calls.py
        ('eval_agent', 'EvalAgent'),
        ('metrics_engine', 'MetricsEngine'),
        ('qdrant_manager', 'QdrantManager'),
        ('smart_learner', 'SmartLearner'),
        ('feedback_loop', 'FeedbackLoop'),
        ('hope_enhancer', 'HopeEnhancer'),
        ('embeddings_projector', 'EmbeddingsProjector'),
        ('student_level_system', 'StudentLevelSystem'),
        ('learner_agent', 'LearnerAgent'),
    ]

    for attr_name, display_name in components:
        start = time.time()
        try:
            instance = getattr(request.app.state, attr_name, None)

            if instance is None:
                checks[attr_name] = {
                    "name": display_name,
                    "status": "unavailable",
                    "available": False,
                    "latency_ms": 0
                }
                continue

            # Try to call health method if exists
            responsive = True
            if hasattr(instance, 'health_check'):
                try:
                    if asyncio.iscoroutinefunction(instance.health_check):
                        health_result = await asyncio.wait_for(
                            instance.health_check(),
                            timeout=2.0
                        )
                    else:
                        health_result = instance.health_check()
                    responsive = health_result if isinstance(health_result, bool) else True
                except asyncio.TimeoutError:
                    responsive = False
                except Exception:
                    responsive = False

            latency = (time.time() - start) * 1000

            checks[attr_name] = {
                "name": display_name,
                "status": "healthy" if responsive else "degraded",
                "available": True,
                "responsive": responsive,
                "latency_ms": round(latency, 2)
            }

            if not responsive:
                overall_healthy = False

        except Exception as e:
            checks[attr_name] = {
                "name": display_name,
                "status": "error",
                "available": False,
                "error": str(e),
                "latency_ms": round((time.time() - start) * 1000, 2)
            }
            overall_healthy = False

    # Get request ID from state if available
    request_id = getattr(request.state, 'request_id', None)

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "request_id": request_id,
        "checks": checks,
        "total_components": len(components),
        "healthy_count": sum(1 for c in checks.values() if c.get("status") == "healthy"),
        "available_count": sum(1 for c in checks.values() if c.get("available", False))
    }


@router.get("/health/ready")
async def readiness_check(request: Request) -> Dict[str, Any]:
    """
    Kubernetes readiness probe.

    Returns ready status only if critical components are available.
    """
    # Check critical components only
    orchestrator = getattr(request.app.state, 'orchestrator', None)
    memory = getattr(request.app.state, 'memory_manager', None)

    ready = orchestrator is not None and memory is not None

    return {
        "ready": ready,
        "status": "ready" if ready else "not_ready",
        "checks": {
            "orchestrator": orchestrator is not None,
            "memory_manager": memory is not None
        }
    }


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes liveness probe.

    Always returns OK if server is running.
    """
    return {"status": "alive"}


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Get application metrics.

    Returns counters, timings, and gauges.
    """
    try:
        from src.monitoring.simple_metrics import metrics
        return {
            "status": "ok",
            **metrics.get_stats()
        }
    except ImportError:
        return {
            "status": "unavailable",
            "error": "Metrics module not available"
        }


@router.get("/metrics/requests")
async def get_request_metrics() -> Dict[str, Any]:
    """Get request-specific metrics."""
    try:
        from src.monitoring.simple_metrics import metrics

        stats = metrics.get_stats()

        # Filter to request-related metrics only
        request_counters = {
            k: v for k, v in stats["counters"].items()
            if k.startswith("requests_")
        }
        request_timings = {
            k: v for k, v in stats["timings"].items()
            if k.startswith("request_")
        }

        return {
            "status": "ok",
            "uptime_seconds": stats["uptime_seconds"],
            "total_requests": stats["counters"].get("requests_total", 0),
            "endpoints": request_counters,
            "timings": request_timings
        }
    except ImportError:
        return {"status": "unavailable"}


@router.get("/metrics/llm")
async def get_llm_metrics() -> Dict[str, Any]:
    """Get LLM-specific metrics."""
    try:
        from src.monitoring.simple_metrics import metrics

        stats = metrics.get_stats()

        # Filter to LLM-related metrics only
        llm_counters = {
            k: v for k, v in stats["counters"].items()
            if k.startswith("llm_")
        }
        llm_timings = {
            k: v for k, v in stats["timings"].items()
            if k.startswith("llm_")
        }

        return {
            "status": "ok",
            "total_calls": stats["counters"].get("llm_calls_total", 0),
            "total_tokens": stats["counters"].get("llm_tokens_total", 0),
            "providers": llm_counters,
            "timings": llm_timings
        }
    except ImportError:
        return {"status": "unavailable"}


@router.get("/health/debug")
async def health_debug(request: Request) -> Dict[str, Any]:
    """
    Debug endpoint - show initialization errors and external service status.

    Phase 44.5: Added for troubleshooting initialization issues.
    """
    components = {}

    # Check each critical component
    critical = ['orchestrator', 'memory_manager', 'eval_agent', 'model_router']  # api_gateway REMOVED: Phase 95
    for name in critical:
        instance = getattr(request.app.state, name, None)
        if instance is None:
            components[name] = {"status": "NOT INITIALIZED", "type": None}
        else:
            components[name] = {"status": "OK", "type": type(instance).__name__}

    # Check availability flags
    flags = {}
    flag_names = [
        'METRICS_AVAILABLE', 'MODEL_ROUTER_V2_AVAILABLE',  # 'API_GATEWAY_AVAILABLE' removed Phase 95
        'QDRANT_AUTO_RETRY_AVAILABLE', 'FEEDBACK_LOOP_V2_AVAILABLE',
        'SMART_LEARNER_AVAILABLE', 'HOPE_ENHANCER_AVAILABLE', 'ELISYA_ENABLED'
    ]
    for flag in flag_names:
        flags[flag] = getattr(request.app.state, flag, False)

    # Check external services
    external = {}

    # Check Ollama
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get("http://localhost:11434/api/tags")
            models = r.json().get("models", [])
            external["ollama"] = {"status": "up", "models": len(models)}
    except Exception as e:
        external["ollama"] = {"status": "down", "error": str(e)[:100]}

    # Check Qdrant
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get("http://localhost:6333/health")
            external["qdrant"] = {"status": "up" if r.status_code == 200 else "error"}
    except Exception as e:
        external["qdrant"] = {"status": "down", "error": str(e)[:100]}

    return {
        "phase": "44.5",
        "components": components,
        "flags": flags,
        "external_services": external
    }
