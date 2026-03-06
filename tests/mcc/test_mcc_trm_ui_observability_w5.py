from __future__ import annotations

from pathlib import Path


def test_w5_mcc_has_trm_badge_and_diagnostics_chip_markers() -> None:
    code = Path("client/src/components/mcc/MyceliumCommandCenter.tsx").read_text(encoding="utf-8")
    assert "MARKER_161.TRM.UI.SOURCE_BADGE.V1" in code
    assert "MARKER_161.TRM.UI.DIAGNOSTICS_CHIP.V1" in code
    assert "trmDiagnosticsUi" in code
    assert "TRM Source: Refined" in code
    assert "profile:" in code
    assert "acc:" in code
    assert "rej:" in code


def test_w5_roadmap_hook_exposes_graph_source_and_trm_meta() -> None:
    code = Path("client/src/hooks/useRoadmapDAG.ts").read_text(encoding="utf-8")
    assert "graphSource: string" in code
    assert "trmMeta: Record<string, any> | null" in code
    assert "setGraphSource(String(buildData?.graph_source || 'baseline'))" in code
    assert "setTrmMeta((buildData?.trm_meta" in code

