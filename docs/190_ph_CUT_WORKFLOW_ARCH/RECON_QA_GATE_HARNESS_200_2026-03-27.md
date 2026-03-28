# RECON: QA Gate + IS_ANCESTOR + AUTO_PROVISION Verification

**Date:** 2026-03-27
**Agent:** Delta (QA)
**Task:** tb_1774592259_1
**Branch under test:** claude/harness (commits e402a785, 1046082e)

---

## Verification Summary

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | promote_to_main rejects done_worktree without verified | PASS | Returns QA_GATE error with hint |
| 2 | promote_to_main accepts with skip_qa=true | PASS | Logs warning, allows promote |
| 3 | promote_to_main accepts verified tasks normally | PASS | Both status=verified and verified-in-history |
| 4 | Cherry-pick skips is-ancestor commits | PASS | MARKER_200.IS_ANCESTOR + skipped_ancestors array |
| 5 | session_init auto_provision on no role | PASS | _detect_origin + _detect_model_class + ephemeral role |
| 6 | Python syntax clean (5 files, main) | PASS | ast.parse all 5 |
| 7 | Python syntax clean (3 files, harness) | PASS | ast.parse harness versions |
| 8 | Import smoke (task_board, tools, session) | PASS | 3/3 import clean |
| 9 | skip_qa in schema + passthrough | PASS | In TASK_BOARD_SCHEMA, passes to promote_to_main |

## Test Results

```
33 passed, 1 xfail (PyYAML missing in test env — agent_registry), 0 failed
Test file: tests/test_phase200_qa_gate.py
```

## Findings

### No Bugs Found in QA_GATE Logic

The QA gate correctly:
- Checks `status_history` for verified event/status (dual check: `h.get("status") == "verified" or h.get("event") == "verified"`)
- Handles missing `status_history` key gracefully via `.get("status_history", [])`
- Only applies to `done_worktree` status (verified/done skip the gate)
- Provides clear error with hint for flow and skip_qa bypass

### No Bugs in IS_ANCESTOR

Cherry-pick loop correctly:
- Runs `git merge-base --is-ancestor` before each commit
- Appends skipped commits to `skipped_ancestors` array
- Also catches empty cherry-picks (existing logic) and adds to skipped list
- Returns `skipped_ancestors` in error responses for debugging

### AUTO_PROVISION — Minor Code Smell (non-blocking)

In `_auto_provision()` (session_tools.py):
- Uses `hashlib.md5(f"{os.getpid()}{time.time()}")` — `time.time()` makes instance names non-deterministic across restarts. This is intentional (unique per process) but means the same agent restarting gets a new ephemeral role each time.
- `_detect_origin()` relies on env vars that non-standard tools may not set (flagged by Zeta previously).

### Pre-existing: PyYAML not in test venv

`agent_registry.py` imports `yaml` which isn't available in the test environment. Not a harness issue.

## Verdict

**PASS** — All 3 features (QA_GATE, IS_ANCESTOR, AUTO_PROVISION) are correctly implemented. Safe to merge to main.
