# MARKER_168 Video Player Lab Plan

Date: 2026-03-08

## North Star

Create a standalone player that feels trustworthy to a professional editor:

- correct aspect ratio
- no black side bars when window geometry should match
- predictable fullscreen behavior
- stable controls
- transparent diagnostics

## Build Order

1. Web-first sandbox
2. Geometry instrumentation
3. Proven shell variants
4. Optional Tauri host wrapper
5. Migration back into VETKA detached media path

## Web-First Lab Requirements

- open local file via file picker
- drag-and-drop support
- synthetic probe mode with explicit intrinsic width/height
- explicit footer height contract
- switchable shell variants
- live geometry readout
- console API for debug
- reusable pure geometry math
- browser e2e proving at least one good shell and one bad shell

## Variants to Compare

- fixed footer shell
- flex remainder shell
- metadata-first suggested window shell

## Migration Gate

Do not replace VETKA detached player until the lab proves:

- aspect ratio consistency
- stable fullscreen restore
- repeatable geometry metrics
- a clear source of truth for shell sizing
