"""
LM Studio MCP Proxy Bridge
Converts OpenAI-compatible chat completion requests to VETKA MCP tool calls

@file lmstudio_proxy.py
@status PRODUCTION (Phase 106h)
@phase Phase 106h - LM Studio + Warp Integration
@lastAudit 2026-02-02

MARKER_106h_1: LM Studio MCP Proxy

This proxy enables LM Studio local models to access VETKA tools via OpenAI-compatible API.
It intercepts tool calls from the chat completion response and executes them via VETKA MCP.

Architecture:
  LM Studio (localhost:1234) <-> This Proxy (localhost:5004) <-> VETKA MCP (localhost:5002)

Usage:
  1. Start VETKA MCP server: python src/mcp/vetka_mcp_server.py --http --port 5002
  2. Start LM Studio with local model
  3. Start this proxy: python src/mcp/lmstudio_proxy.py
  4. Configure LM Studio to use http://localhost:5004/v1 as OpenAI endpoint

Features:
  - OpenAI-compatible /v1/chat/completions endpoint
  - Automatic tool call extraction and execution
  - Fallback to LM Studio API for model inference
  - Tool result injection back into chat context
"""

import fastapi
import httpx
import json
import logging
import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Configuration
LMSTUDIO_URL = os.getenv('LMSTUDIO_URL', 'http://localhost:1234/v1')
MCP_URL = os.getenv('MCP_URL', 'http://localhost:5002/mcp')
PROXY_PORT = int(os.getenv('LMSTUDIO_PROXY_PORT', '5004'))

app = fastapi.FastAPI(
    title="LM Studio MCP Proxy",
    version="106h-1.0",
    description="OpenAI-compatible proxy with VETKA MCP tool support"
)

# CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTP clients
lm_client = None
mcp_client = None


@app.on_event("startup")
async def startup():
    """Initialize HTTP clients on startup"""
    global lm_client, mcp_client
    lm_client = httpx.AsyncClient(
        base_url=LMSTUDIO_URL,
        timeout=httpx.Timeout(120.0)
    )
    mcp_client = httpx.AsyncClient(
        base_url=MCP_URL,
        timeout=httpx.Timeout(90.0)
    )
    logger.info(f"[LM Studio Proxy] Started on port {PROXY_PORT}")
    logger.info(f"[LM Studio Proxy] LM Studio: {LMSTUDIO_URL}")
    logger.info(f"[LM Studio Proxy] VETKA MCP: {MCP_URL}")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    global lm_client, mcp_client
    if lm_client:
        await lm_client.aclose()
    if mcp_client:
        await mcp_client.aclose()


# OpenAI-compatible request models
class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = "auto"
    stream: Optional[bool] = False


async def list_mcp_tools() -> List[Dict[str, Any]]:
    """
    Fetch available tools from VETKA MCP server
    """
    try:
        response = await mcp_client.post(
            "",  # Base URL is already set to /mcp
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
        )

        if response.status_code != 200:
            logger.error(f"[LM Studio Proxy] MCP tools/list failed: {response.status_code}")
            return []

        data = response.json()
        tools = data.get("result", {}).get("tools", [])

        # Convert MCP tools to OpenAI function format
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("inputSchema", {})
                }
            })

        logger.info(f"[LM Studio Proxy] Loaded {len(openai_tools)} tools from MCP")
        return openai_tools

    except Exception as e:
        logger.error(f"[LM Studio Proxy] Error fetching MCP tools: {e}")
        return []


async def execute_mcp_tool(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool via VETKA MCP server
    """
    try:
        response = await mcp_client.post(
            "",  # Base URL is already set to /mcp
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": tool_args
                }
            }
        )

        if response.status_code != 200:
            logger.error(f"[LM Studio Proxy] Tool execution failed: {response.status_code}")
            return {
                "error": f"Tool execution failed with status {response.status_code}"
            }

        data = response.json()

        if "error" in data:
            logger.error(f"[LM Studio Proxy] MCP error: {data['error']}")
            return {"error": data["error"].get("message", "Unknown error")}

        result = data.get("result", {})
        logger.info(f"[LM Studio Proxy] Tool {tool_name} executed successfully")
        return result

    except Exception as e:
        logger.error(f"[LM Studio Proxy] Error executing tool {tool_name}: {e}")
        return {"error": str(e)}


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completion endpoint with MCP tool support

    Flow:
    1. If tools are requested, fetch from VETKA MCP
    2. Forward request to LM Studio for model inference
    3. Extract any tool calls from response
    4. Execute tool calls via VETKA MCP
    5. Inject tool results back into chat
    6. Return final response to client
    """
    try:
        # Fetch MCP tools if requested
        if request.tools is None:
            mcp_tools = await list_mcp_tools()
            if mcp_tools:
                request.tools = mcp_tools

        # Forward to LM Studio
        lm_payload = request.dict(exclude_none=True)

        logger.info(f"[LM Studio Proxy] Forwarding to LM Studio: {request.model}")

        lm_response = await lm_client.post(
            "/chat/completions",
            json=lm_payload,
            timeout=120.0
        )

        if lm_response.status_code != 200:
            logger.error(f"[LM Studio Proxy] LM Studio error: {lm_response.status_code}")
            return fastapi.Response(
                content=lm_response.content,
                status_code=lm_response.status_code,
                media_type="application/json"
            )

        response_data = lm_response.json()

        # Check for tool calls in response
        if "choices" in response_data and len(response_data["choices"]) > 0:
            first_choice = response_data["choices"][0]
            message = first_choice.get("message", {})
            tool_calls = message.get("tool_calls", [])

            if tool_calls:
                logger.info(f"[LM Studio Proxy] Found {len(tool_calls)} tool calls")

                # Execute each tool call
                tool_results = []
                for tool_call in tool_calls:
                    tool_id = tool_call.get("id", "unknown")
                    function = tool_call.get("function", {})
                    tool_name = function.get("name", "")
                    tool_args_str = function.get("arguments", "{}")

                    # Parse arguments
                    try:
                        tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                    except json.JSONDecodeError:
                        tool_args = {}

                    logger.info(f"[LM Studio Proxy] Executing tool: {tool_name}")

                    # Execute via MCP
                    result = await execute_mcp_tool(tool_name, tool_args)

                    # Format result
                    tool_results.append({
                        "tool_call_id": tool_id,
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(result, indent=2)
                    })

                # Inject tool results into response metadata
                response_data["tool_results"] = tool_results
                logger.info(f"[LM Studio Proxy] Executed {len(tool_results)} tools successfully")

        return response_data

    except httpx.TimeoutException:
        logger.error("[LM Studio Proxy] LM Studio request timeout")
        return fastapi.Response(
            content=json.dumps({"error": "LM Studio request timeout"}),
            status_code=504,
            media_type="application/json"
        )

    except Exception as e:
        logger.error(f"[LM Studio Proxy] Error: {e}")
        import traceback
        return fastapi.Response(
            content=json.dumps({
                "error": str(e),
                "traceback": traceback.format_exc()
            }),
            status_code=500,
            media_type="application/json"
        )


@app.get("/v1/models")
async def list_models():
    """
    Forward model list request to LM Studio
    """
    try:
        response = await lm_client.get("/models")
        return fastapi.Response(
            content=response.content,
            status_code=response.status_code,
            media_type="application/json"
        )
    except Exception as e:
        logger.error(f"[LM Studio Proxy] Error listing models: {e}")
        return {"error": str(e)}


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    try:
        # Check LM Studio
        lm_health = await lm_client.get("/models", timeout=5.0)
        lm_ok = lm_health.status_code == 200
    except Exception:
        lm_ok = False

    try:
        # Check VETKA MCP
        mcp_health = await mcp_client.post(
            "",
            json={
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {}
            },
            timeout=5.0
        )
        mcp_ok = mcp_health.status_code == 200
    except Exception:
        mcp_ok = False

    status = "healthy" if (lm_ok and mcp_ok) else "degraded"

    return {
        "status": status,
        "proxy_version": "106h-1.0",
        "lm_studio_available": lm_ok,
        "mcp_available": mcp_ok,
        "endpoints": {
            "lm_studio": LMSTUDIO_URL,
            "mcp": MCP_URL
        }
    }


@app.get("/")
async def root():
    """
    Root endpoint with usage info
    """
    return {
        "name": "LM Studio MCP Proxy",
        "version": "106h-1.0",
        "phase": "Phase 106h - LM Studio + Warp Integration",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "models": "/v1/models",
            "health": "/health"
        },
        "usage": "Configure LM Studio or compatible client to use http://localhost:5004/v1 as OpenAI endpoint"
    }


# MARKER_106h_2: Warp Terminal MCP integration helper
def generate_warp_config() -> Dict[str, Any]:
    """
    Generate Warp Terminal configuration for VETKA MCP

    Warp supports MCP via HTTP endpoints.
    This generates the config file content for ~/.warp/config.json
    """
    return {
        "mcp_servers": [
            {
                "name": "vetka",
                "type": "http",
                "url": "http://localhost:5002/mcp",
                "description": "VETKA 3D Knowledge Base with 25+ AI tools",
                "enabled": True,
                "headers": {
                    "X-Client": "warp-terminal",
                    "X-Session-ID": "warp-default"
                }
            }
        ],
        "proxy_servers": [
            {
                "name": "lm_studio_proxy",
                "type": "openai",
                "url": "http://localhost:5004/v1",
                "description": "LM Studio with VETKA MCP tool support",
                "enabled": True
            }
        ]
    }


@app.get("/warp/config")
async def get_warp_config():
    """
    Get Warp Terminal configuration for VETKA MCP
    """
    return generate_warp_config()


# Main entry point
if __name__ == "__main__":
    import uvicorn

    log_level = os.getenv('LOG_LEVEL', 'info').lower()

    print("\n" + "=" * 60)
    print("  LM Studio MCP Proxy (Phase 106h)")
    print("=" * 60)
    print(f"  Listening on: http://127.0.0.1:{PROXY_PORT}")
    print(f"  OpenAI endpoint: http://localhost:{PROXY_PORT}/v1")
    print(f"  LM Studio: {LMSTUDIO_URL}")
    print(f"  VETKA MCP: {MCP_URL}")
    print("=" * 60 + "\n")

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=PROXY_PORT,
        log_level=log_level,
        access_log=True
    )
