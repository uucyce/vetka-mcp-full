# Phase 171 Multi-Track Sync Alignment Recon

## Scope

Task:
- `tb_1773372827_7`

## Alignment hierarchy

For montage-engine use, sync sources must be ranked rather than blended blindly.

### 1. Hard sync
- timecode
- shared production audio

These sources define structural alignment.

### 2. Soft sync
- meta sync
- semantic grouping
- inferred shot relationships

These sources can fill gaps but must not silently override hard sync.

### 3. Editorial timing
- music cues
- pause slices
- transcript accents

These sources shape montage decisions after alignment is already established.

## Berlin implication

Punch is editorial timing, not master sync.

That means:
- use `timecode_sync_result` and `audio_sync_result` to place clips
- use `music_sync_result` to choose where cuts and accents belong
- keep provenance separate so montage decisions can explain whether they came from hard sync or editorial timing

## Recommended grouping model

- alignment groups: clips that already agree on hard sync
- cue overlays: music/transcript/pause hints layered onto those groups
- promotion candidates: ranked montage decisions produced from aligned groups plus overlay cues

## Rule

Hard sync wins over meta sync.
Editorial timing enriches decisions after that hierarchy is resolved.
