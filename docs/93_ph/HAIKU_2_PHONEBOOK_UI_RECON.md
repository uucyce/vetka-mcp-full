# Phase 93: Phonebook UI Reconnaissance

**Agent:** Haiku
**Date:** 2026-01-25
**Status:** COMPLETE

---

## 1. COMPONENT

**Path:** `client/src/components/ModelDirectory.tsx`
**Lines:** 1199
**Style:** Inline only (no external CSS)

---

## 2. COLOR SCHEME

### Grayscale Palette (Phase 80.3: "GRAYSCALE ONLY")

| Element | Color | Hex |
|---------|-------|-----|
| Background dark | #0a0a0a | ![](https://via.placeholder.com/15/0a0a0a/0a0a0a) |
| Background medium | #111, #1a1a1a | |
| Background light | #222, #333 | |
| Borders | #1a1a1a - #555 | |
| Text dark | #444, #555 | |
| Text medium | #666, #888 | |
| Text light | #aaa, #ccc | |

### Status Dots (Monochrome)
| Type | Color |
|------|-------|
| MCP Agents | #888 |
| Voice Models | #666 |
| Local Models | #777 |
| Cloud Models | #444 |

### Toast Colors
| Type | Background | Text |
|------|------------|------|
| Error | #2a1a1a | #a86 |
| Success | #1a2a1a | #6a8 |

---

## 3. BLUE COLOR FOUND

**Primary VETKA Blue:** `#4a9eff`
**NOT in ModelDirectory** (grayscale design)

**Found in ScanPanel:**
```css
/* ScanPanel.css */
Progress gradient: #5c8aaa → #7ab3d4
Box shadow: rgba(122, 179, 212, 0.3)
File counter: #7ab3d4
```

**Recommendation:** Use `#7ab3d4` for online status (matches existing scanner blue)

---

## 4. TYPOGRAPHY

| Element | Size | Weight |
|---------|------|--------|
| Title | 16px | bold |
| Model name | 13px | 500 |
| ID/meta | 11px, 10px | normal |
| Badges | 9px | normal |
| Labels | 10px | uppercase |

**Font:** Inherit (system)

---

## 5. ICONS

**Source:** lucide-react library

### Main Icons:
```
Phone, Search, X, Bot, Cpu,
DollarSign, Layers, Home, Zap,
Crown, Mic, Terminal, Key,
ChevronDown, ChevronUp, Volume2
```

**Size:** 16-18px (SVG)

---

## 6. LAYOUT

```
PANEL (380px)
├─ HEADER (16px padding)
│  ├─ Title + close
│  └─ Search input
├─ MAIN (flex)
│  ├─ SIDEBAR (54px) ← vertical tabs
│  └─ MODEL LIST (flex: 1)
└─ API KEYS DRAWER
   └─ Collapsible
```

---

## 7. CURRENT STATUS DISPLAY

**Model status:** Monochrome dots only
**API key status:** Text badges (active/backup/invalid/rate_limited)
**Ollama status:** Gray dots (#888 running, #444 stopped)

**Missing:**
- ❌ Online/offline indicator
- ❌ Last seen timestamp
- ❌ OpenRouter badge

---

## RECOMMENDATIONS

1. **Online status dot:** Use `#7ab3d4` (scanner blue)
2. **Offline status dot:** Use `#555` (existing gray)
3. **Last seen:** Add small text below model name
4. **OpenRouter badge:** Small "OR" label in corner
