# Effects Browser — Architecture
**Date:** 2026-03-23
**Owner:** Gamma (claude/cut-ux)
**Commit:** GAMMA-36

---

## Overview

EffectsPanel now has two modes:
1. **Effects Browser** (no clip selected) — FCP7 Ch.13 style browsable list
2. **Effect Controls** (clip selected) — per-clip adjustment sliders

## Effects Registry

30 effects across 4 categories:

| Category | Count | Examples |
|----------|-------|---------|
| Video Filters | 10 | Brightness, Blur, Chroma Key, LUT Apply |
| Audio Filters | 8 | EQ, Compressor, Limiter, Reverb |
| Transitions | 7 | Cross Dissolve, Dip to Black, Wipe |
| Generators | 5 | Color Matte, Bars & Tone, Slug, Text |

## Drag-and-Drop Protocol

Effects are draggable with MIME type `application/x-cut-effect`.

```json
{
  "id": "cross_dissolve",
  "name": "Cross Dissolve"
}
```

**Drop targets (future work):**
- Timeline clip → apply effect to clip
- Timeline edit point → apply transition between clips
- Timeline empty area → insert generator

## Search

Real-time filter across effect names and descriptions. Categories auto-expand when searching.

## Next Steps

1. **Alpha:** Wire drop handler in TimelineTrackView to receive `application/x-cut-effect` drops
2. **Alpha:** Add `applyEffect(clipId, effectId)` to useCutEditorStore
3. **Gamma:** Add effect preview thumbnails (SVG icons per effect)
4. **Gamma:** Add "Favorites" category (user-pinned effects)
5. **Beta:** Backend `EFFECT_DEFS` → FFmpeg filter mapping for render pipeline
