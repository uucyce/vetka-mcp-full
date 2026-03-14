# Phase 170 CUT Debug Runtime Flags Recon

## Scope
Browser-only smoke for `Project Overview` and `Runtime Flags` cards in CUT debug shell.

## Stable selectors
- View-mode toggle: `page.locator('button[title="Toggle NLE / Debug view"]')`
- Debug shell title: `page.getByText('VETKA CUT')`
- Project Overview anchor: `page.getByText('Project Overview')`
- Runtime Flags anchor: `page.getByText('Runtime Flags')`
- Refresh action: `page.getByRole('button', { name: 'Refresh Project State' })`
- Crash guard: `page.locator('text=MCC Runtime Error')`

## Initial visible anchors
Useful first-pass anchors:
- `CUT Runtime Flags Smoke`
- `/tmp/cut/runtime_flags_source.mov`
- `runtime_ready: false`
- `graph_ready: true`
- `waveform_ready: false`
- `audio_sync_ready: true`
- `time_markers_ready: true`

## Refresh proof
After one refresh, expect changed overview + flags such as:
- `CUT Runtime Flags Smoke v2`
- `/tmp/cut/runtime_flags_source_v2.mov`
- `runtime_ready: true`
- `waveform_ready: true`
- `transcript_ready: false`
- `slice_ready: true`
- `sync_surface_ready: true`
- `meta_sync_ready: true`
- `time_markers_ready: false`

## Expected status text
### Refresh Project State
- transient may pass through `Hydrating project state...`
- settled status follows runtime readiness and can become `Project loaded` or `Runtime ready`
- failure fallback: `Project state error`
