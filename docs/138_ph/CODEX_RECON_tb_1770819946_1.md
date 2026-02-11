# MARKER_138.RECON_MCC_STATS_NORMALIZE
# Recon Report: tb_1770819946_1 (MCC STATS normalize)

Date: 2026-02-11
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Task
MCC STATS normalization:
1. Normalize bar heights to dataset max (not fixed 100)
2. Token breakdown: switch from vertical bars to horizontal area-style charts
3. BY PRESET bars: proportional to each other
4. Add hover tooltips with exact numbers

## Findings
1. Stats UI entry is in `DevPanel.tsx`, but rendering logic is in `PipelineStats.tsx`.
- `DevPanel.tsx` only mounts `<PipelineStats tasks={tasks} />`
- Actual bars/charts are implemented in `client/src/components/panels/PipelineStats.tsx`

2. Current charting state:
- Top Recharts bar chart uses success %, no explicit dynamic Y-domain.
- BY PRESET includes LLM/tokens bars with normalization by max values.
- Token breakdown row is currently plain text (`in/out/ratio`), not area visualization.
- Hover tooltips exist only in Recharts chart, not for custom preset bars.

## Planned implementation
1. `PipelineStats.tsx`
- Add dynamic Y-domain normalization for success chart based on dataset max.
- Replace token breakdown text row with horizontal area-style mini chart (In/Out series).
- Keep BY PRESET bars normalized against dataset max and make normalization explicit.
- Add hover tooltips (`title`) with exact values on preset bars and token area points.
- Add marker: `MARKER_138.MCC_STATS_NORMALIZE`.

2. `DevPanel.tsx`
- Add marker near Stats tab mount to reflect task ownership trace.

## Scope
Frontend only, isolated to Stats components.
