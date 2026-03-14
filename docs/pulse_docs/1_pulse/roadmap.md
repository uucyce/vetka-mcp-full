# Pulse — Roadmap & Feature Requests

**Last Updated:** 2026-02-23

---

## ✅ Version 1.1 - ARP + Beat Quantization (2026-02-23)

### Features
- Tauri + React + WebAudio Synth
- MediaPipe Hands tracking (pinch → gate)
- X-axis → Pitch (3 octaves, C3-B5)
- Y-axis → Legato/Arpeggio (with Tone.js Arpeggiator)
- **True ARP** - Tone.js Arpeggiator with patterns (up, down, upDown, downUp)
- Camelot Wheel selector (interactive Konva)
- Beat Quantization (quarter, eighth, sixteenth)
- **Auto Key Detection v2** - Chromagram + Krumhansl-Schmuckler
- Real-time notes display (C4, G#5)
- BPM Detection
- Beat-synced key switching
- Left/Right hand swap
- Simulation mode
- ARP Pattern selector UI

### Key Detection Algorithm
- Chromagram (12 pitch classes)
- Krumhansl-Schmuckler key profiles
- Cosine similarity matching
- Harmonic analysis (2nd, 3rd harmonics)

---

## ✅ Completed

### Day 1: Foundation
- Tauri + React + WebAudio Synth
- Basic UI shell with Header

### Day 2: Vision + Synthesis  
- MediaPipe Hands tracking
- Pinch detection → Gate (sound on/off)
- X-axis → Frequency (pitch) - like piano
- Mirror video horizontally
- Simulation mode for testing

### Day 3: Scale Quantizer (Camelot)
- Camelot Wheel selector with image
- Quantize to scale notes
- Color theme based on key
- Left/Right hand swap

### Day 4: Auto Key Detection v2 (CHROMAGRAM)
- Microphone input for key detection
- Chromagram-based note detection
- Krumhansl-Schmuckler algorithm
- All harmonics analysis
- Show detected notes + key + confidence

---

## 🔬 Research Findings (2026-02-23)

### Key Detection Approaches

| Method | Accuracy | Complexity | Notes |
|--------|----------|------------|-------|
| **Chromagram + Krumhansl** (v2) | ⭐⭐⭐⭐ | Medium | Industry standard |
| **FFT + Peak Detection** (v1) | ⭐⭐ | Simple | Only detects fundamental frequency |

---

## 🐛 Known Bugs / Issues

### Fixed in v1.4
- [x] Hand swap now works (colors + function)
- [x] Filter hand Y-axis
- [x] Pitch hand X-axis separate
- [x] BPM detection added
- [x] Beat-synced key switching (experimental)

### Current Issues - NEEDS RESEARCH
- [ ] **ARP (Arpeggio) implementation is wrong**:
  - Current: simply mutes audio - NOT true arpeggio
  - **CORRECT Y-axis mapping**: 
    - **Y < 0.4 (DOWN)** = ARP - true arpeggio pattern
    - **Y > 0.6 (UP)** = LEGATO - continuous sound
    - Y 0.4-0.6 = NORMAL
  - **Recommended solution**: Use Tone.js Arpeggiator
    - BPM-synced patterns (up, down, upDown, random)
    - rate changes based on Y position
    - Humanize for natural feel

### Research Notes (from GROK 2026-02-23)
```
Tone.Arpeggiator features:
- pattern: 'up', 'down', 'upDown', 'random', 'randomWalk'
- rate: BPM-synced ('16n', '8n', etc.)
- humanize: adds slight timing variation
- Connect to PolySynth, feed scale notes

Implementation:
1. npm i tone
2. initArp(scaleNotes) - called on scale change
3. updateArp(y, pitchMidi) - called on gesture
4. Y < 0.5: arp.rate increases (faster ARP)
5. Y > 0.5: direct triggerAttackRelease (legato)
```

### Future Features (Research Needed)
- [ ] **Camelot auto-shift**: On each bar (every 4 beats), shift key to adjacent
- [ ] **True arpeggio engine** using Tone.js Arpeggiator
- [ ] MIDI out support

---

## 🎯 Future Features (Post-v1.1)

### Phase 1: BPM/Beat Detection
- Detect tempo from microphone input
- Identify strong beats (downbeats)
- Trigger key changes on beats
- Confidence threshold for stability

### Phase 2: Korg Kaos Style Controls
- **Pitch hand Y-axis**: up = legato, down = arpeggio
- Depends on BPM detection for timing
- Visual feedback for current mode

### Phase 3: Advanced Features
- Mode wheel (7 modes: Ionian, Dorian, etc.)
- Sample/file upload for precise key detection
- MIDI out support

---

## 📋 Implementation Notes

### Hand Mapping (v1.1+)
```
Notes Hand (pinch to play):
  - X axis: pitch (left=low, right=high)
  - Y axis: legato ↔ arpeggio (Korg Kaos style)

Filter Hand:
  - Y axis: filter cutoff (up=open, down=closed)
  - No pinch required
```

### Key Detection Flow (with BPM)
1. Detect BPM and beat positions
2. Analyze chromagram on each beat
3. If confidence > threshold → auto-switch key on downbeat
| **Chromagram + Krumhansl** | ⭐⭐⭐⭐ | Medium | Industry standard, uses pitch class profiles |
| **webKeyFinder (WASM)** | ⭐⭐⭐⭐⭐ | Complex | Compiled libKeyFinder, heavy |
| **Essentia.js** | ⭐⭐⭐⭐⭐ | Complex | 85-95% accuracy, AGPLv3 license |
| **Tone.js + Tonal** | ⭐⭐⭐⭐ | Medium | Already in project, has Chord.detect() |

### Key Detection Libraries Found

1. **napulen/justkeydding** (GitHub)
   - Uses chromagram + Hidden Markov Model
   - State-of-the-art accuracy
   
2. **dogayuksel/webKeyFinder** (GitHub, 34 stars)
   - Browser-based key detection
   - Uses libKeyFinder compiled to WASM
   - Supports live stream + audio files

3. **Corentin-Lcs/music-key-finder** (GitHub)
   - Krumhansl-Schmuckler algorithm
   - Python implementation

4. **Tonal.js Chord.detect()**
   - Already in project!
   - `Chord.detect(["C", "E", "G"])` → `["Cmaj"]`

### Audio Analysis Improvements

- **Use chromagram** instead of single frequency detection
- **Collect notes over 1-2 seconds** before determining key
- **Krumhansl-Schmuckler profiles** for major/minor key comparison
- **Confidence threshold** (0.7+) before accepting key change

---

## 📋 In Progress

### Current Issues
1. Key detection unstable - jumps between keys
2. Only detects fundamental frequency, not all notes
3. Camelot wheel UI too small
4. No sample/file upload mode

### Research: Sample-Based vs Live Detection
- **Live (air)**: Very noisy, single note detection
- **Sample mode**: Analyze pre-recorded audio, much more accurate
- **Recommendation**: Add sample upload for accurate detection

---

## 🎯 Implementation Plan

### Priority 1: UI Improvements
- [ ] Make Camelot wheel larger and visible
- [ ] Show all detected notes in real-time
- [ ] Add confidence indicator

### Priority 2: Algorithm Improvements  
- [ ] Implement chromagram-based detection
- [ ] Add Krumhansl-Schmuckler key profiles
- [ ] Increase buffer time for better analysis

### Priority 3: Sample Mode
- [ ] Add audio file upload
- [ ] Analyze entire file for key
- [ ] Show all detected notes + key

### Priority 4: Integration
- [ ] Use Tone.js Chord.detect() for chord detection
- [ ] Add BPM detection
- [ ] Add MIDI out

---

## 🔄 User's Vision Summary

**Current Implementation:**
- Left hand = Notes (pinch to play)
- Right hand = Filter (X-axis)
- Auto Key detection working (basic FFT)
- Camelot selector working

**Requested:**
- Two wheels (Camelot + Mode)
- Better key detection (Essentia.js/chromagram)
- Accompaniment (bass + chords)
- Per-finger filters

---

## 📝 Libraries to Add (Future)

```bash
npm install tone @tonejs/chroma
```

### Priority
1. `tonal` - Already added, for scale/mode definitions
2. `chroma` - Chromagram computation
3. `tone` - For accompaniment patterns

---

## 🐛 Known Bugs (to fix)

1. **Key detection instability** - Needs longer buffer + chromagram
2. **One note detection** - Should detect all harmonics
3. **Camelot UI small** - Needs larger display

---

## 🚀 Version 2.0 - Smart Audio Analysis (IN PROGRESS)

### Documents
- Research: `docs/pulse/SMART_AUDIO_ANALYSIS.md`
- Implementation: `docs/pulse/IMPLEMENTATION_V2.md`

### Key Features
1. ~~**Circular Buffer**~~ - ✅ DONE (Max 10 sec, no memory leak)
2. **Smart Trigger** - Onset detection (Spectral Flux) → only analyze on events
3. **Downbeat Detection** - Strong vs weak beat via energy analysis
4. **Camelot Matrix** - 24x24 probability for harmonic mixing
5. **Predictive Modulation** - Auto-switch on strong beats
6. **Single Start Button** - Camera + BPM + Key all at once

### Completed
- [x] Phase 1: CircularAudioBuffer class
- [x] Phase 1: Integration into KeyDetector
- [x] Tests: 59 passed

### Memory Leak Fix Required
- Current: Buffer fills unlimited → app freezes
- Solution: Circular buffer + max size + cleanup

---

*Pulse — Gesture Synthesizer*
