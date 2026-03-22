# Architecture: Agent Initialization System (Zeta)
**Phase:** 195+ (Agent Infrastructure)
**Date:** 2026-03-22
**Author:** Opus (Zeta Recon)
**Task:** tb_1774141462_11
**Status:** RECON COMPLETE — Architecture defined

---

## 1. Current State (Recon Findings)

### 1.1 Task Board (R1)

**Core:** `src/orchestration/task_board.py` — 54 fields (19 SQLite indexed, 35 JSON extra)

| Aspect | Status | Detail |
|--------|--------|--------|
| `assigned_to` | No validation | Accepts any string, no enum check |
| `agent_type` | No validation | Used only for `execution_mode` inference (manual vs pipeline) |
| `allowed_paths` | Stored, NOT enforced | Descriptive metadata only — no check on claim or complete |
| `blocked_paths` | Stored, NOT enforced | Same — advisory only |
| Branch detection | Works | `_detect_current_branch()` → `done_worktree` vs `done_main` |
| Closure protocol | Exists | `_validate_closure_proof()` + `run_closure_protocol()` — opt-in per task |
| Role/domain fields | DO NOT EXIST | No concept of agent role or domain on task |

**Hooks on lifecycle:**
- **Claim:** `_append_history("claimed")` + SocketIO `task_claimed` event
- **Complete:** `_append_history("closed")` + SocketIO `task_completed` + optional closure proof

**Key files:**
- `src/orchestration/task_board.py` (core, ~1700 lines)
- `src/mcp/tools/task_board_tools.py` (MCP handler)
- `src/api/routes/task_board_routes.py` (REST API)
- `tests/test_phase121_task_board.py`, `tests/test_phase136_task_board_claim_complete.py`

### 1.2 MCC Roles & Tiers (R2)

**5 pipeline roles** (defined in `model_presets.json` + `agent_pipeline.py`):
```
scout → architect → researcher → coder → verifier
```

**3 Dragon tiers** (+ Titan variants):
```
Bronze (0.3x) → Silver (1.0x, default) → Gold (2.5x) → Gold+GPT (5.0x)
```

**Tier selection:** `_tier_map` in model_presets.json maps complexity → preset:
```json
{"low": "dragon_bronze", "medium": "dragon_silver", "high": "dragon_gold"}
```

**MCC ≠ CUT callsigns.** Pipeline roles (scout/architect/coder/verifier) are internal to
Mycelium pipeline execution. CUT callsigns (Alpha/Beta/Gamma/Delta) are domain-based
agent assignments. They operate at different abstraction levels:

```
MCC Role (per-subtask)     CUT Callsign (per-session)
─────────────────────      ──────────────────────────
scout                      Alpha = Engine domain
architect                  Beta  = Media domain
researcher                 Gamma = UX domain
coder                      Delta = QA domain
verifier                   Commander = Architect
```

**Role mapping in orchestrator** (`orchestrator_with_elisya.py:1035`):
```python
role_map = {"PM": "pm", "Architect": "architect", "Dev": "coder",
            "QA": "qa", "Researcher": "researcher", "Hostess": "orchestrator"}
```

### 1.3 REFLEX & Guard System (R3)

**REFLEX = 4-layer reactive tool recommendation engine:**

| Layer | File | Purpose |
|-------|------|---------|
| Registry | `reflex_registry.py` | Tool catalog (`data/reflex/tool_catalog.json`) |
| Scorer | `reflex_scorer.py` | 8-signal weighted scoring in <5ms |
| CORTEX | `reflex_feedback.py` | Learning loop: `feedback_log.jsonl` (append-only, decay) |
| Emotions | `reflex_emotions.py` | Post-scoring modulation (curiosity/trust/caution) |

**8 Scorer signals** (Phase 187.3 weights):
1. Semantic match (0.22)
2. CAM surprise (0.12)
3. Feedback score (0.18)
4. ENGRAM preference (0.07)
5. STM relevance (0.15)
6. Phase match (0.18)
7. HOPE LOD match (0.05)
8. MGC cache heat (0.03)

**Protocol Guard** (`protocol_guard.py`) — 6 rules:
```
session_init_first, taskboard_before_work, task_before_code,
recon_before_code, read_before_edit, roadmap_before_tasks
```

**Guard** (`reflex_guard.py`) — 3 rule sources:
1. ENGRAM L1 Danger entries (hard blocks)
2. CORTEX failure history (≥10 calls, <15% success → warn)
3. Static rules (`data/reflex_guard_rules.json`)

**Critical gaps:**
- No `experience_report_required` rule
- No session end hook
- No auto-update of CLAUDE.md from REFLEX learnings
- CORTEX feedback stays in JSONL, never surfaces to agent instructions

### 1.4 Worktree ↔ Role Binding (R4)

**12 worktrees** (5 role-specific, 7 generic):

| Worktree | Branch | Callsign | Domain |
|----------|--------|----------|--------|
| cut-engine | claude/cut-engine | Alpha | Engine: store, hotkeys, playback |
| cut-media | claude/cut-media | Beta | Media: codecs, color, scopes |
| cut-ux | claude/cut-ux | Gamma | UX: panels, menus, layout |
| cut-qa | worktree-cut-qa | Delta | QA: E2E tests, TDD, compliance |
| pedantic-bell | claude/pedantic-bell | Commander | Coordination, merge, dispatch |

**File ownership** — explicit per-worktree CLAUDE.md boundaries:
- Alpha: `useTimelineInstanceStore.ts`, `useCutHotkeys.ts` (editing actions), `TimelineTrackView.tsx`
- Beta: `VideoScopesPanel.tsx`, `ColorCorrectionPanel.tsx`, `cut_codec_probe.py`, `cut_render_engine.py`
- Gamma: `MenuBar.tsx`, `DockviewLayout.tsx`, `VideoPreview.tsx` (UI layer), panels/*.tsx
- Delta: `e2e/*.spec.cjs`, `playwright.config.ts`, `tests/test_*.py`
- Shared zones: `useCutHotkeys.ts` (Alpha+Gamma), `DockviewLayout.tsx` (Gamma+Beta), `useCutEditorStore.ts` (Alpha+Gamma)

**Experience reports** — per-agent + consolidated:
```
docs/190_ph_CUT_WORKFLOW_ARCH/feedback/
├── EXPERIENCE_ALPHA_ENGINE_2026-03-22.md
├── EXPERIENCE_BETA_MEDIA_2026-03-22.md
├── EXPERIENCE_GAMMA_UX_2026-03-22.md
├── EXPERIENCE_DELTA1_QA_2026-03-22.md
├── EXPERIENCE_DELTA2_QA_2026-03-22.md
└── FEEDBACK_WAVE5_6_ALL_AGENTS_2026-03-22.md  ← consensus
```

Each report: What Worked → What Didn't → Insights → Bugs → Recommendations for Successor.

---

## 2. Architecture Design

### 2.1 Agent Registry (D1)

**File:** `data/templates/agent_registry.yaml`
**Loader:** `src/services/agent_registry.py`

```yaml
# Agent Registry — Single Source of Truth for CUT agent roles
version: "1.0"
project_id: "CUT"

roles:
  - callsign: "Alpha"
    domain: "engine"
    worktree: "cut-engine"
    branch: "claude/cut-engine"
    owned_paths:
      - "client/src/store/useTimelineInstanceStore.ts"
      - "client/src/store/useCutEditorStore.ts:timeline"   # field-level ownership
      - "client/src/hooks/useCutHotkeys.ts:editing"        # scope: editing actions
      - "client/src/components/cut/TimelineTrackView.tsx"
      - "client/src/components/cut/CutEditorLayoutV2.tsx:editing"
      - "client/src-tauri/"
      - "tests/test_*.py"
    blocked_paths:
      - "client/src/components/cut/MenuBar.tsx"            # Gamma
      - "client/src/components/cut/DockviewLayout.tsx"     # Gamma+Beta
      - "client/src/components/cut/panels/"                # Gamma
      - "e2e/"                                             # Delta
    predecessor_docs: "docs/190_ph_CUT_WORKFLOW_ARCH/feedback/EXPERIENCE_ALPHA_*.md"
    roadmap: "ROADMAP_A_ENGINE_DETAIL.md"

  - callsign: "Beta"
    domain: "media"
    worktree: "cut-media"
    branch: "claude/cut-media"
    owned_paths:
      - "client/src/components/cut/panels/VideoScopesPanel.tsx"
      - "client/src/components/cut/panels/ColorCorrectionPanel.tsx"
      - "client/src/components/cut/panels/LUTBrowserPanel.tsx"
      - "client/src/components/cut/TimelineDisplayControls.tsx"
      - "client/src/components/cut/EffectsPanel.tsx"
      - "client/src/components/cut/ColorWheel.tsx"
      - "src/services/cut_codec_probe.py"
      - "src/services/cut_render_engine.py"
      - "src/services/cut_effects_engine.py"
      - "src/services/cut_scope_renderer.py"
      - "src/services/cut_color_pipeline.py"
      - "src/services/cut_lut_manager.py"
      - "src/api/routes/cut_routes.py:color,scopes,lut,probe"
    blocked_paths:
      - "client/src/components/cut/MenuBar.tsx"
      - "e2e/"
    predecessor_docs: "docs/190_ph_CUT_WORKFLOW_ARCH/feedback/EXPERIENCE_BETA_*.md"

  - callsign: "Gamma"
    domain: "ux"
    worktree: "cut-ux"
    branch: "claude/cut-ux"
    owned_paths:
      - "client/src/components/cut/MenuBar.tsx"
      - "client/src/components/cut/DockviewLayout.tsx"
      - "client/src/components/cut/dockview-cut-theme.css"
      - "client/src/components/cut/VideoPreview.tsx:ui"
      - "client/src/components/cut/panels/*.tsx"
      - "client/src/components/cut/WorkspacePresets.tsx"
      - "client/src/hooks/useCutHotkeys.ts:panel_focus"
      - "client/src/store/useCutEditorStore.ts:ui"
    blocked_paths:
      - "src/services/cut_*.py"
      - "e2e/"
    predecessor_docs: "docs/190_ph_CUT_WORKFLOW_ARCH/feedback/EXPERIENCE_GAMMA_*.md"

  - callsign: "Delta"
    domain: "qa"
    worktree: "cut-qa"
    branch: "worktree-cut-qa"
    owned_paths:
      - "e2e/*.spec.cjs"
      - "e2e/playwright.config.ts"
      - "client/e2e/"
      - "tests/test_*.py"
    blocked_paths:
      - "client/src/components/"
      - "client/src/store/"
      - "src/services/"
    predecessor_docs: "docs/190_ph_CUT_WORKFLOW_ARCH/feedback/EXPERIENCE_DELTA*_*.md"

  - callsign: "Commander"
    domain: "architect"
    worktree: "pedantic-bell"
    branch: "claude/pedantic-bell"
    owned_paths:
      - "docs/"
      - "CLAUDE.md"
    blocked_paths:
      - "client/src/"                # Delegates to Alpha/Beta/Gamma
      - "src/services/"             # Delegates to Beta
    predecessor_docs: "docs/190_ph_CUT_WORKFLOW_ARCH/COMMANDER_ROLE_PROMPT.md"

# Shared files requiring coordination
shared_zones:
  - file: "client/src/hooks/useCutHotkeys.ts"
    owners: ["Alpha:editing", "Gamma:panel_focus"]
    protocol: "Declare scope in task description"
  - file: "client/src/components/cut/DockviewLayout.tsx"
    owners: ["Gamma:registry", "Beta:new_panels"]
    protocol: "Beta notifies Gamma of new panel names"
  - file: "client/src/store/useCutEditorStore.ts"
    owners: ["Alpha:timeline", "Gamma:ui"]
    protocol: "New fields: declare ownership via task"
  - file: "src/api/routes/cut_routes.py"
    owners: ["Beta"]
    protocol: "Consider splitting per-domain route files"
```

**Python loader interface:**
```python
@dataclass
class AgentRole:
    callsign: str           # "Alpha"
    domain: str             # "engine"
    worktree: str           # "cut-engine"
    branch: str             # "claude/cut-engine"
    owned_paths: list[str]
    blocked_paths: list[str]
    predecessor_docs: str   # glob pattern

class AgentRegistry:
    def get_role_by_callsign(self, callsign: str) -> AgentRole
    def get_role_by_branch(self, branch: str) -> AgentRole
    def get_role_by_worktree(self, worktree: str) -> AgentRole
    def validate_file_ownership(self, callsign: str, file_path: str) -> OwnershipResult
    def get_shared_zones(self) -> list[SharedZone]
```

### 2.2 Experience Lifecycle (D2)

```
┌─────────────────────────────────────────────────────────────┐
│                    EXPERIENCE LIFECYCLE                      │
│                                                             │
│  SESSION START                                              │
│    │                                                        │
│    ├── session_init()                                       │
│    │     ├── Load CLAUDE.md (role + predecessor advice)     │
│    │     ├── Check pending_experience_reports (prev session)│
│    │     └── Protocol Guard: session_init ✓                 │
│    │                                                        │
│    ├── task_board list + claim                              │
│    │     ├── Validate: agent role matches task domain       │
│    │     └── Protocol Guard: task_before_code ✓             │
│    │                                                        │
│    ├── WORK (edit files, run tests)                         │
│    │     └── REFLEX: tool recommendations + feedback        │
│    │                                                        │
│    ├── task_board complete                                  │
│    │     ├── Validate: committed files ⊆ allowed_paths     │
│    │     └── Closure protocol (if required)                 │
│    │                                                        │
│  SESSION END                                                │
│    │                                                        │
│    ├── GUARD: experience_report_required                    │
│    │     ├── Warn if no report submitted                    │
│    │     └── Block session_end (soft: warn, not hard block) │
│    │                                                        │
│    ├── submit_experience_report()  ← NEW MCP TOOL          │
│    │     ├── reflex_report (auto from REFLEX)               │
│    │     ├── lessons_learned (agent-written)                │
│    │     ├── recommendations (for successor)                │
│    │     └── Store → data/experience_reports/<session>.json │
│    │                                                        │
│  NEXT SESSION                                               │
│    │                                                        │
│    └── CLAUDE.md Generator (D3)                             │
│          ├── Read agent_registry.yaml                       │
│          ├── Read latest experience reports                 │
│          ├── Read feedback consensus doc                    │
│          ├── Read task board state                          │
│          └── Generate → .claude/worktrees/<wt>/CLAUDE.md    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Protocol Guard extension:**
```python
# New rule in protocol_guard.py
RULES = {
    ...existing 6 rules...,
    "experience_report_required": {
        "severity": "warn",          # soft enforcement first
        "check": "_check_experience_report",
        "triggers_on": ["session_end", "task_complete"],
        "message": "Experience report not submitted — lessons will be lost",
        "suggestion": "Call submit_experience_report() before ending session"
    }
}
```

**Experience Report schema:**
```json
{
  "session_id": "uuid",
  "agent_callsign": "Alpha",
  "domain": "engine",
  "branch": "claude/cut-engine",
  "timestamp": "2026-03-22T05:00:00Z",
  "tasks_completed": ["tb_xxx", "tb_yyy"],
  "reflex_report": {
    "total_entries": 42,
    "success_rate": 0.85,
    "top_tools": ["vetka_edit_file", "vetka_search_semantic"]
  },
  "lessons_learned": [
    "Three-Point Edit requires I→O→, sequence, not separate operations",
    "useCutHotkeys scope guard prevents cross-domain key conflicts"
  ],
  "recommendations": [
    "Read FCP7 PDF chapters 3-5 before touching timeline editing",
    "Always run Python reference tests before TypeScript implementation"
  ],
  "bugs_found": [
    {"file": "DockviewLayout.tsx", "description": "Panel re-registration on hot reload"}
  ],
  "files_touched": ["useTimelineInstanceStore.ts", "TimelineTrackView.tsx"],
  "metrics": {
    "commits": 5,
    "tests_added": 12,
    "tests_passing": 43
  }
}
```

### 2.3 CLAUDE.md Generator (D3)

**Input sources:**
1. `agent_registry.yaml` → role definition, owned_paths, blocked_paths
2. `data/experience_reports/*.json` → latest 3 reports per role (sorted by date)
3. `docs/.../feedback/FEEDBACK_WAVE*_ALL_AGENTS_*.md` → latest consensus doc
4. Task board API → current pending/claimed tasks for this role

**Output:** `.claude/worktrees/<worktree>/CLAUDE.md`

**Template structure (Jinja2):**
```
# Agent {{ callsign }} — {{ domain | title }} Domain
**Role:** {{ role_title }} | **Callsign:** {{ callsign }} | **Branch:** {{ branch }}

## Your First Task in 3 Steps
1. mcp__vetka__vetka_session_init
2. mcp__vetka__vetka_task_board action=list project_id=cut filter_status=pending
3. Claim → Do work → action=complete task_id=<id> branch={{ branch }}

## Identity
{{ role_description }}

## Owned Files (ONLY touch these)
{% for path in owned_paths %}
- {{ path }}
{% endfor %}

## DO NOT Touch
{% for path in blocked_paths %}
- {{ path }}
{% endfor %}

## Predecessor Advice
{% for lesson in predecessor_lessons %}
- {{ lesson }}
{% endfor %}

## Current Tasks
{% for task in pending_tasks %}
- [{{ task.id }}] {{ task.title }} ({{ task.priority }})
{% endfor %}

## Key Docs
{% for doc in key_docs %}
- {{ doc }}
{% endfor %}
```

**Invocation:**
```bash
python src/tools/generate_claude_md.py --role Alpha --dry-run
python src/tools/generate_claude_md.py --all
```

### 2.4 Task Board Extensions (D4)

**New fields on task:**
```python
# In task_board.py add_task() / INDEXED_COLUMNS:
"role": str,        # Agent callsign: "Alpha", "Beta", "Gamma", "Delta"
"domain": str,      # Domain: "engine", "media", "ux", "qa", "architect"
```

**Validation on claim (warn mode):**
```python
def claim_task(self, task_id, agent_name, agent_type, **kwargs):
    task = self.get_task(task_id)
    agent_role = self.registry.get_role_by_branch(self._detect_current_branch())

    # Domain match check (WARN, not BLOCK)
    if task.get("domain") and agent_role and task["domain"] != agent_role.domain:
        logger.warning(
            f"[TaskBoard] Domain mismatch: agent {agent_role.callsign} ({agent_role.domain}) "
            f"claiming task in domain '{task['domain']}'"
        )
        # Still allow claim — warn only for Phase 1

    # Set role from registry if not explicit
    if not task.get("role") and agent_role:
        task["role"] = agent_role.callsign

    ...existing claim logic...
```

**Validation on complete (warn mode):**
```python
def complete_task(self, task_id, **kwargs):
    task = self.get_task(task_id)
    agent_role = self.registry.get_role_by_callsign(task.get("role"))

    # File ownership check (WARN, not BLOCK)
    if agent_role and kwargs.get("committed_files"):
        for f in kwargs["committed_files"]:
            result = self.registry.validate_file_ownership(agent_role.callsign, f)
            if result.violation:
                logger.warning(f"[TaskBoard] File ownership violation: {f} not in {agent_role.callsign} owned_paths")

    ...existing complete logic...
```

**Backward compatibility:** Tasks without `role`/`domain` skip all validation.

---

## 3. Implementation Order

```
Phase 1 (DONE):
  ✅ R1-R4 Recon — architecture gaps identified
  ✅ Architecture doc (this document)
  ✅ Phase 2 tasks created on board

Phase 2 (NEXT):
  D1: agent_registry.yaml + loader    → tb_1774147698_1 (P2, medium)
  D2: Experience lifecycle guards      → tb_1774147705_2 (P2, high)

Phase 3 (AFTER D1):
  D3: CLAUDE.md generator             → tb_1774147714_3 (P3, medium, depends D1)
  D4: Task board role/domain fields   → tb_1774147722_4 (P3, high, depends D1)

Phase 4 (FUTURE):
  Mycelium pipeline integration (MCC role → CUT callsign mapping)
  Auto-promotion/demotion from REFLEX trajectory
  Dashboard: per-agent REFLEX history visualization
```

---

## 4. Constraints

1. **Task board is LIVE** — 94+ pending tasks, multiple agents. All changes backward-compatible.
2. **Warn-first enforcement** — D4 starts in warn mode. Hard blocking only after validation in production.
3. **No hardcodes** — all role/domain definitions in `agent_registry.yaml`, not in code.
4. **Experience ≠ code** — reports stay in `docs/feedback/` and `data/experience_reports/`, not in source.
5. **MCC compatibility** — CUT callsigns are orthogonal to MCC pipeline roles. Don't conflate them.
6. **Test everything** — existing `test_phase121` and `test_phase136` must pass after D4 changes.

---

*"The best agent is one who already knows what their predecessor learned."*
