---
name: CUT Critical Bugs — Apr 8, 2026 QA Verification
description: 3 P0/P1 bugs marked needs_fix after QA verification. Awaiting Alpha assignment and fix.
type: project
---

## Status (as of 2026-04-08 20:54 UTC)

3 critical CUT bugs have incomplete fixes and are marked **needs_fix**:

### 1. P0 — DockView Drag Broken in Tauri
- **Task ID:** tb_1775664186_82805_1
- **Timeline:** Created 19:03, claimed 19:48, done_worktree 19:49, marked needs_fix 20:54
- **Attempted Fix:** Apr 5 commit 5376e8630 — CSS `-webkit-user-drag: element` in dockview-cut-theme.css
- **Why Insufficient:** CSS fix verified correct by Epsilon but doesn't work in Tauri WKWebView
- **Likely Root Cause:**
  - dockview-react incompatible with Tauri 2.x
  - WKWebView drag event delegation differs from browser Safari
  - Tauri data-tauri-drag-region conflict
- **Blocker:** Users cannot reposition any of 22 dockable panels

### 2. P1 — Video Monitors Don't Resize with Window
- **Task ID:** tb_1775664262_82805_1
- **Timeline:** Created 19:04, claimed 19:49, done_worktree 19:50, marked needs_fix 20:54
- **Branch:** claude/cut-ux
- **Symptom:** Monitors pinned to left, content overflows right edge when window resized
- **Likely Cause:** Fixed-width CSS instead of flex/responsive layout
- **Blocker:** Monitors unusable at small window sizes (< 1400px)

### 3. P1 — Markers Cannot Be Added
- **Task ID:** tb_1775664967_82805_1
- **Timeline:** Created 19:16, claimed 19:46, done_worktree 20:04, marked needs_fix 20:54
- **Branch:** claude/cut-engine
- **Commit:** a8289bae — MARKER_CIRCULAR_FIX2 (time-marker imports)
- **Symptom:** No way to add markers to media clips or timeline tracks
- **Likely Cause:** Backend/frontend wiring incomplete (imports fixed but UI/handlers missing)
- **Blocker:** Core workflow feature missing (markers are essential for editing)

## Why:** Mar 22 debrief + last week's tests found these issues. Quick fixes attempted but QA verification (Epsilon) found them incomplete.

## How to apply:** Commander should assign all 3 to Alpha (owns layout/viewers/markers). Alpha to re-investigate root causes and provide full fixes with E2E verification.

## Related
- Apr 5 DockView CSS fix: commit 5376e8630, task tb_1775407414_68814_7
- Mar 22 Epsilon debrief: TransportBar shuttle issue + ClipTransition type mismatch
- Current CUT state: 78% FCP7 feature coverage, but these 3 regressions block core workflow
