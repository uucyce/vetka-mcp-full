# 🔍 GROK RESEARCH RECOMMENDATIONS + ARCHITECTURE AUDIT
## Все рекомендации + Checklist для Claude Code

**Дата:** 22 декабря 2025  
**Статус:** Подготовка к Phase 17-19  
**Цель:** Убедиться что ничего не упущено перед большим скачком  

---

## 📋 ЧАСТЬ 1: РЕКОМЕНДАЦИИ GROK (выписано из документов)

### Topic 1: Optimal Layer Height Formula
**Статус:** ❓ НУЖНО ПРОВЕРИТЬ - используется ли?

```python
def optimal_layer_height(max_depth, total_nodes, screen_height=1080, base_height=80):
    depth_factor = max_depth
    density_factor = 1 + math.log10(total_nodes / 100)
    layer_height = base_height * (screen_height / 1080) / (depth_factor * (1 + 0.3 * density_factor))
    return max(50, min(200, layer_height))
```

**Где должно быть:** `src/visualizer/sugiyama_layout.js` или `src/visualizer/kg_layout.py`  
**Текущее значение:** `LAYER_HEIGHT = 80` (hardcoded)  
**Проблема:** Не адаптируется по плотности узлов  
**Action:** Заменить hardcoded на dynamic

---

### Topic 2: Semantic vs Structural Hierarchy (KG Mode)
**Статус:** ⚠️ ЧАСТИЧНО РЕАЛИЗОВАНО

**Рекомендация Grok:**
```python
knowledge_level = 0.6 * prerequisite_depth + 0.4 * embedding_novelty_score
```

**Где должно быть:** `src/transformers/kg_transformer.py`  
**Текущее:** Может быть использована простая формула in_degree/out_degree  
**Нужна интеграция:** PREREQ++ model для лучшей точности  
**Action:** Проверить реализацию, добавить hybrid formula

---

### Topic 3: DeepSeek-OCR Hallucination Rates
**Статус:** 📋 ТОЛЬКО В ПЛАНАХ (Phase 18)

**Данные (Dec 2025):**
```
10x compression:  97.2% accuracy, 2.1% hallucination ✅
15x compression:  89.4% accuracy, 8.7% hallucination
20x compression:  78.1% accuracy, 18.3% hallucination ❌
```

**Рекомендация:** 
- Использовать только ≤12x compression
- Fallback на Tesseract при confidence < 0.85
- Post-processing: entity linking к KG

**Action:** Документировать в Phase 18 spec

---

### Topic 4: KG Extraction Methods (2025 SOTA)
**Статус:** ⚠️ НЕИЗВЕСТНО

**Лучшие методы 2025:**
1. **CodeGraph** (Microsoft) - AST + LLM → 94% F1
2. **Doc2Graph** (Google) - DeepSeek-OCR + relation extraction
3. **Tree-of-Thoughts prompting** - Claude structured output

**Рекомендуемый pipeline:**
```
File → DeepSeek-OCR → Structured text → CodeGraph/Doc2Graph → Triples → Qdrant
```

**Статус в VETKA:** CodeGraph?Doc2Graph? Unknown  
**Action:** Проверить что используется, если вообще используется

---

### Topic 5: Phase Transition Formula (Directory ↔ Knowledge)
**Статус:** ❓ НУЖНО РЕАЛИЗОВАТЬ

**Формула:**
```python
transition_score = 0.5 * semantic_density + 0.3 * prerequisite_strength + 0.2 * user_interaction

if transition_score > 0.7:
    switch to Knowledge mode
else:
    stay in Directory mode
```

**Action:** Реализовать автоматический trigger

---

### Topic 6: Multimodal Embedding Fusion (Text + Image + Code)
**Статус:** 🤔 ТЕКУЩИЙ BOTTLENECK

**Текущее в VETKA:**
- Text → Gemma 768
- Image → ???
- Code → ???

**Рекомендация Grok (2025 SOTA):**
```
Text → Gemma-768
Image → DeepSeek-OCR → text → Gemma-768
Code → CodeGemma → 768
Late fusion: concatenate + linear projection → 768 unified space
```

**Qdrant schema:**
```json
{
  "vectors": {
    "text": {"size": 768, "distance": "Cosine"},
    "unified": {"size": 768, "distance": "Cosine"}
  },
  "payload": {"modality": ["text", "image", "code"]}
}
```

**Action:** Проверить что используется, заполнить пробелы

---

## 📊 ЧАСТЬ 2: ВСЕ РОАДМЭПЫ Phase 10+ (восстановлено)

### Phase 10: Real-time Sync (from docs)
```
├─ Socket.IO listeners for tree updates
├─ Incremental layout recalculation
├─ Broadcast to all clients
└─ ✅ COMPLETED (документ упоминает Phase 14-15)
```

### Phase 11: Vector Search Enhancement
```
├─ Weaviate VetkaLeaf collection
├─ Qdrant VetkaTree collection  
├─ Triple Write architecture
└─ ✅ COMPLETED (используется в текущей версии)
```

### Phase 12: Agent Orchestration
```
├─ PM → Dev → QA → ARC chain
├─ Baton passing mechanism
├─ API Aggregator (8 providers)
└─ ✅ COMPLETED (orchestrator_with_elisya.py)
```

### Phase 13: Y-Axis Enhancement (planned)
```
├─ Knowledge Level Calculator
├─ Time offset within layer
├─ Semantic offset (UMAP 1D)
└─ ❓ STATUS UNKNOWN
```

### Phase 14: X-Axis Enhancement (planned)
```
├─ Alternative files clustering
├─ Semantic clustering (HDBSCAN/UMAP)
├─ Contrastive learning
└─ ❓ STATUS UNKNOWN
```

### Phase 15: Z-Axis + Duplicates (IN PROGRESS)
```
├─ Near-duplicate detection (cosine > 0.95)
├─ Z-compression for duplicates
├─ Forest organization (MDS layout)
├─ Rich Context Integration
└─ ✅ PARTIALLY COMPLETED (Phase 15-3 just finished)
```

### Phase 16: Visual Polish (planned)
```
├─ Magnification under cursor
├─ LOD (Level of Detail)
├─ Colors by file type
├─ Organic branch curves
└─ ⏳ NOT STARTED
```

### Phase 17: Semantic Mode (TARGET)
```
├─ Mode 2: Layer = knowledge_level
├─ Knowledge Graph integration
├─ Prerequisite chains
└─ ⏳ READY TO START (document created)
```

### Phase 18: DeepSeek-OCR
```
├─ Document text extraction (10x compression)
├─ Multimodal embeddings
├─ Semantic search with images/PDFs
└─ 📋 PLANNED
```

### Phase 19: Advanced Features (future)
```
├─ Interactive drag-to-create
├─ Concept search + auto-positioning
├─ Multi-modal KG
└─ 🔮 FUTURE
```

---

## 🔴 ЧАСТЬ 3: КРИТИЧЕСКИЕ ВОПРОСЫ

### Вопрос 1: Weaviate vs Qdrant
**Текущее:**
- Weaviate: VetkaLeaf collection (file embeddings)
- Qdrant: VetkaTree collection (semantic search)

**Вопрос:** Зачем ДВА? Второе колесо как mem0?

**Ответ (из документов):**
```
Weaviate: Tree structure + chat history (relational)
Qdrant: Vector search (semantic similarity)

Нужны оба!
├─ Weaviate = graph relationships
└─ Qdrant = similarity search
```

**Action:** Проверить оба используются

---

### Вопрос 2: Gemma Embedding — где используется?

**Текущее:**
- Gemma 2B = локальный LLM (llama3.2, qwen2.5)
- Gemma для embeddings? Или используется другое?

**Из документов:**
```
Embeddings: Gemma 2B (768 dims)
Vectorization: Sentence-Transformers
```

**Action:** Проверить какая модель РЕАЛЬНО используется для embeddings
- Gemma-2B?
- Sentence-Transformers (all-MiniLM-L6-v2)?
- CLIP?
- Что-то другое?

**Нужно в логах:** `[EMBED] Using model: ___`

---

### Вопрос 3: Достаточно ли данных для KG?

**Текущее:**
- Qdrant содержит только docs/ (90 файлов)
- src/, config/, app/ - НЕ сканируются

**Для KG нужно:**
- Все файлы в проекте
- Связи между ними
- Семантические отношения

**Action:** Проверить что сканируется, расширить на весь проект

---

### Вопрос 4: CAM интеграция

**Статус:** Упоминается но не понятно насколько реализовано

**Нужно:**
- Branching при новом контенте
- Pruning при low-entropy
- Merging похожих
- Surprise metric для автоматизации

**Action:** Проверить что реализовано из 3 операций

---

### Вопрос 5: Surprise Metric

**Статус:** Только что добавлено в документы, реализовано ли?

```python
surprise = 1 - cosine(new_embedding, avg_subtree_embedding)

if surprise > 0.65: branch
elif surprise > 0.3: append
else: merge/prune
```

**Action:** Проверить наличие в коде

---

## ✅ ЧАСТЬ 4: COMPREHENSIVE CHECKLIST

### BACKEND Components

- [ ] **Weaviate**
  - [ ] VetkaLeaf collection exists
  - [ ] Data indexed
  - [ ] Query works
  - [ ] Connected in code

- [ ] **Qdrant**
  - [ ] VetkaTree collection exists
  - [ ] Data indexed
  - [ ] Search works
  - [ ] Connected in code

- [ ] **Gemma/Embeddings**
  - [ ] Model loaded
  - [ ] Embeddings computed
  - [ ] 768-dim confirmed
  - [ ] In logs visible

- [ ] **Elisya (Context Middleware)**
  - [ ] Import in orchestrator
  - [ ] Context assembly works
  - [ ] Qdrant integration OK
  - [ ] Rich context (2000+ chars) delivered

- [ ] **CAM Engine**
  - [ ] Branching logic exists
  - [ ] Pruning logic exists
  - [ ] Merging logic exists
  - [ ] Operations trigger correctly

- [ ] **Surprise Metric**
  - [ ] Formula implemented
  - [ ] Threshold logic (0.65, 0.3)
  - [ ] Operations mapped to surprise
  - [ ] Logged

- [ ] **Agent Orchestration**
  - [ ] PM → Dev → QA chain works
  - [ ] Rich context delivered
  - [ ] Responses > 1000 chars
  - [ ] All 3-4 agents get context

### FRONTEND Components

- [ ] **Tree Renderer (Three.js)**
  - [ ] Sprites/CanvasTexture working
  - [ ] No infinite lines
  - [ ] Positions correct
  - [ ] Real-time updates

- [ ] **Controls**
  - [ ] Directory/Knowledge toggle ready
  - [ ] Zoom works
  - [ ] Reset works
  - [ ] LOD implemented

- [ ] **Panels**
  - [ ] Info panel shows stats
  - [ ] Chat panel works
  - [ ] Artifact panel (if implemented)
  - [ ] No layout bugs

### Data Pipeline

- [ ] **File Scanning**
  - [ ] DocsScanner works
  - [ ] All folders scanned (not just docs/)
  - [ ] Metadata correct
  - [ ] Paths absolute

- [ ] **Vectorization**
  - [ ] Every file gets embedding
  - [ ] 768-dim confirmed
  - [ ] Stored in Qdrant
  - [ ] Searchable

- [ ] **Knowledge Graph**
  - [ ] Prerequisite edges extracted
  - [ ] Similarity > 0.75 threshold
  - [ ] Directed edges in both DBs
  - [ ] Counts correct

- [ ] **Layout Calculation**
  - [ ] Y-axis dynamic (not hardcoded 80px)
  - [ ] X-axis angular distribution
  - [ ] Z-axis for duplicates/forest
  - [ ] Soft repulsion applied
  - [ ] Positions in correct ranges

### Integration Points

- [ ] **API Endpoints**
  - [ ] /api/tree/data works
  - [ ] /api/tree/kg-mode exists
  - [ ] /api/chat receives context
  - [ ] /api/health returns status

- [ ] **Socket.IO**
  - [ ] Real-time updates
  - [ ] tree_updated events
  - [ ] No dropped messages
  - [ ] All clients receive

- [ ] **Database Consistency**
  - [ ] Triple Write: Weaviate + Qdrant + ChangeLog
  - [ ] No orphaned records
  - [ ] IDs match across DBs
  - [ ] Sync correct

### Code Quality

- [ ] **No Dead Code**
  - [ ] Mem0 removed? Or still there?
  - [ ] Old test files not loaded
  - [ ] main.py from Phase 5001 not 5000
  - [ ] Paths correct

- [ ] **Redundant Code**
  - [ ] Duplicate functionality removed
  - [ ] Clear separation of concerns
  - [ ] No "zombie" modules

- [ ] **Documentation**
  - [ ] Matches actual code
  - [ ] Examples work
  - [ ] No outdated references

---

## 🚀 ЧАСТЬ 5: ПРОМТ ДЛЯ CLAUDE CODE

Буду давать отдельно как промт-документ

---

**Готово к следующему шагу?** 🎯

Дальше:
1. Даю промт для Claude Code (проверка кода)
2. Ты запускаешь и даёшь результаты
3. Я анализирую и даю новый roadmap
4. Чистка + новое видение Phase 17-19
