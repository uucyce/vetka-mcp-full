#!/bin/bash
# scripts/test_context_restart.sh — Integration test for HARNESS-209.1 context restart
# MARKER_209.TEST
#
# Tests the full cycle:
#   1. Checkpoint save (via task_board Python API)
#   2. Checkpoint load + consume
#   3. Context monitor detection (pattern matching)
#   4. synapse_write.sh validation
#   5. synapse_wake.sh validation
#   6. Template update verification

set -euo pipefail

PROJECT_ROOT="$HOME/Documents/VETKA_Project/vetka_live_03"
# Support running from worktree — use worktree src for imports
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$SCRIPT_DIR" == *"worktrees"* ]]; then
    WORKTREE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    WORKTREE_ROOT="$PROJECT_ROOT"
fi
# Python imports from worktree src (where edits live), data from main repo
PY_SRC="$WORKTREE_ROOT/src"

# Checkpoints go to worktree data/ (task_board resolves __file__-relative)
CHECKPOINT_DIR="$WORKTREE_ROOT/data/checkpoints"
PASS=0
FAIL=0
LOG_PREFIX="[TEST-209.1]"

pass() { PASS=$((PASS+1)); echo "$LOG_PREFIX PASS: $1"; }
fail() { FAIL=$((FAIL+1)); echo "$LOG_PREFIX FAIL: $1"; }

# ── Clean test state ──────────────────────────────────────
rm -f "$CHECKPOINT_DIR/TestAgent_checkpoint.json"
rm -f "$CHECKPOINT_DIR/TestAgent_checkpoint.consumed.json"
mkdir -p "$CHECKPOINT_DIR"

echo "$LOG_PREFIX Starting HARNESS-209.1 context restart tests"
echo "============================================================"

# ── Test 1: Checkpoint save via Python API ────────────────
echo ""
echo "$LOG_PREFIX Test 1: Checkpoint save via TaskBoard API"
python3 -c "
import sys
sys.path.insert(0, '$PY_SRC')
from orchestration.task_board import TaskBoard
tb = TaskBoard()
result = tb.save_context_checkpoint('TestAgent', reason='test', extra={'test_key': 'test_value'})
assert result['success'], f'save failed: {result}'
assert 'TestAgent_checkpoint.json' in result['checkpoint_path']
assert result['checkpoint']['role'] == 'TestAgent'
assert result['checkpoint']['test_key'] == 'test_value'
print('OK')
" 2>&1 && pass "Checkpoint save" || fail "Checkpoint save"

# ── Test 2: Checkpoint file exists ────────────────────────
echo ""
echo "$LOG_PREFIX Test 2: Checkpoint file on disk"
if [ -f "$CHECKPOINT_DIR/TestAgent_checkpoint.json" ]; then
    pass "Checkpoint file exists"
else
    fail "Checkpoint file not found"
fi

# ── Test 3: Checkpoint load ──────────────────────────────
echo ""
echo "$LOG_PREFIX Test 3: Checkpoint load (no consume)"
python3 -c "
import sys
sys.path.insert(0, '$PY_SRC')
from orchestration.task_board import TaskBoard
tb = TaskBoard()
result = tb.load_context_checkpoint('TestAgent', consume=False)
assert result['has_checkpoint'], f'load failed: {result}'
assert result['checkpoint']['role'] == 'TestAgent'
assert result['checkpoint']['reason'] == 'test'
print('OK')
" 2>&1 && pass "Checkpoint load (no consume)" || fail "Checkpoint load (no consume)"

# ── Test 4: Checkpoint load with consume ──────────────────
echo ""
echo "$LOG_PREFIX Test 4: Checkpoint load + consume"
python3 -c "
import sys
sys.path.insert(0, '$PY_SRC')
from orchestration.task_board import TaskBoard
tb = TaskBoard()
result = tb.load_context_checkpoint('TestAgent', consume=True)
assert result['has_checkpoint'], f'load failed: {result}'
assert result.get('consumed'), 'not consumed'
print('OK')
" 2>&1 && pass "Checkpoint consume" || fail "Checkpoint consume"

# ── Test 5: Consumed checkpoint no longer loadable ────────
echo ""
echo "$LOG_PREFIX Test 5: Consumed checkpoint returns has_checkpoint=False"
python3 -c "
import sys
sys.path.insert(0, '$PY_SRC')
from orchestration.task_board import TaskBoard
tb = TaskBoard()
result = tb.load_context_checkpoint('TestAgent', consume=False)
assert not result['has_checkpoint'], f'checkpoint should be consumed: {result}'
print('OK')
" 2>&1 && pass "Consumed checkpoint not loadable" || fail "Consumed checkpoint not loadable"

# ── Test 6: Consumed file exists ──────────────────────────
echo ""
echo "$LOG_PREFIX Test 6: Consumed file exists on disk"
if [ -f "$CHECKPOINT_DIR/TestAgent_checkpoint.consumed.json" ]; then
    pass "Consumed checkpoint file exists"
else
    fail "Consumed checkpoint file not found"
fi

# ── Test 7: list_checkpoints ─────────────────────────────
echo ""
echo "$LOG_PREFIX Test 7: list_checkpoints returns empty after consume"
python3 -c "
import sys
sys.path.insert(0, '$PY_SRC')
from orchestration.task_board import TaskBoard
tb = TaskBoard()
# Create a fresh one for listing
tb.save_context_checkpoint('ListTest', reason='test_list')
result = tb.list_checkpoints()
assert len(result['checkpoints']) >= 1, f'expected at least 1 checkpoint: {result}'
found = any(cp['role'] == 'ListTest' for cp in result['checkpoints'])
assert found, 'ListTest checkpoint not found in list'
print('OK')
" 2>&1 && pass "list_checkpoints" || fail "list_checkpoints"

# ── Test 8: Context monitor pattern matching ──────────────
echo ""
echo "$LOG_PREFIX Test 8: Context exhaustion pattern detection"
# Test the grep patterns used by the monitor
PATTERNS="conversation is getting long|context window|compacting conversation|auto-compact|messages were compressed|message limit|prior messages in your conversation|context limits|will automatically compress"

TEST_LINES=(
    "The system will automatically compress prior messages in your conversation"
    "Your context window is getting large"
    "compacting conversation to save tokens"
    "Normal output line with no signal"
    "Building project..."
)

DETECTED=0
NOT_DETECTED=0
for line in "${TEST_LINES[@]}"; do
    if echo "$line" | grep -qiE "$PATTERNS"; then
        DETECTED=$((DETECTED+1))
    else
        NOT_DETECTED=$((NOT_DETECTED+1))
    fi
done

if [ "$DETECTED" -eq 3 ] && [ "$NOT_DETECTED" -eq 2 ]; then
    pass "Pattern matching (3 detected, 2 clean)"
else
    fail "Pattern matching (expected 3/2, got $DETECTED/$NOT_DETECTED)"
fi

# ── Test 9: Scripts exist and are executable ──────────────
echo ""
echo "$LOG_PREFIX Test 9: Scripts executable"
ALL_EXEC=true
for script in synapse_context_monitor.sh synapse_write.sh synapse_wake.sh; do
    if [ -x "$WORKTREE_ROOT/scripts/$script" ]; then
        echo "  $script: executable"
    else
        echo "  $script: NOT executable"
        ALL_EXEC=false
    fi
done
if $ALL_EXEC; then
    pass "All scripts executable"
else
    fail "Some scripts not executable"
fi

# ── Test 10: synapse_write.sh fails gracefully on missing session ─
echo ""
echo "$LOG_PREFIX Test 10: synapse_write.sh error on missing session"
WRITE_OUT=$("$WORKTREE_ROOT/scripts/synapse_write.sh" "NonExistentAgent" "test" 2>&1 || true)
if echo "$WRITE_OUT" | grep -q "not running"; then
    pass "synapse_write.sh graceful error"
else
    fail "synapse_write.sh didn't show proper error: $WRITE_OUT"
fi

# ── Test 11: synapse_wake.sh fails gracefully on missing session ─
echo ""
echo "$LOG_PREFIX Test 11: synapse_wake.sh error on missing session"
WAKE_OUT=$("$WORKTREE_ROOT/scripts/synapse_wake.sh" "NonExistentAgent" 2>&1 || true)
if echo "$WAKE_OUT" | grep -q "not running"; then
    pass "synapse_wake.sh graceful error"
else
    fail "synapse_wake.sh didn't show proper error: $WAKE_OUT"
fi

# ── Test 12: Template includes context restart section ────
echo ""
echo "$LOG_PREFIX Test 12: CLAUDE.md template has context restart section"
if grep -q "Context Restart Recovery" "$WORKTREE_ROOT/data/templates/claude_md_template.j2"; then
    pass "Template has context restart section"
else
    fail "Template missing context restart section"
fi

# ── Test 13: Context monitor --status runs without error ──
echo ""
echo "$LOG_PREFIX Test 13: Context monitor --status"
if "$WORKTREE_ROOT/scripts/synapse_context_monitor.sh" --status 2>&1; then
    pass "Context monitor --status"
else
    fail "Context monitor --status failed"
fi

# ── Cleanup ──────────────────────────────────────────────
rm -f "$CHECKPOINT_DIR/TestAgent_checkpoint.consumed.json"
rm -f "$CHECKPOINT_DIR/ListTest_checkpoint.json"

# ── Summary ──────────────────────────────────────────────
echo ""
echo "============================================================"
echo "$LOG_PREFIX Results: $PASS passed, $FAIL failed (total: $((PASS+FAIL)))"
echo "============================================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
