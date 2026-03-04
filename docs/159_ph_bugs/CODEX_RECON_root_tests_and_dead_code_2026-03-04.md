# CODEX RECON — Root Test Hygiene + Dead Code Candidates (Phase 159)

Date: 2026-03-04
Scope: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03` (root-only audit, high-safety mode)

## MARKER_159_RECON_1_ROOT_TEST_SCAN
Goal: detect test artifacts saved directly in project root instead of `tests/`.

Result:
- Found **1** unambiguous root test file:
  - `DETECTION_DIRECT_API_TEST.py`

Action taken:
- Moved file to `tests/`:
  - from: `DETECTION_DIRECT_API_TEST.py`
  - to: `tests/DETECTION_DIRECT_API_TEST.py`

Notes:
- No other root-level files matched conservative test patterns (`test_*.py`, `*_test.py`, `*test*.py`, `*_spec.py`).

## MARKER_159_RECON_2_AMBIGUOUS_TEST_ASSETS
Items that look test-related but were **not moved** (to avoid breaking unknown flows without explicit approval):
- `test_claude_tools/`
  - contains: `CLAUDE_TOOLS_ANALYSIS.md`, `mac_diagnostic.py`
  - reason not moved: folder-level relocation is higher-risk than single-file hygiene; may be referenced by external/manual workflows.

## MARKER_159_RECON_3_DEAD_CODE_CANDIDATES_REPORT_ONLY
Below are **candidates** for dead/archival code or stale assets. Nothing was deleted or modified.

1. `archive/`
- current state: empty directory.
- candidate reason: no active contents.

2. `backup/phase_103_dead_code/`
- contains archived implementation remnants (example: `user_message_handler_v2.py`).
- candidate reason: explicitly marked as dead code archive in historical docs (`docs/104_ph/DEAD_CODE_CLEANUP.md`).

3. `backups/` (qdrant timestamped folders)
- contains snapshot-like timestamped directories (`qdrant_20260120_*`, etc.).
- candidate reason: likely operational backups, not runtime code.

4. `test_claude_tools/`
- candidate reason: diagnostic/tooling artifacts; not part of main runtime path by name/location.

## MARKER_159_RECON_4_SAFETY_GUARDRAILS
Given active parallel development (multiple agents), this pass intentionally used strict rules:
- only root-level test hygiene move for one unambiguous file,
- no destructive actions,
- no refactors/renames for ambiguous folders,
- dead-code section is report-only.
