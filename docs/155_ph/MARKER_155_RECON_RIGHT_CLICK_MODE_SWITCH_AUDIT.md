# MARKER_155_RECON_RIGHT_CLICK_MODE_SWITCH_AUDIT

Date: 2026-02-19
Scope: right-click on folder -> context menu -> mode switch (Directed/Knowledge)

## Summary
Root cause confirmed: right-click flow was only reliable on `mesh`, but user interaction on folders mostly happens on folder `Html` label. The label had no `onContextMenu`, so event never reached `vetka-node-context-menu` dispatcher.

Result: user right-clicked folder label, nothing happened, even though menu system in `App.tsx` was implemented.

---

## Findings

### MARKER_155.RECON.RCLICK.PIPELINE_OK
`App.tsx` context-menu pipeline is present and logically correct:
- listens `vetka-node-context-menu`
- stores menu state
- renders menu with Directed/Knowledge actions
- dispatches `vetka-switch-tree-mode`

Refs:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx:662`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx:687`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx:1008`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx:1033`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx:1059`

### MARKER_155.RECON.RCLICK.MESH_ONLY_GAP
Dispatch exists on FileCard mesh (`handleContextMenu` + right button in `handlePointerDown`), but that does not cover folder label DOM overlay.

Refs:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx:919`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx:944`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx:1164`

### MARKER_155.RECON.RCLICK.LABEL_INTERCEPT_ROOT_CAUSE
Folder label is rendered as `<Html>` with `pointerEvents: 'auto'`, and had only `onClick` (zoom), no `onContextMenu`.

This overlay captures pointer interactions over folder label area, so right-click did not dispatch menu event.

Refs:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx:1486`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx:1490`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx:1507`

### MARKER_155.RECON.RCLICK.TDZ_FIXED
Prior TDZ bug (use before init) in `FileCard` callbacks has been fixed: `handleContextMenu` now declared before `handlePointerDown`.

Refs:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx:919`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx:944`

### MARKER_155.RECON.RCLICK.DUPLICATION_NOTE
There is still duplicated open-path on mesh:
- `onContextMenu={handleContextMenu}`
- right-button branch in `handlePointerDown` calling `handleContextMenu`

Not a blocker, but can cause redundant dispatches depending on browser/event order.

Ref:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx:944`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx:1164`

---

## Applied fix

### MARKER_155.FIX.RCLICK.LABEL_CONTEXT
Added folder-label right-click handling:
- `onContextMenu` on label `<div>` now calls `handleContextMenu`
- `onMouseDown` consumes right-button to avoid OrbitControls right-rotate stealing UX

Refs:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx:1497`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx:1500`

---

## Dead code / logic risk audit notes

### MARKER_155.AUDIT.MINOR.CLOSE_LISTENER
Global `window.click` closes menu (`App.tsx`). Container has `stopPropagation`, so menu click is safe. No bug found.

Ref:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx:683`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx:1023`

### MARKER_155.AUDIT.MINOR.TYPE_GUARD
Menu actions disabled for non-folder nodes (`nodeType !== 'folder'`). Correct behavior.

Ref:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx:1034`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx:1060`

---

## Validation checklist
- Right-click on folder **label** opens context menu.
- Right-click on folder **card mesh** opens context menu.
- Click outside closes menu.
- Directed/Knowledge menu items enabled for folder and disabled for file/chat/artifact.
- Selecting mode dispatches `vetka-switch-tree-mode` with `scopePath`.

