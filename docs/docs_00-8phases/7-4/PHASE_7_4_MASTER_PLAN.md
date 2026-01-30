# 🚀 **PHASE 7.4 — DASHBOARD & METRICS (PRODUCTION UI LAYER)**

**Date:** 2025-10-28  
**Status:** 🎯 **PLANNING PHASE**  
**Focus:** Backend is production-ready, NOW: UI/Dashboard + Model Router + Feedback Loop v2

---

## 📊 **EXECUTIVE SUMMARY**

PHASE 7.3 v2 achieved:
- ✅ **Parallelism confirmed** (DEV & QA in 12.7s parallel)
- ✅ **Memory stability** (Triple Write: Weaviate + Qdrant + ChangeLog)
- ✅ **Context management** (Flask `app.app_context()` fixes resolved RuntimeError)
- ✅ **Graceful shutdown** (ThreadPoolExecutor cleanup via atexit)

**PHASE 7.4 Goal:** Add **production-grade UI layer** + **intelligent model routing** + **self-learning feedback loop**

---

## 🧩 **ARCHITECTURE OVERVIEW**

```
┌─────────────────────────────────────────────────────────┐
│          PHASE 7.4 UI LAYER (React/Dashboard)          │
│  ┌──────────────┬──────────────┬──────────────────────┐ │
│  │ Workflow     │ Metrics Real │ Model Router         │ │
│  │ Timeline     │ Time Stream  │ Status               │ │
│  └──────────────┴──────────────┴──────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          ↑ Socket.IO
          (workflow_log, metrics_update, model_status)
                          ↓
┌─────────────────────────────────────────────────────────┐
│      PHASE 7.3 v2 Backend (Fully Parallel)             │
│  ┌──────────────┬──────────────┬──────────────────────┐ │
│  │ LangGraph    │ EvalAgent    │ MemoryManager        │ │
│  │ Parallelism  │ Auto-scoring │ (Weaviate+Qdrant)    │ │
│  └──────────────┴──────────────┴──────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 **PHASE 7.4 DELIVERABLES**

### **1️⃣ DASHBOARD UI MODULE** (React/Next.js)

**File:** `frontend/components/VetkaMetricsDashboard.jsx` (350-400 lines)

```jsx
// Dashboard shows:
✅ Timeline view (PM → Architect → Dev/QA parallel → Eval)
✅ Real-time latency counter (per agent, total)
✅ Score distribution (0.0-1.0 from EvalAgent)
✅ Model usage chart (Ollama vs OpenRouter vs Gemini)
✅ Memory usage (Weaviate, Qdrant, ChangeLog)
✅ Retry analytics (success rate, avg retry count)
✅ Feedback submissions (Good/Poor/Retry breakdown)
```

**Socket.IO Events to consume:**
- `workflow_log` → log lines with timestamps
- `metrics_update` → latency, scores, model usage
- `model_status` → router health, fallback usage
- `memory_status` → DB connection, entry count

### **2️⃣ METRICS ENGINE** (Python Backend)

**File:** `src/monitoring/metrics_engine.py` (300-400 lines)

```python
class MetricsEngine:
    """Real-time metrics collection & aggregation"""
    
    def __init__(self):
        self.workflows = {}  # workflow_id → metrics
        self.agents = {}     # agent_name → perf stats
        self.models = {}     # model_name → usage count
        self.retries = []    # retry history
        self.feedback = []   # user feedback
    
    def record_workflow_start(self, workflow_id):
        # Emit workflow_started event
        pass
    
    def record_agent_completion(self, agent_name, duration, status):
        # Emit agent_complete event with latency
        pass
    
    def record_eval_score(self, score, feedback_type):
        # Track score distribution
        pass
    
    def get_dashboard_data(self):
        # Return aggregated metrics for UI
        return {
            'timeline': [...],
            'latencies': {...},
            'scores': {...},
            'model_usage': {...},
            'retry_rate': 0.15,
            'feedback_breakdown': {...}
        }
```

### **3️⃣ MODEL ROUTER v2** (Enhanced)

**File:** `src/elisya/model_router_v2.py` (250-350 lines)

**Features:**
- ✅ Route by **task complexity** (LOW/MEDIUM/HIGH)
- ✅ Route by **model capability** (coding vs planning vs eval)
- ✅ Route by **cost** (Ollama free → OpenRouter paid → Gemini fallback)
- ✅ **Fallback chain:** preferred → secondary → tertiary
- ✅ **Latency tracking** (which models are fast/slow)
- ✅ **Error recovery** (mark provider down, auto-rotate)

```python
class ModelRouterV2:
    ROUTES = {
        'pm_planning': {
            'optimal': 'gpt-4-turbo',  # complexity analysis
            'fallback': ['claude-opus', 'gemini-pro'],
            'cost_limit': 0.15,
        },
        'architecture': {
            'optimal': 'claude-opus',  # reasoning
            'fallback': ['gpt-4', 'gemini-pro'],
            'cost_limit': 0.12,
        },
        'dev_coding': {
            'optimal': 'deepseek-coder:6.7b',  # Ollama, free
            'fallback': ['gpt-4', 'gemini-pro-vision'],
            'cost_limit': 0.10,
        },
        'qa_testing': {
            'optimal': 'ollama:llama2:13b',  # fast, local
            'fallback': ['claude-sonnet', 'gemini-pro'],
            'cost_limit': 0.05,
        },
        'eval_scoring': {
            'optimal': 'deepseek-coder:6.7b',  # must be deterministic
            'fallback': ['claude-sonnet', 'gemini-pro'],
            'cost_limit': 0.03,
        }
    }
    
    def select_model(self, task_type: str, complexity: str) -> str:
        """Route task to best model based on type + complexity"""
        # 1. Get route config
        # 2. Check provider health (RedisCache)
        # 3. If down, use fallback
        # 4. Return selected model + cost estimate
        pass
    
    def record_usage(self, model: str, duration: float, success: bool):
        """Track model performance for analytics"""
        pass
```

### **4️⃣ FEEDBACK LOOP v2** (Self-Learning)

**File:** `src/orchestration/feedback_loop_v2.py` (250-300 lines)

**Flow:**
```
User submits rating (Good/Poor/Retry)
    ↓
EvalAgent score < 0.7 → Auto-feedback "Needs improvement"
    ↓
Memory stores (task + output + rating + score)
    ↓
On next similar task:
  • Retrieve from Weaviate (semantic search)
  • Pass as "Few-shot examples" to agents
  • Track if performance improved
```

```python
class FeedbackLoopV2:
    def __init__(self, memory_manager, weaviate_client):
        self.memory = memory_manager
        self.weaviate = weaviate_client
    
    def submit_feedback(self, eval_id, task, output, rating, correction=None):
        """Store feedback for learning"""
        # Save to Weaviate with tags:
        # - rating: "good" | "poor" | "retry"
        # - complexity: LOW|MEDIUM|HIGH
        # - agent: PM|Architect|Dev|QA
        # - improvement_area: if correction provided
        pass
    
    def get_similar_examples(self, task: str, agent: str, limit=3):
        """Retrieve similar high-scoring examples as context"""
        # Vector search in Weaviate
        # Filter by: agent + complexity
        # Return top 3 with score > 0.8
        pass
    
    def track_improvement(self, before_score, after_score):
        """Measure if feedback improved performance"""
        # Calculate delta
        # Log to Prometheus/Grafana
        pass
```

### **5️⃣ QDRANT AUTO-CONNECT & RETRY** (Infrastructure)

**File:** `src/memory/qdrant_auto_retry.py` (150-200 lines)

**Current Issue:** Qdrant logs warnings if not running  
**Solution:** Background retry with exponential backoff

```python
class QdrantAutoRetry:
    def __init__(self, host='localhost', port=6333, max_retries=5):
        self.host = host
        self.port = port
        self.max_retries = max_retries
        self.retry_count = 0
        self.is_connected = False
        
        # Background thread: try to connect every 30s
        self.start_background_retry()
    
    def start_background_retry(self):
        """Attempt Qdrant connection in background"""
        thread = threading.Thread(target=self._retry_connect, daemon=True)
        thread.start()
    
    def _retry_connect(self):
        """Exponential backoff retry"""
        while self.retry_count < self.max_retries:
            try:
                # Attempt connection
                client = QdrantClient(host=self.host, port=self.port)
                client.get_collection_info('VetkaTree')
                self.is_connected = True
                print(f"✅ Qdrant connected at attempt #{self.retry_count + 1}")
                break
            except Exception as e:
                self.retry_count += 1
                wait_time = 2 ** self.retry_count  # 2s, 4s, 8s, 16s, 32s
                print(f"⏳ Qdrant reconnecting... (attempt {self.retry_count}, retry in {wait_time}s)")
                time.sleep(wait_time)
```

---

## 📋 **IMPLEMENTATION CHECKLIST**

### **Priority 1: Core Dashboard** (Days 1-2)
- [ ] Create `VetkaMetricsDashboard.jsx` (React component)
- [ ] Add Socket.IO event emitters in `orchestrator_langgraph_v2.py`
- [ ] Create `metrics_engine.py` (collection logic)
- [ ] Hook metrics into `main.py` endpoints

### **Priority 2: Model Router** (Day 2-3)
- [ ] Create `model_router_v2.py` with routing logic
- [ ] Add Redis cache for provider health
- [ ] Integrate into agent initialization
- [ ] Add metrics tracking for model usage

### **Priority 3: Feedback Loop** (Day 3)
- [ ] Create `feedback_loop_v2.py`
- [ ] Extend `/api/eval/feedback/submit` with few-shot injection
- [ ] Add "similar examples" retrieval
- [ ] Track improvement metrics

### **Priority 4: Qdrant Auto-Retry** (Day 1 - Quick Win)
- [ ] Create `qdrant_auto_retry.py`
- [ ] Background retry thread with exponential backoff
- [ ] Silent startup if Qdrant unavailable

---

## 🎨 **UI/UX MOCKUP**

### **Dashboard Layout:**
```
┌────────────────────────────────────────────────────────────────┐
│  VETKA METRICS DASHBOARD                          [⚙️ Settings] │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Timeline View                  │ Real-Time Stats             │
│  ├─ 🟢 PM Planning (2.3s)       │ Total Workflows: 247        │
│  ├─ 🟢 Architect Design (3.1s)  │ Success Rate: 94.2%         │
│  ├─ 🟠 Dev & QA Parallel        │ Avg Latency: 38.2s          │
│  │  ├─ Dev (8.2s)               │ Score Avg: 0.82             │
│  │  ├─ QA (9.1s)                │ Model Router Status: ✅      │
│  ├─ 🟢 Evaluation (5.3s)        │                             │
│  └─ 🟢 Feedback Storage (1.1s)  │                             │
│                                  │                             │
│  Model Usage Chart               │ Feedback Breakdown          │
│  Ollama:      ████████ 65%       │ 🟢 Good:  186 (75%)         │
│  OpenRouter:  ███ 22%            │ 🟡 Retry: 48 (19%)          │
│  Gemini:      █ 13%              │ 🔴 Poor:  13 (5%)           │
│                                  │                             │
│ [Recent Workflows]               │ [Export Data] [Settings]    │
└────────────────────────────────────────────────────────────────┘
```

---

## 🔌 **SOCKET.IO EVENTS REFERENCE**

**Server → Client (Dashboard):**
```javascript
// Workflow lifecycle
socketio.emit('workflow_started', {workflow_id, feature, timestamp})
socketio.emit('agent_complete', {agent, duration, status, timestamp})
socketio.emit('eval_score', {score, feedback_type, timestamp})
socketio.emit('workflow_complete', {duration, success, timestamp})

// Metrics updates
socketio.emit('metrics_update', {
    latency_per_agent: {...},
    score_distribution: [...],
    model_usage: {...},
    timestamp
})

// Model router status
socketio.emit('model_status', {
    selected_model: 'deepseek-coder:6.7b',
    fallback_used: false,
    cost_estimate: 0.05,
    provider_health: 'healthy'
})

// Memory status
socketio.emit('memory_status', {
    weaviate: 'connected',
    qdrant: 'reconnecting',
    changelog_entries: 1247,
    timestamp
})
```

---

## 🚀 **DEPLOYMENT CHECKLIST**

### **Backend Changes:**
- [ ] `src/monitoring/metrics_engine.py` ← NEW
- [ ] `src/elisya/model_router_v2.py` ← NEW/ENHANCED
- [ ] `src/orchestration/feedback_loop_v2.py` ← NEW
- [ ] `src/memory/qdrant_auto_retry.py` ← NEW
- [ ] `src/orchestration/orchestrator_langgraph_v2.py` ← ADD METRICS HOOKS
- [ ] `main.py` ← ADD METRICS ENDPOINTS

### **Frontend Changes:**
- [ ] `frontend/components/VetkaMetricsDashboard.jsx` ← NEW
- [ ] `frontend/pages/index.html` ← ADD DASHBOARD LINK
- [ ] `frontend/static/css/dashboard.css` ← NEW

### **Configuration:**
- [ ] `.env` ← ADD MODEL_ROUTER_CONFIG
- [ ] `config/metrics_config.yaml` ← NEW
- [ ] Redis connection string for model health cache

---

## 📈 **SUCCESS METRICS**

✅ **Dashboard loads in <2s**  
✅ **Metrics update real-time (< 100ms latency)**  
✅ **Model router reduces cost by 30%**  
✅ **Feedback loop improves score by 5-10% on second attempt**  
✅ **Qdrant auto-connects silently (no spam logs)**  
✅ **UI shows all 5 core metrics (latency, score, model, memory, retry)**

---

## 🔥 **NOTES FOR PHASE 7.4 IMPLEMENTATION**

1. **Backend is production-ready** → Focus on UI visualization
2. **Socket.IO already working** → Extend event set for metrics
3. **Metrics engine is lightweight** → Use in-memory dict + Redis for persistence
4. **Model Router can be gradual** → Start with simple rule-based routing
5. **Feedback Loop learns over time** → No breaking changes to existing workflow

**Estimated Time:** 2-3 days with parallel work streams  
**Risk Level:** LOW (Backend stable, UI additive)

---

**PHASE 7.4 — READY TO START IMPLEMENTATION! 🚀**
