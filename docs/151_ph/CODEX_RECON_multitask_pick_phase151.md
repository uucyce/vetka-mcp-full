# CODEX RECON — Multitask Pick (Phase 151)

Date: 2026-02-16
Protocol stage: RECON + REPORT (no implementation yet)

## Source checked
- `data/task_board.json` (`tasks` map)

## Pending/queued tasks snapshot (lightness-first)
1. `tb_1770577538_9` — Research: search/embedding model categories  
   status: `pending`, priority: `4`, complexity: `low`, phase: `research`
2. `tb_1771092050_4` — Wire HeartbeatChip + PlaygroundBadge into MCC header  
   status: `queued`, priority: `3`, complexity: `simple`
3. `tb_1770809271_3` — Cmd+K frontend to unified search API  
   status: `queued`, priority: `1`, complexity: `medium`
4. `tb_1771188524_9` — build new API endpoint  
   status: `pending`, priority: `2`, complexity: `medium` (underspecified)

## Quick feasibility notes
- `tb_1771092050_4` appears outdated vs current MCC changes (header already refactored in Phase 151; PlaygroundBadge intentionally replaced by SandboxDropdown).
- `tb_1771188524_9` is too vague (no endpoint contract).
- `tb_1770809271_3` is implementable but not “семечки” size.
- `tb_1770577538_9` is the smallest/clearest item and safe to complete fast as a concrete research deliverable.

## TAKEN (reserved for Codex)
`tb_1770577538_9` — **Research: search/embedding model categories**

## Narrow implementation plan (after GO)
1. Build focused research doc in `docs/151_ph/` with marker map:
   - search providers (Tavily/Serper/etc.) vs embedding providers
   - where they are wired now in repo
   - recommended UI category split + minimal API shape
2. Add explicit action checklist (small PR-ready steps, no speculative rewrites).
3. Verify references with file paths + grep evidence.
