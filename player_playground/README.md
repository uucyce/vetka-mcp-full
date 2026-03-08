# VETKA Video Player Lab

MARKER_168.VIDEOPLAYER.LAB.SANDBOX

Standalone sandbox for isolated video-player geometry work.

Default mode is now player-first:

- video-centered shell
- hidden debug drawer by default
- auto-fit shell after metadata load
- native fullscreen toggle in Tauri host

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
npm run tauri:dev
npm run tauri:build
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/player_lab_review.sh /absolute/path/to/video.mp4
```

Open [http://127.0.0.1:1424](http://127.0.0.1:1424) and load a local video.

## Shortcuts

- `Space`: play / pause
- `F`: fullscreen
- `I`: toggle debug drawer

## Synthetic Probe Mode

You can debug geometry without a real file by setting intrinsic dimensions directly in the UI or by query params:

```text
http://127.0.0.1:1424/?variant=fixed-footer&mockWidth=640&mockHeight=480&applySuggestedShell=1
```

This is the fastest way to compare shell contracts and verify whether a suggested metadata-first shell removes side letterboxing.

## Native App Output

The lab now has a minimal Tauri host.

Local macOS bundles are produced at:

```text
player_playground/src-tauri/target/release/bundle/macos/VETKA Player Lab.app
player_playground/src-tauri/target/release/bundle/dmg/VETKA Player Lab_0.1.0_aarch64.dmg
```

Use `npm run tauri:dev` for a live native shell and `npm run tauri:build` for a distributable `.app` and `.dmg`.

## Review Probe

Before a commit, capture a stable screenshot and geometry snapshot:

```bash
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/player_lab_review.sh /absolute/path/to/video.mp4
```

Artifacts are saved to:

```text
player_playground/output/review/latest-player-review.png
player_playground/output/review/latest-player-review.json
```

If no video path is passed, the probe falls back to a synthetic `1280x720` review frame.

## Debug API

Browser console:

```js
window.vetkaPlayerLab.snapshot()
window.vetkaPlayerLab.print()
window.vetkaPlayerLab.setVariant("fixed-footer")
window.vetkaPlayerLab.setSyntheticSize(640, 480)
window.vetkaPlayerLab.applySuggestedShell()
window.vetkaPlayerLab.toggleDebug()
window.vetkaPlayerLab.toggleFullscreen()
```
