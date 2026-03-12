# PHASE 177 — localguys Implementation Backlog

Date: 2026-03-12
Status: planning
Tag: `localguys`

## Purpose
Turn the phase roadmap into concrete implementation work packages with explicit test obligations.

## Milestone 1 — Registry and contract foundation

### BG-001 — Add workflow contract registry
Scope:
- add workflow contract storage (JSON-backed or code-backed)
- support `g3_localguys` as first contract
- include steps, roles, model policy, tool budget, artifact contract, failure policy, sandbox policy

Files likely touched:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/mcc_routes.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/` contract registry files
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/mcc/`

Tests:
- contract fetch by workflow family
- task-bound contract resolution
- invalid family returns structured error
- contract contains mandatory fields for `g3_localguys`

Acceptance:
- MCC API returns machine-readable `workflow_contract`

### BG-002 — Add local model policy resolver
Scope:
- merge `LLMModelRegistry`, `ModelRegistry`, and local role mapping into one MCC-facing resolver
- bind real Ollama ids to stable role policy
- stop relying on generic fallback for core localguys models

Files likely touched:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/llm_model_registry.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/model_registry.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/mcc_routes.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/`

Tests:
- exact mapping for `qwen3:8b`, `qwen2.5:7b`, `deepseek-r1:8b`, `phi4-mini:latest`, `qwen2.5vl:3b`, `embeddinggemma:300m`
- provider/capability/context policy resolution
- role-fit resolution for `coder`, `verifier`, `scout`
- fallback remains structured for unknown models

Acceptance:
- MCC can resolve local role policy without fuzzy ambiguity

## Milestone 2 — Playground runtime binding

### BG-003 — Bind workflow run to playground metadata
Scope:
- each localguys run gets `playground_id`, `branch_name`, `worktree_path`, `task_id`, `workflow_family`
- persist this as active run state

Files likely touched:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/playground_manager.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/mcc_routes.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/phase146*`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/mcc/`

Tests:
- run cannot start without playground lock
- run metadata survives reload/init
- main tree writes are rejected for localguys runs
- multiple playgrounds do not cross wires

Acceptance:
- every localguys run is tied to one playground and visible as such

### BG-004 — Add artifact contract writer
Scope:
- standardize artifact base path and file names
- write `facts.json`, `plan.json`, `patch.diff`, `test_output.txt`, `review.json`, `final_report.json`
- attach artifact list to task/run payload

Tests:
- artifact directory created on run start
- required artifacts written on success path
- missing required artifact forces `blocked` or `failed`
- artifact list is serializable into MCC payload

Acceptance:
- every run is inspectable from stored artifacts

## Milestone 3 — G3 localguys execution path

### BG-005 — Add `g3_localguys` workflow family
Scope:
- create family/contract based on `g3_critic_coder`
- bind `coder` and `verifier` to local policies
- define strict `recon -> plan -> execute -> verify -> review -> finalize`

Tests:
- family appears in workflow contract resolution
- task can explicitly bind to `g3_localguys`
- role order and required steps are stable

Acceptance:
- G3 local workflow becomes selectable and resolvable in MCC

### BG-005B — Adapt remaining workflow families
Scope:
- inventory all workflow families in MCC banks (`core`, `saved`, `n8n`, `comfyui`, `imported`)
- decide which families should get localguys variants first
- define family mapping table:
  - `source_family`
  - `localguys_family`
  - `default_role_map`
  - `default_model_policy`
  - `operator_command`
  - `status` (`ready`, `hybrid`, `blocked`)
- avoid special-case runtimes; adapt by contract/policy where possible

Tests:
- workflow catalog can identify supported localguys-capable families
- each adapted family resolves to a valid contract
- unsupported families return explicit reason, not silent fallback
- operator command mapping is deterministic per family

Acceptance:
- localguys roadmap covers the full useful workflow set, not only `g3_localguys`

### BG-006 — Verifier-gated completion
Scope:
- `done` requires verifier pass and required tests
- `failed` / `blocked` / `escalated` become structured end states

Tests:
- verifier fail blocks completion
- test failure blocks completion
- success path with complete artifacts reaches `done`
- repeated review rounds respect budget

Acceptance:
- localguys cannot silently self-approve

## Milestone 4 — MCC monitoring and control

### BG-007 — Show localguys runtime in MCC
Scope:
- current step
- active role
- model id
- playground name/id
- artifact links
- failure reason
- verifier outcome

Files likely touched:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/store/useMCCStore.ts`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MiniContext.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/mcc/`

Tests:
- active run payload renders in MCC state
- project tab shows localguys playground binding
- artifact links render from payload
- blocked/failure reason visible without log scraping

Acceptance:
- operator can supervise localguys from MCC directly

## Milestone 5 — Real-task proving ground

### BG-008 — Replay solved multitask tasks
Scope:
- select previously solved small tasks from multitask archive
- replay them under `g3_localguys` in playground
- collect comparison artifacts

Tests:
- replay set can be executed end-to-end
- result is classified as pass/fail/policy-gap
- verifier output is stored and diffable

Acceptance:
- at least one solved task is reproducible under localguys

### BG-009 — Live queue trials
Scope:
- run real active narrow-scope TaskBoard tasks under localguys
- treat them as acceptance tests, not demos

Recommended task classes:
- backend endpoint patch
- tests-first bugfix
- narrow frontend API wiring

Tests:
- one live task reaches `done`
- one induced failure reaches `blocked` cleanly
- soak run: multiple tasks without stale context or broken playground cleanup

Acceptance:
- localguys prove useful on real work

## Milestone 6 — One-command operator tool

### BG-010 — Create localguys operator tool
Scope:
- one command for Codex/Claude to launch localguys
- input: task id, optional workflow family, optional model overrides
- output: run id, playground id, artifact paths, final status
- tool must call MCC/runtime contract, not bypass it

Tests:
- tool creates or selects playground correctly
- tool resolves workflow contract correctly
- tool launches run and returns structured status
- tool failure mirrors MCC failure semantics
- tool prints a stable metrics block (`latency_ms`, `artifact_missing_count`, `required_artifact_count`, `run_status`)

Acceptance:
- localguys can be started by one command with no manual stitching

### BG-011 — Add one-command method launchers for every supported team/workflow mode
Scope:
- build family-specific commands on top of the shared operator tool
- provide one-button/one-command launch semantics per supported method
- examples:
  - `g3_localguys`
  - `ralph_localguys`
  - `research_localguys`
  - `architect_localguys`
  - `scout_localguys`
- commands must stay aliases/wrappers over the same MCC runtime contract

Tests:
- each supported method resolves to the correct workflow family
- each launcher passes the expected default role/model policy
- launcher output is structurally identical across methods
- blocked methods fail with explicit reason and suggested fallback
- method launch metrics can be compared across workflows using the same output schema

Acceptance:
- every supported MCC work method/team style has a matching one-command localguys launcher

### BG-012 — Real-task metrics regression pack
Scope:
- define a fixed benchmark pack of narrow multitask tasks for localguys
- collect comparable metrics from operator runs and MCC runs
- store pass/fail plus runtime metrics for longitudinal comparison

Tests:
- replay pack returns stable metrics schema
- benchmark run records `latency_ms`, `artifact_missing_count`, `required_artifact_count`, `run_status`, `workflow_family`
- benchmark detects regressions when required artifacts or final states drift

Acceptance:
- localguys rollout is judged by reproducible task metrics, not ad hoc impressions

### BG-013 — LiteRT benchmark feasibility lane
Scope:
- evaluate LiteRT on Apple Silicon as an adjacent runtime benchmark
- compare LiteRT results against the current local stack using the same metrics vocabulary
- keep this lane benchmark-only until data justifies deeper integration

Tests:
- benchmark notes are reproducible
- metrics schema matches localguys benchmark summary vocabulary
- recommendation is explicit: adopt / benchmark-only / drop

Acceptance:
- LiteRT is either promoted to a justified benchmark lane or rejected with evidence

### BG-014 — Roadmap <-> TaskBoard context packet
Scope:
- design the canonical task packet for MCC/localguys dispatch
- include roadmap binding, workflow contract, docs, code scope, tests, artifacts
- close the gap between roadmap planning and TaskBoard execution

Tests:
- packet schema covers a real task end-to-end
- missing bindings return structured gaps
- one task can be reconstructed from packet data without manual recon

Acceptance:
- localguys intake can rely on a structured task packet instead of ad hoc context gathering

### BG-015 — Roadmap -> TaskBoard sync tool path
Scope:
- formalize roadmap node expansion into TaskBoard task generation
- persist roadmap binding metadata on tasks
- sync task completion back to roadmap progress

Tests:
- roadmap node generates a deterministic task pack
- generated tasks preserve roadmap metadata
- TaskBoard outcome can update roadmap progress

Acceptance:
- roadmap and TaskBoard act like one execution system with two views

## Real-task test policy
Use real multitask tasks whenever possible.

Priority order:
1. previously solved small tasks
2. safe active tasks with narrow file scope
3. repeated soak tasks for stability

Do not use as first proving tasks:
- broad refactors
- architecture redesign
- multi-surface UI rewrites
- infra/deploy changes

## Definition of useful testing
A test is useful if it validates one of these:
- contract resolution correctness
- local model policy correctness
- playground safety
- verifier gate correctness
- artifact completeness
- MCC observability
- usefulness on real TaskBoard work
- correctness of workflow-family adaptation and per-method launcher mapping

## BG-016 - TaskBoard governance V1
- formalize lane ownership and allowed edit surface on tasks
- add minimal governance fields to TaskBoard model and adapters
- enforce owner/done transition gates
- extend MCC task packets with governance metadata
- acceptance: agents can continue safely in dirty trees when changes are outside allowed_paths


## BG-017 - MCC code context inspection and DAG readability

- hide low-value structural labels in normal MCC mode
- project directory/file/code-aggregate nodes differently from task/workflow nodes
- support descendant browsing across children, grandchildren, and great-grandchildren, then `+1 deeper` on request
- apply fractal scale to descendant levels with minimum clickable-size guardrails
- add code-first MiniContext ordering and breadcrumb header
- add a clearer docked code viewer path from MiniContext
