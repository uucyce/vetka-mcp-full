# ROADMAP B6: Color Grading Depth
**Agent:** Beta (Media Pipeline)
**Branch:** claude/cut-media
**Date:** 2026-03-23
**FCP7 Ref:** Ch.79-83

## Gap Analysis

| Layer | Status | Detail |
|-------|--------|--------|
| UI (ColorCorrectionPanel) | 75% | 3-way wheels, basic sliders, curve presets. Missing: curve editor |
| FFmpeg render | 100% | All 12 color effects compile to filters |
| Numpy preview | 25% | Only basic 6 (brightness/contrast/saturation/gamma/exposure/hue) |
| Overall FCP7 Ch.79-83 | 25% | Preview gap makes wheels feel broken |

## Tasks

| # | Task | Priority | Complexity | What |
|---|------|----------|------------|------|
| B9.1 | Numpy: lift/midtone/gain preview | P0 | Low | 3-way wheel corrections visible in preview |
| B9.2 | Numpy: white_balance preview | P0 | Low | Temperature slider visible in preview |
| B9.3 | Numpy: curves preview | P1 | Medium | Curve preset + custom spline evaluation |
| B9.4 | Numpy: color_balance unified | P1 | Low | 9-param shadows/mids/highlights |
| B9.5 | Split compare viewer | P2 | Medium | Before/after side-by-side (Gamma wires) |

## Execution: B9.1-B9.4 in single commit (all numpy, same file)
