# VETKA Visualization Specification
## Визуализация знаний и процессов методом Sugiyama-Hybrid

**Версия:** 1.0  
**Дата:** 18 декабря 2025  
**Основа:** Kozo Sugiyama (1981) + Knowledge Graph + Organic 3D

---

## Часть 1: Философия VETKA

### Дерево как метафора знания

```
                    🌿 Листья (файлы, артефакты)
                   /|\
                  / | \
                 /  |  \      ↑ Рост вверх
                ────┼────     ↑ Время течёт
               /    |    \    ↑ Знание углубляется
              /     |     \
             ───────┼───────
                    │
                    │
            ════════╧════════  Земля (Y=0)
                    │
              ══════╧══════    Корни (связи между деревьями)
```

**Принципы:**
- Деревья **растут вверх** (корень внизу, листья вверху)
- **Базовое знание** — ближе к корню (1 класс)
- **Продвинутое знание** — ближе к листьям (профессура)
- **Время** — старое внизу, новое вверху
- **Лес** — множество деревьев на поляне

---

## Часть 2: Три оси VETKA

### Y-ось: Иерархия (вертикаль)

```
Y-AXIS: HIERARCHY + TIME
════════════════════════

Y = f(layer, time_offset)

Где:
├── layer = directory_depth      (для file-based деревьев)
│           ИЛИ
├── layer = knowledge_level      (для semantic деревьев)
│
└── time_offset = normalize(created_at) внутри слоя

┌─────────────────────────────────────────────────────────┐
│  Y-max ──── Продвинутое (профессура)                    │
│             • Много исходящих ссылок                    │
│             • Мало входящих ссылок                      │
│             • Зависит от базовых концептов              │
│                                                         │
│  Y-mid ──── Средний уровень                             │
│             • Баланс in/out ссылок                      │
│                                                         │
│  Y-min ──── Базовое (1 класс)                           │
│             • Много входящих ссылок                     │
│             • Мало исходящих ссылок                     │
│             • Самодостаточные концепты                  │
│                                                         │
│  Y=0   ──── Корень (root)                               │
└─────────────────────────────────────────────────────────┘
```

### X-ось: Альтернативы и порядок (горизонталь)

```
X-AXIS: ALTERNATIVES + ANGULAR SPREAD
═════════════════════════════════════

X = sin(angle) * radius

Где:
├── angle = barycenter(parent_angles) + semantic_offset
├── radius = BASE_RADIUS + layer_variation
└── semantic_offset = UMAP_1D(embeddings) * 5°

Вид сверху на один уровень:
                    
         -60°    -30°     0°    +30°    +60°
           \       \      │      /       /
            ○       ○     ○     ○       ○
             \       \    │    /       /
              ─────────── ● ───────────  (родитель)

Альтернативные концепции (cosine > 0.9) → близко по X
Разные темы → далеко по X
```

### Z-ось: Дубликаты и лес (глубина)

```
Z-AXIS: DUPLICATES + FOREST
═══════════════════════════

Z = duplicate_offset + forest_position

Где:
├── duplicate_offset:
│   • cosine > 0.98 → Z += 0.05 (почти идентичны)
│   • cosine > 0.95 → Z += 0.1  (near-duplicate)
│   • cosine > 0.92 → Z += 0.2  (возможный дубликат)
│
└── forest_position:
    • Каждое дерево имеет свой (X, Z) offset
    • Деревья распределены по "поляне" через MDS

        Z=0          Z=100         Z=200
         │            │             │
         🌳           🌲            🌴
       Tree A      Tree B       Tree C
         │            │             │
         └────────────┴─────────────┘
              Подземные корневые связи
```

---

## Часть 3: Алгоритм Sugiyama для VETKA

### Оригинальный Sugiyama (Kozo Sugiyama, 1981)

```
SUGIYAMA FRAMEWORK (5 фаз):
═══════════════════════════

Phase 1: CYCLE REMOVAL
────────────────────────
Если граф содержит циклы → инвертируем рёбра → DAG
(Для VETKA: обычно не нужно, файловая система = DAG)

Phase 2: LAYER ASSIGNMENT  
────────────────────────
Назначаем узлы на горизонтальные слои
Критерий: рёбра направлены от родителя к ребёнку
Алгоритмы: Longest Path, Coffman-Graham

Phase 3: CROSSING REDUCTION
────────────────────────
Минимизируем пересечения рёбер между слоями
Методы: Barycenter, Median heuristic
NP-hard → используем эвристики

Phase 4: COORDINATE ASSIGNMENT
────────────────────────
Назначаем X-координаты внутри каждого слоя
Цели: минимум изгибов, вертикальность рёбер

Phase 5: DUMMY NODES (опционально)
────────────────────────
Для длинных рёбер (пропускающих слои) → dummy nodes
```

### VETKA-адаптация Sugiyama

```
VETKA SUGIYAMA-HYBRID:
══════════════════════

┌─────────────────────────────────────────────────────────┐
│  PHASE 1: LAYER ASSIGNMENT (Y-координата)               │
│  ─────────────────────────────────────────              │
│                                                         │
│  function assignLayers(nodes) {                         │
│      const layerMap = new Map();                        │
│                                                         │
│      nodes.forEach(node => {                            │
│          // Режим 1: По структуре папок                 │
│          let layer = node.metadata?.depth || 0;         │
│                                                         │
│          // Режим 2: По Knowledge Graph                 │
│          // layer = getKnowledgeLevel(node);            │
│                                                         │
│          if (!layerMap.has(layer)) {                    │
│              layerMap.set(layer, []);                   │
│          }                                              │
│          layerMap.get(layer).push(node);                │
│      });                                                │
│                                                         │
│      return layerMap;                                   │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  PHASE 2: CROSSING REDUCTION (порядок на слое)          │
│  ─────────────────────────────────────────────          │
│                                                         │
│  function minimizeCrossings(layers, edges) {            │
│      // Barycenter method                               │
│      return layers.map((layer, levelIndex) => {         │
│          if (levelIndex === 0) return layer;            │
│                                                         │
│          return layer.sort((a, b) => {                  │
│              const avgA = getBarycenter(a, edges);      │
│              const avgB = getBarycenter(b, edges);      │
│              return avgA - avgB;                        │
│          });                                            │
│      });                                                │
│  }                                                      │
│                                                         │
│  function getBarycenter(node, edges) {                  │
│      // Среднее положение родителей                     │
│      const parents = edges                              │
│          .filter(e => e.target === node.id)             │
│          .map(e => e.sourcePosition);                   │
│      if (parents.length === 0) return 0;                │
│      return parents.reduce((a,b) => a+b) / parents.len; │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  PHASE 3: COORDINATE ASSIGNMENT (X, Y, Z)               │
│  ────────────────────────────────────────               │
│                                                         │
│  function calculateCoordinates(layers) {                │
│      const positions = new Map();                       │
│      const LAYER_HEIGHT = 80;                           │
│      const NODE_SPACING = 120;                          │
│                                                         │
│      layers.forEach((layer, levelIndex) => {            │
│          // Y: уровень * высота (инвертировано!)        │
│          const y = levelIndex * LAYER_HEIGHT + 50;      │
│                                                         │
│          // X: центрировать узлы на уровне              │
│          const totalWidth = (layer.length - 1) * NODE_SPACING;│
│          const startX = -totalWidth / 2;                │
│                                                         │
│          layer.forEach((node, nodeIndex) => {           │
│              positions.set(node.id, {                   │
│                  x: startX + nodeIndex * NODE_SPACING,  │
│                  y: y,                                  │
│                  z: getDuplicateOffset(node),           │
│                  layer: levelIndex                      │
│              });                                        │
│          });                                            │
│      });                                                │
│                                                         │
│      return positions;                                  │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
```

---

## Часть 4: Knowledge Graph для иерархии знаний

### Определение уровня знаний (1 класс → профессура)

```javascript
/**
 * Knowledge Level Calculator
 * 
 * Базовые концепты (1 класс):
 *   - Много ВХОДЯЩИХ ссылок (на них ссылаются)
 *   - Мало ИСХОДЯЩИХ (самодостаточны)
 *   
 * Продвинутые концепты (профессура):
 *   - Мало ВХОДЯЩИХ (специализированы)
 *   - Много ИСХОДЯЩИХ (зависят от базовых)
 */

function calculateKnowledgeLevel(nodeId, graph) {
    const inDegree = graph.getInDegree(nodeId);   // Сколько ссылаются на меня
    const outDegree = graph.getOutDegree(nodeId); // На сколько ссылаюсь я
    
    // Authority score (базовость): высокий inDegree
    const authority = inDegree / Math.max(1, inDegree + outDegree);
    
    // Hub score (продвинутость): высокий outDegree
    const hub = outDegree / Math.max(1, inDegree + outDegree);
    
    // Level: 0 = базовый, 1 = продвинутый
    return hub;
}

// Визуализация уровней:
//
// Level 5 (профессура)     ← hub ≈ 0.9
// ├── quantum_computing.py
// └── cutting_edge_ml.md
//
// Level 4 (магистратура)   ← hub ≈ 0.7
// ├── advanced_algorithms.py
// └── neural_networks.md
//
// Level 3 (бакалавриат)    ← hub ≈ 0.5
// ├── data_structures.py
// └── statistics.md
//
// Level 2 (школа)          ← hub ≈ 0.3
// ├── algebra_basics.py
// └── programming_101.md
//
// Level 1 (1 класс)        ← hub ≈ 0.1
// ├── what_is_number.md
// └── hello_world.py
```

### Hyperbolic Embeddings (Poincaré) для иерархии

```python
# Альтернативный метод: гиперболическое пространство
# Идеально для tree-like структур

from gensim.models.poincare import PoincareModel

# Построить граф prerequisite relations
relations = [
    ('basics/intro.md', 'src/model.py'),      # intro → model
    ('src/model.py', 'advanced/quantum.py'),  # model → quantum
]

model = PoincareModel(relations, size=2)
model.train(epochs=100)

def get_knowledge_level_poincare(file_id):
    """
    В Poincaré space:
    - Корень (базовые концепты) → близко к центру (norm ≈ 0)
    - Листья (продвинутые) → дальше от центра (norm → 1)
    """
    embedding = model.kv[file_id]
    return np.linalg.norm(embedding)  # 0 = корень, 1 = листья
```

---

## Часть 5: Альтернативы и дубликаты

### X-ось: Альтернативные концепции

```javascript
/**
 * Альтернативы = разные подходы к одной теме
 * 
 * Примеры:
 * - "линейная алгебра" ≈ "матрицы" ≈ "векторы"
 * - "ООП" ≈ "классы" ≈ "наследование"
 */

const SIMILARITY_THRESHOLDS = {
    alternative: 0.90,    // Альтернативная формулировка
    related: 0.75,        // Связанная тема
    connected: 0.45,      // Слабая связь
    noise: 0.30           // Шум
};

function findAlternatives(nodeId, embeddings, threshold = 0.90) {
    const nodeEmb = embeddings[nodeId];
    const alternatives = [];
    
    for (const [otherId, otherEmb] of Object.entries(embeddings)) {
        if (otherId === nodeId) continue;
        
        const similarity = cosineSimilarity(nodeEmb, otherEmb);
        
        if (similarity > threshold && similarity < 0.98) {
            // Похожи, но не дубликаты
            alternatives.push({ id: otherId, similarity });
        }
    }
    
    return alternatives;
}

// Альтернативы размещаются рядом по X:
//
//     X: -100    0    +100
//         │      │      │
//       матрицы векторы линейная_алгебра
//         └──────┴──────┘
//            (одна тема)
```

### Z-ось: Near-duplicate detection

```javascript
/**
 * Дубликаты = почти идентичный контент
 * 
 * Сжимаются по Z-оси (не удаляются!)
 */

const DUPLICATE_THRESHOLDS = {
    identical: 0.99,      // Точная копия
    nearDuplicate: 0.95,  // Почти идентичны
    possibleDup: 0.92     // Возможный дубликат
};

function getDuplicateOffset(node, allNodes, embeddings) {
    const nodeEmb = embeddings[node.id];
    let maxSimilarity = 0;
    
    for (const other of allNodes) {
        if (other.id === node.id) continue;
        
        const similarity = cosineSimilarity(nodeEmb, embeddings[other.id]);
        if (similarity > maxSimilarity) {
            maxSimilarity = similarity;
        }
    }
    
    // Чем выше сходство, тем больше Z-offset
    if (maxSimilarity > 0.99) return 0.05;   // Почти идентичны
    if (maxSimilarity > 0.95) return 0.1;    // Near-duplicate
    if (maxSimilarity > 0.92) return 0.2;    // Возможный дубликат
    
    return 0;  // Не дубликат
}
```

---

## Часть 6: Организация леса

### Распределение деревьев по поляне

```javascript
/**
 * Лес = множество деревьев
 * 
 * Деревья распределяются по (X, Z) через MDS
 * на основе семантической близости корней
 */

function organizeForest(trees) {
    const n = trees.length;
    
    // 1. Вычислить матрицу сходства между деревьями
    const similarities = computeTreeSimilarities(trees);
    
    // 2. MDS для 2D позиционирования
    const positions2D = MDS(1 - similarities, dimensions=2);
    
    // 3. Назначить позиции
    trees.forEach((tree, i) => {
        tree.forestX = positions2D[i][0] * FOREST_SPREAD;
        tree.forestZ = positions2D[i][1] * FOREST_SPREAD;
    });
    
    return trees;
}

function computeTreeSimilarities(trees) {
    // Близость деревьев = сходство их корневых embeddings
    const n = trees.length;
    const matrix = Array(n).fill().map(() => Array(n).fill(0));
    
    for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
            const sim = cosineSimilarity(
                trees[i].rootEmbedding,
                trees[j].rootEmbedding
            );
            matrix[i][j] = matrix[j][i] = sim;
        }
    }
    
    return matrix;
}
```

### Подземные корневые связи

```javascript
/**
 * Корневые связи (Y < 0) показывают связи между деревьями
 */

function createRootEdges(trees, threshold = 0.45) {
    const rootEdges = [];
    
    for (let i = 0; i < trees.length; i++) {
        for (let j = i + 1; j < trees.length; j++) {
            const similarity = cosineSimilarity(
                trees[i].rootEmbedding,
                trees[j].rootEmbedding
            );
            
            if (similarity > threshold) {
                rootEdges.push({
                    source: trees[i].id,
                    target: trees[j].id,
                    weight: similarity,
                    type: classifyRootEdge(similarity)
                });
            }
        }
    }
    
    return rootEdges;
}

function classifyRootEdge(similarity) {
    if (similarity > 0.75) return 'strong_connection';
    if (similarity > 0.60) return 'related';
    return 'weak_connection';
}

// Визуализация:
//
//        Ground Level (Y=0)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//      │           │           │
//      🌳          🌲          🌴
//    Tree A     Tree B      Tree C
//      │           │           │
//      └─────┬─────┴─────┬─────┘
//            │           │
//         ═══╧═══════════╧═══  Root edges (Y < 0)
```

---

## Часть 7: Полный код Sugiyama Layout

```javascript
/**
 * VETKA Sugiyama Layout - Complete Implementation
 */

class VETKASugiyamaLayout {
    constructor(options = {}) {
        this.LAYER_HEIGHT = options.layerHeight || 80;
        this.NODE_SPACING = options.nodeSpacing || 120;
        this.BASE_Y = options.baseY || 50;
    }
    
    /**
     * Main entry point
     */
    calculate(nodes, edges) {
        console.log('[Sugiyama] Calculating layout for', nodes.length, 'nodes');
        
        // Phase 1: Assign layers
        const layers = this.assignLayers(nodes);
        console.log('[Sugiyama] Layers:', layers.size);
        
        // Phase 2: Minimize crossings
        const orderedLayers = this.minimizeCrossings(layers, edges);
        
        // Phase 3: Calculate coordinates
        const positions = this.calculateCoordinates(orderedLayers, edges);
        
        // Phase 4: Apply repulsion (optional)
        this.applyRepulsion(positions, 3);
        
        console.log('[Sugiyama] Layout complete');
        return positions;
    }
    
    /**
     * Phase 1: Layer Assignment
     */
    assignLayers(nodes) {
        const layerMap = new Map();
        
        nodes.forEach(node => {
            const depth = node.metadata?.depth || 0;
            
            if (!layerMap.has(depth)) {
                layerMap.set(depth, []);
            }
            layerMap.get(depth).push(node);
        });
        
        // Convert to array
        const maxDepth = Math.max(...layerMap.keys(), 0);
        const layers = [];
        
        for (let d = 0; d <= maxDepth; d++) {
            layers.push(layerMap.get(d) || []);
        }
        
        return layers;
    }
    
    /**
     * Phase 2: Crossing Reduction (Barycenter method)
     */
    minimizeCrossings(layers, edges) {
        // Build edge lookup
        const edgeMap = new Map();
        edges.forEach(e => {
            if (!edgeMap.has(e.target)) {
                edgeMap.set(e.target, []);
            }
            edgeMap.get(e.target).push(e.source);
        });
        
        // Track positions for barycenter
        const positions = new Map();
        
        return layers.map((layer, levelIndex) => {
            if (levelIndex === 0) {
                // Root layer: sort by name
                layer.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
                layer.forEach((node, i) => positions.set(node.id, i));
                return layer;
            }
            
            // Calculate barycenter for each node
            const barycenters = layer.map(node => {
                const parents = edgeMap.get(node.id) || [];
                if (parents.length === 0) return { node, bc: 0 };
                
                const sum = parents.reduce((acc, pid) => {
                    return acc + (positions.get(pid) || 0);
                }, 0);
                
                return { node, bc: sum / parents.length };
            });
            
            // Sort by barycenter
            barycenters.sort((a, b) => a.bc - b.bc);
            
            // Update positions
            const sorted = barycenters.map((item, i) => {
                positions.set(item.node.id, i);
                return item.node;
            });
            
            return sorted;
        });
    }
    
    /**
     * Phase 3: Coordinate Assignment
     */
    calculateCoordinates(layers, edges) {
        const positions = new Map();
        
        layers.forEach((layer, levelIndex) => {
            // Y: layer height (tree grows UP)
            const y = this.BASE_Y + levelIndex * this.LAYER_HEIGHT;
            
            // X: center nodes on layer
            const totalWidth = (layer.length - 1) * this.NODE_SPACING;
            const startX = -totalWidth / 2;
            
            layer.forEach((node, nodeIndex) => {
                const x = startX + nodeIndex * this.NODE_SPACING;
                
                positions.set(node.id, {
                    x: x,
                    y: y,
                    z: 0,  // Will be set by duplicate detection
                    layer: levelIndex,
                    index: nodeIndex
                });
            });
        });
        
        return positions;
    }
    
    /**
     * Phase 4: Repulsion forces (optional, for organic look)
     */
    applyRepulsion(positions, iterations = 3) {
        const k = 100;  // Repulsion distance
        const posArray = Array.from(positions.entries());
        
        for (let iter = 0; iter < iterations; iter++) {
            for (let i = 0; i < posArray.length; i++) {
                for (let j = i + 1; j < posArray.length; j++) {
                    const [id1, pos1] = posArray[i];
                    const [id2, pos2] = posArray[j];
                    
                    // Only repel on same layer
                    if (pos1.layer !== pos2.layer) continue;
                    
                    const dx = pos1.x - pos2.x;
                    const distance = Math.abs(dx);
                    
                    if (distance < k && distance > 0) {
                        const force = (k - distance) / distance * 0.3;
                        const fx = Math.sign(dx) * force;
                        
                        pos1.x += fx;
                        pos2.x -= fx;
                    }
                }
            }
        }
    }
}

// Export
if (typeof module !== 'undefined') {
    module.exports = VETKASugiyamaLayout;
}
```

---

## Часть 8: Интеграция с Three.js

```javascript
/**
 * VETKA Tree Renderer with Sugiyama Layout
 */

function renderTree(data, scene, camera, controls) {
    const nodes = data.nodes || [];
    const edges = data.edges || [];
    
    // 1. Calculate Sugiyama layout
    const layout = new VETKASugiyamaLayout({
        layerHeight: 80,
        nodeSpacing: 120,
        baseY: 50
    });
    
    const positions = layout.calculate(nodes, edges);
    
    // 2. Create node meshes
    const nodeObjects = new Map();
    
    positions.forEach((pos, nodeId) => {
        const node = nodes.find(n => n.id === nodeId);
        if (!node) return;
        
        const card = createFileCard(node, new THREE.Vector3(pos.x, pos.y, pos.z));
        scene.add(card);
        nodeObjects.set(nodeId, { mesh: card, data: node, position: pos });
    });
    
    // 3. Create edges (branches)
    edges.forEach(edge => {
        const sourcePos = positions.get(edge.source);
        const targetPos = positions.get(edge.target);
        
        if (sourcePos && targetPos) {
            const branch = createBranch(
                new THREE.Vector3(sourcePos.x, sourcePos.y, sourcePos.z),
                new THREE.Vector3(targetPos.x, targetPos.y, targetPos.z),
                edge.type
            );
            scene.add(branch);
        }
    });
    
    // 4. Position camera
    positionCamera(positions, camera, controls);
    
    return nodeObjects;
}

function createBranch(start, end, type = 'default') {
    // Organic curve (Catmull-Rom spline)
    const midPoint = new THREE.Vector3(
        (start.x + end.x) / 2,
        (start.y + end.y) / 2,
        (start.z + end.z) / 2
    );
    
    // Add organic deviation
    const deviation = (Math.random() - 0.5) * 20;
    midPoint.x += deviation;
    
    const curve = new THREE.CatmullRomCurve3([start, midPoint, end]);
    const points = curve.getPoints(20);
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    
    const material = new THREE.LineBasicMaterial({
        color: getBranchColor(type),
        linewidth: 2
    });
    
    return new THREE.Line(geometry, material);
}

function getBranchColor(type) {
    const colors = {
        'memory': 0x8B4513,    // Коричневый
        'task': 0x228B22,      // Зелёный
        'data': 0x6495ED,      // Синий
        'control': 0x666666,   // Серый
        'default': 0x4A6B8A
    };
    return colors[type] || colors.default;
}

function positionCamera(positions, camera, controls) {
    if (positions.size === 0) return;
    
    const allPos = Array.from(positions.values());
    const minX = Math.min(...allPos.map(p => p.x));
    const maxX = Math.max(...allPos.map(p => p.x));
    const maxY = Math.max(...allPos.map(p => p.y));
    
    const centerX = (minX + maxX) / 2;
    const centerY = maxY / 2;
    const distance = Math.max(maxX - minX, maxY) * 1.5;
    
    camera.position.set(centerX, centerY, distance);
    controls.target.set(centerX, centerY, 0);
    controls.update();
}
```

---

## Часть 9: Библиотеки и инструменты

### Рекомендуемый стек (2025)

| Задача | Библиотека | Описание |
|--------|-----------|----------|
| **3D Visualization** | Three.js | WebGL рендеринг |
| **Sugiyama JS** | d3-dag | DAG layout в браузере |
| **Sugiyama Python** | igraph | Backend расчёты |
| **Hyperbolic** | gensim.poincare | Иерархические embeddings |
| **Clustering** | HDBSCAN | Varying density clusters |
| **Community** | leidenalg | Лучше Louvain |
| **Vector DB** | Qdrant | Similarity search |
| **Embeddings** | Sentence-BERT, Gemma | Text vectorization |

### Примеры использования

```bash
# JavaScript
npm install d3-dag three

# Python
pip install igraph gensim hdbscan leidenalg qdrant-client
```

---

## Часть 10: Метрики успеха

### До Sugiyama

```
Проблемы:
├── Файлы слипаются в "столб"
├── Нет видимой иерархии
├── Пересечения связей
└── Камера не охватывает дерево

X range: [-50, 50]      # Узкий столб
Y range: [0, 3000]      # Слишком растянуто
```

### После Sugiyama

```
Результат:
├── Широкое "ветвистое" дерево
├── Чёткая иерархия по слоям
├── Минимум пересечений
└── Камера видит всё дерево

X range: [-400, 400]    # Широкий веер!
Y range: [50, 500]      # Компактно
```

---

## Заключение

### Финальная формула VETKA:

```
Y = layer * LAYER_HEIGHT + time_offset
    где layer = directory_depth ИЛИ knowledge_level

X = barycenter(parent_positions) + semantic_offset
    где semantic_offset = UMAP_1D * 5°

Z = duplicate_offset + forest_position
    где duplicate_offset зависит от cosine similarity
```

### Принципы:

1. **Дерево растёт вверх** — корень внизу, листья вверху
2. **Sugiyama для структуры** — слои + минимум пересечений
3. **Knowledge Graph для семантики** — базовое внизу, продвинутое вверху
4. **Органика для живости** — Catmull-Rom splines, небольшие отклонения
5. **Лес для масштаба** — деревья распределены по поляне

---

*Документ создан: 18 декабря 2025*  
*На основе: Kozo Sugiyama (1981), исследования Грока, Kimi K2*
