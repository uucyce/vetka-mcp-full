from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _FakeBoard:
    def __init__(self, task: dict | None = None) -> None:
        self.task = dict(task or {})

    def get_task(self, task_id: str):
        if self.task.get("id") != task_id:
            return None
        return dict(self.task)


class _FakeLLMRegistry:
    def __init__(self, profiles: dict[str, object]) -> None:
        self._profiles = profiles

    async def get_profile(self, model_id: str):
        if model_id not in self._profiles:
            raise AssertionError(f"unexpected model lookup: {model_id}")
        return self._profiles[model_id]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import src.api.routes.mcc_routes as routes
    from src.api.routes.mcc_routes import router

    board = _FakeBoard(
        {
            "id": "tb_local_1",
            "title": "Localguys narrow fix",
            "description": "Run local workflow in playground",
            "phase_type": "fix",
            "complexity": "medium",
            "preset": "dragon_silver",
            "team_profile": "dragon_silver",
            "workflow_id": "g3_localguys",
            "workflow_family": "g3_localguys",
            "workflow_selection_origin": "user-selected",
        }
    )
    monkeypatch.setattr(routes, "_get_task_board_instance", lambda: board)

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
    monkeypatch.setattr(
        "src.elisya.llm_model_registry.get_llm_registry",
        lambda: _FakeLLMRegistry(profiles),
    )

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
        lambda: SimpleNamespace(
            _models=fake_models, _detect_capabilities=lambda model_id: []
        ),
    )

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_workflow_contract_fetch_returns_g3_localguys_with_exact_local_model_policy(
    client: TestClient,
) -> None:
    resp = client.get("/api/mcc/workflow-contract/g3_localguys")
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert data["workflow_family"] == "g3_localguys"
    contract = data["contract"]
    assert contract["workflow_family"] == "g3_localguys"
    assert contract["roles"] == ["coder", "verifier"]
    assert contract["steps"] == [
        "recon",
        "plan",
        "execute",
        "verify",
        "review",
        "finalize",
    ]
    assert contract["execution_mode"] == "staged_state_machine"
    assert contract["sandbox_policy"]["mode"] == "playground_only"
    assert contract["write_opt_ins"] == {
        "task_board": False,
        "edit_file": True,
        "playground_artifacts": True,
        "main_tree_write": False,
    }
    assert contract["completion_policy"]["requires_verifier_pass"] is True
    assert contract["verification_target"] == "targeted_tests"
    assert contract["max_turns"] == 13
    assert "playground" in contract["idle_nudge_template"].lower()
    assert contract["operator_method"]["method"] == "g3"
    assert (
        contract["operator_method"]["command_template"]
        == "localguys run g3 --task {task_id}"
    )
    assert contract["stage_tool_policy"]["recon"] == [
        "context",
        "search",
        "artifacts",
        "stats",
    ]
    assert contract["stage_tool_policy"]["verify"] == [
        "context",
        "tests",
        "artifacts",
        "git_diff",
        "stats",
    ]

    coder_models = contract["model_policy"]["coder"]["preferred_models"]
    assert [row["model_id"] for row in coder_models] == ["qwen3:8b", "qwen2.5:7b"]
    assert coder_models[0]["provider"] == "ollama"
    assert coder_models[0]["context_length"] == 32768
    assert coder_models[0]["prompt_style"] == "coder_compact_v1"
    assert "code" in coder_models[0]["capabilities"]

    verifier_models = contract["model_policy"]["verifier"]["preferred_models"]
    assert [row["model_id"] for row in verifier_models] == ["deepseek-r1:8b"]
    assert verifier_models[0]["tool_budget_class"] == "low-medium"
    assert "reasoning" in verifier_models[0]["capabilities"]

    catalog = {row["model_id"]: row for row in contract["local_model_catalog"]}
    assert set(catalog) == {
        "qwen3.5:latest",
        "qwen3:8b",
        "qwen2.5:7b",
        "qwen2.5:3b",
        "deepseek-r1:8b",
        "phi4-mini:latest",
        "qwen2.5vl:3b",
        "embeddinggemma:300m",
    }
    assert catalog["qwen2.5vl:3b"]["role_fit"] == ["scout"]
    assert catalog["embeddinggemma:300m"]["role_fit"] == ["retrieval"]
    assert catalog["phi4-mini:latest"]["prompt_style"] == "router_tiny_v1"


def test_task_workflow_contract_resolution_uses_task_binding(
    client: TestClient,
) -> None:
    resp = client.get("/api/mcc/tasks/tb_local_1/workflow-contract")
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert data["task_id"] == "tb_local_1"
    assert data["binding"]["workflow_family"] == "g3_localguys"
    assert data["contract"]["workflow_family"] == "g3_localguys"
    assert data["contract"]["write_opt_ins"]["edit_file"] is True
    assert data["contract"]["artifact_contract"]["required"] == [
        "facts.json",
        "plan.json",
        "patch.diff",
        "test_output.txt",
        "review.json",
        "final_report.json",
    ]


def test_workflow_contract_fetch_returns_patchchain_localguys_playbook_contract(
    client: TestClient,
) -> None:
    resp = client.get("/api/mcc/workflow-contract/patchchain_localguys")
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert data["workflow_family"] == "patchchain_localguys"
    contract = data["contract"]
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
    assert contract["reflex_policy"] == {
        "enabled": True,
        "inject_system_hint": True,
        "reorder_tools": True,
        "normalize_native_tool_calls": True,
        "rehydrate_tool_arguments": True,
        "idle_nudge_loop": True,
    }
    assert contract["stage_tool_policy"]["recon"] == ["context", "artifacts"]
    assert contract["stage_tool_policy"]["verify"] == [
        "context",
        "tests",
        "artifacts",
        "git_diff",
    ]
    assert contract["write_opt_ins"] == {
        "task_board": False,
        "edit_file": True,
        "playground_artifacts": True,
        "main_tree_write": False,
    }
    assert contract["completion_policy"]["requires_expected_sequence"] is True
    assert contract["verification_target"] == "targeted_tests"
    assert contract["operator_method"]["method"] == "patchchain"
    assert contract["operator_method"]["source_family"] == "local_patch_chain"
    coder_models = contract["model_policy"]["coder"]["preferred_models"]
    assert [row["model_id"] for row in coder_models] == ["qwen3.5:latest", "qwen3:8b"]
    assert coder_models[0]["ttft_ms"] == 620.0


def test_unknown_workflow_contract_returns_404(client: TestClient) -> None:
    resp = client.get("/api/mcc/workflow-contract/unknown_family_xyz")
    assert resp.status_code == 404
    assert "workflow contract" in resp.json()["detail"].lower()


def test_localguys_operator_methods_catalog_is_deterministic(
    client: TestClient,
) -> None:
    resp = client.get("/api/mcc/localguys/operator-methods")
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert data["count"] == 11
    methods = {row["workflow_family"]: row for row in data["methods"]}
    assert methods["dragons_localguys"]["method"] == "dragons"
    assert (
        methods["dragons_localguys"]["command_template"]
        == "localguys run dragons --task {task_id}"
    )
    assert methods["refactor_localguys"]["method"] == "refactor"
    assert methods["patchchain_localguys"]["method"] == "patchchain"
    assert methods["patchchain_localguys"]["source_family"] == "local_patch_chain"
    assert methods["ownership_localguys"]["method"] == "ownership"
    assert methods["ownership_localguys"]["source_family"] == "local_task_ownership"
    assert methods["bmad_localguys"]["roles"] == [
        "scout",
        "researcher",
        "architect",
        "coder",
        "verifier",
        "approval",
    ]


@pytest.mark.parametrize(
    ("family", "roles", "steps", "requires_verifier_pass", "required_artifacts"),
    [
        (
            "ralph_localguys",
            ["coder", "verifier"],
            ["recon", "execute", "verify", "finalize"],
            True,
            ["facts.json", "patch.diff", "test_output.txt", "final_report.json"],
        ),
        (
            "quickfix_localguys",
            ["scout", "coder", "verifier"],
            ["recon", "execute", "verify", "review", "finalize"],
            True,
            [
                "facts.json",
                "patch.diff",
                "test_output.txt",
                "review.json",
                "final_report.json",
            ],
        ),
        (
            "testonly_localguys",
            ["scout", "coder", "verifier"],
            ["recon", "plan", "execute", "verify", "finalize"],
            True,
            [
                "facts.json",
                "plan.json",
                "patch.diff",
                "test_output.txt",
                "review.json",
                "final_report.json",
            ],
        ),
        (
            "docs_localguys",
            ["scout", "coder"],
            ["recon", "execute", "review", "finalize"],
            False,
            ["facts.json", "patch.diff", "final_report.json"],
        ),
        (
            "research_localguys",
            ["researcher", "architect", "coder", "verifier"],
            ["recon", "research", "plan", "execute", "verify", "review", "finalize"],
            True,
            [
                "facts.json",
                "plan.json",
                "patch.diff",
                "test_output.txt",
                "review.json",
                "final_report.json",
            ],
        ),
        (
            "dragons_localguys",
            ["scout", "architect", "coder", "verifier"],
            ["recon", "plan", "execute", "verify", "review", "finalize"],
            True,
            [
                "facts.json",
                "plan.json",
                "patch.diff",
                "test_output.txt",
                "review.json",
                "final_report.json",
            ],
        ),
        (
            "refactor_localguys",
            ["scout", "architect", "coder", "verifier"],
            ["recon", "research", "plan", "execute", "verify", "review", "finalize"],
            True,
            [
                "facts.json",
                "plan.json",
                "patch.diff",
                "test_output.txt",
                "review.json",
                "final_report.json",
            ],
        ),
        (
            "bmad_localguys",
            ["scout", "researcher", "architect", "coder", "verifier", "approval"],
            [
                "recon",
                "research",
                "plan",
                "execute",
                "verify",
                "review",
                "approve",
                "finalize",
            ],
            True,
            [
                "facts.json",
                "plan.json",
                "patch.diff",
                "test_output.txt",
                "review.json",
                "approval.json",
                "final_report.json",
            ],
        ),
    ],
)
def test_supported_localguys_workflow_families_resolve_contracts(
    client: TestClient,
    family: str,
    roles: list[str],
    steps: list[str],
    requires_verifier_pass: bool,
    required_artifacts: list[str],
) -> None:
    resp = client.get(f"/api/mcc/workflow-contract/{family}")
    assert resp.status_code == 200
    data = resp.json()
    contract = data["contract"]

    assert data["workflow_family"] == family
    assert contract["workflow_family"] == family
    assert contract["roles"] == roles
    assert contract["steps"] == steps
    assert contract["sandbox_policy"]["mode"] == "playground_only"
    assert (
        contract["completion_policy"]["requires_verifier_pass"]
        is requires_verifier_pass
    )
    assert contract["artifact_contract"]["required"] == required_artifacts
    assert "qwen3:8b" in {row["model_id"] for row in contract["local_model_catalog"]}


def test_local_model_catalog_includes_reflex_decay_fields(client: TestClient) -> None:
    """MARKER_177.BG-002: Verify reflex_decay fields are included in local_model_catalog."""
    resp = client.get("/api/mcc/workflow-contract/g3_localguys")
    assert resp.status_code == 200
    data = resp.json()
    contract = data["contract"]
    catalog = contract["local_model_catalog"]

    coder_entry = next((m for m in catalog if m["model_id"] == "qwen3:8b"), None)
    assert coder_entry is not None, "qwen3:8b should be in catalog"
    assert "fc_reliability" in coder_entry, "fc_reliability field missing"
    assert "max_tools" in coder_entry, "max_tools field missing"
    assert "prefer_simple" in coder_entry, "prefer_simple field missing"
    assert isinstance(coder_entry["fc_reliability"], float), (
        "fc_reliability should be float"
    )
    assert isinstance(coder_entry["max_tools"], int), "max_tools should be int"
    assert isinstance(coder_entry["prefer_simple"], bool), (
        "prefer_simple should be bool"
    )

    verifier_entry = next(
        (m for m in catalog if m["model_id"] == "deepseek-r1:8b"), None
    )
    assert verifier_entry is not None, "deepseek-r1:8b should be in catalog"
    assert "fc_reliability" in verifier_entry
    assert "max_tools" in verifier_entry
    assert "prefer_simple" in verifier_entry

    assert coder_entry["fc_reliability"] == 0.82, (
        "qwen3:8b fc_reliability should be 0.82"
    )
    assert coder_entry["max_tools"] == 8, "qwen3:8b max_tools should be 8"
