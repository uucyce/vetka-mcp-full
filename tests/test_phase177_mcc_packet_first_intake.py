from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


def test_build_role_context_slice_is_role_aware() -> None:
    from src.services.roadmap_task_sync import build_role_context_slice

    packet = {
        "task": {"id": "tb_packet_1", "title": "Packet-first task"},
        "workflow_binding": {"workflow_family": "g3_localguys"},
        "workflow_contract": {"steps": ["recon", "execute"]},
        "governance": {"owner_agent": "codex"},
        "roadmap_binding": {"roadmap_node_id": "node_sync_1"},
        "docs": {
            "architecture_docs": ["docs/177_MCC_local/MCC_ROLE_CONTEXT_POLICY_V1.md"],
            "recon_docs": ["docs/177_MCC_local/MCC_AGENT_CONTEXT_AUDIT_20260312.md"],
        },
        "code_scope": {"closure_files": ["src/services/roadmap_task_sync.py"]},
        "tests": {"closure_tests": ["python -m pytest tests/test_phase177_mcc_packet_first_intake.py -q"]},
        "artifacts": {"recent_localguys_runs": [{"run_id": "run_1"}]},
        "history": [{"status": "running"}, {"status": "done"}],
        "gaps": ["missing preview"],
    }

    architect = build_role_context_slice(
        packet,
        "architect",
        overlays={
            "viewport_summary": "task node_sync_1 and stats window in focus",
            "pinned_summary": "[Pinned Files]\\n  src/services/roadmap_task_sync.py",
            "myco_focus": {"label": "node_sync_1"},
        },
    )
    coder = build_role_context_slice(packet, "coder", overlays={"pinned_summary": "[Pinned Files]\\n  src/services/roadmap_task_sync.py"})
    verifier = build_role_context_slice(packet, "verifier", overlays={"viewport_summary": "must stay hidden"})
    myco = build_role_context_slice(
        packet,
        "myco",
        overlays={
            "viewport_summary": "task node_sync_1 and stats window in focus",
            "pinned_summary": "[Pinned Files]\\n  src/services/roadmap_task_sync.py",
            "myco_focus": {"label": "node_sync_1"},
        },
    )

    assert architect["docs"]["architecture_docs"] == ["docs/177_MCC_local/MCC_ROLE_CONTEXT_POLICY_V1.md"]
    assert architect["roadmap_binding"]["roadmap_node_id"] == "node_sync_1"
    assert architect["history"] == [{"status": "running"}, {"status": "done"}]
    assert architect["ui_context"]["viewport_summary"] == "task node_sync_1 and stats window in focus"
    assert "pinned_summary" in architect["ui_context"]

    assert "docs" not in coder
    assert coder["code_scope"]["closure_files"] == ["src/services/roadmap_task_sync.py"]
    assert coder["artifacts"]["recent_localguys_runs"][0]["run_id"] == "run_1"
    assert "viewport_summary" not in coder["ui_context"]
    assert "pinned_summary" in coder["ui_context"]

    assert "code_scope" not in verifier
    assert verifier["tests"]["closure_tests"] == ["python -m pytest tests/test_phase177_mcc_packet_first_intake.py -q"]
    assert verifier["artifacts"]["recent_localguys_runs"][0]["run_id"] == "run_1"
    assert "ui_context" not in verifier

    assert "code_scope" not in myco
    assert len(myco["docs"]["architecture_docs"]) == 1
    assert myco["docs"]["recon_docs"] == ["docs/177_MCC_local/MCC_AGENT_CONTEXT_AUDIT_20260312.md"]
    assert myco["ui_context"]["viewport_summary"] == "task node_sync_1 and stats window in focus"
    assert myco["ui_context"]["myco_focus"]["label"] == "node_sync_1"


@pytest.mark.asyncio
async def test_pipeline_execute_passes_mcc_task_packet_to_architect_prefetch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from src.orchestration.agent_pipeline import AgentPipeline
    from src.orchestration.task_board import TaskBoard
    from src.services.architect_prefetch import PrefetchContext

    board = TaskBoard(board_file=tmp_path / "task_board.json")
    task_id = board.add_task(
        title="Packet-first task",
        description="Use canonical MCC packet",
        workflow_family="g3_localguys",
        workflow_id="g3_localguys",
        roadmap_id="rm_177",
        roadmap_node_id="node_sync_1",
        roadmap_lane="core",
        roadmap_title="Sync Node",
        architecture_docs=["docs/177_MCC_local/MCC_WORKFLOW_CONTRACT_V1.md"],
        closure_files=["src/services/roadmap_task_sync.py"],
        closure_tests=["python -m pytest tests/test_phase177_mcc_packet_first_intake.py -q"],
    )

    monkeypatch.setattr("src.orchestration.task_board.get_task_board", lambda: board)

    async def _fake_contract(_family: str):
        return {"workflow_family": "g3_localguys", "steps": ["recon", "execute"], "artifact_contract": {"required": []}}

    import src.api.routes.mcc_routes as routes

    monkeypatch.setattr(routes, "_resolve_workflow_contract", _fake_contract)

    captured: dict = {}

    def _fake_prepare(**kwargs):
        captured.update(kwargs)
        return PrefetchContext(
            workflow_id="g3_localguys",
            workflow_name="G3 Localguys",
            preset="dragon_silver",
            task_packet=dict(kwargs.get("task_packet") or {}),
        )

    monkeypatch.setattr("src.services.architect_prefetch.ArchitectPrefetch.prepare", _fake_prepare)

    pipeline = AgentPipeline(chat_id="test-chat", auto_write=False, preset="dragon_silver")
    pipeline._board_task_id = task_id
    pipeline._emit_progress = AsyncMock()
    pipeline._emit_to_chat = AsyncMock()
    pipeline._emit_stream_event = MagicMock()
    pipeline._update_task = MagicMock()
    pipeline._log_stm_summary = MagicMock()
    pipeline._bridge_to_global_stm = MagicMock()
    pipeline._parallel_recon = AsyncMock(return_value=(None, {"confidence": 0.95}))
    pipeline._architect_plan = AsyncMock(return_value={
        "subtasks": [{"description": "implement feature", "needs_research": False, "marker": "M1"}],
        "execution_order": "sequential",
        "estimated_complexity": "low",
    })
    pipeline._execute_subtask = AsyncMock(return_value="implemented code")
    pipeline._verify_subtask = AsyncMock(return_value={
        "passed": True, "issues": [], "confidence": 0.9, "severity": "minor"
    })
    pipeline._resolve_tier = MagicMock(return_value=None)

    result = await pipeline.execute("test task", "build")

    assert result["status"] == "done"
    assert captured["workflow_family"] == "g3_localguys"
    packet = captured["task_packet"]
    assert packet["roadmap_binding"]["roadmap_node_id"] == "node_sync_1"
    assert packet["docs"]["architecture_docs"] == ["docs/177_MCC_local/MCC_WORKFLOW_CONTRACT_V1.md"]
    assert packet["tests"]["closure_tests"] == ["python -m pytest tests/test_phase177_mcc_packet_first_intake.py -q"]
