# vetka-orchestration-core

Agent orchestration kernel for VETKA: DAG execution, pipeline coordination,
task lifecycle control, and runtime context routing across multi-agent flows.

## Why This Module Exists

Complex agent systems need more than model calls. They need:
- deterministic task progression across stages and roles,
- scheduling and concurrency control for parallel pipelines,
- durable workflow state/history and analytics,
- robust integration with memory and runtime layers.

`vetka-orchestration-core` is this control plane.

## Canonical Terms

- VETKA: Visual Enhanced Tree Knowledge Architecture.
- MYCELIUM: Multi-agent Yielding Cognitive Execution Layer for Intelligent Unified Management.
- ELISYA: Efficient Language-Independent Synchronization of Yielding Agents.
- ELISION: Efficient Language-Independent Symbolic Inversion of Names.

## Core Capabilities

- Workflow orchestration:
  - staged multi-agent pipelines,
  - sequential and parallel execution modes.
- DAG execution:
  - dependency-aware task graph planning and run management.
- Runtime coordination:
  - task board, progress tracking, failure handling, and retry logic.
- Context routing:
  - context packing/fusion and dispatch to appropriate runtime lanes.
- Operations analytics:
  - pipeline analytics, weak-link detection, and execution diagnostics.

## Architecture

- `orchestrator_with_elisya.py`, `agent_orchestrator.py`:
  - top-level orchestration entrypoints.
- `dag_executor.py`, `semantic_dag_builder.py`:
  - graph planning and dependency execution flow.
- `agent_pipeline.py`, `task_board.py`, `progress_tracker.py`:
  - pipeline state and task lifecycle controls.
- `context_packer.py`, `context_fusion.py`, `query_dispatcher.py`:
  - context shaping and routing logic.
- `memory_manager.py`, `pipeline_analytics.py`:
  - persistence-facing workflow memory and analytics plane.

## Innovation Focus

- Unified control plane for mixed orchestration patterns (DAG + staged pipeline).
- Practical operations layer: analytics and bottleneck detection built into the
  orchestration module, not bolted on externally.
- Tight but modular coupling to runtime/memory layers through explicit interfaces.

## Open Source Positioning

`vetka-orchestration-core` can be reused as a standalone orchestrator for:
- multi-agent engineering copilots,
- workflow-heavy AI production systems,
- graph-driven execution platforms needing traceable runtime control.

See [OPEN_SOURCE_CREDITS.md](OPEN_SOURCE_CREDITS.md) for ecosystem references.

## Development

1. Fork the repository.
2. Create branch: `feature/<name>` or `fix/<name>`.
3. Use Conventional Commits.
4. Add tests for DAG correctness, retries, and orchestration state transitions.
5. Open a PR with reproducible workflow traces.

## Release Policy

- Versioning: Semantic Versioning (`vMAJOR.MINOR.PATCH`).
- Changelog source: `CHANGELOG.md`.

## Security

Please report vulnerabilities via `SECURITY.md`.

## License

MIT (`LICENSE`).
