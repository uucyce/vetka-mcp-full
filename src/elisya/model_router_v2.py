"""
MODEL ROUTER v2 for PHASE 7.4
Intelligent routing of tasks to optimal models based on complexity, cost, and availability

@file model_router_v2.py
@status active
@phase 96
@depends time, hashlib, os, enum, dataclasses, threading, json, redis (optional)
@used_by provider_registry.py, orchestrator_with_elisya.py, routing_service.py, model_routes.py, elisya/__init__.py
"""

import time
import hashlib
import os
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass
import threading
import json

# MARKER_93.11_MODEL_STATUS: Global model status storage
# Stores online/offline status, timestamps, error codes for UI display
_model_status_cache: Dict[str, Dict] = {}
_status_cache_path = "data/model_status_cache.json"
_status_lock = threading.Lock()

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class TaskType(Enum):
    """Task classification for routing"""

    PM_PLANNING = "pm_planning"
    ARCHITECTURE = "architecture"
    DEV_CODING = "dev_coding"
    QA_TESTING = "qa_testing"
    EVAL_SCORING = "eval_scoring"
    UNKNOWN = "unknown"


class Provider(Enum):
    """Phase 32.5: Compatibility alias for old model_router.py Provider enum"""

    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    CLAUDE = "claude"
    OPENAI = "openai"


class Complexity(Enum):
    """Task complexity levels"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class ModelRoute:
    """Model routing configuration"""

    task_type: str
    optimal_model: str
    fallback_models: List[str]
    cost_limit: float  # USD per request
    min_version: Optional[str] = None
    required_capabilities: List[str] = None

    def __post_init__(self):
        if self.required_capabilities is None:
            self.required_capabilities = []


class ModelRouterV2:
    """
    Intelligent model routing engine

    Features:
    - Task-type aware routing (PM, Architect, Dev, QA, Eval)
    - Complexity-based selection (LOW/MEDIUM/HIGH)
    - Cost optimization (route to cheapest available)
    - Provider health tracking (Redis cache)
    - Fallback chains (optimal → secondary → tertiary)
    - Latency tracking and analytics
    - Auto-recovery on provider failure
    """

    # Routing rules: task_type → {complexity → ModelRoute}
    ROUTES: Dict[str, Dict[str, ModelRoute]] = {
        TaskType.PM_PLANNING.value: {
            Complexity.LOW.value: ModelRoute(
                task_type=TaskType.PM_PLANNING.value,
                optimal_model="ollama:mistral:latest",
                fallback_models=["claude-sonnet", "gpt-4", "gemini-pro"],
                cost_limit=0.05,
                required_capabilities=["planning", "reasoning"],
            ),
            Complexity.MEDIUM.value: ModelRoute(
                task_type=TaskType.PM_PLANNING.value,
                optimal_model="gpt-4",
                fallback_models=["claude-opus", "gemini-pro"],
                cost_limit=0.15,
                required_capabilities=["complex-planning", "multi-step-reasoning"],
            ),
            Complexity.HIGH.value: ModelRoute(
                task_type=TaskType.PM_PLANNING.value,
                optimal_model="claude-opus",
                fallback_models=["gpt-4-turbo", "gemini-2.0-flash-exp"],
                cost_limit=0.30,
                required_capabilities=[
                    "strategic-planning",
                    "deep-reasoning",
                    "risk-analysis",
                ],
            ),
        },
        TaskType.ARCHITECTURE.value: {
            Complexity.LOW.value: ModelRoute(
                task_type=TaskType.ARCHITECTURE.value,
                optimal_model="ollama:neural-chat:latest",
                fallback_models=["claude-sonnet", "gpt-3.5-turbo"],
                cost_limit=0.05,
                required_capabilities=["architecture", "design"],
            ),
            Complexity.MEDIUM.value: ModelRoute(
                task_type=TaskType.ARCHITECTURE.value,
                optimal_model="claude-sonnet",
                fallback_models=["gpt-4", "gemini-pro"],
                cost_limit=0.12,
                required_capabilities=["system-design", "scalability"],
            ),
            Complexity.HIGH.value: ModelRoute(
                task_type=TaskType.ARCHITECTURE.value,
                optimal_model="claude-opus",
                fallback_models=["gpt-4-turbo", "gemini-2.0-flash-exp"],
                cost_limit=0.25,
                required_capabilities=[
                    "enterprise-architecture",
                    "deep-technical-design",
                ],
            ),
        },
        TaskType.DEV_CODING.value: {
            Complexity.LOW.value: ModelRoute(
                task_type=TaskType.DEV_CODING.value,
                optimal_model="ollama:deepseek-coder:6.7b",
                fallback_models=["ollama:neural-chat:latest", "claude-sonnet"],
                cost_limit=0.02,
                required_capabilities=["coding", "syntax"],
            ),
            Complexity.MEDIUM.value: ModelRoute(
                task_type=TaskType.DEV_CODING.value,
                optimal_model="deepseek-coder",
                fallback_models=["gpt-4", "claude-sonnet"],
                cost_limit=0.10,
                required_capabilities=["coding", "debugging", "optimization"],
            ),
            Complexity.HIGH.value: ModelRoute(
                task_type=TaskType.DEV_CODING.value,
                optimal_model="gpt-4-turbo",
                fallback_models=["claude-opus", "deepseek-coder"],
                cost_limit=0.20,
                required_capabilities=[
                    "advanced-coding",
                    "architecture",
                    "performance",
                ],
            ),
        },
        TaskType.QA_TESTING.value: {
            Complexity.LOW.value: ModelRoute(
                task_type=TaskType.QA_TESTING.value,
                optimal_model="ollama:llama2:13b",
                fallback_models=["claude-sonnet", "gpt-3.5-turbo"],
                cost_limit=0.03,
                required_capabilities=["testing", "verification"],
            ),
            Complexity.MEDIUM.value: ModelRoute(
                task_type=TaskType.QA_TESTING.value,
                optimal_model="claude-sonnet",
                fallback_models=["gpt-4", "gemini-pro"],
                cost_limit=0.08,
                required_capabilities=["qa", "edge-cases", "security"],
            ),
            Complexity.HIGH.value: ModelRoute(
                task_type=TaskType.QA_TESTING.value,
                optimal_model="gpt-4",
                fallback_models=["claude-opus", "gemini-pro"],
                cost_limit=0.15,
                required_capabilities=["security-testing", "performance-testing"],
            ),
        },
        TaskType.EVAL_SCORING.value: {
            Complexity.LOW.value: ModelRoute(
                task_type=TaskType.EVAL_SCORING.value,
                optimal_model="ollama:deepseek-coder:6.7b",
                fallback_models=["claude-sonnet", "gpt-3.5-turbo"],
                cost_limit=0.02,
                required_capabilities=["evaluation", "deterministic"],
            ),
            Complexity.MEDIUM.value: ModelRoute(
                task_type=TaskType.EVAL_SCORING.value,
                optimal_model="claude-sonnet",
                fallback_models=["gpt-4", "gemini-pro"],
                cost_limit=0.08,
                required_capabilities=["evaluation", "reasoning", "consistency"],
            ),
            Complexity.HIGH.value: ModelRoute(
                task_type=TaskType.EVAL_SCORING.value,
                optimal_model="claude-opus",
                fallback_models=["gpt-4-turbo", "gemini-2.0-flash-exp"],
                cost_limit=0.15,
                required_capabilities=["complex-evaluation", "nuanced-scoring"],
            ),
        },
        # Phase 32.5: UNKNOWN fallback route for unclassified tasks
        TaskType.UNKNOWN.value: {
            Complexity.LOW.value: ModelRoute(
                task_type=TaskType.UNKNOWN.value,
                optimal_model="ollama:qwen2:7b",
                fallback_models=["ollama:llama3.1:8b", "gpt-3.5-turbo"],
                cost_limit=0.02,
                required_capabilities=["general"],
            ),
            Complexity.MEDIUM.value: ModelRoute(
                task_type=TaskType.UNKNOWN.value,
                optimal_model="ollama:deepseek-llm:7b",
                fallback_models=["claude-sonnet", "gpt-4"],
                cost_limit=0.05,
                required_capabilities=["general", "reasoning"],
            ),
            Complexity.HIGH.value: ModelRoute(
                task_type=TaskType.UNKNOWN.value,
                optimal_model="claude-sonnet",
                fallback_models=["gpt-4", "claude-opus"],
                cost_limit=0.10,
                required_capabilities=["general", "complex-reasoning"],
            ),
        },
    }

    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        """
        Initialize model router

        Args:
            redis_host: Redis server host (for provider health cache)
            redis_port: Redis server port
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_client = None
        self.lock = threading.RLock()

        # Initialize Redis connection (optional)
        self._init_redis()

        # In-memory provider status (fallback if Redis unavailable)
        self.provider_status: Dict[str, Dict] = {}
        self.usage_stats: Dict[str, Dict] = {}

    def _init_redis(self):
        """Initialize Redis connection for provider health cache"""
        if not REDIS_AVAILABLE:
            return

        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=0,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_keepalive=True,
            )
            # Test connection
            self.redis_client.ping()
            print("✅ Model Router: Redis connected for provider health cache")
        except Exception as e:
            print(f"⚠️  Model Router: Redis unavailable ({e}), using in-memory cache")
            self.redis_client = None

    def select_model(
        self,
        task_type: str,
        complexity: str = "MEDIUM",
        preferred_provider: Optional[str] = None,
    ) -> Tuple[str, Dict]:
        """
        Select optimal model for task

        Args:
            task_type: Task type (pm_planning, dev_coding, etc.)
            complexity: Complexity level (LOW, MEDIUM, HIGH)
            preferred_provider: Preferred provider if available (e.g., "openai", "anthropic")

        Returns:
            Tuple of (selected_model, routing_metadata)
        """
        with self.lock:
            # Normalize inputs
            task_type = task_type.lower()
            complexity = complexity.upper()

            # Get route config
            if task_type not in self.ROUTES:
                task_type = TaskType.UNKNOWN.value

            if complexity not in [c.value for c in Complexity]:
                complexity = Complexity.MEDIUM.value

            route = self.ROUTES.get(task_type, {}).get(
                complexity,
                self.ROUTES[TaskType.UNKNOWN.value].get(Complexity.MEDIUM.value),
            )

            # Build fallback chain
            models_to_try = [route.optimal_model] + route.fallback_models

            # Select first available model
            selected_model, is_fallback = self._select_available_model(models_to_try)

            # Record usage
            self._record_usage(selected_model, task_type, complexity)

            return selected_model, {
                "task_type": task_type,
                "complexity": complexity,
                "selected_model": selected_model,
                "is_fallback": is_fallback,
                "optimal_model": route.optimal_model,
                "cost_limit": route.cost_limit,
                "required_capabilities": route.required_capabilities,
            }

    def _select_available_model(self, models: List[str]) -> Tuple[str, bool]:
        """Select first available model from list"""
        for i, model in enumerate(models):
            if self._is_model_healthy(model):
                return model, i > 0  # is_fallback = True if not first

        # If no healthy models, return first (will likely fail, but we tried)
        return models[0], False

    def _is_model_healthy(self, model: str) -> bool:
        """Check if model provider is healthy"""
        if self.redis_client:
            try:
                health = self.redis_client.get(f"model_health:{model}")
                return health != "down"
            except:
                pass

        # Fallback to in-memory status
        return self.provider_status.get(model, {}).get("healthy", True)

    def mark_model_success(
        self, model: str, duration: float, tokens: int = 0, cost: float = 0.0
    ):
        """Record successful model usage"""
        with self.lock:
            # Update Redis
            if self.redis_client:
                try:
                    self.redis_client.setex(
                        f"model_health:{model}",
                        3600,  # 1 hour TTL
                        "up",
                    )
                except:
                    pass

            # Update in-memory
            if model not in self.provider_status:
                self.provider_status[model] = {"healthy": True, "error_count": 0}
            self.provider_status[model]["healthy"] = True
            self.provider_status[model]["error_count"] = 0
            self.provider_status[model]["last_success"] = time.time()

            # Track usage
            self._record_model_stat(model, "success", duration, tokens, cost)

    def mark_model_error(self, model: str, error: str = "unknown"):
        """Record model error"""
        with self.lock:
            # Update in-memory
            if model not in self.provider_status:
                self.provider_status[model] = {"healthy": True, "error_count": 0}

            self.provider_status[model]["error_count"] = (
                self.provider_status[model].get("error_count", 0) + 1
            )
            self.provider_status[model]["last_error"] = time.time()

            # Mark down if too many errors
            error_count = self.provider_status[model]["error_count"]
            if error_count >= 3:
                self.provider_status[model]["healthy"] = False

                if self.redis_client:
                    try:
                        self.redis_client.setex(
                            f"model_health:{model}",
                            600,  # 10 minute timeout
                            "down",
                        )
                    except:
                        pass

            # Track usage
            self._record_model_stat(model, "error", error=error)

    def _record_usage(self, model: str, task_type: str, complexity: str):
        """Record model selection"""
        if model not in self.usage_stats:
            self.usage_stats[model] = {
                "selections": 0,
                "successful": 0,
                "failed": 0,
                "total_duration": 0.0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "task_types": {},
            }

        self.usage_stats[model]["selections"] += 1

        if task_type not in self.usage_stats[model]["task_types"]:
            self.usage_stats[model]["task_types"][task_type] = 0
        self.usage_stats[model]["task_types"][task_type] += 1

    def _record_model_stat(
        self,
        model: str,
        status: str,
        duration: float = 0,
        tokens: int = 0,
        cost: float = 0,
        error: str = "",
    ):
        """Record model execution stat"""
        if model not in self.usage_stats:
            self.usage_stats[model] = {
                "selections": 0,
                "successful": 0,
                "failed": 0,
                "total_duration": 0.0,
                "total_tokens": 0,
                "total_cost": 0.0,
            }

        stat = self.usage_stats[model]

        if status == "success":
            stat["successful"] += 1
            stat["total_duration"] += duration
            stat["total_tokens"] += tokens
            stat["total_cost"] += cost
        else:
            stat["failed"] += 1

    def get_model_stats(self, model: Optional[str] = None) -> Dict:
        """Get model usage statistics"""
        with self.lock:
            if model:
                stats = self.usage_stats.get(model, {})
                if not stats.get("selections"):
                    return {"model": model, "no_data": True}

                total = stats["successful"] + stats["failed"]
                return {
                    "model": model,
                    "selections": stats["selections"],
                    "success_rate": stats["successful"] / total if total > 0 else 0,
                    "avg_duration": stats["total_duration"] / stats["successful"]
                    if stats["successful"] > 0
                    else 0,
                    "total_tokens": stats["total_tokens"],
                    "total_cost": stats["total_cost"],
                    "task_types": stats.get("task_types", {}),
                }
            else:
                return {m: self.get_model_stats(m) for m in self.usage_stats.keys()}

    def get_provider_health(self) -> Dict:
        """Get health status of all providers"""
        with self.lock:
            return {
                model: {
                    "healthy": status["healthy"],
                    "error_count": status["error_count"],
                    "last_success": status.get("last_success", 0),
                    "last_error": status.get("last_error", 0),
                }
                for model, status in self.provider_status.items()
            }

    def export_stats(self, format: str = "json") -> str:
        """Export routing statistics"""
        data = {
            "models": self.get_model_stats(),
            "providers": self.get_provider_health(),
            "timestamp": time.time(),
        }

        if format == "json":
            return json.dumps(data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")


# Singleton instance
_model_router = None


def init_model_router(
    redis_host: str = "localhost", redis_port: int = 6379
) -> ModelRouterV2:
    """Initialize global model router"""
    global _model_router
    _model_router = ModelRouterV2(redis_host=redis_host, redis_port=redis_port)
    return _model_router


def get_model_router() -> Optional[ModelRouterV2]:
    """Get global model router"""
    return _model_router


# ============ PHASE 32.5: COMPATIBILITY LAYER ============
# These classes provide backward compatibility with the old model_router.py


@dataclass
class ModelConfig:
    """Phase 32.5: Compatibility alias for old model_router.py ModelConfig"""

    name: str
    provider: str
    cost_per_1k_tokens: float = 0.0
    # max_tokens: int = 8000  # REMOVED - unlimited responses
    capabilities: List[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


class ModelRouter:
    """
    Phase 32.5: Compatibility wrapper around ModelRouterV2.
    Provides the old ModelRouter API for backward compatibility.
    """

    def __init__(self, default_provider: Provider = Provider.OLLAMA):
        self.default_provider = default_provider
        self._router_v2 = ModelRouterV2()

        # Provide a 'models' dict for backward compatibility
        self.models = {
            "ollama:qwen2:7b": ModelConfig("qwen2:7b", "ollama", 0.0),
            "ollama:deepseek-llm:7b": ModelConfig("deepseek-llm:7b", "ollama", 0.0),
            "ollama:llama3.1:8b": ModelConfig("llama3.1:8b", "ollama", 0.0),
            "gpt-4": ModelConfig("gpt-4", "openrouter", 0.03),
            "gpt-4-turbo": ModelConfig("gpt-4-turbo", "openrouter", 0.01),
            "claude-opus": ModelConfig("claude-opus", "openrouter", 0.015),
            "claude-sonnet": ModelConfig("claude-sonnet", "openrouter", 0.003),
            "gemini-pro": ModelConfig("gemini-pro", "gemini", 0.001),
        }

    def route(self, task: str) -> Dict[str, Any]:
        """
        Route a task to the optimal model.
        Returns dict with 'model' and 'provider' keys for compatibility.
        """
        # Try to determine task type from task string
        task_lower = task.lower()

        if "pm" in task_lower or "plan" in task_lower:
            task_type = TaskType.PM_PLANNING.value
        elif "architect" in task_lower or "design" in task_lower:
            task_type = TaskType.ARCHITECTURE.value
        elif "dev" in task_lower or "code" in task_lower or "implement" in task_lower:
            task_type = TaskType.DEV_CODING.value
        elif "qa" in task_lower or "test" in task_lower:
            task_type = TaskType.QA_TESTING.value
        elif "eval" in task_lower or "score" in task_lower:
            task_type = TaskType.EVAL_SCORING.value
        else:
            task_type = TaskType.UNKNOWN.value

        # Use v2 router for actual selection
        model, metadata = self._router_v2.select_model(
            task_type, Complexity.MEDIUM.value
        )

        return {
            "model": model,
            "provider": self.default_provider.value,
            "fallback_models": metadata.get("fallback_models", []),
            "task_type": task_type,
        }


# ============ PHASE 93.11: MODEL STATUS FOR UI ============
# Global functions for tracking online/offline status with timestamps
# Used by /api/models/status endpoint for phonebook UI


def _load_model_status() -> None:
    """Load model status from JSON cache on startup."""
    global _model_status_cache

    if os.path.exists(_status_cache_path):
        try:
            with open(_status_cache_path, 'r') as f:
                _model_status_cache = json.load(f)
        except (json.JSONDecodeError, IOError):
            _model_status_cache = {}


def _persist_model_status() -> None:
    """Save model status to JSON cache (called after each update)."""
    with _status_lock:
        try:
            os.makedirs(os.path.dirname(_status_cache_path), exist_ok=True)
            with open(_status_cache_path, 'w') as f:
                json.dump(_model_status_cache, f, indent=2)
        except IOError:
            pass  # Silently fail if can't persist


def update_model_status(model_id: str, success: bool, error_code: int = None) -> None:
    """
    Update model status after each API call.

    Args:
        model_id: The model identifier (e.g., "openai/gpt-4o", "anthropic/claude-3")
        success: True if call succeeded, False if failed
        error_code: HTTP error code if failed (401, 402, 404, 429, etc.)
    """
    global _model_status_cache

    with _status_lock:
        if model_id not in _model_status_cache:
            _model_status_cache[model_id] = {
                "healthy": True,
                "error_count": 0,
                "last_success": None,
                "last_error": None,
                "error_code": None,
                "call_count": 0
            }

        status = _model_status_cache[model_id]
        status["call_count"] = status.get("call_count", 0) + 1

        if success:
            status["healthy"] = True
            status["last_success"] = time.time()
            status["error_count"] = 0
            status["error_code"] = None
        else:
            status["error_count"] = status.get("error_count", 0) + 1
            status["last_error"] = time.time()
            status["error_code"] = error_code
            # Mark unhealthy after 3 consecutive errors
            if status["error_count"] >= 3:
                status["healthy"] = False

    # Persist immediately (Grok improvement)
    _persist_model_status()


def get_model_status_for_ui() -> Dict[str, Dict]:
    """
    Get model status formatted for UI display.

    Returns:
        Dict mapping model_id to status info with:
        - status: "online" | "offline" | "unknown"
        - last_success: Unix timestamp or None
        - last_error: Unix timestamp or None
        - error_code: HTTP code or None
        - call_count: Total calls
    """
    with _status_lock:
        result = {}
        for model_id, status in _model_status_cache.items():
            result[model_id] = {
                "status": "online" if status.get("healthy", True) else "offline",
                "last_success": status.get("last_success"),
                "last_error": status.get("last_error"),
                "error_code": status.get("error_code"),
                "call_count": status.get("call_count", 0)
            }
        return result


# Load status cache on module import
_load_model_status()
