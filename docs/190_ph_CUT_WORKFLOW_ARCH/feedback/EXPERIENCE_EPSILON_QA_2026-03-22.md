# EXPERIENCE_EPSILON_QA — 2026-03-22
## Agent: Epsilon | QA-2 & FCP7 Compliance | GREEN terminal | Branch: claude/cut-qa-2

---

## Mission
Run FCP7 Deep Compliance TDD specs (`cut_fcp7_deep_compliance_tdd.spec.cjs`) and audit how many RED-by-design tests have turned GREEN after Alpha/Gamma fixes.

## Results: 5/14 GREEN, 4/14 RED, 5/14 SKIP

### GREEN (newly passing — previously RED by design)

| Test | Feature | Notes |
|------|---------|-------|
| TL1 | Track height Shift-T cycle | Height changes on keypress |
| TL1b | Track divider draggable | `row-resize` cursor detected between V/A tracks |
| MON1 | Transport buttons centered | Centering within 20% tolerance confirmed |
| MON1b | Prev/Next Edit buttons | `[aria-label*="previous edit"]` and `[aria-label*="next edit"]` found |
| KEYS:Shift-L | Linked Selection toggle | `linkedSelection` state toggles via `__CUT_STORE__` |

### RED (still failing — needs Alpha/Gamma implementation)

| Test | Feature | Failure Reason |
|------|---------|----------------|
| TL2 | Track visibility toggle (eye icon) | No `[aria-label*="visib"]` or `[data-testid*="visibility"]` elements in lane headers |
| MON2 | Mark Clip (X) / Match Frame (F) buttons | Source panel `[data-testid="cut-panel-source"]` not found, or marking buttons absent |
| EDIT1 | Razor tool (B key) splits clip | `activeTool` state changes but clip count stays at 6 (split not executing on click) |
| KEYS:Cmd-K | Add Edit / split at playhead | Same as EDIT1 — `seek()` works but split logic doesn't increment clip count |

### SKIP (serial cascade — blocked by earlier failure in same describe.serial)

| Test | Blocked By |
|------|------------|
| TL2b: visibility toggle dims track | TL2 fail |
| TL3: editable timecode field | TL2 fail |
| TL3b: typing timecode navigates playhead | TL2 fail |
| TL4: display controls (overlays/waveform) | TL2 fail |
| EDIT2: linked clip names underlined | EDIT1 fail |
| EDIT3: through edit red triangles | EDIT1 fail |

## Observations

1. **Track infrastructure (TL1) is solid** — height cycling and divider cursor both work, meaning the lane layout system is functional.
2. **Monitor transport (MON1) is complete** — centering and edit navigation buttons are present and correct.
3. **Linked Selection (KEYS:Shift-L)** — store-level toggle works, confirming hotkey wiring is live.
4. **Razor/Split gap is the biggest blocker** — EDIT1 and KEYS:Cmd-K both fail on the same issue: the split action doesn't actually create a new clip. This blocks 3 downstream tests (EDIT2, EDIT3 cascade).
5. **Visibility toggle (TL2)** is the other major blocker — its failure cascades to skip 4 tests (TL2b, TL3, TL3b, TL4).
6. **Serial describe blocks amplify failures** — 2 root failures (TL2, EDIT1) cascade to 6 skips. Consider splitting into independent groups once features land.

## Recommendations for Commander

- **Priority 1:** Razor/Split implementation (EDIT1) — unblocks 3 tests
- **Priority 2:** Track visibility toggle (TL2) — unblocks 4 tests
- **Priority 3:** Monitor Mark Clip/Match Frame buttons (MON2) — standalone, no cascade

## Session Stats
- Duration: ~5 min active
- Tests run: 14 unique (29 with retries)
- Dev server: reused existing on port 3009
- No conflicts with Delta (verified via active_agents check)

## Tooling Notes
- `node node_modules/@playwright/test/cli.js test` — confirmed working (npx exits 194)
- Retry config (retries=1) doubles Playwright output — read unique test names, not line count
- `__CUT_STORE__` exposure confirmed working for state inspection
