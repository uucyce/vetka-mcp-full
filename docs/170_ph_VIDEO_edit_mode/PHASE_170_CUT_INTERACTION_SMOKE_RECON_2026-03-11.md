# Phase 170 CUT Interaction Smoke Recon

## Scope
- Target file: `client/e2e/cut_nle_interactions_smoke.spec.cjs`
- Surface: default CUT NLE view on `/cut` with mocked `project-state`
- Goal: prove timeline clips render, clip context menu opens, marker draft opens on double click, and marker hotkeys do not crash the page

## Stable selectors
| Surface | Selector | Expected state |
| --- | --- | --- |
| NLE root | `[data-testid="cut-editor-layout"]` | Visible after `/cut` hydration |
| Transport bar | `[data-testid="cut-transport-bar"]` | Visible in both NLE and debug wrapper |
| Source browser | `[data-testid="cut-source-browser"]` | Visible once media items exist |
| Timeline root | `[data-testid="cut-timeline-track-view"]` | Visible after `runtime_ready: true` |
| Ruler | `[data-testid="cut-timeline-ruler"]` | Visible and accepts double click for marker draft |
| Lane body | `[data-testid="cut-timeline-lane-video_main"]` | Visible when mocked lane exists |
| Clip A | `[data-testid="cut-timeline-clip-clip_a"]` | Visible clip block for right click / select |
| Clip B | `[data-testid="cut-timeline-clip-clip_b"]` | Visible second clip block proving row render |
| Clip context menu | `[data-testid="cut-clip-context-menu"]` | Visible after right click on a clip |
| Context action | `button:has-text("Set as Active")` | Visible inside clip context menu |
| Context action | `button:has-text("Add Marker Here")` | Visible inside clip context menu |
| Context action | `button:has-text("Apply Sync")` | Enabled when mocked `sync_surface` has recommendation |
| Marker draft | `[data-testid="cut-marker-draft"]` | Visible after ruler double click |
| Marker create CTA | `[data-testid="cut-marker-draft-create"]` | Clickable after draft opens |
| Marker text input | `input[placeholder="marker text"]` | Editable when draft is open |
| Rendered comment marker | `[title^="comment: smoke marker"]` | Two nodes after create: ruler marker + lane marker |
| Rendered favorite marker | `[title^="favorite:"]` | Two nodes after `KeyM`: ruler marker + lane marker |

## Expected interaction states
1. Navigation to `/cut?sandbox_root=...&project_id=...` should hydrate directly into NLE, not legacy shell.
2. `project-state` with `runtime_ready: true` and one `video_main` lane should render visible clip blocks.
3. Right click on a clip should open the clip context menu without dragging or crashing.
4. Double click on the ruler over a clip time should open marker draft UI bound to that clip media.
5. Creating a marker should survive refresh and render new marker chrome in both ruler and lane overlay.
6. Pressing `m` after selecting a clip should hit the hotkey marker path and leave `localStorage.vetka_last_runtime_error` empty.

## Notes
- The marker draft resolves media path from clip coverage at the clicked timeline time. The smoke click therefore must land inside an existing clip window.
- `Apply Sync` depends only on mocked `sync_surface.items[].recommended_method`; no timeline mutation is required unless the smoke starts clicking the action.
