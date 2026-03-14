#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"

python3 "$ROOT/scripts/photo_parallax_contour_snap_gate.py" "$@"
