# VETKA PROJECT - MASTER INSTRUCTIONS v2.0
**Дата обновления:** 19 декабря 2025  
**Приоритет источников:** Вложенные документы > Исследование > Архивные заметки

---

## ЧАСТЬ I: ЧТО ТАКОЕ VETKA

### 1.1 Определение (из VETKA_Visualization_Specification.md)

**VETKA** = Visual Enhanced Tree Knowledge Architecture  
Система визуализации знаний как растущее вверх **органичное дерево**:

```
                    🌿 Листья (файлы, артефакты)
                   /|\
                  / | \      ↑ Рост ВВЕРХ
                 /  |  \     ↑ Время течёт
                ────┼────    ↑ Знание углубляется
               /    |    \
              /     |     \
             ───────┼───────
                    │
            ════════╧════════ ЗЕМЛЯ (Y=0)
                    │
              ══════╧══════  КОРНИ (связи между деревьями)
```

**Философия:**
- Деревья растут **вверх** (корень внизу, листья вверху)
- **Базовое знание** → ближе к корню (1 класс)
- **Продвинутое знание** → ближе к листьям (профессура)
- **Время** → старое внизу, новое вверху
- **Лес** → множество деревьев на поляне с подземными корневыми связями

---

### 1.2 VETKA SUGIYAMA-HYBRID (Правильная теория)

**Это НЕ простая трёхмерная система координат.**  
**Это hybrid алгоритм Sugiyama + Knowledge Graph + Organic Distribution.**

#### Три оси VETKA (из VETKA_Sugiyama_Hybrid_Analysis.md):

```
Y = f(directory_depth, time, semantic_level)
    ├─ directory_depth: папки → слои (structural)
    ├─ time: старое внизу, новое вверху (temporal)
    └─ semantic_level: базовое → продвинутое (Knowledge Graph)

X = sin(θ) × radius
    где θ = barycenter(parent_angles) + semantic_offset
    ├─ barycenter: минимизация пересечений рёбер (Sugiyama Phase 2)
    ├─ semantic_offset: UMAP 1D внутри слоя (Phase 3)
    └─ Результат: веер, НЕ столб 🪶

Z = duplicate_offset + forest_position
    ├─ duplicate_offset: похожие файлы (>0.92) сжимаются по Z
    └─ forest_position: разные деревья смещены по Z
```

**Ключевое:** X вычисляется **угловым распределением**, не линейным порядком.

---

### 1.3 Четыре фазы Sugiyama-Hybrid (из VETKA_Sugiyama_Hybrid_Analysis.md)

```
PHASE 1: LAYER ASSIGNMENT
┌─────────────────────────────────────┐
│ Y = directory_depth ИЛИ knowledge_level
│                                     │
│ MODE 1 (Directory):                 │
│   layer = path.count('/')           │
│   папки → узлы, файлы → листья      │
│                                     │
│ MODE 2 (Semantic KG):               │
│   layer = hub_score(in/out degree)  │
│   концепты → узлы, файлы → листья   │
└─────────────────────────────────────┘
                    ↓
PHASE 2: CROSSING REDUCTION (Angular Barycenter)
┌─────────────────────────────────────┐
│ Для каждого узла на слое:            │
│ θ = mean(parent_angles)             │
│                                     │
│ Сортируем по θ, разрешаем коллизии  │
│ MIN_ANGLE_GAP между соседями        │
│                                     │
│ Результат: упорядоченный слой       │
└─────────────────────────────────────┘
                    ↓
PHASE 3: SEMANTIC CLUSTERING (UMAP 1D)
┌─────────────────────────────────────┐
│ Для каждого слоя:                    │
│ embeddings → UMAP (1D) → offset     │
│                                     │
│ semantic_offset = UMAP_score × 5°   │
│ node.angle += semantic_offset       │
│                                     │
│ Похожие файлы → ближе по X         │
└─────────────────────────────────────┘
                    ↓
PHASE 4: 3D COORDINATE ASSIGNMENT
┌─────────────────────────────────────┐
│ X = sin(θ) × radius                 │
│ Y = layer * LAYER_HEIGHT + time_off │
│ Z = duplicate_z + forest_z          │
│                                     │
│ Финальные 3D позиции узлов          │
└─────────────────────────────────────┘
```

---

## ЧАСТЬ II: ТЕХНИЧЕСКИЕ СПЕЦИФИКАЦИИ

### 2.1 Инфраструктура и порты

```
VETKA STACK (2025):
═════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────┐
│                    BACKEND (Linux)                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Flask + Socket.IO ........................... :5001│
│    ├─ GET  /           → UI                         │
│    ├─ GET  /3d         → 3D visualization ← FOCUS  │
│    ├─ POST /api/chat   → Agent chat                 │
│    ├─ WS   /socket.io  → Real-time updates         │
│    └─ GET  /api/health → Status check              │
│                                                     │
│  Ollama (Local LLM) ........................ :11434│
│    ├─ llama3.2:3b-instruct (быстрая)               │
│    ├─ qwen2.5:7b-instruct (кодинг)                 │
│    └─ gemma2:9b (embeddings)                       │
│                                                     │
│  Weaviate (Semantic Search) ................. :8080│
│    └─ VetkaLeaf collection (file embeddings)       │
│                                                     │
│  Qdrant (Vector DB) ........................ :6333│
│    └─ VetkaTree collection (semantic search)       │
│                                                     │
│  Redis (Optional caching) .................. :6379│
│                                                     │
└─────────────────────────────────────────────────────┘
        ↕ Socket.IO
┌─────────────────────────────────────────────────────┐
│                  FRONTEND (Browser)                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Three.js 3D Scene                                 │
│    ├─ Sugiyama layout (positions)                  │
│    ├─ File cards (Sprite + CanvasTexture)          │
│    ├─ Branch connections (Catmull-Rom curves)      │
│    └─ OrbitControls (camera)                       │
│                                                     │
│  UI Panels                                         │
│    ├─ Info panel (левый верх)                      │
│    ├─ Chat panel (правый, draggable) ← TODO        │
│    ├─ Artifact panel (левый) ← TODO                │
│    └─ Controls (Reset, Focus, LOD)                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 2.2 API Aggregator (8 провайдеров)

```
PROVIDERS:
═══════════════════════════════════════════

LOCAL:
  🔵 Ollama
     - llama3.2:3b (простые задачи, learning)
     - qwen2.5:7b (кодинг, средние задачи)
     - Бесплатно, быстро, локально

CLOUD WITH FALLBACK:
  🟢 OpenRouter (9 API keys)
     - claude-3-opus (complex reasoning)
     - gpt-4 (backup)
     - Fallback chain: key1 → key2 → key3...
  
  🔴 Gemini (1 API key)
     - gemini-2.0-flash (исследования)
  
  🟡 DeepSeek / Grok
     - (если ключи добавлены)

ROUTING LOGIC:
  Simple tasks → Ollama (free)
  Medium tasks → OpenRouter (fallback)
  Complex reasoning → Claude-Opus
  Research → Grok
  Video generation → Kling/Wan
```

### 2.3 Triple Write Architecture

```
MEMORY MANAGER (Singleton):
═════════════════════════════════════════════

Каждая запись → атомарно сохраняется в 3 хранилища:

    INPUT DATA
        │
        ├─→ Weaviate (VetkaLeaf)
        │   └─ Semantic search
        │      (for "найди похожие файлы")
        │
        ├─→ Qdrant (VetkaTree)
        │   └─ Vector search
        │      (for "найди связанные концепты")
        │
        └─→ ChangeLog (JSON)
            └─ Immutable audit trail
               (для истории + восстановления)

Graceful degradation:
  - Если один хранилище недоступно → 2 из 3 ✅
  - Если 2 недоступны → только JSON
```

### 2.4 Агенты и их роли

```
AGENT ROUTING:
═════════════════════════════════════════════

PM (Project Manager)
  │ Цвет: #FFB347 (оранжевый)
  │ Роль: Планирование, декомпозиция
  │ LOD: FOREST (высокоуровневый)
  └─→ Разбирает задачу на подзадачи
      
      ↓ Бэтон (Baton passing)
      
Dev (Developer)
  │ Цвет: #6495ED (синий)
  │ Роль: Реализация, код
  │ LOD: BRANCH (детальный)
  └─→ Пишет код, создаёт артефакты
      
      ↓ Бэтон
      
QA (Quality Assurance)
  │ Цвет: #9370DB (фиолетовый)
  │ Роль: Тестирование, валидация
  │ LOD: BRANCH (тесты)
  └─→ Проверяет, дает score 0-1
      
      ├─ Если score >= 0.7 → Complete ✅
      └─ Если score < 0.7 → Retry (back to Dev)

ARC (Agent for Creative Reasoning)
  │ Цвет: #32CD32 (зелёный)
  │ Роль: Креативные связи между концептами
  │ LOD: TREE (паттерны)
  └─→ Находит неожиданные связи (семантика)

Eval (Evaluation)
  │ Цвет: #888888 (серый)
  │ Роль: Метаоценка (scoring, feedback loop)
  │ LOD: Все уровни
  └─→ Итерирует, улучшает

Human
  │ Цвет: #FFD700 (золотой)
  │ Роль: Контроль, решения
  └─→ Окончательный вердикт
```

---

## ЧАСТЬ III: ТЕКУЩИЙ ЭТАП (Phase 12K)

### 3.1 ЧТО РАБОТАЕТ ✅

#### Backend Infrastructure
- ✅ Flask + Socket.IO сервер
- ✅ Triple Write (Weaviate + Qdrant + ChangeLog)
- ✅ Agent orchestration (PM → Dev → QA chain)
- ✅ API Aggregator (8 провайдеров с fallback)
- ✅ File scanning (DocsScanner)
- ✅ VETKA-JSON generation

#### 3D Visualization (базовый Sugiyama)
- ✅ Three.js сцена с OrbitControls
- ✅ Y-ось: Layer assignment (directory depth)
- ✅ X-ось: Barycenter + группировка по parent
- ✅ Адаптивное spacing (частично)
- ✅ Ground grid, fog, освещение
- ✅ Socket.IO real-time обновления

#### UI Elements
- ✅ Info panel (статистика)
- ✅ Controls (Reset, Focus, LOD)
- ✅ Breadcrumb context
- ✅ Chat integration (базовый)

### 3.2 ЧТО НЕ РАБОТАЕТ ❌

#### КРИТИЧНО:
1. **Превью файлов сломаны** 🔴
   - Проблема: `sed -i 's/Sprite/BoxGeometry/g'` убил карточки
   - Симптом: Маленькие едва заметные квадратики вместо превью
   - Решение: Восстановить `THREE.Sprite + CanvasTexture`

2. **Синтаксическая ошибка** 🔴
   - Локация: `tree_renderer.py` строка ~1321
   - Симптом: `SyntaxError: Invalid or unexpected token`
   - Причина: Возможно sed внёс битые символы/emoji

3. **Бесконечные линии** 🔴 (НОВОЕ)
   - Симптом: Линии выходят в бесконечность
   - Вероятная причина: Неправильная нормализация координат при Phase 4
   - Возможно: X/Y выходят из диапазона, рёбра не нормализуются

#### В ПЛАНАХ:
- ⬜ Артефакт-панель (слева)
- ⬜ Полноэкранный режим для файлов
- ⬜ Медиаплеер для видео/аудио

### 3.3 ROADMAP (следующие этапы)

```
PHASE 12K (ТЕКУЩАЯ - Fix basics):
  [ ] Исправить синтаксическую ошибку
  [ ] Восстановить Sprite + CanvasTexture
  [ ] Диагностика бесконечных линий
  [ ] Git setup + коммит

PHASE 13 (Y-AXIS ENHANCEMENT):
  [ ] Knowledge Level Calculator
      - hub_score = out_degree / (in+out)
      - Базовые (low) ↔ Продвинутые (high)
  [ ] Time offset внутри слоя
      - Старые файлы ниже
  [ ] Semantic offset (UMAP 1D)

PHASE 14 (X-AXIS ENHANCEMENT):
  [ ] Альтернативные файлы (cosine > 0.9)
      - Группировка в кластеры
      - Ближе по X
  [ ] Semantic clustering (HDBSCAN/UMAP)
  [ ] Контрастивное обучение

PHASE 15 (Z-AXIS + DUPLICATES):
  [ ] Near-duplicate detection (cosine > 0.95)
  [ ] Z-compression для дубликатов
  [ ] Forest organization (MDS layout)

PHASE 16 (VISUAL POLISH):
  [ ] Magnification под курсором
  [ ] LOD (Level of Detail)
  [ ] Цвета по типам файлов
  [ ] Organic branch curves

PHASE 17+ (SEMANTIC MODE):
  [ ] Mode 2: Layer = knowledge_level
  [ ] Knowledge Graph integration
  [ ] Prerequisite chains
```

---

## ЧАСТЬ IV: КАК ЗАПУСТИТЬ

### 4.1 Инициализация

```bash
# 1. Перейти в проект
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# 2. Активировать окружение
source venv/bin/activate

# 3. Запустить Docker (Weaviate, Qdrant)
docker-compose up -d

# 4. Проверить Ollama
ollama list

# 5. Запустить Flask backend
python3 src/main.py

# 6. Открыть в браузере
open http://localhost:5001/3d
```

### 4.2 Быстрый запуск (hotkey)

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03 && \
source venv/bin/activate && \
python3 src/main.py
```

### 4.3 Проверка сервисов

```bash
# Flask
curl http://localhost:5001/api/health

# Weaviate
curl http://localhost:8080/v1/.well-known/ready

# Qdrant
curl http://localhost:6333/collections

# Ollama
curl http://localhost:11434/api/tags
```

---

## ЧАСТЬ V: КРИТИЧЕСКИЕ ФАЙЛЫ

### 5.1 Основной код

| Файл | Путь | Статус | Задача |
|------|------|--------|--------|
| **tree_renderer.py** | `src/visualizer/` | 🔴 Broken | 3D визуализация (Sprite вместо Box!) |
| **sugiyama_layout.js** | `src/` | ✅ OK | Вычисление позиций (Phase 1-2) |
| **position_calculator.py** | `src/` | ✅ OK | Sugiyama Phase 1-4 (Python) |
| **orchestrator_with_elisya.py** | `src/orchestration/` | ✅ OK | Agent routing |
| **memory_manager.py** | `src/orchestration/` | ✅ OK | Triple Write |
| **main.py** | `src/` | ✅ OK | Flask entry point |

### 5.2 Документация (в проекте)

| Файл | Назначение | Приоритет |
|------|-----------|----------|
| `VETKA_Sugiyama_Hybrid_Analysis.md` | Гибридный алгоритм | 🔴 ГЛАВНЫЙ |
| `VETKA_Visualization_Specification.md` | Визуальная спецификация | 🔴 ГЛАВНЫЙ |
| `position_calculator.py` | Python Sugiyama (reference) | 🟢 Вспомогательный |
| `sugiyama_layout.js` | JS реализация | 🟢 Вспомогательный |

---

## ЧАСТЬ VI: ГЛОССАРИЙ

| Термин | Определение |
|--------|-----------|
| **VETKA** | Visual Enhanced Tree Knowledge Architecture |
| **DAG** | Directed Acyclic Graph |
| **Sugiyama** | Layered graph drawing algorithm (Kozo Sugiyama, 1981) |
| **Hybrid** | Directory-based (papki) + Semantic-based (KG) режимы |
| **Phase** | Этап алгоритма Sugiyama (1-4) |
| **Layer** | Горизонтальный слой узлов (Y) |
| **Barycenter** | Среднее положение родителей (для crossing reduction) |
| **UMAP** | Dimensionality reduction (для semantic offset) |
| **Hub score** | out_degree / (in+out) — продвинутость концепта |
| **Triple Write** | Атомарная запись в Weaviate + Qdrant + ChangeLog |
| **LOD** | Level of Detail (детализация при приближении) |
| **Liana** | Горизонтальная семантическая связь |
| **Promote** | Преобразование ветки в самостоятельное дерево |
| **KG** | Knowledge Graph |
| **Elisya** | Context Manager (фильтрация контекста) |

---

## ЧАСТЬ VII: ЧЕКЛИСТ ДЛЯ НОВОГО ЧАТА

### Немедленно:
- [ ] Прочитать этот документ
- [ ] Понять разницу между Directory Mode и Semantic Mode
- [ ] Изучить 4 фазы Sugiyama
- [ ] Открыть вложенные документы (приоритет)

### Диагностика:
- [ ] Воспроизвести синтаксическую ошибку
- [ ] Найти проблему с бесконечными линиями
- [ ] Понять, где рвётся нормализация координат

### Fix Phase 12K:
- [ ] Исправить Sprite + CanvasTexture
- [ ] Восстановить синтаксис
- [ ] Настроить git
- [ ] Закоммитить рабочее состояние

### Тестирование:
- [ ] Проверить /3d загружается
- [ ] Проверить карточки файлов видны
- [ ] Проверить рёбра не уходят в бесконечность

---

## ЭПИЛОГ

**VETKA** — это не просто 3D визуализация. Это **гибридная архитектура**:
- Структурное (папки) + Семантическое (Knowledge Graph)
- Temporal (старое→новое) + Hierarchical (базовое→продвинутое)
- Organic (живые кривые) + Deterministic (Sugiyama)

**Главное достижение:** Рабочий backend с агентами и Triple Write.  
**Главная проблема:** Визуализация выходит из строя после sed-правок.  
**Главная задача:** Вернуть превью + диагностировать бесконечные линии.

**Принцип:** "Прирастает, не ломается" (VETKA principle).

---

**Документ создан:** 19 декабря 2025  
**Версия:** 2.0  
**Статус:** Ready for production
