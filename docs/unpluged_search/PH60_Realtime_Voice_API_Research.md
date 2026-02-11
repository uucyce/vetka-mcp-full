# 🎤 Research: Realtime Voice API Integration for VETKA

## Context

VETKA - это AI-приложение с 3D визуализацией знаний. Мы добавляем голосовой интерфейс.

**Текущая проблема:**
- Сейчас используем Web Speech API (браузер) для STT → текст → отправка в LLM → текст обратно
- Это НЕ настоящий голосовой диалог
- GPT-4o-audio-preview требует аудио вход/выход, текстом не работает
- Нет VAD (Voice Activity Detection) - пользователь должен вручную останавливать запись

**Цель:**
Настоящий голосовой диалог как в ChatGPT Voice или Grok Voice:
- Пользователь говорит → модель слышит аудио напрямую
- Модель отвечает голосом в реальном времени
- Автоматическое определение конца речи (VAD)
- Low-latency (<500ms)

---

## Research Questions

### 1. OpenAI Realtime API
- Как работает `gpt-4o-realtime-preview`?
- WebSocket протокол или HTTP streaming?
- Формат аудио (PCM, opus, mp3)?
- Есть ли встроенный VAD?
- Цены за минуту/токены?
- Можно ли через OpenRouter или только напрямую?

### 2. Google Gemini Live API
- Существует ли Gemini Live/Realtime API?
- Двунаправленный аудио стрим?
- Какие модели поддерживают (gemini-2.0-flash-live)?
- Формат аудио?
- Доступ через API или только через приложение?

### 3. xAI Grok Voice
- Есть ли у Grok голосовой API?
- Как реализован voice в приложении X/Grok?
- Доступен ли для разработчиков?

### 4. Альтернативы
- **ElevenLabs Conversational AI** - realtime voice agents
- **Deepgram** - streaming STT с VAD
- **Hume AI** - эмоциональный голосовой AI
- **Vapi.ai** - voice agent platform

### 5. Архитектура для VETKA
- WebSocket vs WebRTC для аудио?
- Как интегрировать с существующим Socket.IO?
- Client-side: MediaRecorder vs AudioWorklet?
- Fallback для браузеров без поддержки?

---

## Desired Output Format

```markdown
## Provider: [Name]

### API Type
- [ ] REST + Polling
- [ ] WebSocket bidirectional
- [ ] WebRTC
- [ ] Server-Sent Events

### Audio Format
- Input: [format, sample rate, channels]
- Output: [format, sample rate, channels]

### VAD (Voice Activity Detection)
- [ ] Built-in
- [ ] Need external (Silero VAD, etc.)

### Latency
- First byte: ~Xms
- Full response: ~Xms

### Pricing
- Per minute / per token / per request

### Code Example
\`\`\`javascript
// Minimal working example
\`\`\`

### Pros/Cons
+ ...
- ...

### Integration Complexity
⭐⭐⭐⭐⭐ (1-5)
```

---

## Priority

1. **OpenAI Realtime** - most mature, best docs
2. **Gemini Live** - if available, we have keys
3. **Grok Voice** - if API exists
4. **ElevenLabs** - fallback for TTS quality

---

## Technical Stack (for context)

- **Frontend:** React + TypeScript + Vite
- **Backend:** Python FastAPI + Socket.IO
- **Current voice:** Web Speech API (STT) + speechSynthesis (TTS)
- **Models:** OpenRouter (400+ models), direct Gemini, Ollama local

---

## Deadline

Research needed ASAP to decide on architecture for Phase 60.6 (Realtime Voice).

---

*Generated for Grok research by VETKA Phase 60.5*
