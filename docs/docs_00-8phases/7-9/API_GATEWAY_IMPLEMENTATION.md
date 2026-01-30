# 🔧 CRITICAL FIX: Model Router Failover Implementation

## 🎯 THE REAL PROBLEM

**Current Architecture:**
```
main.py
├── Uses ModelRouterV2.select_model() ✅ 
├── Gets model name (e.g., "gemini-pro")
└── ❌ STOPS HERE — never calls the API
    ├── No Gemini API call logic
    ├── No timeout handling
    ├── No fallback on failure
```

**What's Missing:**
1. `src/elisya/model_router_v2.py` → **only selects which model to use**
   - ✅ Has routing logic (task_type → model)
   - ✅ Has health tracking
   - ❌ NO code to actually CALL the model API

2. **No API Gateway** → No code that:
   - Calls Gemini API
   - Calls OpenRouter API
   - Calls Ollama API
   - Handles timeouts
   - Implements fallback

3. **Key Management API partially exists** but:
   - ✅ Registered in main.py
   - ❌ Never used for actual API calls

---

## 🔍 WHERE GEMINI IS BEING CALLED?

Let me search for actual API calls:

**Option 1:** Elisya endpoints (`src/orchestration/elisya_endpoints.py`)  
**Option 2:** AutoGen workflow (`src/orchestration/autogen_extension.py`)  
**Option 3:** EvalAgent (`src/agents/eval_agent.py`)

These are where Gemini/Ollama/OpenRouter actually get invoked.

---

## 📋 WHAT WE NEED TO BUILD

### Step 1: Create API Gateway
**File:** `src/elisya/api_gateway.py` (NEW)

```python
import requests
import time
from typing import Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class APIGateway:
    """Unified API gateway for all LLM providers with automatic failover"""
    
    def __init__(self, model_router_v2, key_management_api):
        self.router = model_router_v2
        self.keys = key_management_api
        self.timeout = 10  # seconds
        
    def call_model(self, task_type: str, prompt: str, 
                   complexity: str = "MEDIUM") -> Dict[str, Any]:
        """
        Universal model call with automatic failover
        
        Usage:
            response = gateway.call_model(
                task_type="dev_coding",
                prompt="Write a Python function...",
                complexity="HIGH"
            )
        
        Returns fallback response if all providers fail
        """
        # Step 1: Select model via router
        model, metadata = self.router.select_model(task_type, complexity)
        models_to_try = [model] + metadata.get('fallback_models', [])
        
        # Step 2: Try each model until success
        for attempt, model_name in enumerate(models_to_try):
            try:
                start = time.time()
                response = self._call_provider(model_name, prompt)
                duration = time.time() - start
                
                # Record success
                self.router.mark_model_success(model_name, duration)
                self.keys.record_success(model_name)
                
                return {
                    'status': 'success',
                    'model': model_name,
                    'response': response,
                    'duration': duration,
                    'attempt': attempt + 1
                }
                
            except (TimeoutError, ConnectionError) as e:
                print(f"❌ {model_name} timeout/connection: {e}")
                self.router.mark_model_error(model_name, str(e))
                self.keys.record_failure(model_name)
                continue
                
            except Exception as e:
                print(f"❌ {model_name} error: {e}")
                self.router.mark_model_error(model_name, str(e))
                self.keys.record_failure(model_name)
                continue
        
        # All providers failed
        return {
            'status': 'error',
            'models_tried': models_to_try,
            'error': 'All providers exhausted',
            'fallback_response': 'System overloaded. Please try again later.'
        }
    
    def _call_provider(self, model: str, prompt: str) -> str:
        """Call specific provider"""
        if model.startswith('ollama:') or model.startswith('ollama/'):
            return self._call_ollama(model, prompt)
        elif 'gemini' in model.lower():
            return self._call_gemini(model, prompt)
        elif 'openrouter' in model.lower() or 'gpt' in model.lower():
            return self._call_openrouter(model, prompt)
        else:
            raise ValueError(f"Unknown model: {model}")
    
    def _call_gemini(self, model: str, prompt: str) -> str:
        """Call Google Gemini API with timeout"""
        api_key = self.keys.get_next_key("gemini")
        if not api_key:
            raise ValueError("No Gemini API keys available")
        
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        
        try:
            response = session.post(
                f"https://generativelanguage.googleapis.com/v1/chat/completions",
                json={"model": model, "prompt": prompt},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=self.timeout  # ← CRITICAL: Prevents hanging
            )
            
            if response.status_code == 429:
                raise Exception("Rate limited - rotating key")
            if response.status_code >= 400:
                raise Exception(f"API error: {response.status_code}")
            
            return response.json().get('text', '')
            
        except requests.Timeout:
            raise TimeoutError(f"Gemini timeout after {self.timeout}s")
        except requests.ConnectionError as e:
            raise ConnectionError(f"Gemini connection failed: {e}")
    
    def _call_openrouter(self, model: str, prompt: str) -> str:
        """Call OpenRouter API"""
        api_key = self.keys.get_next_key("openrouter")
        if not api_key:
            raise ValueError("No OpenRouter keys available")
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}]
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=self.timeout
            )
            
            if response.status_code >= 400:
                raise Exception(f"OpenRouter error: {response.status_code}")
            
            return response.json()['choices'][0]['message']['content']
            
        except requests.Timeout:
            raise TimeoutError(f"OpenRouter timeout after {self.timeout}s")
    
    def _call_ollama(self, model: str, prompt: str) -> str:
        """Call local Ollama API"""
        model_name = model.replace('ollama:', '').replace('ollama/', '')
        
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": model_name, "prompt": prompt, "stream": False},
                timeout=self.timeout
            )
            
            if response.status_code >= 400:
                raise Exception(f"Ollama error: {response.status_code}")
            
            return response.json().get('response', '')
            
        except requests.Timeout:
            raise TimeoutError(f"Ollama timeout after {self.timeout}s")
        except requests.ConnectionError:
            raise ConnectionError("Ollama not running (localhost:11434)")
```

### Step 2: Update main.py
Add to main.py after initializing key_api:

```python
# Initialize API Gateway
api_gateway = None
if key_api and model_router:
    try:
        from src.elisya.api_gateway import APIGateway
        api_gateway = APIGateway(model_router, key_api)
        print("✅ API Gateway initialized with auto-failover")
    except Exception as e:
        print(f"⚠️  API Gateway init failed: {e}")
```

### Step 3: Create Chat Endpoint
Add to main.py:

```python
@app.route("/api/chat", methods=["POST"])
def chat_endpoint():
    """
    Chat endpoint with automatic model failover
    
    Request:
    {
        "message": "Your prompt",
        "task_type": "dev_coding",  # or pm_planning, qa_testing, eval_scoring
        "complexity": "MEDIUM"  # LOW, MEDIUM, HIGH
    }
    """
    if not api_gateway:
        return jsonify({'error': 'API Gateway not available'}), 503
    
    try:
        data = request.json or {}
        message = data.get('message', '')
        task_type = data.get('task_type', 'unknown')
        complexity = data.get('complexity', 'MEDIUM')
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        # Call with automatic failover
        result = api_gateway.call_model(task_type, message, complexity)
        
        if result['status'] == 'error':
            return jsonify(result), 503  # Service unavailable
        
        return jsonify({
            'response': result['response'],
            'model': result['model'],
            'duration': result['duration'],
            'attempt': result['attempt'],
            'timestamp': time.time()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## 🧪 TEST THE FIXES

### Test 1: Normal request (Gemini working)
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is 2+2?",
    "task_type": "dev_coding",
    "complexity": "LOW"
  }'

# Expected: Gemini responds quickly
```

### Test 2: Gemini expired key (should fallback)
```bash
# Manually expire first Gemini key in config
# Then make request again

# Expected: System tries Gemini → timeout → tries OpenRouter → success
```

### Test 3: All providers down (simulate)
```bash
# Kill Ollama: killall ollama
# Kill OpenRouter: curl -X DELETE...
# Make request to Gemini

# Expected: Clear error message, not hanging
```

---

## 📊 INTEGRATION CHECKLIST

- [ ] Create `src/elisya/api_gateway.py` with APIGateway class
- [ ] Add timeout to all API calls (5-10 seconds)
- [ ] Implement fallback logic (try next provider on error)
- [ ] Update main.py to initialize APIGateway
- [ ] Create `/api/chat` endpoint
- [ ] Add metrics logging for each API call
- [ ] Test with intentionally failing providers
- [ ] Update Key Management to rotate keys
- [ ] Add circuit breaker pattern (disable provider after N failures)
- [ ] Document API in `/docs/API.md`

---

## 🎯 RESULT AFTER FIX

**Before:**
```
POST /api/chat → calls Gemini → timeout → ❌ HANGS
```

**After:**
```
POST /api/chat 
  → calls Gemini (timeout=10s)
  → timeout/error
  → tries OpenRouter (timeout=10s)
  → timeout/error
  → tries Ollama (timeout=10s)
  → ✅ SUCCESS (returns response)
  → logs: "Gemini failed (timeout), OpenRouter failed (rate-limit), Ollama succeeded"
```

---

## 💡 PRIORITY

**Absolute Priority 1:** Create API Gateway + implement timeout  
**Priority 2:** Add fallback logic  
**Priority 3:** Update Key Management  
**Priority 4:** Add metrics/logging  

**Time estimate:** 45 minutes  
**Complexity:** Medium (straightforward pattern)

Ready to implement? 🚀
