# vetka-memory-stack

Memory runtime for VETKA: short-term buffers, long-term vector memory,
context compression, and user-preference persistence for agent interactions.

## Why This Module Exists

Agent systems fail when memory is either too shallow or too noisy. VETKA needs:
- fast short-term recall for current reasoning loops,
- durable long-term memory across chats and sessions,
- user preference persistence for personalization,
- context compression to keep token budgets under control.

`vetka-memory-stack` provides this full memory path.

## Canonical Terms

- VETKA: Visual Enhanced Tree Knowledge Architecture.
- MYCELIUM: Multi-agent Yielding Cognitive Execution Layer for Intelligent Unified Management.
- ELISYA: Efficient Language-Independent Synchronization of Yielding Agents.
- ELISION: Efficient Language-Independent Symbolic Inversion of Names.

## Core Capabilities

- Short-term memory:
  - STM buffers for recent conversational/task context.
- Long-term memory:
  - vector-backed persistence and retrieval for historical knowledge.
- User memory:
  - Engram-like preference and profile storage.
- Context shaping:
  - compression and elision pipelines for prompt-safe context windows.
- Operational resilience:
  - proxy/cache/retry layers around memory backends.

## Architecture

- `stm_buffer.py`, `hostess_memory.py`:
  - short-horizon and recency-weighted context handling.
- `engram_user_memory.py`, `user_memory.py`, `user_memory_updater.py`:
  - user-specific memory lifecycle and preference updates.
- `qdrant_client.py`, `qdrant_auto_retry.py`, `qdrant_batch_manager.py`:
  - vector backend integration, retry and batching behavior.
- `memory_proxy.py`, `mgc_cache.py`:
  - deduplication, caching, and call-shaping to reduce backend churn.
- `elision.py`, `compression.py`, `jarvis_prompt_enricher.py`:
  - context compression and prompt enrichment logic.

## Innovation Focus

- Unified short+long memory path for agent orchestration.
- Practical token-economy controls via compression and layered context.
- Personalization-ready memory primitives integrated into runtime flow.
- Fault-tolerant vector operations for unstable local infra conditions.

## Open Source Positioning

`vetka-memory-stack` can serve as a standalone memory substrate for:
- multi-agent assistants,
- long-running copilot systems,
- personalized model runtimes with durable context.

See [OPEN_SOURCE_CREDITS.md](OPEN_SOURCE_CREDITS.md) for upstream ecosystem
attribution.

## Development

1. Fork the repository.
2. Create branch: `feature/<name>` or `fix/<name>`.
3. Use Conventional Commits.
4. Add tests for memory correctness, retries, and compression behavior.
5. Open a PR with reproducible before/after memory traces.

## Release Policy

- Versioning: Semantic Versioning (`vMAJOR.MINOR.PATCH`).
- Changelog source: `CHANGELOG.md`.

## Security

Please report vulnerabilities via `SECURITY.md`.

## License

MIT (`LICENSE`).
