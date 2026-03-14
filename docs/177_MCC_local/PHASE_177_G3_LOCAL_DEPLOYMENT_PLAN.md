# PHASE 177 — G3 localguys Deployment Plan

Date: 2026-03-12
Status: planning
Workflow family target: `g3_localguys`
Tag: `localguys`

## Why start with G3
`g3_critic_coder` already exists and matches the smallest useful local team:
- `coder` produces patch
- `verifier` attacks and gates patch
- bounded loop is already natural for local models

This is the right first field deployment because it is:
- small enough to control
- useful enough to save real work
- strict enough to expose missing MCC contract pieces

G3 is the first deployment slice, not the terminal architecture.
After G3 proves the runtime, the same localguys contract must be extended to the rest of the useful MCC workflow families.

## Proposed `g3_localguys` shape
Based on existing G3, but local-first.

Roles:
- `coder`
- `verifier`

Optional upstream feeder:
- `architect` can remain external/hybrid for the first rollout

## Candidate local role mapping
### MVP default
- `coder` -> `qwen3:8b` or `qwen2.5:7b`
- `verifier` -> `deepseek-r1:8b`

### Alternate low-cost mode
- `coder` -> `qwen2.5:3b`
- `verifier` -> `phi4-mini:latest`

### Visual mode extension
- `scout` -> `qwen2.5vl:3b`

## Workflow steps
1. `recon`
   - read target files
   - collect markers
   - collect related tests
   - produce `facts.json`
2. `plan`
   - produce bounded patch plan
   - produce `plan.json`
3. `execute`
   - `coder` edits only allowlisted files in playground
   - produce `patch.diff`
4. `verify`
   - targeted tests
   - static checks if defined
   - produce `test_output.txt`
5. `critic_gate`
   - `verifier` reviews patch + test output
   - produce `review.json`
6. `finalize`
   - write `final_report.json`
   - return `done`, `blocked`, or `failed`

## Real-task test strategy
Use real TaskBoard tasks from the multitask queue as the proving set.

Test ladder:
1. dry contract tests
   - resolve workflow contract
   - resolve local model policy
   - create and lock playground
2. narrow replay tests
   - take previously solved small multitask tasks and replay them in playground
   - compare generated artifacts and verifier decisions
3. live queue tests
   - pick active small-scope tasks from multitask
   - run under `g3_localguys`
   - require operator-visible MCC telemetry during execution
4. soak tests
   - run several sequential tasks to check recovery, cleanup, and no-context-drift behavior

Acceptance for real-task tests:
- targeted tests pass
- verifier gate passes
- artifacts are complete
- task outcome is visible in MCC
- failures classify into policy / tooling / model buckets

## MCC requirements for this rollout
### Must have
- workflow binding can resolve `g3_localguys`
- workflow contract can be fetched by family
- task run can lock to a playground
- MCC shows current step and active local models
- artifacts are linked and visible
- verifier outcome is visible on the task card/detail

### Should have
- local-only filter in workflow picker
- model badge showing `ollama` + model id
- blocked/failure reason surfaced without opening logs

### Nice to have
- live token/context pressure indicator
- per-step elapsed time and retry counter

## Backend work packages
### WP1 — workflow contract registry
- add family contract for `g3_localguys`
- expose via MCC API

### WP2 — local model policy mapping
- bind actual local model IDs to MCC role execution
- stop using fuzzy defaults for key local agents

### WP3 — playground run metadata
- persist `playground_id`, `branch_name`, `worktree_path`, `task_id`, `workflow_family`

### WP4 — artifact writer
- standardize output files
- connect to TaskBoard proof path

### WP5 — verifier bridge
- final state can only be `done` if verifier says pass and required checks pass

### WP5B — workflow family adapter matrix
- inventory all existing workflow families from MCC banks
- define which ones get:
  - direct local variant
  - hybrid local/cloud variant
  - explicit non-local exclusion
- keep the adaptation at contract/model-policy level, not bespoke runtime forks

## Frontend/MCC work packages
### WP6 — workflow contract UI
- show contract summary in task detail / MiniContext
- show which local models are assigned to current run

### WP7 — runtime monitor
- current step
- current role
- model id
- playground name
- artifact links
- failure reason

### WP8 — localguys task flow
- add `localguys` tag and workflow family selection path
- make it easy to launch a new playground tab for local work

### WP9 — method launch surface
- expose one-button launchers per supported method/team
- examples:
  - `Run G3 Local`
  - `Run Ralph Local`
  - `Run Research Local`
  - `Run Architect Local`
- buttons call the same MCC runtime/operator entrypoint with family-specific defaults

## Pilot task policy
Allow on launch:
- backend API patch
- test-only fixes
- contained frontend wiring
- small refactors with explicit file allowlist

Block on launch:
- multi-package migrations
- schema overhauls
- large UI redesign
- infra/deploy changes
- unbounded research tasks

## Final operator tool target
The end state is a one-command launcher for Codex and Claude.

Shape:
- input: `task_id`, optional `workflow_family`, optional local model overrides
- action: resolve contract -> create/select playground -> run localguys -> stream status to MCC
- output: run id, playground id, artifact paths, final status, metrics summary

This tool must not bypass MCC rules; it should call the same runtime contract and safety checks.

Final shape is broader than a single G3 launcher:
- one shared operator tool surface
- multiple method commands on top of it
- one command per workflow method/team style

Examples:
- `localguys run g3 --task <task_id>`
- `localguys run ralph --task <task_id>`
- `localguys run research --task <task_id>`
- `localguys run architect --task <task_id>`

Each command should:
- resolve the mapped MCC workflow family
- create/select playground
- launch the run
- stream status back into MCC
- return artifacts/proof in the same structure
- return a stable metrics block for benchmark and regression packs

## Exit criteria
- at least one real TaskBoard task completes end-to-end in playground under `g3_localguys`
- MCC shows live state during execution
- artifacts are generated and inspectable
- verifier gate determines final task outcome
- failure path returns structured `blocked` or `failed` with reason
- the same workflow can be launched from a one-command tool for Codex and Claude
- the G3 implementation is ready to be cloned into the rest of the supported workflow families without redesigning the runtime
- operator and MCC runs expose comparable metrics for replay and soak tests
