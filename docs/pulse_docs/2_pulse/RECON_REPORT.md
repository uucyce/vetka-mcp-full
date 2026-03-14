# Pulse Phase 2 - COMPREHENSIVE RECON REPORT

**Date:** 2026-02-24  
**Status:** CRITICAL - System Broken

---

## MARKER_2P_010: GROK RESEARCH vs IMPLEMENTED

### Grok Research Sources
1. `grok_bigd2_scale_pulse.md` - Full scale formulas (34+ scales)
2. `scale-genge-numbers.csv` - Vertices, colors, genres
3. `genre_geometry.csv` - Geometric visualization data

### Scale Formulas from Grok (Semitones from Root)

| Scale | Notes (from C) | Formula |
|-------|----------------|---------|
| Ionian (Major) | C D E F G A B | 0,2,4,5,7,9,11 |
| Dorian | C D Eb F G A Bb | 0,2,3,5,7,9,10 |
| Phrygian | C Db Eb F G Ab Bb | 0,1,3,5,7,8,10 |
| Lydian | C D E F# G A B | 0,2,4,6,7,9,11 |
| Mixolydian | C D E F G A Bb | 0,2,4,5,7,9,10 |
| Aeolian | C D Eb F G Ab Bb | 0,2,3,5,7,8,10 |
| Locrian | C Db Eb F Gb Ab Bb | 0,1,3,5,6,8,10 |
| Major Pentatonic | C D E G A | 0,2,4,7,9 |
| Minor Pentatonic | C Eb F G Bb | 0,3,5,7,10 |
| Minor Blues | C Eb F Gb G Bb | 0,3,5,6,7,10 |
| Major Blues | C D Eb E G A | 0,2,3,4,7,9 |
| Harmonic Minor | C D Eb F G Ab B | 0,2,3,5,7,8,11 |
| Melodic Minor | C D Eb F G A B | 0,2,3,5,7,9,11 |
| Whole Tone | C D E F# G# A# | 0,2,4,6,8,10 |
| Diminished | C D Eb F Gb G# A B | 0,2,3,5,6,8,9,11 |

### Currently Implemented in code

| What | Status | Problem |
|------|--------|---------|
| CAMELOT_WHEEL (24 keys) | ✅ Exists | Wrong formulas in some keys |
| KEY_PROFILES (24 profiles) | ⚠️ Partial | Only Major/Minor profiles |
| SCALE_POLYGONS (24 keys) | ❌ Broken | Wrong vertices, system crashed |
| getKeySparseMatch() | ❌ Broken | Causes hang |
| getKeyFromAllModes() | ❌ Disabled | Not used |

---

## MARKER_2P_011: CRITICAL BUGS

### Bug 1: getKeySparseMatch() causes hang
**Location:** `SmartAudioEngine.ts` line 138
**Problem:** Algorithm too slow, causes system freeze
**Fix:** Revert to simpler correlation-based approach

### Bug 2: SCALE_POLYGONS has wrong vertices  
**Location:** `theory.ts` lines 213-240
**Problem:** Hardcoded wrong, caused crash
**Fix:** Auto-calculate from CAMELOT_WHEEL

### Bug 3: Key detection always returns same key
**Location:** `SmartAudioEngine.ts` 
**Problem:** Chromagram noise, no proper filtering

---

## MARKER_2P_012: WHAT SHOULD BE DONE

### Phase 1: Fix Immediate (Critical)
1. [ ] Remove getKeySparseMatch(), use simple correlation
2. [ ] Auto-generate SCALE_POLYGONS from CAMELOT_WHEEL
3. [ ] Verify wheel shows different polygons per key

### Phase 2: Proper Implementation (According to Grok)
1. [ ] Add ALL 34 scale formulas from Grok research
2. [ ] Create proper key profiles (not just Major/Minor)
3. [ ] Implement downbeat-triggered detection

---

## MARKER_2P_013: FILES STATUS

| File | Current Status |
|------|---------------|
| `SmartAudioEngine.ts` | ❌ Broken - hangs on key detection |
| `UnifiedWheel.tsx` | ⚠️ Works but showing wrong data |
| `theory.ts` | ❌ SCALE_POLYGONS corrupted |
| `CAMELOT_MATRIX.ts` | ✅ Working |

---

## MARKER_2P_014: RECOMMENDED FIX SEQUENCE

### Step 1: Restore Working State
```typescript
// In SmartAudioEngine.ts - USE SIMPLE CORRELATION
const { key, score } = getKeyFromChromagram(this.chromagram);
```

### Step 2: Auto-generate Polygons
```typescript
// In theory.ts - GENERATE FROM EXISTING DATA
function getScaleVertices(camelotKey: string): number[] {
  const notes = CAMELOT_WHEEL[camelotKey];
  return [...new Set(notes.map(n => n % 12))].sort((a,b) => a-b);
}
```

### Step 3: Test basic functionality first

---

## CONCLUSION
The system is broken because:
1. getKeySparseMatch() is too slow/complex
2. Hardcoded SCALE_POLYGONS has wrong data
3. Multiple untested changes accumulated

**NEXT ACTION:** Fix Step 1 and Step 2 to restore working state, then test.
