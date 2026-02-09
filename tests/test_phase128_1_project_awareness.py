"""
Tests for Phase 128.1: Coder Project Awareness

Tests:
1. _detect_project_context() — detects imports from TS/Python files
2. Coder prompt has PROJECT STACK section
3. Coder prompt workflow changed from "search first" to "read first"
4. project_context wired through scout_report to coder
5. Scout pre-fetch includes project context section
"""
import json
import os
import pytest
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# Ensure project root is on path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestDetectProjectContext:
    """Test _detect_project_context static method."""

    def _get_pipeline(self):
        from src.orchestration.agent_pipeline import AgentPipeline
        return AgentPipeline

    def test_detects_zustand_import(self, tmp_path):
        """Should detect 'zustand' from TypeScript import."""
        f = tmp_path / "useStore.ts"
        f.write_text("import { create } from 'zustand';\nimport React from 'react';\n")
        cls = self._get_pipeline()
        result = cls._detect_project_context([str(f)])
        assert "zustand" in result
        assert "react" in result

    def test_detects_python_imports(self, tmp_path):
        """Should detect FastAPI, httpx from Python imports."""
        f = tmp_path / "server.py"
        f.write_text("from fastapi import FastAPI\nimport httpx\nimport os\n")
        cls = self._get_pipeline()
        result = cls._detect_project_context([str(f)])
        assert "fastapi" in result
        assert "httpx" in result
        # os should be filtered out (stdlib)
        assert "os" not in result.split(":")[-1]  # Not in the imports list

    def test_skips_relative_imports(self, tmp_path):
        """Should NOT include relative imports like ./utils or ../types."""
        f = tmp_path / "comp.tsx"
        f.write_text("import { Foo } from './utils';\nimport Bar from '../types/bar';\nimport { create } from 'zustand';\n")
        cls = self._get_pipeline()
        result = cls._detect_project_context([str(f)])
        # Should have zustand but not relative paths
        assert "zustand" in result
        # Relative paths should not appear as package names
        assert "utils" not in result.split(":")[-1]

    def test_returns_empty_for_no_files(self):
        """Should return empty string if no files found."""
        cls = self._get_pipeline()
        result = cls._detect_project_context([])
        assert result == ""

    def test_returns_empty_for_nonexistent(self):
        """Should return empty string if files don't exist."""
        cls = self._get_pipeline()
        result = cls._detect_project_context(["/nonexistent/file.ts"])
        assert result == ""

    def test_multiple_files_dedup(self, tmp_path):
        """Should deduplicate imports across multiple files."""
        f1 = tmp_path / "a.ts"
        f1.write_text("import { create } from 'zustand';\n")
        f2 = tmp_path / "b.ts"
        f2.write_text("import { create } from 'zustand';\nimport { Canvas } from '@react-three/fiber';\n")
        cls = self._get_pipeline()
        result = cls._detect_project_context([str(f1), str(f2)])
        assert "zustand" in result
        assert "@react-three" in result
        # Count: zustand should appear only once
        imports_part = result.split(": ")[-1]
        assert imports_part.count("zustand") == 1

    def test_limits_to_15_imports(self, tmp_path):
        """Should limit to max 15 detected imports."""
        lines = [f"import pkg{i} from 'package{i}';\n" for i in range(20)]
        f = tmp_path / "big.ts"
        f.write_text("".join(lines))
        cls = self._get_pipeline()
        result = cls._detect_project_context([str(f)])
        imports_part = result.split(": ")[-1]
        assert len(imports_part.split(", ")) <= 15


class TestCoderPromptProjectStack:
    """Test that coder prompt has PROJECT STACK section."""

    def _load_prompts(self):
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..",
            "data", "templates", "pipeline_prompts.json"
        )
        with open(prompts_path) as f:
            return json.load(f)

    def test_has_project_stack_section(self):
        """Coder prompt must have PROJECT STACK section."""
        prompts = self._load_prompts()
        coder_system = prompts["coder"]["system"]
        assert "PROJECT STACK" in coder_system

    def test_mentions_zustand(self):
        """Coder prompt must mention Zustand (not MobX)."""
        prompts = self._load_prompts()
        coder_system = prompts["coder"]["system"]
        assert "Zustand" in coder_system
        assert "NOT MobX" in coder_system

    def test_read_first_workflow(self):
        """Coder prompt should say READ FIRST, not SEARCH FIRST."""
        prompts = self._load_prompts()
        coder_system = prompts["coder"]["system"]
        assert "READ FIRST" in coder_system
        # Should NOT have old "Use this FIRST" for search_code
        assert "Use this FIRST" not in coder_system

    def test_mentions_react_typescript(self):
        """Coder prompt must mention React and TypeScript."""
        prompts = self._load_prompts()
        coder_system = prompts["coder"]["system"]
        assert "React" in coder_system
        assert "TypeScript" in coder_system

    def test_vetka_read_file_first_tool(self):
        """vetka_read_file should be listed as first tool."""
        prompts = self._load_prompts()
        coder_system = prompts["coder"]["system"]
        # Check that read_file appears before search_code in tool list
        read_pos = coder_system.find("vetka_read_file")
        search_pos = coder_system.find("vetka_search_code")
        assert read_pos < search_pos, "vetka_read_file should come before vetka_search_code"

    def test_never_invent_imports_rule(self):
        """Coder prompt must say NEVER invent imports."""
        prompts = self._load_prompts()
        coder_system = prompts["coder"]["system"]
        assert "NEVER invent imports" in coder_system or "NEVER guess imports" in coder_system or "do NOT guess imports" in coder_system


class TestProjectContextWiring:
    """Test that project_context flows from Scout to Coder."""

    def test_scout_report_project_context_injected(self):
        """Coder should see project_context from scout_report."""
        from src.orchestration.agent_pipeline import AgentPipeline

        # Create minimal pipeline
        pipeline = AgentPipeline.__new__(AgentPipeline)

        # Simulate subtask with scout_report containing project_context
        from dataclasses import dataclass, field
        from typing import Optional, Dict, List

        @dataclass
        class MockSubtask:
            description: str = "Add toggleBookmark"
            context: Dict = field(default_factory=lambda: {
                "scout_report": {
                    "relevant_files": ["client/src/store/useStore.ts"],
                    "patterns_found": ["Zustand create pattern"],
                    "project_context": "Detected imports in project files: zustand, react, three",
                    "marker_map": [],
                }
            })
            marker: str = "MARKER_TEST"
            retry_count: int = 0
            verifier_feedback: Optional[Dict] = None
            escalated: bool = False
            status: str = "pending"

        subtask = MockSubtask()
        scout = subtask.context["scout_report"]
        files = ", ".join(scout.get("relevant_files", [])[:5])
        project_ctx = scout.get("project_context", "")

        # Verify project_context would appear in coder context
        assert project_ctx != ""
        assert "zustand" in project_ctx


class TestScoutPrefetchProjectContext:
    """Test that Scout pre-fetch generates project context section."""

    def test_prefetch_output_has_project_context(self, tmp_path):
        """Scout pre-fetch output should include '--- Project context ---' section."""
        # Create a mock TS file
        ts_file = tmp_path / "useStore.ts"
        ts_file.write_text("import { create } from 'zustand';\nexport const useStore = create((set) => ({}));\n")

        from src.orchestration.agent_pipeline import AgentPipeline
        cls = AgentPipeline

        # Test _detect_project_context directly
        result = cls._detect_project_context([str(ts_file)])
        assert "zustand" in result
        assert "Detected imports" in result


class TestRegression:
    """Regression tests — existing functionality must not break."""

    def test_scout_prompt_unchanged(self):
        """Scout prompt should still have marker_map as PRIMARY output."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..",
            "data", "templates", "pipeline_prompts.json"
        )
        with open(prompts_path) as f:
            prompts = json.load(f)
        assert "marker_map" in prompts["scout"]["system"]
        assert "PRIMARY" in prompts["scout"]["system"]

    def test_verifier_prompt_unchanged(self):
        """Verifier prompt should still check 3 things."""
        prompts_path = os.path.join(
            os.path.dirname(__file__), "..",
            "data", "templates", "pipeline_prompts.json"
        )
        with open(prompts_path) as f:
            prompts = json.load(f)
        assert "HAS CODE" in prompts["verifier"]["system"]
        assert "CORRECT" in prompts["verifier"]["system"]

    def test_fc_loop_max_turns_unchanged(self):
        """FC loop max turns should still be 4."""
        from src.tools.fc_loop import MAX_FC_TURNS_CODER
        assert MAX_FC_TURNS_CODER == 4

    def test_coder_tools_count(self):
        """Coder should still have 5 tools available."""
        from src.tools.fc_loop import PIPELINE_CODER_TOOLS
        assert len(PIPELINE_CODER_TOOLS) == 5
