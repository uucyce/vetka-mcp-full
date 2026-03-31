# Parallax UI Operator Recon Roadmap

Date: `2026-03-29`
Project: `parallax`
Workspace source of current UI state: `photo_parallax_playground_codex/photo_parallax_playground`

## 1. Purpose

This roadmap formalizes the current UI cleanup pass for `photo_parallax_playground`.

It exists because the latest UI work was advanced through direct screenshot feedback and handoff, while the next operator-facing cleanup steps were not yet explicitly represented as TaskBoard items.

This document is limited to:

- operator-facing UI structure;
- contextual tool reveal;
- monitor/stage presentation;
- bottom workspace reservation for future camera keyframes;
- QA for portrait and square layouts.

It explicitly does **not** introduce new processing features or new product flows.

## 2. Factual Inputs

Primary sources used for this roadmap:

- `photo_parallax_playground_codex/photo_parallax_playground/HANDOFF_TO_FRESH_CHAT_UI_2026-03-29.md`
- `photo_parallax_playground/src/App.tsx`
- `photo_parallax_playground/src/index.css`
- user-provided UI references:
  - DaVinci Resolve Depth Map Effects
  - Aiarty Image Matting screenshots

## 3. Current State In Code

### 3.1. What is already better

The current handoff correctly reflects that the UI moved toward a cleaner viewer-first structure:

- right-side `Depth / Isolate / Camera / Export` workflow cards exist in the main path;
- the main monitor is centered in the layout;
- `Debug Snapshot` is not part of the default visible layout;
- some auxiliary controls were already demoted from the always-open path.

### 3.2. What is still structurally wrong

The following issues are directly visible in the current code:

1. A large amount of tooling still lives behind `debugOpen` instead of a clear operator workflow.
   - `Focus Proxy`, `Guided Hints`, `Stage Tools`, `Algorithmic Matte`, `Hint Brushes`, `Merge Groups`, and `AI Assist` render only inside the `debugOpen` block in `src/App.tsx`.

2. The right-side operator cards are still permanently expanded sheets, not accordion-style effect sections.
   - `Depth`, `Isolate`, `Camera`, and `Export` each render their full control payload at once in `workflow-dock`.

3. `Export` remains a fully open readout instead of a compact action section.

4. The stage still carries decorative/non-editor framing that weakens the "real monitor" feel.
   - `focus-frame` uses a `border-radius: 28px`.
   - stage overlays still favor visual chrome over strict rectangular image reading.

5. The lower area is not reserved as a purposeful authoring strip.
   - `bottom-panels` only appear in `debugOpen`.
   - there is no stable bottom lane for camera keys or timeline-like animation authoring.

6. Tool-to-canvas causality is weak.
   - stage interactions exist in the pointer surface (`hint-editor-surface`), but the UI still explains them as debug/manual internals instead of exposing a clear "select object / refine / matte / brush" operator path.

## 4. Operator Model To Target

The target model is derived from the supplied references and current product scope:

1. Use section headers that can expand when needed.
2. Do not keep post-extract repair tools visible before the operator is in a repair context.
3. Keep the monitor rectangular and visually primary.
4. Present fewer always-visible controls, with stronger causal linkage between:
   - current stage;
   - current selection;
   - available tools.
5. Reserve a bottom strip for future camera animation authoring, but in this phase only establish the spatial shell and interaction boundary, not full CUT integration.

## 5. Ordered Work

### Track UI-A. Remove hidden-debug workflow dependency

Goal:

- stop treating operator tools as debug-only;
- separate `debug diagnostics` from `authoring tools`.

Must do:

- identify which controls belong to the real operator path;
- move those controls out of `debugOpen` gating;
- keep pure diagnostics behind debug.

Done criteria:

- the operator can access real layer/matte/selection tools without opening a debug-only mode;
- debug pane remains diagnostic, not workflow-critical.

### Track UI-B. Convert right dock into compact effect inspector

Goal:

- make the right side behave closer to Resolve-style effect sections.

Must do:

- turn `Depth`, `Isolate`, `Camera`, and `Export` into collapsible sections;
- keep only short summaries visible when collapsed;
- ensure only the active section expands by default.

Done criteria:

- right dock reads as a compact inspector, not as four open forms;
- `Export` becomes compact like the other sections.

### Track UI-C. Contextualize post-extract cleanup

Goal:

- stop presenting cleanup tools as a permanent sheet.

Must do:

- show cleanup tools only when extraction/selection cleanup is active;
- make brush, matte, and grouping tools appear as contextual operator tools;
- keep inactive tools hidden until the workflow justifies them.

Done criteria:

- no long always-open "manual cleanup" slab remains in the primary path;
- repair tools appear only when the operator enters that mode.

### Track UI-D. Normalize monitor and visual hierarchy

Goal:

- remove UI styling that makes the image feel like a decorative card.

Must do:

- remove rounded monitor treatment and decorative frame cues that do not belong to photo/video monitoring;
- reduce badge/color noise;
- preserve image dominance over inspector chrome.

Done criteria:

- the stage reads as a monitor, not a rounded widget;
- visual hierarchy clearly favors the image.

### Track UI-E. Reserve bottom animation lane

Goal:

- create the structural bottom zone for future camera key authoring.

Must do:

- reserve stable vertical space under the monitor;
- avoid importing full CUT complexity into this playground;
- define the bottom lane as a shell for camera animation work only.

Done criteria:

- the layout no longer collapses the bottom zone away;
- there is a clear placeholder/shell for future camera keyframes.

### Track UI-F. Portrait and square QA

Goal:

- verify that the cleaned layout still protects monitor priority on non-16:9 samples.

Must do:

- run portrait and square checks after the structural cleanup;
- verify that dock scrolling does not displace the image;
- verify that contextual tools do not overwhelm narrow heights.

Done criteria:

- portrait and square samples remain usable;
- monitor stays dominant;
- inspector and bottom lane remain controlled.

## 6. Scope Guard

This roadmap does not authorize:

- new AI assistant panels;
- new permanent left-column control families;
- deep CUT timeline integration in this pass;
- new backend extraction logic;
- new routing/export semantics.

This phase is UI structure and operator clarity only.

## 7. Immediate Execution Slice

The next execution slice should be:

1. formalize operator tools vs debug diagnostics;
2. convert the right dock to a compact accordion inspector including `Export`;
3. remove rounded/decorative monitor treatment and reduce badge noise;
4. establish bottom lane reservation for future camera keys;
5. run portrait/square QA;
6. only after that, wire missing functions into the cleaned UI.
