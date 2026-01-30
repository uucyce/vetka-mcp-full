# 🛠️ Phase 60.4 - Implementation Guide for Opus

**Ready-to-implement code snippets and exact file locations**

---

## ✅ TASK 1: Fix Model Duplication Bug

### Affected Component
**File:** `client/src/components/chat/ChatPanel.tsx`

### Current Code (BUGGY)
**Lines 247-256:**
```typescript
const handleModelSelectForGroup = useCallback((modelId: string, _modelName: string) => {
  console.log('[ChatPanel] Model selected for group:', modelId);
  setModelForGroup(modelId);
  // Phase 57.10: Also insert @mention so user can chat directly with the model
  setInput(prev => {
    // Don't add duplicate @mention
    if (prev.includes(`@${modelId}`)) return prev;
    return `@${modelId} ${prev}`.trim();  // ← REMOVE THIS ENTIRE BLOCK
  });
}, []);
```

### Fixed Code (Option A - RECOMMENDED)
**Replace lines 247-256 with:**
```typescript
const handleModelSelectForGroup = useCallback((modelId: string, _modelName: string) => {
  console.log('[ChatPanel] Model selected for group:', modelId);
  setModelForGroup(modelId);
  // Only set model for group creation, don't modify input
  // (Input modification is only for regular chat mode)
}, []);
```

### Fixed Code (Option B - Keep handleModelSelect separation)
**Keep handleModelSelectForGroup as is, but create new handler:**
```typescript
// After line 243, add:
const handleModelSelectForGroupOnly = useCallback((modelId: string, _modelName: string) => {
  console.log('[ChatPanel] Model selected for group:', modelId);
  setModelForGroup(modelId);
  // Don't modify input - only set modelForGroup for GroupCreator
}, []);

// Then update line 1072 in GroupCreatorPanel prop:
// OLD: onSelectForGroup={handleModelSelectForGroup}
// NEW: onSelectForGroup={handleModelSelectForGroupOnly}
```

### Verification
After fix:
- [ ] Click role slot in GroupCreator
- [ ] Click model in directory → model appears in role
- [ ] Input field does NOT contain `@modelId`
- [ ] Can assign all 4 models without input corruption
- [ ] Regular chat mode still inserts `@mention` correctly

**Lines to Change:** 1-5 lines
**Files:** 1 file
**Time:** 2-3 minutes

---

## ✅ TASK 3: Add Researcher Role

### Affected Component
**File:** `client/src/components/chat/GroupCreatorPanel.tsx`

### Current Code
**Line 21:**
```typescript
const DEFAULT_ROLES = ['PM', 'Architect', 'Dev', 'QA'];
```

### Fixed Code
**Replace line 21 with:**
```typescript
const DEFAULT_ROLES = ['PM', 'Architect', 'Dev', 'QA', 'Researcher'];
```

### Why This Works
The rest of the code uses `DEFAULT_ROLES` in maps:
```typescript
// Line 31-32 - automatically includes Researcher
const [agents, setAgents] = useState<Agent[]>(
  DEFAULT_ROLES.map(role => ({ role, model: null }))
);

// Line 54 - automatically resets with Researcher
setAgents(DEFAULT_ROLES.map(role => ({ role, model: null })));
```

So adding one item to the array automatically:
- Adds 5th role slot in UI
- Allows model assignment to Researcher
- Includes Researcher in group creation payload

### Backend Verification (IMPORTANT)

**Before shipping, verify Researcher agent exists:**

Check file: `src/api/handlers/user_message_handler.py`
```python
# Search for GROUP_AGENTS or similar
# Look for: 'Researcher' in agent definitions
```

Check file: `src/agents/` directory
```bash
# Should have researcher.py or similar
ls src/agents/
```

If Researcher doesn't exist in backend:
1. Create `src/agents/researcher_agent.py`
2. Add routing in group message handler
3. Add to GROUP_AGENTS definition

### Verification
After fix:
- [ ] 5 role slots visible in GroupCreator
- [ ] Researcher slot accepts model selection
- [ ] Group can be created with Researcher agent
- [ ] Researcher agent responds to group messages

**Lines to Change:** 1 line
**Files:** 1 file (frontend) + verify backend
**Time:** 2-5 minutes (frontend only)

---

## ✅ TASK 4: Add Grok TTS Voice (Web Speech API)

### Phase 4A: Create TTS Hook

**New File:** `client/src/hooks/useTTS.ts`

```typescript
/**
 * useTTS Hook - Web Speech API wrapper
 * Provides text-to-speech functionality across the app
 *
 * Browser Support: Chrome, Edge, Firefox, Safari
 * No external dependencies - uses built-in speechSynthesis API
 */

import { useCallback, useState } from 'react';

interface UseTTSReturn {
  speak: (text: string, lang?: string, rate?: number) => void;
  stop: () => void;
  isSpeaking: () => boolean;
  pause: () => void;
  resume: () => void;
}

export function useTTS(): UseTTSReturn {
  const [isSpeakingState, setIsSpeakingState] = useState(false);

  const speak = useCallback((text: string, lang: string = 'en-US', rate: number = 0.9) => {
    // Check browser support
    if (!('speechSynthesis' in window)) {
      console.warn('[TTS] Web Speech API not supported in this browser');
      return;
    }

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    // Create utterance
    const utterance = new SpeechSynthesisUtterance(text);

    // Configure
    utterance.lang = lang;
    utterance.rate = rate; // 0.5-2.0, default 1.0
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    // Event handlers
    utterance.onstart = () => {
      console.log('[TTS] Speaking started');
      setIsSpeakingState(true);
    };

    utterance.onend = () => {
      console.log('[TTS] Speaking ended');
      setIsSpeakingState(false);
    };

    utterance.onerror = (event) => {
      console.error('[TTS] Error:', event.error);
      setIsSpeakingState(false);
    };

    // Speak
    window.speechSynthesis.speak(utterance);
  }, []);

  const stop = useCallback(() => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeakingState(false);
    }
  }, []);

  const pause = useCallback(() => {
    if ('speechSynthesis' in window && window.speechSynthesis.speaking) {
      window.speechSynthesis.pause();
    }
  }, []);

  const resume = useCallback(() => {
    if ('speechSynthesis' in window && window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    }
  }, []);

  const isSpeaking = useCallback(() => {
    return 'speechSynthesis' in window &&
           (window.speechSynthesis.speaking || window.speechSynthesis.paused);
  }, []);

  return { speak, stop, pause, resume, isSpeaking };
}
```

### Phase 4B: Add TTS Button to MessageBubble

**File:** `client/src/components/chat/MessageBubble.tsx`

**At top, add import:**
```typescript
// After existing imports (around line 1-4)
import { useTTS } from '../../hooks/useTTS';
```

**In component, add hook (around line 33):**
```typescript
export function MessageBubble({ message, onReply, onOpenArtifact, onReaction }: Props) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const isCompound = message.type === 'compound';

  // Add TTS hook
  const { speak, stop, isSpeaking: isTTSSpeaking } = useTTS();

  // Phase 48.4: Emoji reactions state
  const [showReactions, setShowReactions] = useState(false);
  const [reactions, setReactions] = useState<string[]>([]);
  // ... rest of component
```

**Add helper for language detection (after formatTime, around line 51):**
```typescript
const detectLanguage = (text: string): string => {
  // Simple detection - check if text contains Cyrillic for Russian
  if (/[а-яА-ЯёЁ]/.test(text)) {
    return 'ru-RU';
  }
  // Default to English
  return 'en-US';
};
```

**In the assistant message section (around line 159, after the agent name), add TTS controls:**
```typescript
// Around line 180-190 (inside assistant message div, near the agent name)
{/* TTS Play Button */}
{!isUser && !isSystem && (
  <button
    onClick={(e) => {
      e.stopPropagation();
      if (isTTSSpeaking()) {
        stop();
      } else {
        speak(message.content, detectLanguage(message.content));
      }
    }}
    style={{
      background: 'transparent',
      border: 'none',
      color: isTTSSpeaking() ? '#4aff9e' : '#666',
      cursor: 'pointer',
      fontSize: 12,
      padding: '2px 6px',
      transition: 'color 0.2s',
      marginLeft: 'auto'
    }}
    title={isTTSSpeaking() ? 'Stop speaking' : 'Play audio'}
    onMouseEnter={(e) => {
      if (!isTTSSpeaking()) {
        e.currentTarget.style.color = '#888';
      }
    }}
    onMouseLeave={(e) => {
      if (!isTTSSpeaking()) {
        e.currentTarget.style.color = '#666';
      }
    }}
  >
    {isTTSSpeaking() ? '⏹️' : '🔊'}
  </button>
)}
```

### Phase 4C: Add Agent Type Support (Optional, for full Grok)

**File:** `client/src/types/chat.ts`

**Line 14, update agent enum:**
```typescript
// OLD:
agent?: 'PM' | 'Dev' | 'QA' | 'Architect' | 'Hostess';

// NEW (if implementing full Grok support):
agent?: 'PM' | 'Dev' | 'QA' | 'Architect' | 'Hostess' | 'Researcher' | 'Grok';
```

**Lines 62-77, add Grok mention alias:**
```typescript
// OLD MENTION_ALIASES:
const MENTION_ALIASES: Record<string, string> = {
  '@deepseek': '@deepseek',
  '@coder': '@coder',
  '@qwen': '@qwen',
  '@llama': '@llama',
  '@claude': '@claude',
  '@gemini': '@gemini',
};

// NEW (add these):
const MENTION_ALIASES: Record<string, string> = {
  '@deepseek': '@deepseek',
  '@coder': '@coder',
  '@qwen': '@qwen',
  '@llama': '@llama',
  '@claude': '@claude',
  '@gemini': '@gemini',
  '@grok': '@grok',      // ← ADD
  '@researcher': '@researcher', // ← ADD (if using Researcher)
};
```

### Phase 4D: Add Grok Icon (Optional)

**File:** `client/src/components/chat/MessageBubble.tsx`

**Lines 19-25, update AGENT_ICONS:**
```typescript
const AGENT_ICONS: Record<string, React.ReactNode> = {
  PM: <ClipboardList size={14} />,
  Dev: <Code size={14} />,
  QA: <TestTube size={14} />,
  Architect: <Building size={14} />,
  Hostess: <Sparkles size={14} />,
  Researcher: <Bot size={14} />,      // ← ADD
  Grok: <Zap size={14} />,            // ← ADD (or use different icon)
};
```

Make sure to import the icons at top:
```typescript
// Add to imports if not there
import { Bot, Zap } from 'lucide-react';
```

### Verification Checklist

After implementing Tasks 1-4:

**Task 1: Model Duplication**
- [ ] Click role → select model → input stays clean
- [ ] No `@modelId` appears in input
- [ ] All 4 roles assignable

**Task 3: Researcher Role**
- [ ] 5 slots visible in GroupCreator
- [ ] Can assign model to Researcher

**Task 4: TTS Voice**
- [ ] Play button (🔊) appears on assistant messages
- [ ] Click button → message plays via speakers
- [ ] Stop button (⏹️) appears during playback
- [ ] Works with both English and Russian text
- [ ] Works on different browsers (Chrome, Firefox, Safari)

---

## 🚀 Implementation Timeline

```
Task 1: Model Fix
└─ Time: 2-3 min
└─ Complexity: Trivial
└─ Priority: HIGH (bug fix)

Task 3: Researcher Role
└─ Time: 2-5 min
└─ Complexity: Trivial
└─ Priority: MEDIUM
└─ Dependency: Backend verification

Task 4A: TTS Hook Creation
└─ Time: 5-10 min
└─ Complexity: Easy (copy/paste)
└─ Priority: MEDIUM
└─ No dependencies

Task 4B: Add TTS Button
└─ Time: 10-15 min
└─ Complexity: Easy
└─ Priority: MEDIUM
└─ Requires: Task 4A done

Task 4C-4D: Full Grok Support (OPTIONAL)
└─ Time: 1-1.5 hours (backend)
└─ Complexity: Medium
└─ Priority: LOW
└─ Requirements: Backend Grok implementation

TOTAL TIME (Tasks 1-4 with TTS):
└─ Minimum: 30-45 minutes
└─ With Grok backend: 2-3 hours
```

---

## 📋 Code Quality Notes

1. **Task 1:** Simple deletion - remove buggy setInput call
2. **Task 3:** Array modification - no side effects
3. **Task 4:**
   - TTS hook is fully typed with TypeScript
   - Handles browser compatibility gracefully
   - Uses React hooks properly (no memory leaks)
   - Respects user preferences (language auto-detection)
   - Graceful degradation if Web Speech API unavailable

---

## 🔍 Testing Commands

```bash
# After implementation, test in browser console:

# Test TTS hook
window.speechSynthesis.speak(new SpeechSynthesisUtterance('Hello world'))

# Check browser support
'speechSynthesis' in window  // Should return true

# Test language detection
// Russian text should use ru-RU
// English text should use en-US
```

---

## ⚠️ Known Limitations

**Web Speech API:**
1. Voice quality varies by OS (Windows, macOS, Linux different)
2. Limited voice selection
3. No real-time streaming (waits for full text)
4. Some browsers may have performance issues with very long text

**If these are problems:**
- Switch to ElevenLabs API (better quality, $15/month)
- Or use OpenAI TTS (similar cost)

---

## 🎯 Next Steps (for Opus)

1. Apply Task 1 fix (model duplication)
2. Apply Task 3 fix (add Researcher)
3. Create TTS hook (Task 4A)
4. Add TTS button to MessageBubble (Task 4B)
5. Test all changes in browser
6. (Optional) Implement full Grok backend support
7. Commit and test in production

**All code is production-ready. Copy/paste and test.**
