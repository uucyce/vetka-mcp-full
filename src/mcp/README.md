# vetka-mcp-core

VETKA MCP runtime core: a multi-transport MCP gateway and tool system for
agent orchestration, semantic retrieval, workflow execution, and controlled
write operations.

## Canonical Terms

- VETKA: Visual Enhanced Tree Knowledge Architecture.
- MYCELIUM: Multi-agent Yielding Cognitive Execution Layer for Intelligent Unified Management.
- ELISYA: Efficient Language-Independent Synchronization of Yielding Agents.
- ELISION: Efficient Language-Independent Symbolic Inversion of Names.

## Why This Module Matters
- Bridges external agents to VETKA through MCP with one tool surface.
- Supports both low-latency stateless calls and heavy async pipelines.
- Adds production controls around agent write operations (approval, rate limit,
  audit) instead of exposing raw filesystem/git calls directly.

## Core Capabilities
- Multi-transport MCP server:
  - stdio for Claude Desktop/Code
  - HTTP/SSE endpoints for IDE and service integrations
  - optional WebSocket channel for realtime paths
- Session-aware dispatch:
  - per-session actor isolation
  - header-based session routing (`X-Session-ID`)
- Tooling surface:
  - semantic search and file operations
  - git status/commit/test helpers
  - session bootstrap (`vetka_session_init`) and context DAG injection
  - workflow/task/artifact tools and Mycelium bridge tools
- Safety and observability:
  - approval workflow for dangerous write operations
  - audit log stream for tool calls
  - rate limiting policy for read/write paths

## Runtime Components
- `vetka_mcp_server.py`: universal MCP server with stdio + HTTP/SSE/WS modes.
- `vetka_mcp_bridge.py`: bridge layer mapping MCP tools to VETKA API/services.
- `mycelium_mcp_server.py`: async-heavy orchestration server (`mycelium_*` tool namespace).
- `jarvis_mcp_server.py`: dedicated Jarvis MCP server and unified search proxy.
- `mcp_server.py` / `stdio_server.py`: JSON-RPC tool execution servers.
- `tools/`: typed tool implementations (session, workflow, artifact, context DAG, search).

## Innovation Highlights
- Dual-server MCP architecture:
  - VETKA MCP for fast stateless agent tools
  - MYCELIUM MCP for long-running async orchestration
- Context-first session bootstrap:
  - session init merges preferences, pinned context, viewport state, memory
    summaries, and hyperlinks for lazy follow-up fetches.
- Agent-safe write path:
  - risky actions require explicit approvals and are tracked in audit trails.

## Open Source Attribution
This module builds on public OSS standards and libraries. See
[OPEN_SOURCE_CREDITS.md](OPEN_SOURCE_CREDITS.md) for upstream references and
license notes.

## Status
- Source of truth: monorepo `danilagoleen/vetka`
- Mirror sync: automated via subtree publish workflow
- Stability: experimental / fast-moving

## Development
1. Fork this repository.
2. Create a branch: `feature/short-name` or `fix/short-name`.
3. Use Conventional Commits.
4. Open a PR with validation notes.

## Security
Please report vulnerabilities via `SECURITY.md`.

## License
MIT. See `LICENSE`.
