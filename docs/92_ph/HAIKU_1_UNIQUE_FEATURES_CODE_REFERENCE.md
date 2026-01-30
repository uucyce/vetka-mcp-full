# HAIKU_1: UNIQUE FEATURES - CODE REFERENCE

**Complete code snippets for all unique features in api_aggregator_v3.py**

---

## FEATURE 1: STREAMING WITH ANTI-LOOP DETECTION

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_aggregator_v3.py`
**Lines:** 481-581
**Status:** MUST MIGRATE to provider_registry.py

### Complete Function

```python
async def call_model_stream(
    prompt: str,
    model_name: str = None,
    system_prompt: str = "You are a helpful assistant.",
    **kwargs,
) -> AsyncGenerator[str, None]:
    """
    Phase 46: Streaming tokens from Ollama.
    Phase 90.2: Added anti-loop detection.
    Yields tokens one by one for real-time UI.
    """
    import httpx
    from collections import deque
    import time as time_module

    global OLLAMA_HOST, OLLAMA_DEFAULT_MODEL, HOST_HAS_OLLAMA

    if not HOST_HAS_OLLAMA:
        yield "[ERROR] Streaming requires Ollama"
        return

    target_model = model_name or OLLAMA_DEFAULT_MODEL

    # Validate model exists
    if OLLAMA_AVAILABLE_MODELS and target_model not in OLLAMA_AVAILABLE_MODELS:
        target_model = OLLAMA_DEFAULT_MODEL
        print(f"[STREAM] Model not found, using {target_model}")

    payload = {
        "model": target_model,
        "prompt": f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:",
        "stream": True,
        "options": {"temperature": kwargs.get("temperature", 0.7)},
    }

    print(f"[STREAM] Starting stream from {target_model}")

    # MARKER_90.2_START: Anti-loop detection
    token_history = deque(maxlen=100)  # Track last 100 tokens
    stream_start = time_module.time()
    max_duration = kwargs.get(
        "stream_timeout", 300
    )  # 300 second timeout for unlimited responses
    loop_threshold = 0.5  # 50% overlap triggers loop detection
    # MARKER_90.2_END

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            async with client.stream(
                "POST", f"{OLLAMA_HOST}/api/generate", json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # MARKER_90.2_START: Check timeout
                    if time_module.time() - stream_start > max_duration:
                        print(f"[STREAM] Timeout after {max_duration}s")
                        yield "\n\n[Stream stopped: timeout]"
                        break
                    # MARKER_90.2_END

                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            # MARKER_90.2_START: Loop detection
                            token_history.append(token)

                            # Check for loops every 50 tokens
                            if len(token_history) >= 50:
                                recent_text = "".join(list(token_history)[-50:])
                                prior_text = "".join(list(token_history)[:-50])

                                # Check word-level overlap
                                recent_words = set(recent_text.split())
                                prior_words = set(prior_text.split())

                                if prior_words:  # Avoid division by zero
                                    overlap = len(recent_words & prior_words) / max(
                                        len(recent_words), 1
                                    )

                                    if overlap > loop_threshold:
                                        print(
                                            f"[STREAM] Loop detected (overlap: {overlap:.2f})"
                                        )
                                        yield "\n\n[Stream stopped: repetition detected]"
                                        break
                            # MARKER_90.2_END

                            yield token
                        if data.get("done"):
                            print(f"[STREAM] Complete")
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"[STREAM ERROR] {e}")
            yield f"\n[STREAM ERROR]: {str(e)}"
```

### Imports Required

```python
# At module level (lines 12, 15, 16):
from typing import Dict, List, Optional, Any, AsyncGenerator
import json
import asyncio

# Inside function:
import httpx
from collections import deque
import time as time_module
```

### Global Variables Required

```python
# Lines 34-35:
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_AVAILABLE_MODELS: List[str] = []  # Phase 32.4: Cache of available models
OLLAMA_DEFAULT_MODEL = "qwen2:7b"  # Will be updated if not available
```

---

## FEATURE 2: ENCRYPTION INFRASTRUCTURE

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_aggregator_v3.py`
**Lines:** 21-28, 216-226, 261-267
**Status:** NEEDS IMPLEMENTATION (stubs only)

### Initialization Code (Lines 21-28)

```python
# Encryption
try:
    from cryptography.fernet import Fernet

    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    logger.warning("⚠️  cryptography not installed (pip install cryptography)")
```

### APIAggregator Init with Encryption (Lines 216-226)

```python
class APIAggregator:
    def __init__(self, memory_manager=None):
        self.memory = memory_manager
        self.providers: Dict[ProviderType, APIProvider] = {}

        # Initialize encryption
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key and ENCRYPTION_AVAILABLE:
            encryption_key = Fernet.generate_key()
            logger.warning(
                "⚠️  Generated new encryption key (set ENCRYPTION_KEY in .env)"
            )

        self.cipher = (
            Fernet(encryption_key) if ENCRYPTION_AVAILABLE and encryption_key else None
        )

        logger.debug("APIAggregator initialized")
```

### Encryption/Decryption Methods (Lines 261-267)

```python
    def _encrypt(self, key: str) -> str:
        # Boilerplate...
        return key

    def _decrypt(self, encrypted_key: str) -> str:
        # Boilerplate...
        return encrypted_key
```

### IMPORTANT NOTE

The encryption methods are **STUBS** - they just return the key unchanged:

```python
def _encrypt(self, key: str) -> str:
    if self.cipher:
        return self.cipher.encrypt(key.encode()).decode()
    return key

def _decrypt(self, encrypted_key: str) -> str:
    if self.cipher:
        return self.cipher.decrypt(encrypted_key.encode()).decode()
    return encrypted_key
```

**Status:** Need to replace stubs with real encryption logic above.

---

## FEATURE 3: OLLAMA HEALTH CHECK

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_aggregator_v3.py`
**Lines:** 39-82
**Status:** EXISTS in provider_registry.py but with different approach

### Full Function

```python
def _check_ollama_health() -> bool:
    """Phase 32.4: Check if Ollama is running and get available models."""
    global HOST_HAS_OLLAMA, OLLAMA_AVAILABLE_MODELS, OLLAMA_DEFAULT_MODEL
    try:
        import requests

        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            OLLAMA_AVAILABLE_MODELS = [m["name"] for m in data.get("models", [])]
            HOST_HAS_OLLAMA = True
            # Update default if qwen2:7b not available
            if (
                OLLAMA_AVAILABLE_MODELS
                and OLLAMA_DEFAULT_MODEL not in OLLAMA_AVAILABLE_MODELS
            ):
                # Prefer deepseek or qwen models
                for preferred in ["deepseek-llm:7b", "qwen2.5vl:3b", "llama3.1:8b"]:
                    if preferred in OLLAMA_AVAILABLE_MODELS:
                        OLLAMA_DEFAULT_MODEL = preferred
                        break
                else:
                    OLLAMA_DEFAULT_MODEL = OLLAMA_AVAILABLE_MODELS[0]
            print(
                f"✅ Ollama health check: {len(OLLAMA_AVAILABLE_MODELS)} models available"
            )
            print(f"   Default model: {OLLAMA_DEFAULT_MODEL}")
            return True
    except Exception as e:
        print(f"⚠️  Ollama health check failed: {e}")
        HOST_HAS_OLLAMA = False
    return False


# Called at module load:
try:
    # Phase 32.4: Newer Ollama versions use OLLAMA_HOST env var, not set_server_host()
    # The health check already uses OLLAMA_HOST via requests
    os.environ.setdefault("OLLAMA_HOST", OLLAMA_HOST)
    logger.debug(f"Ollama host set to: {OLLAMA_HOST}")
    _check_ollama_health()  # Phase 32.4: Run health check on module load
except Exception as e:
    logger.warning(f"Failed to initialize Ollama: {e}")
    HOST_HAS_OLLAMA = False
```

### Global Variables

```python
HOST_HAS_OLLAMA = False  # Phase 32.4: Start false, set true after health check
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_AVAILABLE_MODELS: List[str] = []  # Phase 32.4: Cache of available models
OLLAMA_DEFAULT_MODEL = "qwen2:7b"  # Will be updated if not available
```

### Comparison with provider_registry.py

provider_registry.py has a similar method (lines 449-470) but:
- Instance method instead of module-level function
- Doesn't have smart model preference logic
- Doesn't update default model selection

**Recommendation:** Enhance provider_registry's implementation with the smart selection logic.

---

## FEATURE 4: OPENROUTER TO OLLAMA MODEL MAPPING

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_aggregator_v3.py`
**Lines:** 334-347, 396, 450-452
**Status:** MUST MIGRATE to provider_registry.py

### Mapping Definition (Lines 334-347)

```python
# Phase 27.15: Map OpenRouter models to local Ollama equivalents for tool support
OPENROUTER_TO_OLLAMA = {
    "deepseek/deepseek-chat": "deepseek-llm:7b",
    "deepseek/deepseek-coder": "deepseek-llm:7b",
    "meta-llama/llama-3.1-8b-instruct": "llama3.1:8b",
    "anthropic/claude-3-haiku": globals().get(
        "OLLAMA_DEFAULT_MODEL", "deepseek-llm:7b"
    ),
    "anthropic/claude-3.5-sonnet": globals().get(
        "OLLAMA_DEFAULT_MODEL", "deepseek-llm:7b"
    ),
    "qwen2:7b": globals().get(
        "OLLAMA_DEFAULT_MODEL", "deepseek-llm:7b"
    ),  # Phase 32.4: Map if not available
}
```

### Usage 1: Tool Calling (Lines 394-399)

```python
# Phase 27.15: For tool-enabled calls with OpenRouter models, use Ollama
if tools and globals().get("HOST_HAS_OLLAMA") and not is_direct_api_model:
    # Map OpenRouter model to Ollama equivalent
    ollama_model = OPENROUTER_TO_OLLAMA.get(model_name, model_name)
    if is_openrouter_model:
        print(f"[OLLAMA] Tool call: mapping {model_name} → {ollama_model}")
        model_name = ollama_model
```

### Usage 2: Fallback (Lines 448-454)

```python
# 2. Try Ollama (Local)
if globals().get("HOST_HAS_OLLAMA"):
    # Map OpenRouter model to Ollama if needed
    if is_openrouter_model:
        ollama_model = OPENROUTER_TO_OLLAMA.get(
            model_name, globals().get("OLLAMA_DEFAULT_MODEL", "deepseek-llm:7b")
        )
        print(f"[OLLAMA] Fallback: mapping {model_name} → {ollama_model}")
        model_name = ollama_model
```

### Rationale

**Why this is needed:**
- OpenRouter has limited tool calling support
- Local Ollama models support tools better
- Map remote models to local equivalents for tool-enabled calls
- Enables function calling that would otherwise fail

---

## FEATURE 5: TIMING INSTRUMENTATION

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_aggregator_v3.py`
**Lines:** 17, 298, 412, 428, 440, 462
**Status:** ALREADY COMPLETE in both files

### Import (Line 17)

```python
import time  # Phase 32.4: Timing for LLM calls
```

### Usage in call_model() (Lines 298-462)

```python
async def call_model(...) -> Any:
    call_start = time.time()  # Line 298

    # ... model selection logic ...

    # Phase 32.4: Use dynamic default model from health check
    if not model_name:
        model_name = globals().get("OLLAMA_DEFAULT_MODEL", "deepseek-llm:7b")

    # ... tool calling logic ...

    # 1. Try OpenRouter (API) for non-tool calls
    if is_openrouter_model and call_openrouter and OPENROUTER_API_KEY:
        try:
            print(f"[API] OpenRouter called for {model_name}")
            result = await call_openrouter(prompt, model_name)
            duration = time.time() - call_start  # Line 440
            print(f"[API] ✅ OpenRouter completed in {duration:.1f}s")
            return {"message": {"content": result}}
        except Exception as e:
            print(f"[API] OpenRouter failed: {e}, falling back to Ollama")

    # 2. Try Ollama (Local)
    if globals().get("HOST_HAS_OLLAMA"):
        try:
            params = {"model": model_name, "messages": messages, "stream": False}
            print(f"[OLLAMA] Calling {model_name}...")
            # Phase 32.4: Run sync ollama.chat in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _ollama_chat_sync, params)
            duration = time.time() - call_start  # Line 462
            print(f"[OLLAMA] ✅ Call completed in {duration:.1f}s")
            return response
        except Exception as e:
            print(f"[API] Ollama failed: {e}")
            return {"message": {"content": f"[OLLAMA ERROR] Call failed: {e}"}}
```

### Usage in call_model_stream() (Lines 520, 537)

```python
async def call_model_stream(...) -> AsyncGenerator[str, None]:
    # ...
    stream_start = time_module.time()  # Line 520
    max_duration = kwargs.get("stream_timeout", 300)

    # ...

    # MARKER_90.2_START: Check timeout
    if time_module.time() - stream_start > max_duration:  # Line 537
        print(f"[STREAM] Timeout after {max_duration}s")
        yield "\n\n[Stream stopped: timeout]"
        break
    # MARKER_90.2_END
```

---

## FEATURE 6: DIRECT API CALLS (PHASE 80.9)

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/elisya/api_aggregator_v3.py`
**Lines:** 362-391
**Status:** EXISTS in both files (api_gateway.py has versions)

### Provider Detection (Lines 313-331)

```python
# Phase 27.15: Detect provider from model name
# Phase 80.9: Better provider detection for direct API calls
is_openai_model = model_name.startswith("openai/") or model_name.startswith("gpt-")
is_anthropic_model = model_name.startswith("anthropic/") or model_name.startswith(
    "claude-"
)
is_google_model = model_name.startswith("google/") or model_name.startswith(
    "gemini"
)
is_direct_api_model = is_openai_model or is_anthropic_model or is_google_model
is_openrouter_model = (
    "/" in model_name
    and not model_name.startswith("ollama")
    and not is_direct_api_model
)
is_ollama_model = (
    ":" in model_name
    or model_name.startswith("ollama")
    or (not "/" in model_name and not is_direct_api_model)
)
```

### Direct API Calls (Lines 362-391)

```python
# Phase 80.9: Direct API calls for OpenAI/Anthropic/Google models (they support tools natively)
if is_direct_api_model:
    print(
        f"[API] Direct API call for {model_name} (tools: {len(tools) if tools else 0})"
    )
    try:
        if is_openai_model:
            # Call OpenAI directly
            from src.elisya.api_gateway import call_openai_direct

            result = await call_openai_direct(messages, model_name, tools)
            return result
        elif is_anthropic_model:
            # Call Anthropic directly
            from src.elisya.api_gateway import call_anthropic_direct

            result = await call_anthropic_direct(messages, model_name, tools)
            return result
        elif is_google_model:
            # Call Google directly
            from src.elisya.api_gateway import call_google_direct

            result = await call_google_direct(messages, model_name, tools)
            return result
    except ImportError as ie:
        print(
            f"[API] Direct API not available: {ie}, falling back to OpenRouter/Ollama"
        )
    except Exception as e:
        print(f"[API] Direct API call failed: {e}, falling back")
```

---

## MIGRATION CHECKLIST

When implementing these features in provider_registry.py:

### Streaming (CRITICAL)
- [ ] Add `call_model_stream()` as module-level function
- [ ] Import `httpx`, `deque`, keep `time` import
- [ ] Copy exact anti-loop detection logic
- [ ] Test with VETKA UI
- [ ] Verify MARKER_90.2 blocks preserved

### Anti-Loop Detection (CRITICAL)
- [ ] Copy lines 518-570 exactly
- [ ] Maintain MARKER_90.2 comments
- [ ] Test loop detection with repetitive model
- [ ] Test timeout handling
- [ ] Verify word overlap calculation

### Encryption (HIGH)
- [ ] Decide: Fernet or secrets manager?
- [ ] If Fernet: implement real _encrypt/_decrypt
- [ ] If secrets: refactor APIKeyService
- [ ] Add comprehensive tests
- [ ] Document key rotation strategy

### OpenRouter→Ollama Mapping (MEDIUM)
- [ ] Add OPENROUTER_TO_OLLAMA dict
- [ ] Update call_model_v2() with mapping logic
- [ ] Test tool calling with OR models
- [ ] Add fallback when model not in mapping

### Ollama Health Check (LOW)
- [ ] Optional: enhance OllamaProvider._check_health() with smart selection
- [ ] Or keep as-is if current works

---

**Reference Document**
Generated: 2026-01-25
Auditor: Claude Haiku 4.5
