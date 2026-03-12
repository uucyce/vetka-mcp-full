#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
LAB="$ROOT/photo_parallax_playground"
VENV="$LAB/.depth-venv"

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Depth venv missing. Run scripts/photo_parallax_depth_bootstrap.sh first." >&2
  exit 1
fi

source "$VENV/bin/activate"
python "$ROOT/scripts/photo_parallax_mask_bakeoff.py" "$@"
