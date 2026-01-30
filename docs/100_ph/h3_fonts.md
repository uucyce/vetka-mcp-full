# H3: Fonts Report - VETKA Phase 100 Tauri Migration

## Summary

**156+ Font Files** across multiple formats. Primary UI uses Inter from Google Fonts CDN.

## Font Files by Format

| Format | Count | Location |
|--------|-------|----------|
| TTF | 56+ | KaTeX, Three.js, Source Code Pro |
| WOFF | 54+ | Web optimization |
| WOFF2 | 39+ | Modern browser compression |
| OTF | 5+ | OpenType variants |

## Primary Typography

### 1. Inter Font (Main UI)
- **Source:** Google Fonts CDN
- **Weights:** 400, 500, 600
- **Import:** `client/index.html`
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap">
```

### 2. System Font Stack (Fallback)
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

### 3. Monospace (Code)
```css
font-family: 'Monaco', 'Consolas', 'Courier New', 'SF Mono', 'Menlo', monospace;
```

### 4. KaTeX Math Fonts (19+ variants)
- Location: `node_modules/katex/dist/fonts/`
- Used for mathematical equation rendering
- Already bundled in project

## Configuration Files

| File | Purpose |
|------|---------|
| `client/index.html` | Google Fonts import |
| `frontend/src/config/design_system.ts` | Typography config |
| `app/artifact-panel/src/index.css` | Tailwind + system fonts |
| `frontend/static/css/mcp_console.css` | MCP monospace fonts |

## Font Face Declarations

| Font Name | Source | Weight | Style |
|-----------|--------|--------|-------|
| Inter | Google CDN | 400, 500, 600 | normal |
| KaTeX_Main | Local bundle | 400, 700 | normal, italic |
| KaTeX_Math | Local bundle | 400, 700 | italic |
| KaTeX_Size1-4 | Local bundle | 400 | normal |
| Codicon | Local bundle | 400 | normal |

## External Fonts

| Source | URL | Used For |
|--------|-----|----------|
| Google Fonts | fonts.googleapis.com | Inter UI font |

## Markers

[FONT_FILE] 156+ files in node_modules (KaTeX, Three.js)
[FONT_FACE] Declarations in index.html, design_system.ts
[FONT_EXTERNAL] Google Fonts CDN (Inter)

## Tauri Migration Recommendations

1. **Embed Inter WOFF2** - Currently CDN-based, embed locally for offline
2. **Update paths** - `file://` protocol compatibility
3. **KaTeX fonts** - Already bundled, no action needed
4. **System fonts** - Remain compatible cross-platform

## Font Embedding Strategy

For Tauri offline mode:
```
client/public/fonts/
├── inter-regular.woff2
├── inter-medium.woff2
└── inter-semibold.woff2
```

Update CSS:
```css
@font-face {
  font-family: 'Inter';
  src: url('/fonts/inter-regular.woff2') format('woff2');
  font-weight: 400;
}
```

---
Generated: 2026-01-29 | Agent: H3 Haiku | Phase 100
