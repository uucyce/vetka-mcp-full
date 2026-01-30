# Phase 93: API Keys Input Reconnaissance

**Agent:** Haiku
**Date:** 2026-01-25
**Status:** COMPLETE

---

## 1. UI COMPONENT

**Path:** `client/src/components/ModelDirectory.tsx`
**Lines:** 777-1172 (API Keys drawer section)

---

## 2. INPUT FIELDS

### Smart API Key Input:
| Field | Value |
|-------|-------|
| Name | `smart_api_key_input` |
| Type | text (monospace) |
| Placeholder | "Paste any API key..." |
| Detection | Auto (debounced) |

### Detected Provider Display:
- Provider name (display_name)
- Confidence % (0-100)
- Status indicator dot
- Add button (enabled if confidence >= 50%)

---

## 3. KEY TYPE DETECTION

### Detection Flow:
```
1. Static patterns (sk-or-*, sk-ant-*, AIza*, etc.)
     ↓
2. Learned patterns (learned_key_patterns.json)
     ↓
3. API endpoint: POST /api/keys/detect
     ↓
4. Unknown → "Ask @hostess" button
```

### Known Prefixes:
| Prefix | Provider |
|--------|----------|
| sk-or- | OpenRouter |
| sk-ant- | Anthropic |
| sk- | OpenAI |
| AIza | Google |
| gsk_ | Groq |
| hf_ | HuggingFace |
| xai- | XAI |
| tvly-dev- | Tavily |

---

## 4. HOSTESS SCENARIO

### When Hostess Asks:

**Trigger:** Unknown key type (confidence < 50%)

**Flow:**
1. User pastes unknown key
2. UI shows "Unknown key type"
3. User clicks "Ask @hostess to add this key"
4. Hostess receives CustomEvent with key
5. Hostess calls `analyze_unknown_key` tool
6. Returns hints: prefix, length, charset
7. **Hostess asks: "What service is this key for?"**
8. User responds with provider name
9. Hostess calls `learn_api_key` to save

### Hostess Tools:
| Tool | Purpose |
|------|---------|
| `save_api_key` | Auto-save with detection |
| `learn_api_key` | Learn new pattern |
| `analyze_unknown_key` | Extract pattern hints |
| `get_api_key_status` | Check configured providers |

---

## 5. ENDPOINTS

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/keys/detect` | POST | Auto-detect provider |
| `/api/keys/add-smart` | POST | Smart add with detection |
| `/api/keys/add` | POST | Manual add |
| `/api/keys` | GET | List saved keys |
| `/api/keys/learn-pattern` | POST | Learn new type |

---

## 6. VALIDATION

### Before Saving:
| Check | Value |
|-------|-------|
| Min length | >= 10 chars |
| Confidence | >= 50% to enable Add |
| Pattern analysis | prefix, length, charset |

### Response from /api/keys/detect:
```json
{
  "detected": true,
  "provider": "openrouter",
  "confidence": 0.95,
  "display_name": "OpenRouter"
}
```

---

## 7. STORAGE

| Data | Location |
|------|----------|
| Active keys | `data/config.json` → `api_keys` |
| Learned patterns | `data/learned_key_patterns.json` |

### Pattern Format:
```json
{
  "tavily": {
    "prefix": "tvly-dev-",
    "length_min": 40,
    "length_max": 50,
    "charset": "alphanumeric",
    "separator": "-",
    "confidence": 0.9
  }
}
```

---

## 8. FLOW DIAGRAM

```
User pastes key
       ↓
[Smart Input] debounced
       ↓
POST /api/keys/detect
       ↓
   Detected?
   ├─ YES (≥50%)
   │   └─ Show "Add {Provider}" button
   │       └─ POST /api/keys/add-smart
   │
   └─ NO (<50%)
       └─ Show "Ask @hostess" button
           └─ Hostess: "What service?"
               └─ User: "tavily"
                   └─ learn_api_key + save
```

---

## NOTES

- Detection is real-time (debounced 500ms)
- Hostess only asks for PROVIDER name, not key alias
- Patterns are self-learning (accumulate over time)
- Keys stored in config.json under provider names
