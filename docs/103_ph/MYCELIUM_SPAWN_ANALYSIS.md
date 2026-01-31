# MYCELIUM SPAWN ANALYSIS
**Детальный анализ spawn механизма VETKA для интеграции в MYCELIUM**

Generated: 2026-01-31
Target: MYCELIUM group chat integration
Source: `/src/orchestration/agent_pipeline.py`, `/src/mcp/vetka_mcp_bridge.py`

---

## 1. Current Implementation

### 1.1 Pipeline Architecture

**File**: `/src/orchestration/agent_pipeline.py`

VETKA spawn pipeline реализован как **fractal task orchestration** с тремя фазами:

```
Phase 1: Architect (планирование)
  └─> Разбивает задачу на subtasks
  └─> Помечает неясные части как needs_research=True
  └─> Возвращает execution_order: "sequential" | "parallel"

Phase 2: Researcher (автоисследование) + Executor (выполнение)
  └─> Для каждого subtask:
      ├─> IF needs_research:
      │     └─> Grok researcher углубляет контекст
      │     └─> Recursive: если confidence < 0.7, задаёт follow-up вопросы
      └─> Execute subtask с enriched context
          └─> Build phase: extract code blocks → write files

Phase 3: Compilation
  └─> Собирает результаты всех subtasks
  └─> Сохраняет в data/pipeline_tasks.json
```

### 1.2 Key Classes & Data Structures

```python
class AgentPipeline:
    def __init__(self, chat_id: Optional[str] = None, auto_write: bool = True)

    # Core execution
    async def execute(task: str, phase_type: str) -> Dict[str, Any]

    # Internal phases
    async def _architect_plan(task, phase_type) -> Dict[str, Any]
    async def _research(question: str) -> Dict[str, Any]
    async def _execute_subtask(subtask, phase_type) -> str

@dataclass
class PipelineTask:
    task_id: str
    task: str
    phase_type: str  # "research" | "fix" | "build"
    status: str      # "pending" | "planning" | "executing" | "done" | "failed"
    subtasks: List[Subtask]
    results: Optional[Dict]

@dataclass
class Subtask:
    description: str
    needs_research: bool = False
    question: Optional[str] = None
    context: Optional[Dict] = None  # Research insights, STM, enriched context
    result: Optional[str] = None
    status: str  # "pending" | "researching" | "executing" | "done" | "failed"
    marker: Optional[str] = None
```

### 1.3 Agent Roles

**NO explicit agent numbering** (dev1, dev2) в текущей реализации.

Вместо этого используются **role-based agents**:

| Role | Model (default) | Purpose |
|------|----------------|---------|
| `@architect` | claude-sonnet-4 | Task decomposition |
| `@researcher` | grok-4 | Deep research on unclear parts |
| `@coder` | claude-sonnet-4 | Implementation (fix/build phases) |
| `@pipeline` | System | Progress orchestration |

Роли определяются в `/data/templates/pipeline_prompts.json` (или default prompts в коде).

### 1.4 Execution Modes

**Текущая реализация: SEQUENTIAL ONLY**

```python
# Lines 426-473: agent_pipeline.py
for i, subtask in enumerate(pipeline_task.subtasks):
    # 1. Research (if needed)
    if subtask.needs_research:
        research = await self._research(question)
        subtask.context.update(research)

    # 2. Execute
    result = await self._execute_subtask(subtask, phase_type)

    # 3. Update STM for next subtask
    self._add_to_stm(subtask.marker, result)
```

**Parallel execution** планируется в `execution_order`, но **НЕ РЕАЛИЗОВАНО**:

```python
# Line 112: architect prompt returns execution_order
"execution_order": "sequential" or "parallel"  # ← returned but NOT used!

# Line 482: results include execution_order
pipeline_task.results = {
    "execution_order": plan.get("execution_order", "sequential")  # ← saved but ignored
}
```

---

## 2. Data Flow

### 2.1 Spawn Trigger (MCP Tool)

**File**: `/src/mcp/vetka_mcp_bridge.py` (lines 1300-1353)

```python
# Tool definition (lines 679-715)
Tool(name="vetka_spawn_pipeline", ...)

# Handler (lines 1300-1353)
elif name == "vetka_spawn_pipeline":
    task = arguments.get("task", "")
    phase_type = arguments.get("phase_type", "research")
    chat_id = arguments.get("chat_id", MCP_LOG_GROUP_ID)
    auto_write = arguments.get("auto_write", True)

    pipeline = AgentPipeline(chat_id=chat_id, auto_write=auto_write)

    # Fire-and-forget: background execution
    asyncio.create_task(run_pipeline_background())

    # Return immediately with task_id
    return task_id
```

**Важно**: Spawn запускается **асинхронно** (fire-and-forget), не блокирует MCP call.

### 2.2 Progress Streaming to Chat

**File**: `/src/orchestration/agent_pipeline.py` (lines 153-193)

```python
def _emit_progress(self, role: str, message: str, subtask_idx: int, total: int):
    """Emit progress update to VETKA chat."""

    # Format message
    progress = f"[{subtask_idx}/{total}] " if total > 0 else ""
    full_message = f"{role}: {progress}{message}"

    # HTTP POST to group chat
    httpx.Client().post(
        "http://localhost:5001/api/chat/send",
        json={
            "group_id": self.chat_id,
            "sender_id": "@pipeline",
            "content": full_message,
            "message_type": "system"
        }
    )
```

**Progress events** (lines 409-489):

1. `@pipeline`: Pipeline start
2. `@architect`: Planning start/complete
3. `@researcher`: Research start (per subtask)
4. `@coder`: Execution start/complete (per subtask)
5. `@coder`: Files created (if auto_write=True)
6. `@pipeline`: Pipeline complete/failed

### 2.3 Artifact Creation

**Two modes** (MARKER_103.5):

#### Mode 1: Auto-write (default)

```python
# Lines 700-705
if phase_type == "build" and "```" in content:
    if self.auto_write:
        files_created = self._extract_and_write_files(content, subtask)
        self._emit_progress("@coder", f"📁 Created {len(files_created)} files: ...")
```

Файлы **сразу создаются** на диске + сохраняются в JSON.

#### Mode 2: Staging (safe review)

```python
# Lines 706-709
else:
    # Staging mode - just log, files stay in JSON
    self._emit_progress("@coder", f"📝 Code staged in JSON (auto_write=False)")
```

Файлы **только в JSON**, применяются позже через:
```bash
python scripts/retro_apply_spawn.py --task-filter "feature_name"
```

**Fallback staging directory**: `/data/spawn_staging/` (создаётся при ошибке записи).

### 2.4 Task Storage

**File**: `/data/pipeline_tasks.json`

```json
{
  "task_1769770313": {
    "task_id": "task_1769770313",
    "task": "Audit and improve spawn system...",
    "phase_type": "research",
    "status": "done",
    "subtasks": [
      {
        "description": "Analyze STM implementation",
        "needs_research": false,
        "context": {
          "enriched_context": "...",
          "previous_results": "..."
        },
        "result": "...",
        "status": "done",
        "marker": "MARKER_102.25"
      }
    ],
    "timestamp": 1769770313.308144,
    "results": {
      "plan": {...},
      "subtasks_completed": 3,
      "subtasks_total": 3,
      "execution_order": "sequential"
    }
  }
}
```

---

## 3. Memory Integration

### 3.1 STM (Short-Term Memory)

**File**: `/src/orchestration/agent_pipeline.py` (lines 69-72, 285-306, 424-474)

**Purpose**: Передача результатов между subtasks внутри одного pipeline run.

```python
class AgentPipeline:
    def __init__(self, ...):
        self.stm: List[Dict[str, str]] = []  # Last N subtask results
        self.stm_limit = 5  # Keep last 5 results

    def _add_to_stm(self, marker: str, result: str):
        self.stm.append({
            "marker": marker,
            "result": result[:500]  # Truncate for efficiency
        })
        if len(self.stm) > self.stm_limit:
            self.stm.pop(0)

    def _get_stm_summary(self) -> str:
        summary_parts = ["Previous results:"]
        for item in self.stm[-3:]:  # Last 3 for brevity
            summary_parts.append(f"- [{item['marker']}]: {item['result'][:200]}...")
        return "\n".join(summary_parts)
```

**Injection point**:

```python
# Line 432-437: Before each subtask execution
if self.stm:
    stm_summary = self._get_stm_summary()
    if subtask.context is None:
        subtask.context = {}
    subtask.context["previous_results"] = stm_summary
```

**Lifecycle**: STM сбрасывается при каждом `execute()` (line 427).

### 3.2 Researcher Context Injection

**File**: `/src/orchestration/agent_pipeline.py` (lines 585-602)

Researcher использует **semantic search** для обогащения контекста:

```python
# Line 588-602: _research method
result = tool.execute({
    "model": "x-ai/grok-4",
    "messages": [...],
    "inject_context": {
        "semantic_query": question,     # ← Auto-search VETKA knowledge
        "semantic_limit": 5,
        "include_prefs": True,          # ← Engram preferences
        "compress": True                # ← ELISION compression
    }
})
```

**Context sources** (from `/src/mcp/tools/llm_call_tool.py`):

1. **Files**: Explicit file paths
2. **Session**: MCP session state
3. **Engram**: User preferences (hot RAM cache + Qdrant)
4. **CAM**: Context-Aware Memory active nodes
5. **Semantic search**: Qdrant vector search

### 3.3 Memory Systems Status

| System | Integration in Pipeline | Notes |
|--------|------------------------|-------|
| **STM** | ✅ Implemented | Within-pipeline context passing |
| **Engram** | ✅ Via inject_context | User preferences (researcher only) |
| **CAM** | ✅ Via inject_context | Context-Aware Memory (researcher only) |
| **Semantic Search** | ✅ Via inject_context | Qdrant vector search (researcher only) |
| **ARC** | ❌ NOT integrated | No ARC gap analysis in pipeline |
| **HOPE** | ❌ NOT integrated | No HOPE suggestions |
| **Elisya** | ❌ NOT integrated | No Elisya state sharing |

**Critical gap**: Spawn pipeline **изолирован** от основного orchestrator с Elisya/HOPE/ARC.

---

## 4. Gaps (что не реализовано)

### 4.1 Parallel Execution

**Gap**: `execution_order: "parallel"` возвращается Architect, но **игнорируется**.

**Impact**: Все subtasks выполняются последовательно, даже если они независимы.

**Example use case**:
```python
# Architect plan:
{
  "subtasks": [
    {"description": "Create backend API", "needs_research": false},
    {"description": "Create frontend UI", "needs_research": false},
    {"description": "Write tests", "needs_research": false}
  ],
  "execution_order": "parallel"  # ← Could run all 3 in parallel!
}
```

**Missing code**:

```python
# NOT IMPLEMENTED:
if plan.get("execution_order") == "parallel":
    tasks = [self._execute_subtask(st, phase_type) for st in subtasks]
    results = await asyncio.gather(*tasks)
else:
    # Sequential (current)
    for st in subtasks:
        result = await self._execute_subtask(st, phase_type)
```

### 4.2 Agent Numbering

**Gap**: Нет нумерации агентов (dev1, dev2, researcher1).

**Impact**: При параллельном выполнении невозможно отследить, какой агент за что отвечает.

**Recommended structure**:

```python
@dataclass
class Subtask:
    agent_id: str = "dev1"  # dev1, dev2, researcher1, etc.

# Progress emission:
self._emit_progress(f"@{subtask.agent_id}", message)
```

### 4.3 Cross-Pipeline Memory

**Gap**: STM сбрасывается при каждом `execute()`. Нет долговременной памяти между запусками.

**Impact**: Если spawn вызывается несколько раз для одной feature, контекст теряется.

**Recommended**: Интеграция с Elisya CAM/Engram для сохранения spawn истории.

### 4.4 ARC/HOPE Integration

**Gap**: Spawn не использует:
- **ARC gap analysis** для улучшения планов
- **HOPE suggestions** для обогащения researcher запросов

**Impact**: Architect может пропустить важные аспекты задачи, которые ARC бы выявил.

**Example**:

```python
# MISSING: Before architect planning
arc_gaps = await self.arc_agent.analyze_gaps(task)
plan = await self._architect_plan(task, phase_type, arc_context=arc_gaps)
```

### 4.5 Elisya State Sharing

**Gap**: Spawn изолирован от `orchestrator_with_elisya.py`.

**Impact**:
- Нет доступа к `ElisyaState` (workflow context)
- Нет Chain Context (PM → Architect → Dev → QA)
- Spawn не видит результаты основного workflow

**Recommended**: Spawn должен принимать `elisya_state: ElisyaState` для чтения контекста.

### 4.6 Group Chat Integration

**Gap**: Progress streaming есть, но **односторонний** (только output).

**Missing**:
- Чтение сообщений из группы (для динамических указаний)
- Реакция на feedback в процессе выполнения
- Пауза/возобновление на основе чата

**MYCELIUM need**: Bidirectional chat для "живого" взаимодействия.

### 4.7 Artifact Metadata

**Gap**: Создаются файлы, но **нет метаданных**:
- Кто создал (какой agent_id)
- Когда создано
- Связь с task_id
- Статус (draft/staged/applied)

**Recommended**:

```json
// data/spawn_artifacts.json
{
  "src/voice/config.py": {
    "created_by": "dev1",
    "task_id": "task_1769770313",
    "timestamp": "2026-01-31T12:00:00",
    "status": "applied",
    "marker": "MARKER_104.3"
  }
}
```

---

## 5. Recommendations for MYCELIUM

### 5.1 Adopt Core Spawn Mechanism

**Use as-is** (с минимальными адаптациями):

```python
from src.orchestration.agent_pipeline import AgentPipeline

# MYCELIUM wrapper
async def mycelium_spawn(task: str, group_id: str):
    pipeline = AgentPipeline(
        chat_id=group_id,
        auto_write=False  # ← Safe mode for MYCELIUM
    )

    result = await pipeline.execute(task, phase_type="build")
    return result["task_id"]
```

**Why**: Fractal task decomposition + auto-research уже работает хорошо.

### 5.2 Add Parallel Execution

**Priority**: HIGH (для масштабирования MYCELIUM)

**Implementation**:

```python
# agent_pipeline.py: After line 423
execution_order = pipeline_task.results.get("plan", {}).get("execution_order", "sequential")

if execution_order == "parallel":
    # Parallel execution with agent_id assignment
    async def run_subtask_with_id(idx, subtask):
        subtask.agent_id = f"{phase_type}{idx+1}"  # dev1, dev2, researcher1
        self._emit_progress(f"@{subtask.agent_id}", "Starting...")
        result = await self._execute_subtask(subtask, phase_type)
        self._emit_progress(f"@{subtask.agent_id}", "Done!")
        return result

    tasks = [run_subtask_with_id(i, st) for i, st in enumerate(subtasks)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
else:
    # Sequential (current)
    ...
```

### 5.3 Bidirectional Chat Integration

**Priority**: CRITICAL (для MYCELIUM UX)

**New method**:

```python
class AgentPipeline:
    async def _check_chat_feedback(self, subtask_idx: int):
        """Check if user posted feedback during execution."""
        resp = await httpx.get(
            f"http://localhost:5001/api/groups/{self.chat_id}/messages",
            params={"since": self.execution_start_time, "limit": 10}
        )

        messages = resp.json().get("messages", [])
        for msg in messages:
            if msg["sender_id"] == "user" and "pause" in msg["content"]:
                # Pause execution
                await self._pause_and_wait_for_resume()
```

**Inject point**: After each subtask (line 468).

### 5.4 Elisya State Integration

**Priority**: MEDIUM (для long-term MYCELIUM context)

**Pass ElisyaState to pipeline**:

```python
class AgentPipeline:
    def __init__(self, chat_id, auto_write, elisya_state: Optional[ElisyaState] = None):
        self.elisya_state = elisya_state

    async def _architect_plan(self, task, phase_type):
        # Enrich with Elisya context
        pm_context = self.elisya_state.pm_plan if self.elisya_state else ""
        arch_context = self.elisya_state.architecture if self.elisya_state else ""

        prompt = f"""
        Task: {task}
        PM Plan: {pm_context}
        Architecture: {arch_context}

        Break down into subtasks...
        """
```

### 5.5 Artifact Metadata Tracking

**Priority**: MEDIUM (для MYCELIUM audit trail)

**New file**: `data/spawn_artifacts.json`

```python
class AgentPipeline:
    def _extract_and_write_files(self, content, subtask):
        files_created = []

        for filepath, code in self._parse_code_blocks(content):
            # Write file
            Path(filepath).write_text(code)

            # Save metadata
            self._save_artifact_metadata({
                "path": filepath,
                "created_by": subtask.agent_id,
                "task_id": self.current_task_id,
                "marker": subtask.marker,
                "timestamp": datetime.now().isoformat(),
                "status": "applied" if self.auto_write else "staged"
            })

            files_created.append(filepath)

        return files_created
```

### 5.6 ARC Gap Analysis Pre-Planning

**Priority**: LOW (nice-to-have)

**Add before Architect**:

```python
async def execute(self, task, phase_type):
    # Phase 0: ARC gap analysis
    if self.arc_agent:
        arc_gaps = await self.arc_agent.analyze_task_gaps(task)
        task_enriched = f"{task}\n\nARC Context: {arc_gaps}"
    else:
        task_enriched = task

    # Phase 1: Architect with ARC context
    plan = await self._architect_plan(task_enriched, phase_type)
```

### 5.7 MYCELIUM-Specific Extensions

**Recommended additions**:

1. **Subtask voting**: Пользователи в MYCELIUM чате могут голосовать за приоритет subtasks
2. **Dynamic re-planning**: Если subtask fails, Architect пересоздаёт план
3. **Multi-model routing**: Разные subtasks используют разные модели (Grok для research, Claude для code)
4. **Spawn nesting**: Subtask может сам вызвать spawn для сложных задач

---

## 6. Integration Points with MYCELIUM

### 6.1 Spawn Entry Point

**MYCELIUM command**: `/spawn <task>`

**Handler**:

```python
# mycelium_chat_handler.py
async def handle_spawn_command(group_id: str, task: str, sender_id: str):
    # Create pipeline with MYCELIUM group
    pipeline = AgentPipeline(
        chat_id=group_id,
        auto_write=False  # Staging mode for review
    )

    # Start background execution
    task_id = await spawn_pipeline(task, phase_type="build", chat_id=group_id)

    # Send immediate response
    await send_to_group(group_id,
        f"🚀 Spawn started! Task ID: {task_id}\n"
        f"Progress will stream here. Use /status {task_id} to check."
    )
```

### 6.2 Progress Display

**Already works** via `_emit_progress()` → `POST /api/chat/send`.

**MYCELIUM UI** can display:
- Agent icons (@architect, @researcher, @coder)
- Progress bars ([3/5] subtasks done)
- File creation notifications (📁 Created src/voice/config.py)

### 6.3 Artifact Review

**MYCELIUM command**: `/review <task_id>`

**Shows**:
```
📋 Spawn Results: task_1769770313

Subtasks: 5/5 ✅
Files staged: 3

📁 src/voice/config.py (234 lines)
📁 src/voice/tts_engine.py (450 lines)
📁 src/voice/pipeline.py (180 lines)

Commands:
  /apply task_1769770313  → Create files on disk
  /reject task_1769770313 → Discard changes
  /edit task_1769770313 src/voice/config.py → Review specific file
```

### 6.4 Status Tracking

**MYCELIUM command**: `/status <task_id>`

**Uses existing** `pipeline.get_task_status(task_id)`:

```python
async def handle_status_command(group_id: str, task_id: str):
    pipeline = AgentPipeline()
    status = pipeline.get_task_status(task_id)

    await send_to_group(group_id, format_status(status))
```

---

## 7. Summary

### Current State (Phase 103)

✅ **Working well**:
- Fractal task decomposition (Architect → Subtasks)
- Auto-research trigger (needs_research=True)
- STM context passing between subtasks
- Progress streaming to chat
- Staging mode for safe artifact review
- Researcher uses semantic search + Engram + CAM

❌ **Missing**:
- Parallel execution (planned but not implemented)
- Agent numbering (dev1, dev2)
- Cross-pipeline memory (STM resets each run)
- ARC/HOPE integration
- Elisya state sharing
- Bidirectional chat (only one-way progress)
- Artifact metadata tracking

### MYCELIUM Integration Readiness

| Feature | Priority | Complexity | Status |
|---------|----------|-----------|--------|
| Adopt core spawn | CRITICAL | LOW | ✅ Ready |
| Progress streaming | CRITICAL | LOW | ✅ Ready |
| Staging mode | HIGH | LOW | ✅ Ready |
| Parallel execution | HIGH | MEDIUM | ⚠️ Needs impl |
| Bidirectional chat | CRITICAL | MEDIUM | ⚠️ Needs impl |
| Artifact metadata | MEDIUM | LOW | ⚠️ Needs impl |
| Elisya integration | MEDIUM | HIGH | ❌ Future |
| ARC gap analysis | LOW | MEDIUM | ❌ Future |

### Next Steps for MYCELIUM

1. **Week 1**: Adopt core spawn as-is (chat_id integration)
2. **Week 2**: Implement parallel execution + agent numbering
3. **Week 3**: Add bidirectional chat feedback
4. **Week 4**: Artifact metadata + review UI
5. **Week 5+**: Elisya state sharing, ARC integration

---

**End of Analysis**

Files referenced:
- `/src/orchestration/agent_pipeline.py` (769 lines)
- `/src/mcp/vetka_mcp_bridge.py` (1901 lines)
- `/data/pipeline_tasks.json` (spawn results storage)
- `/scripts/retro_apply_spawn.py` (artifact staging recovery)
