"""
OpenCode MCP Proxy Bridge
Converts MCP protocol calls to OpenCode API calls via HTTP
"""

import fastapi
import httpx
import json
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum
import os

logger = logging.getLogger(__name__)

# OpenCode API configuration
OPENCODE_API_KEY = os.getenv('OPENCODE_API_KEY', '')
OPENCODE_BASE_URL = os.getenv('OPENCODE_BASE_URL', 'http://localhost:8080')
OPENCODE_PROXY_PORT = int(os.getenv('OPENCODE_PROXY_PORT', '5003'))

app = fastapi.FastAPI(title="OpenCode MCP Proxy", version="1.0.0")

class MCPCallType(str, Enum):
    """MCP call types that OpenCode needs to handle"""
    TOOL_CALL = "tool_call"
    RESOURCE_READ = "resource_read"
    RESOURCE_WRITE = "resource_write"
    PROMPT_EXECUTE = "prompt_execute"

class MCPProxyRequest(BaseModel):
    """MCP request payload to proxy to OpenCode"""
    call_type: MCPCallType
    agent_id: str
    session_id: str
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, str]] = None

class MCPProxyResponse(BaseModel):
    """Response from OpenCode via proxy"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    call_id: str

# MARKER_106g_1_2: MCP to OpenCode HTTP proxy endpoint
async_client = None

@app.on_event("startup")
async def startup():
    """Initialize HTTP client on startup"""
    global async_client
    async_client = httpx.AsyncClient(
        base_url=OPENCODE_BASE_URL,
        timeout=httpx.Timeout(60.0),
        headers={
            "Authorization": f"Bearer {OPENCODE_API_KEY}",
            "X-Proxy-Version": "106g-1.0",
        }
    )
    logger.info(f"OpenCode proxy initialized: {OPENCODE_BASE_URL}")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    global async_client
    if async_client:
        await async_client.aclose()

@app.post("/mcp", response_model=MCPProxyResponse)
async def proxy_mcp_call(request: MCPProxyRequest) -> MCPProxyResponse:
    """
    Main MCP proxy endpoint

    Converts MCP protocol calls to OpenCode API calls
    Handles tool execution, resource I/O, and prompt evaluation
    """
    try:
        # Map MCP call types to OpenCode API endpoints
        endpoint_map = {
            MCPCallType.TOOL_CALL: "/api/tools/execute",
            MCPCallType.RESOURCE_READ: "/api/resources/read",
            MCPCallType.RESOURCE_WRITE: "/api/resources/write",
            MCPCallType.PROMPT_EXECUTE: "/api/prompts/execute",
        }

        endpoint = endpoint_map.get(request.call_type)
        if not endpoint:
            return MCPProxyResponse(
                success=False,
                call_id=request.session_id,
                error=f"Unknown call type: {request.call_type}"
            )

        # Add session context to payload
        opencode_payload = {
            **request.payload,
            "agent_id": request.agent_id,
            "session_id": request.session_id,
            "call_type": request.call_type.value,
        }

        if request.metadata:
            opencode_payload["metadata"] = request.metadata

        # Proxy request to OpenCode
        response = await async_client.post(
            endpoint,
            json=opencode_payload,
            timeout=45.0
        )

        if response.status_code >= 400:
            logger.error(
                f"OpenCode error: {response.status_code}",
                extra={"session_id": request.session_id}
            )
            return MCPProxyResponse(
                success=False,
                call_id=request.session_id,
                error=f"OpenCode API error: {response.status_code}"
            )

        data = response.json()
        return MCPProxyResponse(
            success=True,
            data=data,
            call_id=request.session_id
        )

    except httpx.TimeoutException:
        logger.error("OpenCode request timeout", extra={"session_id": request.session_id})
        return MCPProxyResponse(
            success=False,
            call_id=request.session_id,
            error="OpenCode request timeout"
        )
    except Exception as e:
        logger.error(f"Proxy error: {str(e)}", extra={"session_id": request.session_id})
        return MCPProxyResponse(
            success=False,
            call_id=request.session_id,
            error=str(e)
        )

@app.get("/health")
async def health_check():
    """Health check for OpenCode proxy"""
    try:
        response = await async_client.get(
            f"{OPENCODE_BASE_URL}/health",
            timeout=5.0
        )
        return {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "opencode_available": response.status_code == 200,
            "proxy_version": "106g-1.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "opencode_available": False,
            "error": str(e),
            "proxy_version": "106g-1.0"
        }

# MARKER_106g_1_3: OpenCode MCP agent wrapper
class OpenCodeMCPAgent:
    """
    Wrapper to use OpenCode with MCP protocol
    Bridges MCP tools/resources to OpenCode endpoints
    """

    def __init__(self, agent_id: str, session_id: str, proxy_url: str = None):
        self.agent_id = agent_id
        self.session_id = session_id
        self.proxy_url = proxy_url or f"http://localhost:{OPENCODE_PROXY_PORT}"
        self.http_client = None

    async def initialize(self):
        """Initialize async HTTP client"""
        self.http_client = httpx.AsyncClient(base_url=self.proxy_url)

    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool via OpenCode proxy"""
        request = MCPProxyRequest(
            call_type=MCPCallType.TOOL_CALL,
            agent_id=self.agent_id,
            session_id=self.session_id,
            payload={
                "tool_name": tool_name,
                "arguments": args
            }
        )

        response = await self.http_client.post(
            "/mcp",
            json=request.dict()
        )
        return response.json()

    async def read_resource(self, resource_path: str) -> str:
        """Read resource via OpenCode proxy"""
        request = MCPProxyRequest(
            call_type=MCPCallType.RESOURCE_READ,
            agent_id=self.agent_id,
            session_id=self.session_id,
            payload={"resource_path": resource_path}
        )

        response = await self.http_client.post("/mcp", json=request.dict())
        data = response.json()
        return data.get("data", {}).get("content", "")

    async def shutdown(self):
        """Cleanup resources"""
        if self.http_client:
            await self.http_client.aclose()

# MARKER_106g_1_4: OpenCode proxy main entry point
if __name__ == "__main__":
    import uvicorn
    import sys

    log_level = os.getenv('LOG_LEVEL', 'info').lower()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=OPENCODE_PROXY_PORT,
        log_level=log_level,
        access_log=True
    )
