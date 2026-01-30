# VETKA Codebase Audit Report
**Date:** 2026-01-04
**Total Files:** 366 (Python, TypeScript, JavaScript)

---

## 1. File Structure Overview

### Root Level Python Files (Entry Points)
- `main.py` (7550 lines) - MAIN entry point
- `launch_vetka.py` - Alternative launcher
- `start.py` - Startup script

### Core Structure
```
src/                     # Main source code (32 subdirectories)
├── agents/              # 28 agent files
├── chat/                # Chat management
├── elisya/              # LLM abstraction layer
├── elisya_integration/  # Elisya integration
├── layout/              # Graph layout algorithms
├── mcp/                 # MCP server and tools
├── memory/              # Qdrant/Weaviate clients
├── orchestration/       # Workflow orchestration (18 files)
├── server/              # FastAPI routes
├── tools/               # Tool execution
├── transformers/        # Data transformers
├── validators/          # Data validators
├── visualizer/          # Tree visualization
└── workflows/           # LangGraph workflows

app/                     # DUPLICATE STRUCTURE (should be deleted)
├── config/              # Duplicate of config/
├── elisya_integration/  # Duplicate
├── langgraph_flows/     # Duplicate
├── src/agents/          # Partial duplicate
├── src/memory/          # Partial duplicate
└── src/workflows/       # Partial duplicate

frontend/                # Vanilla JS frontend (OLD)
├── static/js/           # 10 Vanilla JS files
└── templates/           # HTML templates

client/                  # React frontend (NEW)
├── src/components/      # React components
├── src/hooks/           # React hooks
├── src/store/           # Zustand store
└── src/utils/           # Utilities

archive/                 # Archived old code
├── backups/
├── experiments/
├── old_installers/
├── old_tests/
├── patches/
└── vanilla_frontend_backup/
```

---

## 2. Duplicate Folders (CRITICAL - DELETE)

| Duplicate Path | Original Path | Action |
|----------------|---------------|--------|
| `app/config/` | `config/` | DELETE app/config |
| `app/elisya_integration/` | `elisya_integration/` or `src/elisya_integration/` | DELETE app/elisya_integration |
| `app/langgraph_flows/` | `langgraph_flows/` | DELETE app/langgraph_flows |
| `app/src/agents/` | `src/agents/` | DELETE app/src/agents (older, smaller) |
| `app/src/memory/` | `src/memory/` | DELETE app/src/memory (older) |
| `app/src/workflows/` | `src/workflows/` | DELETE app/src/workflows |
| `elisya_integration/` | `src/elisya_integration/` | MERGE into src/, DELETE root |
| `langgraph_flows/` | `src/workflows/` | MERGE into src/workflows, DELETE root |
| `config/` | Keep, but consider moving to `src/config/` | KEEP (referenced by main.py) |

### Triple Duplicates:
- `elisya_integration/` exists in 3 places:
  - `./elisya_integration/`
  - `./app/elisya_integration/`
  - `./src/elisya_integration/`

---

## 3. Vanilla JS Files (DELETE - React Migration Complete)

These files use `document.getElementById`, `addEventListener` etc. and should be deleted:

| File | Lines | Status |
|------|-------|--------|
| `frontend/static/js/vetka-main.js` | ~200 | DELETE |
| `frontend/static/js/kg-tree-renderer.js` | ~300 | DELETE |
| `frontend/static/js/socket_handler.js` | ~100 | DELETE |
| `frontend/static/js/zoom_manager.js` | ~80 | DELETE |
| `frontend/static/js/artifact_panel.js` | ~150 | DELETE |
| `frontend/static/js/approval_modal.js` | ~100 | DELETE |
| `frontend/static/js/ui/chat_panel.js` | ~200 | DELETE |
| `frontend/static/js/config.js` | ~50 | DELETE |
| `frontend/static/js/layout/sugiyama.js` | ~100 | DELETE |
| `frontend/static/js/modes/knowledge_mode.js` | ~80 | DELETE |
| `frontend/static/js/renderer/lod.js` | ~50 | DELETE |

**Also delete:**
- `app/frontend/static/js/` - Same Vanilla files
- `archive/vanilla_frontend_backup/` - Already backed up

---

## 4. Unused Python Files (Candidates for DELETE)

Files not imported anywhere in the codebase:

### Memory (DELETE)
- `src/memory/test_hybrid_search.py` - Test file
- `src/memory/vetka_validate_endpoints.py` - Old validation
- `src/memory/vetka_create_collections.py` - Old setup

### Workflows (DELETE or MERGE)
- `src/workflows/langgraph_builder.py` - Unused
- `src/workflows/langgraph_nodes.py` - Unused

### Agents (REVIEW CAREFULLY)
- `src/agents/vetka_visual.py` - Not imported
- `src/agents/pixtral_learner.py` - Not imported
- `src/agents/vetka_ops.py` - Not imported (but may be used dynamically)
- `src/agents/learner_agent_init.py` - Not imported
- `src/agents/agentic_tools.py` - Not imported
- `src/agents/hostess_agent.py` - May be used dynamically via __init__.py
- `src/agents/dev_agent_enhanced.py` - May be used dynamically
- `src/agents/role_prompts.py` - May be used at runtime
- `src/agents/pm_agent_enhanced.py` - May be used dynamically
- `src/agents/qwen_learner.py` - Not imported

### Orchestration (DELETE - Old Versions)
- `src/orchestration/elisya_endpoints.py`
- `src/orchestration/context_assembler.py`
- `src/orchestration/router_phase3.py`
- `src/orchestration/autogen_extension.py`
- `src/orchestration/key_management_api.py`
- `src/orchestration/agent_orchestrator_backup.py` - BACKUP file
- `src/orchestration/orchestrator_langgraph_v2.py` - Old version
- `src/orchestration/orchestrator_langgraph_v2_with_metrics.py` - Old version
- `src/orchestration/agent_orchestrator_fixed.py` - Old fix

### Integrations (DELETE)
- `src/integrations/action_registry.py`
- `src/elisya_integration/elysia_langgraph_integration.py`

### Other (DELETE)
- `src/utils/artifact_extractor.py`
- `src/visualizer/kg_layout.py`

---

## 5. TODO/FIXME Markers (Minimal)

Only 2 markers found in active code:
1. `src/elisya/api_aggregator_v3.py:174` - "TODO: Implement other providers when needed"
2. `src/agents/role_prompts.py:128` - Documentation line (not actual TODO)

---

## 6. Top 30 Files by Size

| # | Lines | File | Action |
|---|-------|------|--------|
| 1 | 7550 | `main.py` | REFACTOR - Too large |
| 2 | 5189 | `archive/backups/main_backup_day1.py` | KEEP (backup) |
| 3 | 2502 | `src/layout/knowledge_layout.py` | OK |
| 4 | 1904 | `src/visualizer/tree_renderer.py` | OK |
| 5 | 1728 | `src/orchestration/orchestrator_with_elisya.py` | OK |
| 6 | 1680 | `src/transformers/phase9_to_vetka.py` | OK |
| 7 | 1363 | `src/agents/tools.py` | REVIEW - Large |
| 8 | 1211 | `src/knowledge_graph/position_calculator.py` | OK |
| 9 | 1196 | `src/agents/arc_solver_agent.py` | OK |
| 10| 983 | `tests/test_mcp_server.py` | OK |

---

## 7. semantic_search Method Analysis

**Result:** `semantic_search` is NOT defined anywhere in src/

This method does NOT exist. Any code expecting it will fail.
Check if this should be in `src/memory/qdrant_client.py` or similar.

---

## 8. Recommendations Summary

### IMMEDIATE ACTIONS (Phase 32.6):

1. **DELETE entire `app/` folder structure duplicates:**
   ```bash
   rm -rf app/config app/elisya_integration app/langgraph_flows app/src
   ```

2. **DELETE Vanilla frontend files:**
   ```bash
   rm -rf frontend/static/js/
   rm -rf app/frontend/static/js/
   ```

3. **DELETE root-level duplicate folders:**
   ```bash
   rm -rf elisya_integration/  # Use src/elisya_integration instead
   rm -rf langgraph_flows/     # Merge into src/workflows
   ```

4. **DELETE unused orchestration files:**
   ```bash
   rm src/orchestration/agent_orchestrator_backup.py
   rm src/orchestration/orchestrator_langgraph_v2.py
   rm src/orchestration/orchestrator_langgraph_v2_with_metrics.py
   rm src/orchestration/agent_orchestrator_fixed.py
   ```

5. **DELETE unused memory files:**
   ```bash
   rm src/memory/test_hybrid_search.py
   rm src/memory/vetka_validate_endpoints.py
   rm src/memory/vetka_create_collections.py
   ```

### FUTURE REFACTORING:

1. **Split main.py (7550 lines)** into smaller modules:
   - `main_routes.py` - Route definitions
   - `main_websocket.py` - WebSocket handlers
   - `main_initialization.py` - App initialization

2. **Consolidate agents** - Too many similar agents, consider merging:
   - All `*_learner.py` files into unified learner
   - All `vetka_*.py` agents into single enhanced agent

3. **Clean up src/orchestration/** - 18 files, many unused

---

## 9. Safe Files (DO NOT DELETE)

| Path | Reason |
|------|--------|
| `src/agents/hostess_agent.py` | Used dynamically via __init__.py |
| `src/agents/role_prompts.py` | May be imported at runtime |
| `src/agents/dev_agent_enhanced.py` | Dynamic usage |
| `config/` folder | Referenced by main.py |
| `archive/` folder | Historical backup |
| `client/` folder | Active React frontend |

---

## 10. File Count Summary

| Category | Count | Action |
|----------|-------|--------|
| Total files | 366 | |
| Python (.py) | ~200 | |
| TypeScript (.ts/.tsx) | ~80 | |
| JavaScript (.js) | ~86 | |
| Duplicate files | ~50 | DELETE |
| Unused files | ~28 | DELETE |
| Vanilla JS | ~12 | DELETE |
| **Files to delete** | **~90** | |
| **Remaining after cleanup** | **~276** | |

---

**End of Audit Report**
