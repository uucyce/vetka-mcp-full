# 🔍 MEMORY SYNC PROTOCOL - FEASIBILITY AUDIT

**Phase:** 77-78
**Auditor:** Claude Opus 4.5
**Date:** 2026-01-20
**Status:** ✅ FEASIBLE WITH CAVEATS

---

## 📋 EXECUTIVE SUMMARY

Memory Sync Protocol **реализуем**, но требует **точечных доработок** в 6 местах. Основная архитектура совместима с существующим codebase Phase 75-76. Рекомендуется **инкрементальная реализация** с промежуточными тестами.

---

## 1. 🔌 INTEGRATION POINTS

### ✅ CLEAR TO GO

| Компонент | Файл | Строка | Совместимость |
|-----------|------|--------|---------------|
| QdrantVetkaClient | `src/memory/qdrant_client.py` | 53-535 | ✅ Полная |
| LocalScanner | `src/scanners/local_scanner.py` | 34-200 | ✅ Полная |
| MemoryService | `src/orchestration/services/memory_service.py` | 20-127 | ✅ Полная |
| HostessMemory | `src/memory/hostess_memory.py` | 28-144 | ✅ Полная |
| ReplayBuffer | `src/memory/replay_buffer.py` | 72-512 | ✅ Полная |

### ⚠️ ТРЕБУЕТ ДОРАБОТКИ

#### [MARKER-77-01] orchestrator_with_elisya.py - Integration Hook
**Файл:** `src/orchestration/orchestrator_with_elisya.py:1179`
**Проблема:** Нет точки входа для Memory Sync перед `execute_full_workflow_streaming()`
**Решение:** Добавить хук в начало метода для вызова `MemorySyncEngine.check_and_sync()`
```python
# MARKER-77-01: Add before line 1210
async def execute_full_workflow_streaming(self, ...):
    # === PHASE 77: Memory Sync Check ===
    if hasattr(self, 'memory_sync_engine'):
        await self.memory_sync_engine.check_and_sync()
    # ... rest of method
```

#### [MARKER-77-02] qdrant_client.py - New Collection
**Файл:** `src/memory/qdrant_client.py:61-65`
**Проблема:** Нет `vetka_trash` collection в `COLLECTION_NAMES`
**Решение:** Добавить в словарь коллекций
```python
COLLECTION_NAMES = {
    'tree': 'VetkaTree',
    'leaf': 'VetkaLeaf',
    'changelog': 'VetkaChangeLog',
    'trash': 'VetkaTrash',  # MARKER-77-02: Add this
}
```

#### [MARKER-77-03] hostess_agent.py - Memory Curator Tool
**Файл:** `src/agents/hostess_agent.py:56-180`
**Проблема:** В `self.tools` нет инструмента для Memory Curation
**Решение:** Добавить новый tool `memory_sync_dialog`
```python
# MARKER-77-03: Add to self.tools list
{
    "name": "memory_sync_dialog",
    "description": "Ask user about memory sync decisions (keep/trash/compress files)",
    "parameters": {
        "type": "object",
        "properties": {
            "changes_summary": {"type": "string"},
            "options": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["changes_summary", "options"]
    }
}
```

---

## 2. 🔄 BACKWARD COMPATIBILITY

### ✅ Phase 75-76 Совместимость

| Компонент Phase 75-76 | Конфликт? | Причина |
|-----------------------|-----------|---------|
| JARVIS Prompt Enricher | ❌ НЕТ | Независимый модуль, работает с preferences |
| Engram User Memory | ❌ НЕТ | Отдельная collection `vetka_user_memories` |
| Replay Buffer | ❌ НЕТ | Отдельная collection `vetka_replay` |
| LangGraph Workflow | ❌ НЕТ | Memory Sync вызывается ДО workflow |
| EvalAgent / LearnerAgent | ❌ НЕТ | Работают после workflow |

### ⚠️ Потенциальные проблемы

#### [MARKER-77-04] Qdrant Collection Naming
**Риск:** Коллизия имён при создании `vetka_trash`
**Проверка:** Выполнить `qdrant.get_collections()` перед созданием
**Fallback:** Использовать `vetka_trash_v2` если коллизия

#### [MARKER-77-05] Migration Scripts
**Нужен?** НЕТ для начальной имплементации
**Почему:** MemorySnapshot строится с нуля, не требует миграции старых данных
**Когда понадобится:** При апгрейде структуры NodeState (Phase 78+)

---

## 3. ⚡ PERFORMANCE ANALYSIS

### Diff Algorithm (1000+ файлов)

| Операция | Оценка | M4 Mac Pro | Приемлемо? |
|----------|--------|------------|------------|
| File hashes (MD5) | O(n) | ~2-3 сек на 1000 файлов | ✅ ДА |
| Dict comparison | O(n) | ~50ms | ✅ ДА |
| Edge changes | O(n²) worst | ~1-2 сек | ⚠️ Мониторить |

**Рекомендация:** Добавить `tqdm` progress bar для visibility

### PCA Reduction (768D → 256D)

| Метрика | Значение |
|---------|----------|
| sklearn.PCA на 100 vectors | ~15ms |
| sklearn.PCA на 1000 vectors | ~150ms |
| Memory overhead | ~3MB per batch |

**Оценка для M4 Mac:** ✅ БЫСТРО (sklearn уже установлен)

### Trash Cleanup Frequency

**Рекомендация:**
```python
# MARKER-77-06: Cleanup schedule
TRASH_CLEANUP_INTERVAL = 86400  # 24 hours (не чаще!)
TRASH_TTL_DEFAULT = 90  # days
```

**Почему не чаще:** Qdrant scroll операции дорогие на больших коллекциях

---

## 4. 📦 MISSING PIECES

### Зависимости (requirements.txt)

| Package | Статус | Нужен для |
|---------|--------|-----------|
| numpy | ✅ Установлен | PCA, vector ops |
| scikit-learn | ✅ Установлен | PCA reduction |
| qdrant-client | ✅ Установлен | Vector storage |
| hashlib | ✅ Встроен | Content hashes |

**Новые зависимости:** НЕ ТРЕБУЮТСЯ

### Файлы для создания

| Файл | LOC | Приоритет |
|------|-----|-----------|
| `src/backup/vetka_backup.py` | ~80 | 🔴 HIGH |
| `src/memory/snapshot.py` | ~100 | 🔴 HIGH |
| `src/memory/diff.py` | ~120 | 🔴 HIGH |
| `src/agents/memory_curator_agent.py` | ~150 | 🟡 MEDIUM |
| `src/memory/compression.py` | ~100 | 🟡 MEDIUM |
| `src/memory/dep_compression.py` | ~60 | 🟢 LOW |
| `src/memory/trash.py` | ~90 | 🟡 MEDIUM |
| `tests/test_memory_sync.py` | ~200 | 🔴 HIGH |

### Директории для создания

```bash
mkdir -p src/backup
touch src/backup/__init__.py
```

---

## 5. 📐 IMPLEMENTATION ORDER

### ОБЯЗАТЕЛЬНАЯ последовательность (зависимости)

```
77.0 Backup ──┐
              ├──> 77.1 Snapshot ──> 77.2 Diff ──> 77.3 Hostess Dialog
              │                                            │
              │                                            v
              └──────────────────────────────────> 77.4 Compression
                                                          │
                                                          v
                                                   77.5 DEP Compression
                                                          │
                                                          v
                                                   77.6 Trash Memory
                                                          │
                                                          v
                                                   77.7 Tests + Integration
```

### Параллелизация возможна

| Группа | Этапы | Parallel? |
|--------|-------|-----------|
| Core | 77.0 + 77.1 | ✅ ДА (независимые dataclasses) |
| Logic | 77.2 | ❌ НЕТ (зависит от 77.1) |
| Dialog | 77.3 | ❌ НЕТ (зависит от 77.2) |
| Compression | 77.4 + 77.5 | ✅ ДА (независимые алгоритмы) |
| Trash | 77.6 | ❌ НЕТ (зависит от 77.4) |

### Рекомендуемый Plan

**День 1 (8h):**
1. [2h] 77.0 + 77.1 PARALLEL
2. [3h] 77.2 Diff Algorithm
3. [2h] 77.3 Hostess Dialog
4. [1h] Tests для 77.0-77.3

**День 2 (6h):**
1. [2h] 77.4 + 77.5 PARALLEL
2. [2h] 77.6 Trash Memory
3. [2h] 77.7 Integration + Final Tests

---

## 6. ⚠️ RISK ASSESSMENT

### 🔴 HIGH RISK

#### Backup Restore Failure
**Сценарий:** Backup создан, но restore не работает из-за изменённой схемы Qdrant
**Mitigation:**
- [MARKER-77-07] Добавить версионирование backup формата
- Тестировать restore СРАЗУ после backup в каждом тесте

#### Hostess Timeout
**Сценарий:** User dialog зависает, workflow блокируется
**Mitigation:**
- [MARKER-77-08] Добавить timeout 30s на dialog
- Fallback: auto-approve с default decisions

### 🟡 MEDIUM RISK

#### Diff Algorithm False Positives
**Сценарий:** content_hash совпадает, но metadata изменилась
**Mitigation:** Проверять timestamp + hash + size

#### PCA Information Loss
**Сценарий:** После 768D→256D поиск становится менее точным
**Mitigation:**
- Хранить оригинальный embedding для top-accessed nodes
- [MARKER-77-09] Добавить метрику `search_quality_degradation`

### 🟢 LOW RISK

#### Trash Overflow
**Сценарий:** trash collection переполняется
**Mitigation:** Hard limit 10000 items, auto-purge oldest

---

## 7. 📋 MARKERS SUMMARY

| Marker | File | Action |
|--------|------|--------|
| MARKER-77-01 | orchestrator_with_elisya.py:1210 | Add sync hook |
| MARKER-77-02 | qdrant_client.py:65 | Add vetka_trash collection |
| MARKER-77-03 | hostess_agent.py:56 | Add memory_sync_dialog tool |
| MARKER-77-04 | (check) | Verify collection names |
| MARKER-77-05 | (future) | Migration scripts when needed |
| MARKER-77-06 | trash.py | Set cleanup interval |
| MARKER-77-07 | vetka_backup.py | Add backup versioning |
| MARKER-77-08 | memory_curator_agent.py | Add dialog timeout |
| MARKER-77-09 | compression.py | Add quality metric |

---

## 8. ✅ FINAL VERDICT

### GO / NO-GO Decision: ✅ GO

| Criterion | Status |
|-----------|--------|
| Dependencies available | ✅ |
| No breaking changes | ✅ |
| Performance acceptable | ✅ |
| Risk mitigations defined | ✅ |
| Implementation order clear | ✅ |

### Recommendations for Opus

1. **Начать с 77.0 Backup** — safe point критичен
2. **Тестировать каждый этап** — не накапливать долг
3. **Hostess Dialog — MVP сначала** — усложнять позже
4. **PCA только для >30 дней** — сохранять свежие полными
5. **Использовать markers** — они указывают точные места для кода

---

## 9. 🚀 PROMPT FOR OPUS

```markdown
# Phase 77: Memory Sync Protocol Implementation

## Context
Read MEMORY_SYNC_FEASIBILITY_AUDIT.md in docs/77-78ph/
This audit identifies 9 markers where code changes are needed.

## Implementation Order (STRICT)
1. Create src/backup/ directory
2. 77.0: VetkaBackup (with MARKER-77-07 versioning)
3. 77.1: MemorySnapshot dataclass
4. 77.2: MemoryDiff algorithm
5. Apply MARKER-77-01 to orchestrator
6. Apply MARKER-77-02 to qdrant_client
7. 77.3: HostessMemoryCuratorAgent (apply MARKER-77-03, MARKER-77-08)
8. 77.4: MemoryCompression (apply MARKER-77-09)
9. 77.5: DEPCompression
10. 77.6: TrashMemory (apply MARKER-77-06)
11. 77.7: Tests

## Key Files to Read First
- src/memory/qdrant_client.py (understand existing patterns)
- src/scanners/local_scanner.py (ScannedFile dataclass)
- src/agents/hostess_agent.py (tool calling pattern)
- src/memory/replay_buffer.py (Qdrant collection pattern)

## Success Criteria
- [ ] Backup creates and restores successfully
- [ ] Diff correctly identifies added/modified/deleted
- [ ] Hostess dialog works with 30s timeout
- [ ] Compression reduces 768D→256D for old nodes
- [ ] Trash recovery works
- [ ] All 9 markers applied
- [ ] Tests pass

Ready to implement?
```

---

**Audit completed.** 🎯

Opus 4.5, у тебя есть всё необходимое. Вперёд!
