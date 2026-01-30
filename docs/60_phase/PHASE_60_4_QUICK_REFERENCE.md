# ⚡ Phase 60.4 - Quick Reference

**4 Cosmetic Fixes + Grok Voice Investigation**
**Status:** ✅ Complete | **Complexity:** Mixed | **Total Time:** 2.5-3 hours

---

## 🎯 Quick Summary

| # | Task | Status | File | Lines | Fix | Time |
|---|------|--------|------|-------|-----|------|
| 1 | Model duplication in input | ❌ BUG | ChatPanel.tsx | 247-256 | Remove setInput from group handler | 2-3 min |
| 2 | Cursor "not-allowed" | ✅ WORKS | GroupCreatorPanel.tsx | 306 | No change needed | 0 min |
| 3 | Add Researcher role | ⚠️ FOUND | GroupCreatorPanel.tsx | 21 | Add 'Researcher' to array | 2-5 min |
| 4 | Grok TTS voice | 📋 PLANNED | Multiple | N/A | Web Speech API hook + button | 2-3 hrs |

---

## 🔴 TASK 1: Model Duplication (HIGH PRIORITY)

**Problem:** Selecting model for role also adds `@modelId` to chat input

**Root Cause:**
```typescript
// ChatPanel.tsx:247-256
const handleModelSelectForGroup = useCallback((modelId: string) => {
  setModelForGroup(modelId);  // ✅ Correct
  setInput(prev => `@${modelId} ${prev}`);  // ❌ BUG - removes this!
}, []);
```

**Fix:**
```typescript
// Option A: Create separate handler (RECOMMENDED)
const handleModelSelectForGroupOnly = useCallback((modelId: string) => {
  setModelForGroup(modelId);  // ONLY this, don't touch input
}, []);

// Pass this to GroupCreatorPanel instead
```

**Files:** 1 file, ~5 lines
**Time:** 2-3 minutes

---

## 🟢 TASK 2: Cursor (NO FIX NEEDED)

**Verdict:** Code is correct! Cursor properly shows:
- `'pointer'` when ready to create (has name + filled agents)
- `'not-allowed'` when incomplete

**Current Logic (CORRECT):**
```typescript
cursor: canCreate ? 'pointer' : 'not-allowed'
const canCreate = groupName.trim() && filledAgents.length > 0;
```

**Likely User Issue:**
- Forgot to fill Group Name
- Selected role but didn't choose model
- Partial agent assignment

**Time:** 0 minutes (no changes)

---

## 🟡 TASK 3: Add Researcher Role (MEDIUM PRIORITY)

**Location:** `client/src/components/chat/GroupCreatorPanel.tsx:21`

**Current:**
```typescript
const DEFAULT_ROLES = ['PM', 'Architect', 'Dev', 'QA'];
```

**Change To:**
```typescript
const DEFAULT_ROLES = ['PM', 'Architect', 'Dev', 'QA', 'Researcher'];
```

**Frontend:** 1 line change ✅
**Backend Check:** Verify Researcher agent exists ⚠️

**Files:** 1 file, 1 line
**Time:** 2-5 minutes (+ backend validation)

---

## 🟣 TASK 4: Grok TTS Voice (COMPLEX)

### Current Status
- ❌ No TTS in codebase
- ❌ Grok backend NOT implemented
- ✅ Audio playback (WaveSurfer.js) exists
- ✅ XAI key infrastructure ready

### Recommended: Web Speech API (QUICK)

**Create:** `client/src/hooks/useTTS.ts`
```typescript
export function useTTS() {
  const speak = (text: string, lang: string = 'en-US') => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      speechSynthesis.speak(utterance);
    }
  };
  return { speak };
}
```

**Modify:** `client/src/components/chat/MessageBubble.tsx`
- Add `<button onClick={() => speak(message.content)}>🔊</button>`

**Files to Create/Modify:**
1. `client/src/hooks/useTTS.ts` (NEW, 50 lines)
2. `client/src/components/chat/MessageBubble.tsx` (ADD button)
3. `client/src/types/chat.ts` (OPTIONAL - add Grok agent)

**Time Estimate:**
- Web Speech API: 30-40 min
- Full Grok backend: +1-1.5 hours
- Testing: +30 min
- **TOTAL: 2-3 hours**

### Alternative: ElevenLabs API (BETTER QUALITY)
- Cost: $0.30 per 1M characters (~$15/month)
- Quality: Professional voices
- Time: 2-3 hours
- Complexity: Medium (needs backend integration)

---

## 📌 Implementation Order (for Opus)

```
1. TASK 1 (2-3 min)
   └─ Fix: Remove setInput from handleModelSelectForGroup

2. TASK 3 (2-5 min)
   └─ Add: 'Researcher' to DEFAULT_ROLES array
   └─ Verify: Researcher agent exists in backend

3. TASK 4 (30-40 min for quick version)
   └─ Create: useTTS hook with Web Speech API
   └─ Add: Play button to MessageBubble
   └─ Test: Verify TTS works

4. TASK 4B (optional, +1-1.5 hours)
   └─ Implement: Full Grok backend provider
   └─ Update: Message routing & enums
```

---

## 🔗 Related Files

**Group Creation Flow:**
- ModelDirectory.tsx (427-433) → Router
- ChatPanel.tsx (247-256, 236-243) → Handlers
- GroupCreatorPanel.tsx (21, 35-44, 296-310) → UI

**Message Display:**
- MessageBubble.tsx (19-25, 159-392) → Where TTS button goes
- chat.ts (14, 62-77) → Type definitions for agents

**Grok Infrastructure:**
- api_aggregator_v3.py (111, 184-194) → Backend provider definition
- unified_key_manager.py (41, 169, 192-195) → XAI key validation

---

## ✨ Key Insights

1. **Task 1 is a UX bug** - Model names leaking into input field
2. **Task 2 works correctly** - Code implements proper cursor behavior
3. **Task 3 is simple** - One-line addition to array
4. **Task 4 has options:**
   - **Quick:** Web Speech API (free, 30-40 min, basic quality)
   - **Better:** ElevenLabs (paid, 2-3 hours, professional)
   - **Full:** Grok backend + TTS (3+ hours, complete integration)

---

## 🚀 Ready for Implementation

All code locations precisely identified. Opus can start immediately with high confidence on file/line references.
