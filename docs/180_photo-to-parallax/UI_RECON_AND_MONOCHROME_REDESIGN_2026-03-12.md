# UI Recon And Monochrome Redesign

## Goal

Move the parallax lab from research-sandbox UI to a compact operator surface:

- monochrome only,
- 16:10 friendly,
- no essential controls below the fold,
- depth-first workflow,
- research tools hidden behind debug.

## Recon 1: VETKA / MCC

Sources reviewed:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/README.md`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/docs/showcase/05-left-rail.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/docs/showcase/08-wide-layout.png`

Signals worth reusing:

- low-noise black-and-white operator look;
- strong zoning instead of decorative cards;
- left rail for task entry, center workspace for the main artifact, right side for detail/debug;
- compact typography and restrained accents;
- dock / drawer logic instead of endless stacked panels.

Conclusion:

The parallax tool should not look like a toy editor. It should inherit MCC discipline:
calm monochrome shell, dense but readable controls, central workspace first.

## Recon 2: Other Tools

Primary behavioral references:

- DaVinci Resolve depth-map inspector mental model
- After Effects / compositing inspector layouts

Patterns consistently worth copying:

- center viewer is primary;
- controls grouped by job, not by implementation detail;
- source/import first, image interpretation second, motion third, export last;
- drawer/accordion sections beat long control stacks;
- advanced controls are present but not always visible.

Conclusion:

The correct product structure is:

1. Import
2. View
3. Depth
4. Isolate
5. Camera
6. Export

Everything else belongs to debug.

## Recon 3: Current Lab

Problems in the existing sandbox before redesign:

- too many vertically stacked cards;
- research controls competing with user controls;
- colored accents pulled attention away from depth review;
- motion and export were mixed with internal experimentation;
- stage overlays exposed too much internal state in normal mode.

Useful pieces to keep:

- real B/W depth preview;
- DaVinci-like remap controls;
- stage-centered preview;
- debug pane for internal metrics.

## Redesign Policy

User-facing controls:

- Import
- View
- Depth
- Isolate
- Camera
- Export

Hidden in debug:

- Focus Proxy
- Guided Hints
- Stage Tools
- Algorithmic Matte
- Hint Brushes
- Merge Groups
- AI Assist

## Layout Target

- left rail: compact operator drawers;
- center: viewer and main stage;
- right pane: debug only when opened;
- no color dependency for understanding state;
- SVG icons only, monochrome strokes.

## Implementation Notes

Applied in this wave:

- monochrome shell replaces orange/blue gradients;
- left rail reduced to compact clustered sections;
- drawer state introduced for `Depth`, `Isolate`, `Camera`;
- export surfaced as a dedicated compact block;
- stage badges simplified in non-debug mode.

Still to do:

- tighten stage header metrics further;
- reduce visual weight of sample chooser;
- align final spacing against a strict 16:10 screenshot review;
- move any remaining non-essential motion internals to debug.
