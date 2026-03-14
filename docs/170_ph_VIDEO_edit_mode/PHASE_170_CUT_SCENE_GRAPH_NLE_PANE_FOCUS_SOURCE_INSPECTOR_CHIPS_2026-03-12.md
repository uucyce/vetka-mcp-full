# PHASE 170 CUT Scene Graph NLE Pane Focus Source + Inspector Chips (2026-03-12)

## Scope

Small loaded-state polish for the promoted NLE Scene Graph pane.

## Added signals

### MARKER_170.NLE_GRAPH.FOCUS_SOURCE
`Selection Summary` now surfaces a normalized `focus source` line:
- `timeline + storyboard crosslinks`
- `storyboard crosslinks`
- `scene graph anchor only`
- `none`

This keeps the graph selection provenance visible without reading the larger Selected Shot panel.

### MARKER_170.NLE_GRAPH.INSPECTOR_CHIPS
`Media Card` now renders compact inspector chips for linked inspector nodes.

Expected behaviors:
- if inspector nodes exist, render pills like `inspector Opening Scene`
- if none exist, render fallback `no inspector chips`

## Why this matters

The promoted Scene Graph pane is now dense enough to be useful on loaded state, but still needs low-noise provenance cues. `focus source` explains why the graph is highlighted, and inspector chips expose semantic links without forcing the user into the right-side inspector.
