# CUT Color Pipeline — Research Document

**Date:** 2026-03-20
**Author:** Opus-Beta (Media Agent)
**Sources:** FCP7 User Manual Ch.78-83, Grok web research, colour-science docs, FFmpeg docs
**Task:** tb_1773995461_6

---

## 1. FCP7 Color Correction Reference (Ch.78-83)

### 1.1 Video Scopes (Ch.78)

FCP7 provides 4 scopes in a Tool Bench window, available via `Tools > Video Scopes (Option-9)`:

| Scope | What it measures | CUT equivalent |
|-------|-----------------|----------------|
| **Waveform Monitor** | Luma (Y') distribution left-to-right, matches spatial position in frame | WaveformCanvas (audio only currently) |
| **Vectorscope** | Hue + saturation on circular polar plot, 6 target boxes (R/G/B/Cy/Mg/Yl) + Flesh Tone line | NOT IMPLEMENTED |
| **Histogram** | Luma distribution as bar graph (0-110%), shows contrast range | NOT IMPLEMENTED |
| **RGB Parade** | Three separate R/G/B waveforms side by side, shows per-channel levels | NOT IMPLEMENTED |

**Layout options:** All, Waveform, Vectorscope, Histogram, Parade, WF+Hist, WF+Parade, Luminance

**Display options per scope:**
- Brightness: display traces + scales brightness
- Saturation: toggle on Waveform to show chroma thickness
- Magnify: zoom inner 55% of Vectorscope for low-saturation detail
- Targets: ideal color bar measurement points

**Accuracy modes:** All Lines (highest), All Lines Except Top & Bottom, Limited Lines (fastest — for real-time)

**Key insight:** Scopes update in real-time during playback (Limited Lines mode), or analyze all pixels when paused.

### 1.2 Color Models (Ch.78)

- **RGB:** Additive. Computer-generated content.
- **Y'CbCr (YUV):** Separates luminance (Y') from chroma (Cb, Cr). Most video formats use this internally.
- **Luma (Y'):** Brightness channel. 0% = black, 100% = white, 101-109% = super-white.
- **Chroma:** Hue (angle on color wheel) + Saturation (distance from center).
- **Blacks/Midtones/Whites:** Overlapping luma ranges that FCP7 uses for 3-zone color correction.
  - Blacks: 0-75% luma (leftmost 3/4 of gradient)
  - Midtones: 25-75% luma (middle half)
  - Whites: 25-100% luma (rightmost 3/4)

### 1.3 Broadcast Safety (Ch.78)

- **Broadcast Safe filter:** Clamps luma + chroma to legal levels (NTSC/PAL/HD)
- **Modes:** Extremely Conservative (100) → Conservative (115) → Normal (120) → In-house (135+UNSAFE) → Custom
- **RGB Limit filter:** Works in 32-bit float RGB space, clamps min/max RGB values
- **Range Check:** Zebra stripes overlay on Viewer (red = excess luma >100%, green = 90-100%)
- **Processing order:** Filters → Motion → Transitions → Compositing → Broadcast Safe (always LAST)

### 1.4 Color Corrector Filter (Ch.81)

Single color wheel + level sliders. Controls:
- **Balance control:** Color wheel for whites — drag indicator to shift RGB mix
- **Hue control:** Separate rotary dial for overall hue shift
- **Auto-Balance eyedropper:** Click whitest area → auto white balance
- **Level sliders:** Whites, Mids, Blacks (luma levels) + Saturation
- **Auto Level:** Auto White Level, Auto Black Level, Auto Contrast buttons
- **Match Hue:** Eyedropper to sample color from adjacent clip → auto-match
- **Limit Effect:** Secondary color correction — key by hue/saturation/luma range
  - Color Range: top/bottom handles for hue width
  - Saturation control: range of saturation affected
  - Luma control: range of luma affected
  - Edge Thin / Softening: key edge refinement
  - Select Color eyedropper + View Final/Matte/Source toggle + Invert

### 1.5 Color Corrector 3-Way Filter (Ch.81)

Three color wheels (Blacks/Mids/Whites) + level sliders. The main grading tool:
- **3 Color balance wheels:** Each is a virtual trackball. Drag to shift R/G/B mix in shadows/mids/highlights
- **Shift-drag:** Constrains angle — change intensity without shifting hue
- **Cmd-drag:** "Gears up" — faster, larger changes (opposite of other FCP tools)
- **Level sliders:** Blacks, Mids, Whites + Saturation
- **Auto Level:** Same as Color Corrector
- **Match Hue:** Same as Color Corrector
- **Copy Filter controls:** Copy From 1st/2nd Clip Back, Copy To 1st/2nd Clip Forward, Drag Filter
- **Limit Effect:** Same secondary CC as Color Corrector
- **Keyframe controls:** Animate all CC settings over time

### 1.6 Additional Filters (Ch.81)

- **Desaturate Highlights / Desaturate Lows:** Remove unwanted color in extremes
- **RGB Balance:** Per-channel R/G/B level control for highlights/midtones/blacks independently

### 1.7 Color Correction Workflow (Ch.79, Ch.82)

**5-Stage Process:**
1. Pick master shot as reference
2. Primary CC: maximize contrast (Auto Level → Whites/Mids/Blacks), then color balance
3. Additional CC filters as needed (stack multiple, each targets different luma range)
4. Special filters: Desaturate Highlights, Broadcast Safe
5. Match coverage shots to master (Copy Filter controls)

**Key workflow patterns:**
- Always start with luma (contrast) before color
- Use scopes + broadcast monitor simultaneously
- Copy corrections between adjacent clips (shot-reverse-shot)
- Multiple CC filters stack serially (output of first = input of second)

---

## 2. Modern Color Standards

### 2.1 Color Spaces

| Standard | Gamut | White Point | Bit Depth | Use Case |
|----------|-------|-------------|-----------|----------|
| **Rec.709** | sRGB-equivalent | D65 | 8-bit | HD broadcast, web, most monitors |
| **Rec.2020** | Wide gamut | D65 | 10/12-bit | UHD/4K broadcast, HDR content |
| **DCI-P3** | Cinema gamut | DCI (~D63) | 12-bit | Digital cinema projection |
| **sRGB** | = Rec.709 gamut | D65 | 8-bit | Web, computer displays |
| **Display P3** | = DCI-P3 gamut | D65 | 10-bit | Apple displays, HDR web |

### 2.2 Transfer Functions (OETF/EOTF)

| Name | Type | Range | Use |
|------|------|-------|-----|
| **Gamma 2.4** | SDR display | 0-100 nits | Rec.709 standard |
| **sRGB** | SDR computer | ~2.2 effective | Web/computer displays |
| **PQ (ST.2084)** | HDR absolute | 0-10,000 nits | HDR10, Dolby Vision |
| **HLG** | HDR relative | SDR-compatible | HLG (BBC/NHK), broadcast HDR |
| **Linear** | Scene-referred | Unbounded | ACES, compositing |

### 2.3 Camera Log Curves

| Camera | Log Profile | Gamut | `colour-science` function= |
|--------|-----------|-------|---------------------------|
| Panasonic GH5/S5 | V-Log L | V-Gamut | `"V-Log"` |
| Sony FX6/A7S III | S-Log3 | S-Gamut3.Cine | `"S-Log3"` |
| ARRI Alexa | LogC3 | ARRI Wide Gamut 3 | `"ARRI LogC3"` |
| ARRI Alexa 35 | LogC4 | ARRI Wide Gamut 4 | `"ARRI LogC4"` |
| Canon C70/R5 | Canon Log 3 | Cinema Gamut | `"Canon Log 3"` |
| RED | Log3G10 | REDWideGamutRGB | `"Log3G10"` |
| Fuji X-H2S | F-Log | — | `"F-Log"` |
| DJI | D-Log | — | `"D-Log"` |

### 2.4 ACES Workflow

```
Camera → Input Transform (IDT) → ACEScg (AP1, linear) → Grading → Output Transform (ODT) → Display
```

- **ACEScg:** Scene-linear, AP1 primaries — grading working space
- **ACES 2065-1:** Archival, AP0 primaries
- Not recommended for CUT MVP — add as future option. Rec.709 working space is simpler.

### 2.5 LUT Formats

| Format | Extension | Type | Source |
|--------|-----------|------|--------|
| Iridas/Resolve | `.cube` | 1D/3D | Industry standard |
| Nuke | `.spi1d`, `.spi3d` | 1D/3D | VFX |
| Cinespace | `.csp` | 1D/3D | Legacy |
| Hald CLUT | `.png` | Identity image | Open-source |

---

## 3. FFmpeg Color Management

### 3.1 Key Filters for Color Correction

| Filter | What it does | CUT mapping |
|--------|-------------|-------------|
| `eq` | brightness, contrast, saturation, gamma | B16: brightness/contrast/saturation/gamma |
| `colorbalance` | per-zone RGB (rs/gs/bs/rm/gm/bm/rh/gh/bh) | B16: lift/midtone/gain |
| `hue` | hue shift, saturation | B9: hue |
| `curves` | preset or custom spline per channel | B16: curves |
| `lut3d` | Apply .cube/.3dl LUT file | B18 (planned) |
| `colorspace` | Convert between color spaces (BT.709/BT.2020/etc) | NOT IMPLEMENTED |
| `colorchannelmixer` | Per-channel matrix | B12: opacity |
| `zscale` | High-quality color space conversion (via libzimg) | NOT IMPLEMENTED |

### 3.2 Color Space Conversion Chain

```bash
ffmpeg -i input.mov \
  -vf "zscale=t=linear:npl=100,\
       zscale=p=bt709:t=bt709:m=bt709:r=tv,\
       format=yuv420p" \
  output.mp4
```

Key parameters: `p=` (primaries), `t=` (transfer), `m=` (matrix), `r=` (range: tv/pc)

### 3.3 Broadcast Safe via FFmpeg

```bash
ffmpeg -i input.mov -vf "limiter=min=16:max=235:planes=0" output.mov  # Y only
ffmpeg -i input.mov -vf "colorlevels=rimin=16/255:rimax=235/255:..." output.mov
```

### 3.4 Performance (CPU)

| Filter chain | 1080p30 | 4K30 |
|-------------|---------|------|
| eq + colorbalance | Real-time | Real-time |
| curves (preset) | Real-time | ~25fps |
| lut3d (33-pt .cube) | ~45fps | ~12fps |
| colorspace (BT.709→BT.2020) | ~30fps | ~8fps |
| Full chain (eq+cb+curves+lut3d) | ~25fps | ~6fps |

---

## 4. Current CUT Implementation

### 4.1 What We Have (cut_effects_engine.py)

**30+ effect types across 6 categories:**

| Category | Effects | FFmpeg Filter |
|----------|---------|---------------|
| **Color basic** | brightness, contrast, saturation, gamma, hue, exposure, white_balance | eq, hue, colorbalance |
| **Color 3-way** | lift (shadows), midtone (mids), gain (highlights) | colorbalance rs/gs/bs, rm/gm/bm, rh/gh/bh |
| **Color curves** | curves (9 presets + custom spline per channel) | curves |
| **Color balance** | color_balance (full 9-param) | colorbalance |
| **Motion** | position, scale, rotation, anchor, opacity | pad, scale, rotate, colorchannelmixer |
| **Transform** | crop, hflip, vflip, vignette | crop, hflip, vflip, vignette |
| **Blur** | blur, sharpen, denoise | gblur, unsharp, nlmeans |
| **Time** | fade_in, fade_out | fade |
| **Audio** | volume, fade, loudnorm, compressor | volume, afade, loudnorm, acompressor |

**Compilation pipeline:** `compile_video_filters()` merges eq params, chains others in order.
**CSS preview:** `compile_css_filters()` for real-time browser preview (subset: brightness/contrast/saturate/blur/hue + transform).

### 4.2 Gap Analysis: CUT vs FCP7

| FCP7 Feature | CUT Status | Priority |
|-------------|-----------|----------|
| **Waveform scope** | Audio waveform only (WaveformCanvas). No video luma waveform. | P1 |
| **Vectorscope** | NOT IMPLEMENTED | P1 |
| **Histogram** | NOT IMPLEMENTED | P2 |
| **RGB Parade** | NOT IMPLEMENTED | P2 |
| **Color Corrector (1-way)** | PARTIAL — have balance+hue, missing Auto-Balance eyedropper | P2 |
| **Color Corrector 3-Way** | IMPLEMENTED (B16) — lift/midtone/gain RGB sliders. Missing color wheels (trackball UI). | P1 (UI upgrade) |
| **Auto Level (auto contrast)** | NOT IMPLEMENTED | P2 |
| **Match Hue (eyedropper)** | NOT IMPLEMENTED | P3 |
| **Limit Effect (secondary CC)** | NOT IMPLEMENTED — needs pixel-level processing (PyAV path) | P3 |
| **Copy Filter to adjacent clips** | NOT IMPLEMENTED | P2 |
| **Broadcast Safe** | NOT IMPLEMENTED | P2 |
| **Desaturate Highlights/Lows** | NOT IMPLEMENTED — FFmpeg `selectivecolor` or pixel-level | P3 |
| **LUT .cube import** | Declared in effects_engine ("lut3d") but NOT COMPILED — no compile path | P1 |
| **Camera log decode** | NOT IMPLEMENTED — needs colour-science | P1 |
| **Color space conversion** | NOT IMPLEMENTED — needs zscale or colour-science | P2 |
| **Keyframed color correction** | NOT IMPLEMENTED — effects are static per-clip | P3 (future) |

---

## 5. Proposed Architecture

### 5.1 Two-Layer Color Pipeline

```
Layer 1: FFmpeg Filter Layer (CURRENT — cut_effects_engine.py)
  ├── eq, colorbalance, curves, hue → filter_complex strings
  ├── Fast, no Python runtime overhead
  ├── Works in render engine (cut_render_engine.py)
  └── Limited: no pixel access, no LUT, no log decode, no scopes

Layer 2: PyAV + colour-science Pixel Layer (NEW — cut_color_pipeline.py)
  ├── PyAV decode → NumPy frame (float32 [0-1])
  ├── colour.log_decoding() → camera log → linear
  ├── colour.RGB_to_RGB() → gamut conversion
  ├── colour.read_LUT().apply() → .cube LUT
  ├── numpy ops → custom curves, advanced CC
  ├── Scopes: waveform/vectorscope/parade/histogram
  └── PyAV encode → output
```

**Rule:** Layer 1 for render (fast, CLI-based). Layer 2 for preview + scopes + LUT (pixel-level).

### 5.2 Video Scopes Component Spec

**ScopePanel.tsx** — dockview panel with 4 scope modes:

| Mode | Algorithm | Input | Output |
|------|-----------|-------|--------|
| Waveform | Per-column luma histogram (vectorized, downsample to 512px) | RGB frame | 256x512 grayscale |
| Vectorscope | YCbCr → polar plot (Cb=x, Cr=y), skin tone line at ~123° | RGB frame | 256x256 circular |
| Histogram | Global luma histogram (256 bins) | RGB frame | 256x512 bar chart |
| Parade | Per-channel R/G/B column histograms (tinted) | RGB frame | 768x512 (3x stacked) |

**Update modes (following FCP7):**
- Paused: All Lines (every pixel)
- Playing: Limited Lines (every 32nd line, ~5% of pixels)
- Real-time target: all 4 scopes < 50ms on 1080p (downsample to 512px first)

### 5.3 3-Way Color Corrector UI Spec

**Current:** RGB sliders in ColorCorrectionPanel.tsx (lift/midtone/gain with R/G/B sliders)

**Target (FCP7-like):** 3 color wheels + level sliders

Each wheel:
- Circular color gradient (hue on angle, saturation on radius)
- Draggable center indicator (balance point)
- Shift-drag: constrain angle (saturation only)
- Reset button per wheel
- Auto-Balance eyedropper (click white/black/gray in viewer)

Below wheels:
- Blacks/Mids/Whites level sliders
- Saturation slider
- Auto Level (Auto White, Auto Black, Auto Contrast)

### 5.4 LUT Support Plan

1. **Import:** Upload .cube file → store in `{sandbox}/config/luts/`
2. **Apply:** `lut3d` FFmpeg filter for render, `colour.read_LUT().apply()` for preview
3. **Camera presets:** Built-in V-Log→Rec.709, S-Log3→Rec.709, LogC3→Rec.709 (as LUTs or transforms)
4. **UI:** LUT browser panel with thumbnails (apply LUT to reference frame)

### 5.5 Implementation Priority

| Phase | Tasks | Dependencies |
|-------|-------|-------------|
| **Phase 1: LUT + Log** | B18: cut_color_pipeline.py, camera log decode, .cube import | colour-science, PyAV |
| **Phase 2: Scopes** | B19: cut_scope_renderer.py, ScopePanel.tsx | PyAV (frame extraction) |
| **Phase 3: 3-Way Wheel UI** | Upgrade ColorCorrectionPanel → color wheel trackball UI | Canvas/SVG drawing |
| **Phase 4: Broadcast Safe** | Broadcast Safe filter + Range Check zebra overlay | FFmpeg limiter |
| **Phase 5: Secondary CC** | Limit Effect (key by hue/sat/luma) | PyAV pixel pipeline |
| **Phase 6: Match + Copy** | Match Hue eyedropper, Copy Filter to adjacent clips | Store actions |

---

## References

- Apple FCP7 User Manual, Ch.78-83 (p.1315-1434)
- colour-science 0.4.7: https://github.com/colour-science/colour
- PyAV: https://github.com/PyAV-Org/PyAV
- FFmpeg filters: https://ffmpeg.org/ffmpeg-filters.html
- RECON_B_PYAV_COLOR_PIPELINE.md (Grok research, verified)
- ITU-R BT.709, BT.2020, SMPTE ST.2084 (PQ), ARIB STD-B67 (HLG)
