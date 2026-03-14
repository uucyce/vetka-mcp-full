"""
VETKA Agent Tools - Function Calling Interface.

Provides tool implementations for agent function calling.
Includes search, execution, CAM tools, and agent permission system.

@file tools.py
@status: active
@phase: 96
@depends: subprocess, json, glob, ast, pathlib, dataclasses,
          src.tools.base_tool (BaseTool, ToolDefinition, ToolResult, registry),
          src.tools.sandbox_executor.SandboxExecutor,
          src.orchestration.cam_engine, src.memory.elision, src.memory.compression
@used_by: src/orchestration/orchestrator_with_elisya.py,
          src/api/handlers/user_message_handler.py,
          src/agents/hostess_agent.py,
          src/mcp/mcp_server.py, src/mcp/stdio_server.py,
          tests/test_agent_tools.py, tests/test_mcp_server.py

This module provides:
1. Extended tool definitions beyond basic code tools
2. Agent-specific tool permissions (PM, Dev, QA, Hostess, Researcher)
3. Weaviate/Qdrant search integration
4. Code validation and test execution
5. CAM tools (CalculateSurprise, CompressWithElision, AdaptiveMemorySizing)
"""

import os
import asyncio
import subprocess
import json
import sys
import glob as glob_module
import ast
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

# Import base tool framework
from src.tools.base_tool import (
    BaseTool,
    ToolDefinition,
    ToolResult,
    PermissionLevel,
    registry,
)
from src.services.reflex_tool_memory import (
    list_reflex_tool_memory,
    remember_reflex_tool,
)
from src.services.reflex_registry import reset_reflex_registry
from src.services.local_qwen_model_selector import get_best_local_qwen_model

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


# ============================================================================
# PHASE 19 CACHING - Embedding Model & Search Results
# ============================================================================

# Module-level cache for embedding model (singleton pattern)
_embedding_model_cache: Dict[str, Any] = {
    "model": None,
    "model_name": None,
    "loaded_at": None,
}

# Search results cache with TTL
_search_cache: Dict[str, Dict[str, Any]] = {}
_SEARCH_CACHE_TTL = 300  # 5 minutes


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    """
    Get cached embedding model or load it.
    Singleton pattern to avoid reloading on every search.
    """
    global _embedding_model_cache

    if (
        _embedding_model_cache["model"] is not None
        and _embedding_model_cache["model_name"] == model_name
    ):
        return _embedding_model_cache["model"]

    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
        _embedding_model_cache = {
            "model": model,
            "model_name": model_name,
            "loaded_at": datetime.now().isoformat(),
        }
        print(f"      Embedding model '{model_name}' loaded and cached")
        return model
    except ImportError:
        print("      sentence-transformers not installed")
        return None
    except Exception as e:
        print(f"      Failed to load embedding model: {e}")
        return None


def get_cached_search(cache_key: str) -> Optional[Dict]:
    """Get cached search result if not expired."""
    if cache_key in _search_cache:
        cached = _search_cache[cache_key]
        age = (
            datetime.now() - datetime.fromisoformat(cached["timestamp"])
        ).total_seconds()
        if age < _SEARCH_CACHE_TTL:
            print(f"      [CACHE] HIT: {cache_key[:50]}... (age: {age:.1f}s)")
            return cached["result"]
        else:
            print(
                f"      [CACHE] EXPIRED: {cache_key[:50]}... (age: {age:.1f}s > TTL {_SEARCH_CACHE_TTL}s)"
            )
            del _search_cache[cache_key]
    else:
        print(f"      [CACHE] MISS: {cache_key[:50]}...")
    return None


def set_search_cache(cache_key: str, result: Dict):
    """Cache search result with timestamp."""
    _search_cache[cache_key] = {
        "result": result,
        "timestamp": datetime.now().isoformat(),
    }
    print(
        f"      [CACHE] SET: {cache_key[:50]}... (total cached: {len(_search_cache)})"
    )
    # Cleanup old entries (keep max 100)
    if len(_search_cache) > 100:
        oldest_keys = sorted(
            _search_cache.keys(), key=lambda k: _search_cache[k]["timestamp"]
        )[:50]
        for k in oldest_keys:
            del _search_cache[k]
        print(f"      [CACHE] CLEANUP: removed {len(oldest_keys)} old entries")


# ============================================================================
# ADDITIONAL TOOL IMPLEMENTATIONS
# ============================================================================


class SearchCodebaseTool(BaseTool):
    """Search for pattern in codebase using grep"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_codebase",
            description="Search for text/pattern in codebase using grep. Returns matching lines with file paths.",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (regex supported)",
                    },
                    "file_type": {
                        "type": "string",
                        "description": "File extension to search (e.g., 'py', 'js'). Default: all files",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in. Default: project root",
                    },
                },
                "required": ["pattern"],
            },
            permission_level=PermissionLevel.READ,
            needs_user_approval=False,
        )

    async def execute(
        self, pattern: str, file_type: str = None, path: str = "."
    ) -> ToolResult:
        try:
            search_path = PROJECT_ROOT / path
            if not search_path.resolve().is_relative_to(PROJECT_ROOT):
                return ToolResult(
                    success=False, result=None, error="Path traversal detected"
                )

            # Build grep command
            include_flag = f"--include='*.{file_type}'" if file_type else ""
            cmd = f"grep -rn '{pattern}' {include_flag} {search_path} 2>/dev/null | head -50"

            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(PROJECT_ROOT),
            )

            matches = []
            for line in result.stdout.split("\n")[:50]:
                if ":" in line:
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        matches.append(
                            {
                                "file": parts[0],
                                "line": parts[1],
                                "content": parts[2][:200],
                            }
                        )

            return ToolResult(
                success=True, result=matches if matches else "No matches found"
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, result=None, error="Search timeout")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


class ExecuteCodeTool(BaseTool):
    """
    Execute shell commands safely with optional sandbox.
    Phase 20: Enhanced with macOS sandbox-exec support.

    Security features:
    - Case-insensitive pattern matching
    - Blocks absolute paths to dangerous binaries
    - Blocks shell metacharacters for command injection
    """

    # Commands blocked for security (checked case-insensitive)
    BLOCKED_PATTERNS = [
        "rm -rf",
        "rm -r",  # Recursive delete (any case: rm -RF, RM -rf, etc.)
        "sudo",
        "su ",  # Privilege escalation
        "chmod 777",
        "chmod +x",  # Permission changes
        "chown",
        "chgrp",  # Ownership changes
        "> /dev",
        "mkfs",
        "dd if=",  # Destructive operations
        "curl | sh",
        "wget | sh",  # Remote code execution
        "curl | bash",
        "wget | bash",
        ":(){ :|:& };:",  # Fork bomb
        "eval ",
        "exec ",  # Code execution
        "`",
        "$(",  # Command substitution
        "&& rm",
        "; rm",  # Chained destructive commands
    ]

    # Dangerous binaries (absolute paths)
    DANGEROUS_BINARIES = [
        "/bin/rm",
        "/usr/bin/rm",
        "/bin/sudo",
        "/usr/bin/sudo",
        "/bin/su",
        "/usr/bin/su",
        "/bin/chmod",
        "/usr/bin/chmod",
        "/bin/chown",
        "/usr/bin/chown",
        "/sbin/mkfs",
        "/usr/sbin/mkfs",
        "/bin/dd",
        "/usr/bin/dd",
    ]

    # Commands that are safe to run without sandbox
    SAFE_COMMANDS = [
        "python -m pytest",
        "pytest",
        "python -m py_compile",
        "git status",
        "git diff",
        "git log",
        "git branch",
        "ls",
        "cat",
        "head",
        "tail",
        "grep",
        "find",
        "pip show",
        "pip list",
    ]

    def __init__(self):
        self._sandbox_executor = None

    @property
    def sandbox_executor(self):
        """Lazy-load sandbox executor to avoid import issues"""
        if self._sandbox_executor is None:
            try:
                from src.tools.sandbox_executor import SandboxExecutor

                self._sandbox_executor = SandboxExecutor()
            except ImportError:
                self._sandbox_executor = None
        return self._sandbox_executor

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="execute_code",
            description="Execute a shell command. Use for running tests, builds, Python scripts, etc. Commands run in sandbox by default for security.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30, max: 120)",
                    },
                    "sandbox": {
                        "type": "boolean",
                        "description": "Run in sandbox (default: true). Set to false for trusted commands.",
                    },
                },
                "required": ["command"],
            },
            permission_level=PermissionLevel.EXECUTE,
            needs_user_approval=True,  # Requires confirmation!
        )

    def _is_safe_command(self, command: str) -> bool:
        """Check if command is in safe list"""
        for safe in self.SAFE_COMMANDS:
            if command.strip().startswith(safe):
                return True
        return False

    def _is_dangerous_command(self, command: str) -> Optional[str]:
        """
        Check if command contains dangerous patterns.
        Returns the matched pattern or None if safe.

        Uses case-insensitive matching and checks absolute paths.
        """
        command_lower = command.lower()

        # Check blocked patterns (case-insensitive)
        for blocked in self.BLOCKED_PATTERNS:
            if blocked.lower() in command_lower:
                return blocked

        # Check absolute paths to dangerous binaries
        for binary in self.DANGEROUS_BINARIES:
            if binary in command:
                return binary

        return None

    async def execute(
        self, command: str, timeout: int = 30, sandbox: bool = True
    ) -> ToolResult:
        try:
            # Security check - block dangerous patterns (case-insensitive)
            dangerous = self._is_dangerous_command(command)
            if dangerous:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Blocked dangerous command pattern: {dangerous}",
                )

            # Limit timeout
            timeout = min(timeout, 120)

            # Determine if we should use sandbox
            use_sandbox = sandbox and self.sandbox_executor is not None

            # Safe commands can skip sandbox for performance
            if self._is_safe_command(command):
                use_sandbox = False

            if use_sandbox:
                # Use sandbox executor
                from src.tools.sandbox_executor import SandboxLevel

                sandbox_result = self.sandbox_executor.execute_command(
                    command=command,
                    level=SandboxLevel.STANDARD,
                    timeout=timeout,
                    working_dir=PROJECT_ROOT,
                )

                output = sandbox_result.stdout
                if sandbox_result.stderr:
                    output += f"\n[STDERR]: {sandbox_result.stderr}"

                return ToolResult(
                    success=sandbox_result.success,
                    result={
                        "output": output[:10000],
                        "sandbox": True,
                        "sandbox_level": sandbox_result.sandbox_level,
                        "execution_time_ms": sandbox_result.execution_time_ms,
                    },
                    error=sandbox_result.error if not sandbox_result.success else None,
                )
            else:
                # Run without sandbox (legacy behavior)
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(PROJECT_ROOT),
                )

                output = result.stdout
                if result.stderr:
                    output += f"\n[STDERR]: {result.stderr}"

                return ToolResult(
                    success=result.returncode == 0,
                    result={
                        "output": output[:10000],
                        "sandbox": False,
                        "exit_code": result.returncode,
                    },
                    error=None
                    if result.returncode == 0
                    else f"Exit code: {result.returncode}",
                )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False, result=None, error=f"Command timeout ({timeout}s)"
            )
        except Exception as e:
            return ToolResult(success=False, result={}, error=str(e))

class CalculateSurpriseTool(BaseTool):
    """
    Calculate surprise/novelty score for content using CAM engine.
    Phase 76.4: CAM Tool for detecting novel information.
    Phase 92: Restored after Big Pickle deletion.
    """

    def __init__(self):
        self._name = "calculate_surprise"
        self._description = (
            "Calculate surprise/novelty score for content to detect new information"
        )
        self._permission = PermissionLevel.READ

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self._name,
            description=self._description,
            parameters={
                "type": "object",
                "properties": {
                    "context": {
                        "type": "string",
                        "description": "Content/context to analyze for novelty",
                    },
                    "baseline": {
                        "type": "string",
                        "description": "Optional baseline to compare against",
                        "default": None,
                    },
                },
                "required": ["context"],
            },
            permission_level=self._permission,
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Calculate surprise score using CAM engine"""
        context = kwargs.get("context", "")
        baseline = kwargs.get("baseline")

        try:
            # Import CAM engine for surprise calculation
            from src.orchestration.cam_engine import calculate_surprise

            # Calculate surprise score
            surprise_score = calculate_surprise(context, baseline)

            return ToolResult(
                success=True,
                result={
                    "surprise_score": surprise_score,
                    "interpretation": self._interpret_surprise(surprise_score),
                    "context_length": len(context),
                    "baseline_provided": baseline is not None,
                },
            )
        except ImportError as e:
            # Fallback: simple entropy-based surprise
            import math

            chars = set(context)
            entropy = -sum(
                (context.count(c) / len(context)) * math.log2(context.count(c) / len(context))
                for c in chars
                if context.count(c) > 0
            ) if context else 0
            normalized = min(entropy / 5.0, 1.0)  # Normalize to 0-1

            return ToolResult(
                success=True,
                result={
                    "surprise_score": normalized,
                    "interpretation": self._interpret_surprise(normalized),
                    "context_length": len(context),
                    "_fallback": True,
                    "_fallback_reason": str(e),
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def _interpret_surprise(self, score: float) -> str:
        """Interpret surprise score for agents"""
        if score > 0.8:
            return "Highly novel - significant new information"
        elif score > 0.6:
            return "Moderately novel - some new insights"
        elif score > 0.4:
            return "Low novelty - mostly familiar"
        else:
            return "Very low novelty - routine information"


class CompressWithElisionTool(BaseTool):
    """Compress context using ELISION path compression"""

    def __init__(self):
        self._name = "compress_with_elision"
        self._description = (
            "Compress context using ELISION path compression to reduce token usage"
        )
        self._permission = PermissionLevel.READ

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self._name,
            description=self._description,
            parameters={
                "type": "object",
                "properties": {
                    "context": {
                        "type": "string",
                        "description": "Context text to compress",
                    },
                    "target_ratio": {
                        "type": "number",
                        "description": "Target compression ratio (0.1-0.9)",
                        "default": 0.5,
                    },
                },
                "required": ["context"],
            },
            permission_level=self._permission,
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Compress context using ELISION - Phase 92 Implementation"""
        context = kwargs.get("context", "")
        target_ratio = kwargs.get("target_ratio", 0.5)

        try:
            # Phase 92: Use real ELISION compression
            from src.memory.elision import get_elision_compressor

            compressor = get_elision_compressor()

            # Determine compression level based on target_ratio
            # Lower ratio = more aggressive compression = higher level
            if target_ratio <= 0.3:
                level = 4  # Maximum compression with local dictionary
            elif target_ratio <= 0.5:
                level = 3  # Whitespace removal
            elif target_ratio <= 0.7:
                level = 2  # Path compression
            else:
                level = 1  # Keys only

            result = compressor.compress(
                context, level=level, target_ratio=target_ratio
            )

            return ToolResult(
                success=True,
                result={
                    "compressed_context": result.compressed,
                    "original_length": result.original_length,
                    "compressed_length": result.compressed_length,
                    "compression_ratio": result.compression_ratio,
                    "tokens_saved": result.tokens_saved_estimate,
                    "compression_level": result.level,
                    "_legend": result.legend if result.legend else None,
                },
            )
        except ImportError:
            # Fallback to simple truncation if elision module not available
            target_length = int(len(context) * target_ratio)
            compressed = (
                context[:target_length] + "... [compressed]"
                if target_length < len(context)
                else context
            )
            return ToolResult(
                success=True,
                result={
                    "compressed_context": compressed,
                    "original_length": len(context),
                    "compressed_length": len(compressed),
                    "compression_ratio": len(context) / len(compressed)
                    if compressed
                    else 1.0,
                    "tokens_saved": len(context) - len(compressed),
                    "compression_level": 0,
                    "_fallback": True,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class AdaptiveMemorySizingTool(BaseTool):
    """Dynamically adjust memory based on content"""

    def __init__(self):
        self._name = "adaptive_memory_sizing"
        self._description = (
            "Dynamically adjust memory allocation based on content complexity"
        )
        self._permission = PermissionLevel.READ

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self._name,
            description=self._description,
            parameters={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Content to analyze for complexity",
                    },
                    "current_limit": {
                        "type": "number",
                        "description": "Current memory limit in tokens",
                        "default": 4000,
                    },
                },
                "required": ["content"],
            },
            permission_level=self._permission,
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Adaptive memory sizing based on content"""
        content = kwargs.get("content", "")
        current_limit = kwargs.get("current_limit", 4000)
        try:
            # Import memory analysis
            from src.memory.compression import analyze_content_complexity

            # Analyze content complexity - returns dict with complexity_score
            complexity_result = analyze_content_complexity(content)
            complexity_score = complexity_result.get("complexity_score", 0.5)

            # Calculate optimal memory allocation
            base_size = 4000  # Default context size
            complexity_multiplier = 0.5 + (
                complexity_score * 1.5
            )  # 0.5x to 2x based on complexity
            optimal_size = int(base_size * complexity_multiplier)

            # If current_limit provided, compare with optimal
            if current_limit:
                adjustment = "increase" if optimal_size > current_limit else "decrease"
                difference = abs(optimal_size - current_limit)
            else:
                adjustment = "recommend"
                difference = optimal_size

            return ToolResult(
                success=True,
                result={
                    "content_complexity": complexity_score,
                    "complexity_details": complexity_result,
                    "optimal_context_size": optimal_size,
                    "current_limit": current_limit,
                    "recommended_adjustment": adjustment,
                    "size_difference": difference,
                    "complexity_level": self._interpret_complexity(complexity_score),
                },
            )
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _interpret_complexity(self, score: float) -> str:
        """Interpret complexity score"""
        if score > 0.8:
            return "High complexity - needs more memory"
        elif score > 0.6:
            return "Medium-high complexity - consider memory increase"
        elif score > 0.4:
            return "Medium complexity - standard memory adequate"
        else:
            return "Low complexity - can reduce memory allocation"


# MARKER_114.1_REGISTER_MISSING: Register tools that had classes but no register() calls
registry.register(SearchCodebaseTool())
registry.register(ExecuteCodeTool())

# Register CAM tools
registry.register(CalculateSurpriseTool())
registry.register(CompressWithElisionTool())
registry.register(AdaptiveMemorySizingTool())


# ============================================================================
# PHASE 97: ARC SUGGEST TOOL
# ============================================================================


class ARCSuggestTool(BaseTool):
    """
    ARC (Adaptive Reasoning Context) Suggest Tool.

    Provides creative workflow suggestions and connection ideas.
    Available to: PM, Architect, Researcher, Hostess (NOT Dev/QA - they execute, not plan)

    @status: active
    @phase: 97
    @depends: src.agents.arc_solver_agent.ARCSolverAgent
    @used_by: PM, Architect, Researcher, Hostess agents in group chat
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="arc_suggest",
            description="Get creative suggestions for workflow improvements, "
                       "architectural connections, or research directions. "
                       "Use when stuck or need fresh ideas. Returns JSON with suggestions.",
            parameters={
                "type": "object",
                "properties": {
                    "context": {
                        "type": "string",
                        "description": "Current task/problem description (what you're working on)",
                    },
                    "focus": {
                        "type": "string",
                        "enum": ["architecture", "workflow", "research", "general"],
                        "description": "Type of suggestions needed",
                        "default": "general",
                    },
                    "num_suggestions": {
                        "type": "integer",
                        "description": "Number of suggestions to return (1-5)",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 5,
                    },
                },
                "required": ["context"],
            },
            permission_level=PermissionLevel.READ,  # Low risk - read-only suggestions
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute ARC suggestion generation."""
        try:
            context = kwargs.get("context", "")
            focus = kwargs.get("focus", "general")
            num_suggestions = min(max(kwargs.get("num_suggestions", 3), 1), 5)

            if not context:
                return ToolResult(
                    success=False,
                    result=None,
                    error="Context is required for ARC suggestions",
                )

            # Import ARC solver
            try:
                from src.agents.arc_solver_agent import ARCSolverAgent
            except ImportError as e:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"ARCSolverAgent not available: {e}",
                )

            # Create minimal graph for suggestions
            arc_solver = ARCSolverAgent(use_api=False, learner=None)

            graph_data = {
                "nodes": [
                    {"id": "current_task", "type": "task", "label": context[:100]},
                    {"id": focus, "type": "focus", "label": focus},
                ],
                "edges": [],
            }

            # Get suggestions
            arc_result = arc_solver.suggest_connections(
                workflow_id=f"chat_arc_{focus}",
                graph_data=graph_data,
                task_context=context,
                num_candidates=num_suggestions,
                min_score=0.3,
            )

            suggestions = arc_result.get("top_suggestions", [])

            if not suggestions:
                return ToolResult(
                    success=True,
                    result={
                        "suggestions": [],
                        "message": "No strong suggestions found. Try rephrasing the context.",
                        "focus": focus,
                    },
                )

            # Format suggestions
            formatted = []
            for idx, s in enumerate(suggestions[:num_suggestions], 1):
                formatted.append({
                    "id": idx,
                    "idea": s.get("explanation", "No explanation"),
                    "confidence": round(s.get("score", 0.0), 2),
                    "type": s.get("type", focus),
                })

            return ToolResult(
                success=True,
                result={
                    "suggestions": formatted,
                    "count": len(formatted),
                    "focus": focus,
                    "context_preview": context[:200] + "..." if len(context) > 200 else context,
                },
            )

        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


# Register ARC tool
registry.register(ARCSuggestTool())


# ============================================================================
# API KEY MANAGEMENT TOOLS - Phase 110 (FIX_110.3)
# ============================================================================

class SaveAPIKeyTool(BaseTool):
    """
    Save API key with auto-detection of provider.
    Phase 57.1: Accept API keys via chat.
    FIX_110.3: Implemented missing tool class.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="save_api_key",
            description="Save an API key with automatic provider detection (OpenAI, Anthropic, Groq, etc.)",
            parameters={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "The API key to save",
                    },
                    "provider": {
                        "type": "string",
                        "description": "Force specific provider (optional, auto-detected if not provided)",
                    },
                },
                "required": ["key"],
            },
            permission_level=PermissionLevel.WRITE,
            needs_user_approval=False,
        )

    async def execute(self, key: str, provider: str = None) -> ToolResult:
        try:
            from src.elisya.api_key_detector import detect_api_key
            from src.elisya.key_learner import get_key_learner

            # Mask key for logging
            key_preview = f"{key[:8]}****" if len(key) > 12 else "****"

            # Detect provider if not specified
            if provider:
                detected = {"provider": provider, "display_name": provider.title(), "confidence": 1.0}
            else:
                detected = detect_api_key(key)

                # Fallback to learned patterns
                if not detected or not detected.get("provider"):
                    learner = get_key_learner()
                    learned = learner.check_learned_pattern(key)
                    if learned:
                        detected = learned
                        detected["source"] = "learned"

            if not detected or not detected.get("provider"):
                # Unknown key - analyze and return info
                learner = get_key_learner()
                analysis = learner.analyze_key(key)
                return ToolResult(
                    success=True,
                    result={
                        "saved": False,
                        "detected": False,
                        "analysis": analysis,
                        "message": "Unknown key type. Please specify provider or use learn_api_key tool.",
                        "pending_key": key_preview,
                    },
                )

            # Save the key
            provider_name = detected["provider"]
            # Normalize openai variants
            if provider_name.startswith("openai"):
                provider_name = "openai"

            learner = get_key_learner()
            learner._save_key_to_config(provider_name, key)

            return ToolResult(
                success=True,
                result={
                    "saved": True,
                    "provider": provider_name,
                    "display_name": detected.get("display_name", provider_name.title()),
                    "confidence": detected.get("confidence", 0.9),
                    "category": detected.get("category", "llm"),
                    "message": f"Saved {detected.get('display_name', provider_name)} key successfully",
                },
            )

        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


class LearnAPIKeyTool(BaseTool):
    """
    Learn new API key type after user confirms provider.
    Phase 57.9: Learn new key types dynamically.
    FIX_110.3: Implemented missing tool class.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="learn_api_key",
            description="Learn a new API key pattern and save the key. Use after user identifies an unknown key's provider.",
            parameters={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "The API key to learn and save",
                    },
                    "provider": {
                        "type": "string",
                        "description": "Name of the provider (e.g., 'tavily', 'polza')",
                    },
                },
                "required": ["key", "provider"],
            },
            permission_level=PermissionLevel.WRITE,
            needs_user_approval=False,
        )

    async def execute(self, key: str, provider: str) -> ToolResult:
        try:
            from src.elisya.key_learner import get_key_learner

            learner = get_key_learner()
            success, message = learner.learn_key_type(key, provider, save_key=True)

            if success:
                return ToolResult(
                    success=True,
                    result={
                        "learned": True,
                        "provider": provider,
                        "message": message,
                    },
                )
            else:
                return ToolResult(
                    success=False,
                    result={"learned": False, "provider": provider},
                    error=message,
                )

        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


class GetAPIKeyStatusTool(BaseTool):
    """
    Get status of configured API keys.
    Phase 57.9: Check key status.
    FIX_110.3: Implemented missing tool class.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_api_key_status",
            description="Get status of API keys and configured providers",
            parameters={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "description": "Specific provider to check (optional, returns all if not specified)",
                    },
                },
                "required": [],
            },
            permission_level=PermissionLevel.READ,
            needs_user_approval=False,
        )

    async def execute(self, provider: str = None) -> ToolResult:
        try:
            from src.elisya.key_learner import get_key_learner
            import json

            config_path = PROJECT_ROOT / "data" / "config.json"
            with open(config_path, "r") as f:
                config = json.load(f)

            api_keys = config.get("api_keys", {})
            learner = get_key_learner()
            learned_providers = learner.get_learned_providers()

            if provider:
                # Single provider status
                keys = api_keys.get(provider)
                if keys is None:
                    return ToolResult(
                        success=True,
                        result={"provider": provider, "configured": False, "count": 0},
                    )

                if isinstance(keys, str):
                    count = 1
                elif isinstance(keys, list):
                    count = len(keys)
                elif isinstance(keys, dict):
                    count = sum(1 if isinstance(v, str) else len(v) for v in keys.values() if v)
                else:
                    count = 0

                return ToolResult(
                    success=True,
                    result={
                        "provider": provider,
                        "configured": True,
                        "count": count,
                        "learned": provider in learned_providers,
                    },
                )
            else:
                # All providers status
                providers_status = []
                for prov, keys in api_keys.items():
                    if keys is None:
                        continue
                    if isinstance(keys, str):
                        count = 1
                    elif isinstance(keys, list):
                        count = len(keys)
                    elif isinstance(keys, dict):
                        count = sum(1 if isinstance(v, str) else len(v) for v in keys.values() if v)
                    else:
                        count = 0

                    if count > 0:
                        providers_status.append({
                            "provider": prov,
                            "count": count,
                            "learned": prov in learned_providers,
                        })

                return ToolResult(
                    success=True,
                    result={
                        "providers": providers_status,
                        "total_providers": len(providers_status),
                        "learned_providers": learned_providers,
                    },
                )

        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


class AnalyzeUnknownKeyTool(BaseTool):
    """
    Analyze an unknown API key to identify its pattern.
    Phase 57.9: Analyze unknown keys.
    FIX_110.3: Implemented missing tool class.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="analyze_unknown_key",
            description="Analyze an unknown API key to identify its pattern (prefix, length, charset)",
            parameters={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "The API key to analyze",
                    },
                },
                "required": ["key"],
            },
            permission_level=PermissionLevel.READ,
            needs_user_approval=False,
        )

    async def execute(self, key: str) -> ToolResult:
        try:
            from src.elisya.key_learner import get_key_learner

            learner = get_key_learner()
            analysis = learner.analyze_key(key)

            return ToolResult(
                success=True,
                result={
                    "analysis": analysis,
                    "message": f"Key pattern: prefix='{analysis.get('prefix', 'none')}', "
                               f"length={analysis.get('length')}, charset={analysis.get('charset')}",
                    "suggestion": "Use learn_api_key tool to save this key after identifying the provider.",
                },
            )

        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


class SeedMCCPlaywrightFixtureTool(BaseTool):
    """
    Seed a deterministic MCC project fixture for Playwright visual regression.
    Phase 177: Internal bridge so REFLEX can recommend and execute the seeded path.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="seed_mcc_playwright_fixture",
            description="Seed a deterministic MCC Playwright fixture project and return project_id plus browser_url.",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
            permission_level=PermissionLevel.EXECUTE,
            needs_user_approval=False,
        )

    async def execute(self) -> ToolResult:
        try:
            script_path = PROJECT_ROOT / "scripts" / "mcc_seed_playwright_fixture.py"
            if not script_path.exists():
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"Seed script not found: {script_path}",
                )

            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(PROJECT_ROOT),
            )

            if result.returncode != 0:
                return ToolResult(
                    success=False,
                    result=None,
                    error=(result.stderr or result.stdout or "Seed script failed").strip(),
                )

            payload = json.loads((result.stdout or "").strip())
            return ToolResult(success=True, result=payload)
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"Seed script returned invalid JSON: {e}",
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                result=None,
                error="Seed script timed out",
            )
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


class SelectBestLocalQwenModelTool(BaseTool):
    """
    Inspect local Ollama tags and pick the strongest available Qwen model.
    Uses the HTTP tags API instead of `ollama list` for better local stability.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="select_best_local_qwen_model",
            description="Inspect local Ollama models and choose the strongest available Qwen for local tool-capable work.",
            parameters={
                "type": "object",
                "properties": {
                    "ollama_url": {
                        "type": "string",
                        "description": "Optional Ollama base URL. Default: http://127.0.0.1:11434",
                    },
                    "timeout": {
                        "type": "number",
                        "description": "HTTP timeout in seconds for the Ollama tags request.",
                        "default": 3.0,
                    },
                },
                "required": [],
            },
            permission_level=PermissionLevel.READ,
            needs_user_approval=False,
        )

    async def execute(
        self,
        ollama_url: str = "http://127.0.0.1:11434",
        timeout: float = 3.0,
    ) -> ToolResult:
        try:
            result = await asyncio.to_thread(
                get_best_local_qwen_model,
                ollama_url,
                float(timeout),
            )
            if not result.get("best_model"):
                return ToolResult(
                    success=False,
                    result=result,
                    error="No local Qwen models found in Ollama tags",
                )
            return ToolResult(success=True, result=result)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


class RememberReflexToolTool(BaseTool):
    """
    Persist a reminder about a local script/tool/skill so REFLEX can surface it later.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="remember_reflex_tool",
            description="Remember a local script, tool, or skill for REFLEX so it can be suggested later.",
            parameters={
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "Canonical tool or script name to remember.",
                    },
                    "entry_type": {
                        "type": "string",
                        "description": "Type of entry, for example script, tool, skill, or workflow.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Project-relative or absolute path for the remembered entry.",
                    },
                    "tool_id": {
                        "type": "string",
                        "description": "Optional canonical tool_id if this entry already maps to a catalog tool.",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Short notes about when and why to use it.",
                    },
                    "intent_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Intent tags that help REFLEX match this entry later.",
                    },
                    "trigger_hint": {
                        "type": "string",
                        "description": "Short hint about what user request should trigger this tool.",
                    },
                    "aliases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Alternative names or search phrases for this entry.",
                    },
                    "active": {
                        "type": "boolean",
                        "description": "Whether the remembered tool should stay active for recommendations.",
                        "default": True,
                    },
                },
                "required": ["tool_name", "entry_type", "path"],
            },
            permission_level=PermissionLevel.WRITE,
            needs_user_approval=False,
        )

    async def execute(
        self,
        tool_name: str,
        entry_type: str,
        path: str,
        tool_id: str = "",
        notes: str = "",
        intent_tags: List[str] = None,
        trigger_hint: str = "",
        aliases: List[str] = None,
        active: bool = True,
    ) -> ToolResult:
        try:
            result = remember_reflex_tool(
                tool_name=tool_name,
                entry_type=entry_type,
                path=path,
                tool_id=tool_id,
                notes=notes,
                intent_tags=intent_tags or [],
                trigger_hint=trigger_hint,
                aliases=aliases or [],
                active=active,
            )
            reset_reflex_registry()
            return ToolResult(success=True, result=result)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


class ListReflexToolMemoryTool(BaseTool):
    """
    List remembered REFLEX scripts/tools/skills.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_reflex_tool_memory",
            description="List remembered REFLEX scripts, tools, and skills, optionally filtered by type or query.",
            parameters={
                "type": "object",
                "properties": {
                    "entry_type": {
                        "type": "string",
                        "description": "Optional type filter such as script, tool, skill, or workflow.",
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional free-text filter across tool_name, path, notes, and aliases.",
                    },
                    "only_active": {
                        "type": "boolean",
                        "description": "Whether to return only active remembered entries.",
                        "default": True,
                    },
                    "exclude_stale": {
                        "type": "boolean",
                        "description": "Whether to filter remembered entries whose path or catalog mapping is stale.",
                        "default": True,
                    },
                },
                "required": [],
            },
            permission_level=PermissionLevel.READ,
            needs_user_approval=False,
        )

    async def execute(
        self,
        entry_type: str = "",
        query: str = "",
        only_active: bool = True,
        exclude_stale: bool = True,
    ) -> ToolResult:
        try:
            result = list_reflex_tool_memory(
                entry_type=entry_type,
                query=query,
                only_active=only_active,
                exclude_stale=exclude_stale,
            )
            return ToolResult(success=True, result=result)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))


# Register API Key tools
registry.register(SaveAPIKeyTool())
registry.register(LearnAPIKeyTool())
registry.register(GetAPIKeyStatusTool())
registry.register(AnalyzeUnknownKeyTool())
registry.register(SeedMCCPlaywrightFixtureTool())
registry.register(SelectBestLocalQwenModelTool())
registry.register(RememberReflexToolTool())
registry.register(ListReflexToolMemoryTool())


# ============================================================================
# AGENT TOOL PERMISSIONS
# ============================================================================

# Define which tools each agent can access
# Phase 19: Added search_semantic and get_tree_context
# Phase 22: Added camera_focus for all agents
# Phase 57.8: Added Researcher agent
# Phase 97: Added arc_suggest for creative agents (PM, Architect, Researcher, Hostess)
# FIX_98.4: Added Default for models without roles (read-only tools)
# MARKER_114.1_TOOL_NAME_FIX: Fixed name mismatches + removed phantoms + registered missing tools
# search_semantic → vetka_search_semantic, camera_focus → vetka_camera_focus
# Removed phantoms: search_weaviate, get_file_info, create_artifact, validate_syntax, run_tests
# Registered: SearchCodebaseTool, ExecuteCodeTool (were classes without register())
AGENT_TOOL_PERMISSIONS: Dict[str, List[str]] = {
    # FIX_98.4: Default tools for models without explicit role (e.g., Grok in chat)
    # MARKER_114.1: Read-only tools, unified names
    "Default": [
        "read_code_file",
        "list_files",
        "search_codebase",  # MARKER_114.1: now registered
        "vetka_search_semantic",  # MARKER_114.1: was "search_semantic"
        "get_tree_context",
        "vetka_camera_focus",  # MARKER_114.1: was "camera_focus"
        # CAM tools (read-only)
        "calculate_surprise",
        "compress_with_elision",
        "adaptive_memory_sizing",
        # ARC for creative suggestions
        "arc_suggest",
        "list_reflex_tool_memory",
        "select_best_local_qwen_model",
    ],
    "PM": [
        "read_code_file",
        "list_files",
        "search_codebase",  # MARKER_114.1: now registered
        "vetka_search_semantic",  # MARKER_114.1: was "search_semantic"
        "get_tree_context",
        "vetka_camera_focus",  # MARKER_114.1: was "camera_focus"
        "vetka_edit_artifact",  # MARKER_114.3: for creating specs/plans
        # Phase 76.4: CAM Tools
        "calculate_surprise",  # Novelty detection for strategic analysis
        "adaptive_memory_sizing",  # Optimize memory for project management
        # Phase 97: ARC Tool for creative suggestions
        "arc_suggest",  # Get creative workflow suggestions when planning
        "list_reflex_tool_memory",
        "remember_reflex_tool",
        "select_best_local_qwen_model",
    ],
    "Dev": [
        "read_code_file",
        "write_code_file",
        "list_files",
        "execute_code",  # MARKER_114.1: now registered
        "search_codebase",  # MARKER_114.1: now registered
        "vetka_search_semantic",  # MARKER_114.1: was "search_semantic"
        "get_tree_context",
        "vetka_camera_focus",  # MARKER_114.1: was "camera_focus"
        "vetka_edit_artifact",  # MARKER_114.3: restored (was create_artifact, Big Pickle Phase 92)
        # Phase 76.4: CAM Tools
        "calculate_surprise",  # Detect novel implementation challenges
        "compress_with_elision",  # Reduce token usage for large codebases
        "adaptive_memory_sizing",  # Optimize memory for complex implementations
        "seed_mcc_playwright_fixture",
        "list_reflex_tool_memory",
        "remember_reflex_tool",
        "select_best_local_qwen_model",
    ],
    "QA": [
        "read_code_file",
        "execute_code",  # MARKER_114.1: now registered
        "search_codebase",  # MARKER_114.1: now registered
        "vetka_search_semantic",  # MARKER_114.1: was "search_semantic"
        "get_tree_context",
        "vetka_camera_focus",  # MARKER_114.1: was "camera_focus"
        # Phase 76.4: CAM Tools
        "calculate_surprise",  # Detect novel issues in testing
        "adaptive_memory_sizing",  # Optimize memory for test analysis
    ],
    "Architect": [
        "read_code_file",
        "list_files",
        "search_codebase",  # MARKER_114.1: now registered
        "vetka_search_semantic",  # MARKER_114.1: was "search_semantic"
        "get_tree_context",
        "vetka_camera_focus",  # MARKER_114.1: was "camera_focus"
        "vetka_edit_artifact",  # MARKER_114.3: restored (was create_artifact, Big Pickle Phase 92)
        # Phase 76.4: CAM Tools (Full access for architect)
        "calculate_surprise",
        "compress_with_elision",
        "adaptive_memory_sizing",
        # Phase 97: ARC Tool for creative architecture suggestions
        "arc_suggest",  # Get creative suggestions for system design
        "seed_mcc_playwright_fixture",
        "list_reflex_tool_memory",
        "remember_reflex_tool",
        "select_best_local_qwen_model",
    ],
    # Phase 57.8: Researcher Agent - Knowledge Investigator (Full CAM access)
    "Researcher": [
        "vetka_search_semantic",  # MARKER_114.1: was "search_semantic" - Primary tool
        "search_codebase",  # MARKER_114.1: now registered - Code pattern search
        "read_code_file",  # Read specific files
        "list_files",  # Browse project structure
        "get_tree_context",  # Understand file relationships
        "vetka_camera_focus",  # MARKER_114.1: was "camera_focus" - Navigate to files
        # Phase 76.4: Full CAM Tools for research
        "calculate_surprise",
        "compress_with_elision",
        "adaptive_memory_sizing",
        # Phase 97: ARC Tool for creative research suggestions
        "arc_suggest",  # Get creative suggestions during research
        "seed_mcc_playwright_fixture",
        "list_reflex_tool_memory",
        "remember_reflex_tool",
        "select_best_local_qwen_model",
    ],
    "Hostess": [
        "vetka_search_semantic",  # MARKER_114.1: was "search_semantic"
        "get_tree_context",
        "list_files",
        "vetka_camera_focus",  # MARKER_114.1: was "camera_focus"
        "select_best_local_qwen_model",
        "save_api_key",  # Phase 57.1: Accept API keys via chat
        "learn_api_key",  # Phase 57.9: Learn new key types
        "get_api_key_status",  # Phase 57.9: Check key status
        "analyze_unknown_key",  # Phase 57.9: Analyze unknown keys
        # Phase 76.4: Limited CAM tools for Hostess
        "calculate_surprise",  # Detect novel user needs
        # Phase 97: ARC Tool for creative suggestions to users
        "arc_suggest",  # Suggest creative connections to help users
        "list_reflex_tool_memory",
        "remember_reflex_tool",
    ],
}
# MARKER_114.1_TOOL_NAME_FIX_END


def get_tools_for_agent(agent_type: str) -> List[Dict]:
    """
    Get tool schemas available for a specific agent type.

    Args:
        agent_type: 'PM', 'Dev', 'QA', 'Architect', 'Hostess', or any model name

    Returns:
        List of tool schemas in Ollama/OpenAI function calling format

    FIX_98.4: Falls back to 'Default' permissions for unknown agent types.
    """
    # FIX_98.4: Use Default as fallback for models without explicit role
    allowed_tool_names = AGENT_TOOL_PERMISSIONS.get(
        agent_type,
        AGENT_TOOL_PERMISSIONS.get("Default", [])
    )

    tools = []
    for name in allowed_tool_names:
        tool = registry.get(name)
        if tool:
            tools.append(tool.to_ollama_schema())

    return tools


def get_tool_names_for_agent(agent_type: str) -> List[str]:
    """Get list of tool names available for agent (FIX_98.4: falls back to Default)"""
    return AGENT_TOOL_PERMISSIONS.get(
        agent_type,
        AGENT_TOOL_PERMISSIONS.get("Default", [])
    )


# ============================================================================
# LEGACY COMPATIBILITY - TOOL EXECUTOR WRAPPER
# ============================================================================


class AgentToolExecutor:
    """
    Legacy-compatible wrapper for executing tools.
    Provides the same interface as Phase 17-L spec but uses the new framework.
    Note: CreateArtifactTool removed by Big Pickle in Phase 92
    """

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else PROJECT_ROOT
        self._artifacts = []  # Local artifacts storage

    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool and return result.

        Synchronous wrapper for async tool execution.
        """
        import asyncio

        tool = registry.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        try:
            # Run async tool in sync context
            # Fix: Use asyncio.run instead of run_until_complete
            try:
                result = asyncio.run(tool.execute(**parameters))
            except Exception as e:
                print(f"[TOOLS] Error executing async tool: {e}")
                result = ToolResult(success=False, result=None, error=str(e))

            return {
                "success": result.success,
                "result": result.result,
                "error": result.error,
                "execution_time_ms": result.execution_time_ms,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_artifacts(self) -> List[Dict]:
        """Get all created artifacts as dicts"""
        return self._artifacts

    def clear_artifacts(self):
        """Clear artifacts list"""
        self._artifacts = []


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Tool classes (existing after Phase 92 Big Pickle cleanup)
    "SearchCodebaseTool",
    "ExecuteCodeTool",
    # Phase 76.4: CAM Tools
    "CalculateSurpriseTool",
    "CompressWithElisionTool",
    "AdaptiveMemorySizingTool",
    "SeedMCCPlaywrightFixtureTool",
    "RememberReflexToolTool",
    "ListReflexToolMemoryTool",
    # Agent permissions
    "AGENT_TOOL_PERMISSIONS",
    "get_tools_for_agent",
    "get_tool_names_for_agent",
    # Legacy executor
    "AgentToolExecutor",
    # Project root
    "PROJECT_ROOT",
]
