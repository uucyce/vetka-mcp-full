# Phase 170 CUT Export Failure Smoke Recon

## Scope
Browser-only failure-path coverage for the existing export controls in the NLE transport bar. This smoke must not edit shared CUT UI files.

## Stable selectors
- Export format toggle: `page.getByTitle('Click to switch export format')`
- Export action button: `page.locator('button[title^="Export to "]')`
- NLE surface ready check: `page.getByText('Source Browser').first()`
- Crash guard: `page.locator('text=MCC Runtime Error')`

## Expected visible states
### Premiere default
- Toggle text starts as `PPro`.
- Export button title matches `Export to Premiere Pro XML`.
- Idle button text stays `📤`.
- Idle button color resolves to `rgb(204, 204, 204)`.

### FCP / DaVinci branch
- One toggle click switches text to `FCP/DR`.
- Export button title matches `Export to FCPXML (FCP/DaVinci)`.

## Failure-path expectations
- A failed export still posts to the route selected by the current toggle.
- Failure does not open any extra modal.
- Failure does not throw `MCC Runtime Error`.
- Failure changes the export button color to `rgb(239, 68, 68)`.
- The icon stays `📤`; the visual error cue is color, not a new label.
- The transport resets back to the idle color after roughly 3 seconds.

## Timing notes
- Use `expect.poll()` against computed color instead of fixed sleeps where possible.
- Give the reset check up to 4.5 seconds to tolerate dev-server jitter.
- Immediate red state should appear without waiting for the full reset window.

## Markers
- `MARKER_170.NLE.EXPORT_UI` in `TransportBar.tsx` defines the source behavior under test.
- `MARKER_170.WAVE6.EXPORT_FAILURE_SMOKE` should be referenced in hand-off notes when this smoke is extended.
