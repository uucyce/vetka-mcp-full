# MARKER_168 PLAYER LAB RECON — 2026-03-11

## Current state
- **MARKER_168.PLAYER_LAB.SCREEN_BOUNDS** — `player_playground` now derives suggested shell from `screen.availWidth/Height` when running inside Tauri, dor `window.innerWidth/Height` in the web sandbox. Tests cover portrait image sizing and first-frame preview (see `player_stability.spec.ts`). Native window configuration snaps logical sizes to the closest integer ratio and stores trace data via `trace_player_window` to compare DOM vs native.
- **MARKER_168.PLAYER_LAB.PORTRAIT_IMAGE** — Images (including portrait) behave like first-class media: they prime instantly, compute display dimensions via `computeDisplayedBox`, and clear footer chrome so the viewer area fills. Added debut harness for `/work/teletape_temp/berlin/style_lor/*` assets to reproduce portrait stress cases.
- **MARKER_170.CUT.MARKER_CONTRACT** — Documented that VETKA logo prescribes provisional capture events until `VETKA Core/CUT` connects, after which star/moment markers replace it. Contracts now include fields like `migration_status`, `srt_comment` export mode, and anchor metadata, all captured in `PHASE_170_COGNITIVE_TIME_MARKERS_CONTRACT_2026-03-09.md`.
- **MARKER_170.CUT.PLAYER_DONOR** — The player is intentionally standalone, no CUT runtime bundled; contextual actions funnel into the local marker lane, and `window.vetkaPlayerLab` exposes APIs for snapshots, markers, provisional events, and quality controls. Tests assert the provisional workflow stays local and the UI flips only after explicitly enabling CUT.
- **MARKER_168.PLAYER_LAB.DEBUGTOOLS** — Review Artefacts and Playwright probe exist for repeated snapshotting (`player_lab_review.sh`, `dream_player_probe.spec.ts`), ensuring geometry, letterbox, and scoring numbers stay stable; new geometry snapshot fields now include native inner/outer logical + physical widths/heights.

## Pending work
- **MARKER_168.PLAYER_LAB.NATIVE_QUANTIZATION** — Capture and log native scale + inner/outer sizes on the `.app` to see the residual black bars; once traced, tweak `configure_player_window` to respect macOS DPR quantization when locking aspect content size.
- **MARKER_168.PLAYER_LAB.TOOLBAR_MINIMALISM** — Remove remaining UI chrome that constrains max shell width on portrait assets; ensure `pure mode` top row stays hidden and the transport overlay is the only visible chrome when `showTransport` hides.
- **MARKER_170.CUT.PAUSE_SEGMENTATION** — Prepare the player to produce `time markers` with `camera / pause-to-pause` semantics, communicating those markers through the documented endpoints before hooking up the real CUT runtime.
- **MARKER_170.CUT.SRT_EXPORT** — Build the SRT-compatible export pipeline so provisional events become shareable comments/subtitles and later importable by CUT; include `cam_payload` and `chat_thread_id` fields for future captions/whisper tooling.
- **MARKER_170.CUT.BRIDGE** — Continue tightening the `vetkaPlayerLab` APIs so CUT agent(s) can pull snapshots, trace data, and marker bundles without loading the full VETKA UI; keep the player as a donor surface.

## Next steps for CUT team
1. Consume `trace_player_window` output from the player to determine whether target shell sizes match native inner/outer geometry on macOS retina. Use those numbers to fine-tune the native aspect snapping heuristics.
2. Integrate provisional capture events with CUT when `migration_status` becomes `migrated`, replacing the UI icon and enabling CAM ranking/metadata extraction.
3. Wire the SRT export/import plus comment-subtitle toggle shelf so the player can seed CUT with both captions and annotations.

