# VETKA: Аудит системы памяти и координации агентов

**Дата:** 2026-02-08  
**Фаза:** 118+  
**Статус:** Полный аудит завершён

---

## 📊 Обзор архитектуры памяти

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VETKA MEMORY ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   ENGRAM     │  │     CAM      │  │     STM      │  │     MGC      │   │
│  │  User Memory │  │  (Surprise)  │  │ Short-Term   │  │Multi-Gen     │   │
│  │              │  │              │  │   Memory     │  │   Cache      │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │           │
│         └─────────────────┴─────────────────┴─────────────────┘           │
│                              │                                            │
│                    ┌─────────┴─────────┐                                  │
│                    │  SPIRAL CONTEXT   │                                  │
│                    │    GENERATOR      │                                  │
│                    └─────────┬─────────┘                                  │
│                              │                                            │
│                    ┌─────────┴─────────┐                                  │
│                    │     ELISION       │                                  │
│                    │  (Compression)    │                                  │
│                    └─────────┬─────────┘                                  │
│                              │                                            │
│         ┌────────────────────┼────────────────────┐                       │
│         ▼                    ▼                    ▼                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                   │
│  │  Chat Agent │    │@dragon Pip.│    │  MCP Agent  │                   │
│  │  (Group)    │    │ (Pipeline) │    │ (Autonomous)│                   │
│  └─────────────┘    └─────────────┘    └─────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Детальный анализ компонентов

### 1. ENGRAM User Memory (`engram_user_memory.py`)

**Назначение:** Персистентное хранение предпочтений пользователя

**Архитектура:**
- Гибридная: RAM (hot) + Qdrant (cold)
- UUID5 для конвертации user_id → integer для Qdrant
- Temporal decay: confidence -= 0.05/week
- ELISION интеграция для компрессии

**Проблемы:**
```python
# Строка 95-98: UUID5 может давать коллизии для разных user_id
uuid_value = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)
user_id_int = int(uuid_value.hex[:16], 16)  # Обрезка до 16 hex chars
```

**Риск:** Коллизии UUID5 при большом количестве пользователей

---

### 2. CAM Memory (`cam_memory.py`) ⚠️ ПЕРЕИМЕНОВАТЬ

**Назначение:** Surprise detection для ELISION compression

**Конфликт имён:**
- `cam_memory.py` = Context Awareness Module (surprise detection)
- `cam_routes.py` = Constructivist Agentic Memory (emoji weights)

**Рекомендация:** Переименовать `cam_memory.py` → `surprise_detector.py`

---

### 3. STM Buffer (`stm_buffer.py`)

**Назначение:** Краткосрочная память последних 5-10 взаимодействий

**Проблема дублирования:**
```python
# stm_buffer.py - общий STMBuffer класс
# agent_pipeline.py - свой self.stm список (строка 127)
# orchestrator_with_elisya.py - ElisyaState (строка 65)
```

**3 разных реализации STM!**

---

### 4. MGC Cache - КРИТИЧЕСКОЕ ДУБЛИРОВАНИЕ

**3 разных реализации:**

| Файл | Класс | Назначение |
|------|-------|------------|
| `mgc_cache.py` | `MGCCache` | Общий многоуровневый кеш |
| `spiral_context_generator.py` | `MGCGraphCache` | Кеш для spiral context |
| `arc_solver_agent.py` | `MGCGraphCache` | Кеш для ARC solver |

**Проблема:** Дублирование кода, разные API, нет единого интерфейса

---

### 5. Spiral Context Generator (`spiral_context_generator.py`)

**Назначение:** Генерация контекста для LLM на основе zoom level

**Интеграция:**
- MGC (3 поколения: Gen0/RAM, Gen1/Qdrant, Gen2/Archive)
- ELISION (40-60% token savings)
- HOPE (frequency layers: LOW/MID/HIGH)

**Pi-spiral параметры:**
```python
zoom < 0.3:   ~500 tokens  (LOW layer only)
zoom 0.3-1.0: ~1000 tokens (LOW + MID)
zoom > 1.0:   ~2000 tokens (all layers)
```

---

### 6. ELISION (`elision.py`)

**Назначение:** Компрессия контекста

**Уровни компрессии:**
- Level 1: Key abbreviation
- Level 2: + Path compression
- Level 3: + Vowel skipping (CAM surprise-based)
- Level 4: + Whitespace removal
- Level 5: + Local dictionary

**Использование:**
- ✅ `spiral_context_generator.py`
- ✅ `agent_pipeline.py`
- ❌ Не везде есть fallback при недоступности

---

### 7. Age-Based Compression (`compression.py`)

**Назначение:** Сжатие embeddings по возрасту

**Schedule:**
```
0-6 days:   768D (100% quality)
7-29 days:  768D (99% quality)
30-89 days: 384D (90% quality)
90-180 days: 256D (80% quality)
180+ days:   64D (60% quality)
```

---

## ⚠️ Критические проблемы

### Проблема 1: Тройное дублирование MGC

```python
# mgc_cache.py
class MGCCache:
    def cascade(self, key, data, gen=0): ...

# spiral_context_generator.py
class MGCGraphCache:
    def cascade_update(self, key, data, gen=0): ...

# arc_solver_agent.py
class MGCGraphCache:
    def cascade_update(self, key, graph_state): ...
```

**Решение:** Создать единый `MGCCache` в `mgc_cache.py`, использовать везде

---

### Проблема 2: Дублирование STM

```python
# stm_buffer.py - общий класс
class STMBuffer:
    def add_interaction(self, text, agent, importance=1.0): ...

# agent_pipeline.py - свой список
self.stm: List[Dict[str, str]] = []  # Last N subtask results

# orchestrator_with_elisya.py - ElisyaState
self.elisya_states: Dict[str, ElisyaState] = {}
```

**Решение:** Использовать `STMBuffer` из `stm_buffer.py` везде

---

### Проблема 3: Конфликт имён CAM

```
cam_memory.py    → Context Awareness Module (surprise detection)
cam_routes.py    → Constructivist Agentic Memory (emoji weights)
```

**Решение:**
- `cam_memory.py` → `surprise_detector.py`
- `cam_routes.py` → оставить как есть

---

### Проблема 4: Нет единого Memory Manager

```python
# Сейчас: каждый компонент сам управляет памятью
engram = EngramUserMemory(user_id)
stm = STMBuffer()
mgc = MGCCache()
cam = CAMMemory()  # surprise detector

# Нужно: единый интерфейс
memory = VetkaMemoryManager(user_id)
memory.get_context_for_llm(zoom=0.5, query="...")
```

---

### Проблема 5: Race conditions в singleton

```python
# singletons.py
_compressor_instance: Optional[ElisionCompressor] = None

async def async_compress_context(...):
    compressor = get_elision_compressor()  # Не thread-safe!
```

**Решение:** Добавить threading.Lock

---

## 🧪 Рекомендуемые тесты

### Тест 1: Консистентность MGC

```python
async def test_mgc_consistency():
    """Проверить что все MGC используют один и тот же кеш"""
    from src.memory.mgc_cache import MGCCache
    from src.memory.spiral_context_generator import MGCGraphCache  # должен быть удалён
    
    cache1 = MGCCache()
    cache2 = MGCGraphCache()  # если существует - проблема
    
    # Они должны быть одинаковые
    assert type(cache1) == type(cache2), "Different MGC implementations!"
```

### Тест 2: STM персистентность

```python
async def test_stm_persistence():
    """Проверить что STM сохраняется между сессиями"""
    stm = STMBuffer()
    stm.add_interaction("test", "agent", importance=1.0)
    
    # Перезагрузка
    stm2 = STMBuffer.load_from_disk()
    assert len(stm2.get_recent(1)) == 1
```

### Тест 3: ELISION round-trip

```python
def test_elision_roundtrip():
    """Проверить что ELISION сжимает и восстанавливает без потерь"""
    from src.memory.elision import compress_context, expand_context
    
    original = {"key": "value with some data"}
    compressed = compress_context(original)
    expanded = expand_context(compressed)
    
    assert expanded == original
```

### Тест 4: Memory pressure

```python
async def test_memory_pressure():
    """Проверить поведение при высокой нагрузке"""
    mgc = MGCCache()
    
    # Заполнить Gen0
    for i in range(1000):
        mgc.cascade(f"key_{i}", {"data": "x" * 1000}, gen=0)
    
    # Проверить что произошла миграция в Gen1
    assert len(mgc.generations[0]) <= 100
```

### Тест 5: Конкурентный доступ

```python
async def test_concurrent_access():
    """Проверить thread-safety"""
    import asyncio
    
    mgc = MGCCache()
    
    async def writer(n):
        for i in range(100):
            mgc.cascade(f"key_{n}_{i}", {"data": i})
    
    # Запустить 10 concurrent writers
    await asyncio.gather(*[writer(n) for n in range(10)])
```

---

## 📋 Чеклист рефакторинга

### Приоритет P0 (Критический)

- [ ] **Унифицировать MGC Cache**
  - [ ] Удалить `MGCGraphCache` из `spiral_context_generator.py`
  - [ ] Удалить `MGCGraphCache` из `arc_solver_agent.py`
  - [ ] Расширить `MGCCache` из `mgc_cache.py` при необходимости
  - [ ] Обновить все импорты

- [ ] **Унифицировать STM**
  - [ ] Использовать `STMBuffer` в `agent_pipeline.py`
  - [ ] Использовать `STMBuffer` в `orchestrator_with_elisya.py`
  - [ ] Убрать дублирующие реализации

- [ ] **Переименовать CAM**
  - [ ] `cam_memory.py` → `surprise_detector.py`
  - [ ] Обновить все импорты

### Приоритет P1 (Важный)

- [ ] **Создать Memory Manager**
  ```python
  # src/memory/memory_manager.py
  class VetkaMemoryManager:
      def __init__(self, user_id):
          self.engram = EngramUserMemory(user_id)
          self.stm = STMBuffer()
          self.mgc = MGCCache()
          self.surprise = SurpriseDetector()
      
      def get_context_for_llm(self, zoom, query, pinned_files):
          # Единая точка входа
          ...
  ```

- [ ] **Добавить thread-safety**
  - [ ] Lock для singleton инициализации
  - [ ] Lock для MGC cascade операций
  - [ ] Lock для STM modifications

- [ ] **Улучшить error handling**
  - [ ] Fallback при недоступности ELISION
  - [ ] Fallback при недоступности Qdrant
  - [ ] Graceful degradation

### Приоритет P2 (Желательный)

- [ ] **Метрики памяти**
  - [ ] Cache hit/miss ratio
  - [ ] Compression ratio tracking
  - [ ] Memory usage monitoring

- [ ] **Тесты производительности**
  - [ ] Benchmark MGC cascade
  - [ ] Benchmark ELISION compression
  - [ ] Benchmark context generation

---

## 🎯 Итоговая оценка

| Компонент | Статус | Проблемы | Приоритет |
|-----------|--------|----------|-----------|
| ENGRAM | ✅ Работает | UUID5 коллизии | P2 |
| CAM (surprise) | ⚠️ Переименовать | Конфликт имён | P0 |
| STM | ❌ Дублирование | 3 реализации | P0 |
| MGC | ❌ Дублирование | 3 реализации | P0 |
| ELISION | ✅ Работает | Нет fallback | P1 |
| Spiral | ✅ Работает | Зависит от MGC | - |
| Compression | ✅ Работает | Нет проблем | - |

---

## 🚀 Быстрые победы

### 1. Удалить дублирующие MGC (30 минут)
```bash
# В spiral_context_generator.py заменить:
from src.memory.mgc_cache import MGCCache
self.mgc_cache = MGCCache()

# В arc_solver_agent.py то же самое
```

### 2. Переименовать CAM (15 минут)
```bash
mv src/memory/cam_memory.py src/memory/surprise_detector.py
# Обновить импорты
```

### 3. Добавить thread-safety (20 минут)
```python
# В singletons.py
import threading
_singleton_lock = threading.Lock()

def get_elision_compressor():
    global _compressor_instance
    with _singleton_lock:
        if _compressor_instance is None:
            _compressor_instance = ElisionCompressor()
    return _compressor_instance
```

---

*Аудит выполнен. Система памяти работает, но требует рефакторинга для устранения дублирования и улучшения согласованности.*
