# MARKER_136.RECON_REPORT

# Phase 136 Recon Report (Codex)
Date: 2026-02-11
Scope: `tb_..._4`, `tb_..._5`, `tb_..._10`, `tb_..._13`, `tb_..._14`, `tb_..._15`
Mode: reconnaissance only (no new backend implementation in this report)

## 1) Snapshot from TaskBoard
- `tb_1770804784_4`: tests for `task_tracker.py` (`on_task_completed`, `on_cursor_task_completed`, `on_task_started`, `get_tracker_status`), P2.
- `tb_1770804787_5`: remove duplicate CLI (`src/cli/vetka_cli.py`, `src/cli/pipeline_runner.py`, `bin/vetka` + tests), P3.
- `tb_1770805995_10`: chat message compression to 500 chars in storage (`src/chat/chat_history_manager.py`), P3.
- `tb_1770806011_13`: tests for `artifact_scanner.py` scan/approve/reject flows, P2.
- `tb_1770806015_14`: feedback integration tests (pipeline report -> next run feedback), P3.
- `tb_1770806018_15`: backend file connections API (`GET /api/files/{id}/connections`), P3.

## 2) What already exists (facts)
### 2.1 Task tracker
- Module exists: `src/services/task_tracker.py` (marker `MARKER_133.TRACKER`).
- API routes exist: `src/api/routes/task_tracker_routes.py` (marker `MARKER_133.TRACKER_API`).
- Before current wave, dedicated tests for this service were not present in this workspace.

### 2.2 Artifact scanner
- Service exists: `src/services/artifact_scanner.py` (marker `MARKER_108_3_ARTIFACT_SCAN`).
- Current functions found: `scan_artifacts()`, `build_artifact_edges()`, `update_artifact_positions()`.
- `approve_artifact()/reject_artifact()` functions are not present in `src/services/artifact_scanner.py` now.
- Tree integration exists in `src/api/routes/tree_routes.py` (artifact nodes/edges in response).

### 2.3 Chat compression
- `ChatHistoryManager.add_message()` currently stores full `message["content"]`.
- Digest already truncates output (`200` for agent logs, `500` for `recent_messages`) in `get_chat_digest()`.
- No `truncated_content` field in stored message model yet.

### 2.4 Feedback integration
- Core service exists: `src/services/feedback_service.py`.
- Existing tests exist: `tests/test_phase135_feedback_loop.py` (marker `MARKER_135.TEST_FB`) and are broad for service-level behavior.
- Missing specifically: end-to-end style integration test bridging pipeline-like save and architect feedback consumption in a separate phase-136 file.

### 2.5 File connections API
- `src/api/routes/files_routes.py` has no `/connections` endpoint today.
- Scanner stack exists (`src/scanners/python_scanner.py`, `src/scanners/import_resolver.py`) and can be reused for lightweight connections API.

### 2.6 CLI duplication task
- Newly added CLI files are present:
  - `src/cli/vetka_cli.py`
  - `src/cli/pipeline_runner.py`
  - `bin/vetka`
  - tests: `tests/test_vetka_cli.py`, `tests/test_pipeline_runner.py`
- TaskBoard explicitly marks them as duplicate MCP infrastructure (`tb_..._5`).

## 3) Duplication check (requested)
- In current workspace:
  - `tests/test_task_tracker.py` and `tests/test_artifact_scanner.py` are new/untracked (not previously present).
- In `.claude/worktrees/*`:
  - no same-named files found (`test_task_tracker.py`, `test_artifact_scanner.py` absent there).
  - old related artifact test exists only as `test_artifact_scan.py` in worktrees (different file, different location).

## 4) Gaps and risks by task
### `tb_..._4` tests task_tracker
- Gap: no canonical test module existed before.
- Risk: low. File-path globals need monkeypatching in tests.

### `tb_..._13` tests artifact_scanner
- Gap: requested approve/reject flow cannot be tested directly because approve/reject functions are currently absent.
- Risk: medium. Need either:
  - adjust task scope to current functions (scan/edges/positions), or
  - implement approve/reject API/service first, then test.

### `tb_..._5` remove duplicate CLI
- Gap: none (clear cleanup task).
- Risk: low. Must remove all introduced CLI files and corresponding tests in one commit.

### `tb_..._10` chat compression 500 chars
- Gap: storage write path (`add_message`) still keeps full content only.
- Risk: medium. Need backward-compatible schema (`content` + optional `truncated_content`) and clear rule (likely only `role=user`).

### `tb_..._14` feedback integration tests
- Gap: integration-level tests not isolated as phase-136 artifact.
- Risk: low/medium. Need stable temp-dir patching for feedback paths and deterministic mtimes/order.

### `tb_..._15` backend file connections API
- Gap: endpoint absent.
- Risk: medium. Scope must be explicit:
  - import-based connections (fast, local) vs semantic/Qdrant connections (heavier, unstable).
  - Recommended first step: deterministic import-graph endpoint in `files_routes.py`.

## 5) Proposed execution order (after approval)
1. Finalize Wave-1 tests (`tb_..._4`, `tb_..._13`) with explicit scope note for approve/reject gap.
2. Cleanup duplicate CLI (`tb_..._5`).
3. Add chat 500-char storage compression (`tb_..._10`) with marker and tests.
4. Add phase-136 feedback integration tests (`tb_..._14`).
5. Add file connections API route + tests (`tb_..._15`).

## 6) Markers status for this wave
- Added in new test files:
  - `MARKER_136.TEST_TASK_TRACKER`
  - `MARKER_136.TEST_ARTIFACT_SCANNER`
- This report marker:
  - `MARKER_136.RECON_REPORT`

## 7) Decision needed before implementation
- Confirm handling for `tb_..._13`:
  - A) test only current `artifact_scanner` functions now, or
  - B) first add approve/reject functionality, then test those flows.
