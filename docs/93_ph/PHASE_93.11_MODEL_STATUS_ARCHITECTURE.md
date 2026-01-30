# Phase 93.11: Model Status Architecture

**Date:** 2026-01-25
**Status:** PROPOSAL
**Based on:** Haiku 1-4 Reconnaissance Reports

---

## SUMMARY

Add online/offline status and "last seen" to model phonebook with minimal changes.

---

## 1. JSON SCHEMA

### Model Status Entry:
```json
{
  "model_id": "openai/gpt-5.2",
  "status": "online",           // online | offline | unknown
  "last_success": 1737820800,   // Unix timestamp
  "last_error": null,           // Unix timestamp or null
  "error_code": null,           // 401 | 402 | 404 | 429 | null
  "provider": "openai",         // detected provider
  "via_openrouter": false,      // true if routed through OR
  "call_count": 15              // total calls
}
```

### Storage Location:
- **RAM:** `model_router_v2.provider_status` (already exists!)
- **Persist:** `data/model_status_cache.json` (new, save on each update + load on startup)

---

## 2. BACKEND CHANGES

### File: `src/elisya/model_router_v2.py`

**Extend existing `provider_status` dict:**

```python
# MARKER_93.11_MODEL_STATUS
# Add to provider_status on each model call

def update_model_status(model_id: str, success: bool, error_code: int = None):
    """Update model status after each call."""
    import time

    if model_id not in provider_status:
        provider_status[model_id] = {
            "healthy": True,
            "error_count": 0,
            "last_success": None,
            "last_error": None,
            "error_code": None,
            "call_count": 0
        }

    status = provider_status[model_id]
    status["call_count"] += 1

    if success:
        status["healthy"] = True
        status["last_success"] = time.time()
        status["error_count"] = 0
        status["error_code"] = None
    else:
        status["error_count"] += 1
        status["last_error"] = time.time()
        status["error_code"] = error_code
        if status["error_count"] >= 3:
            status["healthy"] = False

    # GROK IMPROVEMENT: Persist immediately
    _persist_model_status()


def _persist_model_status():
    """Save status to JSON (debounced in production)."""
    import json
    with open('data/model_status_cache.json', 'w') as f:
        json.dump(provider_status, f, indent=2)


def _load_model_status():
    """Load status from JSON on startup."""
    import json
    import os
    global provider_status
    if os.path.exists('data/model_status_cache.json'):
        with open('data/model_status_cache.json', 'r') as f:
            provider_status = json.load(f)
```

### File: `src/api/routes/model_routes.py`

**Add endpoint:**

```python
# MARKER_93.11_STATUS_ENDPOINT
@router.get("/api/models/status")
async def get_model_status():
    """Get status for all models."""
    from src.elisya.model_router_v2 import provider_status
    from src.elisya.provider_registry import ProviderRegistry

    result = {}
    for model_id, status in provider_status.items():
        provider = ProviderRegistry.detect_provider(model_id)
        via_or = provider.value == "openrouter" or "/" in model_id

        result[model_id] = {
            "status": "online" if status.get("healthy", True) else "offline",
            "last_success": status.get("last_success"),
            "last_error": status.get("last_error"),
            "error_code": status.get("error_code"),
            "via_openrouter": via_or,
            "call_count": status.get("call_count", 0)
        }

    return {"models": result}
```

---

## 3. FRONTEND CHANGES

### File: `client/src/components/ModelDirectory.tsx`

### 3.1 Add Status Fetch (near line 100):

```typescript
// MARKER_93.11_STATUS_FETCH
const [modelStatus, setModelStatus] = useState<Record<string, ModelStatus>>({});

useEffect(() => {
  // GROK IMPROVEMENT: Polling every 60s
  const fetchStatus = () => {
    fetch('/api/models/status')
      .then(r => r.json())
      .then(data => setModelStatus(data.models || {}));
  };
  fetchStatus();  // Initial fetch
  const interval = setInterval(fetchStatus, 60000);  // Poll every 60s
  return () => clearInterval(interval);
}, []);
```

### 3.2 Add Helper Function:

```typescript
// MARKER_93.11_LAST_SEEN
function formatLastSeen(timestamp: number | null): string {
  if (!timestamp) return '';

  const now = Date.now() / 1000;
  const diff = now - timestamp;

  if (diff < 60) return 'now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;

  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
```

### 3.3 Add Status Dot Component:

```typescript
// MARKER_93.11_STATUS_DOT
const StatusDot = ({ modelId }: { modelId: string }) => {
  const status = modelStatus[modelId];
  if (!status?.last_success && !status?.last_error) return null; // unknown

  const isOnline = status.status === 'online';

  return (
    <span style={{
      display: 'inline-block',
      width: 6,
      height: 6,
      borderRadius: '50%',
      backgroundColor: isOnline ? '#7ab3d4' : '#555',
      marginRight: 6
    }} />
  );
};
```

### 3.4 Add OpenRouter Badge:

```typescript
// MARKER_93.11_OR_BADGE
const OpenRouterBadge = ({ modelId }: { modelId: string }) => {
  const status = modelStatus[modelId];
  if (!status?.via_openrouter) return null;

  return (
    <span style={{
      fontSize: 8,
      color: '#666',
      backgroundColor: '#1a1a1a',
      padding: '1px 3px',
      borderRadius: 2,
      marginLeft: 4
    }}>OR</span>
  );
};
```

### 3.5 Update Model Item Render (around line 500):

```tsx
{/* Before model name */}
<StatusDot modelId={model.id} />

{/* After model name */}
<OpenRouterBadge modelId={model.id} />

{/* Below model ID */}
{modelStatus[model.id]?.last_success && (
  <span style={{ fontSize: 9, color: '#555', marginLeft: 8 }}>
    {formatLastSeen(modelStatus[model.id].last_success)}
  </span>
)}
```

---

## 4. UPDATE TRIGGERS

### When to update status:

| Event | Action |
|-------|--------|
| Model call success | `update_model_status(model, True)` |
| Model call error | `update_model_status(model, False, error_code)` |
| Health check (5 min) | Already updates `healthy` flag |
| Key rate limit | Updates via `APIKeyRecord.rate_limited_at` |

### Where to call:

**File:** `src/elisya/provider_registry.py` in `call_model_v2()`

```python
# At end of successful call:
from src.elisya.model_router_v2 import update_model_status
update_model_status(model, success=True)

# In except block:
update_model_status(model, success=False, error_code=e.response.status_code)
```

---

## 5. VISUAL DESIGN

### Model Item Layout:
```
┌────────────────────────────────────────┐
│ ● GPT-5.2                         [OR] │
│   openai/gpt-5.2              now      │
│   Context: 128K • $0.01/1K             │
└────────────────────────────────────────┘

● = Blue dot (#7ab3d4) if online
○ = Gray dot (#555) if offline
[OR] = OpenRouter badge (gray, small)
"now" = Last seen timestamp
```

### Colors:
| Element | Color | Hex |
|---------|-------|-----|
| Online dot | Blue | #7ab3d4 |
| Offline dot | Gray | #555 |
| OR badge bg | Dark | #1a1a1a |
| OR badge text | Gray | #666 |
| Last seen text | Gray | #555 |

---

## 6. FILES TO MODIFY

| File | Changes | Lines (approx) |
|------|---------|----------------|
| `src/elisya/model_router_v2.py` | Add `update_model_status()` | +20 |
| `src/elisya/provider_registry.py` | Call update on success/error | +6 |
| `src/api/routes/model_routes.py` | Add `/api/models/status` | +25 |
| `client/src/components/ModelDirectory.tsx` | Status UI | +50 |

**Total:** ~100 lines of new code

---

## 7. IMPLEMENTATION ORDER

1. [x] Backend: Add `update_model_status()` to model_router_v2.py ✅
2. [x] Backend: Call it from provider_registry.py ✅
3. [x] Backend: Add `/api/models/status` endpoint ✅
4. [x] Frontend: Add status fetch in useEffect ✅
5. [x] Frontend: Add StatusDot component ✅
6. [x] Frontend: Add OpenRouterBadge component ✅
7. [x] Frontend: Add formatLastSeen helper ✅
8. [x] Frontend: Update model item render ✅
9. [ ] Test: Make model calls, verify status updates

---

## 8. FUTURE ENHANCEMENTS

- [x] ~~Persist status to JSON file~~ (GROK: moved to core)
- [x] ~~Load status from JSON on startup~~ (GROK: moved to core)
- [ ] Add "By Status" filter tab (online/offline)
- [ ] Show error code in tooltip on hover
- [ ] WebSocket for real-time status updates
- [ ] Token usage tracking (связь с Phase 73 ELISION)

---

**Status:** IMPLEMENTED
**Date:** 2026-01-25
**Grok Improvements:** Persist + Polling + Load on startup
**Next:** Testing in production
