from __future__ import annotations

from pathlib import Path


def test_stats_workflow_diagnostics_contract() -> None:
    code = Path("client/src/components/mcc/MiniStats.tsx").read_text(encoding="utf-8")
    assert "MARKER_167.STATS_WORKFLOW.DIAGNOSTICS.V1" in code
    assert "Workflow Diagnostics" in code
    assert "workflow:" in code
    assert "origin:" in code
    assert "binding:" in code
    assert "override:" in code
    assert "graph:" in code
    assert "runtime:" in code
