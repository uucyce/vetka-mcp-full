# HANDOFF TO FRESH CHAT — UI CONTINUATION — 2026-03-29

Updated: `2026-03-29 11:40:48 MSK`

## Workspace
- Worktree: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/photo_parallax_playground`
- Branch: `codex/parallax`
- Main edited files:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/photo_parallax_playground/src/App.tsx`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/photo_parallax_playground/src/index.css`

## Live Check
- Dev URL used for checks:
  - `http://127.0.0.1:14350/?sample=hover-politsia&debug=1&fresh=1`
- Playwright reload was used repeatedly during the session.
- Latest verified snapshot:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/.playwright-cli/page-2026-03-29T08-40-04-502Z.yml`
- Latest build status:
  - `npm run build` passed

## What Was Changed

### 1. Overall UI direction shifted closer to Resolve
- `Debug Snapshot` removed from the default working layout.
- `Export` moved to the right-side inspector column.
- Main image monitor was given more visual priority.
- Right-side `Depth / Extract / Camera` stopped behaving like three large always-open cards.

### 2. Right-side inspector now behaves more like compact effect sections
- `Depth / Extract / Camera` are now collapsed by default.
- Each shows a one-line summary when closed:
  - `Depth`: `near / far / gamma`
  - `Extract`: `mask / mid`
  - `Camera`: `x / y / overscan`
- Only one effect section opens at a time through `activeEffectPanel`.
- Right inspector now has its own scroll:
  - `workflow-dock { overflow: auto; max-height: min(78vh, 920px); }`

### 3. Left rail was heavily cleaned up
- Removed `Stage` as a separate left panel.
- Removed `AI Assist` from the working left column.
- Removed `Layer Guides` from the working left column.
- Top-left brand block was demoted to a compact project label instead of a second control panel.
- `Objects and Route Notes` stayed folded by default and was compacted.

### 4. `Manual Cleanup` no longer opens as a long scroll of all tools
- `After Extract: Manual Cleanup` still exists, but now behaves as a tool picker.
- It now opens into:
  - a compact row of rescue tools
  - one active tool panel only
- Active cleanup tool is controlled by:
  - `activeCleanupTool: "focus" | "hints" | "stage" | "matte" | "brushes" | null`
- Current tool list:
  - `focus proxy`
  - `guided hints`
  - `stage tools`
  - `algorithmic matte`
  - `hint brushes`
- If no cleanup tool is selected, user sees only an empty helper state instead of a long settings sheet.

### 5. Context-sensitive cleanup tools
- `protect region` now opens cleanup and selects `hint brushes`
- `refine silhouette` now opens cleanup and selects `algorithmic matte`

### 6. Support / object controls
- `object role` was clarified as real functionality, not decorative UI.
- It now reads as `layer role`.
- UI note was added explaining it changes layer routing for preview / camera safety / export order.
- Left-rail support typography was reduced significantly.

## Important Current Behavior
- The monitor remains in the center.
- Left rail has its own scroll.
- Right effect inspector has its own scroll.
- `Depth / Extract / Camera` start collapsed.
- `Manual Cleanup` starts collapsed, and when opened it does not dump all subtools at once anymore.

## Remaining Gaps

### 1. Manual Cleanup still needs one more Resolve/Airy pass
Current state is much better, but it is still a rail section, not yet a truly minimal context-tool system.

Best next step:
- demote the cleanup section even further
- make its tool row feel more like contextual helper tools
- open tool controls only when the corresponding stage mode or recommendation is activated

### 2. `Export` is still more open than the other right-side sections
Best next step:
- make `Export` compact and accordion-like too
- keep actions visible, but reduce always-open readout bulk

### 3. Non-16:9 / portrait behavior still needs a dedicated final pass
Current layout improved monitor priority, but this still needs explicit QA across multiple samples.

Best next step:
- verify on portrait and square samples
- ensure monitor always stays dominant
- ensure effect inspector scrolling never displaces the image

### 4. Some technical console noise still exists
Known recurring issues observed during Playwright reloads:
- duplicate React key warning:
  - `rejected_fg_box`
- repeated canvas warning:
  - `getImageData` / `willReadFrequently`

These were not the focus of this UI session and were not fully resolved here.

## Recommended Next Move For Fresh Chat
Continue from current workspace state and do this next:

1. Keep the current compact right-side inspector pattern.
2. Apply the same compact/collapsed treatment to `Export`.
3. Push `Manual Cleanup` one step further toward contextual helper tools:
   - show tools only when needed
   - avoid a permanent left-column sheet
4. Run explicit portrait / square QA after that.

## Quick State Summary
- Large progress was made.
- UI is materially cleaner than the starting point.
- The biggest conceptual shift already happened:
  - monitor-first center
  - compact right-side inspector
  - auxiliary tools no longer permanently flood the layout
- The next chat should focus on polish and contextual cleanup behavior, not on returning to the old card-heavy layout.
