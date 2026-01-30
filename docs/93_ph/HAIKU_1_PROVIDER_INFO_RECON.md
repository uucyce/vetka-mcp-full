# Phase 93: Provider Info Reconnaissance

**Agent:** Haiku
**Date:** 2026-01-25
**Status:** COMPLETE

---

## 1. MODEL INFORMATION SOURCES

### Primary Sources:

| Source | Location | Description |
|--------|----------|-------------|
| Hardcoded | `src/services/model_registry.py:81-245` | 45 default models in `DEFAULT_MODELS` |
| Ollama Discovery | `model_registry.discover_ollama_models()` | Queries `http://localhost:11434/api/tags` |
| Cache | `data/models_cache.json` | 381 models, cached 2026-01-24 |
| Config | `data/config.json` | API keys determine provider availability |

---

## 2. HEALTH CHECK MECHANISM

### Registry Health Checks:
- **Interval:** Every 5 minutes (configurable)
- **Location:** `model_registry.check_health()` lines 299-345
- **Ollama:** Checks via `/api/tags` endpoint
- **Cloud:** Verifies API key existence

### Provider Status Tracking:
- **Location:** `model_router_v2.provider_status` (in-memory Dict)
- **Redis backup:** Optional (Phase 7.4)

**Fields tracked:**
```python
{
    "healthy": bool,
    "error_count": int,
    "last_success": float,  # Unix timestamp
    "last_error": float     # Unix timestamp
}
```

### Key Manager Health:
- **Location:** `unified_key_manager.APIKeyRecord`
- **Cooldown:** 24 hours on 401/402/403/429 errors
- **Methods:** `is_available()`, `cooldown_remaining()`

---

## 3. OFFLINE DETECTION

### API Gateway Detection:
- **File:** `api_gateway.py` lines 571-607
- **Methods:**
  - `get_provider_health()` - analyzes all keys
  - `export_health_report()` - complete status

### Status Codes Handled:
| Code | Meaning | Action |
|------|---------|--------|
| 401 | Unauthorized | Mark rate-limited (24h) |
| 402 | Payment required | Mark rate-limited |
| 403 | Forbidden | Mark rate-limited |
| 429 | Rate limit | Mark rate-limited |
| 404 | Not found | Fallback to OpenRouter |

---

## 4. TIMESTAMP STORAGE

| Field | Location | Type | Meaning |
|-------|----------|------|---------|
| `last_health_check` | ModelEntry | datetime | Last API check |
| `last_used` | APIKeyRecord | datetime | Last key usage |
| `last_success` | provider_status | float | Last successful call |
| `last_error` | provider_status | float | Last error |
| `rate_limited_at` | APIKeyRecord | datetime | Cooldown start |
| `cached_at` | models_cache.json | ISO string | Cache time |

---

## 5. API ENDPOINTS

**File:** `src/api/routes/model_routes.py`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/models` | GET | All models |
| `/api/models/available` | GET | Available only |
| `/api/models/local` | GET | Ollama models |
| `/api/models/free` | GET | Free + local |
| `/api/models/mcp-agents` | GET | MCP agents |
| `/api/models/health/{id}` | POST | Health check |
| `/api/models/recent` | GET | Recently used |
| `/api/models/favorites` | GET | Starred |

---

## SUMMARY

**Current State:**
- ✅ Timestamps exist (`last_success`, `last_error`)
- ✅ Health checks run every 5 min
- ✅ 24h cooldown on rate limits
- ❌ No UI display of model status
- ❌ No "last seen" in phonebook

**To Add:**
- Display `last_success` as "last seen" in UI
- Show online/offline status based on `healthy` field
