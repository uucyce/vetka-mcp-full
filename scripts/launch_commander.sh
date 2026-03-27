#!/usr/bin/env bash
# MARKER_198.CMD: Launch Commander terminal in pedantic-bell worktree
#
# Usage:
#   ./scripts/launch_commander.sh              # normal mode (asks permission)
#   ./scripts/launch_commander.sh --auto       # skip-permissions mode
#
# Prerequisites:
#   - Claude Code CLI installed (`claude` in PATH)
#   - MCP server running (port 5001)
#   - Worktree pedantic-bell exists

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKTREE="$REPO_ROOT/.claude/worktrees/pedantic-bell"

# Verify worktree exists
if [ ! -d "$WORKTREE" ]; then
  echo "ERROR: Commander worktree not found at $WORKTREE"
  echo "Create it:  cd $REPO_ROOT && git worktree add .claude/worktrees/pedantic-bell claude/pedantic-bell"
  exit 1
fi

# Regenerate CLAUDE.md to ensure fresh identity
echo "Regenerating Commander CLAUDE.md..."
cd "$REPO_ROOT"
python3 -m src.tools.generate_claude_md --role Commander 2>/dev/null || true

# Build startup prompt
STARTUP_PROMPT="vetka session init"

# Launch mode
if [ "${1:-}" = "--auto" ]; then
  echo "Launching Commander (auto-permissions)..."
  exec claude --dangerously-skip-permissions \
    --project-dir "$WORKTREE" \
    -p "$STARTUP_PROMPT"
else
  echo "Launching Commander..."
  exec claude \
    --project-dir "$WORKTREE" \
    -p "$STARTUP_PROMPT"
fi
