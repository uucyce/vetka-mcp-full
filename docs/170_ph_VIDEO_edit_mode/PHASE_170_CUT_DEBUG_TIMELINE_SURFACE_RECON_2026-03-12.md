# PHASE 170 — CUT Debug Timeline Surface Recon

## Scope
- Screen: `/cut` debug shell
- Card: `Timeline Surface`
- Related action: `Select First Clip`

## Stable anchors
- `VETKA CUT`
- `Timeline Surface`
- empty state: `Timeline not ready. Run scene assembly.`
- lane header: `<lane_id> / <lane_type>`
- clip rows:
  - clip id
  - filename from `source_path`
  - `start <n>s · duration <n>s`
- selection label: `timeline selected`
- action button: `Select First Clip`

## Hydration behavior
- when `runtime_ready` is false, the card stays on the empty-state message even if timeline lanes are absent
- once `runtime_ready` becomes true and `timeline_state.lanes[]` is populated, the card renders each lane and its clips
- the shell action `Select First Clip` posts to `/api/cut/timeline/apply`, then refreshes project-state

## Selection behavior
- the first click should target `timelineLanes[0].clips[0].clip_id`
- after the refresh, the matching clip row gets the `timeline selected` marker
- selection can be verified purely from refreshed `timeline_state.selection.clip_ids[]`; no direct DOM mutation is expected before refresh
