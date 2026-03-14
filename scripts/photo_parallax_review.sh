#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
LAB="$ROOT/photo_parallax_playground"
OUT_DIR="$LAB/output/review"
STAMP="$(date +%Y%m%d-%H%M%S)"

SAMPLE_ID="${1:-hover-politsia}"
PREVIEW_MODE="${PARALLAX_LAB_PREVIEW_MODE:-}"
MANUAL_HINTS_PATH="${PARALLAX_LAB_MANUAL_HINTS_PATH:-}"
SCREENSHOT_PATH="$OUT_DIR/parallax-review-$STAMP.png"
SNAPSHOT_PATH="$OUT_DIR/parallax-review-$STAMP.json"
LATEST_SCREENSHOT="$OUT_DIR/latest-parallax-review.png"
LATEST_SNAPSHOT="$OUT_DIR/latest-parallax-review.json"

mkdir -p "$OUT_DIR"

cd "$LAB"

if command -v lsof >/dev/null 2>&1; then
  lsof -ti tcp:1434 | xargs -r kill >/dev/null 2>&1 || true
fi

PARALLAX_LAB_SAMPLE_ID="$SAMPLE_ID" \
PARALLAX_LAB_PREVIEW_MODE="$PREVIEW_MODE" \
PARALLAX_LAB_MANUAL_HINTS_PATH="$MANUAL_HINTS_PATH" \
PARALLAX_LAB_SCREENSHOT_PATH="$SCREENSHOT_PATH" \
PARALLAX_LAB_SNAPSHOT_PATH="$SNAPSHOT_PATH" \
npx playwright test e2e/parallax_review_probe.spec.ts --reporter=line

cp "$SCREENSHOT_PATH" "$LATEST_SCREENSHOT"
cp "$SNAPSHOT_PATH" "$LATEST_SNAPSHOT"

echo "MARKER_180.PARALLAX.REVIEW.SCREENSHOT=$SCREENSHOT_PATH"
echo "MARKER_180.PARALLAX.REVIEW.SNAPSHOT=$SNAPSHOT_PATH"
echo "MARKER_180.PARALLAX.REVIEW.LATEST_SCREENSHOT=$LATEST_SCREENSHOT"
echo "MARKER_180.PARALLAX.REVIEW.LATEST_SNAPSHOT=$LATEST_SNAPSHOT"

python3 - "$SNAPSHOT_PATH" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as fh:
    data = json.load(fh)

print(
    "MARKER_180.PARALLAX.REVIEW.SUMMARY="
    f"sample:{data.get('sampleId')} "
    f"score:{data.get('previewScore')} "
    f"overscan:{data.get('overscanPct')} "
    f"disocclusion:{data.get('disocclusionRisk')} "
    f"cardboard:{data.get('cardboardRisk')}"
)
PY

if [[ "${2:-}" != "--no-open" ]] && command -v open >/dev/null 2>&1; then
  open "$SCREENSHOT_PATH"
fi
