# PHASE 177 — Workflow Family Adapter Matrix

Date: 2026-03-12
Status: planning
Tag: `localguys`

## Purpose
Inventory the current MCC workflow families and define how each should adapt into the `localguys` runtime.

This matrix is the bridge between:
- workflow catalog/template sources
- `workflow_contract`
- local model policy
- future one-command operator launchers

## Source inventory used
Primary source files:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/templates/workflows/*.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/mcc_routes.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/TaskEditPopup.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx`

## Readiness states
- `ready` — can get a direct localguys variant now
- `hybrid` — useful, but some role(s) should stay cloud/upstream initially
- `split` — needs contract split before safe local execution
- `blocked` — not a first local target
- `stub` — template exists but is intentionally not production-ready

## Adapter matrix

| source family | bank/source | current shape | localguys target | readiness | default local roles | operator command | notes |
|---|---|---|---|---|---|---|---|
| `g3_critic_coder` | core template | critic + coder bounded loop | `g3_localguys` | `ready` | `coder`, `verifier` | `localguys run g3 --task <id>` | first production slice |
| `ralph_loop` | core template | single-agent loop | `ralph_localguys` | `ready` | `coder` | `localguys run ralph --task <id>` | cheapest narrow fix mode |
| `quick_fix` | core template | scout -> coder -> verify | `quickfix_localguys` | `ready` | `scout`, `coder`, `verifier` | `localguys run quickfix --task <id>` | good for bugfix and API wiring |
| `test_only` | core template | scout -> coder[test] -> verify | `testonly_localguys` | `ready` | `scout`, `coder`, `verifier` | `localguys run testonly --task <id>` | should be one of the earliest one-button methods |
| `docs_update` | core template | scout -> docs coder | `docs_localguys` | `ready` | `scout`, `coder` | `localguys run docs --task <id>` | low risk, good proving ground |
| `research_first` | core template | researcher -> architect -> coder -> verify | `research_localguys` | `ready` | `researcher`, `architect`, `coder`, `verifier` | `localguys run research --task <id>` | contract implemented; can stay hybrid at model-selection level |
| `refactor` | core template | deep scout -> architect -> parallel coders -> verify | `refactor_localguys` | `ready` | `scout`, `architect`, `coder`, `verifier` | `localguys run refactor --task <id>` | contract implemented with allowlist gate; parallel coders still collapsed into bounded local pass |
| `bmad_default` | core template | scout + architect + researcher + coder + eval + approval + deploy | `bmad_localguys` | `ready` | `scout`, `researcher`, `architect`, `coder`, `verifier`, `approval` | `localguys run bmad --task <id>` | contract implemented as bounded local BMAD with approval gate; deploy stays outside local runtime |
| `dragons` | heuristic/UI family | preset-driven multi-role team | `dragons_localguys` | `ready` | `scout`, `architect`, `coder`, `verifier` | `localguys run dragons --task <id>` | family contract implemented; preset semantics still come from team profile |
| `openhands_family` | stub template | architect + coder + critic + verifier + deploy | `openhands_localguys` | `stub` | many | `localguys run openhands --task <id>` | do not productize until stub removed |
| `pulse_family` | stub template | planner + scheduler + executor + eval + approval + deploy | `pulse_localguys` | `stub` | many | `localguys run pulse --task <id>` | not a local MVP candidate |
| `saved/*` custom families | saved workflows | user-defined | per-family mapping | `blocked` | unknown | `localguys run custom --task <id> --family <family>` | need contract introspection first |
| `n8n/*` imported | external bank | integration/automation flows | per-family mapping | `blocked` | varies | `localguys run n8n --task <id> --family <family>` | not until import contracts are normalized |
| `comfyui/*` imported | external bank | graph/image workflows | per-family mapping | `blocked` | varies | `localguys run comfy --task <id> --family <family>` | separate visual/runtime concerns |
| `imported/*` generic | external bank | arbitrary imported flow | per-family mapping | `blocked` | unknown | `localguys run imported --task <id> --family <family>` | explicit exclusion until typed |

## Near-term rollout order
1. `g3_localguys`
2. `ralph_localguys`
3. `quickfix_localguys`
4. `testonly_localguys`
5. `docs_localguys`
6. `research_localguys`
7. `dragons_localguys`
8. `refactor_localguys`
9. `bmad_localguys`

## Command surface target
All operator commands should be thin wrappers over the same MCC runtime.

Examples:
- `localguys run g3 --task <task_id>`
- `localguys run ralph --task <task_id>`
- `localguys run quickfix --task <task_id>`
- `localguys run testonly --task <task_id>`
- `localguys run docs --task <task_id>`
- `localguys run research --task <task_id>`
- `localguys run dragons --task <task_id>`
- `localguys run refactor --task <task_id>`
- `localguys run bmad --task <task_id>`

Shared guarantees:
- same `workflow_contract` resolution
- same playground locking
- same artifact contract
- same verifier/failure semantics
- same MCC observability path

## Implementation consequences
### Contract layer
Need explicit contracts for:
- `ralph_localguys`
- `quickfix_localguys`
- `testonly_localguys`
- `docs_localguys`
- `research_localguys`
- later: operator tooling for `dragons_localguys`, `refactor_localguys`, `bmad_localguys`

### Model policy layer
Need role defaults per adapted family, not only per model.

Examples:
- `ralph_localguys` -> `coder=qwen3:8b`, no verifier by default unless strict mode enabled
- `testonly_localguys` -> `scout=qwen2.5:3b`, `coder=qwen2.5:7b`, `verifier=deepseek-r1:8b`
- `research_localguys` -> `researcher=qwen3:8b or gemma3:12b`, `architect=hybrid/cloud initially`

### Operator layer
Need one shared operator binary/tool with subcommands, not separate ad hoc scripts.

Preferred structure:
- `localguys run <method> --task <id>`
- `localguys status <run_id>`
- `localguys artifacts <run_id>`
- `localguys stop <run_id>`

## Explicit exclusions for now
Do not adapt first:
- imported arbitrary workflows
- deploy-heavy families
- multi-surface graph/stub families with no proven contract
- wide refactor families without subtask split

## Decision
Phase 177 is now defined as:
- prove the runtime with `g3_localguys`
- then adapt the rest of the useful MCC workflow families through one shared contract/runtime
- then expose one-button/one-command launchers per method/team style
