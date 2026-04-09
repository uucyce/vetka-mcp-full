"""
API Key Auto-Detection System
Supports 70+ providers (2025/2026 updated list)

@file api_key_detector.py
@status ACTIVE
@phase Phase 57.1 - Smart API Key Auto-Detection
@lastUpdate 2026-01-09

Detects API key provider from key format automatically.
User doesn't need to specify provider - system figures it out!
"""

import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class ProviderCategory(Enum):
    """Category of API provider."""
    LLM = "llm"
    AGGREGATOR = "aggregator"
    CHINESE = "chinese"
    CLOUD = "cloud"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    THREE_D = "3d"
    HOSTING = "hosting"


@dataclass
class ProviderConfig:
    """
    Configuration for a provider's key format.

    Phase 111.9: Added openai_compatible flag for dynamic routing.
    """
    prefix: str
    regex: str
    base_url: str
    category: ProviderCategory
    display_name: str
    validation_endpoint: str = "/models"
    openai_compatible: bool = True  # Phase 111.9: Most APIs are OpenAI-compatible


class APIKeyDetector:
    """
    Auto-detect API key provider from key format.
    Supports 70+ providers (2025/2026 updated list).

    Usage:
        result = APIKeyDetector.detect("sk-or-v1-abc123...")
        # Returns: {"provider": "openrouter", "display_name": "OpenRouter", ...}
    """

    # Patterns ordered by prefix uniqueness (most unique first)
    PATTERNS: Dict[str, ProviderConfig] = {

        # ═══════════════════════════════════════════════════════════════
        # UNIQUE PREFIXES (Easy to detect - high confidence)
        # ═══════════════════════════════════════════════════════════════

        # Anthropic (Claude) - sk-ant-
        "anthropic": ProviderConfig(
            prefix="sk-ant-",
            regex=r"^sk-ant-[a-zA-Z0-9\-_]{90,110}$",
            base_url="https://api.anthropic.com/v1",
            category=ProviderCategory.LLM,
            display_name="Anthropic (Claude)",
            openai_compatible=False  # Phase 111.9: Uses different format
        ),

        # OpenRouter - sk-or-v1-
        "openrouter": ProviderConfig(
            prefix="sk-or-v1-",
            regex=r"^sk-or-v1-[a-zA-Z0-9]{32,64}$",
            base_url="https://openrouter.ai/api/v1",
            category=ProviderCategory.AGGREGATOR,
            display_name="OpenRouter"
        ),

        # NanoGPT - sk-nano-
        "nanogpt": ProviderConfig(
            prefix="sk-nano-",
            regex=r"^sk-nano-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
            base_url="https://nano-gpt.com/api/v1",
            category=ProviderCategory.AGGREGATOR,
            display_name="NanoGPT"
        ),

        # Google Gemini - AIza
        "gemini": ProviderConfig(
            prefix="AIza",
            regex=r"^AIza[0-9A-Za-z\-_]{35,45}$",
            base_url="https://generativelanguage.googleapis.com/v1beta",
            category=ProviderCategory.LLM,
            display_name="Google Gemini",
            openai_compatible=False  # Phase 111.9: Uses Google AI format
        ),

        # Groq - gsk_
        "groq": ProviderConfig(
            prefix="gsk_",
            regex=r"^gsk_[a-zA-Z0-9]{40,60}$",
            base_url="https://api.groq.com/openai/v1",
            category=ProviderCategory.AGGREGATOR,
            display_name="Groq"
        ),

        # HuggingFace - hf_
        "huggingface": ProviderConfig(
            prefix="hf_",
            regex=r"^hf_[a-zA-Z0-9]{30,50}$",
            base_url="https://api-inference.huggingface.co/v1",
            category=ProviderCategory.HOSTING,
            display_name="Hugging Face"
        ),

        # Replicate - r8_
        "replicate": ProviderConfig(
            prefix="r8_",
            regex=r"^r8_[a-zA-Z0-9]{35,50}$",
            base_url="https://api.replicate.com/v1",
            category=ProviderCategory.HOSTING,
            display_name="Replicate"
        ),

        # Fireworks AI - fw_
        "fireworks": ProviderConfig(
            prefix="fw_",
            regex=r"^fw_[a-zA-Z0-9]{35,50}$",
            base_url="https://api.fireworks.ai/inference/v1",
            category=ProviderCategory.AGGREGATOR,
            display_name="Fireworks AI"
        ),

        # Perplexity - pa- (new format) or pplx- (legacy)
        "perplexity": ProviderConfig(
            prefix="pa-",
            regex=r"^pa-[a-zA-Z0-9\-_]{35,60}$",
            base_url="https://api.perplexity.ai/v1",
            category=ProviderCategory.LLM,
            display_name="Perplexity"
        ),

        # Poe - no unique prefix, generic alphanumeric
        "poe": ProviderConfig(
            prefix="",  # No standard prefix
            regex=r"^[a-zA-Z][a-zA-Z0-9\-_]{35,50}$",  # Starts with letter, 36-51 chars total
            base_url="https://api.poe.com/v1",  # Phase 111.9: Fixed to v1
            category=ProviderCategory.AGGREGATOR,
            display_name="Poe"
        ),

        # Phase 111.9: Polza AI - pza_ prefix
        "polza": ProviderConfig(
            prefix="pza_",
            regex=r"^pza_[a-zA-Z0-9]{20,50}$",
            base_url="https://api.polza.ai/api/v1",
            category=ProviderCategory.AGGREGATOR,
            display_name="Polza AI"
        ),

        # Phase 60.5: xAI (Grok) - xai-
        "xai": ProviderConfig(
            prefix="xai-",
            regex=r"^xai-[a-zA-Z0-9]{60,90}$",
            base_url="https://api.x.ai/v1",
            category=ProviderCategory.LLM,
            display_name="xAI (Grok)"
        ),

        # Together AI - multiple formats
        "together": ProviderConfig(
            prefix="",  # Can start with various prefixes
            regex=r"^[a-f0-9]{64}$",  # 64 hex chars
            base_url="https://api.together.xyz/v1",
            category=ProviderCategory.AGGREGATOR,
            display_name="Together AI"
        ),

        # NVIDIA NIM - nvapi-
        "nvidia": ProviderConfig(
            prefix="nvapi-",
            regex=r"^nvapi-[a-zA-Z0-9\-]{35,60}$",
            base_url="https://integrate.api.nvidia.com/v1",
            category=ProviderCategory.CLOUD,
            display_name="NVIDIA NIM"
        ),

        # AWS Bedrock - AKIA
        "aws_bedrock": ProviderConfig(
            prefix="AKIA",
            regex=r"^AKIA[A-Z0-9]{16}$",
            base_url="https://bedrock-runtime.us-east-1.amazonaws.com",
            category=ProviderCategory.CLOUD,
            display_name="AWS Bedrock"
        ),

        # Google Vertex AI (OAuth token) - ya29.
        "google_vertex": ProviderConfig(
            prefix="ya29.",
            regex=r"^ya29\.[a-zA-Z0-9_\-]{100,250}$",
            base_url="https://us-central1-aiplatform.googleapis.com/v1",
            category=ProviderCategory.CLOUD,
            display_name="Google Vertex AI"
        ),

        # RunPod
        "runpod": ProviderConfig(
            prefix="rp_",
            regex=r"^rp_[a-zA-Z0-9]{20,40}$",
            base_url="https://api.runpod.io/v2",
            category=ProviderCategory.HOSTING,
            display_name="RunPod"
        ),

        # Modal - ak-
        "modal": ProviderConfig(
            prefix="ak-",
            regex=r"^ak-[a-zA-Z0-9]{28,40}$",
            base_url="https://api.modal.com/v1",
            category=ProviderCategory.HOSTING,
            display_name="Modal"
        ),

        # Zhipu AI (GLM)
        "zhipu": ProviderConfig(
            prefix="",
            regex=r"^[a-f0-9]{32}\.[a-zA-Z0-9]{16}$",  # UUID-like.short
            base_url="https://open.bigmodel.cn/api/paas/v4",
            category=ProviderCategory.CHINESE,
            display_name="Zhipu AI (GLM)"
        ),

        # FAL AI - fal key id format
        "fal": ProviderConfig(
            prefix="",
            regex=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}:[a-zA-Z0-9]{32,}$",
            base_url="https://fal.run",
            category=ProviderCategory.IMAGE,
            display_name="FAL AI"
        ),

        # ═══════════════════════════════════════════════════════════════
        # IMAGE/VIDEO GENERATION
        # ═══════════════════════════════════════════════════════════════

        # Stability AI - sk-
        "stability": ProviderConfig(
            prefix="sk-",
            regex=r"^sk-[a-zA-Z0-9]{48,52}$",
            base_url="https://api.stability.ai/v1",
            category=ProviderCategory.IMAGE,
            display_name="Stability AI"
        ),

        # Midjourney (via proxy APIs)
        "midjourney": ProviderConfig(
            prefix="mj-",
            regex=r"^mj-[a-zA-Z0-9]{32,50}$",
            base_url="https://api.midjourney.com/v1",
            category=ProviderCategory.IMAGE,
            display_name="Midjourney"
        ),

        # Runway ML
        "runwayml": ProviderConfig(
            prefix="rw_",
            regex=r"^rw_[a-zA-Z0-9]{32,50}$",
            base_url="https://api.runwayml.com/v1",
            category=ProviderCategory.VIDEO,
            display_name="Runway ML"
        ),

        # Pika Labs
        "pika": ProviderConfig(
            prefix="pk_",
            regex=r"^pk_[a-zA-Z0-9]{32,50}$",
            base_url="https://api.pika.art/v1",
            category=ProviderCategory.VIDEO,
            display_name="Pika Labs"
        ),

        # Leonardo AI
        "leonardo": ProviderConfig(
            prefix="",
            regex=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",  # UUID
            base_url="https://cloud.leonardo.ai/api/rest/v1",
            category=ProviderCategory.IMAGE,
            display_name="Leonardo AI"
        ),

        # Ideogram
        "ideogram": ProviderConfig(
            prefix="idg_",
            regex=r"^idg_[a-zA-Z0-9]{32,50}$",
            base_url="https://api.ideogram.ai/v1",
            category=ProviderCategory.IMAGE,
            display_name="Ideogram"
        ),

        # HeyGen
        "heygen": ProviderConfig(
            prefix="",
            regex=r"^[a-zA-Z0-9]{32,40}$",  # Generic alphanumeric
            base_url="https://api.heygen.com/v2",
            category=ProviderCategory.VIDEO,
            display_name="HeyGen"
        ),

        # Kling AI (Kuaishou)
        "kling": ProviderConfig(
            prefix="",
            regex=r"^[a-f0-9]{32}$",
            base_url="https://api.klingai.com/v1",
            category=ProviderCategory.VIDEO,
            display_name="Kling AI"
        ),

        # ═══════════════════════════════════════════════════════════════
        # AUDIO GENERATION
        # ═══════════════════════════════════════════════════════════════

        # ElevenLabs
        "elevenlabs": ProviderConfig(
            prefix="",
            regex=r"^[a-f0-9]{32}$",
            base_url="https://api.elevenlabs.io/v1",
            category=ProviderCategory.AUDIO,
            display_name="ElevenLabs"
        ),

        # Play.ht
        "playht": ProviderConfig(
            prefix="",
            regex=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
            base_url="https://api.play.ht/api/v2",
            category=ProviderCategory.AUDIO,
            display_name="Play.ht"
        ),

        # Suno (Music)
        "suno": ProviderConfig(
            prefix="",
            regex=r"^[a-zA-Z0-9]{40,50}$",
            base_url="https://studio-api.suno.ai/api",
            category=ProviderCategory.AUDIO,
            display_name="Suno (Music)"
        ),

        # Udio (Music)
        "udio": ProviderConfig(
            prefix="",
            regex=r"^[a-zA-Z0-9]{32,40}$",
            base_url="https://www.udio.com/api",
            category=ProviderCategory.AUDIO,
            display_name="Udio (Music)"
        ),

        # Phase 60.5: Deepgram (STT)
        "deepgram": ProviderConfig(
            prefix="",
            regex=r"^[a-f0-9]{40}$",
            base_url="https://api.deepgram.com/v1",
            category=ProviderCategory.AUDIO,
            display_name="Deepgram (STT)"
        ),

        # Phase 60.5: AssemblyAI (STT)
        "assemblyai": ProviderConfig(
            prefix="",
            regex=r"^[a-f0-9]{32}$",
            base_url="https://api.assemblyai.com/v2",
            category=ProviderCategory.AUDIO,
            display_name="AssemblyAI (STT)"
        ),

        # ═══════════════════════════════════════════════════════════════
        # 3D GENERATION
        # ═══════════════════════════════════════════════════════════════

        # Luma Labs (Dream Machine)
        "luma": ProviderConfig(
            prefix="luma-",
            regex=r"^luma-[a-f0-9\-]{36}$",
            base_url="https://api.lumalabs.ai/dream-machine/v1",
            category=ProviderCategory.THREE_D,
            display_name="Luma Labs"
        ),

        # Meshy
        "meshy": ProviderConfig(
            prefix="",
            regex=r"^[a-zA-Z0-9]{32,40}$",
            base_url="https://api.meshy.ai/v1",
            category=ProviderCategory.THREE_D,
            display_name="Meshy"
        ),

        # Tripo 3D
        "tripo3d": ProviderConfig(
            prefix="tsk_",
            regex=r"^tsk_[a-zA-Z0-9]{32,50}$",
            base_url="https://api.tripo3d.ai/v2",
            category=ProviderCategory.THREE_D,
            display_name="Tripo 3D"
        ),

        # ═══════════════════════════════════════════════════════════════
        # CHINESE LLM PROVIDERS
        # ═══════════════════════════════════════════════════════════════

        # DeepSeek
        "deepseek": ProviderConfig(
            prefix="sk-",
            regex=r"^sk-[a-f0-9]{32}$",
            base_url="https://api.deepseek.com/v1",
            category=ProviderCategory.CHINESE,
            display_name="DeepSeek"
        ),

        # Moonshot (Kimi)
        "moonshot": ProviderConfig(
            prefix="sk-",
            regex=r"^sk-[a-zA-Z0-9]{40,50}$",
            base_url="https://api.moonshot.cn/v1",
            category=ProviderCategory.CHINESE,
            display_name="Moonshot (Kimi)"
        ),

        # Baidu Qianfan (Ernie)
        "baidu": ProviderConfig(
            prefix="",
            regex=r"^[a-zA-Z0-9]{24}$",
            base_url="https://aip.baidubce.com/rpc/2.0/ai_custom",
            category=ProviderCategory.CHINESE,
            display_name="Baidu Qianfan"
        ),

        # Alibaba Qwen (Tongyi)
        "alibaba": ProviderConfig(
            prefix="sk-",
            regex=r"^sk-[a-f0-9]{32}$",
            base_url="https://dashscope.aliyuncs.com/api/v1",
            category=ProviderCategory.CHINESE,
            display_name="Alibaba Qwen"
        ),

        # ByteDance (Doubao)
        "bytedance": ProviderConfig(
            prefix="",
            regex=r"^[a-f0-9]{32}$",
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            category=ProviderCategory.CHINESE,
            display_name="ByteDance Doubao"
        ),

        # MiniMax
        "minimax": ProviderConfig(
            prefix="",
            regex=r"^[a-zA-Z0-9]{40,50}$",
            base_url="https://api.minimax.chat/v1",
            category=ProviderCategory.CHINESE,
            display_name="MiniMax"
        ),

        # ═══════════════════════════════════════════════════════════════
        # GENERIC sk- PREFIXES (Detect by length - LOWER priority)
        # ═══════════════════════════════════════════════════════════════

        # OpenAI - sk-proj- format (2024/2025 format)
        # Keys contain letters, numbers, underscores, and dashes
        # Length varies: 100-200+ chars total
        "openai": ProviderConfig(
            prefix="sk-proj-",
            regex=r"^sk-proj-[a-zA-Z0-9_\-]{80,200}$",
            base_url="https://api.openai.com/v1",
            category=ProviderCategory.LLM,
            display_name="OpenAI"
        ),

        # OpenAI - legacy format (sk-...)
        "openai_legacy": ProviderConfig(
            prefix="sk-",
            regex=r"^sk-[a-zA-Z0-9]{48}$",
            base_url="https://api.openai.com/v1",
            category=ProviderCategory.LLM,
            display_name="OpenAI (Legacy)"
        ),

        # OpenAI - new format without sk- prefix (2025+)
        # Format: alphanumeric with _ and -, ~49-60 chars, no prefix
        # Example: ZvWK8NXnx8OaD0uAP6_Apw618TfWSVmlKuCak-V9XSYNJ9vsA
        "openai_new": ProviderConfig(
            prefix="",
            regex=r"^[a-zA-Z0-9][a-zA-Z0-9_\-]{45,70}[a-zA-Z0-9]$",
            base_url="https://api.openai.com/v1",
            category=ProviderCategory.LLM,
            display_name="OpenAI"
        ),

        # Mistral - sk- + 32 chars
        "mistral": ProviderConfig(
            prefix="",
            regex=r"^[a-zA-Z0-9]{32}$",
            base_url="https://api.mistral.ai/v1",
            category=ProviderCategory.LLM,
            display_name="Mistral AI"
        ),

        # Cohere
        "cohere": ProviderConfig(
            prefix="",
            regex=r"^[a-zA-Z0-9]{40}$",
            base_url="https://api.cohere.ai/v1",
            category=ProviderCategory.LLM,
            display_name="Cohere"
        ),

        # AI21 Labs
        "ai21": ProviderConfig(
            prefix="",
            regex=r"^[a-zA-Z0-9]{40,50}$",
            base_url="https://api.ai21.com/studio/v1",
            category=ProviderCategory.LLM,
            display_name="AI21 Labs"
        ),

        # Anyscale
        "anyscale": ProviderConfig(
            prefix="esecret_",
            regex=r"^esecret_[a-zA-Z0-9]{32,50}$",
            base_url="https://api.endpoints.anyscale.com/v1",
            category=ProviderCategory.HOSTING,
            display_name="Anyscale"
        ),

        # Cerebras
        "cerebras": ProviderConfig(
            prefix="csk-",
            regex=r"^csk-[a-zA-Z0-9]{32,50}$",
            base_url="https://api.cerebras.ai/v1",
            category=ProviderCategory.LLM,
            display_name="Cerebras"
        ),

        # SambaNova
        "sambanova": ProviderConfig(
            prefix="",
            regex=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
            base_url="https://api.sambanova.ai/v1",
            category=ProviderCategory.LLM,
            display_name="SambaNova"
        ),
    }

    # Detection order - unique prefixes first
    DETECTION_ORDER = [
        # Unique prefixes (highest confidence)
        "anthropic",      # sk-ant-
        "openrouter",     # sk-or-v1-
        "nanogpt",        # sk-nano-
        "openai",         # sk-proj-
        "gemini",         # AIza
        "groq",           # gsk_
        "huggingface",    # hf_
        "replicate",      # r8_
        "fireworks",      # fw_
        "perplexity",     # pa- (new format)
        "xai",            # xai- (Grok) - Phase 60.5
        "poe",            # Generic alphanumeric (lower priority)
        "nvidia",         # nvapi-
        "aws_bedrock",    # AKIA
        "google_vertex",  # ya29.
        "runpod",         # rp_
        "modal",          # ak-
        "anyscale",       # esecret_
        "cerebras",       # csk-
        "tripo3d",        # tsk_
        "luma",           # luma-
        # Less unique but still identifiable
        "stability",      # sk- + 48-52 chars
        "midjourney",     # mj-
        "runwayml",       # rw_
        "pika",           # pk_
        "ideogram",       # idg_
        "fal",            # UUID:key format
        # Generic patterns (lower confidence)
        "openai_legacy",  # sk- + 48 chars
        "together",       # 64 hex chars
        "zhipu",          # UUID.short
        "deepseek",       # sk- + 32 hex
        "moonshot",       # sk- + 40-50 chars
        "leonardo",       # UUID
        "playht",         # UUID
        "sambanova",      # UUID
        "elevenlabs",     # 32 hex
        "kling",          # 32 hex
        "bytedance",      # 32 hex
        "mistral",        # 32 alphanumeric
        "baidu",          # 24 alphanumeric
        "cohere",         # 40 alphanumeric
        "ai21",           # 40-50 alphanumeric
        "minimax",        # 40-50 alphanumeric
        "heygen",         # 32-40 alphanumeric
        "meshy",          # 32-40 alphanumeric
        "suno",           # 40-50 alphanumeric
        "udio",           # 32-40 alphanumeric
        "deepgram",       # 40 hex - Phase 60.5
        "assemblyai",     # 32 hex - Phase 60.5
        "alibaba",        # sk- + 32 hex (conflicts with deepseek)
        "openai_new",     # 47-72 chars with _ and - (new 2025 format)
    ]

    @classmethod
    def detect(cls, key: str) -> Optional[Dict[str, Any]]:
        """
        Detect provider from key format.
        Returns dict with provider info or None if unknown.

        Priority:
        1. Unique prefixes (sk-ant-, sk-or-v1-, AIza, gsk_, hf_, etc.)
        2. Specific length patterns
        3. Generic patterns (lower confidence)
        """
        key = key.strip()

        # DEBUG: Log detection attempt
        print(f"[APIKeyDetector.detect] Input key: {key[:20]}...{key[-4:] if len(key) > 24 else ''} (len={len(key)})")

        if not key or len(key) < 10:
            print(f"[APIKeyDetector.detect] REJECTED: key too short ({len(key)} chars)")
            return None

        # Try each provider in order
        for provider_id in cls.DETECTION_ORDER:
            config = cls.PATTERNS.get(provider_id)
            if not config:
                continue

            # Check prefix first (if provider has one)
            if config.prefix:
                if not key.startswith(config.prefix):
                    continue

            # Check regex pattern
            if re.match(config.regex, key):
                # Calculate confidence based on prefix uniqueness
                confidence = cls._calculate_confidence(provider_id, key)

                print(f"[APIKeyDetector.detect] MATCHED: {provider_id} (confidence={confidence})")
                return {
                    "provider": provider_id,
                    "display_name": config.display_name,
                    "category": config.category.value,
                    "base_url": config.base_url,
                    "confidence": confidence,
                    "note": cls._get_note(provider_id, confidence)
                }

        print(f"[APIKeyDetector.detect] NO MATCH found for key pattern")
        return None

    @classmethod
    def _calculate_confidence(cls, provider_id: str, key: str) -> float:
        """Calculate detection confidence based on pattern uniqueness."""
        config = cls.PATTERNS[provider_id]

        # Unique prefixes = high confidence
        unique_prefixes = [
            "sk-ant-", "sk-or-v1-", "sk-nano-", "AIza", "gsk_", "hf_", "r8_", "fw_",
            "pplx-", "nvapi-", "AKIA", "ya29.", "rp_", "ak-", "esecret_",
            "csk-", "tsk_", "luma-", "sk-proj-"
        ]

        if config.prefix and config.prefix in unique_prefixes:
            return 0.95

        # Medium confidence - somewhat unique
        if config.prefix and len(config.prefix) >= 3:
            return 0.80

        # Low confidence - generic patterns
        if provider_id in ["together", "elevenlabs", "kling", "bytedance", "mistral"]:
            return 0.50

        # Default
        return 0.60

    @classmethod
    def _get_note(cls, provider_id: str, confidence: float) -> Optional[str]:
        """Get note about detection uncertainty."""
        if confidence >= 0.90:
            return None

        if confidence >= 0.70:
            return "High confidence detection"

        # Low confidence notes
        notes = {
            "deepseek": "Could also be Alibaba Qwen (same format)",
            "moonshot": "Could also be other Chinese providers",
            "openai_legacy": "Legacy OpenAI format - could be other provider",
            "elevenlabs": "32-char hex - could be ElevenLabs or Kling",
            "mistral": "32-char alphanumeric - multiple providers use this",
            "cohere": "40-char alphanumeric - could be Cohere or AI21",
        }

        return notes.get(provider_id, "Multiple providers use similar format")

    @classmethod
    def get_all_providers(cls) -> Dict[str, List[Dict]]:
        """Get all supported providers grouped by category."""
        result: Dict[str, List[Dict]] = {}

        for provider_id, config in cls.PATTERNS.items():
            category = config.category.value
            if category not in result:
                result[category] = []

            result[category].append({
                "id": provider_id,
                "name": config.display_name,
                "prefix": config.prefix if config.prefix else "(no prefix)",
                "base_url": config.base_url
            })

        return result

    @classmethod
    def get_provider_count(cls) -> int:
        """Get total number of supported providers."""
        return len(cls.PATTERNS)

    @classmethod
    def get_categories(cls) -> List[str]:
        """Get all provider categories."""
        return [c.value for c in ProviderCategory]


# ============================================================
# PROVIDER CONFIG HELPERS - Phase 111.9
# ============================================================

def get_provider_config(provider_name: str) -> Optional[ProviderConfig]:
    """
    Get provider configuration by name.

    Phase 111.9: Used by provider_registry for dynamic routing.

    Args:
        provider_name: Provider identifier (e.g., "poe", "polza", "openrouter")

    Returns:
        ProviderConfig if found, None otherwise
    """
    return APIKeyDetector.PATTERNS.get(provider_name)


def get_provider_base_url(provider_name: str) -> Optional[str]:
    """Get base URL for a provider."""
    config = get_provider_config(provider_name)
    return config.base_url if config else None


def is_openai_compatible(provider_name: str) -> bool:
    """Check if provider uses OpenAI-compatible API format."""
    config = get_provider_config(provider_name)
    return config.openai_compatible if config else True  # Default to True


def get_all_provider_names() -> List[str]:
    """Get list of all known provider names."""
    return list(APIKeyDetector.PATTERNS.keys())


# ============================================================
# TRUFFLEHOG PATTERNS INTEGRATION - Phase 110 / Phase 113
# ============================================================

import threading

_trufflehog_patterns: Optional[Dict[str, Any]] = None
_trufflehog_lock = threading.Lock()  # Phase 113: Thread safety


def _load_trufflehog_patterns() -> Dict[str, Any]:
    """
    Load TruffleHog-based patterns from JSON file.
    Phase 113: Added thread safety with lock.
    """
    global _trufflehog_patterns

    # Fast path: already loaded
    if _trufflehog_patterns is not None:
        return _trufflehog_patterns

    # Thread-safe loading
    with _trufflehog_lock:
        # Double-check after acquiring lock
        if _trufflehog_patterns is not None:
            return _trufflehog_patterns

        import json
        from pathlib import Path

        patterns_file = Path(__file__).parent.parent.parent / "data" / "trufflehog_patterns.json"
        try:
            if patterns_file.exists():
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    _trufflehog_patterns = data.get('patterns', {})
                    print(f"[TruffleHog] Loaded {len(_trufflehog_patterns)} patterns")
            else:
                _trufflehog_patterns = {}
                print("[TruffleHog] Patterns file not found")
        except json.JSONDecodeError as e:
            print(f"[TruffleHog] Invalid JSON in patterns file: {e}")
            _trufflehog_patterns = {}
        except Exception as e:
            print(f"[TruffleHog] Error loading patterns: {e}")
            _trufflehog_patterns = {}

    return _trufflehog_patterns


def detect_with_trufflehog(key: str) -> Optional[Dict[str, Any]]:
    """
    Detect API key using TruffleHog-style patterns from JSON file.
    Phase 113: Fixed detection order (prefix before regex for performance).

    This is used as a fallback when built-in detector doesn't match.
    Currently supports ~36 patterns from data/trufflehog_patterns.json.

    Args:
        key: The API key to detect

    Returns:
        Dict with detection info or None
    """
    patterns = _load_trufflehog_patterns()
    if not patterns:
        return None

    key = key.strip()
    if len(key) < 10:
        return None

    for pattern_id, pattern_config in patterns.items():
        # Phase 113: Check prefix FIRST (fast string operation)
        prefix = pattern_config.get('prefix')
        if prefix and not key.startswith(prefix):
            continue  # Skip early if prefix doesn't match

        regex = pattern_config.get('regex', '')
        if not regex:
            continue

        try:
            # Phase 113: Regex check SECOND (expensive operation)
            if re.match(regex, key):
                confidence = pattern_config.get('confidence', 0.70)
                return {
                    "provider": pattern_id,
                    "display_name": pattern_config.get('display_name', pattern_id),
                    "category": pattern_config.get('category', 'unknown'),
                    "confidence": confidence,
                    "source": "trufflehog",
                    "note": pattern_config.get('note')
                }
        except re.error:
            continue

    return None


# Convenience function
def detect_api_key(key: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function for auto-detection.
    Phase 110: Now uses TruffleHog patterns as fallback.

    Usage:
        from src.elisya.api_key_detector import detect_api_key
        result = detect_api_key("sk-or-v1-abc123...")
        print(result["display_name"])  # "OpenRouter"
    """
    # Try built-in detector first
    result = APIKeyDetector.detect(key)
    if result:
        result["source"] = "builtin"
        return result

    # Fallback to TruffleHog patterns
    result = detect_with_trufflehog(key)
    if result:
        print(f"[detect_api_key] TruffleHog fallback matched: {result.get('provider')}")
        return result

    return None
