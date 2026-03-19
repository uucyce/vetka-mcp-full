# RECON: CUT UI Layout — PULSE, Tools, Toolbar
**Date:** 2026-03-19
**Source:** Grok research (user-relayed)
**Status:** APPROVED by user

---

## 1. PULSE Placement

### Problem
PULSE dropdown lives in timeline tab bar. This is wrong — PULSE is a DAG-level capability, not a timeline feature.

### Decision
- **Remove** PULSE dropdown from timeline tab bar entirely
- **PULSE** = internal system name, never shown in UI
- **User-facing name:** "Auto Cut"

### Where Auto Cut lives
1. **DAG / Graph panel** — right-click context menu on scene nodes
2. **Inspector panel** — button when scene is selected
3. **NOT** on timeline toolbar, NOT in tab bar

### Auto Cut modes (renamed)
| Old | New |
|-----|-----|
| Favorites Cut | From Favorites |
| Script Cut | Follow Script |
| Music Cut | Match Music |

### Context menu (DAG scene node)
```
Right-click SCN_03:
  Open in Source
  Add to Timeline
  ─────────────
  Auto Cut >
    From Favorites
    Follow Script
    Match Music
  ─────────────
  Explore Alternatives
```

### BPM / Rhythm Track
- **OFF by default**
- Toggle: "Rhythm" in timeline toolbar
- When ON: single simplified dot-line (not 4 engineering tracks AUD/VIS/SCR/SYN)
- Simplify to max 2 lines: Audio (green) + Story (white)

### Core principle
```
DAG = space of possibilities
PULSE = explores/selects paths through that space
Timeline = linear projection of selected path

Timeline is a result surface, not a control surface.
```

---

## 2. Tools

### Problem
U (undo), V (selection), C (razor), LK (linked selection) are crammed into timeline toolbar. These are 3 different UI levels mixed together.

### Categories (must not mix)
| Category | Examples | UI Location |
|----------|----------|-------------|
| **Tools** (cursor modes) | Selection, Razor, Hand, Zoom | Hotkeys only (V, C, H, Z) |
| **Actions** (operations) | Undo, Export | Hotkeys (Cmd+Z) / menus |
| **Toggles** (state) | Snap, Linked Selection | Timeline toolbar icons |

### MVP Tools (hotkey-only, no panel)
| Key | Tool | Cursor |
|-----|------|--------|
| V | Selection | Default pointer |
| C | Razor | Knife icon |
| H | Hand | Palm icon |
| Z | Zoom | Magnifier icon |

### NOT tools (remove from tools area)
- **Undo (U)** → Cmd+Z, Edit menu, History panel
- **Linked Selection (LK)** → toggle icon (chain) in toolbar, Cmd+L

### No floating Tools panel in MVP
- CUT follows FCP model: hotkeys > panels
- No tool options bar needed

---

## 3. Timeline Toolbar

### Problem
Current toolbar mixes tools + toggles + actions + export = chaos.

### Final layout (MVP)
```
LEFT                              RIGHT
[magnet] [chain]        Zoom ────────

 Snap     Linked        Zoom slider
```

### Allowed in toolbar
- Snap toggle (magnet icon)
- Linked Selection toggle (chain icon)
- Zoom slider
- (optional) Rhythm toggle

### NOT allowed in toolbar
- V / C (tools) — cursor modes, use hotkeys
- Undo — Cmd+Z
- Export — File > Export menu
- AI buttons — belong to DAG context
- Scene detect — not toolbar level

### Export location
File > Export > Master / Social / XML

### Principle
```
Toolbar controls STATE, not ACTIONS.
```

---

## 4. Interaction Flows (canonical)

### Flow 1: Script > Film (narrative)
1. Import Script → Script Panel populates → DAG builds spine
2. Import footage → auto-link to scenes
3. Select scene in DAG → Source shows raw
4. Auto Cut > Follow Script → creates cut-00
5. Editor refines → cut-01, cut-02

### Flow 2: Footage > Script (documentary)
1. Import footage → Generate Script
2. System transcribes, groups, generates Script
3. DAG appears → Auto Cut
4. Editor refines

### Flow 3: Explore Alternatives
1. Click scene in timeline → DAG highlights
2. "Explore Alternatives" → variants A/B/C
3. Preview in Source → drag to timeline

### Flow 4: Music Driven
1. Add music → Auto Cut > Match Music
2. Enable Rhythm toggle → see beat dots
3. Manual refinement

### Flow 5: Versioning
```
[cut-00] (AI) [cut-01] (Music) [cut-02 ★] (Editor)
```
- Switch between tabs
- Each is a full timeline version
- DAG = source of truth, Timeline = selected path

---

## 5. Track Headers

### Problem
Buttons (●, L, S, M) overlap at 76px width. Speaker icon renders as garbage.

### Fix
- Increase track header min-width to 100px
- Grid layout for buttons: 2x2
- Proper SVG icons (white monochrome, no emoji)
- Layout: `[● L] [S M]` with 2px gap

---

## References
- Premiere Tools panel: 12+ tools, separate floating window
- DaVinci: panel + hotkeys
- FCP: almost hotkey-only (closest to CUT model)
- Avid: classic heavy panel
