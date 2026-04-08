# vetka-bridge-core

Shared bridge runtime for VETKA tools. This module unifies tool behavior across
different agent entrypoints, so MCP clients and IDE/runtime integrations execute
the same logic, validations, and response shaping.

## Why This Module Exists

VETKA runs in a multi-agent environment where multiple adapters need the same
capabilities:
- semantic retrieval over project knowledge,
- safe read/write file operations,
- git and test execution hooks,
- memory-aware context and preference access.

`vetka-bridge-core` is the compatibility layer that keeps these operations
consistent across transports.

## Core Capabilities

- Unified tool taxonomy:
  - `ReadTool` for deterministic, side-effect-free operations.
  - `WriteTool` for state-changing operations with safe execution paths.
  - `ExecutionTool` for model calls, test runs, and runtime actions.
- Shared registry and lookup:
  - central `TOOL_REGISTRY`,
  - `get_tool` and `list_tools` utilities for adapter wiring.
- Standardized result formatters:
  - compact output adapters for search, tree, health, git, tests, and memory.
- Memory-aware bridge surfaces:
  - conversation context packing,
  - user preference retrieval,
  - memory summary generation.

## Architecture

- `shared_tools.py`:
  - bridge primitives (`VETKATool`, `ReadTool`, `WriteTool`, `ExecutionTool`),
  - concrete tools and formatter helpers,
  - tool registry.
- `__init__.py`:
  - public package exports for external bridge consumers.

This module is used by VETKA MCP bridge and additional runtime adapters to
minimize behavior drift and duplicate logic.

## Design Principles

- Single implementation, multiple transports.
- Explicit argument validation per tool.
- Stable response contract for agent clients.
- Operational safety for write and execution paths.
- Incremental extensibility for new bridge adapters.

## Open Source Positioning

`vetka-bridge-core` is intended as a reusable integration kernel for
agent-native applications that need:
- one internal tool contract,
- multiple external protocols,
- predictable outputs for orchestration pipelines.

See [OPEN_SOURCE_CREDITS.md](OPEN_SOURCE_CREDITS.md) for upstream ecosystem
references and attribution.

## Development

1. Fork the repository.
2. Create branch: `feature/<name>` or `fix/<name>`.
3. Follow Conventional Commits.
4. Add tests/docs for behavior changes.
5. Open a PR with context and validation notes.

## Release Policy

- Versioning: Semantic Versioning (`vMAJOR.MINOR.PATCH`).
- Changelog source: `CHANGELOG.md`.

## Security

See `SECURITY.md` for vulnerability reporting workflow.

## License

MIT (`LICENSE`).
