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
