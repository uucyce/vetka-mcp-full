from __future__ import annotations

from pathlib import Path


def test_myco_mcc_probe_runner_and_spec_exist_with_expected_markers():
    script_path = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/myco_mcc_probe_review.sh")
    spec_path = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/player_playground/e2e/myco_mcc_probe.spec.ts")
    app_path = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/player_playground/src/MycoProbeApp.tsx")

    assert script_path.exists()
    assert spec_path.exists()
    assert app_path.exists()

    script = script_path.read_text(encoding="utf-8")
    assert "MARKER_168.MYCO.MCC_PROBE.SUMMARY=" in script
    assert "MYCO_PROBE_ASSET_PATH" in script
    assert "MYCO_PROBE_SURFACE" in script
    assert "MYCO_PROBE_STATE" in script
    assert "realpath" in script or 'cd "$(dirname "$ASSET_PATH")"' in script

    spec = spec_path.read_text(encoding="utf-8")
    assert "myco-probe-file-input" in spec
    assert "window.vetkaMycoProbe?.snapshot()" in spec
