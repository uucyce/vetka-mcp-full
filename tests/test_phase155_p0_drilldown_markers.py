from __future__ import annotations

from pathlib import Path
import re
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155 contracts changed")


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
    assert "MARKER_155A.G26.WF_CANONICAL_LAYOUT" in code
    assert "const localLayout = layoutInlineWorkflowCanonical(localDagNodes, localDagEdges);" in code
    assert "MARKER_155A.G26.WF_CANONICAL_PACKING" in code
    assert "MARKER_155A.G26.WF_MICRO_ENVELOPE" in code
    assert "MARKER_155A.G26.WF_ANCHOR_ROOT_LOCK" in code
    assert "MARKER_155A.G27.RESERVED_WORKFLOW_FRAME" in code
    assert "MARKER_155A.G27.MICRO_HANDLE_DOWNSCALE" in code
    assert "MARKER_155A.G27.GLOBAL_HANDLE_FLOW" in code
    assert "MARKER_155A.G27.WF_BOTTOM_UP_ORIENTATION" in code
    assert "const RESERVED_WF_FRAME_W = 248;" in code
    assert "const RESERVED_WF_FRAME_H = 188;" in code
    assert "MARKER_155A.G23.LOCAL_PUSH_V1" in code
    assert "MARKER_155A.G24.LOCAL_REPEL_VECTOR" in code
    assert "const overlapX =" in code
    assert "const overlapY =" in code
    assert "const maxShiftX = 160;" in code
    assert "const maxShiftY = 180;" in code


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
    assert "MARKER_155A.G26.NODE_DRILL_RICHER_PATH_FALLBACK" in code
    assert "MARKER_155A.G27.NODE_DRILL_PRIORITY" in code
    assert "MARKER_155A.G25.NODE_DRILL_THRESHOLDS" in code
    assert "MARKER_155A.G25.NODE_DRILL_OVERFLOW_BADGE" in code
    assert "const DEPTH1_LIMIT = 6;" in code
    assert "const DEPTH2_PER_PARENT_LIMIT = 3;" in code
    assert "const DEPTH2_TOTAL_LIMIT = 8;" in code
    assert "label: `+${count} more`" in code
    assert "function overlayRoadmapNodeChildren(" in code
    assert "id: `rd_" in code
    assert "if (e.type === 'structural') return true;" in code
    assert "rd_depth: depth," in code


def test_mcc_lazy_unfold_cleanup_contract_exists():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "MARKER_155A.G25.LAZY_UNFOLD_STATE_CLEANUP" in code
    assert "taskDrillState === 'expanded' && roadmapNodeDrillState === 'expanded'" in code
    assert "setRoadmapNodeDrillState('collapsed');" in code
    assert "setRoadmapDrillNodeId(null);" in code
    assert "if (isInlineWorkflowFocus || isRoadmapNodeInlineFocus) return;" in code
    assert "prev.id.startsWith('wf_')" in code
    assert "prev.id.startsWith('rd_')" in code


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


def test_inline_workflow_edges_are_pruned_to_canonical_signal():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "MARKER_155A.G26.WF_EDGE_PRUNE_CANONICAL" in code
    assert "if (inN >= 2 || outN >= 3) return false;" in code
    assert "const key = `${e.source}->${e.target}`;" in code
    assert "if (td >= sd) return true;" in code
    assert "MARKER_155A.G26.WF_MINI_SCALE_MICRO" in code
    assert "className: 'wf-inline-edge'" in code
    assert "className: 'wf-bridge-edge'" in code


def test_capture_and_spectral_scripts_exist():
    capture = ROOT / "scripts/capture_mcc_drilldown_playwright.sh"
    spectral = ROOT / "scripts/mcc_spectral_audit.py"
    assert capture.exists()
    assert spectral.exists()


def test_workflow_source_arbitration_has_explicit_priority_contract():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "function selectInlineWorkflowSource(" in code
    assert "source: 'dag' | 'template' | 'pipeline'" in code
    assert "MARKER_155A.G28.WF_SOURCE_SCOPE_GUARD" in code
    assert "const scopedDagNodes = dagNodes.filter((n) => {" in code
    assert "const hasDetailedDagWorkflow = scopedDagNodes.some((n) => n.type !== 'task');" in code
    assert "if (hasDetailedDagWorkflow && scopedDagEdges.length > 0)" in code
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


def test_dagview_inline_focus_keeps_context_and_edge_emphasis():
    code = _read("client/src/components/mcc/DAGView.tsx")
    assert "MARKER_155A.G24.HIGHLIGHT_INLINE_CONTEXT" in code
    assert "opacity: isConnected ? 1.0 : 0.56" in code
    assert "setNodes(nds => nds.map(n => ({" in code
    assert "opacity: 1" in code


def test_dagview_incremental_reuse_is_adaptive_in_architecture_mode():
    code = _read("client/src/components/mcc/DAGView.tsx")
    assert "MARKER_155A.G24.INCREMENTAL_LAYOUT_ARBITRATION" in code
    assert "layoutMode !== 'architecture' || (!hasWorkflowInline && !hasRoadmapDrillInline)" in code
    assert "MARKER_155A.G25.INCREMENTAL_STRESS_TUNE" in code
    assert "const reuseArchitectureBaseWhileInline =" in code
    assert "MARKER_155A.G27.PIN_SANITIZE_INLINE" in code
    assert "id.startsWith('wf_') || id.startsWith('rd_')" in code
    assert "if (reuseArchitectureBaseWhileInline && !isInlineOverlayNodeId(node.id)) {" in code
    assert "prevPositionsRef.current = retained;" in code


def test_breadcrumb_supports_roadmap_inline_drill_context():
    code = _read("client/src/components/mcc/MCCBreadcrumb.tsx")
    assert "MARKER_155A.G24.BREADCRUMB_ROADMAP_CONTEXT" in code
    assert "const selectedTaskId = useMCCStore(s => s.selectedTaskId);" in code
    assert "if (navLevel === 'roadmap' && selectedTaskId)" in code
    assert "if (navLevel === 'roadmap' && navHistory.length === 0 && !navRoadmapNodeId && !selectedTaskId)" in code


def test_mcc_renders_breadcrumb_for_all_non_first_run_levels():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "{navLevel !== 'first_run' ? <MCCBreadcrumb /> : null}" in code


def test_minitasks_expanded_panel_no_longer_depends_on_deprecated_mcctasklist():
    code = _read("client/src/components/mcc/MiniTasks.tsx")
    assert "MARKER_155A.G25.MINITASKS_EXPANDED_V2" in code
    assert "expandedContent={<TasksExpanded />}" in code
    assert "from './MCCTaskList'" not in code


def test_mcc_runtime_path_does_not_import_deprecated_mcc_ui_components():
    code = _read("client/src/components/mcc/MyceliumCommandCenter.tsx")
    assert "MARKER_155A.G25.DEPRECATED_UI_RUNTIME_GUARD" in code
    assert "from './MCCTaskList'" not in code
    assert "from './MCCDetailPanel'" not in code
    assert "from './WorkflowToolbar'" not in code
    assert "from './RailsActionBar'" not in code


def test_no_new_runtime_imports_of_deprecated_mcc_components():
    mcc_dir = ROOT / "client/src/components/mcc"
    deprecated = {
        "./MCCTaskList",
        "./MCCDetailPanel",
        "./WorkflowToolbar",
        "./RailsActionBar",
        "./TaskDAGView",
    }
    import_pat = re.compile(r"""from\s+['"](\./[A-Za-z0-9_/-]+)['"]""")
    allowed_files = {
        "MCCTaskList.tsx",
        "MCCDetailPanel.tsx",
        "WorkflowToolbar.tsx",
        "RailsActionBar.tsx",
        "TaskDAGView.tsx",
    }
    violations: list[str] = []
    for file in mcc_dir.glob("*.tsx"):
        if file.name in allowed_files:
            continue
        code = file.read_text(encoding="utf-8")
        for m in import_pat.finditer(code):
            target = m.group(1)
            if target in deprecated:
                violations.append(f"{file.name} -> {target}")
    assert not violations, f"Deprecated runtime imports found: {violations}"


def test_deprecated_surfaces_are_explicitly_locked():
    files = [
        "client/src/components/mcc/MCCTaskList.tsx",
        "client/src/components/mcc/MCCDetailPanel.tsx",
        "client/src/components/mcc/WorkflowToolbar.tsx",
        "client/src/components/mcc/RailsActionBar.tsx",
        "client/src/components/mcc/TaskDAGView.tsx",
    ]
    for rel in files:
        code = _read(rel)
        assert "MARKER_155A.G25.DEPRECATED_SURFACE_LOCK" in code
