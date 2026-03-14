from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCC = ROOT / "client/src/components/mcc/MyceliumCommandCenter.tsx"
STORE = ROOT / "client/src/store/useMCCStore.ts"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_store_exposes_workflow_source_mode_contract():
    code = _read(STORE)
    assert "export type WorkflowSourceMode = 'runtime' | 'design' | 'predict';" in code
    assert "workflowSourceMode: 'design'," in code
    assert "setWorkflowSourceMode: (mode) => set({ workflowSourceMode: mode })," in code


def test_mcc_guards_source_mode_setter_before_calling():
    code = _read(MCC)
    assert "typeof setWorkflowSourceMode === 'function'" in code
    assert "if (workflowSourceMode !== 'runtime' && typeof setWorkflowSourceMode === 'function')" in code


def test_task_anchor_is_always_visible_and_selection_expands():
    code = _read(MCC)
    assert "MARKER_155E.ROADMAP_TASK_ANCHOR_ALWAYS_VISIBLE.V1" in code
    assert "overlay-affects-primary-" in code
    assert "for (const anchor of effectiveAnchors.slice(1))" in code


def test_roadmap_uses_design_as_default_source_mode():
    code = _read(MCC)
    assert ": 'design';" in code
    assert "const effectiveWorkflowSourceMode: WorkflowSourceMode = isWorkflowRuntimeForced ? 'runtime' : normalizedWorkflowSourceMode;" in code


def test_roadmap_source_override_is_not_global_default():
    code = _read(MCC)
    assert "const roadmapSourceOverrideEnabled =" in code
    assert "debugMode || (navLevel === 'roadmap' && taskDrillState === 'expanded' && Boolean(selectedTaskId));" in code
