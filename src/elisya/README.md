# vetka-elisya-runtime

Core runtime of Elisya: multi-provider model execution, routing, key-management,
and resilient fallback logic for VETKA agent workflows.

## Why This Module Exists

Agent orchestration needs a stable inference runtime layer that can:
- route calls across heterogeneous providers and model families,
- enforce provider-specific tool-calling formats,
- survive key outages and transient API failures,
- expose predictable execution semantics to upper orchestration layers.

`vetka-elisya-runtime` is this execution kernel.

## Canonical System Names

### 🌳 VETKA
Visual Enhanced Tree Knowledge Architecture
→ структура знаний (скелет / дерево)

### 🍄 MYCELIUM
Multi-agent Yielding Cognitive Execution Layer for Intelligent Unified Management
→ распределённая сеть агентов (грибница / нервная сеть), literally "мозг под землёй"

### 🧠 ELISYA
Efficient Language-Independent Synchronization of Yielding Agents
→ координация / сознание / синхронизация, нервная система

### 🫧 ELISION
Efficient Language-Independent Symbolic Inversion of Names
→ сжатие / забывание / абстракция, память / гиппокамп / компрессор опыта

## Core Capabilities

- Multi-provider model runtime:
  - OpenAI, Anthropic, Google, Ollama, OpenRouter, xAI and compatible lanes.
- Dynamic routing and dispatch:
  - provider detection from model/source metadata,
  - runtime selection via registry and router components.
- Fallback and resilience:
  - retry strategies,
  - key roaming/rotation,
  - degraded-but-available execution paths.
- Tool-call aware execution:
  - provider-specific translation for tool/function calling contracts.
- Runtime bridge interfaces:
  - clean boundary between routing decisions and model execution.

## Architecture

- `provider_registry.py`:
  - provider adapters and execution contracts,
  - provider detection and runtime dispatch.
- `model_router_v2.py`, `llm_model_registry.py`:
  - routing and model metadata/profile selection.
- `call_model_with_fallback.py`, `llm_executor_bridge.py`:
  - fallback path orchestration and execution bridge.
- `key_manager.py`, `key_roaming_handler.py`, `api_key_detector.py`:
  - key lifecycle, rotation, and provider credential management.
- `state.py`:
  - shared runtime state surfaces used by orchestration layer.

## Innovation Focus

- One runtime contract across provider-fragmented model APIs.
- Production-pragmatic fallback behavior for unstable model/network lanes.
- Explicit transport boundary that keeps orchestrator logic decoupled from
  low-level provider quirks.

## Open Source Positioning

`vetka-elisya-runtime` can be reused as a standalone LLM runtime core for:
- multi-provider agent platforms,
- self-hosted + API-hybrid inference stacks,
- orchestration systems requiring deterministic fallback semantics.

See [OPEN_SOURCE_CREDITS.md](OPEN_SOURCE_CREDITS.md) for upstream ecosystem
attribution.

## Development

1. Fork the repository.
2. Create branch: `feature/<name>` or `fix/<name>`.
3. Use Conventional Commits.
4. Add tests for routing, fallback, and provider contract compatibility.
5. Open a PR with reproducible runtime traces.

## Release Policy

- Versioning: Semantic Versioning (`vMAJOR.MINOR.PATCH`).
- Changelog source: `CHANGELOG.md`.

## Security

Please report vulnerabilities via `SECURITY.md`.

## License

MIT (`LICENSE`).
