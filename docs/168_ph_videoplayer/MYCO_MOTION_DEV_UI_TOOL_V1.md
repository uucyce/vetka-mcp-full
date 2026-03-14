# MYCO Motion Dev UI Tool V1

Date: 2026-03-09
Status: proposed shared internal dev tool

## 1. Purpose

This toolchain is a reusable internal `dev UI` capability for animation-backed UI elements.

It is intended for:
- MCC
- VETKA
- Codex-side UI experiments
- future detached UI labs

## 2. Toolchain Layers

### Layer A. Asset conversion
Convert role motion MP4 into transparent APNG.

Primary script:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/media/mp4_to_apng_alpha.py`

Baseline family for current MYCO assets:
- `mode=luma`
- `fps=8`
- `luma-threshold=52`
- `alpha-blur=0.8`

### Layer B. Asset geometry QA
Existing player-lab review path verifies geometry, aspect fit, and shell dominance.

Tools:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/player_lab_review.sh`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/player_playground/e2e/dream_player_probe.spec.ts`

### Layer C. MCC-specific UI QA
Future dedicated probe for role assets inside compact runtime panels.

Scope:
- `MiniChat`
- helper topbar
- compact task/context panels
- workflow/team views

## 3. Why This Must Be Shared

Animation-backed UI is hard to evaluate by eye only.

This toolchain gives:
- reproducible screenshots,
- JSON metrics,
- geometry validation,
- future trigger validation,
- a common baseline across multiple apps.

## 4. Expected Repo Placement

The shared doctrine should live in `dev UI` documentation and be referenced by all agents that work on animation-backed surfaces.

Minimum references to keep in sync:
- probe entrypoint
- conversion preset
- trigger state matrix
- screenshot/snapshot artifact paths
- marker vocabulary

## 5. Adoption Rule

No MYCO motion asset should be promoted into runtime UI unless:
1. conversion preset is documented,
2. asset probe passes,
3. MCC-specific probe passes,
4. trigger mapping is explicitly documented.
