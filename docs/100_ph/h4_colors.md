# H4: Colors & Themes Report - VETKA Phase 100 Tauri Migration

## Summary

Unified **dark theme** throughout. No light mode. Primary palette: grayscale + blue/green/red accents.

## Tailwind Colors Configuration

Location: `app/artifact-panel/tailwind.config.js`

| Name | Value | Usage |
|------|-------|-------|
| vetka.bg | #0a0a0a | Dark background base |
| vetka.surface | #111111 | Panel backgrounds |
| vetka.border | #222222 | Borders and dividers |
| vetka.text | #d4d4d4 | Primary text |
| vetka.muted | #666666 | Secondary text |
| vetka.accent | #3b82f6 | Primary blue accent |

## Color Palette

### Background Colors
| Color | Hex | Usage |
|-------|-----|-------|
| Root Background | #0a0a0a | Main app background |
| Surface Primary | #111111 | Panels, inputs |
| Surface Secondary | #0f0f0f | Headers |
| Surface Tertiary | #1a1a1a | Hover states |

### Border Colors
| Color | Hex | Usage |
|-------|-----|-------|
| Primary Border | #222222 | Main borders |
| Secondary Border | #333 | Lighter borders |
| Hover Border | #444 | Active/hover |

### Text Colors
| Color | Hex | Brightness |
|-------|-----|-----------|
| Primary | #d4d4d4 | 83% |
| Light | #ffffff | 100% |
| Muted | #666666 | 40% |
| Dim | #555555 | 33% |
| Very Dim | #333333 | 20% |

### Accent Colors
| Color | Hex | Usage |
|-------|-----|-------|
| Blue Primary | #3b82f6 | Focus, accent |
| Bright Blue | #4a9eff | Listening, voice |
| Bright Green | #4aff9e | Speaking, TTS |
| Cyan Teal | #66aabb | Listening state |
| Red | #f87171 | Error, delete |
| Yellow | #facc15 | Warning |
| Green | #4ade80 | Success |

## Voice State Colors

Location: `client/src/styles/voice.css`

| State | Color | Background | Border |
|-------|-------|------------|--------|
| Listening | #4a9eff | #1a3a5c | #2a4a6c |
| Speaking | #4aff9e | #1a3a2a | #2a4a3a |
| Idle | #666 | #1a1a1a | #333 |
| Error | #ff4a4a | #2a1a1a | #3a2a2a |

## CSS Variables

Location: `app/artifact-panel/src/index.css`

```css
--rpv-core__background-color: #0a0a0a
--rpv-core__border-color: #222
--rpv-core__text-color: #d4d4d4
--rpv-core__shadow-color: rgba(0, 0, 0, 0.5)
```

## Component Color Functions

### MessageInput Wave Colors
```javascript
Speaking: #4a9eff (Blue)
Playing: #4aff9e (Green)
Listening: #66aabb (Teal)
Idle: #555555 (Gray)
```

### FileCard Border Colors
```javascript
Pinned: #4a9eff (Blue)
Dragging: #666666 (Gray)
Selected: #888888 (Light Gray)
Highlighted: #777777 (Gray)
Default: #444444 (Dark Gray)
```

## Scrollbar Styling

All scrollbars:
```css
Track: #0a0a0a
Thumb: #333 (default), #555 (hover)
Border-radius: 3px
Width: 6-8px
```

## Markers

[COLOR_TAILWIND] `app/artifact-panel/tailwind.config.js`
[COLOR_CSS_VAR] `app/artifact-panel/src/index.css`
[COLOR_THEME] `client/src/styles/voice.css`
[COLOR_SIDEBAR] `client/src/components/chat/ChatSidebar.css`
[COLOR_SCAN] `client/src/components/scanner/ScanPanel.css`

## Dark Mode Implementation

- **Status:** Unified dark mode only
- **Declaration:** `:root { color-scheme: dark; }`
- **Strategy:** rgba for layered transparency
- **Contrast:** WCAG AA compliant

## Tauri Migration Notes

- All colors CSS-based, work identically in Tauri
- No system theme detection needed (always dark)
- Voice state colors already implemented

---
Generated: 2026-01-29 | Agent: H4 Haiku | Phase 100
