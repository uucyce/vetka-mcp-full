# PHASE 171 CUT Montage Engine Architecture Freeze (2026-03-13)

## Purpose

Freeze the first implementation shape of the montage engine so Phase 171 can move from editor surfaces to persisted editorial decisions.

## Proven foundation from Phase 170

Already in place:
- CUT review app/dmg lane with fixed-port launch path
- Berlin fixture bootstrap/profile and browser acceptance
- first-class Scene Graph viewport in NLE
- marker bundle path from music/sync into Scene Graph
- handler-verified Scene Graph focus -> timeline round-trip

## Architecture decision

Phase 171 will treat the montage engine as a layer above workers and below editor actions.

Pipeline:
1. workers produce raw cues
2. project-state carries normalized cue summaries
3. montage engine ranks/promotes cues into decision candidates
4. editor accepts or rejects decisions
5. accepted decisions persist in montage state

## First frozen objects

### 1. Cue sources
- transcript cues
- pause / silence cues
- music cues
- sync cues
- scene graph semantic cues
- manual notes / director intent

### 2. Montage decision candidate
Each candidate must carry:
- stable id
- source family
- cue provenance ids
- confidence / score
- start/end time or anchor time
- lane / target context
- editorial intent label
- accepted / rejected / pending state

### 3. Persisted montage state
Minimal persisted state must include:
- accepted decisions
- rejected decisions
- decision provenance
- source bundle revision
- timestamp / author

## Hard rules
- hard sync stays authoritative over meta/intel suggestions
- music cues enrich montage decisions, they do not silently rewrite sync results
- Scene Graph remains first-class viewport, not fallback UI
- Berlin fixture remains the deterministic acceptance lane for Phase 171
- reserved ports stay fixed (`3011`, `3211`)

## Immediate implementation order

1. seed montage state contract
2. persist accepted marker -> montage promotions
3. formalize music cue contract from Punch track
4. expose project-state music summary
5. add Berlin montage acceptance smoke

## Markers
- `MARKER_171.MONTAGE_ENGINE.ARCH_FREEZE`
- `MARKER_171.MONTAGE_ENGINE.CANDIDATE_MODEL`
- `MARKER_171.MONTAGE_ENGINE.PERSISTENCE_MINIMUM`
