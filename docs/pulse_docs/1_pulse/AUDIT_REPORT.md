# 🔍 Pulse AUDIT REPORT

**Date:** 2026-02-23  
**Status:** CRITICAL ISSUES FOUND

---

## 🚨 CRITICAL BUGS

### 1. 🔴 ONLY 1 OCTAVE - Missing 2 Octaves
**Location:** `src/music/theory.ts:5-33`

**Problem:** CAMELOT_WHEEL contains only 7 notes per key (1 octave):
```typescript
'8B': [60, 62, 64, 65, 67, 69, 71],  // C Major - only 1 octave!
```

**Impact:** 
- X-axis can only play 7 notes
- No low notes (bass), no high notes (lead)
- Very limited musical range

**Solution:** Extend to 3 octaves:
```typescript
'8B': [48, 50, 52, 53, 55, 57, 59,  // Octave 3 (C3-B3)
        60, 62, 64, 65, 67, 69, 71,  // Octave 4 (C4-B4)
        72, 74, 76, 77, 79, 81, 83], // Octave 5 (C5-B5)
```

---

### 2. 🔴 quantizeToScale Uses Only 7 Notes
**Location:** `src/music/theory.ts:122-127`

**Problem:**
```typescript
export function quantizeToScale(normalizedValue: number, scaleKey: string = '8B'): number {
  const scale = CAMELOT_WHEEL[scaleKey] || CAMELOT_WHEEL['8B'];
  const index = Math.floor(clamped * (scale.length - 1));  // Only 7 positions!
  return scale[index];
}
```

**Fix Needed:**
```typescript
const index = Math.floor(clamped * (scale.length - 1));
// Should expand to cover 3 octaves properly
```

---

### 3. 🔴 AutoKey → Scale Connection MAY BE BROKEN
**Location:** `src/App.tsx:265-277`

**Flow Analysis:**
```
AutoKey detected → setSelectedScale(key) → quantizeToScale(X, selectedScale) → sound
```

**Potential Issues:**
- Line 78: `const scaleNotes = CAMELOT_WHEEL[selectedScale]` - syntax error? (missing `]`)
- Need to verify selectedScale actually changes
- Need console logs to confirm

---

## ⚠️ MEDIUM ISSUES

### 4. 🟡 BPM Not Connected to Scale/Note Selection
**Location:** `src/audio/BPMDetector.ts`

**Problem:** 
- BPM detected (tempo)
- beatPhase tracked (0-1 position in beat)
- BUT: No differentiation between strong/weak beats
- No way to know which notes should land on downbeat

**Solution:** Need to pass beat position to quantizer for "on-beat" quantization

---

### 5. 🟡 SynthEngine Frequency Range Limited
**Location:** `src/audio/SynthEngine.ts:10-11`

```typescript
private readonly minFrequency = 110;  // A2
private readonly maxFrequency = 880;  // A5
```

**Problem:** Only ~3 octaves, hardcoded

---

### 6. 🟡 Mode Wheel Not Implemented
**Location:** `src/music/theory.ts:46-54`

```typescript
export const MODE_WHEEL = [
  { name: 'Ionian', short: 'ION', type: 'major' },
  { name: 'Dorian', short: 'DOR', type: 'minor' },
  ...
];
```

**Problem:** Defined but NOT USED in UI or quantizer

---

## 📊 DATA FLOW MAP

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUTS                                    │
├─────────────────────────────────────────────────────────────────┤
│  Camera (MediaPipe)    → Hand Tracking (X, Y, pinch)         │
│  Microphone            → KeyDetector (notes)                   │
│  Microphone            → BPMDetector (tempo)                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PROCESSING                                  │
├─────────────────────────────────────────────────────────────────┤
│  X-axis → quantizeToScale(selectedScale) → MIDI note          │
│  Y-axis → (filter cutoff OR legato/arp mode)                 │
│  AutoKey → selectedScale (Camelot key)                       │
│  BPM → beatPhase (0-1)                                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        OUTPUT                                   │
├─────────────────────────────────────────────────────────────────┤
│  SynthEngine.play(midiNote)                                    │
│  - Oscillator frequency from MIDI                              │
│  - Filter cutoff from Y                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 WHAT WORKS vs NOT WORKS

| Feature | Status | Notes |
|---------|--------|-------|
| Hand tracking | ✅ Works | Green/red hands detected |
| Pinch → gate | ✅ Works | Sound on/off |
| X → pitch | ⚠️ Limited | Only 1 octave |
| Y → filter | ✅ Works | Filter cutoff |
| Hand swap | ✅ Works | Colors + function |
| Camelot Wheel (UI) | ✅ Works | Clickable, shows scale |
| AutoKey detection | ✅ Works | Finds key from audio |
| **Scale → Sound** | ❌ **BROKEN?** | Needs verification |
| **3 Octaves** | ❌ **MISSING** | Only 1 octave |
| BPM → beat | ⚠️ Partial | Phase tracked, not used |
| Mode Wheel | ❌ Not used | Defined but not wired |

---

## 🔧 REQUIRED FIXES (Priority Order)

### P0 - CRITICAL
1. [ ] **Add 3 octaves to CAMELOT_WHEEL**
   - Extend each key from 7 notes to 21 notes
   - Update quantizeToScale to handle 21 notes

2. [ ] **Verify AutoKey → Sound connection**
   - Add debug logging to confirm scale changes
   - Test with known key (e.g., play C-E-G, verify 8B)

### P1 - HIGH
3. [ ] **Connect BPM to note selection**
   - Pass beatPhase to quantizer
   - Option to quantize to strong beats only

4. [ ] **Implement Mode Wheel**
   - Wire MODE_WHEEL to UI
   - Allow mode selection (Ionian, Dorian, etc.)

### P2 - MEDIUM
5. [ ] **Extend SynthEngine range**
   - Lower minFrequency to 55 (A1)
   - Upper maxFrequency to 1760 (A6)

---

## 📁 FILES TO MODIFY

| File | Changes |
|------|---------|
| `src/music/theory.ts` | Add 3 octaves, fix quantizeToScale |
| `src/App.tsx` | Debug AutoKey→Scale, connect BPM to notes |
| `src/audio/SynthEngine.ts` | Extend frequency range |
| `src/components/CamelotModeWheel.tsx` | Add mode selector |

---

## 🧪 TEST PLAN

1. **Test Scale Quantization:**
   - Play C-E-G on instrument
   - Check: Should get consistent scale notes
   - Verify scale matches detected key

2. **Test 3 Octaves:**
   - Left hand position = low notes
   - Right hand position = high notes
   - Should hear ~3 octave range

3. **Test BPM Connection:**
   - Enable BPM detection
   - Play rhythmic pattern
   - Notes should land on beat when enabled

---

*End of Audit Report*
