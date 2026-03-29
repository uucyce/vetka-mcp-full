#!/usr/bin/env bash
# install_post_merge_hook.sh — Deploy post-merge and post-rewrite hooks to all worktrees.
#
# Installs two hooks in the main repo AND all worktrees under .claude/worktrees/:
#
#   .git/hooks/post-merge   — runs regression detectors after every `git merge`:
#     1. detect_merge_regressions.py  — dropped lines + conflict markers (Delta)
#     2. detect_xpass_drift.py        — stale @pytest.mark.xfail markers (Epsilon)
#
#   .git/hooks/post-rewrite — fires after `git rebase`, auto-restores docs/ files
#     that exist on main but were lost during rebase. Zero manual intervention needed.
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
# post-rewrite hook content (auto-restore docs/ after rebase)
# ---------------------------------------------------------------------------
post_rewrite_hook_content() {
    cat <<'HOOK'
#!/usr/bin/env bash
# post-rewrite hook — installed by scripts/install_post_merge_hook.sh
# Fires after `git rebase`. Auto-restores docs/ files that exist on main
# but are missing on the current branch after rebase.
# $1 = "rebase" | "amend"

set -uo pipefail

[[ "${1:-}" == "rebase" ]] || exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0

echo ""
echo "▶ post-rewrite: checking for docs/ files lost during rebase..."

RESTORED=()
while IFS= read -r f; do
    [[ -n "$f" ]] || continue
    if git checkout main -- "$f" 2>/dev/null; then
        RESTORED+=("$f")
        echo "  restored: $f"
    else
        echo "  [warn] failed to restore: $f"
    fi
done < <(git diff --diff-filter=D --name-only main -- docs/ 2>/dev/null)

if [[ ${#RESTORED[@]} -gt 0 ]]; then
    git add docs/
    git commit --no-verify \
        -m "fix: auto-restore ${#RESTORED[@]} docs/ file(s) after rebase [post-rewrite hook]" \
        2>/dev/null || echo "  [warn] commit failed (possibly nothing staged)"
    echo "  ✓ committed ${#RESTORED[@]} restored file(s)"
else
    echo "  nothing to restore."
fi

echo "▶ post-rewrite: done."
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

    mkdir -p "$hooks_dir"

    # post-merge hook
    local pm_file="$hooks_dir/post-merge"
    if [[ "$DRY_RUN" == true ]]; then
        echo "  [dry-run] would write $pm_file"
    else
        hook_content > "$pm_file"
        chmod +x "$pm_file"
        echo "  ✓ installed → $pm_file  ($label)"
    fi

    # post-rewrite hook (auto-restore docs after rebase)
    local pr_file="$hooks_dir/post-rewrite"
    if [[ "$DRY_RUN" == true ]]; then
        echo "  [dry-run] would write $pr_file"
    else
        post_rewrite_hook_content > "$pr_file"
        chmod +x "$pr_file"
        echo "  ✓ installed → $pr_file  ($label)"
    fi
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
    echo "Done. Hooks installed in all worktrees:"
    echo "  post-merge   — fires after \`git merge\`, runs regression detectors"
    echo "  post-rewrite — fires after \`git rebase\`, auto-restores docs/ from main"
fi
