# MARKER_168 Video Player Lab Recon

Date: 2026-03-08

## Context

Phase159 detached media window inside VETKA remains unstable after several days of debugging.
The issue now looks less like "broken playback" and more like "broken contract between native window geometry and actual video viewport."

## Proven Facts

- `ffprobe` returns correct dimensions for affected files, e.g. `1920x1080`.
- detached path now receives media metadata correctly before window open.
- fullscreen exit often improves or stabilizes geometry.
- the old embedded path rendered video visually closer to correct, but had fullscreen coupling and wrong authority path.
- mixed native Tauri window lifecycle + detached React layout + VETKA routing makes the current environment too noisy for precise iteration.

## Why a Separate Lab

The current detached player is entangled with:

- Tauri window reuse
- VETKA routing
- artifact panel actions
- MCC / dev panel noise
- multiple event paths for opening artifacts
- unrelated in-flight changes by other agents

This makes every geometry change expensive to evaluate.

## Lab Principle

Build a standalone `VETKA Video Player Lab` that isolates:

1. video metadata
2. shell geometry
3. footer/toolbar reserve
4. native-vs-DOM metrics
5. fullscreen transitions

## Decision

Use a web-first, Tauri-compatible sandbox first.

Rationale:
- faster iteration
- easier to instrument
- easy to open-source later
- can still be wrapped into Tauri once the shell contract is proven

## Immediate Deliverables

- isolated player playground
- geometry debugger overlay
- console API for snapshots
- tests for pure geometry math
- docs + markers for migration back into VETKA
