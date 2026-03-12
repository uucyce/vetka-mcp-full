#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
LAB="$ROOT/photo_parallax_playground"
VENV="$LAB/.depth-venv"
CHECKPOINT_DIR="$LAB/checkpoints/realesrgan"
CHECKPOINT_PATH="$CHECKPOINT_DIR/RealESRGAN_x2plus.pth"
CHECKPOINT_URL="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth"

if [[ ! -d "$VENV" ]]; then
  echo "Missing venv: $VENV" >&2
  echo "Run ./scripts/photo_parallax_depth_bootstrap.sh first." >&2
  exit 1
fi

source "$VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install "basicsr>=1.4.2" "realesrgan>=0.3.0"

mkdir -p "$CHECKPOINT_DIR"
if [[ ! -f "$CHECKPOINT_PATH" ]]; then
  curl -L "$CHECKPOINT_URL" -o "$CHECKPOINT_PATH"
fi

python - <<'PY'
import importlib.util
import sys
import types
from pathlib import Path

from torchvision.transforms import functional as F

mod = types.ModuleType("torchvision.transforms.functional_tensor")
mod.rgb_to_grayscale = F.rgb_to_grayscale
sys.modules["torchvision.transforms.functional_tensor"] = mod

from realesrgan import RealESRGANer  # noqa: F401
from basicsr.archs.rrdbnet_arch import RRDBNet  # noqa: F401

checkpoint = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/checkpoints/realesrgan/RealESRGAN_x2plus.pth")
print(f"realesrgan={bool(importlib.util.find_spec('realesrgan'))}")
print(f"basicsr={bool(importlib.util.find_spec('basicsr'))}")
print(f"checkpoint_exists={checkpoint.exists()}")
print(f"checkpoint_path={checkpoint}")
PY
