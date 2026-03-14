# RECON OPUS — Full System Check (2026-03-10)

**Agent:** Opus Commander (Claude Code worktree: clever-murdock)
**Method:** 4 parallel Haiku scouts, Opus synthesis
**Scope:** Project state audit, digest staleness, Phase 171 Codex review, feature inventory

---

## MARKER_RECON.1 — Git History Since Phase 155

### Commit Volume
- **100+ commits** in 20 days (Feb 20 — Mar 10)
- **Peak burst:** 16 commits in ~20 hours (Mar 8-9)
- **Cadence:** ~4 commits/day, 70% feature / 30% docs
- **Author:** 100% Danila Gulin (no multi-agent Co-Authored-By in recent history)

### Phase Progression (155 → 171+)

| Phase | Status | Key Feature |
|-------|--------|-------------|
| 155 | DONE | Research corpus, verified recon baseline |
| 157 | DONE | File-first search intent, ranking regression |
| 158 | DONE | Premiere adapter MCP lane, media contracts, NLE XML |
| 161 | DONE | TRM pipeline W1-W6, UI observability, RAG-ready MYCO core |
| 162 | IN PROGRESS | MYCO helper p0 contracts, hidden memory bridge |
| 163 | ACTIVE | Long-tail surfaces, button hint catalog, MYCO help atlas |
| 166 | ACTIVE | Auto-apply favorite API keys, monochrome key input |
| 170 | ACTIVE | CUT mode (video editing), project/job store, 19 API endpoints |
| 171 | DONE | Multitask digest hardening (Codex) |

### Feature Cluster Breakdown (last 100 commits)
```
player-lab         12  (12%)   Tauri video player, geometry, fullscreen
myco/onboarding     9  (9%)    Conversational guide, hints, scenarios
MCC/workflow        9  (9%)    Template registration, runtime editing
chat/artifacts      6  (6%)    Unified search, media preview, versioning
scanner             3  (3%)    Unified scan panel, carousel sources
cut-mode            5  (5%)    Video editing engine, timeline, scene graph
docs/contracts     20  (20%)   Schema-first, 25+ JSON contracts
other              36  (36%)   Fixes, refactors, tests
```

---

## MARKER_RECON.2 — Phase 171 Codex Review

### Verdict: CORRECT, COMPLETE

Codex report `MARKER_171_P1_MULTITASK_DIGEST_VETKA_MCP_REPORT_2026-03-09.md` reviewed.

| Task | File | Status | Verified |
|------|------|--------|----------|
| Digest normalization | `myco_memory_bridge.py` | DONE | dict→structured fields (phase_number, phase_subphase, etc.) |
| Multitask status split | `myco_memory_bridge.py` | DONE | failed/cancelled → `failed` bucket, claimed → `active` |
| MYCO quick reply signal | `chat_routes.py` | DONE | `multitask errors: failed N` line added |
| Unit tests (3) | `test_phase171_*.py` | DONE | 3/3 passing |
| Regression tests (8) | `test_phase162_*.py` | DONE | 8/8 passing |

### Minor Observations (not bugs)
- Report baseline: `total=8, queued=6, failed=2` — actual board now shows `total=9` (1 running task appeared after report)
- Math still holds: `9 = 0 done + 1 active + 2 failed + 6 queued`
- No breaking changes to downstream APIs
- Pre-existing test failures in `test_phase159` and `test_agents_routes` are NOT introduced by Phase 171

---

## MARKER_RECON.3 — Digest Staleness Root Cause

### Current Digest State
```
last_updated:    2026-03-09T19:02:36Z
current_phase:   155.0 ("157 research corpus")
git.commit:      830e07c7
git.branch:      codex/mcc-wave-d-runtime-closeout
on_connect:      "Phase 144 COMPLETE!"  ← VERY STALE
```

### Actual State (HEAD)
```
HEAD commit:     ce86275c (8 commits newer)
Active phases:   162, 163, 166, 170, 171
Real features:   CUT mode, Player Lab, Myco Mode A, Scanner redesign
```

### Root Cause: 3-Layer Problem

**Layer 1 — `on_connect` frozen at Phase 144:**
- `agent_instructions.on_connect` in digest is manually set
- Nobody updated it since Phase 144
- Should reflect current state (Phase 162+)

**Layer 2 — Phase auto-sync broken for multi-feature work:**
- `auto_sync_from_git()` in `scripts/update_project_digest.py` parses commit messages for `Phase XXX`
- Recent commits don't follow the pattern (e.g., `fix(search):`, `feat(player-lab):`)
- So phase stays at 155.0 — the last commit with "Phase" in the message

**Layer 3 — `key_achievements` polluted:**
- Dragon bronze test/fix tasks dominate the achievements list
- Real feature commits (cut-mode, player-lab, myco) not captured
- Task tracker only logs Dragon pipeline completions, not manual git commits

### Digest Update Mechanism (Working But Limited)

| Mechanism | Trigger | What It Updates | Status |
|-----------|---------|-----------------|--------|
| Pre-commit hook | `git commit` | git info, Qdrant, MCP status, phase auto-sync | Working |
| Post-commit hook | After commit | Auto-push (main only) | Working |
| MCP git tool | After MCP commit | Commit hash + dirty flag only | Working |
| Task tracker | Pipeline completion | Achievements, headline | Working |
| Manual script | `python3 scripts/update_project_digest.py` | Full audit | Available |

**Key insight:** Digest is a **snapshot artifact**, not a live dashboard. For live context, `vetka_session_init` should combine stale digest + fresh system queries. But `on_connect` being 10+ phases behind misleads agents on connect.

---

## MARKER_RECON.4 — Current Feature Inventory

### Major New Modules (last 2 weeks)

#### CUT Mode — AI Video Editing Engine
```
src/api/routes/cut_routes.py        1,903 lines, 19 endpoints
src/services/cut_project_store.py      619 lines
src/services/cut_mcp_job_store.py      131 lines
docs/contracts/cut_*.json              20 schemas
docs/170_ph_VIDEO_edit_mode/           17 docs
```
- Bootstrap → Timeline → Scene Graph → Export pipeline
- Async job queue for waveform/transcript/thumbnail
- Contract-first design with 20 JSON schemas

#### Myco Mode A — Conversational Guide
```
client/src/components/myco/            4 components
src/services/myco_memory_bridge.py     803 lines
docs/163_ph_myco_VETKA_help/           45+ docs
```
- Animated hint lane with SVG icons
- Rules engine for contextual help scenarios
- Hidden memory indexing (README, internal docs)
- ENGRAM user task memory integration

#### Player Lab — Standalone Video Player
```
player_playground/src/App.tsx          37K lines
player_playground/src/lib/             geometry, native window
```
- Tauri native window with DMG packaging
- Time markers (cut_time_marker_v1 compatible)
- Global API: `window.vetkaPlayerLab` (10 methods)
- Quality presets (1x to 1/32 scale)

#### Scanner Redesign
```
client/src/components/scanner/ScanPanel.tsx   500+ lines
```
- Carousel source selector (Local, Cloud, Browser, Social)
- Inline path input, 10px progress bar
- Hover preview (300ms) + click-to-camera-fly

#### Workflow Templates
```
data/templates/workflows/              6 templates
```
- g3_critic_coder.json — adversarial 2-agent loop
- ralph_loop.json — iterative PRD story loop
- Schema: nodes (task/agent/condition) + edges (dataflow/structural/feedback)

### Codebase Totals
- **Python backend:** ~188K lines (86 files modified recently)
- **TypeScript/TSX:** ~72K lines (56 files modified recently)
- **Contract schemas:** 25+ JSON definitions
- **Documentation:** 80+ markdown files (phases 163, 170, 171)

---

## MARKER_RECON.5 — Action Items

### Priority 1: Fix Digest
- [ ] Update `agent_instructions.on_connect` → reflect Phase 162+ reality
- [ ] Update `current_phase` → 170+ (CUT mode is the active frontier)
- [ ] Clean `key_achievements` — replace dragon_bronze noise with real features
- [ ] Fix `auto_sync_from_git()` to handle `feat(xxx):` commit convention (not just `Phase XXX`)
- [ ] Update `summary.headline` to reflect CUT + Myco + Player work

### Priority 2: System Health
- [ ] Fix `requests` dependency for MCP server health check
- [ ] Verify Qdrant collections (currently showing 0 points)
- [ ] Update `git.branch` to reflect main HEAD

### Priority 3: Test Coverage
- [ ] Pre-existing failures in `test_phase159`, `test_agents_routes` — investigate or mark as known
- [ ] Add E2E tests for CUT mode endpoints
- [ ] Add contract tests for Player Lab time markers

---

## Summary

| Area | Status | Notes |
|------|--------|-------|
| Phase 171 (Codex) | CORRECT | All 3 tasks done, 11/11 tests pass, no red flags |
| Digest | VERY STALE | `on_connect` frozen at Phase 144, phase at 155, achievements polluted |
| Features | HEALTHY | CUT, Myco, Player, Scanner — all functional, contract-first |
| Git | ACTIVE | 4 commits/day, solo developer, well-organized |
| Architecture | SOLID | Sandwich layering, async jobs, schema-driven |
