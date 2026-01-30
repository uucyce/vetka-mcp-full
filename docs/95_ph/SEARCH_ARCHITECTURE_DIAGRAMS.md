# VETKA Search Architecture - Visual Diagrams

## 1. High-Level System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VETKA SEARCH ECOSYSTEM                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│                              🎨 FRONTEND                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  UnifiedSearchBar Component                                          │  │
│  │  ├─ Input field (300ms debounce)                                    │  │
│  │  ├─ Mode buttons: HYB | SEM | KEY | FILE                            │  │
│  │  ├─ Context prefix selector                                         │  │
│  │  └─ Results panel (paginated, sortable, pinnable)                   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                              ↓ WebSocket                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  useSearch Hook + useSocket Hook                                     │  │
│  │  ├─ Debouncing logic                                                │  │
│  │  ├─ Mode switching                                                  │  │
│  │  ├─ Event listeners (search-results, search-error)                  │  │
│  │  └─ Pagination state                                                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│                            ⚙️ BACKEND                                        │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  search_handlers.py (Socket.IO Layer)                               │   │
│  │  ├─ Validate search_query event                                    │   │
│  │  ├─ Call HybridSearchService.search()                              │   │
│  │  └─ Emit search_results or search_error                            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  HybridSearchService (Orchestrator)                                  │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │   │
│  │  │ Cache Layer      │  │ Parallel Exec    │  │ RRF Fusion       │  │   │
│  │  │ (TTL: 5 min)     │  │ (asyncio)        │  │ (Weighted ranks) │  │   │
│  │  │ (max: 200)       │  │ ├─ Semantic      │  │ ├─ w_semantic: 0.5
│  │  │                  │  │ │ (Qdrant)       │  │ ├─ w_keyword: 0.3│  │   │
│  │  │ Cache miss→      │  │ └─ Keyword       │  │ └─ k=60          │  │   │
│  │  │ Execute search   │  │   (Weaviate)     │  │                  │  │   │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│          ↓ Semantic               ↓ Keyword               ↓ Fused            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │ Qdrant           │  │ Weaviate         │  │ Result formatter │          │
│  │ ├─ 768D Gemma    │  │ ├─ BM25 hybrid   │  │ ├─ rrf_score     │          │
│  │ ├─ Threshold: 0.3│  │ ├─ Alpha: 0.7    │  │ ├─ explanation   │          │
│  │ └─ Metadata      │  │ └─ Score norm    │  │ └─ search_mode   │          │
│  │   preservation   │  │                  │  │                  │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│                         🧠 CONTEXT & MEMORY                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  CAM Engine (Context-Aware Memory)                                   │   │
│  │  ├─ Query history (last 100)                                        │   │
│  │  ├─ Activation scoring                                              │   │
│  │  ├─ Branching (novel: sim < 0.7)                                    │   │
│  │  ├─ Pruning (low-entropy: score < 0.2)                              │   │
│  │  ├─ Merging (similar: sim > 0.92)                                   │   │
│  │  └─ Tool suggestions (NOT in UI)                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  context_fusion.py (Phase 75.3)                                      │   │
│  │  ├─ Spatial context (300 tokens)                                    │   │
│  │  ├─ Pinned files (400 tokens)                                       │   │
│  │  ├─ CAM hints (100 tokens)                                          │   │
│  │  └─ Code context (1200 tokens, lazy)                                │   │
│  │  ═════════════════════════════════════                              │   │
│  │  └─ Unified context (≤2000 tokens) → LLM                            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│                      📡 MCP TOOLS (Claude Code)                              │
│  vetka_search | vetka_search_knowledge | vetka_list_files                    │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. RRF Fusion Logic Flow

```
Input: Query = "authentication flow"
       Mode = "hybrid"
       Limit = 100

       ┌─────────────────────────────────────────┐
       │ 1. Parallel Search Execution            │
       └─────────────────────────────────────────┘
              ↓                    ↓
    ┌─────────────────┐  ┌──────────────────┐
    │ Qdrant Query    │  │ Weaviate Query   │
    │ ─────────────   │  │ ──────────────   │
    │ Embedding Gen   │  │ BM25 Search      │
    │ Vector Search   │  │ Score normalize  │
    └─────────────────┘  └──────────────────┘
           ↓                     ↓
    Results A (50 docs)    Results B (50 docs)
    with scores 0.0-1.0    with scores 0.0-1.0

       ┌─────────────────────────────────────────┐
       │ 2. Normalize Result Sets                │
       └─────────────────────────────────────────┘
           ↓                     ↓
    Ranked: 1-50           Ranked: 1-50

       ┌─────────────────────────────────────────┐
       │ 3. RRF Score Calculation                │
       │ RRF(d) = w_A × 1/(60+rank_A(d))        │
       │        + w_B × 1/(60+rank_B(d))        │
       │ where w_A=0.5, w_B=0.3                 │
       └─────────────────────────────────────────┘
           ↓
    Combined Ranked List (0-80 docs visible)
    with RRF scores combining both sources

       ┌─────────────────────────────────────────┐
       │ 4. Return Top-N Results                 │
       │ (sorted by rrf_score descending)        │
       └─────────────────────────────────────────┘
           ↓
    Final Results: [{id, path, rrf_score,
                     explanation, search_mode,
                     sources: [qdrant, weaviate]},
                    ...]
```

---

## 3. Search Mode Decision Tree

```
                    Query Received
                         │
                         ↓
         ┌───────────────────────────────────┐
         │ Validate Query                    │
         │ • Length ≥ 2 chars                │
         │ • Not empty                       │
         │ • Not duplicate of last query     │
         └───────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ↓               ↓               ↓
    Mode=SEM         Mode=KEY       Mode=HYB
    (Semantic        (Keyword       (Hybrid)
     only)           only)
         │               │               │
         ↓               ↓               ↓
    ┌─────────┐      ┌─────────┐    ┌──────────┐
    │ Qdrant  │      │Weaviate │    │Parallel: │
    │Ready?   │      │Ready?   │    │Qdrant+   │
    └────┬────┘      └────┬────┘    │Weaviate  │
         │                │         └────┬─────┘
     YES │  NO       YES │ NO           │
         ↓   ↓            ↓  ↓           ↓
       ✅  FALLBACK    ✅  FALLBACK    ATTEMPT
            TO              TO          BOTH
           KEY            SEM

    Fallback Chain (if primary fails):
    Semantic fail → Try keyword
    Keyword fail  → Try semantic
    Both fail     → Return error + empty
```

---

## 4. Frontend State Flow (useSearch Hook)

```
┌─────────────────────────────────────────────────────────────┐
│                    useSearch Hook State                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  State Variables:                                            │
│  • query: string                                             │
│  • results: SearchResult[]                                   │
│  • isSearching: boolean                                      │
│  • error: string | null                                      │
│  • totalResults: number                                      │
│  • searchTime: number (ms)                                   │
│  • searchMode: 'hybrid' | 'semantic' | 'keyword' | 'file'   │
│  • displayLimit: number (pagination: 20 at start)           │
│  • hasMore: boolean                                          │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  User Action Flow:                                           │
│                                                               │
│  1. User types in input                                      │
│     setQuery(text)                                           │
│           ↓                                                  │
│           └→ [Effect] Debounce 300ms                        │
│                   ↓                                          │
│                   setIsSearching(true)                       │
│                   setTimeout → executeSearch(query)          │
│                                                               │
│  2. executeSearch() triggered                                │
│     • Check isConnected                                      │
│     • Call searchQuery() → Socket.IO event                   │
│     • State: isSearching = true                              │
│                                                               │
│  3. Server responds                                          │
│     Event: 'search-results' or 'search-error'               │
│                                                               │
│  4. Results received (via window events)                     │
│     • setResults(data.results)                               │
│     • setTotalResults(data.total)                            │
│     • setSearchTime(data.took_ms)                            │
│     • setSearchMode(data.mode)                               │
│     • setIsSearching(false)                                  │
│     • setDisplayLimit(PAGE_SIZE) [reset pagination]         │
│                                                               │
│  5. User clicks "Load More"                                  │
│     loadMore() → setDisplayLimit(prev + PAGE_SIZE)           │
│     → Filtered view updates (via slice in render)            │
│                                                               │
│  6. User changes search mode                                 │
│     setSearchMode(newMode) → [Effect] re-execute search     │
│                                                               │
│  7. User clears search                                       │
│     clearResults()                                           │
│     → Reset ALL state to initial values                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Socket.IO Event Sequence Diagram

```
CLIENT                          SERVER
  │                               │
  ├─ 'search_query' event ────────→│
  │  {text: "auth",               │
  │   limit: 100,                 │
  │   mode: "hybrid",             │
  │   filters: {},                │
  │   min_score: 0.3}             │
  │                               │
  │                      ┌────────┤ search_handlers.py
  │                      │ validate input
  │                      │ call HybridSearchService.search()
  │                      │        ├─ Check cache
  │                      │        ├─ Execute searches (parallel)
  │                      │        │  ├─ Qdrant (50-150ms)
  │                      │        │  └─ Weaviate (80-200ms)
  │                      │        ├─ RRF fusion
  │                      │        └─ Format results
  │                      │
  │← 'search_results' ───┤
  │  {results: [{...}],  │
  │   total: 42,         │
  │   total_raw: 50,     │
  │   filtered: 8,       │
  │   query: "auth",     │
  │   took_ms: 187,      │
  │   mode: "hybrid",    │
  │   sources: [qdrant,  │
  │             weaviate]│
  │   min_score: 0.3}    │
  │                      │
  ├─ Update UI           │
  │  display results     │
  │  hide loading        │
  │  show timing         │
  │
  [If error occurs]
  │← 'search_error' ─────┤
  │  {error: "message",  │
  │   query: "auth"}     │
  │
  ├─ Show error to user  │
  │  hide loading        │
```

---

## 6. CAM (Context-Aware Memory) Operation Diagram

```
                    New Artifact Created
                           │
                           ↓
        ┌──────────────────────────────────────┐
        │ CAM Engine: handle_new_artifact()    │
        │ ├─ Get or compute embedding         │
        │ ├─ Create VETKANode with metadata   │
        │ └─ Find most similar existing node   │
        └──────────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │ Calculate Similarity Score           │
        │ (cosine similarity of embeddings)    │
        └──────────────┬───────────────────────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
          ↓            ↓            ↓
    sim < 0.7     0.7 ≤ sim     sim ≥ 0.92
                    < 0.92
          │            │            │
          ↓            ↓            ↓
    ┌─────────┐  ┌─────────┐  ┌─────────┐
    │ BRANCH  │  │ MERGE   │  │ VARIANT │
    │ (Novel) │  │PROPOSAL │  │(Dup)    │
    │         │  │         │  │         │
    │ Create  │  │ Notify  │  │ Mark    │
    │ new     │  │ user +  │  │ as      │
    │ subtree │  │ ask OK  │  │ linked  │
    │         │  │         │  │ node    │
    └────┬────┘  └────┬────┘  └────┬────┘
         │            │            │
         └────────┬───┴────┬───────┘
                  │        │
                  ↓        ↓
        ┌──────────────────────────┐
        │ accommodate_layout()      │
        │ ├─ Compute new layout    │
        │ ├─ Procrustes alignment  │
        │ └─ Animate transitions   │
        └──────────────────────────┘
                  │
                  ↓
        ┌──────────────────────────┐
        │ Store in tree + emit      │
        │ Socket.IO event           │
        └──────────────────────────┘


        Maintenance Cycle (Periodic):

        Query History
             ↓
    Calculate Activation Scores
    (relevance + connectivity + recency)
             ↓
        ┌─────┴─────┐
        ↓           ↓
    Pruning     Merging
    (score<0.2) (sim>0.92)
        ↓           ↓
    Mark for    Combine
    deletion    subtrees
        ↓           ↓
    Ask user    Emit event
    for OK      with merge
              proposal
```

---

## 7. Context Fusion Integration (Phase 75.3)

```
                    User Query
                         │
                         ↓
        ┌────────────────────────────────────┐
        │ context_fusion()                   │
        │ (Max 2000 tokens budget)           │
        └────────┬───────────────────────────┘
                 │
    ┌────────────┼────────────┬─────────────┐
    │            │            │             │
    ↓            ↓            ↓             ↓
 Spatial     Pinned        CAM          Code
 Context    Files         Hints        Context
 (300 tok)  (400 tok)     (100 tok)    (1200 tok)
    │            │            │             │
    │            │            │             │
    ├─ Viewport  ├─ Pinned    ├─ Tool       ├─ Editor
    │  position  │  file list │  suggestions│  state
    ├─ Zoom     │  Summary   ├─ JARVIS     ├─ File ops
    ├─ Camera    │  text      │  hint       ├─ Test
    │  target    │  (first    ├─ Activation│  output
    │            │  500 chars │  scores    ├─ Shell
    │            │  per file) │            │  output
    │            │            │            └─ Errors
    │            │            │
    └────────────┴────────────┴────────────┘
                 │
                 ↓
        ┌─────────────────────┐
        │ Unified Context     │
        │ String (~1800 toks) │
        └────────┬────────────┘
                 │
                 ↓
         Sent to LLM/Agent
         for intelligent response


        Decision Logic:
        Include code context IFF:
        • Query contains: "read", "write", "edit", "code",
                         "file", "test", "commit", "function",
                         "class", "import", "bug", "fix",
                         "implement"
          OR
        • Query in Russian: "прочитай", "напиши", "исправь",
                           "код", "файл", "тест"

        Otherwise: Only spatial + pinned + CAM hints
```

---

## 8. Fallback & Error Handling

```
                    HybridSearchService
                         │
          ┌──────────────┴──────────────┐
          │                             │
    Initialize Backends         executeSearch()
    ├─ Get Qdrant              ├─ Cache check
    │  ↓ on error              │  ↓ hit
    │  → Mark unavailable      │  Return cached
    │                          │
    ├─ Get Weaviate           ├─ on miss
    │  ↓ on error             │  Check mode
    │  → Mark unavailable     │
    │                         ├─ "semantic"
    └─ Get Embeddings         │  ├─ Qdrant OK?
       (fallback in            │  │  ✅ search
        each method)           │  │  ❌ error return
       │                       │
       ✅ / ⚠️ / ❌           ├─ "keyword"
                              │  ├─ Weaviate OK?
                              │  │  ✅ search
                              │  │  ❌ error return
                              │
                              ├─ "hybrid"
                              │  ├─ Both OK?
                              │  │  ✅ parallel + RRF
                              │  │  ❌ fallback:
                              │  │     - Qdrant only? → semantic
                              │  │     - Weaviate only? → keyword
                              │  │     - Neither? → error
                              │
                              └─ "filename"
                                 ├─ Qdrant OK?
                                 │  ✅ scroll+filter
                                 │  ❌ error return


                    Error Responses
                    {
                      "results": [],
                      "count": 0,
                      "mode": "error",
                      "error": "Qdrant unavailable; Weaviate also down",
                      "sources": []
                    }
```

---

## 9. Performance Profile

```
                Search Mode Performance
        ┌─────────────────────────────────────┐
        │          Time Distribution (%)       │
        ├─────────────────────────────────────┤
        │                                      │
        │ Semantic (Qdrant only):              │
        │ ████████░░░░░░░░░░░░░░░  50-150ms   │
        │                                      │
        │ Keyword (Weaviate only):             │
        │ ██████████░░░░░░░░░░░░░  80-200ms   │
        │                                      │
        │ Hybrid (RRF):                        │
        │ ████████████░░░░░░░░░░░  150-300ms  │
        │ (parallel + fusion overhead)         │
        │                                      │
        │ Filename (Qdrant payload):           │
        │ ███░░░░░░░░░░░░░░░░░░░░  20-80ms    │
        │                                      │
        │ Cache hit:                           │
        │ ░░░░░░░░░░░░░░░░░░░░░░░  1-2ms     │
        │                                      │
        └─────────────────────────────────────┘

        Typical Query Result Breakdown:
        100 results = ~300ms
        ├─ Qdrant parallel: 150ms
        ├─ Weaviate parallel: 200ms
        ├─ RRF fusion: 20ms
        ├─ Result formatting: 10ms
        ├─ Network I/O: 20ms
        └─ Total overhead: ~300ms


        Cache Impact (40-60% hit rate):
        ├─ 60% hit: avg latency = 300ms * 0.4 + 2ms * 0.6 = 121ms
        ├─ 50% hit: avg latency = 300ms * 0.5 + 2ms * 0.5 = 151ms
        └─ 40% hit: avg latency = 300ms * 0.6 + 2ms * 0.4 = 181ms
```

---

## 10. MCP Tools Integration Flow

```
Claude Code (User in Terminal)
         │
         ├─ /search "authentication flow"
         │       ↓
         │  VetkaSearchTool.execute()
         │       ├─ get_memory_manager()
         │       ├─ SemanticTagger.find_files_by_semantic_tag()
         │       └─ Format results
         │       ↓
         └─ Returns: {success, results[], count}

Claude Code (User in Terminal)
         │
         ├─ /search-knowledge "error handling"
         │  [with file_types filter]
         │       ↓
         │  SearchKnowledgeTool.execute()
         │       ├─ get_memory_manager()
         │       ├─ SemanticTagger (filtered)
         │       └─ Format results
         │       ↓
         └─ Returns: {success, results[], count}

Claude Code (User in Terminal)
         │
         ├─ /list-files "src" [pattern: "*.py"]
         │       ↓
         │  ListFilesTool.execute()
         │       ├─ Directory traversal (max depth: 5)
         │       ├─ Glob pattern matching
         │       └─ Format file list
         │       ↓
         └─ Returns: {success, items[], count}
```

---

*Diagrams compiled from Phase 95 HAIKU-RECON-3 audit | 2026-01-26*
