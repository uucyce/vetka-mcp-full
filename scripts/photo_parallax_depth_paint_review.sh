#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
OUT_DIR="$ROOT/photo_parallax_playground/output/review"

SAMPLE_ID="${1:-drone-portrait}"
PRESET_PATH="${2:-$ROOT/photo_parallax_playground/e2e/depth_paint_presets/$SAMPLE_ID.depth-paint.json}"

RAW_DEPTH_PNG="$OUT_DIR/$SAMPLE_ID-depth-raw.png"
RAW_DEPTH_JSON="$OUT_DIR/$SAMPLE_ID-depth-raw.json"
EDITED_DEPTH_PNG="$OUT_DIR/$SAMPLE_ID-depth-edited.png"
EDITED_DEPTH_JSON="$OUT_DIR/$SAMPLE_ID-depth-edited.json"
RAW_COMPOSITE_PNG="$OUT_DIR/$SAMPLE_ID-composite-raw.png"
RAW_COMPOSITE_JSON="$OUT_DIR/$SAMPLE_ID-composite-raw.json"
EDITED_COMPOSITE_PNG="$OUT_DIR/$SAMPLE_ID-composite-edited.png"
EDITED_COMPOSITE_JSON="$OUT_DIR/$SAMPLE_ID-composite-edited.json"
DEPTH_COMPARE_PNG="$OUT_DIR/$SAMPLE_ID-depth-compare.png"
COMPOSITE_COMPARE_PNG="$OUT_DIR/$SAMPLE_ID-composite-compare.png"

mkdir -p "$OUT_DIR"

if [[ ! -f "$PRESET_PATH" ]]; then
  echo "Preset not found: $PRESET_PATH" >&2
  exit 1
fi

copy_latest() {
  local out_png="$1"
  local out_json="$2"
  cp "$OUT_DIR/latest-parallax-review.png" "$out_png"
  cp "$OUT_DIR/latest-parallax-review.json" "$out_json"
}

json_field() {
  local path="$1"
  local field="$2"
  python3 - "$path" "$field" <<'PY'
import json
import sys
path, field = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as fh:
    data = json.load(fh)
print(data.get("debugState", {}).get(field))
PY
}

capture_review() {
  local mode="$1"
  local out_png="$2"
  local out_json="$3"
  local hints_path="${4:-}"
  local require_real_depth="${5:-0}"
  local tries=0
  while [[ "$tries" -lt 2 ]]; do
    tries=$((tries + 1))
    if [[ -n "$hints_path" ]]; then
      PARALLAX_LAB_PREVIEW_MODE="$mode" \
      PARALLAX_LAB_MANUAL_HINTS_PATH="$hints_path" \
        "$ROOT/scripts/photo_parallax_review.sh" "$SAMPLE_ID" --no-open
    else
      PARALLAX_LAB_PREVIEW_MODE="$mode" \
        "$ROOT/scripts/photo_parallax_review.sh" "$SAMPLE_ID" --no-open
    fi
    copy_latest "$out_png" "$out_json"
    if [[ "$require_real_depth" != "1" ]]; then
      return 0
    fi
    if [[ "$(json_field "$out_json" usingRealDepth)" == "True" ]]; then
      return 0
    fi
    sleep 1
  done
  return 0
}

capture_review depth "$RAW_DEPTH_PNG" "$RAW_DEPTH_JSON" "" 1

capture_review depth "$EDITED_DEPTH_PNG" "$EDITED_DEPTH_JSON" "$PRESET_PATH" 1

capture_review composite "$RAW_COMPOSITE_PNG" "$RAW_COMPOSITE_JSON" "" 1

capture_review composite "$EDITED_COMPOSITE_PNG" "$EDITED_COMPOSITE_JSON" "$PRESET_PATH" 1

ffmpeg -y \
  -i "$RAW_DEPTH_PNG" \
  -i "$EDITED_DEPTH_PNG" \
  -filter_complex "[0:v][1:v]hstack=inputs=2[out]" \
  -frames:v 1 -update 1 -map "[out]" "$DEPTH_COMPARE_PNG" >/dev/null 2>&1

ffmpeg -y \
  -i "$RAW_COMPOSITE_PNG" \
  -i "$EDITED_COMPOSITE_PNG" \
  -filter_complex "[0:v][1:v]hstack=inputs=2[out]" \
  -frames:v 1 -update 1 -map "[out]" "$COMPOSITE_COMPARE_PNG" >/dev/null 2>&1

python3 - "$RAW_DEPTH_JSON" "$EDITED_DEPTH_JSON" "$RAW_COMPOSITE_JSON" "$EDITED_COMPOSITE_JSON" <<'PY'
import json
import sys

paths = sys.argv[1:]
labels = [
    "raw_depth",
    "edited_depth",
    "raw_composite",
    "edited_composite",
]
for label, path in zip(labels, paths):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    debug = data.get("debugState", {})
    print(
        f"{label}: preview={debug.get('previewMode')} "
        f"real_depth={debug.get('usingRealDepth')} "
        f"strokes={debug.get('hintStrokeCount')} "
        f"selection={debug.get('selectionCoverage')} "
        f"near_mean={debug.get('nearMean')}"
    )
PY

echo "MARKER_180.PARALLAX.DEPTH_PAINT.REVIEW.DEPTH_COMPARE=$DEPTH_COMPARE_PNG"
echo "MARKER_180.PARALLAX.DEPTH_PAINT.REVIEW.COMPOSITE_COMPARE=$COMPOSITE_COMPARE_PNG"
