# MARKER_159.C5 VIDEO WINDOW QUICKTIME-FIT RECON (2026-03-07)

## Context
Goal from user: media artifact window should behave like QuickTime:
- no large empty dark strip under video,
- window size should harmonize with actual video resolution/aspect,
- remove hardcoded bottom darkening that visually amplifies the gap.

Protocol mode: RECON only (no implementation in this step).

## MARKER_159.C5.RECON.1 Current Window Sizing Is Static (Primary mismatch source)
Source: `client/src-tauri/src/commands.rs:245-250`

Current detached media window opens with fixed defaults:
- `inner_size(960.0, 680.0)`
- `min_inner_size(760.0, 460.0)`

Impact:
- for many videos (for example 16:9 and especially horizontal clips), viewport height exceeds displayed video height,
- this creates guaranteed extra vertical space even before toolbar/overlays,
- behavior is opposite to QuickTime-like "fit to media" opening.

## MARKER_159.C5.RECON.2 Detached Video Render Uses Fill-Container + contain (Secondary gap source)
Sources:
- `client/src/components/artifact/ArtifactPanel.tsx:1210-1212` (viewer container forced to `height: '100%'`)
- `client/src/components/artifact/viewers/VideoArtifactPlayer.tsx:619-621`

Current behavior in detached mode:
- video style switches to `{ width: '100%', height: '100%', objectFit: 'contain' }`.
- parent layout is column flex with viewer area taking full remaining height.

Impact:
- `contain` preserves aspect ratio and letterboxes inside available box,
- when available box is taller than media ratio, visual black area appears,
- with static 960x680 defaults this is frequent.

## MARKER_159.C5.RECON.3 Dark Background Is Layered In Multiple Levels
Sources:
- `client/src/ArtifactMediaStandalone.tsx:70` (`background: '#0a0a0a'`)
- `client/src/components/artifact/ArtifactPanel.tsx:1425-1430` (`background: '#0a0a0a'` root)
- `client/src/components/artifact/viewers/VideoArtifactPlayer.tsx:596`, `:620` (`background: '#000'`)

Impact:
- any leftover layout space is rendered as solid dark field,
- perceived as "empty dead zone" under media.

## MARKER_159.C5.RECON.4 Bottom Hardcoded Darkening Exists Inside Player Controls
Source: `client/src/components/artifact/viewers/VideoArtifactPlayer.tsx:670-678`

Current controls bar overlay uses:
- `background: linear-gradient(transparent, rgba(0,0,0,0.9))`

Impact:
- even when geometry is fixed, bottom of media remains intentionally darkened,
- with existing empty zone this makes visual problem stronger.

## MARKER_159.C5.RECON.5 Detached Footer Toolbar Adds Its Own Dark Strip
Source: `client/src/components/artifact/Toolbar.tsx:157-164`

Current footer style:
- `background: 'rgba(15, 15, 15, 0.95)'`
- `borderTop: '1px solid #222'`

Impact:
- expected to be visible (action row),
- but when video area already over-tall, combined result looks like large dark bottom block.

## MARKER_159.C5.RECON.6 Existing Phase159 Contracts Lock Current "fill height contain" Behavior
Source: `tests/phase159/test_phase159_detached_video_fill_height_contract.py`

Current contract explicitly asserts detached mode keeps:
- `(isAnyFullscreen || currentWindowMode === "detached")`
- `{ width: "100%", height: "100%", display: "block", objectFit: "contain", background: "#000" }`

Impact:
- moving to QuickTime-fit requires contract update,
- otherwise tests will force current gap-producing geometry back.

## Root Cause Summary
The bottom empty dark space is not a single bug; it is an interaction of:
1. static detached window size (`960x680`) not tied to media dimensions,
2. detached renderer filling full container height with `contain` letterboxing,
3. explicit black backgrounds on wrapper/panel/player,
4. hardcoded gradient darkening at controls,
5. dark bottom toolbar row.

## Recommended Implementation Direction (for GO phase)
### Option A (QuickTime-like, preferred)
1. On `loadedmetadata`, read `videoWidth/videoHeight`.
2. Compute target content size preserving aspect ratio + fixed chrome budget (titlebar + toolbar).
3. Resize current Tauri window (`getCurrentWindow().setSize(...)`) with min/max clamps.
4. In detached mode, render video by intrinsic ratio (not forced `height:100%` fill policy).
5. Replace hard gradient with lighter/non-forced controls backdrop.
6. Update phase159 contracts to the new policy.

### Option B (minimal risk)
1. Keep static window size,
2. remove forced `height:100%` detached video rule,
3. reduce/disable bottom gradient,
4. keep footer toolbar as-is.

Option B will reduce visual pain but will not fully match QuickTime fit-to-media open behavior.

## Files To Touch In IMPL Phase
- `client/src/components/artifact/viewers/VideoArtifactPlayer.tsx`
- `client/src/components/artifact/ArtifactPanel.tsx`
- `client/src/config/tauri.ts` (window sizing helper)
- possibly `client/src-tauri/src/commands.rs` (opening defaults / optional initial sizing policy)
- phase159 tests listed above.

## Verification Checklist (post-impl)
1. Open 16:9, 4:3, portrait video files in detached window.
2. Confirm no large black dead zone below media in normal mode.
3. Confirm footer actions remain aligned and functional (⭐/VETKA/X).
4. Confirm fullscreen toggle still works and exits cleanly.
5. Confirm favorite/add-to-vetka endpoints still work in detached mode.
