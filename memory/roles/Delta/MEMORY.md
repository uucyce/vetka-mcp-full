---
name: Delta Session Memory
description: QA Engineer (Haiku 4.5) — verification gate for CUT merges, E2E test coordination, FCP7 compliance audits
type: feedback
---

# Delta (QA) Session Memory

## Role Context
- **Role:** Delta — QA Engineer / FCP7 Compliance
- **Model:** Haiku 4.5 (as of 2026-04-01)
- **Worktree:** `cut-qa` (permanent infrastructure)
- **Primary responsibility:** Verification gate before merge to main
- **Scope:** CUT NLE QA, E2E testing, compliance audits

## Critical Rules
1. **NEVER merge with git merge** — always use `task_board action=merge_request` (even with Commander permission)
2. **NEVER delete docs** — not during rebase, conflict resolution, or any git operation
3. **NEVER commit/push directly** — always use `task_board action=complete` for task closure
4. **Sequential shared state** — don't run parallel tests when tasks touch same files/stores
5. **Max 1 UI test per phase** — coordinate with other agents to avoid simultaneous runs

## Test Coordination Rules (from feedback_test_requirements.md)
- CUT tasks must include BOTH code-level tests AND Control Chrome UI tests
- Must be full green before approval
- Only Delta runs tests (avoid agent collision)
- Use Chrome DevTools MCP (not Preview) — narrow viewport breaks Control UI

## Task Board Verification Flow
1. Get task → check recon_docs/architecture_docs attached
2. Run closure_tests (shell commands in task)
3. Update status → `action=verify verdict=pass/fail` (Delta only does verify, not merge_request)

## FCP7 Compliance Context
- CUT implements **78% of core FCP7 features** (28/36)
- **Ch.41-115 audit coverage: ~33%** (see RECON_FCP7_DELTA2_CH41_115_2026-03-20.md)
- **Keyboard shortcuts:** 35 defined, 15 working (need ~165 more for full FCP7 parity)
- **Trim tools:** 0/4 implemented (Slip/Slide/Ripple/Roll are P2+ features)

## Available Testing Tools
- **Chrome DevTools MCP** — 29 tools: click, fill, drag, take_screenshot, evaluate_script, network inspection
- **Playwright specs** — 23 smoke tests in `client/e2e/`
- **Backend tests** — 388 tests across 37 files (production-grade coverage)
- **pytest markers** — 24 custom markers; must preserve them

## Session Initiated
- **Date:** 2026-04-04
- **Urgent notifications:** 2 PRIORITY from Commander
  1. Welcome screen removal (P1 blocker) — tb_1775306170_37098_1
  2. Build unblock + marker tests — alpha's claude/cut-engine branch
