# 🌳 **PHASE 7.5 — VETKA 3D TREE VISUALIZATION**

**Status**: ✅ **READY FOR DEPLOYMENT**  
**Date**: October 28, 2025  
**Version**: Phase 7.5.0

---

## 📋 **SUMMARY**

**Phase 7.5** вводит **живую 3D визуализацию VetkaTree** с интерактивным мониторингом workflow'ов в реальном времени. Это **production-ready dashboard**, который показывает:

- ✅ **3D Tree с 4 веткам** (PM → DEV → QA → EVAL)
- ✅ **Live metrics** и динамические score'ы
- ✅ **Socket.IO интеграция** для real-time обновлений
- ✅ **System health monitoring** на боковой панели
- ✅ **Workflow history** с фильтрацией
- ✅ **Interactive controls** (rotate, zoom, reset)

---

## 🚀 **GETTING STARTED**

### **1. Запуск Backend (Phase 7.4.1 optimized)**

```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python main_phase_7_4_1_optimized.py
```

**Output:**
```
🌳 VETKA PHASE 7.4.1 - OPTIMIZED (ChatGPT & Qwen Feedback Applied)
=========================================================================

📊 Services:
   • Flask API: http://localhost:5001
   • Socket.IO: ws://localhost:5001/socket.io/
   • Weaviate: http://localhost:8080
   • Ollama: http://localhost:11434
   • Qdrant: http://localhost:6333 (auto-connecting...)

📈 Workflow Endpoints:
   ...
```

---

### **2. Открыть 3D Dashboard**

**Основной UI:**
```
http://localhost:5001  (Original Workflow UI)
```

**3D Tree Visualization (Phase 7.5):**
```
http://localhost:5001/3d  ← ⭐ NEW!
```

---

## 🎨 **UI COMPONENTS**

### **Left Panel: Workflow History**
```
🌳 VETKA
Phase 7.5 - 3D Tree Visualization

[Workflow 1] → ab2c3d
Score: 0.96

[Workflow 2] → xe9f2k
Score: 0.87

[Workflow 3] → zx1m4n
Score: 0.73
```

- **Clickable items** для выбора workflow'а
- **Live score display**
- **Last 10 workflows** в истории

---

### **Center Panel: 3D Tree Canvas**
```
       🟡 EVAL (0.96)
         ↑
    PM ─┼─ DEV (0.90)
(0.85)  │
        QA (0.78)
        
Root: 🔵
```

**Features:**
- Three.js рендер
- Интерактивная орбита камеры (drag для вращения)
- Real-time обновление scores
- Animated branches (opacity = score)
- Color-coded agents:
  - 🔵 **PM** — `#667eea` (фиолетовый)
  - 🟣 **Dev** — `#764ba2` (пурпурный)
  - 🟢 **QA** — `#4ade80` (зеленый)
  - 🟠 **Eval** — `#f59e0b` (оранжевый)

---

### **Top-Left: Tree Info**
```
🌳 Workflow Tree
PM Score:    0.85
Dev Score:   0.90
QA Score:    0.78
Eval Score:  0.96
──────────────────
Overall:     0.87
```

Auto-updates при выборе нового workflow'а.

---

### **Bottom-Left: Tree Controls**
```
[↺ Reset View] [↻ Auto Rotate] [📊 Metrics]
```

- **Reset View** — вернуть камеру в исходную позицию
- **Auto Rotate** — включить автоматическое вращение дерева
- **Metrics** — показать/скрыть info panel

---

### **Right Panel: System Status & Analytics**

#### **⚙️ System Status**
```
Backend:      🟢 Connected
Weaviate:     🟢 Connected
Model Router: 🟢 Enabled
Qdrant:       🟡 Connecting
```

#### **📊 Current Workflow**
```
Duration:      12.5s
Status:        Running
Queue Size:    2
```

#### **🤖 Agent Scores**
```
PM
0.85
[Running]

Dev
0.90
[Complete]

QA
0.78
[Complete]

Eval
0.96
[Complete]
```

#### **🎨 Legend**
```
🟣 PM Planning
🟣 Development
🟢 QA Testing
🟠 Evaluation
```

---

## 🔌 **SOCKET.IO INTEGRATION**

### **Incoming Events (Frontend слушает)**

```javascript
// Новый workflow завершен
socket.on('workflow_complete', (data) => {
    workflows.unshift(data);
    updateWorkflowList();
    drawTree(data.result);
});

// Система отправляет статус
socket.on('status_update', (data) => {
    updateSystemStatus(data);
});

// Qdrant подключился
socket.on('qdrant_connected', () => {
    document.getElementById('qdrant-status').textContent = '🟢 Connected';
});
```

### **Outgoing Events (Frontend отправляет)**

```javascript
// Backend для проверки статуса
socket.emit('get_status');

// Запуск нового workflow'а
socket.emit('start_workflow', {
    feature: 'Add OAuth2 authentication...'
});
```

---

## 📊 **API ENDPOINTS (Phase 7.5 Compatible)**

### **Health & System**
```
GET /health
GET /api/system/summary
GET /api/qdrant/status
```

### **Workflow Data**
```
GET /api/workflow/history?limit=10
GET /api/workflow/stats
GET /api/workflow/<workflow_id>
```

### **Metrics (for Dashboard)**
```
GET /api/metrics/dashboard
GET /api/metrics/agents
GET /api/metrics/models
GET /api/metrics/providers
GET /api/metrics/feedback
```

---

## 🎯 **THREE.JS FEATURES**

### **Geometry**
```javascript
// Branch = Cylinder (0.15 radius, dynamic length)
// Root = Sphere (0.4 radius)
// Labels = Canvas textures + sprites
```

### **Materials**
```javascript
// Metalness: 0.3
// Roughness: 0.4
// Emissive: based on score (0.0 - 1.0)
// Transparency: opacity = score
```

### **Lighting**
```javascript
// Ambient: 0.6 intensity
// Point Light: position [10, 10, 10], intensity 0.8
// Shadows: castShadow + receiveShadow
```

### **Camera Controls**
```javascript
// OrbitControls:
//   - damping: true (smooth movement)
//   - autoRotate: toggleable
//   - auto_speed: 4 rpm
```

---

## 💡 **USAGE EXAMPLES**

### **Пример 1: Посмотреть последний workflow в 3D**

```
1. Open http://localhost:5001/3d
2. Last workflow автоматически загружается
3. Кликните на другой workflow в левой панели
4. Дерево обновится с его scores
```

---

### **Пример 2: Мониторить live workflow**

```
1. На обычном UI http://localhost:5001:
   - Запустите workflow
   - Следите за progress

2. На 3D Dashboard http://localhost:5001/3d:
   - Автоматически обновится при завершении
   - Увидите final scores в дереве
   - Queue size будет обновляться в real-time
```

---

### **Пример 3: Анализировать metrics**

```
1. Запустите несколько workflow'ов
2. В правой панели посмотрите:
   - Average latency
   - Success rate (завершенные/total)
   - Per-agent performance
```

---

## 🔧 **TECHNICAL ARCHITECTURE**

### **Frontend Stack**
- **Three.js r128** — 3D рендеринг
- **Socket.IO 4.5.4** — Real-time communication
- **OrbitControls** — Interactive camera
- **Chart.js 3.9.1** — (optional for future metrics graphs)
- **Vanilla JavaScript** — No dependencies except above

### **Backend Integration**
- **Flask 2.x** — HTTP server
- **Flask-SocketIO** — WebSocket support
- **Python 3.9+** — Backend language

### **Data Flow**
```
Backend (main.py)
    ↓
    Metrics Engine
    ↓
Socket.IO Broadcast
    ↓
Frontend (vetka_tree_3d.html)
    ↓
JavaScript Event Listeners
    ↓
Three.js Scene Updates
    ↓
🖥️ 3D Canvas Render
```

---

## 📈 **PERFORMANCE METRICS**

| Metric | Value | Note |
|--------|-------|------|
| FPS | 60 | Target frame rate |
| Canvas Size | Responsive | Full-screen minus sidebars |
| Message Latency | <100ms | Socket.IO overhead |
| Tree Update | <50ms | JavaScript geometry rebuild |
| Workflow Refresh | ~5s | Data from server |

---

## 🚨 **TROUBLESHOOTING**

### **3D Canvas не загружается**

```bash
# Проверьте браузер console (F12):
# - WebGL поддержка
# - Three.js loaded
# - Socket.IO connected

# Решение:
1. Use Chrome/Safari (better WebGL support)
2. Check http://localhost:5001/3d loads
3. Open DevTools → Console для ошибок
```

---

### **Дерево не обновляется**

```bash
# Проверьте Socket.IO connection:

socket.on('connect', () => {
    console.log('✅ Connected');
});

# Если не connected:
1. Проверьте backend на http://localhost:5001
2. Проверьте CORS настройки (должны быть "*")
3. Перезагрузите браузер
```

---

### **Scores всегда 0.00**

```bash
# Проверьте workflow'ов результаты:

# 1. На обычном UI http://localhost:5001:
#    - Запустите workflow
#    - Посмотрите scores в stream'е

# 2. На 3D Dashboard:
#    - Подождите 2-3 сек после завершения
#    - Дерево должно обновиться
#    - Если нет, проверьте консоль для Socket.IO ошибок
```

---

## 📝 **FILE STRUCTURE**

```
vetka_live_03/
├── main_phase_7_4_1_optimized.py    ← Backend (updated with /3d endpoint)
├── frontend/
│   ├── templates/
│   │   ├── index.html               ← Original workflow UI
│   │   └── vetka_tree_3d.html       ← ⭐ NEW: 3D Tree Dashboard
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── package.json
└── PHASE_7_5_README.md              ← This file
```

---

## 🎓 **LEARNING PATH**

### **For Developers:**
1. Open `vetka_tree_3d.html` → Понять структуру
2. Modify `createBranch()` → Экспериментировать с geometry
3. Change colors → `#667eea`, `#764ba2`, и т.д.
4. Add new metrics → Extend Socket.IO listeners

### **For DevOps:**
1. Monitor `/api/system/summary` endpoint
2. Track `/api/metrics/dashboard` for performance
3. Use `/api/qdrant/status` to verify VetkaTree availability

### **For Users:**
1. Open `/3d` URL
2. Watch your workflows in 3D
3. Click history items to explore past executions
4. Use controls to rotate/inspect the tree

---

## ✅ **DEPLOYMENT CHECKLIST**

- [x] Backend endpoint `/3d` created
- [x] HTML template `vetka_tree_3d.html` created
- [x] Three.js integration working
- [x] Socket.IO real-time updates
- [x] System status panel
- [x] Workflow history sidebar
- [x] Interactive controls
- [x] Responsive layout
- [x] Error handling
- [x] Documentation (this file)

---

## 🔮 **FUTURE ENHANCEMENTS (Phase 7.6+)**

- [ ] **Export to PNG** — Screenshot workflow tree
- [ ] **Animation Timeline** — Replay workflow execution step-by-step
- [ ] **Metrics Graphs** — Embed Chart.js for latency/success rate
- [ ] **VR Support** — WebXR for immersive 3D experience
- [ ] **Team Collaboration** — Multi-user 3D dashboard
- [ ] **Mobile Responsive** — Touch controls for tablets
- [ ] **Dark Mode Toggle** — Already dark, but add light mode
- [ ] **Custom Themes** — User-configurable colors

---

## 📞 **SUPPORT**

```
Issues: Check browser console (F12 → Console tab)
Logs: Check Flask console output
Socket.IO: Check network tab in DevTools
```

---

## 📄 **VERSION HISTORY**

| Version | Date | Changes |
|---------|------|---------|
| 7.5.0 | Oct 28, 2025 | Initial release - 3D Tree visualization, real-time metrics, system health panel |

---

**Made with ❤️ for VETKA Phase 7.5**

🚀 **Ready for production deployment!**
