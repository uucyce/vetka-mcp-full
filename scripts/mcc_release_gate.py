#!/usr/bin/env python3
"""
MCC MVP release gate (G3/G4).

Executes deterministic checks for MCC scope:
- verifier/readability thresholds via DAG auto-compare harness
- runtime safety contract (when runtime is enabled)
- MCC test pack (`tests/mcc`)

Exit code:
- 0: PASS
- 1: FAIL
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Ensure repo root is importable when script is executed directly.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.mcc_dag_compare import run_dag_auto_compare
from src.services.jepa_runtime import runtime_health


MARKER = "MARKER_155.READINESS.G3_G4.RELEASE_GATE.V1"

# Frozen gate thresholds (v1).
MIN_SCORE = 70.0
MAX_ORPHAN_RATE = 0.35
MIN_VARIANTS = 2
REQUIRE_ACYCLIC = True
REQUIRE_MONOTONIC = True


@dataclass
class GateCheck:
    name: str
    passed: bool
    details: Dict[str, Any]


def _sample_records() -> List[Dict[str, Any]]:
    return [
        {"id": "root_src", "path": "src", "kind": "dir", "label": "src"},
        {"id": "core", "path": "src/core.py", "kind": "file", "label": "core"},
        {"id": "api", "path": "src/api.py", "kind": "file", "label": "api"},
        {"id": "ui", "path": "client/app.tsx", "kind": "file", "label": "ui"},
    ]


def _sample_relations() -> List[Dict[str, Any]]:
    return [
        {"source": "core", "target": "api", "weight": 0.9},
        {"source": "api", "target": "ui", "weight": 0.7},
    ]


def _run_compare_gate() -> GateCheck:
    out = run_dag_auto_compare(
        project_id="mcc_release_gate",
        variants=[
            {"name": "clean", "max_nodes": 140, "use_predictive_overlay": False},
            {"name": "balanced", "max_nodes": 220, "use_predictive_overlay": False},
        ],
        source_kind="array",
        records=_sample_records(),
        relations=_sample_relations(),
        scope_name="mcc_release_gate_scope",
        persist_versions=False,
        set_primary_best=False,
    )

    variants = list(out.get("variants") or [])
    best = dict(out.get("best") or {})
    best_score = float(best.get("score") or 0.0)

    decision_ok = True
    orphan_ok = True
    acyclic_ok = True
    monotonic_ok = True

    if variants:
        top = dict(variants[0] or {})
        scorecard = dict(top.get("scorecard") or {})
        decision = str(scorecard.get("decision") or "")
        orphan_raw = scorecard.get("orphan_rate")
        orphan_rate = float(1.0 if orphan_raw is None else orphan_raw)
        acyclic = bool(scorecard.get("acyclic"))
        monotonic = bool(scorecard.get("monotonic_layers"))
        decision_ok = decision in {"pass", "warn"}
        orphan_ok = orphan_rate <= MAX_ORPHAN_RATE
        acyclic_ok = (not REQUIRE_ACYCLIC) or acyclic
        monotonic_ok = (not REQUIRE_MONOTONIC) or monotonic
    else:
        decision_ok = False
        orphan_ok = False
        acyclic_ok = False
        monotonic_ok = False

    passed = all(
        [
            len(variants) >= MIN_VARIANTS,
            best_score >= MIN_SCORE,
            decision_ok,
            orphan_ok,
            acyclic_ok,
            monotonic_ok,
        ]
    )
    return GateCheck(
        name="layout_verifier_gate",
        passed=passed,
        details={
            "count": len(variants),
            "best_score": best_score,
            "min_score": MIN_SCORE,
            "max_orphan_rate": MAX_ORPHAN_RATE,
            "decision_ok": decision_ok,
            "orphan_ok": orphan_ok,
            "acyclic_ok": acyclic_ok,
            "monotonic_ok": monotonic_ok,
            "best": best,
            "top_variant": variants[0] if variants else {},
        },
    )


def _run_runtime_gate() -> GateCheck:
    data = runtime_health(True)
    enabled = bool(data.get("enabled"))
    ok = bool(data.get("ok"))

    # Runtime gate policy:
    # - if runtime disabled, pass with explicit "disabled" detail
    # - if runtime enabled, must be healthy
    passed = (not enabled) or ok
    return GateCheck(
        name="runtime_safety_gate",
        passed=passed,
        details={
            "enabled": enabled,
            "ok": ok,
            "detail": str(data.get("detail") or ""),
            "health": data,
        },
    )


def _run_pytest_gate() -> GateCheck:
    venv_python = ROOT / ".venv" / "bin" / "python"
    py_exec = str(venv_python) if venv_python.exists() else sys.executable
    cmd = [py_exec, "-m", "pytest", "-q", "tests/mcc"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    passed = proc.returncode == 0
    return GateCheck(
        name="mcc_scope_pytest_gate",
        passed=passed,
        details={
            "command": " ".join(cmd),
            "returncode": proc.returncode,
            "stdout_tail": "\n".join(proc.stdout.splitlines()[-30:]),
            "stderr_tail": "\n".join(proc.stderr.splitlines()[-30:]),
        },
    )


def _build_report(checks: List[GateCheck]) -> Dict[str, Any]:
    passed = all(c.passed for c in checks)
    return {
        "marker": MARKER,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if passed else "FAIL",
        "checks": [
            {
                "name": c.name,
                "status": "PASS" if c.passed else "FAIL",
                "details": c.details,
            }
            for c in checks
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json-out",
        default="data/reports/mcc_release_gate.json",
        help="Path to JSON report output",
    )
    args = parser.parse_args()

    checks = [
        _run_compare_gate(),
        _run_runtime_gate(),
        _run_pytest_gate(),
    ]
    report = _build_report(checks)

    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
