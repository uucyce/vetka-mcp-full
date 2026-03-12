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
- before `VETKA Core/CUT` is available, presses on the `VETKA` logo may be recorded as provisional player-side events using the same local marker/comment lane that can later export to SRT-compatible bundles
- once `VETKA Core/CUT` is connected, these provisional events must migrate into canonical CUT time markers and the contextual icon switches from `VETKA` logo to `star`
- keep preview quality selector in the donor-player because high-resolution media needs performance control independently of CUT runtime

Transitional rule:
- `VETKA` logo in standalone mode is not a permanent file favorite
- it is a temporary capture affordance before Core/CUT is online
- `star` appears only after Core/CUT-backed moment semantics are available

Marker:
- `MARKER_168.VIDEOPLAYER.TRANSITIONAL_VETKA_LOGO_BUFFER`

Artifacts in this folder:
- recon reports
- architecture notes
- sandbox decisions
- migration notes back into VETKA
