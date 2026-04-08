# RECON: VETKA Public Repos Documentation Status

**Date:** 2026-04-09
**Phase:** 210
**Author:** Terminal_81ce (VETKA Agent)
**Task:** tb_1775685557_37553_1
**Status:** IN PROGRESS

---

## 1. Public Repositories Overview

| Repo | Description | Quick Install | MCP Config | Dependencies | Status |
|------|-------------|--------------|------------|---------------|--------|
| `vetka-mcp-core` | MCP server core | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Good |
| `vetka-mcp-full` | Complete MCP (all-in-one) | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Good |
| `vetka-agents` | Agent runtime, role generation | ✅ Yes | ❌ N/A | ✅ Yes | ✅ Good |
| `vetka-taskboard` | Task coordination API | ✅ Yes | ❌ N/A | ✅ Yes | ✅ Good |
| `vetka-bridge-core` | Tool bridge | ✅ Yes | ❌ N/A | ✅ Yes | ✅ Updated |
| `vetka-memory-stack` | Memory runtime | ✅ Yes | ❌ N/A | ✅ Yes | ✅ Updated |
| `vetka-search-retrieval` | Hybrid search | ✅ Yes | ❌ N/A | ✅ Yes | ✅ Updated |
| `vetka-orchestration-core` | Orchestration | ✅ Yes | ❌ N/A | ✅ Yes | ✅ Updated |
| `vetka-ingest-engine` | Ingestion | ✅ Yes | ❌ N/A | ✅ Yes | ✅ Updated |
| `vetka-elisya-runtime` | LLM runtime | ✅ Yes | ❌ N/A | ✅ Yes | ✅ Updated |
| `vetka-chat-ui` | React chat UI | ✅ Yes | ❌ N/A | ✅ Yes | ✅ Updated |
| `mycelium` | DAG command center | ✅ Yes | ❌ N/A | ✅ Yes | ✅ Updated |

**Summary:** 12/12 have Quick Install ✅

---

## 2. UPDATES COMPLETED (2026-04-09)

### Repos Updated with Quick Install:
- [x] `vetka-bridge-core` — Added requirements.txt, Quick Install, Related Modules
- [x] `vetka-memory-stack` — Added requirements.txt, Quick Install, Related Modules
- [x] `vetka-search-retrieval` — Added requirements.txt, Quick Install, Related Modules
- [x] `vetka-orchestration-core` — Added requirements.txt, Quick Install, Related Modules
- [x] `vetka-ingest-engine` — Added requirements.txt, Quick Install, Related Modules
- [x] `vetka-elisya-runtime` — Added requirements.txt, Quick Install, Related Modules
- [x] `vetka-chat-ui` — Added requirements.txt, Quick Install, Related Modules
- [x] `mycelium` — Added requirements.txt, Quick Install, Related Modules

### Repos Already Good:
- [x] `vetka-mcp-full` — ✅ Complete (was already good)
- [x] `vetka-mcp-core` — ✅ Updated earlier
- [x] `vetka-agents` — ✅ Updated earlier
- [x] `vetka-taskboard` — ✅ Already had Quick Start

---

## 3. Architecture Decision

### Current State (Duplication)
```
vetka-mcp-full/
├── src/mcp/          ← duplicate of vetka-mcp-core
├── src/bridge/        ← duplicate of vetka-bridge-core
├── src/memory/       ← duplicate of vetka-memory-stack
├── src/orchestration/  ← duplicate of vetka-orchestration-core
├── src/search/        ← duplicate of vetka-search-retrieval
└── src/agents/       ← duplicate of vetka-agents
```

### Recommended Structure
Each repo should have clear role:

| Repo | Role | Install Type |
|------|------|--------------|
| `vetka-mcp-full` | **Entry Point** | Full install (all-in-one) |
| `vetka-mcp-core` | MCP Reference | Module install |
| `vetka-agents` | Agent Reference | Module install |
| `vetka-taskboard` | Task API | Standalone |
| Other `-core` repos | **Reference only** | Internal deps |

---

## 3. Missing in Most READMEs

### Required Sections (Reference Repos)
1. **Quick Install** — 3-5 commands
2. **Requirements** — pip install line
3. **What you get** — Features list
4. **Related Modules** — Links to other VETKA repos
5. **Type indicator** — "Reference module" vs "Standalone"

### Required Sections (Entry Points)
1. **Quick Install** — One-liner or 3 steps
2. **MCP Configuration** — JSON config for Claude/Codex
3. **Environment Variables** — Required setup
4. **Supported Clients** — Claude, Codex, OpenCode, etc.
5. **Architecture Diagram** — Visual overview

---

## 4. Plan to Fix

### Phase 1: Add Quick Install to Reference Repos ✅ COMPLETED
- [x] `vetka-bridge-core` — Added requirements.txt + Quick Install
- [x] `vetka-memory-stack` — Added requirements.txt + Quick Install
- [x] `vetka-search-retrieval` — Added requirements.txt + Quick Install
- [x] `vetka-orchestration-core` — Added requirements.txt + Quick Install
- [x] `vetka-ingest-engine` — Added requirements.txt + Quick Install
- [x] `vetka-elisya-runtime` — Added requirements.txt + Quick Install

### Phase 2: Update Entry Points ✅ COMPLETED (partially)
- [x] `vetka-mcp-core` — Updated with Quick Install earlier
- [x] `vetka-mcp-full` — Already had good docs

### Phase 3: Other Repos ✅ COMPLETED
- [x] `vetka-chat-ui` — Added Quick Install for React app
- [x] `mycelium` — Added Quick Install

### Phase 4: GitHub Metadata ⏳ PENDING
- [ ] Update topics on all repos
- [ ] Add homepage links
- [ ] Verify descriptions are clear

---

## 5. Template: Quick Install Section

```markdown
## Quick Install

```bash
# Clone
git clone https://github.com/danilagoleen/vetka-{module}.git
cd vetka-{module}

# Install dependencies
pip install -r requirements.txt
```

## Requirements

- Python 3.10+
- See `requirements.txt` for full list

## Related Modules

| Module | Description |
|--------|-------------|
| [vetka-mcp-full](https://github.com/danilagoleen/vetka-mcp-full) | Complete MCP install (all-in-one) |
| [vetka-mcp-core](https://github.com/danilagoleen/vetka-mcp-core) | MCP server reference |
```

---

## 6. Next Steps

1. Create requirements.txt for repos that don't have it
2. Add Quick Install sections to all reference repos
3. Update vetka-mcp-full as the recommended entry point
4. Sync changes to monorepo via workflow

---

*RECON in progress by Terminal_81ce, 2026-04-09*
