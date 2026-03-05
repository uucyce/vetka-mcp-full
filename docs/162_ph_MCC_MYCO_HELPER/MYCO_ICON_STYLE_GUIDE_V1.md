# MYCO Icon Style Guide V1

Status: `P0 CONTRACT`
Date: `2026-03-06`

Marker: `MARKER_162.MYCO.UI_ICON_BIND.V1`

## Direction
1. Minimalist mushroom helper (MYCO) in MCC style.
2. White/gray only, no red.
3. Readable at 16px/20px/24px.

## Asset requirements
1. Primary: `SVG` (vector, stroke-based).
2. Tauri fallback: `PNG` @1x/@2x.
3. Transparent background.

## Visual constraints
1. No photorealistic/3D asset in main UI.
2. No emoji-like multicolor palette.
3. Rounded geometry consistent with mini-window language.

## States
1. `idle`
2. `active`
3. `listening`

## Placement
1. Helper toggle in existing action surface only (no permanent extra floating panel).
2. Optional tiny badge near chat header when helper mode != off.
