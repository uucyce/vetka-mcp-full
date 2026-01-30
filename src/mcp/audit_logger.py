"""
Audit logging for MCP tool calls.

@status: active
@phase: 96
@depends: json, datetime, pathlib
@used_by: mcp_server
"""
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path

PROJECT_ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


class MCPAuditLogger:
    """Log all MCP tool calls to audit file"""

    def __init__(self, log_dir: str = None):
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = PROJECT_ROOT / "data" / "mcp_audit"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file(self) -> Path:
        """Get today's log file"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"mcp_audit_{date_str}.jsonl"

    def log_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        client_id: str,
        success: bool,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None
    ):
        """Log a tool call"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "client_id": client_id,
            "tool": tool_name,
            "arguments": self._sanitize_args(arguments),
            "success": success,
            "duration_ms": round(duration_ms, 2) if duration_ms else None,
        }

        if error:
            entry["error"] = error

        # Don't log full results (could be huge), just summary
        if result and success:
            entry["result_summary"] = self._summarize_result(result)

        log_file = self._get_log_file()
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _sanitize_args(self, args: Dict) -> Dict:
        """Remove sensitive data from args"""
        sanitized = {}
        for k, v in args.items():
            if k in ("content", "password", "token", "api_key", "secret"):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, str) and len(v) > 500:
                sanitized[k] = v[:500] + "...[truncated]"
            else:
                sanitized[k] = v
        return sanitized

    def _summarize_result(self, result: Any) -> str:
        """Create short summary of result"""
        if isinstance(result, dict):
            if "count" in result:
                return f"count={result['count']}"
            if "items" in result:
                return f"items={len(result.get('items', []))}"
            if "status" in result:
                return f"status={result['status']}"
            keys = list(result.keys())[:5]
            return f"keys={keys}"
        return str(type(result).__name__)

    def get_recent_calls(self, limit: int = 100) -> list:
        """Get recent audit entries"""
        log_file = self._get_log_file()
        if not log_file.exists():
            return []

        entries = []
        with open(log_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        return entries[-limit:]

    def get_stats(self) -> Dict:
        """Get statistics for today's calls"""
        entries = self.get_recent_calls(1000)

        tools_count = {}
        success_count = 0
        error_count = 0
        total_duration = 0

        for entry in entries:
            tool = entry.get("tool", "unknown")
            tools_count[tool] = tools_count.get(tool, 0) + 1

            if entry.get("success"):
                success_count += 1
            else:
                error_count += 1

            if entry.get("duration_ms"):
                total_duration += entry["duration_ms"]

        return {
            "total_calls": len(entries),
            "success_count": success_count,
            "error_count": error_count,
            "tools_count": tools_count,
            "avg_duration_ms": round(total_duration / len(entries), 2) if entries else 0
        }


# Global audit logger
audit_logger = MCPAuditLogger()
