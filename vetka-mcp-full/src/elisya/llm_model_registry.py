"""
VETKA LLM Model Registry - Adaptive Timeout & Model Profiles.

Fetches speed/capacity metadata for LLM models from external APIs,
caches profiles locally, and provides adaptive timeout calculation
based on model performance characteristics.

MARKER_145.ADAPTIVE_TIMEOUT
MARKER_172.OPT — Performance optimization (Phase 172):
  P1: Shared httpx client (no TCP/TLS per request)
  P2: Bulk fetch + dict index (O(1) lookup vs O(N) scan)
  P3: Debounced disk save (coalesce writes)
  P4: asyncio.Lock for async paths
  P5: DRY _profile_from_defaults helper
  P6: Batch prefetch on first use
  P7: Module-level httpx availability check

Data sources (in priority order):
1. Artificial Analysis API (primary)
2. OpenRouter API (fallback)
3. Hardcoded safe defaults (last resort)

@status: active
@phase: 145 + 172.OPT
@depends: httpx, json, asyncio, pathlib, logging, dataclasses, os, time, threading
@used_by: agent_pipeline, fc_loop, orchestrator, reflex_scorer
"""

import asyncio
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# --- P7: Module-level httpx availability check ---
try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore
    _HTTPX_AVAILABLE = False
    logger.warning("httpx not installed — external API fetches disabled")

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

# P3: Debounce interval for disk cache writes (seconds)
_SAVE_DEBOUNCE_SECONDS = 2.0

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
    "qwen3.5:latest": {
        "context_length": 32768,
        "output_tokens_per_second": 46.0,
        "input_tokens_per_second": 120.0,
        "ttft_ms": 620.0,
        "provider": "ollama",
    },
    "qwen3:8b": {
        "context_length": 32768,
        "output_tokens_per_second": 42.0,
        "input_tokens_per_second": 115.0,
        "ttft_ms": 650.0,
        "provider": "ollama",
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
    "deepseek-r1:8b": {
        "context_length": 32768,
        "output_tokens_per_second": 28.0,
        "input_tokens_per_second": 95.0,
        "ttft_ms": 900.0,
        "provider": "ollama",
    },
    "deepseek-v3": {
        "context_length": 128000,
        "output_tokens_per_second": 80.0,
        "input_tokens_per_second": 180.0,
        "ttft_ms": 600.0,
        "provider": "deepseek",
    },
    "qwen2.5:7b": {
        "context_length": 32768,
        "output_tokens_per_second": 38.0,
        "input_tokens_per_second": 105.0,
        "ttft_ms": 700.0,
        "provider": "ollama",
    },
    "qwen2.5:3b": {
        "context_length": 16384,
        "output_tokens_per_second": 62.0,
        "input_tokens_per_second": 140.0,
        "ttft_ms": 420.0,
        "provider": "ollama",
    },
    "phi4-mini:latest": {
        "context_length": 16384,
        "output_tokens_per_second": 70.0,
        "input_tokens_per_second": 155.0,
        "ttft_ms": 350.0,
        "provider": "ollama",
    },
    "qwen2.5vl:3b": {
        "context_length": 16384,
        "output_tokens_per_second": 34.0,
        "input_tokens_per_second": 88.0,
        "ttft_ms": 720.0,
        "provider": "ollama",
    },
    "embeddinggemma:300m": {
        "context_length": 8192,
        "output_tokens_per_second": 0.0,
        "input_tokens_per_second": 0.0,
        "ttft_ms": 50.0,
        "provider": "ollama",
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

    MARKER_172.OPT optimizations:
    - Shared httpx.AsyncClient (reuses TCP connections)
    - Bulk API fetch → dict index (O(1) lookup)
    - Debounced disk writes (coalesce rapid updates)
    - asyncio.Lock for async paths (no event-loop blocking)
    - Proactive prefetch of known models on first use

    Thread-safe. Use get_llm_registry() to obtain the singleton instance.
    """

    def __init__(self) -> None:
        self._profiles: Dict[str, ModelProfile] = {}
        self._cache_loaded_at: float = 0.0
        self._sync_lock = threading.Lock()  # For sync disk I/O only

        # P4: asyncio.Lock for async paths (non-blocking)
        self._async_lock: Optional[asyncio.Lock] = None

        # P1: Shared HTTP client (lazy init, reuses connections)
        self._http_client: Optional["httpx.AsyncClient"] = None

        # P2: Bulk API index — fetched once, O(1) lookup
        self._aa_index: Optional[Dict[str, Dict]] = None  # Artificial Analysis
        self._or_index: Optional[Dict[str, Dict]] = None  # OpenRouter
        self._aa_fetched = False
        self._or_fetched = False

        # P3: Debounced save
        self._dirty = False
        self._save_timer: Optional[threading.Timer] = None

        # P6: Prefetch flag
        self._prefetch_started = False

        self._load_cache()

    def _get_async_lock(self) -> asyncio.Lock:
        """Lazy-init asyncio.Lock (must be created in event loop context)."""
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock

    # --- P1: Shared HTTP client ---

    def _get_http_client(self) -> "httpx.AsyncClient":
        """Get or create shared httpx.AsyncClient with connection pooling."""
        if self._http_client is None or self._http_client.is_closed:
            if not _HTTPX_AVAILABLE:
                raise RuntimeError("httpx not installed")
            self._http_client = httpx.AsyncClient(
                timeout=15.0,
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5,
                    keepalive_expiry=60.0,
                ),
                follow_redirects=True,
            )
        return self._http_client

    async def close(self) -> None:
        """Close shared HTTP client. Call on shutdown."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
        # Flush any pending saves
        self._flush_save()

    # --- Cache I/O ---

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
        """Persist current profiles to disk cache (synchronous, called from timer)."""
        with self._sync_lock:
            if not self._dirty:
                return
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

                self._dirty = False
                logger.debug("Saved %d model profiles to cache", len(profiles_data))

            except OSError as e:
                logger.warning("Cannot write model profile cache: %s", e)

    # P3: Debounced save — coalesce rapid writes into one disk flush
    def _schedule_save(self) -> None:
        """Mark cache dirty and schedule a debounced disk write."""
        self._dirty = True
        # Cancel pending timer if any
        if self._save_timer is not None:
            self._save_timer.cancel()
        self._save_timer = threading.Timer(_SAVE_DEBOUNCE_SECONDS, self._save_cache)
        self._save_timer.daemon = True
        self._save_timer.start()

    def _flush_save(self) -> None:
        """Force immediate save if dirty (call on shutdown)."""
        if self._save_timer is not None:
            self._save_timer.cancel()
            self._save_timer = None
        if self._dirty:
            self._save_cache()

    # --- Profile lookup ---

    async def get_profile(self, model_id: str) -> ModelProfile:
        """
        Get a model profile by model_id.

        Resolution order:
        1. In-memory cache (O(1) dict lookup)
        2. Bulk API index — Artificial Analysis (fetched once)
        3. Bulk API index — OpenRouter (fetched once)
        4. Safe defaults (hardcoded, with fuzzy matching)
        5. Generic fallback profile

        Args:
            model_id: The model identifier (e.g., "gpt-4o", "qwen3-coder")

        Returns:
            ModelProfile with speed/capacity metadata.
        """
        # Normalize: strip provider prefix if present (e.g., "openai/gpt-4o" -> "gpt-4o")
        normalized_id = self._normalize_model_id(model_id)

        # 1. Check in-memory cache (instant, no lock needed for read)
        profile = self._profiles.get(normalized_id)
        if profile is not None:
            return profile

        # P6: Trigger background prefetch on first cache miss
        if not self._prefetch_started:
            self._prefetch_started = True
            # Don't await — fire and forget, current request continues below
            asyncio.ensure_future(self._prefetch_all_apis())

        # Serialize API lookups to avoid duplicate fetches
        async with self._get_async_lock():
            # Double-check after acquiring lock
            profile = self._profiles.get(normalized_id)
            if profile is not None:
                return profile

            # 2. Try Artificial Analysis bulk index
            profile = await self._lookup_artificial_analysis(normalized_id)
            if profile:
                self._store_profile(profile)
                return profile

            # 3. Try OpenRouter bulk index
            profile = await self._lookup_openrouter(normalized_id)
            if profile:
                self._store_profile(profile)
                return profile

            # 4. Try hardcoded safe defaults (with fuzzy matching)
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
        """Store profile in memory and schedule debounced disk save."""
        self._profiles[profile.model_id] = profile
        self._schedule_save()  # P3: debounced, not immediate

    # --- P2: Bulk API fetch + dict index ---

    async def _ensure_aa_index(self) -> Dict[str, Dict]:
        """Fetch Artificial Analysis models ONCE, build O(1) lookup dict."""
        if self._aa_index is not None:
            return self._aa_index
        if self._aa_fetched:
            return {}  # Already tried, failed

        self._aa_fetched = True
        self._aa_index = {}

        api_key = os.environ.get("ARTIFICIAL_ANALYSIS_API_KEY", "").strip()
        if not api_key or not _HTTPX_AVAILABLE:
            logger.debug("Artificial Analysis: no API key or httpx unavailable")
            return self._aa_index

        try:
            client = self._get_http_client()
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            resp = await client.get(ARTIFICIAL_ANALYSIS_API_URL, headers=headers)

            if resp.status_code != 200:
                logger.warning(
                    "Artificial Analysis API returned %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return self._aa_index

            data = resp.json()
            models = data if isinstance(data, list) else data.get("data", [])

            # Build index: normalized_id → raw model data
            for model_data in models:
                aa_model_id = model_data.get("model_id", "") or model_data.get("id", "")
                normalized = self._normalize_model_id(aa_model_id)
                if normalized:
                    self._aa_index[normalized] = model_data
                    # Also store original ID for exact match
                    if aa_model_id and aa_model_id != normalized:
                        self._aa_index[aa_model_id] = model_data

            logger.info("Artificial Analysis: indexed %d models", len(self._aa_index))

        except Exception as e:
            logger.warning("Artificial Analysis API bulk fetch error: %s", e)

        return self._aa_index

    async def _ensure_or_index(self) -> Dict[str, Dict]:
        """Fetch OpenRouter models ONCE, build O(1) lookup dict."""
        if self._or_index is not None:
            return self._or_index
        if self._or_fetched:
            return {}  # Already tried, failed

        self._or_fetched = True
        self._or_index = {}

        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key or not _HTTPX_AVAILABLE:
            logger.debug("OpenRouter: no API key or httpx unavailable")
            return self._or_index

        try:
            client = self._get_http_client()
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            resp = await client.get(OPENROUTER_API_URL, headers=headers)

            if resp.status_code != 200:
                logger.warning(
                    "OpenRouter API returned %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return self._or_index

            data = resp.json()
            models = data.get("data", [])

            # Build index: normalized_id → raw model data
            for model_data in models:
                or_model_id = model_data.get("id", "")
                normalized = self._normalize_model_id(or_model_id)
                if normalized:
                    self._or_index[normalized] = model_data
                    if or_model_id and or_model_id != normalized:
                        self._or_index[or_model_id] = model_data

            logger.info("OpenRouter: indexed %d models", len(self._or_index))

        except Exception as e:
            logger.warning("OpenRouter API bulk fetch error: %s", e)

        return self._or_index

    async def _lookup_artificial_analysis(self, model_id: str) -> Optional[ModelProfile]:
        """O(1) lookup in Artificial Analysis index."""
        index = await self._ensure_aa_index()
        model_data = index.get(model_id)
        if model_data:
            return self._parse_artificial_analysis_model(model_id, model_data)
        return None

    async def _lookup_openrouter(self, model_id: str) -> Optional[ModelProfile]:
        """O(1) lookup in OpenRouter index."""
        index = await self._ensure_or_index()
        model_data = index.get(model_id)
        if model_data:
            return self._parse_openrouter_model(model_id, model_data)
        return None

    # P6: Proactive prefetch — warm cache for all known models
    async def _prefetch_all_apis(self) -> None:
        """Background: fetch all API models once and cache known defaults.

        Called on first cache miss. Populates bulk indices so subsequent
        get_profile() calls are instant O(1) lookups.
        """
        try:
            t0 = time.monotonic()
            await self._ensure_aa_index()
            await self._ensure_or_index()

            # Pre-populate profiles for all safe defaults from API data
            populated = 0
            for model_id in _SAFE_DEFAULTS:
                if model_id not in self._profiles:
                    # Try AA first, then OR, then hardcoded
                    profile = await self._lookup_artificial_analysis(model_id)
                    if not profile:
                        profile = await self._lookup_openrouter(model_id)
                    if not profile:
                        profile = self._get_safe_default(model_id)
                    if profile:
                        self._profiles[profile.model_id] = profile
                        populated += 1

            if populated > 0:
                self._schedule_save()

            elapsed_ms = (time.monotonic() - t0) * 1000
            logger.info(
                "[PREFETCH] Warmed %d model profiles in %.0fms (AA: %d indexed, OR: %d indexed)",
                populated,
                elapsed_ms,
                len(self._aa_index or {}),
                len(self._or_index or {}),
            )
        except Exception as e:
            logger.warning("[PREFETCH] Background prefetch failed: %s", e)

    # --- API response parsers ---

    def _parse_artificial_analysis_model(
        self, model_id: str, data: Dict[str, Any]
    ) -> ModelProfile:
        """Parse Artificial Analysis API response into a ModelProfile."""
        output_tps = (
            data.get("output_tokens_per_second")
            or data.get("tokens_per_second")
            or data.get("output_speed")
            or 35.0
        )
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

        logger.debug("Parsed profile for %s from Artificial Analysis", model_id)
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

    def _parse_openrouter_model(
        self, model_id: str, data: Dict[str, Any]
    ) -> ModelProfile:
        """Parse OpenRouter API response into a ModelProfile."""
        context_length = data.get("context_length", 128000)

        # Heuristic: estimate speed from pricing tier
        pricing = data.get("pricing", {})
        prompt_price = float(pricing.get("prompt", "0") or "0")

        if prompt_price == 0:
            output_tps = 80.0
        elif prompt_price < 0.5e-6:
            output_tps = 70.0
        elif prompt_price < 3e-6:
            output_tps = 50.0
        elif prompt_price < 15e-6:
            output_tps = 35.0
        else:
            output_tps = 25.0

        or_full_id = data.get("id", "")
        provider = or_full_id.split("/")[0] if "/" in or_full_id else "unknown"

        logger.debug("Parsed profile for %s from OpenRouter", model_id)
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

    # --- P5: DRY helper for safe defaults ---

    @staticmethod
    def _profile_from_defaults(
        model_id: str, defaults: Dict[str, Any], source: str = "hardcoded_defaults"
    ) -> ModelProfile:
        """Build a ModelProfile from a _SAFE_DEFAULTS entry. Single source of truth."""
        return ModelProfile(
            model_id=model_id,
            context_length=defaults.get("context_length", 128000),
            output_tokens_per_second=defaults.get("output_tokens_per_second", 35.0),
            input_tokens_per_second=defaults.get("input_tokens_per_second", 90.0),
            ttft_ms=defaults.get("ttft_ms", 800.0),
            provider=defaults.get("provider", "unknown"),
            source=source,
            updated_at=time.time(),
        )

    def _get_safe_default(self, model_id: str) -> Optional[ModelProfile]:
        """
        Look up model in hardcoded safe defaults.
        Supports exact match and fuzzy prefix matching.
        """
        # Exact match
        if model_id in _SAFE_DEFAULTS:
            logger.info("Using hardcoded defaults for %s", model_id)
            return self._profile_from_defaults(model_id, _SAFE_DEFAULTS[model_id])

        # Strip namespace prefix: "qwen/qwen3-coder" → "qwen3-coder"
        stripped_id = model_id.split("/")[-1] if "/" in model_id else model_id
        if stripped_id != model_id and stripped_id in _SAFE_DEFAULTS:
            logger.info("Using namespace-stripped defaults for %s (matched: %s)", model_id, stripped_id)
            return self._profile_from_defaults(
                model_id, _SAFE_DEFAULTS[stripped_id], source="hardcoded_defaults_stripped"
            )

        # Fuzzy prefix match: "gpt-4o-2024-05-13" matches "gpt-4o"
        for default_id, defaults in _SAFE_DEFAULTS.items():
            if model_id.startswith(default_id) or default_id.startswith(model_id):
                logger.info(
                    "Using fuzzy-matched defaults for %s (matched: %s)", model_id, default_id
                )
                return self._profile_from_defaults(
                    model_id, defaults, source="hardcoded_defaults_fuzzy"
                )

        return None

    # --- Public helpers ---

    @property
    def profile_count(self) -> int:
        """Number of profiles currently in memory."""
        return len(self._profiles)

    def get_all_profiles(self) -> Dict[str, ModelProfile]:
        """Return all cached profiles (read-only snapshot)."""
        return dict(self._profiles)


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


def reset_llm_registry() -> None:
    """Reset singleton (for testing). Closes HTTP client and flushes cache."""
    global _registry_instance
    if _registry_instance is not None:
        _registry_instance._flush_save()
        # Note: can't await close() from sync context, but timer cleanup is done
        if _registry_instance._save_timer:
            _registry_instance._save_timer.cancel()
    _registry_instance = None


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
