#!/bin/bash
# MARKER_204.3: Install notification hooks in all Claude Code agent worktrees.
#
# Adds PreToolUse hook (check_notifications.sh) to .claude/settings.json
# for each Claude Code agent. Safe to run multiple times (idempotent).
#
# Usage:
#   bash scripts/install_notification_hooks.sh
#   bash scripts/install_notification_hooks.sh --dry-run
#
# Agents covered (8 core Claude Code agents):
#   Alpha (cut-engine), Beta (cut-media), Gamma (cut-ux),
#   Delta (cut-qa), Epsilon (cut-qa-2), Zeta (harness),
#   Eta (harness-eta), Commander (pedantic-bell)

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKTREES_DIR="$(cd "$REPO_ROOT/../" && pwd)"

DRY_RUN=false
[ "${1:-}" = "--dry-run" ] && DRY_RUN=true

# Agent → Worktree mapping (8 core Claude Code agents): "ROLE:worktree" pairs
AGENT_MAP=(
    "Alpha:cut-engine"
    "Beta:cut-media"
    "Gamma:cut-ux"
    "Delta:cut-qa"
    "Epsilon:cut-qa-2"
    "Zeta:harness"
    "Eta:harness-eta"
    "Commander:pedantic-bell"
)

echo "MARKER_204.3: Installing notification hooks"
echo "Worktrees dir: $WORKTREES_DIR"
echo "Dry run: $DRY_RUN"
echo ""

INSTALLED=0
SKIPPED=0
ERRORS=0

install_hook() {
    local role="$1"
    local worktree="$2"
    local settings_path="$WORKTREES_DIR/$worktree/.claude/settings.json"

    if [ ! -f "$settings_path" ]; then
        echo "  [SKIP] $role ($worktree): settings.json not found at $settings_path"
        SKIPPED=$((SKIPPED + 1))
        return
    fi

    # Check if hook already installed
    if python3 -c "
import json, sys
with open('$settings_path') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('PreToolUse', [])
for h in hooks:
    for inner in h.get('hooks', []):
        if 'check_notifications' in inner.get('command', ''):
            sys.exit(0)  # already installed
sys.exit(1)  # not found
" 2>/dev/null; then
        echo "  [SKIP] $role ($worktree): hook already installed"
        SKIPPED=$((SKIPPED + 1))
        return
    fi

    if $DRY_RUN; then
        echo "  [DRY]  $role ($worktree): would add PreToolUse hook"
        return
    fi

    # Add PreToolUse hook via Python (safe JSON merge)
    python3 - "$settings_path" "$role" <<'PYEOF'
import json, sys, os

settings_path = sys.argv[1]
role = sys.argv[2]

with open(settings_path) as f:
    settings = json.load(f)

hooks = settings.setdefault("hooks", {})
pre_hooks = hooks.setdefault("PreToolUse", [])

new_hook = {
    "matcher": "",
    "hooks": [
        {
            "type": "command",
            "command": f"bash scripts/check_notifications.sh {role} 2>/dev/null || true"
        }
    ]
}
pre_hooks.append(new_hook)

# Write back (pretty-print, 2-space indent to match existing style)
with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"OK")
PYEOF

    if [ $? -eq 0 ]; then
        echo "  [OK]   $role ($worktree): PreToolUse hook installed"
        INSTALLED=$((INSTALLED + 1))
    else
        echo "  [ERR]  $role ($worktree): failed to update settings.json"
        ERRORS=$((ERRORS + 1))
    fi
}

for entry in "${AGENT_MAP[@]}"; do
    role="${entry%%:*}"
    worktree="${entry##*:}"
    install_hook "$role" "$worktree"
done

echo ""
echo "Done: $INSTALLED installed, $SKIPPED skipped, $ERRORS errors"

# Ensure signal directory exists
mkdir -p "$HOME/.claude/signals"
echo "Signal dir: $HOME/.claude/signals/ (created if missing)"
