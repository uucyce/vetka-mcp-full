# vetka-ingest-engine

Ingestion and indexing runtime for VETKA. This module converts heterogeneous
project and media inputs into structured chunks, dependencies, and vector-ready
artifacts for downstream memory/search systems.

## Why This Module Exists

Agent workflows depend on data quality at ingestion time. VETKA needs:
- robust file and dependency scanning across large codebases,
- continuous re-indexing when files change,
- multimodal extraction contracts for text/media pipelines,
- reliable handoff into embedding and vector update paths.

`vetka-ingest-engine` is this intake-to-index backbone.

## Core Capabilities

- Project scanning:
  - local filesystem traversal and file metadata/content extraction.
- Dependency extraction:
  - AST-based Python import analysis and path resolution.
- Real-time indexing hooks:
  - file watcher with adaptive scan behavior and update coalescing.
- Multimodal ingestion contracts:
  - normalized chunk schemas for media/OCR pipelines.
- Embedding/index pipeline integration:
  - ingestion output prepared for vector/index backends.

## Architecture

- `local_scanner.py`, `local_project_scanner.py`:
  - local tree scan and content capture primitives.
- `python_scanner.py`, `import_resolver.py`, `dependency_calculator.py`:
  - code intelligence extraction and dependency graph signals.
- `file_watcher.py`, `qdrant_updater.py`:
  - near-real-time change tracking and reindex/update orchestration.
- `embedding_pipeline.py`, `extractor_registry.py`:
  - extraction/embedding flow coordination.
- `multimodal_contracts.py`, `mime_policy.py`:
  - schema and policy normalization for mixed media inputs.

## Innovation Focus

- Hybrid static+live ingestion:
  - one-time scans plus continuous watcher-driven updates.
- Practical anti-noise indexing:
  - skip and throttling heuristics for high-frequency/generated files.
- Schema-first multimodal normalization:
  - consistent chunk contract across extraction lanes.

## Open Source Positioning

`vetka-ingest-engine` can be reused as a standalone ingest layer for:
- AI code assistants,
- local-first knowledge indexing tools,
- multimodal retrieval stacks requiring unified chunk contracts.

See [OPEN_SOURCE_CREDITS.md](OPEN_SOURCE_CREDITS.md) for upstream ecosystem
attribution.

## Development

1. Fork the repository.
2. Create branch: `feature/<name>` or `fix/<name>`.
3. Use Conventional Commits.
4. Add tests for extraction correctness and watcher/index edge cases.
5. Open a PR with reproducible ingest traces.

## Release Policy

- Versioning: Semantic Versioning (`vMAJOR.MINOR.PATCH`).
- Changelog source: `CHANGELOG.md`.

## Security

Please report vulnerabilities via `SECURITY.md`.

## License

MIT (`LICENSE`).
