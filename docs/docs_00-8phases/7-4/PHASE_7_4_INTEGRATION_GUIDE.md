# 🔗 **PHASE 7.4 INTEGRATION GUIDE**

**For:** Integrating new Phase 7.4 modules into existing Phase 7.3 backend

---

## 🎯 **WHAT'S BEING INTEGRATED**

```
MetricsEngine (480 lines)      → Real-time workflow metrics
    ↓
ModelRouterV2 (420 lines)      → Intelligent task routing
    ↓
QdrantAutoRetry (280 lines)    → Background Qdrant connection
    ↓
Existing Backend (Phase 7.3)   → Orchestrator + Agents
    ↓
Socket.IO                       → Stream metrics to UI
```

---

## 📝 **STEP-BY-STEP INTEGRATION**

### **STEP 1: Initialize MetricsEngine in main.py**

**Location:** `main.py` at top (after Flask initialization)

```python
# ============ ADD AFTER IMPORTS ============
from src.monitoring.metrics_engine import init_metrics_engine, get_metrics_engine

# ============ ADD AFTER SocketIO INITIALIZATION ============
# Initialize metrics engine
metrics_engine = init_metrics_engine(max_history=500, window_size=100)

# Register callback for real-time Socket.IO updates
def emit_metrics_to_ui(event_type: str, data: dict):
    """Emit metric updates to connected clients via Socket.IO"""
    try:
        socketio.emit(event_type, data, broadcast=True)
    except Exception as e:
        print(f"⚠️  Metrics emission error: {e}")

metrics_engine.register_callback(emit_metrics_to_ui)

print("✅ Metrics Engine initialized with Socket.IO callback")
```

---

### **STEP 2: Initialize ModelRouter in main.py**

**Location:** Same section as metrics (after imports)

```python
# ============ ADD AFTER METRICS ENGINE ============
from src.elisya.model_router_v2 import init_model_router

# Initialize model router (with Redis if available)
try:
    model_router = init_model_router(redis_host='localhost', redis_port=6379)
    print("✅ Model Router v2 initialized (with Redis cache)")
except Exception as e:
    print(f"⚠️  Model Router Redis failed: {e}")
    model_router = init_model_router()  # Fallback to in-memory
```

---

### **STEP 3: Initialize QdrantAutoRetry in main.py**

**Location:** Same section (after model router)

```python
# ============ ADD AFTER MODEL ROUTER ============
from src.memory.qdrant_auto_retry import init_qdrant_auto_retry

def on_qdrant_connected():
    """Callback when Qdrant successfully connects"""
    print("🎉 Qdrant is now connected! VetkaTree available.")
    socketio.emit('qdrant_connected', {
        'status': 'connected',
        'timestamp': time.time()
    }, broadcast=True)

# Start background Qdrant connection (non-blocking)
qdrant_manager = init_qdrant_auto_retry(
    host='localhost',
    port=6333,
    max_retries=5,
    on_connected=on_qdrant_connected
)
print("⏳ Qdrant auto-retry started (background)")
```

---

### **STEP 4: Add Metrics Hooks to Orchestrator**

**File:** `src/orchestration/orchestrator_langgraph_v2.py`

**Location:** In `run_parallel_workflow()` function

```python
# ============ AT FUNCTION START ============
from src.monitoring.metrics_engine import get_metrics_engine

async def run_parallel_workflow(...):
    metrics = get_metrics_engine()
    
    # Record workflow start
    metrics.record_workflow_start(workflow_id, feature_request)
    
    # ... existing code ...
    
    # ============ IN NODE EXECUTION LOOPS ============
    # For each agent node:
    
    start_time = time.time()
    
    # Execute node
    result = await pm_node(...)  # or dev_node, qa_node, etc.
    
    duration = time.time() - start_time
    
    # Record metrics
    metrics.record_agent_complete(
        workflow_id=workflow_id,
        agent_name='PM',  # or 'Dev', 'QA', 'Architect'
        duration=duration,
        status='success' if result.get('error') is None else 'error',
        model=result.get('model', 'unknown'),
        tokens=result.get('tokens_used', 0),
        cost=result.get('cost', 0.0)
    )
    
    # ============ AFTER EVALUATION ============
    # After EvalAgent scores:
    
    metrics.record_eval_score(
        workflow_id=workflow_id,
        score=eval_result.get('score', 0.0),
        feedback_type=eval_result.get('feedback', None)
    )
    
    # ============ AT WORKFLOW COMPLETION ============
    metrics.record_workflow_complete(
        workflow_id=workflow_id,
        success=result.get('success', False)
    )
```

---

### **STEP 5: Add ModelRouter Hooks to Agents**

**File:** `src/agents/vetka_pm.py` (and dev_agent, qa_agent, architect_agent)

**Location:** In agent initialization / model selection

```python
# ============ AT TOP OF AGENT CLASS ============
from src.elisya.model_router_v2 import get_model_router

class VetkaPM:
    def __init__(self, ...):
        # ... existing init ...
        self.model_router = get_model_router()
    
    # ============ IN EXECUTION METHOD ============
    def execute(self, prompt: str, complexity: str = "MEDIUM"):
        # Route to optimal model
        if self.model_router:
            model, routing_meta = self.model_router.select_model(
                task_type='pm_planning',
                complexity=complexity
            )
            print(f"📦 PM routed to model: {model}")
        else:
            model = self.default_model
            routing_meta = {}
        
        # Execute with selected model
        try:
            start_time = time.time()
            result = self.llm.invoke(prompt, model=model)
            duration = time.time() - start_time
            
            # Record success
            if self.model_router:
                self.model_router.mark_model_success(
                    model=model,
                    duration=duration,
                    tokens=len(result) // 4,  # Rough estimate
                    cost=self._estimate_cost(model, len(result))
                )
            
            return result
        
        except Exception as e:
            # Record error
            if self.model_router:
                self.model_router.mark_model_error(model, str(e))
            raise
```

---

### **STEP 6: Add Metrics API Endpoints in main.py**

**Location:** After existing endpoints (before `if __name__ == "__main__"`)

```python
# ============ METRICS ENDPOINTS ============

@app.route("/api/metrics/dashboard", methods=["GET"])
def metrics_dashboard():
    """Get complete metrics dashboard data"""
    try:
        metrics = get_metrics_engine()
        return jsonify(metrics.get_dashboard_data()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/metrics/timeline/<workflow_id>", methods=["GET"])
def metrics_timeline(workflow_id):
    """Get timeline for specific workflow"""
    try:
        metrics = get_metrics_engine()
        return jsonify(metrics.get_timeline_data(workflow_id)), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/metrics/agents", methods=["GET"])
def metrics_agents():
    """Get per-agent statistics"""
    try:
        metrics = get_metrics_engine()
        return jsonify(metrics.get_agent_stats()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/metrics/models", methods=["GET"])
def metrics_models():
    """Get model router statistics"""
    try:
        router = get_model_router()
        if router:
            return jsonify(router.get_model_stats()), 200
        return jsonify({'error': 'Model router not initialized'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/metrics/providers", methods=["GET"])
def metrics_providers():
    """Get provider health status"""
    try:
        router = get_model_router()
        if router:
            return jsonify(router.get_provider_health()), 200
        return jsonify({'error': 'Model router not initialized'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/metrics/export", methods=["GET"])
def metrics_export():
    """Export metrics in specified format"""
    try:
        metrics = get_metrics_engine()
        format = request.args.get('format', 'json')
        export_data = metrics.export_metrics(format)
        
        if format == 'csv':
            return export_data, 200, {'Content-Type': 'text/csv'}
        else:
            return export_data, 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/api/qdrant/status", methods=["GET"])
def qdrant_status():
    """Get Qdrant connection status"""
    try:
        from src.memory.qdrant_auto_retry import get_qdrant_auto_retry
        mgr = get_qdrant_auto_retry()
        if mgr:
            return jsonify(mgr.get_status()), 200
        return jsonify({'status': 'not initialized'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

### **STEP 7: Update Startup Messages in main.py**

**Location:** In `if __name__ == "__main__"` section

```python
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🌳 VETKA PHASE 7.4 - DASHBOARD & METRICS LAYER")
    print("="*70)
    print("\n📊 Services:")
    print("   • Flask API: http://localhost:5001")
    print("   • Socket.IO: ws://localhost:5001/socket.io/")
    print("   • Weaviate: http://localhost:8080")
    print("   • Ollama: http://localhost:11434")
    print("   • Qdrant: http://localhost:6333 (auto-connecting...)")
    print("\n📈 Workflow Endpoints:")
    print("   • POST /api/workflow/start - Start standard workflow")
    print("   • POST /api/workflow/autogen - Start Autogen workflow")
    print("   • GET /api/workflow/history - Workflow history")
    print("   • GET /api/workflow/stats - Workflow statistics")
    
    print("\n📊 **NEW: Metrics Endpoints (Phase 7.4):**")
    print("   • GET /api/metrics/dashboard - Complete dashboard data")
    print("   • GET /api/metrics/timeline/<workflow_id> - Workflow timeline")
    print("   • GET /api/metrics/agents - Per-agent statistics")
    print("   • GET /api/metrics/models - Model router stats")
    print("   • GET /api/metrics/providers - Provider health")
    print("   • GET /api/metrics/export?format=json|csv - Export metrics")
    print("   • GET /api/qdrant/status - Qdrant connection status")
    
    print("\n🚀 Production-Ready Features:")
    print("   ✅ Real-time metrics streaming (Socket.IO)")
    print("   ✅ Intelligent model routing")
    print("   ✅ Provider health tracking")
    print("   ✅ Qdrant silent auto-reconnect (background)")
    print("   ✅ Cost optimization & usage analytics")
    print("   ✅ Per-agent & per-workflow timing")
    print("   ✅ Feedback tracking & analysis")
    print("\n🚀 Starting Flask server...")
    print("="*70 + "\n")
    
    # ... rest of startup code ...
```

---

## ✅ **VERIFICATION CHECKLIST**

After integration, verify each module:

```bash
# 1. Check MetricsEngine loads
curl http://localhost:5001/api/metrics/dashboard

# Expected: JSON with structure:
# {
#   "timestamp": ...,
#   "workflows": {...},
#   "latency": {...},
#   "scores": {...},
#   "feedback": {...},
#   "models": {...},
#   "agents": {...},
#   "retries": {...},
#   "recent_workflows": [...]
# }

# 2. Check ModelRouter loads
curl http://localhost:5001/api/metrics/models

# Expected: JSON with model stats (empty initially)

# 3. Check Qdrant status
curl http://localhost:5001/api/qdrant/status

# Expected: 
# {
#   "host": "localhost",
#   "port": 6333,
#   "connected": false or true,
#   "status": "connecting..." or "connected",
#   ...
# }

# 4. Start a workflow and check metrics update
# (open browser, start workflow via UI)
# Check Socket.IO events in browser console

# 5. Get complete metrics after workflow
curl http://localhost:5001/api/metrics/dashboard | jq .workflows.completed
```

---

## 🔧 **TROUBLESHOOTING**

| Issue | Solution |
|-------|----------|
| `ImportError: No module named 'src.monitoring'` | Restart Python, ensure `__init__.py` exists in dirs |
| `Redis connection failed` | ModelRouter falls back to in-memory (OK) |
| `Qdrant connection spam` | Normal! Auto-retry running silently in background |
| `Metrics not updating` | Check Socket.IO callback registered in step 1 |
| `Model router always returns "unknown"` | Ensure agents call `mark_model_success/error` |

---

## 📈 **NEXT: UI DASHBOARD**

Once integration is complete:

1. Create `frontend/components/VetkaMetricsDashboard.jsx`
2. Add real-time Socket.IO listeners for metrics events
3. Display timeline, charts, and statistics
4. Integrate Chart.js for visualizations

---

**Integration complete! Ready for Phase 7.4 Dashboard UI 🚀**
