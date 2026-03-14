from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
MCC_ROUTES_PATH = ROOT / "src/api/routes/mcc_routes.py"


def _load_mcc_routes_module():
    spec = importlib.util.spec_from_file_location("phase173_mcc_routes", MCC_ROUTES_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakeLLMRegistry:
    def __init__(self, profiles: dict[str, object]) -> None:
        self._profiles = profiles

    async def get_profile(self, model_id: str):
        if model_id not in self._profiles:
            raise AssertionError(f"unexpected model lookup: {model_id}")
        return self._profiles[model_id]


@pytest.fixture
def localguys_module(monkeypatch: pytest.MonkeyPatch):
    module = _load_mcc_routes_module()

    profiles = {
        "qwen3.5:latest": SimpleNamespace(
            model_id="qwen3.5:latest",
            context_length=32768,
            output_tokens_per_second=46.0,
            input_tokens_per_second=120.0,
            ttft_ms=620.0,
            provider="ollama",
            source="test_fixture",
        ),
        "qwen3:8b": SimpleNamespace(
            model_id="qwen3:8b",
            context_length=32768,
            output_tokens_per_second=42.0,
            input_tokens_per_second=115.0,
            ttft_ms=650.0,
            provider="ollama",
            source="test_fixture",
        ),
        "qwen2.5:7b": SimpleNamespace(
            model_id="qwen2.5:7b",
            context_length=32768,
            output_tokens_per_second=38.0,
            input_tokens_per_second=105.0,
            ttft_ms=700.0,
            provider="ollama",
            source="test_fixture",
        ),
        "qwen2.5:3b": SimpleNamespace(
            model_id="qwen2.5:3b",
            context_length=16384,
            output_tokens_per_second=62.0,
            input_tokens_per_second=140.0,
            ttft_ms=420.0,
            provider="ollama",
            source="test_fixture",
        ),
        "deepseek-r1:8b": SimpleNamespace(
            model_id="deepseek-r1:8b",
            context_length=32768,
            output_tokens_per_second=28.0,
            input_tokens_per_second=95.0,
            ttft_ms=900.0,
            provider="ollama",
            source="test_fixture",
        ),
        "phi4-mini:latest": SimpleNamespace(
            model_id="phi4-mini:latest",
            context_length=16384,
            output_tokens_per_second=70.0,
            input_tokens_per_second=155.0,
            ttft_ms=350.0,
            provider="ollama",
            source="test_fixture",
        ),
        "qwen2.5vl:3b": SimpleNamespace(
            model_id="qwen2.5vl:3b",
            context_length=16384,
            output_tokens_per_second=34.0,
            input_tokens_per_second=88.0,
            ttft_ms=720.0,
            provider="ollama",
            source="test_fixture",
        ),
        "embeddinggemma:300m": SimpleNamespace(
            model_id="embeddinggemma:300m",
            context_length=8192,
            output_tokens_per_second=0.0,
            input_tokens_per_second=0.0,
            ttft_ms=50.0,
            provider="ollama",
            source="test_fixture",
        ),
    }
    monkeypatch.setattr("src.elisya.llm_model_registry.get_llm_registry", lambda: _FakeLLMRegistry(profiles))

    fake_models = {
        model_id: SimpleNamespace(
            id=model_id,
            provider="ollama",
            available=True,
            type=SimpleNamespace(value="local"),
            capabilities=[SimpleNamespace(value=value) for value in caps],
        )
        for model_id, caps in {
            "qwen3.5:latest": ["chat", "code"],
            "qwen3:8b": ["chat", "code"],
            "qwen2.5:7b": ["chat", "code"],
            "qwen2.5:3b": ["chat", "code"],
            "deepseek-r1:8b": ["chat", "reasoning"],
            "phi4-mini:latest": ["chat", "reasoning"],
            "qwen2.5vl:3b": ["chat", "vision"],
            "embeddinggemma:300m": ["embeddings"],
        }.items()
    }
    monkeypatch.setattr(
        "src.services.model_registry.get_model_registry",
        lambda: SimpleNamespace(_models=fake_models, _detect_capabilities=lambda model_id: []),
    )
    return module


@pytest.mark.asyncio
async def test_patchchain_localguys_contract_encodes_playbook_surface(localguys_module) -> None:
    contract = await localguys_module._resolve_workflow_contract("patchchain_localguys")

    assert contract is not None
    assert contract["workflow_family"] == "patchchain_localguys"
    assert contract["roles"] == ["coder"]
    assert contract["steps"] == ["recon", "execute", "verify", "finalize"]
    assert contract["allowed_tools"] == ["context", "artifacts", "tests", "git_diff"]
    assert contract["direct_allowed_tools"] == [
        "vetka_read_file",
        "vetka_edit_file",
        "vetka_run_tests",
    ]
    assert contract["expected_sequence"] == [
        "vetka_read_file",
        "vetka_edit_file",
        "vetka_run_tests",
    ]
    assert contract["reflex_policy"]["normalize_native_tool_calls"] is True
    assert contract["reflex_policy"]["rehydrate_tool_arguments"] is True
    assert contract["write_opt_ins"]["edit_file"] is True
    assert contract["write_opt_ins"]["task_board"] is False
    assert contract["verification_target"] == "targeted_tests"
    assert contract["operator_method"] == {
        "method": "patchchain",
        "source_family": "local_patch_chain",
        "command_template": "localguys run patchchain --task {task_id}",
    }
    assert contract["stage_tool_policy"]["recon"] == ["context", "artifacts"]
    assert contract["stage_tool_policy"]["verify"] == ["context", "tests", "artifacts", "git_diff"]
    assert [row["model_id"] for row in contract["model_policy"]["coder"]["preferred_models"]] == [
        "qwen3.5:latest",
        "qwen3:8b",
    ]


@pytest.mark.asyncio
async def test_ownership_localguys_contract_encodes_task_board_write_opt_in(localguys_module) -> None:
    contract = await localguys_module._resolve_workflow_contract("ownership_localguys")

    assert contract is not None
    assert contract["workflow_family"] == "ownership_localguys"
    assert contract["roles"] == ["operator"]
    assert contract["allowed_tools"] == ["context", "tasks", "stats"]
    assert contract["direct_allowed_tools"] == ["mycelium_task_board"]
    assert contract["expected_sequence"] == ["mycelium_task_board"]
    assert contract["write_opt_ins"] == {
        "task_board": True,
        "edit_file": False,
        "playground_artifacts": False,
        "main_tree_write": False,
    }
    assert contract["reflex_policy"]["allow_task_board_writes"] is True
    assert [row["model_id"] for row in contract["model_policy"]["operator"]["preferred_models"]] == [
        "qwen3.5:latest",
        "phi4-mini:latest",
    ]
    assert contract["operator_method"] == {
        "method": "ownership",
        "source_family": "local_task_ownership",
        "command_template": "localguys run ownership --task {task_id}",
    }


def test_patchchain_localguys_operator_catalog_exposes_new_method(localguys_module) -> None:
    method = localguys_module._LOCALGUYS_OPERATOR_METHODS["patchchain_localguys"]
    assert method == {
        "method": "patchchain",
        "source_family": "local_patch_chain",
        "command_template": "localguys run patchchain --task {task_id}",
    }
    ownership = localguys_module._LOCALGUYS_OPERATOR_METHODS["ownership_localguys"]
    assert ownership == {
        "method": "ownership",
        "source_family": "local_task_ownership",
        "command_template": "localguys run ownership --task {task_id}",
    }
    assert "qwen3.5:latest" in localguys_module._LOCALGUYS_CATALOG_IDS


def test_qwen35_defaults_are_present_in_safe_registry_and_decay_profile() -> None:
    from src.elisya.llm_model_registry import _SAFE_DEFAULTS
    from src.services.reflex_decay import get_model_profile

    assert _SAFE_DEFAULTS["qwen3.5:latest"] == {
        "context_length": 32768,
        "output_tokens_per_second": 46.0,
        "input_tokens_per_second": 120.0,
        "ttft_ms": 620.0,
        "provider": "ollama",
    }

    profile = get_model_profile("qwen3.5:latest")
    assert profile.model_name == "qwen3.5:latest"
    assert profile.fc_reliability == 0.86
    assert profile.max_tools == 10
