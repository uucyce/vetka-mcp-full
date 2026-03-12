MARKER_163C.MYCO.SCENARIO.AUTHOR.CHECKLIST.V1
LAYER: L1
DOMAIN: UI|CHAT|TOOLS|AGENTS
STATUS: IMPLEMENTED
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/MYCO_SCENARIO_AUTHOR_CHECKLIST_V1.md
LAST_VERIFIED: 2026-03-08

# MYCO Scenario Author Checklist V1
## Practical roadmap for writing MYCO scenarios

## Synopsis
This is the practical checklist for a MYCO scenario author. It captures the actual work pattern used in this chat: start from first-run reality, audit all windows and controls, separate implemented from partial and planned, deepen scenarios in passes, then prepare compact deterministic hints plus deeper LLM-friendly documentation.

## Table of Contents
1. Core rule
2. Working phases
3. Detailed checklist
4. Patterns learned in this chat
5. Output package
6. Quality gate
7. Cross-links
8. Status matrix

## Core rule
MYCO scenarios are not written top-down from imagination.
They are discovered bottom-up from:
- real runtime surfaces;
- real controls;
- real state transitions;
- real onboarding blockers;
- real errors;
- real recovery paths.

## Working phases
0. Check first-run scenario
1. Recon all windows
2. Recon all buttons and controls
3. Map user entry levels
4. Build root scenario tree
5. Add deterministic trigger matrix
6. Add anti-noise and silence rules
7. Deepen scenarios and recovery branches
8. Produce full context docs for LLM and future MYCO tracks

## Detailed checklist
### 0. Check first-run scenario
Goal:
- understand what a brand-new user sees;
- identify what blocks “bringing the product to life”.

Checklist:
- verify whether user starts with zero keys or existing keys;
- verify whether chat is open or closed on first load;
- verify whether search is usable immediately;
- verify whether web search needs a separate provider key;
- verify which advice must not appear if setup is already complete;
- define first-run MYCO hint for `zero setup`;
- define first-run MYCO silence rule for `already configured`.

Expected result:
- explicit `E0 cold start` scenario;
- onboarding hint only when needed;
- no false setup nagging.

### 1. Recon all windows
Goal:
- enumerate all full windows, detached windows, half-windows, embedded panels, overlays, popups.

Checklist:
- main app surfaces;
- chat surfaces;
- history panel;
- phonebook/model directory;
- scanner panel;
- group setup;
- active group chat;
- artifact windows;
- media subtypes;
- web shell;
- dev panels;
- onboarding overlays;
- context menus;
- detached/native windows if present.

For each window record:
- name;
- how it opens;
- where it lives in code;
- what state flag activates it;
- what user can do there;
- current implementation status.

Expected result:
- windows and surfaces atlas;
- no “hidden” UI zone left undocumented.

### 2. Recon all buttons and controls
Goal:
- move from surface-level docs to actionable interface coverage.

Checklist:
- audit all `<button>` controls;
- audit clickable icons;
- audit tabs, dropdowns, segmented controls;
- audit search context selectors;
- audit mode switches;
- audit star/favorite toggles;
- audit toolbar controls;
- audit buttons inside artifacts and media viewers;
- audit controls inside scanner and team setup;
- separately note custom `onClick` div/span controls.

For each control record:
- control label or role;
- file and line;
- visible surface;
- intended user action;
- resulting state change;
- MYCO micro-hint candidate.

Expected result:
- controls atlas;
- button catalog;
- list of remaining non-button interactive gaps.

### 3. Map user entry levels
Goal:
- stop writing one-size-fits-all hints.

Checklist:
- define `cold start`;
- define `surface orientation`;
- define `action discovery`;
- define `flow execution`;
- define `recovery`;
- define `optimization`;
- define `expert silence`.

For each level record:
- what user already knows;
- what user still needs;
- what MYCO must explain;
- what MYCO must not repeat.

Expected result:
- scenario levels that prevent beginner advice from leaking into expert flows.

### 4. Build root scenario tree
Goal:
- create top-down navigable scenario coverage before deepening details.

Checklist:
- define L0: what user sees and what user can do;
- define L1: core workspaces;
- define L2: concrete actions;
- define L3: edge cases, errors, warnings, reminders.

Must include:
- tree;
- chat;
- artifact;
- search;
- scanner;
- model directory;
- team/group flow;
- history;
- media-specific surfaces.

Expected result:
- root scenario index;
- stable scenario IDs and navigation.

### 5. Add deterministic trigger matrix
Goal:
- bind scenarios to actual UI events, not descriptions.

Checklist:
- selection triggers;
- open/close triggers;
- mode-switch triggers;
- search-context triggers;
- search-mode triggers;
- artifact-type triggers;
- group-state triggers;
- input-empty/input-busy triggers;
- error triggers;
- disabled-feature triggers.

For each trigger record:
- event source;
- required state fields;
- target MYCO state key;
- expected hint payload;
- exit transition.

Expected result:
- deterministic rule matrix;
- event contract ready for implementation and tests.

### 6. Add anti-noise and silence rules
Goal:
- keep MYCO useful instead of annoying.

Checklist:
- if user is typing in chat, MYCO is silent;
- if user is typing in search, MYCO is silent unless recovery is critical;
- if keys exist, do not suggest adding keys;
- if chat is already open, do not suggest “open chat first”;
- if user moved from one surface to another, previous hint must disappear;
- if feature is disabled, explain once and redirect to a runnable path;
- never show two hints for the same state key.

Expected result:
- dedupe rules;
- stale-hint rules;
- silence rules.

### 7. Deepen scenarios and recovery branches
Goal:
- go beyond “basic happy path”.

Checklist:
- split artifact into:
  - regular document;
  - code artifact;
  - external artifact;
  - web artifact;
  - audio artifact;
  - video artifact;
- split search into:
  - `vetka/`;
  - `web/`;
  - `file/`;
  - visible but disabled contexts;
  - search modes;
- split key guidance into:
  - zero keys;
  - model key missing;
  - web key missing;
  - auth error;
  - billing/quota;
  - rate limit;
  - provider down/timeout;
- split team flow into:
  - group setup;
  - role-slot composition;
  - phonebook selection;
  - active group chat;
  - `@mention`;
- split scanner flow into:
  - connect source;
  - scan;
  - inspect results;
  - bring results back into VETKA.

Expected result:
- MYCO scenarios become actually helpful, not generic.

### 8. Produce full context docs for LLM and future MYCO tracks
Goal:
- support both deterministic MYCO and future deeper LLM/voice explanation.

Checklist:
- create short deterministic hint layer;
- create full scenario docs with evidence;
- create UI-capability matrix;
- create gap registry;
- create implementation plan;
- create verify report;
- create LLM-friendly reference docs that are easy to cite;
- write docs so a speaking model can summarize them cleanly later.

Formatting rules:
- keep proactive hint short;
- keep deep docs structured;
- avoid long raw URLs inside user-facing voice-oriented prose;
- separate current implementation from roadmap.

Expected result:
- deterministic UX layer plus rich document layer.

## Patterns learned in this chat
These are the practical patterns that emerged while expanding MYCO coverage.

### Pattern 1. Start broad, then deepen
We began with surface audit.
Then controls.
Then scenarios.
Then long-tail surfaces.
Then onboarding and recovery.

Lesson:
- do not start with prose;
- start with inventory.

### Pattern 2. Treat every “control question” as a missing scenario
When a user asked:
- what about phonebook;
- what about favorite key;
- what about search modes;
- what about scanner;
- what about team chat;
- what about media artifact subtypes;
that was not “feedback”.
That was a signal that the scenario tree was incomplete.

Lesson:
- every forgotten affordance becomes a new branch in the scenario matrix.

### Pattern 3. Separate source truth from assumption
We repeatedly had to verify:
- docs;
- code;
- runtime.

Lesson:
- “documented” is not enough;
- “coded” is not enough;
- runtime still wins.

### Pattern 4. Recovery scenarios are as important as happy paths
Useful MYCO behavior came not only from “what can I do here”.
It came from:
- no keys;
- missing Tavily;
- auth error;
- quota issue;
- disabled search mode;
- artifact save path hang.

Lesson:
- every important failure needs deterministic recovery guidance.

### Pattern 5. Anti-noise quality is core behavior
The product value increased when MYCO learned:
- not to talk while the user types;
- not to repeat solved setup;
- not to keep stale hints after context switch.

Lesson:
- silence behavior is a first-class scenario.

### Pattern 6. Team and context return flows matter
We found that helpful MYCO advice often connects surfaces:
- artifact -> chat context;
- team setup -> phonebook;
- group chat -> Team settings -> phonebook;
- web result -> artifact -> save/import path.

Lesson:
- good scenarios are not isolated screens;
- they are transitions between screens.

## Output package
At the end of scenario authoring, the scenario author should have:
1. first-run and onboarding matrix;
2. windows and surfaces atlas;
3. controls and buttons atlas;
4. root scenario tree;
5. deterministic trigger matrix;
6. anti-noise rules;
7. deep scenario coverage;
8. implementation plan;
9. verify report;
10. LLM-friendly deep docs.

## Quality gate
A MYCO scenario package is ready only if:
1. first-run is covered;
2. all core windows are covered;
3. all important controls are covered;
4. key recovery flows are covered;
5. hints are state-aware;
6. stale hints are prevented;
7. setup nagging is suppressed when setup is complete;
8. implemented vs partial vs planned is explicit;
9. docs link to code and runtime evidence;
10. a future MYCO or LLM maintainer can extend the package without guessing.

## Cross-links
See also:
- [MYCO Core Scenario Architecture](./MYCO_CORE_SCENARIO_ARCHITECTURE_V1.md)
- [MYCO VETKA Master Index](./MYCO_VETKA_MASTER_INDEX_V1.md)
- [MYCO VETKA Windows and Surfaces Atlas](./MYCO_VETKA_WINDOWS_AND_SURFACES_ATLAS_V1.md)
- [MYCO VETKA Controls and Buttons Atlas](./MYCO_VETKA_CONTROLS_AND_BUTTONS_ATLAS_V1.md)
- [MYCO VETKA Button Hint Catalog](./MYCO_VETKA_BUTTON_HINT_CATALOG_V1.md)
- [Phase 163A MYCO Mode A Scenario Matrix](./PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08.md)
- [Phase 163A MYCO Mode A Implementation Plan](./PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08.md)
- [Phase 163A MYCO Mode A Verify Report](./PHASE_163A_MYCO_MODE_A_VERIFY_REPORT_2026-03-08.md)
- [Phase 162 MCC MYCO Helper README](./../162_ph_MCC_MYCO_HELPER/README.md)
- [Phase 162 Runtime Scenario Matrix Recon](./../162_ph_MCC_MYCO_HELPER/PHASE_162_P4_P5_RUNTIME_SCENARIO_MATRIX_RECON_REPORT_2026-03-07.md)

## Status matrix
| Scope | Status | Evidence |
|---|---|---|
| Practical MYCO scenario-writing roadmap | Implemented | this file |
| Based on phase-162 MCC origin | Implemented | `docs/162_ph_MCC_MYCO_HELPER/*` |
| Based on phase-163 VETKA scenario expansion | Implemented | `docs/163_ph_myco_VETKA_help/*` |
