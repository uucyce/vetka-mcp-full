# PHASE 164 — P5.P4 Workflow Guidance Depth Recon Markers Report (2026-03-11)

Status: `RECON COMPLETE`

## Goal
Зафиксировать, что шаг `164-P5.P4` действительно довел MYCO workflow guidance до уровня role/status-aware chat-guidance и синхронизировал top hint с chat без возврата к generic roadmap fallback.

## Closed Step
- `164-P5.P4` closed

## Recon Verdict
1. P5.P4 подтвержден в текущем дереве.
2. Top hint и chat опираются на один и тот же статусный хвост next-step (`running` / `done` / `failed` / fallback).
3. Workflow focus удерживает приоритет над roadmap/module-unfold fallback.
4. Глубина guidance расширена до role/gate веток, а не только `architect/coder/verifier`.

## Markers Confirmed
1. `MARKER_164.P5.P4.MYCO.WORKFLOW_ROLE_STATUS_DEPTH_MATRIX.V1`
2. `MARKER_164.P5.P4.MYCO.TOP_HINT_ROLE_STATUS_DEPTH_MATRIX.V1`
3. `MARKER_164.P5.P4.MYCO.WORKFLOW_OPEN_NO_GENERIC_ROADMAP_FALLBACK.V1`
4. `MARKER_164.P5.P4.MYCO.SCOUT_RESEARCH_GUIDANCE_SPLIT.V1`
5. `MARKER_164.P5.P4.MYCO.VERIFIER_EVAL_GUIDANCE_SPLIT.V1`
6. `MARKER_164.P5.P4.MYCO.QUALITY_DEPLOY_GUIDANCE_BRANCHES.V1`

## What Was Confirmed In Code
1. In [MiniChat.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MiniChat.tsx):
- вынесен общий `buildWorkflowStatusAction(...)` для статусных next-step веток;
- вынесен `buildWorkflowRoleGuidance(...)` с ветками `architect`, `scout`, `researcher`, `coder`, `verifier`, `eval`, `quality gate`, `approval gate`, `deploy`, `measure`;
- workflow guidance применяется не только при `taskDrillExpanded`, но и при `workflowNodeContext`;
- после установления workflow focus чат не падает обратно в generic roadmap/module-unfold формулировки.

2. In [MyceliumCommandCenter.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx):
- top hint использует `buildTopHintWorkflowStatusAction(activeTaskStatus)`;
- role-aware workflow hint вызывается в обеих workflow-ветках: `isTaskWorkflowExpanded` и `isWorkflowFocused`;
- top hint держит workflow priority выше unfold fallback;
- матрица top-hint покрывает те же role/gate сценарии, что и chat.

3. In [test_phase164_p5_p4_workflow_guidance_depth_contract.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/test_phase164_p5_p4_workflow_guidance_depth_contract.py):
- проверяется присутствие P5.P4 markers в chat и top hint;
- проверяются все ключевые role/gate token-ветки top hint;
- проверяется повторное использование role-guidance helper в двух workflow paths.

## Scope Reconstruction
1. `architect`
- guidance переведен от generic "workflow open" к конкретному действию по subtasks/team preset.

2. `scout` / `researcher`
- разведены в разные сценарии: code surface/deps vs docs/constraints evidence.

3. `coder`
- закреплен как Context/model/prompt execution path, а не просто общий agent fallback.

4. `verifier` / `eval`
- разведены на acceptance/completeness vs score/quality signals.

5. `quality gate` / `approval gate` / `deploy` / `measure`
- добавлены как отдельные workflow-stage ветки, чтобы MYCO объяснял transition decision, release decision и telemetry loop.

6. Task status tail
- `running`: monitor stream/stats and wait verify/eval gate;
- `done`: inspect artifacts/result and move to next queued task or targeted retry;
- `failed`: inspect failure cause and retry with corrected model/prompt;
- fallback: start from Tasks and iterate through Context/stream.

## Non-P5.P4 Noise Separated During Recon
1. В [MiniChat.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MiniChat.tsx) рядом присутствуют маркеры `PHASE 168` по compact avatars/runtime preview.
2. Эти блоки не относятся к P5.P4 guidance-depth и в recon не засчитывались как часть закрытого шага.

## Files Confirmed
1. [MyceliumCommandCenter.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx)
2. [MiniChat.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MiniChat.tsx)
3. [test_phase164_p5_p4_workflow_guidance_depth_contract.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/test_phase164_p5_p4_workflow_guidance_depth_contract.py)
4. [PHASE_164_P5_P4_WORKFLOW_GUIDANCE_DEPTH_IMPL_REPORT_2026-03-11.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/164_MYCO_ARH_MCC/PHASE_164_P5_P4_WORKFLOW_GUIDANCE_DEPTH_IMPL_REPORT_2026-03-11.md)
5. [README.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/164_MYCO_ARH_MCC/README.md)

## Verification Snapshot
Command:

```bash
pytest -q \
  tests/test_phase164_p5_p4_workflow_guidance_depth_contract.py \
  tests/test_phase164_p5_p3_workflow_priority_over_unfold_contract.py \
  tests/test_phase164_p5_p2_task_status_propagation_contract.py \
  tests/test_phase164_p5_p1_status_aware_guidance_contract.py
```

Expected contract result:
- `9 passed`
- legacy warning in `conftest.py` may remain and is outside P5.P4 scope

## Carry Forward
Next logical step remains `164-P5.P5`:
- scenario synchronization for `roadmap -> task -> workflow -> agent -> run/retry`
- goal: top hint and chat must not diverge across transition edges

## Recon Gate
`164-P5.P4` is documented and can be treated as closed with markers.
