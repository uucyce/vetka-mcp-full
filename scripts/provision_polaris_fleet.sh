#!/bin/bash
# scripts/provision_polaris_fleet.sh — Create worktrees for all 6 Polaris agents
# Phase 209.3 | MARKER_209.PROVISION_POLARIS
#
# Creates git branches + worktrees + CLAUDE.md for:
#   Theta (opencode/engine), Iota (opencode/media), Kappa (opencode/harness)
#   Lambda (vibe/ux), Mu (vibe/ux), Nu (vibe/qa)
#
# Usage: scripts/provision_polaris_fleet.sh [--dry-run]

set -euo pipefail

PROJECT_ROOT="$HOME/Documents/VETKA_Project/vetka_live_03"
WORKTREES_DIR="$PROJECT_ROOT/.claude/worktrees"
LOG_PREFIX="[POLARIS-PROVISION]"
DRY_RUN="${1:-}"

# ── Polaris fleet definition (parallel arrays) ────────────
ROLES=(    Theta             Iota              Kappa              Lambda            Mu               Nu)
WT_NAMES=( polaris-theta     polaris-iota      polaris-kappa      polaris-lambda    polaris-mu       polaris-nu)
BRANCHES=( claude/polaris-theta claude/polaris-iota claude/polaris-kappa claude/polaris-lambda claude/polaris-mu claude/polaris-nu)

CREATED=0
SKIPPED=0
FAILED=0

echo "$LOG_PREFIX Provisioning 6 Polaris fleet worktrees"
echo "============================================================"

if [ "$DRY_RUN" = "--dry-run" ]; then
    echo "$LOG_PREFIX DRY RUN — no changes will be made"
    echo ""
fi

cd "$PROJECT_ROOT"

for i in "${!ROLES[@]}"; do
    ROLE="${ROLES[$i]}"
    WT_NAME="${WT_NAMES[$i]}"
    BRANCH="${BRANCHES[$i]}"
    WT_PATH="$WORKTREES_DIR/$WT_NAME"

    echo ""
    echo "$LOG_PREFIX [$ROLE] branch=$BRANCH worktree=$WT_NAME"

    # ── Skip if worktree already exists ────────────────────
    if [ -d "$WT_PATH" ]; then
        echo "$LOG_PREFIX [$ROLE] SKIP — worktree already exists at $WT_PATH"
        SKIPPED=$((SKIPPED+1))
        continue
    fi

    if [ "$DRY_RUN" = "--dry-run" ]; then
        echo "$LOG_PREFIX [$ROLE] WOULD create branch $BRANCH + worktree $WT_NAME"
        CREATED=$((CREATED+1))
        continue
    fi

    # ── Create branch if needed ────────────────────────────
    if git show-ref --verify --quiet "refs/heads/$BRANCH" 2>/dev/null; then
        echo "$LOG_PREFIX [$ROLE] Branch $BRANCH already exists"
    else
        git branch "$BRANCH" main
        echo "$LOG_PREFIX [$ROLE] Created branch $BRANCH from main"
    fi

    # ── Create worktree ────────────────────────────────────
    git worktree add "$WT_PATH" "$BRANCH" 2>&1 || {
        echo "$LOG_PREFIX [$ROLE] FAILED to create worktree"
        FAILED=$((FAILED+1))
        continue
    }
    echo "$LOG_PREFIX [$ROLE] Created worktree at $WT_PATH"

    # ── Generate CLAUDE.md via template ────────────────────
    # Use generate_claude_md.py from main repo (not worktree — it resolves paths from __file__)
    if [ -f "$PROJECT_ROOT/src/tools/generate_claude_md.py" ]; then
        python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/src')
try:
    from tools.generate_claude_md import generate_for_role
    generate_for_role('$ROLE')
    print('CLAUDE.md generated for $ROLE')
except ImportError:
    # Fallback: try generate_all which handles all roles
    from tools.generate_claude_md import generate_all
    generate_all()
    print('CLAUDE.md generated (all roles)')
except Exception as e:
    print(f'CLAUDE.md generation error: {e}')
" 2>&1 || echo "$LOG_PREFIX [$ROLE] CLAUDE.md generation failed (non-fatal — will use root CLAUDE.md)"
    fi

    # ── Create .claude dir structure in worktree ───────────
    mkdir -p "$WT_PATH/.claude"

    CREATED=$((CREATED+1))
    echo "$LOG_PREFIX [$ROLE] DONE"
done

echo ""
echo "============================================================"
echo "$LOG_PREFIX Results: $CREATED created, $SKIPPED skipped, $FAILED failed"
echo "============================================================"

# ── Verification ──────────────────────────────────────────
echo ""
echo "$LOG_PREFIX Verification:"
for i in "${!ROLES[@]}"; do
    ROLE="${ROLES[$i]}"
    WT_NAME="${WT_NAMES[$i]}"
    WT_PATH="$WORKTREES_DIR/$WT_NAME"
    if [ -d "$WT_PATH" ]; then
        CLAUDE_MD="N"
        [ -f "$WT_PATH/CLAUDE.md" ] && CLAUDE_MD="Y"
        BRANCH_OK="N"
        git show-ref --verify --quiet "refs/heads/${BRANCHES[$i]}" 2>/dev/null && BRANCH_OK="Y"
        printf "  %-8s %-20s branch=%s CLAUDE.md=%s\n" "$ROLE" "$WT_NAME" "$BRANCH_OK" "$CLAUDE_MD"
    else
        printf "  %-8s %-20s MISSING\n" "$ROLE" "$WT_NAME"
    fi
done

if [ "$FAILED" -gt 0 ]; then
    exit 1
fi
exit 0
