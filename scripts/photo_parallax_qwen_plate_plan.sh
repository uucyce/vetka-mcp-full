#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
VENV_PY="$ROOT_DIR/photo_parallax_playground/.depth-venv/bin/python"

"$VENV_PY" "$ROOT_DIR/scripts/photo_parallax_qwen_plate_plan.py" "$@"
