# Phase 170 CUT Debug Worker Smoke Recon

## Scope
Browser-only smoke for the legacy debug shell embedded inside CUT. This lane proves that the shell can bootstrap a project, start async jobs, and surface state transitions without touching backend or shared NLE UI implementation.

## Entry path
1. Open `/cut`.
2. Wait for the default NLE surface (`Source Browser`).
3. Click the transport button with title `Toggle NLE / Debug view`.
4. Expect the debug shell title `VETKA CUT`.

## Stable selectors
- View-mode toggle: `page.locator('button[title="Toggle NLE / Debug view"]')`
- Bootstrap button: `page.getByRole('button', { name: 'Open CUT Project' })`
- Scene assembly button: `page.getByRole('button', { name: 'Start Scene Assembly' })`
- Waveform worker button: `page.getByRole('button', { name: 'Build Waveforms' })`
- Audio sync worker button: `page.getByRole('button', { name: 'Build Audio Sync' })`
- Status card text: raw text assertions such as `Project loaded`, `Running scene assembly...`, `Runtime ready`
- Runtime flag checks: `page.getByText('runtime_ready: true')`
- Crash guard: `page.locator('text=MCC Runtime Error')`

## Expected transitions
### Bootstrap
- Initial shell status: `Idle`
- After clicking `Open CUT Project`: status passes through `Bootstrapping CUT project...`
- On successful refresh: status settles on `Project loaded`
- Project id becomes visible in the status card

### Scene assembly
- Click `Start Scene Assembly`
- Status shows `Running scene assembly...`
- After job completion and refresh: status settles on `Runtime ready`
- Timeline surface no longer says `Run scene assembly.`
- One timeline lane and one scene node are enough for smoke

### Worker actions
- `Build Waveforms` should transiently show `Building waveform bundle...`
- `Build Audio Sync` should transiently show `Building audio sync offsets...`
- Worker Outputs should reflect `waveforms: 1` and `audio_sync: 1` after refresh

## Minimal visible proof after workers
- `video_main / video_main`
- `Scene Debug A`
- `waveforms: 1`
- `audio_sync: 1`
- `SYNC · clip_debug_a.mov`

## Markers
- `MARKER_170.NLE` in `CutStandalone.tsx` defines that the debug shell is wrapped by the NLE layout
- `MARKER_170.WAVE6.DEBUG_WORKER_SMOKE` should be used in hand-off notes for this lane
