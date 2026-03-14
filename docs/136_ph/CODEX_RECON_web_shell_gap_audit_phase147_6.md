# VETKA Web Shell Gap Audit (Phase 147.6 Recon)

Date: 2026-02-14
Scope: `/web` search -> click result -> native Tauri web shell -> save-to-vetka pathing -> viewport-context ranking

## TL;DR
- `/web` is already **REST-based** (`/api/search/unified`), not Socket.IO. The earlier Socket concern is not the current blocker.
- Current Tauri web window is **not a full browser runtime flow** in-app: `WebShellStandalone` renders server-fetched sanitized HTML via `iframe srcDoc` (`/api/search/web-preview`).
- This architecture explains the current failures: unstable page navigation behavior, weak/broken find-in-page on dynamic sites, and shell controls disappearing when flow escapes srcDoc lifecycle.
- Save path defaults are generated client-side from viewport state; when no selected/pinned/usable camera-derived nodes are available, suggestions become empty.
- Viewport contextual rerank is wired, but for web it is lexical-only post-rerank (no web embeddings/Qdrant fusion), so weak influence is expected.

---

## MARKER_1476.WEB_CLICK_PIPELINE
### What is implemented
- Web result click in search triggers native open directly:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/App.tsx:256`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx:917`
- Tauri command reuses one shell window by label `vetka-web-shell` and emits navigation event:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src-tauri/src/commands.rs:96`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src-tauri/src/commands.rs:142`
- Shell listens to `vetka:web-shell:navigate` and calls `loadPreview(nextUrl)`:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/WebShellStandalone.tsx:128`

### Gap
- `loadPreview()` has no request cancellation or navigation token guard.
- Competing async loads can resolve out-of-order and overwrite newer navigation with older content.

### Risk signature
- “First link holds” / non-deterministic URL/page mismatch after consecutive clicks.

### Research needed
- Compare two options:
1. `AbortController` cancellation per navigation.
2. Monotonic `navigationRequestId` guard (apply response only if latest).
- Validate event delivery timing in Tauri when window already exists and receives rapid emits.

---

## MARKER_1476.WEB_RUNTIME_MODEL
### What is implemented
- Shell does fetch -> sanitize -> `srcDoc` preview:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/WebShellStandalone.tsx:167`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/unified_search_routes.py:121`
- Backend strips scripts/forms/iframes and rewrites markup for safety:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/unified_search_routes.py:42`

### Gap
- This is a preview pipeline, not a full browser tab engine behavior inside shell.
- Dynamic apps degrade by design after sanitization; DOM-based features become partial.

### User-visible effects
- Find-in-page inconsistent.
- Page interaction differs from real site behavior.
- Header/controls state can desync after certain navigation paths.

### Research needed
- Decide target architecture:
1. Keep preview model and accept constraints.
2. Move shell body to native `WebviewUrl::External` under managed control (real page runtime) while retaining top shell UI.
3. Hybrid: default external-native runtime + optional “safe preview” mode.

---

## MARKER_1476.FIND_IN_PAGE
### What is implemented
- `window.find(...)` fallback + manual text range walker over `iframe.contentDocument`:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/WebShellStandalone.tsx:256`

### Gap
- Works only when document remains same-origin and stable in preview DOM.
- With dynamic/sanitized pages, text map and focus lifecycle are fragile.

### Research needed
- Implement deterministic search model with:
1. Per-document index rebuild on load.
2. Next/prev traversal state reset on URL change.
3. Explicit unsupported-state messaging for non-indexable pages.

---

## MARKER_1476.SAVE_PATH_SUGGESTIONS
### What is implemented
- `openLiveWebWindow()` infers candidate paths from selected node, pinned nodes, and viewport context:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/config/tauri.ts:214`
- Shell receives `save_path` / `save_paths` via query and runtime event:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/WebShellStandalone.tsx:128`

### Gap
- If `selectedId` invalid/empty and camera-derived context yields no file/folder paths, suggestions are empty.
- No backend fallback endpoint to provide canonical nearest-node list.

### Related defect
- In chat search select (non-web path), `selectNode(result.path)` uses path where store expects node id:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx:938`
- This can corrupt selection semantics and weaken follow-on save-path defaults.

### Research needed
- Add a backend resolver API: `POST /api/tree/recommend-save-paths` based on viewport payload.
- Standardize selection contract to node-id everywhere.
- Define A/B policy:
  - A0: most relevant node by viewport+semantic
  - A1: nearest visible node by camera distance

---

## MARKER_1476.VIEWPORT_CONTEXT_SEARCH
### What is implemented
- `/web` search request includes `viewport_context` in REST path:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/search/UnifiedSearchBar.tsx:535`
- Backend applies contextual rerank:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/unified_search.py:471`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/search/contextual_retrieval.py:129`

### Gap
- For web rows, boost is lexical token overlap only; no structural web embedding memory.
- So “Blender first everywhere” can happen when provider rank dominates and context tokens are weak.

### Research needed
- Instrument query logs with per-result fields: provider score, context_boost, final score.
- Add weighted blending controls per context (`VETKA_WEB_CTX_BOOST_WEIGHT`).
- Evaluate optional web-snippet embedding path (Qdrant-backed rerank) for true contextuality.

---

## MARKER_1476.QDRANT_EXPECTATION_MISMATCH
### Current state
- Qdrant is used in VETKA semantic/file flows and memory layers.
- `/web` current pipeline is provider retrieval + local rerank, not full web-to-qdrant ingestion loop by default.

### Gap
- User expectation: web context should benefit from persistent semantic memory similar to local tree.
- Current implementation does not auto-ingest every web result into semantic index.

### Research needed
- Define policy:
1. On-click ingest only.
2. Save-to-vetka ingest only.
3. Top-N background ingest with TTL and dedup.
- Add source tags (`web_live`, `web_saved`, `web_preview`) for retrieval routing.

---

## MARKER_1476.NO_SOCKET_WEB_CONFIRMATION
### Confirmed
- `/web` search mode uses REST unified endpoint (debounced fetch), not Socket.IO.
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/search/UnifiedSearchBar.tsx:498`

### Conclusion
- The current `/web` bugs are not caused by socket transport.

---

## MARKER_1476.RESEARCH_BACKLOG
Priority research tasks before implementation:
1. Navigation consistency: concurrency-safe navigation protocol for existing shell window.
2. Runtime model decision: preview DOM vs true native external runtime in shell container.
3. Canonical save-path resolver service from viewport state.
4. Contextual web ranking observability and boost tuning.
5. Optional web semantic memory integration with Qdrant.

---

## MARKER_1476.IMPLEMENTATION_READINESS
Recommended implementation order (after research decisions):
1. **Stability first**: navigation request guard + single-window strict routing.
2. **Save UX**: guaranteed non-empty suggestions with backend resolver fallback.
3. **Find UX**: deterministic document-search behavior + explicit unsupported states.
4. **Relevance**: viewport-context telemetry + tuned rerank blending.
5. **Memory**: optional web snippet ingestion path into Qdrant for contextual web recall.

