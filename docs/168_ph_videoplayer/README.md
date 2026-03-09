# VETKA Video Player Lab

MARKER_168.VIDEOPLAYER.LAB.ROOT

This folder tracks the isolated sandbox effort for a standalone `VETKA Video Player`.

Goal:
- remove MCC/VETKA runtime noise from player debugging
- isolate native-window vs DOM-video geometry
- produce a player shell that can be reused inside VETKA or open-sourced separately
- keep the donor-player standalone and minimal, so it can later serve as a CUT preview surface

Current strategy:
- build a web-first, Tauri-compatible player lab
- lock geometry/debug contracts in isolation
- only after that re-import the winning shell into VETKA detached media window
- keep default route in pure-player mode with no outer lab chrome
- treat contextual actions as status-gated:
  - file not yet in VETKA -> show VETKA ingest action
  - file already in VETKA -> replace ingest action with time-marker actions
- keep preview quality selector in the donor-player because high-resolution media needs performance control independently of CUT runtime

Artifacts in this folder:
- recon reports
- architecture notes
- sandbox decisions
- migration notes back into VETKA
