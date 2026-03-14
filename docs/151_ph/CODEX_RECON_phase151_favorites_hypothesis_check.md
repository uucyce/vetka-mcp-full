# CODEX RECON — Favorites Hypothesis Check (Phase 151)

Date: 2026-02-15
Question: Is `tests/test_favorite_utils.py` tied to real feature: "top chats/files/activity favorites"?

## Checked Inputs
- `docs/108_ph/TIMELINE_DECAY_FLOW_DIAGRAM.txt`
- Current chat history code: `src/chat/chat_history_manager.py`
- Chat/history routes + UI references via grep (`favorite|favorites|pin|pinned|timeline|decay`)

## Findings

### 1) Document from 108 phase
`TIMELINE_DECAY_FLOW_DIAGRAM.txt` describes:
- chat temporal decay formula
- opacity mapping
- Y-axis timeline positioning

It does **not** describe favorites ranking for chats/files/activity.

### 2) Current implementation for chats
`src/chat/chat_history_manager.py` currently sorts chats by `updated_at` descending.
No `favorite` field, no `FavoriteStore`, no favorite-priority sorting layer.

### 3) Existing favorites in codebase
Only real favorites logic found now:
- Model favorites in `src/services/model_registry.py`
- Endpoints in `src/api/routes/model_routes.py` (`/favorites`)

This is model favorites, not chat/file/activity favorites.

### 4) CAM/ENGRAM relation
No functional linkage of `tests/test_favorite_utils.py` to CAM/ENGRAM paths.
CAM has pinned files and memory tools, but not this `FavoriteStore` test path.

### 5) Origin of the stray test
`tests/test_favorite_utils.py` is untracked local artifact.
`src/utils/favorite_utils.py` is absent.
The pair appears in pipeline telemetry tasks, but source file was not materialized.

## Verdict
Hypothesis not confirmed in latest code.
`tests/test_favorite_utils.py` is a stray unfinished artifact, not an active feature test.

## Action
Per user instruction: remove `tests/test_favorite_utils.py`.
