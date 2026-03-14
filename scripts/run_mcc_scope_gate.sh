#!/usr/bin/env bash
set -euo pipefail

# MARKER_155.READINESS.G4.MCC_SCOPED_GATE.V1
# Single command for MCC-scoped gate (no global frontend debt noise).

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 scripts/mcc_release_gate.py --json-out data/reports/mcc_release_gate.json
