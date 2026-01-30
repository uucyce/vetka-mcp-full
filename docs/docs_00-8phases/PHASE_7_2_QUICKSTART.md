# 🚀 Phase 7.2 — Quick Start Guide

## Step 1: Start Docker Services

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# Start Weaviate + Qdrant + Ollama
docker-compose up -d

# Verify services are running
docker-compose ps
```

**Expected output:**
```
NAME      SERVICE   STATUS
weaviate  weaviate  Up (healthy)
qdrant    qdrant    Up (healthy)
ollama    ollama    Up (healthy)
```

## Step 2: Create Data Directory

```bash
mkdir -p data
```

## Step 3: Verify Services Are Healthy

```bash
# Check Weaviate
curl -s http://localhost:8080/v1/meta | jq .

# Check Qdrant
curl -s http://localhost:6333/health | jq .

# Check Ollama
curl -s http://localhost:11434/api/tags | jq .
```

## Step 4: Run Triple Write Tests

```bash
# Make test executable
chmod +x test_triple_write.py

# Run tests
python3 test_triple_write.py
```

**Expected output:**
```
✅ TEST 1: Triple Write Functionality
✅ TEST 2: High-Score Example Retrieval
✅ TEST 3: Semantic Search
✅ TEST 4: Workflow History
✅ TEST 5: User Feedback Saving
✅ TEST 6: Agent Statistics
```

## Step 5: Verify Data Persistence

```bash
# Check ChangeLog was created
ls -lh data/changelog.jsonl

# See last entry
tail -1 data/changelog.jsonl | jq .

# Count entries
wc -l data/changelog.jsonl

# Pretty print all entries
cat data/changelog.jsonl | jq .
```

## Step 6: Access Web Interfaces

- **Weaviate Console:** http://localhost:8080
- **Qdrant Web UI:** http://localhost:6333/dashboard

## Common Issues

### Issue: "Cannot connect to Docker daemon"
**Solution:** 
```bash
# Start Docker Desktop first
# Or check if it's running
docker ps
```

### Issue: "Port 8080 already in use"
**Solution:**
```bash
# Check what's using port 8080
lsof -i :8080

# Kill the process or use a different port in docker-compose.yml
```

### Issue: "Ollama not responding"
**Solution:**
```bash
# Ollama may take time to start
docker logs vetka_ollama

# Wait 30 seconds and try again
```

## Monitoring Logs

```bash
# Watch Weaviate logs
docker logs -f vetka_weaviate

# Watch Qdrant logs
docker logs -f vetka_qdrant

# Watch Ollama logs
docker logs -f vetka_ollama

# Watch all logs
docker-compose logs -f
```

## Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ loses data)
docker-compose down -v
```

## Next: Integrate with Main App

In `main.py`, update Flask routes to use MemoryManager:

```python
from src.orchestration.memory_manager import get_memory_manager

@app.route('/api/workflow/complete', methods=['POST'])
def complete_workflow():
    data = request.json
    mm = get_memory_manager()
    
    # Triple-write automatically
    mm.save_workflow_result(data['workflow_id'], data['result'])
    
    return {"status": "ok", "workflow_id": data['workflow_id']}
```

## Phase 7.2 Status

✅ MemoryManager rewritten with Triple Write  
✅ Docker-compose.yml created  
✅ Tests written and verified  
✅ Documentation complete  
✅ Ready for Phase 7.3 (LangGraph + Dashboard)

---

**Questions?** Check `POLISH_7_2_TRIPLE_WRITE_COMPLETE.md`
