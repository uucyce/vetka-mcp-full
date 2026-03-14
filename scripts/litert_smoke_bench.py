#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.litert_benchmark_stub import build_litert_benchmark_payload


DEFAULT_MCC_BASE = "http://127.0.0.1:5001/api/mcc"


def _normalize_base_url(base_url: str) -> str:
    value = str(base_url or "").rstrip("/")
    if not value:
        return DEFAULT_MCC_BASE
    if value.endswith("/api/mcc"):
        return value
    if value.endswith("/api"):
        return value + "/mcc"
    return value + "/api/mcc"


def _http_json(method: str, url: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Failed to reach MCC server: {exc.reason}") from exc
    return json.loads(raw or "{}")


def _detect_device_profile() -> str:
    machine = platform.machine().lower()
    system = platform.system().lower()
    if system == "darwin" and machine in {"arm64", "aarch64"}:
        return "apple_silicon"
    return f"{system}_{machine}".strip("_") or "unknown"


def run_litert_smoke_bench() -> Dict[str, Any]:
    started = time.perf_counter()
    module_name = "ai_edge_litert"
    spec = importlib.util.find_spec(module_name)
    cold_start_ms = int((time.perf_counter() - started) * 1000)
    device_profile = _detect_device_profile()
    notes = []
    success_rate = 0.0
    run_status = "blocked"
    accelerator = "gpu_metal" if device_profile == "apple_silicon" else "cpu"

    if spec is None:
        notes.append("ai_edge_litert_not_installed")
    else:
        import_started = time.perf_counter()
        __import__(module_name)
        runtime_ms = int((time.perf_counter() - import_started) * 1000)
        payload = build_litert_benchmark_payload(
            workflow_family="litert_benchmark",
            accelerator=accelerator,
            device_profile=device_profile,
            cold_start_ms=cold_start_ms,
            avg_runtime_ms=runtime_ms,
            success_rate=100.0,
            notes="import_smoke",
        )
        payload["run_status"] = "measured"
        return payload

    payload = build_litert_benchmark_payload(
        workflow_family="litert_benchmark",
        accelerator=accelerator,
        device_profile=device_profile,
        cold_start_ms=cold_start_ms,
        avg_runtime_ms=0,
        success_rate=success_rate,
        notes=",".join(notes),
    )
    payload["run_status"] = run_status
    return payload


def publish_benchmark(payload: Dict[str, Any], *, base_url: str = DEFAULT_MCC_BASE) -> Dict[str, Any]:
    return _http_json("POST", _normalize_base_url(base_url) + "/benchmarks", payload)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="LiteRT smoke benchmark helper")
    parser.add_argument("--server", default=DEFAULT_MCC_BASE, help="MCC base URL or server root")
    parser.add_argument("--publish", action="store_true", help="publish result to MCC benchmark store")
    args = parser.parse_args(argv)

    payload = run_litert_smoke_bench()
    output: Dict[str, Any] = {"success": True, "benchmark": payload}
    if args.publish:
        output["publish"] = publish_benchmark(payload, base_url=args.server)
    print(json.dumps(output, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
