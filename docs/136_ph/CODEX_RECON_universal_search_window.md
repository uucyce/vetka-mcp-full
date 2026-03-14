# MARKER_142.RECON_UNIVERSAL_SEARCH_WINDOW

Date: 2026-02-13
Scope: reconnaissance only (no implementation)
Goal: stable universal search window for `vetka/web/file/cloud/social` without mode leakage or fallback confusion.

## 1) Executive Summary

- Regression symptom is real: in `web/file` contexts UI can fall back to VETKA socket results, so user sees local VETKA search instead of internet/filesystem source.
- Root cause is frontend orchestration mismatch, not only provider outage.
- Current architecture has two parallel engines:
  - VETKA search via Socket.IO (`search_query` -> hybrid service with modes)
  - web/file search via REST `/api/search/unified` (source-only, no search modes)
- Mode buttons (`HYB/SEM/KEY/FILE`) are globally visible but semantically valid only for VETKA now.
- Tavily is **not mandatory architecturally**. It is just current provider for `web` source in unified backend.

---

## 2) What Is Broken Exactly

### MARKER_142.BUG_FALLBACK_LEAK

1. `UnifiedSearchBar` returns VETKA results when unified list is empty.
- File: `client/src/components/search/UnifiedSearchBar.tsx:293`
- Logic:
  - if `searchContext !== 'vetka' && unifiedResults.length > 0` -> use unified
  - else -> use `results` (Socket/VETKA)
- Effect: any web/file backend miss silently shows VETKA output.

2. `useSearch` auto-search runs regardless of selected context.
- File: `client/src/hooks/useSearch.ts:160`
- Effect: even while in `web/file`, socket VETKA search executes in background and populates `results`.

3. For web provider failures, unified backend returns empty list gracefully.
- File: `src/api/handlers/unified_search.py:142`
- File: `src/mcp/tools/web_search_tool.py:103`
- Effect: empty unified + fallback leak => visual switch to VETKA search.

### MARKER_142.BUG_MODE_MISMATCH

4. Search mode buttons are not context-aware.
- File: `client/src/components/search/UnifiedSearchBar.tsx:921`
- Buttons always shown; but for `web/file` requests these modes are not sent to `/api/search/unified`.

5. `/api/search/unified` supports `query/limit/sources` only.
- File: `src/api/routes/unified_search_routes.py:20`
- No `mode`, no capability response, no per-source mode mapping.

6. VETKA mode semantics exist only in Socket pipeline.
- File: `client/src/hooks/useSocket.ts:1742`
- File: `src/api/handlers/search_handlers.py:33`
- File: `src/search/hybrid_search.py:121`

### MARKER_142.BUG_CHAT_ARTIFACT_GAP

7. In ChatPanel, artifact opening assumes file-like result; web-specific artifact open path is missing.
- File: `client/src/components/chat/ChatPanel.tsx:2288`
- `App.tsx` has web-aware open path, ChatPanel does not.

---

## 3) Current Capability Matrix (As-Is)

### MARKER_142.CAPABILITY_MATRIX_ASIS

- `vetka/`:
  - transport: Socket.IO
  - endpoint/event: `search_query`
  - modes: `hybrid`, `semantic`, `keyword`, `filename`
  - backends: Qdrant + Weaviate + RRF (`HybridSearchService`)

- `web/`:
  - transport: REST
  - endpoint: `/api/search/unified` with `sources=['web']`
  - modes: not implemented
  - provider: `WebSearchTool` (Tavily)

- `file/`:
  - transport: REST
  - endpoint: `/api/search/unified` with `sources=['file']`
  - modes: not implemented (substring/content scan only)
  - backend: `_file_search` in handler

- `cloud/social`:
  - transport: REST (same unified route)
  - implementation status: placeholders / limited

---

## 4) Tavily: Mandatory or Not?

### MARKER_142.TAVILY_DECISION

Short answer: **No, not mandatory by design**.

Current code path for `web` source is Tavily-dependent:
- `src/api/handlers/unified_search.py:_web_search()` -> `WebSearchTool`.
- `WebSearchTool` currently wraps Tavily SDK and key manager.

Recommended architecture:
- Keep Tavily as one provider adapter (`web_provider=tavily`).
- Add provider abstraction in unified web search (`tavily | serper | brave | direct_fetch_indexed`) with feature flags.
- UI must never blur sources when provider unavailable; show source-specific error state instead.

---

## 5) How Modes Should Work Across Contexts

### MARKER_142.MODE_POLICY

Proposed policy (clean and deterministic):

- `vetka`: allow `hybrid/semantic/keyword/filename`.
- `web`: allow `hybrid/keyword` initially.
  - `semantic` only if web embeddings/index are available.
  - `filename` hidden (not meaningful for internet docs).
- `file`: allow `filename/keyword` initially.
  - `semantic` only if local file embeddings exist.
  - `hybrid` only if both semantic + keyword available.
- `cloud/social`: dynamic based on adapter capabilities.

UI rule:
- mode controls must be generated from server capability response for active context.
- unavailable modes hidden or disabled with reason tooltip.

---

## 6) Socket.IO for Non-VETKA Spaces

### MARKER_142.TRANSPORT_STRATEGY

Current:
- VETKA uses Socket.IO (stream-like interaction pattern).
- web/file use REST polling-style query.

Best options:

1. **Unified Socket event for all contexts** (recommended long-term)
- Add `search_query_v2` with payload:
  - `context`, `mode`, `query`, `limit`, `filters`, `request_id`
- Server emits `search_results_v2` with:
  - `request_id`, `context`, `results`, `capabilities`, `error`, `timing`, `source_stats`
- Benefit: one frontend state machine, same cancellation/debounce/status pipeline.

2. Keep mixed transport but formalize boundaries (short-term)
- VETKA via Socket; web/file via REST.
- Hard block fallback cross-contamination in UI.
- Benefit: minimal migration risk.

Recommendation: phase rollout (2 -> 1).

---

## 7) Save-to-VETKA Flows (Web + File)

### MARKER_142.SAVE_FLOW

Existing:
- Web save exists in ArtifactPanel:
  - `POST /api/artifacts/save-webpage`
  - files saved under `data/artifacts/web_research`
  - extractor: `WebIntake` (`trafilatura` + BeautifulSoup fallback)

Gaps:
- Save action is exposed from artifact view, not first-class from search result list.
- File search results pin to context but no explicit “Save as VETKA artifact” action from search item.

Recommended:
- Add per-result actions in UnifiedSearchBar for non-vetka sources:
  - `Open` (artifact preview)
  - `Pin`
  - `Save to VETKA`
- For file source:
  - create markdown artifact with snippet + absolute/relative source + timestamp + checksum.
- For web source:
  - reuse existing `save-webpage` handler.

---

## 8) No-Crutch Target Architecture

### MARKER_142.TARGET_ARCH

`SearchOrchestrator` contract (backend):
- input: `{context, query, mode, limit, filters, request_id}`
- output: `{results, timing_ms, error, capabilities, source_health}`

`capabilities` example:
- `supported_modes`
- `supports_stream`
- `supports_save_to_vetka`
- `provider_status` (e.g., tavily_key_present, sdk_installed)

Frontend:
- one search state machine keyed by `request_id` + `context`
- no implicit fallback across contexts
- mode buttons derive from `capabilities.supported_modes`
- consistent style/UX across all contexts (single renderer + source badges)

---

## 9) Implementation Markers (for next coding phase)

### MARKER_142.IMPL_STEP_1_GUARDRAILS

- `client/src/components/search/UnifiedSearchBar.tsx`
  - remove cross-context fallback to `results` in `web/file/cloud/social`
  - keep separate result buckets per context

- `client/src/hooks/useSearch.ts`
  - add `enabled` flag, disable socket auto-search when context != `vetka`

### MARKER_142.IMPL_STEP_2_CAPABILITIES

- `src/api/routes/unified_search_routes.py`
  - extend request with optional `mode`
  - add `/api/search/capabilities?context=...`

- `src/api/handlers/unified_search.py`
  - implement mode handling per source (at least validation + explicit rejection)
  - return structured source health/errors (not silent empty)

### MARKER_142.IMPL_STEP_3_UI_DYNAMIC_MODES

- `client/src/components/search/UnifiedSearchBar.tsx`
  - fetch capabilities on context switch
  - render only supported mode buttons

### MARKER_142.IMPL_STEP_4_SOCKET_UNIFICATION

- `src/api/handlers/search_handlers.py`
  - add `search_query_v2` for any context
- `client/src/hooks/useSocket.ts`
  - add v2 event handlers with request correlation

### MARKER_142.IMPL_STEP_5_SAVE_ACTIONS

- `client/src/components/search/UnifiedSearchBar.tsx`
  - add Save action per result for web/file
- backend:
  - reuse `save_webpage_artifact`
  - add `save_file_search_result_artifact` handler

### MARKER_142.IMPL_STEP_6_CHAT_PARITY

- `client/src/components/chat/ChatPanel.tsx`
  - mirror web-aware artifact open logic from `App.tsx`.

---

## 10) Direct Answers to Your Questions

### MARKER_142.DIRECT_ANSWERS

1. “В web/file контексте никогда не падать в VETKA results?”
- Yes, this must be strict. Current leak is identified at `UnifiedSearchBar.tsx:293` + `useSearch.ts:160`.

2. “Обязательно ли через Tavily искать интернет?”
- No. Current implementation uses Tavily, but architecture should support pluggable web providers.

3. “Как работают hybrid/semantic/filename в web/file сейчас?”
- Сейчас полноценно работают только для `vetka` Socket pipeline.
- В `web/file` режимы UI показываются, но backend unified их не использует.

4. “Можно ли через Socket.IO показывать остальные пространства?”
- Yes. Recommended via `search_query_v2` with context + capabilities.

---

## 11) Final Recon Verdict

### MARKER_142.FINAL_VERDICT

Core issue is wiring inconsistency, not one broken function.
To get a clean universal search window in VETKA style:
- enforce context isolation,
- make mode controls capability-driven,
- expose explicit provider health,
- unify transport progressively (v2 socket),
- add first-class Save-to-VETKA actions for web/file at result level.

This path removes current ambiguity and preserves your existing style/components with minimal conceptual debt.

---

## 12) Grok Addendum (Merged)

### MARKER_143.TAVILY_RESEARCH

- Tavily is not mandatory architecturally; it is the current web adapter.
- Recommended direction:
  - keep Tavily as adapter (`web_provider=tavily`);
  - add pluggable providers (`serper`, `brave`, later custom crawl/index);
  - expose provider health in capabilities so UI can explain why `web` has 0 results.

### MARKER_143.RRF_WEB_FEASIBILITY

- VETKA RRF/hybrid primitives are reusable for web/file result sets.
- Practical sequence:
  1. fetch web candidates from one or more providers;
  2. normalize + deduplicate;
  3. run rank fusion (RRF);
  4. (next phase) embed snippets and add semantic layer.
- Current phase implements API contract alignment first (context modes + capabilities), then hybrid enrichment.

### MARKER_143.RECON_SUPPLEMENTS

- Add web snippet embedding into VETKA index for semantic re-search/history.
- Introduce multi-provider web fusion (parallel adapters + RRF) to remove single-provider bottleneck.
- Move to `search_query_v2` over Socket.IO for all contexts after guardrails are stable.
- Keep source-specific error surfaces explicit (no cross-context fallback).

### MARKER_143.ROLLING_IMPL_STATUS

Started in this turn:
- implemented strict context isolation in UI (no `web/file` fallback into VETKA results);
- added backend capabilities endpoint (`/api/search/capabilities`);
- added unified `mode` parameter plumbing and server-side mode validation by context;
- connected frontend mode selection to backend capabilities.

Next (implementation phase continuation):
1. wire ChatPanel web artifact open parity with App behavior;
2. add per-result Save-to-VETKA actions for non-vetka contexts;
3. add provider health details to UI (e.g., key/sdk status);
4. introduce multi-provider web adapter + RRF merge.

Update 2026-02-13 (continued):
- item 1 implemented (`ChatPanel` web artifact parity);
- item 2 implemented (`/api/artifacts/save-search-result` + `SV` action in `UnifiedSearchBar`);
- item 3 partially implemented (web provider health surfaced in `capabilities`, basic UI warning).

Update 2026-02-13 (multi-provider web):
- `unified_search` now supports pluggable web providers via `VETKA_WEB_PROVIDERS` (currently `tavily,serper`).
- Added Serper adapter and provider-level error reporting (`source_errors` keys: `web:tavily`, `web:serper`).
- Added RRF merge for multi-provider web results (`WEB_RRF_K`, default 60) using `src/search/rrf_fusion.py`.
- `capabilities` now returns both Tavily and Serper health + configured provider list.
