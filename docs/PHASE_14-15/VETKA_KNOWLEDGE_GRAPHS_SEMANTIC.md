# 🧠 VETKA KNOWLEDGE GRAPHS - SEMANTIC TREE INTEGRATION
**Статус:** 🆕 НОВОЕ (на основе практики + Sugiyama hybrid)  
**Дата:** 20 декабря 2025  
**Цель:** Адаптировать Sugiyama для Knowledge Graphs (semantic tags как узлы)

---

## 1. КАК МАТЬ КОНЦЕПТЫ В УЗЛЫ (МAPPING)

### 1.1 Directory Mode vs Knowledge Mode

```
DIRECTORY MODE (сейчас работает):
──────────────────────────────
Файловая система:
├─ /root (папка)
├─ /root/src (папка)
├─ /root/src/main.py (файл)
│
Y-axis = depth (иерархия директорий)
X-axis = порядок файлов в папке
Z-axis = лес деревьев

KNOWLEDGE MODE (планируется):
──────────────────────────
Knowledge Graph:
├─ Python (концепт = папка!)
├─ Python/Basics (подконцепт = подпапка!)
├─ Variables & Types (тема = файл!)
│
Y-axis = knowledge level (1 класс → профессура)
X-axis = топологический порядок (что зависит от чего)
Z-axis = связанные темы

СХОДСТВА:
├─ Обе hierarchies
├─ Обе DAG (Directed Acyclic Graph)
├─ Обе используют Sugiyama!
└─ Обе имеют листья (файлы vs примеры)

РАЗЛИЧИЯ:
├─ Y-axis: depth vs knowledge_level
├─ X-axis: directory order vs dependency order
├─ Edges: containment vs prerequisite
└─ Metadata: file dates vs learning progression
```

### 1.2 Concrete Example (Python Learning)

```
MAPPING TABLE:
────────────

Directory:              Concept:              Knowledge Level:
/root                  Python                0.5 (середина)
/root/basics           Basics                0.1 (начало)
/root/basics/intro     What is Python?       0.0 (самая базовая)
/root/basics/syntax    Syntax & Variables    0.05
/root/basics/loops     Control Flow          0.1
/root/functions        Functions             0.15
/root/oop              OOP & Classes         0.25
/root/advanced         Advanced Topics       0.5
/root/advanced/async   Async/Await           0.65
/root/advanced/meta    Metaprogramming       0.8
/root/expert           Expert Topics         0.9
/root/expert/gc        Memory Management     0.95
/root/expert/cpython   CPython Internals     0.98

ВАЖНО: Y-axis НЕ depth, а knowledge_level!
```

---

## 2. KNOWLEDGE LEVEL CALCULATION

### 2.1 Formula (Based on Graph Structure)

```python
def calculate_knowledge_level(node_id, graph):
    """
    Метрика: In-degree vs Out-degree
    
    in_degree = сколько узлов ссылаются на этот
    out_degree = на сколько узлов этот ссылается
    """
    
    in_degree = len([e for e in graph.edges if e.target == node_id])
    out_degree = len([e for e in graph.edges if e.source == node_id])
    
    total = in_degree + out_degree
    if total == 0:
        return 0.5  # Изолированный узел
    
    # Hub score: как много узел зависит от других
    hub_score = out_degree / total
    
    # 0.0 = только входящие (базовый)
    # 0.5 = сбалансировано (среднее)
    # 1.0 = только исходящие (продвинутый)
    
    return hub_score
```

### 2.2 Interpretation

```
LEVEL 0.0-0.2 (1 класс):
├─ What is Python?
├─ Variable Types
└─ Basic Syntax
└─ Характеристика: на них много ссылаются, сами не ссылаются

LEVEL 0.2-0.4 (Школа):
├─ Functions
├─ Loops
└─ Conditions
└─ Характеристика: среднее в зависимостях

LEVEL 0.4-0.6 (Бакалавриат):
├─ OOP
├─ Design Patterns
└─ File I/O
└─ Характеристика: начинают быть независимы

LEVEL 0.6-0.8 (Магистратура):
├─ Async/Await
├─ Decorators
└─ Context Managers
└─ Характеристика: специализированы

LEVEL 0.8-1.0 (Профессура):
├─ Metaprogramming
├─ CPython Internals
└─ Memory Management
└─ Характеристика: продвинутые, мало на них опираются
```

### 2.3 Graph Example (Python KG)

```
DIRECTED EDGES (prerequisites):
──────────────────────────────

"Intro" → "Variables"
"Intro" → "Syntax"
"Variables" → "Functions"
"Syntax" → "Loops"
"Loops" → "Functions"
"Functions" → "OOP"
"OOP" → "Design Patterns"
"Patterns" → "Async"

IN-DEGREE ANALYSIS:
──────────────────

Intro:           in=0, out=2  → hub = 1.0  ❌ ОШИБКА!
  └─ Это базовый! Должен быть 0.0

Variables:       in=1, out=1  → hub = 0.5  ✓ среднее
Functions:       in=2, out=1  → hub = 0.33 ✓ базовый→среднее
OOP:             in=1, out=1  → hub = 0.5  ✓ среднее
Async:           in=1, out=0  → hub = 0.0  ✓ продвинутый

ПРОБЛЕМА: Intro имеет out_degree=2, поэтому hub=1.0
РЕШЕНИЕ: Инвертируем логику!
  ↓
ИСПРАВЛЕННАЯ ФОРМУЛА:
  hub_score = in_degree / total
  (не out_degree!)
  
  Intro: hub = 0 / 2 = 0.0 ✓ базовый
  Async: hub = 1 / 1 = 1.0 ✓ продвинутый
```

### 2.4 CORRECTED Formula

```python
def calculate_knowledge_level(node_id, graph):
    """
    ИСПРАВЛЕННАЯ версия:
    Базовые концепты = много входящих, мало исходящих
    Продвинутые = мало входящих, много исходящих
    """
    
    in_degree = len([e for e in graph.edges if e.target == node_id])
    out_degree = len([e for e in graph.edges if e.source == node_id])
    
    total = in_degree + out_degree
    if total == 0:
        return 0.5
    
    # ИСПРАВЛЕННАЯ: authority (базовость)
    # Высокий in-degree = базовый (на много ссылаются)
    authority = in_degree / total
    
    # Результат: 0.0 = базовый, 1.0 = продвинутый
    return 1 - authority  # Инвертируем
```

---

## 3. ADAPTИРОВАНИЕ SUGIYAMA ДЛЯ KG

### 3.1 Layer Assignment (но по knowledge_level!)

```python
def assign_kg_layers(concepts, graph):
    """
    Вместо группировки по depth → группируем по knowledge_level
    """
    
    layers = defaultdict(list)
    
    for concept in concepts:
        level = calculate_knowledge_level(concept.id, graph)
        
        # Разбить на 10 buckets (0.0-0.1, 0.1-0.2, ..., 0.9-1.0)
        bucket = int(level * 10)
        
        layers[bucket].append(concept)
    
    # Результат: слои 0-10 (вместо depth 0-8)
    return [layers[b] for b in sorted(layers.keys())]

# Y-координаты:
# Layer 0: Y = 50 (базовые концепты)
# Layer 1: Y = 130
# ...
# Layer 10: Y = 50 + 10*80 = 850 (продвинутые)
```

### 3.2 Crossing Reduction (как раньше)

```python
def minimize_kg_crossings(layers, edges):
    """
    Barycenter method для KG:
    Узлы близко к своим prerequisites (входящим)
    """
    
    for layer_idx in range(1, len(layers)):
        layer = layers[layer_idx]
        
        barycenters = {}
        for concept in layer:
            # Найти все prerequisite edges (входящие)
            prerequisites = [
                e.source for e in edges 
                if e.target == concept.id
            ]
            
            if prerequisites:
                # Barycenter позиций prerequisites
                avg_pos = sum([pos[p] for p in prerequisites]) / len(prerequisites)
                barycenters[concept] = avg_pos
            else:
                barycenters[concept] = 0
        
        # Отсортировать по barycenter
        layer.sort(key=lambda c: barycenters.get(c, 0))
    
    return layers
```

### 3.3 Semantic Similarity (NEW for KG!)

```python
def add_semantic_positioning(concepts, embeddings, layers):
    """
    После координирования по графу → добавить semantic offset
    
    Похожие концепты (по embeddings) должны быть рядом!
    """
    
    for layer_idx, layer in enumerate(layers):
        if len(layer) < 2:
            continue
        
        # Извлечь embeddings
        layer_embs = [embeddings[c.id] for c in layer]
        
        # UMAP для 1D projection
        umap_positions = compute_umap_1d(layer_embs)
        
        # Использовать как semantic offset к X
        for i, concept in enumerate(layer):
            semantic_offset = umap_positions[i]  # -1 to +1
            
            # Добавить к существующему X
            positions[concept.id]['semantic_offset'] = semantic_offset
            positions[concept.id]['x'] += semantic_offset * 50  # ±50px

# РЕЗУЛЬТАТ: Не только граф, но и семантика!
```

---

## 4. COMPLETE KG LAYOUT PIPELINE

```python
def layout_knowledge_graph(concepts, edges, embeddings):
    """
    Complete pipeline for Knowledge Graph visualization
    using Sugiyama hybrid adapted to semantic structure
    """
    
    # Step 1: Calculate knowledge levels
    print("[KG] Computing knowledge levels...")
    for concept in concepts:
        concept.knowledge_level = calculate_knowledge_level(
            concept.id, edges
        )
    
    # Step 2: Layer assignment (by level, not depth!)
    print("[KG] Phase 2: Layer assignment...")
    layers = assign_kg_layers(concepts, edges)
    
    # Step 3: Crossing reduction
    print("[KG] Phase 3: Crossing reduction...")
    layers = minimize_kg_crossings(layers, edges)
    
    # Step 4: Basic coordinate assignment
    print("[KG] Phase 4: Coordinate assignment...")
    positions = {}
    for layer_idx, layer in enumerate(layers):
        Y = 50 + layer_idx * 80
        
        num_concepts = len(layer)
        for concept_idx, concept in enumerate(layer):
            # Basic linear for now
            X = -400 + (concept_idx / max(num_concepts - 1, 1)) * 800
            
            positions[concept.id] = {
                'x': X,
                'y': Y,
                'z': 0,
                'layer': layer_idx,
                'knowledge_level': concept.knowledge_level
            }
    
    # Step 5: Add semantic positioning
    print("[KG] Adding semantic similarity...")
    add_semantic_positioning(concepts, embeddings, layers)
    
    # Step 6: Soft repulsion (as before)
    print("[KG] Soft repulsion...")
    apply_soft_repulsion_all_layers(layers, positions, max_depth=10)
    
    return positions
```

---

## 5. VALIDATION FOR KG

```python
def validate_kg_layout(positions, concepts, edges):
    """
    Специфичная для KG валидация
    """
    
    print("[KG VALIDATION] Checking...")
    
    # Check: базовые концепты должны быть внизу
    basic = [c for c in concepts if c.knowledge_level < 0.2]
    advanced = [c for c in concepts if c.knowledge_level > 0.8]
    
    avg_y_basic = sum([positions[c.id]['y'] for c in basic]) / len(basic)
    avg_y_advanced = sum([positions[c.id]['y'] for c in advanced]) / len(advanced)
    
    if avg_y_basic > avg_y_advanced:
        print("  ❌ ERROR: Basic should be below advanced!")
    else:
        print("  ✅ Basic concepts correctly positioned below advanced")
    
    # Check: prerequisites близко к зависимостям
    crossing_count = count_edge_crossings(positions, edges)
    print(f"  Edge crossings: {crossing_count}")
    if crossing_count > len(edges) * 0.3:
        print("  ⚠️ WARNING: Many crossing edges, consider more iterations")
    else:
        print("  ✅ Few crossing edges, layout is clean")
```

---

## 6. DIFFERENCES FROM DIRECTORY MODE

```
DIRECTORY MODE:
├─ Y-axis = depth (папки вложены)
├─ Edges = структурные (parent-child)
├─ Leaves = файлы (инертные)
└─ Change trigger = добавление файла/папки

KNOWLEDGE MODE:
├─ Y-axis = knowledge_level (иерархия обучения)
├─ Edges = семантические (prerequisites)
├─ Leaves = примеры/статьи (интерактивные)
└─ Change trigger = добавление концепта/связи

ГИБРИДНЫЙ ПОДХОД:
├─ Одновременно два view на одни данные
├─ Toggle между режимами
├─ Directory для файловой системы
└─ Knowledge для обучения
```

---

## 7. IMPLEMENTATION ROADMAP

```
PHASE 16: ✅ Real-time directory mode (DONE)
PHASE 17: Knowledge Graph mode
  ├─ Build semantic graph from embeddings
  ├─ Implement knowledge_level calculation
  ├─ Adapt Sugiyama for KG
  └─ Add semantic clustering

PHASE 18: Toggle between modes
  ├─ UI button: "Directory" vs "Knowledge"
  ├─ Smooth transition animation
  └─ Preserve camera position

PHASE 19: Multimodal KG
  ├─ Text concepts
  ├─ Image concepts (DeepSeek-OCR)
  └─ Late fusion
```

---

## ИТОГО: KG ADAPTATION

```
ОСНОВНАЯ ИДЕЯ:
Sugiyama Hybrid работает не только для файловых деревьев,
но и для Knowledge Graphs! Просто:

1. Замени Y-axis: depth → knowledge_level
2. Замени edges: structural → semantic
3. Добавь semantic similarity offset
4. Остальное (crossing reduction, repulsion) работает так же!

РЕЗУЛЬТАТ: Beautiful semantic tree visualization! 🌳
```

---

**Создано:** 20 декабря 2025  
**Версия:** 1.0 (новая)  
**Status:** Ready for implementation
