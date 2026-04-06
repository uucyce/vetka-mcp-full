#!/usr/bin/env bash
# install_post_merge_hook.sh — Deploy post-merge regression hooks to all worktrees.
#
# Installs .git/hooks/post-merge in the main repo AND all worktrees under
# .claude/worktrees/. The hook runs two detectors after every `git merge`:
#
#   1. detect_merge_regressions.py  — dropped lines + conflict markers (Delta)
#   2. detect_xpass_drift.py        — stale @pytest.mark.xfail markers (Epsilon)
#
# Usage:
#   bash scripts/install_post_merge_hook.sh [--repo-root PATH] [--dry-run]
#
# Options:
#   --repo-root PATH   Repo root (default: git rev-parse --show-toplevel)
#   --dry-run          Print what would be installed, don't write files

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------
REPO_ROOT=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo-root) REPO_ROOT="$2"; shift 2 ;;
        --dry-run)   DRY_RUN=true; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$REPO_ROOT" ]]; then
    REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
        echo "ERROR: not in a git repo and --repo-root not provided" >&2
        exit 1
    }
fi

SCRIPTS_DIR="$REPO_ROOT/scripts"

# ---------------------------------------------------------------------------
# Hook content
# ---------------------------------------------------------------------------
# Written as a here-doc so the installed hook is self-contained.
hook_content() {
    cat <<'HOOK'
#!/usr/bin/env bash
# post-merge hook — installed by scripts/install_post_merge_hook.sh
# Runs regression detectors after every `git merge`.
# Non-blocking: detector failures print warnings but do NOT abort the merge.

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
SCRIPTS="$REPO_ROOT/scripts"
PYTHON="${PYTHON:-python3}"

echo ""
echo "▶ post-merge: running regression detectors..."

# 1. Merge regression detector (Delta) — dropped lines + conflict markers
if [[ -f "$SCRIPTS/detect_merge_regressions.py" ]]; then
    if ! "$PYTHON" "$SCRIPTS/detect_merge_regressions.py" 2>&1; then
        echo "⚠ detect_merge_regressions: regressions found — check output above"
    fi
else
    echo "  [skip] detect_merge_regressions.py not found at $SCRIPTS/"
fi

# 2. Stale xfail detector (Epsilon) — XPASS markers
if [[ -f "$SCRIPTS/detect_xpass_drift.py" ]]; then
    if ! "$PYTHON" "$SCRIPTS/detect_xpass_drift.py" 2>&1; then
        echo "⚠ detect_xpass_drift: stale xfail markers found — check output above"
    fi
else
    echo "  [skip] detect_xpass_drift.py not found at $SCRIPTS/"
fi

echo "▶ post-merge: detectors done."
echo ""
HOOK
}

# ---------------------------------------------------------------------------
# Install to a single git dir
# ---------------------------------------------------------------------------
install_to() {
    local git_dir="$1"
    local label="$2"
    local hooks_dir="$git_dir/hooks"
    local hook_file="$hooks_dir/post-merge"

    if [[ "$DRY_RUN" == true ]]; then
        echo "  [dry-run] would write $hook_file"
        return
    fi

    mkdir -p "$hooks_dir"
    hook_content > "$hook_file"
    chmod +x "$hook_file"
    echo "  ✓ installed → $hook_file  ($label)"
}

# ---------------------------------------------------------------------------
# Find all git dirs to install into
# ---------------------------------------------------------------------------
echo "Installing post-merge hook..."
echo "  repo root: $REPO_ROOT"
echo ""

# Main repo
MAIN_GIT_DIR="$REPO_ROOT/.git"
if [[ -f "$MAIN_GIT_DIR" ]]; then
    # Worktree: .git is a file pointing to the real gitdir
    MAIN_GIT_DIR="$(cat "$MAIN_GIT_DIR" | sed 's/^gitdir: //')"
fi

if [[ -d "$MAIN_GIT_DIR" ]]; then
    install_to "$MAIN_GIT_DIR" "main repo"
else
    echo "  [warn] main .git dir not found at $MAIN_GIT_DIR"
fi

# All worktrees under .claude/worktrees/
WORKTREES_DIR="$REPO_ROOT/.claude/worktrees"
if [[ -d "$WORKTREES_DIR" ]]; then
    for wt_path in "$WORKTREES_DIR"/*/; do
        [[ -d "$wt_path" ]] || continue
        wt_name="$(basename "$wt_path")"

        # Worktree .git is a file: "gitdir: ../../.git/worktrees/<name>"
        wt_git_file="$wt_path/.git"
        if [[ -f "$wt_git_file" ]]; then
            wt_git_dir="$(cat "$wt_git_file" | sed 's/^gitdir: //')"
            # Resolve relative path
            if [[ "$wt_git_dir" != /* ]]; then
                wt_git_dir="$wt_path/$wt_git_dir"
            fi
            # Worktree gitdir has its own hooks/ subdir
            install_to "$wt_git_dir" "worktree/$wt_name"
        else
            echo "  [skip] $wt_name — no .git file at $wt_git_file"
        fi
    done
else
    echo "  [info] no worktrees dir at $WORKTREES_DIR"
fi

echo ""
if [[ "$DRY_RUN" == true ]]; then
    echo "Dry run complete — no files written."
else
    echo "Done. Hook fires after every \`git merge\` in all worktrees."
    echo "To test: git merge --no-ff <branch> (or run the hook directly)"
fi
