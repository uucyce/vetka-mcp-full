# Phase 22-MCP-4: Claude Desktop Integration + Memory Export

**Date:** 2024-12-30
**Status:** COMPLETE
**Tests:** 32/32 passed

---

## Overview

Phase 22-MCP-4 implements Claude Desktop integration and a portable memory transfer protocol for VETKA. This enables:
1. Direct connection from Claude Desktop to VETKA MCP server
2. Export/import of VETKA memory in `.vetka-mem` format
3. Memory sharing between VETKA instances

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/mcp/claude_desktop.py` | 148 | Claude Desktop config generator |
| `src/mcp/stdio_server.py` | 183 | Stdio transport server for Claude Desktop |
| `src/mcp/memory_transfer.py` | 295 | Memory export/import (.vetka-mem format) |

## Files Modified

| File | Changes |
|------|---------|
| `main.py` | +4 REST endpoints for memory transfer |
| `src/mcp/__init__.py` | Added new exports |
| `tests/test_mcp_server.py` | +6 tests (27-32) |

---

## New Components

### 1. Claude Desktop Config Generator (`claude_desktop.py`)

Generates configuration for Claude Desktop integration.

```python
from src.mcp.claude_desktop import generate_claude_config, get_installation_instructions

# Generate config
config = generate_claude_config(server_name="vetka-mcp")

# Get installation guide
print(get_installation_instructions())
```

**Features:**
- Stdio transport (default, recommended)
- SSE transport (alternative)
- Auto-detects Python path and project root
- Generates complete `claude_desktop_config.json`

**Generated Config Example:**
```json
{
  "mcpServers": {
    "vetka-mcp": {
      "command": "/path/to/python",
      "args": ["/path/to/vetka/src/mcp/stdio_server.py"],
      "env": {
        "VETKA_PROJECT_PATH": "/path/to/vetka",
        "PYTHONPATH": "/path/to/vetka"
      }
    }
  }
}
```

### 2. Stdio Transport Server (`stdio_server.py`)

Standalone server for Claude Desktop subprocess communication.

**Protocol:**
- JSON-RPC 2.0 over stdin/stdout
- Logs to stderr (non-interfering)
- Supports all 11 VETKA tools

**MCP Methods:**
- `initialize` - Protocol handshake
- `tools/list` - List available tools
- `tools/call` - Execute tool
- `ping` - Health check

**Usage:**
```bash
# Direct execution
python src/mcp/stdio_server.py

# Or via Claude Desktop (spawned automatically)
```

### 3. Memory Transfer Protocol (`memory_transfer.py`)

Export and import VETKA memory snapshots.

**Format:** `.vetka-mem` (JSON with metadata)

```python
from src.mcp.memory_transfer import memory_transfer

# Export
result = memory_transfer.export_memory(
    filename="backup.vetka-mem",
    include_history=True,
    include_tree=True,
    include_reactions=True,
    compress=False
)

# Import (dry run first)
result = memory_transfer.import_memory(
    filepath="backup.vetka-mem",
    merge_strategy="merge",  # or "replace", "skip_existing"
    dry_run=True
)

# List exports
exports = memory_transfer.list_exports()
```

**File Format:**
```json
{
  "_meta": {
    "magic": "VETKA-MEM",
    "version": "1.0.0",
    "created_at": "2024-12-30T12:00:00",
    "checksum": "abc123..."
  },
  "tree": { ... },
  "history": [ ... ],
  "reactions": { ... }
}
```

**Security:**
- Checksum validation on import
- Path traversal protection
- Sensitive data not exposed

---

## REST API Endpoints

### Memory Export
```http
POST /api/memory/export
Content-Type: application/json

{
  "filename": "backup.vetka-mem",
  "include_history": true,
  "include_tree": true,
  "include_reactions": true,
  "compress": false
}
```

### Memory Import
```http
POST /api/memory/import
Content-Type: application/json

{
  "filepath": "/path/to/backup.vetka-mem",
  "merge_strategy": "merge",
  "dry_run": true
}
```

### List Exports
```http
GET /api/memory/exports
```

### Delete Export
```http
DELETE /api/memory/exports/<filename>
```

---

## Tests Added (27-32)

| # | Test | Description |
|---|------|-------------|
| 27 | `test_claude_config_generator` | Stdio config generation |
| 28 | `test_claude_config_sse` | SSE transport config |
| 29 | `test_installation_instructions` | Instructions contain all tools |
| 30 | `test_memory_transfer_export` | Export creates valid file |
| 31 | `test_memory_transfer_import_validation` | Import validates format |
| 32 | `test_memory_transfer_list_exports` | List exports correctly |

---

## Claude Desktop Installation

1. Open Claude Desktop Settings (⌘,)
2. Navigate to "Developer" → "MCP Servers"
3. Click "Edit Config"
4. Add VETKA configuration:

```json
{
  "mcpServers": {
    "vetka-mcp": {
      "command": "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/.venv/bin/python",
      "args": ["/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/stdio_server.py"],
      "env": {
        "VETKA_PROJECT_PATH": "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03",
        "PYTHONPATH": "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
      }
    }
  }
}
```

5. Restart Claude Desktop
6. Verify tools available in new chat

---

## Module Exports

```python
from src.mcp import (
    # Claude Desktop
    generate_claude_config,
    save_claude_config,
    get_installation_instructions,
    # Memory Transfer
    MemoryTransfer,
    memory_transfer,
)
```

---

## Data Directories

```
data/
└── memory_exports/           # .vetka-mem files
    └── vetka_memory_*.vetka-mem
```

---

## Summary

Phase 22-MCP-4 enables VETKA to integrate with Claude Desktop and share memory between instances:

- **Claude Desktop Integration**: Full stdio transport support with all 11 tools
- **Memory Export**: Complete knowledge graph backup to portable format
- **Memory Import**: Merge, replace, or skip existing data strategies
- **Security**: Checksum validation, path protection, dry-run mode

All 32 tests pass. VETKA can now be used directly from Claude Desktop as an MCP server.
