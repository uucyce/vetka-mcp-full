# Pulse v2.0 - Unified Smart Engine

**Created by Kimi K2 (Analysis)**
**Date:** 2026-02-23

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PULSE UNIFIED ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────┐     ┌─────────────────┐     ┌─────────────────────────┐   │
│   │  MIC/LINE   │────▶│  Smart Trigger  │────▶│   Downbeat Detector     │   │
│   │   INPUT     │     │  (Onset/Flux)   │     │  (Strong/Weak Beat)     │   │
│   └─────────────┘     └─────────────────┘     └────────────┬────────────┘   │
│                                                            │                │
│                                                            ▼                │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    UNIFIED STATE MACHINE                             │   │
│   │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────────────┐  │   │
│   │  │  IDLE   │──▶│ LISTEN  │──▶│ ANALYZE│──▶│   PREDICT/MODULATE  │  │   │
│   │  └─────────┘   └─────────┘   └─────────┘   └─────────────────────┘  │   │
│   │       ▲                                                    │        │   │
│   │       └────────────────────────────────────────────────────┘        │   │
│   │                         (Auto-loop on downbeat)                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                            │                                                │
│                            ▼                                                │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  KEY DETECTION (Trigger on DOWNBEAT only)                           │   │
│   │  - Chromagram analysis on STRONG beat                              │   │
│   │  - Scale refinement over multiple beats                            │   │
│   │  - Confidence-based scale locking                                 │   │
│   └──────────────────────────┬──────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  SYNTH ENGINE (Auto-tuned to detected key/scale)                    │   │
│   │  - X: Pitch quantized to scale                                   │   │
│   │  - Y: Legato (top) ↔ Arpeggio (bottom)                        │   │
│   │  - Filter/Volume: Second hand                                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Features

1. **Smart Trigger** - Onset detection (Spectral Flux)
2. **Downbeat Detection** - Strong/weak beat via energy analysis
3. **Key Detection** - Only on strong beats
4. **Predictive Modulation** - Camelot matrix transitions
5. **UnifiedWheel** - Itten colors + Camelot + Scale polygon
6. **Kaoss Control** - X=pitch, Y=legato/arp

## Files to Implement

- `src/audio/SmartAudioEngine.ts` - Unified audio pipeline
- `src/components/UnifiedWheel.tsx` - Itten + Camelot + polygon
- `src/components/PulseApp.tsx` - Single START button UI

## Quick Start

```bash
npm install tone react-konva konva lucide-react
npm run tauri dev
```

Press START - system automatically listens, detects BPM on strong beats, detects key, and predicts modulation.
