# Phase 106g: OpenCode & Cursor MCP Integration Gaps

**Research Source:** Grok MCP compatibility analysis
**Status:** IMPLEMENTATION MARKERS READY

## Executive Summary

Phase 106g addresses the remaining integration gaps discovered by Grok:
- **OpenCode:** No native MCP support → requires FastAPI proxy wrapper
- **Cursor:** Native MCP works → requires config generator tool
- **Health Monitoring:** Add Ollama-based doctor tool for agent diagnostics

This phase enables full IDE ecosystem integration while maintaining system reliability.

---

## MARKER_106g_1: OpenCode Proxy Bridge

### Task 1.1: FastAPI Proxy Server Setup
**File:** `src/mcp/opencode_proxy.py` (NEW)
**Purpose:** Proxy MCP calls to OpenCode API since OpenCode has no native MCP support

```python
# MARKER_106g_1_1: OpenCode FastAPI proxy initialization
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
```

### Task 1.2: HTTP Proxy Endpoint
**File:** `src/mcp/opencode_proxy.py`
**Line:** After class definitions (~80)

```python
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
```

### Task 1.3: OpenCode Agent Wrapper
**File:** `src/mcp/opencode_proxy.py`
**Line:** After endpoints (~180)

```python
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
```

### Task 1.4: Main Entry Point
**File:** `src/mcp/opencode_proxy.py`
**Line:** At end of file (~240)

```python
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
```

---

## MARKER_106g_2: Cursor MCP Config Generator

### Task 2.1: Config Generator Core
**File:** `src/mcp/tools/cursor_config_generator.py` (NEW)
**Purpose:** Auto-generate cursor-specific MCP configuration files

```python
# MARKER_106g_2_1: Cursor MCP config generator
"""
Generates Cursor IDE MCP configuration files
Supports both Kilo-Code and Roo-Cline agent setups
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class CursorAgentType(str, Enum):
    """Cursor agent types that need MCP configs"""
    KILO_CODE = "kilo_code"
    ROO_CLINE = "roo_cline"
    CUSTOM = "custom"

@dataclass
class MCPServerConfig:
    """MCP server configuration for Cursor"""
    name: str
    description: str
    command: str
    args: List[str]
    environment: Dict[str, str]
    disabled: bool = False
    alwaysAllow: List[str] = None

class CursorMCPConfigGenerator:
    """
    Generates Cursor IDE MCP configurations
    Creates config files for agent integration
    """

    def __init__(self, cursor_config_dir: str = None):
        """
        Initialize config generator

        Args:
            cursor_config_dir: Path to Cursor config directory
                              Default: ~/.cursor/config/mcp
        """
        if cursor_config_dir is None:
            home = os.path.expanduser("~")
            cursor_config_dir = os.path.join(home, ".cursor", "config", "mcp")

        self.cursor_config_dir = Path(cursor_config_dir)
        self.cursor_config_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cursor config directory: {self.cursor_config_dir}")

    def generate_vetka_server_config(self,
                                     vetka_mcp_url: str = "http://localhost:5002",
                                     session_id: str = None) -> MCPServerConfig:
        """
        Generate VETKA MCP server configuration for Cursor

        Args:
            vetka_mcp_url: URL of VETKA MCP HTTP endpoint
            session_id: Optional session ID for agent isolation
        """
        env = {
            "VETKA_MCP_URL": vetka_mcp_url,
            "MCP_HTTP_MODE": "true",
        }

        if session_id:
            env["MCP_SESSION_ID"] = session_id

        return MCPServerConfig(
            name="vetka-mcp",
            description="VETKA Multi-Agent MCP Hub",
            command="python",
            args=[
                "-m", "src.mcp.vetka_mcp_bridge",
                "--http",
                "--port", "5002"
            ],
            environment=env,
            alwaysAllow=["vetka_tool_call", "vetka_resource_read", "vetka_resource_write"]
        )

    def generate_kilo_code_config(self) -> Dict[str, Any]:
        """
        Generate MCP configuration for Kilo-Code agent in Cursor

        Returns:
            Configuration dict for cursor settings.json
        """
        return {
            "mcp": {
                "servers": {
                    "vetka-kilo-code": {
                        "command": "python",
                        "args": [
                            "-m", "src.mcp.vetka_mcp_bridge",
                            "--http",
                            "--port", "5002",
                            "--session-id", "kilo-code-agent"
                        ],
                        "disabled": False,
                        "alwaysAllow": [
                            "vetka_tool_call",
                            "vetka_resource_read",
                            "vetka_resource_write",
                            "kilo_execute_code"
                        ],
                        "env": {
                            "VETKA_MCP_URL": "http://localhost:5002",
                            "AGENT_TYPE": "kilo_code",
                            "MCP_HTTP_MODE": "true",
                        }
                    }
                },
                "allowedHosts": ["localhost", "127.0.0.1"]
            }
        }

    def generate_roo_cline_config(self) -> Dict[str, Any]:
        """
        Generate MCP configuration for Roo-Cline agent in Cursor

        Returns:
            Configuration dict for cursor settings.json
        """
        return {
            "mcp": {
                "servers": {
                    "vetka-roo-cline": {
                        "command": "python",
                        "args": [
                            "-m", "src.mcp.vetka_mcp_bridge",
                            "--http",
                            "--port", "5002",
                            "--session-id", "roo-cline-agent"
                        ],
                        "disabled": False,
                        "alwaysAllow": [
                            "vetka_tool_call",
                            "vetka_resource_read",
                            "vetka_resource_write",
                            "roo_cline_execute"
                        ],
                        "env": {
                            "VETKA_MCP_URL": "http://localhost:5002",
                            "AGENT_TYPE": "roo_cline",
                            "MCP_HTTP_MODE": "true",
                            "ROO_CLINE_MODEL": "claude-opus-4-5"
                        }
                    }
                },
                "allowedHosts": ["localhost", "127.0.0.1"]
            }
        }

    def write_config_file(self, agent_type: CursorAgentType, config: Dict[str, Any]) -> Path:
        """
        Write MCP config file for agent type

        Args:
            agent_type: Type of Cursor agent
            config: Configuration dictionary

        Returns:
            Path to written config file
        """
        filename = f"cursor_{agent_type.value}_mcp.json"
        config_path = self.cursor_config_dir / filename

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        logger.info(f"Wrote config: {config_path}")
        return config_path

    def generate_all_configs(self) -> Dict[str, Path]:
        """
        Generate all Cursor MCP configs in one go

        Returns:
            Dictionary mapping agent types to config file paths
        """
        results = {}

        # Kilo-Code config
        kilo_config = self.generate_kilo_code_config()
        kilo_path = self.write_config_file(CursorAgentType.KILO_CODE, kilo_config)
        results["kilo_code"] = kilo_path

        # Roo-Cline config
        roo_config = self.generate_roo_cline_config()
        roo_path = self.write_config_file(CursorAgentType.ROO_CLINE, roo_config)
        results["roo_cline"] = roo_path

        logger.info(f"Generated {len(results)} Cursor MCP configurations")
        return results

    def apply_to_cursor_settings(self,
                                settings_file: str = None,
                                agent_type: CursorAgentType = None) -> bool:
        """
        Apply MCP config to Cursor settings.json

        Args:
            settings_file: Path to Cursor settings.json
                          Default: ~/.cursor/settings.json
            agent_type: Specific agent to configure or None for all

        Returns:
            True if successful
        """
        if settings_file is None:
            home = os.path.expanduser("~")
            settings_file = os.path.join(home, ".cursor", "settings.json")

        try:
            # Load existing settings
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
            else:
                settings = {}

            # Generate and merge configs
            if agent_type == CursorAgentType.KILO_CODE or agent_type is None:
                kilo_config = self.generate_kilo_code_config()
                settings["mcp"] = {**settings.get("mcp", {}), **kilo_config["mcp"]}

            if agent_type == CursorAgentType.ROO_CLINE or agent_type is None:
                roo_config = self.generate_roo_cline_config()
                settings["mcp"] = {**settings.get("mcp", {}), **roo_config["mcp"]}

            # Write back
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)

            logger.info(f"Updated Cursor settings: {settings_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to update Cursor settings: {e}")
            return False
```

### Task 2.2: CLI Tool for Config Generation
**File:** `src/mcp/tools/cursor_config_generator.py`
**Line:** At end of file (~320)

```python
# MARKER_106g_2_2: Cursor config generator CLI
def main():
    """
    CLI interface for Cursor MCP config generation

    Usage:
        python cursor_config_generator.py --generate-all
        python cursor_config_generator.py --agent kilo_code --apply
        python cursor_config_generator.py --agent roo_cline --apply
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Cursor IDE MCP configurations"
    )
    parser.add_argument(
        "--generate-all",
        action="store_true",
        help="Generate all agent configs"
    )
    parser.add_argument(
        "--agent",
        type=str,
        choices=["kilo_code", "roo_cline"],
        help="Specific agent to configure"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply config to Cursor settings.json"
    )
    parser.add_argument(
        "--cursor-config-dir",
        type=str,
        help="Cursor config directory"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    # Initialize generator
    generator = CursorMCPConfigGenerator(args.cursor_config_dir)

    if args.generate_all:
        results = generator.generate_all_configs()
        print(f"Generated {len(results)} configs:")
        for agent, path in results.items():
            print(f"  - {agent}: {path}")

    if args.apply:
        agent_type = None
        if args.agent:
            agent_type = CursorAgentType[args.agent.upper()]

        success = generator.apply_to_cursor_settings(agent_type=agent_type)
        if success:
            print(f"Applied MCP config to Cursor settings")
        else:
            print("Failed to apply config")
            exit(1)

if __name__ == "__main__":
    main()
```

---

## MARKER_106g_3: Doctor Tool (Deepseek/Ollama Health Monitor)

### Task 3.1: Doctor Tool Core
**File:** `src/mcp/tools/doctor_tool.py` (NEW)
**Purpose:** Health check and diagnostic tool for local Ollama/Deepseek models

```python
# MARKER_106g_3_1: Doctor tool for model health monitoring
"""
Doctor Tool: MCP Health Diagnostics
Monitors Ollama, Deepseek, and agent system health
Provides actionable remediation suggestions
"""

import httpx
import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class HealthStatus(str, Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class DiagnosticLevel(str, Enum):
    """Diagnostic detail levels"""
    QUICK = "quick"          # < 2s, basic checks
    STANDARD = "standard"    # < 10s, full checks
    DEEP = "deep"            # < 30s, with performance analysis

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    status: HealthStatus
    message: str
    duration_ms: float
    details: Optional[Dict[str, Any]] = None
    remediation: Optional[List[str]] = None

class DoctorTool:
    """
    MCP Doctor Tool for system health monitoring
    Checks Ollama, Deepseek, MCP bridge, and agent connectivity
    """

    def __init__(self,
                 ollama_url: str = None,
                 deepseek_url: str = None,
                 mcp_bridge_url: str = None,
                 timeout: float = 5.0):
        """
        Initialize doctor tool

        Args:
            ollama_url: Ollama API endpoint
            deepseek_url: Deepseek/local model endpoint
            mcp_bridge_url: VETKA MCP bridge endpoint
            timeout: HTTP request timeout
        """
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.deepseek_url = deepseek_url or os.getenv("DEEPSEEK_URL", "http://localhost:8000")
        self.mcp_bridge_url = mcp_bridge_url or os.getenv("MCP_BRIDGE_URL", "http://localhost:5002")
        self.timeout = timeout
        self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    async def check_ollama_health(self) -> HealthCheckResult:
        """Check Ollama service health"""
        start = time.time()

        try:
            response = await self.http_client.get(
                f"{self.ollama_url}/api/tags",
                timeout=self.timeout
            )

            duration_ms = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])

                return HealthCheckResult(
                    component="ollama",
                    status=HealthStatus.HEALTHY,
                    message=f"Ollama running with {len(models)} model(s)",
                    duration_ms=duration_ms,
                    details={
                        "models": len(models),
                        "model_list": [m.get("name") for m in models[:5]],
                        "endpoint": self.ollama_url
                    }
                )
            else:
                return HealthCheckResult(
                    component="ollama",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Ollama returned {response.status_code}",
                    duration_ms=duration_ms,
                    remediation=[
                        f"Check if Ollama is running on {self.ollama_url}",
                        "Run: ollama serve",
                        "Check firewall/port settings"
                    ]
                )

        except httpx.TimeoutException:
            duration_ms = (time.time() - start) * 1000
            return HealthCheckResult(
                component="ollama",
                status=HealthStatus.UNHEALTHY,
                message="Ollama request timeout",
                duration_ms=duration_ms,
                remediation=[
                    "Ollama may be hung or slow",
                    "Check: ps aux | grep ollama",
                    "Restart Ollama if needed"
                ]
            )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return HealthCheckResult(
                component="ollama",
                status=HealthStatus.UNHEALTHY,
                message=f"Error: {str(e)}",
                duration_ms=duration_ms,
                remediation=[
                    f"Ollama not accessible at {self.ollama_url}",
                    "Install Ollama: https://ollama.ai",
                    "Run: ollama serve"
                ]
            )

    async def check_deepseek_health(self) -> HealthCheckResult:
        """Check Deepseek/local model endpoint health"""
        start = time.time()

        try:
            # Try Ollama-compatible endpoint first
            response = await self.http_client.get(
                f"{self.deepseek_url}/api/tags",
                timeout=self.timeout
            )

            duration_ms = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])

                return HealthCheckResult(
                    component="deepseek",
                    status=HealthStatus.HEALTHY,
                    message=f"Deepseek endpoint healthy with {len(models)} model(s)",
                    duration_ms=duration_ms,
                    details={
                        "models": len(models),
                        "endpoint": self.deepseek_url
                    }
                )

        except httpx.TimeoutException:
            duration_ms = (time.time() - start) * 1000
            return HealthCheckResult(
                component="deepseek",
                status=HealthStatus.DEGRADED,
                message="Deepseek request timeout",
                duration_ms=duration_ms,
                remediation=[
                    "Model endpoint may be overloaded",
                    "Check system resources",
                    "Consider load balancing"
                ]
            )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return HealthCheckResult(
                component="deepseek",
                status=HealthStatus.UNKNOWN,
                message=f"Deepseek endpoint not accessible: {str(e)}",
                duration_ms=duration_ms,
                remediation=[
                    "Optional: Deepseek not needed if using Ollama",
                    f"If needed, run local endpoint at {self.deepseek_url}"
                ]
            )

    async def check_mcp_bridge_health(self) -> HealthCheckResult:
        """Check VETKA MCP bridge health"""
        start = time.time()

        try:
            response = await self.http_client.get(
                f"{self.mcp_bridge_url}/health",
                timeout=self.timeout
            )

            duration_ms = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()

                return HealthCheckResult(
                    component="mcp_bridge",
                    status=HealthStatus.HEALTHY,
                    message="MCP bridge operational",
                    duration_ms=duration_ms,
                    details=data
                )
            else:
                return HealthCheckResult(
                    component="mcp_bridge",
                    status=HealthStatus.UNHEALTHY,
                    message=f"MCP bridge returned {response.status_code}",
                    duration_ms=duration_ms,
                    remediation=[
                        f"Start MCP bridge: python -m src.mcp.vetka_mcp_bridge --http --port 5002"
                    ]
                )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return HealthCheckResult(
                component="mcp_bridge",
                status=HealthStatus.UNHEALTHY,
                message=f"Cannot connect to MCP bridge: {str(e)}",
                duration_ms=duration_ms,
                remediation=[
                    "Start VETKA MCP bridge",
                    f"Check if running on {self.mcp_bridge_url}",
                    "Check port availability"
                ]
            )

    async def run_diagnostic(self, level: DiagnosticLevel = DiagnosticLevel.STANDARD) -> Dict[str, Any]:
        """
        Run full diagnostic suite

        Args:
            level: Diagnostic detail level

        Returns:
            Comprehensive diagnostic report
        """
        start_time = time.time()
        results = []

        # Always run basic checks
        results.append(await self.check_ollama_health())
        results.append(await self.check_mcp_bridge_health())

        # Add optional checks based on level
        if level in [DiagnosticLevel.STANDARD, DiagnosticLevel.DEEP]:
            results.append(await self.check_deepseek_health())

        total_duration = (time.time() - start_time) * 1000

        # Aggregate status
        statuses = [r.status for r in results]
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return {
            "timestamp": datetime.now().isoformat(),
            "diagnostic_level": level.value,
            "overall_status": overall_status.value,
            "total_duration_ms": total_duration,
            "components": [
                {
                    "name": r.component,
                    "status": r.status.value,
                    "message": r.message,
                    "duration_ms": r.duration_ms,
                    "details": r.details,
                    "remediation": r.remediation
                }
                for r in results
            ]
        }

    async def shutdown(self):
        """Cleanup resources"""
        await self.http_client.aclose()
```

### Task 3.2: MCP Tool Integration
**File:** `src/mcp/tools/doctor_tool.py`
**Line:** At end of file (~400)

```python
# MARKER_106g_3_2: MCP tool wrapper for doctor
async def mcp_doctor_tool(diagnostic_level: str = "standard") -> Dict[str, Any]:
    """
    MCP-wrapped doctor tool endpoint

    Args:
        diagnostic_level: "quick", "standard", or "deep"

    Returns:
        Diagnostic report JSON
    """
    level = DiagnosticLevel(diagnostic_level.lower())
    doctor = DoctorTool()

    try:
        report = await doctor.run_diagnostic(level)
        return {
            "success": True,
            "report": report
        }
    finally:
        await doctor.shutdown()

def main():
    """CLI interface for doctor tool"""
    import argparse

    parser = argparse.ArgumentParser(description="VETKA System Doctor")
    parser.add_argument(
        "--level",
        choices=["quick", "standard", "deep"],
        default="standard",
        help="Diagnostic detail level"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Run diagnostic
    doctor = DoctorTool()
    report = asyncio.run(doctor.run_diagnostic(DiagnosticLevel(args.level)))

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        # Pretty print
        print(f"\nVETKA System Diagnostic Report")
        print(f"Time: {report['timestamp']}")
        print(f"Status: {report['overall_status'].upper()}")
        print()

        for component in report["components"]:
            status_symbol = "✓" if component["status"] == "healthy" else "✗"
            print(f"{status_symbol} {component['name']}: {component['status']}")
            print(f"  Message: {component['message']}")
            print(f"  Duration: {component['duration_ms']:.1f}ms")

            if component["remediation"]:
                print(f"  Actions:")
                for action in component["remediation"]:
                    print(f"    - {action}")

        print(f"\nTotal time: {report['total_duration_ms']:.1f}ms")

if __name__ == "__main__":
    main()
```

---

## Integration Points Summary

### Phase 106g Completion Checklist

- **MARKER_106g_1: OpenCode Proxy Bridge**
  - [ ] Create `src/mcp/opencode_proxy.py` with FastAPI proxy server
  - [ ] Implement MCP-to-OpenCode HTTP translation layer
  - [ ] Add OpenCodeMCPAgent wrapper class
  - [ ] Test with `uvicorn src.mcp.opencode_proxy:app --port 5003`
  - [ ] Add environment variables: `OPENCODE_API_KEY`, `OPENCODE_BASE_URL`, `OPENCODE_PROXY_PORT`

- **MARKER_106g_2: Cursor MCP Config Generator**
  - [ ] Create `src/mcp/tools/cursor_config_generator.py`
  - [ ] Implement `CursorMCPConfigGenerator` class
  - [ ] Generate Kilo-Code agent configuration
  - [ ] Generate Roo-Cline agent configuration
  - [ ] Add CLI interface for automation
  - [ ] Test with `python src/mcp/tools/cursor_config_generator.py --generate-all --apply`

- **MARKER_106g_3: Doctor Tool**
  - [ ] Create `src/mcp/tools/doctor_tool.py`
  - [ ] Implement `DoctorTool` class with three diagnostic levels
  - [ ] Add health checks for Ollama, Deepseek, MCP bridge
  - [ ] Implement remediation suggestions
  - [ ] Add MCP tool wrapper for integration
  - [ ] Test with `python src/mcp/tools/doctor_tool.py --level standard`

### Environment Variables (Phase 106g)

```bash
# OpenCode Proxy (for MARKER_106g_1)
OPENCODE_API_KEY=your-api-key
OPENCODE_BASE_URL=http://localhost:8080
OPENCODE_PROXY_PORT=5003

# Doctor Tool (for MARKER_106g_3)
OLLAMA_URL=http://localhost:11434
DEEPSEEK_URL=http://localhost:8000
MCP_BRIDGE_URL=http://localhost:5002
```

### Test Commands

```bash
# Test OpenCode proxy
curl -X POST http://localhost:5003/mcp \
  -H "Content-Type: application/json" \
  -d '{"call_type": "tool_call", "agent_id": "test", "session_id": "test-1", "payload": {"tool_name": "test_tool"}}'

# Generate Cursor configs
python src/mcp/tools/cursor_config_generator.py --generate-all --apply

# Run doctor diagnostic
python src/mcp/tools/doctor_tool.py --level standard --json
```

---

## References

- **OpenCode MCP Integration:** OpenCode has no native MCP but accepts HTTP calls
- **Cursor Native MCP:** Requires config in `~/.cursor/config/mcp/` for Kilo-Code and Roo-Cline
- **Ollama Health Monitoring:** Using `/api/tags` endpoint for model availability
- **Session Isolation:** All proxy requests include `session_id` for multi-tenant tracking

---

**Phase 106g Status:** MARKERS READY FOR IMPLEMENTATION
**Target Implementation:** Sonnet 3.5 with GPT-4 fallback for OpenCode proxy
**Estimated Effort:** 3-4 hours for full integration + testing
