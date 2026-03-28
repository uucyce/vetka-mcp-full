#!/bin/bash
# MARKER_201.NOTIFY: Agent inbox check hook for Claude Code
#
# Usage: Add as post-tool hook in .claude/settings.json:
#   "hooks": {
#     "PostToolUse": [
#       { "matcher": ".*", "command": "bash scripts/check_agent_inbox.sh" }
#     ]
#   }
#
# Reads .inbox file in current worktree, displays notifications, clears file.
# Designed to run after every tool call — fast no-op when inbox is empty.

set -euo pipefail

# Resolve inbox path: current worktree/.inbox
INBOX="${PWD}/.inbox"

# Fast exit if no inbox or empty
[ -f "$INBOX" ] || exit 0
[ -s "$INBOX" ] || exit 0

# Read and clear atomically (move then read)
TEMP_INBOX="${INBOX}.$$"
mv "$INBOX" "$TEMP_INBOX" 2>/dev/null || exit 0

# Display each notification
echo ""
echo "━━━ INCOMING NOTIFICATIONS ━━━"
while IFS= read -r line; do
    # Parse JSON fields with lightweight extraction
    FROM=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('from','?'))" 2>/dev/null || echo "?")
    MSG=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message',''))" 2>/dev/null || echo "$line")
    AT=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('at',''))" 2>/dev/null || echo "")

    printf "  [%s] %s: %s\n" "$AT" "$FROM" "$MSG"
done < "$TEMP_INBOX"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Cleanup
rm -f "$TEMP_INBOX"

# Terminal bell for attention
printf '\a'
