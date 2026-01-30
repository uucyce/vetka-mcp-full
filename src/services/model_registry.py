# === PHASE 56: MODEL REGISTRY ===
"""
Phonebook for AI models - local (Ollama) and cloud (OpenRouter, Gemini).

Handles health checks, capabilities, auto-selection, and voice models.

@status: active
@phase: 96
@depends: asyncio, httpx, dataclasses
@used_by: model_routes.py, chat_handler.py
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class ModelType(Enum):
    LOCAL = "local"                    # Ollama
    CLOUD_FREE = "cloud_free"         # OpenRouter free tier
    CLOUD_PAID = "cloud_paid"         # Paid APIs
    VOICE = "voice"                    # Phase 60.5: TTS/STT models
    MCP_AGENT = "mcp_agent"            # Phase 80.3: External MCP agents (Claude Code, Browser Haiku)


class Capability(Enum):
    CODE = "code"
    REASONING = "reasoning"
    CHAT = "chat"
    VISION = "vision"
    EMBEDDINGS = "embeddings"
    TTS = "tts"                        # Phase 60.5: Text-to-Speech
    STT = "stt"                        # Phase 60.5: Speech-to-Text
    TESTING = "testing"                # Phase 80.3: QA/Testing capability
    EXECUTE = "execute"                # Phase 80.3: Can execute code/commands (MCP agents)


@dataclass
class ModelEntry:
    """Single model in the phonebook."""
    id: str                            # "qwen2:7b" or "openrouter/deepseek-r1"
    name: str                          # Display name
    provider: str                      # "ollama" | "openrouter" | "gemini"
    type: ModelType
    capabilities: List[Capability] = field(default_factory=list)
    context_window: int = 4096
    cost_per_1k: float = 0.0           # $ per 1k tokens
    rate_limit: int = 100              # req/min
    rating: float = 0.0                # 0-1 from benchmarks
    available: bool = True
    last_health_check: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'provider': self.provider,
            'type': self.type.value,
            'capabilities': [c.value for c in self.capabilities],
            'context_window': self.context_window,
            'cost_per_1k': self.cost_per_1k,
            'rate_limit': self.rate_limit,
            'rating': self.rating,
            'available': self.available,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None
        }


class ModelRegistry:
    """
    Phonebook for all available AI models.

    Features:
    - Auto-discovery of Ollama models
    - Health checks every 5 minutes
    - Capability-based selection
    - Favorites and recent tracking
    """

    # Default models (always available)
    DEFAULT_MODELS = [
        ModelEntry(
            id="qwen2:7b",
            name="Qwen 2 7B",
            provider="ollama",
            type=ModelType.LOCAL,
            capabilities=[Capability.CODE, Capability.REASONING],
            context_window=8192,
            rating=0.80
        ),
        ModelEntry(
            id="llama3:8b",
            name="Llama 3 8B",
            provider="ollama",
            type=ModelType.LOCAL,
            capabilities=[Capability.CHAT, Capability.REASONING],
            context_window=8192,
            rating=0.78
        ),
        ModelEntry(
            id="deepseek-coder:6.7b",
            name="DeepSeek Coder 6.7B",
            provider="ollama",
            type=ModelType.LOCAL,
            capabilities=[Capability.CODE],
            context_window=16384,
            rating=0.82
        ),
        # OpenRouter Free
        ModelEntry(
            id="deepseek/deepseek-r1:free",
            name="DeepSeek R1 (Free)",
            provider="openrouter",
            type=ModelType.CLOUD_FREE,
            capabilities=[Capability.CODE, Capability.REASONING],
            context_window=32768,
            rate_limit=80,
            rating=0.85
        ),
        ModelEntry(
            id="meta-llama/llama-3.1-405b-instruct:free",
            name="Llama 3.1 405B (Free)",
            provider="openrouter",
            type=ModelType.CLOUD_FREE,
            capabilities=[Capability.REASONING, Capability.CHAT],
            context_window=32768,
            rate_limit=60,
            rating=0.88
        ),
        ModelEntry(
            id="qwen/qwen3-coder:free",
            name="Qwen 3 Coder (Free)",
            provider="openrouter",
            type=ModelType.CLOUD_FREE,
            capabilities=[Capability.CODE],
            context_window=32768,
            rate_limit=120,
            rating=0.80
        ),
        # === PHASE 60.5: Voice Models (TTS/STT) ===
        ModelEntry(
            id="elevenlabs/bella",
            name="ElevenLabs Bella",
            provider="elevenlabs",
            type=ModelType.VOICE,
            capabilities=[Capability.TTS],
            context_window=0,
            cost_per_1k=0.30,  # ~$0.30/1k chars
            rating=0.95
        ),
        ModelEntry(
            id="elevenlabs/adam",
            name="ElevenLabs Adam",
            provider="elevenlabs",
            type=ModelType.VOICE,
            capabilities=[Capability.TTS],
            context_window=0,
            cost_per_1k=0.30,
            rating=0.94
        ),
        ModelEntry(
            id="google/wavenet",
            name="Google WaveNet",
            provider="google",
            type=ModelType.VOICE,
            capabilities=[Capability.TTS, Capability.STT],
            context_window=0,
            cost_per_1k=0.016,  # $16/1M chars
            rating=0.88
        ),
        ModelEntry(
            id="deepgram/nova-2",
            name="Deepgram Nova 2",
            provider="deepgram",
            type=ModelType.VOICE,
            capabilities=[Capability.STT],
            context_window=0,
            cost_per_1k=0.0043,  # $0.0043/min
            rating=0.92
        ),
        ModelEntry(
            id="openai/whisper-1",
            name="OpenAI Whisper",
            provider="openai",
            type=ModelType.VOICE,
            capabilities=[Capability.STT],
            context_window=0,
            cost_per_1k=0.006,  # $0.006/min
            rating=0.90
        ),
        ModelEntry(
            id="whisper/local",
            name="Whisper (Local)",
            provider="local",
            type=ModelType.VOICE,
            capabilities=[Capability.STT],
            context_window=0,
            cost_per_1k=0.0,  # Free
            rating=0.85
        ),
        ModelEntry(
            id="piper/local",
            name="Piper (Local)",
            provider="local",
            type=ModelType.VOICE,
            capabilities=[Capability.TTS],
            context_window=0,
            cost_per_1k=0.0,  # Free
            rating=0.75
        ),
        ModelEntry(
            id="browser/speechsynthesis",
            name="Browser TTS",
            provider="browser",
            type=ModelType.VOICE,
            capabilities=[Capability.TTS],
            context_window=0,
            cost_per_1k=0.0,  # Free
            rating=0.60
        ),
        # === PHASE 80.3: MCP Agents ===
        # External agents with special permissions - can participate in group chats
        ModelEntry(
            id="mcp/claude_code",
            name="Claude Code",
            provider="mcp",
            type=ModelType.MCP_AGENT,
            capabilities=[Capability.CODE, Capability.REASONING, Capability.EXECUTE],
            context_window=200000,  # Claude's context
            cost_per_1k=0.0,  # Via MCP, not billed here
            rating=0.98,
            available=True
        ),
        ModelEntry(
            id="mcp/browser_haiku",
            name="Browser Haiku",
            provider="mcp",
            type=ModelType.MCP_AGENT,
            capabilities=[Capability.TESTING, Capability.CHAT, Capability.VISION],
            context_window=200000,  # Haiku's context
            cost_per_1k=0.0,  # Via browser, not billed here
            rating=0.92,
            available=True
        ),
    ]

    def __init__(self):
        self._models: Dict[str, ModelEntry] = {}
        self._favorites: List[str] = []
        self._recent: List[str] = []
        self._api_keys: Dict[str, str] = {}  # provider -> key
        self._health_check_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()  # ✅ PHASE 56.2: Prevent race conditions

        # Load defaults
        for model in self.DEFAULT_MODELS:
            self._models[model.id] = model

    async def start_health_checks(self, interval: int = 300):
        """Start periodic health checks (every 5 min by default)."""
        self._health_check_task = asyncio.create_task(
            self._health_check_loop(interval)
        )
        logger.info("[ModelRegistry] Health check task started")

    async def stop_health_checks(self):
        """Stop health check task."""
        if self._health_check_task:
            self._health_check_task.cancel()
            logger.info("[ModelRegistry] Health check task stopped")

    async def _health_check_loop(self, interval: int):
        """Periodic health check for all models."""
        while True:
            try:
                await asyncio.sleep(interval)
                await self.check_all_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[ModelRegistry] Health check failed: {e}")

    async def check_all_health(self):
        """Check health of all models in parallel."""
        # ✅ PHASE 56.2: Get snapshot of model IDs under lock
        async with self._lock:
            model_ids = list(self._models.keys())

        # ✅ Run all checks in parallel (not sequentially)
        if model_ids:
            tasks = [self.check_health(mid) for mid in model_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log failures
            for mid, result in zip(model_ids, results):
                if isinstance(result, Exception):
                    logger.debug(f"[ModelRegistry] Health check failed for {mid}: {result}")

    async def check_health(self, model_id: str) -> bool:
        """Check if model is available with proper locking."""
        # ✅ PHASE 56.2: Get model under lock
        async with self._lock:
            model = self._models.get(model_id)
            if not model:
                return False
            # Make a copy to avoid holding lock during I/O
            provider = model.provider
            model_type = model.type

        # Do blocking health check OUTSIDE lock
        is_available = True
        try:
            if provider == "ollama":
                # Ping Ollama
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get("http://localhost:11434/api/tags")
                    if resp.status_code == 200:
                        tags = resp.json().get("models", [])
                        is_available = any(t["name"] == model_id for t in tags)
                    else:
                        is_available = False

            elif provider == "openrouter":
                # Check if we have API key
                is_available = "openrouter" in self._api_keys or model_type == ModelType.CLOUD_FREE

            elif provider == "gemini":
                is_available = "gemini" in self._api_keys

        except Exception as e:
            logger.debug(f"[ModelRegistry] Health check failed for {model_id}: {e}")
            is_available = False

        # ✅ Update atomically with lock
        async with self._lock:
            if model_id in self._models:
                old_model = self._models[model_id]
                # Create new entry with updated fields
                self._models[model_id] = replace(
                    old_model,
                    available=is_available,
                    last_health_check=datetime.now()
                )

        return is_available

    def get_all(self) -> List[dict]:
        """Get all models as list of dicts."""
        return [m.to_dict() for m in self._models.values()]

    def get_by_capability(self, capability: Capability) -> List[ModelEntry]:
        """Get models with specific capability."""
        return [m for m in self._models.values()
                if capability in m.capabilities and m.available]

    def get_available(self) -> List[ModelEntry]:
        """Get all available models."""
        return [m for m in self._models.values() if m.available]

    def get_local(self) -> List[ModelEntry]:
        """Get local (Ollama) models."""
        return [m for m in self._models.values()
                if m.type == ModelType.LOCAL and m.available]

    def get_free(self) -> List[ModelEntry]:
        """Get free cloud models."""
        return [m for m in self._models.values()
                if m.type in [ModelType.LOCAL, ModelType.CLOUD_FREE] and m.available]

    def get_voice(self) -> List[ModelEntry]:
        """Phase 60.5: Get voice (TTS/STT) models."""
        return [m for m in self._models.values()
                if m.type == ModelType.VOICE and m.available]

    def get_tts(self) -> List[ModelEntry]:
        """Phase 60.5: Get TTS-capable models."""
        return [m for m in self._models.values()
                if Capability.TTS in m.capabilities and m.available]

    def get_stt(self) -> List[ModelEntry]:
        """Phase 60.5: Get STT-capable models."""
        return [m for m in self._models.values()
                if Capability.STT in m.capabilities and m.available]

    def get_mcp_agents(self) -> List[ModelEntry]:
        """Phase 80.3: Get MCP agents (Claude Code, Browser Haiku)."""
        return [m for m in self._models.values()
                if m.type == ModelType.MCP_AGENT and m.available]

    def select_best(
        self,
        task_type: str,
        context_size: int = 4096,
        prefer_local: bool = True,
        prefer_free: bool = True
    ) -> Optional[ModelEntry]:
        """
        Auto-select best model for task.

        Args:
            task_type: 'code', 'reasoning', 'chat', etc.
            context_size: Required context window
            prefer_local: Prefer local models (faster, free)
            prefer_free: Prefer free models

        Returns:
            Best matching model or None
        """
        # Map task to capability
        cap_map = {
            'code': Capability.CODE,
            'reasoning': Capability.REASONING,
            'chat': Capability.CHAT,
            'vision': Capability.VISION,
            'embeddings': Capability.EMBEDDINGS
        }
        capability = cap_map.get(task_type.lower(), Capability.CHAT)

        # Filter candidates
        candidates = [
            m for m in self._models.values()
            if m.available
            and capability in m.capabilities
            and m.context_window >= context_size
        ]

        if not candidates:
            logger.warning(f"[ModelRegistry] No model found for {task_type}")
            return None

        # Sort by preference
        def score(m: ModelEntry) -> float:
            s = m.rating
            if prefer_local and m.type == ModelType.LOCAL:
                s += 0.2
            if prefer_free and m.cost_per_1k == 0:
                s += 0.1
            return s

        candidates.sort(key=score, reverse=True)
        return candidates[0]

    def add_api_key(self, provider: str, key: str) -> bool:
        """Add API key for provider."""
        self._api_keys[provider] = key
        logger.info(f"[ModelRegistry] Added API key for {provider}")

        # Enable models for this provider
        for model in self._models.values():
            if model.provider == provider:
                model.available = True

        return True

    def remove_api_key(self, provider: str) -> bool:
        """Remove API key for provider."""
        if provider in self._api_keys:
            del self._api_keys[provider]

            # Disable paid models for this provider
            for model in self._models.values():
                if model.provider == provider and model.type == ModelType.CLOUD_PAID:
                    model.available = False

            return True
        return False

    def add_to_favorites(self, model_id: str):
        """Add model to favorites."""
        if model_id not in self._favorites:
            self._favorites.append(model_id)

    def remove_from_favorites(self, model_id: str):
        """Remove model from favorites."""
        if model_id in self._favorites:
            self._favorites.remove(model_id)

    def get_favorites(self) -> List[dict]:
        """Get favorite models."""
        return [
            self._models[m].to_dict()
            for m in self._favorites
            if m in self._models
        ]

    def track_usage(self, model_id: str):
        """Track model usage for recent list."""
        if model_id in self._recent:
            self._recent.remove(model_id)
        self._recent.insert(0, model_id)
        self._recent = self._recent[:10]  # Keep last 10

    def get_recent(self) -> List[dict]:
        """Get recently used models."""
        return [
            self._models[m].to_dict()
            for m in self._recent
            if m in self._models
        ]

    # === PHASE 60.4: Ollama Auto-Discovery ===

    async def discover_ollama_models(self) -> int:
        """
        Auto-discover all Ollama models and register them.
        Phase 60.4: Dynamically discovers local models instead of hardcoding.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:11434/api/tags")
                if resp.status_code != 200:
                    logger.warning("[ModelRegistry] Ollama not responding")
                    return 0

                models = resp.json().get('models', [])
                registered = 0

                for m in models:
                    model_id = m.get('name', '')
                    if not model_id:
                        continue

                    # Skip if already registered
                    if model_id in self._models:
                        continue

                    # Detect capabilities
                    capabilities = self._detect_capabilities(model_id)

                    # Calculate size in GB
                    size_bytes = m.get('size', 0)
                    size_gb = round(size_bytes / (1024 ** 3), 2)

                    # Create entry
                    entry = ModelEntry(
                        id=model_id,
                        name=self._format_name(model_id),
                        provider="ollama",
                        type=ModelType.LOCAL,
                        available=True,
                        capabilities=capabilities,
                        context_window=8192,  # Default, could be improved with model info
                        rating=0.75,  # Default rating for discovered models
                    )

                    async with self._lock:
                        self._models[model_id] = entry
                    registered += 1
                    logger.info(f"[ModelRegistry] Discovered: {model_id} ({size_gb}GB)")

                return registered

        except Exception as e:
            logger.error(f"[ModelRegistry] Discovery failed: {e}")
            return 0

    def _detect_capabilities(self, model_id: str) -> List[Capability]:
        """Detect model capabilities from name. Phase 60.4."""
        caps = [Capability.CHAT]
        model_lower = model_id.lower()

        if 'coder' in model_lower or 'code' in model_lower:
            caps.append(Capability.CODE)
        if 'vl' in model_lower or 'vision' in model_lower:
            caps.append(Capability.VISION)
        if 'embedding' in model_lower or 'embed' in model_lower:
            caps = [Capability.EMBEDDINGS]  # Only embeddings for embedding models
        if 'instruct' in model_lower or 'reason' in model_lower:
            caps.append(Capability.REASONING)

        return caps

    # === PHASE 60.5: Voice Model Discovery ===

    async def discover_voice_models(self) -> int:
        """
        Phase 60.5: Discover voice models from OpenRouter cache.
        Models with audio input/output are classified as voice.
        """
        try:
            from src.elisya.model_fetcher import get_all_models, classify_model_type

            models = await get_all_models()
            registered = 0

            for m in models:
                # Classify if not already done
                classify_model_type(m)

                # Only process voice models
                if m.get('type') != 'voice':
                    continue

                model_id = m.get('id', '')
                if not model_id or model_id in self._models:
                    continue

                # Map capabilities
                capabilities = []
                for cap in m.get('capabilities', []):
                    if cap == 'stt':
                        capabilities.append(Capability.STT)
                    elif cap == 'tts':
                        capabilities.append(Capability.TTS)
                    elif cap == 'vision':
                        capabilities.append(Capability.VISION)

                # Always add CHAT for models that can do text
                if Capability.STT in capabilities:
                    capabilities.append(Capability.CHAT)

                # Get pricing
                pricing = m.get('pricing', {})
                cost = float(pricing.get('prompt', '0') or '0') * 1000000

                # Create entry
                entry = ModelEntry(
                    id=model_id,
                    name=m.get('name', model_id),
                    provider="openrouter",
                    type=ModelType.VOICE,
                    available=True,
                    capabilities=capabilities,
                    context_window=m.get('context_length', 32000),
                    cost_per_1k=cost,
                    rating=0.85,
                )

                async with self._lock:
                    self._models[model_id] = entry
                registered += 1
                logger.info(f"[ModelRegistry] Voice model: {model_id} ({capabilities})")

            return registered

        except Exception as e:
            logger.error(f"[ModelRegistry] Voice discovery failed: {e}")
            return 0

    def _format_name(self, model_id: str) -> str:
        """Format model ID to display name. Phase 60.4."""
        # llama3.1:8b -> Llama3 1 8b
        # qwen2.5vl:3b -> Qwen2 5vl 3b
        name = model_id.replace(':', ' ').replace('.', ' ').replace('-', ' ')
        parts = name.split()
        formatted = ' '.join(word.capitalize() for word in parts)
        return formatted


# Singleton
_model_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get or create singleton ModelRegistry."""
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry
