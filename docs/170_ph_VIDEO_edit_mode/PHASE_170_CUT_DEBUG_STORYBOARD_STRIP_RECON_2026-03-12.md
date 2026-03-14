# PHASE 170 — CUT Debug Storyboard Strip Recon

## Scope
- Screen: `/cut` debug shell
- Card: `Storyboard Strip`
- Dependency: `thumbnail_bundle.items[]` drives both the strip itself and the `Selected Shot` panel

## Stable anchors
- `VETKA CUT`
- `Storyboard Strip`
- empty state: `No thumbnails yet. Run thumbnail build.`
- thumbnail filename rows, e.g. `clip_story_a.mov`, `clip_story_b.mov`
- action buttons per card:
  - `Select Shot`
  - `Favorite Moment`
  - `Comment Marker`
  - `CAM Marker`
  - `Open Preview`

## Visual fields per card
Each storyboard card can render:
- poster image when `poster_url` exists, otherwise a placeholder block
- filename from `source_path`
- modality label
- optional sync badge from `sync_surface.items[]` matching the same `source_path`
- `marker window <start>s - <end>s` derived from slice, transcript, or preview fallback

## Selection behavior
- when `thumbnail_bundle.items[]` is empty, `Selected Shot` shows `No storyboard item selected.`
- once thumbnails appear, the first item is auto-selected if no explicit selection exists
- clicking the second `Select Shot` button should switch the right panel to that thumbnail and update its marker window / sync hints

## Refresh behavior
- initial `GET /api/cut/project-state` can return no thumbnails
- after `Refresh Project State`, the next `project-state` response should hydrate thumbnail cards and a selected-shot panel
- a changed thumbnail payload should update card content and the selected-shot panel without runtime errors
