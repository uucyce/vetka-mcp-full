# MCC Agent Context Audit — 2026-03-12

Status: audit snapshot
Task: `tb_1773276211_1`

## Goal
Check whether enriched MCC task context packets are actually consumed by MCC agent paths, not only exposed by API.

## Producer -> transport -> consumer map
### Producer
- `src/services/roadmap_task_sync.py`
  - builds enriched task packet with roadmap binding, docs, code scope, tests, artifacts, history, gaps
- `src/api/routes/mcc_routes.py`
  - `GET /api/mcc/tasks/{task_id}/context-packet`
  - resolves workflow binding and contract, injects latest localguys run

### Transport
- task metadata in TaskBoard
- workflow binding in MCC routes
- ad hoc UI context in MCC panels
- prefetch context in architect path

### Current consumers
- `client/src/components/mcc/MiniStats.tsx`
  - consumes benchmark and runtime summaries
  - does not consume the full task context packet
- `client/src/components/mcc/MiniContext.tsx`
  - renders context previews for humans
  - currently acts as UI preview, not agent runtime ingestion path
- `src/services/architect_prefetch.py`
  - prepares role/workflow-oriented context from task description, task type, complexity, and workflow family
  - does not currently take the canonical MCC task context packet
- `src/orchestration/agent_pipeline.py`
  - calls `ArchitectPrefetch.prepare(...)`
  - still passes task description and phase info rather than packet-first context

## Findings
1. The canonical packet now exists, but agent runtime consumption is still partial.
2. Human-facing MCC surfaces are ahead of agent-facing ingestion.
3. `ArchitectPrefetch.prepare(...)` remains the main bridge, but it is still packet-poor.
4. DAG/workflow links exist in MCC, but packet-first transport into agent execution is not yet canonical.

## Concrete gap
The strongest current gap is:
- packet producer exists
- packet endpoint exists
- TaskBoard bindings exist
- but `agent_pipeline` and `architect_prefetch` do not yet use `task_id -> context-packet` as the canonical intake path

## Recommended next fix
1. add packet-aware prefetch entrypoint
2. route MCC/agent launch through `task_id -> context-packet`
3. preserve role-specific slices from the same canonical packet
4. keep MiniContext as preview of the same packet, not a parallel source of truth

## Outcome
The system is now structurally ready for packet-first agent intake, but the actual consumer path is not fully switched over yet.
