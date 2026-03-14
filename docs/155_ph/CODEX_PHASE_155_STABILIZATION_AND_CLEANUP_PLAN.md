# Phase 155 MCC Stabilization and Cleanup Plan (Codex)

## Scope
- Reviewed architecture target in `docs/154_ph/MCC_ARCHITECTURE_DIAGRAM.md`.
- Reviewed Gemini execution draft in `docs/154_ph/PHASE_155_IMPLEMENTATION.md`.
- Audited current MCC implementation and markers in `client/src/components/mcc/*` and `client/src/store/useMCCStore.ts`.

## Root Cause of White Screen
- Immediate crash source was not `ReactFlowProvider` (it is present in current MCC).
- Crash source was missing identifiers in `MyceliumCommandCenter`:
  - `fetchDAG`
  - `mccReady` / `setMccReady`
  - `showOnboarding` / `setShowOnboarding`
- These names were still referenced inside hooks/render and caused runtime/compile failure.

## Fix Applied
- File: `client/src/components/mcc/MyceliumCommandCenter.tsx`
- Restored:
  - `fetchDAG` callback (DAG API load + fallback stats)
  - `showOnboarding` state
  - `mccReady` state
- This is a stabilization patch only; no redesign of navigation model was introduced.

## Marker Audit (Phase 154/155)
- Confirmed active marker clusters:
  - `MARKER_155.1/2/3` in `DAGView.tsx` (zoom controls + imperative camera API)
  - `MARKER_155.2A/3A` in `MyceliumCommandCenter.tsx` (tasks-level tree + level-aware routing)
  - `MARKER_155.DRAGGABLE.*` in `MiniWindow.tsx` and mini-windows
  - `MARKER_154.2A` in `FooterActionBar.tsx` (max 3 contextual actions)
  - `MARKER_154.1B` in `useMCCStore.ts` (level config, first_run state)
- Gap vs implementation doc:
  - `MARKER_155.DANGER.STUB` placeholder is defined in plan but not consistently materialized in code comments.

## Cleanup Plan After Minimax Iteration

### P0 (stability, now)
- Remove dead/unused imports and states in `MyceliumCommandCenter.tsx` (WizardContainer branch residue, unused tooltip vars, unused captain vars).
- Add a single guard rail comment block for critical lifecycle vars (`fetchDAG`, `mccReady`, onboarding state) to prevent partial deletion in future edits.
- Verify runtime in dev UI (open MCC, roadmap -> tasks drill, back navigation, footer actions).
- MARKER_155.P3_5.JEPA_AUTOSTART: run JEPA runtime together with main Mycelium server in launch path (`run.sh`) and app lifespan (`main.py`) with health-wait and graceful shutdown cleanup, so architecture strict mode does not start in degraded state.

### P1 (architecture alignment)
- Implement explicit `MARKER_155.DANGER.STUB` comments for deferred camera URL sync and other postponed behaviors.
- Ensure one clear source of truth for step flow:
  - either keep `FirstRunView` path only
  - or fully wire `WizardContainer`
  - do not keep both half-active.

### P2 (debt cleanup)
- Remove deprecated MCC files when references are fully eliminated:
  - `RailsActionBar.tsx`
  - `WorkflowToolbar.tsx`
  - `MCCTaskList.tsx`
  - `MCCDetailPanel.tsx`
- Keep marker-based deprecation notes in commit message and migration doc.

## Notes
- Global frontend typecheck currently has many unrelated legacy errors outside MCC scope; this patch targets MCC white-screen recovery first.
