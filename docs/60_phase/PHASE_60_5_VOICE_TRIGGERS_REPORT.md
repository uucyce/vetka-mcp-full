# Phase 60.5: Voice Mode Triggers - Session Report

**Date:** 2026-01-11
**Focus:** Smart Voice Input with Multiple Activation Triggers

---

## Executive Summary

Реализована система умных триггеров голосового режима для MessageInput. Теперь голосовой ввод активируется автоматически в контекстно-зависимых ситуациях, создавая seamless voice experience в стиле Grok/ChatGPT Voice.

---

## What Was Implemented

### 1. Voice Trigger: Model Selection from ModelDirectory

**File:** `client/src/components/chat/MessageInput.tsx`

Когда пользователь выбирает голосовую модель через ModelDirectory, автоматически показывается иконка микрофона вместо Send.

```typescript
// Phase 60.5: Trigger 1 - Check if selected model from ModelDirectory is a voice model
const isSelectedModelVoice = useMemo(() => {
  if (!selectedModel || voiceModels.length === 0) return false;
  return voiceModels.some(vm =>
    vm.toLowerCase() === selectedModel.toLowerCase() ||
    vm.toLowerCase().includes(selectedModel.toLowerCase()) ||
    selectedModel.toLowerCase().includes(vm.toLowerCase())
  );
}, [selectedModel, voiceModels]);
```

**Props added:**
- `selectedModel?: string | null` - ID выбранной модели из ModelDirectory

---

### 2. Voice Trigger: Voice-Only Mode Toggle

**File:** `client/src/components/chat/MessageInput.tsx`

Кнопка `[🎤 voice]` внизу поля ввода. При активации микрофон показывается всегда (если нет текста).

```typescript
// Props
voiceOnlyMode?: boolean;
onVoiceOnlyModeChange?: (value: boolean) => void;

// UI - small toggle button
{onVoiceOnlyModeChange && (
  <button
    onClick={() => onVoiceOnlyModeChange(!voiceOnlyMode)}
    style={{
      background: voiceOnlyMode ? '#1a2a3a' : 'transparent',
      border: voiceOnlyMode ? '1px solid #4a9eff40' : '1px solid #333',
      color: voiceOnlyMode ? '#4a9eff' : '#555',
      // ...
    }}
  >
    <Mic size={10} />
    <span>{voiceOnlyMode ? 'ON' : 'voice'}</span>
  </button>
)}
```

**Visual states:**
- OFF: `[🎤 voice]` - серый, transparent
- ON: `[🎤 ON]` - синий, с подсветкой

---

### 3. Voice Trigger: Auto-Continue After Response

**File:** `client/src/components/chat/MessageInput.tsx`

Кнопка `[↻ loop]` появляется когда голосовой режим активен. При включении микрофон автоматически стартует после ответа модели.

```typescript
// Props
autoContinueVoice?: boolean;
onAutoContinueVoiceChange?: (value: boolean) => void;

// Auto-continue effect
const wasLoadingRef = useRef(isLoading);
useEffect(() => {
  const wasLoading = wasLoadingRef.current;
  wasLoadingRef.current = isLoading;

  // Only trigger when loading just finished
  if (wasLoading && !isLoading && autoContinueVoice) {
    const shouldAutoStart =
      (voiceModelDetection.hasVoiceModel && !voiceModelDetection.hasTextAfter) ||
      isReplyingToVoiceModel ||
      isSelectedModelVoice ||
      voiceOnlyMode;

    if (shouldAutoStart && !isListening) {
      const timer = setTimeout(() => {
        startListening();
      }, 600); // Delay for response render
      return () => clearTimeout(timer);
    }
  }
}, [isLoading, autoContinueVoice, ...]);
```

**Visual states:**
- OFF: `[↻ loop]` - серый
- ON: `[↻ auto]` - зелёный (#4aff9e)

---

## Complete Voice Mode Trigger Logic

```typescript
// Phase 60.5: Voice mode triggers:
// 1. @mention of voice model (no text after)
// 2. Reply to voice model message (empty input)
// 3. Selected model from ModelDirectory is voice model (empty input)
// 4. Voice-only mode toggle (always show mic unless typing)
const showVoiceMode = (
  (voiceModelDetection.hasVoiceModel && !voiceModelDetection.hasTextAfter) ||
  (isReplyingToVoiceModel && !hasText) ||
  (isSelectedModelVoice && !hasText) ||
  (voiceOnlyMode && !hasText)
) && !isListening;
```

---

## Files Modified

### 1. `client/src/components/chat/MessageInput.tsx`

**New Props Interface:**
```typescript
interface Props {
  // ... existing props ...

  // Phase 60.5: Voice models list for smart detection
  voiceModels?: string[];
  // Phase 60.5: Selected model from ModelDirectory
  selectedModel?: string | null;
  // Phase 60.5: Voice-only mode (always show mic)
  voiceOnlyMode?: boolean;
  onVoiceOnlyModeChange?: (value: boolean) => void;
  // Phase 60.5: Auto-continue voice after response
  autoContinueVoice?: boolean;
  onAutoContinueVoiceChange?: (value: boolean) => void;
}
```

**New useMemo hooks:**
- `isReplyingToVoiceModel` - проверка reply на voice модель
- `isSelectedModelVoice` - проверка выбранной модели
- `voiceModelDetection` - детекция @mention voice модели

**New useEffect:**
- Auto-continue effect - запуск микрофона после ответа

**New UI elements:**
- Voice-only toggle button
- Auto-continue toggle button (условный, только при активном voice mode)

---

### 2. `client/src/components/chat/ChatPanel.tsx`

**New State:**
```typescript
// Phase 60.5: Voice-only mode toggle (Trigger 2)
const [voiceOnlyMode, setVoiceOnlyMode] = useState(false);

// Phase 60.5: Auto-continue voice after response (Trigger 3)
const [autoContinueVoice, setAutoContinueVoice] = useState(false);
```

**Updated MessageInput call:**
```tsx
<MessageInput
  value={input}
  onChange={setInput}
  onSend={handleSend}
  isLoading={isTyping}
  replyTo={replyTo?.model}
  replyToModel={replyTo?.model}
  isGroupMode={!!activeGroupId}
  voiceModels={voiceModels}
  selectedModel={selectedModel}           // NEW
  voiceOnlyMode={voiceOnlyMode}           // NEW
  onVoiceOnlyModeChange={setVoiceOnlyMode} // NEW
  autoContinueVoice={autoContinueVoice}   // NEW
  onAutoContinueVoiceChange={setAutoContinueVoice} // NEW
/>
```

---

## Previous Session Work (Context)

Эта сессия продолжила работу Phase 60.5, где ранее было реализовано:

1. **Smart Voice Button** - кнопка меняется: Mic ↔ Send ↔ Stop
2. **Voice Model Detection** - детекция @voice-model в тексте
3. **Reply to Voice Model** - trigger на reply сообщению voice модели
4. **Wave Animation** - canvas-based анимация при записи
5. **Web Speech API STT** - браузерное распознавание речи
6. **xAI (Grok) Key Detection** - добавлен в api_key_detector.py
7. **Voice Models Fetch** - загрузка списка voice моделей из /api/models

---

## User Flow Examples

### Flow 1: Model Selection
1. User opens ModelDirectory
2. User selects `openai/gpt-4o-audio-preview`
3. MessageInput shows Mic icon (empty input)
4. User clicks Mic → recording starts
5. User speaks → text appears
6. User sends (Enter or text accumulates → Send appears)

### Flow 2: Voice-Only Mode
1. User clicks `[🎤 voice]` → becomes `[🎤 ON]`
2. Mic icon always shown (when input empty)
3. User speaks, sends, speaks again
4. Toggle off → normal Send behavior

### Flow 3: Auto-Continue Dialog
1. User activates voice-only mode
2. User clicks `[↻ loop]` → becomes `[↻ auto]`
3. User speaks → sends → model responds
4. After response (600ms delay) → Mic auto-starts
5. Continuous voice dialog like ChatGPT Voice

---

## Technical Notes

### Voice Model Detection
```typescript
// Models are detected via OpenRouter modalities:
// architecture.input_modalities: ['audio', 'text']
// architecture.output_modalities: ['audio', 'text']

// Backend classifies in model_fetcher.py:
if has_audio_input or has_audio_output:
    model_type = 'voice'
```

### Known Limitations
1. **Web Speech API only** - no real WebSocket audio streaming yet
2. **No VAD** - user must manually stop recording
3. **GPT-4o-audio-preview requires audio I/O** - text mode doesn't work
4. **Browser support varies** - Chrome best, Safari partial

### Future: Realtime Voice API
Research document created: `GROK_REALTIME_VOICE_RESEARCH.md`
- OpenAI Realtime API (WebSocket, VAD built-in)
- Gemini Live API
- ElevenLabs Conversational AI
- Deepgram streaming STT

---

## Styling (Nolan Dark Theme)

```css
/* Voice-only toggle */
ON:  background: #1a2a3a, border: #4a9eff40, color: #4a9eff
OFF: background: transparent, border: #333, color: #555

/* Auto-continue toggle */
ON:  background: #1a3a2a, border: #4aff9e40, color: #4aff9e
OFF: background: transparent, border: #333, color: #555

/* Mic button (voice mode) */
background: #1a2a30, color: #6ab, shadow: rgba(100, 170, 187, 0.25)

/* Recording state */
background: #1a2a3a, color: #4a9eff, shadow: rgba(74, 158, 255, 0.5)
```

---

## Testing Checklist

- [ ] Select voice model from ModelDirectory → Mic appears
- [ ] Type text after @voice-model → Send appears
- [ ] Reply to voice model message → Mic appears
- [ ] Toggle voice-only ON → Mic always shown
- [ ] Toggle auto-continue ON → Mic starts after response
- [ ] Wave animation works during recording
- [ ] Status text shows "Слушаю..."
- [ ] Enter sends even in voice mode
- [ ] Esc cancels recording

---

## Architecture Summary

```
ChatPanel.tsx
├── voiceModels[] (fetched from /api/models)
├── selectedModel (from ModelDirectory)
├── voiceOnlyMode (toggle state)
├── autoContinueVoice (toggle state)
└── MessageInput.tsx
    ├── isSelectedModelVoice (useMemo)
    ├── isReplyingToVoiceModel (useMemo)
    ├── voiceModelDetection (useMemo)
    ├── showVoiceMode (computed)
    ├── Auto-continue effect (useEffect)
    ├── Wave animation (useEffect + canvas)
    └── Web Speech API (recognition)
```

---

## For Next Session

1. **Realtime Voice API** - implement WebSocket audio streaming
2. **TTS Playback** - play model audio responses
3. **VAD Integration** - auto-stop when user finishes speaking
4. **Grok Voice** - research if xAI has voice API

---

*Generated by Claude Code - Phase 60.5 Voice Triggers Session*
