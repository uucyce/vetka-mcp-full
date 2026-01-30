# Phase 36: Route Extraction Report

**Date:** 2026-01-04
**Commit:** `3c2abf7`
**Status:** COMPLETE

## Summary

Extracted 4 route modules from `main.py`, reducing file size by ~914 lines.

**Before:** 7220 lines
**After:** 6306 lines
**Reduction:** -914 lines (-12.7%)

---

## Extracted Modules

### 1. `src/server/routes/student_routes.py`

| Property | Value |
|----------|-------|
| **Lines** | ~350 |
| **Endpoints** | 14 |
| **Source Lines** | main.py:4440-4793 |

**Endpoints:**
- `GET /api/students/status` - Student system status
- `GET /api/students/levels` - Get all level definitions
- `GET /api/students/progress` - Get current student progress
- `POST /api/students/answer` - Submit answer and evaluate
- `GET /api/students/leaderboard` - Get student leaderboard
- `POST /api/students/reset` - Reset student progress
- `GET /api/training/simpo/status` - SimPO training status
- `POST /api/training/simpo/start` - Start SimPO training loop
- `POST /api/training/simpo/stop` - Stop SimPO training loop
- `GET /api/training/simpo/logs` - Get training logs
- `POST /api/training/simpo/config` - Update SimPO config
- `GET /api/training/simpo/examples` - Get training examples
- `POST /api/training/simpo/example` - Add training example
- `DELETE /api/training/simpo/example/<id>` - Delete training example

**Dependencies (via app.config):**
- `STUDENT_SYSTEM_AVAILABLE`
- `student_level_system`
- `promotion_engine`
- `simpo_loop`

---

### 2. `src/server/routes/learner_routes.py`

| Property | Value |
|----------|-------|
| **Lines** | ~290 |
| **Endpoints** | 8 |
| **Source Lines** | main.py:4054-4324 |

**Endpoints:**
- `GET /api/learner/stats` - Get learner statistics
- `GET /api/learner/info` - Get learner info and available models
- `POST /api/learner/switch` - Switch learner model
- `POST /api/smart-learner/select` - Select optimal model for task
- `POST /api/smart-learner/classify` - Classify task into category
- `GET /api/smart-learner/stats` - Get SmartLearner usage stats
- `POST /api/hope/analyze` - HOPE hierarchical analysis
- `POST /api/hope/quick` - Quick single-layer HOPE analysis

**Dependencies (via app.config):**
- `LEARNER_AVAILABLE`, `learner_agent`, `LearnerFactory`
- `LEARNER_TYPE`, `LEARNER_CONFIG`
- `SMART_LEARNER_AVAILABLE`, `smart_learner`
- `HOPE_ENHANCER_AVAILABLE`, `hope_enhancer`, `FrequencyLayer`
- `get_memory_manager`, `get_eval_agent`

---

### 3. `src/server/routes/intake_routes.py`

| Property | Value |
|----------|-------|
| **Lines** | ~100 |
| **Endpoints** | 4 |
| **Source Lines** | main.py:6393-6484 |

**Endpoints:**
- `POST /api/intake/process` - Process URL and extract content
- `GET /api/intake/list` - List processed intakes
- `GET /api/intake/<filename>` - Get specific intake
- `DELETE /api/intake/<filename>` - Delete an intake

**Dependencies:**
- `IntakeManager` (lazy loaded via `get_intake_manager()`)

---

### 4. `src/server/routes/mcp_routes.py`

| Property | Value |
|----------|-------|
| **Lines** | ~240 |
| **Endpoints** | 13 |
| **Source Lines** | main.py:6149-6391 |

**Endpoints:**

*MCP Core:*
- `GET /api/mcp/status` - MCP health check
- `POST /api/mcp/call` - REST endpoint for tool calls
- `GET /api/mcp/tools` - List available MCP tools

*MCP Security:*
- `GET /api/mcp/rate-limit` - Rate limit status
- `GET /api/mcp/audit` - Audit log entries
- `GET /api/mcp/approvals` - Pending approvals
- `POST /api/mcp/approvals/<id>/approve` - Approve request
- `POST /api/mcp/approvals/<id>/reject` - Reject request

*Claude Desktop:*
- `GET /api/mcp/claude-config` - Generate Claude Desktop config

*Memory Transfer:*
- `POST /api/memory/export` - Export VETKA memory
- `POST /api/memory/import` - Import VETKA memory
- `GET /api/memory/exports` - List memory exports
- `DELETE /api/memory/exports/<filename>` - Delete export

**Dependencies (via app.config):**
- `MCP_AVAILABLE`
- `mcp_server`

---

## Updated Files

### Modified

| File | Changes |
|------|---------|
| `main.py` | -957 lines (route functions removed), +43 lines (section markers, config injection) |
| `src/server/routes/__init__.py` | +4 imports, +4 register calls |

### Created

| File | Lines | Description |
|------|-------|-------------|
| `src/server/routes/student_routes.py` | 350 | Student system + SimPO routes |
| `src/server/routes/learner_routes.py` | 328 | Learner + SmartLearner + HOPE routes |
| `src/server/routes/intake_routes.py` | 106 | Content intake routes |
| `src/server/routes/mcp_routes.py` | 260 | MCP API + Memory transfer routes |

---

## Technical Details

### Dependency Injection Pattern

All extracted blueprints use dependency injection via `app.config` to access globals:

```python
# In main.py (after initialization)
app.config['STUDENT_SYSTEM_AVAILABLE'] = STUDENT_SYSTEM_AVAILABLE
app.config['student_level_system'] = student_level_system

# In blueprint
def _get_deps():
    """Get dependencies from app.config."""
    return {
        'available': current_app.config.get('STUDENT_SYSTEM_AVAILABLE', False),
        'system': current_app.config.get('student_level_system'),
    }

@blueprint.route('/api/students/status')
def status():
    deps = _get_deps()
    if not deps['available']:
        return jsonify({'error': 'Not available'}), 503
    # ... use deps['system']
```

### Section Markers in main.py

Each extracted section is replaced with a marker:

```python
# ═══════════════════════════════════════════════════════════════
# SECTION: STUDENT_ROUTES — EXTRACTED to src/server/routes/student_routes.py
# Endpoints: /api/students/*, /api/training/simpo/* (14 endpoints, ~350 lines)
# ═══════════════════════════════════════════════════════════════
# See src/server/routes/student_routes.py for all 14 endpoints
```

### What Remains in main.py

SocketIO handlers for `/mcp` namespace remain in main.py because they require the `socketio` instance:
- `@socketio.on('connect', namespace='/mcp')`
- `@socketio.on('disconnect', namespace='/mcp')`
- `@socketio.on('list_tools', namespace='/mcp')`
- `@socketio.on('tool_call', namespace='/mcp')`

---

## Route Registration Order

`src/server/routes/__init__.py`:

```python
from . import (
    tree_routes,      # /3d, /3d-dashboard
    chat_routes,      # /chat
    scan_routes,      # /api/scan/*, /onboarding
    health_routes,    # /health, /api/system/*, /api/phase*/status
    files_routes,     # /api/files/*
    artifact_routes,  # /artifact-panel/*, /api/artifact/*
    workflow_routes,  # /api/workflow/*
    student_routes,   # /api/students/*, /api/training/simpo/*
    learner_routes,   # /api/learner/*, /api/smart-learner/*, /api/hope/*
    intake_routes,    # /api/intake/*
    mcp_routes,       # /api/mcp/*, /api/memory/*
)
```

---

## Testing Checklist

- [ ] `curl http://localhost:5001/api/students/status`
- [ ] `curl http://localhost:5001/api/learner/stats`
- [ ] `curl http://localhost:5001/api/intake/list`
- [ ] `curl http://localhost:5001/api/mcp/status`
- [ ] `curl http://localhost:5001/api/memory/exports`

---

## Next Steps

Routes remaining in main.py for future extraction:

| Section | Lines | Complexity |
|---------|-------|------------|
| `/api/tree/data` | ~750 | High - needs layout refactor |
| `/api/chat` | ~300 | High - needs orchestrator refactor |
| Other API routes | ~2000 | Medium - needs module extraction |
| SocketIO handlers | ~500 | High - needs workflow_runner.py |

Estimated total remaining: ~3500 lines in main.py after all extractions.
