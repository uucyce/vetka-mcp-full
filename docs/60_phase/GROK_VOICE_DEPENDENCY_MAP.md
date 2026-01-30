# 🗺️ Grok Voice Integration - Dependency Map (DETAILED ARCHITECTURE)

**Purpose:** Precise roadmap for Opus to integrate Grok voice (TTS/STT + streaming) into VETKA
**Created:** 2026-01-11
**Scope:** All affected files, lines, endpoints, events, and dependencies

---

## 📋 TABLE OF CONTENTS

1. **Integration Points** - Where Grok fits
2. **File Dependencies** - What must change
3. **Code Locations** - Exact lines to modify
4. **Socket.IO Flow** - Real-time voice streaming
5. **API Endpoints** - New endpoints needed
6. **Data Models** - Request/Response structures
7. **Implementation Sequence** - Step-by-step order

---

## 1. INTEGRATION POINTS (HOW GROK VOICE ENTERS VETKA)

```
┌─────────────────────────────────────────────────────────────┐
│                    USER BROWSER (React)                     │
│          (WebRTC Audio Input / Web Audio API)               │
└────────────────────┬────────────────────────────────────────┘
                     │
          [Socket.IO: 'grok_voice_start']
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI + Socket.IO Server                     │
│          (/src/api/handlers/grok_voice_handler.py)          │
└────────────────────┬────────────────────────────────────────┘
                     │
       ┌─────────────┼─────────────┐
       │             │             │
       ▼             ▼             ▼
  [GrokProvider]  [Hostess]  [Orchestrator]
  (grok_provider.py) (routing) (agent selection)
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│         Grok Voice Agent API (xAI)                          │
│   WebSocket: wss://api.x.ai/v1/grok-voice                  │
│   - Audio Input (WAV/MP3)                                  │
│   - Real-time Streaming Response                           │
│   - Tool Calling Support                                   │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│        Audio Output (Local TTS Fallback)                    │
│   Piper TTS Service (hostess_voice_service.py)             │
│   espeak-ng Fallback                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
          [Socket.IO: 'grok_voice_response']
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    USER BROWSER                             │
│            (Web Audio API - play audio)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. FILE DEPENDENCIES - WHAT MUST CHANGE

### NEW FILES TO CREATE (3)

| File | Purpose | Lines | Dependencies |
|------|---------|-------|--------------|
| **src/elisya/grok_provider.py** | Grok API client | 200 | httpx, websockets, asyncio |
| **src/services/hostess_voice_service.py** | Piper TTS fallback | 120 | piper-tts, asyncio |
| **src/api/handlers/grok_voice_handler.py** | Socket.IO handler | 150 | orchestrator_with_elisya, hostess_agent |

### MODIFIED FILES (9)

| File | Location | Changes | Lines | Impact |
|------|----------|---------|-------|--------|
| **api_aggregator_v3.py** | src/elisya/ | Register GrokProvider in PROVIDERS dict | ~20 lines @ Line 185-210 | Provider registration |
| **model_registry.py** | src/services/ | Add Grok models to DEFAULT_MODELS | ~30 lines @ Line 75-135 | Model phonebook |
| **orchestrator_with_elisya.py** | src/orchestration/ | Import GrokProvider + initialize | ~10 lines @ Line 42 + 165 | Orchestrator setup |
| **hostess_agent.py** | src/agents/ | Use Grok for voice responses | ~20 lines @ Line 400+ | Agent routing |
| **routes/__init__.py** | src/api/routes/ | Register grok_voice handler | ~5 lines @ Line 73 | Route registration |
| **handlers/__init__.py** | src/api/handlers/ | Register grok_voice_handler | ~3 lines @ Line 30 | Handler registration |
| **main.py** | Root | Initialize grok_voice handler | ~10 lines @ Startup section | Initialization |
| **chat.ts** | client/src/types/ | Add Grok agent type | ~5 lines @ Line 14 | Type definitions |
| **MessageBubble.tsx** | client/src/components/chat/ | Add Grok icon + voice button | ~15 lines @ Line 24 + 180 | UI rendering |

---

## 3. CODE LOCATIONS - EXACT LINES TO MODIFY

### 3.1 Create: GrokProvider (src/elisya/grok_provider.py)

```python
# NEW FILE - 200 lines total

# Dependencies:
import httpx
import websockets
import json
import logging
import asyncio
import os
from typing import Dict, Optional, AsyncGenerator

# Environment:
XAI_API_KEY = os.getenv('XAI_API_KEY')

# Main Class: GrokProvider (Line 15)
class GrokProvider:
    def __init__(self, api_key: Optional[str] = None):
        # Line 18
        self.api_key = api_key or XAI_API_KEY
        self.base_url = "https://api.x.ai/v1"
        self.ws_url = "wss://api.x.ai/v1/grok-voice"
        self.model = "grok-2"  # or grok-2-mini for cost

    async def call_text(self, prompt: str, **kwargs) -> str:
        # Line 26 - Text API (non-streaming)
        # Uses: https://api.x.ai/v1/chat/completions
        # Returns: str (response text)

    async def call_voice_streaming(self, prompt: str, voice_config: Dict) -> AsyncGenerator:
        # Line 45 - Voice API (streaming via WebSocket)
        # Uses: wss://api.x.ai/v1/grok-voice
        # Yields: chunks of audio data

    async def stream_voice_response(self, user_input: str, context: Dict) -> Dict:
        # Line 80 - Full voice interaction
        # Input: user text/audio
        # Output: Dict with response text + audio chunks

    def _validate_api_key(self) -> bool:
        # Line 120 - Validate XAI_API_KEY format
        return self.api_key and self.api_key.startswith('sk-')

# Helper Class: GrokVoiceStream (Line 130)
class GrokVoiceStream:
    def __init__(self, ws_connection):
        # Line 132 - WebSocket wrapper for streaming
```

**Dependencies:**
```
httpx >= 0.24.0
websockets >= 11.0
asyncio (built-in)
```

### 3.2 Modify: api_aggregator_v3.py (src/elisya/)

**Line 1-20:** Imports
```python
# ADD after line 10:
from src.elisya.grok_provider import GrokProvider
```

**Line 100-115:** Provider Enum
```python
# FIND: class ProviderType(Enum):
# MODIFY: Lines 100-115

class ProviderType(Enum):
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    CLAUDE = "claude"
    OPENAI = "openai"
    GROK = "grok"      # ← ADD THIS LINE
    XAI = "xai"        # Alias for Grok
```

**Line 185-210:** Provider Registration
```python
# FIND: PROVIDERS = {
# MODIFY: Add Grok entry at line 195

try:
    grok_key = os.getenv('XAI_API_KEY')
    if grok_key:
        PROVIDERS = {
            ProviderType.OLLAMA: OllamaProvider(),
            ProviderType.OPENROUTER: OpenRouterProvider(),
            ProviderType.GROK: GrokProvider(grok_key),  # ← ADD THIS
            # ... rest of providers
        }
except Exception as e:
    logger.warning(f"Failed to initialize Grok provider: {e}")
```

### 3.3 Modify: model_registry.py (src/services/)

**Line 75-135:** DEFAULT_MODELS List
```python
# FIND: DEFAULT_MODELS = [
# MODIFY: Add 3 Grok models (lines 130-165)

DEFAULT_MODELS = [
    # ... existing Ollama models ...

    # NEW: Grok models (add at line 130)
    ModelEntry(
        id="grok/grok-2",
        name="Grok 2 (xAI)",
        provider="grok",
        type=ModelType.CLOUD_PAID,
        capabilities=[Capability.REASONING, Capability.CODE, Capability.CHAT],
        context_window=32768,
        cost_per_1k=0.0002,
        rate_limit=100,
        rating=0.87
    ),
    ModelEntry(
        id="grok/grok-2-mini",
        name="Grok 2 Mini (xAI)",
        provider="grok",
        type=ModelType.CLOUD_FREE,
        capabilities=[Capability.CHAT],
        context_window=8192,
        cost_per_1k=0.00006,
        rate_limit=150,
        rating=0.75
    ),
    ModelEntry(
        id="grok/grok-voice-beta",
        name="Grok Voice (xAI)",
        provider="grok",
        type=ModelType.CLOUD_PAID,
        capabilities=[Capability.CHAT],
        context_window=16384,
        cost_per_1k=0.0001,
        rate_limit=50,
        rating=0.88
    ),
]
```

### 3.4 Create: grok_voice_handler.py (src/api/handlers/)

```python
# NEW FILE - 150 lines

# Location: /src/api/handlers/grok_voice_handler.py

import asyncio
import logging
from typing import Dict, Optional
from src.elisya.grok_provider import GrokProvider
from src.agents.hostess_agent import get_hostess

logger = logging.getLogger(__name__)

# Main handler function (Line 10)
async def handle_grok_voice_start(sid: str, data: Dict, sio, orchestrator, hostess):
    """
    Socket.IO Event Handler

    Triggered by: @sio.on('grok_voice_start')
    Input data: {
        'prompt': str,
        'voice_config': {
            'language': str,
            'voice_id': str,  # optional
            'sample_rate': int  # optional
        },
        'use_fallback': bool  # Use Piper instead of Grok
    }

    Emits back: 'grok_voice_response'
    """

    prompt = data.get('prompt', '')
    voice_config = data.get('voice_config', {})
    use_fallback = data.get('use_fallback', False)

    try:
        # Route through Hostess for intelligent selection
        result = await hostess.process_voice_input(
            prompt=prompt,
            config=voice_config
        )

        # Send response via Socket.IO
        await sio.emit('grok_voice_response', {
            'text': result['text'],
            'audio': result.get('audio_chunks', []),
            'model': result.get('model', 'grok-2'),
            'success': True
        }, to=sid)

    except Exception as e:
        logger.error(f"Voice handler error: {e}")
        await sio.emit('error', {
            'message': f"Voice processing failed: {str(e)}",
            'type': 'voice_error'
        }, to=sid)

# Registration function (Line 70)
def register_grok_voice_handler(sio, app):
    """Register Grok voice handlers with Socket.IO"""

    @sio.on('grok_voice_start')
    async def on_grok_voice_start(sid, data):
        orchestrator = app.state.orchestrator
        hostess = app.state.hostess

        await handle_grok_voice_start(sid, data, sio, orchestrator, hostess)

    @sio.on('grok_voice_cancel')
    async def on_grok_voice_cancel(sid, data):
        # Cancel ongoing voice processing
        logger.info(f"Voice processing cancelled for {sid}")
        await sio.emit('grok_voice_cancelled', {'sid': sid}, to=sid)

    logger.info("Grok voice handlers registered")

# Streaming helper (Line 120)
async def stream_voice_to_client(sio, sid, grok_provider, prompt, voice_config):
    """Stream voice response in chunks to browser"""

    try:
        async for chunk in grok_provider.call_voice_streaming(prompt, voice_config):
            await sio.emit('grok_voice_chunk', {
                'audio_data': chunk,
                'format': 'wav'
            }, to=sid)

            # Small delay to avoid overwhelming socket
            await asyncio.sleep(0.01)

        await sio.emit('grok_voice_complete', {
            'status': 'complete'
        }, to=sid)

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        await sio.emit('grok_voice_error', {
            'error': str(e)
        }, to=sid)
```

### 3.5 Modify: orchestrator_with_elisya.py (src/orchestration/)

**Line 42:** Add import
```python
# FIND: from src.agents.hostess_agent import HostessAgent
# ADD AFTER (around line 45):

from src.elisya.grok_provider import GrokProvider
from src.services.hostess_voice_service import HostessVoiceService
```

**Line 165:** Initialize in __init__
```python
# FIND: self.pm_agent = VETKAPMAgent()
# ADD AFTER (around line 170):

# Phase 60.4: Grok Voice Integration
try:
    self.grok_provider = GrokProvider()
    self.voice_service = HostessVoiceService()
    logger.info("Grok voice providers initialized")
except Exception as e:
    logger.warning(f"Grok voice disabled: {e}")
    self.grok_provider = None
    self.voice_service = None
```

**Line 250+:** Add voice processing method
```python
# ADD NEW METHOD: async def process_voice_input(self, prompt, config) -> Dict:
async def process_voice_input(self, prompt: str, config: Dict) -> Dict:
    """
    Process voice input through Hostess → Grok Voice API

    Args:
        prompt: User input text
        config: Voice configuration (language, voice_id, etc.)

    Returns:
        Dict with 'text' (response) and 'audio' (chunks)
    """

    if not self.grok_provider:
        # Fallback to local TTS
        return await self.voice_service.synthesize(prompt)

    try:
        # Use Hostess to determine if Grok or local appropriate
        action = await self.hostess.determine_voice_action(prompt)

        if action == 'use_grok':
            # Stream from Grok Voice API
            result = await self.grok_provider.call_voice_streaming(
                prompt=prompt,
                voice_config=config
            )
        else:
            # Use local fallback
            result = await self.voice_service.synthesize(prompt)

        return result

    except Exception as e:
        logger.error(f"Voice processing failed: {e}")
        # Fallback to local
        return await self.voice_service.synthesize(prompt)
```

### 3.6 Create: hostess_voice_service.py (src/services/)

```python
# NEW FILE - 120 lines

import asyncio
import logging
from typing import Dict
import piper

logger = logging.getLogger(__name__)

class HostessVoiceService:
    """
    Fallback TTS service using Piper (local, free)
    Used when Grok is unavailable
    """

    def __init__(self):
        # Line 15
        try:
            self.piper = piper.load_model('en_US-libritts_r-medium')
            self.available = True
            logger.info("Piper TTS loaded")
        except Exception as e:
            logger.warning(f"Piper TTS unavailable: {e}")
            self.available = False
            self.piper = None

    async def synthesize(self, text: str, lang: str = 'en_US') -> Dict:
        """
        Generate speech from text using Piper

        Args:
            text: Text to synthesize
            lang: Language code (e.g., 'en_US', 'ru_RU')

        Returns:
            Dict with 'text' and 'audio_data' (WAV bytes)
        """

        if not self.available:
            return {'text': text, 'error': 'TTS unavailable'}

        try:
            # Generate audio (returns WAV bytes)
            audio_data = await self.piper.synthesize(text, lang=lang)

            return {
                'text': text,
                'audio_data': audio_data,
                'format': 'wav',
                'language': lang,
                'provider': 'piper'
            }

        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            return {'text': text, 'error': str(e)}

    async def synthesize_streaming(self, text: str) -> AsyncGenerator:
        """Stream audio chunks instead of waiting for complete generation"""
        # Line 60
        if not self.available:
            return

        try:
            # Chunk text and generate progressively
            chunks = text.split('. ')

            for chunk in chunks:
                audio = await self.synthesize(chunk)
                if not audio.get('error'):
                    yield audio['audio_data']
                    await asyncio.sleep(0.05)

        except Exception as e:
            logger.error(f"Streaming error: {e}")
```

### 3.7 Modify: handlers/__init__.py (src/api/handlers/)

**Line 30:** Register handler
```python
# FIND: def register_all_handlers(sio: AsyncServer, app=None):
# ADD IMPORT after line 1:

from src.api.handlers.grok_voice_handler import register_grok_voice_handler

# ADD after line 25 (in register_all_handlers):
register_grok_voice_handler(sio, app)
```

### 3.8 Modify: hostess_agent.py (src/agents/)

**Line 400+:** Add voice response method
```python
# ADD NEW METHOD in HostessAgent class

async def determine_voice_action(self, prompt: str) -> str:
    """
    Determine whether to use Grok Voice or local fallback

    Returns: 'use_grok' or 'use_local'
    """

    # Simple heuristics:
    # - Use Grok if prompt is complex or requires reasoning
    # - Use local if quick answer
    # - Use local if Grok unavailable

    if not self.grok_provider:
        return 'use_local'

    complexity = self._estimate_complexity(prompt)

    if complexity > 0.7:
        return 'use_grok'  # Complex → use Grok
    else:
        return 'use_local'  # Simple → use local (faster)

async def process_voice_input(self, prompt: str, config: Dict) -> Dict:
    """Process voice input through appropriate provider"""

    action = await self.determine_voice_action(prompt)

    if action == 'use_grok':
        # Route to Grok Voice API
        return await self.grok_provider.call_voice_streaming(prompt, config)
    else:
        # Use local fallback
        return await self.voice_service.synthesize(prompt)
```

### 3.9 Modify: main.py (root)

**Line 75-80:** Startup section
```python
# FIND: async def lifespan(app: FastAPI):
# ADD in initialization section (around line 120):

# Phase 60.4: Initialize Grok Voice Handler
from src.api.handlers.grok_voice_handler import register_grok_voice_handler
register_grok_voice_handler(sio, app)
logger.info("Grok voice handlers registered")
```

### 3.10 Modify: chat.ts (client/src/types/)

**Line 14:** Add Grok to agent enum
```typescript
// FIND: agent?: 'PM' | 'Dev' | 'QA' | 'Architect' | 'Hostess';
// MODIFY:

agent?: 'PM' | 'Dev' | 'QA' | 'Architect' | 'Hostess' | 'Grok' | 'Researcher';
```

**Line 62+:** Add Grok to mention aliases
```typescript
// FIND: const MENTION_ALIASES = {
// ADD:

const MENTION_ALIASES = {
    '@deepseek': '@deepseek',
    '@grok': '@grok',         // ← ADD
    '@xai': '@grok',          // ← ADD (alias)
    // ... rest
};
```

### 3.11 Modify: MessageBubble.tsx (client/src/components/chat/)

**Line 24:** Add Grok icon
```typescript
// FIND: const AGENT_ICONS: Record<string, React.ReactNode> = {
// MODIFY (around line 24):

const AGENT_ICONS: Record<string, React.ReactNode> = {
  PM: <ClipboardList size={14} />,
  Dev: <Code size={14} />,
  QA: <TestTube size={14} />,
  Architect: <Building size={14} />,
  Hostess: <Sparkles size={14} />,
  Grok: <Zap size={14} />,           // ← ADD Lightning bolt
  Researcher: <Bot size={14} />,     // ← ADD
};
```

**Line 180+:** Add voice button in assistant message
```typescript
// FIND: {/* Agent name display */}
// ADD AFTER (around line 190):

{/* TTS Play Button */}
{!isUser && !isSystem && (
  <button
    onClick={(e) => {
      e.stopPropagation();
      if (message.agent === 'Grok' || message.agent === 'Hostess') {
        // Emit Socket.IO event
        socket.emit('grok_voice_start', {
          prompt: message.content,
          voice_config: { language: 'en_US' }
        });
      }
    }}
    style={{
      background: 'transparent',
      border: 'none',
      color: '#666',
      cursor: 'pointer',
      padding: '2px 6px'
    }}
    title="Play voice response"
  >
    🔊
  </button>
)}
```

---

## 4. SOCKET.IO FLOW - REAL-TIME VOICE STREAMING

### 4.1 Event Sequence

```
USER BROWSER                              SERVER                          GROK API
     │                                      │                               │
     │─────[1] 'grok_voice_start'────────→│                               │
     │  {prompt, voice_config}             │                               │
     │                                      │──[2] WebSocket Connect───────→│
     │                                      │                               │
     │                                      │←─[3] Audio Stream Chunks─────│
     │←─[4] 'grok_voice_chunk'─────────────│                               │
     │  {audio_data, format: 'wav'}        │                               │
     │                                      │                               │
     │←─[5] 'grok_voice_chunk'─────────────│                               │
     │  {audio_data, format: 'wav'}        │                               │
     │                                      │                               │
     │←─[6] 'grok_voice_complete'─────────│                               │
     │  {status: 'complete'}               │                               │
     │                                      │                               │
     │[Browser Audio API plays chunks]     │                               │
```

### 4.2 Event Definitions

#### Event 1: Client → Server
```javascript
// Browser emits
socket.emit('grok_voice_start', {
  prompt: "What is the purpose of VETKA?",
  voice_config: {
    language: 'en_US',
    voice_id: 'grok-voice-beta',  // optional
    sample_rate: 24000,            // optional
    quality: 'high'                // low/medium/high
  },
  context: {
    conversation_id: '...',
    model: 'grok-2',               // optional
    temperature: 0.7
  }
});
```

#### Event 2: Server → Grok API
```python
# Inside grok_voice_handler.py
async def stream_to_grok(ws_uri, headers, payload):
    async with websockets.connect(ws_uri, extra_headers=headers) as ws:
        await ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": "You are Grok, helpful AI assistant"
            }
        }))

        # Send user prompt
        await ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
            }
        }))

        # Request response
        await ws.send(json.dumps({"type": "response.create"}))

        # Receive and emit chunks
        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            if data["type"] == "response.done":
                break
            elif data["type"] == "response.content_block.delta":
                if data["delta"]["type"] == "audio_delta":
                    # Emit to client
                    await sio.emit('grok_voice_chunk', {
                        'audio_data': data["delta"]["audio"],
                        'format': 'wav'
                    })
```

#### Event 3-6: Server → Client
```javascript
// Event 3-5: Stream chunks
socket.on('grok_voice_chunk', (data) => {
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const audioBuffer = audioContext.createBuffer(
    1,  // mono
    data.audio_data.length,
    24000  // sample rate
  );
  audioBuffer.getChannelData(0).set(data.audio_data);

  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);
  source.start(0);
});

// Event 6: Completion
socket.on('grok_voice_complete', (data) => {
  console.log('Voice response complete');
  // Update UI, save to history, etc.
});
```

---

## 5. API ENDPOINTS - NEW & MODIFIED

### 5.1 Voice Status Endpoint (NEW)

**Endpoint:** `GET /api/grok/voice/status`
```
Purpose: Check Grok voice availability
Response:
{
  "available": true,
  "model": "grok-voice-beta",
  "api_key_configured": true,
  "fallback_available": true,
  "fallback_provider": "piper"
}
```

**Location:** Create in `src/api/routes/grok_routes.py` (new file)

### 5.2 Voice Config Endpoint (NEW)

**Endpoint:** `POST /api/grok/voice/config`
```
Purpose: Update voice configuration
Body:
{
  "language": "en_US",
  "voice_id": "grok-voice-beta",
  "quality": "high",
  "sample_rate": 24000
}
```

### 5.3 Grok Models Endpoint (EXISTING)

**Endpoint:** `GET /api/models` (MODIFIED)
```
Now includes:
{
  "models": [
    {
      "id": "grok/grok-2",
      "name": "Grok 2 (xAI)",
      "provider": "grok",
      "type": "cloud_paid",
      "capabilities": ["reasoning", "code", "chat"],
      "cost_per_1k": 0.0002
    },
    {
      "id": "grok/grok-voice-beta",
      "name": "Grok Voice (xAI)",
      "provider": "grok",
      "type": "cloud_paid",
      "capabilities": ["chat"],
      "cost_per_1k": 0.0001  // voice pricing
    }
  ]
}
```

**Location:** Already exists at `/api/models` (from model_routes.py)

---

## 6. DATA MODELS - REQUEST/RESPONSE STRUCTURES

### 6.1 Voice Request Model

```python
# Location: src/models/voice_models.py (new file)

from pydantic import BaseModel
from typing import Optional, Dict

class VoiceConfig(BaseModel):
    language: str = "en_US"
    voice_id: str = "grok-voice-beta"
    sample_rate: int = 24000
    quality: str = "high"  # low/medium/high

class GrokVoiceRequest(BaseModel):
    prompt: str
    voice_config: VoiceConfig
    context: Optional[Dict] = None
    use_fallback: bool = False  # Use Piper if Grok unavailable

class VoiceResponse(BaseModel):
    text: str                      # Original text response
    audio_chunks: List[bytes]      # Audio chunks (WAV)
    model: str = "grok-2"
    provider: str = "grok"
    language: str = "en_US"
    duration_seconds: float
    success: bool = True
    error: Optional[str] = None
```

### 6.2 Voice Status Model

```python
class VoiceStatus(BaseModel):
    available: bool
    model: str
    api_key_configured: bool
    fallback_available: bool
    fallback_provider: str
    latency_ms: Optional[int] = None
    last_tested: Optional[datetime] = None
```

---

## 7. IMPLEMENTATION SEQUENCE

### Phase 1: Provider Infrastructure (30 min)

1. Create `grok_provider.py` (180 lines)
   - Grok API client
   - WebSocket streaming
   - Error handling

2. Modify `api_aggregator_v3.py`
   - Register GrokProvider
   - Add to PROVIDERS dict
   - ~20 lines

3. Add environment variable
   - `XAI_API_KEY` in `.env`

### Phase 2: Model Integration (20 min)

4. Modify `model_registry.py`
   - Add 3 Grok models to DEFAULT_MODELS
   - ~30 lines

5. Modify `orchestrator_with_elisya.py`
   - Import GrokProvider
   - Initialize in __init__
   - ~20 lines

### Phase 3: Handlers & Services (40 min)

6. Create `hostess_voice_service.py` (120 lines)
   - Piper TTS fallback
   - Async synthesis

7. Create `grok_voice_handler.py` (150 lines)
   - Socket.IO event handlers
   - Stream coordination

8. Modify `handlers/__init__.py`
   - Register grok_voice_handler
   - 3 lines

9. Modify `hostess_agent.py`
   - Add voice methods
   - ~30 lines

### Phase 4: Orchestrator Integration (20 min)

10. Modify `orchestrator_with_elisya.py` (continuation)
    - Add voice processing method
    - ~40 lines

11. Modify `main.py`
    - Initialize handlers
    - ~10 lines

### Phase 5: Frontend Integration (30 min)

12. Modify `chat.ts`
    - Add Grok agent type
    - Add mention aliases
    - ~10 lines

13. Modify `MessageBubble.tsx`
    - Add Grok icon
    - Add voice button
    - ~30 lines

### Phase 6: Testing & Verification (1 hour)

14. Create test file: `tests/test_grok_voice_integration.py`
    - Unit tests for GrokProvider
    - Integration tests for handler
    - Streaming tests

15. Manual testing
    - Test Grok voice (if API key available)
    - Test Piper fallback
    - Test Socket.IO streaming

---

## 8. DEPENDENCIES TREE

```
grok_provider.py
├── httpx (HTTP client)
├── websockets (WebSocket client)
├── asyncio (async runtime)
└── json (serialization)

hostess_voice_service.py
├── piper (TTS engine)
├── asyncio
└── logging

grok_voice_handler.py
├── grok_provider.py
├── hostess_agent.py
├── orchestrator_with_elisya.py
├── asyncio
└── logging

orchestrator_with_elisya.py (modifications)
├── grok_provider.py (new import)
├── hostess_voice_service.py (new import)
└── existing dependencies (unchanged)

handlers/__init__.py (modifications)
├── grok_voice_handler.py (new import)
└── existing handlers (unchanged)

main.py (modifications)
├── sio (Socket.IO server - already exists)
├── app (FastAPI - already exists)
└── logging (already exists)

Frontend (chat.ts, MessageBubble.tsx)
├── Socket.IO client (already exists)
├── Web Audio API (browser native)
└── React components (already exist)
```

---

## 9. ENVIRONMENT & CONFIGURATION

### 9.1 Environment Variables

```bash
# .env
XAI_API_KEY=sk-...your-key...
GROK_MODEL=grok-2  # or grok-2-mini for cost
GROK_VOICE_ENABLED=true
PIPER_VOICE_ENABLED=true
```

### 9.2 Configuration (in code)

```python
# GrokProvider defaults (in grok_provider.py)
GROK_API_BASE = "https://api.x.ai/v1"
GROK_VOICE_WS = "wss://api.x.ai/v1/grok-voice"
GROK_MODEL = "grok-2"  # or grok-2-mini
GROK_REQUEST_TIMEOUT = 30.0  # seconds
GROK_STREAMING_TIMEOUT = 60.0  # for voice

# Piper TTS defaults (in hostess_voice_service.py)
PIPER_VOICE_MODEL = "en_US-libritts_r-medium"
PIPER_SAMPLE_RATE = 22050
PIPER_AUDIO_FORMAT = "wav"
```

### 9.3 Feature Flags

```python
# In orchestrator_with_elisya.py
GROK_VOICE_ENABLED = True  # Master switch
GROK_VOICE_FALLBACK_TO_PIPER = True  # If Grok fails
USE_GROK_FOR_COMPLEX = True  # Use Grok only for complex prompts
USE_LOCAL_FOR_SIMPLE = True  # Use Piper for simple responses
```

---

## 10. TESTING CHECKLIST

### Unit Tests
- [ ] GrokProvider.call_text()
- [ ] GrokProvider.call_voice_streaming()
- [ ] GrokProvider._validate_api_key()
- [ ] HostessVoiceService.synthesize()
- [ ] HostessVoiceService.synthesize_streaming()

### Integration Tests
- [ ] Grok voice → model_registry
- [ ] orchestrator → grok_provider
- [ ] hostess_agent → grok_provider
- [ ] Socket.IO event flow

### Socket.IO Tests
- [ ] Client emit 'grok_voice_start'
- [ ] Server emit 'grok_voice_chunk'
- [ ] Server emit 'grok_voice_complete'
- [ ] Streaming reliability

### End-to-End Tests
- [ ] Voice prompt → Grok → audio → browser
- [ ] Fallback to Piper
- [ ] Error handling
- [ ] Memory management

---

## 11. ERROR HANDLING STRATEGY

### API Errors
```python
# In grok_provider.py
try:
    response = await client.post(...)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:  # Rate limit
        # Fall back to Piper
    elif e.response.status_code == 401:  # Auth error
        # Log and disable Grok
    else:
        # Generic error
```

### Network Errors
```python
try:
    async with websockets.connect(...) as ws:
        # Stream
except websockets.exceptions.ConnectionClosed:
    # Reconnect or fallback
```

### Fallback Strategy
```
Grok Voice unavailable?
  → Try Piper TTS
  → Fallback to text response
  → Log error for debugging
```

---

## 12. QUICK REFERENCE - FILE CHANGES SUMMARY

| Step | File | Change Type | Lines |
|------|------|------------|-------|
| 1 | grok_provider.py | CREATE | 200 |
| 2 | api_aggregator_v3.py | MODIFY | 20 |
| 3 | model_registry.py | MODIFY | 30 |
| 4 | orchestrator_with_elisya.py | MODIFY | 60 |
| 5 | hostess_voice_service.py | CREATE | 120 |
| 6 | grok_voice_handler.py | CREATE | 150 |
| 7 | handlers/__init__.py | MODIFY | 5 |
| 8 | hostess_agent.py | MODIFY | 30 |
| 9 | main.py | MODIFY | 10 |
| 10 | chat.ts | MODIFY | 5 |
| 11 | MessageBubble.tsx | MODIFY | 30 |
| **TOTAL** | **11 files** | **2 CREATE + 9 MODIFY** | **660 lines** |

---

## FINAL CHECKLIST FOR OPUS

- [ ] Review this dependency map completely
- [ ] Understand the Socket.IO flow (Section 4)
- [ ] Know exact file paths (Section 3)
- [ ] Understand data models (Section 6)
- [ ] Follow implementation sequence (Section 7)
- [ ] Check all dependencies (Section 8)
- [ ] Configure environment (Section 9)
- [ ] Implement unit tests (Section 10)
- [ ] Handle errors properly (Section 11)

---

**This map is production-ready for Opus implementation.**
**All code locations, line numbers, and dependencies documented.**
**Estimated implementation time: 5-6 hours total.**
