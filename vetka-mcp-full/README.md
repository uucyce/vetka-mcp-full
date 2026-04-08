# VETKA MCP Full

**Complete MCP server with all modules — ready to run out of the box.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-Native-green.svg)](https://modelcontextprotocol.io)

---

## What is this?

**VETKA MCP Full** is a complete, self-contained MCP server that includes:

- **MCP Server** with 30+ tools
- **Memory Stack** — short/long-term context, Qdrant/Weaviate
- **Orchestration** — task board, DAG execution, workflow pipelines
- **Search & Retrieval** — semantic + keyword search
- **Agent System** — role generation, worktree management
- **Reflex Engine** — feedback, scoring, recommendations

This is the **full-fat** version of `vetka-mcp-core` — no external dependencies needed.

## Quick Install

```bash
# Clone
git clone https://github.com/danilagoleen/vetka-mcp-full.git
cd vetka-mcp-full

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run MCP server
python -m src.vetka_mcp_server
```

## MCP Configuration

### Claude Desktop (macOS)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vetka": {
      "command": "python",
      "args": ["-m", "src.vetka_mcp_server", "--transport", "stdio"],
      "env": {
        "VETKA_API_URL": "http://localhost:5001"
      }
    }
  }
}
```

### Claude Code

```json
{
  "mcpServers": {
    "vetka": {
      "command": "python",
      "args": ["-m", "src.vetka_mcp_server", "--transport", "stdio"]
    }
  }
}
```

## What's Included

### Modules

| Module | Description |
|--------|-------------|
| `src/mcp/` | MCP server core + 30+ tools |
| `src/memory/` | Short/long-term memory, context compression |
| `src/orchestration/` | Task board, DAG execution, pipelines |
| `src/search/` | Hybrid semantic + keyword search |
| `src/bridge/` | Tool validation, response contracts |
| `src/agents/` | Agent implementations (ARC solver, Hostess, etc.) |
| `src/services/` | Reflex, artifacts, activity, balance tracking |
| `src/initialization/` | Server initialization stubs |
| `src/utils/` | Key management, staging utilities |

### MCP Tools (30+)

**Session & Context:**
- `vetka_session_init` — Initialize session with fat context
- `vetka_session_status` — Get session status
- `vetka_get_context_dag` — Context digest from all sources

**Search & Navigation:**
- `vetka_search` — File search by name/content
- `vetka_search_knowledge` — Semantic search
- `vetka_get_tree` — Folder hierarchy

**File Operations:**
- `vetka_read_file` — Read file content
- `vetka_edit_file` — Edit file (dry-run by default)
- `vetka_list_files` — List directory

**Git Operations:**
- `vetka_git_status` — Git status
- `vetka_git_commit` — Create commit (dry-run by default)

**Task Board:**
- `vetka_task_board` — CRUD operations for tasks
- `vetka_task_dispatch` — Dispatch to agent
- `vetka_task_import` — Import from file

**Memory:**
- `vetka_memory_get` — Get memory entries
- `vetka_memory_store` — Store new entry
- `vetka_memory_search` — Search memory

**Workflows & ARC:**
- `vetka_execute_workflow` — Execute full workflow
- `vetka_arc_gap` — Analyze prompt for gaps
- `vetka_arc_concepts` — Extract concepts

**Artifacts:**
- `vetka_list_artifacts` — List artifacts
- `vetka_edit_artifact` — Edit artifact
- `vetka_approve_artifact` — Approve
- `vetka_reject_artifact` — Reject

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VETKA MCP Full                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│   │   Claude    │     │    MCP     │     │   Other    │  │
│   │   Desktop   │────▶│   Server   │◀────│   Agents   │  │
│   │   (stdio)   │     │  (30+ tools)│     │  (HTTP)    │  │
│   └─────────────┘     └──────┬──────┘     └─────────────┘  │
│                              │                               │
│   ┌──────────────────────────┼──────────────────────────┐    │
│   │                          │                          │    │
│   ▼                          ▼                          ▼    │
│ ┌──────────┐          ┌───────────┐           ┌──────────┐ │
│ │  Memory  │          │Orchestra- │           │  Search  │ │
│ │  Stack   │          │   tion    │           │          │ │
│ │ (Qdrant)│          │(TaskBoard)│           │          │ │
│ └──────────┘          └───────────┘           └──────────┘ │
│ ┌──────────┐          ┌───────────┐           ┌──────────┐ │
│ │   Reflex │          │  Agents   │           │  Bridge  │ │
│ │  Engine  │          │(ARC, etc) │           │          │ │
│ └──────────┘          └───────────┘           └──────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VETKA_API_URL` | `http://localhost:5001` | Backend API URL |
| `VETKA_SESSION_DIR` | `~/.vetka/sessions` | Session storage |
| `VETKA_MEMORY_BACKEND` | `qdrant` | Memory backend |
| `VETKA_QDRANT_URL` | `http://localhost:6333` | Qdrant server |

## Related Modules

| Module | Description |
|--------|-------------|
| [vetka-agents](https://github.com/danilagoleen/vetka-agents) | Agent runtime & role generation |
| [vetka-taskboard](https://github.com/danilagoleen/vetka-taskboard) | Task coordination API |

## Development

```bash
# Clone
git clone https://github.com/danilagoleen/vetka-mcp-full.git
cd vetka-mcp-full

# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio

# Run tests
pytest tests/ -v

# Run MCP server in stdio mode
python -m src.vetka_mcp_server

# Run MCP server in HTTP mode
uvicorn src.vetka_mcp_server:app --port 5001
```

## Status

- **Phase**: Active development
- **Source**: Monorepo `danilagoleen/vetka`
- **Stability**: Experimental

## License

MIT License. See [LICENSE](LICENSE).

---

**Built with ❤️ by the [VETKA Project](https://github.com/danilagoleen/vetka)**
