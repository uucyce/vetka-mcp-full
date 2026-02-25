# CODEX Unified DAG Recon Map (Phase 155+)

**Date:** 2026-02-22  
**Status:** RECON COMPLETE, READY FOR IMPL NARROW  
**Canonical Plan:** `docs/155_ph/CODEX_UNIFIED_DAG_MASTER_PLAN.md`

## Usage
This is a surgical change map:
- `Marker` -> what to implement
- `File + line anchor` -> where to patch
- `Action` -> add/update/remove
- `Risk` -> likely regression
- `Verify` -> minimal acceptance check

## Hot Path (Do First)

| Marker | Phase | File | Line anchor | Action | Change intent | Risk | Verify |
|---|---|---|---|---|---|---|---|
| `MARKER_155A.P0.FLOW_GATE` | P0 | `client/src/store/useMCCStore.ts` | `:467`, `:479`, `:483` | `update` | Gate startup: prevent direct landing into drill levels before setup complete. | Existing users might lose restored context unexpectedly. | Fresh profile starts setup; existing setup users resume DAG safely. |
| `MARKER_155A.P0.FLOW_GATE` | P0 | `client/src/store/useMCCStore.ts` | `:239` | `update` | Change default `navLevel` to first-run-safe bootstrap behavior. | May affect tests relying on roadmap default. | No project -> `first_run`; configured project -> DAG. |
| `MARKER_155A.P0.STEP_VISIBILITY` | P0 | `client/src/components/mcc/MyceliumCommandCenter.tsx` | `:715`, `:716`, `:778`, `:817` | `update` | Hide/limit step strip and floating windows until setup context is valid. | Users may think elements disappeared. | On first run only setup UI visible; no premature Drill. |
| `MARKER_155A.P0.STEP_VISIBILITY` | P0 | `client/src/components/mcc/StepIndicator.tsx` | `:35`, `:38`, `:42` | `update` | Correct step mapping so `tasks/workflow` does not always imply Step 5. | Step-state confusion if mapping inconsistent with store. | Step progression matches flow (1->2->3->4->5). |
| `MARKER_155A.P0.ONBOARDING_REBIND` | P0 | `client/src/components/mcc/OnboardingOverlay.tsx` | `:14`, `:15-18`, `:29` | `update` | Rebind onboarding targets to current UI data-onboarding anchors. | Null-target overlay with dark mask. | Overlay highlights real elements. |
| `MARKER_155A.P0.ONBOARDING_REBIND` | P0 | `client/src/components/mcc/MyceliumCommandCenter.tsx` | `:1112`, `:1120` | `update` | Run hints only in correct first-start context; avoid overlap with modal/setup. | Double onboarding (overlay + modal) race. | Only one guided layer at a time. |
| `MARKER_155A.P0.ONBOARDING_REBIND` | P0 | `client/src/hooks/useOnboarding.ts` | `:11`, `:37`, `:52` | `update` | Scope onboarding lifecycle to MCC setup flow and persist completion cleanly. | Re-show onboarding to old users accidentally. | First launch shows once; dismissed/completed persists. |

## Full Marker Map (P0..P4)

| Marker | Phase | File | Line anchor | Action | Change intent | Risk | Verify |
|---|---|---|---|---|---|---|---|
| `MARKER_155A.P1.GRAPH_SCHEMA` | P1 | `client/src/components/mcc/MyceliumCommandCenter.tsx` | `:100`, `:415`, `:423`, `:442` | `update` | Move from split roadmap/tasks/workflow payload semantics toward unified graph contract adapters. | Contract mismatch with backend APIs. | Single payload adapter can render LOD1+LOD2. |
| `MARKER_155A.P1.CROSSCUT_TASKS` | P1 | `client/src/components/mcc/MyceliumCommandCenter.tsx` | `:423-439` | `update` | Support `affected_nodes[]` mapping instead of only module/tag fallback. | Over-linking tasks to unrelated branches. | One task can appear on multiple branches deterministically. |
| `MARKER_155A.P1.ADAPTERS` | P1 | `client/src/components/mcc/MyceliumCommandCenter.tsx` | `:58`, `:78`, `:88`, `:265` | `update` | Normalize mapping functions to unified node/edge kinds and IDs. | Break existing DAG fields if not backward-compatible. | Old payloads still render through adapter fallback. |
| `MARKER_155A.P2.LOD_THRESHOLDS` | P2 | `client/src/components/mcc/DAGView.tsx` | `:45-50`, `:165-199` | `update` | Define consistent LOD threshold behavior for architecture/tasks/workflow zoom zones. | Jitter during zoom transitions. | Zoom in/out switches context smoothly without remounting screen. |
| `MARKER_155A.P2.FRACTAL_RENDER` | P2 | `client/src/components/mcc/DAGView.tsx` | `:137-159` | `update` | Render parent architecture and child workflow hints in one canvas using scalable density rules. | Performance regression on large graphs. | 1k+ nodes still interactive with bounded FPS drop. |
| `MARKER_155A.P2.FAN_LAYOUT_BRIDGE` | P2 | `client/src/components/mcc/DAGView.tsx` | `:138`, `:493` | `update` | Bridge fan-layout/Sugiyama behavior into unified LOD rendering policy. | Layout instability between level switches. | Node positions preserve spatial memory across drill. |
| `MARKER_155A.P2.DRILL_POLICY` | P2 | `client/src/components/mcc/MyceliumCommandCenter.tsx` | `:526`, `:536`, `:543`, `:844` | `update` | Keep drill in same canvas with clear focus/back logic and hint consistency. | Incorrect drill on virtual nodes. | Double-click task opens workflow context in place. |
| `MARKER_155A.P2.CAMERA_STATE` | P2 | `client/src/store/useMCCStore.ts` | `:246-248`, `:555` | `update` | Persist camera/focus for smooth return path across drill levels. | Stale camera values on graph refresh. | Back returns to previous view position reliably. |
| `MARKER_155A.P3.NODE_CONTEXT_WINDOW` | P3 | `client/src/components/mcc/MyceliumCommandCenter.tsx` | `:548-559` | `update` | Activate node-centric mini window instead of unused selected node data. | Duplicate panels and conflicting interactions. | Clicking node opens one context mini-window. |
| `MARKER_155A.P3.MODEL_EDIT_BIND` | P3 | `client/src/components/mcc/MCCDetailPanel.tsx` | `:2-12`, `:32-36` | `update` | Extract model-edit and node detail capabilities from deprecated panel into new mini-window. | Reviving deprecated code path accidentally. | Model can be viewed/changed from selected node context. |
| `MARKER_155A.P3.STATS_CONTEXT` | P3 | `client/src/components/mcc/MiniStats.tsx` | `:75`, `:102`, `:109` | `update` | Make stats contextual (global/module/task/agent) instead of only global analytics pulls. | API fan-out and stale values. | Selected node changes stats scope instantly. |
| `MARKER_155A.P3.STREAM_CONTEXT` | P3 | `client/src/components/mcc/MyceliumCommandCenter.tsx` | `:361-380`, `:973` | `update` | Bind stream visibility and content to focused task/agent context. | Stream gets too noisy for local context. | Focused task shows filtered live events. |
| `MARKER_155A.P4.ARCHITECT_MERGE` | P4 | `client/src/store/useMCCStore.ts` | `:498-505` | `update` | Add integration task metadata flow for architect merge checkpoints. | Complex task dependencies may deadlock visually. | Integration task links appear as explicit graph nodes/edges. |
| `MARKER_155A.P4.CONFLICT_POLICY` | P4 | `client/src/components/mcc/MyceliumCommandCenter.tsx` | `:865`, `:869`, `:895` | `update` | Expose conflict/merge actions in context when overlapping code-space tasks detected. | Overloading primary actions beyond 3 slots. | Conflict actions appear in gear/secondary only. |
| `MARKER_155A.P4.INTEGRATION_VERIFY` | P4 | `client/src/components/mcc/FooterActionBar.tsx` | `:19`, `:55`, `:74` | `update` | Add verify/integration secondary actions while preserving 3 primary buttons. | Shortcut collisions and accidental actions. | Primary button count remains <=3 in all states. |

## Legacy / Remove Candidates (Post-Stabilization)

| Marker | File | Line anchor | Action | Why |
|---|---|---|---|---|
| `MARKER_155A.CLEANUP.LEGACY_WIZARD` | `client/src/components/mcc/WizardContainer.tsx` | `:223` | `remove/update` | References `setNavLevel` not in store API; currently half-integrated path. |
| `MARKER_155A.CLEANUP.LEGACY_DETAIL` | `client/src/components/mcc/MCCDetailPanel.tsx` | `:1-13` | `extract/remove` | Deprecated but still holds useful node model-edit logic to migrate. |
| `MARKER_155A.CLEANUP.LEGACY_RAILS` | `client/src/components/mcc/RailsActionBar.tsx` | `:4-13` | `remove` | Deprecated duplicate action system. |
| `MARKER_155A.CLEANUP.LEGACY_WORKFLOW_TOOLBAR` | `client/src/components/mcc/WorkflowToolbar.tsx` | `:4-12` | `remove` | Deprecated duplicate action system. |
| `MARKER_155A.CLEANUP.LEGACY_TASK_DAG` | `client/src/components/mcc/TaskDAGView.tsx` | `:2`, `:62` | `remove` | Conflicts with single-canvas unified DAG direction. |

## Deferred Stubs (`DANGER.STUB`)

| Marker | File | Action | Intent |
|---|---|---|---|
| `MARKER_155A.DANGER.STUB.CAMERA_URL_SYNC` | `client/src/store/useMCCStore.ts` | `add` | URL persistence for camera/focus (defer to later wave). |
| `MARKER_155A.DANGER.STUB.HINT_WORKFLOW_PREVIEW` | `client/src/components/mcc/DAGView.tsx` | `add` | Tiny workflow previews at LOD1, behind perf guard. |
| `MARKER_155A.DANGER.STUB.GRAPH_BACKEND_UNIFIED_ENDPOINT` | `client/src/components/mcc/MyceliumCommandCenter.tsx` | `add` | Placeholder for single backend endpoint migration. |

## Verify Checklist (Global)
- No white screen; MCC mounts on fresh and existing sessions.
- First-run user never lands directly in `tasks/workflow` before setup completion.
- Onboarding highlights valid targets in current UI.
- Drill remains in single canvas; no route/screen switching.
- Primary action bar never exceeds 3 buttons.
