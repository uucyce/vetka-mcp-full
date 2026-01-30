# 🔬 RESEARCH GAPS FOR GROK - VETKA PROJECT
**Статус:** Ready for Grok investigation  
**Дата:** 20 декабря 2025  
**Назначение:** Topics where Claude exhausted knowledge, need Grok's research capability

---

## 🎯 OVERVIEW

Claude создал практическую документацию на основе:
- ✅ Working code (Phase 14-15)
- ✅ Theoretical frameworks (Sugiyama 1981)
- ✅ DeepSeek-OCR paper (October 2025)

**НО есть пробелы** где нужны свежие исследования + синтез информации. Это для Grok!

---

## TOPIC 1: OPTIMAL LAYER HEIGHT FOR VARYING TREE SIZES

### Current State (Claude):
```
EMPIRICAL VALUE (работает сейчас):
├─ LAYER_HEIGHT = 80px
├─ Found experimentally for VETKA Project (172 files)
├─ Tested on M1 MacBook, Firefox, Chrome
└─ But: не ясно как масштабируется на:
   ├─ 10,000 файлов (корпоративное дерево)
   ├─ 1,000,000 файлов (огромные системы)
   ├─ 5 слоев глубины vs 20 слоев
   └─ Different aspect ratios (ultrawide 5K displays)
```

### What We Need (for Grok):
```
ИССЛЕДОВАНИЕ: Зависимость LAYER_HEIGHT от параметров

Методология:
├─ Собрать данные из 10+ real-world projects
│  ├─ Linux kernel (8+ million lines)
│  ├─ Corporate repos (various sizes: 100, 1000, 10000 files)
│  ├─ Scientific data trees
│  └─ Academic paper hierarchies
│
├─ Для каждого:
│  ├─ Measure visual comfort (когда нужна прокрутка?)
│  ├─ Measure overlap/collision率 (percent of overlapping nodes)
│  ├─ Measure readability (font size needed?)
│  └─ Record: num_files, num_layers, max_depth, aspect_ratio
│
└─ Анализ:
   ├─ LAYER_HEIGHT как function(num_files, depth, viewport_height)
   ├─ Найти формулу или lookup table
   └─ Validate на новых данных

OUTPUT:
Формула типа:
  LAYER_HEIGHT = 50 + 30 * (1 - depth/max_depth) + viewport_height * 0.01
  
Или: таблица lookup по размеру дерева
```

---

## TOPIC 2: SEMANTIC SIMILARITY vs STRUCTURAL HIERARCHY

### Current State (Claude):
```
ПРОБЛЕМА:
├─ Sugiyama Hybrid работает для DIR структуры (depth-based)
├─ Knowledge Graph mode использует in/out degree
├─ НО: семантическая близость может ПРОТИВОРЕЧИТЬ иерархии!

ПРИМЕР:
├─ File A: "quantum_computing.py" (depth=3)
├─ File B: "quantum_basics.md" (depth=1)
├─ Семантически ОЧЕНЬ близки (cosine ~ 0.95)
├─ Но структурно ДАЛЕКО (depth=3 vs depth=1)
│
└─ Sugiyama разместит их по Y (depth) отдельно
   └─ Визуально друг от друга будут на 160px!
   └─ Может быть НЕПРАВИЛЬНО?
```

### What We Need (for Grok):
```
ИССЛЕДОВАНИЕ: When to prioritize semantic vs structural?

Разделы:
├─ 1. Literature review
│  ├─ How do other graph layout algorithms handle this?
│  │  ├─ Force-directed graphs (D3.js approach)
│  │  ├─ Hierarchical clustering visualizations
│  │  ├─ Knowledge graph visualizations (Neo4j, Gephi)
│  │  └─ Document similarity trees
│  │
│  └─ What do UX studies say?
│     ├─ Do users prefer hierarchical or semantic grouping?
│     ├─ Mixed mode (hybrid weighting)?
│     └─ Context-dependent (toggle between modes)?
│
├─ 2. Quantitative analysis
│  ├─ Metric: "structural coherence" (how well does Sugiyama preserve hierarchy?)
│  ├─ Metric: "semantic coherence" (how well does X-axis group similar items?)
│  ├─ Trade-off function: structural_weight + semantic_weight
│  │  (where weights sum to 1.0)
│  └─ Test different weight ratios (0.1:0.9, 0.3:0.7, 0.5:0.5, etc.)
│
├─ 3. Implementation strategies
│  ├─ Option A: Pure structural (current Sugiyama)
│  │  └─ Pros: clear hierarchy, easy to navigate
│  │  └─ Cons: semantically similar items far apart
│  │
│  ├─ Option B: Pure semantic (force-directed on embeddings)
│  │  └─ Pros: similar items close, UMAP-like
│  │  └─ Cons: no hierarchy visible, disorientation
│  │
│  ├─ Option C: Hybrid (Sugiyama Y-axis + semantic X/Z)
│  │  └─ Current VETKA approach
│  │  └─ Pros/cons: needs empirical validation!
│  │
│  └─ Option D: Multi-view (toggle between A and B)
│     └─ Transition animation between views
│     └─ UX research: is switching confusing?
│
└─ 4. Recommendations
   └─ Formula for optimal weight blending
   └─ Decision tree: "use this strategy when..."
```

---

## TOPIC 3: DEEPSEEK-OCR HALLUCINATION RATES BY DOCUMENT TYPE

### Current State (Claude):
```
ИНФОРМАЦИЯ ИЗ DEEPSEEK PAPER:
├─ FOX benchmark: 97% accuracy at 10x compression
├─ OmniDocBench: better than GOT-OCR2.0
├─ BUT: "hallucinations" mentioned at 15x+ compression
│
└─ НО НЕ ПОНЯТНО:
   ├─ Hallucination rate по типам документов?
   │  ├─ Tables: X% hallucinations
   │  ├─ Formulas: Y% hallucinations
   │  ├─ Code snippets: Z% hallucinations
   │  └─ Handwritten: A% hallucinations
   │
   ├─ Какие ошибки типичные?
   │  ├─ Missing content?
   │  ├─ Duplicate content?
   │  ├─ Invented content?
   │  └─ Confidence calibration (is 0.98 really 98%)?
   │
   └─ Чем лучше других OCR методов?
      ├─ vs Tesseract
      ├─ vs PaddleOCR
      ├─ vs Google Vision API
      └─ для каждого типа документа
```

### What We Need (for Grok):
```
ИССЛЕДОВАНИЕ: DeepSeek-OCR Quality & Reliability

Структура:
├─ 1. Benchmark analysis
│  ├─ Собрать результаты всех public benchmarks
│  │  ├─ FOX (document understanding)
│  │  ├─ OmniDocBench (comprehensive)
│  │  ├─ CROHME (mathematical formulas)
│  │  ├─ TableBank (table extraction)
│  │  └─ Other OCR benchmarks (where DeepSeek was tested)
│  │
│  └─ Aggregated metrics:
│     ├─ Macro-average F1 score across all
│     ├─ Per-type breakdown (table, formula, text, etc.)
│     └─ Confidence calibration analysis
│
├─ 2. Hallucination taxonomy
│  ├─ Types of errors:
│  │  ├─ Type 1: Missing content (incomplete OCR)
│  │  │  └─ Rate by document type
│  │  ├─ Type 2: Duplicate content (repeated text)
│  │  │  └─ Rate by document type
│  │  ├─ Type 3: Invented content (true hallucination)
│  │  │  └─ Rate by document type
│  │  ├─ Type 4: Format errors (wrong markdown, broken tables)
│  │  │  └─ Rate by document type
│  │  └─ Type 5: Confidence drift (says 0.95 but only 0.70 correct)
│  │     └─ Rate by document type
│  │
│  └─ Severity classification:
│     ├─ Critical (changes meaning)
│     ├─ Major (loses important info)
│     ├─ Minor (formatting issues)
│     └─ Negligible (typos, spacing)
│
├─ 3. Comparative analysis
│  ├─ DeepSeek-OCR vs alternatives:
│  │  ├─ Speed comparison (tokens/sec)
│  │  ├─ Quality comparison (F1, CER, WER)
│  │  ├─ Resource efficiency (GB needed)
│  │  ├─ Language support (which supports 100+ languages?)
│  │  └─ Cost (open source vs API)
│  │
│  └─ Matrix: which tool best for each document type?
│
├─ 4. Real-world application recommendations
│  ├─ When to use DeepSeek (best-case scenarios)
│  ├─ When NOT to use (worst-case scenarios)
│  ├─ Hybrid approaches (combine with other tools)
│  │  ├─ DeepSeek-OCR + Tesseract fallback
│  │  ├─ DeepSeek-OCR + LLM verification
│  │  └─ DeepSeek-OCR + human review
│  │
│  └─ Quality assurance workflow for VETKA:
│     └─ Confidence threshold + human review process
│
└─ 5. Output
   └─ Decision table: "Use DeepSeek if (criteria)"
   └─ Confidence thresholds per document type
   └─ Fallback strategy recommendations
```

---

## TOPIC 4: KNOWLEDGE GRAPH EXTRACTION FROM CODE

### Current State (Claude):
```
ТЕКУЩИЙ ПОДХОД:
├─ Directory structure → Y-axis (depth-based layers)
├─ Knowledge level → computed from in/out degree
└─ BUT: это работает только если граф ДА существует!

ПРОБЛЕМА:
├─ Для knowledge graph нужны СВЯЗИ между узлами
├─ Текущая VETKA сканирует файлы, но не извлекает зависимости
├─ Например:
│  ├─ File A imports File B (dependency!)
│  ├─ File C references concept from File A (semantic edge!)
│  └─ Document X cites Document Y (citation graph!)
│
└─ Как автоматически построить граф из кода + документов?
```

### What We Need (for Grok):
```
ИССЛЕДОВАНИЕ: Automatic Knowledge Graph Extraction

Разделы:
├─ 1. Code dependency extraction
│  ├─ Parser approaches:
│  │  ├─ Language-specific parsers (Python AST, JS AST, etc.)
│  │  ├─ Generic pattern matching (import/require statements)
│  │  ├─ Abstract syntax trees (full dependency resolution)
│  │  └─ Static analysis (what does function call?)
│  │
│  ├─ Tools review:
│  │  ├─ Existing libraries (Networkx, graph-tool, igraph)
│  │  ├─ Language tools (Python: ast, JS: acorn, etc.)
│  │  ├─ Build system analysis (Makefile, package.json, setup.py)
│  │  └─ New deep learning approaches (CodeBERT, GraphCodeBERT)
│  │
│  └─ Validation:
│     ├─ How accurate is dependency extraction?
│     ├─ False positive rate (incorrectly detected dependency)
│     └─ False negative rate (missed dependency)
│
├─ 2. Document link extraction
│  ├─ Citation graphs (papers citing papers)
│  │  └─ Existing solutions (Semantic Scholar, CrossRef)
│  │
│  ├─ Markdown link extraction
│  │  ├─ [Link text](path/to/file) parsing
│  │  ├─ Relative vs absolute paths
│  │  └─ Cross-document references
│  │
│  ├─ Semantic link extraction (without explicit links)
│  │  ├─ "This chapter builds on Chapter 5 concepts"
│  │  ├─ "Related: see also document_x.pdf"
│  │  └─ Named entity matching across documents
│  │
│  └─ Implementation complexity?
│
├─ 3. Semantic edge extraction
│  ├─ Using embeddings to find implicit connections:
│  │  ├─ Cosine similarity > threshold → edge
│  │  ├─ What threshold optimal? (0.85, 0.90, 0.95?)
│  │  ├─ Type of edge (depends on content)
│  │  └─ Edge weight (similarity score as weight)
│  │
│  ├─ DeepSeek-OCR integration:
│  │  ├─ Extract key concepts from OCR text
│  │  ├─ Match concepts across documents
│  │  └─ Create edges for concept co-occurrence
│  │
│  └─ Validation:
│     ├─ Do extracted edges make sense?
│     ├─ User study: does graph help navigation?
│     └─ Precision/recall metrics
│
├─ 4. Graph quality metrics
│  ├─ Completeness (% of edges captured)
│  ├─ Correctness (% of edges valid)
│  ├─ Connectivity (graph is connected?)
│  ├─ Cycles (DAG properties maintained?)
│  └─ Centrality (which nodes are hubs?)
│
├─ 5. Real-time updates
│  ├─ As files change, update graph incrementally
│  ├─ Performance: what's the cost?
│  ├─ Correctness: can we verify without full rebuild?
│  └─ Visualization: smooth animation as graph changes?
│
└─ 6. Recommendations
   └─ Best approach per use case
   └─ Tools to use (implement vs existing)
   └─ Integration with VETKA architecture
```

---

## TOPIC 5: PHASE TRANSITION FORMULA FOR KNOWLEDGE GRAPH VISUALIZATION

### Current State (Claude):
```
ПРОБЛЕМА:
├─ Directory Mode: Y = depth (0, 1, 2, 3, ...)
├─ Knowledge Mode: Y = knowledge_level (0.0-1.0)
│
└─ Как переходить между режимами БЕЗ LOOKSского дизориентирования?
   ├─ Резкая смена layout → scary
   ├─ Плавная трансформация → красиво!
   ├─ НО: формула для smooth interpolation?
   └─ НЕЯСНО КАК КОДИРОВАТЬ
```

### What We Need (for Grok):
```
ИССЛЕДОВАНИЕ: Smooth Graph Layout Transitions

Разделы:
├─ 1. Theory review
│  ├─ Existing approaches:
│  │  ├─ D3.js transitions (SMACOF algorithm)
│  │  ├─ Force-directed relaxation during transition
│  │  ├─ Optimal transport (Wasserstein distance)
│  │  ├─ Linear interpolation (naive)
│  │  └─ Procrustes alignment (optimal rotation)
│  │
│  └─ Papers/resources:
│     ├─ "Smooth Transitions in Graph Visualization"
│     ├─ Animation in force-directed layouts
│     └─ Perceptual studies on layout changes
│
├─ 2. Problem formulation for VETKA
│  ├─ Source layout (directory mode): positions_dir[node] = {x, y, z}
│  ├─ Target layout (KG mode): positions_kg[node] = {x, y, z}
│  │
│  ├─ Goal: positions(t) smooth path from dir to kg
│  │  └─ t ∈ [0, 1] (0=directory, 1=KG)
│  │
│  └─ Constraints:
│     ├─ No nodes should collide during transition
│     ├─ Visual distinctiveness maintained throughout
│     ├─ Navigation still possible during transition
│     └─ Performance: smooth 60 FPS animation
│
├─ 3. Algorithm comparison
│  ├─ Approach A: Linear interpolation
│  │  ├─ pos(t) = (1-t) * pos_dir + t * pos_kg
│  │  ├─ Pro: trivial to implement
│  │  ├─ Con: may cause collisions mid-way
│  │  └─ Tested? Not in literature
│  │
│  ├─ Approach B: Procrustes-aligned interpolation
│  │  ├─ Align pos_kg to pos_dir via Procrustes transformation
│  │  ├─ Then linearly interpolate
│  │  ├─ Pro: minimizes rotation needed
│  │  ├─ Con: still may have collisions
│  │  └─ Status: used in some vis systems
│  │
│  ├─ Approach C: Force-directed relaxation
│  │  ├─ During transition, apply repulsion forces
│  │  ├─ Intermediate positions avoid collisions
│  │  ├─ Pro: collision-free guaranteed
│  │  ├─ Con: slower, unpredictable
│  │  └─ Status: D3.js standard approach
│  │
│  └─ Approach D: Morphing with intermediate layout
│     ├─ Divide into steps: dir → intermediate1 → intermediate2 → kg
│     ├─ At each step, resolve collisions
│     ├─ Pro: smoother, more control
│     ├─ Con: complex implementation
│     └─ Status: not well studied
│
├─ 4. Empirical validation
│  ├─ Implement each approach
│  ├─ Test on VETKA data (172 files)
│  ├─ Measure:
│  │  ├─ Collision rate (% nodes too close at any t)
│  │  ├─ Visual distinctiveness (can you still see structure?)
│  │  ├─ Disorientation (user study?)
│  │  └─ Performance (frame rate at all t)
│  │
│  └─ Findings:
│     └─ Which approach wins?
│
├─ 5. Implementation details
│  ├─ Animation duration (0.5s, 1.0s, 2.0s?)
│  ├─ Easing function (linear, ease-in-out, cubic?)
│  ├─ Intermediate collision resolution strategy
│  └─ Reverting back (directory ← KG transition)
│
└─ 6. Output
   └─ Formula for positions(t)
   └─ Implementation code (JavaScript for Three.js)
   └─ Performance benchmarks
   └─ UX recommendations
```

---

## TOPIC 6: MULTIMODAL EMBEDDING FUSION (TEXT + VISION + CODE)

### Current State (Claude):
```
ТЕКУЩИЙ ПЛАН:
├─ Text files: embed with Gemma (768 dims)
├─ Visual files: OCR with DeepSeek → embed with Gemma
├─ Code files: embed with CodeBERT? (unknown dims)
│
└─ ПРОБЛЕМА: все в разных embedding spaces!
   ├─ Как найти similarity между text и code?
   ├─ Как найти similarity между image и code?
   ├─ Какой fusion метод лучше?
   └─ Что о multimodal embeddings известно в 2025?
```

### What We Need (for Grok):
```
ИССЛЕДОВАНИЕ: State-of-the-art Multimodal Embeddings (Dec 2025)

Разделы:
├─ 1. Current landscape (Dec 2025)
│  ├─ Available models:
│  │  ├─ CLIP (text + image, but no code)
│  │  ├─ CodeBERT (code, no vision)
│  │  ├─ Qwen2-VL (visual + text, no code)
│  │  ├─ Llava (image + text, no code)
│  │  ├─ GraphCodeBERT (code only)
│  │  └─ Any new unified models in Oct-Dec 2025?
│  │
│  ├─ Dimensions:
│  │  ├─ CLIP: 512 dims
│  │  ├─ Gemma: 768 dims
│  │  ├─ CodeBERT: 768 dims
│  │  ├─ BGE: 1024 dims
│  │  └─ Any alignment needed?
│  │
│  └─ Performance/size trade-offs
│
├─ 2. Fusion strategies
│  ├─ Strategy A: Normalize all to 768 dims
│  │  ├─ Gemma (768) → keep
│  │  ├─ CLIP (512) → project to 768
│  │  ├─ CodeBERT (768) → keep
│  │  └─ Concatenate all? → 768 x 3 = 2304 dims!
│  │
│  ├─ Strategy B: Reduce all to 256 dims (efficiency)
│  │  ├─ Matryoshka embeddings approach
│  │  ├─ Keeps information at 256 dims
│  │  └─ Query time faster
│  │
│  ├─ Strategy C: Separate indices
│  │  ├─ Text index (Qdrant, Gemma embeddings)
│  │  ├─ Code index (Milvus, CodeBERT embeddings)
│  │  ├─ Image index (Qdrant, CLIP embeddings)
│  │  └─ Unified search via late fusion
│  │
│  ├─ Strategy D: Late fusion with learned weights
│  │  ├─ Train small NN to combine scores
│  │  ├─ text_score + code_score + image_score (weighted)
│  │  └─ Requires labeled data
│  │
│  └─ Strategy E: Universal embedding space (future?)
│     ├─ Single model that handles text+code+vision
│     ├─ DeepSeek-VL3? Qwen3-VL? (coming 2026?)
│     └─ TBD
│
├─ 3. Qdrant multimodal support (Dec 2025)
│  ├─ What's the state of Qdrant multimodal?
│  ├─ Can store multiple embedding types?
│  ├─ Can query across modalities?
│  ├─ Performance implications?
│  └─ Any new features in recent versions?
│
├─ 4. Semantic search across modalities
│  ├─ Query: "machine learning tutorial"
│  │  ├─ Should match: text docs, code examples, diagrams
│  │  ├─ How to rank (code vs tutorial vs image)?
│  │  └─ User preference?
│  │
│  ├─ Fusion scoring:
│  │  ├─ Simple: max(scores) across modalities
│  │  ├─ Average: mean(scores)
│  │  ├─ Weighted: w_text * text_score + w_code * code_score + ...
│  │  └─ Which performs best?
│  │
│  └─ Validation:
│     └─ Relevance judgments needed
│
├─ 5. Real-world implementation
│  ├─ VETKA specific:
│  │  ├─ Text files (Markdown, docs): Gemma 768
│  │  ├─ Code files (.py, .js): CodeBERT 768
│  │  ├─ Images (OCR'd): DeepSeek-OCR → Gemma 768
│  │  ├─ Diagrams: extract + OCR → Gemma 768
│  │  └─ All in single Qdrant index!
│  │
│  └─ Complexity:
│     ├─ Preprocessing pipeline (different extractors)
│     ├─ Type detection (which extractor to use?)
│     ├─ Quality control (confidence per type)
│     └─ Incremental updates
│
├─ 6. Recommendations
│  ├─ Best fusion strategy for VETKA
│  ├─ Model choices (which to use)
│  ├─ Dimension choices (efficiency vs quality)
│  ├─ Implementation roadmap
│  └─ Expected challenges
│
└─ 7. Output
   └─ Fusion algorithm code
   └─ Performance benchmarks
   └─ Qdrant schema design
   └─ Query/indexing pipeline
```

---

## SUMMARY: GROK RESEARCH TOPICS

```
PRIORITY RANKING:

🔴 HIGH (needed for Phase 17-18):
├─ Topic 2: Semantic vs Structural hierarchy
├─ Topic 3: DeepSeek-OCR hallucination rates
└─ Topic 6: Multimodal embedding fusion

🟡 MEDIUM (nice to have):
├─ Topic 1: Optimal layer height formula
├─ Topic 4: Knowledge graph extraction
└─ Topic 5: Phase transition formula

🟢 LOW (future exploration):
└─ Advanced topics (multimodal models 2026+)

ESTIMATED TIME (Grok research each):
├─ Topic 1: 2-3 hours (moderate scope)
├─ Topic 2: 3-4 hours (needs lit review + empirical work)
├─ Topic 3: 2-3 hours (paper analysis + synthesis)
├─ Topic 4: 4-6 hours (high complexity)
├─ Topic 5: 3-4 hours (algorithm design)
└─ Topic 6: 3-4 hours (landscape analysis)

TOTAL: 17-24 hours of focused research
```

---

## HOW TO SUBMIT TO GROK

**Format for each request:**

```
Topic: [Name]

Background:
[What Claude knows and did]

Research Question:
[What we need to know]

Specific Requirements:
- Criteria for answer
- Depth needed
- Any constraints

Desired Output:
- Format (formula, comparison table, code, etc.)
- Size (brief summary vs comprehensive report)
- Any deliverables

Timeline:
- When needed
- Priority level
```

---

**Создано:** 20 декабря 2025  
**Статус:** Ready to send to Grok  
**Total Research Hours:** 17-24 hours
