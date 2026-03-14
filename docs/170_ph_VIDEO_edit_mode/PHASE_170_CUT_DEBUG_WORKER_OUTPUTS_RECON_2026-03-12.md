# PHASE 170 — CUT Debug Worker Outputs Recon

## Scope
- Screen: `/cut` debug shell
- Card: `Worker Outputs`

## Stable anchors
- `VETKA CUT`
- `Worker Outputs`
- count lines:
  - `waveforms: <n>`
  - `transcripts: <n>`
  - `thumbnails: <n>`
  - `timecode_sync: <n>`
  - `audio_sync: <n>`
  - `pause_slices: <n>`
  - `time_markers: <n>`

## Representative rows
The card renders up to three rows per bundle family:
- waveform row: `WF · <filename>` and readiness/degraded text
- transcript row: `TX · <filename>` and readiness/degraded text
- audio sync row: `SYNC · <filename>`, offset/conf line, method line
- timecode sync row: `TC · <filename>`, timecode line, offset/fps line

## Empty-state rule
`No worker bundles available.` appears only when waveform/transcript/thumbnail arrays are all empty.

## Refresh behavior
- initial `project-state` can expose a smaller worker-output set
- after `Refresh Project State`, the card should render updated counts and representative rows from the new payload
- the smoke should stay read-only: no worker mutation routes are required beyond a generic API success fallback
