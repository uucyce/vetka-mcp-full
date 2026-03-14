from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "litert_benchmark_stub.py"

spec = importlib.util.spec_from_file_location("litert_benchmark_stub", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(module)


def test_litert_benchmark_payload_matches_shared_metrics_vocabulary() -> None:
    payload = module.build_litert_benchmark_payload(
        workflow_family="litert_benchmark",
        accelerator="gpu_metal",
        device_profile="apple_silicon_m4",
        cold_start_ms=180,
        avg_runtime_ms=42,
        success_rate=100.0,
        notes="starter",
    )

    assert payload["runtime_name"] == "litert"
    assert payload["workflow_family"] == "litert_benchmark"
    assert payload["run_status"] == "measured"
    assert payload["cold_start_ms"] == 180
    assert payload["avg_runtime_ms"] == 42
    assert payload["runtime_ms"] == 42
    assert payload["success_rate"] == 100.0
    assert set(payload) >= {
        "runtime_name",
        "workflow_family",
        "run_status",
        "cold_start_ms",
        "avg_runtime_ms",
        "runtime_ms",
        "artifact_missing_count",
        "required_artifact_count",
        "artifact_present_count",
        "success_rate",
        "notes",
    }
