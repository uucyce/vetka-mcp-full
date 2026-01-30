# 🌳 VETKA PROJECT INSTRUCTIONS
## Phase 67+ | Context-Aware Self-Learning System

**Last Updated:** 2026-01-18
**Current Phase:** 67 (CAM + Qdrant → Context Assembly Integration)

---

## 📌 PROJECT IDENTITY

**Название:** VETKA (Visual Enhanced Tree Knowledge Architecture)
**Vision:** "VETKA — workshop for agents, spacesuit for humans"
**Владелец:** Данила (@danilagoleen)

### Путь к проекту:
```
/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/
```

### Git Remote:
```
origin  https://github.com/danilagoleen/vetka.git (fetch)
origin  https://github.com/danilagoleen/vetka.git (push)
```

---

## 🔒 GIT SYNC POLICY (ОБЯЗАТЕЛЬНО!)

### После КАЖДОЙ фазы работы:

```bash
git add .
git commit -m "Phase XX.X: [описание на английском]"
git push origin main
```

### Проверка push:
```bash
git log origin/main --oneline -3
```

### В конце КАЖДОГО ответа с изменениями кода:
```
💾 Git Status:
- Commits: [список коммитов]
- Pushed to: github.com/danilagoleen/vetka ✅
```

### ❌ НИКОГДА:
- Не создавай новые remotes
- Не пуши в другие репозитории
- Не оставляй коммиты без push
- Если push не удался — СТОП, сообщи пользователю

---

## 🏗️ АРХИТЕКТУРА (Актуальная на Phase 67)

```
VETKA/
├── src/
│   ├── api/handlers/
│   │   ├── message_utils.py      ← 🎯 КЛЮЧЕВОЙ ФАЙЛ Phase 67
│   │   ├── user_message_handler.py
│   │   ├── chat_handler.py
│   │   ├── streaming_handler.py
│   │   └── workflow_handler.py
│   │
│   ├── orchestration/
│   │   ├── cam_engine.py         ← ✅ 840+ lines, ГОТОВ
│   │   ├── cam_event_handler.py  ← ✅ 526 lines, ГОТОВ
│   │   ├── memory_manager.py     ← TripleWrite
│   │   └── orchestrator_with_elisya.py
│   │
│   ├── memory/
│   │   ├── qdrant_client.py      ← ✅ Vector search, ГОТОВ
│   │   ├── vetka_weaviate_*.py   ← ⚠️ Config only, не интегрировано
│   │   └── hostess_memory.py
│   │
│   ├── agents/
│   │   ├── eval_agent.py         ← ✅ 560 lines, ГОТОВ
│   │   ├── learner_agent.py      ← ✅ Готов
│   │   └── [PM, Dev, QA, Architect]
│   │
│   └── utils/
│       └── embedding_service.py  ← ✅ Gemma 768D embeddings
│
├── app/frontend/                 ← React + Three.js
├── docs/                         ← Phase documentation
├── data/                         ← Runtime data
└── main.py                       ← Flask app (~7000 lines)
```

---

## 📊 СТАТУС КОМПОНЕНТОВ

### ✅ Полностью реализовано:
| Компонент | Файл | Строки | Статус |
|-----------|------|--------|--------|
| CAM Engine | cam_engine.py | 840+ | ✅ Branching, Pruning, Merging |
| CAM Events | cam_event_handler.py | 526 | ✅ Event-driven |
| Surprise Metric | cam_engine.py:688 | — | ✅ calculate_surprise_for_file() |
| Activation Score | cam_engine.py:195 | — | ✅ 0.0-1.0 per node |
| Qdrant Client | qdrant_client.py | 350+ | ✅ TripleWrite, search |
| Embeddings | embedding_service.py | — | ✅ Gemma 768D |
| EvalAgent | eval_agent.py | 560 | ✅ Готов |
| God Object Split | handlers/*.py | — | ✅ Phase 64 complete |

### ❌ НЕ интегрировано (Phase 67 цель):
| Проблема | Файл | Что нужно |
|----------|------|-----------|
| Context Assembly | message_utils.py:72-107 | Подключить Qdrant + CAM |
| Weaviate | vetka_weaviate_*.py | Интегрировать в TripleWrite |
| EvalAgent | orchestrator.py | Вызывать после QA |
| LearnerAgent | orchestrator.py | Trigger на score < 0.7 |

---

## 🎯 PHASE 67: ГЛАВНАЯ ЗАДАЧА

### Проблема:
```python
# СЕЙЧАС (message_utils.py):
def build_pinned_context(pinned_files, max_files=10):
    content = load_pinned_file_content(file_path)  # ← ТУПО ЧИТАЕТ
    # НЕТ: Qdrant query
    # НЕТ: CAM activation_score
    # НЕТ: Smart selection
```

### Решение:
```python
# НУЖНО:
def build_pinned_context(pinned_files, user_query="", max_files=5, max_tokens=4000):
    # 1. Embed user_query
    # 2. Query Qdrant для relevance
    # 3. Get CAM activation_score
    # 4. Rank: 0.7 * qdrant_sim + 0.3 * cam_activation
    # 5. Take top N
    # 6. Smart truncate
```

---

## 🔧 КЛЮЧЕВЫЕ ИНТЕГРАЦИИ

### Qdrant Search:
```python
from src.memory.qdrant_client import get_qdrant_client
qdrant = get_qdrant_client()
results = qdrant.search_by_vector(query_vector, limit=10, score_threshold=0.5)
```

### CAM Activation:
```python
from src.orchestration.cam_engine import get_cam_engine
cam = get_cam_engine()
score = cam.calculate_activation_score(node_id)
```

### Embeddings:
```python
from src.utils.embedding_service import get_embedding_service
emb = get_embedding_service()
vector = await emb.get_embedding(text)
```

### CAM Thresholds:
```python
SIMILARITY_THRESHOLD_NOVEL = 0.7   # → create_new_branch()
SIMILARITY_THRESHOLD_MERGE = 0.92  # → merge()
ACTIVATION_THRESHOLD_PRUNE = 0.2   # → mark_for_deletion()
```

---

## 📡 SOCKET.IO EVENTS

### Существующие:
```
agent_started, agent_progress, agent_complete
stream_start, stream_token, stream_end
tree_structure_updated
```

### Phase 29+ (добавить):
```
eval_started, eval_complete          # EvalAgent
learner_started, learner_complete    # LearnerAgent
cam_branching, cam_merging, cam_pruning  # CAM ops
context_assembled                    # Phase 67
```

---

## 🧪 ТЕСТИРОВАНИЕ

### Запуск тестов:
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
pytest tests/ -v
```

### Проверка импортов:
```bash
python -c "from src.api.handlers import *; print('OK')"
python -c "from src.orchestration.cam_engine import get_cam_engine; print('OK')"
python -c "from src.memory.qdrant_client import get_qdrant_client; print('OK')"
```

---

## 📋 WORKFLOW ДЛЯ CLAUDE CODE

### Перед началом работы:
1. `git pull origin main`
2. `git status` — убедиться что clean
3. Прочитать релевантные файлы

### Во время работы:
1. Делать небольшие изменения
2. Тестировать после каждого изменения
3. Не ломать существующий функционал

### После завершения:
```bash
git add .
git commit -m "Phase XX.X: [description]"
git push origin main
git log origin/main --oneline -3
```

### Формат ответа:
```
✅ Изменения:
- [файл]: [что изменено]

🧪 Тесты:
- [результат]

💾 Git Status:
- Commits: Phase XX.X: description
- Pushed to: github.com/danilagoleen/vetka ✅
```

---

## ⚠️ ВАЖНЫЕ ПРАВИЛА

### ❌ НЕ ДЕЛАТЬ:
- Не трогать cam_engine.py без необходимости (он готов)
- Не менять API контракты существующих функций
- Не удалять fallback логику
- Не создавать новые remotes
- Не коммитить без push

### ✅ ДЕЛАТЬ:
- Добавлять fallback к старой логике
- Логировать: `[CONTEXT] Using smart selection: {n} files`
- Тестировать после каждого изменения
- Пушить после каждой фазы

---

## 📚 ДОКУМЕНТАЦИЯ

### Ключевые файлы:
- `docs/65_phases/PHASE_66_3_CAM_AUDIT.md` — CAM аудит
- `docs/65_phases/PHASE_66_2_SUMMARY.txt` — Embeddings аудит
- `docs/PHASE_64_DEPENDENCY_MAP.md` — Handlers структура

### Phase History:
- **Phase 29:** CAM + LangGraph (спецификация)
- **Phase 35-54:** CAM реализация
- **Phase 64:** God Object Split
- **Phase 65:** Hotkeys (shift=pin, ctrl=move)
- **Phase 66:** Аудиты (embeddings, CAM)
- **Phase 67:** Context Assembly Integration ← ТЕКУЩАЯ

---

## 🎯 ACCEPTANCE CRITERIA (Phase 67)

1. ✅ `build_pinned_context()` принимает `user_query`
2. ✅ Использует Qdrant semantic search
3. ✅ Использует CAM activation_score
4. ✅ Fallback к старой логике если сервисы недоступны
5. ✅ Все существующие тесты проходят
6. ✅ Логирование контекста

---

## 📈 ROADMAP: Phase 65-68

### ✅ СДЕЛАНО (Phase 54-64):

| Фича | Статус | Phase |
|------|--------|-------|
| Multi-model chat | ✅ | 56 |
| ModelProvider enum (все провайдеры) | ✅ | 64 |
| LOD система (Google Maps стиль) | ✅ | 62 |
| File preview on hover | ✅ | 61 |
| Multi-file pin (Ctrl+Click) | ✅ | 61 |
| God object split | ✅ | 64 |
| User messages saving | ✅ | 64 |
| Unified key manager | ✅ | 63 |
| Group chat (команды агентов) | ✅ | 57 |
| LangGraph 1.0 | ✅ | 29+ |
| Researcher agent | ✅ | ? |
| Hotkeys (Shift=pin, Ctrl=move) | ✅ | 65 |
| CAM Engine (full implementation) | ✅ | 35-54 |

---

### ❌ НЕ СДЕЛАНО (приоритеты):

#### 🔴 HIGH PRIORITY:

| # | Фича | Описание | Сложность |
|---|------|----------|-----------|
| 1 | Branch pin (Alt+Click) | Выделить папку → все файлы в контекст | 2-3ч |
| 2 | Search (text) | Поиск по словам в файлах | 4-5ч |
| 3 | Search (semantic) | Поиск по тегам/embeddings | 6-8ч |
| 4 | Sugiyama directed mode | Исправить формулы layout | 4-6ч |
| 5 | Move branch (not just node) | Двигать ветку целиком | 3-4ч |

#### 🟡 MEDIUM PRIORITY:

| # | Фича | Описание | Сложность |
|---|------|----------|-----------|
| 6 | Knowledge mode | Граф связей, knowledge level (дерево) | 8-10ч |
| 7 | Create new trees | Создавать деревья через UI | 4-5ч |
| 8 | Live tree physics | Двигаешь корень → двигается всё | 6-8ч |
| 9 | Folder context | Клик на папку → контекст всех файлов | 3-4ч |

#### 🟢 JARVIS MODE (Advanced):

| # | Фича | Описание | Сложность |
|---|------|----------|-----------|
| 10 | Auto Hostess rotation | Ротация моделей незаметно для user | 8-10ч |
| 11 | User memory | История работы, личность user | 10-15ч |
| 12 | Unified agent (JARVIS) | Один агент = много моделей под капотом | 15-20ч |
| 13 | Chat-first settings | Настройки через чат, не UI | 5-6ч |

---

### 📋 ПОРЯДОК ФАЗ (Phase 65+):

```
Phase 65: Branch Context + Search ← ЧАСТИЧНО СДЕЛАНО
├── 65.1: Shift+Click → pin file ✅ DONE
├── 65.2: Ctrl+Click → move node ✅ DONE  
├── 65.3: Alt+Click → pin entire branch (2-3ч) ❌ TODO
├── 65.4: Folder click → folder context (3-4ч) ❌ TODO
├── 65.5: Text search (4-5ч) ❌ TODO
└── 65.6: Semantic search (6-8ч) ❌ TODO

Phase 66: Tree Improvements + Audits ← ЧАСТИЧНО СДЕЛАНО
├── 66.1: Embeddings audit ✅ DONE
├── 66.2: CAM audit ✅ DONE
├── 66.3: Move branch (not just node) (3-4ч) ❌ TODO
├── 66.4: Sugiyama directed fix (4-6ч) ❌ TODO
└── 66.5: Live tree physics (6-8ч) ❌ TODO

Phase 67: Context Assembly + Knowledge Mode ← ТЕКУЩАЯ
├── 67.1: CAM + Qdrant → Context (4-5ч) 🔄 IN PROGRESS
├── 67.2: Graph layout (tree) (4-5ч) ❌ TODO
├── 67.3: Semantic links (4-5ч) ❌ TODO
└── 67.4: Create new trees UI (4-5ч) ❌ TODO

Phase 68: EvalAgent + LearnerAgent
├── 68.1: EvalAgent call after QA (3-4ч) ❌ TODO
├── 68.2: LearnerAgent on failures (4-5ч) ❌ TODO
├── 68.3: Learning examples storage (3-4ч) ❌ TODO
└── 68.4: Agent Work Panel (React) (6-8ч) ❌ TODO

Phase 69: JARVIS Mode (Hostess Evolution)
├── 69.1: Auto model rotation (8-10ч) ❌ TODO
├── 69.2: User memory system (10-15ч) ❌ TODO
├── 69.3: Unified agent facade (10-15ч) ❌ TODO
└── 69.4: Chat-first settings (5-6ч) ❌ TODO
```

---

### ⏱️ TIMELINE ОЦЕНКА:

| Phase | Время | Приоритет | Статус |
|-------|-------|-----------|--------|
| 65: Branch + Search | 15-20ч | 🔴 HIGH | 🔄 Partial |
| 66: Tree Improvements | 13-18ч | 🔴 HIGH | 🔄 Partial |
| 67: Context + Knowledge | 12-15ч | 🟡 MEDIUM | 🔄 In Progress |
| 68: Eval + Learner | 16-21ч | 🟡 MEDIUM | ❌ Not Started |
| 69: JARVIS | 35-45ч | 🟢 ADVANCED | ❌ Not Started |

**Total: ~90-120 часов (4-5 недель при 4ч/день)**

---

### 🎯 БЛИЖАЙШИЕ ЗАДАЧИ (This Week):

1. **Phase 67.1:** Интеграция CAM + Qdrant в `build_pinned_context()` 🔄
2. **Phase 65.3:** Alt+Click для pin entire branch
3. **Phase 65.5:** Text search implementation

---

**Let's build context-aware VETKA! 🚀**
