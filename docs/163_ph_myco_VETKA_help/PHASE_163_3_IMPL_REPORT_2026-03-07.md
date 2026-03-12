# Phase 163.3 — VETKA MYCO Help RAG Glue (Impl Report)

Date: 2026-03-07
Status: Implemented (narrow)

## Scope
- Connect voice-path Jarvis MYCO_HELP mode to Phase-163 documentation corpus.
- Remove empty hidden retrieval behavior for MYCO_HELP turns.
- Enforce RU continuity when user/session is RU.

## Implemented

### 1) Retrieval glue in Jarvis handler
- File: `src/api/handlers/jarvis_handler.py`
- Marker: `MARKER_163.P3.VETKA_HELP_RAG_GLUE.V1`
- Behavior:
  - after `get_jarvis_context(...)`, if `hidden_retrieval.items` is empty and `JARVIS_MYCO_HELP_MODE=true`, inject retrieval from Phase-163 docs via dedicated retriever.

### 2) New retrieval service for Phase-163 corpus
- File: `src/services/vetka_myco_help_retrieval.py`
- Marker: `MARKER_163.P3.VETKA_MYCO_HELP_RAG_RETRIEVAL.V1`
- Behavior:
  - lexical retrieval over docs in:
    - `docs/163_ph_myco_VETKA_help/*.md`
    - `docs/163_ph_myco_VETKA_help/rag/*.md`
  - returns payload compatible with `hidden_retrieval` (`items/source/marker`).

### 3) RU fallback guard (no EN switch)
- File: `src/api/handlers/jarvis_handler.py`
- Marker: `MARKER_163.P3.RU_GUARD_FALLBACK_NO_EN_SWITCH.V1`
- Behavior:
  - if RU rewrite stage times out/fails, force RU deterministic fallback (MYCO_HELP fallback or short RU system line), preventing EN response flips.

## Added RAG docs (source corpus)
- `docs/163_ph_myco_VETKA_help/rag/VETKA_HELP_CORE_ACTIONS_V1.md`
- `docs/163_ph_myco_VETKA_help/rag/VETKA_HELP_FILES_AND_ARTIFACTS_V1.md`
- `docs/163_ph_myco_VETKA_help/rag/VETKA_HELP_CHAT_PIN_VIEWPORT_V1.md`
- `docs/163_ph_myco_VETKA_help/rag/VETKA_HELP_NODE_AND_CAMERA_V1.md`
- `docs/163_ph_myco_VETKA_help/rag/VETKA_HELP_TROUBLESHOOTING_SHORT_V1.md`

## Verification
- `python -m py_compile src/api/handlers/jarvis_handler.py src/services/vetka_myco_help_retrieval.py` => OK
- local retrieval smoke => returns non-empty `items` for MYCO_HELP-like queries.

## Next e2e checks
1. Ask voice: "Что я сейчас вижу?"
2. Ask voice: "Как закрепить несколько файлов?"
3. Ask correction: "Ответ неверный, повтори"

Expected in `/api/debug/jarvis/traces`:
- `myco_help_mode=true`
- `voice_profile=vetka_ru_female`
- `response_lang=ru` on RU turns
- `hidden_retrieval_hits > 0` for help intents
- no long-tail EN-switch after correction turns
