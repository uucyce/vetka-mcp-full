# Phase 170 CUT Debug Sync Hints Recon

## Scope
Browser-only smoke for the `Sync Hints` card in CUT debug shell.

## Stable selectors
- View-mode toggle: `page.locator('button[title="Toggle NLE / Debug view"]')`
- Debug shell title: `page.getByText('VETKA CUT')`
- Card title: `page.getByText('Sync Hints')`
- Refresh action: `page.getByRole('button', { name: 'Refresh Project State' })`
- Crash guard: `page.locator('text=MCC Runtime Error')`

## Initial visible anchors
Useful first-pass anchors:
- `sync_surface items: 1`
- `timecode_sync results: 1`
- `audio_sync results: 1`
- `clip_tc.mov`
- `ref: master_tc.mov`
- `01:00:00:00`
- `peaks+correlation`
- `recommended: waveform`

## Refresh proof
After one refresh, expect changed sync hints such as:
- `sync_surface items: 2`
- `clip_tc_b.mov`
- `ref: master_tc_v2.mov`
- `02:00:00:00`
- `fft+peaks`
- `recommended: meta_sync`

The card should continue to render at least one `recommended: waveform` row if the refreshed payload still contains one waveform recommendation.

## Expected status text
### Refresh Project State
- transient may pass through `Hydrating project state...`
- settled status follows runtime readiness and can become `Project loaded` or `Runtime ready`
- failure fallback: `Project state error`
