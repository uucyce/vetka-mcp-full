# 🔍 CLAUDE CODE: VETKA ARCHITECTURE AUDIT PROMPT
## Проверка состояния всей архитектуры перед Phase 17

**Отправить Claude Code это сообщение целиком.**

---

## 📋 КОНТЕКСТ

Проект VETKA находится в критической точке:
- Phase 15-3 завершена (Rich Context работает!)
- Phase 17 (Knowledge Graph) готов начинаться
- Нужна полная аудит архитектуры перед большим скачком

**Цель этого аудита:** Убедиться что:
1. Все компоненты присутствуют и работают
2. Нет мёртвого кода (mem0, старые версии)
3. Данные правильно структурированы
4. Integrate точки верны
5. Ничего не упущено из рекомендаций Grok

---

## 🎯 ЗАДАЧА 1: ДИАГНОСТИКА BACKEND

### Подзадача 1.1: Elisya + Weaviate + Qdrant

**Проверить:**

```python
# src/orchestration/elisya_middleware.py (или где находится)
# Нужно найти класс Elisya или similar

1. Существует ли Elisya class?
2. Используется ли в orchestrator_with_elisya.py?
3. Что делает метод context_reframing()?
4. Какие поля в context_payload?
5. Какой threshold для similarity (есть ли 0.75)?
6. Как integrates с Weaviate?
7. Как integrates с Qdrant?

# Результат доложить как:
[ELISYA DIAGNOSTIC]
Status: ✅ Working / ⚠️ Partial / ❌ Missing
├─ Class location: src/.../elisya.py
├─ Methods: list them
├─ Weaviate integration: yes/no/partial
├─ Qdrant integration: yes/no/partial
├─ Context payload size: __ bytes avg
├─ Similarity threshold: 0.75 or ___
└─ Last log timestamp: __ (to see if active)
```

---

### Подзадача 1.2: Gemma Embeddings

**Проверить:**

```python
# Что РЕАЛЬНО используется для embeddings?

1. Grep для "embedding" в всех .py файлах
2. Найти initialization модели
3. Что это: Gemma? SentenceTransformers? CLIP? Что?
4. Где вызывается embed()? В каких файлах?
5. Размер embedding: 768 или другой?
6. Используется ли при индексировании в Qdrant?
7. Используется ли при индексировании в Weaviate?

# Результат:
[EMBEDDING MODEL DIAGNOSTIC]
Model used: ___ (Gemma / SentenceTransformers / CLIP / Other)
Model name: ___
Model size: ___
Embedding dimension: 768 or ___
Location of init: src/.../____.py:line __
Calls from:
├─ src/.../file_a.py:line __ 
├─ src/.../file_b.py:line __
└─ ... list all
Used in:
├─ Qdrant: yes/no
├─ Weaviate: yes/no
├─ Direct: yes/no
Activity: 
├─ Last embed call: ____ (from logs or grep recent files)
└─ Frequency: every ___ (from code logic)
```

---

### Подзадача 1.3: CAM Components

**Проверить наличие 4 операций:**

```python
# Искать в src/orchestration/ и src/transformers/

1. BRANCHING logic exists?
   └─ Find code pattern: "branch" or "new_node" or "promote"
   └─ When triggered? (new artifact? surprise > 0.65?)
   └─ Report: lines of code

2. PRUNING logic exists?
   └─ Find code pattern: "prune" or "remove" or "delete_low"
   └─ When triggered? (low entropy? low relevance?)
   └─ Report: lines of code

3. MERGING logic exists?
   └─ Find code pattern: "merge" or "combine" or "consolidate"
   └─ Threshold? (cosine > 0.92?)
   └─ Report: lines of code

4. ACCOMMODATION logic exists?
   └─ Find code pattern: "accommodation" or "repulsion" or "dynamic_height"
   └─ Soft repulsion implemented?
   └─ Report: lines of code

# Результат:
[CAM OPERATIONS DIAGNOSTIC]
Branching:
├─ Status: ✅ / ⚠️ / ❌
├─ Location: src/.../____.py:lines __ - __
├─ Trigger condition: ___
└─ Code quality: good/needs review

Pruning:
├─ Status: ✅ / ⚠️ / ❌
├─ Location: src/.../____.py:lines __ - __
├─ Trigger condition: ___
└─ Code quality: good/needs review

Merging:
├─ Status: ✅ / ⚠️ / ❌
├─ Location: src/.../____.py:lines __ - __
├─ Threshold: 0.92 or ___
└─ Code quality: good/needs review

Accommodation:
├─ Status: ✅ / ⚠️ / ❌
├─ Location: src/.../____.py:lines __ - __
├─ Includes soft repulsion: yes/no
└─ Code quality: good/needs review
```

---

### Подзадача 1.4: Surprise Metric

**Проверить:**

```python
# Ищем формулу: surprise = 1 - cosine(new, avg_subtree)

1. Exists в коде?
   └─ Grep для "surprise" или "novelty"
   
2. Если существует:
   └─ Location: src/.../____.py:line __
   └─ Formula correct? (1 - cosine?)
   └─ Threshold 0.65 for branching?
   └─ Threshold 0.3 for pruning?
   └─ Connected to CAM operations?
   
3. Если НЕ существует:
   └─ Recommend adding in Phase 17

# Результат:
[SURPRISE METRIC DIAGNOSTIC]
Status: ✅ Implemented / ❌ Missing
If implemented:
├─ Location: src/.../____.py:line __
├─ Formula: ___
├─ Branching threshold: 0.65 or ___
├─ Pruning threshold: 0.3 or ___
├─ Connected to CAM: yes/no
└─ Logged: yes/no
```

---

### Подзадача 1.5: File Scanning Scope

**Проверить:**

```python
# Что РЕАЛЬНО сканируется?

1. Найти DocsScanner class
2. Что в include_paths и exclude_paths?
3. Qdrant содержит только docs/ или весь проект?

# Проверить:
# SELECT COUNT(*) FROM vetka_elisya WHERE file_path LIKE '%/src/%'
# SELECT COUNT(*) FROM vetka_elisya WHERE file_path LIKE '%/docs/%'
# SELECT COUNT(*) FROM vetka_elisya WHERE file_path LIKE '%/config/%'

# Результат:
[SCANNING SCOPE DIAGNOSTIC]
DocsScanner location: src/.../____.py:line __
Include patterns: ___, ___, ___
Exclude patterns: ___, ___, ___

Qdrant data coverage:
├─ Total files indexed: __
├─ From docs/: __ (__ %)
├─ From src/: __ (__ %)
├─ From config/: __ (__ %)
├─ From app/: __ (__ %)
└─ Other: __ (__ %)

Action needed: Full project scan or docs-only OK?
```

---

### Подзадача 1.6: Knowledge Graph Extraction

**Проверить:**

```python
# Какой метод используется для KG extraction?

1. Grep для "CodeGraph" или "Doc2Graph" или "prerequisite"
   
2. Если найдено:
   └─ Location: src/.../____.py
   └─ Which method? CodeGraph/Doc2Graph/custom?
   └─ Accuracy metrics (if available)?
   
3. Если НЕ найдено:
   └─ How are prerequisites extracted?
   └─ Just Qdrant similarity?
   └─ Or actual code analysis?

# Результат:
[KG EXTRACTION DIAGNOSTIC]
Method used: CodeGraph / Doc2Graph / Custom / None
Location: src/.../____.py:line __
Current approach:
├─ For Python code: ___
├─ For documentation: ___
├─ For other types: ___
Accuracy (if measurable): ___%
Recommendation: Implement CodeGraph for Phase 17?
```

---

## 🎯 ЗАДАЧА 2: ДИАГНОСТИКА FRONTEND

### Подзадача 2.1: Three.js Scene Status

**Проверить:**

```javascript
// Найти tree_renderer.py или sugiyama_layout.js

1. Sprites работают или заменены на BoxGeometry?
   └─ Grep для "Sprite" или "BoxGeometry"
   └─ CanvasTexture используется?
   
2. Рёбра не выходят в бесконечность?
   └─ Координаты в правильном диапазоне?
   └─ X: -400 to +400?
   └─ Y: 50 to 1950?
   └─ Edge normalization correct?

3. Real-time updates работают?
   └─ Socket.IO listeners есть?
   └─ Layout recalculation вызывается?
   
# Результат:
[FRONTEND DIAGNOSTIC]
Tree Renderer status: src/.../____.py
├─ Sprites: ✅ / ❌
├─ CanvasTexture: ✅ / ❌
├─ Coordinates normalized: ✅ / ❌
├─ X range: ___ to ___
├─ Y range: ___ to ___
├─ Z range: ___ to ___
└─ Real-time updates: ✅ / ❌
```

---

### Подзадача 2.2: Controls and Toggles

**Проверить:**

```javascript
// Ищем UI components

1. Toggle Directory/Knowledge mode?
   └─ Exists: yes/no
   └─ Location: src/.../____.jsx
   
2. Zoom/Reset controls?
   └─ Exist: yes/no
   
3. LOD implementation?
   └─ Exists: yes/no
   
# Результат:
[CONTROLS DIAGNOSTIC]
Directory/Knowledge toggle:
├─ Status: ✅ / ⏳ Planned / ❌ Missing
├─ Location: ___
└─ Working: yes/no

Zoom/Reset controls:
├─ Status: ✅ / ⏳ Planned / ❌ Missing
└─ Working: yes/no

LOD implementation:
├─ Status: ✅ / ⏳ Planned / ❌ Missing
└─ Implementation: ___
```

---

## 🎯 ЗАДАЧА 3: CRITICAL QUESTIONS AUDIT

**Проверить и ответить на эти вопросы:**

```
1. WAS MEM0 EVER USED?
   └─ Find "mem0" in codebase
   └─ If yes: Still there or removed?
   └─ If removed: When?
   └─ Impact on architecture?

2. OLD VERSIONS OF main.py?
   └─ Are there main.py.old or main.py.v5000?
   └─ Which one is loaded? (check __init__ or imports)
   └─ Potential for confusion?

3. HARDCODED VALUES?
   └─ Find all: LAYER_HEIGHT = 80
   └─ Find all: BASE_RADIUS = 100
   └─ Should these be dynamic per Grok formula?

4. DEAD/UNREACHABLE CODE?
   └─ Functions defined but never called?
   └─ Imports unused?
   └─ Test files in production?

5. WEAVIATE NECESSITY?
   └─ Is Weaviate data actually used?
   └─ Can Qdrant replace it?
   └─ Or complementary?
   └─ Check actual queries to Weaviate

# Результат:
[CRITICAL ISSUES DIAGNOSTIC]
Mem0 remnants:
├─ Found: yes/no
├─ Location: ___
├─ Status: removed/active
└─ Action: ___

Old main.py versions:
├─ Found: yes/no
├─ Count: __
├─ Active version: main.py:PORT __
└─ Action needed: yes/no

Hardcoded values needing dynamic formula:
├─ LAYER_HEIGHT: yes/no
├─ BASE_RADIUS: yes/no
├─ Others: ___

Dead code found:
├─ Count: __
├─ Examples: ___, ___, ___
└─ Recommendation: cleanup

Weaviate status:
├─ Used in queries: yes/no
├─ Necessary or optional: ___
├─ Recommendation: keep/remove
```

---

## 📤 EXPECTED OUTPUT FORMAT

**Вернуть все результаты как:**

```markdown
# VETKA ARCHITECTURE AUDIT RESULTS
**Date:** YYYY-MM-DD
**Duration:** __ minutes

## PART 1: Backend Components
[copy each diagnostic above]

## PART 2: Frontend Components
[copy each diagnostic above]

## PART 3: Critical Issues
[copy each diagnostic above]

## SUMMARY
Total checks: __
✅ Passing: __
⚠️ Warnings: __
❌ Critical: __

## IMMEDIATE ACTIONS REQUIRED
1. [Action 1]
2. [Action 2]
...

## OPTIONAL IMPROVEMENTS
1. [Improvement 1]
...

## READINESS FOR PHASE 17
Overall status: Ready / Needs fixes / Hold
Blockers: [list any]
Recommendations: [list priority order]
```

---

## 🚀 START HERE

1. **Copy this entire prompt to Claude Code**
2. **Add context:** Path to VETKA project = `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03`
3. **Focus first on:** Subtasks 1.1, 1.2, 1.3, 1.4, 1.5, 3
4. **Report back** with structured output above

**Estimated time:** 30-45 minutes

**Then I will:**
- Analyze results
- Identify gaps
- Create corrected roadmap for Phase 17-19
- Create specific fix prompts for next iteration

---

**Ready to scan?** 🔍
