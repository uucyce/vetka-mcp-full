# Phase 170 CUT Debug Marker Archive and Focus Recon

## Scope
Browser-only smoke for focus and archive flows already exposed by CUT debug-shell marker cards.

## Stable selectors
- View-mode toggle: `page.locator('button[title="Toggle NLE / Debug view"]')`
- Debug shell title: `page.getByText('VETKA CUT')`
- Selected-shot focus action: `page.getByRole('button', { name: 'Focus Marker In Timeline' }).first()`
- Global visibility toggle:
  - active-only default: `page.getByRole('button', { name: 'Show All Global Markers' })`
  - expanded state: `page.getByRole('button', { name: 'Show Active Global Only' })`
- Global archive action: `page.getByRole('button', { name: 'Archive Marker' }).first()`
- Crash guard: `page.locator('text=MCC Runtime Error')`

## Readiness anchors
The lane is ready when these anchors are visible:
- selected-shot count: `markers for shot: 2`
- global count in active-only mode: `markers: 2`
- one selected-shot marker section such as `Favorite Markers`
- `Comment Markers` absent before global archived markers are unmasked

## Expected status text
### Focus Marker In Timeline
- transient: `Focusing marker in timeline...`
- settled after refresh: `Runtime ready`
- failure fallback: `Timeline marker focus failed`

### Archive Marker
- transient: `Archiving marker...`
- settled after refresh: `Runtime ready`
- failure fallback: `Time marker archive failed`

## Visibility toggle expectations
### Show All Global Markers
- button text flips to `Show Active Global Only`
- archived sections such as `Comment Markers` become visible
- global count increases to include archived markers

### Show Active Global Only
- button text flips back to `Show All Global Markers`
- archived-only sections disappear again
- global count drops back to active markers only
