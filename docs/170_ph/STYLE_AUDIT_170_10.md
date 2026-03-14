# MARKER_170.10 — CUT UI Style Audit: Adobe Premiere Pro Alignment

## Executive Summary

CUT editor uses **emoji icons** and **hardcoded colors** throughout. To achieve Adobe Premiere Pro parity:
1. Replace all emoji with monochrome SVG icons
2. Strip color from UI chrome — only markers/clips get color
3. Consolidate to design token system
4. Make panels resizable

## Current State

### Icons (ALL EMOJI — must replace)

| Location | Current | Proposed SVG |
|----------|---------|-------------|
| Lane: video_main | `🎬` | Film strip icon (mono) |
| Lane: audio_sync | `🔊` | Speaker/waveform icon (mono) |
| Lane: take_alt | `🎥` | Camera icon (mono) |
| Lane: aux | `📎` | Link/chain icon (mono) |
| Transport: skip start | `⏮` | `|◀` chevron (mono) |
| Transport: play | `▶` | Triangle (mono) |
| Transport: pause | `⏸` | Double bar (mono) |
| Transport: skip end | `⏭` | `▶|` chevron (mono) |
| Transport: export | `📤` | Arrow-up-from-box (mono) |
| View: NLE mode | `🎬` | Grid/layout icon (mono) |
| View: debug | `🔧` | Wrench icon (mono) |
| Music badge | `🎵` | Note icon (mono) |
| Audio fallback | `♪` | Note icon (mono) |

### Colors — Chrome Must Be Neutral

**Keep (semantic marker colors):**
- Lane accent colors (blue, green, purple, amber) — clip/lane identity
- Marker kind colors (amber, blue, purple, green) — marker type
- VU meter gradient (green→yellow→red) — audio level
- Scene Graph marker source colors (purple, pink, amber)

**Neutralize (chrome should be gray-scale):**
- Transport bar buttons — white/gray only
- Panel headers — no accent colors
- Export button — neutral gray, not blue
- Source browser — no colored badges beyond file type indicators

### Panel Layout — Fixed → Resizable

| Panel | Current | Target |
|-------|---------|--------|
| Source Browser | 280px fixed | min 200px, resizable |
| Program Monitor | flex: 1 | flex: 1 (keeps growing) |
| Scene Graph | 280px fixed | min 200px, resizable |
| Inspector | 260px fixed | min 200px, resizable |
| Timeline | 40% height | min 120px, resizable (already has handle) |

### Typography — Already Good
- System UI for labels, JetBrains Mono for timecodes
- Matches Premiere Pro approach

## Implementation Plan

### 170.13: SVG Icon Set
- Create `client/src/components/cut/icons/` directory
- ~15 monochrome SVG components (React, currentColor)
- Replace all emoji references in CUT components

### 170.10.1: Color Neutralization
- Strip accent colors from transport/chrome elements
- Keep semantic colors only for clips, markers, VU
- Consolidate to CSS custom properties or constants file

### 170.11: Resizable Panels
- Add horizontal resize handles between panels
- Store widths in useCutEditorStore
- Min/max constraints per panel

### 170.12: Multi-Timeline
- Tab system above timeline area
- Multiple TimelineTrackView instances
- Shared playhead sync option

## Reference: Adobe Premiere Pro Design Language
- Near-black backgrounds (#1e1e1e to #2d2d2d)
- Gray-scale chrome (#3d3d3d borders, #808080 text)
- White icons on dark (#cccccc default, #ffffff active)
- Color ONLY for: clips (blue/green/purple), markers, audio meters
- Thin 1px borders, no rounded corners on panels
- Tight 24-28px panel headers
