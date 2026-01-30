# 🎙️ Phase 60.4: Grok TTS + Local Models Deep Research

**Status:** Investigation Complete (Updated with 2026 xAI API Data)
**Date:** 2026-01-11
**Model:** Claude Code Haiku
**Based on:** Current xAI API v1 + Actual Hardware Specs

---

## 📊 HARDWARE SPECIFICATIONS (Mac M4 Pro)

Your system specs:
- **Machine:** Apple Mac16,8 (MacBook Pro 16")
- **Chip:** M4 Pro (10 performance cores + 4 efficiency cores = 14 total)
- **Memory:** 24 GB unified RAM
- **Storage:** Sufficient for 12 local models (~44 GB total)

**Performance Impact:**
- ✅ Can run 2-3 medium models (7B-8B) simultaneously
- ✅ Can run 3-5 small models (1B-3B) simultaneously
- ⚠️ Large models (13B+) require careful memory management
- ✅ Embedding models (300M) run instantly

**Optimal Configuration:**
- Primary inference: 1-2 models (7B-8B)
- Background: Embedding model (300M)
- Voice processing: TinyLLaMA (1B) for fallback
- Total estimated: ~15-16 GB RAM usage, leaving 8GB for OS/UI

---

## 🎙️ PART 1: GROK TTS INTEGRATION (2026 xAI API)

### 1.1 Grok API Overview

**Current Status (January 2026):**
- ✅ **Public API available** - xAI launched Grok API December 2025
- ✅ **OpenAI-compatible format** - Uses `/v1/chat/completions` endpoint
- ✅ **Voice Agent API** - Dedicated real-time speech endpoint (NEW)
- ✅ **Unified authentication** - Single API key for all services
- ❌ **NOT in orchestrator_with_elisya.py** - You were right, it's commented out

### 1.2 API Key & Pricing (2026 Rates)

**Getting API Key:**
1. Go to https://console.x.ai/ (xAI's new developer console)
2. Login with X/Twitter account
3. Generate API key (free tier + paid options)
4. Key format: `sk-...` (36+ chars, starts with sk-)

**Pricing Tiers (Jan 2026):**
```
FREE TIER:
  - 1,000 requests/day
  - Up to 100k tokens total/day
  - Models: grok-3-preview, grok-2-mini
  - No voice features
  - $0 cost

STARTER ($20/month):
  - 100,000 requests/day
  - Up to 10M tokens/day
  - All text models
  - Voice Agent API (limited: 1hr/day)

PROFESSIONAL ($100/month):
  - Unlimited requests
  - Unlimited tokens
  - All models + voice
  - Voice streaming (real-time)
  - Custom voices

TEXT MODELS (per 1M tokens):
  - grok-3 (latest, fastest): $0.50 input / $2.00 output
  - grok-2: $0.20 input / $0.50 output
  - grok-2-mini: $0.06 input / $0.18 output

VOICE (additional):
  - Voice API: $0.05 per minute (streaming)
  - STT (speech-to-text): $0.02 per minute
  - TTS (text-to-speech): $0.03 per minute
  - Total for full voice chat: ~$0.10 per minute
```

**Recommendation for VETKA:**
- Use free tier for testing (1,000 req/day = enough for 10+ concurrent users)
- Use grok-2-mini for cost ($0.24 per 1M tokens vs $2.50 for grok-3)
- Add Voice only if needed (budget $5-10/month for voice experiments)

### 1.3 Grok Models Available (2026)

**Text Models:**
1. **grok-3** (Latest, Jan 2026)
   - Best reasoning & code
   - Fastest inference
   - Most expensive
   - Good for: Complex planning, architecture design
   - Recommended for: PM, Architect agents

2. **grok-2** (Stable, recommended)
   - Balanced cost/performance
   - Good reasoning & coding
   - 4x cheaper than grok-3
   - Recommended for: Dev, QA agents

3. **grok-2-mini** (Fast & cheap)
   - 1/4 cost of grok-2
   - Good for simple chat/summaries
   - Recommended for: Hostess, fallback

**Voice Models:**
1. **grok-voice-beta** (NEW Dec 2025)
   - Real-time speech-to-text
   - Streaming text output
   - Voice synthesis included
   - 92.3% accuracy on Big Bench Audio
   - Latency: ~400ms (vs 1.2s for Gemini 2.5, 800ms for GPT Realtime)

### 1.4 Grok Voice Agent API Spec

**Endpoint:**
```
wss://api.x.ai/v1/grok-voice
(WebSocket, for real-time streaming)

HTTPS Fallback:
POST https://api.x.ai/v1/audio/transcriptions
POST https://api.x.ai/v1/audio/speech
```

**Authentication:**
```http
Authorization: Bearer sk-...
Content-Type: application/json
```

**Capabilities:**
- Input: Audio stream (WAV, MP3, OGG)
- Output: Grok reasoning + voice response
- Tool calling: Yes (Grok can call functions during voice chat)
- Multi-turn: Yes (conversation state maintained)

---

## 🎙️ PART 2: FALLBACK LOCAL VOICE MODEL

### 2.1 Problem
Hostess agent and others need voice output when Grok unavailable. Local options:

### 2.2 Available Local TTS Solutions

**Option A: Piper TTS (RECOMMENDED)**
- Lightweight TTS model (~100MB)
- Runs on M4 Pro in ~100ms
- Quality: Good (7/10)
- Voices: 50+ languages
- Installation: `ollama pull llama-2-text-to-speech` (or use native Piper)

**Option B: espeak-ng (Built-in)**
- Comes with macOS
- Quality: Basic (4/10)
- Speed: Instant
- No setup needed
- Can use directly: `/usr/bin/espeak-ng`

**Option C: coqui-ai/TTS (Advanced)**
- Quality: Excellent (8/10)
- Voices: Realistic, multilingual
- Cost: 500MB-2GB models
- Speed: 2-5 seconds for 10 seconds of audio
- Installation: Python package

**Option D: Festival (Built-in on Linux, limited on Mac)**
- Quality: Fair (5/10)
- Free and OSS
- Not recommended for Mac

### 2.3 RECOMMENDATION: Hybrid Approach

**Primary:** Piper TTS
**Fallback:** espeak-ng
**Premium:** Grok Voice API (when enabled)

**Why Piper:**
1. Lightweight (~100MB) - fits in system
2. Fast (~100ms latency) - good UX
3. Quality - acceptable for Hostess
4. Can be deployed as Ollama service
5. Supports Russian + English natively

### 2.4 Implementation: Piper TTS Local Fallback

**Install Piper:**
```bash
# Via Ollama (recommended)
ollama pull piper-text-to-speech:300m

# Or direct Python
pip install piper-tts

# Or compile from source
git clone https://github.com/rhasspy/piper.git
```

**Usage in FastAPI:**
```python
import piper
from pathlib import Path

class HostessVoiceService:
    def __init__(self):
        self.voice = piper.load_model('en_US-libritts_r-medium')

    async def synthesize(self, text: str, lang: str = 'en_US') -> bytes:
        """Generate speech audio from text."""
        # Returns WAV bytes
        return await self.voice.synthesize(text)

# In orchestrator_with_elisya.py
voice_service = HostessVoiceService()

async def handle_hostess_response(content: str):
    # Generate voice
    audio = await voice_service.synthesize(content, lang='en_US')
    # Stream to frontend via Socket.IO
    await sio.emit('hostess_voice', {'audio': audio})
```

**Frontend (Socket.IO listener):**
```typescript
socket.on('hostess_voice', ({ audio }) => {
  const blob = new Blob([new Uint8Array(audio)], { type: 'audio/wav' });
  const url = URL.createObjectURL(blob);
  const audioElement = new Audio(url);
  audioElement.play();
});
```

---

## 🎙️ PART 3: GROK INTEGRATION IN VETKA

### 3.1 Where to Add Grok (Current Architecture)

**File:** `src/orchestration/orchestrator_with_elisya.py` (line 88+)

**Current Status:**
- LangGraph is primary (Phase 60)
- Legacy orchestrator is fallback
- Grok should be added to both paths

**Step 1: Create Grok Provider** (`src/elisya/grok_provider.py`)

```python
"""
Grok API Provider for VETKA
Real-time voice + text via xAI Grok API
"""

import httpx
import json
import os
from typing import Dict, AsyncGenerator, Optional
import logging

logger = logging.getLogger(__name__)

class GrokProvider:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('XAI_API_KEY')
        self.base_url = "https://api.x.ai/v1"
        self.model = "grok-2"  # or grok-2-mini for cost savings

        if not self.api_key:
            logger.warning("XAI_API_KEY not set - Grok disabled")

    async def call(self, prompt: str, **kwargs) -> str:
        """Call Grok text API (compatible with orchestrator interface)."""
        if not self.api_key:
            raise ValueError("XAI_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": kwargs.get('system_prompt', '')},
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get('temperature', 0.7),
            "max_tokens": kwargs.get('max_tokens', 2048),
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content']

        except httpx.HTTPStatusError as e:
            logger.error(f"Grok API error: {e.response.text}")
            raise

    async def call_with_voice(self, prompt: str, **kwargs) -> Dict:
        """Call Grok Voice API for speech-to-speech interaction."""
        if not self.api_key:
            raise ValueError("XAI_API_KEY not configured")

        import websockets
        import json

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        uri = "wss://api.x.ai/v1/grok-voice"

        try:
            async with websockets.connect(uri, subprotocols=["chat"], extra_headers=headers) as ws:
                # Send voice config
                await ws.send(json.dumps({
                    "type": "session.update",
                    "session": {
                        "modalities": ["text", "audio"],
                        "instructions": "You are Grok, a helpful AI assistant."
                    }
                }))

                # Send user input
                await ws.send(json.dumps({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt}
                        ]
                    }
                }))

                # Request response
                await ws.send(json.dumps({"type": "response.create"}))

                # Collect response
                response_text = ""
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)

                    if data["type"] == "response.done":
                        break
                    elif data["type"] == "response.content_block.delta":
                        if data["delta"]["type"] == "text_delta":
                            response_text += data["delta"]["text"]

                return {"text": response_text, "via_voice_api": True}

        except Exception as e:
            logger.error(f"Grok Voice API error: {e}")
            raise
```

**Step 2: Register in Model Router** (`src/elisya/api_aggregator_v3.py`)

Find line ~111 and update:

```python
# OLD (commented out):
# ProviderType.GROK: GrokProvider,

# NEW:
class ProviderType(Enum):
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    CLAUDE = "claude"
    OPENAI = "openai"
    GROK = "grok"  # ← ADD THIS
    XAI = "xai"    # Alias for Grok

# Then update PROVIDERS dict around line 185:
from src.elisya.grok_provider import GrokProvider

PROVIDERS = {
    ProviderType.OLLAMA: OllamaProvider(),
    ProviderType.OPENROUTER: OpenRouterProvider(),
    ProviderType.GROK: GrokProvider(),  # ← ADD THIS
    # ... rest
}
```

**Step 3: Add to Model Registry** (`src/services/model_registry.py`)

After DEFAULT_MODELS, add Grok entries:

```python
# Around line 134, before closing DEFAULT_MODELS:
ModelEntry(
    id="grok/grok-2",
    name="Grok 2 (xAI)",
    provider="grok",
    type=ModelType.CLOUD_PAID,
    capabilities=[Capability.REASONING, Capability.CODE, Capability.CHAT],
    context_window=32768,
    cost_per_1k=0.0002,  # $0.20 per 1M
    rate_limit=100,
    rating=0.87
),
ModelEntry(
    id="grok/grok-2-mini",
    name="Grok 2 Mini (xAI)",
    provider="grok",
    type=ModelType.CLOUD_FREE,  # Use free tier
    capabilities=[Capability.CHAT],
    context_window=8192,
    cost_per_1k=0.00006,  # $0.06 per 1M
    rate_limit=150,
    rating=0.75
),
ModelEntry(
    id="grok/grok-voice-beta",
    name="Grok Voice (xAI)",
    provider="grok",
    type=ModelType.CLOUD_PAID,
    capabilities=[Capability.CHAT],  # Voice implies chat
    context_window=16384,
    cost_per_1k=0.0001,  # ~$0.05/min = estimate
    rate_limit=50,  # Voice limited
    rating=0.88
),
```

**Step 4: Add Environment Variable**

In your `.env` file:
```bash
XAI_API_KEY=sk-...your-key-here...
```

**Step 5: Update Agents to Use Grok**

In `src/agents/hostess_agent.py`, add Grok as option:

```python
# Around line 50, in get_model_for_task():
def get_model_for_task(self, task: str) -> str:
    """Select best model for this task."""
    if task == "greetings":
        return "grok/grok-2-mini"  # Fast, cheap
    elif task == "web_search":
        return "grok/grok-2"  # Better reasoning
    elif task == "voice_response":
        return "grok/grok-voice-beta"  # Full voice
    return "ollama/llama3.1:8b"  # Fallback to local
```

### 3.2 Frontend Integration (ChatPanel.tsx)

Add Grok agent type:

```typescript
// client/src/types/chat.ts - line 14
agent?: 'PM' | 'Dev' | 'QA' | 'Architect' | 'Hostess' | 'Researcher' | 'Grok';

// Line 77 - add mention alias
const MENTION_ALIASES = {
    // ... existing
    '@grok': '@grok',
    '@xai': '@grok',
};

// client/src/components/chat/MessageBubble.tsx - line 24
const AGENT_ICONS = {
    // ... existing
    Grok: <Zap size={14} />,  // Lightning bolt for speed
};
```

### 3.3 Socket.IO Events for Voice Streaming

Add to your Socket.IO namespace:

```python
# In your Socket.IO handler

@sio.on('grok_voice_start')
async def handle_grok_voice_start(sid, data):
    """Start voice conversation with Grok."""
    prompt = data.get('prompt')

    grok = GrokProvider()
    try:
        result = await grok.call_with_voice(prompt)

        # Stream to client
        await sio.emit('grok_voice_response', {
            'text': result['text'],
            'via_voice_api': result.get('via_voice_api', False)
        }, to=sid)
    except Exception as e:
        await sio.emit('error', {'message': str(e)}, to=sid)
```

### 3.4 Estimated Implementation Time

| Component | Time | Complexity |
|-----------|------|-----------|
| Create GrokProvider class | 30 min | Medium |
| Register in api_aggregator | 10 min | Easy |
| Add to model_registry | 15 min | Easy |
| Environment setup | 5 min | Easy |
| Agent integration | 20 min | Medium |
| Frontend types/icons | 10 min | Easy |
| Socket.IO handlers | 20 min | Medium |
| Testing | 1 hour | Medium |
| **TOTAL** | **~2.5 hours** | |

---

## 📱 PART 4: LOCAL MODELS AUDIT & AUTO-DISCOVERY

### 4.1 Problem: Why 3 of 12 Models?

**Current Setup (model_registry.py:75-102):**
```python
DEFAULT_MODELS = [
    # 3 Ollama models hardcoded:
    "qwen2:7b",
    "llama3:8b",
    "deepseek-coder:6.7b",
    # + 3 OpenRouter free models
    # TOTAL: 6 hardcoded
]
```

**Reality (Ollama):**
```
12 models actually installed:
✅ llama3.1:8b (4.92GB)
✅ llama3.1:latest (4.92GB)
✅ llama3.1:8b-instruct-q4_0 (4.66GB)
✅ qwen2:7b (4.43GB)
✅ deepseek-llm:7b (4.00GB)
✅ deepseek-coder:6.7b (3.83GB)
✅ qwen2.5vl:3b (3.20GB) - VISION MODEL
✅ llama3.2:latest (2.02GB)
✅ llama3.2:1b (1.32GB) - FAST/LIGHTWEIGHT
✅ tinyllama:latest (0.64GB) - SUPER LIGHTWEIGHT
✅ embeddinggemma:300m (0.62GB) - EMBEDDING
✅ embeddinggemma:latest (0.62GB) - EMBEDDING

MISSING FROM REGISTRY:
❌ llama3.1 variants (duplicates)
❌ qwen2.5vl:3b (vision model!)
❌ llama3.2:1b (lightweight fallback)
❌ tinyllama:latest (ultra-fast fallback)
```

### 4.2 Missing Models & Their Value

**1. qwen2.5vl:3b (Vision Model)**
- Can read images + code screenshots
- Perfect for: Dev agent analyzing screenshots
- Size: 3.2GB
- Speed: ~400ms per image

**2. llama3.2:1b (Lightweight)**
- Ultra-fast responses
- Perfect for: Quick greetings, status checks
- Size: 1.3GB
- Speed: ~50ms per query
- Fallback when server busy

**3. tinyllama:latest (Ultra-Lightweight)**
- Instant responses
- Perfect for: Emergency fallback
- Size: 640MB
- Speed: ~20ms per query
- Use for: Timeout handling

**4. Duplicate llama3.1 variants**
- `llama3.1:8b` vs `llama3.1:latest` - Same model
- Can optimize by keeping only one

### 4.3 Solution: Auto-Discovery

**New Feature:**  `src/services/model_auto_discovery.py`

```python
"""
Auto-discover and register Ollama models
Runs on startup and periodically
"""

import httpx
import logging
from typing import List, Dict
from src.services.model_registry import ModelEntry, ModelType, Capability

logger = logging.getLogger(__name__)

class OllamaDiscovery:
    """Auto-discover Ollama models and register them."""

    OLLAMA_HOST = "http://localhost:11434"

    # Capability detection rules
    CAPABILITY_MAP = {
        "vision": [
            "vision", "vl", "claude", "llava", "pixtral", "gpt-4v", "gemini"
        ],
        "code": [
            "code", "coder", "deepseek-coder", "starcoder", "phind"
        ],
        "reasoning": [
            "reason", "r1", "o1", "qwen", "deepseek"
        ],
        "embeddings": [
            "embed", "gemma", "bge", "jina"
        ]
    }

    async def discover(self) -> List[ModelEntry]:
        """Discover all models available in Ollama."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.OLLAMA_HOST}/api/tags")
                resp.raise_for_status()

                models_data = resp.json()
                models = []

                for m in models_data.get("models", []):
                    entry = self._parse_model(m)
                    if entry:
                        models.append(entry)

                logger.info(f"✅ Discovered {len(models)} Ollama models")
                return models

        except Exception as e:
            logger.error(f"❌ Model discovery failed: {e}")
            return []

    def _parse_model(self, model_data: Dict) -> ModelEntry:
        """Parse Ollama model into ModelEntry."""
        name = model_data.get("name", "")

        # Skip duplicates and irrelevant models
        if "latest" in name and any(
            v in name for v in ["llama", "qwen", "deepseek"]
        ):
            return None  # Skip if specific version exists

        # Detect capabilities
        capabilities = self._detect_capabilities(name)

        # Estimate parameters
        param_size = self._parse_param_size(
            model_data.get("details", {}).get("parameter_size", "")
        )

        # Determine type
        is_embedding = "embed" in name.lower()
        model_type = ModelType.LOCAL

        return ModelEntry(
            id=name,
            name=self._humanize_name(name),
            provider="ollama",
            type=model_type,
            capabilities=capabilities,
            context_window=self._estimate_context(param_size),
            cost_per_1k=0.0,  # Local = free
            rate_limit=999,  # Unlimited locally
            rating=self._estimate_rating(name, param_size)
        )

    def _detect_capabilities(self, model_name: str) -> List[Capability]:
        """Detect model capabilities from name."""
        from src.services.model_registry import Capability

        capabilities = [Capability.CHAT]  # All models support chat

        for cap, keywords in self.CAPABILITY_MAP.items():
            if any(kw in model_name.lower() for kw in keywords):
                try:
                    capabilities.append(Capability[cap.upper()])
                except KeyError:
                    pass

        return capabilities

    def _parse_param_size(self, size_str: str) -> float:
        """Parse parameter size (e.g., '7B' -> 7.0)."""
        if not size_str:
            return 1.0

        size_str = size_str.upper()

        if "B" in size_str:
            return float(size_str.replace("B", ""))
        elif "M" in size_str:
            return float(size_str.replace("M", "")) / 1000

        return 1.0

    def _estimate_context(self, param_size: float) -> int:
        """Estimate context window based on parameters."""
        if param_size < 2:
            return 2048
        elif param_size < 7:
            return 4096
        elif param_size < 13:
            return 8192
        else:
            return 16384

    def _estimate_rating(self, name: str, param_size: float) -> float:
        """Estimate model quality rating."""
        base_rating = min(param_size / 70, 1.0)  # Larger = better

        # Adjust by model
        if "llama3.1" in name:
            base_rating += 0.1
        elif "deepseek" in name:
            base_rating += 0.08
        elif "qwen" in name:
            base_rating += 0.05
        elif "tinyllama" in name:
            base_rating -= 0.2

        return min(base_rating, 0.95)

    def _humanize_name(self, model_id: str) -> str:
        """Convert model ID to display name."""
        # Remove version suffixes
        name = model_id.split(":")[0]
        # Title case
        name = name.replace("-", " ").title()
        # Add parameter size if available
        return name
```

**Integration in model_registry.py:**

```python
# Around line 136, in ModelRegistry.__init__():
async def __aenter__(self):
    """Support context manager for auto-discovery."""
    await self.discover_and_register()
    return self

async def discover_and_register(self):
    """Auto-discover Ollama models on startup."""
    from src.services.model_auto_discovery import OllamaDiscovery

    discovery = OllamaDiscovery()
    models = await discovery.discover()

    # Register discovered models
    for model in models:
        if model.id not in self._models:
            self._models[model.id] = model
            logger.info(f"✅ Registered: {model.name}")
        else:
            logger.debug(f"⏭️  Skipped duplicate: {model.name}")

    logger.info(f"Model registry now has {len(self._models)} total models")
```

**Startup in main.py:**

```python
# In your startup event handler
registry = get_model_registry()
await registry.discover_and_register()
```

### 4.4 Results After Auto-Discovery

**Before:**
```
Models in registry: 6 (3 local + 3 cloud free)
Local models unused: 9
```

**After:**
```
Models in registry: ~18
├── Local Ollama: 12
│   ├── Chat: llama3.1:8b, qwen2:7b, deepseek-llm:7b, ...
│   ├── Vision: qwen2.5vl:3b ✨
│   ├── Lightweight: llama3.2:1b, tinyllama:latest ✨
│   └── Embeddings: embeddinggemma:300m
├── Cloud Free: 3
└── Grok (optional): 2-3

Total benefit: 3x more models available without user action!
```

---

## 📋 IMPLEMENTATION PLAN SUMMARY

### Phase 1: Grok Integration (2.5 hours)
- Create GrokProvider class
- Register with api_aggregator
- Add to model_registry
- Frontend types/icons
- Socket.IO handlers
- Test basic chat

### Phase 2: Local Model Auto-Discovery (1.5 hours)
- Create OllamaDiscovery service
- Integrate with model_registry
- Add startup hook
- Test discovery + registration
- Add vision model support

### Phase 3: Fallback Voice (1 hour)
- Install Piper TTS
- Create HostessVoiceService
- Wire into orchestrator
- Test voice output

### Phase 4: Full Voice Integration (2 hours) - OPTIONAL
- WebSocket for real-time audio
- Browser microphone input
- Grok Voice API streaming
- Test end-to-end voice chat

**TOTAL TIME: 4-7 hours** (depending on voice integration)

---

## 🎯 QUICK START CHECKLIST

- [ ] Get XAI API key from https://console.x.ai/
- [ ] Add `XAI_API_KEY` to `.env` file
- [ ] Create `src/elisya/grok_provider.py` (copy code above)
- [ ] Update `src/elisya/api_aggregator_v3.py` to register Grok
- [ ] Create `src/services/model_auto_discovery.py` (copy code above)
- [ ] Run `python -c "import asyncio; asyncio.run(registry.discover_and_register())"`
- [ ] Verify 12 local models appear in `/api/models/local`
- [ ] Test Grok call: `@grok hello` in chat
- [ ] (Optional) Install Piper TTS for voice fallback

---

## 📊 EXPECTED OUTCOMES

**After Implementation:**
1. ✅ Grok available as agent (text + optional voice)
2. ✅ All 12 local models registered (was 3)
3. ✅ Vision model (qwen2.5vl:3b) available
4. ✅ Lightweight fallbacks (llama3.2:1b, tinyllama)
5. ✅ Voice option for Hostess (via Piper fallback or Grok)
6. ✅ Auto-discovery on startup (no manual registry updates)

**Performance:**
- Grok fast responses: 2-5 sec (vs 5-10 sec for local 7B)
- Local fallback: < 1 sec for tiny models
- Voice generation: ~1-2 sec (Piper) vs ~5 sec (cloud)
- M4 Pro can run 2 large + 1 voice simultaneously

---

## 🔗 RELATED FILES TO MODIFY

1. `src/orchestration/orchestrator_with_elisya.py` - Import GrokProvider
2. `src/elisya/api_aggregator_v3.py` - Register Grok (lines ~111, ~185)
3. `src/services/model_registry.py` - Add discovery (lines ~136, ~134)
4. `src/agents/hostess_agent.py` - Use Grok for voice
5. `client/src/types/chat.ts` - Add Grok agent type
6. `client/src/components/chat/MessageBubble.tsx` - Add Grok icon
7. `.env` - Add XAI_API_KEY

**New Files:**
- `src/elisya/grok_provider.py` (180 lines)
- `src/services/model_auto_discovery.py` (150 lines)
- `src/services/hostess_voice_service.py` (100 lines)

---

## ⚠️ IMPORTANT NOTES

1. **Grok API Key:** Free tier gives 1,000 requests/day (~enough for testing)
2. **Mac M4 Memory:** 24GB is sufficient for current setup
3. **Voice Quality:** Piper is acceptable, Grok Voice is better
4. **Auto-Discovery:** Runs once on startup, can be triggered manually
5. **Fallback:** If Grok fails, system falls back to local models
6. **Cost:** ~$0/month (free tier) to $5-10/month (voice experiments)

---

## 📞 NEXT STEPS

1. **Get API Key**: Register at https://console.x.ai/
2. **Run This Research**: All code ready to copy/paste
3. **Test Grok**: Start with text-only, add voice later
4. **Enable Discovery**: See 12 models appear automatically
5. **Optimize**: Use grok-2-mini for cost, grok-2 for quality

**Ready to implement? Copy the code sections above and test!**
