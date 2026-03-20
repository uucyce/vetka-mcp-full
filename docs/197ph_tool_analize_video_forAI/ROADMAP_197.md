# Roadmap: Phase 197 — Video Inspection Tool for AI

**Architecture:** [ARCHITECTURE_VIDEO_INSPECTION_TOOL.md](ARCHITECTURE_VIDEO_INSPECTION_TOOL.md)
**Date:** 2026-03-20
**Task:** tb_1773972236_2

---

## Vision

Универсальный CLI-инструмент, который превращает любой mp4 в набор лёгких артефактов (~800KB), понятных и AI-агентам, и людям. Два слоя: RGB (мгновенный) + Depth (тяжёлый, но даёт пространство). Замыкает feedback loop для автономной работы агентов с видео.

---

## Milestones

### M1: Layer 1 — RGB Inspection (MVP)
> **"Агент может смотреть видео"**

| Task | Deliverable | Agent | Priority |
|------|-------------|-------|----------|
| 197.3: Core CLI scaffold | `video_inspection_pack.py` — argparse, ffprobe metadata, outdir creation | Codex/Dragon | P2 |
| 197.4: Contact sheet | Extract N frames (uniform) + Pillow grid assembly + timestamp overlay | Codex/Dragon | P1 |
| 197.5: Motion diff strip | Consecutive frame absdiff via Pillow, horizontal strip | Codex/Dragon | P1 |
| 197.6: inspection.json | JSON manifest: input meta + settings + output paths + timestamps | Codex/Dragon | P1 |

**Exit criteria M1:**
- `python3 scripts/video_inspection_pack.py --input video.mp4 --outdir out/` produces `contact_sheet.jpg` + `motion_diff.jpg` + `inspection.json`
- No dependencies beyond ffmpeg + Pillow
- Works on macOS with any mp4

---

### M2: Layer 2 — Depth Inspection
> **"Агент понимает пространство"**

| Task | Deliverable | Agent | Priority |
|------|-------------|-------|----------|
| 197.7: Depth model wrapper | `video_inspection_depth.py` — load Depth Anything V2 Small, single-frame inference, batch mode | Codex/Dragon | P1 |
| 197.8: Depth contact sheet | Same grid layout as RGB contact sheet, but depth maps. `--depth` flag | Codex/Dragon | P1 |
| 197.9: Depth diff | Absdiff between consecutive depth frames, strip layout | Codex/Dragon | P2 |
| 197.10: Motion energy heatmap | Mean of all absdiff frames → single heatmap PNG, colormap overlay | Codex/Dragon | P2 |
| 197.11: Progress bar | tqdm or simple print progress for depth inference (N/total frames) | Codex/Dragon | P3 |

**Exit criteria M2:**
- `--depth` flag produces `depth_contact_sheet.jpg` + `depth_diff.jpg` + `motion_energy.png`
- Progress bar shows inference progress
- Depth Anything V2 Small auto-downloads weights on first run
- `inspection.json` includes `depth_stats` section

**Depth model decision:**
- Primary: Depth Anything V2 Small (cross-platform, PyTorch)
- Optional: Apple DepthPro (CoreML, macOS only, faster) — only if worth the maintenance cost
- Decision point: benchmark both at M2 start, pick one, don't support two

---

### M3: Advanced Features
> **"Удобно для реальной работы"**

| Task | Deliverable | Agent | Priority |
|------|-------------|-------|----------|
| 197.12: ROI crop | `--crop x,y,w,h` applied to all outputs (ffmpeg vf + Pillow crop) | Codex/Dragon | P2 |
| 197.13: Keyframe mode | `--keyframes` — ffmpeg scene detection instead of uniform sampling | Codex/Dragon | P3 |
| 197.14: Sample rate control | `--sample-rate N` for depth layer (every Nth frame) | Codex/Dragon | P3 |
| 197.15: Batch mode | `--input-dir /path/` — process all mp4s, per-video subdirs in outdir | Codex/Dragon | P3 |

**Exit criteria M3:**
- Crop works consistently across all artifacts
- Keyframe mode finds scene changes, not uniform frames
- Batch mode handles 10+ videos without crashing

---

### M4: Integration
> **"Агенты используют это автоматически"**

| Task | Deliverable | Agent | Priority |
|------|-------------|-------|----------|
| 197.16: MCP tool wrapper | `vetka_inspect_video` MCP tool — calls CLI, returns inspection.json | Opus | P2 |
| 197.17: photo_to_parallax hook | Post-render auto-inspection in parallax pipeline | Opus/Cursor | P3 |
| 197.18: CUT integration | Post-export inspection for PULSE auto-montage results | Cursor | P3 |
| 197.19: Agent prompt template | Standard prompt for "analyze this inspection pack" with vision model | Opus | P2 |

**Exit criteria M4:**
- Agent can call `mcp__vetka__vetka_inspect_video --input render.mp4` and get structured results
- Parallax pipeline auto-generates inspection pack after each render
- Prompt template tested with Claude vision + Qwen vision

---

### M5: Tests & Hardening
> **"Не ломается"**

| Task | Deliverable | Agent | Priority |
|------|-------------|-------|----------|
| 197.20: Contract tests | test_video_inspection_pack.py — CLI args, output files exist, JSON schema | Codex | P2 |
| 197.21: Edge cases | 0-duration video, single frame, no audio, 4K, vertical video | Codex | P3 |
| 197.22: Eval: real-world test | Run on 5 real parallax renders + 5 CUT exports, verify AI can analyze | Opus | P2 |

---

## Dependency Graph

```
M1 (RGB MVP)
  ├── 197.3 scaffold
  ├── 197.4 contact sheet  ──┐
  ├── 197.5 motion diff    ──┤
  └── 197.6 inspection.json──┘
                              │
M2 (Depth) ───────────────────┘
  ├── 197.7 depth wrapper
  ├── 197.8 depth contact  ──depends on 197.7
  ├── 197.9 depth diff     ──depends on 197.7
  ├── 197.10 motion energy ──depends on 197.7
  └── 197.11 progress bar
                              │
M3 (Advanced) ────────────────┘
  ├── 197.12 crop          ──independent
  ├── 197.13 keyframes     ──independent
  ├── 197.14 sample rate   ──depends on 197.7
  └── 197.15 batch mode    ──depends on M1
                              │
M4 (Integration) ─────────────┘
  ├── 197.16 MCP wrapper   ──depends on M1+M2
  ├── 197.17 parallax hook ──depends on 197.16
  ├── 197.18 CUT hook      ──depends on 197.16
  └── 197.19 prompt template──depends on M1
                              │
M5 (Tests) ───────────────────┘
  ├── 197.20 contract tests──depends on M1
  ├── 197.21 edge cases    ──depends on M1
  └── 197.22 real-world eval──depends on M2+M4
```

---

## Agent Assignment Strategy

| Agent | Best for | Tasks |
|-------|----------|-------|
| **Codex** (worktree) | Pure Python CLI code, isolated module | 197.3–197.6 (M1), 197.12–197.15 (M3), 197.20–197.21 (M5) |
| **Dragon** (pipeline) | Depth model integration, heavy computation | 197.7–197.11 (M2) |
| **Opus** | Architecture decisions, MCP integration, prompts | 197.16, 197.19, 197.22 |
| **Cursor** | UI hooks if needed | 197.17, 197.18 |

**Recommended start:** Codex takes M1 (scaffold + RGB) → merge → Dragon takes M2 (depth).

---

## Risk Log

| Risk | Impact | Mitigation |
|------|--------|------------|
| Depth model weights too large | Slow first run, disk space | Use Small variant (~100MB), lazy download |
| ffmpeg version differences | Broken filters on older ffmpeg | Pin minimum ffmpeg 5.0, test in CI |
| Pillow font not found on macOS | Ugly text or crash | Fallback to `load_default()`, already handled |
| 4K video → huge contact sheets | Memory, disk | Always scale to `--width` before processing |
| Depth model accuracy on CG/rendered content | Bad depth maps for non-photo content | Test on parallax renders early (M2), fallback to RGB-only |

---

## Success Metrics

1. **AI can analyze video:** Agent sends contact_sheet + depth_contact_sheet to vision model → gets structured quality feedback
2. **Human glance test:** One look at contact_sheet → understand video pacing. One look at depth_diff → see spatial artifacts
3. **Weight budget:** Total inspection pack < 1MB
4. **Speed:** Layer 1 < 3 sec, Layer 2 < 10 sec for 10-sec video on M1/M2 Mac
5. **Zero config:** `--input video.mp4 --outdir out/` works with no other flags
