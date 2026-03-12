# PHASE 170 CUT Scene Graph Node Click Loaded Smoke (2026-03-12)

## Scope

Extend the loaded-state Scene Graph browser smoke so it proves the graph is not just rendered, but also interactive inside the promoted NLE pane.

## What is verified

### MARKER_170.NODE_CLICK.SMOKE.TIMELINE_ROUNDTRIP
Clicking a visible DAG node in the loaded fixture must trigger `/api/cut/timeline/apply`.

### MARKER_170.NODE_CLICK.SMOKE.FOCUS_SOURCE
After the click, the NLE Scene Graph pane should still show a coherent provenance line:
- `focus source: timeline + storyboard crosslinks`

### MARKER_170.NODE_CLICK.SMOKE.INSPECTOR_LINK
After the click, the pane should still expose linked semantic inspector text:
- `pane inspector link: Opening Scene · Take A`

## Why this matters

This is the first browser check that proves the promoted Scene Graph pane behaves as a control surface, not just a rendered DAG snapshot.
