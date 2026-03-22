# CUT Agent Feedback — Wave 5-6 Consolidated
**Date:** 2026-03-22
**Session:** 4-Opus parallel (Alpha/Beta/Gamma/Delta-2) + Delta-1 QA
**Commander:** Opus 4.6 (pedantic-bell)

---

## Session Metrics

| Agent | Tasks | Commits | Tests | Domain |
|-------|-------|---------|-------|--------|
| Alpha | 12 | 12 | 141 | Engine: store migration, 3-point edit, JKL, desktop build |
| Beta | 13 | 13 | 79 | Media: full Color Pipeline v2 (scopes, LUT, log, broadcast safe) |
| Gamma | 11+ | 11 | — | UX: menus (all 8), panel focus, DnD, timecode, speed, L/J-cut |
| Delta-2 | 5 | 5 | 40 TDD | QA: FCP7 recon Ch.41-115, 26 smoke tests, 40 TDD specs |
| Delta-1 | 3 | 3 | 41+ pass | QA: debug shell, scene graph, transport mount |

**Total: ~44 tasks, ~44 commits, ~300+ tests**

---

## Consensus: What Works

1. **Test-first discipline** — ALL agents independently confirm: Python ref tests (Alpha), color math tests (Beta), TDD specs (Delta) catch real bugs early
2. **FCP7 manual as specification** — not guessing at behavior. "Test the contract, not the implementation"
3. **Task board discipline** — 12 commits to 12 tasks, zero orphaned code (Alpha). Sub-roadmap as architecture tool (Beta)
4. **File ownership boundaries** — zero cross-agent conflicts this session (vs 3+ last session)
5. **Store actions as single entry point** — menu → `store.getState().action()`, no synthetic keyboard events (Gamma)
6. **Pure-function approach** — resolveThreePointEdit, formatTimecode, parseTimecodeInput, scope renderers — all trivially testable

## Consensus: What Doesn't Work

1. **Dockview CSS cascade** — #1 pain point across ALL agents. !important overrides, nuclear wildcards, inline rgb() values
2. **Worktree infrastructure** — no node_modules (need symlink), file drift, task board branch detection manual
3. **TransportBar.tsx is dead code** — 163 lines, 0 imports, causes confusion. KILL IT.
4. **Source = Program video feed** — both monitors read same video element. VideoPreview ignores `feed` prop.
5. **Playwright CLI broken** — `npx playwright test` exits 194. Workaround: `node node_modules/@playwright/test/cli.js test`
6. **Vite dev server cache** — editing doesn't always invalidate, wrong CWD serves wrong files

---

## Architectural Insights (per domain)

### Alpha — Engine
- **Three-Point Edit** (`I → O → ,`) is THE NLE litmus test
- **JKL shuttle** needs own rAF render loop (manual seek for reverse/speed > 2x)
- **Store migration Phase 2**: lane-level, not field-level → `useTimelineData(timelineId?)` hook
- **Dockview = layout, not component model** — components must be idempotent

### Beta — Media/Color
- **Camera log curves** all follow same pattern: linear near black + log for rest (5-10 lines numpy each)
- **.cube LUT**: R varies fastest; 33-point = 35,937 lines, parses <10ms; trilinear interp caught axis bug
- **Scopes performance** (M-series): histogram ~2ms, waveform ~8ms, parade ~20ms, vectorscope ~12ms, all four ~42ms
- **Scopes need WebSocket** for live playback (currently HTTP, ~2x/sec, jerky)
- **Gamut conversion without colour-science is lossy** — acceptable preview, not final render

### Gamma — UX/Panels
- **ACTION_SCOPE map** — cleanest way to scope 50+ hotkeys in 4 lines
- **Panel focus is prerequisite, not feature** — without it, JKL/Delete/I-O all go wrong
- **Menus are documentation** — even disabled items with shortcuts change perception (4→20 items in Sequence)
- **L-cut/J-cut** is signature of professional editing — CUT's separate V/A lanes make this natural
- **togglePanel()** pattern: if exists → setActive(), if not → addPanel(). Solves "can't reopen"

### Delta-2 — QA/Compliance
- **3-tier test strategy**: DOM-only / store-based / backend-integrated
- **Shared dev server** instead of per-spec spawn saves 6s per test
- **data-testid convention**: cut-editor-layout, cut-timeline-track-view, cut-timeline-clip-{id}, monitor-tc-source/program
- **__CUT_STORE__ exposure** via useEffect (not module-level) avoids ESM circular dep

---

## Bugs Found (cross-agent)

| # | Bug | Found by | Priority | Status |
|---|-----|----------|----------|--------|
| 1 | Duplicate TransportBar from corrupt dockview localStorage | All | P0 | Partially fixed (dedup guard), stashed Delta-1 code also adds dupe |
| 2 | Source = Program video feed (same video element) | Alpha | P1 | Open |
| 3 | TransportBar.tsx dead code (163 lines, 0 imports) | Gamma | P2 | Delete it |
| 4 | Input/Output logic confused (Source vs Timeline) | User | P0 | Task tb_1774137356_10 |
| 5 | ~50 pre-existing TS errors | Alpha | P3 | Won't block dev build |
| 6 | BPMTrack labels overlap at timeline bottom | Alpha | P3 | Open |
| 7 | Autosave not wired to backend (stub) | Alpha | P2 | Open |
| 8 | ColorWheel not rendering in dockview (file drift) | Beta/Delta-2 | P2 | Open |
| 9 | containerWidth non-reactive in TimelineTrackView | Alpha | P3 | Pre-existing |

---

## Predecessor Advice Chains

### For next Alpha (Engine):
- Read FCP7 PDF chapters BEFORE coding
- Write Python reference tests FIRST
- Check dockview localStorage for duplicate panel IDs
- Don't touch MenuBar.tsx (Gamma territory)
- Use `TAURI_PLATFORM=1 npx vite build` (not `npm run build`)
- Store migration Phase 2: `useTimelineData(timelineId?)` hook

### For next Beta (Media):
- FFmpeg for render, PyAV for preview/scopes — keep separate
- Effects live in 3 places: EFFECT_DEFS (schema), compile_video_filters() (FFmpeg), apply_numpy_effects() (preview)
- Install colour-science + PyAV for real gamut conversion
- Camera log auto-detect needs real footage testing
- Scopes need WebSocket upgrade for live playback

### For next Gamma (UX):
- Kill TransportBar.tsx (dead code, 163 lines)
- Convert remaining keyboard dispatch → store actions
- CSS isolation for timeline content (dockview cascade = nightmare)
- Bridge effect: multi-instance timeline data pipeline
- Pin dockview version, test theme after any upgrade

### For next Delta (QA):
- Use Playwright MCP, not osascript for Chrome testing
- Run tests with `node node_modules/@playwright/test/cli.js test`
- Read existing tests (Ch.1-40 by Delta-1) — don't duplicate
- Debug shell tests need real backend — consider mock fixture
- FCP7 recon doc is your map — don't re-read 1924-page PDF

---

## Priority Matrix (next wave)

```
P0 — BLOCKING DEPLOYMENT:
  tb_1774137356_10: Fix TransportBar dupe + Input/Output Source vs Program logic
  Source ≠ Program video feed (Bug #2 above)

P1 — USABLE NLE:
  Store migration Phase 2 (useTimelineData hook)
  Autosave wired to backend
  WebSocket scopes for live playback

P2 — PROFESSIONAL QUALITY:
  Kill TransportBar.tsx dead code
  ColorWheel rendering in dockview
  FCP7 razor split, ⌘K split, linked selection (tb_1774130923_4)

P3 — POLISH:
  Audio Mixer (tb_1773996025_9)
  Motion attributes (tb_1773996031_10)
  Keyframe navigation (tb_1773996076_15)
```

---

## Commander's Session Notes

- **Merge cycles**: 8+ successful merges, 3x cut_routes.py conflict resolution
- **Delta confusion**: Two Delta agents sharing same worktree (cut-qa) caused identity confusion. Solution: different colored terminals or separate worktrees (cut-qa-1, cut-qa-2)
- **Stash trap**: Delta-1 left uncommitted code on main adding standalone `<TransportBar />` — likely root cause of persistent dupe bar
- **User's strategic pivot**: CUT needs to be a WORKING NLE for paid video editing work. APP/DMG deployment before AI features (DAG/PULSE). FCP7 baseline first.
- **Key user quote**: "мне реально надо монтировать видео, надо немного деньжат заработать"

---

*"The orchestra played. The conductor listened. The music was in the silence between the notes."*
