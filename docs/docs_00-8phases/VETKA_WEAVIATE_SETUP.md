# 🌳 VETKA v3.0 - Weaviate Setup

**Status:** ✅ Phase 1 Complete - October 24, 2025

## 🚀 Quick Start (3 шага)

### 1️⃣ Убедись что Weaviate запущен

```bash
curl http://localhost:8080/.well-known/ready
# Expected: HTTP 204
```

Если не запущен, запусти:
```bash
docker run -d -p 8080:8080 -p 50051:50051 cr.weaviate.io/weaviate:latest
```

### 2️⃣ Создай коллекции

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python3 src/memory/vetka_create_collections.py
```

### 3️⃣ Проверь что всё работает

```bash
python3 src/memory/vetka_validate_endpoints.py
```

## 🐍 Использование в коде

```python
from src.memory.vetka_weaviate_helper import WeaviateHelper

helper = WeaviateHelper()

# Hybrid search (Primary)
results = helper.hybrid_search(
    collection='VetkaLeaf',
    query='JWT authentication',
    alpha=0.7,  # 70% vector + 30% BM25
    limit=5
)

# Insert object
obj_id = helper.insert_object(
    collection='VetkaLeaf',
    data_object={
        'file_path': '/src/auth.py',
        'content': 'def validate(): ...',
        'status': 'ready'
    }
)

# Save checkpoint
helper.save_checkpoint('workflow-001', 1, {'task': '...'}, 'node_name')

# Log change
helper.log_change('VETKA-Dev', 'create', '/src/auth.py', {}, {...})
```

## 📦 6 Weaviate Collections

1. **VetkaGlobal** - Project overview
2. **VetkaTree** - Branch structure
3. **VetkaLeaf** - Files/tasks (searchable)
4. **VetkaAgentsMemory** - Agent logs
5. **VetkaSharedMemory** - LangGraph checkpoints
6. **VetkaChangeLog** - Audit trail

## 🔍 Search Types

- **Hybrid** (default) - 70% vector + 30% BM25
- **Vector** - Pure semantic similarity
- **Filter** - WHERE clauses

## 📍 Endpoints

Base URL: `http://localhost:8080`

- Health: `/.well-known/ready`
- Collections: `/v1/collections`
- Objects: `/v1/objects`
- GraphQL: `/graphql`

## ✅ API Methods

```python
helper.health_check()                              # Verify connection
helper.list_collections()                          # See all collections
helper.insert_object(collection, data, vector)    # Create
helper.batch_insert(collection, objects, vectors) # Batch create (max 100)
helper.get_object(collection, uuid)               # Read
helper.update_object(collection, uuid, data)      # Update
helper.delete_object(collection, uuid)            # Delete
helper.hybrid_search(collection, query, alpha)    # Search
helper.save_checkpoint(workflow_id, step, state)  # Save state
helper.log_change(initiator, action, path, b, a) # Audit
```

## 🎯 Next: Phase 2

- LangGraph agent integration
- Flask UI with real-time updates
- 3D tree visualization
- Workflow orchestration

---

**VETKA v3.0 - Ready for Production** 🚀
