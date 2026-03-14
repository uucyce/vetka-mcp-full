#!/usr/bin/env bash
set -euo pipefail

# Detached artifact geometry probe:
# 1) requires an already running VETKA dev server
# 2) opens /artifact-media for the provided file
# 3) waits until window.debugMedia is ready
# 4) prints the geometry snapshot JSON and optional PASS/FAIL summary
#
# Usage:
#   scripts/detached_media_geometry_probe.sh /abs/path/to/video.mp4
#   scripts/detached_media_geometry_probe.sh /abs/path/to/video.mp4 4

VIDEO_PATH="${1:-}"
THRESHOLD_PX="${2:-4}"
BASE_URL="${VETKA_MEDIA_BASE_URL:-http://127.0.0.1:3001}"

if [[ -z "$VIDEO_PATH" ]]; then
  echo "Usage: $0 /abs/path/to/video.mp4 [thresholdPx]" >&2
  exit 2
fi
if [[ ! -f "$VIDEO_PATH" ]]; then
  echo "Video not found: $VIDEO_PATH" >&2
  exit 2
fi
if ! command -v npx >/dev/null 2>&1; then
  echo "npx is required" >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 2
fi

export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
PWCLI="$CODEX_HOME/skills/playwright/scripts/playwright_cli.sh"
if [[ ! -f "$PWCLI" ]]; then
  echo "Playwright wrapper not found: $PWCLI" >&2
  exit 2
fi

ENCODED_PATH="$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$VIDEO_PATH")"
FILE_NAME="$(basename "$VIDEO_PATH")"
ENCODED_NAME="$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$FILE_NAME")"
EXTENSION="${FILE_NAME##*.}"
TARGET_URL="${BASE_URL}/artifact-media?path=${ENCODED_PATH}&name=${ENCODED_NAME}&extension=${EXTENSION}"

export PLAYWRIGHT_CLI_SESSION="vetka-media-geometry"
bash "$PWCLI" close >/dev/null 2>&1 || true
bash "$PWCLI" open "$TARGET_URL" >/dev/null

READY="false"
for _ in $(seq 1 120); do
  READY="$(bash "$PWCLI" eval "(()=>Boolean(window.debugMedia && window.debugMedia.snapshot && window.debugMedia.snapshot().ok))()" | tail -n 1 | tr -d '\r' || true)"
  if [[ "$READY" == "true" ]]; then
    break
  fi
  sleep 0.25
done

if [[ "$READY" != "true" ]]; then
  echo "detached media debug API did not become ready" >&2
  bash "$PWCLI" eval "window.debugMedia ? JSON.stringify(window.debugMedia.snapshot(), null, 2) : 'debugMedia_missing'" >&2 || true
  bash "$PWCLI" close >/dev/null 2>&1 || true
  exit 1
fi

SNAPSHOT="$(bash "$PWCLI" eval "JSON.stringify(window.debugMedia.snapshot())" | tail -n 1)"
ASSERTION="$(bash "$PWCLI" eval "JSON.stringify(window.debugMedia.assertNoSideLetterbox(${THRESHOLD_PX}))" | tail -n 1)"

echo "$SNAPSHOT"
echo "$ASSERTION"

PASS="$(python3 -c 'import json, sys; print("true" if json.loads(sys.argv[1]).get("pass") else "false")' "$ASSERTION")"
if [[ "$PASS" != "true" ]]; then
  echo "FAIL: horizontal letterbox exceeds threshold ${THRESHOLD_PX}px" >&2
  bash "$PWCLI" close >/dev/null 2>&1 || true
  exit 1
fi

echo "PASS: detached media geometry probe"
bash "$PWCLI" close >/dev/null 2>&1 || true
