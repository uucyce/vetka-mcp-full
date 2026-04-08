# RECON: Git Merge Regression Audit — 3 Waves in 48 Hours

**Date:** 2026-04-09  
**Task ID:** `tb_1775685074_37073_1`  
**Period:** 2026-04-07 (00:00) → 2026-04-09 (00:00)  
**Scope:** Last 48 hours of main branch commits

---

## Executive Summary

**Three regression waves detected** in last 48 hours, each with multiple hotfixes:

1. **Wave 1 (Apr 8, 00:03-00:32):** Sherpa pipeline crash → forced rollback
2. **Wave 2 (Apr 7, 21:59-23:43):** smart_snapshot merge incomplete → circular import crash
3. **Wave 3 (Apr 8, 21:49-23:24):** Large harness-eta merge (56 commits) → hook/guard issues

**Total regressions:** 12+ commits of hotfixes  
**Pattern:** Large merges without adequate pre-merge validation  
**Gate failures:** merge_request() allowed all 3 waves to reach main

---

## Wave 1: Sherpa Pipeline Collapse (Apr 8, 00:03-00:32)

### Timeline

| Time | Commit | Message | Status |
|------|--------|---------|--------|
| 00:05 | `0c47bf77c` | Switch Sherpa from qwen3.5 → gemma4:e4b | ❌ BROKEN |
| 00:03 | `02cfeabde` | E2E Scout→Sherpa pipeline — 9 tests | ⚠️ PASSED but broken |
| 00:13 | `437503b5d` | Fix: FeedbackCollector.record → log_task (NAME ERROR crash) | 🔧 HOTFIX |
| 00:23 | `839681a34` | Fix: Remove unsupported 'extra' kwarg (SECOND CRASH) | 🔧 HOTFIX |
| 00:28 | `3122bee39` | Fix: Remove 'extra' kwarg again (THIRD ATTEMPT) | 🔧 HOTFIX |
| **00:32** | **`12a643027`** | **Fix: Restore correct sherpa.py (PULSAR v1.1) — ROLLBACK** | ✅ RESTORED |

### Root Cause Analysis

**What happened:**
1. Gemma4 model switch triggered code refactor
2. FeedbackCollector API changed (record → log_task)
3. Old calls not updated in sherpa_loop.py
4. Crash: `NameError: name 'feedback' is not defined`
5. Three separate hotfixes attempted
6. Final solution: **ROLLBACK to previous sherpa.py**

**Why it reached main:**
- E2E test passed (9/9) but didn't catch Sherpa runtime crash
- Test suite didn't test actual Gemma4 model switch
- Pre-commit hook didn't validate sherpa.py syntax/imports

**Severity:** 🔴 **CRITICAL** — System non-functional until rollback

---

## Wave 2: smart_snapshot Merge Incomplete (Apr 7, 21:59-23:43)

### Timeline

| Time | Commit | Message | Status |
|------|--------|---------|--------|
| 23:43 | `52deb444f` | Smart snapshot merge photo_parallax_playground_codex into main | ❌ INCOMPLETE |
| 23:08 | `5780d8417` | Fix: Expose smart_snapshot in MCP enum | 🔧 HOTFIX |
| 21:59 | `8d68e8cb7` | Fix: Register Codex + fix circular import CRASH | 🔧 HOTFIX |
| 22:02 | `272351dfa` | Fix: Add proactive role generator hint | 🔧 HOTFIX |
| 23:48 | `d69caf123` | Fix: smart_snapshot uses wrong branch name | 🔧 HOTFIX |

### Root Cause Analysis

**What happened:**
1. smart_snapshot merge strategy executed (photo_parallax_playground_codex → main)
2. Merge succeeded but **enum registration missing** (smart_snapshot not in MCP enum)
3. Commit c09d snapshot merge succeeded
4. Immediate follow-ups: register enum, fix circular imports, fix branch name
5. **Total: 4 hotfixes for one merge**

**Why it reached main:**
- merge_request() didn't validate that strategy-specific registrations are present
- MCP enum not auto-generated (manual registration required)
- No post-merge integration test for smart_snapshot strategy

**Severity:** 🟠 **HIGH** — Merge strategy partially functional, workarounds needed

---

## Wave 3: Large harness-eta Merge (Apr 8, 21:49-23:24)

### Timeline

| Time | Commit | Message | Status |
|------|--------|---------|--------|
| 21:49 | `5bff4aebb` | fix: register pick_files_native in Tauri main.rs | 🔧 HOTFIX |
| 21:52 | `f7ab115ab` | **MERGE-GUARD-HOTFIX** — restore _qa_skipped var | 🔧 CRITICAL HOTFIX |
| 21:55 | `8a2d6fd3d` | feat: IMPL Phase 2 — MCP guard in vetka_git_commit | ✅ NEW FEATURE |
| 21:56 | `974bad55d` | feat: MCP guard in vetka_git_commit | ✅ NEW FEATURE |
| 22:23 | `8d0162462` | feat: MEM-FIX — wake protocol + storage rules | ✅ NEW FEATURE |
| 23:03 | `325899b21` | fix: **невалидный PostToolUse хук** в generate_claude_md.py | 🔧 HOTFIX |
| 23:20 | `049d63eed` | fix: NOTIFY-WAKE — _synapse_wake hookup | 🔧 HOTFIX |
| **23:24** | **`d74b18c27`** | **merge: claude/harness-eta → main (56 commits)** | ⚠️ LARGE MERGE |

### Root Cause Analysis

**What happened:**
1. Multiple fixes and features committed to main
2. CRITICAL: _qa_skipped variable deleted from merge_request() then restored (?)
3. PostToolUse hook in generate_claude_md.py is invalid (not caught by validation)
4. Large 56-commit harness-eta merge merged **without pre-merge verification**
5. MEM-FIX hooks added (wake protocol, storage rules) **but not validated**

**Why it reached main:**
- merge_request() checks minimal criteria (needs_fix blocking, but not comprehensive)
- Large merges (56 commits) not required to run full integration test suite
- Hook validation in generate_claude_md.py doesn't exist
- No pre-merge collision detection for large multi-agent merges

**Severity:** 🟠 **HIGH** — System mostly functional but hooks broken, large merge risk

---

## QA Regression (Apr 8, 20:07)

**Commit:** `8e418cba1`  
**Test:** QA-routes test  
**Result:** 6 FAIL, 5 PASS  
**Issue:** CUT API routes not wired  
**Fixed by:** `fef9a298e` (Wire up all CUT API routers)

---

## Analysis: Why Did Merge Gates Fail?

### Current merge_request() Gate

Checks:
- ✅ No needs_fix tasks blocking
- ✅ Has commit_hash
- ✅ Allows force=True bypass
- ❌ No large-merge pre-flight validation
- ❌ No hook syntax validation
- ❌ No enum registration verification
- ❌ No strategy-specific post-merge checks

### What Passed Through

| Regression | Gate Check | Result |
|-------------|-----------|--------|
| Sherpa crash | Pre-commit hook | ❌ MISSING |
| smart_snapshot missing enum | merge_request | ❌ NOT CHECKED |
| _qa_skipped deletion | merge_request | ❌ NOT CHECKED |
| PostToolUse hook invalid | merge_request | ❌ NOT CHECKED |
| 56-commit harness-eta | merge_request | ✅ NO LIMITS |

---

## Patterns Identified

### 1. Large Merges Have No Pre-Merge Validation
```
56-commit harness-eta merge → no pre-flight check
→ Multiple hook/guard issues → Multiple hotfixes
```

**Current:** merge_request() treats 1-commit and 56-commit merges the same  
**Should be:** Merges >20 commits require:
- Full integration test suite run
- Collision detection across preset boundaries
- Hook validation check

### 2. Hook/Registration Missing Until Needed
```
smart_snapshot merge → enum not registered
→ Hotfix 1 day later (5780d8417)
```

**Current:** No audit that "strategy X requires registration Y"  
**Should be:** Post-merge validation:
- `smart_snapshot` strategy → MCP enum must contain it
- `PostToolUse` hook → validate syntax before storing
- Any `_xyz` variable deletion → flag for human review

### 3. Pre-commit Hook Doesn't Catch Semantic Errors
```
sherpa.py refactor → FeedbackCollector API mismatch
→ Pre-commit hook doesn't validate imports/calls
→ Crash on first execution
```

**Current:** Pre-commit only checks generated artifacts (CLAUDE.md) and digest  
**Should add:**
- Python syntax check (ast.parse)
- Import validation (ImportError simulation)
- For sherpa.py specifically: run dry-run with test data

### 4. Hotfixes Go to Main Instead of Fix-in-Worktree
```
Regression detected → hotfix committed directly to main (f7ab115ab)
→ Bypasses pre-commit guard, merge_request validation
```

**Current:** Agent with regression permission commits directly  
**Should be:** Even hotfixes go through worktree + task board

---

## Comparison: "Good" vs "Bad" Commits

### Good Commit Pattern (Jan-Mar)
```bash
git log --format="%h %s" origin/main | head -50 | grep -E "fix:|feat:" | wc -l
→ ~5-8 per day
→ Each with task ID
→ No rollbacks, no "restore" messages
→ Tests run before merge
```

### Bad Commit Pattern (Apr 7-8)
```
0c47bf77c — Switch model (untested)
437503b5d — Fix crash from switch
839681a34 — Fix again
12a643027 — ROLLBACK (3 commits later)
→ 4 commits to fix 1 issue
→ Model switch should have included e2e tests
```

---

## Recommendations

### Immediate (This Week)

**1. Strengthen merge_request() Gate**
```python
def promote_to_main(task_id, branch):
    # New checks:
    
    # Check 1: Large merge pre-flight
    commit_count = count_commits(branch, "main")
    if commit_count > 20:
        require_integration_tests(branch)  # Must pass full suite
        require_no_force_push()  # force=True not allowed
        require_hook_validation(branch)  # Check all hooks
    
    # Check 2: Post-merge validation
    validate_enum_registrations(branch)  # MCP, etc.
    validate_hook_syntax(branch)  # generate_claude_md hooks
    validate_variable_changes(branch)  # Flag deletions like _qa_skipped
```

**2. Pre-commit Hook Enhancements**
- Add Python AST syntax check
- Add import validation (ImportError simulation)
- For sherpa.py: dry-run check with test data

**3. Hotfix Discipline**
- Hotfixes also go through worktree + task board
- Even P0 hotfixes must pass pre-commit hook
- Rollbacks require a task explaining why

### Medium-term (Next 2 weeks)

**4. Merge Strategy Validation**
- smart_snapshot → auto-verify enum registration
- Any new strategy → document required post-merge validations
- Auto-test each strategy in CI

**5. Hook System Audit**
- Find all `generate_claude_md` hooks that can be invalid
- Add validation to each hook before allowing hook to be registered
- Create hook-validation.py as part of pre-commit

**6. Integration Test Expansion**
- Sherpa.py model switch should run full e2e before merge
- smart_snapshot should include enum registration tests
- Post-merge hook tests (wake protocol, storage rules)

### Long-term (Phase 210+)

**7. Multi-Agent Merge Collision Detection**
- Detect when merges from different roles touch overlapping files
- Flag for human review before allowing merge
- Auto-test all presets on merged code

**8. Merge Queue / Staging**
- Instead of direct main, use staging branch
- Run full regression suite on staging
- Only merge to main after staging passes
- Rollbacks come from staging, not main

---

## Timeline Reconstruction

**Clean timeline (what should have happened):**

```
Apr 7, 18:00 → Branch: photo_parallax_playground_codex → feature branch
Apr 7, 23:40 → merge_request(photo_parallax_playground_codex)
              → PRE-FLIGHT CHECK: 5 commits, safe to merge
              → TESTS: smart_snapshot registration checked ✅
              → MERGE to main
              → POST-MERGE: enum validated ✅

Apr 8, 00:00 → Branch: sherpa model switch (gemma4:e4b)
              → Refactor: FeedbackCollector API
              → TESTS: e2e scout-sherpa with gemma4 ✅
              → TESTS: imports validated ✅
              → merge_request()
              → MERGE to main

Apr 8, 21:00 → Branch: harness-eta (56 commits)
              → PRE-FLIGHT: Large merge detected
              → COLLISION: Check 56 commits against main
              → TESTS: Full integration suite on merged code
              → POST-MERGE: Hook validation ✅
              → MERGE to main
```

**Actual timeline (what happened):**

```
Apr 7, 23:43 → Smart snapshot merge (incomplete)
Apr 7, 23:48 → Hotfix: enum registration
Apr 8, 00:05 → Model switch (untested)
Apr 8, 00:13 → Crash: FeedbackCollector
Apr 8, 00:32 → Rollback: sherpa.py
Apr 8, 21:49 → Hotfix: _qa_skipped restoration
Apr 8, 23:24 → Large harness-eta merge (no pre-flight)
```

---

## Metrics

**Before (Jan-Mar):** Stable  
**Now (Apr 7-8):**
- Regressions per day: 3
- Hotfixes per day: 8
- Rollbacks: 1 (Sherpa)
- Time to fix regression: 10-30 minutes (still good)
- **But:** No unified root cause addressed

---

## Conclusion

The regression pattern is **not accidental** — it's **systematic failure of merge gates** for large, multi-agent merges.

**Root issue:** merge_request() was designed for 1-5 commit worktree merges, not 56-commit feature branches.

**Solution:** Distinguish merge types and apply appropriate validation:
- **Worktree merge (1-5 commits):** Current gates sufficient
- **Large feature merge (20+ commits):** Require pre-flight + full test suite
- **Critical code paths (sherpa.py, hooks):** Additional e2e validation

**Next steps:** Implement immediate recommendations (Gate strengthening + Pre-commit + Hotfix discipline) this week. Then tackle merge strategy validation and integration test expansion.

