# 🔬 GROK RESEARCH REQUESTS - VETKA Phase 2-6
**Запросить как только закончится Phase 1**

---

## REQUEST #1: Artifact Architecture & Storage

```
Привет Grok! VETKA project нужна твоя помощь с артефактами.

КОНТЕКСТ:
- Agents (PM, Dev, QA) создают ответы в чате
- Большой ответ (> 500 chars) или код → нужно сохранить как artifact
- Artifact должен стать листом в 3D дереве
- Система должна быть scalable (1000+ artifacts)

ВОПРОСЫ:

1. **JSON Schema для artifact**
   Какие поля должны быть? Пример структуры?
   Fields needed:
   - id (UUID или timestamp?)
   - type (code | document | media | canvas)
   - content (что именно?)
   - created_by (PM | Dev | QA | User)
   - created_at
   - parent_node_id
   - metadata (language, size, tags?)
   
   Return: Complete JSON schema with examples

2. **Storage Location Strategy**
   Где хранить физически?
   Options:
   a) /vetka_live_03/artifacts/ folder
   b) Embedded in tree_data.json
   c) Next to source file (.artifacts/main_001.json)
   d) Cloud storage?
   
   Return: Recommendation + pros/cons of each

3. **File Naming Convention**
   artifact_20251221_001.json? UUID? Hash?
   Должны ли быть читаемые имена?
   
   Return: Recommended convention + rationale

4. **Validation & Error Handling**
   Что делать если:
   - Artifact JSON invalid?
   - Disk full?
   - Duplicate artifact id?
   - File corrupted?
   
   Return: Error handling strategy

5. **Scalability Considerations**
   Performance для:
   - 100 artifacts ✅
   - 1000 artifacts ?
   - 10000 artifacts ?
   
   Нужна ли indexing? Caching?
   
   Return: Scalability analysis + recommendations

---

DEADLINE: ASAP (blocks Phase 2-3)
```

---

## REQUEST #2: CAM + Artifacts Integration

```
Привет Grok! VETKA использует CAM (Constructivist Agentic Memory).

КОНТЕКСТ:
- VETKA это живое дерево (THREE.js visualization)
- Когда artifact создан → дерево должно расти naturally
- CAM операции: BRANCHING, ACCOMMODATION, PRUNING, MERGING

ВОПРОСЫ:

1. **BRANCHING: Когда artifact становится веткой?**
   - Если artifact < 100 tokens → просто лист?
   - Если artifact 100-1000 tokens → новая ветка?
   - Если artifact > 1000 tokens → promote to subtree?
   
   Return: Decision tree with thresholds

2. **ACCOMMODATION: Как дерево перестраивается?**
   - Если new artifact → soft repulsion нужна?
   - Layer height может увеличиться?
   - Sugiyama recalculation strategy?
   
   Return: Algorithm для smooth tree adaptation

3. **PRUNING: Как удалять artifacts?**
   - Low quality (QA score < 0.5)? Mark for deletion?
   - Duplicates (similarity > 0.95)? Auto-remove?
   - Timing: instant deletion vs cleanup job?
   
   Return: Pruning strategy with thresholds

4. **MERGING: Когда объединять artifacts?**
   - Если similarity > 0.92 → можно merge?
   - Как сохранить обе версии (A and B)?
   - Metadata: которая становится главной?
   
   Return: Merging algorithm with conflict resolution

5. **Integration with Sugiyama**
   - Новый artifact добавлен → весь layer recalc?
   - Или только siblings + soft repulsion?
   - Performance impact?
   
   Return: Optimal update strategy

6. **Visual Feedback**
   - Когда artifact создан → какой animation?
   - Glow effect на новый лист?
   - Timeline (instant или fade-in)?
   
   Return: Animation recommendations

---

DEADLINE: ASAP (blocks Phase 6)
```

---

## REQUEST #3: Incremental Tree Update Algorithm

```
Привет Grok! VETKA нужна оптимальная стратегия обновления дерева.

КОНТЕКСТ:
- Tree: Sugiyama hybrid (Y=layer, X=angle, Z=duplicate offset)
- Update trigger: новый artifact или file добавлен
- Constraint: 60 FPS animation, no collisions

ВОПРОСЫ:

1. **Full vs Incremental Recalculation**
   - Option A: Recalculate весь Sugiyama
     Pros: Correct layout
     Cons: Slow, jarring animation
   
   - Option B: Incremental (только affected layer + siblings)
     Pros: Fast
     Cons: May miss global optimization
   
   - Option C: Hybrid (affected layer + soft repulsion)
     Pros: Fast + correct
     Cons: More complex
   
   Return: Recommendation + performance estimates

2. **Soft Force Relaxation Parameters**
   Текущие параметры:
   - k_repulsion = 150
   - damping = 0.5
   - min_distance = 100px
   - iterations = 3-5
   
   Нужны ли изменения для artifacts?
   
   Return: Optimized parameters

3. **Collision Detection & Resolution**
   - AABB collision detection для new artifacts?
   - Какой алгоритм разрешения?
   - Performance cost?
   
   Return: Collision strategy

4. **Z-axis Management**
   - New artifacts на каком Z?
   - Если duplicate → Z compression?
   - Forest spacing (если multiple trees)?
   
   Return: Z-axis allocation strategy

5. **Animation Smoothness**
   - Linear interpolation или easing?
   - Duration (500ms? 1000ms?)?
   - Procrustes alignment needed?
   
   Return: Animation specification

6. **Performance Benchmarks**
   Estimated timing для:
   - 100 nodes + new artifact
   - 1000 nodes + new artifact
   - 10000 nodes + new artifact
   
   Return: Performance estimates + optimization tips

---

DEADLINE: Before Phase 4 (blocks tree updates)
```

---

## OPTIONAL: LangGraph Workflow Design

```
Привет Grok! VETKA agents используют простую PM→Dev→QA цепочку.

КОНТЕКСТ:
- Хотим улучшить до LangGraph
- Graph nodes: PM analysis → Dev implementation → QA validation → artifact creation

ВОПРОСЫ:

1. **Graph Structure**
   Какие edges? Conditional logic? Looping?
   
   Return: StateGraph definition + recommendations

2. **Artifact Node**
   Когда triggered? Conditional logic?
   Входящие parameters, выходящие data?
   
   Return: Node implementation guide

3. **Error Handling in Graph**
   Retry logic? Max iterations? Fallback?
   
   Return: Error handling patterns

4. **Integration with Socket.IO**
   Streaming updates из graph? Batch updates?
   
   Return: Integration approach

---

DEADLINE: Optional (Phase 5)
```

---

## HOW TO SUBMIT

```
1. Создай новый чат с Grok
2. Copy/paste REQUEST #1 полностью
3. Ждёшь ответа
4. Затем REQUEST #2
5. Параллельно Claude Code может делать Phase 1

Не спешить - лучше правильно!
```

---

## TIMELINE

```
BEFORE PHASE 1:
└─ Send REQUEST #1 to Grok (artifact architecture)
   └─ Grok answers in ~2-4 hours

DURING PHASE 1:
├─ Send REQUEST #2 to Grok (CAM + artifacts)
├─ Send REQUEST #3 to Grok (tree update algorithm)
└─ Parallel: You implement Phase 1 (2-3 hours)

AFTER PHASE 1:
├─ Use Grok findings for Phase 2-4
├─ Optional: REQUEST LangGraph (Phase 5)
└─ Integrate CAM (Phase 6, with Grok findings)
```

---

## SUCCESS = CLEAR SPECIFICATIONS

```
BEFORE Grok:
❌ "Какой format артефактов? Где хранить? Когда branching?"
🤔 Много вопросов

AFTER Grok:
✅ "Artifact JSON format: {...}"
✅ "Storage: /artifacts/ folder"
✅ "Branching: если > 1000 tokens"
✅ "Update algorithm: incremental + soft repulsion"

→ IMPLEMENTATION СТАНОВИТСЯ STRAIGHTFORWARD!
```

**Не начинай Phase 2 без Grok ответов!**
