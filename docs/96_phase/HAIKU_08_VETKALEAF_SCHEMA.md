# HAIKU RECON 08: VetkaLeaf Weaviate Schema

**Agent:** Haiku
**Date:** 2026-01-28
**Task:** Analyze VetkaLeaf collection schema and BM25 search

---

## SCHEMA DEFINITION LOCATIONS

| Location | Purpose | API Version |
|----------|---------|-------------|
| `src/orchestration/triple_write_manager.py:155-198` | Main schema definition | v3 REST |
| `scripts/sync_qdrant_to_weaviate.py:129-162` | Sync script schema | v4 SDK |
| `config/config.py:20` | Collection mapping | Config |

---

## VETKALEAF SCHEMA

**Class Name:** `VetkaLeaf`
**Vectorizer:** `none` (uses custom vectors)

### Properties

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | text | Full relative path to file |
| `file_name` | text | Just the filename |
| `content` | text | File content (truncated to 5000 chars) |
| `file_type` | text | File extension (without dot) |
| `depth` | int | Directory depth |
| `size` | int | File size in bytes |
| `created_at` | date | Indexing timestamp |
| `modified_at` | date | File modification time |

### Additional Fields (from BM25 search)
- `path` - alternative name for `file_path`
- `creator` - author (legacy schema)
- `node_type` - node type (legacy schema)

---

## BM25 SEARCH IMPLEMENTATION

**File:** `src/memory/weaviate_helper.py:191-239`

```python
def bm25_search(self, collection: str, query: str, limit: int = 5) -> List[Dict]:
    """Pure BM25 text search"""
    col_name = COLLECTIONS.get(collection, collection)  # 'leaf' → 'VetkaLeaf'

    graphql_query = f"""
    {{
      Get{{
        {col_name}(
          bm25: {{
            query: \"{query}\"
          }}
          limit: {limit}
        ) {{
          _additional {{
            score
            id
          }}
          content
          file_path
          file_name
        }}
      }}
    }}
    """
```

### Search Flow
1. GraphQL query with BM25 parameters
2. Request sent to `{WEAVIATE_URL}/graphql`
3. Results normalized: `file_path` → `path`, `file_name` → `name`
4. Return list with scores

---

## HYBRID SEARCH (BM25 + Vector)

**File:** `src/memory/weaviate_helper.py:103-148`

```python
def hybrid_search(collection, query, vector, limit, alpha=0.5):
    # alpha controls weight between BM25 and vector
    # alpha=0 → pure BM25
    # alpha=1 → pure vector
```

---

## COLLECTION INITIALIZATION

**File:** `src/orchestration/triple_write_manager.py`
**Method:** `_init_weaviate()` → `_ensure_vetka_leaf_schema()`

### Initialization Flow
```
TripleWriteManager()
    ↓
_init_weaviate()
    ↓
Check Weaviate connection
    ↓
_ensure_vetka_leaf_schema()
    ↓
If VetkaLeaf doesn't exist → create with schema
If exists but wrong schema → delete and recreate
```

---

## OTHER WEAVIATE COLLECTIONS

| Collection | Purpose | Initialization |
|------------|---------|----------------|
| **VetkaLeaf** | File-oriented data | TripleWriteManager |
| VetkaTree | Tree-level knowledge | create_collections.py |
| VetkaGlobal | Global knowledge base | create_collections.py |
| VetkaSharedMemory | Shared across agents | create_collections.py |
| VetkaAgentsMemory | Individual agent knowledge | create_collections.py |
| VetkaChangeLog | System change history | create_collections.py |

---

## FIELD MAPPING (FIX_95.10)

**File:** `src/memory/weaviate_helper.py:225-232`

```python
# Map VetkaLeaf fields for compatibility
normalized = {
    'path': result.get('file_path'),
    'name': result.get('file_name'),
    'content': result.get('content'),
    ...
}
```

---

## SYNC SCRIPT

**File:** `scripts/sync_qdrant_to_weaviate.py`

### What It Does
- Syncs data from Qdrant `vetka_elisya` to Weaviate `VetkaLeaf`
- Supports batch operations (50 objects per batch)
- Truncates content to 5000 chars for Weaviate
- Converts timestamps to RFC3339 format

### Usage
```bash
python scripts/sync_qdrant_to_weaviate.py
```

---

## WEAVIATE API VERSIONS IN USE

| Component | API Version | Notes |
|-----------|-------------|-------|
| TripleWriteManager | v3 REST | Main write path |
| WeaviateHelper | v1 REST | Legacy/search |
| sync_qdrant_to_weaviate.py | v4 SDK | Standalone sync |

**Recommendation:** Consolidate to v4 SDK

---

## RELATED MARKERS

| Marker | File | Description |
|--------|------|-------------|
| FIX_95.7 | hybrid_search.py:127 | Changed default 'tree'→'leaf' |
| FIX_95.10 | weaviate_helper.py:225 | VetkaLeaf field mapping |
| MARKER_ARCH_001 | weaviate_helper.py:8 | Duplicate Weaviate implementations |

---

## KEY INSIGHTS

1. **VetkaLeaf is the main collection** for file data in VETKA
2. **Auto-initialized** when TripleWriteManager is created
3. **BM25 search** via GraphQL API
4. **Integrates with hybrid search** (Qdrant + Weaviate RRF fusion)
5. **Three different Weaviate implementations** need consolidation
