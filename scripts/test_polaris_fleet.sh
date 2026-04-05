#!/bin/bash
# scripts/test_polaris_fleet.sh — Integration test for HARNESS-209.2 Polaris fleet
# MARKER_209.TEST_POLARIS
#
# Tests:
#   1. All 6 Polaris roles exist in agent_registry.yaml
#   2. Model IDs are set correctly (Qwen for opencode, Mistral for vibe)
#   3. Fleet tag is "polaris" for all 6
#   4. spawn_synapse.sh builds correct commands per agent_type
#   5. Task routing accepts opencode/vibe agent_types
#   6. Registry YAML parses without error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKTREE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PY_SRC="$WORKTREE_ROOT/src"
REGISTRY="$WORKTREE_ROOT/data/templates/agent_registry.yaml"

PASS=0
FAIL=0
LOG_PREFIX="[TEST-209.2]"

pass() { PASS=$((PASS+1)); echo "$LOG_PREFIX PASS: $1"; }
fail() { FAIL=$((FAIL+1)); echo "$LOG_PREFIX FAIL: $1"; }

echo "$LOG_PREFIX Starting HARNESS-209.2 Polaris fleet tests"
echo "============================================================"

# ── Test 1: Registry YAML parses cleanly ──────────────────
echo ""
echo "$LOG_PREFIX Test 1: Registry YAML parses without error"
python3 -c "
import yaml
data = yaml.safe_load(open('$REGISTRY'))
assert 'roles' in data, 'no roles key'
assert len(data['roles']) >= 14, f'expected >= 14 roles, got {len(data[\"roles\"])}'
print(f'OK — {len(data[\"roles\"])} roles found')
" 2>&1 && pass "YAML parse" || fail "YAML parse"

# ��─ Test 2: All 6 Polaris callsigns exist ─────────────────
echo ""
echo "$LOG_PREFIX Test 2: All 6 Polaris callsigns present"
python3 -c "
import yaml
data = yaml.safe_load(open('$REGISTRY'))
callsigns = {r['callsign'] for r in data['roles']}
polaris = {'Theta', 'Iota', 'Kappa', 'Lambda', 'Mu', 'Nu'}
missing = polaris - callsigns
assert not missing, f'missing Polaris agents: {missing}'
print(f'OK — all 6 present: {sorted(polaris)}')
" 2>&1 && pass "All 6 Polaris callsigns" || fail "All 6 Polaris callsigns"

# ── Test 3: Tool types correct (3 opencode + 3 vibe) ─────
echo ""
echo "$LOG_PREFIX Test 3: Tool types correct"
python3 -c "
import yaml
data = yaml.safe_load(open('$REGISTRY'))
polaris = {r['callsign']: r for r in data['roles'] if r.get('fleet') == 'polaris'}
opencode_agents = [c for c, r in polaris.items() if r['tool_type'] == 'opencode']
vibe_agents = [c for c, r in polaris.items() if r['tool_type'] == 'vibe']
assert len(opencode_agents) == 3, f'expected 3 opencode, got {opencode_agents}'
assert len(vibe_agents) == 3, f'expected 3 vibe, got {vibe_agents}'
print(f'OK — opencode: {sorted(opencode_agents)}, vibe: {sorted(vibe_agents)}')
" 2>&1 && pass "Tool types (3 opencode + 3 vibe)" || fail "Tool types"

# ── Test 4: Model IDs set correctly ───────────────────────
echo ""
echo "$LOG_PREFIX Test 4: Model IDs present and correct"
python3 -c "
import yaml
data = yaml.safe_load(open('$REGISTRY'))
polaris = {r['callsign']: r for r in data['roles'] if r.get('fleet') == 'polaris'}
for callsign, role in polaris.items():
    mid = role.get('model_id', '')
    tt = role['tool_type']
    if tt == 'opencode':
        assert 'qwen' in mid.lower(), f'{callsign}: opencode should have qwen model_id, got {mid}'
    elif tt == 'vibe':
        assert 'mistral' in mid.lower(), f'{callsign}: vibe should have mistral model_id, got {mid}'
print('OK — all model_ids match tool_type')
" 2>&1 && pass "Model IDs correct" || fail "Model IDs"

# ── Test 5: Fleet tag is 'polaris' for all 6 ─────────────
echo ""
echo "$LOG_PREFIX Test 5: Fleet tag = 'polaris'"
python3 -c "
import yaml
data = yaml.safe_load(open('$REGISTRY'))
polaris_names = {'Theta', 'Iota', 'Kappa', 'Lambda', 'Mu', 'Nu'}
for r in data['roles']:
    if r['callsign'] in polaris_names:
        assert r.get('fleet') == 'polaris', f'{r[\"callsign\"]}: fleet={r.get(\"fleet\")}, expected polaris'
print('OK — all 6 have fleet=polaris')
" 2>&1 && pass "Fleet tag" || fail "Fleet tag"

# ── Test 6: model_tier = 'free' for all Polaris ──────────
echo ""
echo "$LOG_PREFIX Test 6: Model tier = 'free'"
python3 -c "
import yaml
data = yaml.safe_load(open('$REGISTRY'))
polaris = [r for r in data['roles'] if r.get('fleet') == 'polaris']
for r in polaris:
    assert r.get('model_tier') == 'free', f'{r[\"callsign\"]}: model_tier={r.get(\"model_tier\")}'
print('OK — all free tier')
" 2>&1 && pass "Model tier free" || fail "Model tier"

# ── Test 7: Domains distributed correctly ─────────────────
echo ""
echo "$LOG_PREFIX Test 7: Domain distribution"
python3 -c "
import yaml
data = yaml.safe_load(open('$REGISTRY'))
polaris = {r['callsign']: r['domain'] for r in data['roles'] if r.get('fleet') == 'polaris'}
domains = list(polaris.values())
assert 'engine' in domains, 'missing engine domain'
assert 'media' in domains, 'missing media domain'
assert 'ux' in domains, 'missing ux domain'
assert 'harness' in domains, 'missing harness domain'
assert 'qa' in domains, 'missing qa domain'
print(f'OK — domains: {polaris}')
" 2>&1 && pass "Domain distribution" || fail "Domain distribution"

# ── Test 8: spawn_synapse.sh has model routing ────────────
echo ""
echo "$LOG_PREFIX Test 8: spawn_synapse.sh has model routing"
if grep -q "MARKER_209.POLARIS" "$WORKTREE_ROOT/scripts/spawn_synapse.sh" && \
   grep -q "MODEL_ID" "$WORKTREE_ROOT/scripts/spawn_synapse.sh" && \
   grep -q "model_id" "$WORKTREE_ROOT/scripts/spawn_synapse.sh"; then
    pass "spawn_synapse.sh model routing"
else
    fail "spawn_synapse.sh missing model routing"
fi

# ── Test 9: opencode spawn includes -m model flag ────────
echo ""
echo "$LOG_PREFIX Test 9: opencode spawn uses -m flag"
if grep -q "opencode -m" "$WORKTREE_ROOT/scripts/spawn_synapse.sh"; then
    pass "opencode -m flag"
else
    fail "opencode -m flag missing"
fi

# ── Test 10: No duplicate callsigns in registry ───���──────
echo ""
echo "$LOG_PREFIX Test 10: No duplicate callsigns"
python3 -c "
import yaml
data = yaml.safe_load(open('$REGISTRY'))
callsigns = [r['callsign'] for r in data['roles']]
dupes = [c for c in callsigns if callsigns.count(c) > 1]
assert not dupes, f'duplicate callsigns: {set(dupes)}'
print(f'OK — {len(callsigns)} unique callsigns')
" 2>&1 && pass "No duplicate callsigns" || fail "Duplicate callsigns"

# ── Test 11: AgentRegistry loads Polaris roles ────────────
echo ""
echo "$LOG_PREFIX Test 11: AgentRegistry Python loader"
python3 -c "
import sys; sys.path.insert(0, '$PY_SRC')
from services.agent_registry import AgentRegistry
reg = AgentRegistry()
theta = reg.get_by_callsign('Theta')
assert theta is not None, 'Theta not found in registry'
assert theta.tool_type == 'opencode', f'Theta tool_type={theta.tool_type}'
assert theta.domain == 'engine', f'Theta domain={theta.domain}'
print(f'OK — Theta loaded: tool_type={theta.tool_type}, domain={theta.domain}')
" 2>&1 && pass "AgentRegistry loads Polaris" || fail "AgentRegistry load"

# ── Test 12: Task board accepts opencode agent_type ────���──
echo ""
echo "$LOG_PREFIX Test 12: TaskBoard accepts opencode/vibe"
python3 -c "
import sys; sys.path.insert(0, '$PY_SRC')
from orchestration.task_board import TaskBoard
manual_types = TaskBoard._MANUAL_AGENT_TYPES
assert 'opencode' in manual_types, f'opencode not in manual types: {manual_types}'
print(f'OK — opencode in TaskBoard._MANUAL_AGENT_TYPES')
" 2>&1 && pass "TaskBoard opencode routing" || fail "TaskBoard routing"

# ── Test 13: Worktree names unique ────────────────────────
echo ""
echo "$LOG_PREFIX Test 13: Worktree names unique"
python3 -c "
import yaml
data = yaml.safe_load(open('$REGISTRY'))
worktrees = [r['worktree'] for r in data['roles']]
dupes = [w for w in worktrees if worktrees.count(w) > 1]
assert not dupes, f'duplicate worktrees: {set(dupes)}'
print(f'OK — {len(worktrees)} unique worktrees')
" 2>&1 && pass "Unique worktrees" || fail "Duplicate worktrees"

# ── Test 14: Branch names unique ──────────────────────────
echo ""
echo "$LOG_PREFIX Test 14: Branch names unique"
python3 -c "
import yaml
data = yaml.safe_load(open('$REGISTRY'))
branches = [r['branch'] for r in data['roles']]
dupes = [b for b in branches if branches.count(b) > 1]
assert not dupes, f'duplicate branches: {set(dupes)}'
print(f'OK — {len(branches)} unique branches')
" 2>&1 && pass "Unique branches" || fail "Duplicate branches"

# ── Summary ──��───────────────────────────────────────────
echo ""
echo "============================================================"
echo "$LOG_PREFIX Results: $PASS passed, $FAIL failed (total: $((PASS+FAIL)))"
echo "============================================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
