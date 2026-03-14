#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
LAB="$ROOT/player_playground"
OUT_DIR="$LAB/output/myco_probe"
STAMP="$(date +%Y%m%d-%H%M%S)"

ASSET_PATH="${1:-}"
SURFACE="${2:-top_avatar}"
STATE="${3:-idle}"

if [[ -n "$ASSET_PATH" ]]; then
  if command -v realpath >/dev/null 2>&1; then
    ASSET_PATH="$(realpath "$ASSET_PATH")"
  else
    ASSET_PATH="$(cd "$(dirname "$ASSET_PATH")" && pwd)/$(basename "$ASSET_PATH")"
  fi
fi

SCREENSHOT_PATH="$OUT_DIR/${SURFACE}-${STATE}-$STAMP.png"
SNAPSHOT_PATH="$OUT_DIR/${SURFACE}-${STATE}-$STAMP.json"
LATEST_SCREENSHOT="$OUT_DIR/latest-${SURFACE}-${STATE}.png"
LATEST_SNAPSHOT="$OUT_DIR/latest-${SURFACE}-${STATE}.json"

mkdir -p "$OUT_DIR"

cd "$LAB"

if command -v lsof >/dev/null 2>&1; then
  lsof -ti tcp:1424 | xargs -r kill >/dev/null 2>&1 || true
fi

MYCO_PROBE_ASSET_PATH="$ASSET_PATH" \
MYCO_PROBE_SURFACE="$SURFACE" \
MYCO_PROBE_STATE="$STATE" \
MYCO_PROBE_SCREENSHOT_PATH="$SCREENSHOT_PATH" \
MYCO_PROBE_SNAPSHOT_PATH="$SNAPSHOT_PATH" \
npx playwright test e2e/myco_mcc_probe.spec.ts --reporter=line

cp "$SCREENSHOT_PATH" "$LATEST_SCREENSHOT"
cp "$SNAPSHOT_PATH" "$LATEST_SNAPSHOT"

echo "MARKER_168.MYCO.MCC_PROBE.SCREENSHOT=$SCREENSHOT_PATH"
echo "MARKER_168.MYCO.MCC_PROBE.SNAPSHOT=$SNAPSHOT_PATH"
echo "MARKER_168.MYCO.MCC_PROBE.LATEST_SCREENSHOT=$LATEST_SCREENSHOT"
echo "MARKER_168.MYCO.MCC_PROBE.LATEST_SNAPSHOT=$LATEST_SNAPSHOT"

python3 - "$SNAPSHOT_PATH" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as fh:
    data = json.load(fh)

print(
    "MARKER_168.MYCO.MCC_PROBE.SUMMARY="
    f"surface:{data.get('surface')} "
    f"state:{data.get('state')} "
    f"clip:{data.get('clipRatio')} "
    f"text_overlap:{data.get('textOverlapRatio')} "
    f"dominance:{data.get('motionDominanceScore')} "
    f"readable:{data.get('readabilityPass')}"
)
PY
