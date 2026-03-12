# Phase 170 CUT Debug Worker Queue Recon

## Scope
Browser-only smoke for the Worker Queue card in CUT debug shell.

## Stable selectors
- View-mode toggle: `page.locator('button[title="Toggle NLE / Debug view"]')`
- Debug shell title: `page.getByText('VETKA CUT')`
- Queue card title: `page.getByText('Worker Queue')`
- Active count: `page.getByText(/active_jobs:\s*1/)`
- Recent count: `page.getByText(/recent_jobs:\s*1/)`
- Cancel action: `page.getByRole('button', { name: 'Cancel Job' })`
- Crash guard: `page.locator('text=MCC Runtime Error')`

## Readiness anchors
The queue lane is ready when all of these are visible:
- `Worker Queue`
- `active_jobs: 1`
- `recent_jobs: 1`
- one active job row such as `waveform_build` + `running · 42%`
- one recent job row such as `audio_sync` + `done · 100%`

## Expected status text
### Cancel Job
- transient from code path: `Cancelling job job_wavef...` (first 8 chars of job id)
- settled after refresh: status can return to the default project-state message path
- failure fallback: `Cancel failed`

## Post-cancel visible proof
After cancelling the active job, expect:
- `active_jobs: 0`
- `recent_jobs: 2`
- a recent job row with `cancelled · 42%`
