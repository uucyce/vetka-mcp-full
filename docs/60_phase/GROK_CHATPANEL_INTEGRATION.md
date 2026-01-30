# 🎬 Grok Voice in ChatPanel - Design & Integration (NOLAN'S DARK MINIMALISM)

**Concept:** Batman Nolan (Dark, minimal, functional) - NOT Burton (colorful, Gothic)
**Design System:** Ikea functional minimalism with sliding panels
**Tech Stack:** React + TypeScript + Socket.IO + Web Audio API
**Status:** Architecture for Opus integration into existing ChatPanel

---

## 🎯 DESIGN PHILOSOPHY

### Core Principles
✅ **Minimalist Grayscale** - Black, white, grays only (like Grok's interface)
✅ **Functional Layout** - Every element serves purpose (Ikea principle)
✅ **Sliding Panels** - Expandable/collapsible sections (like VETKA tree)
✅ **Dark Mode Optimized** - VETKA already uses dark theme
✅ **No Colorful Distractions** - Stark, professional, focused

### NOT This
❌ Colorful icons
❌ Emoji decorations
❌ Playful animations
❌ Bright alerts

### YES This
✅ Monochrome controls
✅ Subtle micro-interactions
✅ Solid performance focus
✅ Professional typography

---

## 📐 CHATPANEL ARCHITECTURE (CURRENT)

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`
**Total Lines:** 1170

### Current Structure
```
ChatPanel
├── Header (lines 750-1048)
│   ├── AI-Chat/Team toggle (lines 767-809)
│   ├── History button (lines 812-842)
│   ├── Model Directory button (lines 845-877)
│   ├── Spacer (line 880)
│   ├── Scanner button (lines 883-911)
│   └── Close button (lines 914-928)
│
├── Selected File Indicator (lines 931-956)
├── Selected Model Indicator (lines 958-993)
├── Workflow Progress (line 995)
├── Active Group Indicator (lines 998-1047)
│
├── Split Layout When Scanner Active (lines 1051-1060)
│   └── ScannerPanel (max-height: 40%)
│
├── Group Creator Panel (lines 1062-1081)
│   └── GroupCreatorPanel (max-height: 50%)
│
├── Messages Area (lines 1084-1100)
│   └── MessageList (flex: 1)
│
└── Input Area (lines 1143-1151)
    └── MessageInput
```

### Key State Variables (lines 45-65)
```typescript
const [input, setInput] = useState('');              // Current message
const [selectedModel, setSelectedModel] = useState(); // For @mention
const [activeTab, setActiveTab] = useState<'chat' | 'scanner' | 'group'>();
const [modelForGroup, setModelForGroup] = useState(); // Group creation
const [activeGroupId, setActiveGroupId] = useState();  // Active group
const [currentChatId, setCurrentChatId] = useState();
```

---

## 🎙️ VOICE PANEL - NEW SLIDING PANEL DESIGN

### Design Specification

**Panel Position:** Between header and messages (like ScannerPanel)
**Toggle:** Add voice icon to header (line 845+)
**Height:** 120px when active, 0px when inactive (slide animation)
**Style:** Monochrome, functional

```
┌─────────────────────────────────────────────────┐
│  [Chat] [History] [Models] [Spacer] [Scanner] [X]  │ Header (existing)
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│  [🎙️] Listening... [Model selector ▼]            │ Voice Panel (NEW)
│  [Mic Level ▓▓▓▓▓▓▓░░░] [Stop/Pause]              │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│                                                 │
│  [User message]                                 │ Messages
│  Chat history...                                │
│  [Grok/Hostess response]                        │
│                                                 │
└─────────────────────────────────────────────────┘
│  [Message Input] [Send]                          │ Input (existing)
└─────────────────────────────────────────────────┘
```

### React Component Structure

**New File:** `/client/src/components/chat/VoicePanel.tsx`

```typescript
// Location: client/src/components/chat/VoicePanel.tsx
// NEW FILE - 250 lines

interface VoicePanelProps {
  isOpen: boolean;                    // Slide panel open/close
  selectedModel: string;              // Current model
  onSelectModel: (model: string) => void;  // Model change
  onStart: () => void;                // Start recording
  onStop: () => void;                 // Stop recording
  isListening: boolean;               // Mic active state
  micLevel: number;                   // 0-100 for level indicator
}

export function VoicePanel({
  isOpen,
  selectedModel,
  onSelectModel,
  onStart,
  onStop,
  isListening,
  micLevel
}: VoicePanelProps) {

  return (
    <div style={{
      position: 'relative',
      maxHeight: isOpen ? '120px' : '0px',
      overflow: 'hidden',
      transition: 'max-height 0.3s ease-in-out',  // Smooth slide
      borderBottom: isOpen ? '1px solid #222' : 'none',
      background: '#0a0a0a',
      padding: isOpen ? '12px 16px' : '0px'
    }}>

      {/* Mic Status & Controls (Line 50) */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        marginBottom: 12
      }}>

        {/* Mic Icon + Status */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          minWidth: '120px'
        }}>
          {/* Animated listening indicator */}
          <span style={{
            fontSize: 16,
            opacity: isListening ? 1 : 0.4,
            transition: 'opacity 0.3s'
          }}>
            🎙️
          </span>
          <span style={{
            fontSize: 11,
            color: isListening ? '#888' : '#555',
            fontWeight: 500
          }}>
            {isListening ? 'Listening...' : 'Ready'}
          </span>
        </div>

        {/* Model Selector (Line 90) */}
        <select
          value={selectedModel}
          onChange={(e) => onSelectModel(e.target.value)}
          style={{
            padding: '6px 10px',
            background: '#111',
            border: '1px solid #333',
            borderRadius: 4,
            color: '#888',
            fontSize: 11,
            cursor: 'pointer'
          }}
        >
          <option value="grok-2">Grok 2 (xAI)</option>
          <option value="grok-voice-beta">Grok Voice (xAI)</option>
          <option value="piper-local">Piper (Local)</option>
          <option value="llama3.2:1b">Llama 3.2 1B (Local)</option>
          <option value="qwen2:7b">Qwen 2 (Local)</option>
        </select>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Mic Level Indicator (Line 120) */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          minWidth: '180px'
        }}>
          <span style={{
            fontSize: 9,
            color: '#555',
            textTransform: 'uppercase'
          }}>
            Level
          </span>
          <div style={{
            width: '100px',
            height: '6px',
            background: '#1a1a1a',
            borderRadius: 2,
            overflow: 'hidden',
            border: '1px solid #333'
          }}>
            <div style={{
              width: `${micLevel}%`,
              height: '100%',
              background: '#666',
              transition: 'width 0.1s linear'
            }} />
          </div>
        </div>

        {/* Controls (Line 150) */}
        {isListening ? (
          <button
            onClick={onStop}
            style={{
              padding: '6px 12px',
              background: '#333',
              border: '1px solid #555',
              borderRadius: 4,
              color: '#aaa',
              cursor: 'pointer',
              fontSize: 11,
              fontWeight: 500,
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#444';
              e.currentTarget.style.borderColor = '#666';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#333';
              e.currentTarget.style.borderColor = '#555';
            }}
          >
            ■ Stop
          </button>
        ) : (
          <button
            onClick={onStart}
            style={{
              padding: '6px 12px',
              background: '#222',
              border: '1px solid #444',
              borderRadius: 4,
              color: '#888',
              cursor: 'pointer',
              fontSize: 11,
              fontWeight: 500,
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#333';
              e.currentTarget.style.borderColor = '#555';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#222';
              e.currentTarget.style.borderColor = '#444';
            }}
          >
            ● Mic
          </button>
        )}
      </div>

      {/* Additional Options Row (Line 200) */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        fontSize: 10,
        color: '#555'
      }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
          <input type="checkbox" defaultChecked /> Auto-send when complete
        </label>
        <span>|</span>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
          <input type="checkbox" defaultChecked /> Voice feedback
        </label>
        <span>|</span>
        <button
          style={{
            background: 'transparent',
            border: 'none',
            color: '#555',
            cursor: 'pointer',
            fontSize: 10,
            textDecoration: 'underline'
          }}
        >
          Settings...
        </button>
      </div>

    </div>
  );
}

export default VoicePanel;
```

---

## 🔧 CHATPANEL MODIFICATIONS

### 1. Add Voice Icon to Header (lines 845+)

**Location:** `/client/src/components/chat/ChatPanel.tsx`
**Lines:** Around 845-877 (after Model Directory button)

```typescript
{/* Voice / Microphone Button - NEW */}
{(activeTab === 'chat' || activeGroupId) && (
  <button
    onClick={() => setVoicePanel(voicePanel === 'closed' ? 'open' : 'closed')}
    style={{
      background: voicePanel === 'open' ? '#1a1a1a' : 'transparent',
      border: 'none',
      borderRadius: 4,
      padding: 6,
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'all 0.2s'
    }}
    onMouseEnter={(e) => {
      if (voicePanel !== 'open') {
        (e.currentTarget as HTMLButtonElement).style.background = '#1a1a1a';
      }
    }}
    onMouseLeave={(e) => {
      if (voicePanel !== 'open') {
        (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
      }
    }}
    title="Voice input (Beta)"
  >
    <div style={{
      color: voicePanel === 'open' ? '#fff' : '#555',
      transition: 'color 0.2s'
    }}>
      🎙️
    </div>
  </button>
)}
```

### 2. Add Voice Panel State

**Location:** ChatPanel.tsx lines 45-65
**Add:**

```typescript
// Voice panel state
const [voicePanel, setVoicePanel] = useState<'open' | 'closed'>('closed');
const [isListening, setIsListening] = useState(false);
const [micLevel, setMicLevel] = useState(0);
const [voiceModel, setVoiceModel] = useState('grok-2');

// Use effect for microphone level tracking
useEffect(() => {
  if (!isListening) return;

  // Use Web Audio API to track mic level
  navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const analyser = audioContext.createAnalyser();
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    audioContext.createMediaStreamSource(stream).connect(analyser);

    const updateLevel = () => {
      analyser.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
      setMicLevel(Math.min(100, (average / 255) * 100));

      if (isListening) {
        requestAnimationFrame(updateLevel);
      }
    };

    updateLevel();
  });
}, [isListening]);
```

### 3. Add Voice Panel Component (lines 1050+)

**Location:** Between Scanner Panel and Messages Area

```typescript
{/* Phase 60.4: Voice Panel (Sliding) */}
{activeTab === 'chat' && (
  <VoicePanel
    isOpen={voicePanel === 'open'}
    selectedModel={voiceModel}
    onSelectModel={setVoiceModel}
    onStart={() => setIsListening(true)}
    onStop={() => setIsListening(false)}
    isListening={isListening}
    micLevel={micLevel}
  />
)}
```

---

## 🎤 VOICE INPUT FLOW

### Sequence Diagram

```
User                    Browser                  Server              Model
 │                         │                       │                  │
 │─[1] Click Mic Button──→│                       │                  │
 │                         │─[2] getUserMedia()───→ OS               │
 │                         │←[3] Audio Stream──────│                  │
 │                         │                       │                  │
 │  [Speaking...]          │                       │                  │
 │                         │                       │                  │
 │─[4] Click Stop──────────│                       │                  │
 │                         │                       │                  │
 │                         │─[5] Emit grok_voice_start──→│           │
 │                         │  {prompt, model, voice_config}          │
 │                         │                       │                  │
 │                         │                       │──[6] Stream──────→│
 │                         │                       │  to Grok API     │
 │                         │                       │                  │
 │                         │←[7] grok_voice_chunk─│←[Response]────── │
 │←[8] Play Audio───────────│                       │                  │
 │  via Web Audio API       │                       │                  │
 │                         │                       │                  │
 │                         │←[9] grok_voice_complete────│             │
 │                         │                       │                  │
 │[Message in input field]←[10] Add to MessageInput───│              │
```

### Code Implementation

**In VoicePanel.tsx:**

```typescript
async function handleMicStart() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // Store stream for later
    mediaStreamRef.current = stream;
    mediaRecorderRef.current = new MediaRecorder(stream);

    const audioChunks: Blob[] = [];

    mediaRecorderRef.current.ondataavailable = (event) => {
      audioChunks.push(event.data);
    };

    mediaRecorderRef.current.onstop = async () => {
      // Convert audio to text (if needed)
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });

      // Emit to server
      socket.emit('grok_voice_start', {
        prompt: await transcribeAudio(audioBlob),  // or send raw audio
        model: selectedModel,
        voice_config: {
          language: 'en_US',
          quality: 'high'
        }
      });

      setIsListening(false);
    };

    mediaRecorderRef.current.start();
    setIsListening(true);

  } catch (error) {
    console.error('Microphone access denied:', error);
    alert('Please allow microphone access to use voice input');
  }
}

function handleMicStop() {
  if (mediaRecorderRef.current) {
    mediaRecorderRef.current.stop();

    // Stop all media tracks
    mediaStreamRef.current?.getTracks().forEach(track => track.stop());
  }
  setIsListening(false);
}
```

---

## 🔊 VOICE OUTPUT - MESSAGE DISPLAY

### Voice Button on Messages

**In MessageBubble.tsx (lines 180-200):**

```typescript
{/* Voice Output Button for Grok/Hostess Messages */}
{!isUser && !isSystem && (message.agent === 'Grok' || message.agent === 'Hostess') && (
  <button
    onClick={(e) => {
      e.stopPropagation();

      // Emit voice request
      socket.emit('grok_voice_start', {
        prompt: message.content,
        model: message.model || 'grok-voice-beta',
        voice_config: {
          language: 'en_US'
        }
      });

      // Visual feedback
      e.currentTarget.style.opacity = '0.5';
    }}
    style={{
      background: 'transparent',
      border: 'none',
      color: '#666',
      cursor: 'pointer',
      padding: '2px 6px',
      fontSize: 11,
      transition: 'all 0.2s',
      marginLeft: 'auto'
    }}
    onMouseEnter={(e) => {
      (e.currentTarget as HTMLButtonElement).style.color = '#aaa';
    }}
    onMouseLeave={(e) => {
      (e.currentTarget as HTMLButtonElement).style.color = '#666';
      (e.currentTarget as HTMLButtonElement).style.opacity = '1';
    }}
    title="Play voice response"
  >
    🔊
  </button>
)}
```

---

## 🎨 STYLING SYSTEM (NOLAN'S MINIMALISM)

### Color Palette
```typescript
const THEME = {
  // Grays only
  background: '#0a0a0a',      // Pure black background
  surface: '#111',             // Slightly lighter surface
  border: '#222',              // Border color
  text_primary: '#ccc',        // Main text (light gray)
  text_secondary: '#888',      // Secondary text (medium gray)
  text_tertiary: '#555',       // Tertiary text (dark gray)
  text_disabled: '#333',       // Disabled text (very dark gray)

  // Interactive
  button_bg: '#1a1a1a',        // Button background
  button_hover: '#333',        // Button hover state
  input_bg: '#111',            // Input background
  input_border: '#333',        // Input border

  // Status
  active: '#aaa',              // Active element
  inactive: '#555',            // Inactive element
  accent: '#666'               // Accent (subtle)
};

// All elements use these colors - NO OTHER COLORS
```

### Typography
```typescript
const TYPOGRAPHY = {
  header: {
    fontSize: 13,
    fontWeight: 500,
    color: '#999'
  },
  body: {
    fontSize: 12,
    fontWeight: 400,
    color: '#888'
  },
  small: {
    fontSize: 10,
    fontWeight: 400,
    color: '#555'
  },
  code: {
    fontSize: 11,
    fontFamily: 'monospace',
    color: '#aaa'
  }
};
```

### Animation
```typescript
// Minimal, functional animations only
const ANIMATIONS = {
  slide: 'all 0.3s ease-in-out',
  fade: 'opacity 0.2s ease',
  pulse: 'opacity 0.5s ease-in-out'
};
```

---

## 🛠️ IMPLEMENTATION CHECKLIST

### Phase 1: Voice Panel UI
- [ ] Create `VoicePanel.tsx` (250 lines)
- [ ] Add voice icon to header (ChatPanel.tsx line 845+)
- [ ] Add state variables (ChatPanel.tsx line 45-65)
- [ ] Insert VoicePanel component (ChatPanel.tsx line 1050+)
- [ ] Test panel slide animation

### Phase 2: Microphone Input
- [ ] Implement Web Audio API for mic level tracking
- [ ] Add getUserMedia() permission handling
- [ ] Implement audio buffer collection
- [ ] Add error handling for mic access denied
- [ ] Test microphone input and level display

### Phase 3: Voice Output
- [ ] Add voice button to MessageBubble.tsx
- [ ] Add audio playback via Web Audio API
- [ ] Implement chunk streaming via Socket.IO
- [ ] Add visual feedback (playing indicator)
- [ ] Test voice playback on messages

### Phase 4: Model Selection
- [ ] Add model dropdown in VoicePanel
- [ ] Populate with Grok models + local models
- [ ] Store user preference
- [ ] Pass to backend in voice request
- [ ] Test model switching

### Phase 5: Advanced Features
- [ ] Auto-send checkbox
- [ ] Voice feedback toggle
- [ ] Settings panel (language, quality, voice)
- [ ] Speech-to-text integration (optional)
- [ ] History of voice interactions

### Phase 6: Testing
- [ ] Unit test VoicePanel component
- [ ] Integration test Socket.IO events
- [ ] Test with Grok API (if key available)
- [ ] Test with Piper fallback
- [ ] Test cross-browser compatibility

---

## 📱 RESPONSIVE DESIGN

### Desktop Layout (Current - Unchanged)
```
┌─────────────────────────────────────────────┐
│        Header (360px fixed width)          │
├─────────────────────────────────────────────┤
│ Voice Panel (120px when open)               │
├─────────────────────────────────────────────┤
│ Messages (flex 1)                           │
├─────────────────────────────────────────────┤
│ Input (MessageInput component)              │
└─────────────────────────────────────────────┘
```

### Mobile Layout (If Needed)
```
┌─────────────────────────────┐
│ Compact Header (fit screen) │
├─────────────────────────────┤
│ Voice Panel (stackable)     │
├─────────────────────────────┤
│ Messages                    │
├─────────────────────────────┤
│ Input (full width)          │
└─────────────────────────────┘
```

---

## 🔐 ERROR HANDLING UI

### Microphone Denied
```typescript
<div style={{
  padding: '12px',
  background: '#1a1a1a',
  border: '1px solid #333',
  borderRadius: 4,
  color: '#888',
  fontSize: 11,
  textAlign: 'center'
}}>
  Microphone access denied.
  <button style={{ /* clear button */ }}>
    Try again
  </button>
</div>
```

### Grok Unavailable
```typescript
<div style={{
  padding: '8px',
  background: '#111',
  color: '#666',
  fontSize: 10
}}>
  Grok unavailable - using Piper TTS (local)
</div>
```

---

## 📝 COMPLETE FILE MODIFICATIONS SUMMARY

| File | Location | Change | Lines |
|------|----------|--------|-------|
| **VoicePanel.tsx** | client/src/components/chat/ | CREATE | 250 |
| **ChatPanel.tsx** | client/src/components/chat/ | MODIFY | 80 |
| **MessageBubble.tsx** | client/src/components/chat/ | MODIFY | 30 |
| **chat.ts** | client/src/types/ | MODIFY | 5 |
| **Main grok integration** | Backend (as per dependency map) | MODIFY | 400+ |

---

## 🚀 FOR OPUS: START HERE

1. **Read GROK_VOICE_DEPENDENCY_MAP.md** - Backend architecture
2. **Read THIS FILE** - Frontend ChatPanel integration
3. **Create VoicePanel.tsx** - New voice UI component
4. **Modify ChatPanel.tsx** - Add voice icon + panel
5. **Implement backend** - Following dependency map
6. **Test end-to-end** - Voice input → Grok/local → audio output

---

**Design:** Nolan's functional minimalism (Dark, stark, no distractions)
**Framework:** React + TypeScript
**Interactivity:** Smooth sliding panels, clean micro-interactions
**Accessibility:** Clear status indicators, error messages
**Performance:** Optimized for real-time voice streaming

All code ready for implementation. ChatPanel is designed like Ikea's sliding cabinet - modular, functional, user-friendly.
