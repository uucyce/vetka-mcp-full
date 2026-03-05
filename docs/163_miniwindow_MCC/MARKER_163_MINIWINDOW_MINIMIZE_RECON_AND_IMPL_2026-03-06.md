# MARKER_163 - MCC MiniWindow Minimize + Dock (Recon + Implementation)

Date: 2026-03-06
Scope: MCC frontend (`client/src/components/mcc/*`)

## Request
Add minimal monochrome `-` minimize control for MCC mini-windows.
When minimized, window should move into a bottom dock-style preview strip (Mac-like idea):
- title visible,
- restore control,
- expand control,
- restore returns the same window instance (position/size persistence already exists).

## Recon

### Existing behavior before patch
- Mini-window framework located in:
  - `client/src/components/mcc/MiniWindow.tsx`
- States existed:
  - compact (draggable + resizable)
  - expanded (overlay dialog)
- Missing state:
  - minimized/docked preview
- Position/size persistence already implemented via localStorage:
  - `miniwindow_pos_v*`
  - `miniwindow_size_v*`
- Existing event bus already available:
  - `mcc-miniwindow-open` (used e.g. by MiniChat opening MiniContext)

### Integration point
- Mini-windows are mounted from:
  - `client/src/components/mcc/MyceliumCommandCenter.tsx`
- Best low-risk insertion for dock:
  - same DAG canvas layer where mini-windows are rendered.

## Implementation

### MARKER_163.MCC.MINIWINDOW_MINIMIZE_STATE.V1
Updated `MiniWindow` with explicit minimized state:
- Added internal state: `minimized`
- Added `minimize()` action:
  - collapses expanded mode
  - hides compact card
  - registers window in shared dock registry

### MARKER_163.MCC.MINIWINDOW_DOCK.V1
Added shared dock mechanism in `MiniWindow.tsx`:
- Module-level registry for minimized windows (`windowId/title/icon`)
- Broadcast updates via custom event:
  - `mcc-miniwindow-dock-updated`
- New exported component:
  - `MiniWindowDock`
- Dock UI behavior:
  - bottom centered strip
  - each item shows icon + title
  - `↗` button: restore to compact
  - `⤢` button: restore directly to expanded

### MARKER_163.MCC.MINIWINDOW_OPEN_EVENT_UNMINIMIZE.V1
Preserved compatibility with existing open event bus:
- `mcc-miniwindow-open` now also unminimizes the target window before applying expanded/compact state.

### MARKER_163.MCC.MINIWINDOW_HEADER_CONTROLS.V1
Header controls updated in both compact and expanded modes:
- Added `-` minimize button
- Existing expand/collapse controls kept

### MARKER_163.MCC.DOCK_MOUNT.V1
Mounted dock in MCC runtime:
- `client/src/components/mcc/MyceliumCommandCenter.tsx`
- Added `<MiniWindowDock />` in mini-window render block (non-first-run modes).

## Files changed
- `client/src/components/mcc/MiniWindow.tsx`
- `client/src/components/mcc/MyceliumCommandCenter.tsx`
- `docs/163_miniwindow_MCC/MARKER_163_MINIWINDOW_MINIMIZE_RECON_AND_IMPL_2026-03-06.md`

## Validation notes
- Ran: `npm --prefix client run build`
- Result: build fails due large pre-existing TypeScript issues unrelated to this task.
- New feature-level validation to perform in UI:
  1. Open MCC, click `-` on each mini-window -> card disappears, appears in dock.
  2. Dock `↗` restores compact draggable card at prior position.
  3. Dock `⤢` restores expanded overlay.
  4. Existing event-driven open actions (e.g. from MiniChat to MiniContext) unminimize correctly.

## Risk assessment
- Low runtime risk: change is localized to mini-window shell + MCC mount.
- Medium visual overlap risk: bottom-centered dock may overlap footer hints in some states; can be tuned with `bottom` offset if needed.
