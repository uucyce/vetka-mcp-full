from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_dagview_disables_double_click_zoom():
    code = _read("client/src/components/mcc/DAGView.tsx")
    assert "zoomOnDoubleClick={false}" in code


def test_dagview_click_split_single_vs_double():
    code = _read("client/src/components/mcc/DAGView.tsx")
    assert "if (event.detail > 1) return;" in code
    assert "onNodeDoubleClick?.(node.id);" in code


def test_dagview_workflow_layout_is_adaptive_not_fixed_box():
    code = _read("client/src/components/mcc/DAGView.tsx")
    assert "MARKER_155A.G23.WF_LAYER_PHYSICS_V1" in code
    assert "MARKER_155A.G23.NO_SINK_ACCUMULATION" in code
    assert "const localLayout = layoutSugiyamaBT(localDagNodes, localDagEdges, {" in code
    assert "const targetW = Math.min(340, Math.max(210, 140 + nodeCount * 18));" in code
    assert "const targetH = Math.min(220, Math.max(120, 92 + nodeCount * 12));" in code
    assert "MARKER_155A.G23.LOCAL_PUSH_V1" in code
    assert "shiftY = Math.max(shiftY, Math.round(wfBox.h * 0.55));" in code


def test_mcc_keeps_full_roadmap_context_while_selecting():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "MARKER_155A.P0.WF_STABLE_CONTEXT" in code
    assert "if (navLevel === 'roadmap')" in code
    assert "return roadmapNodeExpanded;" in code


def test_mcc_has_roadmap_node_drill_matryoshka_marker():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "MARKER_155A.G23.NODE_DRILL_NEXT_DEPTH" in code
    assert "MARKER_155A.G23.NODE_DRILL_BREADTH" in code
    assert "MARKER_155A.G23.NODE_DRILL_PATH_FALLBACK" in code
    assert "function overlayRoadmapNodeChildren(" in code
    assert "id: `rd_" in code
    assert "if (e.type === 'structural') return true;" in code
    assert "rd_depth: depth," in code


def test_mini_scale_contract_is_wired():
    dag_layout = _read("client/src/utils/dagLayout.ts")
    assert "miniScale: Number((node as any)?.metadata?.mini_scale)," in dag_layout
    assert "startsWith('rd_')" in dag_layout
    assert "rd_depth: Number((node as any)?.metadata?.rd_depth || 0)," in dag_layout
    for rel in [
        "client/src/components/mcc/nodes/AgentNode.tsx",
        "client/src/components/mcc/nodes/SubtaskNode.tsx",
        "client/src/components/mcc/nodes/ProposalNode.tsx",
        "client/src/components/mcc/nodes/RoadmapTaskNode.tsx",
    ]:
        code = _read(rel)
        assert "miniScale?: number;" in code
        assert "resolveMiniScale" in code


def test_capture_and_spectral_scripts_exist():
    capture = ROOT / "scripts/capture_mcc_drilldown_playwright.sh"
    spectral = ROOT / "scripts/mcc_spectral_audit.py"
    assert capture.exists()
    assert spectral.exists()


def test_workflow_source_arbitration_has_explicit_priority_contract():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "function selectInlineWorkflowSource(" in code
    assert "source: 'dag' | 'template' | 'pipeline'" in code
    assert "const hasDetailedDagWorkflow = dagNodes.some((n) => n.type !== 'task');" in code
    assert "if (hasDetailedDagWorkflow)" in code
    assert "if (templateNodes.length > 0 && templateEdges.length > 0)" in code
    assert "if (pipelineNodes.length > 0 && pipelineEdges.length > 0)" in code
    assert "const selectedWorkflow = selectInlineWorkflowSource(" in code
    assert "selectedWorkflow.nodes" in code
    assert "selectedWorkflow.edges" in code


def test_workflow_template_key_policy_no_longer_forces_wf_prefix_to_default():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "const workflowKey = rawWorkflowKey || 'bmad_default';" in code
    assert "rawWorkflowKey && !rawWorkflowKey.startsWith('wf_')" not in code


def test_task_workflow_expand_is_explicit_toggle_not_selection_side_effect():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "selection alone does not auto-expand workflow" in code
    assert "setTaskDrillState((prev) => (selectedTaskId === taskId && prev === 'expanded' ? 'collapsed' : 'expanded'))" in code
    assert "if (navLevel !== 'roadmap') {" in code
    assert "if (!selectedTaskId) {" in code
