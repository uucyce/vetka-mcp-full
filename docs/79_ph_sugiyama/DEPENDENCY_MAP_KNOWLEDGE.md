# 🗺️ DEPENDENCY MAP: KNOWLEDGE MODE

**Фокус:** Семантические кластеры, знание (KL), связи между файлами
**Mode:** `?mode=knowledge` (ещё не работает, требует fix)
**Визуализация:** Теги (кластеры) с файлами, сгруппированными по смыслу

---

## 🔄 DATA FLOW

```
VETKA PROJECT (embeddings)
    ↓
[Qdrant: vetka_elisya collection]
    payload: {path, name, content, content_hash, embedding}
    ↓
[tree_routes.py:548-667] GET KNOWLEDGE GRAPH
    calls: build_knowledge_graph_from_qdrant()
    ↓
[knowledge_layout.py:*] BUILD SEMANTIC GRAPH
    Step 1: cluster_files_to_tags() via HDBSCAN
    Step 2: build_prerequisite_edges() via similarity
    Step 3: calculate_knowledge_positions() via Sugiyama
    ↓
[Output] {tags, edges, positions, knowledge_levels}
    Y = knowledge_level (не depth!)
    X = semantic fan
    ↓
[tree_routes.py:638-654] BUILD NODES & EDGES (SEMANTIC)
    nodes = [tags, files]
    edges = [semantic edges]
    ↓
[API Response] mode='knowledge'
    ↓
[Client/Canvas] 3D Visualization (semantic view)
```

---

## 📊 LAYER STRUCTURE: KNOWLEDGE MODE

```
KNOWLEDGE LEVEL 1.0 (Advanced/Specialized):
┌──────────────────────────────────────────────────┐
│ Advanced Architectures                           │
│ ├─ ML Models (Y≈0.95)                           │
│ ├─ 3D Rendering (Y≈0.92)                        │
│ └─ Performance Optimization (Y≈0.88)            │
└──────────────────────────────────────────────────┘

KNOWLEDGE LEVEL 0.5 (Intermediate):
┌──────────────────────────────────────────────────┐
│ Core Infrastructure                              │
│ ├─ API Utilities (Y≈0.55)                       │
│ ├─ Database Helpers (Y≈0.48)                    │
│ └─ Configuration (Y≈0.52)                       │
└──────────────────────────────────────────────────┘

KNOWLEDGE LEVEL 0.1 (Fundamental):
┌──────────────────────────────────────────────────┐
│ Foundational Concepts                            │
│ ├─ Base Classes (Y≈0.15)                        │
│ ├─ Type Definitions (Y≈0.12)                    │
│ └─ Constants (Y≈0.18)                           │
└──────────────────────────────────────────────────┘
```

**КЛЮЧЕВОЕ ОТЛИЧИЕ:** Y ≠ depth! Y зависит от **знаний требуемых для понимания файла**.

---

## 🧮 CORE FORMULAS (KNOWLEDGE MODE)

### Formula 1: Knowledge Level (KL) - ГЛАВНАЯ

**Файл:** `knowledge_layout.py:207-234`
**Формула:**
```python
def compute_knowledge_level_enhanced(centrality_score, rrf_score, max_centrality):
    # Step 1: Inverse centrality (low centrality = specialized = HIGH KL)
    centrality_normalized = 1.0 - (centrality_score / (max_centrality + 1e-8))

    # Step 2: Apply sigmoid for smooth spread
    sigmoid = 1.0 / (1.0 + exp(-10 * (centrality_normalized - 0.5)))

    # Step 3: Add RRF boost (importance)
    rrf_boost = rrf_score * 0.15  # Max +0.15

    # Final KL
    kl = 0.1 + (sigmoid * 0.75) + rrf_boost
    return max(0.1, min(1.0, kl))
```

**Что это значит:**
- Файлы, которые используются **везде** → LOW KL (0.1 = foundation)
- Файлы, которые используются **мало** → HIGH KL (0.9 = specialized)
- Важные файлы (RRF) → +0.15 boost

**Примеры:**
- `__init__.py` (везде используется): centrality=1.0 → KL≈0.1
- `ml_model.py` (специализированный): centrality=0.1 → KL≈0.85
- `utils.py` + RRF=0.8 (important common): KL = 0.1 + sigmoid(0.0) * 0.75 + 0.12 ≈ 0.45

---

### Formula 2: File Spacing (in cluster)

**Файл:** `knowledge_layout.py:242-293`
**Формула:**
```python
def compute_file_spacing(num_files, semantic_variance, kl_variance, depth):
    # Factor 1: Count scaling
    count_factor = sqrt(num_files / max_files_per_cluster)
    count_factor = max(1.0, count_factor)  # Don't shrink

    # Factor 2: Semantic diversity
    variance_factor = 1.0 + semantic_variance * 0.8  # Up to 1.8x

    # Factor 3: KL diversity
    kl_factor = 1.0 + kl_variance * 0.6  # Up to 1.6x

    # Factor 4: Depth compression
    depth_factor = 1.0 / (1.0 + depth * 0.1)

    file_spacing = BASE_FILE_SPACING * count_factor * variance_factor * kl_factor * depth_factor
    # BASE_FILE_SPACING = 100px
```

**Интерпретация:**
- Много файлов в кластере → большей spacing
- Разные семантически → больше spacing
- Разные по KL → больше spacing
- Глубокие кластеры → компактнее

**Примеры:**
- 1 файл, однородный, depth=0: spacing = 100 * 1.0 * 1.0 * 1.0 * 1.0 = 100px
- 5 файлов, diverse (sem_var=0.7, kl_var=0.5), depth=0:
  - spacing = 100 * 1.58 * 1.56 * 1.3 * 1.0 = 320px
- 10 файлов, depth=3:
  - spacing = 100 * 1.73 * variance_factors * 0.77 ≈ 200px

---

### Formula 3: Cluster Radius

**Файл:** `knowledge_layout.py:296-338`
**Формула:**
```python
def compute_cluster_radius(num_children, semantic_entropy, depth, rrf_weight):
    # Factor 1: Children count
    children_factor = 1.0 + sqrt(num_children) * 0.4

    # Factor 2: Semantic entropy (messiness)
    entropy_factor = 1.0 + semantic_entropy * 0.6  # Up to 1.6x

    # Factor 3: Importance (RRF)
    rrf_factor = 0.8 + rrf_weight * 0.4  # Range [0.8, 1.2]

    # Factor 4: Depth penalty
    depth_factor = 1.0 / (1.0 + depth * 0.15)

    radius = BASE_RADIUS * children_factor * entropy_factor * rrf_factor * depth_factor
    # BASE_RADIUS = 300px
```

**Интерпретация:**
- Много детей → большой radius
- Беспорядочный кластер → большой radius
- Важный кластер (RRF) → больше видимости
- Глубокие кластеры → меньше (компактнее)

---

### Formula 4: Semantic Variance

**Файл:** `knowledge_layout.py:341-367`
**Формула:**
```python
def compute_semantic_variance(embeddings):
    # Stack embeddings
    emb_matrix = normalize(embeddings)

    # Compute pairwise cosine similarities
    sim_matrix = emb_matrix @ emb_matrix.T

    # Variance = 1 - mean_similarity
    mean_sim = mean(sim_matrix)
    variance = 1.0 - mean_sim

    return clamp(variance, 0, 1)
```

**Интерпретация:**
- variance = 0.0: все файлы семантически ОДИНАКОВЫЕ
- variance = 1.0: все файлы РАЗНЫЕ (low similarity)

---

### Formula 5: KL Variance

**Файл:** `knowledge_layout.py:370-386`
**Формула:**
```python
def compute_kl_variance(knowledge_levels):
    kl_array = array(knowledge_levels)
    variance = std(kl_array)  # Standard deviation

    # Normalize to [0, 1]
    normalized = min(1.0, variance / 0.3)
    return normalized
```

**Интерпретация:**
- variance = 0.0: все файлы имеют ОДИНАКОВЫЙ KL
- variance = 1.0: файлы распределены по всему спектру [0.1, 1.0]

---

### Formula 6: Auto-Relocation from INTAKE

**Файл:** `knowledge_layout.py:121-204`
**Алгоритм:**
```python
def auto_relocate_from_intake(file_id, file_embedding, tags):
    best_tag = INTAKE_TAG_ID
    best_score = 0.0

    for tag in tags:
        # Factor 1: Semantic similarity (60% weight)
        semantic_sim = cosine_similarity(file_embedding, tag.centroid)

        # Factor 2: Project match (Kimi's check)
        if project_mismatch:
            semantic_sim *= 0.05  # Almost reject

        # Combined score
        combined = semantic_sim * 0.6 + (0.4 if project_match else 0.0)

        if combined > best_score:
            best_score = combined
            best_tag = tag.id

    # Only relocate if confidence ≥ threshold
    if best_score < INTAKE_MIN_CONFIDENCE (0.65):
        return (INTAKE_TAG_ID, best_score)  # Stay in intake
    else:
        return (best_tag, best_score)  # Relocate
```

**Интерпретация:**
- Новый файл идет в INTAKE (оранжевый кластер)
- Если он похож на существующий кластер И в правильном проекте → relocates
- Если нет → остается в INTAKE (нужен человеческий обзор)

---

## 🔗 FILE-TO-CODE MAPPING

### File: tree_routes.py (Knowledge Graph endpoint)

**Строка 548-667:** Главный endpoint для KNOWLEDGE mode

```python
@router.api_route("/knowledge-graph", methods=["GET", "POST"])
async def get_knowledge_graph(
    request: Request,
    force_refresh: bool = Query(False),
    min_cluster_size: int = Query(3),
    similarity_threshold: float = Query(0.7)
):
    # Line 579-598: Return cached if available
    if not force_refresh and _knowledge_graph_cache['tags'] is not None:
        return {
            'status': 'ok',
            'source': 'cache',
            'tags': _knowledge_graph_cache['tags'],
            'edges': _knowledge_graph_cache['edges'],
            'positions': _knowledge_graph_cache['positions'],
            'knowledge_levels': _knowledge_graph_cache['knowledge_levels'],
        }

    # Line 615-626: Build Knowledge Graph
    from src.layout.knowledge_layout import build_knowledge_graph_from_qdrant

    kg_data = build_knowledge_graph_from_qdrant(
        qdrant_client=qdrant,
        collection_name='vetka_elisya',
        min_cluster_size=min_cluster_size,
        similarity_threshold=similarity_threshold
    )

    # Line 628-634: Cache result
    _knowledge_graph_cache['tags'] = kg_data['tags']
    _knowledge_graph_cache['edges'] = kg_data['edges']
    _knowledge_graph_cache['positions'] = kg_data['positions']
    _knowledge_graph_cache['knowledge_levels'] = kg_data['knowledge_levels']

    return {
        'status': 'ok',
        'source': 'computed',
        'tags': kg_data['tags'],
        'edges': kg_data['edges'],
        'positions': kg_data['positions'],
        'knowledge_levels': kg_data['knowledge_levels']
    }
```

---

### File: knowledge_layout.py (Core logic)

**Строка 1-50:** Data classes

```python
@dataclass
class KnowledgeTag:
    """A semantic cluster/tag"""
    id: str
    name: str
    files: List[str]  # file IDs in this tag
    centroid: Optional[ndarray]  # mean embedding
    depth: int  # hierarchical depth (0=root)
    parent_tag_id: Optional[str]  # hierarchical parent
    position: Dict[str, float]  # {'x': ..., 'y': ..., 'z': ...}
```

**Строка 98-118:** INTAKE branch (Phase 22 v4)

```python
def ensure_intake_branch(tags):
    """Create special intake tag for unclassified files"""
    if INTAKE_TAG_ID not in tags:
        tags[INTAKE_TAG_ID] = KnowledgeTag(
            id=INTAKE_TAG_ID,
            name='Intake',
            files=[],
            color=INTAKE_COLOR,  # '#FFB347' (warm orange)
            depth=0,
            parent_tag_id=None
        )
    return tags
```

---

### File: knowledge_layout.py (Functions chain)

```
build_knowledge_graph_from_qdrant()
    ├─→ ensure_intake_branch()
    ├─→ cluster_files_to_tags()  [HDBSCAN clustering]
    ├─→ build_prerequisite_edges()
    ├─→ compute_knowledge_level_enhanced()  [KL formula]
    ├─→ calculate_knowledge_positions()  [Sugiyama layout]
    ├─→ auto_relocate_from_intake()  [Phase 22 v4]
    └─→ classify_edge()  [Edge types]
        ├─ LOCAL (in cluster)
        ├─ CROSS_CLUSTER (between clusters)
        ├─ TEMPORAL (long-range)
        └─ CHAT_HISTORY (from chat)
```

---

## 🎨 EDGE TYPES (KNOWLEDGE MODE)

| Edge Type | Style | Color | Opacity | Usage |
|-----------|-------|-------|---------|-------|
| LOCAL | solid | #888888 | 0.8 | Files within same tag |
| CROSS_CLUSTER | dashed | #888888 | 0.5 | Files in different tags |
| TEMPORAL | dotted | #FF6B6B | 0.5 | Long-range dependency (>7 days) |
| CHAT_HISTORY | glow | #FFD700 | 0.7 | Reference from chat |

---

## 🧪 VERIFICATION POINTS

### ✅ Check 1: Tags created

```bash
curl -s "http://localhost:5001/api/tree/knowledge-graph" \
  | python3 -c "import sys, json; d=json.load(sys.stdin); \
    tags=d.get('tags', {}); \
    print(f'Tags created: {len(tags)}'); \
    [print(f'  {name}: {len(tag[\"files\"])} files') for name, tag in list(tags.items())[:5]]"
```

**Expected:** 5+ tags, файлы в каждой

---

### ✅ Check 2: Knowledge Levels

```bash
curl ... | python3 -c "import sys, json; d=json.load(sys.stdin); \
  kl=d.get('knowledge_levels', {}); \
  kls=list(kl.values()); \
  print(f'KL range: [{min(kls):.2f}, {max(kls):.2f}]'); \
  print(f'KL mean: {mean(kls):.2f}')"
```

**Expected:** KL in range [0.1, 1.0], разнообразие

---

### ✅ Check 3: Positions distribution

```bash
curl ... | python3 -c "import sys, json; d=json.load(sys.stdin); \
  pos=d.get('positions', {}); \
  ys=[p['y'] for p in pos.values()]; \
  print(f'Y range: [{min(ys):.2f}, {max(ys):.2f}]'); \
  print(f'Y values should spread from 0.1 to 1.0 (KL-based)')"
```

**Expected:** Y values соответствуют KL (не depth!)

---

## 📝 KNOWN ISSUES (KNOWLEDGE MODE)

### Issue 1: Mode not used in get_tree_data

**Проблема:** `?mode=knowledge` игнорируется в основном эндпоинте
**Причина:** Нет условия `if mode == "knowledge"`
**Статус:** ❌ КРИТИЧНОЕ (Маркер A в аудите)
**Fix:** Добавить условие в tree_routes.py:78-420

---

### Issue 2: INTAKE confidence threshold

**Проблема:** Новые файлы могут быть stuck в INTAKE
**Причина:** INTAKE_MIN_CONFIDENCE = 0.65 может быть высоким
**Статус:** 🟡 УЛУЧШЕНИЕ
**Fix:** Может потребоваться A/B testing

---

### Issue 3: Hierarchical tags not fully implemented

**Проблема:** Tags могут иметь parent_tag_id, но layout может не учитывать
**Причина:** Phase 17.15 использует Sugiyama, но иерархия не везде
**Статус:** 🟡 ПЛАНИРУЕТСЯ

---

## 🎯 DEPENDENCIES SUMMARY

```
Qdrant (vetka_elisya collection)
    ├─→ embeddings (from Ollama)
    └─→ payload: {path, name, content, ...}
        └─→ tree_routes.py (/knowledge-graph endpoint)
            └─→ knowledge_layout.py
                ├─→ cluster_files_to_tags()  [HDBSCAN]
                ├─→ build_prerequisite_edges()
                ├─→ compute_knowledge_level_enhanced()  [KL formula]
                ├─→ compute_file_spacing()  [spacing formula]
                ├─→ compute_cluster_radius()  [radius formula]
                ├─→ calculate_knowledge_positions()  [Sugiyama]
                ├─→ auto_relocate_from_intake()  [Phase 22 v4]
                └─→ classify_edge()
                    └─→ API Response (tags, edges, positions, KL)
                        └─→ Client 3D Canvas (semantic view)
```

---

## 🔄 LAYER SEPARATION (KNOWLEDGE vs DIRECTED)

**КРИТИЧНАЯ ТАБЛИЦА:**

| Аспект | DIRECTED MODE | KNOWLEDGE MODE |
|--------|---------------|----------------|
| **Y-координата основана на** | depth папки | knowledge_level файла |
| **X-координата основана на** | fan spread | semantic similarity |
| **Группировка узлов** | структура папок | semantic clusters |
| **Edges значат** | папка содержит | семантическая связь |
| **Root** | VETKA (папка) | INTAKE + теги |
| **Иерархия** | папка → подпапка → файл | тег → файлы |
| **Y-range** | [0, max_depth * Y_PER_DEPTH] | [0.1, 1.0] (KL) |

---

**Конец KNOWLEDGE MODE документации.** ✅

Все формулы семантических кластеров, all dependencies, готово к реализации fix-а.
