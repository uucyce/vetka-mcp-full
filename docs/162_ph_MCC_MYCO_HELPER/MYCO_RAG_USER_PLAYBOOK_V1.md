# MYCO RAG User Playbook V1

Marker: `MARKER_162.P3.P3.MYCO.RAG_USER_PLAYBOOK_SPLIT.V1`

## Quick flow
1. Open project tab.
2. Select node or task.
3. Ask MYCO for next action.
4. If needed, drill into workflow and choose model/context.

## MYCO prompts
- "Explain this node and dependencies"
- "Plan next action for this task"
- "Show mismatch between task and code area"
- "What changed in orchestration status?"

## Interpreting replies
1. `focus` tells what MYCO currently reads.
2. `multitask` tells execution pressure (active/queued/done + cap).
3. `digest` tells project phase and summary.
4. `hidden memory index` means instruction corpus is available to helper path.

## Guardrails
1. MYCO suggests; user/architect executes.
2. If no node selected, MYCO returns project-level guidance.
3. In ambiguous context, prefer asking follow-up clarifier.
