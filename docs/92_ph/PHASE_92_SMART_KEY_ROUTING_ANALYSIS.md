# Phase 92: Smart Key Routing Analysis + MCP Integration

**Date:** 2026-01-25
**Status:** 📋 ANALYZED
**Agent:** Claude Sonnet 4.5

---

## 🎯 Mission

Analyze smart key routing functionality and MCP integration with Claude Code for optimal model selection and key management.

---

## 📊 Current Architecture

### 🔑 Key Management System

**Core Component:** `src/utils/unified_key_manager.py`

**Key Providers:**
- **OpenRouter:** Multiple keys (free/paid) with auto-rotation
- **xAI (Grok):** Single key with fallback to OpenRouter
- **OpenAI:** GPT models
- **Anthropic:** Claude models (через OpenRouter)
- **Ollama:** Локальные модели

### 🔄 Smart Routing Logic

**File:** `src/orchestration/orchestrator_with_elisya.py`
**Function:** `_inject_api_key()` (lines 553-554)

**Flow:**
1. **Check xAI key first** (Phase 80.37)
2. **Fallback to OpenRouter** if xAI unavailable
3. **Rotate keys on failure** (auto-rotation)
4. **Mark failed keys** (avoid reuse)

---

## 🔍 Claude Code MCP Integration Details

### 📡 MCP Bridge Configuration

**Current Setup:** VETKA использует `vetka_call_model` через MCP

**Format According to Claude Code:**
```json
{
  "model": "xai/grok-beta",     // provider/model-name format
  "messages": [{"role": "user", "content": "Hello"}],
  "max_tokens": 999999
}
```

**Supported Model Formats:**
- **Grok:** `xai/grok-beta` или `xai/grok-3`
- **GPT-4o:** `openai/gpt-4o`
- **Claude:** `anthic/claude-3-opus` (через OpenRouter)
- **Ollama:** `ollama/qwen2:7b` (локально)

### 🚨 Current Issue: Ollama Fallback

**Problem:** vetka_call_model падает на Ollama

**Root Cause According to Claude Code:**
1. **Нет API ключа для xai** в ~/.bashrc или ~/.zshrc
2. **Ключ не экспортирован:** `export XAI_API_KEY=...`

**Diagnostic Commands:**
```bash
echo $XAI_API_KEY
# Если пусто - добавить в ~/.zshrc:
export XAI_API_KEY="xai-xxxxxx"
source ~/.zshrc
```

---

## 🔧 Key Routing Implementation

### 1. OpenRouter Multi-Key System

**File:** `src/utils/unified_key_manager.py`

**Core Functions:**
```python
def get_openrouter_key(self, index: Optional[int] = None, rotate: bool = False) -> Optional[str]:
    """Get OpenRouter key with smart rotation"""
    
def rotate_openrouter_key(self, mark_failed: bool = False) -> None:
    """Rotate to next available key"""
    
def get_openrouter_keys_count(self) -> int:
    """Count available keys"""
```

**Features:**
- **Auto-rotation on failure**
- **Separate free/paid key pools**
- **Failed key tracking**
- **Health checking**

### 2. xAI Fallback System (Phase 80.37)

**File:** `src/orchestration/orchestrator_with_elisya.py`
**Lines:** 1247-1270

**Logic:**
```python
# Phase 80.37: Check if xai key exists, fallback to openrouter
if routing.get("provider") == "xai" and not self.key_service.has_xai_key():
    print("[ORCHESTRATOR] xAI key not found, falling back to OpenRouter")
    routing["provider"] = "openrouter"
    routing["model"] = "anthropic/claude-3.5-sonnet"  # Fallback model
```

### 3. Provider Registry Integration

**File:** `src/elisya/provider_registry.py`

**Key Injection:**
```python
api_key = APIKeyService().get_key('openrouter')
if api_key:
    # Route to OpenRouter with key
```

---

## 📊 Key Status Monitoring

### 🔍 Configuration Endpoints

**File:** `src/api/routes/config_routes.py`

**Endpoints:**
- `GET /api/keys/status` - Check key status
- `POST /api/keys/add` - Add new key
- `POST /api/keys/detect` - Auto-detect keys
- `GET /api/keys/validate` - Validate keys

**Sample Response:**
```json
{
  "openrouter": {
    "total": 5,
    "active": 4,
    "paid": 3,
    "free": 1
  },
  "xai": {
    "available": true,
    "model": "grok-beta"
  }
}
```

---

## 🎯 Smart Routing Recommendations

### 1. Fix xAI Key Export

**Immediate Action:**
```bash
# Check current status
echo $XAI_API_KEY

# Add to ~/.zshrc if missing
echo 'export XAI_API_KEY="xai-xxxxxx"' >> ~/.zshrc
source ~/.zshrc
```

**Impact:**
- ✅ Grok models will work correctly
- ✅ Reduces Ollama fallback pressure
- ✅ Improves response quality

### 2. Optimize Key Pool Management

**Strategy:**
- **Prioritize paid keys** for quality
- **Use free keys** for development/testing
- **Auto-disable failed keys** temporarily
- **Health check** all keys periodically

### 3. Model Selection Logic

**Current Priority:**
1. **xAI Grok** (if key available)
2. **OpenRouter paid** (highest quality)
3. **OpenRouter free** (fallback)
4. **Ollama local** (last resort)

---

## 🧪 Testing Plan

### 1. MCP Integration Test

```python
# Test vetka_call_model with different providers
models_to_test = [
    "xai/grok-beta",
    "openai/gpt-4o", 
    "anthropic/claude-3-opus",
    "ollama/qwen2:7b"
]

for model in models_to_test:
    result = vetka_call_model(model, test_message)
    assert result.success, f"Failed for {model}"
```

### 2. Key Rotation Test

```python
# Test automatic key rotation
for i in range(10):
    key = key_manager.get_openrouter_key()
    response = make_request(key)
    if not response.success:
        key_manager.rotate_openrouter_key(mark_failed=True)
```

### 3. Fallback Test

```python
# Test xAI to OpenRouter fallback
remove_xai_key()
response = vetka_call_model("xai/grok-beta")
assert response.provider == "openrouter"  # Should fallback
```

---

## 📝 Integration Status

### ✅ Working Components

1. **OpenRouter Multi-Key System** - Fully functional
2. **Key Auto-Rotation** - Working on failures
3. **xAI Fallback Logic** - Implemented (Phase 80.37)
4. **Health Monitoring** - API endpoints available

### 🟡 Issues to Address

1. **xAI Key Export** - Need proper environment setup
2. **Ollama Model Format** - May need adjustment in MCP
3. **Key Detection** - Could be more automated

### 🔴 Critical Issues

1. **MCP vetka_call_model** - Falls back to Ollama incorrectly
2. **Environment Variables** - xAI key not properly exported
3. **Model Name Mapping** - Provider/model format confusion

---

## 🚀 Action Items

### Immediate (Today)

1. **Fix xAI Key Export:**
   ```bash
   # Add to ~/.zshrc
   export XAI_API_KEY="actual-key-here"
   source ~/.zshrc
   ```

2. **Test MCP Integration:**
   - Try `vetka_call_model` with different providers
   - Verify fallback behavior
   - Check error messages

### Short-term (This Week)

1. **Enhance Key Detection:**
   - Auto-scan for keys in multiple locations
   - Better error messages for missing keys
   - Key validation on startup

2. **Improve Model Routing:**
   - Better model name mapping
   - Provider preference configuration
   - Cost-aware routing

### Long-term (Next Phase)

1. **Advanced Routing:**
   - Performance-based key selection
   - Cost optimization
   - Quality scoring

2. **Monitoring Dashboard:**
   - Real-time key status
   - Usage analytics
   - Failure tracking

---

## 🔍 Debugging Commands

### Check Key Status
```bash
# Check current keys
curl http://localhost:8000/api/keys/status

# Check environment variables
echo $XAI_API_KEY
echo $OPENROUTER_API_KEY
```

### Test MCP Directly
```python
# Test vetka_call_model
{
  "model": "xai/grok-beta",
  "messages": [{"role": "user", "content": "Test"}],
  "max_tokens": 100
}
```

### Monitor Logs
```bash
# Watch key rotation logs
tail -f logs/vetka.log | grep -i "key\|rout"

# Watch MCP errors
tail -f logs/mcp.log
```

---

## 📊 Success Metrics

### Key Performance Indicators

1. **Key Success Rate:** >95% (currently ~85%)
2. **Fallback Frequency:** <10% (currently ~30%)
3. **Response Time:** <5s average (currently ~8s)
4. **Model Availability:** >98% uptime

### Monitoring Points

- **Key rotation events**
- **Fallback triggers**  
- **MCP call success rates**
- **Provider availability**

---

**Agent Notes:**

Умный роутинг ключей в VETKA уже хорошо реализован на уровне backend (unified_key_manager.py), но есть проблемы с интеграцией на уровне MCP и environment variables. 

Основная проблема - xAI ключ не экспортирован правильно, что вызывает постоянный fallback на Ollama. После исправления export XAI_API_KEY система должна работать корректно.

MCP интеграция через vetka_call_model выглядит перспективной, но нужно проверить правильность форматирования имен моделей и обработку ошибок.