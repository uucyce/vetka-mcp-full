#!/bin/bash
# Install pre-commit hook for task board compliance check
#
# MARKER_210.TASK_BOARD_GUARDRAIL: Installation script
# Sets up the pre-commit hook in .git/hooks/pre-commit
#
# Usage: bash scripts/hooks/install-hooks.sh
#        or: bash scripts/hooks/install-hooks.sh --uninstall

set -e

PROJECT_ROOT="$(cd "$(dirname "$(dirname "$(dirname "$0")")")" && pwd)"
GIT_HOOK_DIR="$PROJECT_ROOT/.git/hooks"
PRE_COMMIT_HOOK="$GIT_HOOK_DIR/pre-commit"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================="
echo "Task Board Guardrail Hook Installation"
echo "=================="
echo ""

# Check if we're in a git repo
if [ ! -d "$GIT_HOOK_DIR" ]; then
    echo -e "${RED}❌ Error: Not in a git repository (no .git/hooks found)${NC}"
    exit 1
fi

# Handle uninstall
if [ "$1" = "--uninstall" ]; then
    echo "Uninstalling pre-commit hook..."
    if [ -f "$PRE_COMMIT_HOOK" ]; then
        rm -f "$PRE_COMMIT_HOOK"
        echo -e "${GREEN}✅ Hook removed${NC}"
    else
        echo -e "${YELLOW}⚠️  Hook not found${NC}"
    fi
    exit 0
fi

# Check if hook already exists
if [ -f "$PRE_COMMIT_HOOK" ]; then
    # Check if it already has our marker
    if grep -q "MARKER_210.TASK_BOARD_GUARDRAIL" "$PRE_COMMIT_HOOK"; then
        echo -e "${GREEN}✅ Hook already installed (MARKER_210 found)${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠️  Pre-commit hook exists but doesn't have MARKER_210${NC}"
        echo "   Backing up to pre-commit.backup..."
        cp "$PRE_COMMIT_HOOK" "${PRE_COMMIT_HOOK}.backup"
    fi
fi

# Create git hooks directory if it doesn't exist
mkdir -p "$GIT_HOOK_DIR"

# Check if our guard check script exists
GUARD_SCRIPT="$PROJECT_ROOT/scripts/check_task_board_compliance.py"
if [ ! -f "$GUARD_SCRIPT" ]; then
    echo -e "${RED}❌ Error: Guard script not found at $GUARD_SCRIPT${NC}"
    exit 1
fi

# Make sure the guard script is executable
chmod +x "$GUARD_SCRIPT"

echo "Installing pre-commit hook..."
echo "  Guard script: $GUARD_SCRIPT"
echo "  Hook location: $PRE_COMMIT_HOOK"
echo ""

# Check if the main hook already exists from .git/hooks (should be symlinked or copied from there)
if [ ! -f "$PRE_COMMIT_HOOK" ]; then
    echo -e "${RED}❌ Error: .git/hooks/pre-commit doesn't exist${NC}"
    echo "   The pre-commit hook should be in .git/hooks/pre-commit"
    exit 1
fi

# The hook should already have been updated by the earlier edit command
# Just verify that MARKER_210 is in the hook
if grep -q "MARKER_210.TASK_BOARD_GUARDRAIL" "$PRE_COMMIT_HOOK"; then
    chmod +x "$PRE_COMMIT_HOOK"
    echo -e "${GREEN}✅ Hook installed successfully${NC}"
    echo ""
    echo "The hook will now:"
    echo "  • Detect your role from branch name (claude/{role}-{domain})"
    echo "  • Check for claimed tasks"
    echo "  • Block commits without a claimed task"
    echo "  • Allow bypass with: git commit --no-verify"
    echo ""
    echo -e "${YELLOW}ℹ️  To test the hook:${NC}"
    echo "  1. Claim a task: vetka_task_board action=claim task_id=tb_XXXXX"
    echo "  2. Make a commit: git commit -m 'test'"
    echo ""
else
    echo -e "${RED}❌ Error: Hook installation failed (MARKER_210 not found)${NC}"
    exit 1
fi

exit 0
