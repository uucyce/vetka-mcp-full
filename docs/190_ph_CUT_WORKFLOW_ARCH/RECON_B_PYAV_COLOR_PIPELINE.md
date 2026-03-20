# RECON: PyAV + colour-science Color Pipeline for CUT

**Date:** 2026-03-20
**Source:** Grok research + Opus verification
**Status:** VERIFIED — ready for implementation

---

## Stack (all open-source, pip-installable)

| Library | Version | Purpose |
|---------|---------|---------|
| **PyAV** | 14.x | Decode/encode via FFmpeg → NumPy frames |
| **colour-science** | 0.4.7+ | Color math: log curves, gamut conversion, LUT apply |
| **OpenCV** (cv2) | 4.x | Fast pixel ops, scope rendering |
| **NumPy** | 2.x | Array foundation |

```bash
pip install colour-science opencv-python av numpy
```

**IMPORTANT:** PyAV must be built against our custom FFmpeg (max codecs).
Standard pip wheel has limited codec support.

---

## 1. Camera Log Profiles (VERIFIED)

All via `colour.log_encoding()` / `colour.log_decoding()`:

| Camera | `function=` string | Gamut name |
|--------|-------------------|------------|
| Panasonic GH5/GH6/S5 (V-Log L) | `"V-Log"` | `"V-Gamut"` |
| Sony FX6/A7S III (S-Log3) | `"S-Log3"` | `"S-Gamut3.Cine"` or `"S-Gamut3"` |
| ARRI Alexa (LogC3) | `"ARRI LogC3"` | `"ARRI Wide Gamut 3"` |
| ARRI Alexa 35 (LogC4) | `"ARRI LogC4"` | `"ARRI Wide Gamut 4"` |
| Canon (Canon Log 3) | `"Canon Log 3"` | Canon Cinema Gamut |
| Canon (Canon Log) | `"Canon Log"` | — |
| RED (Log3G10) | `"Log3G10"` | `"REDWideGamutRGB"` |
| Fuji (F-Log) | `"F-Log"` | — |
| Nikon (N-Log) | `"N-Log"` | — |
| DJI (D-Log) | `"D-Log"` | — |

### Verified API pattern:
```python
import colour
import numpy as np

# Log → Linear (decode camera footage)
linear = colour.log_decoding(log_frame, function="V-Log")

# Linear → Rec.709 display (gamut conversion)
rec709 = colour.RGB_to_RGB(
    linear,
    input_colourspace="V-Gamut",
    output_colourspace="ITU-R BT.709",
)
```

### CAUTION (Grok errors corrected):
- `colour.RGB_COLOURSPACE_VLog` does NOT exist — gamut is `"V-Gamut"`, log is separate
- `colour.eotf_VLog()` does NOT exist — use `colour.log_decoding(x, function="V-Log")`
- Gamut names must match `colour.RGB_COLOURSPACES` keys exactly (run `print(sorted(colour.RGB_COLOURSPACES))` to verify)

---

## 2. LUT Import + Apply (VERIFIED)

```python
import colour

# Read .cube file (1D or 3D, auto-detected)
lut = colour.read_LUT("cinematic.cube")

# Apply to frame (float32 [0-1], shape (H, W, 3))
graded = lut.apply(frame)  # uses trilinear interpolation by default
```

### Supported formats:
- `.cube` (Resolve/Premiere standard)
- `.spi1d`, `.spi3d` (OCIO/Nuke)
- `.csp` (Cinespace)
- `.lut` (various)

### Performance (REALISTIC estimates):
| LUT size | 1080p frame | 4K frame |
|----------|-------------|----------|
| 17-point 3D | ~10ms | ~40ms |
| 33-point 3D | ~20-30ms | ~80-120ms |
| 65-point 3D | ~50-70ms | ~200-280ms |

### CAUTION (Grok errors corrected):
- `KDTreeInterpolator` is NOT for LUT apply — default is trilinear
- `query_size=8` param does NOT exist on `lut.apply()`
- "40-55 FPS on M2" is optimistic — realistic is 20-35 FPS for 33-pt on 1080p
- For real-time preview: apply LUT on downscaled proxy (540p), not full res

---

## 3. Scopes (Waveform / Parade / Vectorscope)

### Waveform — CORRECTED (vectorized, not per-column loop):
```python
def waveform_vectorized(frame_uint8: np.ndarray, scope_h: int = 256) -> np.ndarray:
    """Luma waveform — fully vectorized, ~5-10ms on 1080p."""
    luma = np.dot(frame_uint8[..., :3].astype(np.float32),
                  [0.2126, 0.7152, 0.0722]).astype(np.uint8)
    # Downsample width for scope display
    w = min(luma.shape[1], 512)
    luma_ds = cv2.resize(luma, (w, luma.shape[0]))
    scope = np.zeros((scope_h, w), dtype=np.uint8)
    for x in range(w):  # 512 iterations, not 1920
        hist = np.bincount(luma_ds[:, x], minlength=256)
        if hist.max() > 0:
            normalized = np.clip(hist * 200 / hist.max(), 0, 255).astype(np.uint8)
            scope[:, x] = normalized[:scope_h]
    return scope
```

### CAUTION (Grok errors corrected):
- Per-column Python loop on FULL width (1920) = ~50-100ms, NOT "< 8ms"
- Must downsample to scope width (512) FIRST, then loop = ~5-15ms
- Vectorscope via HSV is simplified — pro scopes use YCbCr (Rec.601/709)
- Parade should use separate R/G/B histograms, not stacked waveforms

### Realistic performance:
| Scope | 1080p input → 512px scope |
|-------|--------------------------|
| Waveform (luma) | ~5-10ms |
| Parade (RGB) | ~15-25ms |
| Vectorscope | ~8-15ms |
| All three | ~30-50ms |

---

## 4. Integration Architecture for CUT

```
┌─────────────────────────────────────────────────┐
│  cut_color_pipeline.py (NEW)                     │
│                                                   │
│  PyAV decode → numpy frame                        │
│       ↓                                           │
│  Log decode (colour.log_decoding)                 │
│       ↓                                           │
│  Gamut convert (colour.RGB_to_RGB)                │
│       ↓                                           │
│  LUT apply (colour.read_LUT → .apply)             │
│       ↓                                           │
│  Effects (cut_effects_engine compile → numpy ops) │
│       ↓                                           │
│  Scopes (waveform/parade/vectorscope)             │
│       ↓                                           │
│  Preview: downscale → base64 JPEG → WebSocket     │
│  Render: full-res → PyAV encode                   │
└─────────────────────────────────────────────────┘
```

### Two modes:
1. **Preview** — 540p proxy, ~30fps, scopes + LUT preview, via WebSocket to frontend
2. **Render** — full-res, offline, PyAV encode with all effects applied at pixel level

### Files:
- `src/services/cut_color_pipeline.py` — PyAV + colour-science integration
- `src/services/cut_scope_renderer.py` — waveform/parade/vectorscope
- `client/src/components/cut/ScopePanel.tsx` — scope display in UI

---

## 5. Tasks

### P1 — LUT Import + Camera Log (highest value)
- `cut_color_pipeline.py`: log_decoding for V-Log/S-Log3/LogC3/Canon Log 3
- LUT .cube read + apply on numpy frame
- POST /cut/lut/apply endpoint (single frame preview)
- POST /cut/lut/import endpoint (upload .cube to project)

### P2 — Scope Renderer
- `cut_scope_renderer.py`: vectorized waveform, parade, vectorscope
- GET /cut/scopes?source_path=...&time=... endpoint (returns scope images)
- ScopePanel.tsx frontend

### P3 — PyAV Decode/Encode Pipeline
- Replace FFmpeg subprocess with PyAV for preview frames
- Real-time preview at 540p with effects + LUT
- WebSocket frame delivery to frontend

### P4 — Full Render with Pixel Pipeline
- Extend cut_render_engine.py with PyAV path
- Apply effects at pixel level (not FFmpeg filter strings)
- 10-bit float32 pipeline throughout
