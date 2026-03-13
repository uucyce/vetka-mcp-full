# PHASE 177 — localguys Master Roadmap

Date: 2026-03-12
Status: planning
Tag: `localguys`
Scope: MCC + TaskBoard + playground + local LLM workers

## Goal
Bring local models into MCC as first-class workers that can execute bounded workflows inside playgrounds, report progress to TaskBoard, and stay observable and controllable from MCC.

## North Star
`localguys` are not a separate toy subsystem.
They are MCC-native workers with:
- role binding (`architect`, `coder`, `verifier`, `scout`)
- workflow-family binding (`g3_localguys`, then all existing MCC workflow families)
- playground isolation
- model-policy enforcement
- artifact reporting
- verifier-gated completion

## What already exists
- workflow binding and workflow catalog in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/mcc_routes.py`
- G3 template family in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/templates/workflows/g3_critic_coder.json`
- playground/worktree isolation in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/playground_manager.py`
- model profile registry in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/llm_model_registry.py`
- local/capability registry in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/model_registry.py`
- role preprompt preview in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MiniContext.tsx`
- TaskBoard history/proof/dispatch infrastructure already active

## New adjacent directions
- LiteRT benchmark lane for Apple Silicon should be tracked as a benchmark direction, not a core runtime dependency yet
- roadmap <-> TaskBoard sync should be treated as a force multiplier for localguys because it upgrades task intake from title-only to context packet

## Main gaps
1. No unified `workflow_contract` object for MCC execution.
2. No exact model-policy mapping for real Ollama IDs.
3. No first-class `localguys` workflow family.
4. No artifact contract for autonomous runs.
5. No MCC runtime surface showing local worker state, playground binding, and verifier outcome.
6. Preprompt exists as preview, not as hard execution enforcement.

## Delivery stages

### Stage 1 — Model grounding
Goal: make local models deterministic participants in MCC.
- normalize local model IDs
- map them to role fitness and capability classes
- merge `LLMModelRegistry` and `ModelRegistry` into one MCC-facing policy view
- expose exact profile per task/workflow run

Exit criteria:
- MCC can resolve a local model into context budget, output budget, provider, capabilities, reliability tier, and tool discipline

### Stage 2 — Workflow contract
Goal: define how a workflow actually executes.
- add `workflow_contract` registry
- include `steps`, `roles`, `tool_budget`, `model_policy`, `artifact_contract`, `failure_policy`, `sandbox_policy`
- attach contract to workflow binding and task binding responses

Exit criteria:
- any task with a workflow binding can return a machine-readable execution contract

### Stage 3 — localguys workflow family
Goal: launch the first local-only team.
- create `g3_localguys` based on G3 critic+coder
- bind `coder` and `verifier` to local models
- keep `architect` optional or upstream-generated for MVP

Exit criteria:
- one TaskBoard task can be assigned to `g3_localguys` and fully executed in playground mode

### Stage 3B — Family-wide workflow adaptation
Goal: do not stop at G3; adapt the whole MCC workflow catalog to localguys-compatible execution.
- inventory all existing workflow families and banks
- classify each family by local readiness: `ready`, `hybrid_only`, `needs_contract_split`, `not_for_local`
- add a localguys variant or local policy matrix for every useful workflow family
- keep one shared contract shape so MCC/operator tooling does not branch per family

Exit criteria:
- every relevant MCC workflow family has an explicit localguys execution policy or an explicit exclusion reason

### Stage 4 — Playground execution
Goal: enforce safe isolated work.
- every run gets a `playground_id`, `branch_name`, `worktree_path`
- all writes go to playground only
- run metadata is visible in MCC and stored for recovery

Exit criteria:
- no local autonomous write path reaches main tree directly

### Stage 5 — Artifact and proof layer
Goal: make every run inspectable.
- standardize `facts.json`, `plan.json`, `patch.diff`, `test_output.txt`, `review.json`, `final_report.json`
- link artifacts to task and run
- make verifier outcome first-class proof

Exit criteria:
- MCC can open artifacts for any `localguys` run

### Stage 6 — MCC runtime control
Goal: let user supervise local workers without dropping to logs.
- show worker roster
- show active run, current step, elapsed time, failure reason
- show playground binding and artifact list
- show verifier gate and final disposition

Exit criteria:
- operator can answer "who is doing what, where, and why blocked" directly from MCC

### Stage 7 — Autonomy hardening
Goal: remove prompt-only fragility.
- enforce stop conditions
- enforce retries and tool budgets
- block repeated recon loops
- fail cleanly into `blocked` / `failed` / `escalated`

Exit criteria:
- localguys stop predictably and report structured reasons

### Stage 8 — Real-task proving ground
Goal: validate localguys on actual multitask work, not synthetic demos.
- use real TaskBoard tasks from the multitask queue as acceptance tests
- start with narrow file-scoped tasks already suitable for G3
- compare localguys output against verifier outcome, tests, and operator review
- record failures as policy gaps, not just model mistakes
- add metrics tests for latency, verifier pass rate, artifact completeness, retry count, and budget overrun rate
- keep a small fixed benchmark pack so regressions in localguys quality are measurable, not anecdotal
- reserve one benchmark lane for non-LLM local runtime candidates such as LiteRT on Apple Silicon

Exit criteria:
- localguys complete a small pack of real TaskBoard tasks in playground mode with artifacts and verifier-gated proof

### Stage 8B — Adjacent runtime benchmark lanes
Goal: compare promising local runtime candidates without polluting core MCC execution.
- evaluate LiteRT on Apple Silicon as a benchmark candidate
- compare it using the same metrics vocabulary as localguys benchmarks
- explicitly decide whether it should stay experimental, become a helper lane, or be dropped

Exit criteria:
- one benchmark document and one comparable metrics pack exist for LiteRT or the candidate is explicitly rejected

### Stage 8C — Roadmap/TaskBoard convergence
Goal: reduce planning/execution duplication by binding roadmap nodes to executable task packets.
- define roadmap binding fields in TaskBoard
- expose a canonical MCC task context packet
- preserve docs, workflow binding, and code/test hints in task intake

Exit criteria:
- a task can be reconstructed from roadmap + TaskBoard + MCC contract without ad hoc recon

### Stage 9 — One-command operator tool
Goal: make localguys launchable by one command for Codex and Claude.
- wrap workflow resolution + playground creation + run start into one tool entrypoint
- accept task id, workflow family, and preferred local model set
- emit structured run status and artifact links back into MCC/TaskBoard
- use the same contract and safety rules as MCC UI launch
- expose metrics in the same tool output so operator runs can be compared across methods and models

Exit criteria:
- Codex and Claude can start localguys with one command instead of manually stitching steps

### Stage 10 — One-button methods for every work mode
Goal: expose one-button/one-command launchers for each real MCC method of work, not only G3.
- ship operator commands per workflow family / team method
- examples: `g3_localguys`, `ralph_localguys`, `research_localguys`, `architect_localguys`, `scout_localguys`
- each launcher resolves to the same MCC runtime, not a side system
- each launcher returns run id, playground id, assigned models, current step, and artifact links

Exit criteria:
- for every supported method/team workflow in MCC there is a matching one-command localguys launcher

## Recommended rollout order
1. `MODEL_POLICY_MATRIX.md`
2. `WORKFLOW_FAMILY_ADAPTER_MATRIX.md`
3. `MCC_WORKFLOW_CONTRACT_V1.md`
4. `PHASE_177_G3_LOCAL_DEPLOYMENT_PLAN.md`
5. backend registry + contract API
6. MCC runtime surface
7. pilot with narrow task types
8. metrics regression pack for real-task proving
9. one-command operator wrapper

## First production slice
- workflow family: `g3_localguys`
- roles: `coder` + `verifier`
- environment: playground only
- task types: narrow backend fix, tests-first patch, contained frontend wiring
- completion rule: verifier-approved + targeted tests pass + artifacts written
- proving set: real multitask TaskBoard tasks, not toy prompts

## After first slice
- adapt remaining high-value workflow families instead of freezing on G3
- preserve one contract/runtime path across all local methods
- ship one-button launchers per method/team so operators can pick the work style directly

## Non-goals for initial rollout
- no free-form self-routing swarm
- no 5-agent fully autonomous council
- no direct edits in main workspace
- no broad architecture tasks on local-only stack

## Success criteria
- local-only workflow can run end-to-end from TaskBoard
- MCC shows live run state and final proof
- playground isolation is enforced
- verifier is mandatory for `done`
- the operating cost is effectively electricity + local hardware time

## Stage 8D - TaskBoard governance and lane isolation
Goal: stop false agent blocks in dirty trees by making lane ownership machine-readable.
- add TaskBoard governance fields: ownership_scope, allowed_paths, owner_agent, completion_contract
- extend with blocked_paths, verification_agent, worktree_hint, touch_policy, overlap_risk, depends_on_docs
- feed governance metadata into MCC task packets so agents consume it from the DAG-linked contract
- enforce done/ownership gates in TaskBoard transitions

## Stage 8E - MCC code context inspection

- remove low-value graph labels like `struct` from normal reading mode
- distinguish code scope nodes from task/workflow nodes visually and semantically
- make descendant browsing support children, grandchildren, and great-grandchildren on demand, with `+1 deeper` beyond that
- apply MCC fractal scale rule so each deeper level is visually smaller but remains operable
- split fractal render policy by generation band (`depth1`, `depth2`, `depth3+`) instead of one shared mini-layer floor
- verify generation bands through Playwright against a hydrated or replayed MCC graph state; a blank browser shell is not enough
- use a reusable MCC graph fixture + `project_id` boot override so browser verification does not depend on manual desktop state
- add code-first MiniContext mode with breadcrumbs and direct code viewing actions
- treat task packet as supporting context for code nodes, not the default headline
