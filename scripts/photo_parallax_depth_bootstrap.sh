#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
LAB="$ROOT/photo_parallax_playground"
VENV="$LAB/.depth-venv"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Missing Python interpreter: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -d "$VENV" ]]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi

source "$VENV/bin/activate"
python -m pip install --upgrade pip wheel setuptools
python -m pip install "numpy>=1.26" "pillow>=10.4" "huggingface_hub>=0.34" "transformers>=4.57" "safetensors>=0.6" "torch>=2.6"

echo "MARKER_180.PARALLAX.DEPTH.VENV=$VENV"
python - <<'PY'
from importlib.util import find_spec
mods = ["torch", "transformers", "numpy", "PIL"]
for mod in mods:
    print(f"{mod}={bool(find_spec(mod))}")
PY
