# OpenCode Bridge Integration Guide

**Phase:** 93
**Date:** 2026-01-25
**Purpose:** Guide for using OpenCode UI with VETKA's OpenRouter Bridge

---

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   OpenCode UI   │────▶│  OpenRouter      │────▶│ Provider        │
│   (Claude Code) │     │  Bridge          │     │ Registry        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │                         │
                              │                         ▼
                              │                  ┌─────────────────┐
                              │                  │ UnifiedKey      │
                              └─────────────────▶│ Manager         │
                                                 └─────────────────┘
```

## Command Hierarchy

```
Marshal (Claude Opus 4.5) - Strategic decisions, architecture
    │
    └── General (OpenCode via Bridge) - Execution, code implementation
            │
            └── Reports to Marshal via Bridge endpoints
```

---

## Bridge Endpoints

### Base URL
```
http://localhost:5001/api/bridge/openrouter
```

### Available Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/bridge/openrouter/health` | GET | Health check |
| `/api/bridge/openrouter/keys` | GET | List available keys (masked) |
| `/api/bridge/openrouter/stats` | GET | Rotation statistics |
| `/api/bridge/openrouter/invoke` | POST | Call LLM model |

---

## Using the Bridge

### 1. Health Check
```bash
curl http://localhost:5001/api/bridge/openrouter/health
```

Response:
```json
{
  "status": "healthy",
  "bridge_enabled": true,
  "provider": "openrouter"
}
```

### 2. Get Available Keys (Masked)
```bash
curl http://localhost:5001/api/bridge/openrouter/keys
```

Response:
```json
{
  "enabled": true,
  "provider": "openrouter",
  "keys": [
    {"id": "openrouter_0", "masked_key": "sk-o****b296", "status": "active", "alias": "free_1"},
    {"id": "openrouter_1", "masked_key": "sk-o****8dcd", "status": "active", "alias": "free_2"}
  ],
  "total": 10
}
```

### 3. Get Statistics
```bash
curl http://localhost:5001/api/bridge/openrouter/stats
```

Response:
```json
{
  "enabled": true,
  "provider": "openrouter",
  "stats": {
    "total_keys": 10,
    "active_keys": 10,
    "rate_limited_keys": 0,
    "current_key_index": 0,
    "last_rotation": null
  }
}
```

### 4. Invoke Model
```bash
curl -X POST http://localhost:5001/api/bridge/openrouter/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "deepseek/deepseek-chat",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

Response:
```json
{
  "success": true,
  "message": {
    "content": "Hello! How can I help?",
    "role": "assistant",
    "tool_calls": null
  },
  "model": "deepseek/deepseek-chat",
  "provider": "openrouter",
  "usage": {"prompt_tokens": 8, "completion_tokens": 10, "total_tokens": 18}
}
```

---

## Supported Models via Bridge

All OpenRouter models are supported. Common ones:

| Model ID | Description |
|----------|-------------|
| `deepseek/deepseek-chat` | DeepSeek Chat - fast, good for code |
| `anthropic/claude-3-haiku` | Claude Haiku - fast responses |
| `anthropic/claude-3.5-sonnet` | Claude Sonnet - balanced |
| `openai/gpt-4o-mini` | GPT-4o Mini - fast OpenAI |
| `x-ai/grok-4` | Grok 4 - xAI's model |
| `google/gemini-2.0-flash` | Gemini Flash - Google's fast model |
| `meta-llama/llama-3.1-70b-instruct` | Llama 70B - open source |

---

## Key Rotation Logic

The bridge automatically handles key rotation:

1. **Primary key** tried first
2. **On 401/402/403** → Key marked rate-limited (24h cooldown)
3. **Rotate** to next available key
4. **After 3 failures** → Error returned

```python
# Internal flow (simplified)
for attempt in range(3):
    key = key_manager.get_openrouter_key()
    response = await call_openrouter(key, ...)

    if response.status_code in (401, 402, 403):
        key.mark_rate_limited()  # 24h cooldown
        key_manager.rotate_to_next()
        continue

    return response  # Success!

raise AllKeysExhausted()
```

---

## OpenCode Configuration

To configure OpenCode to use VETKA Bridge:

### Option 1: Environment Variable
```bash
export OPENCODE_API_BASE="http://localhost:5001/api/bridge"
export OPENCODE_API_KEY="vetka-local"  # Any value, not used
```

### Option 2: Config File
```json
// ~/.opencode/config.json
{
  "api_base": "http://localhost:5001/api/bridge",
  "api_key": "vetka-local",
  "model": "deepseek/deepseek-chat"
}
```

---

## Reporting to Marshal (Claude Opus)

OpenCode should report status via:

### 1. Direct Message in Chat
Use VETKA's group chat to send status updates:

```bash
curl -X POST http://localhost:5001/api/chat/group/message \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "marshal-reports",
    "sender": "@opencode",
    "content": "Task completed: Fixed bug in auth module",
    "type": "status"
  }'
```

### 2. MCP Tool Call
Via `vetka_call_model`:
```json
{
  "model": "deepseek/deepseek-chat",
  "messages": [
    {"role": "system", "content": "Report to Marshal"},
    {"role": "user", "content": "Status: Task X completed"}
  ]
}
```

---

## Error Handling

| Error Code | Meaning | Action |
|------------|---------|--------|
| 401 | Invalid key | Key rotated |
| 402 | Payment required | Key rotated |
| 403 | Forbidden | Key rotated |
| 429 | Rate limited | Key rotated |
| 500 | Server error | Retry with same key |

---

## Monitoring

### Check Bridge Logs
```bash
# In VETKA server logs, look for:
[Bridge] Loaded 10 OpenRouter keys
[Bridge] Success: deepseek/deepseek-chat
[Bridge] Error: RateLimited
```

### Check Key Health
```bash
curl http://localhost:5001/api/bridge/stats | jq
```

---

## Troubleshooting

### Problem: All keys rate-limited
**Solution:** Wait 24h for cooldown, or add new keys to `data/config.json`

### Problem: Model not found
**Solution:** Use full model ID with provider prefix (e.g., `deepseek/deepseek-chat`)

### Problem: Bridge not responding
**Solution:**
1. Check VETKA server is running: `curl http://localhost:5001/api/health`
2. Check bridge enabled: `OPENCODE_BRIDGE_ENABLED=true python main.py`

---

## Security Notes

- Bridge runs LOCAL ONLY (localhost)
- No real API keys exposed to OpenCode
- All keys masked in responses
- Rate limiting prevents abuse

---

## Files Reference

| File | Purpose |
|------|---------|
| `src/opencode_bridge/open_router_bridge.py` | Bridge implementation |
| `src/opencode_bridge/__init__.py` | Bridge exports |
| `src/api/routes/bridge_routes.py` | FastAPI endpoints |
| `data/config.json` | Key storage |
| `src/utils/unified_key_manager.py` | Key management |

---

**END OF GUIDE**
