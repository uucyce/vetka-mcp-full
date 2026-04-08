# vetka-search-retrieval

Hybrid retrieval core for VETKA. This module combines vector search, keyword
retrieval, local file indexing fallbacks, and contextual reranking to produce
higher-precision results in agent workflows.

## Why This Module Exists

Large agent systems degrade quickly when retrieval is noisy. VETKA needs search
that can:
- handle semantic intent and exact filename intent differently,
- combine multiple backends with deterministic fusion,
- rerank using live UI context and user focus,
- degrade gracefully when one backend is unavailable.

`vetka-search-retrieval` is that reliability layer.

## Core Capabilities

- Hybrid search orchestration:
  - semantic retrieval (vector),
  - keyword retrieval (BM25-like),
  - local file-name/content search.
- Multi-source fusion:
  - weighted Reciprocal Rank Fusion (RRF) for stable blending.
- Contextual reranking:
  - viewport-aware scoring boosts to prioritize what user currently sees.
- Intent-aware routing:
  - special handling for filename/doc discovery to reduce semantic noise.
- Resilience and fallback:
  - backend unavailability fallback to available retrieval channels.

## Architecture

- `hybrid_search.py`:
  - service lifecycle,
  - backend dispatch,
  - cache and fallback strategy,
  - per-intent result assembly.
- `rrf_fusion.py`:
  - weighted fusion implementation and explainability helpers.
- `contextual_retrieval.py`:
  - context profile construction and rerank adjustments.
- `file_search_service.py`:
  - local search and scoring pipeline,
  - macOS-first indexed lookup + grep/find/walk fallback paths.

## Innovation Focus

- Agent-first retrieval behavior:
  - not only "best score", but "best next step for the agent task".
- Practical anti-noise controls:
  - explicit mode routing (`semantic`, `keyword`, `hybrid`),
  - result reranking with context signals,
  - bounded local search to avoid pathological scans.

## Open Source Positioning

`vetka-search-retrieval` can be reused as a standalone retrieval subsystem for:
- AI IDE copilots,
- long-context assistant backends,
- multi-agent orchestration systems with heterogeneous search sources.

See [OPEN_SOURCE_CREDITS.md](OPEN_SOURCE_CREDITS.md) for upstream ecosystem
attribution.

## Development

1. Fork the repository.
2. Create branch: `feature/<name>` or `fix/<name>`.
3. Use Conventional Commits.
4. Add tests for ranking/fallback behavior changes.
5. Open a PR with before/after retrieval examples.

## Release Policy

- Versioning: Semantic Versioning (`vMAJOR.MINOR.PATCH`).
- Changelog source: `CHANGELOG.md`.

## Security

Please report vulnerabilities via `SECURITY.md`.

## License

MIT (`LICENSE`).
