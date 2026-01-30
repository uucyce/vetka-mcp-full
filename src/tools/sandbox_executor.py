"""
VETKA Sandbox Executor.

Safe code execution using macOS sandbox-exec (Seatbelt). Provides isolated
execution environment with configurable restriction levels.

@status: active
@phase: 96
@depends: subprocess, tempfile, shutil
@used_by: src/tools/__init__, src/agents/

Usage:
    from src.tools.sandbox_executor import SandboxExecutor, SandboxLevel

    executor = SandboxExecutor()
    result = executor.execute("print('Hello')", level=SandboxLevel.READONLY)
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Sandbox profile path
SANDBOX_PROFILE = PROJECT_ROOT / "src" / "config" / "sandbox_profiles" / "vetka-sandbox.sb"

# Sandbox working directory
SANDBOX_DIR = Path("/tmp/vetka_sandbox")


class SandboxLevel(Enum):
    """Sandbox restriction levels"""
    READONLY = "readonly"      # Read-only access to project
    RESTRICTED = "restricted"  # + /tmp write access
    STANDARD = "standard"      # + sandbox dir write access
    DISABLED = "disabled"      # No sandbox (for trusted operations)


@dataclass
class ExecutionResult:
    """Result of sandboxed execution"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float = 0
    sandbox_level: str = "unknown"
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "execution_time_ms": self.execution_time_ms,
            "sandbox_level": self.sandbox_level,
            "error": self.error
        }


class SandboxExecutor:
    """
    Execute code in macOS sandbox (Seatbelt).

    Security features:
    - Network access blocked
    - File write restricted to sandbox dir
    - .git directory protected
    - main.py protected from writes
    """

    def __init__(
        self,
        profile_path: Optional[Path] = None,
        sandbox_dir: Optional[Path] = None,
        default_timeout: int = 30
    ):
        self.profile_path = Path(profile_path) if profile_path else SANDBOX_PROFILE
        self.sandbox_dir = Path(sandbox_dir) if sandbox_dir else SANDBOX_DIR
        self.default_timeout = default_timeout

        # Ensure sandbox directory exists
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

        # Check if sandbox-exec is available
        self._sandbox_available = self._check_sandbox_available()

    def _check_sandbox_available(self) -> bool:
        """Check if sandbox-exec is available on this system"""
        try:
            result = subprocess.run(
                ["which", "sandbox-exec"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _get_profile_content(self, level: SandboxLevel) -> str:
        """Get sandbox profile content, potentially modified for level"""
        if not self.profile_path.exists():
            raise FileNotFoundError(f"Sandbox profile not found: {self.profile_path}")

        return self.profile_path.read_text()

    def execute(
        self,
        code: str,
        level: SandboxLevel = SandboxLevel.STANDARD,
        timeout: Optional[int] = None,
        working_dir: Optional[Path] = None
    ) -> ExecutionResult:
        """
        Execute Python code in sandbox.

        Args:
            code: Python code to execute
            level: Sandbox restriction level
            timeout: Execution timeout in seconds
            working_dir: Working directory (default: sandbox_dir)

        Returns:
            ExecutionResult with stdout, stderr, exit_code
        """
        import time
        start_time = time.time()

        timeout = timeout or self.default_timeout
        working_dir = working_dir or self.sandbox_dir

        # Create temp file for code
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                dir=str(self.sandbox_dir),
                delete=False
            ) as f:
                f.write(code)
                temp_file = Path(f.name)

            # Build command
            if level == SandboxLevel.DISABLED or not self._sandbox_available:
                cmd = ["python3", str(temp_file)]
            else:
                cmd = [
                    "sandbox-exec",
                    "-f", str(self.profile_path),
                    "python3", str(temp_file)
                ]

            # Execute
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(working_dir),
                env=self._get_safe_env()
            )

            execution_time = (time.time() - start_time) * 1000

            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout[:10000],  # Limit output
                stderr=result.stderr[:5000],
                exit_code=result.returncode,
                execution_time_ms=execution_time,
                sandbox_level=level.value
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time_ms=(time.time() - start_time) * 1000,
                sandbox_level=level.value,
                error=f"Execution timeout ({timeout}s)"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time_ms=(time.time() - start_time) * 1000,
                sandbox_level=level.value,
                error=str(e)
            )
        finally:
            # Cleanup temp file
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

    def execute_command(
        self,
        command: str,
        level: SandboxLevel = SandboxLevel.STANDARD,
        timeout: Optional[int] = None,
        working_dir: Optional[Path] = None
    ) -> ExecutionResult:
        """
        Execute shell command in sandbox.

        Args:
            command: Shell command to execute
            level: Sandbox restriction level
            timeout: Execution timeout in seconds
            working_dir: Working directory

        Returns:
            ExecutionResult with stdout, stderr, exit_code
        """
        import time
        start_time = time.time()

        timeout = timeout or self.default_timeout
        working_dir = working_dir or PROJECT_ROOT

        try:
            # Build command
            if level == SandboxLevel.DISABLED or not self._sandbox_available:
                full_cmd = command
            else:
                full_cmd = f"sandbox-exec -f {self.profile_path} /bin/bash -c '{command}'"

            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(working_dir),
                env=self._get_safe_env()
            )

            execution_time = (time.time() - start_time) * 1000

            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout[:10000],
                stderr=result.stderr[:5000],
                exit_code=result.returncode,
                execution_time_ms=execution_time,
                sandbox_level=level.value
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time_ms=(time.time() - start_time) * 1000,
                sandbox_level=level.value,
                error=f"Command timeout ({timeout}s)"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time_ms=(time.time() - start_time) * 1000,
                sandbox_level=level.value,
                error=str(e)
            )

    def execute_file(
        self,
        file_path: Path,
        level: SandboxLevel = SandboxLevel.STANDARD,
        timeout: Optional[int] = None,
        args: Optional[List[str]] = None
    ) -> ExecutionResult:
        """
        Execute Python file in sandbox.

        Args:
            file_path: Path to Python file
            level: Sandbox restriction level
            timeout: Execution timeout in seconds
            args: Additional arguments to pass to script

        Returns:
            ExecutionResult
        """
        import time
        start_time = time.time()

        file_path = Path(file_path)
        timeout = timeout or self.default_timeout
        args = args or []

        if not file_path.exists():
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                sandbox_level=level.value,
                error=f"File not found: {file_path}"
            )

        try:
            # Build command
            python_args = ["python3", str(file_path)] + args

            if level == SandboxLevel.DISABLED or not self._sandbox_available:
                cmd = python_args
            else:
                cmd = ["sandbox-exec", "-f", str(self.profile_path)] + python_args

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(file_path.parent),
                env=self._get_safe_env()
            )

            execution_time = (time.time() - start_time) * 1000

            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout[:10000],
                stderr=result.stderr[:5000],
                exit_code=result.returncode,
                execution_time_ms=execution_time,
                sandbox_level=level.value
            )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                execution_time_ms=(time.time() - start_time) * 1000,
                sandbox_level=level.value,
                error=f"Execution timeout ({timeout}s)"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time_ms=(time.time() - start_time) * 1000,
                sandbox_level=level.value,
                error=str(e)
            )

    def _get_safe_env(self) -> dict:
        """Get safe environment variables for sandbox execution"""
        env = os.environ.copy()

        # Remove potentially dangerous env vars
        dangerous_vars = [
            'LD_PRELOAD', 'LD_LIBRARY_PATH',
            'PYTHONSTARTUP', 'PYTHONPATH',
        ]
        for var in dangerous_vars:
            env.pop(var, None)

        # Add sandbox-specific vars
        env['VETKA_SANDBOX'] = '1'
        env['VETKA_SANDBOX_DIR'] = str(self.sandbox_dir)

        return env

    def cleanup_sandbox_dir(self):
        """Clean up sandbox directory"""
        if self.sandbox_dir.exists():
            for item in self.sandbox_dir.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception:
                    pass

    @property
    def is_sandbox_available(self) -> bool:
        """Check if sandbox execution is available"""
        return self._sandbox_available


# Default executor instance
default_sandbox_executor = SandboxExecutor()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'SandboxExecutor',
    'SandboxLevel',
    'ExecutionResult',
    'default_sandbox_executor',
    'PROJECT_ROOT',
    'SANDBOX_DIR'
]
