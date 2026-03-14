# PHASE 170 — CUT Debug CAM Ready Recon

## Scope
- Screen: `/cut` debug shell
- Card: `CAM Ready`
- Dependency: selected shot hydrates from the first `thumbnail_bundle.items[]` entry when no explicit selection exists

## Stable anchors
- `VETKA CUT`
- `Selected Shot`
- selected media filename, e.g. `clip_cam.mov`
- `CAM Ready`
- `cam markers: 0` / `cam markers: 1`
- `status: waiting for CAM payloads`
- `status: context-linked markers detected`
- `next: attach \`cam_payload\` and contextual hints for this shot`

## Representative hydrated row
Each visible CAM row in the card is rendered from `selectedShotCamMarkers.slice(0, 3)` and shows:
- time span: `<start_sec>s - <end_sec>s`
- payload line: `source: <source> · status: <status>`
- hint line: `cam_payload.hint` fallbacking to marker text

## Refresh behavior
- initial `GET /api/cut/project-state` can return no CAM markers for the selected shot
- after `Refresh Project State`, the next `project-state` response should include an active `cam` marker with matching `media_path`
- the card should switch from waiting state to hydrated state without runtime errors
