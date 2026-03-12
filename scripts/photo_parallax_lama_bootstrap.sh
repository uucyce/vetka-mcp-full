#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
VENV_DIR="$ROOT_DIR/photo_parallax_playground/.depth-venv"
MODEL_DIR="$ROOT_DIR/photo_parallax_playground/checkpoints/lama"
MODEL_PATH="$MODEL_DIR/big-lama.pt"
MODEL_URL="https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Missing venv: $VENV_DIR" >&2
  echo "Run ./scripts/photo_parallax_depth_bootstrap.sh first." >&2
  exit 1
fi

source "$VENV_DIR/bin/activate"

if python - <<'PY'
import importlib.util
import sys

missing = [name for name in ("simple_lama_inpainting",) if importlib.util.find_spec(name) is None]
if missing:
    sys.exit(1)
PY
then
  echo "simple-lama-inpainting already available in $VENV_DIR"
else
  pip install simple-lama-inpainting==0.1.2 --no-deps
fi

mkdir -p "$MODEL_DIR"
if [[ ! -f "$MODEL_PATH" ]]; then
  curl -L "$MODEL_URL" -o "$MODEL_PATH"
fi

LAMA_MODEL="$MODEL_PATH" python - <<'PY'
from pathlib import Path
import torch
from simple_lama_inpainting import SimpleLama

model_path = Path(Path.cwd(), "photo_parallax_playground/checkpoints/lama/big-lama.pt")
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
print(f"model_path={model_path}")
print(f"device={device}")
SimpleLama(device=device)
print("LaMa bootstrap verification passed")
PY
