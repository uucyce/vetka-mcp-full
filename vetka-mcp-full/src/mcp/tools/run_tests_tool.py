"""
Run tests tool - pytest/unittest execution.

@status: active
@phase: 96
@depends: base_tool, subprocess, pathlib, os
@used_by: mcp_server, stdio_server
"""
import subprocess
import os
from pathlib import Path
from typing import Any, Dict
from .base_tool import BaseMCPTool

PROJECT_ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


class RunTestsTool(BaseMCPTool):
    """Run pytest tests with timeout and output capture"""

    @property
    def name(self) -> str:
        return "vetka_run_tests"

    @property
    def description(self) -> str:
        return "Run pytest tests. Returns stdout/stderr/exit code."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "test_path": {
                    "type": "string",
                    "default": "tests/",
                    "description": "Path to test file or directory"
                },
                "pattern": {
                    "type": "string",
                    "default": "",
                    "description": "Test name pattern (-k flag)"
                },
                "verbose": {
                    "type": "boolean",
                    "default": True,
                    "description": "Verbose output"
                },
                "timeout": {
                    "type": "integer",
                    "default": 60,
                    "description": "Timeout in seconds (max 300)"
                }
            },
            "required": []
        }

    def validate_arguments(self, args: Dict[str, Any]) -> str:
        test_path = args.get("test_path", "tests/")
        if ".." in test_path:
            return "Path traversal not allowed"
        timeout = args.get("timeout", 60)
        if not isinstance(timeout, int):
            return "Timeout must be an integer"
        if timeout < 1 or timeout > 300:
            return "Timeout must be between 1 and 300 seconds"
        return None

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        test_path = arguments.get("test_path", "tests/")
        pattern = arguments.get("pattern", "")
        verbose = arguments.get("verbose", True)
        timeout = min(arguments.get("timeout", 60), 300)

        full_path = PROJECT_ROOT / test_path
        if not full_path.exists():
            return {"success": False, "error": f"Test path not found: {test_path}", "result": None}

        # Build pytest command
        cmd = ["python3", "-m", "pytest", str(full_path)]
        if verbose:
            cmd.append("-v")
        if pattern:
            cmd.extend(["-k", pattern])
        cmd.append("--tb=short")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
            )

            # Truncate long outputs
            stdout = result.stdout
            stderr = result.stderr
            if len(stdout) > 5000:
                stdout = stdout[:5000] + "\n... (output truncated)"
            if len(stderr) > 2000:
                stderr = stderr[:2000] + "\n... (stderr truncated)"

            return {
                "success": result.returncode == 0,
                "result": {
                    "passed": result.returncode == 0,
                    "returncode": result.returncode,
                    "stdout": stdout,
                    "stderr": stderr
                },
                "error": None if result.returncode == 0 else "Tests failed"
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Tests timed out after {timeout}s", "result": None}
        except FileNotFoundError:
            return {"success": False, "error": "pytest not found. Install with: pip install pytest", "result": None}
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}
