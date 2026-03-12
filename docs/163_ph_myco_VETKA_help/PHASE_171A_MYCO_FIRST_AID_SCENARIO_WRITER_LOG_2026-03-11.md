MARKER_171A.MYCO.FIRST_AID.SCENARIO_WRITER.LOG.V1
LAYER: L1
DOMAIN: UI|SEARCH|SCANNER|ARTIFACT|VOICE|AGENTS
STATUS: IMPLEMENTED
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_171A_MYCO_FIRST_AID_SCENARIO_WRITER_LOG_2026-03-11.md
LAST_VERIFIED: 2026-03-11

# Phase 171.A MYCO First Aid Scenario Writer Log

## Synopsis
This is the board journal for the current recon pass.

Purpose:
- preserve the actual work pattern
- capture mistakes to avoid
- hand practical experience to the next MYCO scenario author, including MCC colleagues

## Table of Contents
1. Working log
2. Patterns confirmed
3. Mistakes to avoid
4. Reusable authoring rules
5. Cross-links
6. Status matrix

## Treatment
This is not a product spec.
It is an engineering memory of how the scenario work actually deepened.

## Short Narrative
The important lesson did not change: good MYCO scenarios are discovered, not invented. The new lesson from the first-aid pass is sharper: "error help" only works when you refuse vague language and refuse to pretend every block is user-fixable.

## Full Spec
### Working Log
#### Pass 1. Check our own method first
- reopened the MYCO scenario checklist and core architecture
- used them as constraints instead of starting from new copy
- result:
  - the first-aid work stayed grounded in triggers, states, and recovery paths

#### Pass 2. Search for a global error index
- looked for a single existing product-wide index
- result:
  - none exists
  - error truth is fragmented across routes, socket events, panel logic, and prior docs

#### Pass 3. Start from likely user dead ends
- web/provider/key failures
- scanner/connectors auth and token states
- socket/connectivity breaks
- artifact save/open failures
- media open/playback degradation
- file permission and not-found
- voice timeout and no-audio
- collaboration dead-end and `@doctor`

#### Pass 4. Reject fiction
- checked whether `@doctor` is real
- checked whether media already exposes codec-style user errors
- checked whether connectors are one-click for end users
- result:
  - `@doctor` is real
  - media has some low-level failure signals, but not a full user-facing codec taxonomy
  - connectors are only partly end-user self-service because OAuth app credentials may be missing on the VETKA side

#### Pass 5. Keep browser and runtime truth conservative
- reused prior runtime verify docs where they were stronger than current code-only inference
- did not overclaim new runtime coverage where only code existed

### Patterns Confirmed
1. Search is usually the best place to design the first structured failure envelope.
2. Scanner and connectors generate many believable UI states that are still not fully runnable.
3. Media code often has useful degradation signals before it has useful user messaging.
4. `@doctor` is not a fantasy fallback. It is a real escalation path and should be used deliberately.
5. First aid is strongest when it distinguishes:
   - user can fix
   - operator must fix
   - retry later
   - escalate now

### Mistakes To Avoid
1. Do not write `something went wrong`.
2. Do not say `try later` without at least one concrete local action.
3. Do not promise one-click auth when the product still needs provider app credentials.
4. Do not invent codec advice unless a media signal actually supports it.
5. Do not send user to `@doctor` before the obvious recovery step.
6. Do not mark runtime as verified if only tests or code were checked.

### Reusable Authoring Rules
#### Rule 1. Ask "what exact signal exists today?"
If none exists:
- do not fake implemented behavior
- mark the scenario as `Planned`
- add the trigger to roadmap

#### Rule 2. Advice must fit one of four buckets
- fix locally now
- retry later
- switch path
- escalate

#### Rule 3. Recovery hints must name a real control or a real action
Good:
- `open phonebook and add a key`
- `switch unified lane to web/`
- `reconnect the provider`
- `pin the file into chat context`

Bad:
- `restore context`
- `return found items`
- `something is unavailable`

#### Rule 4. Distinguish user error from operator error
Example:
- missing Tavily key can be user-fixable
- missing OAuth client credentials for Google Drive is usually operator-side

#### Rule 5. Search, scanner, artifact, and voice should share one envelope shape
The surface differs.
The logic should not.

#### Rule 6. Keep a final escalation path
When the local path is exhausted:
- suggest `@doctor`
- include what already failed

## Cross-links
See also:
- [MYCO_SCENARIO_AUTHOR_CHECKLIST_V1.md](./MYCO_SCENARIO_AUTHOR_CHECKLIST_V1.md)
- [MYCO_CORE_SCENARIO_ARCHITECTURE_V1.md](./MYCO_CORE_SCENARIO_ARCHITECTURE_V1.md)
- [PHASE_171A_MYCO_FIRST_AID_RECON_REPORT_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_RECON_REPORT_2026-03-11.md)
- [PHASE_171A_MYCO_FIRST_AID_ERROR_INDEX_AND_SCENARIO_MATRIX_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_ERROR_INDEX_AND_SCENARIO_MATRIX_2026-03-11.md)
- [PHASE_171A_MYCO_FIRST_AID_ROADMAP_2026-03-11.md](./PHASE_171A_MYCO_FIRST_AID_ROADMAP_2026-03-11.md)

## Status Matrix
| Scope | Status |
|---|---|
| Board journal for first-aid recon | Implemented |
| Reusable lessons for MCC/MYCO colleagues | Implemented |
| Runtime/browser diary for every domain | Partial |
