from __future__ import annotations

import json

import pytest


class _BridgeProbe:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish_workflow_complete(self, workflow_id: str, result: dict) -> None:
        self.events.append((workflow_id, dict(result or {})))


@pytest.mark.asyncio
async def test_mycelium_execute_workflow_threads_ownership_contract_to_runtime_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.mcp.mycelium_mcp_server import call_tool
    from src.mcp.tools.workflow_tools import ExecuteWorkflowTool

    captured: dict = {}
    bridge = _BridgeProbe()

    async def _fake_execute_parallel(
        self,
        feature_request: str,
        workflow_id: str,
        rich_context=None,
        workflow_family: str = "",
        workflow_runtime_metadata: dict | None = None,
    ) -> dict:
        captured["feature_request"] = feature_request
        captured["workflow_id"] = workflow_id
        captured["workflow_family"] = workflow_family
        captured["workflow_runtime_metadata"] = dict(workflow_runtime_metadata or {})
        return {
            "workflow_id": workflow_id,
            "status": "complete",
            "probe": "MARKER_173.P6.P11",
        }

    monkeypatch.setattr(
        "src.orchestration.orchestrator_with_elisya.OrchestratorWithElisya._execute_parallel",
        _fake_execute_parallel,
    )
    monkeypatch.setattr("src.orchestration.services.get_mcp_state_bridge", lambda: bridge)

    async def _async_vetka_execute_workflow(
        *,
        request: str,
        workflow_type: str = "pm_to_qa",
        workflow_family: str = "",
        include_eval: bool = True,
        timeout: int = 300,
    ) -> dict:
        del timeout
        tool = ExecuteWorkflowTool()
        return await tool._execute_async(
            request=request,
            workflow_type=workflow_type,
            workflow_id="wf_probe_p611",
            include_eval=include_eval,
            workflow_family=workflow_family,
        )

    monkeypatch.setattr(
        "src.mcp.tools.workflow_tools.vetka_execute_workflow",
        _async_vetka_execute_workflow,
    )

    payload = {
        "request": "Ownership localguys runtime probe for workflow-entry REFLEX preflight.",
        "workflow_type": "pm_to_qa",
        "workflow_family": "ownership_localguys",
        "include_eval": False,
        "timeout": 30,
    }
    result = await call_tool("mycelium_execute_workflow", payload)
    data = json.loads(result[0].text)

    assert data["success"] is True
    wf_result = data["result"]
    runtime_meta = dict(wf_result.get("runtime_metadata") or {})

    assert wf_result["workflow_family"] == "ownership_localguys"
    assert runtime_meta["workflow_family"] == "ownership_localguys"
    assert runtime_meta["direct_allowed_tools"] == ["mycelium_task_board"]
    assert runtime_meta["expected_sequence"] == ["mycelium_task_board"]
    assert runtime_meta["write_opt_ins"]["task_board"] is True
    assert runtime_meta["write_opt_ins"]["edit_file"] is False
    assert runtime_meta["reflex_policy"]["allow_task_board_writes"] is True

    assert captured["workflow_family"] == "ownership_localguys"
    assert captured["workflow_runtime_metadata"]["workflow_family"] == "ownership_localguys"
    assert captured["workflow_runtime_metadata"]["write_opt_ins"]["task_board"] is True
    assert captured["workflow_runtime_metadata"]["write_opt_ins"]["edit_file"] is False
    assert captured["workflow_runtime_metadata"]["direct_allowed_tools"] == ["mycelium_task_board"]

    assert len(bridge.events) == 1
    assert bridge.events[0][0] == wf_result["workflow_id"]
