# Pulse v2.0 - Smart Audio Analysis Implementation

**Based on Grok Research (Feb 2026)**
**Last Updated:** 2026-02-23

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     SMART AUDIO PIPELINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────────────┐  │
│  │  Mic     │───▶│ Circular     │───▶│ Onset Detection     │  │
│  │  Input   │    │ Buffer       │    │ (Spectral Flux)     │  │
│  │          │    │ (10 sec max) │    │                     │  │
│  └──────────┘    └──────────────┘    └──────────┬──────────┘  │
│                                                 │              │
│                                                 ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐ │
│  │ Key          │◀───│ Beat         │◀───│ Downbeat         │ │
│  │ Detector     │    │ Tracker      │    │ Detection        │ │
│  │ (Krumhansl)  │    │ (BPM)        │    │ (Energy + Phase) │ │
│  └──────┬───────┘    └──────┬───────┘    └────────┬────────┘ │
│         │                    │                     │           │
│         ▼                    ▼                     ▼           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              PREDICTIVE MODULATION                       │   │
│  │  - Camelot Matrix (24x24 probability)                  │   │
│  │  - Markov Chain for next key                           │   │
│  │  - Trigger on STRONG BEAT only                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Implementation Tasks

### Phase 1: Memory Management & Circular Buffer

**Problem:** Buffer fills unlimited → app freezes

**Solution:** Implement circular buffer with max size

```typescript
// src/audio/CircularAudioBuffer.ts

export class CircularAudioBuffer {
  private buffer: Float32Array;
  private writeIndex: number = 0;
  private maxSize: number;
  
  constructor(maxSeconds: number = 10, sampleRate: number = 44100) {
    this.maxSize = maxSeconds * sampleRate;
    this.buffer = new Float32Array(this.maxSize);
  }
  
  push(sample: number) {
    this.buffer[this.writeIndex] = sample;
    this.writeIndex = (this.writeIndex + 1) % this.maxSize;
  }
  
  pushArray(samples: Float32Array) {
    for (let i = 0; i < samples.length; i++) {
      this.push(samples[i]);
    }
  }
  
  getRecent(size: number): Float32Array {
    const result = new Float32Array(size);
    let idx = (this.writeIndex - size + this.maxSize) % this.maxSize;
    for (let i = 0; i < size; i++) {
      result[i] = this.buffer[idx];
      idx = (idx + 1) % this.maxSize;
    }
    return result;
  }
  
  clear() {
    this.buffer.fill(0);
    this.writeIndex = 0;
  }
  
  getSize(): number {
    return this.maxSize;
  }
}
```

**Status:** TODO

---

### Phase 2: Smart Trigger (Onset Detection)

**Problem:** Currently listens continuously → memory leak + CPU waste

**Solution:** Trigger analysis only on onset events

**Algorithm: Spectral Flux**
- Compute FFT of recent window
- Compare with previous frame
- Detect significant changes (> threshold)
- Trigger key/BPM detection only on onset

```typescript
// src/audio/OnsetDetector.ts

export class OnsetDetector {
  private fft: FFTProcessor;
  private threshold: number = 0.3;
  private previousSpectrum: Float32Array | null = null;
  private minInterval: number = 50; // ms between triggers
  
  private lastTriggerTime: number = 0;
  
  constructor() {
    this.fft = new FFTProcessor(2048);
  }
  
  detect(audioBuffer: Float32Array): boolean {
    const spectrum = this.fft.forward(audioBuffer);
    
    if (!this.previousSpectrum) {
      this.previousSpectrum = spectrum;
      return false;
    }
    
    // Compute spectral flux
    let flux = 0;
    for (let i = 0; i < spectrum.length; i++) {
      const diff = spectrum[i] - this.previousSpectrum[i];
      if (diff > 0) flux += diff;
    }
    
    this.previousSpectrum = spectrum;
    
    // Check threshold and min interval
    const now = Date.now();
    if (flux > this.threshold && now - this.lastTriggerTime > this.minInterval) {
      this.lastTriggerTime = now;
      return true; // Onset detected!
    }
    
    return false;
  }
  
  setThreshold(value: number) {
    this.threshold = value;
  }
}
```

**Status:** TODO

---

### Phase 3: Downbeat Detection

**Problem:** Can't distinguish strong vs weak beats

**Solution:** Analyze energy envelope + phase

```typescript
// src/audio/DownbeatDetector.ts

export class DownbeatDetector {
  private bpm: number = 120;
  private lastBeatTime: number = 0;
  private beatPhase: number = 0;
  private energyHistory: number[] = [];
  private windowSize: number = 4; // beats
  
  update(audioBuffer: Float32Array, currentTime: number): { isDownbeat: boolean; phase: number } {
    // Compute RMS energy
    let energy = 0;
    for (let i = 0; i < audioBuffer.length; i++) {
      energy += audioBuffer[i] * audioBuffer[i];
    }
    energy = Math.sqrt(energy / audioBuffer.length);
    
    this.energyHistory.push(energy);
    if (this.energyHistory.length > this.windowSize) {
      this.energyHistory.shift();
    }
    
    // Compute beat phase (0-1)
    const beatDuration = 60 / this.bpm;
    this.beatPhase = (currentTime % beatDuration) / beatDuration;
    
    // Downbeat: phase ~0 AND higher energy than average
    const avgEnergy = this.energyHistory.reduce((a, b) => a + b, 0) / this.energyHistory.length;
    const isDownbeat = this.beatPhase < 0.15 && energy > avgEnergy * 1.2;
    
    return { isDownbeat, phase: this.beatPhase };
  }
  
  setBpm(bpm: number) {
    this.bpm = bpm;
  }
}
```

**Status:** TODO

---

### Phase 4: Camelot Transition Matrix

**Problem:** Random key changes sound bad

**Solution:** Use probability matrix for harmonic mixing

```typescript
// src/music/CamelotMatrix.ts

export const CAMELOT_MATRIX: number[][] = [];

function buildMatrix() {
  const keys = [];
  for (let i = 1; i <= 12; i++) {
    keys.push(`${i}A`);
    keys.push(`${i}B`);
  }
  
  for (let i = 0; i < 24; i++) {
    CAMELOT_MATRIX[i] = new Array(24).fill(0);
  }
  
  for (let i = 0; i < 24; i++) {
    // Same key: 100%
    CAMELOT_MATRIX[i][i] = 1.0;
    
    // +1 / -1 (boost/drop): 80-90%
    const plus1 = (i + 1) % 24;
    const minus1 = (i - 1 + 24) % 24;
    CAMELOT_MATRIX[i][plus1] = 0.85;
    CAMELOT_MATRIX[i][minus1] = 0.75;
    
    // Relative (A↔B same number): 70%
    const relative = i < 12 ? i + 12 : i - 12;
    CAMELOT_MATRIX[i][relative] = 0.7;
    
    // +7 semitones: 50%
    const plus7 = (i + 7) % 24;
    CAMELOT_MATRIX[i][plus7] = 0.5;
  }
}

buildMatrix();

export function getCompatibleKeys(currentKey: string): string[] {
  const keys = [];
  for (let i = 1; i <= 12; i++) {
    keys.push(`${i}A`);
    keys.push(`${i}B`);
  }
  
  const currentIdx = keys.indexOf(currentKey);
  if (currentIdx === -1) return [currentKey];
  
  const compatibles: { key: string; prob: number }[] = [];
  
  for (let i = 0; i < 24; i++) {
    if (CAMELOT_MATRIX[currentIdx][i] > 0.3) {
      compatibles.push({ key: keys[i], prob: CAMELOT_MATRIX[currentIdx][i] });
    }
  }
  
  return compatibles
    .sort((a, b) => b.prob - a.prob)
    .map(c => c.key);
}

export function predictNextKey(currentKey: string): string {
  const keys = [];
  for (let i = 1; i <= 12; i++) {
    keys.push(`${i}A`);
    keys.push(`${i}B`);
  }
  
  const currentIdx = keys.indexOf(currentKey);
  if (currentIdx === -1) return currentKey;
  
  // Find key with highest probability (excluding current)
  let bestKey = currentKey;
  let bestProb = 0;
  
  for (let i = 0; i < 24; i++) {
    if (i !== currentIdx && CAMELOT_MATRIX[currentIdx][i] > bestProb) {
      bestProb = CAMELOT_MATRIX[currentIdx][i];
      bestKey = keys[i];
    }
  }
  
  return bestKey;
}
```

**Status:** TODO

---

### Phase 5: Unified Audio Engine

**Problem:** Separate buttons for BPM, Key, Camera

**Solution:** One "Start" button that orchestrates everything

```typescript
// src/audio/SmartAudioEngine.ts

export type AudioState = 'idle' | 'listening' | 'analyzing' | 'playing';

export class SmartAudioEngine {
  private buffer: CircularAudioBuffer;
  private onsetDetector: OnsetDetector;
  private downbeatDetector: DownbeatDetector;
  private keyDetector: KeyDetector;
  private bpmDetector: BPMDetector;
  
  private state: AudioState = 'idle';
  private currentKey: string = '8B';
  private predictedKey: string | null = null;
  
  // State machine
  async start() {
    this.buffer.clear();
    this.state = 'listening';
    
    // Start BPM detector
    await this.bpmDetector.start((bpm, beatPhase) => {
      this.downbeatDetector.setBpm(bpm);
      
      // Check for downbeat
      const { isDownbeat } = this.downbeatDetector.update(
        this.buffer.getRecent(2048),
        Date.now() / 1000
      );
      
      if (isDownbeat && this.predictedKey) {
        // Switch to predicted key on downbeat!
        this.currentKey = this.predictedKey;
        this.predictedKey = null;
        this.onKeyChange?.(this.currentKey);
      }
    });
  }
  
  onAudioData(data: Float32Array) {
    this.buffer.pushArray(data);
    
    if (this.state !== 'listening') return;
    
    // Smart trigger: only analyze on onset
    if (this.onsetDetector.detect(data)) {
      // Run key detection
      const detectedKey = this.keyDetector.detect(this.buffer.getRecent(4096));
      
      if (detectedKey.confidence > 0.7) {
        // Predict next key
        this.predictedKey = predictNextKey(detectedKey.key);
      }
    }
  }
  
  stop() {
    this.bpmDetector.stop();
    this.keyDetector.stop();
    this.state = 'idle';
  }
}
```

**Status:** TODO

---

## 🔧 Integration with Pulse UI

### Current UI Flow (v1.1)
```
[Start Camera] → [Start Simulation] → [Auto Key] → [BPM Detect]
4 separate buttons
```

### New UI Flow (v2.0)
```
[▶ START] → camera + BPM + key detection auto-start
           ↓
     Smart trigger on
     downbeat/onset
           ↓
     Predictive modulation
     on strong beats
```

### UI Changes Required
1. Replace 4 buttons with 1 "▶ START"
2. Add status indicator: "Listening..." → "On beat X" → "Key: 8B → Predicting: 9B"
3. Show beat visualization (strong/weak)
4. Show predicted next key

---

## 📦 Dependencies

```bash
# Already installed
npm install tone          # For ARP
npm install tonal        # For music theory

# New for v2.0
# No new deps - implement with existing Web Audio API
```

---

## ✅ Checklist

- [ ] CircularAudioBuffer class
- [ ] OnsetDetector (Spectral Flux)
- [ ] DownbeatDetector (energy + phase)
- [ ] CamelotMatrix (24x24 probability)
- [ ] predictNextKey function
- [ ] SmartAudioEngine orchestrator
- [ ] UI: Single "Start" button
- [ ] UI: Beat visualization
- [ ] UI: Predicted key display

---

## 📝 Notes

- All algorithms run on main thread initially
- For better performance, move to AudioWorklet
- Circular buffer prevents memory leaks (max 10 seconds)
- Onset detection reduces CPU usage (not continuous analysis)
- Downbeat detection enables "DJ-style" modulation
- Predictive key follows harmonic mixing rules

---

*Based on Grok Research - Feb 2026*
