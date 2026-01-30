# MARKER_90.0.1_START: Grok Button Investigation

## Phase 90.0.1: Critical Voice/Text Input Bug Analysis

### Bug Summary
**Expected:** When text is in input, clicking send button should send the message
**Broken:** When text is in input, clicking sends button activates voice mode instead of sending

### Current Logic Flow (Pseudocode)

```
handleButtonClick():
  [Line 454] if (showVoiceMode || voiceOnlyMode || isSelectedModelVoice):
    if (realtimeVoice.isListening):
      STOP voice
    else:
      START voice listening  ← WRONG: always enters voice mode
    return  ← EXITS WITHOUT CHECKING TEXT

  [Line 464] if (isListening):
    STOP legacy voice
  [Line 466] else if (hasText):
    SEND MESSAGE
```

### Inverted Condition Location

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/MessageInput.tsx`

**Lines:** 453-460 (Early return block in new realtime voice section)

**Problem:** The condition at **line 454** invokes voice mode BEFORE checking if user has typed text.

```typescript
// CURRENT BROKEN CODE (lines 453-461)
if (showVoiceMode || voiceOnlyMode || isSelectedModelVoice) {
  if (realtimeVoice.isListening) {
    realtimeVoice.stopListening();
  } else {
    realtimeVoice.startListening();  // ← ALWAYS STARTS VOICE
  }
  return;  // ← EXITS WITHOUT CHECKING TEXT!
}
```

The `showVoiceMode` variable is set to true based on voice model detection (lines 258-263):

```typescript
const showVoiceMode = (
  (voiceModelDetection.hasVoiceModel && !voiceModelDetection.hasTextAfter) ||
  (isReplyingToVoiceModel && !hasText) ||
  (isSelectedModelVoice && !hasText) ||
  (voiceOnlyMode && !hasText)
) && !isListening;
```

**The Logic Flaw:**
- When a voice model is selected AND user types text, the logic SHOULD switch to "send text" mode
- However, `showVoiceMode` contains a condition `!hasText` that SHOULD prevent voice mode when text is present
- BUT the button handler line 454 uses OR logic: `if (showVoiceMode || voiceOnlyMode || isSelectedModelVoice)`
- This means `isSelectedModelVoice` (voice model selected) alone triggers voice mode even when user typed text

### Git Commit History

**Introduced in commit:** `f94ec893` (Phase 60.5.1: Realtime Voice Pipeline)
**Date:** Jan 12, 2026 03:10:25

```
Commit: f94ec893
Message: Phase 60.5.1: Realtime Voice Pipeline
Changed: client/src/components/chat/MessageInput.tsx

- REMOVED: Old logic that checked showVoiceMode with text handling
  Old: } else if (showVoiceMode) { startListening(); }
       } else if (hasText) { onSend(); }

- ADDED: New early return that always enters voice for any voice model
  New: if (showVoiceMode || voiceOnlyMode || isSelectedModelVoice) {
         realtimeVoice.startListening();
         return;
       }
```

### Detailed Diff Analysis

**Before (Correct - e2555344):**
```typescript
// Legacy voice mode
if (isListening) {
  stopListening();
} else if (showVoiceMode) {
  // Voice model detected - start listening
  startListening();
} else if (hasText) {
  onSend();
}
```

Flow: Stop → Voice mode → Send (checked in order, only one triggers)

**After (Broken - f94ec893):**
```typescript
// Voice mode active (voice model selected/mentioned) - use realtime pipeline
if (showVoiceMode || voiceOnlyMode || isSelectedModelVoice) {
  if (realtimeVoice.isListening) {
    realtimeVoice.stopListening();
  } else {
    realtimeVoice.startListening();  // ALWAYS STARTS VOICE
  }
  return;  // EXITS EARLY
}

// Legacy voice mode (for non-voice models with voiceOnlyMode)
if (isListening) {
  stopListening();
} else if (hasText) {
  onSend();
}
```

Flow: Always enters voice mode when voice model is selected (regardless of text)

### Root Cause Hypothesis

**The Problem:** Line 454's condition is too broad.

When Phase 60.5.1 refactored to use realtime voice pipeline, it changed the logic from:
- Sequential if/else (only one action per click)
- To: Voice models get early return (always enter voice mode)

The condition `isSelectedModelVoice` includes voice models that ARE SELECTED but should NOT activate voice mode if the user typed text.

**The showVoiceMode variable already handles this correctly** with its `!hasText` condition, but line 454 ALSO checks `isSelectedModelVoice` independently:

```typescript
if (showVoiceMode || voiceOnlyMode || isSelectedModelVoice) {
                                     ↑
                    This part is WRONG - ignores !hasText check
```

### Suspected Inverted Logic

The condition should be:
```typescript
// Only use voice mode if conditions are met AND no text
if (showVoiceMode || (voiceOnlyMode && !hasText)) {
  // NOT: if (showVoiceMode || voiceOnlyMode || isSelectedModelVoice)
  // NOT: if (showVoiceMode || voiceOnlyMode)
```

OR the logic needs to be restructured to check `hasText` FIRST:
```typescript
if (hasText) {
  onSend();
} else if (showVoiceMode || voiceOnlyMode || isSelectedModelVoice) {
  // Voice logic
}
```

### Impact Scope

- **Affected Users:** Anyone using Grok or voice-enabled models in text mode
- **Trigger:** Selecting a voice model then typing text
- **Behavior:** Text mode button click → voice mode activates → no message sent
- **Workaround:** Users must press Enter key or stop using voice models in text mode

### Recent Related Commits

```
c83cfa2 (Jan 22) - Phase 80.38-80.40: Fix xai key detection (NOT related to button logic)
711cf45 (Jan 21) - Phase 80.37: xai fallback to openrouter (NOT related)
4d7850b (Jan 19) - Phase 80.36: x-ai provider name (NOT related)
6072e08 (Jan 19) - Phase 80.35: Fix Grok routing (NOT related)
b6c98f1 (Jan 16) - Phase 80.30: Fix @mention dropdown (NOT related, only added soloModels param)

f94ec893 (Jan 12) - Phase 60.5.1: Realtime Voice Pipeline ← THIS INTRODUCED THE BUG
e2555344 (Jan 11) - Before this commit, logic was correct
```

### Timeline

| Date    | Commit | Phase          | Status                                  |
|---------|--------|----------------|-----------------------------------------|
| Jan 11  | e2555344 | 60.5    | ✅ Logic correct: sequential if/else    |
| Jan 12  | f94ec893 | 60.5.1  | ❌ BUG: Early return for voice models   |
| Jan 12-22 | (5 commits) | 60-80  | Bug persists through all changes        |

# MARKER_90.0.1_END
