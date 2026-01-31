# TASK B: Artifact → File Pipeline

**Phase:** 102 → 103
**Assignee:** Claude Code + Vetka Agents
**Priority:** P0 (Core Feature)
**Status:** Ready to Start

---

## Objective

Превратить артефакты (код от Dev агента) в **реальные файлы** на диске с:
- QA review workflow
- Стриминг прогресса в чат
- Elisya tools интеграция

---

## Current State

### Что есть (40-50%):
- `artifact_extractor.py` - извлекает код из ответов ✅
- `ArtifactPanel.tsx` - UI для просмотра ✅
- Tauri FS - нативная запись ✅
- Elisya tool loop - работает ✅

### Что отсутствует:
- `create_artifact` в tools.py - **STUB** ❌
- Персистенция в Qdrant ❌
- QA approval hooks ❌
- Streaming progress ❌

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Dev Agent   │────▶│ Artifact     │────▶│ QA Review   │
│ generates   │     │ Extractor    │     │ (score>0.75)│
└─────────────┘     └──────────────┘     └─────────────┘
                                                │
                    ┌───────────────────────────┘
                    ▼
              ┌─────────────┐     ┌──────────────┐
              │ create_     │────▶│ Disk + Qdrant│
              │ artifact()  │     │ persistence  │
              └─────────────┘     └──────────────┘
                    │
                    ▼
              ┌─────────────┐     ┌──────────────┐
              │ Socket emit │────▶│ UI Panel     │
              │ + streaming │     │ opens file   │
              └─────────────┘     └──────────────┘
```

---

## Implementation Steps

### Step 1: `create_artifact` Tool (P0)

**File:** `src/agents/tools.py` (line ~895)

```python
@tool
def create_artifact(
    name: str,
    content: str,
    type_: str = 'code',
    language: str = 'python',
    agent: str = 'Dev'
) -> Dict:
    """
    Save artifact to disk and Qdrant.
    Emits socket events for UI.
    """
    artifact_id = str(uuid.uuid4())
    filepath = f"artifacts/{artifact_id}_{name}.{language}"

    # 1. Write to disk
    os.makedirs('artifacts', exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(content)

    # 2. Persist to Qdrant
    upsert_artifact_to_qdrant({
        'id': artifact_id,
        'name': name,
        'path': filepath,
        'content': content[:1000],
        'language': language,
        'agent': agent,
        'created_at': datetime.now().isoformat()
    })

    # 3. Emit events
    emit('artifact_created', {...})

    return {'status': 'saved', 'path': filepath}
```

### Step 2: QA Review Hook (P1)

**File:** `src/services/group_chat_manager.py`

```python
# After Dev response with artifact
if artifact_detected and agent_role == 'Dev':
    qa_score = extract_qa_score(content)

    if qa_score > 0.75:
        # Auto-approve
        create_artifact(...)
        emit_to_group('artifact_approved', {...})
    else:
        # Request QA review
        emit_to_group('qa_review_needed', {...})
```

### Step 3: Streaming Progress (P1)

**Интеграция с MARKER_102.26-28:**

```python
# In artifact creation flow
await stream_to_vetka_chat(
    chat_id,
    f"📦 Creating artifact: {name}"
)

# After save
await stream_to_vetka_chat(
    chat_id,
    f"✅ Saved: {filepath}"
)
```

### Step 4: Elisya Tools (P2)

**Дать Dev агенту доступ к:**
- `read_file` - читать существующие файлы
- `write_file` - создавать/редактировать
- `list_directory` - навигация

```python
# In orchestrator elisya tools
ARTIFACT_TOOLS = [
    'create_artifact',
    'read_file',
    'write_file',
    'list_directory'
]
```

---

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `src/agents/tools.py:895` | Implement `create_artifact` | P0 |
| `src/memory/qdrant_client.py` | Add `upsert_artifact_to_qdrant` | P0 |
| `src/services/group_chat_manager.py` | QA approval hooks | P1 |
| `src/orchestration/orchestrator_with_elisya.py` | Elisya file tools | P2 |
| `client/src/components/artifact/ArtifactPanel.tsx` | Socket listeners | P1 |

---

## Dependencies (Must Fix First!)

### VetkaTree Fixes (Phase 101) - ✅ DONE!

| Fix | File | Line | Status |
|-----|------|------|--------|
| `"file"` → `"leaf"` | shared_tools.py | 331 | ✅ FIXED |
| VetkaTree write | triple_write_manager.py | 318 | ✅ FIXED |
| parent_folder + depth | qdrant_updater.py | 362 | ✅ FIXED |

**VetkaTree: 1768 points - работает!**

---

## Acceptance Criteria

- [ ] Dev agent может создать файл через `create_artifact`
- [ ] Файл появляется на диске в `artifacts/`
- [ ] Файл индексируется в Qdrant
- [ ] QA approval workflow работает в group chat
- [ ] Progress стримится в Vetka chat
- [ ] UI ArtifactPanel открывается автоматически

---

## Testing Flow

```
1. User: "@Dev создай hello.py с print Hello World"
2. Dev: Генерирует код
3. System: Извлекает артефакт
4. QA: Автоматически проверяет (score > 0.75)
5. System: Сохраняет файл + Qdrant
6. UI: Открывает ArtifactPanel
7. Chat: Стримит "✅ Saved: artifacts/xxx_hello.py"
```

---

## Timeline

| Day | Task |
|-----|------|
| 1 | `create_artifact` implementation |
| 2 | QA hooks + streaming |
| 3 | Elisya tools + testing |

---

*Task created: 2025-01-30*
*Depends on: Phase 101 VetkaTree fixes*
