#!/usr/bin/env bash
set -euo pipefail

# Real-browser media probe:
# 1) serve a local HTML page + target video
# 2) play video in Playwright-controlled Chromium
# 3) assert currentTime advances
#
# Usage:
#   scripts/media_dom_playback_probe.sh /abs/path/to/video.mp4

VIDEO_PATH="${1:-}"
if [[ -z "$VIDEO_PATH" ]]; then
  echo "Usage: $0 /abs/path/to/video.mp4" >&2
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

TMP_DIR="$(mktemp -d /tmp/vetka_media_probe.XXXXXX)"
SERVER_PORT="${VETKA_MEDIA_PROBE_PORT:-39117}"
SERVER_PID=""

cleanup() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT INT TERM

cp "$VIDEO_PATH" "$TMP_DIR/probe.mp4"
cat > "$TMP_DIR/index.html" <<'HTML'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>VETKA media probe</title>
  <style>
    html, body { margin: 0; background: #0a0a0a; color: #e5e5e5; font-family: sans-serif; }
    main { padding: 12px; }
    video { width: 640px; max-width: 100%; background: #000; border: 1px solid #333; }
  </style>
</head>
<body>
  <main>
    <video id="probe-video" preload="auto" muted playsinline src="/probe.mp4"></video>
  </main>
</body>
</html>
HTML

python3 -m http.server "$SERVER_PORT" --bind 127.0.0.1 --directory "$TMP_DIR" >/tmp/vetka_media_probe_server.log 2>&1 &
SERVER_PID=$!

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${SERVER_PORT}/index.html" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done
if ! curl -fsS "http://127.0.0.1:${SERVER_PORT}/index.html" >/dev/null 2>&1; then
  echo "HTTP probe server failed to start on ${SERVER_PORT}" >&2
  exit 1
fi

export PLAYWRIGHT_CLI_SESSION="vmprobe"
bash "$PWCLI" close >/dev/null 2>&1 || true
bash "$PWCLI" open "http://127.0.0.1:${SERVER_PORT}/index.html" >/dev/null
bash "$PWCLI" eval "(v=document.querySelector('#probe-video'), v ? (v.currentTime=0, v.muted=true, v.play(), 'ok') : 'missing')" >/tmp/vetka_media_probe_playwright.log
sleep 1.4
bash "$PWCLI" eval "document.querySelector('#probe-video')?.currentTime || 0" >>/tmp/vetka_media_probe_playwright.log
bash "$PWCLI" close >/dev/null 2>&1 || true

CURRENT_TIME="$(grep -E "^[0-9]+(\\.[0-9]+)?$" /tmp/vetka_media_probe_playwright.log | tail -n 1 || true)"
if [[ -z "$CURRENT_TIME" ]]; then
  echo "Could not parse currentTime from Playwright output" >&2
  cat /tmp/vetka_media_probe_playwright.log >&2 || true
  exit 1
fi
awk -v t="$CURRENT_TIME" 'BEGIN { if (t <= 0.25) exit 1; }' || {
  echo "Playback currentTime too small: $CURRENT_TIME" >&2
  cat /tmp/vetka_media_probe_playwright.log >&2 || true
  exit 1
}
echo "PLAYBACK_CURRENT_TIME=${CURRENT_TIME}"
echo "PASS: DOM playback probe"
