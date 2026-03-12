from __future__ import annotations

import json
from pathlib import Path


CONTRACT_PATH = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/myco_mcc_motion_probe_contract_v1.json")


def test_myco_mcc_motion_probe_contract_has_expected_surfaces_and_triggers():
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert payload["marker"] == "MARKER_168.MYCO.MOTION.MCC_PROBE.CONTRACT.V1"

    surface_ids = {row["id"] for row in payload["surfaces"]}
    assert surface_ids == {
        "top_avatar",
        "top_hint",
        "mini_chat_compact",
        "mini_chat_expanded",
        "mini_stats_compact",
        "mini_stats_expanded",
    }

    triggers = set(payload["triggers"])
    assert {
        "idle",
        "ready",
        "speaking",
        "window_focus_chat",
        "window_focus_context",
        "window_focus_stats",
        "window_focus_tasks",
        "window_focus_balance",
        "workflow_selected",
        "model_selected",
        "task_started",
        "task_completed",
        "task_failed",
        "parallel_role_active",
    }.issubset(triggers)


def test_myco_mcc_motion_probe_contract_role_policy_matches_design():
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert payload["roles"]["singleton"] == ["architect", "researcher", "verifier"]
    assert payload["roles"]["parallel"]["coder"] == 2
    assert payload["roles"]["parallel"]["scout"] == 3

    assert "motion_dominance_score" in payload["metrics"]
    assert "surface_state_matrix" in payload["artifacts"]
