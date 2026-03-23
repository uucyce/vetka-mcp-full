# ROADMAP C: UX Excellence — FCP7 Parity UI
**Date:** 2026-03-23
**Owner:** Gamma (claude/cut-ux)
**Mandate:** Commander's Final Orders — "каждая панель функциональна, не заглушка"
**Sources:** FCP7 User Manual (Ветхий завет), CUT_Interface_Architecture_v1.docx (Новый завет)

---

## Strategic Pillars

### P1: Project Panel — FCP7 Ch.3-4 (THE FOUNDATION)
**Priority:** 1 | **Complexity:** High | **Deps:** None
**Why first:** Every NLE session starts here. Without a functional Project panel,
the editor cannot organize media. This is the #1 gap between CUT and a real NLE.

| ID | Task | FCP7 Ref | Owner |
|----|------|----------|-------|
| P1.1 | Bin system (folders for organizing clips) | Ch.3 §Browser | Gamma |
| P1.2 | Column view: Name, Duration, In, Out, Media Start, Reel | Ch.4 §Columns | Gamma |
| P1.3 | Sort by any column (click header) | Ch.4 §Sorting | Gamma |
| P1.4 | Search/filter clips (real-time text input) | Ch.4 §Find | Gamma |
| P1.5 | Drag from Project → Source monitor (load clip for preview) | Ch.3 §Loading | Gamma → Beta (media) |
| P1.6 | Drag from Project → Timeline (insert at playhead) | Ch.3 §Insert | Gamma → Alpha (timeline) |
| P1.7 | Clip metadata display (codec, resolution, fps, audio channels) | Ch.4 §Item Props | Beta (probe) → Gamma (UI) |

### P2: Effects Browser Depth — FCP7 Ch.13
**Priority:** 2 | **Complexity:** Medium | **Deps:** GAMMA-36 (browser skeleton done)

| ID | Task | FCP7 Ref | Owner |
|----|------|----------|-------|
| P2.1 | Drag effect → clip on timeline (apply) | Ch.13 §Applying | Gamma (drag) → Alpha (handler) |
| P2.2 | Drag transition → edit point (apply between clips) | Ch.13 §Transitions | Gamma (drag) → Alpha (handler) |
| P2.3 | Favorites system (star/unstar effects, persist localStorage) | Ch.13 §Favorites | Gamma |
| P2.4 | Effect preview tooltip on hover (description + parameters) | Ch.13 §Preview | Gamma |
| P2.5 | Recently Used category (auto-populated, top of list) | — | Gamma |

### P3: Keyboard Shortcuts Window — FCP7 Window Menu
**Priority:** 3 | **Complexity:** High | **Deps:** useHotkeyStore (Gamma)

| ID | Task | Ref | Owner |
|----|------|-----|-------|
| P3.1 | useHotkeyStore — custom override persistence (localStorage) | ROADMAP_C2 R6.1 | Gamma |
| P3.2 | Visual keyboard layout (SVG or grid, highlight bound keys) | Premiere ref | Gamma |
| P3.3 | Search by action name (filter shortcut list) | — | Gamma |
| P3.4 | Switchable presets: FCP7 / Premiere / DaVinci / Custom | — | Gamma |
| P3.5 | Conflict detection + resolution dialog | — | Gamma |
| P3.6 | Export/import presets (JSON file) | — | Gamma |

### P4: Visual Polish
**Priority:** Ongoing | **Complexity:** Low-Medium | **Deps:** Delta QA findings

| ID | Task | Owner |
|----|------|-------|
| P4.1 | Kill ALL remaining color violations (Delta creates tasks) | Gamma + Delta |
| P4.2 | Consistent typography audit (font sizes, weights, families) | Gamma |
| P4.3 | Panel resize handle visibility (subtle sash highlight) | Gamma |
| P4.4 | Loading states for all panels (skeleton placeholders) | Gamma |
| P4.5 | Empty states for all panels (helpful text, not blank) | Gamma |

---

## Execution Order

```
Phase 1 (NOW):
  P1.1-P1.4  — Project Panel internals (Gamma solo)
  P2.3       — Effects Favorites (quick win)

Phase 2 (after P1 core):
  P1.5-P1.6  — Cross-panel DnD (coordinate Alpha/Beta)
  P2.1-P2.2  — Effect apply DnD (coordinate Alpha)

Phase 3 (polish):
  P3.1-P3.6  — Keyboard Shortcuts window
  P4.*       — Visual polish sweep

Phase 4 (deep):
  P1.7       — Clip metadata (needs Beta probe integration)
  P2.4-P2.5  — Effect preview + recently used
```

## Delegation Protocol

- **Gamma → Alpha:** Timeline drop handlers (P1.6, P2.1, P2.2)
- **Gamma → Beta:** Media preview/probe (P1.5, P1.7)
- **Gamma → Delta:** QA gate before every merge
- **Delta → Gamma:** Color violation tasks (P4.1)

## Cross-References

- FCP7 User Manual: Ch.3 (Browser), Ch.4 (Managing), Ch.13 (Effects)
- CUT_Interface_Architecture_v1.docx: §3 (Panels), §5 (Effects Pipeline)
- ROADMAP_C2_UX_REMAINING.md: R5-R7 (predecessor roadmap)
- EFFECTS_BROWSER_ARCHITECTURE.md: drag protocol spec

---

*"Every panel must be functional, not a stub." — Commander, 2026-03-23*
