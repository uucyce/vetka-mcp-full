# VETKA Video Player Lab

MARKER_168.VIDEOPLAYER.LAB.SANDBOX

Standalone sandbox for isolated video-player geometry work.

## Goals

- prove the viewer-shell contract outside MCC/VETKA noise
- compare shell variants quickly
- measure letterboxing directly
- prepare a player that can later be wrapped by Tauri or open-sourced separately
- allow synthetic geometry probes without a real video file

## Run

```bash
cd player_playground
npm install
npm run dev
npm test
npm run test:e2e
```

Open [http://127.0.0.1:1424](http://127.0.0.1:1424) and load a local video.

## Synthetic Probe Mode

You can debug geometry without a real file by setting intrinsic dimensions directly in the UI or by query params:

```text
http://127.0.0.1:1424/?variant=fixed-footer&mockWidth=640&mockHeight=480&applySuggestedShell=1
```

This is the fastest way to compare shell contracts and verify whether a suggested metadata-first shell removes side letterboxing.

## Debug API

Browser console:

```js
window.vetkaPlayerLab.snapshot()
window.vetkaPlayerLab.print()
window.vetkaPlayerLab.setVariant("fixed-footer")
window.vetkaPlayerLab.setSyntheticSize(640, 480)
window.vetkaPlayerLab.applySuggestedShell()
```
