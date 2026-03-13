"""Tests for Phase 173 P6 direct local-model tool path."""

import pytest


def _tool_schema(name, properties=None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"{name} test tool",
            "parameters": {
                "type": "object",
                "properties": properties or {},
            },
        },
    }


class TestDirectLocalToolPath:
    def test_sync_ollama_call_applies_reflex_reordering_and_read_only_task_board(self, monkeypatch):
        from src.mcp.tools.llm_call_tool import LLMCallTool
        import src.services.reflex_integration as reflex_integration

        captured = {}

        monkeypatch.setattr(reflex_integration, "_is_enabled", lambda: True)
        monkeypatch.setattr(
            reflex_integration,
            "reflex_pre_fc",
            lambda subtask, phase_type="research", agent_role="coder": [
                {"tool_id": "select_best_local_qwen_model", "score": 0.98, "reason": "local model recall"},
                {"tool_id": "vetka_search_files", "score": 0.91, "reason": "repo lookup"},
            ],
        )
        monkeypatch.setattr(
            reflex_integration,
            "reflex_filter_schemas",
            lambda tools, **kwargs: list(tools),
        )

        tool = LLMCallTool()
        monkeypatch.setattr(tool, "_detect_provider", lambda model, source=None: "ollama")
        monkeypatch.setattr(tool, "_emit_request_to_chat", lambda *args, **kwargs: None)
        monkeypatch.setattr(tool, "_emit_response_to_chat", lambda *args, **kwargs: None)
        monkeypatch.setattr(tool, "_track_usage_for_balance", lambda *args, **kwargs: None)
        monkeypatch.setattr(tool, "_apply_favorite_preferred_key", lambda *args, **kwargs: None)

        def fake_call_provider_sync(**kwargs):
            captured["messages"] = kwargs["messages"]
            captured["tools"] = kwargs["tools"]
            return {
                "message": {
                    "content": "done",
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "vetka_task_board",
                                "arguments": "{\"action\":\"update\",\"task_id\":\"tb_1\"}",
                            },
                        },
                        {
                            "id": "call_2",
                            "type": "function",
                            "function": {
                                "name": "select_best_local_qwen_model",
                                "arguments": "{}",
                            },
                        },
                    ],
                },
                "model": "qwen3.5:latest",
                "provider": "ollama",
                "usage": None,
            }

        monkeypatch.setattr(tool, "_call_provider_sync", fake_call_provider_sync)

        result = tool.execute(
            {
                "model": "qwen3.5:latest",
                "messages": [{"role": "user", "content": "Search repo context and pick local tools"}],
                "model_source": "ollama",
                "_reflex_phase": "build",
                "_reflex_role": "coder",
                "tools": [
                    _tool_schema("vetka_read_file"),
                    _tool_schema("vetka_search_files"),
                    _tool_schema("select_best_local_qwen_model"),
                    _tool_schema(
                        "vetka_task_board",
                        {
                            "action": {
                                "type": "string",
                                "enum": ["add", "list", "get", "update", "summary", "claim", "complete"],
                            }
                        },
                    ),
                ],
            }
        )

        assert result["success"] is True
        assert captured["tools"][0]["function"]["name"] == "select_best_local_qwen_model"
        assert captured["tools"][1]["function"]["name"] == "vetka_search_files"
        assert captured["tools"][3]["function"]["parameters"]["properties"]["action"]["enum"] == [
            "active_agents",
            "get",
            "list",
            "summary",
        ]
        assert "[REFLEX Direct Recommendations]" in captured["messages"][0]["content"]
        assert "select_best_local_qwen_model" in captured["messages"][0]["content"]
        assert result["result"]["tool_calls"] == [
            {
                "id": "call_2",
                "type": "function",
                "function": {
                    "name": "select_best_local_qwen_model",
                    "arguments": "{}",
                },
            }
        ]
        assert result["result"]["reflex"]["recommended_tools"][:2] == [
            "select_best_local_qwen_model",
            "vetka_search_files",
        ]
        assert result["result"]["reflex"]["model_tier"] in {"bronze", "silver"}

    @pytest.mark.asyncio
    async def test_async_ollama_call_keeps_read_only_task_board_when_opted_in_not_set(self, monkeypatch):
        from src.mcp.tools.llm_call_tool_async import LLMCallToolAsync
        import src.services.reflex_integration as reflex_integration
        import src.mcp.tools.llm_call_tool_async as async_module

        captured = {}

        monkeypatch.setattr(reflex_integration, "_is_enabled", lambda: True)
        monkeypatch.setattr(
            reflex_integration,
            "reflex_pre_fc",
            lambda subtask, phase_type="research", agent_role="coder": [
                {"tool_id": "vetka_read_file", "score": 0.95, "reason": "inspect file first"},
            ],
        )
        monkeypatch.setattr(
            reflex_integration,
            "reflex_filter_schemas",
            lambda tools, **kwargs: list(tools),
        )

        async def fake_resilient_llm_call(**kwargs):
            captured["messages"] = kwargs["messages"]
            captured["tools"] = kwargs["tools"]
            return {
                "message": {
                    "content": "",
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "mycelium_task_board",
                                "arguments": "{\"action\":\"summary\"}",
                            },
                        }
                    ],
                },
                "model": "qwen2.5:7b",
                "provider": "ollama",
                "usage": None,
            }

        monkeypatch.setattr(async_module, "resilient_llm_call", fake_resilient_llm_call)

        tool = LLMCallToolAsync()
        monkeypatch.setattr(tool, "_detect_provider", lambda model, source=None: "ollama")
        monkeypatch.setattr(tool, "_track_usage_for_balance", lambda *args, **kwargs: None)
        monkeypatch.setattr(tool, "_apply_favorite_preferred_key", lambda *args, **kwargs: None)

        result = await tool.execute(
            {
                "model": "qwen2.5:7b",
                "messages": [{"role": "user", "content": "Inspect repository task status before coding"}],
                "model_source": "ollama",
                "_reflex_phase": "build",
                "_reflex_role": "coder",
                "tools": [
                    _tool_schema("mycelium_task_board"),
                    _tool_schema("vetka_read_file"),
                ],
            }
        )

        assert result["success"] is True
        assert captured["tools"][0]["function"]["name"] == "vetka_read_file"
        assert captured["tools"][1]["function"]["name"] == "mycelium_task_board"
        assert result["result"]["tool_calls"][0]["function"]["name"] == "mycelium_task_board"
        assert result["result"]["reflex"]["applied"] is True
        assert "[REFLEX Direct Recommendations]" in captured["messages"][0]["content"]

    def test_local_helper_tools_are_in_safe_allowlists(self):
        from src.mcp.tools.llm_call_tool import SAFE_FUNCTION_CALLING_TOOLS as sync_allowlist
        from src.mcp.tools.llm_call_tool_async import SAFE_FUNCTION_CALLING_TOOLS as async_allowlist

        for allowlist in (sync_allowlist, async_allowlist):
            assert "select_best_local_qwen_model" in allowlist
            assert "vetka_task_board" in allowlist
            assert "mycelium_task_board" in allowlist

    def test_sync_task_board_write_opt_in_preserves_claim_call(self, monkeypatch):
        from src.mcp.tools.llm_call_tool import LLMCallTool
        import src.services.reflex_integration as reflex_integration

        captured = {}

        monkeypatch.setattr(reflex_integration, "_is_enabled", lambda: True)
        monkeypatch.setattr(
            reflex_integration,
            "reflex_pre_fc",
            lambda subtask, phase_type="research", agent_role="coder": [
                {"tool_id": "mycelium_task_board", "score": 0.97, "reason": "ownership flow"},
            ],
        )
        monkeypatch.setattr(
            reflex_integration,
            "reflex_filter_schemas",
            lambda tools, **kwargs: list(tools),
        )

        tool = LLMCallTool()
        monkeypatch.setattr(tool, "_detect_provider", lambda model, source=None: "ollama")
        monkeypatch.setattr(tool, "_emit_request_to_chat", lambda *args, **kwargs: None)
        monkeypatch.setattr(tool, "_emit_response_to_chat", lambda *args, **kwargs: None)
        monkeypatch.setattr(tool, "_track_usage_for_balance", lambda *args, **kwargs: None)
        monkeypatch.setattr(tool, "_apply_favorite_preferred_key", lambda *args, **kwargs: None)

        def fake_call_provider_sync(**kwargs):
            captured["tools"] = kwargs["tools"]
            return {
                "message": {
                    "content": "",
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "mycelium_task_board",
                                "arguments": "{\"action\":\"claim\",\"task_id\":\"tb_42\",\"assigned_to\":\"local_qwen\"}",
                            },
                        }
                    ],
                },
                "model": "qwen3.5:latest",
                "provider": "ollama",
                "usage": None,
            }

        monkeypatch.setattr(tool, "_call_provider_sync", fake_call_provider_sync)

        result = tool.execute(
            {
                "model": "qwen3.5:latest",
                "messages": [{"role": "user", "content": "Claim task tb_42"}],
                "model_source": "ollama",
                "_reflex_phase": "build",
                "_reflex_role": "coder",
                "_allow_task_board_writes": True,
                "tools": [
                    _tool_schema(
                        "mycelium_task_board",
                        {
                            "action": {
                                "type": "string",
                                "enum": ["list", "get", "summary", "claim", "update", "complete"],
                            }
                        },
                    ),
                ],
            }
        )

        assert result["success"] is True
        assert captured["tools"][0]["function"]["parameters"]["properties"]["action"]["enum"] == [
            "list",
            "get",
            "summary",
            "claim",
            "update",
            "complete",
        ]
        assert result["result"]["tool_calls"][0]["function"]["name"] == "mycelium_task_board"

    def test_sync_edit_file_write_opt_in_preserves_edit_call(self, monkeypatch):
        from src.mcp.tools.llm_call_tool import LLMCallTool
        import src.services.reflex_integration as reflex_integration

        captured = {}

        monkeypatch.setattr(reflex_integration, "_is_enabled", lambda: True)
        monkeypatch.setattr(
            reflex_integration,
            "reflex_pre_fc",
            lambda subtask, phase_type="research", agent_role="coder": [
                {"tool_id": "vetka_edit_file", "score": 0.99, "reason": "apply patch"},
            ],
        )
        monkeypatch.setattr(
            reflex_integration,
            "reflex_filter_schemas",
            lambda tools, **kwargs: list(tools),
        )

        tool = LLMCallTool()
        monkeypatch.setattr(tool, "_detect_provider", lambda model, source=None: "ollama")
        monkeypatch.setattr(tool, "_emit_request_to_chat", lambda *args, **kwargs: None)
        monkeypatch.setattr(tool, "_emit_response_to_chat", lambda *args, **kwargs: None)
        monkeypatch.setattr(tool, "_track_usage_for_balance", lambda *args, **kwargs: None)
        monkeypatch.setattr(tool, "_apply_favorite_preferred_key", lambda *args, **kwargs: None)

        def fake_call_provider_sync(**kwargs):
            captured["tools"] = kwargs["tools"]
            return {
                "message": {
                    "content": "",
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "vetka_edit_file",
                                "arguments": "{\"path\":\"tmp/demo.py\",\"content\":\"print('ok')\",\"dry_run\":false}",
                            },
                        }
                    ],
                },
                "model": "qwen3.5:latest",
                "provider": "ollama",
                "usage": None,
            }

        monkeypatch.setattr(tool, "_call_provider_sync", fake_call_provider_sync)

        result = tool.execute(
            {
                "model": "qwen3.5:latest",
                "messages": [{"role": "user", "content": "Patch tmp/demo.py"}],
                "model_source": "ollama",
                "_reflex_phase": "build",
                "_reflex_role": "coder",
                "_allow_edit_file_writes": True,
                "tools": [
                    _tool_schema(
                        "vetka_edit_file",
                        {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                            "dry_run": {"type": "boolean"},
                        },
                    ),
                ],
            }
        )

        assert result["success"] is True
        assert captured["tools"][0]["function"]["name"] == "vetka_edit_file"
        assert result["result"]["tool_calls"][0]["function"]["name"] == "vetka_edit_file"
