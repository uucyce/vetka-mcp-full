# VETKA Phase 90.1: Fix Grok Button Input Mode Inversion

**Status:** COMPLETED
**Date:** 2026-01-23
**Agent:** Claude Sonnet 4.5

---

## Problem Description

When a voice model (e.g., Grok) was selected, the send button logic was inverted:
- User types text → Click button → Voice mode activates (WRONG)
- Expected: User types text → Click button → Send text message

### Root Cause

The `handleButtonClick` function checked voice mode conditions BEFORE checking if the user had typed text. This caused voice mode to activate even when the input field contained text.

**File:** `client/src/components/chat/MessageInput.tsx`
**Lines:** 450-469 (original)

---

## Solution

Reordered the button click handler to prioritize text input over voice mode:

1. **PRIORITY 1:** If text exists in input → Send text message
2. **PRIORITY 2:** If input is empty + voice model active → Activate voice mode

---

## Code Changes

### Before (Lines 450-469)

```typescript
const handleButtonClick = useCallback(() => {
  // Voice mode active (voice model selected/mentioned) - use realtime pipeline
  if (showVoiceMode || voiceOnlyMode || isSelectedModelVoice) {
    if (realtimeVoice.isListening) {
      realtimeVoice.stopListening();
    } else {
      realtimeVoice.startListening();
    }
    return;
  }

  // Legacy voice mode (for non-voice models with voiceOnlyMode)
  if (isListening) {
    stopListening();
  } else if (hasText) {
    onSend();
  }
}, [isListening, showVoiceMode, hasText, stopListening, onSend, realtimeVoice, voiceOnlyMode, isSelectedModelVoice]);
```

### After (Lines 452-481)

```typescript
// MARKER_90.1_START: Fix voice/text priority
const handleButtonClick = useCallback(() => {
  // PRIORITY 1: If user typed text, ALWAYS send text (regardless of voice model)
  if (hasText) {
    // Stop any active voice recording first
    if (isListening) stopListening();
    if (realtimeVoice.isListening) realtimeVoice.stopListening();
    onSend();
    return;
  }

  // PRIORITY 2: Voice mode active (empty input + voice model selected/mentioned)
  if (showVoiceMode || voiceOnlyMode || isSelectedModelVoice) {
    if (realtimeVoice.isListening) {
      realtimeVoice.stopListening();
    } else {
      realtimeVoice.startListening();
    }
    return;
  }

  // Legacy voice mode (for non-voice models with voiceOnlyMode)
  if (isListening) {
    stopListening();
  }
}, [isListening, showVoiceMode, hasText, stopListening, onSend, realtimeVoice, voiceOnlyMode, isSelectedModelVoice]);
// MARKER_90.1_END
```

---

## Key Changes

1. **Check `hasText` FIRST** - If the user typed anything, send it as text
2. **Stop active voice sessions** - Before sending text, stop any voice recording
3. **Voice mode as fallback** - Only activate voice when input is empty

---

## Testing Checklist

- [x] Text in input + click button = Send text message ✅
- [x] Empty input + Grok selected + click button = Activate voice mode ✅
- [x] Text typed with Grok selected + click = Send text (not voice) ✅
- [x] Active voice recording + type text + click = Stop voice and send text ✅

---

## Impact

This fix resolves the inverted behavior where selecting a voice model would prevent text messages from being sent. Users can now:
- Type text messages to voice models (e.g., Grok) normally
- Use voice input when the input field is empty
- Switch seamlessly between text and voice modes

---

## Markers

- `MARKER_90.1_START` - Line 453
- `MARKER_90.1_END` - Line 481

---

## Related Files

- `client/src/components/chat/MessageInput.tsx` (fixed)
- `docs/90_ph/PHASE_90.0.1_HAIKU_RECON.md` (recon that identified the issue)

---

## Next Steps

- Test in production with Grok model
- Verify no regressions with other voice models (Gemini Flash, etc.)
- Monitor user feedback on text/voice mode switching
