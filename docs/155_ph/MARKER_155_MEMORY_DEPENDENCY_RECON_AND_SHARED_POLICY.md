# MARKER_155 Memory Dependency Recon And Shared Policy

Status: Recon complete (no code changes in this step)  
Date: 2026-02-23  
Owner: MCC/VETKA Architecture

Markers:
- `MARKER_155.MEMORY.RECON.V1`
- `MARKER_155.MEMORY.SHARED_DAG_POLICY.V1`
- `MARKER_155.MEMORY.ENGRAM_DAG_PREFS.V1`

Search tags:
- `memory`
- `engram`
- `stm`
- `mgc`
- `cam`
- `mcc`
- `vetka`
- `dag`
- `layout_preferences`
- `shared_user_state`

## 1) What exists now (fact map)

### MCC (Mycelium)
- UI layout pins are stored in browser local state:
  - `client/src/store/useMCCStore.ts`
  - key: `mcc_layout_pins_v1`
- Scope key is per graph context (`scope/nav/focus` style identity).
- This is fast and stable for live drag/pin UX, but currently local to MCC runtime.

### VETKA (main graph)
- Spatial positions are stored in local UI state + backend save:
  - `client/src/store/useStore.ts`
  - local key: `vetka_node_positions_v1` (via `POSITIONS_STORAGE_KEY`)
  - backend sync: socket `save_positions` and `/api/layout/positions`
- This is a separate persistence loop from MCC.

### Shared memory system (backend)
- ENGRAM user preferences:
  - `src/memory/engram_user_memory.py`
  - schema: `src/memory/user_memory.py`
  - relevant categories already exist: `viewport_patterns`, `tree_structure`, `tool_usage_patterns`
- STM/ELISION/MGC/CAM are production memory layers for context/task intelligence, not UI coordinate caches.

## 2) Dependency conclusion

Yes: MCC and VETKA should share one **logical** user preference memory for DAG behavior.  
No: they should not share one raw coordinate blob.

Reason:
- Raw coordinates are viewport/device/session dependent (different canvases, scales, LOD).
- Shared memory must keep reusable intent, not brittle pixel snapshots.

## 3) Recommended policy (authoritative)

### 3.1 Two-layer model
1. Local hot cache (per UI):
- MCC: keeps exact pin positions for current canvas responsiveness.
- VETKA: keeps exact node positions for current 3D viewport responsiveness.

2. Shared canonical preference memory (ENGRAM):
- Stores **layout intent profile** (biases and habits), not absolute x/y.
- Used by both MCC and VETKA as soft priors for next auto-layout pass.

### 3.2 ENGRAM payload shape (proposed)
- Category path: `viewport_patterns.dag_layout_profiles`
- Optional companion: `tree_structure.layout_mode`
- Suggested profile structure:
  - `scope_key`
  - `vertical_separation_bias`
  - `sibling_spacing_bias`
  - `branch_compactness_bias`
  - `focus_overlay_preference`
  - `pin_persistence_preference`
  - `confidence`
  - `sample_count`
  - `updated_at`

### 3.3 Ownership boundaries
- ENGRAM:
  - user intent, long-lived patterns, cross-app reuse (MCC + VETKA)
- MCC/VETKA local stores:
  - immediate coordinates and pin states for current render context
- STM/MGC/CAM:
  - execution/context memory, retrieval, orchestration (not UI position source of truth)

## 4) Why ENGRAM is not optional here

ENGRAM is the correct layer for persistent user DAG preferences because:
- it already stores user behavioral categories (`viewport_patterns`, `tree_structure`);
- it is shared and model-agnostic;
- it is designed for confidence/sample-based evolution (good for preference learning).

So: ENGRAM is not extra; it is the canonical cross-surface memory for layout intent.

## 5) Extrapolation to VETKA + MCC

Single user memory experience:
- User refines layout in MCC architecture view -> profile updates in ENGRAM.
- User opens VETKA DAG mode -> same bias profile influences initial auto-layout.
- User adjusts in VETKA -> profile evolves and later improves MCC auto-layout.

This gives shared “muscle memory” across both DAG surfaces while preserving each UI’s local precision state.

## 6) Risks and guardrails

Risks:
- Cross-project contamination of preferences.
- Overfitting to one temporary session.
- Jitter if profile applied too aggressively.

Guardrails:
- Scope-bounded keys (`project_root + nav_level + graph_type`).
- Confidence gating before applying bias.
- Explicit pin always wins over inferred bias.
- Trigger-only updates (drag/pin commit), no periodic retrain loop.

## 7) Minimal next implementation step

1. Add ENGRAM write/read bridge for `dag_layout_profiles` (no raw coordinates).
2. Keep existing MCC/VETKA local position persistence unchanged.
3. Apply ENGRAM profile as soft objective in auto-layout (both surfaces).
4. Add marker-based telemetry: profile hit-rate and verifier delta.

## 8) Status

Recon answer to user question:
- “One memory for MCC and VETKA DAG preferences?” -> **Yes, as logical ENGRAM preference layer.**
- “One raw coordinate storage for both?” -> **No. Keep local coordinate caches separate.**
