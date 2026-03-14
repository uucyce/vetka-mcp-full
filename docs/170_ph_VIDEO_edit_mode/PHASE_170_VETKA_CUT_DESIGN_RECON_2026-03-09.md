# PHASE 170 VETKA CUT Design Recon
**Date:** 2026-03-09  
**Status:** Recon complete, UI rules v1 frozen for current shell slice  
**Scope:** style unification for `VETKA CUT` without forcing MCP/API rewrites

## Why now
`CUT` already has stable-enough shell contracts for the current slice:
- `project-state`
- worker outputs: `waveform`, `transcript`, `thumbnail`
- worker queue visibility
- storyboard strip baseline

That is the right point for design recon: after first shell/runtime contracts exist, before rich timeline and smart inspector complexity starts.

## Source set reviewed
1. `client/src/utils/dagLayout.ts`
2. `client/src/components/mcc/MyceliumCommandCenter.tsx`
3. `client/src/components/mcc/FooterActionBar.tsx`
4. `client/src/components/mcc/MiniContext.tsx`
5. `client/src/components/mcc/CaptainBar.tsx`
6. `client/src/components/search/UnifiedSearchBar.tsx`
7. `client/src/WebShellStandalone.tsx`
8. `client/src/CutStandalone.tsx`
9. `docs/118_ph/PHASE_118_ICON_REFACTOR_RECON.md`
10. `docs/165_MCC_search_context/PHASE_165_MCC_CONTEXT_SEARCH_RECON_MARKERS_2026-03-07.md`

## Main conclusion
`CUT` should not invent a new visual language.

The strongest current VETKA/MYCELIUM UI language is:
- dark monochrome base,
- thin gray borders,
- white/gray text hierarchy,
- simple iconography,
- contextual action bars,
- compact smart panels instead of many permanent sidebars.

`CUT` should inherit that language, then add only editorial-specific surfaces: storyboard strip, timeline lanes, inspector, scene graph overlays.

## Current VETKA design truth
### 1. Palette baseline already exists
The cleanest shared palette source is `NOLAN_PALETTE` in `client/src/utils/dagLayout.ts`.

It already defines:
- black backgrounds,
- gray borders,
- white/gray text hierarchy,
- grayscale status colors.

This is a better baseline for `CUT` than the current blue-accent shell in `client/src/CutStandalone.tsx`.

### 2. Icons are split across two systems
There are two live icon approaches:
- `lucide-react` for many app surfaces (`App.tsx`, `ChatPanel.tsx`, `MessageBubble.tsx`, viewers),
- inline SVG/custom icons in search/web shell (`UnifiedSearchBar.tsx`, `WebShellStandalone.tsx`).

For `CUT`, the correct direction is:
- simple monochrome icons,
- no emoji as primary runtime language,
- prefer `lucide-react` or inline monochrome SVG where tighter control is needed.

This matches the older icon cleanup direction in `docs/118_ph/PHASE_118_ICON_REFACTOR_RECON.md`.

### 3. VETKA already moved toward contextual controls
The best existing precedent is not a giant toolbar, but:
- `FooterActionBar.tsx`: max 3 context-aware actions,
- `MiniContext.tsx`: entity-aware panel content,
- `CaptainBar.tsx`: inline recommendation banner,
- MCC mini-windows instead of fixed full-height side panels.

This is directly aligned with your `swedish buffet` principle:
- available actions are visible,
- the surface changes by context,
- but the screen is not overloaded by permanent controls.

### 4. CUT shell currently diverges
`client/src/CutStandalone.tsx` is useful as a runtime shell, but visually it is not yet on the shared design language:
- custom blue primary accent,
- local ad-hoc tokens,
- no shared palette import,
- cards/panels are close in spirit, but not aligned to `NOLAN_PALETTE`.

So the next UI pass should be a style-system alignment pass, not a new design invention.

## CUT UI rules v1
### Palette
- Base background: black / near-black only.
- Surface layers: `bg`, `bgDim`, `bgLight` pattern from `NOLAN_PALETTE`.
- Borders: thin gray lines, no bright color borders by default.
- Text hierarchy: white primary, gray secondary, dim gray tertiary.
- Color should be rare and semantic-only; default `CUT` surface stays monochrome.

### Icons
- Use simple white/gray icons.
- No emoji in core editorial runtime surfaces.
- Use icon-first controls only where meaning stays obvious.
- Prefer one consistent icon family per surface.

### Shapes
- Small radii: `4-10px`.
- Panels/cards: thin border + dark fill, not glossy gradients.
- Inputs/buttons: compact, rectangular-soft, no oversized rounded consumer-app styling.

### Panels
- Prefer smart contextual panels over fixed always-open inspector columns.
- Each panel must answer one question:
  - what is selected,
  - what can I do now,
  - what changed,
  - what is processing.
- Avoid spawning new panel types if the same information can live in a contextual inspector block.

### Contextual buttons
- Max 3 primary context actions visible per local scope.
- Extra actions go into overflow or panel-local rows.
- Action sets must change by current selection/runtime state.
- `CUT` should reuse MCC’s “few strong actions” pattern, not an NLE-style giant toolbar at first.

### Swedish buffet principle
Interpretation for `CUT`:
- many relevant actions are available,
- but only the actions for the current context are emphasized,
- the rest are nearby, not globally screaming.

Concrete `CUT` mapping:
- no clip selected -> project/storyboard actions,
- clip selected -> trim/move/take/note actions,
- scene selected -> scene graph / note / alt-take actions,
- active worker jobs -> cancel/retry/status actions,
- no permanent full control ribbon until edit grammar stabilizes.

## What should change next
### Safe now
These changes are safe now and should not force endpoint rewrites:
1. Refactor `CutStandalone` to shared design tokens based on `NOLAN_PALETTE`.
2. Replace any emoji/action-language drift with monochrome icons.
3. Re-group shell cards into:
   - bootstrap/project,
   - storyboard,
   - queue/runtime,
   - inspector.
4. Add auto-refresh while `active_jobs > 0`.

### Not yet
These should wait:
1. rich timeline chrome,
2. node-canvas visual design system,
3. deep inspector branching,
4. animation-heavy UI language,
5. permanent multi-toolbar layout.

Reason: those layers depend on editor interaction grammar that is not frozen yet.

## Recommended design implementation order
1. Align `CutStandalone` to `NOLAN_PALETTE`.
2. Introduce monochrome icon set for CUT shell actions.
3. Convert right rail into contextual smart inspector sections.
4. Add auto-refresh and subtle job-state visuals.
5. Then design the first real editorial timeline/stage layout.

## Decision
For current Phase 170 scope:
- design recon is complete,
- API rewrite is not required,
- the next design step should be shell alignment, not endpoint redesign.

## Markers
1. `MARKER_170.UI.DESIGN_UNIFICATION_RECON`
2. `MARKER_170.UI.SMART_PANELS_CONTEXTUAL_ACTIONS`
3. `MARKER_170.UI.STORYBOARD_THUMBNAILS_V1`
