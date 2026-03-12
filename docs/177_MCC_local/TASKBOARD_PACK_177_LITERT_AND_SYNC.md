# PHASE 177 — TaskBoard pack: LiteRT + roadmap sync

Date: 2026-03-12
Status: ready_for_import
Tag: `localguys`

## Notes
This is a concrete task pack for TaskBoard import or manual creation.
It is intentionally narrow and benchmark-first.

## Task pack

### tb_localguys_177_litert_1
- title: LiteRT feasibility on Apple Silicon
- priority: 1
- phase_type: research
- workflow_family: research_localguys
- team_profile: dragon_silver
- tags: `localguys`, `litert`, `benchmark`, `apple-silicon`
- description:
  - verify LiteRT build/run path on macOS Apple Silicon
  - document realistic supported acceleration paths for our environment
  - output benchmark notes and recommendation: adopt / benchmark-only / drop
- acceptance:
  - reproducible setup notes
  - one successful local run path
  - explicit risk list

### tb_localguys_177_litert_2
- title: LiteRT vs current local stack benchmark pack
- priority: 1
- phase_type: build
- workflow_family: g3_localguys
- team_profile: dragon_silver
- tags: `localguys`, `litert`, `benchmark`, `metrics`
- description:
  - build a comparable benchmark pack for LiteRT vs current local runtime
  - compare latency, runtime stability, artifact overhead, and summary metrics
  - emit results in MCC-compatible summary shape
- acceptance:
  - stable benchmark schema
  - at least one comparable result table
  - recommendation grounded in measured output

### tb_localguys_177_litert_3
- title: Add LiteRT benchmark lane to MCC metrics surface
- priority: 2
- phase_type: build
- workflow_family: quickfix_localguys
- team_profile: dragon_silver
- tags: `localguys`, `litert`, `mcc`, `metrics`
- description:
  - expose LiteRT benchmark results through the same summary surface used for localguys
  - avoid a separate dashboard
  - keep schema aligned with benchmark summary endpoint style
- acceptance:
  - benchmark summary visible in MCC stats surface
  - no schema drift from existing localguys metrics path

### tb_localguys_177_sync_1
- title: Design roadmap-taskboard context packet
- priority: 1
- phase_type: research
- workflow_family: research_localguys
- team_profile: dragon_silver
- tags: `localguys`, `roadmap`, `taskboard`, `context-packet`
- description:
  - define the exact machine-readable packet for task dispatch
  - include roadmap binding, docs, code scope, tests, workflow contract, artifacts
  - keep it compatible with MCC/localguys
- acceptance:
  - packet schema doc
  - example payload for one real task
  - gap list vs current MCC implementation

### tb_localguys_177_sync_2
- title: Add roadmap binding fields to TaskBoard task model
- priority: 1
- phase_type: build
- workflow_family: g3_localguys
- team_profile: dragon_silver
- tags: `localguys`, `roadmap`, `taskboard`, `metadata`
- description:
  - extend TaskBoard tasks with roadmap binding fields
  - preserve compatibility with existing adapters and MCC routes
  - keep fields optional and serializable
- acceptance:
  - fields persist through create/read/update
  - no regression in existing TaskBoard adapters

### tb_localguys_177_sync_3
- title: Add MCC task context packet endpoint
- priority: 1
- phase_type: build
- workflow_family: g3_localguys
- team_profile: dragon_silver
- tags: `localguys`, `mcc`, `taskboard`, `context-packet`
- description:
  - add API endpoint that resolves task + roadmap + workflow + docs + tests + artifacts
  - return a single dispatch packet for agents
  - use this as the canonical launch context for localguys
- acceptance:
  - one endpoint returns full packet for a bound task
  - structured errors for missing binding pieces

### tb_localguys_177_sync_4
- title: Add roadmap to taskboard task generator tool path
- priority: 2
- phase_type: build
- workflow_family: quickfix_localguys
- team_profile: dragon_silver
- tags: `localguys`, `roadmap`, `taskboard`, `automation`
- description:
  - formalize roadmap node -> task template -> TaskBoard entry flow
  - preserve node bindings and docs
  - keep generated tasks narrow and import-safe
- acceptance:
  - one roadmap node can generate a task pack
  - generated tasks preserve roadmap metadata

### tb_localguys_177_sync_5
- title: Sync TaskBoard completion back into roadmap progress
- priority: 2
- phase_type: build
- workflow_family: ralph_localguys
- team_profile: dragon_silver
- tags: `localguys`, `roadmap`, `taskboard`, `status-sync`
- description:
  - when task status/verifier outcome changes, update roadmap execution state
  - make progress visible without manual bookkeeping
- acceptance:
  - completion updates roadmap state
  - failed/blocked states also propagate cleanly

## Suggested execution order
1. `tb_localguys_177_sync_1`
2. `tb_localguys_177_sync_2`
3. `tb_localguys_177_sync_3`
4. `tb_localguys_177_sync_4`
5. `tb_localguys_177_sync_5`
6. `tb_localguys_177_litert_1`
7. `tb_localguys_177_litert_2`
8. `tb_localguys_177_litert_3`
