#!/bin/bash
# MARKER_204.7: Opencode agent signal checker — universal signal dir + PRETOOL_HOOK
#
# Usage (as Opencode PRETOOL_HOOK):
#   export PRETOOL_HOOK="bash scripts/check_opencode_signals.sh"
#   export VETKA_AGENT_ROLE=Lambda
#   opencode -m opencode/qwen3.6-plus-free
#
# Checks two signal locations (universal first, Claude fallback):
#   1. ~/.vetka/signals/{ROLE}.json   ← universal (Opencode, Vibe, external)
#   2. ~/.claude/signals/{ROLE}.json  ← Claude Code fallback
#
# Combines notifications from both locations, outputs to stdout, deletes both files.
# Same JSON format as check_notifications.sh — interoperable.
#
# Same performance contract as check_notifications.sh:
#   - Fast no-op (<1ms) when neither signal file exists
#   - ~30ms when signal present (python3 parse)

set -eo pipefail

ROLE="${VETKA_AGENT_ROLE:-${1:-}}"

# Fast exit: no role → no-op
[ -z "$ROLE" ] && exit 0

UNIVERSAL_DIR="$HOME/.vetka/signals"
CLAUDE_DIR="$HOME/.claude/signals"
UNIVERSAL_FILE="$UNIVERSAL_DIR/${ROLE}.json"
CLAUDE_FILE="$CLAUDE_DIR/${ROLE}.json"

# Fast exit: neither signal file exists
[ -f "$UNIVERSAL_FILE" ] || [ -f "$CLAUDE_FILE" ] || exit 0

# Collect all notifications from both locations (atomic move)
TEMP_UNIVERSAL="/tmp/vetka_sig_${ROLE}_$$_u"
TEMP_CLAUDE="/tmp/vetka_sig_${ROLE}_$$_c"

TEMPS=()
if [ -f "$UNIVERSAL_FILE" ] && [ -s "$UNIVERSAL_FILE" ]; then
    mv "$UNIVERSAL_FILE" "$TEMP_UNIVERSAL" 2>/dev/null && TEMPS+=("$TEMP_UNIVERSAL")
fi
if [ -f "$CLAUDE_FILE" ] && [ -s "$CLAUDE_FILE" ]; then
    mv "$CLAUDE_FILE" "$TEMP_CLAUDE" 2>/dev/null && TEMPS+=("$TEMP_CLAUDE")
fi
# Clean up empty signal files
rm -f "$UNIVERSAL_FILE" "$CLAUDE_FILE" 2>/dev/null || true

[ ${#TEMPS[@]} -eq 0 ] && exit 0

# Parse and output on stdout (Opencode PRETOOL_HOOK reads stdout as context)
python3 - "${TEMPS[@]}" <<'PYEOF'
import sys, json, os

all_notifications = []
temp_files = sys.argv[1:]

for path in temp_files:
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, list):
            all_notifications.extend(data)
    except Exception:
        pass

if not all_notifications:
    sys.exit(0)

print("")
print("┌─────────────────────────────────────────────────────┐")
print(f"│  SIGNAL: {len(all_notifications)} INCOMING NOTIFICATION(S)              │")
print("└─────────────────────────────────────────────────────┘")
for n in all_notifications:
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
PYEOF

# Cleanup temp files
for tmp in "${TEMPS[@]}"; do
    rm -f "$tmp"
done

exit 0
