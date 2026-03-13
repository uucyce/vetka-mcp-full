# Phase 171 Punch Track Music Cue Contract

## Scope

Task:
- `tb_1773372827_5`

## Purpose

Promote the Berlin Punch track from bootstrap metadata into a formal montage-input contract.

## Contract

- schema: `cut_music_sync_result_v1`
- file: `docs/contracts/cut_music_sync_result_v1.schema.json`

## Why a separate contract exists

`cut_audio_sync_result_v1` is for clip/reference alignment.

`cut_music_sync_result_v1` is for editorial timing structure:
- beat and downbeat positions
- phrase windows
- cue points with labels and confidence
- tempo estimate

This keeps technical sync and montage timing separate.

## Required fields

- `project_id`
- `revision`
- `music_path`
- `tempo`
- `downbeats[]`
- `phrases[]`
- `cue_points[]`
- `derived_from`
- `generated_at`

## Montage-engine value

The montage engine can now consume Punch as a first-class cue source without reading raw marker bundles or overloading sync offsets.

## Validation note

Focused music tests now cover:
- schema parseability
- store round-trip for `cut_music_sync_result_v1`
- Berlin project-state cue summary derived from this contract
