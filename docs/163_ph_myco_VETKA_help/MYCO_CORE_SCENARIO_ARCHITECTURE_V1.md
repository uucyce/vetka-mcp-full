MARKER_163C.MYCO.CORE.SCENARIO_ARCHITECTURE.V1
LAYER: L1
DOMAIN: UI|CHAT|TOOLS|AGENTS
STATUS: IMPLEMENTED
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_CORE_SCENARIO_ARCHITECTURE_V1.md
LAST_VERIFIED: 2026-03-08

# MYCO
# Mycelium Context Operator
## The Deterministic Scenario Ladder

## Synopsis
This document is the canonical method for designing MYCO scenarios as a proactive guide layer for complex interfaces. It preserves the practical lessons learned from MCC origins, the full-window/full-button audit in VETKA, and the narrow deterministic MVP of `Mode A`. It is intended to be reused for VETKA, MYCELIUM, and future MYCO-core surfaces.

## Table of Contents
1. Identity and provenance
2. Why this method exists
3. User entry levels
4. Trigger taxonomy
5. State truth hierarchy
6. Scenario authoring rules
7. Anti-noise rules
8. Next-best-action rules
9. Scenario template
10. Debug and verification protocol
11. Marker and TAG standard
12. Author checklist
13. Cross-links
14. Status matrix

## Treatment
MYCO scenarios must not be written as generic assistant copy. They are behavior contracts attached to interface state transitions. A valid scenario starts from a real trigger, resolves against real UI state, avoids stale repetition, and ends in one to three useful next actions. This method is fractal: the same logic applies to one button, one panel, one window, or one entire product surface.

## Short Narrative
MYCO was born in MCC and matured there as a proactive helper. In VETKA, the work went deeper: audit every window, half-window, panel, button, search mode, artifact type, team flow, scanner path, and onboarding dependency. The key engineering lesson is simple: MYCO must not narrate everything. It must speak when the user needs orientation, stay quiet when the user is already acting, and never suggest setup work that is already complete.

## Full Spec
## Identity and Provenance
MYCO now has enough architecture and behavioral depth to be treated as a core guide system, not a UI ornament.

Lineage:
- MCC origin corpus:
  - [README](./../162_ph_MCC_MYCO_HELPER/README.md)
  - [MYCO Help Rules Library](./../162_ph_MCC_MYCO_HELPER/MYCO_HELP_RULES_LIBRARY_V1.md)
  - [MYCO Context Payload Contract](./../162_ph_MCC_MYCO_HELPER/MYCO_CONTEXT_PAYLOAD_CONTRACT_V1.md)
  - [Phase 162 Runtime Scenario Matrix Recon](./../162_ph_MCC_MYCO_HELPER/PHASE_162_P4_P5_RUNTIME_SCENARIO_MATRIX_RECON_REPORT_2026-03-07.md)
  - [Phase 162 Proactive Guidance Recon](./../162_ph_MCC_MYCO_HELPER/PHASE_162_P4_P2_PROACTIVE_GUIDANCE_RECON_REPORT_2026-03-07.md)
- VETKA adaptation corpus:
  - [Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
  - [Windows and Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
  - [Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
  - [Button Hint Catalog](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)
  - [Mode A Architecture](./PHASE_163A_MYCO_MODE_A_ARCHITECTURE_PROPOSAL_2026-03-08.md)
  - [Mode A Scenario Matrix](./PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08.md)
  - [Mode A Verify Report](./PHASE_163A_MYCO_MODE_A_VERIFY_REPORT_2026-03-08.md)

## Why This Method Exists
The real product problem was not “write smarter hints”.
The real product problem was:
- too many windows and half-windows;
- too many buttons and hidden actions;
- changing runtime behavior across tree, chat, artifacts, search, scanner, team chat;
- onboarding failure around API keys and providers;
- stale or noisy helper behavior;
- repeated confusion between implemented, partial, and planned features.

Therefore MYCO scenario engineering must begin with:
1. full surface audit;
2. full controls audit;
3. trigger mapping;
4. state mapping;
5. silence mapping;
6. runtime verification.

## User Entry Levels
MYCO must reason about where the user is in the product journey before deciding what to say.

### E0. Cold Start
The user just opened the product.
Characteristics:
- no orientation;
- no selected node;
- often no chat open;
- often no keys configured.

MYCO focus:
- identify the first viable action;
- do not explain advanced features first;
- if zero keys, explain only the minimum setup path;
- if keys already exist, never repeat setup instructions.

### E1. Surface Orientation
The user sees a window or panel and needs to understand what it is.
Examples:
- tree surface;
- model phonebook;
- scanner panel;
- artifact window;
- group setup;
- search context menu.

MYCO focus:
- what this surface is;
- what the user can do here right now;
- one next-best action.

### E2. Action Discovery
The user clicked something specific and now needs actionable follow-through.
Examples:
- selected a tree node;
- switched to `web/`;
- opened an artifact;
- clicked a role slot in team setup;
- opened chat history.

MYCO focus:
- identify changed state;
- explain resulting affordances;
- propose one to three concrete next actions.

### E3. Flow Execution
The user is already inside a flow.
Examples:
- typing in chat;
- browsing search results;
- editing artifact;
- scanning connector content;
- active group chat.

MYCO focus:
- only intervene if the flow branches, blocks, or risks failure;
- otherwise stay quiet.

### E4. Recovery
The user hit a missing dependency, degraded provider, wrong context, or runtime block.
Examples:
- no API keys;
- missing Tavily key for `web/`;
- auth error;
- billing/quota issue;
- rate limit;
- disabled `cloud/` or `social/`.

MYCO focus:
- classify the failure;
- propose a remedy proportional to certainty;
- provide a fallback path so the user is never stuck.

### E5. Optimization
The user already works productively and needs speed, not onboarding.
Examples:
- favorite key/model/file;
- pin to chat context;
- use `@mention`;
- move from artifact to team execution;
- switch search mode intelligently.

MYCO focus:
- efficiency;
- role-specific next steps;
- shortcuts and preferred patterns.

### E6. Expert Silence
The user is in uninterrupted execution.
Examples:
- typing in chat;
- typing in search;
- repeating known local actions;
- already configured setup state.

MYCO focus:
- silence.

## Trigger Taxonomy
Every scenario must begin from a real trigger.

### T1. Surface Triggers
Examples:
- panel opened;
- chat opened;
- history opened;
- phonebook opened;
- artifact opened;
- scanner opened;
- devpanel opened.

### T2. Focus Triggers
Examples:
- node selected;
- search context selected;
- role slot selected;
- group activated;
- artifact subtype detected.

### T3. Flow Triggers
Examples:
- input became empty;
- input became non-empty;
- user switched tree mode;
- user switched search mode;
- save or pin became available.

### T4. Failure Triggers
Examples:
- provider health is false;
- no key inventory;
- auth or quota error string detected;
- unavailable context clicked.

### T5. Completion Triggers
Examples:
- key added;
- chat opened after artifact;
- group created;
- surface returned from fallback to runnable mode.

Rule:
No scenario without an explicit trigger.

## State Truth Hierarchy
A MYCO scenario is valid only if its truth source is clear.

Priority order:
1. Runtime UI state
2. Event payload
3. Store state
4. Backend capability/health contract
5. Documentation

Interpretation rule:
- docs never override runtime;
- code never overrides live state if runtime disproves it;
- “Implemented” in docs is not accepted without code and runtime evidence.

Required status split:
- implemented in project
- implemented in MCC
- implemented in VETKA main
- implemented in VETKA voice path

These are different states and must stay separate.

## Scenario Authoring Rules
Each scenario must answer seven questions:
1. What changed?
2. What does the user now see?
3. What can the user really do now?
4. What should MYCO say right now?
5. What should MYCO not say?
6. How does the hint change on the next transition?
7. What proves this scenario is real?

Each scenario must contain:
- trigger;
- scope;
- active surface;
- gating conditions;
- deterministic hint payload;
- silence conditions;
- exit transitions;
- evidence links;
- status.

## Anti-Noise Rules
These rules are mandatory.

### Rule A1. No solved-setup repetition
If keys exist, MYCO must not say “insert key”.
If Tavily key exists, MYCO must not say “configure `web/` provider”.
If chat is already open, MYCO must not say “open chat first”.

### Rule A2. No stale hint after state transition
If the user moved from search to artifact, search hint must disappear.
If the user moved from group setup to active group chat, setup hint must disappear.
If tree mode changed, previous mode hint must disappear.

### Rule A3. No narration during typing
If chat input is non-empty, MYCO is silent.
If search input is non-empty in the primary lane, MYCO is silent unless the product explicitly wants inline recovery.

### Rule A4. No vague fallback
Never say:
- “try again”
- “check settings”
- “configure provider”
without naming the concrete next place in UI and the concrete dependency.

### Rule A5. No fake abstraction
Do not document providers or flows as generic if runtime is specific.
Example:
- if `web/` currently uses Tavily, the scenario must say Tavily.
- alternatives may be documented as roadmap or migration guidance, not as current implementation.

### Rule A6. No more than three next actions
MYCO should guide, not dump a menu.

## Next-Best-Action Rules
MYCO next actions must obey this order:
1. unblock the user;
2. keep them in the same flow if possible;
3. use the nearest visible control;
4. avoid requiring memory of hidden architecture;
5. offer fallback before escalation.

Examples:
- artifact with closed chat:
  - open chat;
  - pin to context;
  - favorite via star.
- `web/` without Tavily key:
  - open phonebook;
  - open API Keys drawer;
  - add Tavily key.
- group setup:
  - click role slot;
  - choose model in left phonebook;
  - create group.

## Scenario Template
Use this template for every new MYCO scenario.

```md
MARKER_xxx
TAG:MYCO.SCENARIO.<DOMAIN>.<NAME>

Title:
Surface:
Entry level: E0|E1|E2|E3|E4|E5|E6
Trigger:
State inputs:
- ...

Gates:
- required:
- suppress if:

What user sees:
- ...

Available actions:
1. ...
2. ...
3. ...

MYCO hint:
- title:
- body:
- next actions:
- shortcuts:
- tone:

Do not say:
- ...

Exit transitions:
- trigger -> next scenario

Status:
- project:
- MCC:
- VETKA main:
- VETKA voice:

Evidence:
- UI:
- code:
- backend:
- runtime:
```

## Debug and Verification Protocol
The scenario writing loop must follow the same discipline used in this phase.

### Step 1. Recon
Audit:
- all windows;
- half-windows;
- buttons;
- context menus;
- search modes;
- artifacts;
- onboarding dependencies.

### Step 2. Markerize
Add:
- scenario markers;
- event markers;
- evidence links;
- status labels.

### Step 3. Report
Write:
- what exists;
- what is partial;
- what is planned;
- what is blocked by runtime.

### Step 4. Narrow Implementation
Change only the smallest set of:
- rules;
- snapshot fields;
- UI event bridges;
- tests.

### Step 5. Verify
Use:
- source-contract tests;
- browser verification;
- runtime negative tests for stale/noise behavior.

## Marker and TAG Standard
Recommended core markers:
- `MARKER:MYCO.CORE.ENTRY_LEVELS`
- `MARKER:MYCO.CORE.TRIGGER.TAXONOMY`
- `MARKER:MYCO.CORE.ANTI_NOISE`
- `MARKER:MYCO.CORE.NEXT_ACTION_RULES`
- `MARKER:MYCO.CORE.SCENARIO.TEMPLATE`
- `MARKER:MYCO.CORE.RUNTIME_STATUS_SPLIT`

Recommended tags:
- `TAG:MYCO.CORE.SCENARIO_AUTHORING`
- `TAG:MYCO.CORE.ENTRY.E0_COLD_START`
- `TAG:MYCO.CORE.ENTRY.E4_RECOVERY`
- `TAG:MYCO.CORE.SILENCE.NO_TYPING_INTERRUPT`
- `TAG:MYCO.CORE.SEARCH.PROVIDER_TRUTH`
- `TAG:MYCO.CORE.ARTIFACT.CONTEXT_RETURN`
- `TAG:MYCO.CORE.GROUP.PHONEBOOK_COMPOSITION`

## Author Checklist
Before approving a new MYCO scenario, confirm:
1. Trigger is explicit.
2. State source is explicit.
3. Hint is tied to a real surface.
4. No setup nag appears if setup is already complete.
5. No stale hint survives the next transition.
6. Next actions are visible and actionable.
7. Status split is stated across project, MCC, VETKA main, VETKA voice.
8. Evidence includes code and, when possible, runtime verify.
9. Recovery path includes a fallback.
10. The scenario is short enough for proactive UI guidance, but can hand off to deeper documentation later.

## Cross-links
See also:
- [README from Phase 162 MCC MYCO Helper](./../162_ph_MCC_MYCO_HELPER/README.md)
- [MYCO Help Rules Library V1](./../162_ph_MCC_MYCO_HELPER/MYCO_HELP_RULES_LIBRARY_V1.md)
- [MYCO Context Payload Contract V1](./../162_ph_MCC_MYCO_HELPER/MYCO_CONTEXT_PAYLOAD_CONTRACT_V1.md)
- [Phase 162 Runtime Scenario Matrix Recon](./../162_ph_MCC_MYCO_HELPER/PHASE_162_P4_P5_RUNTIME_SCENARIO_MATRIX_RECON_REPORT_2026-03-07.md)
- [Phase 162 Proactive Guidance Recon](./../162_ph_MCC_MYCO_HELPER/PHASE_162_P4_P2_PROACTIVE_GUIDANCE_RECON_REPORT_2026-03-07.md)
- [MYCO VETKA Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [MYCO VETKA Windows and Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [MYCO VETKA Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [MYCO VETKA Button Hint Catalog](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)
- [Phase 163A MYCO Mode A Architecture Proposal](./PHASE_163A_MYCO_MODE_A_ARCHITECTURE_PROPOSAL_2026-03-08.md)
- [Phase 163A MYCO Mode A Scenario Matrix](./PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08.md)
- [Phase 163A MYCO Mode A Verify Report](./PHASE_163A_MYCO_MODE_A_VERIFY_REPORT_2026-03-08.md)

## Status matrix
| Scope | Status | Evidence |
|---|---|---|
| MCC origin principles documented | Implemented | `docs/162_ph_MCC_MYCO_HELPER/*` |
| VETKA full-surface audit lessons captured | Implemented | `docs/163_ph_myco_VETKA_help/*` |
| Deterministic scenario-writing method | Implemented | this file |
| MYCO-core reusable authoring framework | Implemented | this file + phase-163A architecture/report set |
