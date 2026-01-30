# Phase 104: Jarvis Voice Integration

## 🎯 VISION

**Jarvis = Голос Ветки** - отдельный голосовой интерфейс ПОВЕРХ чата.

```
┌─────────────────────────────────────────────────────────────┐
│  [🔍 Search...]  [〰️ JARVIS WAVE 〰️]  [⚙️]                 │  ← Волна вверху
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   3D Tree        │    Group Chat                           │
│                  │    (PM, Dev, QA, Architect...)          │
│                  │                                          │
│                  │    Jarvis НЕ в чате!                    │
│                  │    Jarvis СЛУШАЕТ и ГОВОРИТ             │
│                  │    отдельно от чата                      │
│                  │                                          │
└─────────────────────────────────────────────────────────────┘
```

**Волна Jarvis:**
- Мерцает когда СЛУШАЕТ (реагирует на голос пользователя)
- Мерцает когда ГОВОРИТ (другой цвет)
- Рядом с поиском или в центре наверху

---

## 📊 РЕЗУЛЬТАТЫ ТЕСТОВ TTS

| TTS | Время | RTF | Real-time? | Качество |
|-----|-------|-----|------------|----------|
| **MLX Qwen3 0.6B** | 3-4s | **0.63x** | ✅ ДА | 🔥 Живой голос, эмоции |
| PyTorch Qwen3 | 8-14s | 2-3x | ❌ | 🔥 Живой |
| Edge TTS | 1-3s | ~0.3x | ✅ | Хороший (online) |

**Выбор: MLX Qwen3-TTS** - offline, real-time, живой голос!

---

## 🏗️ АРХИТЕКТУРА

### Backend

```
venv_voice/                    # Изолированный venv для MLX
├── scripts/
│   └── voice_tts_server.py   # FastAPI microservice :5002
│
src/
├── voice/
│   ├── tts_engine.py         # HTTP client к TTS server
│   └── stt_engine.py         # MLX Whisper (работает)
│
├── api/handlers/
│   ├── jarvis_handler.py     # NEW: Jarvis socket events
│   └── voice_router.py       # Existing: STT→LLM→TTS pipeline
│
└── agents/
    └── jarvis_agent.py       # NEW: Hostess → Jarvis upgrade
```

### Frontend

```
client/src/
├── components/
│   └── jarvis/
│       ├── JarvisWave.tsx    # NEW: Волна визуализация
│       └── JarvisButton.tsx  # NEW: Кнопка активации
│
├── hooks/
│   └── useJarvis.ts          # NEW: Jarvis voice state
│
└── App.tsx                   # Добавить JarvisWave в header
```

---

## 🔌 SOCKET EVENTS (Jarvis-specific)

```typescript
// Client → Server
jarvis_listen_start    // Пользователь нажал кнопку/волну
jarvis_audio_chunk     // PCM chunks от микрофона
jarvis_listen_stop     // VAD end / кнопка отпущена

// Server → Client
jarvis_listening       // Jarvis слушает (волна мерцает синим)
jarvis_thinking        // Jarvis думает (волна пульсирует)
jarvis_speaking        // Jarvis говорит (волна мерцает зелёным)
jarvis_audio_chunk     // TTS audio chunks
jarvis_text            // Текст ответа (для отображения)
jarvis_idle            // Jarvis ждёт
```

---

## 📋 TASKS BREAKDOWN

### TASK A: TTS Microservice (Backend)
- [ ] `scripts/voice_tts_server.py` - FastAPI на :5002
- [ ] MLX Qwen3-TTS load + generate endpoint
- [ ] Streaming chunks support
- **Файлы:** scripts/voice_tts_server.py (NEW)
- **Маркер:** MARKER_104.1

### TASK B: TTS Engine Client (Backend)
- [ ] `src/voice/tts_engine.py` - HTTP client
- [ ] Async generator для chunks
- [ ] Fallback на Edge TTS
- **Файлы:** src/voice/tts_engine.py (UPDATE)
- **Маркер:** MARKER_104.2

### TASK C: Jarvis Handler (Backend)
- [ ] `src/api/handlers/jarvis_handler.py` - Socket events
- [ ] State machine: idle → listening → thinking → speaking
- [ ] Integration с STT + TTS
- **Файлы:** jarvis_handler.py (NEW), main.py (wire)
- **Маркер:** MARKER_104.3

### TASK D: Jarvis Wave UI (Frontend)
- [ ] `JarvisWave.tsx` - Canvas/SVG волна
- [ ] Анимация по состоянию (listening/speaking)
- [ ] Цвета: синий (listen), зелёный (speak), серый (idle)
- **Файлы:** JarvisWave.tsx (NEW)
- **Маркер:** MARKER_104.4

### TASK E: Jarvis Hook (Frontend)
- [ ] `useJarvis.ts` - State + Socket events
- [ ] Audio capture (MediaRecorder/AudioWorklet)
- [ ] Audio playback (Web Audio API)
- **Файлы:** useJarvis.ts (NEW)
- **Маркер:** MARKER_104.5

### TASK F: Integration (Full)
- [ ] Добавить JarvisWave в App header
- [ ] Тестирование end-to-end
- [ ] Latency optimization
- **Маркер:** MARKER_104.6

---

## 🚀 MVP ORDER

1. **TASK A** → TTS server работает
2. **TASK B** → Backend может синтезировать
3. **TASK C** → Socket events готовы
4. **TASK D+E** → Frontend UI + hooks
5. **TASK F** → Всё вместе

---

## 📁 DEPENDENCIES

### venv_voice (MLX)
```
mlx==0.30.4
mlx-audio==0.3.1
mlx-lm==0.30.5
soundfile
numpy
fastapi
uvicorn
```

### main venv (VETKA)
```
httpx  # Для HTTP к TTS server
```

---

## ⚠️ NOTES

1. **Jarvis ≠ Chat** - Jarvis говорит отдельно, не пишет в чат
2. **Jarvis может отправлять в чат** - если нужно делегировать агентам
3. **Voice cloning** - позже (Phase 105), нужен sample голоса
4. **Волна визуализация** - см. Grok chat для reference

---

## 🎨 WAVE REFERENCE

Grok показывал классную волну - запросить отдельно когда дойдём до UI.

Варианты:
- Canvas + Web Audio API analyser
- SVG path animation
- Three.js (если хотим 3D волну)
