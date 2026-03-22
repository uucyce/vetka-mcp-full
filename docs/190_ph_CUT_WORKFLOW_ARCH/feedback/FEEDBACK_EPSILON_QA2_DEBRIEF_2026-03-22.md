# Epsilon-QA2 Debrief — 2026-03-22

## Q1: What's broken?

`TransportBar.tsx:222` — reverse shuttle rAF loop unconditionally resets `shuttleSpeed=0` when `currentTime<=0`. This means pressing J at the start of a timeline silently does nothing. Editor who just opened a project and presses J to review = zero feedback. The `shuttleBack` handler works, sets speed to -1, then TransportBar's animation frame immediately cancels it. Fix: guard with `if (newTime <= 0 && state.shuttleSpeed < 0) { state.pause(); }` instead of resetting shuttle — let the user see the tool is active even at boundary.

Also: `ClipTransition` type in store allows only 3 values (`cross_dissolve | dip_to_black | wipe`) but `TransitionsPanel.tsx` sends 10 different strings (`crossfade`, `dissolve`, `slide_left`, etc.). Type mismatch — will cause bugs when render engine validates transition types.

## Q2: What unexpectedly worked?

The `__CUT_STORE__` exposure pattern is a testing goldmine. Every store action — seek, setLanes, toggleMute, setClipEffects — is callable from `page.evaluate` with zero mocking. I wrote 81 specs and never needed a single React Testing Library import. Zustand's `getState()` as a synchronous read + `set()` as synchronous write = perfect for E2E. The one gotcha (stale snapshot in same evaluate) is easily solved by splitting into two evaluate calls. This pattern should be documented as the official CUT testing strategy.

## Q3: Unrealized idea

**Mutation snapshot testing.** Every `setLanes()` call could log a before/after diff to a `__CUT_MUTATION_LOG__` array on window. Tests would assert not just "did clip count change" but "what exact operation happened" — `{op: 'split', clip: 'v1', at: 2.5, result: ['v1_L', 'v1_R']}`. This would catch subtle bugs like the razor race condition (two handlers firing, one overwriting the other) at the operation level, not the DOM level. Could be a 20-line middleware in the store that's only active when `window.__CUT_TEST_MODE__` is set.

## Session stats
Suites: 6 | Specs: 81 | GREEN: 66 (81%) | Commits: 14 | Tasks created: 7 (4 done, 3 pending)
