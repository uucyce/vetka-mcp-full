#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
OUT_DIR="$ROOT/photo_parallax_playground/output/qwen_plate_gates"

python3 "$ROOT/scripts/photo_parallax_qwen_plate_gate.py" "$@"

echo "MARKER_180.PARALLAX.QWEN_PLATE_GATE.DIR=$OUT_DIR"
echo "MARKER_180.PARALLAX.QWEN_PLATE_GATE.SUMMARY=$OUT_DIR/manifest.json"
