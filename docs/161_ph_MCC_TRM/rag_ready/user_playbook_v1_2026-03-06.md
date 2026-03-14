# User Playbook V1 (How to use MYCO in MCC)

Status: RAG-ready  
Date: 2026-03-06

Markers:
- `MARKER_161.USER.PLAYBOOK.V1`
- `MARKER_161.USER.PLAYBOOK.DAG_BUILD.V1`
- `MARKER_161.USER.PLAYBOOK.COMPARE_SELECT.V1`

## Quick scenario
User opens MCC, creates/selects project tab, builds DAG, compares variants, sets best version.

## Step-by-step

## 1) Create/open project tab
1. Open existing tab or press `+ project`.
2. Choose source:
   - `From Disk`
   - `From Git`
   - Empty/new project
3. Choose workspace folder for this tab project.

What to ask MYCO:
- "Помоги выбрать source и workspace для нового проекта."

## 2) Build architecture DAG
Ask MYCO:
- "Построй baseline DAG и покажи здоровье графа."

Expected:
- Graph appears.
- `Graph Health` shows verifier status.
- `TRM Source` indicates baseline/refined state (debug chip).

## 3) Try TRM refine safely
Ask MYCO:
- "Сравни baseline, trm_light, trm_balanced."

Expected:
- Compare matrix with scores.
- Each variant has source/meta diagnostics.
- If refine unsafe: automatic rollback to baseline.

## 4) Select best version
Ask MYCO:
- "Покажи лучший вариант и сделай его primary."

Expected:
- Best version identified by score.
- Primary version updated.
- `dag-versions/list` reflects selected primary and source status.

## 5) Drill to task architecture
Ask MYCO:
- "Для этой ноды построить task workflow."

Expected:
- Task Architect decomposes module into task DAG/workflow.
- Visible dependencies and ownership boundaries.

## How MYCO should explain statuses to users
- `graph_source=baseline`: base safe architecture graph.
- `graph_source=trm_refined`: refined graph passed safety gate.
- `trm_meta.status=rejected`: refine candidates were rejected; baseline kept.
- `trm_meta.status=degraded`: refine path unavailable; baseline kept.

## Common commands (ready phrases)
- "Построй архитектурный DAG проекта."
- "Объясни почему сейчас baseline."
- "Запусти compare и покажи разницу между профилями."
- "Сделай primary лучший DAG."
- "Разложи выбранный модуль в task workflow."

## Troubleshooting

### Copy failed on source import
- Re-run folder selection.
- MYCO should report tolerant copy behavior and skipped missing files.

### DAG looks noisy
- Ask MYCO to run compare profiles and pick cleaner variant.
- Prefer `baseline` or `trm_light` for conservative mode.

### User unsure what to do
MYCO should always offer one next step only:
1. build
2. compare
3. promote primary
4. drill to task workflow

