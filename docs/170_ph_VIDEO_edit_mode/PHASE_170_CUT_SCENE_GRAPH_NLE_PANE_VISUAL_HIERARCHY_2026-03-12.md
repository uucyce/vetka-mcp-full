# PHASE 170 — CUT Scene Graph NLE Pane Visual Hierarchy

## Goal
Make the NLE Scene Graph pane readable by enforcing a clear order of attention.

## Order
1. `Viewport Priority` — DAG is first
2. `Selection Summary` — linked context second
3. `Media Card` — compact media-native summary third
4. `Actions` — explicit controls last

## Rule
The pane should read top-down without mixing summaries and controls around the viewport.
