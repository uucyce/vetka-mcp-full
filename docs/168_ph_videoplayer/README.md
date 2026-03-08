# VETKA Video Player Lab

MARKER_168.VIDEOPLAYER.LAB.ROOT

This folder tracks the isolated sandbox effort for a standalone `VETKA Video Player`.

Goal:
- remove MCC/VETKA runtime noise from player debugging
- isolate native-window vs DOM-video geometry
- produce a player shell that can be reused inside VETKA or open-sourced separately

Current strategy:
- build a web-first, Tauri-compatible player lab
- lock geometry/debug contracts in isolation
- only after that re-import the winning shell into VETKA detached media window

Artifacts in this folder:
- recon reports
- architecture notes
- sandbox decisions
- migration notes back into VETKA
