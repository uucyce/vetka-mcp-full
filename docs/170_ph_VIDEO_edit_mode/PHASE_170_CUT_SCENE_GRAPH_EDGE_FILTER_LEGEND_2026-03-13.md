# PHASE 170 CUT Scene Graph Edge Filter Legend (2026-03-13)

## Scope

Add a compact live legend beside the Scene Graph edge filter controls in the promoted NLE pane.

## Added signal

### MARKER_170.NLE_GRAPH.EDGE_LEGEND
The NLE graph pane now shows:
- current visible node count
- current visible edge count
- total structural edge count
- total overlay edge count

Format:
- `edge legend: nodes X · edges Y · structural S · overlay O`

## Why this matters

The filter controls are more trustworthy when the pane immediately reports what changed. This is a low-cost product signal that makes the graph pane feel operational rather than decorative.
