#!/bin/bash
# MARKER_204.3: Agent notification signal checker — PreToolUse hook
#
# Usage (in .claude/settings.json PreToolUse hook):
#   "command": "bash scripts/check_notifications.sh <ROLE>"
#
# Reads ~/.claude/signals/<ROLE>.json — signal file written by task_board.send_notification()
# Outputs notifications to stdout (injected as context by Claude Code PreToolUse hook).
# Deletes signal file after reading (one-shot delivery).
# Fast no-op (<1ms) when no signal file exists.
#
# ROLE: positional arg $1, or env var VETKA_AGENT_ROLE
#
# Signal file format (JSON array):
#   [{"id":"notif_xxx","from":"Commander","message":"...","ts":"ISO","ntype":"custom"}]

set -euo pipefail

ROLE="${1:-${VETKA_AGENT_ROLE:-}}"

# Fast exit: no role → no-op
[ -z "$ROLE" ] && exit 0

SIGNAL_DIR="$HOME/.claude/signals"
SIGNAL_FILE="$SIGNAL_DIR/${ROLE}.json"

# Fast exit: no signal file (stat is instant, <1ms)
[ -f "$SIGNAL_FILE" ] || exit 0
[ -s "$SIGNAL_FILE" ] || { rm -f "$SIGNAL_FILE"; exit 0; }

# Atomic read: move first, then parse (prevents duplicate delivery on race)
TEMP_FILE="${SIGNAL_FILE}.$$.tmp"
mv "$SIGNAL_FILE" "$TEMP_FILE" 2>/dev/null || exit 0

# Parse and output on stdout (Claude Code PreToolUse injects stdout as model context)
python3 - "$TEMP_FILE" <<'PYEOF'
import sys, json, os

try:
    with open(sys.argv[1]) as f:
        notifications = json.load(f)
    if not isinstance(notifications, list) or not notifications:
        sys.exit(0)

    print("")
    print("┌─────────────────────────────────────────────────────┐")
    print(f"│  SIGNAL: {len(notifications)} INCOMING NOTIFICATION(S)              │")
    print("└─────────────────────────────────────────────────────┘")
    for n in notifications:
        from_role = n.get('from', n.get('source_role', '?'))
        msg = n.get('message', '')
        ts = str(n.get('ts', n.get('created_at', '')))[:16]
        ntype = n.get('ntype', '')
        notif_id = n.get('id', '')
        type_tag = f"[{ntype}] " if ntype else ""
        print(f"  [{ts}] {from_role} → {type_tag}{msg}")
        if notif_id:
            print(f"           Ref: {notif_id}")
    print("")
    print("  ↳ Action: check via vetka_task_board action=notifications")
    print("")
except json.JSONDecodeError:
    print(f"[check_notifications] Warning: malformed signal file for role {os.environ.get('ROLE','?')}")
except Exception as e:
    # Never block tool use on notification parse error
    pass
PYEOF

# Cleanup temp file
rm -f "$TEMP_FILE"

exit 0
