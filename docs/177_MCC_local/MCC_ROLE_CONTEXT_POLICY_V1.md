# MCC Role Context Policy V1

Status: working policy draft
Parent task: `tb_1773288269_1`
Subtask: `tb_1773288269_2`

## Goal

Define an MCC-native context strategy.

Do not copy the VETKA chat context path blindly.
In MCC, each agent behaves more like a role-bound worker with its own chat/runtime lane.
Shared state should move through workflow/task contracts and explicit handoff, not through one giant common prompt.

## Principles

1. Canonical source is the MCC task packet.
2. Context is sliced by role.
3. Viewport is selective, not global.
4. MYCO is an assist lane, not the same thing as coder context.
5. Workflow handoff should carry distilled outputs, not full upstream prompts.
6. Human UI preview and agent runtime should read from the same packet family, but not necessarily the same rendering.

## Canonical packet layers

### Always available in the canonical packet
- task
- workflow_binding
- workflow_contract
- roadmap_binding
- docs
- code_scope
- tests
- artifacts
- history
- gaps
- governance

### Optional contextual overlays
- viewport_context
- pinned_files
- workflow_myco_hint
- semantic condensation
- benchmark/runtime hints

These overlays should be injected only when the role benefits from them.

## Role policy matrix

### Architect
Required:
- task
- workflow_binding
- workflow_contract
- docs
- code_scope
- tests
- history
- governance

Optional:
- viewport_context when task is topology-heavy, navigation-heavy, UI-layout-heavy, or graph-driven
- pinned_files when user focus matters
- semantic condensation for broad planning/restructure tasks

Avoid by default:
- raw artifact dumps
- full prior agent transcripts

### Scout
Required:
- task
- workflow_binding
- docs
- code_scope
- governance

Optional:
- viewport_context if current focus node is likely the search anchor
- pinned_files for visible/focused files

Avoid by default:
- full workflow history
- verifier/eval scoring noise

### Researcher
Required:
- task
- workflow_binding
- docs
- governance

Optional:
- semantic condensation when docs are broad or clustered
- viewport only when current visual focus is the research subject

Avoid by default:
- code/artifact blobs unless explicitly requested

### Coder
Required:
- task
- workflow_binding
- workflow_contract
- code_scope
- tests
- artifacts
- governance

Optional:
- latest verifier summary
- latest architect handoff summary

Avoid by default:
- viewport_context
- broad chat history
- roadmap topology unless task depends on it directly

### Verifier
Required:
- task
- tests
- artifacts
- completion_contract from governance
- workflow_contract

Optional:
- latest coder handoff summary
- focused code_scope

Avoid by default:
- viewport_context
- exploratory docs unrelated to acceptance

### Eval
Required:
- task
- artifacts
- metrics
- workflow_contract
- governance

Optional:
- verifier output
- benchmark/runtime comparisons when available

### MYCO
Required:
- workflow_myco_hint
- selected task/node metadata
- viewport_context
- pinned_files

Optional:
- lightweight packet summary
- workflow family summary

Avoid by default:
- full coder/verifier payloads

## Viewport injection policy

Inject viewport by default only for:
- MYCO
- architect when task class is visual/topological/navigation-heavy

Inject viewport optionally for:
- scout
- researcher

Do not inject viewport by default for:
- coder
- verifier
- eval

## Semantic compression policy

ELISION remains useful for:
- packet summaries
- role-specific prompt blocks
- workflow handoff summaries

JEPA or semantic condensation should be used as an opt-in planning aid for:
- architect
- researcher
- roadmap generation

It should not be a blanket compression layer for every MCC role.

## Human-facing MiniContext policy

MiniContext should become a readable projection of the canonical packet, not a parallel source.

It should show:
- packet sections present/missing
- architecture docs and recon docs with preview/open affordances
- code scope and tests
- governance fields
- artifact presence
- role-specific slice preview

## DAG/file hierarchy policy

The DAG view should stay topology-first, but context browsing needs deeper file visibility.

Target model:
- DAG keeps high-level operational graph
- MiniContext / side surfaces expose deeper directory and file hierarchy on demand
- users can inspect more than the current shallow directory depth

## Recommended implementation order

1. role-aware packet slicing in runtime
2. selective viewport injection for architect/MYCO
3. richer MiniContext packet rendering
4. deeper file hierarchy browsing in context surfaces
5. only then decide what is worth upstreaming back into VETKA chat context

## Why this is better than blind parity with VETKA chat

- less token waste
- less role confusion
- cleaner workflow handoff
- more controllable UX for MYCO and MiniContext
- stronger chance to upstream the better parts back into VETKA later
