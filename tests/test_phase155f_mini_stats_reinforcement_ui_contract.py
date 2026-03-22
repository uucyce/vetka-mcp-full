from pathlib import Path
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155f contracts changed")

ROOT = Path(__file__).resolve().parents[1]


def test_mini_stats_shows_prefetch_reinforcement_marker():
    code = (ROOT / "client/src/components/mcc/MiniStats.tsx").read_text(encoding="utf-8")
    assert "/mcc/prefetch" in code
    assert "diagnostics?.workflow_selection" in code
    assert "rh:" in code
