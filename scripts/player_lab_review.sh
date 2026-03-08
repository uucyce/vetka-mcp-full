#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
LAB="$ROOT/player_playground"
OUT_DIR="$LAB/output/review"
STAMP="$(date +%Y%m%d-%H%M%S)"

VIDEO_PATH="${1:-}"
SCREENSHOT_PATH="$OUT_DIR/player-review-$STAMP.png"
SNAPSHOT_PATH="$OUT_DIR/player-review-$STAMP.json"
LATEST_SCREENSHOT="$OUT_DIR/latest-player-review.png"
LATEST_SNAPSHOT="$OUT_DIR/latest-player-review.json"

mkdir -p "$OUT_DIR"

cd "$LAB"

PLAYER_LAB_VIDEO_PATH="$VIDEO_PATH" \
PLAYER_LAB_SCREENSHOT_PATH="$SCREENSHOT_PATH" \
PLAYER_LAB_SNAPSHOT_PATH="$SNAPSHOT_PATH" \
npx playwright test e2e/dream_player_probe.spec.ts --reporter=line

cp "$SCREENSHOT_PATH" "$LATEST_SCREENSHOT"
cp "$SNAPSHOT_PATH" "$LATEST_SNAPSHOT"

echo "MARKER_168.VIDEOPLAYER.REVIEW.SCREENSHOT=$SCREENSHOT_PATH"
echo "MARKER_168.VIDEOPLAYER.REVIEW.SNAPSHOT=$SNAPSHOT_PATH"
echo "MARKER_168.VIDEOPLAYER.REVIEW.LATEST_SCREENSHOT=$LATEST_SCREENSHOT"
echo "MARKER_168.VIDEOPLAYER.REVIEW.LATEST_SNAPSHOT=$LATEST_SNAPSHOT"

if [[ "${2:-}" != "--no-open" ]] && command -v open >/dev/null 2>&1; then
  open "$SCREENSHOT_PATH"
fi
