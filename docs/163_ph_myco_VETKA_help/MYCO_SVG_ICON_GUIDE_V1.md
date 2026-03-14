MARKER_163A_PLUS.MYCO.SVG_ICON_GUIDE.V1
LAYER: L2
DOMAIN: UI|TOOLS
STATUS: IMPLEMENTED
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_SVG_ICON_GUIDE_V1.md
LAST_VERIFIED: 2026-03-09

# MYCO SVG Icon Guide V1

## Synopsis
This is the implementation guide for MYCO inline SVG icons used inside deterministic hints. It is written so MCC can reuse the same pattern without re-learning the constraints from scratch.

## Table of Contents
1. Why this icon system exists
2. Design rules
3. Technical rules
4. Token contract
5. Authoring workflow
6. Anti-patterns
7. Copy rules
8. Cross-links
9. Status matrix

## Treatment
The icon system is not decorative. It exists to bind MYCO text to the exact control family the user sees in the UI.

## Short Narrative
If MYCO says `pin the result`, the user should see the same white pin shape in the hint that they will click in the panel. This reduces interpretation cost and makes deterministic hints feel attached to the runtime, not narrated from outside.

## Full Spec
### Why this icon system exists
- MYCO hints must reference real controls, not abstract verbs.
- White inline SVG icons make the hint visually point to the same control family as the UI.
- This is especially important for:
  - `pin`
  - `phonebook`
  - `history`
  - `scanner`
  - `folder`
  - `key`
  - `web`

### Design Rules
- Use simple white or near-white icons only.
- Match the existing VETKA or MCC control silhouette.
- Prefer outline icons over filled icons unless the real control is visibly filled.
- Keep icons visually quiet. MYCO is guidance, not branding chrome.
- Do not use emoji.
- Do not use colorful badges for deterministic hints.
- The icon must help recognition in under one second.

### Technical Rules
- Use inline React SVG, not remote assets, for deterministic hint text.
- Default icon box:
  - `width: 12`
  - `height: 12`
  - `viewBox: 0 0 24 24`
- Default styling:
  - `fill: none`
  - `stroke: currentColor`
  - `strokeWidth: 2`
  - `strokeLinecap: round`
  - `strokeLinejoin: round`
- Default inline placement:
  - `display: inline-block`
  - `verticalAlign: -2px`
  - `marginRight: 4-6px`
  - `color: #f2f5f7`

### Token Contract
Author hint copy with stable tokens inside text:
- `[[pin]]`
- `[[phone]]`
- `[[history]]`
- `[[scanner]]`
- `[[folder]]`
- `[[chat]]`
- `[[web]]`
- `[[file]]`
- `[[star]]`
- `[[key]]`

Runtime then resolves tokens with a deterministic renderer.

### Authoring Workflow
1. Identify the exact control the hint references.
2. Confirm the control exists in runtime.
3. Reuse an existing token if the silhouette already exists.
4. Add a new token only if the control family is genuinely new.
5. Render the token in both:
   - bottom MYCO guide lane
   - top unified MYCO lane
6. Browser-verify that raw token text never leaks to the user.

### Copy Rules
- Write the action in concrete form:
  - good: `Attach the result to chat context through [[pin]].`
  - bad: `Return the found item.`
- Mention the control the user can actually click.
- If the control is absent in this panel, do not mention it.
- If a flow is blocked, point to the real prerequisite:
  - `Check Client ID and secret`
  - `Insert bot token`
  - `Open phonebook`

### Anti-patterns
- Do not invent icons that do not exist in the UI.
- Do not use separate icon sets for top lane and bottom lane.
- Do not mix decorative illustrations with control icons.
- Do not rely on text-only references when the UI itself is icon-first.
- Do not ship raw token strings such as `[[pin]]` to runtime text.

### MCC Transfer Rules
- Keep token names identical between VETKA and MCC wherever the control meaning matches.
- If MCC has a different silhouette for the same action, keep the token name but change only the renderer body.
- Reuse the same authoring checklist:
  - real control
  - real token
  - real runtime verification

## Cross-links
See also:
- [MYCO_SCENARIO_AUTHOR_CHECKLIST_V1.md](./MYCO_SCENARIO_AUTHOR_CHECKLIST_V1.md)
- [PHASE_163A_PLUS_MYCO_SUBPANELS_SCENARIO_MATRIX_2026-03-09.md](./PHASE_163A_PLUS_MYCO_SUBPANELS_SCENARIO_MATRIX_2026-03-09.md)
- [PHASE_163A_PLUS_MYCO_BROWSER_VERIFY_NOTES_2026-03-09.md](./PHASE_163A_PLUS_MYCO_BROWSER_VERIFY_NOTES_2026-03-09.md)
- [README.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/162_ph_MCC_MYCO_HELPER/README.md)

## Status Matrix
| Item | Status |
|---|---|
| Token-based SVG icon system for MYCO hints | Implemented |
| Top-lane icon rendering | Implemented |
| Bottom-lane icon rendering | Implemented |
| MCC transfer guidance | Implemented |
