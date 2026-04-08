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

    # MARKER_113_1: Real API key verification via HTTP
    async def _verify_key_with_api(self, provider: str, key: str) -> Dict[str, Any]:
        """
        Actually test if API key works by making a real HTTP request.

        Phase 113: Real validation instead of just syntax check.
        Returns dict with 'valid', 'status_code', 'error' fields.
        """
        # Provider-specific endpoints for key verification
        # Phase 111.10.1: Fixed URLs and added missing providers
        endpoints = {
            'openrouter': 'https://openrouter.ai/api/v1/auth/key',
            'openai': 'https://api.openai.com/v1/models',
            'gemini': 'https://generativelanguage.googleapis.com/v1/models',
            'poe': 'https://api.poe.com/v1/models',
            'polza': 'https://api.polza.ai/api/v1/models',  # Fixed: polza.io -> polza.ai
            'xai': 'https://api.x.ai/v1/models',
            'anthropic': 'https://api.anthropic.com/v1/models',
            'perplexity': 'https://api.perplexity.ai/chat/completions',
            'mistral': 'https://api.mistral.ai/v1/models',  # Added Phase 111.10.1
            'nanogpt': 'https://api.nano-gpt.com/v1/models',  # Added Phase 111.10.1
            'tavily': 'https://api.tavily.com/search',  # Added Phase 111.10.1 (search API)
        }

        url = endpoints.get(provider)
        if not url:
            return {'valid': None, 'status_code': None, 'error': f'Unknown provider: {provider}'}

        try:
            # Build headers based on provider
            if provider == 'gemini':
                # Gemini uses API key in URL param
                url = f"{url}?key={key}"
                headers = {}
            elif provider == 'anthropic':
                headers = {
                    'x-api-key': key,
                    'anthropic-version': '2023-06-01'
                }
            else:
                # Most providers use Bearer token
                headers = {'Authorization': f'Bearer {key}'}

            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                resp = await client.get(url, headers=headers)

                # 200 = valid key, 401/403 = invalid key, other = service issue
                if resp.status_code == 200:
                    return {'valid': True, 'status_code': 200, 'error': None}
                elif resp.status_code in [401, 403]:
                    return {'valid': False, 'status_code': resp.status_code, 'error': 'Invalid or expired key'}
                else:
                    # Service issue, not key issue
                    return {'valid': None, 'status_code': resp.status_code, 'error': f'Service returned {resp.status_code}'}

        except httpx.TimeoutException:
            return {'valid': None, 'status_code': None, 'error': 'Timeout'}
        except Exception as e:
            return {'valid': None, 'status_code': None, 'error': str(e)}

    # MARKER_111_1: API Keys health check - Phase 111
    async def check_api_keys_health(self, verify_http: bool = False) -> HealthCheckResult:
        """
        Check API keys status and availability.

        Phase 111: Validates configured API keys for all providers.
        Phase 113: Added verify_http=True for real HTTP validation.
        Returns DEGRADED if any provider has no available keys.

        Args:
            verify_http: If True, actually test keys with HTTP requests (slower but accurate)
        """
        start = time.time()

        try:
            from src.utils.unified_key_manager import get_key_manager

            km = get_key_manager()
            stats = km.get_stats()

            issues = []
            total_keys = stats.get('total_keys', 0)
            available_keys = stats.get('available_keys', 0)
            rate_limited = total_keys - available_keys

            # Check provider availability from validate_keys()
            providers_available = stats.get('providers_available', {})
            providers_checked = len(providers_available)
            providers_healthy = sum(1 for v in providers_available.values() if v)

            # Phase 113: Real HTTP verification if requested
            http_results = {}
            if verify_http:
                # Get actual keys for HTTP verification
                provider_keys = km.get_all_keys() if hasattr(km, 'get_all_keys') else {}

                for provider_name in providers_available.keys():
                    key = provider_keys.get(provider_name) or km.get_key(provider_name) if hasattr(km, 'get_key') else None
                    if key:
                        result = await self._verify_key_with_api(provider_name, key)
                        http_results[provider_name] = result

                        if result.get('valid') is False:
                            issues.append(f"{provider_name}: key invalid (HTTP {result.get('status_code')})")
                            providers_available[provider_name] = False
                        elif result.get('valid') is True:
                            # Confirmed working via HTTP
                            pass
                        else:
                            # Could not verify (timeout/error) - keep syntax validation
                            if result.get('error'):
                                issues.append(f"{provider_name}: could not verify ({result.get('error')})")

                # Recalculate healthy count after HTTP verification
                providers_healthy = sum(1 for v in providers_available.values() if v)

            # Build issues list for providers without keys
            for provider_name, is_available in providers_available.items():
                if not is_available and provider_name not in [i.split(':')[0] for i in issues]:
                    issues.append(f"{provider_name}: no available keys")

            # Determine overall status
            if total_keys == 0:
                status = HealthStatus.UNHEALTHY
                message = "No API keys configured"
            elif available_keys == 0:
                status = HealthStatus.UNHEALTHY
                message = f"All {total_keys} keys rate-limited"
            elif issues:
                status = HealthStatus.DEGRADED
                message = f"{providers_healthy}/{providers_checked} providers healthy, {available_keys}/{total_keys} keys available"
            else:
                status = HealthStatus.HEALTHY
                message = f"All {providers_checked} providers healthy with {total_keys} keys"

            # Phase 113: Add verification method to message
            if verify_http:
                message += " (HTTP verified)"

            duration = (time.time() - start) * 1000

            return HealthCheckResult(
                component="api_keys",
                status=status,
                message=message,
                duration_ms=duration,
                details={
                    'total_keys': total_keys,
                    'available_keys': available_keys,
                    'rate_limited_keys': rate_limited,
                    'providers_checked': providers_checked,
                    'providers_healthy': providers_healthy,
                    'openrouter_keys': stats.get('openrouter_keys', 0),
                    'http_verification': http_results if verify_http else None,
                    'verification_method': 'http' if verify_http else 'syntax'
                },
                remediation=issues if issues else None
            )

        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"API keys health check failed: {e}")
            return HealthCheckResult(
                component="api_keys",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check keys: {str(e)}",
                duration_ms=duration,
                remediation=["Check unified_key_manager configuration"]
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
            # Phase 113: Use HTTP verification for DEEP level
            verify_http = (level == DiagnosticLevel.DEEP)
            results.append(await self.check_api_keys_health(verify_http=verify_http))

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
