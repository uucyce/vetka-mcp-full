# MARKER_137.RECON_S1_2_TAVILY
# Recon Report: tb_1770809269_2 (S1.2 Unified Search Tavily)

Date: 2026-02-11
Workspace: /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

## Scope
- Task: Wire web provider (Tavily) into federated unified search router
- File target: `src/api/handlers/unified_search.py`

## Findings
1. `POST /api/search/unified` already exists:
- route: `src/api/routes/unified_search_routes.py`
- handler: `src/api/handlers/unified_search.py`

2. `web` source is already connected to Tavily tool:
- `_web_search()` imports `WebSearchTool` from `src/mcp/tools/web_search_tool.py`
- calls `WebSearchTool().execute({"query": ..., "max_results": ...})`

3. Gap vs sprint wording:
- Task text says “currently returns stub”. In current code it is not stub, but lacks explicit score normalization policy and dedicated tests for Tavily mapping path.

4. Duplicate-risk check:
- No duplicate unified endpoint found beyond current implementation.
- Existing tests (`tests/test_unified_search_api.py`) verify aggregator behavior, but not Tavily score normalization/dedup semantics.

## Planned isolated changes
1. Harden `_web_search()` in `src/api/handlers/unified_search.py`:
- Explicit score normalization to `[0..1]`
- URL dedup
- rank fallback score when provider score missing

2. Add focused tests in `tests/test_unified_search_api.py`:
- verify Tavily mapping + score normalization
- verify dedup by URL

3. Keep scope isolated to unified search handler/tests and docs report only.
