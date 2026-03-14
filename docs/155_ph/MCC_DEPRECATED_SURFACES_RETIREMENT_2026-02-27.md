# MCC Deprecated Surfaces Retirement Policy (2026-02-27)

Статус: active safety policy.

## Scope
Legacy MCC UI surfaces that must not re-enter runtime path:
- `MCCTaskList.tsx`
- `MCCDetailPanel.tsx`
- `WorkflowToolbar.tsx`
- `RailsActionBar.tsx`
- `TaskDAGView.tsx`

## Policy
1. Runtime lock
- Every file above carries marker: `MARKER_155A.G25.DEPRECATED_SURFACE_LOCK`.
- Main runtime path (`MyceliumCommandCenter` + mini windows) must not import them.

2. Guard tests
- Marker tests enforce:
  - no new imports of deprecated surfaces from `client/src/components/mcc/*.tsx` runtime files;
  - explicit lock marker present in each deprecated file.

3. Data-layer compatibility
- Shared state remains in `useMCCStore`; only legacy view shells are deprecated.
- This keeps business logic unified while shrinking UI branch entropy.

4. Removal strategy
- Current phase: keep files as locked references.
- Next safe phase: move to `archive/` or delete after one release cycle with green guard tests.

## Linked markers
- `MARKER_155A.G25.DEPRECATED_UI_RUNTIME_GUARD`
- `MARKER_155A.G25.DEPRECATED_SURFACE_LOCK`
- `MARKER_155A.G25.MINITASKS_EXPANDED_V2`
