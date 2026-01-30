# 🚀 VETKA CHAT + ARTIFACTS - ЧЕКЛИСТ И РОАДМЭП
**Дата:** 21 декабря 2025  
**Статус:** Analyzing current state (Phase 12.5)  
**Цель:** Chat + Elisya + Артефакты = полная интеграция агентов

---

## 📊 ТЕКУЩЕЕ СОСТОЯНИЕ (честная оценка)

### ✅ ЧТО УЖЕ РАБОТАЕТ

#### Backend Infrastructure (ГОТОВО)
- ✅ Flask + Socket.IO сервер
- ✅ Agent orchestration (PM → Dev → QA → Eval)
- ✅ Triple Write (Weaviate + Qdrant + ChangeLog)
- ✅ API Aggregator (8 провайдеров с fallback)
- ✅ Elisya written (Context Manager)
- ✅ File scanning (DocsScanner)

#### 3D Visualization (РАБОТАЕТ)
- ✅ Three.js + Sugiyama hybrid
- ✅ Directory tree visualization
- ✅ Real-time Socket.IO updates
- ✅ Y-axis: directory depth layers
- ✅ X-axis: angular distribution

#### Chat Infrastructure (ЧАСТИЧНО)
- ✅ Chat panel справа (resizable)
- ✅ Socket.emit(`user_message`) работает
- ✅ Socket.on(`agent_message`) listening работает
- ✅ Resize угол для панели (в работе у Claude Code)

### ❌ ЧТО НЕ РАБОТАЕТ ИЛИ ТРЕБУЕТ ДОДЕЛКИ

#### Chat + Elisya Integration (ТРЕБУЕТ ДОДЕЛКИ)
- ⚠️ **node_path не передаётся в socket.emit** 
  - Текущее: просто текст
  - Нужное: {text, node_id, node_path, semantic_query}
  - Статус: Tasks 1-2 отправлены Claude Code

- ⚠️ **Elisya контекст не используется в backend**
  - @socketio.on('user_message') получает данные, но не фильтрует файл
  - Нужно: get_file_context_with_elisya(node_path) → ключевые строки
  - Статус: Код написан, но не интегрирован

- ⚠️ **Ответы агентов не используют контекст**
  - Текущее: generic "Got it! I'm analyzing..."
  - Нужное: ответ с file_summary + relevant code lines
  - Статус: Код есть, нужна интеграция

#### Artifacts Panel (НЕ РАБОТАЕТ)
- ❌ **Левая панель артефактов не реализована**
  - Должна быть: preview файла, медиаплеер, текстовой редактор, канвас
  - Сейчас: вообще не создана

- ❌ **Автоматическое создание артефакта**
  - Когда: если ответ > 500 chars ИЛИ содержит code
  - Процесс: agent → format artifact → emit → save file → add to tree
  - Статус: процесс не определён

- ❌ **Artifact HTML структура**
  - Нужно: медиаплеер для видео/аудио
  - Нужно: текстовой редактор (CodeMirror или Ace)
  - Нужно: canvas для рисования
  - Нужно: preview for images/documents
  - Статус: не начиналось

#### Integration Points (ПРОПУЩЕНО)
- ❌ **Artifact → File creation**
  - Где создавать файл? (рядом с текущей веткой? В special folder?)
  - Какой формат? (.md, .json, зависит от типа?)
  - Как обновить VETKA-JSON в tree_data.json?
  - Статус: НЕ ОПРЕДЕЛЕНО

- ❌ **File → Tree integration**
  - Когда artifact создан → нужно добавить листья в дерево
  - Sugiyama recalculation?
  - Soft force relaxation для новых листьев?
  - Статус: НЕ ОПРЕДЕЛЕНО

- ❌ **LangGraph integration**
  - Планировалось для agent workflow
  - Статус: не начиналось

#### CAM Integration (ТРЕБУЕТ ИССЛЕДОВАНИЯ)
- ❌ **Branching** (новые листья = новые ветки?)
- ❌ **Accommodation** (перестройка дерева при новых артефактах?)
- ❌ **Pruning** (удаление дубликатов?)
- ❌ **Merging** (объединение похожих веток?)
- Статус: **НУЖНО ИССЛЕДОВАНИЕ от Grok**

---

## 🗺️ ФАЗЫ (правильный порядок)

### PHASE 0: CLAUDE CODE TASKS (IN PROGRESS)
```
Отправлено Claude Code две задачи:

TASK 1: ✅ Resize handle в чат-панели
├─ HTML структура (одна панель справа, левая зарезервирована)
├─ CSS для resize
├─ JS для drag resize
└─ Тест: можно тащить уголок вправо/влево

TASK 2: ✅ Elisya context integration
├─ selectNode() должен передавать node_path
├─ socket.emit('user_message') должен включать контекст
├─ Backend должен получать контекст
└─ Тест: в консоли видны контекст данные

ЗАДАЧА 3 (ЕЩЕ НЕ ОТПРАВЛЕНА):
├─ Две панели HTML (left для артефактов, right для чата)
├─ CSS для обеих
├─ JS для resize между панелями
└─ Тест: обе видны, обе раздвигаются
```

**Когда закончит Claude Code Task 1-2 → идем на Phase 1**

### PHASE 1: ELISYA BACKEND INTEGRATION (1-2 часа)
```
Цель: Агенты получают контекст и выдают нормальные ответы

1. ✅ Code exists (из промта)
   ├─ get_file_context_with_elisya(node_path, query)
   └─ Возвращает: {summary, key_lines, error}

2. [ ] Integrate in main.py
   ├─ @socketio.on('user_message')
   ├─ + Elisya call
   ├─ + Enhanced prompts для agentов
   └─ + emit с контекстом

3. [ ] Тест
   ├─ Открыть /3d
   ├─ Кликнуть на Python файл
   ├─ Написать вопрос
   ├─ В консоли должен быть контекст

✅ RESULT: Agents say real things about real files!
```

**КРИТИЧЕСКОЕ УТОЧНЕНИЕ:**
- Какой **точный путь** к файлам? (`/Users/danilagulin/...` или relative?)
- Есть ли **fallback** если файл не читается?
- Какие **file types** поддерживаются? (код? PDF? Images?)

---

### PHASE 2: ARTIFACT ARCHITECTURE DEFINITION (2-4 часа)
```
Цель: Определить как создаются артефакты

1. Artifact trigger
   ├─ Option A: Size-based (response.length > 500)
   ├─ Option B: Type-based (contains code? images? has JSON?)
   ├─ Option C: Agent-directed ("create_artifact=true" in response)
   └─ РЕКОМЕНДАЦИЯ: Комбинация A+C (если large ИЛИ явно создан)

2. Artifact format
   ├─ JSON schema: {type, content, language, metadata}
   ├─ Type: 'code' | 'document' | 'media' | 'canvas'
   ├─ Storage: файл на диск + reference в tree_data.json
   └─ Example:
      {
        "id": "artifact_20251221_001",
        "type": "code",
        "language": "python",
        "content": "...",
        "created_by": "Dev",
        "created_at": "2025-12-21T...",
        "parent_node": "src/main.py",
        "tags": ["fix", "async"]
      }

3. Artifact file location
   ├─ Option A: Рядом с файлом (src/main.py → src/main_artifact_001.py)
   ├─ Option B: В special folder (artifacts/artifact_001.json)
   ├─ Option C: В VETKA JSON как embedded (tree_data.json)
   └─ РЕКОМЕНДАЦИЯ: Option B (cleaner)

4. Tree integration
   ├─ Artifact → листья в дереве
   ├─ parent_node_id = текущий узел
   ├─ Sugiyama recalculation? (да!)
   ├─ Soft repulsion для новых листьев? (да!)
   └─ Real-time Socket.IO emit

НУЖНО ИССЛЕДОВАНИЕ:
├─ Какой формат файла лучше? (JSON? YAML? маппировать на тип?)
├─ Где хранить? (в project/ или в vetka_live_03/?)
├─ Как обновлять дерево без пересчета всего Sugiyama?
└─ Как интегрировать с CAM (branching/pruning)?

>>> SEND TASK TO GROK: "Artifact architecture for VETKA"
```

---

### PHASE 3: LEFT PANEL - ARTIFACT VIEWER (4-6 часов)
```
Цель: Левая панель показывает артефакты с нужными контролами

1. HTML Structure
   ├─ Панель слева (резервируется в Phase 0)
   ├─ Вкладки: File preview | Media | Editor | Canvas
   ├─ Динамический контент по типу artifact
   └─ Close button

2. File Preview (для всех типов)
   ├─ Image: <img src="artifact.png">
   ├─ PDF: pdf.js или embed
   ├─ Code: syntax highlighted (CodeMirror)
   ├─ Document: markdown rendered (marked.js)
   └─ Media: <video> или <audio>

3. Media Player (если artifact.type='media')
   ├─ Video: <video controls>
   ├─ Audio: <audio controls>
   ├─ Плейлист (если несколько медиа?)
   └─ Timeline seeking

4. Text Editor (если artifact.type='code' или 'document')
   ├─ CodeMirror или Ace.js
   ├─ Syntax highlighting по языку
   ├─ Line numbers
   ├─ Read-only или editable? (DECISION NEEDED)
   └─ Save button? (DECISION NEEDED)

5. Canvas (если artifact.type='canvas')
   ├─ HTML5 Canvas element
   ├─ Drawing tools (pencil, eraser, colors)
   ├─ Save as PNG
   └─ Load from file

6. JavaScript
   ├─ Socket.on('artifact_created')
   ├─ Render в левой панели
   ├─ Handle switch between tabs
   └─ Save/close logic

ТЕХНИЧЕСКИЕ ДЕТАЛИ:
├─ CodeMirror или Ace? (CodeMirror более легкий)
├─ PDF viewer library? (pdf.js самый populär)
├─ Canvas library? (plain HTML5 или Fabric.js?)
└─ Drag-to-resize между панелями?
```

---

### PHASE 4: ARTIFACT CREATION FLOW (3-4 часа)
```
Цель: От агента до файла до дерева

1. Agent generates artifact
   ├─ LLM output:
      "Response text...
       <artifact>
       {
         "type": "code",
         "language": "python",
         "content": "def foo():..."
       }
       </artifact>"
   ├─ Parse artifact из response
   ├─ Validate JSON schema
   └─ emit('artifact_created', {...})

2. Backend receives & saves
   ├─ @socketio.on('artifact_created')
   ├─ Create file in artifacts/ folder
   ├─ Save with UUID в filename
   ├─ Write to tree_data.json (as new leaf)
   ├─ Update ChangeLog (Triple Write)
   └─ emit('artifact_saved', {artifact_id, file_path})

3. Frontend receives & displays
   ├─ Socket.on('artifact_saved')
   ├─ Render в левой панели
   ├─ Update дерево (Three.js)
   ├─ Highlight новый лист (glow эффект?)
   └─ Soft repulsion для новых листьев

4. Tree updates
   ├─ VETKA recalculates positions для siblings
   ├─ Soft force relaxation (3-5 iterations)
   ├─ Smooth animation (500ms)
   ├─ Socket.emit('layout_updated') с новыми positions
   └─ Дерево "растёт" естественно

ПОТЕНЦИАЛЬНЫЕ ПРОБЛЕМЫ:
├─ Parsing artifact из LLM ответа (fragile?)
├─ Если artifact создан но файл не сохранился?
├─ Если дерево обновиться но artifact не создан?
├─ Z-ось конфликты для новых листьев?

>>> SEND TASK TO GROK: "Robust artifact parsing + error handling"
```

---

### PHASE 5: LANGRAPH WORKFLOW (2-3 часа)
```
Цель: LangGraph для агентов (опционально, но cleanер)

Current:
  User → Flask socket → PM → Dev → QA → emit response

With LangGraph:
  User → LangGraph workflow
       ├─ Node: PM analysis
       ├─ Node: Dev implementation
       ├─ Node: QA validation
       ├─ Node: Artifact creation (conditional)
       └─ Output: response + artifact(s)

Benefits:
  ✅ Cleaner workflow definition
  ✅ Conditional edges (if score < 0.7 → retry)
  ✅ Automatic artifact handling
  ✅ Better error handling

Implementation:
  1. Install langgraph
  2. Define StateGraph with PM/Dev/QA nodes
  3. Replace current agent routing with graph.invoke()
  4. Add artifact creation node (conditional)
  5. Emit from graph output

DECISION: Priority? (Optional для Phase 1-4, но нужно потом)
```

---

### PHASE 6: CAM INTEGRATION WITH ARTIFACTS (4-6 часов)
```
Цель: Artifacts + Branching/Pruning/Merging (живое дерево)

Current: Artifacts просто добавляются

With CAM:
├─ BRANCHING: Новый artifact = новая ветка?
│  └─ Когда: artifact создан > определённого размера
│  └─ Как: promote artifact как самостоятельное дерево?
│
├─ ACCOMMODATION: Перестройка при новых artifacts
│  └─ Soft repulsion ADAPTIVE (сильнее для нового)
│  └─ Layer height может увеличиться?
│
├─ PRUNING: Удаление low-quality artifacts
│  └─ QA score < 0.5? → mark for deletion?
│  └─ Similarity > 0.95? → duplicate detection
│
└─ MERGING: Похожие artifacts объединяются
   └─ Cosine similarity > 0.92? → можно объединить?

CAM Operations Matrix:
  Artifact size < 100 tokens  → add as leaf (no branching)
  Artifact size 100-1000      → add as branch (branching!)
  Artifact size > 1000        → promote to subtree (major branching!)
  
  Score < 0.5                 → mark for pruning
  Similar artifacts           → suggest merging
  Related artifacts           → create Liana edge

НУЖНО ИССЛЕДОВАНИЕ:
├─ Какой threshold для branching?
├─ Как accommodation работает с Sugiyama?
├─ Скорость pruning (instant или delayed cleanup?)
└─ Merging strategy (user-driven или automatic?)

>>> SEND TASK TO GROK: "CAM operations for artifact management"
```

---

### PHASE 7: KG MODE WITH ARTIFACTS (3-4 часа)
```
Цель: Knowledge Graph mode использует artifacts как примеры

Current KG mode:
  ├─ Слои по knowledge_level
  ├─ Edges по prerequisites
  └─ Концепты как узлы

With artifacts:
  ├─ Artifact = пример концепта
  ├─ Artifact edges = "пример концепта X"
  ├─ Media artifacts = визуальные примеры
  └─ Code artifacts = рабочие примеры

Implementation:
  1. Add artifact relationship to KG
  2. Render artifact icons на листьях
  3. Click artifact → preview в левой панели
  4. Artifact search in semantic mode

DECISION: Priority? (После Phase 4-6, в Phase 17+)
```

---

## 🎯 КРИТИЧЕСКИЕ ПРОПУСКИ (перескочили)

### 1. **FILE READING PATH**
```
Проблема: Где files находятся?

Current:
├─ VETKA JSON: tree_data.json (knows node_id, node_path)
├─ File system: /Users/danilagulin/Documents/.../?

Нужно:
├─ Mapping node_path → actual filesystem path
├─ Elisya может читать файлы?
└─ Если file не существует → fallback?

ACTION: Check DocsScanner как читает файлы в основном проекте!
```

### 2. **ARTIFACT STORAGE LOCATION**
```
Проблема: Где хранить артефакты?

Current: Неопределено

Options:
├─ /vetka_live_03/artifacts/ (new folder)
├─ /vetka_live_03/src/artifacts/
├─ рядом с файлом (src/main.py → src/.artifacts/main_001.json)
└─ embedded в tree_data.json

DECISION NEEDED: Где?
```

### 3. **TREE UPDATE MECHANISM**
```
Проблема: Как обновить дерево без пересчета ВСЕ Sugiyama?

Current: Неопределено

Options:
├─ Recalculate только affected layer (быстро)
├─ Recalculate только siblings (быстро)
├─ Full recalculation (медленно, но correct)
├─ Incremental (новые листья + soft repulsion)

DECISION NEEDED: Какой алгоритм?
```

### 4. **ARTIFACT TYPES SUPPORT**
```
Проблема: Какие типы поддерживаем первыми?

Phase 1 minimum viable:
├─ Text artifact (code, markdown)
├─ Maybe JSON/config

Later:
├─ Media (video, audio) - Phase 3
├─ Canvas drawing - Phase 3
├─ Images - Phase 4
└─ PDF - Phase 4?

DECISION NEEDED: Начнём с чего?
```

### 5. **AGENT PROMPT FORMAT**
```
Проблема: Как агенты создают артефакты?

Need:
├─ System prompt для PM/Dev/QA что может создавать artifacts
├─ Format instruction (XML? JSON? Markdown code blocks?)
├─ Когда создавать (always? conditionally?)
└─ Validation что output парсится

DECISION NEEDED: Какой формат артефактов?
```

---

## 📋 ГРОКОВ ИССЛЕДОВАНИЯ (НУЖНО ЗАПРОСИТЬ)

### RESEARCH 1: Artifact Architecture
```
Запрос Grok:

"VETKA project: agents create artifacts (code, documents, media).
 
 REQUIREMENTS:
 1. Artifact JSON format (with all fields)
 2. Storage location strategy
 3. File naming convention (UUIDs? timestamps?)
 4. Validation schema
 5. Error handling (file conflicts, corruption)
 6. Scalability (1000+ artifacts)
 
 Return:
 - Recommended format + rationale
 - Storage strategy pros/cons
 - Example artifact files"
```

### RESEARCH 2: CAM + Artifacts
```
Запрос Grok:

"VETKA uses Constructivist Agentic Memory (CAM).
 Artifacts are new knowledge being added to tree.
 
 REQUIREMENTS:
 1. When artifact triggers BRANCHING?
 2. How ACCOMMODATION adapts tree layout?
 3. PRUNING strategy (confidence scores?)
 4. MERGING criteria (similarity threshold?)
 5. Integration with Sugiyama layout
 
 Return:
 - Decision tree for operations
 - Thresholds (confidence, similarity)
 - Impact on tree stability"
```

### RESEARCH 3: Incremental Tree Update
```
Запрос Grok:

"VETKA uses Sugiyama hybrid for 3D tree visualization.
 When new artifacts created → tree must update.
 
 REQUIREMENTS:
 1. Full recalculation vs incremental?
 2. Soft repulsion impact on performance?
 3. Animation smoothness during update
 4. Collision detection for new leaves
 5. Z-axis management for artifacts
 
 Return:
 - Algorithm recommendation
 - Performance estimates
 - Implementation approach"
```

---

## ✅ ЧЕКЛИСТ ДО PHASE 1 СТАРТА

### Today (21 Dec):
- [ ] Claude Code завершит Tasks 1-2 (resize + Elisya socket)
- [ ] Ты проверишь что node_path передаётся
- [ ] Ты проверишь что контекст видна в консоли

### Before Phase 1:
- [ ] Определить file reading path (где файлы?)
- [ ] Проверить что Elisya может читать files
- [ ] Выбрать artifact storage location
- [ ] Отправить Grok 3 research запроса (параллельно)

### Phase 1 success:
- [ ] Agents говорят о реальных файлах
- [ ] Context visible в чате
- [ ] Все agent responses включают file info

---

## 🗓️ TIMELINE (realistic)

```
WEEK 1 (now):
├─ Phase 0: Claude Code tasks ..................... 2-3 hours
├─ Phase 1: Elisya backend integration ........... 2-3 hours
└─ Parallel: Grok research (3 topics) ............ 6-8 hours

WEEK 2:
├─ Phase 2: Artifact architecture definition .... 3-4 hours
├─ Phase 3: Left panel - artifact viewer ........ 4-6 hours
├─ Phase 4: Artifact creation flow .............. 3-4 hours
└─ Parallel: Review Grok findings

WEEK 3:
├─ Phase 5: LangGraph workflow (optional) ....... 2-3 hours
├─ Phase 6: CAM integration ..................... 4-6 hours
└─ Testing + bug fixes ........................... 3-4 hours

WEEK 4:
├─ Phase 7: KG mode with artifacts .............. 3-4 hours
├─ Polish + documentation ....................... 2-3 hours
└─ Demo ready! 🎉

TOTAL: ~40-50 hours for full integration
```

---

## 🎯 SUCCESS CRITERIA

### Phase 1 (Elisya):
```
✅ User clicks node
✅ File content loaded
✅ Agents reference file content
✅ Response different per file (not generic)
```

### Phase 4 (Full artifact flow):
```
✅ Agent creates artifact
✅ File saved to disk
✅ Tree updates in real-time
✅ Artifact visible in left panel
✅ New leaf glows (animation)
```

### Phase 6 (CAM + Artifacts):
```
✅ Large artifact triggers branching
✅ Tree restructures smoothly
✅ CAM operations visible (pruning, merging)
✅ No collisions, smooth animation
```

---

## 🚀 NEXT IMMEDIATE ACTIONS

### RIGHT NOW:
1. Wait for Claude Code to finish Tasks 1-2
2. Test that node_path transfers correctly
3. Test that Elisya context visible

### TOMORROW:
1. Start Phase 1 (backend integration - copy/paste from prompt)
2. Parallel: Prepare 3 Grok research requests
3. Test file reading path

### THEN:
1. Phase 2-4 per timeline

---

## ГЛАВНОЕ:

```
СЕЙЧАС: Chat работает, но без контекста
          Artifacts не существуют вообще
          
НУЖНО: Elisya контекст → нормальные ответы
       Artifact creation → левая панель → дерево растёт
       
ИТОГ: Живая система где агенты помогают создавать знание! 🌳
```

**Дальше все по фазам, не перепрыгивая!**
