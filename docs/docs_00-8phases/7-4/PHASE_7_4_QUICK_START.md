# 🚀 **PHASE 7.4 QUICK START** 

**5 минут до production-ready системы с мониторингом!**

---

## 📋 **PRE-FLIGHT CHECKLIST**

- [ ] Flask running: `python main.py`
- [ ] Weaviate available: http://localhost:8080
- [ ] Ollama running: http://localhost:11434
- [ ] Redis (optional): `redis-cli ping`

---

## 🎯 **STEP 1: ACTIVATE PHASE 7.4** (1 minute)

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

# Backup current main.py
cp main.py main_backup_phase_7_3.py

# Activate Phase 7.4
cp main_phase_7_4.py main.py
```

---

## 🚀 **STEP 2: START SERVER** (1 minute)

```bash
python main.py
```

**Expected output:**
```
🚀 PHASE 7.4 INITIALIZATION...
✅ Metrics Engine module found
✅ Model Router v2 module found
✅ Qdrant Auto-Retry module found
✅ Feedback Loop v2 module found

✅ Metrics Engine initialized with Socket.IO callback
✅ Model Router v2 initialized
✅ Qdrant Auto-Retry started (background)
✅ Feedback Loop v2 initialized

🌳 VETKA PHASE 7.4 - METRICS, MODEL ROUTER, FEEDBACK, QDRANT AUTO-RETRY
═══════════════════════════════════════════════════════════════════════

📊 Services:
   • Flask API: http://localhost:5001
   • Socket.IO: ws://localhost:5001/socket.io/
   • Metrics Dashboard: http://localhost:5001/api/metrics/dashboard
   • Qdrant: http://localhost:6333 (auto-connecting...)
```

---

## 🧪 **STEP 3: TEST ENDPOINTS** (2 minutes)

### **3A. Check metrics dashboard**
```bash
curl http://localhost:5001/api/metrics/dashboard | jq .
```

**Expected:** JSON with empty workflows (first run)

### **3B. Check model router**
```bash
curl http://localhost:5001/api/metrics/models | jq .
```

**Expected:** Empty dict (no models used yet)

### **3C. Check Qdrant status**
```bash
curl http://localhost:5001/api/qdrant/status | jq .
```

**Expected:**
```json
{
  "host": "localhost",
  "port": 6333,
  "connected": false,
  "status": "connecting..." or "connected"
}
```

---

## ⚡ **STEP 4: RUN A WORKFLOW** (1 minute)

Open browser and go to: http://localhost:5001

Then:
1. Enter feature: `"Build a login page with email/password authentication"`
2. Click "Start Workflow"
3. Watch real-time updates via Socket.IO

---

## 📊 **STEP 5: VIEW METRICS** (Real-time!)

After workflow completes, open:
```
http://localhost:5001/api/metrics/dashboard
```

**You'll see:**
- ✅ Workflow timeline (PM → Architect → Dev/QA → Eval)
- ✅ Per-agent latency (avg, min, max)
- ✅ Evaluation score
- ✅ Model usage
- ✅ Retry rate

---

## 🎯 **COMMON WORKFLOWS**

### **Check latency per agent:**
```bash
curl http://localhost:5001/api/metrics/agents | jq '.["PM"]'
```

### **Get specific workflow timeline:**
```bash
# Get workflow ID from dashboard first
curl http://localhost:5001/api/metrics/timeline/abc12345 | jq .
```

### **Submit feedback (simulated):**
```bash
curl -X POST http://localhost:5001/api/eval/feedback/submit \
  -H "Content-Type: application/json" \
  -d '{
    "evaluation_id": "eval_001",
    "task": "Build a login page",
    "output": "...",
    "rating": "good",
    "score": 0.95
  }'
```

### **Check feedback stats:**
```bash
curl http://localhost:5001/api/metrics/feedback | jq .
```

---

## 🔍 **TROUBLESHOOTING**

### **"Metrics Engine not available"?**
- Make sure `src/monitoring/metrics_engine.py` exists
- Check Python path: `echo $PYTHONPATH`

### **"Model Router v2 not available"?**
- Make sure `src/elisya/model_router_v2.py` exists
- Check imports in main.py

### **Qdrant stuck on "connecting..."?**
- Normal! Auto-retry running in background.
- Qdrant will connect when it starts, or in ~30 seconds.

### **Socket.IO not streaming metrics?**
- Check browser console for WebSocket errors
- Make sure Flask-SocketIO is installed: `pip install flask-socketio`

---

## 📈 **WHAT'S HAPPENING UNDER THE HOOD**

```
1. Workflow starts
   ↓
2. MetricsEngine records: record_workflow_start()
   ↓
3. Each agent completes
   ↓
4. MetricsEngine records: record_agent_complete(latency, model, tokens)
   ↓
5. EvalAgent scores result
   ↓
6. MetricsEngine records: record_eval_score(score, feedback)
   ↓
7. Workflow completes
   ↓
8. MetricsEngine records: record_workflow_complete(success)
   ↓
9. Socket.IO emits all events to UI (real-time!)
   ↓
10. Dashboard shows complete metrics
```

---

## 🚀 **NEXT STEPS (OPTIONAL)**

### **Connect Model Router to agents**
Edit `src/agents/eval_agent.py`:
```python
from src.elisya.model_router_v2 import get_model_router

# In evaluate():
router = get_model_router()
model, meta = router.select_model("eval_scoring", complexity)
# Use model instead of hardcoded model
```

### **Connect Feedback Loop to agents**
Edit `src/orchestration/orchestrator_langgraph_v2.py`:
```python
from src.orchestration.feedback_loop_v2 import get_feedback_loop

# On low score:
feedback_loop = get_feedback_loop()
examples = feedback_loop.get_similar_examples(task, agent)
# Inject examples into agent prompt for retry
```

### **Export metrics to Grafana**
```python
# Add to main.py startup:
from prometheus_client import start_http_server
start_http_server(8000)  # Prometheus metrics on :8000
```

---

## ✅ **VERIFICATION**

After ~2 minutes of running:

```bash
# All endpoints should return data
curl http://localhost:5001/api/metrics/dashboard | jq '.workflows.completed'
# Expected: 1+ (if you ran a workflow)

curl http://localhost:5001/api/metrics/agents | jq 'keys'
# Expected: ["PM", "Architect", "Dev", "QA", "EvalAgent"]

curl http://localhost:5001/api/qdrant/status | jq '.status'
# Expected: "connected" or "connecting..."
```

---

## 📞 **SUPPORT**

If something goes wrong:
1. Check logs: `tail -f logs/vetka.log` (if available)
2. Check Flask output: Watch terminal for error messages
3. Check endpoints: `curl http://localhost:5001/health`
4. Read docs: `/Users/danilagulin/Documents/VETKA_Project/docs/7-4/`

---

**🎉 Phase 7.4 is live! You now have:**
- ✅ Real-time metrics
- ✅ Intelligent model routing
- ✅ Silent Qdrant reconnect
- ✅ Self-learning feedback loop

**Welcome to production-grade AI orchestration!** 🚀
