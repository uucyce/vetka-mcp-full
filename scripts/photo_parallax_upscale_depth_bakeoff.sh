#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
VENV_DIR="$ROOT_DIR/photo_parallax_playground/.depth-venv"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Missing venv: $VENV_DIR" >&2
  echo "Run ./scripts/photo_parallax_depth_bootstrap.sh first." >&2
  exit 1
fi

source "$VENV_DIR/bin/activate"
export HF_HUB_DISABLE_XET=1
export PYTHONUNBUFFERED=1

python "$ROOT_DIR/scripts/photo_parallax_upscale_depth_bakeoff.py" "$@"
