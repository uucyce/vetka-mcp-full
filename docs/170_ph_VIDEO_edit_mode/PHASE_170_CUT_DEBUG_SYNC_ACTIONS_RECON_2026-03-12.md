# Phase 170 CUT Debug Sync Actions Recon

## Scope
Browser-only smoke for sync actions exposed by the CUT debug shell. This lane verifies existing selected-shot and shell sync controls without editing shared CUT UI or backend code.

## Stable selectors
- View-mode toggle: `page.locator('button[title="Toggle NLE / Debug view"]')`
- Debug shell title: `page.getByText('VETKA CUT')`
- Selected-shot primary action: `page.getByRole('button', { name: 'Sync Timeline Selection' })`
- Selected-shot sync apply button: `page.getByRole('button', { name: 'Apply Sync Offset' })`
- Shell-wide sync apply button: `page.getByRole('button', { name: /Apply All Syncs \(1\)/ })`
- Crash guard: `page.locator('text=MCC Runtime Error')`

## Selected-shot readiness anchors
The sync-action lane is ready when the right panel shows all of these anchors:
- `clip_sync_a.mov` or the selected media filename
- `timeline link: clip_sync_a`
- `sync hint: 0.240s via peaks+correlation`
- `recommended sync: waveform 0.240s`

These anchors prove that:
- a storyboard item is selected
- the selected shot maps to a timeline clip
- an audio sync result is present
- a sync_surface recommendation exists

## Expected status text
### Sync Timeline Selection
- transient: `Syncing selected shot to timeline...`
- settled after refresh: `Runtime ready`

### Apply Selected Sync
Current tree label is `Apply Sync Offset`.
- transient: `Applying sync offset to timeline...`
- settled after refresh: `Runtime ready`
- failure fallback from code path: `Timeline sync apply failed`

### Apply All Syncs
- transient: `Applying 1 sync offset(s)...`
- settled success: `Applied 1 sync offset(s).`
- no-op guard: `No actionable sync recommendations.`
- mismatch guard: `No clips matched sync surface items in timeline.`
- failure fallback: `Batch sync apply failed`

## Markers
- `MARKER_170.NLE` in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/CutStandalone.tsx:1154`
- `MARKER_170.WAVE7.DEBUG_SYNC_ACTIONS` for future hand-off notes and smoke extensions
