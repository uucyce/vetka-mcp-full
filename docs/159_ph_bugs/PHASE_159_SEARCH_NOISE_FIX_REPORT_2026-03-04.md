# PHASE 159 — Search Noise Fix Report

Date: 2026-03-04
Scope: reduce noisy file-search results after test/sample data expansion.

## MARKER_159_SEARCH_NOISE_1_ROOT_CAUSE
Primary noise source was in `src/search/file_search_service.py` (descriptive intent path):
- docs-seed candidate generation could flood weak candidates,
- test/fixture/mock/sample paths were not strongly penalized,
- descriptive recall and precision were competing poorly under larger datasets.

## MARKER_159_SEARCH_NOISE_2_IMPLEMENTED_FIX
File changed:
- `src/search/file_search_service.py`

Key changes:
1. Added stronger path-level noise controls:
- `_TEST_NOISE_MARKERS` with extra penalty for descriptive search when query is not test-related.

2. Made docs seed smarter (term-filtered):
- `_docs_catalog_candidates(...)` now keeps only docs with term hits (instead of broad weak catalog),
- score uses term-hit density,
- candidates are sorted by local relevance before merge.

3. Kept descriptive recall while reducing noise:
- descriptive flow still receives docs seed,
- but seed is bounded and relevance-filtered.

## MARKER_159_SEARCH_NOISE_3_TEST_COVERAGE
File changed:
- `tests/test_phase150_file_search_service.py`

Added test:
- `test_rerank_deprioritizes_test_noise_for_descriptive_queries`
- verifies canonical docs outrank fixture/test duplicates for descriptive doc requests.

## MARKER_159_SEARCH_NOISE_4_VALIDATION
Executed and passed:
- `pytest -q tests/test_phase150_file_search_service.py tests/test_phase157_search_ranking_regression.py tests/test_phase157_hybrid_file_first_policy.py tests/test_phase157_unified_search_descriptive_runtime.py`

Result:
- `10 passed`.

## MARKER_159_SEARCH_NOISE_5_NOTES
No API schema or endpoint contract was changed.
Patch is ranking-layer only and backward-compatible for clients.
