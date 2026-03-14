# MYCO Help Rules Library V1

Status: `P0 CONTRACT`
Date: `2026-03-06`

Marker: `MARKER_162.MYCO.RULES_FALLBACK.V1`

## Purpose
Rule-first подсказки без зависимости от LLM.

## Core rule matrix
1. `nav=roadmap + node=project`
- Explain: что это карта проекта.
- Next: кликни по модулю или задаче.

2. `node=task`
- Explain: задача привязана к модулю/коду.
- Next: Enter drill-in -> workflow.

3. `node=agent`
- Explain: роль агента + статус + модель.
- Next: open context -> change model.

4. `node=file|directory`
- Explain: участок кодовой базы.
- Next: открыть контекст/артефакт.

5. `nav=workflow`
- Explain: runtime pipeline, стрелки = зависимости/feedback.
- Next: выбрать ноду и смотреть stream/context.

## Output templates
1. `what`
2. `why`
3. `next`

## LLM optional overlay
Marker: `MARKER_162.MYCO.LLM_ENRICHMENT_OPTIONAL.V1`
1. If LLM unavailable -> rules only.
2. If LLM available -> enrich wording, not structure.
3. LLM cannot contradict rule facts (nav/node/status).
