"""Guarded live behavior probes for local Qwen tool calling.

Set RUN_LOCAL_QWEN_BEHAVIOR_TESTS=1 to enable.
MARKER_173.P6.LIVE_LOCAL_QWEN_BEHAVIOR
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.mcp.tools.llm_call_tool import LLMCallTool
from src.mcp.tools.edit_file_tool import EditFileTool
from src.mcp.tools.read_file_tool import ReadFileTool
from src.mcp.tools.run_tests_tool import RunTestsTool
from src.orchestration.task_board import TaskBoard
from src.services.local_qwen_model_selector import get_best_local_qwen_model
from src.services.reflex_registry import reset_reflex_registry
from src.services.reflex_scorer import reset_reflex_scorer
from src.services.reflex_tool_memory import list_reflex_tool_memory, remember_reflex_tool


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIRECT_MARKER_FILE = "src/mcp/tools/llm_call_reflex.py"


def _require_live_local_qwen() -> str:
    if os.getenv("RUN_LOCAL_QWEN_BEHAVIOR_TESTS") != "1":
        pytest.skip("Set RUN_LOCAL_QWEN_BEHAVIOR_TESTS=1 to run local Ollama behavior probes")

    try:
        selection = get_best_local_qwen_model()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"Local Ollama Qwen unavailable: {exc}")

    model = selection.get("best_model") or ""
    if not model:
        pytest.skip("No local Qwen model installed in Ollama")
    return model


def _tool_schema(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


def _call_live(tool: LLMCallTool, *, model: str, prompt: str, tools: list[dict], extra: dict | None = None) -> dict:
    args = {
        "model": model,
        "model_source": "ollama",
        "messages": [{"role": "user", "content": prompt}],
        "_reflex_phase": "build",
        "_reflex_role": "coder",
        "tools": tools,
    }
    if extra:
        args.update(extra)
    result = tool.execute(args)
    assert result["success"] is True, result.get("error")
    return result["result"]


def _tool_calls(result: dict) -> list[dict]:
    return list(result.get("tool_calls") or [])


def _parse_tool_args(tool_call: dict) -> dict:
    function = tool_call.get("function", {})
    raw = function.get("arguments") or "{}"
    if isinstance(raw, dict):
        return raw
    return json.loads(raw)


def _assistant_message_from_result(result: dict) -> dict:
    tool_calls = []
    for tool_call in result.get("tool_calls", []):
        normalized = {
            "id": tool_call.get("id"),
            "type": tool_call.get("type", "function"),
            "function": dict(tool_call.get("function", {})),
        }
        raw_args = normalized["function"].get("arguments")
        if isinstance(raw_args, str):
            try:
                normalized["function"]["arguments"] = json.loads(raw_args)
            except Exception:
                normalized["function"]["arguments"] = {}
        tool_calls.append(normalized)

    return {
        "role": "assistant",
        "content": result.get("content", ""),
        "tool_calls": tool_calls,
    }


def _execute_live_tool_call(tool_call: dict) -> dict:
    function = tool_call.get("function", {})
    name = function.get("name")
    args = _parse_tool_args(tool_call)

    if name == "vetka_read_file":
        tool = ReadFileTool()
    elif name == "vetka_edit_file":
        tool = EditFileTool()
    elif name == "vetka_run_tests":
        tool = RunTestsTool()
    else:
        raise AssertionError(f"Unsupported live tool execution: {name}")

    result = tool.safe_execute(args)
    return {
        "role": "tool",
        "tool_call_id": tool_call.get("id") or f"{name}_call",
        "content": json.dumps(
            {
                "success": result.get("success"),
                "result": result.get("result"),
                "error": result.get("error"),
            }
        ),
    }


def _run_direct_live_fc_loop(
    *,
    tool: LLMCallTool,
    model: str,
    messages: list[dict],
    tools: list[dict],
    max_turns: int = 4,
    extra: dict | None = None,
    on_idle=None,
) -> tuple[list[dict], list[dict], dict]:
    history = list(messages)
    tool_history: list[dict] = []
    final_result: dict = {}

    for _ in range(max_turns):
        result = _call_live(
            tool,
            model=model,
            prompt="",
            tools=tools,
            extra={
                "messages": history,
                **(extra or {}),
            },
        )
        final_result = result
        tool_calls = _tool_calls(result)
        if not tool_calls:
            if on_idle is not None:
                follow_up = on_idle(history, tool_history, final_result)
                if follow_up:
                    history.append(follow_up)
                    continue
            break
        history.append(_assistant_message_from_result(result))
        for tool_call in tool_calls:
            tool_history.append(tool_call)
            history.append(_execute_live_tool_call(tool_call))

    return history, tool_history, final_result


class TestLocalQwenLiveBehavior:
    def test_live_local_qwen_search_then_read_repo_context(self):
        model = _require_live_local_qwen()
        tool = LLMCallTool()

        search_result = _call_live(
            tool,
            model=model,
            prompt=(
                "You are inspecting this repository. First find which file contains "
                "MARKER_173.P6.DIRECT_LOCAL_TOOL_PATH. Use the most relevant tool call before any answer."
            ),
            tools=[
                _tool_schema(
                    "vetka_search_files",
                    "Search the repository by filename or file content before reading any file.",
                    {
                        "query": {"type": "string", "description": "Filename or content marker to search for"},
                        "search_type": {"type": "string", "enum": ["filename", "content", "both"]},
                        "limit": {"type": "integer"},
                    },
                    ["query"],
                ),
                _tool_schema(
                    "vetka_read_file",
                    "Read a concrete file after you already know which file is relevant.",
                    {"file_path": {"type": "string", "description": "Relative path to a file in the repo"}},
                    ["file_path"],
                ),
            ],
        )

        search_calls = _tool_calls(search_result)
        assert search_calls, f"{model} returned no tool_calls for repo search"
        assert search_calls[0]["function"]["name"] == "vetka_search_files", search_calls
        search_args = _parse_tool_args(search_calls[0])
        assert "MARKER_173.P6.DIRECT_LOCAL_TOOL_PATH" in (search_args.get("query") or "")

        read_result = _call_live(
            tool,
            model=model,
            prompt=(
                "Search already identified the target file as "
                f"{DIRECT_MARKER_FILE}. Now inspect that file with a read tool before answering."
            ),
            tools=[
                _tool_schema(
                    "vetka_read_file",
                    "Read a concrete file and return its contents with line context.",
                    {"file_path": {"type": "string", "description": "Relative repo path to read"}},
                    ["file_path"],
                )
            ],
        )

        read_calls = _tool_calls(read_result)
        assert read_calls, f"{model} returned no tool_calls for file read"
        assert read_calls[0]["function"]["name"] == "vetka_read_file", read_calls
        read_args = _parse_tool_args(read_calls[0])
        assert (read_args.get("file_path") or "").endswith(DIRECT_MARKER_FILE)

    def test_live_local_qwen_claims_task_when_write_opt_in_enabled(self, tmp_path):
        model = _require_live_local_qwen()
        tool = LLMCallTool()

        board = TaskBoard(board_file=tmp_path / "task_board.json")
        task_id = board.add_task(
            title="P6.3 live claim probe",
            description="Local Qwen should claim this task through the task board tool.",
            priority=2,
            phase_type="build",
            complexity="low",
            tags=["phase173", "p6", "ownership", "live"],
            source="pytest",
        )

        claim_result = _call_live(
            tool,
            model=model,
            prompt=(
                f"Claim task {task_id} through mycelium_task_board before any answer. "
                "Use action=claim, task_id exactly as given, assigned_to=local_qwen, agent_type=grok."
            ),
            tools=[
                _tool_schema(
                    "mycelium_task_board",
                    "Manage task board items. For this request you may claim a task for a local agent.",
                    {
                        "action": {
                            "type": "string",
                            "enum": ["list", "get", "summary", "claim", "update", "complete"],
                        },
                        "task_id": {"type": "string", "description": "Task ID to claim or inspect"},
                        "assigned_to": {"type": "string", "description": "Agent name claiming the task"},
                        "agent_type": {"type": "string", "description": "Agent type claiming the task"},
                        "status": {"type": "string", "enum": ["pending", "claimed", "running", "done"]},
                    },
                    ["action"],
                )
            ],
            extra={"_allow_task_board_writes": True},
        )

        tool_calls = _tool_calls(claim_result)
        assert tool_calls, f"{model} returned no tool_calls for task claim"
        assert tool_calls[0]["function"]["name"] == "mycelium_task_board", tool_calls
        claim_args = _parse_tool_args(tool_calls[0])
        assert claim_args.get("action") == "claim", claim_args
        assert claim_args.get("task_id") == task_id, claim_args

        claim_response = board.claim_task(
            task_id=task_id,
            agent_name=str(claim_args.get("assigned_to") or "local_qwen"),
            agent_type=str(claim_args.get("agent_type") or "grok"),
        )
        assert claim_response["success"] is True, claim_response

        claimed = board.get_task(task_id)
        assert claimed is not None
        assert claimed["status"] == "claimed"
        assert claimed["assigned_to"] in {"local_qwen", claim_args.get("assigned_to")}

    def test_live_local_qwen_remembered_workflow_recalls_read_first(self, tmp_path, monkeypatch):
        model = _require_live_local_qwen()
        tool = LLMCallTool()
        catalog_path = PROJECT_ROOT / "data" / "reflex" / "tool_catalog.json"
        memory_path = tmp_path / "remembered_tools.json"

        remember_reflex_tool(
            tool_name="vetka_read_file",
            entry_type="tool",
            path="src/mcp/tools/read_file_tool.py",
            tool_id="vetka_read_file",
            notes="Before code edits on known targets, inspect the file contents first.",
            intent_tags=["local_models", "coding_workflow", "inspect_before_edit"],
            trigger_hint="known target file should be read before any edit or answer",
            aliases=["read before edit", "inspect target first"],
            memory_path=memory_path,
            catalog_path=catalog_path,
        )
        remember_reflex_tool(
            tool_name="vetka_run_tests",
            entry_type="tool",
            path="src/mcp/tools/run_tests_tool.py",
            tool_id="vetka_run_tests",
            notes="After a small patch, validate with targeted pytest.",
            intent_tags=["local_models", "coding_workflow", "validate_after_patch"],
            trigger_hint="after a small patch, run the targeted pytest file",
            aliases=["run targeted pytest", "validate patch"],
            memory_path=memory_path,
            catalog_path=catalog_path,
        )
        overlay = list_reflex_tool_memory(
            memory_path=memory_path,
            catalog_path=catalog_path,
            exclude_stale=True,
        )

        prompt = (
            "I know the exact target file and test file for a tiny fix. "
            "Start with the correct coding workflow before touching anything. "
            "The target file is src/mcp/tools/llm_call_reflex.py and the test file is "
            "tests/test_phase173_p6_local_qwen_direct_path.py."
        )
        tools = [
            _tool_schema(
                "vetka_search_files",
                "Search the repository when the target file is not yet known.",
                {
                    "query": {"type": "string"},
                    "search_type": {"type": "string", "enum": ["filename", "content", "both"]},
                    "limit": {"type": "integer"},
                },
                ["query"],
            ),
            _tool_schema(
                "vetka_read_file",
                "Read the known target file before editing.",
                {"file_path": {"type": "string", "description": "Relative file path to inspect"}},
                ["file_path"],
            ),
            _tool_schema(
                "vetka_run_tests",
                "Run targeted pytest after a code patch.",
                {
                    "test_path": {"type": "string"},
                    "pattern": {"type": "string"},
                    "verbose": {"type": "boolean"},
                    "timeout": {"type": "integer"},
                },
            ),
        ]

        reset_reflex_registry()
        reset_reflex_scorer()
        try:
            monkeypatch.setattr("src.services.reflex_registry.list_reflex_tool_memory", lambda **_kwargs: {"count": 0, "tools": []})
            baseline = _call_live(
                tool,
                model=model,
                prompt=prompt,
                tools=tools,
                extra={"_reflex_role": "Default"},
            )

            reset_reflex_registry()
            reset_reflex_scorer()
            monkeypatch.setattr("src.services.reflex_registry.list_reflex_tool_memory", lambda **_kwargs: overlay)
            recalled = _call_live(
                tool,
                model=model,
                prompt=prompt,
                tools=tools,
                extra={"_reflex_role": "Default"},
            )
        finally:
            reset_reflex_registry()
            reset_reflex_scorer()

        baseline_calls = _tool_calls(baseline)
        recalled_calls = _tool_calls(recalled)
        assert recalled_calls, f"{model} returned no tool_calls for remembered workflow"
        assert recalled_calls[0]["function"]["name"] == "vetka_read_file", recalled_calls
        if baseline_calls:
            assert recalled_calls[0]["function"]["name"] in {"vetka_read_file", baseline_calls[0]["function"]["name"]}

    def test_live_local_qwen_completes_read_edit_test_chain(self, tmp_path):
        model = _require_live_local_qwen()
        tool = LLMCallTool()
        relative_root = Path("tmp") / "p6_live_qwen" / tmp_path.name
        absolute_root = PROJECT_ROOT / relative_root
        absolute_root.mkdir(parents=True, exist_ok=True)

        code_rel = relative_root / "target_module.py"
        test_rel = relative_root / "test_target_module.py"
        code_abs = PROJECT_ROOT / code_rel
        test_abs = PROJECT_ROOT / test_rel

        code_abs.write_text(
            "def greeting(name: str) -> str:\n"
            "    return 'TODO'\n",
            encoding="utf-8",
        )
        test_abs.write_text(
            "import importlib.util\n"
            "from pathlib import Path\n\n"
            "MODULE_PATH = Path(__file__).with_name('target_module.py')\n"
            "SPEC = importlib.util.spec_from_file_location('target_module_live', MODULE_PATH)\n"
            "MODULE = importlib.util.module_from_spec(SPEC)\n"
            "assert SPEC.loader is not None\n"
            "SPEC.loader.exec_module(MODULE)\n\n"
            "def test_greeting_returns_expected_text():\n"
            "    assert MODULE.greeting('ada') == 'hello, ada'\n",
            encoding="utf-8",
        )

        prompt = (
            f"You are fixing a tiny Python bug. The code file is {code_rel.as_posix()} and the pytest file is "
            f"{test_rel.as_posix()}. Required workflow: read the code file, read the test file, edit only the "
            "code file so the test passes, then run the targeted pytest file. "
            "For vetka_read_file and vetka_edit_file use the 'path' argument. "
            "For vetka_edit_file set dry_run to false. For vetka_run_tests use test_path with the exact pytest file."
        )
        tools = [
            _tool_schema(
                "vetka_read_file",
                "Read a repository file by relative path before editing.",
                {"path": {"type": "string"}, "max_lines": {"type": "integer"}, "encoding": {"type": "string"}},
                ["path"],
            ),
            _tool_schema(
                "vetka_edit_file",
                "Edit a repository file. Use dry_run=false to apply the patch.",
                {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "mode": {"type": "string", "enum": ["write", "append"]},
                    "create_dirs": {"type": "boolean"},
                    "dry_run": {"type": "boolean"},
                },
                ["path", "content"],
            ),
            _tool_schema(
                "vetka_run_tests",
                "Run pytest on a targeted test file after editing.",
                {
                    "test_path": {"type": "string"},
                    "pattern": {"type": "string"},
                    "verbose": {"type": "boolean"},
                    "timeout": {"type": "integer"},
                },
            ),
        ]

        try:
            def _workflow_nudge(_history, seen_tool_calls, _final_result):
                tool_names = [call["function"]["name"] for call in seen_tool_calls]
                if "vetka_edit_file" not in tool_names:
                    return {
                        "role": "user",
                        "content": (
                            f"You have already inspected the files. Now edit only {code_rel.as_posix()} with "
                            "vetka_edit_file, set dry_run=false, then run vetka_run_tests on "
                            f"{test_rel.as_posix()}."
                        ),
                    }
                if "vetka_run_tests" not in tool_names:
                    return {
                        "role": "user",
                        "content": f"Now run vetka_run_tests on {test_rel.as_posix()} to verify the patch.",
                    }
                return None

            history, tool_history, final_result = _run_direct_live_fc_loop(
                tool=tool,
                model=model,
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
                max_turns=6,
                extra={"_allow_edit_file_writes": True},
                on_idle=_workflow_nudge,
            )

            tool_names = [call["function"]["name"] for call in tool_history]
            assert tool_names, "Local Qwen produced no tool calls in patch workflow"
            assert tool_names[0] == "vetka_read_file", tool_names
            assert "vetka_edit_file" in tool_names, tool_names
            assert "vetka_run_tests" in tool_names, tool_names
            assert tool_names.index("vetka_edit_file") < tool_names.index("vetka_run_tests"), tool_names
            assert "vetka_call_model" not in tool_names, tool_names

            patched_source = code_abs.read_text(encoding="utf-8")
            assert "TODO" not in patched_source

            verify = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_abs), "-q"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
            )
            assert verify.returncode == 0, {"stdout": verify.stdout, "stderr": verify.stderr}
            assert final_result.get("content", "") is not None
            assert history, "FC loop history should not be empty"
        finally:
            shutil.rmtree(absolute_root, ignore_errors=True)
