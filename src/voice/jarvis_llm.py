"""
VETKA Phase 104.6 - Jarvis LLM Integration

Fast local LLM for voice responses with VETKA memory integration.
Supports Ollama (qwen2.5:3b, phi3:mini, mistral) for low-latency responses.

@file jarvis_llm.py
@status active
@phase 104.6
@depends aiohttp, logging
@used_by jarvis_handler.py

Grok Recommendations Applied:
- Use quantized models (qwen2.5:3b-q4_0) for speed
- Limit tokens (num_predict: 100) for voice responses
- Lower context window (num_ctx: 2048) for faster processing
- Streaming for perceived latency reduction
"""

import logging
import aiohttp
import json
from typing import Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Ollama Configuration (from Grok recommendations)
OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5vl:3b"  # Fast, good quality for voice (available locally)

# Optimized parameters for voice (short, fast responses)
VOICE_OPTIONS = {
    "num_predict": 150,      # Limit tokens for short responses
    "temperature": 0.7,       # Natural but focused
    "top_p": 0.9,
    "repeat_penalty": 1.1,
    "num_ctx": 2048,          # Smaller context = faster
}


@dataclass
class JarvisLLMConfig:
    """Configuration for Jarvis LLM"""
    model: str = DEFAULT_MODEL
    base_url: str = OLLAMA_BASE_URL
    timeout: float = 30.0
    max_tokens: int = 150
    temperature: float = 0.7
    streaming: bool = True


class JarvisLLM:
    """
    Fast LLM for Jarvis voice responses.

    Uses Ollama with optimized settings for low-latency voice interaction.
    Integrates with VETKA memory systems via JARVISPromptEnricher.

    Usage:
        llm = JarvisLLM()
        response = await llm.generate("Hello, how are you?", user_id="danila")

        # Or with streaming:
        async for chunk in llm.generate_stream("Tell me about VETKA"):
            print(chunk, end="")
    """

    def __init__(self, config: Optional[JarvisLLMConfig] = None):
        self.config = config or JarvisLLMConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        self._enricher = None  # Lazy load

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _get_enricher(self):
        """Lazy load JARVISPromptEnricher"""
        # FIX_104.7: Engram now uses integer IDs for Qdrant REST API
        if self._enricher is None:
            try:
                from src.memory.jarvis_prompt_enricher import get_jarvis_enricher
                self._enricher = get_jarvis_enricher()
                logger.info("[JarvisLLM] JARVISPromptEnricher loaded")
            except ImportError as e:
                logger.warning(f"[JarvisLLM] Could not load enricher: {e}")
                self._enricher = False  # Mark as unavailable
        return self._enricher if self._enricher else None

    def _build_system_prompt(self, user_id: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Build system prompt for Jarvis voice assistant.

        Includes user preferences from VETKA memory if available.
        """
        base_system = f"""You are JARVIS, a voice AI assistant for VETKA - a 3D knowledge management system.

Your personality:
- Concise and helpful (voice responses should be SHORT, 1-3 sentences max)
- Professional but friendly
- You speak naturally, as if in a conversation
- You can understand both Russian and English

Current user: {user_id}

Important: Keep responses SHORT and conversational - this is a voice interface, not a chat.
Avoid bullet points, code blocks, or long explanations unless explicitly asked."""

        # Add context from memory if available
        if context:
            stm_context = context.get("stm_context", "")
            if stm_context:
                base_system += f"\n\nRecent conversation context:\n{stm_context}"

            current_focus = context.get("current_focus")
            if current_focus:
                base_system += f"\n\nUser is currently working on: {current_focus}"

        return base_system

    def _enrich_prompt(self, prompt: str, user_id: str) -> str:
        """Enrich prompt with user preferences from VETKA memory"""
        # FIX_104.7: Re-enabled after Engram integer ID fix
        enricher = self._get_enricher()
        if enricher:
            try:
                return enricher.enrich_prompt(
                    base_prompt=prompt,
                    user_id=user_id,
                    model="qwen"
                )
            except Exception as e:
                logger.warning(f"[JarvisLLM] Enrichment failed: {e}")
        return prompt

    async def check_ollama(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.config.base_url}/api/tags") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]

                    # Check if our model exists
                    model_base = self.config.model.split(":")[0]
                    has_model = any(model_base in m for m in models)

                    if has_model:
                        logger.info(f"[JarvisLLM] Ollama ready with {self.config.model}")
                        return True
                    else:
                        logger.warning(f"[JarvisLLM] Model {self.config.model} not found. Available: {models}")
                        return False
        except Exception as e:
            logger.error(f"[JarvisLLM] Ollama check failed: {e}")
            return False
        return False

    async def generate(
        self,
        transcript: str,
        user_id: str = "default_user",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a response for the given transcript.

        Args:
            transcript: User's speech transcript
            user_id: User identifier for memory lookup
            context: Optional additional context (STM, focus areas, etc.)

        Returns:
            Generated response text
        """
        # Build prompts
        system_prompt = self._build_system_prompt(user_id, context)
        user_prompt = self._enrich_prompt(transcript, user_id)

        # Prepare Ollama request
        payload = {
            "model": self.config.model,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "num_predict": self.config.max_tokens,
                "temperature": self.config.temperature,
                "top_p": VOICE_OPTIONS["top_p"],
                "repeat_penalty": VOICE_OPTIONS["repeat_penalty"],
                "num_ctx": VOICE_OPTIONS["num_ctx"],
            }
        }

        try:
            session = await self._get_session()
            logger.info(f"[JarvisLLM] Generating response for: {transcript[:50]}...")

            async with session.post(
                f"{self.config.base_url}/api/generate",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response = data.get("response", "").strip()

                    # Log stats
                    eval_duration = data.get("eval_duration", 0) / 1e9  # ns to s
                    logger.info(f"[JarvisLLM] Response generated in {eval_duration:.2f}s: {response[:50]}...")

                    return response
                else:
                    error = await resp.text()
                    logger.error(f"[JarvisLLM] Ollama error {resp.status}: {error}")
                    return "I'm having trouble processing that. Could you try again?"

        except aiohttp.ClientError as e:
            logger.error(f"[JarvisLLM] Connection error: {e}")
            return "I couldn't connect to my language model. Please check if Ollama is running."
        except Exception as e:
            logger.error(f"[JarvisLLM] Unexpected error: {e}")
            return "Something went wrong. Let me try again."

    async def generate_stream(
        self,
        transcript: str,
        user_id: str = "default_user",
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate response with streaming (for perceived lower latency).

        Yields chunks as they're generated.

        Args:
            transcript: User's speech transcript
            user_id: User identifier
            context: Optional context

        Yields:
            Response text chunks
        """
        system_prompt = self._build_system_prompt(user_id, context)
        user_prompt = self._enrich_prompt(transcript, user_id)

        payload = {
            "model": self.config.model,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": True,
            "options": {
                "num_predict": self.config.max_tokens,
                "temperature": self.config.temperature,
                "top_p": VOICE_OPTIONS["top_p"],
                "repeat_penalty": VOICE_OPTIONS["repeat_penalty"],
                "num_ctx": VOICE_OPTIONS["num_ctx"],
            }
        }

        try:
            session = await self._get_session()
            logger.info(f"[JarvisLLM] Streaming response for: {transcript[:50]}...")

            async with session.post(
                f"{self.config.base_url}/api/generate",
                json=payload
            ) as resp:
                if resp.status == 200:
                    async for line in resp.content:
                        if line:
                            try:
                                data = json.loads(line)
                                chunk = data.get("response", "")
                                if chunk:
                                    yield chunk
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
                else:
                    error = await resp.text()
                    logger.error(f"[JarvisLLM] Stream error {resp.status}: {error}")
                    yield "I'm having trouble processing that."

        except Exception as e:
            logger.error(f"[JarvisLLM] Stream error: {e}")
            yield "Something went wrong."


# === Context Building Helpers ===

async def get_jarvis_context(user_id: str, transcript: str) -> Dict[str, Any]:
    """
    Build context from VETKA memory systems for Jarvis.

    Lightweight version - only uses STM to avoid Qdrant spam.

    Args:
        user_id: User identifier
        transcript: Current transcript (for semantic search)

    Returns:
        Context dict for LLM prompt
    """
    context = {}

    # STM Buffer (recent conversation) - this is the main context source
    try:
        from src.memory.stm_buffer import get_stm_buffer
        stm = get_stm_buffer()
        stm_entries = stm.get_context(max_items=5)
        if stm_entries:
            stm_text = "\n".join([
                f"[{e.source}] {e.content}"
                for e in stm_entries
            ])
            context["stm_context"] = stm_text
            logger.debug(f"[JarvisContext] STM context: {len(stm_entries)} entries")
    except Exception as e:
        logger.warning(f"[JarvisContext] STM unavailable: {e}")

    # NOTE: Engram/Qdrant disabled for now - causes 400 Bad Request spam
    # TODO: Fix Engram vector format issue, then re-enable
    # User preferences can be added back once Qdrant issue is resolved

    return context


# === Singleton Instance ===

_jarvis_llm: Optional[JarvisLLM] = None


def get_jarvis_llm(config: Optional[JarvisLLMConfig] = None) -> JarvisLLM:
    """Get or create Jarvis LLM singleton"""
    global _jarvis_llm
    if _jarvis_llm is None:
        _jarvis_llm = JarvisLLM(config)
        logger.info("[JarvisLLM] Instance created")
    return _jarvis_llm


async def jarvis_respond(
    transcript: str,
    user_id: str = "default_user"
) -> str:
    """
    Convenience function for quick Jarvis response.

    Args:
        transcript: User's speech
        user_id: User identifier

    Returns:
        Generated response
    """
    llm = get_jarvis_llm()
    context = await get_jarvis_context(user_id, transcript)
    return await llm.generate(transcript, user_id, context)
