# PHASE 170 — CUT Scene Graph NLE Pane Sync Badge Polish

## Goal
Make sync status more legible inside the compact NLE Scene Graph card without making the pane noisy.

## Rules
- Render sync badge as a compact pill when `selectedShotPrimaryGraphCard.syncBadge` exists.
- Keep bucket text secondary beside the badge.
- Fallback remains `no sync badge`.

## Visible Signals
- sync pill with green emphasis when available
- fallback copy: `no sync badge`
- secondary text: `bucket ...`
