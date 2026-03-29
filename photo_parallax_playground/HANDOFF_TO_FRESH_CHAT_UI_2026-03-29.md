# HANDOFF TO FRESH CHAT — UI CONTINUATION — 2026-03-29

Updated: `2026-03-29 14:35:00 MSK`

## Workspace
- Workspace: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground`
- Branch: `main`
- Main edited files:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/index.css`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/package.json`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/scripts/dev-server-stop.sh`

## Mainline State
- Clean parallax UI reset snapshot was integrated into `main`.
- Follow-up UI tasks already landed on `main`:
  - `9b4d3db5f` — `PARALLAX-UIR11.2 compact Export into section-first operator panel`
  - `3cbcfe2c7` — `PARALLAX-UIR11.5 reserve bottom camera key tray and verify wide/square UI`

## Live Check
- Fresh UI verification should use:
  - `npm run dev:clean`
  - then `http://127.0.0.1:14350/`
- `14350` is now the standard fixed dev port for this playground.
- `npm run dev:stop` should be called after QA to avoid runaway `vite` processes.

## What Was Changed

### 1. Viewer-first layout remained the main direction
- Main monitor stays centered and dominant.
- `Depth / Extract / Camera` remain in the bottom working dock.
- `Objects and Route Notes` stay folded by default.
- `Manual Cleanup` remains collapsed by default.

### 2. Right-side inspector is now section-first
- `Export` was converted to the same compact accordion logic as `Depth / Extract / Camera`.
- `Export` now shows a compact summary when closed instead of an always-open readout wall.
- Actions stay visible, but the bulk readout no longer floods the right rail by default.

### 3. Lower workspace now reserves room for camera keys
- A dedicated `camera key tray` now exists under the monitor.
- This is currently a layout reserve / readout strip, not a real keyframe editor yet.
- The purpose is to remove dead space and establish the future CUT-like animation zone.

### 4. Viewer shell is less card-like than before
- Main stage shell no longer reads as a heavily rounded card.
- It still has a softened shell treatment, but it is materially closer to a real image monitor.

### 5. Dev server discipline was added after repeated runaway CPU incidents
- `package.json` now includes:
  - `dev`
  - `dev:stop`
  - `dev:clean`
- `scripts/dev-server-stop.sh` now kills stale `vite` processes across `photo_parallax_playground` workspaces.
- This was added because multiple stray `vite` instances were repeatedly reaching ~`800%` total CPU.

## Important Current Behavior
- Fixed local dev port: `14350`
- `npm run dev:clean` should be the only normal way to start live QA.
- `npm run dev:stop` should be the normal way to finish it.
- `Depth / Extract / Camera / Export` all start compact.
- `Manual Cleanup` starts collapsed.
- `camera key tray` is present under the monitor.

## Verified Checks
- `npm run build` passed after `UIR11.2`
- `npm run build` passed after `UIR11.5`
- Live QA on fresh Vite port confirmed:
  - wide sample: `hover-politsia`
  - square sample: `drone-portrait`

## Known Limits / Gaps

### 1. True portrait QA is still not completed
- `drone-portrait` is square (`1024 x 1024`), not true portrait.
- Current `SAMPLE_LIBRARY` has no true portrait asset.
- This means non-16:9 and portrait-safe framing still need another pass.

### 2. Camera tray is only a reserve, not a full feature
- There is still no real camera key editing, key selection, or animation curve flow.
- The space is now prepared for that next stage.

### 3. Monitor fit for non-16:9 sources remains the next important UI risk
- Wide and square were checked.
- Portrait-safe fit and framing are still open.

## Recommended Next Move For Fresh Chat
Continue from current `main` state and do this next:

1. Take `PARALLAX-UIR12: fix portrait-safe stage fit and non-16:9 source framing`
2. Keep the current compact inspector and tray structure
3. Improve stage fit behavior without reintroducing card-heavy UI
4. Re-run live QA on non-16:9 cases after that

## Quick State Summary
- The core UI reset is already on `main`.
- `Export` compacting is done.
- `camera key tray` reserve is done.
- Dev server lifecycle is now controlled to stop repeated runaway CPU.
- The next clean step is `UIR12`, not another broad visual reset.
