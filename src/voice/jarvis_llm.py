"""
VETKA Phase 104.6 - Jarvis LLM Integration

Fast local LLM for voice responses with VETKA memory integration.
Supports Ollama (qwen2.5:3b, phi3:mini, mistral) for low-latency responses.

@file jarvis_llm.py
@status active
@phase 105
@depends aiohttp, logging, asyncio
@used_by jarvis_handler.py

MARKER_105_OLLAMA_TIMEOUT_FIX

Grok Recommendations Applied:
- Use quantized models (qwen2.5:3b-q4_0) for speed
- Limit tokens (num_predict: 100) for voice responses
- Lower context window (num_ctx: 2048) for faster processing
- Streaming for perceived latency reduction
- CRITICAL: asyncio.wait_for() timeout to prevent server hangs
"""

import logging
import aiohttp
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any, AsyncGenerator, List, Tuple
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

_FAVORITES_PATH = Path("data/favorites.json")
def _read_favorite_models() -> List[str]:
    """Load favorite model IDs from shared favorites storage."""
    if not _FAVORITES_PATH.exists():
        return []
    try:
        payload = json.loads(_FAVORITES_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"[JarvisLLM] Could not read favorites: {exc}")
        return []
    models = payload.get("models", [])
    if not isinstance(models, list):
        return []
    return [str(m).strip() for m in models if str(m).strip()]


def _route_for_model(model_id: str) -> str:
    return "provider_registry" if "/" in model_id else "ollama"


def _build_session_summary(stm_entries: List[Any]) -> str:
    """
    Phase 157.5.2: compact session summary for voice turns.
    Uses ELISION compression when available, falls back to truncation.
    """
    if not stm_entries:
        return ""
    raw_lines: List[str] = []
    for entry in stm_entries[-8:]:
        content = getattr(entry, "content", "")
        source = getattr(entry, "source", "mem")
        if content:
            raw_lines.append(f"[{source}] {str(content).strip()[:240]}")
    raw_text = "\n".join(raw_lines).strip()
    if not raw_text:
        return ""
    try:
        from src.memory.elision import compress_context
        compressed = compress_context({"session": raw_text}, level=2)
        return str(compressed)[:900]
    except Exception:
        return raw_text[:900]


def _build_voice_state_key_query(transcript: str, context: Dict[str, Any]) -> str:
    """
    MARKER_157_7_2_VOICE_STATE_KEY_RETRIEVAL.V1
    Build MYCO-style state-key enriched retrieval query for Jarvis voice.
    """
    parts = [
        str(transcript or "").strip(),
        str(context.get("nav_level") or context.get("navLevel") or "").strip(),
        str(context.get("task_drill_state") or context.get("taskDrillState") or "").strip(),
        str(context.get("roadmap_node_drill_state") or context.get("roadmapNodeDrillState") or "").strip(),
        str(context.get("node_kind") or context.get("nodeKind") or "").strip(),
        str(context.get("role") or "").strip(),
        str(context.get("active_task_id") or context.get("activeTaskId") or "").strip(),
    ]
    return " ".join([p for p in parts if p]).strip()


def resolve_jarvis_text_model(
    default_model: str = DEFAULT_MODEL,
    preferred_model: Optional[str] = None,
    favorites: Optional[List[str]] = None,
    registry: Optional[Any] = None,
) -> Tuple[str, str, str]:
    """
    Resolve text model for Jarvis:
    preferred -> favorites -> free cloud(phonebook) -> local fallback -> default.
    """
    if preferred_model:
        model_id = str(preferred_model).strip()
        if model_id:
            return model_id, _route_for_model(model_id), "preferred"

    if registry is None:
        try:
            from src.services.model_registry import get_model_registry
            registry = get_model_registry()
        except Exception:
            registry = None

    if favorites is None:
        favorites = _read_favorite_models()

    if favorites:
        by_id: Dict[str, Dict[str, Any]] = {}
        if registry is not None:
            try:
                by_id = {m.get("id", ""): m for m in registry.get_all()}
            except Exception:
                by_id = {}

        for model_id in favorites:
            model_meta = by_id.get(model_id)
            if model_meta and model_meta.get("type") == "voice":
                continue
            return model_id, _route_for_model(model_id), "favorite"

    if registry is not None:
        try:
            free_cloud = [
                m for m in registry.get_free()
                if getattr(getattr(m, "type", None), "value", "") == "cloud_free"
            ]
            if free_cloud:
                free_cloud.sort(key=lambda m: float(getattr(m, "rating", 0.0)), reverse=True)
                return free_cloud[0].id, "provider_registry", "free_cloud"
        except Exception as exc:
            logger.debug(f"[JarvisLLM] free cloud resolve skipped: {exc}")

        try:
            local_models = registry.get_local()
            if local_models:
                local_models.sort(key=lambda m: float(getattr(m, "rating", 0.0)), reverse=True)
                return local_models[0].id, "ollama", "local_fallback"
        except Exception as exc:
            logger.debug(f"[JarvisLLM] local fallback resolve skipped: {exc}")

    return default_model, _route_for_model(default_model), "default"


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
        base_system = f"""You are VETKA, a voice AI assistant for the VETKA 3D knowledge management system.

Your personality:
- Concise and helpful (voice responses should be SHORT, 1-3 sentences max)
- Professional but friendly
- You speak naturally, as if in a conversation
- You can understand both Russian and English

Current user: {user_id}

Important: Keep responses SHORT and conversational - this is a voice interface, not a chat.
Avoid bullet points, code blocks, or long explanations unless explicitly asked."""
        base_system += "\nIdentity policy: refer to yourself as VETKA (never Jarvis in user-facing text)."

        # Add context from memory if available
        if context:
            stm_context = context.get("stm_context", "")
            if stm_context:
                base_system += f"\n\nRecent conversation context:\n{stm_context}"

            current_focus = context.get("current_focus")
            if current_focus:
                base_system += f"\n\nUser is currently working on: {current_focus}"

            cam_context = context.get("cam_context")
            if isinstance(cam_context, dict):
                cam_line = ", ".join(
                    f"{k}={cam_context.get(k)}"
                    for k in ("overall_surprise", "compression_level", "high_surprise_ratio")
                    if cam_context.get(k) is not None
                )
                if cam_line:
                    base_system += f"\n\nCAM context: {cam_line}"

            json_context = str(context.get("json_context") or "").strip()
            if json_context:
                base_system += f"\n\nStructured runtime context (ELISION):\n{json_context}"

            pinned_context = str(context.get("pinned_context") or "").strip()
            if pinned_context:
                base_system += f"\n\nPinned context:\n{pinned_context}"

            viewport_summary = str(context.get("viewport_summary") or "").strip()
            if viewport_summary:
                base_system += f"\n\nViewport summary:\n{viewport_summary}"

            jepa_context = str(context.get("jepa_context") or "").strip()
            if jepa_context:
                base_system += f"\n\n{jepa_context}"

            pinned_files = context.get("pinned_files")
            if isinstance(pinned_files, list) and pinned_files:
                pinned_preview = []
                for item in pinned_files[:8]:
                    if isinstance(item, dict):
                        pinned_preview.append(item.get("path") or item.get("name") or str(item))
                    else:
                        pinned_preview.append(str(item))
                base_system += "\n\nPinned files:\n- " + "\n- ".join(pinned_preview)

            open_chat_context = context.get("open_chat_context")
            if isinstance(open_chat_context, dict):
                chat_id = open_chat_context.get("chat_id")
                messages = open_chat_context.get("messages", [])
                lines = []
                for msg in messages[-6:]:
                    if not isinstance(msg, dict):
                        continue
                    role = str(msg.get("role", "unknown"))
                    content = str(msg.get("content", "")).strip()
                    if content:
                        lines.append(f"{role}: {content[:180]}")
                if chat_id or lines:
                    section = f"chat_id={chat_id}\n" if chat_id else ""
                    section += "\n".join(lines)
                    base_system += f"\n\nOpen chat context:\n{section}"

            prefers_russian = context.get("prefers_russian")
            if prefers_russian is True:
                base_system += "\n\nLanguage policy: Always answer in Russian unless user explicitly asks for another language."
            elif prefers_russian is False:
                base_system += "\n\nLanguage policy: Always answer in English unless user explicitly asks for another language."
            else:
                preferred_language = str(context.get("preferred_language") or "").strip().lower()
                if preferred_language in {"ru", "en"}:
                    base_system += f"\n\nLanguage policy: Prefer {preferred_language} unless user explicitly requests another language."

            last_assistant_language = str(context.get("last_assistant_language") or "").strip().lower()
            if last_assistant_language in {"ru", "en"}:
                base_system += f"\n\nRecent assistant language: {last_assistant_language}."

            session_summary = str(context.get("session_summary") or "").strip()
            if session_summary:
                base_system += f"\n\nSession summary (compressed):\n{session_summary}"

            hidden_retrieval = context.get("hidden_retrieval")
            if isinstance(hidden_retrieval, dict):
                items = hidden_retrieval.get("items")
                if isinstance(items, list) and items:
                    lines = []
                    for item in items[:3]:
                        if not isinstance(item, dict):
                            continue
                        source = str(item.get("source_path") or "").strip()
                        snippet = str(item.get("snippet") or "").strip()
                        if source or snippet:
                            lines.append(f"- {source}: {snippet[:180]}")
                    if lines:
                        base_system += "\n\nInstruction retrieval (state-aware):\n" + "\n".join(lines)

            user_name = str(context.get("user_name") or "").strip()
            if user_name:
                base_system += (
                    f"\n\nKnown user name: {user_name}. "
                    "If asked about the user's name, answer directly using this value."
                )

            if bool(context.get("myco_help_mode", False)):
                base_system += (
                    "\n\nMYCO_HELP policy: prioritize interface guidance over generic chat. "
                    "Answer compactly in three parts: what user sees now; what user can do next; exact next click/step. "
                    "Keep answers action-oriented and context-bound."
                )

        return base_system

    async def _repack_context_for_model(
        self,
        *,
        context: Dict[str, Any],
        transcript: str,
        user_id: str,
        model_name: str,
    ) -> Dict[str, Any]:
        """
        MARKER_157_7_3_VOICE_UNIFIED_MODEL_AWARE_PACKING.V1
        Reuse unified ContextPacker for stage/model-specific context budgeting.
        """
        if not isinstance(context, dict):
            return {}

        packed_context = dict(context)
        try:
            from src.orchestration.context_packer import get_context_packer

            viewport_context = (
                packed_context.get("viewport_context")
                if isinstance(packed_context.get("viewport_context"), dict)
                else {}
            )
            pinned_files = (
                packed_context.get("pinned_files")
                if isinstance(packed_context.get("pinned_files"), list)
                else []
            )
            zoom_level = 1.0
            try:
                zoom_level = float(viewport_context.get("zoom_level", 1.0))
            except Exception:
                zoom_level = 1.0

            packer = get_context_packer()
            packed = await packer.pack(
                user_query=str(transcript or ""),
                pinned_files=pinned_files,
                viewport_context=viewport_context,
                session_id=str(packed_context.get("session_id") or user_id),
                model_name=str(model_name or DEFAULT_MODEL),
                user_id=user_id,
                zoom_level=zoom_level,
            )

            packed_context["json_context"] = packed.json_context
            packed_context["pinned_context"] = packed.pinned_context
            packed_context["viewport_summary"] = packed.viewport_summary
            packed_context["jepa_context"] = packed.jepa_context
            packed_context["context_packer_trace"] = dict(packed.trace or {})
        except Exception as e:
            logger.debug(f"[JarvisLLM] Model-aware context pack skipped: {e}")
        return packed_context

    def _enrich_prompt(
        self,
        prompt: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        model: str = "qwen",
    ) -> str:
        """Enrich prompt with user preferences from VETKA memory"""
        # FIX_104.7: Re-enabled after Engram integer ID fix
        enricher = self._get_enricher()
        if enricher:
            try:
                if isinstance(context, dict):
                    return enricher.enrich_prompt_with_viewport(
                        base_prompt=prompt,
                        user_id=user_id,
                        viewport_context=context.get("viewport_context")
                        if isinstance(context.get("viewport_context"), dict)
                        else None,
                        pinned_files=context.get("pinned_files")
                        if isinstance(context.get("pinned_files"), list)
                        else None,
                        model=model or "qwen",
                        compress=True,
                    )
                return enricher.enrich_prompt(
                    base_prompt=prompt,
                    user_id=user_id,
                    model=model or "qwen",
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
        preferred_model = context.get("llm_model") if isinstance(context, dict) else None
        model_id, route, reason = resolve_jarvis_text_model(
            default_model=self.config.model,
            preferred_model=preferred_model,
        )
        working_context = await self._repack_context_for_model(
            context=context or {},
            transcript=transcript,
            user_id=user_id,
            model_name=model_id,
        )
        # Build prompts
        system_prompt = self._build_system_prompt(user_id, working_context)
        user_prompt = self._enrich_prompt(
            transcript,
            user_id,
            context=working_context,
            model=model_id,
        )
        logger.info(f"[JarvisLLM] Text model resolved: {model_id} route={route} reason={reason}")

        if route == "provider_registry":
            try:
                from src.elisya.provider_registry import call_model_v2

                response = await call_model_v2(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    model=model_id,
                )
                content = response.get("message", {}).get("content", "").strip()
                if content:
                    return content
                logger.warning(f"[JarvisLLM] Empty provider_registry response for {model_id}, fallback to ollama")
            except Exception as exc:
                logger.warning(f"[JarvisLLM] provider_registry call failed for {model_id}: {exc}")

        # Prepare Ollama request
        payload = {
            "model": model_id if route == "ollama" else self.config.model,
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

            # MARKER_105_OLLAMA_TIMEOUT_FIX: Wrap in asyncio.wait_for to prevent hangs
            async def _do_request():
                async with session.post(
                    f"{self.config.base_url}/api/generate",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data
                    else:
                        error = await resp.text()
                        logger.error(f"[JarvisLLM] Ollama error {resp.status}: {error}")
                        return None

            try:
                data = await asyncio.wait_for(
                    _do_request(),
                    timeout=self.config.timeout  # Use config timeout (default 30s)
                )
            except asyncio.TimeoutError:
                logger.error(f"[JarvisLLM] Ollama timeout after {self.config.timeout}s - preventing hang!")
                return "I'm taking too long to respond. Let me try a simpler answer."

            if data:
                response = data.get("response", "").strip()
                # Log stats
                eval_duration = data.get("eval_duration", 0) / 1e9  # ns to s
                logger.info(f"[JarvisLLM] Response generated in {eval_duration:.2f}s: {response[:50]}...")
                return response
            else:
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
        model_id = str((context or {}).get("llm_model") or self.config.model)
        working_context = await self._repack_context_for_model(
            context=context or {},
            transcript=transcript,
            user_id=user_id,
            model_name=model_id,
        )
        system_prompt = self._build_system_prompt(user_id, working_context)
        user_prompt = self._enrich_prompt(
            transcript,
            user_id,
            context=working_context,
            model=model_id,
        )

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

async def get_jarvis_context(
    user_id: str,
    transcript: str,
    extra_context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
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
            context["session_summary"] = _build_session_summary(stm_entries)
    except Exception as e:
        logger.warning(f"[JarvisContext] STM unavailable: {e}")

    # FIX_104.7: Engram now uses integer IDs for Qdrant REST API (re-enabled)
    # User preferences from Engram memory (for personalized responses)
    try:
        from src.memory.engram_user_memory import get_engram_user_memory
        engram = get_engram_user_memory()

        # Get communication style preferences (affects response tone)
        formality = engram.get_preference(user_id, "communication_style", "formality")
        if formality is not None:
            context["formality"] = formality
            logger.debug(f"[JarvisContext] Engram formality: {formality}")

        preferred_language = engram.get_preference(user_id, "communication_style", "preferred_language")
        if isinstance(preferred_language, str) and preferred_language.strip().lower() in {"ru", "en", "auto"}:
            context["preferred_language"] = preferred_language.strip().lower()
            logger.debug(f"[JarvisContext] Engram preferred_language: {context['preferred_language']}")

        prefers_russian = engram.get_preference(user_id, "communication_style", "prefers_russian")
        if isinstance(prefers_russian, bool):
            context["prefers_russian"] = prefers_russian
            logger.debug(f"[JarvisContext] Engram prefers_russian: {prefers_russian}")

        last_assistant_language = engram.get_preference(user_id, "communication_style", "last_assistant_language")
        if isinstance(last_assistant_language, str) and last_assistant_language.strip().lower() in {"ru", "en"}:
            context["last_assistant_language"] = last_assistant_language.strip().lower()
            logger.debug(f"[JarvisContext] Engram last_assistant_language: {context['last_assistant_language']}")

        user_name = engram.get_preference(user_id, "communication_style", "user_name")
        if isinstance(user_name, str):
            user_name = user_name.strip()
            if user_name:
                context["user_name"] = user_name
                logger.debug(f"[JarvisContext] Engram user_name present")
    except Exception as e:
        logger.warning(f"[JarvisContext] Engram unavailable: {e}")

    # CAM summary from current transcript
    try:
        from src.memory.surprise_detector import get_compression_advice
        cam_advice = get_compression_advice(transcript or "")
        context["cam_context"] = {
            "overall_surprise": cam_advice.get("overall_surprise"),
            "compression_level": cam_advice.get("compression_level"),
            "high_surprise_ratio": cam_advice.get("high_surprise_ratio"),
        }
    except Exception as e:
        logger.debug(f"[JarvisContext] CAM unavailable: {e}")

    # Client-side context from Jarvis button flow
    if isinstance(extra_context, dict):
        for key in (
            "viewport_context",
            "pinned_files",
            "open_chat_context",
            "cam_context",
            "llm_model",
            "nav_level",
            "navLevel",
            "task_drill_state",
            "taskDrillState",
            "roadmap_node_drill_state",
            "roadmapNodeDrillState",
            "workflow_inline_expanded",
            "workflowInlineExpanded",
            "roadmap_node_inline_expanded",
            "roadmapNodeInlineExpanded",
            "node_kind",
            "nodeKind",
            "active_task_id",
            "activeTaskId",
            "role",
            "label",
            "node_id",
            "nodeId",
            "file_path",
            "node_path",
            "path",
        ):
            if key in extra_context and extra_context.get(key) is not None:
                context[key] = extra_context.get(key)

    # 157.7.2: state-key retrieval (MYCO transfer) for voice instruction grounding.
    try:
        from src.services.myco_memory_bridge import retrieve_myco_hidden_context

        state_key_query = _build_voice_state_key_query(transcript, context)
        if state_key_query:
            retrieval = retrieve_myco_hidden_context(
                query=state_key_query,
                focus=context,
                top_k=3,
                min_score=0.22,
            )
            if isinstance(retrieval, dict):
                items = retrieval.get("items")
                if isinstance(items, list):
                    retrieval = {**retrieval, "items": items[:3]}
                context["hidden_retrieval"] = retrieval
                context["state_key_query"] = state_key_query
    except Exception as e:
        logger.debug(f"[JarvisContext] hidden retrieval unavailable: {e}")

    # Phase 157.7.1: bridge Jarvis voice path to unified ContextPacker (JEPA + pressure trace).
    try:
        from src.orchestration.context_packer import get_context_packer

        viewport_context = context.get("viewport_context") if isinstance(context.get("viewport_context"), dict) else {}
        pinned_files = context.get("pinned_files") if isinstance(context.get("pinned_files"), list) else []
        model_name = str(context.get("llm_model") or DEFAULT_MODEL)
        zoom_level = 1.0
        try:
            zoom_level = float(viewport_context.get("zoom_level", 1.0))
        except Exception:
            zoom_level = 1.0

        packer = get_context_packer()
        packed = await packer.pack(
            user_query=str(transcript or ""),
            pinned_files=pinned_files,
            viewport_context=viewport_context,
            session_id=(session_id or user_id),
            model_name=model_name,
            user_id=user_id,
            zoom_level=zoom_level,
        )

        if packed.pinned_context:
            context["pinned_context"] = packed.pinned_context
        if packed.viewport_summary:
            context["viewport_summary"] = packed.viewport_summary
        if packed.json_context:
            context["json_context"] = packed.json_context
        if packed.jepa_context:
            context["jepa_context"] = packed.jepa_context
        context["context_packer_trace"] = dict(packed.trace or {})
        context["session_id"] = session_id or user_id
    except Exception as e:
        logger.debug(f"[JarvisContext] ContextPacker unavailable: {e}")

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
