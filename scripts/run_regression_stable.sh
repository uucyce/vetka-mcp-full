#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODE="${1:-smoke}"

if [[ "$MODE" == "smoke" ]]; then
  echo "[regression-stable] mode=smoke"
  pytest -q \
    tests/test_model_autodetect_api.py \
    tests/test_jarvis_workflow_router.py \
    tests/test_jarvis_engram_bridge.py \
    tests/test_jarvis_mcp_server.py \
    tests/jarvis_live/test_jarvis_live_context.py \
    tests/test_phase124_3_auto_read.py \
    tests/test_phase156_voice_s6.py
  exit 0
fi

if [[ "$MODE" == "full" ]]; then
  echo "[regression-stable] mode=full (with known-crash excludes)"
  pytest -q \
    --ignore=tests/test_watchdog_real.py \
    --ignore=tests/test_agents_routes.py
  exit 0
fi

echo "Usage: $0 [smoke|full]"
exit 2
