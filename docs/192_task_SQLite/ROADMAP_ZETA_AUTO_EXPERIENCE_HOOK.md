# Roadmap: Auto-Experience Hook + Bugs Found
**Phase:** 195+ (Zeta final)
**Date:** 2026-03-22

---

## Implementation Tasks

### E1: auto_experience_save.py — core script
Create `src/tools/auto_experience_save.py`:
- Detect role from `git branch --show-current` → AgentRegistry
- Read session tracker state (tasks_completed, files_edited, etc.)
- Read CORTEX feedback_log.jsonl (last session entries)
- Compute reflex_summary (success_rate, top_tools, failed_tools)
- Build ExperienceReport → store.submit()
- Skip if no meaningful work (0 tasks + 0 edits + 0 searches)
- Print 3-line summary to stderr
- Always exit 0

### E2: Tests for auto_experience_save
- Test: session with tasks → report saved
- Test: session with no work → report NOT saved
- Test: unknown branch → saves with callsign=""
- Test: CORTEX feedback aggregation correct
- Test: script exits 0 even on error

### E3: Hook configuration + verification
- Add hook to project settings.json (Stop event)
- Integration test: simulate session end → verify report file created
- This IS the last task of the phase → auto-experience should self-trigger

---

## Bug Fix Tasks (found during Zeta recon)

### BUG-1: Test artifacts pollute production task_board.db
API tests (`test_phase121_task_board.py`) create tasks in live database.
Fix: conftest.py fixture should override `TASK_BOARD_FILE` to tmpdir.
Already cleaned 29+5 artifacts manually — need systemic fix.

### BUG-2: _detect_current_branch() always returns main from worktree
`task_board.py:847` uses `cwd=PROJECT_ROOT` which is always main repo.
Worktree agents get wrong branch → tasks close as `done_main` instead of `done_worktree`.
Current workaround: CLAUDE.md says "always pass branch= explicitly".
Fix: accept cwd parameter or detect from calling process.

### BUG-3: Ownership warnings not visible to user
D4 warn-mode validation on complete produces warnings in task_board result,
but user never sees them (only agent's MCP response shows them).
Fix: aggregate warnings in session summary or session_init.

---

*Last task of this phase (E3) is the proof — if auto-experience fires,
this roadmap's experience will persist forever.*
