# Phase 170 CUT Debug Marker Actions Recon

## Scope
Browser-only smoke for selected-shot marker actions in the CUT debug shell. This lane covers existing marker-create and visibility-toggle flows without editing shared CUT UI or backend code.

## Stable selectors
- View-mode toggle: `page.locator('button[title="Toggle NLE / Debug view"]')`
- Debug shell title: `page.getByText('VETKA CUT')`
- Selected-shot marker buttons:
  - `page.getByRole('button', { name: 'Favorite Selected' })`
  - `page.getByRole('button', { name: 'Comment Selected' })`
  - `page.getByRole('button', { name: 'CAM Selected' })`
- Marker visibility toggle:
  - active-only default: `page.getByRole('button', { name: 'Show All Markers' })`
  - expanded state: `page.getByRole('button', { name: 'Show Active Only' })`
- Crash guard: `page.locator('text=MCC Runtime Error')`

## Selected-shot readiness anchors
The marker-action lane is ready when the selected-shot panel shows:
- `clip_marker_a.mov` or the selected media filename
- `markers for shot: 1` in active-only mode
- `Favorite Markers` visible
- `Comment Markers` hidden before archived markers are unmasked

## Expected status text
### Favorite Selected
- transient: `Creating favorite moment...`
- failure fallback: `Time marker apply failed`

### Comment Selected
- prompt title from `window.prompt`: `Comment marker text`
- transient: `Creating comment marker...`
- failure fallback: `Time marker apply failed`

### CAM Selected
- prompt title from `window.prompt`: `CAM marker hint`
- transient: `Creating CAM marker...`
- failure fallback: `Time marker apply failed`

## Toggle expectations
### Show All Markers
- button text flips to `Show Active Only`
- archived marker sections such as `Comment Markers` become visible
- selected-shot count can increase because archived markers are included

### Show Active Only
- button text flips back to `Show All Markers`
- archived-only marker sections disappear again

## Post-create visible proof
After creating favorite + comment + cam markers in active-only mode, expect:
- `markers for shot: 4`
- `Favorite Markers`
- `Comment Markers`
- `CAM Markers`
- `cam markers: 1`
- `status: context-linked markers detected`
