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

if python - <<'PY'
import importlib.util
import sys

missing = [name for name in ("cv2",) if importlib.util.find_spec(name) is None]
if missing:
    sys.exit(1)
PY
then
  echo "opencv already available in $VENV_DIR"
else
  pip install opencv-python-headless
fi
