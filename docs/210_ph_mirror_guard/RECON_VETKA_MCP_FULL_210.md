# RECON: VETKA MCP Full — Module Assembly Plan

**Date:** 2026-04-08
**Phase:** 210
**Author:** Terminal_81ce (VETKA Agent)
**Task:** tb_1775684721_37553_1
**Status:** IN PROGRESS

---

## 1. Problem Statement

External agent tried to run `vetka-mcp-core`:
```
ModuleNotFoundError: No module named 'src'
```

**Root Cause:** `vetka-mcp-core` contains only `src/mcp/`, but has **148+ imports** from other `src/*` modules that exist only in private monorepo.

---

## 2. Current Mirror Repos

| Repo | Contains | Can Reuse |
|------|----------|-----------|
| `vetka-mcp-core` | `src/mcp/` | ✅ Yes |
| `vetka-orchestration-core` | `src/orchestration/` | ✅ Yes |
| `vetka-memory-stack` | `src/memory/` | ✅ Yes |
| `vetka-search-retrieval` | `src/search/` | ✅ Yes |
| `vetka-bridge-core` | `src/bridge/` | ✅ Yes |
| `vetka-agents` | `src/agents/` | ✅ Yes |
| `vetka` (private) | `src/services/*` | ⚠️ Partial |

---

## 3. Required Modules for Full MCP

### 3.1 From Existing Mirrors (Direct Copy)

```
src/
├── mcp/              # ✅ vetka-mcp-core
├── orchestration/     # ✅ vetka-orchestration-core
├── memory/           # ✅ vetka-memory-stack
├── search/           # ✅ vetka-search-retrieval
├── bridge/           # ✅ vetka-bridge-core
└── agents/           # ✅ vetka-agents
```

### 3.2 From Private Monorepo (Need to Extract)

```
src/
├── services/         # ~30 critical files (see 3.3)
├── initialization/  # Need stubs
└── utils/           # Need stubs
```

### 3.3 Critical Services List

| File | Used By | Priority |
|------|---------|----------|
| `agent_registry.py` | session_tools, task_board_tools | 🔴 Critical |
| `session_tracker.py` | most tools | 🔴 Critical |
| `reflex_feedback.py` | session_tools, task_board_tools | 🔴 Critical |
| `reflex_integration.py` | llm_call_tools | 🔴 Critical |
| `reflex_scorer.py` | reflex_integration | 🟡 High |
| `reflex_registry.py` | reflex_scorer | 🟡 High |
| `reflex_guard.py` | session_tools | 🟡 High |
| `reflex_emotions.py` | reflex_scorer | 🟡 High |
| `reflex_filter.py` | reflex_integration | 🟡 High |
| `reflex_preferences.py` | reflex_integration | 🟡 High |
| `reflex_decay.py` | reflex_feedback | 🟢 Medium |
| `reflex_tool_memory.py` | reflex_integration | 🟢 Medium |
| `reflex_streaming.py` | reflex_integration | 🟢 Medium |
| `reflex_workaround_hook.py` | vetka_mcp_bridge | 🟢 Medium |
| `disk_artifact_service.py` | artifact_tools | 🔴 Critical |
| `artifact_scanner.py` | vetka_mcp_bridge | 🟡 High |
| `activity_hub.py` | edit_file, read_file | 🟡 High |
| `activity_emitter.py` | activity_hub | 🟢 Medium |
| `balance_tracker.py` | llm_call_tools | 🟡 High |
| `experience_report.py` | task_board_tools | 🟡 High |
| `roadmap_task_sync.py` | task_board_tools | 🟡 High |
| `roadmap_generator.py` | roadmap_task_sync | 🟢 Medium |
| `mcc_jepa_adapter.py` | task_board_tools, session_tools | 🟡 High |
| `jepa_runtime.py` | mcc_jepa_adapter | 🟢 Medium |
| `tool_source_watch.py` | session_tools | 🟢 Medium |
| `reflex_experiment.py` | reflex_integration | 🟢 Optional |
| `chat_artifact_registry.py` | artifact_scanner | 🟢 Optional |
| `browser_agent_proxy.py` | browser_manager | 🟢 Optional |

---

## 4. Stubs Needed

### 4.1 src/initialization/

```
src/initialization/
├── __init__.py
└── singletons.py      # Stub: get_socketio() returns None
```

### 4.2 src/utils/

```
src/utils/
├── __init__.py
├── staging_utils.py   # Stub: basic file operations
└── ...               # Other utils as needed
```

---

## 5. Import Analysis

### From `src/mcp/vetka_mcp_bridge.py`:
```python
from src.mcp.tools.session_tools import register_session_tools
from src.mcp.tools.task_board_tools import TASK_BOARD_SCHEMA
from src.services.reflex_workaround_hook import register_workaround_hook
from src.services.artifact_scanner import scan_artifacts
```

### From `src/mcp/tools/session_tools.py`:
```python
from src.services.agent_registry import AgentRole, get_agent_registry
from src.services.session_tracker import get_session_tracker
from src.services.reflex_feedback import get_feedback_store
from src.services.reflex_integration import reflex_session
from src.services.reflex_guard import get_feedback_guard, GuardContext
from src.services.reflex_emotions import get_reflex_emotions, EmotionContext
from src.services.tool_source_watch import get_tool_source_watch
```

### From `src/mcp/tools/task_board_tools.py`:
```python
from src.services.roadmap_task_sync import apply_task_profile_defaults
from src.services.session_tracker import get_session_tracker
from src.services.agent_registry import get_agent_registry
from src.services.mcc_jepa_adapter import embed_texts_for_overlay
from src.services.experience_report import ExperienceReport, get_experience_store
```

---

## 6. Solution: vetka-mcp-full Wrapper

### Structure:
```
vetka-mcp-full/
├── src/
│   ├── mcp/                    # From vetka-mcp-core
│   ├── orchestration/          # From vetka-orchestration-core
│   ├── memory/                # From vetka-memory-stack
│   ├── search/                # From vetka-search-retrieval
│   ├── bridge/                # From vetka-bridge-core
│   ├── agents/                # From vetka-agents
│   ├── services/              # From monorepo (30 files)
│   ├── initialization/        # Stubs
│   └── utils/                # Stubs
├── requirements.txt
├── README.md
└── LICENSE
```

### Installation Flow:
```bash
git clone https://github.com/danilagoleen/vetka-mcp-full.git
cd vetka-mcp-full
pip install -r requirements.txt
python -m src.vetka_mcp_server
```

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Circular imports | 🔴 High | Analyze import graph before copying |
| Missing transitive deps | 🟡 Medium | Run `python -c "import src.mcp.vetka_mcp_server"` and fix iteratively |
| JARVIS deps | 🟢 Low | Disable JARVIS server in full build |
| Large repo size | 🟢 Low | Git LFS for binaries if needed |

---

## 8. Implementation Plan

### Phase 1: Copy Direct Mirrors
- [ ] Copy `src/mcp/` from vetka-mcp-core
- [ ] Copy `src/orchestration/` from vetka-orchestration-core
- [ ] Copy `src/memory/` from vetka-memory-stack
- [ ] Copy `src/search/` from vetka-search-retrieval
- [ ] Copy `src/bridge/` from vetka-bridge-core
- [ ] Copy `src/agents/` from vetka-agents

### Phase 2: Extract Critical Services
- [ ] Copy ~30 services from monorepo `src/services/`
- [ ] Create `src/initialization/` stubs
- [ ] Create `src/utils/` stubs

### Phase 3: Test & Fix
- [ ] Run import test
- [ ] Fix circular deps
- [ ] Fix missing imports

### Phase 4: Publish
- [ ] Create GitHub repo `vetka-mcp-full`
- [ ] Push code
- [ ] Add to `public_mirror_map.tsv`

---

## 9. Related Docs

- `docs/200_taskboard_forever/RECON_GIT_MIRRORS_203.md` — Mirror architecture
- `docs/210_ph_mirror_guard/PROJECT_MIRROR_HEALTH_GUARD.md` — Mirror health
- `src/mcp/tools/__init__.py` — Full tool list

---

*RECON completed by Terminal_81ce, 2026-04-08*
