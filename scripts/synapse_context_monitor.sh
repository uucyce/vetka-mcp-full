#!/bin/bash
# scripts/synapse_context_monitor.sh — Context exhaustion auto-restart daemon
# Phase 209.1 | MARKER_209.CONTEXT_MONITOR
#
# Monitors all active Synapse agent tmux sessions for context exhaustion signals.
# On detection: saves checkpoint → kills session → respawns with recovery prompt.
#
# Usage:
#   scripts/synapse_context_monitor.sh              # run once (cron-friendly)
#   scripts/synapse_context_monitor.sh --daemon      # loop every POLL_INTERVAL
#   scripts/synapse_context_monitor.sh --status      # show compacting state
#
# Env:
#   SYNAPSE_POLL_INTERVAL  — seconds between checks (default: 30)
#   SYNAPSE_CAPTURE_LINES  — tmux pane lines to capture (default: 50)
#   SYNAPSE_AUTO_RESTART   — if "true", auto-restart on detection (default: true)

set -euo pipefail

PROJECT_ROOT="$HOME/Documents/VETKA_Project/vetka_live_03"
REGISTRY_FILE="$PROJECT_ROOT/data/synapse_sessions.json"
CHECKPOINT_DIR="$PROJECT_ROOT/data/checkpoints"
POLL_INTERVAL="${SYNAPSE_POLL_INTERVAL:-30}"
CAPTURE_LINES="${SYNAPSE_CAPTURE_LINES:-50}"
AUTO_RESTART="${SYNAPSE_AUTO_RESTART:-true}"
LOG_PREFIX="[CTX-MON]"

mkdir -p "$CHECKPOINT_DIR"

# ── Context exhaustion detection patterns ──────────────────
# Claude Code emits these when context is compressed/exhausted
PATTERNS=(
    "conversation is getting long"
    "context window"
    "compacting conversation"
    "auto-compact"
    "messages were compressed"
    "message limit"
    "prior messages in your conversation"
    "context limits"
    "will automatically compress"
)

# Build grep -E pattern from array
GREP_PATTERN=$(printf '%s|' "${PATTERNS[@]}")
GREP_PATTERN="${GREP_PATTERN%|}"  # remove trailing |

# ── Helper: read synapse sessions ─────────────────────────
get_active_sessions() {
    if [ ! -f "$REGISTRY_FILE" ]; then
        echo "[]"
        return
    fi
    python3 -c "
import json, pathlib
p = pathlib.Path('$REGISTRY_FILE')
data = json.loads(p.read_text()) if p.exists() else {}
for role, info in data.items():
    agent_type = info.get('agent_type', 'claude_code')
    if agent_type == 'vibe':
        continue  # can't monitor browser agents via tmux
    session = info.get('tmux_session', f'vetka-{role}')
    worktree = info.get('worktree', '')
    compacting = info.get('compacting', False)
    print(f'{role}|{session}|{worktree}|{agent_type}|{compacting}')
" 2>/dev/null || true
}

# ── Helper: save checkpoint for agent ─────────────────────
save_checkpoint() {
    local role="$1"
    local worktree="$2"
    local reason="$3"
    local detected_line="$4"

    python3 << PYEOF
import json, pathlib, subprocess, datetime

role = "$role"
worktree = "$worktree"
reason = "$reason"
detected_line = """$detected_line"""

checkpoint = {
    "role": role,
    "worktree": worktree,
    "reason": reason,
    "detected_signal": detected_line.strip()[:200],
    "checkpoint_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
}

# Try to get current task from task board
try:
    import sys
    sys.path.insert(0, "$PROJECT_ROOT/src")
    from orchestration.task_board import TaskBoard
    tb = TaskBoard()
    # Find claimed task for this role
    tasks = tb.list_tasks(filter_status="claimed", limit=5)
    for t in tasks.get("tasks", []):
        if t.get("assigned_to", "").lower() == role.lower() or t.get("owner_agent", "").lower() == role.lower():
            checkpoint["task_id"] = t["id"]
            checkpoint["task_title"] = t.get("title", "")
            checkpoint["branch"] = t.get("branch_name", "")
            break
except Exception as e:
    checkpoint["task_lookup_error"] = str(e)

# Try to get modified files from git
try:
    wt_path = f"$PROJECT_ROOT/.claude/worktrees/{worktree}" if worktree else "$PROJECT_ROOT"
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=wt_path, capture_output=True, text=True, timeout=5
    )
    if result.returncode == 0 and result.stdout.strip():
        checkpoint["files_modified"] = result.stdout.strip().split("\n")
except Exception:
    pass

# Save
cp_path = pathlib.Path("$CHECKPOINT_DIR") / f"{role}_checkpoint.json"
cp_path.write_text(json.dumps(checkpoint, indent=2))
print(f"Checkpoint saved: {cp_path}")
PYEOF
}

# ── Helper: mark compacting in session registry ───────────
mark_compacting() {
    local role="$1"
    local state="$2"  # true or false
    python3 -c "
import json, pathlib
p = pathlib.Path('$REGISTRY_FILE')
if not p.exists(): exit()
data = json.loads(p.read_text())
if '$role' in data:
    data['$role']['compacting'] = $state
    data['$role']['compacting_at'] = __import__('time').time() if $state else None
    p.write_text(json.dumps(data, indent=2))
" 2>/dev/null || true
}

# ── Helper: restart agent ─────────────────────────────────
restart_agent() {
    local role="$1"
    local session_name="$2"
    local worktree="$3"
    local agent_type="$4"

    echo "$LOG_PREFIX Restarting $role..."

    # 1. Kill old session
    tmux kill-session -t "$session_name" 2>/dev/null || true
    sleep 2

    # 2. Build recovery init prompt
    local checkpoint_file="$CHECKPOINT_DIR/${role}_checkpoint.json"
    local init_prompt="vetka session init"

    if [ -f "$checkpoint_file" ]; then
        # Extract task_id from checkpoint for targeted recovery
        local task_id
        task_id=$(python3 -c "
import json
cp = json.load(open('$checkpoint_file'))
print(cp.get('task_id', ''))
" 2>/dev/null || echo "")

        if [ -n "$task_id" ]; then
            init_prompt="CONTEXT RESTART: I was restarted due to context exhaustion. My previous task was $task_id. Please run: vetka session init role=$role — then check data/checkpoints/${role}_checkpoint.json for my saved state and resume the task."
        fi
    fi

    # 3. Respawn via spawn_synapse.sh
    "$PROJECT_ROOT/scripts/spawn_synapse.sh" "$role" "$worktree" "$agent_type" "$init_prompt"

    # 4. Clear compacting flag
    mark_compacting "$role" "False"

    echo "$LOG_PREFIX $role restarted with recovery prompt"
}

# ── Main: check one cycle ─────────────────────────────────
check_all_agents() {
    local sessions
    sessions=$(get_active_sessions)

    if [ -z "$sessions" ]; then
        return
    fi

    while IFS='|' read -r role session_name worktree agent_type is_compacting; do
        [ -z "$role" ] && continue

        # Skip if already in compacting state (restart in progress)
        if [ "$is_compacting" = "True" ]; then
            echo "$LOG_PREFIX $role already in compacting state — skipping"
            continue
        fi

        # Check if tmux session exists
        if ! tmux has-session -t "$session_name" 2>/dev/null; then
            continue
        fi

        # Capture last N lines from tmux pane
        local pane_output
        pane_output=$(tmux capture-pane -t "$session_name" -p -S "-$CAPTURE_LINES" 2>/dev/null || echo "")

        if [ -z "$pane_output" ]; then
            continue
        fi

        # Check for context exhaustion patterns
        local detected_line
        detected_line=$(echo "$pane_output" | grep -iE "$GREP_PATTERN" | tail -1 || echo "")

        if [ -n "$detected_line" ]; then
            echo "$LOG_PREFIX DETECTED context exhaustion for $role: ${detected_line:0:100}"

            # Mark compacting to prevent double-trigger
            mark_compacting "$role" "True"

            # Save checkpoint
            save_checkpoint "$role" "$worktree" "context_exhaustion" "$detected_line"

            # Auto-restart if enabled
            if [ "$AUTO_RESTART" = "true" ]; then
                restart_agent "$role" "$session_name" "$worktree" "$agent_type"
            else
                echo "$LOG_PREFIX Auto-restart disabled — checkpoint saved at $CHECKPOINT_DIR/${role}_checkpoint.json"
            fi
        fi
    done <<< "$sessions"
}

# ── Status command ────────────────────────────────────────
show_status() {
    echo "$LOG_PREFIX Context Monitor Status"
    echo "──────────────────────────────────────────"

    local sessions
    sessions=$(get_active_sessions)

    if [ -z "$sessions" ]; then
        echo "No active sessions in $REGISTRY_FILE"
        return
    fi

    while IFS='|' read -r role session_name worktree agent_type is_compacting; do
        [ -z "$role" ] && continue
        local status="OK"
        local checkpoint_info=""

        if [ "$is_compacting" = "True" ]; then
            status="COMPACTING"
        fi

        if ! tmux has-session -t "$session_name" 2>/dev/null; then
            status="OFFLINE"
        fi

        if [ -f "$CHECKPOINT_DIR/${role}_checkpoint.json" ]; then
            checkpoint_info=" [checkpoint exists]"
        fi

        printf "  %-12s %-15s %-12s %s%s\n" "$role" "$session_name" "$status" "$agent_type" "$checkpoint_info"
    done <<< "$sessions"

    echo ""
    echo "Checkpoints: $(ls -1 "$CHECKPOINT_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ') files in $CHECKPOINT_DIR"
}

# ── Entry point ───────────────────────────────────────────
case "${1:-}" in
    --status)
        show_status
        ;;
    --daemon)
        echo "$LOG_PREFIX Starting daemon (poll every ${POLL_INTERVAL}s, capture ${CAPTURE_LINES} lines)"
        while true; do
            check_all_agents
            sleep "$POLL_INTERVAL"
        done
        ;;
    *)
        # Single run (cron-friendly)
        check_all_agents
        ;;
esac
