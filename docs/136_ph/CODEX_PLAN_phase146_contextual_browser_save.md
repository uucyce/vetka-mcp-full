# MARKER_146.PLAN_CONTEXTUAL_BROWSER_SAVE

Date: 2026-02-13
Status: active
Theme: viewport is always-on in VETKA, so contextual retrieval is automatic by default.

## MARKER_146.STEP1_CONTEXTUAL_RETRIEVAL

Goal:
- make search context-aware based on active viewport branch for all contexts (vetka/web/file), without отдельного CTX toggle.

Implementation:
- backend shared contextual rerank module;
- socket search (`vetka`) receives viewport_context and reranks;
- unified REST search (`web/file`) receives viewport_context and reranks.

Files:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/search/contextual_retrieval.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/search_handlers.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/unified_search.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/unified_search_routes.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/hooks/useSocket.ts`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/search/UnifiedSearchBar.tsx`

Status:
- completed in this wave.

## MARKER_146.STEP2_NATIVE_BROWSER_SHELL

Goal:
- native Tauri browser shell with top black panel in VETKA style:
  - back/forward,
  - address,
  - find-in-page,
  - save button with VETKA icon and ring-state.

Notes:
- keep web rendering in external webview for compatibility;
- do not route page rendering through Socket.IO.

Status:
- completed in this wave (initial shell implementation on `/web-shell` route).

## MARKER_146.STEP3_TWO_STEP_SAVE_UI

Goal:
- strict 2-step save flow from web shell:
  1) file name + format (HTML/MD),
  2) destination path (default nearest viewport node, editable).

Requirements:
- save in VETKA artifacts + physical disk path in directed mode;
- default destination inferred from nearest viewport node.

Status:
- completed in this wave for native web shell:
  - step 1: name + format (MD/HTML),
  - step 2: destination path with default from opener (`save_path`) and manual override.

## MARKER_146.RESEARCH_NOTES_MILVUS_APPLICABILITY

Conclusion:
- Milvus contextual retrieval pattern is applicable as methodology;
- no migration from current Qdrant/Weaviate/RRF required right now;
- adopted pattern: context profile + rerank boost by viewport branch affinity.
