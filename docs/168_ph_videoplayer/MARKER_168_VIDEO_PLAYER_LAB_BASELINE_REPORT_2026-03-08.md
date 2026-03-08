# MARKER_168 Video Player Lab Baseline Report

Date: 2026-03-08

## Status

The isolated `player_playground` sandbox is now runnable and verified.

## What Is Proven

- the lab installs cleanly with its own dependencies
- pure geometry math is covered by unit tests
- a browser e2e now reproduces a bad shell and a good shell deterministically
- `fixed-footer + suggested shell` can eliminate side letterboxing for a 4:3 synthetic probe
- `flex-footer` reproduces side letterboxing for the same 4:3 probe

## Verified Commands

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/player_playground
npm test
npm run build
npm run test:e2e
```

## Winning Baseline

Current winning shell contract inside the lab:

- explicit footer reserve
- metadata-first suggested shell size
- geometry snapshot exposed via `window.vetkaPlayerLab`

## Console API

```js
window.vetkaPlayerLab.snapshot()
window.vetkaPlayerLab.print()
window.vetkaPlayerLab.setVariant("fixed-footer")
window.vetkaPlayerLab.setSyntheticSize(640, 480)
window.vetkaPlayerLab.applySuggestedShell()
window.vetkaPlayerLab.resetShell()
```

## Immediate Next Step

Wrap the same isolated shell in a minimal native host and compare:

1. web-only shell geometry
2. Tauri-hosted shell geometry
3. fullscreen enter/exit restoration

Do not migrate back into VETKA detached media path until the native host proves the same shell contract.
