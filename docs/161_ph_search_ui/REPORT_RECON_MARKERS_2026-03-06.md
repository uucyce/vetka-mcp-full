# PHASE 161 — RECON REPORT (Search UI + Vetka Retrieval)

Date: 2026-03-06
Scope: top-left search controls layout, vetka search relevance gap for `abbreviation`, result-row density/readability
Protocol: RECON + markers only (no implementation in this step)

## MARKERS

- `MARKER_161.RECON.SEARCH_BAR_LAYOUT`
- `MARKER_161.RECON.VETKA_PATH_SPLIT`
- `MARKER_161.RECON.VETKA_ABBREVIATION_MISS`
- `MARKER_161.RECON.QDRANT_FILENAME_PAGINATION_GAP`
- `MARKER_161.RECON.RESULT_ROW_DENSITY`
- `MARKER_161.RECON.TEST_COVERAGE`
- `MARKER_161.RECON.IMPL_PLAN_NARROW`

---

## 1) Layout issue: icons vertical near search

### Evidence
- In app shell, search container has side-icons in **column**:
  - `client/src/App.tsx:1087-1093`
  - `flexDirection: 'column'`
- This exactly matches screenshot #1 (chat/chest/terminal stacked vertically and overlapping search area usage).

### Root cause
- Layout is explicitly vertical at shell level (not in `UnifiedSearchBar`).

### Expected fix direction
- Move these 3 buttons into same horizontal row as input area (single compact top row), preserving current style.

---

## 2) Vetka search misses simple query `abbreviation`

## 2.1 Architectural split (important)

### Evidence
- `vetka` context uses **socket path** (`useSearch` -> `useSocket.searchQuery` -> `search_handlers` -> `HybridSearchService`):
  - `client/src/components/search/UnifiedSearchBar.tsx:293` (`autoSearch: searchContext === 'vetka'`)
  - `client/src/hooks/useSocket.ts:2423-2450`
  - `src/api/handlers/search_handlers.py:33+`
- `file/web/social` contexts use REST `/api/search/unified` / `/api/search/file`:
  - `client/src/components/search/UnifiedSearchBar.tsx:515+`

### Risk
- Two independent search stacks with divergent ranking behavior.

## 2.2 Why `abbreviation` fails in vetka

### Runtime evidence
- `HybridSearchService.search('abbreviation', mode='hybrid', limit=200)` returns many results, but **0 paths containing abbreviation**.
- `semantic` mode (200 results): **0 hits** for abbreviation paths.
- `keyword` mode (Weaviate BM25): **0 hits** for abbreviation paths.
- Yet data exists in Qdrant:
  - `/docs/besedii_google_drive_docs/VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md`
  - `/docs/157_ph/MARKER_157_ABBREVIATIONS_RUNTIME_MAP_2026-03-01.md`

### Root causes
1. In vetka/hybrid, local file source is added only for `descriptive` intent (>=4 words or markers):
   - `src/search/hybrid_search.py:60-66`, `317-321`
   - Single token query `abbreviation` is `name_like`, so no `file_local` source.
2. Weaviate keyword index is incomplete/biased for this query in current dataset (no relevant hits).
3. Semantic embeddings do not prioritize this lexical filename token query.

### Consequence
- User sees valid hits only in `file/` mode (OS-backed file search path), not in vetka stack.

## 2.3 Additional bug found: vetka filename path may miss files

### Evidence
- `search_by_filename('abbreviation')` returns 0 in Qdrant client path.
- Direct Qdrant scan:
  - first page (`limit=2000`) has 0 hits
  - full pagination (`total=3720`) has 2 hits

### Root cause
- `search_by_filename` reads only one scroll page (`limit=2000`) and does not paginate to exhaustion.
  - `src/memory/qdrant_client.py:448-470`

### Impact
- Vetka `filename` mode in socket hybrid path can miss valid matches in larger collections.

---

## 3) Result rows: large empty middle space + truncated title

### Evidence
- Row layout uses `justifyContent: 'space-between'` with fixed right metadata block:
  - `client/src/components/search/UnifiedSearchBar.tsx:731-734`, `1386+`
- Right side reserves width with several min-width fields:
  - size (`minWidth:55`), date (`minWidth:60`), relevance + icons
- Multi-line title/path is enabled only for `web` or `file` rows:
  - `client/src/components/search/UnifiedSearchBar.tsx:1355-1378`
- In `vetka` rows, title remains single line and truncates aggressively.

### Root cause
- Over-constrained right metadata + no compact adaptation for vetka rows.
- Multi-line readability policy is context-conditional and excludes most vetka rows.

---

## 4) Existing tests found

### Relevant present tests
- `tests/test_phase157_search_ranking_regression.py`
  - checks file-search behavior for abbreviations/descriptive intents.
- `tests/test_phase157_unified_search_descriptive_runtime.py`
  - checks unified REST descriptive fallback adds file source.
- `tests/test_unified_search_api.py`, `tests/test_unified_search_e2e.py`
  - validate unified REST aggregator behavior.
- `tests/phase159/test_file_search_media_discovery.py`
  - file search fallback behavior.

### Gaps
- No focused test for **socket vetka/hybrid** short lexical query fallback.
- No test for Qdrant filename pagination across >2000 points.
- No frontend UI regression test for search-topbar icon horizontal arrangement.
- No frontend test asserting row density/readability constraints for vetka rows.

---

## 5) Narrow implementation plan (after GO)

`MARKER_161.RECON.IMPL_PLAN_NARROW`

1. **Topbar layout**
- In `App.tsx`, switch icon group from vertical to horizontal next to search input, align baseline, keep existing style tokens.

2. **Vetka retrieval correctness for lexical queries**
- In `HybridSearchService`:
  - include a lightweight lexical/file component for short `name_like` queries (at least when semantic+keyword confidence is weak), OR add fallback on no lexical-like hits.
  - preserve existing descriptive-intent behavior.

3. **Fix Qdrant filename pagination**
- In `qdrant_client.search_by_filename`, iterate scroll pages until exhaustion (or limit reached), not single page only.

4. **Row density/readability**
- In `UnifiedSearchBar` result row:
  - reduce right metadata footprint (smaller min widths and/or compact mode per viewport width),
  - allow title to use 2 lines for vetka rows too,
  - tighten vertical paddings and line-heights to reduce dead center gap.

5. **Tests**
- Add backend test for filename pagination logic.
- Add hybrid-search regression test for lexical query (`abbreviation`) ensuring expected docs are surfaced in vetka path (with controlled stubs where needed).
- Add lightweight frontend contract test (string/structure-based if existing style in repo) for horizontal icon container and row style markers.

---

## 6) Risks / notes

- Vetka stack currently depends heavily on Weaviate+semantic quality for short lexical tokens; fix must avoid overfitting to one keyword and preserve semantic ranking quality.
- UI density changes should keep hover preview and action buttons usable.
- Need to keep style consistent with current grayscale Nolan-like aesthetic.

---

## GO gate

RECON complete. Ready for implementation after explicit `GO`.
