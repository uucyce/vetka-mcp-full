#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any, Dict


def build_litert_benchmark_payload(
    *,
    workflow_family: str = "litert_benchmark",
    accelerator: str = "gpu_metal",
    device_profile: str = "apple_silicon",
    cold_start_ms: int = 0,
    avg_runtime_ms: int = 0,
    success_rate: float = 0.0,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "runtime_name": "litert",
        "workflow_family": str(workflow_family),
        "run_status": "measured" if success_rate > 0 else "pending",
        "device_profile": str(device_profile),
        "accelerator": str(accelerator),
        "cold_start_ms": int(cold_start_ms),
        "avg_runtime_ms": int(avg_runtime_ms),
        "runtime_ms": int(avg_runtime_ms),
        "artifact_missing_count": 0,
        "required_artifact_count": 0,
        "artifact_present_count": 0,
        "success_rate": float(success_rate),
        "notes": str(notes),
    }


if __name__ == "__main__":
    payload = build_litert_benchmark_payload()
    print(json.dumps(payload, ensure_ascii=True, indent=2))
