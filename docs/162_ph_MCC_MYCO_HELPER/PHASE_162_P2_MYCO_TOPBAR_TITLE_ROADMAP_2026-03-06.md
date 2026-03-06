# PHASE 162 — P2 MYCO Topbar + Title Roadmap (2026-03-06)

Status: `ROADMAP (approved)`
Protocol: `RECON -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`

## Scope lock (P2)
1. Add `MYCO` button (icon + label) in MCC top tab-row.
2. Click toggles helper mode: `off -> passive -> active`.
3. While MYCO replies, icon temporarily switches to animated state (`APNG` preferred).
4. Window title reduced to `MYCELIUM`.

## Markers (P2)
1. `MARKER_162.P2.MYCO.TOPROW_BUTTON.V1`
2. `MARKER_162.P2.MYCO.MODE_TOGGLE_TOPROW.V1`
3. `MARKER_162.P2.MYCO.AVATAR_RESPONSE_ANIM.V1`
4. `MARKER_162.P2.MYCO.WINDOW_TITLE_MYCELIUM.V1`
5. `MARKER_162.P2.MYCO.TOPROW_LAYOUT_GUARD.V1`
6. `MARKER_162.P2.MYCO.MINICHAT_AVATAR_BIND.V1`
7. `MARKER_162.P2.MYCO.TOP_HINT_BRIDGE.V1`

## Recon summary
1. MCC has no internal header bar in grandma mode; the best stable placement is current project tab-row.
2. Current chat MYCO mode chip is too small and should remain secondary, not primary control.
3. Native macOS titlebar currently uses standard decorations (`decorations: true`), so embedding a custom button inside native titlebar is out-of-scope for narrow P2.
4. Tauri window title is set in two places and both must be aligned:
- `client/src-tauri/tauri.conf.json`
- `client/src-tauri/src/main.rs`
5. Input icon assets are alpha PNG and suitable for compact render after resizing.
6. `ffmpeg` on workspace supports `apng`, `gif`, `webp`; P2 chooses `APNG` to keep alpha quality and implementation simple.

## Implementation plan (narrow)
1. Add compact MYCO assets under `client/src/assets/myco`:
- `myco_idle_question.png`
- `myco_ready_smile.png`
- `myco_speaking_loop.apng`
2. Emit event `mcc-myco-reply` from MiniChat when MYCO returns helper output.
3. Listen in `MyceliumCommandCenter` and drive short icon state machine:
- `idle -> speaking -> ready -> idle`
4. Render top-row MYCO button with icon + label + compact mode indicator.
5. Bind click to store mode rotation (`off/passive/active`).
6. Rename MCC window title to `MYCELIUM`.

## Verify checklist
1. Chat still works for architect and MYCO triggers.
2. MYCO top button toggles modes and reflects current state.
3. MYCO icon animates only on helper reply event.
4. MCC window title shows `MYCELIUM`.
5. No changes to DAG layout logic.

## P2.1 UX polish add-on
1. Move MYCO top-row button left to avoid overlap with debug toggle.
2. Make MYCO icon in MiniChat noticeably larger/readable.
3. Show `!` indicator while MYCO is answering (same visual semantics in top-row and chat).
4. Bridge selection/system hint into top MYCO area so helper is perceived as speaker.
5. Remove explicit `MYCO` text labels from visible UI controls (icon-first helper UX).
6. Place helper icon left of top hint bubble (speaker-avatar composition).

## P2.2 behavior lock (2026-03-06)
1. `off` mode: helper visible only in top row, pinned near center-left.
2. `passive/active` mode: helper icon hidden in top row and shown in chat header.
3. Top hint bubble width must be fixed to avoid jitter on hint text length changes.
4. Top-row helper anchor must not depend on right-side controls or debug elements.
5. Node/system hint in `off` mode must animate helper avatar (`? -> ! -> smile -> ?`).

## Markers (P2.2)
1. `MARKER_162.P2.MYCO.TOP_CENTER_ANCHOR.V1`
2. `MARKER_162.P2.MYCO.TOP_HINT_FIXED_WIDTH.V1`
3. `MARKER_162.P2.MYCO.CHAT_ONLY_WHEN_ENABLED.V1`
4. `MARKER_162.P2.MYCO.TOP_SYSTEM_HINT_PRIORITY.V1`
5. `MARKER_162.P2.MYCO.CHAT_MYCO_PLACEHOLDER_CONTEXT.V1`
6. `MARKER_162.P2.MYCO.CHAT_REDUCED_NOISE_WHEN_ACTIVE.V1`
7. `MARKER_162.P2.MYCO.DOCK_RESTORE_SPEAKING.V1`
8. `MARKER_162.P2.MYCO.CHAT_SINGLE_LEFT_ANCHOR.V1`
9. `MARKER_162.P2.MYCO.CHAT_BUBBLE_TAIL.V1`
10. `MARKER_162.P2.MYCO.WINDOW_TITLE_DOC_SYNC.V1`
