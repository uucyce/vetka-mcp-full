# PHASE 170 — CUT Scene Graph NLE Pane Poster Preview

## Goal
Use available poster data to make the compact NLE Scene Graph card more media-native without overwhelming the editor.

## Rules
- If `selectedShotPrimaryGraphCard.posterUrl` exists, render it as a compact preview.
- If poster data is missing, show a neutral fallback block with `no poster preview`.
- Keep the preview subordinate to the DAG viewport and summary text.

## Visible Signals
- compact poster image when available
- fallback copy: `no poster preview`
