# CODEX RECON — `test_favorite_utils.py` Investigation

Date: 2026-02-15
Scope: root-cause of `tests/test_favorite_utils.py` failure and relation to CAM/ENGRAM

## MARKER_151_FAV_01_CURRENT_ERROR
Reproduced directly:
- Command: `pytest -q tests/test_favorite_utils.py`
- Result: `ModuleNotFoundError: No module named 'src.utils.favorite_utils'`

So the failing point is collection-time import, not runtime logic.

## MARKER_151_FAV_02_FILE_PRESENCE
Observed state:
- `tests/test_favorite_utils.py` exists locally and is **untracked** (`git status -> ?? tests/test_favorite_utils.py`).
- `src/utils/favorite_utils.py` does **not** exist in workspace.
- `git` confirms test file is absent from `HEAD` history (`fatal: no such path in HEAD`).

Conclusion: this test is not part of stable branch history; it is a local stray artifact.

## MARKER_151_FAV_03_ORIGIN_TRACE
Trace in project telemetry:
- `data/pipeline_tasks.json` has task `task_1771086738` with exact prompt:
  `Create src/utils/favorite_utils.py ... Also create tests/test_favorite_utils.py ...`
- `data/feedback/reports/task_1771086738.json` reports status `done`, but `files_created: []`.
- `data/changelog/changelog_2026-02-14.json` shows indexing events for `tests/test_favorite_utils.py`, and no entry for `src/utils/favorite_utils.py`.

Conclusion: pipeline marked task complete, but actual source file was not materialized; test file artifact remained.

## MARKER_151_FAV_04_CAM_ENGRAM_CHECK
Cross-check for CAM/ENGRAM linkage:
- `tests/test_favorite_utils.py` imports only `src.utils.favorite_utils`.
- No CAM/ENGRAM imports or references inside this test.
- Existing favorites functionality in backend is separate (`src/services/model_registry.py` + `src/api/routes/model_routes.py`, model favorites only).

Conclusion: issue is **not related** to CAM/ENGRAM subsystems.

## MARKER_151_FAV_05_RISK_ASSESSMENT
Risk level for current branch:
- If full test discovery includes this local file, test suite fails at collection.
- Since file is untracked, failure is environmental/local, not repository regression in `HEAD`.

## MARKER_151_FAV_06_SAFE_OPTIONS
Recommended safe actions (choose one policy):
1. Cleanup policy (preferred for current phase): remove local stray test file `tests/test_favorite_utils.py`.
2. Completion policy: intentionally implement `src/utils/favorite_utils.py` and decide whether this utility is product-needed; if yes, add and track both source+tests properly.
3. Quarantine policy: move file out of `tests/` (e.g., to `docs/` or `data/vetka_staging/blocked`) to avoid pytest collection until formal scope approval.

## Final verdict
This is a **pipeline artifact / unfinished micro-task output**, not CAM/ENGRAM breakage.
