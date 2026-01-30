# 🔍 VETKA Scanner + Layout Reconnaissance Report
## Phase 71: Comprehensive Audit

**Date:** 2026-01-19
**Analyst:** Claude Opus 4.5

---

## 📁 Analyzed Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/scanners/local_scanner.py` | File scanning + metadata extraction | 200 |
| `src/scanners/local_project_scanner.py` | Project structure scanning | 165 |
| `src/layout/semantic_sugiyama.py` | DAG-based knowledge level layout | 643 |
| `src/layout/knowledge_layout.py` | Knowledge mode positioning + clustering | 1800+ |
| `src/layout/fan_layout.py` | Directory mode fan layout | 635 |
| `src/memory/qdrant_client.py` | Vector storage + search | 535 |
| `src/orchestration/semantic_dag_builder.py` | Semantic DAG construction | 500+ |

---

## 🔬 Detailed Analysis

### 1. Извлекаются ли imports при сканировании?

**❌ НЕТ - imports НЕ извлекаются**

#### `local_scanner.py` - ScannedFile dataclass (lines 17-31):
```python
@dataclass
class ScannedFile:
    path: str
    name: str
    extension: str
    size_bytes: int
    modified_time: float
    created_time: float
    content: str           # ← Полный текст файла
    content_hash: str
    parent_folder: str
    depth: int
    # ← НЕТ поля для imports/dependencies!
```

#### `local_project_scanner.py` - Возвращаемая структура (lines 47-52):
```python
files.append({
    "name": item.name,
    "path": str(item.relative_to(root)),
    "language": self._detect_lang(item),
    "size_bytes": item.stat().st_size
    # ← НЕТ imports, НЕТ dependencies
})
```

**Вывод:** Сканер читает полный `content`, но НЕ парсит его для извлечения imports.

---

### 2. Есть ли поле dependency в TreeNode?

**❌ НЕТ - dependency поля отсутствуют**

#### `qdrant_client.py` - VetkaTreeNode (lines 24-37):
```python
@dataclass
class VetkaTreeNode:
    node_id: str
    path: str
    content: str
    metadata: Dict[str, Any]
    timestamp: float
    vector: List[float] = None  # Embedding
    # ← НЕТ dependencies, НЕТ imports, НЕТ references
```

#### `semantic_dag_builder.py` - SemanticNode (lines 26-48):
```python
@dataclass
class SemanticNode:
    id: str
    type: str  # 'concept' or 'file'
    label: str
    embedding: Optional[np.ndarray] = None
    children: List[str] = field(default_factory=list)  # file IDs if concept
    knowledge_level: float = 0.5
    complexity_score: float = 0.5   # ← Embedding L2 norm
    frequency_score: float = 0.5    # ← Token frequency
    depth_hint: int = 0             # ← Directory depth
    # ← НЕТ dependencies, НЕТ imports
```

**Критическая проблема:** Зависимости между файлами вычисляются ТОЛЬКО через **cosine similarity** embeddings, а НЕ через реальные import statements.

---

### 3. Как вычисляется Y-координата сейчас?

**✅ Через DAG depth (knowledge_level)**

#### `semantic_sugiyama.py` - assign_knowledge_levels_from_dag (lines 21-106):
```python
def assign_knowledge_levels_from_dag(nodes, edges):
    """
    Algorithm:
    1. Find root nodes (in_degree == 0)
    2. BFS from roots to calculate depth
    3. Normalize depth to knowledge_level [0.1, 1.0]
    """
    # ...
    for node_id in node_ids:
        if depths[node_id] == float('inf'):
            knowledge_levels[node_id] = 0.5  # Orphan
        else:
            knowledge_levels[node_id] = 0.1 + (depths[node_id] / max_depth) * 0.9
```

#### `semantic_sugiyama.py` - calculate_semantic_sugiyama_layout (lines 217-330):
```python
# Y position based on knowledge_level (columnar, not circular!)
y = 100 + (level_idx * (max_y / 10))  # level_idx = int(kl * 10)
```

**Формула:**
```
Y = 100 + (knowledge_level * 10) × (max_y / 10)
Y = 100 + knowledge_level × max_y
# where max_y = 3000 by default
# Y range: 100 → 3100
```

**Проблема:** knowledge_level вычисляется из DAG, но DAG строится на основе **semantic similarity**, а НЕ реальных зависимостей!

---

### 4. Почему происходят пересечения?

**🔴 Множество причин:**

#### A. Similarity ≠ Real Dependencies
```python
# knowledge_layout.py:1146-1153
for i in range(len(valid_files)):
    for j in range(i + 1, len(valid_files)):
        sim = sim_matrix[i][j]
        if sim >= similarity_threshold:  # 0.7 default
            undirected_edges.append((valid_files[i], valid_files[j], float(sim)))
```
**Проблема:** Два файла могут быть семантически похожи (оба про "API"), но один НЕ зависит от другого.

#### B. DAG Depth ≠ Real Import Order
```python
# semantic_sugiyama.py:56-60
if edge_type == 'prerequisite':
    if target in in_degrees:
        in_degrees[target] += 1
    if source in adjacency:
        adjacency[source].append(target)
```
**Проблема:** "Prerequisite" edges строятся из similarity, а не из `import X from Y`.

#### C. X-axis Collision
```python
# semantic_sugiyama.py:288-294
y = 100 + (level_idx * (max_y / 10))

if use_similarity_x and len(embeddings) > 0:
    x_positions = distribute_by_similarity(layer, embeddings, x_spread)
else:
    x_positions = distribute_horizontally(n_nodes, x_spread)
```
**Проблема:** Файлы на одном Y-уровне могут overlap по X если:
- Много файлов в одном layer
- Soft repulsion недостаточен (min_distance=100px, lines 448-450)

#### D. Crossing Minimization Disabled
```python
# semantic_sugiyama.py:309-312
# Phase 17.20: DISABLED - destroys semantic X positioning
# minimize_crossings(positions, layers, edges, iterations=5, x_spread=x_spread)
logger.info("[SemanticLayout] Phase 17.20: Skipped minimize_crossings to preserve semantic X")
```
**Критическое:** Barycenter crossing minimization **ОТКЛЮЧЕН**!

---

### 5. Где хранится граф зависимостей?

**📍 Граф строится in-memory, НЕ персистится**

#### Edges создаются в:
1. `knowledge_layout.py:build_prerequisite_edges()` → `List[KnowledgeEdge]`
2. `semantic_dag_builder.py:_infer_prerequisite_edges_multicriteria()` → `List[SemanticEdge]`

#### Сохраняется в Qdrant:
```python
# qdrant_client.py:232-247
point = PointStruct(
    id=point_id,
    vector=vector,
    payload={
        'node_id': node_id,
        'path': path,
        'content': content[:500],
        'metadata': metadata,
        'timestamp': time.time()
        # ← НЕТ edges, НЕТ dependencies
    }
)
```

**Вывод:** Граф edges **НЕ сохраняется** в Qdrant. Пересчитывается каждый раз.

---

## 📊 Что есть vs Что нужно

| Компонент | ЧТО ЕСТЬ | ЧТО НУЖНО |
|-----------|----------|-----------|
| **Scanner** | Читает content, extension, size | + Parse imports (AST для .py, regex для .js/.ts) |
| **ScannedFile** | 10 полей (path, name, content...) | + `imports: List[str]`, + `dependencies: List[str]` |
| **TreeNode** | path, content, metadata, vector | + `dependencies: List[str]`, + `imported_by: List[str]` |
| **SemanticNode** | embedding, knowledge_level, children | + `imports: List[str]`, + `import_depth: int` |
| **Qdrant Payload** | node_id, path, content, metadata | + `imports`, + `dependency_edges` |
| **Edge Inference** | Cosine similarity > 0.7 | + Real import parsing |
| **Y calculation** | DAG depth from similarity | + DAG depth from **real imports** |
| **Crossing reduction** | **DISABLED** | + Re-enable with import-based edges |

---

## 🔧 Конкретные места для изменений

### 1. Scanner - Extract Imports

**File:** `src/scanners/local_scanner.py`
**Location:** `_scan_file()` method, line 107-152

```python
# ДОБАВИТЬ после чтения content:
def _extract_imports(self, content: str, extension: str) -> List[str]:
    """Extract import statements based on file type"""
    imports = []

    if extension == '.py':
        # Python: import X, from X import Y
        import re
        imports += re.findall(r'^import\s+([\w\.]+)', content, re.MULTILINE)
        imports += re.findall(r'^from\s+([\w\.]+)\s+import', content, re.MULTILINE)

    elif extension in ['.js', '.ts', '.jsx', '.tsx']:
        # JS/TS: import X from 'Y', require('Y')
        imports += re.findall(r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]", content)
        imports += re.findall(r"require\(['\"]([^'\"]+)['\"]\)", content)

    return imports
```

### 2. ScannedFile Dataclass

**File:** `src/scanners/local_scanner.py`
**Location:** lines 17-31

```python
@dataclass
class ScannedFile:
    # ... existing fields ...
    imports: List[str] = field(default_factory=list)  # ДОБАВИТЬ

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['imports'] = self.imports  # ДОБАВИТЬ
        return data
```

### 3. VetkaTreeNode / Qdrant Payload

**File:** `src/memory/qdrant_client.py`
**Location:** VetkaTreeNode dataclass (line 24), _write_to_qdrant (line 217)

```python
@dataclass
class VetkaTreeNode:
    # ... existing fields ...
    imports: List[str] = None  # ДОБАВИТЬ
    imported_by: List[str] = None  # ДОБАВИТЬ (reverse lookup)
```

### 4. Edge Inference - Real Imports

**File:** `src/layout/knowledge_layout.py`
**Location:** `build_prerequisite_edges()` (line 1108)

```python
def build_prerequisite_edges_from_imports(
    file_ids: List[str],
    file_metadata: Dict[str, Dict],  # Должен содержать 'imports'
    similarity_threshold: float = 0.7
) -> Tuple[List[KnowledgeEdge], Dict[str, float]]:
    """
    PHASE 72: Build edges from REAL import statements
    """
    edges = []

    for fid in file_ids:
        imports = file_metadata.get(fid, {}).get('imports', [])
        for imp in imports:
            # Find file that provides this import
            target = resolve_import_to_file(imp, file_ids, file_metadata)
            if target and target != fid:
                edges.append(KnowledgeEdge(
                    source=target,  # Imported file (lower in DAG)
                    target=fid,     # Importing file (higher in DAG)
                    edge_type='import_dependency',
                    weight=1.0
                ))

    return edges, compute_import_depth(edges, file_ids)
```

### 5. Re-enable Crossing Minimization

**File:** `src/layout/semantic_sugiyama.py`
**Location:** line 309-312

```python
# РАСКОММЕНТИРОВАТЬ и исправить:
if edge_type == 'import_dependency':  # Only for real imports
    minimize_crossings(positions, layers, edges, iterations=5, x_spread=x_spread)
```

---

## 📋 Список недостающих полей

### ScannedFile
- [ ] `imports: List[str]` - Extracted import statements
- [ ] `exports: List[str]` - Exported symbols (optional)

### VetkaTreeNode (Qdrant)
- [ ] `imports: List[str]` - Import dependencies
- [ ] `imported_by: List[str]` - Reverse dependencies
- [ ] `import_depth: int` - Depth in import DAG

### SemanticNode
- [ ] `import_parents: List[str]` - Files this imports from
- [ ] `import_children: List[str]` - Files that import this

### Qdrant Payload
- [ ] `dependencies` field in payload dict
- [ ] `dependency_score` for ranking

### KnowledgeEdge
- [ ] New type: `'import_dependency'` (vs existing `'prerequisite'`)
- [ ] `source_line: int` - Line number of import (optional)

---

## 🚨 Critical Findings Summary

1. **Scanner не парсит imports** → Зависимости угадываются через similarity
2. **TreeNode не хранит dependencies** → Невозможен real import DAG
3. **Y вычисляется из similarity DAG** → Не отражает реальный import order
4. **Crossing minimization ОТКЛЮЧЕН** → Edges пересекаются
5. **Граф не персистится** → Пересчёт при каждом запросе

---

## 🎯 Рекомендуемый порядок исправлений

1. **Phase 72.1:** Add import extraction to LocalScanner
2. **Phase 72.2:** Extend ScannedFile/VetkaTreeNode with imports field
3. **Phase 72.3:** Build import DAG in knowledge_layout.py
4. **Phase 72.4:** Calculate Y from import depth (not similarity)
5. **Phase 72.5:** Re-enable crossing minimization with import edges
6. **Phase 72.6:** Persist dependency graph to Qdrant

---

*End of Audit Report*
