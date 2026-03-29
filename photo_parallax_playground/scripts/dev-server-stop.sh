#!/bin/sh

set -eu

MATCH="photo_parallax_playground/node_modules/.bin/vite"
PIDS="$(pgrep -f "$MATCH" || true)"

if [ -z "$PIDS" ]; then
  echo "No photo_parallax_playground vite processes found."
  exit 0
fi

echo "Stopping photo_parallax_playground vite processes: $PIDS"
kill $PIDS
sleep 1

STILL_RUNNING=""
for PID in $PIDS; do
  if kill -0 "$PID" 2>/dev/null; then
    STILL_RUNNING="$STILL_RUNNING $PID"
  fi
done

if [ -n "${STILL_RUNNING# }" ]; then
  echo "Force stopping stubborn vite processes:${STILL_RUNNING}"
  kill -9 ${STILL_RUNNING# }
fi
