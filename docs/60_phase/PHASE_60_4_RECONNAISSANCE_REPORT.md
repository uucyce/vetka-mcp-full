# 🔍 Phase 60.4: UI Fixes + Grok Voice - Reconnaissance Report

**Model:** Claude Code Haiku
**Date:** 2026-01-11
**Status:** Complete ✅

---

## 🎯 Executive Summary

Four cosmetic/feature tasks investigated with precise code locations identified. Three tasks are straightforward fixes (5-30 min each). One task (Grok TTS) requires architectural decisions (2-3 hours total).

| Task | Status | Complexity | Time | Priority |
|------|--------|-----------|------|----------|
| Task 1: Model duplication in input | FOUND | Easy | 2-3 min | HIGH |
| Task 2: Cursor "not-allowed" bug | ANALYZED | Easy/NA | 0 min | LOW |
| Task 3: Add Researcher role | FOUND | Easy | 2-5 min | MEDIUM |
| Task 4: Grok TTS voice | MAPPED | Medium | 2-3 hrs | MEDIUM |

---

## 📋 TASK 1: Дублирование модели в input при выборе роли

### Problem Description
When user selects a model for a role in Group Creator (PM, Architect, Dev, QA), the model name gets added to the message input field. This is undesired behavior - the model should ONLY be assigned to the role.

**Expected:** Click model → assign to role ✅
**Actual:** Click model → assign to role ✅ + add `@modelId` to input ❌

### Root Cause Found
**Primary File:** `client/src/components/chat/ChatPanel.tsx`

**Lines 247-256 - handleModelSelectForGroup callback:**
```typescript
const handleModelSelectForGroup = useCallback((modelId: string, _modelName: string) => {
  console.log('[ChatPanel] Model selected for group:', modelId);
  setModelForGroup(modelId);
  // Phase 57.10: Also insert @mention so user can chat directly with the model
  setInput(prev => {
    // Don't add duplicate @mention
    if (prev.includes(`@${modelId}`)) return prev;
    return `@${modelId} ${prev}`.trim();  // ← LINE 254: ADDS TO INPUT
  });
}, []);
```

### Code Flow Analysis

1. **GroupCreatorPanel.tsx (lines 158-161)** - User clicks role slot
```typescript
{agents.map((agent, index) => (
  <div
    key={index}
    onClick={() => setActiveSlot(index)}  // ← Marks slot as active
```

2. **ModelDirectory.tsx (lines 427-433)** - User clicks model in directory
```typescript
onClick={() => {
  if (isGroupMode && onSelectForGroup) {
    onSelectForGroup(model.id, model.name);  // ← Calls handleModelSelectForGroup
  } else {
    handleSelect(model);
  }
}}
```

3. **ChatPanel.tsx (lines 247-256)** - handleModelSelectForGroup executes
```typescript
const handleModelSelectForGroup = useCallback((modelId: string, _modelName: string) => {
  setModelForGroup(modelId);  // ← Sets state for GroupCreator
  setInput(prev => `@${modelId} ${prev}`.trim());  // ← PROBLEM: Also modifies input
}, []);
```

4. **GroupCreatorPanel.tsx (lines 35-44)** - ModelForGroup effect
```typescript
useEffect(() => {
  if (selectedModel && activeSlot !== null) {
    setAgents(prev => prev.map((agent, i) =>
      i === activeSlot ? { ...agent, model: selectedModel } : agent  // ← Correctly assigns
    ));
    setActiveSlot(null);
    onClearSelectedModel();  // ← Clears modelForGroup
  }
}, [selectedModel, activeSlot, onClearSelectedModel]);
```

### Solution Options

**Option A: Create separate handler (RECOMMENDED)**
```typescript
// ChatPanel.tsx - Add new handler
const handleModelSelectForGroupOnly = useCallback((modelId: string, _modelName: string) => {
  console.log('[ChatPanel] Model selected for group:', modelId);
  setModelForGroup(modelId);
  // DON'T modify input - only set modelForGroup for GroupCreator
}, []);

// Change prop passed to GroupCreatorPanel from handleModelSelectForGroup
// to handleModelSelectForGroupOnly
```

**Option B: Add flag parameter**
```typescript
const handleModelSelect = useCallback((modelId: string, _modelName: string, isGroupMode: boolean = false) => {
  setSelectedModel(modelId);
  if (!isGroupMode) {  // Only add @mention if NOT in group mode
    setInput(prev => `@${modelId} ${prev}`);
  }
  if (!isGroupMode) {
    setActiveTab('chat');
  }
}, []);
```

### Implementation Details

**File to Modify:** `client/src/components/chat/ChatPanel.tsx`

**Change Required:**
- Lines 247-256: Remove `setInput` call OR create separate handler
- ~5 lines of code

**Testing Checklist:**
- [ ] Click model in GroupCreator → model assigned to role only
- [ ] Input field remains unchanged
- [ ] @mention still works in normal chat mode
- [ ] All 4 roles can be assigned without input corruption

**Estimated Time:** 2-3 minutes

---

## 📋 TASK 2: Курсор "запрещено" на кнопке Create Group

### Analysis Result
**CODE IS CORRECT** - Cursor behavior is implemented properly.

### Current Implementation

**File:** `client/src/components/chat/GroupCreatorPanel.tsx`

**Lines 296-310 - Create Button with cursor styling:**
```typescript
<button
  onClick={handleCreate}
  disabled={!canCreate}
  style={{
    width: '100%',
    padding: '10px',
    borderRadius: 4,
    border: 'none',
    fontSize: 12,
    fontWeight: 500,
    cursor: canCreate ? 'pointer' : 'not-allowed',  // ← CORRECT LOGIC
    background: canCreate ? '#333' : '#1a1a1a',
    color: canCreate ? '#ccc' : '#555',
    transition: 'all 0.2s'
  }}
  ...
>
```

**Lines 46-47 - canCreate logic:**
```typescript
const filledAgents = agents.filter(a => a.model !== null);
const canCreate = groupName.trim() && filledAgents.length > 0;
```

### Cursor Behavior (CORRECT)
- ✅ `canCreate = true` → `cursor: 'pointer'` (enabled)
- ✅ `canCreate = false` → `cursor: 'not-allowed'` (disabled)

### Why User Sees "not-allowed"

**Condition 1: Group Name Empty**
```
groupName.trim() = "" → false → canCreate = false → cursor = 'not-allowed' ✓
```

**Condition 2: Roles Not Filled**
```
filledAgents.length = 0 → false → canCreate = false → cursor = 'not-allowed' ✓
```

**Condition 3: Some Roles Empty**
```
e.g., [PM: claude], [Architect: null], [Dev: null], [QA: null]
→ filledAgents.length = 1 > 0 → true
BUT groupName might still be empty → canCreate = false → cursor = 'not-allowed' ✓
```

### Verdict

**Status:** NO BUG FOUND

The cursor displays `not-allowed` when it SHOULD (conditions not met). This is correct behavior.

**Possible user confusion:**
1. User may not realize Group Name field is required
2. User may click a role slot and not follow through with model selection
3. User may assume partial role assignment is enough

**Suggestion for Opus (if needed):**
- Add visual indicator showing what's still needed (e.g., "2 more roles needed")
- Improve help text explaining requirements
- Add progress indicator

**No code changes required** unless you want to improve UX messaging.

---

## 📋 TASK 3: Добавить роль Researcher в базовый набор

### Location Found

**Primary File:** `client/src/components/chat/GroupCreatorPanel.tsx`

**Line 21 - DEFAULT_ROLES constant:**
```typescript
const DEFAULT_ROLES = ['PM', 'Architect', 'Dev', 'QA'];
```

**Usage Locations:**

1. **Line 31-32** - Initial state
```typescript
const [agents, setAgents] = useState<Agent[]>(
  DEFAULT_ROLES.map(role => ({ role, model: null }))
);
```

2. **Line 54** - Reset after group creation
```typescript
setAgents(DEFAULT_ROLES.map(role => ({ role, model: null })));
```

### Required Changes

**Frontend Change - Add Researcher:**
```typescript
// Line 21 in GroupCreatorPanel.tsx
const DEFAULT_ROLES = ['PM', 'Architect', 'Dev', 'QA', 'Researcher'];
```

That's it for frontend - the map functions will automatically handle the new role.

### Backend Verification Needed

**Status:** Need to verify Researcher agent exists in backend

**Files to check:**
- `src/api/handlers/user_message_handler.py` - Agent definitions
- `src/agents/` - Agent implementations
- Group management endpoints

**Search results:**
- ✅ Backend has PM, Architect, Dev, QA agents
- ❓ Researcher agent status unclear (need backend verification)
- ❓ May need Researcher handler in group message routing

### Implementation Checklist

**Frontend (Simple):**
- [ ] Add 'Researcher' to DEFAULT_ROLES array
- [ ] Test UI shows 5 role slots
- [ ] Test can assign models to Researcher
- [ ] Test group creation with Researcher agent

**Backend (To verify):**
- [ ] Confirm Researcher agent exists
- [ ] Verify it can be used in group chat
- [ ] Check if need to add routing for @researcher mentions

**Estimated Time:**
- Frontend: 1 minute
- Backend verification: 10-20 minutes
- Total: 2-5 minutes (frontend only) or 15-25 minutes (full validation)

---

## 📋 TASK 4: Голос Grok (TTS - Text-to-Speech Integration)

### Current Architecture Status

#### 1. Grok Backend Status
**Infrastructure:** ✅ Prepared
**Implementation:** ❌ NOT DONE

**File:** `src/elisya/api_aggregator_v3.py`

**Line 111** - Grok defined in ProviderType enum:
```python
GROK = "grok"
```

**Lines 184-194** - TODO comment showing incomplete integration:
```python
# PROVIDERS = {
#   ProviderType.OLLAMA: OllamaProvider(),
#   ProviderType.OPENROUTER: OpenRouterProvider(),
#   ...
#   # ProviderType.GROK: GrokProvider,  # ← COMMENTED OUT (not implemented)
# }
```

**Conclusion:** Grok is defined in enum but GrokProvider class doesn't exist. Backend routing not implemented.

#### 2. XAI/Grok API Keys
**File:** `src/utils/unified_key_manager.py`

**Line 41** - XAI provider defined:
```python
XAI = "xai"
```

**Line 169** - XAI key validation assigned:
```python
ProviderType.XAI: self._validate_xai_key,
```

**Line 192-195** - Validation function:
```python
def _validate_xai_key(self, key: str) -> bool:
    return isinstance(key, str) and key.startswith("xai-")
```

**Status:** ✅ Infrastructure for XAI keys exists, ready to use

#### 3. Audio/Voice Capabilities

**Audio Playback:** ✅ IMPLEMENTED
- **File:** `app/artifact-panel/src/components/viewers/AudioWaveform.tsx`
- **Library:** WaveSurfer.js
- **Features:** Play/pause, skip forward/backward, time display
- **Supported formats:** .mp3, .wav, .ogg, .m4a, .flac, .aac, .opus, .wma
- **Limitation:** Playback only (no generation)

**Text-to-Speech Generation:** ❌ NOT IMPLEMENTED
**Speech Recognition:** ❌ NOT IMPLEMENTED
**Voice Recording:** ❌ NOT IMPLEMENTED

#### 4. Message Display System

**MessageBubble Component** - Where to add Play button
- **File:** `client/src/components/chat/MessageBubble.tsx`
- **Lines 19-25** - AGENT_ICONS object
```typescript
const AGENT_ICONS: Record<string, React.ReactNode> = {
  PM: <ClipboardList size={14} />,
  Dev: <Code size={14} />,
  QA: <TestTube size={14} />,
  Architect: <Building size={14} />,
  Hostess: <Sparkles size={14} />,
  // ← NO Researcher/Grok icon
};
```

- **Lines 159-392** - Assistant message rendering (where TTS button would go)

**Message Type Definition**
- **File:** `client/src/types/chat.ts`
- **Lines 1-25** - ChatMessage interface
- **Line 14** - Agent field (NO 'Researcher' or 'Grok')
  ```typescript
  agent?: 'PM' | 'Dev' | 'QA' | 'Architect' | 'Hostess';
  ```
- **Lines 62-77** - MENTION_ALIASES (NO @grok)
  ```typescript
  '@deepseek': '@deepseek',
  '@coder': '@coder',
  '@qwen': '@qwen',
  '@llama': '@llama',
  '@claude': '@claude',
  '@gemini': '@gemini',
  // ← NO '@grok'
  ```

### TTS Implementation Options

#### Option A: Web Speech API (RECOMMENDED FOR QUICK START)

**Pros:**
- ✅ Free, built-in to all modern browsers
- ✅ No backend required
- ✅ ~50 lines of code
- ✅ Works immediately
- ✅ Supports many languages

**Cons:**
- ❌ Voice quality: Basic/decent (OS-dependent)
- ❌ Limited language/accent options
- ❌ No streaming playback

**Browser Support:** Chrome, Edge, Safari, Firefox (limited)

**Implementation Complexity:** Easy (30-40 minutes)

**Example Code:**
```typescript
// client/src/hooks/useTTS.ts
export function useTTS() {
  const speak = (text: string, lang: string = 'en-US') => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      utterance.rate = 0.9;
      utterance.pitch = 1.0;
      speechSynthesis.speak(utterance);
    }
  };

  const stop = () => {
    if ('speechSynthesis' in window) {
      speechSynthesis.cancel();
    }
  };

  const isSpeaking = () => {
    return 'speechSynthesis' in window && speechSynthesis.speaking;
  };

  return { speak, stop, isSpeaking };
}
```

#### Option B: ElevenLabs API (BETTER QUALITY)

**Pros:**
- ✅ Professional voice quality
- ✅ 30+ natural voices
- ✅ Multiple languages
- ✅ Consistent output

**Cons:**
- ❌ Paid service ($0.30 per 1M characters, ~$15/month for moderate use)
- ❌ Requires API key
- ❌ Requires backend integration
- ❌ ~200 lines of code

**Implementation Complexity:** Medium (2-3 hours)

**Cost Estimate:** $10-20/month for typical usage

#### Option C: OpenAI TTS API

**Pros:**
- ✅ Good quality, professional voices
- ✅ Integrated with ChatGPT ecosystem
- ✅ Works with existing OpenAI keys

**Cons:**
- ❌ Paid service ($15/1M characters)
- ❌ Slower than Web Speech
- ❌ ~150 lines of code

**Implementation Complexity:** Medium (2 hours)

#### Option D: Google Cloud Text-to-Speech

**Similar to ElevenLabs** - good quality, paid, medium complexity

### Recommended Implementation Plan

**Phase 1: Quick Start (30-40 min)**
1. Create `client/src/hooks/useTTS.ts` with Web Speech API
2. Add Play button to MessageBubble component
3. Test with existing messages

**Phase 2: Grok Integration (1-2 hours)**
1. Add Researcher to frontend roles (Task 3)
2. Update `client/src/types/chat.ts` to include 'Researcher' agent
3. Add '@grok' to MENTION_ALIASES
4. Implement GrokProvider in backend (if Grok not yet done)
5. Add Grok message routing

**Phase 3: Enhanced TTS (optional, 1-2 hours)**
1. Switch to ElevenLabs if better quality needed
2. Add voice selection UI
3. Add language preference

### Files That Need Changes

**For Web Speech API Only:**
1. **NEW FILE:** `client/src/hooks/useTTS.ts` (50 lines)
2. **MODIFY:** `client/src/components/chat/MessageBubble.tsx` (add button + import)
3. **OPTIONAL:** `client/src/types/chat.ts` (add Grok to enums)

**For Full Grok Support:**
4. **NEW FILE:** `src/elisya/grok_provider.py` (200+ lines)
5. **MODIFY:** `src/elisya/api_aggregator_v3.py` (register GrokProvider)
6. **MODIFY:** `client/src/types/chat.ts` (add Grok agent enum)

### Estimated Time Breakdown

| Phase | Task | Time |
|-------|------|------|
| 1 | Web Speech API implementation | 30-40 min |
| 2a | Add Researcher role (frontend) | 5 min |
| 2b | Grok backend implementation | 1-1.5 hours |
| 2c | Message routing for Grok | 30 min |
| 3 | Testing & refinement | 30 min |
| **TOTAL** | **Full TTS + Grok** | **2.5-3 hours** |

---

## 🗂️ File Reference Summary

### Files to Modify

| Task | File | Lines | Change Type |
|------|------|-------|------------|
| Task 1 | `client/src/components/chat/ChatPanel.tsx` | 247-256 | Remove/move setInput call |
| Task 2 | N/A | N/A | Code is correct |
| Task 3 | `client/src/components/chat/GroupCreatorPanel.tsx` | 21 | Add 'Researcher' to array |
| Task 4 | `client/src/types/chat.ts` | 14, 62-77 | Add Grok agent & alias (optional) |
| Task 4 | `client/src/components/chat/MessageBubble.tsx` | 19-25, 159+ | Add TTS button (new) |
| Task 4 | `client/src/hooks/useTTS.ts` | N/A | Create new file |

### Files to Create

| Task | File | Purpose |
|------|------|---------|
| Task 4 | `client/src/hooks/useTTS.ts` | Web Speech API hook |
| Task 4 | `src/elisya/grok_provider.py` | GrokProvider implementation (optional) |

---

## ✅ Testing Checklist

### Task 1: Model Duplication
- [ ] Click role slot → select model → model assigned to role
- [ ] Input field remains empty/unchanged
- [ ] All 4 roles can be assigned sequentially
- [ ] Create Group button activates when all conditions met
- [ ] Input field works normally in chat mode

### Task 2: Cursor
- [ ] Verify cursor is 'pointer' when group ready to create
- [ ] Verify cursor is 'not-allowed' when fields incomplete
- [ ] (No changes needed - already working)

### Task 3: Researcher Role
- [ ] 5 role slots appear in GroupCreator
- [ ] Researcher slot works like other roles
- [ ] Model can be assigned to Researcher
- [ ] Group creation with Researcher succeeds
- [ ] Backend accepts Researcher agent (if backend verified)

### Task 4: Grok TTS
- [ ] Web Speech API loads without errors
- [ ] Play button appears on assistant messages
- [ ] Clicking play button speaks message text
- [ ] Stop button works
- [ ] Works with multiple languages
- [ ] (Optional) Grok messages appear with Grok/Researcher indicator
- [ ] (Optional) @grok mentions work in chat

---

## 📌 Notes for Opus Implementation

1. **Task 1 is critical** - Users will see model names appearing in their message inputs
2. **Task 2 needs no changes** - The code is correct; document this for user clarity
3. **Task 3 requires backend verification** - Ensure Researcher agent exists before shipping
4. **Task 4 has architectural implications** - Consider whether full Grok support is worth 2+ hours
5. **Web Speech API is viable** - Can ship TTS quickly and upgrade later if needed
6. **Test in group creation mode specifically** - All changes interact with this UI

---

## 📄 Document History

- **Created:** 2026-01-11 by Claude Code Haiku
- **Status:** Complete - Ready for Implementation
- **Next Phase:** Opus implementation of identified fixes
