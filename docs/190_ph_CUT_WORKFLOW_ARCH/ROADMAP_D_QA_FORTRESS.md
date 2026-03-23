# ROADMAP_D: QA Fortress
**Agent:** Delta (QA) | **Created:** 2026-03-23 | **Target:** 95%+ GREEN

## Mission
Delta owns quality gate for CUT NLE. No commit merges without PASS verdict.
Two testaments: FCP7 Manual (feature checklist) + CUT_Interface_Architecture_v1 (target).

---

## Phase 1: Regression Zero (current → 95%+)

### Baseline: 94/161 pass (58%). Target: 150/161 (93%)

| Test Group | Current | Target | Blocker | Owner |
|------------|---------|--------|---------|-------|
| Smoke (22 specs) | 17 pass | 22 pass | Selector drift from UI refactors | Delta updates selectors |
| Layout compliance (13) | 13 pass | 13 pass | DONE | - |
| FCP7 deep TDD (15) | 2 pass, 10 fixme | 6 pass, 9 fixme | TL1-TL4, MON1-MON2 unimplemented | Alpha/Gamma build |
| FCP7 menus TDD (21) | 1 pass, 6 fixme | 10 pass, 6 fixme | SEQ/MARK/CLIP menu items needed | Gamma build |
| Trim/Transitions TDD | 6 pass, 4 fixme | 11 pass, 4 fixme | TR1-TR6 keybind fixed, TX1/TX4/TX5/SP5 unimplemented | Alpha (tool scope) |
| Keyframes/Gaps TDD | 3 pass | 8 pass | GAP5 linked button, KF1-6 keyframe UI | Gamma (GAP5), Alpha (KF) |
| Workflow e2e | 10 pass | 11 pass | WF3 mark in/out routing | Alpha (DUAL-VIDEO) |
| Panel focus TDD | 0 pass | 3 pass | FOCUS1a scope, FOCUS4 indicator | Alpha |
| Coverage sweep | 8 pass | 11 pass | Tab visibility after panel split | Gamma (GAMMA-33) |
| Berlin smoke | 0 pass | 3 pass | Selector updates needed | Delta |
| Debug shell smoke | 0 pass | 13 pass | DebugShellPanel rewrite selectors | Delta |
| Scene graph smoke | 0 pass | 3 pass | DAG node selectors | Delta |
| NLE core smoke | 0 pass | 3 pass | Export/interactions/playback selectors | Delta |

### Priority fix tasks (created):
- `tb_1774231556_13` Alpha P2: TC1-TC3 TimecodeField regression
- `tb_1774224203_8` Alpha P2: FOCUS1a shuttle scope
- `tb_1774224199_7` Alpha P3: FOCUS4 panel indicator
- `tb_1774224195_6` Gamma P2: GAP5 linked selection button
- `tb_1774229402_9` Gamma P1: Navy tab backgrounds
- `tb_1774229408_10` Gamma P1: #3b82f6 in DOM
- `tb_1774229417_11` Alpha P2: Inspector clip selection
- `tb_1774229425_12` Alpha P2: Program Monitor error toast

---

## Phase 2: New Test Coverage

### 2.1 Three-Point Edit e2e (`tb_1774231561_14`)
- Load project with source clips
- Click clip in project bin → Source monitor shows it
- Press I (mark in at sourceCurrentTime)
- Press O (mark out at sourceCurrentTime)
- Focus timeline, seek to 5s
- Press comma (insert edit)
- Verify: new clip at 5s, subsequent clips rippled right
- Verify: undo (Cmd+Z) reverts insertion

### 2.2 Transition e2e (after TX implementation)
- Load project with 2+ clips
- Seek to edit point between clips
- Press Cmd+T (add default transition)
- Verify: cross-dissolve overlay visible at edit point
- Verify: transition duration matches default (1s)

### 2.3 Export e2e
- Load project, bootstrap, have clips on timeline
- File > Export (or Cmd+E)
- Select Premiere XML format
- Verify: export endpoint called with correct timeline state
- Verify: success/failure toast

### 2.4 Effects Browser e2e
- Open Effects panel (Cmd+5)
- Search for effect (e.g., "blur")
- Drag effect to clip (or click Apply)
- Verify: clip.effects updated in store
- Verify: Inspector shows applied effect

---

## Phase 3: Visual Regression

### 3.1 Screenshot Baseline
Capture reference screenshots for each panel in empty + loaded states:
- Source Monitor (empty / clip loaded)
- Program Monitor (empty / playing)
- Timeline (empty / 3 clips)
- Project Panel (list / grid view)
- Inspector (no selection / clip selected)
- Effects Panel
- Audio Mixer
- Color Corrector + Scopes

### 3.2 Playwright Visual Comparison
```typescript
// After each merge, compare:
await expect(page.locator('[data-testid="cut-panel-timeline"]'))
  .toHaveScreenshot('timeline-3clips.png', { threshold: 0.1 });
```
Threshold 0.1 = 10% pixel diff allowed (font rendering variance).

### 3.3 Monochrome Enforcement Test
Automated DOM audit: scan all visible elements for non-grey colors.
```typescript
const violations = await page.evaluate(() => {
  const els = document.querySelectorAll('*');
  const bad = [];
  for (const el of els) {
    const style = getComputedStyle(el);
    // Check color, background-color, border-color
    // Flag any rgb(r,g,b) where r≠g or g≠b (except markers)
  }
  return bad;
});
expect(violations).toHaveLength(0);
```

---

## Phase 4: QA Gate Protocol

### Review Checklist (every done_worktree):
1. `git diff main..claude/<branch>` — what actually changed
2. Task description match — claimed vs delivered
3. Architecture docs — CUT_TARGET_ARCHITECTURE.md compliance
4. FCP7 manual — relevant chapter cross-reference
5. Monochrome rule — ZERO non-grey color (except markers)
6. Scope check — only owned files touched
7. Smoke suite — run affected specs
8. Verdict: PASS / FAIL + specific findings

### Coordination with Epsilon:
- Epsilon writes new TDD specs for unimplemented features
- Delta verifies existing specs pass after implementation
- Max 1 UI test runner at a time (port conflicts)
- Shared dev server pool (globalSetup) — priority improvement

---

## Key Lessons from Predecessor (Delta-1 Debrief)
- `--workers=1` for TDD (port conflicts)
- `window.__CUT_STORE__` for direct Zustand access
- `focusedPanel` click before every hotkey test
- `{ exact: true }` for text selectors (substring collisions)
- `addInitScript` for preset switching
- JSON reporter + Python parser for accurate counts
- `test.fixme()` for known-unimplemented (not `.skip()`)
