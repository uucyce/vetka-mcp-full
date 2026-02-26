# MCC Task Anchoring Implementation Plan (2026-02-26)

## Scope
MCC roadmap canvas: deterministic binding of task nodes to architecture tree with strict minimal UI behavior.

## Contract v1
1. Task -> Anchor Resolution (priority)
- `primary_node_id` (exact id)
- `affected_nodes[]` (exact ids, max 3)
- `module/file_path` (normalized path match to roadmap node ids/labels/project ids)
- fallback: `UNPLACED` lane (right rail)

2. Placement
- Anchored task node is placed near anchor barycenter with collision-safe vertical offsets.
- Unplaced tasks are placed in right rail stack (`UNPLACED`) without overlapping core architecture.
- Edge style remains direct vectors.

3. UX behavior
- Task list and roadmap task nodes are selection-synced.
- Click on roadmap task node opens Matryoshka workflow level (`drillDown('workflow')`).
- No extra popup windows for task workflow drill.

4. Task execution contract fields
- Each task node carries normalized execution metadata:
  - `taskOrigin` (`architect|chat|manual|system` normalized from source)
  - `teamProfile` (defaults to `dragon_bronze`)
  - `workflowId` (existing id or deterministic fallback)

## Implementation steps
1. Add resolver helpers for exact/path anchor matching.
2. Extend roadmap overlay payload for anchor metadata + execution metadata.
3. Add post-layout task placement pass in `DAGView` for anchor/rail positioning.
4. Add selection sync effect (`selectedTaskId` <-> `task_overlay_<id>`).
5. Update click behavior for roadmap task node -> workflow drill.
6. Extend type contract (`TaskData`/`DAGNode`) with execution metadata fields.

## Acceptance checklist
- [ ] Tasks with `primary_node_id` attach near that node.
- [ ] Tasks with only `module/file_path` attach near matched node.
- [ ] Tasks with no resolvable anchors appear in right rail.
- [ ] Task node click from roadmap opens workflow matryoshka.
- [ ] Selecting task in MiniTasks highlights corresponding roadmap task node.
- [ ] `teamProfile` and `workflowId` always present on overlay task node.
- [ ] No graph jitter regression from this change.

## Smoke run
1. Open MCC roadmap with tasks loaded.
2. Validate 3 categories:
- anchored by id,
- anchored by module/path,
- unplaced.
3. Click each roadmap task node and verify workflow drill.
4. Select task in MiniTasks and verify node selection sync.
5. Reload app and ensure behavior remains deterministic.
