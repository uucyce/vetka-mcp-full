# Phase 153: Mycelium Matryoshka — Roadmap

## Strategy

Не переписываем с нуля. Консервируем старую Mycelium (git tag `v0.152-legacy`).
Рефакторим MCC поэтапно, сохраняя все рабочие компоненты.
6 волн, каждая — самостоятельный deliverable. После каждой волны система работает.

---

## Pre-requisite: Conservation

**Перед началом Phase 153:**

```bash
git tag v0.152-legacy   # зафиксировать текущее состояние
git checkout -b phase-153-matryoshka
```

Это позволяет вернуться к старой Mycelium в любой момент.

---

## Wave 0: Cleanup (0.5 day)
**Goal**: Убрать подтверждённый мёртвый код.

### Import Audit Results (Phase 153.0):

Аудит выявил что большинство файлов из первоначального списка АКТИВНО используются:

| File | Lines | Status | Import Sites |
|------|-------|--------|-------------|
| `orchestrator_with_elisya.py` | 2861 | **KEEP** | user_message_handler, workflow_tools, dependency_check (10 imports) |
| `agent_orchestrator.py` | 264 | **KEEP** | dependency_check fallback cascade |
| `agent_orchestrator_parallel.py` | 388 | **KEEP** | dependency_check fallback cascade |
| `langgraph_nodes.py` | 1120 | **KEEP** | langgraph_builder, 2 test files (Phase 60/75.5) |
| `simpo_training_loop.py` | 471 | **KEEP** | components_init, dependency_check (Phase 9.0 Student System) |
| `langgraph_builder.py` | 425 | ✅ **DELETED** | 0 imports |
| `autogen_extension.py` | 284 | ✅ **DELETED** | 0 imports |

### Tasks completed:

| # | Task | Files | Lines removed |
|---|------|-------|---------------|
| 0.1 | ✅ Conservation tag | `git tag v0.152-legacy` | 0 |
| 0.2 | ✅ Delete langgraph_builder.py | `src/orchestration/langgraph_builder.py` | -425 |
| 0.3 | ✅ Delete autogen_extension.py | `src/orchestration/autogen_extension.py` | -284 |
| 0.4 | ✅ Verify no imports break | All key modules import cleanly | 0 |

**Total removed**: 709 lines (not 5,813 as initially estimated).
**Reason**: The other files are actively imported in production code paths.
**Future cleanup**: orchestrator_with_elisya.py can be deprecated AFTER its callers
(user_message_handler, workflow_tools) are migrated to agent_pipeline.py. NOT in Phase 153.

---

## Wave 1: Persistence + Project Config (2 days)
**Goal**: Система запоминает проект между рестартами.

### Backend:

| # | Task | File | Lines |
|---|------|------|-------|
| 1.1 | ProjectConfig model | `src/services/project_config.py` (NEW) | ~100 |
| 1.2 | MCC init endpoint | `src/api/routes/mcc_routes.py` (NEW) | ~120 |
| 1.3 | Session state save/load | `src/api/routes/mcc_routes.py` | (in 1.2) |
| 1.4 | Wire into main.py | `main.py` | ~10 |

**project_config.py**:
```python
@dataclass
class ProjectConfig:
    project_id: str
    source_type: str          # "local" | "git"
    source_path: str          # абсолютный путь или git URL
    sandbox_path: str         # /data/playgrounds/{project_id}/
    quota_gb: int = 10
    created_at: str = ""
    qdrant_collection: str = ""

    @classmethod
    def load(cls) -> Optional['ProjectConfig']:
        """Load from data/project_config.json"""

    def save(self):
        """Save to data/project_config.json"""
```

**mcc_routes.py endpoints**:
```
GET  /api/mcc/init     -> { project_config, session_state, has_project }
POST /api/mcc/state    -> save session_state.json (level, selectedTask, etc)
```

### Frontend:

| # | Task | File | Lines |
|---|------|------|-------|
| 1.5 | useMCCStore: add persistence actions | `useMCCStore.ts` | ~40 |
| 1.6 | MCC: load state on mount | `MyceliumCommandCenter.tsx` | ~20 |
| 1.7 | MCC: save state on navigation | `MyceliumCommandCenter.tsx` | ~15 |

### Tests:
```
test_phase153_wave1.py:
  - test_project_config_save_load
  - test_mcc_init_no_project (returns has_project=false)
  - test_mcc_init_with_project (returns config + state)
  - test_session_state_persist
  - test_session_state_restore_on_mount
```

**Deliverable**: Server restart -> MCC resumes where user left off.

---

## Wave 2: Playground v2 (2 days)
**Goal**: 1 playground per project. Full copy. Quota. Delete.

### Backend:

| # | Task | File | Lines |
|---|------|------|-------|
| 2.1 | Refactor PlaygroundManager | `playground_manager.py` | ~200 (rewrite create/delete) |
| 2.2 | Add quota check | `playground_manager.py` | ~30 |
| 2.3 | New REST endpoints | `src/api/routes/playground_routes.py` (NEW) | ~150 |
| 2.4 | Support non-git projects | `playground_manager.py` | ~50 (cp -r fallback) |
| 2.5a | Source type abstraction | `playground_manager.py` | ~40 (strategy pattern) |

**Source types** (Phase 153 supports `local` + `git`; `remote` documented for Phase 154):
```python
COPY_STRATEGIES = {
    "local": lambda src, dst: shutil.copytree(src, dst),
    "git": lambda src, dst: subprocess.run(["git", "clone", "--depth=1", src, dst]),
    # Phase 154: "remote": lambda src, dst: subprocess.run(["rsync", "-az", src, dst])
}
```

**Refactored PlaygroundManager**:
```python
class PlaygroundManager:
    def create(self, config: ProjectConfig) -> str:
        """
        1. Select copy strategy by config.source_type
        2. If source is git: git clone --depth=1
        3. If source is local: shutil.copytree()
        4. Set sandbox_path in config
        5. Check quota
        6. Return sandbox_path
        """

    def delete(self) -> bool:
        """Remove sandbox dir. Config stays (can recreate)."""

    def check_quota(self) -> dict:
        """Return {used_gb, quota_gb, percent, warning}"""

    def get_status(self) -> dict:
        """Return {exists, path, used_gb, quota_gb, created_at}"""
```

**REST endpoints**:
```
POST   /api/playground/init     -> create sandbox from project_config
DELETE /api/playground           -> delete sandbox (recreatable)
GET    /api/playground/status    -> {exists, used_gb, quota_gb}
```

**Error handling** (playground creation):
```python
try:
    strategy = COPY_STRATEGIES[config.source_type]
    strategy(config.source_path, sandbox_path)
except FileNotFoundError:
    return {"error": "source_not_found", "message": f"Path not found: {config.source_path}"}
except PermissionError:
    return {"error": "permission_denied", "message": "No read access to source"}
except subprocess.CalledProcessError:
    return {"error": "git_clone_failed", "message": "Git clone failed (network/auth)"}
except OSError as e:
    if "No space left" in str(e):
        return {"error": "disk_full", "message": f"Quota exceeded ({config.sandbox.quota_gb}GB)"}
    raise
```

### Frontend:

| # | Task | File | Lines |
|---|------|------|-------|
| 2.5 | Simplify SandboxDropdown | `SandboxDropdown.tsx` | Rewrite: single button |
| 2.6 | Playground status in right panel | `MCCDetailPanel.tsx` | ~30 |

**New SandboxDropdown** (simplified):
```
Playground exists:  [Sandbox ✓ 2.1/10GB]  click -> popup: Delete / Recreate / Open folder
Playground absent:  [Create Sandbox]       click -> POST /api/playground/init
```

### Tests:
```
test_phase153_wave2.py:
  - test_create_from_local (cp -r)
  - test_create_from_git (clone)
  - test_quota_check
  - test_quota_warning_at_80_percent
  - test_delete_and_recreate
  - test_agents_boundary (cwd locked to sandbox)
  - test_single_per_project (create twice -> error)
```

**Deliverable**: One sandbox per project. Works without git. Quota enforced.

---

## Wave 3: Onboarding (First Open) (1 day)
**Goal**: Новый пользователь видит приветствие -> указывает проект -> всё настраивается.

### Frontend:

| # | Task | File | Lines |
|---|------|------|-------|
| 3.1 | OnboardingModal component | `OnboardingModal.tsx` (NEW) | ~180 |
| 3.2 | MCC integration | `MyceliumCommandCenter.tsx` | ~15 |
| 3.3 | Remove old OnboardingOverlay | `OnboardingOverlay.tsx` | DELETE |

**OnboardingModal**:
```tsx
// Shows when /api/mcc/init returns has_project=false
// Step 1: Choose source (local path input + browse OR git URL)
// Step 2: "Scanning..." progress bar (POST /api/project/init)
// Step 3: "Roadmap ready!" -> close modal, show Roadmap DAG

function OnboardingModal({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState<'source' | 'scanning' | 'ready'>('source');
  const [sourcePath, setSourcePath] = useState('');
  const [sourceType, setSourceType] = useState<'local' | 'git'>('local');
  // ...
}
```

### Backend:

| # | Task | File | Lines |
|---|------|------|-------|
| 3.4 | Project init endpoint | `mcc_routes.py` | ~80 |

**POST /api/project/init** flow:
```
1. Receive { source_type, source_path }
2. Validate path exists (or git URL reachable)
3. Create ProjectConfig, save
4. Create Playground (copy project)
5. Index in Qdrant (watcher/index-project)
6. Generate Roadmap DAG (Wave 4)
7. Return { success, project_id, sandbox_path }
```

### Tests:
```
test_phase153_wave3.py:
  - test_onboarding_shows_when_no_config
  - test_project_init_local
  - test_project_init_git
  - test_onboarding_hides_after_init
```

**Deliverable**: First open -> guided setup -> project ready.

---

## Wave 4: Roadmap DAG + Architect Intelligence (3 days)
**Goal**: Architect анализирует проект и генерит карту. DAG-in-DAG навигация. BMAD bridge.

### Backend:

| # | Task | File | Lines |
|---|------|------|-------|
| 4.1 | Roadmap generator | `src/services/roadmap_generator.py` (NEW) | ~300 |
| 4.2 | Roadmap REST API | `mcc_routes.py` | ~60 |
| 4.3 | Architect analyze prompt | `pipeline_prompts.json` | ~30 |
| 4.8 | BMAD/DAGExecutor bridge | `mcc_routes.py` + `roadmap_generator.py` | ~60 |
| 4.9 | Workflow Template Library | `data/templates/workflows/` (6 JSON files) | ~400 |
| 4.10 | Architect Prefetch Pipeline | `src/services/architect_prefetch.py` (NEW) | ~200 |
| 4.11 | Architect Workflow Selector | `src/services/architect_captain.py` | ~80 |

**roadmap_generator.py**:
```python
class RoadmapGenerator:
    async def analyze_project(self, sandbox_path: str) -> RoadmapDAG:
        """
        1. Scan directory structure (modules, packages, key files)
        2. Read key files (package.json, Cargo.toml, setup.py, etc)
        3. Call Architect LLM: "Analyze this project structure. Generate a DAG..."
        4. Parse LLM response into RoadmapDAG (nodes + edges)
        5. Save to data/roadmap_dag.json
        """

    async def update_roadmap(self, completed_task_id: str) -> RoadmapDAG:
        """After task completion, Architect updates roadmap."""
```

**Architect prompt addition** (pipeline_prompts.json):
```json
{
  "architect_roadmap": {
    "system": "You are a project analyst. Given a project's file structure and key config files, generate a hierarchical roadmap DAG. Each node is a module/feature/phase. Edges show dependencies. Root = core/backend. Leaves = frontend/new features. Output JSON: {nodes: [{id, label, status, layer}], edges: [{source, target}]}",
    "user_template": "Project structure:\n{tree}\n\nKey files:\n{key_files}\n\nGenerate roadmap DAG."
  }
}
```

### Frontend:

| # | Task | File | Lines |
|---|------|------|-------|
| 4.4 | MatryoshkaNavigator | `MatryoshkaNavigator.tsx` (NEW) | ~120 |
| 4.5 | RoadmapDAG view | Extend `DAGView.tsx` | ~80 |
| 4.6 | Zoom-level state in useMCCStore | `useMCCStore.ts` | ~30 |
| 4.7 | Breadcrumb bar | `MyceliumCommandCenter.tsx` | ~40 |

**MatryoshkaNavigator** — state machine:
```tsx
type NavLevel = 'roadmap' | 'tasks' | 'workflow' | 'running' | 'results';

interface NavState {
  level: NavLevel;
  roadmapNodeId?: string;   // selected module in roadmap
  taskId?: string;           // selected task
  history: NavLevel[];       // for back navigation
}

function MatryoshkaNavigator() {
  const [nav, setNav] = useState<NavState>({ level: 'roadmap', history: [] });

  const drillDown = (nextLevel: NavLevel, context: Record<string,string>) => {
    setNav(prev => ({
      level: nextLevel,
      ...context,
      history: [...prev.history, prev.level],
    }));
    // POST /api/mcc/state to persist
  };

  const goBack = () => {
    setNav(prev => {
      const history = [...prev.history];
      const prevLevel = history.pop() || 'roadmap';
      return { ...prev, level: prevLevel, history };
    });
  };
}
```

**DAGView.tsx extension**:
```tsx
// Add prop: dagLevel: 'roadmap' | 'tasks' | 'workflow'
// roadmap: fetch from /api/roadmap, use RoadmapNode type
// tasks: fetch from /api/roadmap/{nodeId}/tasks, use TaskNode type
// workflow: existing behavior (agent DAG)
```

### Tests:
```
test_phase153_wave4.py:
  - test_roadmap_generate_from_project
  - test_roadmap_has_valid_dag_structure
  - test_architect_prompt_includes_tree
  - test_navigation_drill_down
  - test_navigation_back
  - test_navigation_state_persists
  - test_workflow_templates_valid_dag (all 6 templates load + validate)
  - test_architect_selects_quick_fix_for_bug
  - test_architect_selects_research_first_for_unknown_lib
  - test_prefetch_returns_files_and_docs
  - test_prefetch_injects_into_pipeline_context
  - test_one_button_chain (execute → prefetch → select → dispatch → stream)
```

### Workflow Template Library — "Дебюты Гроссмейстера" (4.9):

Architect не строит workflow с нуля. Он выбирает из библиотеки проверенных шаблонов:

```
data/templates/workflows/
  ├── bmad_default.json      # Полный цикл (11 nodes) — уже есть как bmad_workflow.json
  ├── quick_fix.json         # Scout → Coder → Verify (4 nodes)
  ├── research_first.json    # Researcher → Architect → Coder → Verify (5 nodes)
  ├── refactor.json          # Scout(deep) → Architect → Coder(parallel) → Verify (6 nodes)
  ├── test_only.json         # Scout → Coder(test-mode) → Verify (4 nodes)
  └── docs_update.json       # Scout → Coder(docs-mode) (3 nodes)
```

Каждый шаблон — валидный DAG JSON (формат bmad_workflow.json).
Architect выбирает шаблон автоматически, user может переопределить.

### Architect Prefetch Pipeline (4.10):

Одна кнопка [Execute] запускает ЦЕПОЧКУ подготовки ДО основного pipeline:
```python
class ArchitectPrefetch:
    async def prepare(self, task: dict, config: ProjectConfig) -> PrefetchContext:
        """
        1. prefetch_files:   Qdrant semantic search по task description → top 5 файлов
        2. prefetch_markers: ripgrep MARKER_* в найденных файлах
        3. prefetch_docs:    Context7 library docs (если framework в стеке)
        4. prefetch_history: pipeline_history.json → как решали похожие задачи
        5. select_workflow:  выбрать шаблон из библиотеки по типу задачи
        6. select_team:      подобрать пресет по сложности + истории
        """
```

Весь контекст подаётся Scout/Architect/Coder — они не тратят FC turns на поиск.

### Architect Workflow Selector (4.11):

```python
# В architect_captain.py — метод select_workflow
async def select_workflow(self, task: dict, history: list) -> str:
    """
    Логика выбора:
    - task.type == "fix" и complexity < 3 → quick_fix.json
    - task.type == "build" и unknown_libs → research_first.json
    - task.type == "refactor" → refactor.json
    - task.type == "test" → test_only.json
    - default или complexity > 5 → bmad_default.json

    CAM/ARC override: если похожая задача решалась другим шаблоном с success → взять тот
    """
```

### BMAD/DAGExecutor Bridge (4.8):

Connect Matryoshka levels to existing execution engine:
```python
# In mcc_routes.py — dispatch task from Roadmap navigation
@router.post("/api/roadmap/{module_id}/dispatch")
async def dispatch_module_task(module_id: str, task_id: str):
    """
    Level 1 (Roadmap) -> Level 2 (Task) -> Level 3 (Workflow):
    1. Get task from TaskBoard by task_id
    2. Get BMAD template (or task-specific workflow if exists)
    3. Call agent_pipeline.execute(task, preset, bmad_template=template)
    4. Pipeline internally uses DAGExecutor for Level 3 execution
    """
```

This bridges the 3 existing systems:
- `roadmap_dag.json` (NEW) -> navigation map
- `task_board.py` (EXISTS) -> task queue
- `dag_executor.py` + `agent_pipeline.py` (EXISTS) -> execution

**Deliverable**: Project map generated by Architect. Click-through navigation. BMAD execution wired.

---

## Wave 5: Rails UX — 3 Actions Max (2 days)
**Goal**: Каждый уровень показывает <=3 действий. WorkflowToolbar -> popup.

### Frontend:

| # | Task | File | Lines |
|---|------|------|-------|
| 5.1 | RailsActionBar component | `RailsActionBar.tsx` (NEW) | ~100 |
| 5.2 | Refactor WorkflowToolbar | `WorkflowToolbar.tsx` | ~200 (slim down) |
| 5.3 | Context-aware right panel | `MCCDetailPanel.tsx` | ~50 |
| 5.4 | Context-aware left panel | `MCCTaskList.tsx` | ~40 |
| 5.5 | Keyboard shortcuts | `useKeyboardShortcuts.ts` (NEW) | ~80 |
| 5.6 | Error toasts + fallback UI | `ErrorBoundary.tsx` / `useToast.ts` | ~60 |

**RailsActionBar** — bottom bar, max 3 buttons:
```tsx
// Replaces WorkflowToolbar for non-edit scenarios.
// Shows different actions per navigation level.

const LEVEL_ACTIONS: Record<NavLevel, ActionDef[]> = {
  roadmap: [
    { label: 'Drill', icon: '▶', action: 'drillNode' },
    { label: 'Architect', icon: '💬', action: 'openChat' },
    { label: 'Settings', icon: '⚙', action: 'openSettings' },
  ],
  tasks: [
    { label: 'Open Task', icon: '▶', action: 'drillTask' },
    { label: 'Accept Plan', icon: '✓', action: 'acceptPlan' },
    { label: 'Back', icon: '←', action: 'goBack' },
  ],
  workflow: [
    { label: 'Execute', icon: '▶', action: 'execute' },
    { label: 'Edit Team', icon: '✏', action: 'editTeam' },
    { label: 'Back', icon: '←', action: 'goBack' },
  ],
  running: [
    { label: 'Stop', icon: '⏹', action: 'stop' },
    { label: 'View Stream', icon: '📺', action: 'expandStream' },
    { label: 'Back', icon: '←', action: 'goBack' },
  ],
  results: [
    { label: 'Apply', icon: '✓', action: 'apply' },
    { label: 'Reject', icon: '✕', action: 'reject' },
    { label: 'Back', icon: '←', action: 'goBack' },
  ],
};
```

**WorkflowToolbar refactor**:
- Edit mode: stays as-is (11 buttons needed for workflow editing)
- Non-edit: replaced by RailsActionBar
- Validate/Generate/Import/Export: moved to NodePicker-style popup
  (accessible via "⚙ Settings" action or right-click context menu)

**Left panel (MCCTaskList) context-awareness**:
```
roadmap level: show module list (from roadmap nodes)
tasks level: show tasks of selected module
workflow level: show subtasks of selected task
running level: show progress + active agents
```

**Right panel (MCCDetailPanel) context-awareness**:
```
roadmap level: overview stats + architect chat compact
tasks level: task info + architect chat compact
workflow level: workflow detail + team info
running level: live stream + progress
results level: code diff + apply/reject
```

**Keyboard shortcuts** (5.5):
```tsx
// useKeyboardShortcuts.ts — context-aware hotkeys
// Uses navLevel from useMCCStore to determine which actions are available

const SHORTCUTS: Record<NavLevel, Record<string, () => void>> = {
  roadmap: { Enter: drillNode, 'c': openChat, 's': openSettings },
  tasks:   { Enter: drillTask, 'a': acceptPlan, Escape: goBack },
  workflow: { Enter: execute, 'e': editTeam, Escape: goBack },
  running: { ' ': stop, 'v': viewStream, Escape: goBack },
  results: { Enter: apply, 'r': reject, Escape: goBack },
};

// Global: Escape = back, F = fullscreen toggle, ? = shortcuts overlay
```

**Error toasts** (5.6):
```tsx
// Lightweight toast system for LLM/playground/pipeline errors
// Uses existing useSocket events: pipeline_activity, task_board_updated
// Toast types: info (blue), warning (amber), error (red), success (green)
// Auto-dismiss: 5s for info/success, sticky for errors
// Fallback UI: if Architect LLM fails -> show "Manual mode" option in chat
```

### Tests:
```
test_phase153_wave5.py:
  - test_rails_action_bar_max_3
  - test_level_actions_complete (every level has actions)
  - test_toolbar_hidden_in_non_edit
  - test_popup_has_validate_generate_import_export
  - test_keyboard_shortcuts_per_level
  - test_escape_goes_back
  - test_error_toast_on_llm_failure
```

**Deliverable**: Clean UX. Max 3 buttons. Context-aware panels. Keyboard shortcuts. Error feedback.

---

## Wave 6: Architect as Captain (2 days)
**Goal**: Architect предлагает следующие шаги. Пользователь подтверждает.

### Backend:

| # | Task | File | Lines |
|---|------|------|-------|
| 6.1 | Architect recommendation engine | `src/services/architect_captain.py` (NEW) | ~200 |
| 6.2 | Auto-recommend on load | `mcc_routes.py` | ~30 |
| 6.3 | Accept/reject recommendation | `mcc_routes.py` | ~40 |

**architect_captain.py**:
```python
class ArchitectCaptain:
    async def recommend_next(self, roadmap: RoadmapDAG, tasks: list) -> Recommendation:
        """
        1. Look at roadmap: which modules done, which pending
        2. Look at tasks: completed, failed, pending
        3. Call Architect LLM: "Given project state, what's the best next task?"
        4. Return: {task_title, description, module, priority, team_preset, reason}
        """

    async def create_tasks_for_module(self, module_id: str) -> list[Task]:
        """Architect breaks module into tasks with dependencies."""

    async def review_and_update(self, completed_task_id: str) -> str:
        """After task done, Architect reviews and updates roadmap."""
```

### Frontend:

| # | Task | File | Lines |
|---|------|------|-------|
| 6.4 | Architect recommendation in chat | `ArchitectChat.tsx` | ~40 |
| 6.5 | One-click accept | `ArchitectChat.tsx` | ~20 |
| 6.6 | Auto-load recommendation on mount | `MyceliumCommandCenter.tsx` | ~15 |

**Flow**:
```
MCC loads -> GET /api/mcc/init (includes recommendation)
  -> Architect chat shows: "Рекомендую: [task]. [reason]. Создать?"
  -> User clicks [Accept] or types alternative
  -> POST /api/architect/accept -> tasks created, roadmap updated
  -> Navigation drills to new task
```

### Tests:
```
test_phase153_wave6.py:
  - test_architect_recommends_on_load
  - test_accept_creates_task
  - test_reject_offers_alternative
  - test_roadmap_updates_after_completion
```

**Deliverable**: Architect drives. User confirms. System runs.

---

## Wave 7: E2E Tests + Polish (1 day)
**Goal**: Playwright E2E tests for critical user flows. Polish loading states.

### Tasks:

| # | Task | File | Lines |
|---|------|------|-------|
| 7.1 | Playwright setup | `e2e/playwright.config.ts` (NEW) | ~30 |
| 7.2 | Onboarding flow test | `e2e/onboarding.spec.ts` (NEW) | ~60 |
| 7.3 | Navigation drill-down test | `e2e/navigation.spec.ts` (NEW) | ~80 |
| 7.4 | Pipeline execution test | `e2e/pipeline.spec.ts` (NEW) | ~60 |
| 7.5 | Loading states + skeleton UI | various components | ~40 |

**E2E test scenarios**:
```
1. Onboarding: open app -> no config -> modal shows -> enter path -> scan -> roadmap appears
2. Navigation: roadmap -> click module -> tasks list -> dbl-click task -> workflow DAG
3. Back navigation: workflow -> Esc -> tasks -> Esc -> roadmap
4. Execute: select task -> execute -> running view -> results
5. Persistence: navigate to L2 -> reload page -> still at L2
```

**Deliverable**: Critical paths covered by E2E tests. Loading states for all async operations.

---

## Summary Timeline

| Wave | Name | Days | Dependencies | Deliverable |
|------|------|------|-------------|-------------|
| 0 | Cleanup | 0.5 | None | -709 verified dead lines |
| 1 | Persistence | 2 | Wave 0 | Server restart resumes state |
| 2 | Playground v2 | 2 | Wave 1 | Single sandbox, quota, delete |
| 3 | Onboarding | 1 | Wave 1, 2 | First open guided setup |
| 4 | Roadmap DAG + BMAD + Templates | 4 | Wave 1, 3 | Project map + workflow library + prefetch + bridge |
| 5 | Rails UX + Shortcuts | 2 | Wave 4 | <=3 actions, keyboards, error toasts |
| 6 | Architect Captain | 2 | Wave 4, 5 | Auto-recommend, user confirms |
| 7 | E2E Tests + Polish | 1 | Wave 6 | Playwright tests, loading states |
| **Total** | | **14.5 days** | | **Full Matryoshka MCC** |

---

## Execution: Who Does What

| Agent | Waves | Strengths |
|-------|-------|-----------|
| **Opus** (Claude Code) | 0, 1, 4 (backend + BMAD bridge), 6 (backend) | Architecture, backend, persistence |
| **Codex** | 2, 3, 5 (Rails + shortcuts), 7 (E2E tests) | Frontend components, playground refactor, tests |
| **Dragon Silver** | 4 (roadmap generator) | Code generation for new files |
| **Grok** | Research per wave | Deep analysis, architecture review |

---

## Research Gaps (Grok answers ✅)

All 6 research gaps answered by Grok. Key findings:

### R1: React Flow zoom + nested sub-graph ✅
**Answer**: Use `useReactFlow().setViewport({ duration: 300 })` for animated transitions.
No GSAP needed — React Flow handles it natively. For nested DAG: swap node/edge data,
call `fitView()` after data change. Sub-flow pattern: same `<ReactFlow>` component,
different data source per level.

### R2: Zustand persist + server sync ✅
**Answer**: Custom `createJSONStorage()` with async getItem/setItem to server API.
`localStorage` as offline fallback. Debounce setItem (500ms) to avoid spamming server.
Pattern: `persist(store, { name: 'mcc-state', storage: serverStorage })`.

### R3: shutil.copytree vs rsync ✅
**Answer**: rsync 2-5x faster for large projects (10GB+), but Unix-only.
`shutil.copytree()` works everywhere, good for <5GB.
**Decision**: Use `shutil.copytree()` in Phase 153 (cross-platform).
Add rsync as optional optimization in Phase 154.

### R4: Tauri file dialog ✅
**Answer**: `import { open } from '@tauri-apps/api/dialog'; const path = await open({ directory: true });`
Fallback for non-Tauri: `<input type="file" webkitdirectory>`.
Always check `window.__TAURI__` before calling Tauri APIs.

### R5: LLM project analysis prompts ✅
**Answer**: Few-shot examples in system prompt. Send: tree output (depth 3) + key config files
(package.json/Cargo.toml/setup.py). Strict JSON output format with schema validation.
Post-LLM: validate nodes array, edges array, check all edge references are valid node IDs.

### R6: ComfyUI/n8n action-bar UX ✅
**Answer**: ComfyUI uses context menu (right-click). n8n uses floating bar that appears
on node selection. Both hide extra actions behind secondary menus.
**Decision**: Floating RailsActionBar at bottom of center DAG column.
Extra actions (validate, generate, import, export) in NodePicker-style popup (⚙ Settings).

---

## Success Criteria

Phase 153 is DONE when:

1. New user opens Mycelium -> sees "Welcome" -> picks project -> sees Roadmap DAG
2. Architect recommends first task -> user confirms -> pipeline runs
3. Results applied to playground -> roadmap updates
4. Server restarts -> user sees exact state where they left off
5. Playground: single per project, deletable, quota shown
6. No screen has more than 3 action buttons
7. Every panel has compact <-> fullscreen toggle
8. All existing analytics/stats/balance features preserved
9. 0 dead code from old systems
10. All tests pass (existing + new)
11. Keyboard shortcuts work on every navigation level (Enter/Esc/level-specific)
12. LLM failures show toast + fallback option (not silent fail)
13. E2E tests pass: onboarding, navigation drill-down, pipeline execution, persistence
14. BMAD bridge: Roadmap node -> task -> workflow DAG -> agent_pipeline execution
15. 6+ workflow templates in library, Architect auto-selects based on task type
16. Prefetch pipeline: one [Execute] click → files + docs + workflow + team selected automatically
17. Architect uses CAM/history to prefer proven workflows over generic ones
