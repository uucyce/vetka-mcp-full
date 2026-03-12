# MCC Agent Context Audit Starter

Status: starter
Task: `tb_1773276211_1`

## Goal
Verify that enriched task context packets are not only available via MCC API, but are actually consumed by MCC agents through workflow and DAG-linked execution paths.

## Audit questions
1. Which MCC agent/runtime paths currently request task context directly?
2. Which paths still rely on ad hoc task title/description only?
3. Where do workflow binding, roadmap binding, docs, code scope, tests, and artifact history get dropped?
4. Which roles already receive role-specific context and which do not?

## Files to inspect first
- `src/api/routes/mcc_routes.py`
- `src/services/roadmap_task_sync.py`
- `src/services/architect_prefetch.py`
- `client/src/components/mcc/MyceliumCommandCenter.tsx`
- `client/src/components/mcc/MiniContext.tsx`
- `src/orchestration/agent_pipeline.py`

## Expected output
- path map: producer -> transport -> consumer
- gaps where packet exists but is not consumed
- recommendation for one canonical packet ingestion path for MCC agents
