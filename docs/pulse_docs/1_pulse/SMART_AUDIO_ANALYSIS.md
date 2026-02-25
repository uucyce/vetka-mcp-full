# Research: Smart Audio Analysis for Gesture Synthesizer

## Vision
AI DJ system that listens to music, detects BPM/beat structure, analyzes key, predicts next key using Camelot matrix, and auto-switches on strong beats - like a human musician would.

## Current Problems
1. Memory leak - listening buffer fills up unlimited, app freezes
2. No strong/weak beat detection
3. Key detector runs continuously without smart triggering
4. No predictive modulation

## Requirements

### 1. Smart Trigger Mechanism
- Detect audio events (note on, transients)
- Trigger analysis only on meaningful events
- Implement buffer size limits and circular buffering
- Use Web Audio API AnalyserNode with proper cleanup

### 2. BPM & Beat Structure Detection
- Detect BPM (already works)
- Detect strong beat vs weak beat (downbeat detection)
- Determine beat phase: strong (0.0), weak (0.25, 0.5, 0.75)
- Use onset detection + amplitude analysis to find downbeats

### 3. Key Detection Timing
- Key detector triggers ONLY on strong beats
- Collect chromagram samples during strong beat windows
- Use Krumhansl algorithm for key detection
- Queue key changes for next strong beat (beat-sync already exists)

### 4. Predictive Modulation (Camelot Matrix)
- Build transition probability matrix from music theory
- Track recent key changes to predict progression
- Modulate to compatible key on strong beats
- Support "mixing" transitions (harmonic mixing)

### 5. Combined Start
- Single button: starts camera + BPM detector
- BPM detector auto-starts when audio detected
- Key detector activates after stable BPM found

## Technical Implementation

### Buffer Management
```javascript
// Circular buffer with max size
const bufferSize = 8192;
const buffer = new Float32Array(bufferSize);
let writeIndex = 0;

// Limit analysis to recent window
const analysisWindow = 2048;
```

### Beat Structure Detection
```javascript
// Onset detection + amplitude envelope
// Strong beat = high amplitude onset after silence
// Weak beat = lower amplitude, regular interval
```

### Camelot Transitions
```javascript
// Compatible keys (distance 1-2 in wheel)
const compatibleKeys = {
  '8B': ['5B', '9B', '8A', '7B'],
  // ... all 24 keys
};
```

## Questions for Research
1. Best algorithms for downbeat detection in real-time?
2. How to implement efficient circular buffer in Web Audio?
3. Transition probability matrices for Camelot wheel?
4. Predictive key selection algorithms used by DJ software?

## Deliverables
1. Algorithm specifications for each component
2. Performance optimization recommendations
3. State machine design for the listening modes
4. Memory management strategy
