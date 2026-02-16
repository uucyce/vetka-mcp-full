"""
VETKA LLM Model Registry - Adaptive Timeout & Model Profiles.

Fetches speed/capacity metadata for LLM models from external APIs,
caches profiles locally, and provides adaptive timeout calculation
based on model performance characteristics.

MARKER_145.ADAPTIVE_TIMEOUT

Data sources (in priority order):
1. Artificial Analysis API (primary)
2. OpenRouter API (fallback)
3. Hardcoded safe defaults (last resort)

@status: active
@phase: 145
@depends: httpx, json, asyncio, pathlib, logging, dataclasses, os, time, threading
@used_by: agent_pipeline, fc_loop, orchestrator
"""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# Project root: src/elisya/llm_model_registry.py -> src/elisya -> src -> project_root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Cache configuration
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
CACHE_FILE = CACHE_DIR / "llm_model_profiles.json"
CACHE_TTL_SECONDS = 3 * 24 * 3600  # 3 days

# API endpoints
ARTIFICIAL_ANALYSIS_API_URL = "https://api.artificialanalysis.ai/v1/models"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/models"

# Complexity multipliers for timeout calculation
COMPLEXITY_MULTIPLIERS = {
    "simple": 1.0,
    "medium": 1.8,
    "complex": 3.2,
}

# Hardcoded safe defaults for well-known models.
# Used when both external APIs are unavailable.
_SAFE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "grok-4": {
        "context_length": 131072,
        "output_tokens_per_second": 60.0,
        "input_tokens_per_second": 150.0,
        "ttft_ms": 600.0,
        "provider": "xai",
    },
    "grok-fast-4.1": {
        "context_length": 131072,
        "output_tokens_per_second": 90.0,
        "input_tokens_per_second": 200.0,
        "ttft_ms": 400.0,
        "provider": "xai",
    },
    "grok-4.1-fast": {
        "context_length": 131072,
        "output_tokens_per_second": 90.0,
        "input_tokens_per_second": 200.0,
        "ttft_ms": 400.0,
        "provider": "xai",
    },
    "gpt-4o": {
        "context_length": 128000,
        "output_tokens_per_second": 80.0,
        "input_tokens_per_second": 150.0,
        "ttft_ms": 500.0,
        "provider": "openai",
    },
    "gpt-4o-mini": {
        "context_length": 128000,
        "output_tokens_per_second": 120.0,
        "input_tokens_per_second": 250.0,
        "ttft_ms": 300.0,
        "provider": "openai",
    },
    "claude-sonnet-4-20250514": {
        "context_length": 200000,
        "output_tokens_per_second": 70.0,
        "input_tokens_per_second": 130.0,
        "ttft_ms": 700.0,
        "provider": "anthropic",
    },
    "claude-opus-4-20250514": {
        "context_length": 200000,
        "output_tokens_per_second": 40.0,
        "input_tokens_per_second": 100.0,
        "ttft_ms": 1200.0,
        "provider": "anthropic",
    },
    "gemini-2.0-flash": {
        "context_length": 1048576,
        "output_tokens_per_second": 100.0,
        "input_tokens_per_second": 300.0,
        "ttft_ms": 400.0,
        "provider": "google",
    },
    "qwen3-coder": {
        "context_length": 131072,
        "output_tokens_per_second": 55.0,
        "input_tokens_per_second": 120.0,
        "ttft_ms": 600.0,
        "provider": "polza",
    },
    "qwen3-coder-flash": {
        "context_length": 131072,
        "output_tokens_per_second": 85.0,
        "input_tokens_per_second": 180.0,
        "ttft_ms": 400.0,
        "provider": "polza",
    },
    "qwen3-30b": {
        "context_length": 131072,
        "output_tokens_per_second": 70.0,
        "input_tokens_per_second": 150.0,
        "ttft_ms": 500.0,
        "provider": "polza",
    },
    "qwen3-30b-a3b": {
        "context_length": 131072,
        "output_tokens_per_second": 70.0,
        "input_tokens_per_second": 150.0,
        "ttft_ms": 500.0,
        "provider": "polza",
    },
    "qwen3-235b": {
        "context_length": 131072,
        "output_tokens_per_second": 30.0,
        "input_tokens_per_second": 80.0,
        "ttft_ms": 1000.0,
        "provider": "polza",
    },
    "qwen3-235b-a22b": {
        "context_length": 131072,
        "output_tokens_per_second": 30.0,
        "input_tokens_per_second": 80.0,
        "ttft_ms": 1000.0,
        "provider": "polza",
    },
    "kimi-k2.5": {
        "context_length": 131072,
        "output_tokens_per_second": 50.0,
        "input_tokens_per_second": 120.0,
        "ttft_ms": 700.0,
        "provider": "polza",
    },
    "kimi-k2": {
        "context_length": 131072,
        "output_tokens_per_second": 45.0,
        "input_tokens_per_second": 110.0,
        "ttft_ms": 750.0,
        "provider": "polza",
    },
    "glm-4.7-flash": {
        "context_length": 131072,
        "output_tokens_per_second": 80.0,
        "input_tokens_per_second": 180.0,
        "ttft_ms": 400.0,
        "provider": "polza",
    },
    "mimo-v2-flash": {
        "context_length": 131072,
        "output_tokens_per_second": 90.0,
        "input_tokens_per_second": 200.0,
        "ttft_ms": 350.0,
        "provider": "polza",
    },
    "deepseek-r1": {
        "context_length": 128000,
        "output_tokens_per_second": 95.0,
        "input_tokens_per_second": 200.0,
        "ttft_ms": 500.0,
        "provider": "deepseek",
    },
    "deepseek-v3": {
        "context_length": 128000,
        "output_tokens_per_second": 80.0,
        "input_tokens_per_second": 180.0,
        "ttft_ms": 600.0,
        "provider": "deepseek",
    },
}


@dataclass
class ModelProfile:
    """Speed and capacity metadata for a single LLM model."""

    model_id: str
    context_length: int = 128000
    output_tokens_per_second: float = 35.0
    input_tokens_per_second: float = 90.0
    ttft_ms: float = 800.0
    provider: str = "unknown"
    source: str = "fallback"
    updated_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelProfile":
        """Deserialize from dictionary. Ignores unknown keys gracefully."""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


class LLMModelRegistry:
    """
    Registry that fetches, caches, and serves LLM model profiles.

    Data source priority:
    1. In-memory cache (instant)
    2. Disk cache (fast, if not expired)
    3. Artificial Analysis API (primary external)
    4. OpenRouter API (fallback external)
    5. Hardcoded safe defaults (always available)

    Thread-safe. Use get_llm_registry() to obtain the singleton instance.
    """

    def __init__(self) -> None:
        self._profiles: Dict[str, ModelProfile] = {}
        self._cache_loaded_at: float = 0.0
        self._lock = threading.Lock()
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cached profiles from disk. Silently skips if file missing or corrupt."""
        try:
            if not CACHE_FILE.exists():
                logger.debug("No model profile cache file found at %s", CACHE_FILE)
                return

            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                logger.warning("Model profile cache has unexpected format, skipping")
                return

            cache_time = data.get("cached_at", 0.0)
            age_seconds = time.time() - cache_time

            if age_seconds > CACHE_TTL_SECONDS:
                logger.info(
                    "Model profile cache expired (age: %.1f hours, TTL: %.1f hours)",
                    age_seconds / 3600,
                    CACHE_TTL_SECONDS / 3600,
                )
                return

            profiles_data = data.get("profiles", {})
            loaded_count = 0
            for model_id, profile_dict in profiles_data.items():
                try:
                    profile_dict["model_id"] = model_id
                    self._profiles[model_id] = ModelProfile.from_dict(profile_dict)
                    loaded_count += 1
                except (TypeError, ValueError) as e:
                    logger.warning("Skipping corrupt cache entry for %s: %s", model_id, e)

            self._cache_loaded_at = cache_time
            logger.info("Loaded %d model profiles from cache", loaded_count)

        except json.JSONDecodeError as e:
            logger.warning("Model profile cache is corrupt JSON: %s", e)
        except OSError as e:
            logger.warning("Cannot read model profile cache: %s", e)

    def _save_cache(self) -> None:
        """Persist current profiles to disk cache."""
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)

            profiles_data = {}
            for model_id, profile in self._profiles.items():
                d = profile.to_dict()
                d.pop("model_id", None)  # model_id is the key
                profiles_data[model_id] = d

            cache_data = {
                "cached_at": time.time(),
                "profile_count": len(profiles_data),
                "profiles": profiles_data,
            }

            # Write atomically via temp file
            tmp_path = CACHE_FILE.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            tmp_path.replace(CACHE_FILE)

            logger.debug("Saved %d model profiles to cache", len(profiles_data))

        except OSError as e:
            logger.warning("Cannot write model profile cache: %s", e)

    async def get_profile(self, model_id: str) -> ModelProfile:
        """
        Get a model profile by model_id.

        Resolution order:
        1. In-memory cache
        2. Artificial Analysis API
        3. OpenRouter API
        4. Safe defaults (hardcoded)
        5. Generic fallback profile

        Args:
            model_id: The model identifier (e.g., "gpt-4o", "qwen3-coder")

        Returns:
            ModelProfile with speed/capacity metadata.
        """
        # Normalize: strip provider prefix if present (e.g., "openai/gpt-4o" -> "gpt-4o")
        normalized_id = self._normalize_model_id(model_id)

        # 1. Check in-memory cache
        with self._lock:
            if normalized_id in self._profiles:
                return self._profiles[normalized_id]

        # 2. Try Artificial Analysis API
        profile = await self._fetch_from_artificial_analysis(normalized_id)
        if profile:
            self._store_profile(profile)
            return profile

        # 3. Try OpenRouter API
        profile = await self._fetch_from_openrouter(normalized_id)
        if profile:
            self._store_profile(profile)
            return profile

        # 4. Try hardcoded safe defaults
        profile = self._get_safe_default(normalized_id)
        if profile:
            self._store_profile(profile)
            return profile

        # 5. Generic fallback with conservative values
        logger.info("Using generic fallback profile for model: %s", normalized_id)
        fallback = ModelProfile(
            model_id=normalized_id,
            source="generic_fallback",
            updated_at=time.time(),
        )
        self._store_profile(fallback)
        return fallback

    def _normalize_model_id(self, model_id: str) -> str:
        """
        Normalize model ID by stripping provider prefixes.

        Examples:
            "openai/gpt-4o" -> "gpt-4o"
            "anthropic/claude-sonnet-4-20250514" -> "claude-sonnet-4-20250514"
            "gpt-4o" -> "gpt-4o" (unchanged)
        """
        if "/" in model_id:
            model_id = model_id.split("/", 1)[-1]
        return model_id.strip()

    def _store_profile(self, profile: ModelProfile) -> None:
        """Store profile in memory and persist to disk."""
        with self._lock:
            self._profiles[profile.model_id] = profile
        self._save_cache()

    async def _fetch_from_artificial_analysis(self, model_id: str) -> Optional[ModelProfile]:
        """
        Fetch model profile from the Artificial Analysis API.

        Returns None if the API key is missing, the request fails,
        or the model is not found.
        """
        api_key = os.environ.get("ARTIFICIAL_ANALYSIS_API_KEY", "").strip()
        if not api_key:
            logger.debug("ARTIFICIAL_ANALYSIS_API_KEY not set, skipping Artificial Analysis")
            return None

        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(ARTIFICIAL_ANALYSIS_API_URL, headers=headers)

                if resp.status_code != 200:
                    logger.warning(
                        "Artificial Analysis API returned %d: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    return None

                data = resp.json()
                models = data if isinstance(data, list) else data.get("data", [])

                for model_data in models:
                    aa_model_id = model_data.get("model_id", "") or model_data.get("id", "")
                    aa_normalized = self._normalize_model_id(aa_model_id)

                    if aa_normalized == model_id or aa_model_id == model_id:
                        return self._parse_artificial_analysis_model(model_id, model_data)

                logger.debug("Model %s not found in Artificial Analysis response", model_id)
                return None

        except ImportError:
            logger.warning("httpx not installed, cannot fetch from Artificial Analysis")
            return None
        except Exception as e:
            logger.warning("Artificial Analysis API error for %s: %s", model_id, e)
            return None

    def _parse_artificial_analysis_model(
        self, model_id: str, data: Dict[str, Any]
    ) -> ModelProfile:
        """Parse Artificial Analysis API response into a ModelProfile."""
        # Handle various field name formats flexibly
        output_tps = (
            data.get("output_tokens_per_second")
            or data.get("tokens_per_second")
            or data.get("output_speed")
            or 35.0
        )
        # If it's a dict with median/p95, extract median
        if isinstance(output_tps, dict):
            output_tps = output_tps.get("median", 35.0)

        input_tps = (
            data.get("input_tokens_per_second")
            or data.get("prompt_tokens_per_second")
            or 90.0
        )
        if isinstance(input_tps, dict):
            input_tps = input_tps.get("median", 90.0)

        ttft = (
            data.get("time_to_first_token_ms")
            or data.get("ttft_ms")
            or data.get("latency_ms")
            or 800.0
        )
        if isinstance(ttft, dict):
            ttft = ttft.get("median", 800.0)

        context_length = (
            data.get("context_length")
            or data.get("max_context")
            or data.get("context_window")
            or 128000
        )

        provider = data.get("provider", {})
        if isinstance(provider, dict):
            provider = provider.get("name", "unknown")

        logger.info("Fetched profile for %s from Artificial Analysis", model_id)
        return ModelProfile(
            model_id=model_id,
            context_length=int(context_length),
            output_tokens_per_second=float(output_tps),
            input_tokens_per_second=float(input_tps),
            ttft_ms=float(ttft),
            provider=str(provider),
            source="artificial_analysis",
            updated_at=time.time(),
        )

    async def _fetch_from_openrouter(self, model_id: str) -> Optional[ModelProfile]:
        """
        Fetch model profile from OpenRouter API.

        OpenRouter provides context_length and pricing but limited speed data.
        Speed is estimated from pricing tier as a heuristic.
        """
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            logger.debug("OPENROUTER_API_KEY not set, skipping OpenRouter")
            return None

        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(OPENROUTER_API_URL, headers=headers)

                if resp.status_code != 200:
                    logger.warning(
                        "OpenRouter API returned %d: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    return None

                data = resp.json()
                models = data.get("data", [])

                for model_data in models:
                    or_model_id = model_data.get("id", "")
                    or_normalized = self._normalize_model_id(or_model_id)

                    if or_normalized == model_id or or_model_id == model_id:
                        return self._parse_openrouter_model(model_id, model_data)

                logger.debug("Model %s not found in OpenRouter response", model_id)
                return None

        except ImportError:
            logger.warning("httpx not installed, cannot fetch from OpenRouter")
            return None
        except Exception as e:
            logger.warning("OpenRouter API error for %s: %s", model_id, e)
            return None

    def _parse_openrouter_model(
        self, model_id: str, data: Dict[str, Any]
    ) -> ModelProfile:
        """Parse OpenRouter API response into a ModelProfile."""
        context_length = data.get("context_length", 128000)

        # Heuristic: estimate speed from pricing tier
        pricing = data.get("pricing", {})
        prompt_price = float(pricing.get("prompt", "0") or "0")

        if prompt_price == 0:
            output_tps = 80.0  # Free tier, likely fast
        elif prompt_price < 0.5e-6:
            output_tps = 70.0
        elif prompt_price < 3e-6:
            output_tps = 50.0
        elif prompt_price < 15e-6:
            output_tps = 35.0
        else:
            output_tps = 25.0  # Very expensive, large model

        or_full_id = data.get("id", "")
        provider = or_full_id.split("/")[0] if "/" in or_full_id else "unknown"

        logger.info("Fetched profile for %s from OpenRouter", model_id)
        return ModelProfile(
            model_id=model_id,
            context_length=int(context_length),
            output_tokens_per_second=output_tps,
            input_tokens_per_second=output_tps * 2.5,
            ttft_ms=800.0,
            provider=provider,
            source="openrouter",
            updated_at=time.time(),
        )

    def _get_safe_default(self, model_id: str) -> Optional[ModelProfile]:
        """
        Look up model in hardcoded safe defaults.
        Supports exact match and fuzzy prefix matching.
        """
        # Exact match
        if model_id in _SAFE_DEFAULTS:
            defaults = _SAFE_DEFAULTS[model_id]
            logger.info("Using hardcoded defaults for %s", model_id)
            return ModelProfile(
                model_id=model_id,
                context_length=defaults.get("context_length", 128000),
                output_tokens_per_second=defaults.get("output_tokens_per_second", 35.0),
                input_tokens_per_second=defaults.get("input_tokens_per_second", 90.0),
                ttft_ms=defaults.get("ttft_ms", 800.0),
                provider=defaults.get("provider", "unknown"),
                source="hardcoded_defaults",
                updated_at=time.time(),
            )

        # Strip namespace prefix: "qwen/qwen3-coder" → "qwen3-coder"
        stripped_id = model_id.split("/")[-1] if "/" in model_id else model_id
        if stripped_id != model_id and stripped_id in _SAFE_DEFAULTS:
            defaults = _SAFE_DEFAULTS[stripped_id]
            logger.info("Using namespace-stripped defaults for %s (matched: %s)", model_id, stripped_id)
            return ModelProfile(
                model_id=model_id,
                context_length=defaults.get("context_length", 128000),
                output_tokens_per_second=defaults.get("output_tokens_per_second", 35.0),
                input_tokens_per_second=defaults.get("input_tokens_per_second", 90.0),
                ttft_ms=defaults.get("ttft_ms", 800.0),
                provider=defaults.get("provider", "unknown"),
                source="hardcoded_defaults_stripped",
                updated_at=time.time(),
            )

        # Fuzzy prefix match: "gpt-4o-2024-05-13" matches "gpt-4o"
        for default_id, defaults in _SAFE_DEFAULTS.items():
            if model_id.startswith(default_id) or default_id.startswith(model_id):
                logger.info(
                    "Using fuzzy-matched defaults for %s (matched: %s)", model_id, default_id
                )
                return ModelProfile(
                    model_id=model_id,
                    context_length=defaults.get("context_length", 128000),
                    output_tokens_per_second=defaults.get("output_tokens_per_second", 35.0),
                    input_tokens_per_second=defaults.get("input_tokens_per_second", 90.0),
                    ttft_ms=defaults.get("ttft_ms", 800.0),
                    provider=defaults.get("provider", "unknown"),
                    source="hardcoded_defaults_fuzzy",
                    updated_at=time.time(),
                )

        return None


# --- Singleton ---

_registry_instance: Optional[LLMModelRegistry] = None
_registry_lock = threading.Lock()


def get_llm_registry() -> LLMModelRegistry:
    """
    Get the thread-safe singleton LLMModelRegistry instance.
    Creates the instance on first call, reuses on subsequent calls.
    """
    global _registry_instance
    if _registry_instance is None:
        with _registry_lock:
            # Double-checked locking
            if _registry_instance is None:
                _registry_instance = LLMModelRegistry()
                logger.info("LLMModelRegistry singleton initialized")
    return _registry_instance


# --- Standalone timeout function ---

async def calculate_timeout(
    model_id: str,
    input_tokens: int = 4000,
    expected_output_tokens: int = 800,
    fc_turns: int = 1,
    task_complexity: str = "medium",  # "simple", "medium", "complex"
) -> int:
    """
    Calculate an adaptive timeout (in seconds) for an LLM call.

    Uses the model's output speed from the registry to estimate how long
    the call should take, then applies complexity multipliers, FC overhead,
    and a safety buffer.

    Formula:
        processing_time = (input_tokens + expected_output_tokens) / output_tokens_per_second
        fc_overhead = fc_turns * 12.0
        safety_buffer = 25.0
        timeout = (processing_time * complexity_multiplier) + fc_overhead + safety_buffer
        return clamp(timeout, 45, 600)

    Args:
        model_id: The model identifier.
        input_tokens: Estimated input token count.
        expected_output_tokens: Estimated output token count.
        fc_turns: Number of function-calling round-trips expected.
        task_complexity: One of "simple", "medium", "complex".

    Returns:
        Timeout in seconds, clamped to [45, 600].
    """
    registry = get_llm_registry()
    profile = await registry.get_profile(model_id)

    # Get complexity multiplier with safe fallback
    complexity_multiplier = COMPLEXITY_MULTIPLIERS.get(task_complexity, 1.8)

    # Prevent division by zero
    output_tps = max(profile.output_tokens_per_second, 1.0)

    # Core calculation
    processing_time = (input_tokens + expected_output_tokens) / output_tps
    fc_overhead = fc_turns * 12.0  # seconds per FC round-trip
    safety_buffer = 25.0

    timeout = (processing_time * complexity_multiplier) + fc_overhead + safety_buffer

    # Clamp to reasonable bounds
    result = max(45, min(int(timeout), 600))

    logger.debug(
        "Timeout for %s: %.1fs processing * %.1fx complexity + %.1fs FC + %.1fs buffer = %ds "
        "(output_tps=%.1f, input=%d, output=%d, fc_turns=%d)",
        model_id,
        processing_time,
        complexity_multiplier,
        fc_overhead,
        safety_buffer,
        result,
        output_tps,
        input_tokens,
        expected_output_tokens,
        fc_turns,
    )

    return result
