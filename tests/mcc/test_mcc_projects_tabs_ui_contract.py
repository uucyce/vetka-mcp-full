from __future__ import annotations

from pathlib import Path


def test_store_has_project_tabs_contract() -> None:
    code = Path("client/src/store/useMCCStore.ts").read_text(encoding="utf-8")
    assert "activeProjectId" in code
    assert "projectTabs" in code
    assert "refreshProjectTabs" in code
    assert "activateProjectTab" in code
    assert "/mcc/projects/list" in code
    assert "/mcc/projects/activate" in code


def test_mcc_renders_project_tab_shell_marker() -> None:
    code = Path("client/src/components/mcc/MyceliumCommandCenter.tsx").read_text(encoding="utf-8")
    assert "MARKER_161.7.MULTIPROJECT.UI.TAB_SHELL_RENDER.V1" in code
    assert "+ project" in code


def test_onboarding_modal_has_local_source_picker_contract() -> None:
    code = Path("client/src/components/mcc/OnboardingModal.tsx").read_text(encoding="utf-8")
    assert "MARKER_161.7.MULTIPROJECT.UI.LOCAL_SOURCE_PICKER.V1" in code
    assert "openFolderDialog" in code
    assert "MARKER_161.7.MULTIPROJECT.UI.SANDBOX_PICKER.V1" in code
    assert "Browse Sandbox in Finder" in code
    assert "MARKER_161.8.MULTIPROJECT.UI.GRANDMA_FLOW_SOURCE_STEP.V1" in code


def test_tauri_detection_hardened_for_dialogs() -> None:
    code = Path("client/src/config/tauri.ts").read_text(encoding="utf-8")
    assert "MARKER_161.7.MULTIPROJECT.UI.TAURI_DETECT_HARDENING.V1" in code
    assert "__TAURI_INTERNALS__" in code


def test_mcc_uses_first_run_instead_of_modal_onboarding() -> None:
    code = Path("client/src/components/mcc/MyceliumCommandCenter.tsx").read_text(encoding="utf-8")
    assert "MARKER_161.8.MULTIPROJECT.UI.NO_MODAL_ONBOARDING.V1" in code
    assert "goToLevel('first_run')" in code
    assert "MARKER_161.8.MULTIPROJECT.UI.DRAFT_TAB_EMPTY_CANVAS.V1" in code
    assert "MARKER_161.8.MULTIPROJECT.UI.DRAFT_TAB_MINI_DEFAULTS.V1" in code
