from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "litert_smoke_bench.py"


def test_litert_smoke_bench_reports_blocked_when_runtime_missing() -> None:
    assert importlib.util.find_spec("ai_edge_litert") is None

    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["success"] is True
    bench = payload["benchmark"]
    assert bench["runtime_name"] == "litert"
    assert bench["workflow_family"] == "litert_benchmark"
    assert bench["run_status"] == "blocked"
    assert "ai_edge_litert_not_installed" in bench["notes"]
