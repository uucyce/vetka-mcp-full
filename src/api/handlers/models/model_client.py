"""
VETKA Model Client - Unified LLM Calling Interface.

Unified client for calling LLM models (Ollama + OpenRouter).
Consolidates 374-line model call block from user_message_handler.py.

Responsibilities:
- Detect model type (local vs remote)
- Call appropriate backend (Ollama vs OpenRouter)
- Handle streaming
- Manage API key rotation
- Emit responses to Socket.IO

@status: active
@phase: 96
@depends: chat_handler, utils.unified_key_manager, httpx
@used_by: di_container, mention.mention_handler
"""

import asyncio
import httpx
import json as json_module
import uuid
from typing import Dict, Any, Optional

from ..chat_handler import is_local_ollama_model, get_agent_short_name


class ModelClient:
    """
    Unified client for calling LLM models (Ollama + OpenRouter).

    This class implements the IModelClient interface and consolidates
    the 374-line model call block from user_message_handler.py.
    """

    def __init__(self, sio, context_builder):
        """
        Initialize model client.

        Args:
            sio: Socket.IO server instance for response emission
            context_builder: ContextBuilder instance for building prompts
        """
        self.sio = sio
        self.context_builder = context_builder

    def is_local_model(self, model_name: str) -> bool:
        """Check if model is local Ollama."""
        return is_local_ollama_model(model_name)

    async def call_model(
        self,
        model_name: str,
        prompt: str,
        session_id: str,
        node_id: str,
        node_path: str,
        streaming: bool = True,
        max_tokens: int = 999999,  # Unlimited responses
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Call a model and return response.

        This is the main entry point that routes to either Ollama or OpenRouter.

        Args:
            model_name: Model identifier (e.g., 'qwen2.5:7b' or 'anthropic/claude-3-haiku')
            prompt: Complete prompt to send to model
            session_id: Socket.IO session ID
            node_id: Node ID for response tracking
            node_path: File path being discussed
            streaming: Enable streaming mode
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            {
                'success': bool,
                'response_text': str,
                'tokens_input': int,
                'tokens_output': int,
                'model_used': str,
                'error': Optional[str]
            }
        """

        # Route to appropriate backend
        if self.is_local_model(model_name):
            return await self._call_ollama(
                model_name=model_name,
                prompt=prompt,
                session_id=session_id,
                node_id=node_id,
                node_path=node_path,
                streaming=streaming,
            )
        else:
            return await self._call_openrouter(
                model_name=model_name,
                prompt=prompt,
                session_id=session_id,
                node_id=node_id,
                node_path=node_path,
                streaming=streaming,
                max_tokens=max_tokens,
                temperature=temperature,
            )

    async def _call_ollama(
        self,
        model_name: str,
        prompt: str,
        session_id: str,
        node_id: str,
        node_path: str,
        streaming: bool,
    ) -> Dict[str, Any]:
        """
        Call Ollama local model.

        This extracts lines 246-370 from user_message_handler.py.
        """
        try:
            import ollama

            print(f"[MODEL_CLIENT] Calling Ollama: {model_name}")

            agent_short_name = get_agent_short_name(model_name)
            msg_id = str(uuid.uuid4())

            # Emit stream start
            await self.sio.emit(
                "stream_start",
                {"id": msg_id, "agent": agent_short_name, "model": model_name},
                to=session_id,
            )

            # Run sync ollama call in executor
            loop = asyncio.get_event_loop()

            def ollama_call():
                return ollama.chat(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    stream=False,
                )

            ollama_response = await loop.run_in_executor(None, ollama_call)

            # Extract response
            if hasattr(ollama_response, "message"):
                full_response = ollama_response.message.content or ""
            else:
                full_response = ollama_response.get("message", {}).get("content", "")

            tokens_output = len(full_response.split())

            print(f"[MODEL_CLIENT] Ollama complete: {len(full_response)} chars")

            # Emit stream end
            await self.sio.emit(
                "stream_end",
                {
                    "id": msg_id,
                    "full_message": full_response,
                    "metadata": {
                        "tokens_output": tokens_output,
                        "tokens_input": len(prompt.split()),
                        "model": model_name,
                        "agent": agent_short_name,
                    },
                },
                to=session_id,
            )

            return {
                "success": True,
                "response_text": full_response,
                "tokens_input": len(prompt.split()),
                "tokens_output": tokens_output,
                "model_used": model_name,
                "error": None,
            }

        except Exception as e:
            print(f"[MODEL_CLIENT] Ollama error: {e}")
            import traceback

            traceback.print_exc()

            error_msg = f"Error calling Ollama model {model_name}: {str(e)[:200]}"
            await self.sio.emit(
                "chat_response",
                {"message": error_msg, "agent": "System", "model": "error"},
                to=session_id,
            )

            return {
                "success": False,
                "response_text": error_msg,
                "tokens_input": 0,
                "tokens_output": 0,
                "model_used": model_name,
                "error": str(e),
            }

    async def _call_openrouter(
        self,
        model_name: str,
        prompt: str,
        session_id: str,
        node_id: str,
        node_path: str,
        streaming: bool,
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        """
        Call OpenRouter remote model.

        This extracts lines 372-601 from user_message_handler.py.
        Includes streaming support and API key rotation.
        """
        try:
            from src.utils.unified_key_manager import get_key_manager

            km = get_key_manager()

            # Track retry state
            max_key_retries = min(3, km.get_openrouter_keys_count())
            key_retry_count = 0
            api_key = km.get_openrouter_key()  # Start with current key (default: paid)

            if not api_key:
                print("[MODEL_CLIENT] ERROR: No OpenRouter API key available!")
                error_msg = "Error: No OpenRouter API key configured. Please add keys in data/config.json"
                await self.sio.emit(
                    "chat_response",
                    {"message": error_msg, "agent": "System", "model": "error"},
                    to=session_id,
                )
                return {
                    "success": False,
                    "response_text": error_msg,
                    "tokens_input": 0,
                    "tokens_output": 0,
                    "model_used": model_name,
                    "error": "No API key",
                }

            print(f"[MODEL_CLIENT] Using API key: ****{api_key[-4:]}")

            agent_short_name = get_agent_short_name(model_name)
            msg_id = str(uuid.uuid4())

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://vetka.app",
                "X-Title": "VETKA",
            }

            full_response = ""
            tokens_output = 0
            use_streaming = True

            async with httpx.AsyncClient(timeout=120.0) as client:
                # First try streaming
                try:
                    # Emit stream start
                    await self.sio.emit(
                        "stream_start",
                        {"id": msg_id, "agent": agent_short_name, "model": model_name},
                        to=session_id,
                    )

                    payload = {
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": True,
                    }

                    async with client.stream(
                        "POST",
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as response:
                        # Handle 429 rate limit
                        if response.status_code == 429:
                            print(f"[MODEL_CLIENT] 429 Rate limited for {model_name}")
                            full_response = f"⚠️ Model **{agent_short_name}** is rate limited. Please try another model or wait a moment."
                            use_streaming = False
                        elif response.status_code != 200:
                            error_text = await response.aread()
                            error_decoded = error_text.decode()[:200]

                            # Check if streaming not supported - fallback
                            if (
                                "stream" in error_decoded.lower()
                                or response.status_code == 400
                            ):
                                print(
                                    f"[MODEL_CLIENT] Streaming not supported, trying fallback"
                                )
                                use_streaming = False
                            elif response.status_code in [401, 402]:
                                # Retry with next key on auth/payment errors
                                key_retry_count += 1
                                if key_retry_count < max_key_retries:
                                    print(
                                        f"[MODEL_CLIENT] Key failed ({response.status_code}), rotating... (attempt {key_retry_count}/{max_key_retries})"
                                    )
                                    km.rotate_to_next()
                                    api_key = km.get_openrouter_key()
                                    headers["Authorization"] = f"Bearer {api_key}"
                                    print(
                                        f"[MODEL_CLIENT] Retrying with key: ****{api_key[-4:]}"
                                    )
                                    use_streaming = (
                                        False  # Will retry in fallback block
                                    )
                                else:
                                    full_response = f"Error {response.status_code}: {'Insufficient credits' if response.status_code == 402 else 'Unauthorized'}. All keys exhausted."
                            else:
                                full_response = (
                                    f"Error {response.status_code}: {error_decoded}"
                                )
                        else:
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    data = line[6:]
                                    if data == "[DONE]":
                                        break
                                    try:
                                        chunk = json_module.loads(data)
                                        token = (
                                            chunk.get("choices", [{}])[0]
                                            .get("delta", {})
                                            .get("content", "")
                                        )
                                        if token:
                                            full_response += token
                                            tokens_output += 1
                                            # Emit token
                                            await self.sio.emit(
                                                "stream_token",
                                                {"id": msg_id, "token": token},
                                                to=session_id,
                                            )
                                    except json_module.JSONDecodeError:
                                        pass

                except Exception as stream_err:
                    print(
                        f"[MODEL_CLIENT] Streaming error: {stream_err}, trying fallback"
                    )
                    use_streaming = False

                # Fallback to non-streaming if needed
                if not use_streaming and not full_response:
                    print(f"[MODEL_CLIENT] Using non-streaming fallback")
                    payload = {
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": False,
                    }

                    resp = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                    if resp.status_code == 429:
                        full_response = f"⚠️ Model **{agent_short_name}** is rate limited. Please try another model."
                    elif resp.status_code == 200:
                        resp_data = resp.json()
                        full_response = (
                            resp_data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                        )
                        tokens_output = resp_data.get("usage", {}).get(
                            "completion_tokens", len(full_response.split())
                        )
                    else:
                        full_response = f"Error {resp.status_code}: {resp.text[:200]}"

            print(
                f"[MODEL_CLIENT] Complete: {len(full_response)} chars, {tokens_output} tokens"
            )

            # Emit stream end
            await self.sio.emit(
                "stream_end",
                {
                    "id": msg_id,
                    "full_message": full_response,
                    "metadata": {
                        "tokens_output": tokens_output,
                        "tokens_input": len(prompt.split()),
                        "model": model_name,
                        "agent": agent_short_name,
                    },
                },
                to=session_id,
            )

            return {
                "success": True,
                "response_text": full_response,
                "tokens_input": len(prompt.split()),
                "tokens_output": tokens_output,
                "model_used": model_name,
                "error": None,
            }

        except Exception as e:
            print(f"[MODEL_CLIENT] Error: {e}")
            import traceback

            traceback.print_exc()

            error_msg = f"Error calling {model_name}: {str(e)[:200]}"
            await self.sio.emit(
                "chat_response",
                {"message": error_msg, "agent": "System", "model": "error"},
                to=session_id,
            )

            return {
                "success": False,
                "response_text": error_msg,
                "tokens_input": 0,
                "tokens_output": 0,
                "model_used": model_name,
                "error": str(e),
            }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_model_client(sio, context_builder):
    """
    Factory function to create ModelClient instance.

    Args:
        sio: Socket.IO server instance
        context_builder: ContextBuilder instance

    Returns:
        ModelClient instance
    """
    return ModelClient(sio, context_builder)
