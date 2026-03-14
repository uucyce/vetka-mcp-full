#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
OUT_DIR="$ROOT/photo_parallax_playground/output/layered_edit_flow"
PYTHON_BIN="$ROOT/photo_parallax_playground/.depth-venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$ROOT/.venv/bin/python"
fi

"$PYTHON_BIN" "$ROOT/scripts/photo_parallax_layered_gate_review.py" --input "$OUT_DIR"

if [[ "${1:-}" != "--no-open" ]] && command -v open >/dev/null 2>&1; then
  open "$OUT_DIR/layered_gate_batch_sheet.png"
fi
