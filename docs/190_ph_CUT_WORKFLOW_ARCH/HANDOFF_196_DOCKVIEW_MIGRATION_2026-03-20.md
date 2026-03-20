# HANDOFF: Phase 196 — Dockview Migration Session
**Date:** 2026-03-20
**Agent:** Opus (Claude Code), worktree `relaxed-rosalind`
**Duration:** 1 session
**Commits:** 5 (MARKER_196.1 — MARKER_196.5)

---

## 1. What Was Done (5 commits)

| Commit | MARKER | What |
|--------|--------|------|
| `9ff38011d` | 196.1 | Hotkeys: 30+ NLE hotkeys wired via `useCutHotkeys`. JKL shuttle, Space, Cmd+K split, I/O marks, V/C tools, zoom, frame stepping. Preset-aware (Premiere/FCP7/Custom). |
| `72d227909` | 196.2 | DOCK-1: `dockview-react` installed, `DockviewLayout.tsx` wrapper, `useDockviewStore`. Panel registry (10 panels), default layout, dark theme CSS. Does NOT replace CutEditorLayoutV2 yet. |
| `4e07b0c6b` | 196.3 | DOCK-2: Full migration. PanelGrid + PanelShell replaced with DockviewLayout. All 10 panels dockable. 5-zone drop targets, tab reorder, drag-to-dock, floating panels. Layout auto-persists to localStorage. |
| `4a43b6d1e` | 196.4 | DOCK-3: Compact theme. Tabs 18px (was 35px), font 9px, monochrome grey. Single-tab groups 14px. Active tab #1a1a1a, inactive #111. |
| `0893c8e57` | 196.5 | DOCK-FIX: CSS nuclear override to kill blue accents. All backgrounds #000, borders #222, text #ccc/#888/#555 from CUT tokens. |

## 2. What Did NOT Work

### 2.1 Blue Borders Still Visible
Despite MARKER_196.5 nuclear CSS override with `*:not()` selector, **blue/purple borders are still visible** at panel edges. The screenshot from user confirms this.

**Root cause analysis:**
- Used `*:not(.lane-clip):not(.marker-dot)` which should catch everything
- Dockview likely injects inline styles or uses shadow DOM elements that CSS specificity doesn't reach
- Need to inspect in browser devtools to find the EXACT elements leaking blue
- May need `!important` on specific dockview internal class names, not wildcard

**What to do:** Open browser devtools, hover the blue borders, find the exact CSS class/element. Override that specific class. Don't use `*` wildcards — they're unreliable with component libraries.

**Color source:** Use CUT tokens.css palette exclusively: `--border-dim: #222`, `--bg-primary: #000`. Zero custom hex values.

### 2.2 Timeline is Still ONE Panel
TimelineTabBar is rendered INSIDE a single dockview panel. This means:
- User cannot drag individual timelines to dock elsewhere
- Cannot split two timelines side-by-side via dockview
- Cannot float a single timeline
- Dockview provides zero value for timeline management

**This defeats the purpose of dockview for CUT.**

**What to do:** See `RECON_TIMELINE_MULTI_INSTANCE_2026-03-20.md` — Active + Snapshot approach. Each timeline version = separate dockview panel. Delete TimelineTabBar.

### 2.3 Tab Headers Too Fat
Even after MARKER_196.4 compact theme (18px tabs), the dockview headers still consume significant space. Each panel has: tab bar + close button + chevron. With 10+ panels visible, this is ~200px of wasted vertical space.

**What to do:** Consider hiding tab bars for single-panel groups entirely. Dockview supports `tabHeight: 0` per group. Show tabs ONLY when a group has 2+ panels.

## 3. Protocol Lessons

### 3.1 What Went Wrong
1. **Rushed to code without full recon** — Timeline multi-instance was marked "multi-instance capable" in recon but NOT actually designed. Implementation was deferred to "Phase 2" but Phase 1 shipped without it.
2. **CSS nuclear override instead of targeted fix** — Used `*:not()` selector instead of identifying exact dockview classes. This is a hack, not a fix.
3. **Did not verify in browser** — Committed CSS changes without opening devtools to confirm zero blue. User caught it.

### 3.2 What to Do Differently
1. **Timeline multi-instance FIRST** — This is the core value of dockview. Without it, dockview is just a heavier PanelGrid. Should have been Phase 1, not deferred.
2. **Devtools before commit** — For CSS work, ALWAYS inspect in browser before committing. Use `document.querySelectorAll('*')` + filter for blue border/background to programmatically verify.
3. **CUT tokens.css as single source** — Import tokens at dockview theme level. Never hardcode hex values in dockview-cut-theme.css.

## 4. Open Tasks (on TaskBoard)

| Task ID | Title | Priority | Status |
|---------|-------|----------|--------|
| `tb_1773969884_5` | DOCK-FIX-2: Kill remaining blue border accents | P1 | pending |
| `tb_1773969892_6` | DOCK-TIMELINE: Multi-instance timelines via dockview | P1 | pending |

## 5. Key Files

| File | What it does | State |
|------|-------------|-------|
| `client/src/components/cut/DockviewLayout.tsx` | Main dockview wrapper, panel registry, default layout | Working but timeline is single-panel |
| `client/src/components/cut/dockview-cut-theme.css` | Dark theme CSS for dockview | Incomplete — blue leaking |
| `client/src/components/cut/TimelineTabBar.tsx` | Internal timeline tabs | TO DELETE (replace with dockview panels) |
| `client/src/components/cut/TimelinePanelDock.tsx` | Timeline panel inside dockview | Must accept `params.timelineId` |
| `client/src/store/useCutEditorStore.ts` | Master store | Needs `timelineSnapshots` Map + snapshot/restore actions |
| `client/src/hooks/useCutHotkeys.ts` | 30+ NLE hotkeys | Working, preset-aware |

## 6. Recon Docs (for next session)

- `docs/190_ph_CUT_WORKFLOW_ARCH/RECON_PANEL_DOCKING_2026-03-19.md` — Library choice (dockview), migration plan
- `docs/190_ph_CUT_WORKFLOW_ARCH/RECON_TIMELINE_MULTI_INSTANCE_2026-03-20.md` — Active+Snapshot design, 5-step migration
- `docs/190_ph_CUT_WORKFLOW_ARCH/CUT_UNIFIED_VISION.md` — Full panel/function/hotkey spec

## 7. Recommendations for Next Session

1. **Start with DOCK-FIX-2** (tb_1773969884_5) — quick win, devtools inspect, find exact classes, kill blue
2. **Then DOCK-TIMELINE** (tb_1773969892_6) — the big one, follow 5-step migration in RECON
3. **Verify with user screenshot** after each change — don't trust CSS alone
4. **localStorage layout reset** — after timeline multi-instance, old saved layouts will break. Add version key to layout JSON, auto-reset on mismatch
