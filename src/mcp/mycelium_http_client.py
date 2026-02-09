"""MYCELIUM HTTP Client — async callbacks to VETKA server.

MYCELIUM has no SocketIO. All communication to VETKA goes through HTTP.
Chat messages, board notifications, and search queries use this client.

MARKER_129.3: Phase 129 — MYCELIUM HTTP callbacks

@status: active
@phase: 129
@depends: httpx, os
@used_by: mycelium_mcp_server.py, agent_pipeline.py (async_mode)
"""

import os
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

VETKA_API_URL = os.environ.get("VETKA_API_URL", "http://localhost:5001")


# MARKER_129.3_START: MyceliumHTTPClient — async HTTP to VETKA
class MyceliumHTTPClient:
    """Async HTTP client for MYCELIUM → VETKA communication.

    Handles:
    - Chat message relay (pipeline progress → ChatPanel)
    - Task board update notifications (→ SocketIO broadcast)
    - Semantic search proxy (→ Qdrant via VETKA REST)
    """

    def __init__(self, vetka_url: str = None):
        self.vetka_url = vetka_url or VETKA_API_URL
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self):
        """Initialize persistent HTTP client with connection pooling."""
        self._client = httpx.AsyncClient(
            base_url=self.vetka_url,
            timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=3.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            headers={"X-Client": "mycelium-mcp", "Content-Type": "application/json"},
        )
        logger.info(f"[MYCELIUM HTTP] Client started → {self.vetka_url}")

    async def stop(self):
        """Close HTTP client and release connections."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("[MYCELIUM HTTP] Client stopped")

    @property
    def is_ready(self) -> bool:
        return self._client is not None

    # --- Chat Messages ---

    async def emit_chat_message(
        self, chat_id: str, message: str,
        sender: str = "pipeline", msg_type: str = "system"
    ):
        """Send message to VETKA group chat (shows in ChatPanel).

        Uses the existing MCP group send endpoint.
        """
        if not self._client:
            return
        try:
            await self._client.post(
                f"/api/debug/mcp/groups/{chat_id}/send",
                json={
                    "agent_id": sender,
                    "content": message,
                    "message_type": msg_type,
                }
            )
        except Exception as e:
            logger.debug(f"[MYCELIUM HTTP] Chat emit failed: {e}")

    async def emit_pipeline_progress(
        self, chat_id: str, role: str, message: str,
        model: str = "system", subtask_idx: int = 0, total: int = 0
    ):
        """Send pipeline progress to VETKA chat.

        Formats message with role prefix and delegates to emit_chat_message.
        """
        if not chat_id:
            return
        model_short = model.split("/")[-1] if "/" in model else model
        if model != "system":
            full_message = f"{role} ({model_short}): {message}"
        else:
            full_message = f"{role}: {message}"
        await self.emit_chat_message(chat_id, full_message, sender="pipeline")

    # --- Task Board Notifications ---

    async def notify_board_update(self, action: str = "update", summary: dict = None):
        """Notify VETKA about task board changes.

        VETKA broadcasts via SocketIO → DevPanel updates.
        """
        if not self._client:
            return
        try:
            await self._client.post(
                "/api/debug/task-board/notify",
                json={"action": action, "summary": summary or {}}
            )
        except Exception as e:
            logger.debug(f"[MYCELIUM HTTP] Board notify failed: {e}")

    # --- Search Proxy ---

    async def search_semantic(self, query: str, limit: int = 10) -> dict:
        """Proxy semantic search through VETKA REST API.

        Returns search results from Qdrant via VETKA's endpoint.
        """
        if not self._client:
            return {"results": []}
        try:
            resp = await self._client.get(
                "/api/search/semantic",
                params={"query": query, "limit": limit}
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.debug(f"[MYCELIUM HTTP] Search failed: {e}")
        return {"results": []}

    # --- Health Check ---

    async def check_vetka_health(self) -> bool:
        """Check if VETKA server is reachable."""
        if not self._client:
            return False
        try:
            resp = await self._client.get("/api/health", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False


# Singleton
_mycelium_client: Optional[MyceliumHTTPClient] = None


def get_mycelium_client() -> MyceliumHTTPClient:
    """Get or create singleton MyceliumHTTPClient."""
    global _mycelium_client
    if _mycelium_client is None:
        _mycelium_client = MyceliumHTTPClient()
    return _mycelium_client
# MARKER_129.3_END
