# CODEX RECON — Artifact Panel UX Audit (Pin + Actions)

Date: 2026-03-03  
Protocol stage: RECON + REPORT (no implementation)

## Scope
- Artifact bottom toolbar behavior and visual states.
- New `pin` icon requirement (active only when chat is open).
- Full audit of artifact actions (functional + UX feedback).

## MARKER_159.RECON.1_SURFACE_MAP
Active implementation path (main app):
- `client/src/components/artifact/Toolbar.tsx`
- `client/src/components/artifact/ArtifactPanel.tsx`
- `client/src/components/artifact/ArtifactWindow.tsx`
- `client/src/App.tsx`

State source for chat open already exists:
- `isChatOpen` in `client/src/App.tsx:236`
- `ChatPanel` receives it in `client/src/App.tsx:865-870`
- `ArtifactWindow` currently does **not** receive it (`client/src/App.tsx:871-882`)

## MARKER_159.RECON.2_PIN_GAP
Finding:
- In active artifact toolbar there is no `pin` button at all (`client/src/components/artifact/Toolbar.tsx:114-156`).

Impact:
- Requirement "pin from artifact into chat context" is currently impossible from this panel.

Required integration path:
1. Pass `isChatOpen` from `App` -> `ArtifactWindow` -> `ArtifactPanel` -> `Toolbar`.
2. Add `onPin` action in toolbar props.
3. In `ArtifactPanel`, resolve current artifact path to node id and call `togglePinFile` from store.
4. Disable or hide pin when chat is closed.

## MARKER_159.RECON.3_CHAT_GATING
Finding:
- Chat visibility exists only in `App` local state (`client/src/App.tsx:236`), not in global store.
- Artifact layer has no awareness of chat state.

Risk:
- Without explicit prop wiring, pin button cannot follow "active only when chat open" rule.

## MARKER_159.RECON.4_COPY_FEEDBACK
Finding:
- Copy handlers in artifact panel do clipboard write only:
  - `handleCopy` (`client/src/components/artifact/ArtifactPanel.tsx:599`)
  - `handleCopyRaw` (`client/src/components/artifact/ArtifactPanel.tsx:1069`)
- No visual reaction state (`copied`, checkmark, temporary highlight, toast).

Why user sees "nothing happened":
- Action is asynchronous and silent; UI color/icon never changes.

Reference pattern available:
- `ChatPanel` already implements copied feedback with timers (`copyGroupId`, `copyChatId` around `client/src/components/chat/ChatPanel.tsx:2017-2029`).

## MARKER_159.RECON.5_ACTIVE_ICON_COLOR_NON_BRAND
Finding:
- Toolbar active/accent states are hardcoded blue:
  - icon accent `#60a5fa` (`client/src/components/artifact/Toolbar.tsx:95`)
  - active background `#3b82f6` (`client/src/components/artifact/Toolbar.tsx:96`)
- This produces the blue "lit" edit state user reported.

Required visual behavior:
- Triggered icon should become brighter white (or neutral brand monochrome), not blue fill background.
- Same rule must apply consistently to all invoked actions.

## MARKER_159.RECON.6_ACTION_AUDIT_MATRIX
Audit of artifact actions (current state):

- `Edit`
  - Wiring: works (`ArtifactPanel` passes `onEdit`, `Toolbar` renders).
  - UX issue: active state uses blue background (`Toolbar.tsx:96`).
- `Undo`
  - Wiring: works only in edit mode.
  - UX issue: no invoked-feedback pulse, only static icon.
- `Save`
  - Wiring: works for file mode; raw mode only when `rawHasChanges`.
  - UX issue: no success confirmation; only spinner while saving.
- `Save As`
  - Wiring: works.
  - UX issue: uses `prompt(...)` modal (`ArtifactPanel.tsx:1103`), no post-action confirmation.
- `Copy`
  - Wiring: works functionally.
  - UX bug: no user-visible reaction (main complaint).
- `Download`
  - Wiring: works.
  - UX issue: no reaction on click/success.
- `Open in Finder`
  - Wiring: works (file mode only).
  - UX issue: silent success/failure (errors only in console).
- `Refresh`
  - File mode: wired to reload (`ArtifactPanel.tsx:1422`).
  - Raw mode: explicitly no-op (`ArtifactPanel.tsx:1167`) -> misleading clickable icon.
- `Close`
  - Works.

## MARKER_159.RECON.7_SECONDARY_CODEPATH_DRIFT
Finding:
- There is a second toolbar implementation in `app/artifact-panel/src/components/Toolbar.tsx`.
- It has different styles/behavior and can drift from the main client behavior.

Risk:
- If both UIs are used in product workflows, visual/interaction consistency breaks.

## MARKER_159.RECON.8_IMPLEMENTATION_READY_PLAN
Implementation-ready sequence (after GO):
1. Add chat-open prop plumbing from `App` to artifact toolbar stack.
2. Add `Pin` button to toolbar:
   - enabled when `isChatOpen === true` and artifact maps to a file node,
   - dimmed or hidden when chat closed.
3. Add per-action visual feedback state in toolbar (`copy`, `download`, `openInFinder`, `save`, `refresh`, `pin`):
   - temporary bright white icon state for 800-1500ms after trigger,
   - optional checkmark swap for copy/pin.
4. Remove blue active styling and replace with neutral brand style token (white/gray contrast only).
5. Fix raw-mode refresh behavior:
   - either real refresh action, or hide/disable with explicit tooltip.
6. Add minimal QA checklist for both modes (file/raw) and both chat states (open/closed).

## Conclusion
Requested behavior is not implemented yet, and current UX issues are reproducible from code:
- no pin action in artifact toolbar,
- no chat-state gating in artifact stack,
- missing click feedback (especially copy),
- non-brand blue active states,
- raw refresh no-op.

Recon complete, ready for implementation phase on approval.
