# Pulse Camelot-Mode Wheel Design

## 🎨 Research Summary

### Geometric Visualization Concept
Scales can be visualized as **polygons** inside a circle:
- **Vertices** = notes in the scale
- **Sides** = intervals (whole/half steps)
- **Polygon shape** = scale pattern (e.g., major = 7-sided heptagon, pentatonic = 5-sided pentagon)

### Why This Works
- **Functionality**: Polygon vertices = scale notes (labeled C, D, E...). Lines = intervals
- **Mode Wheel**: Inner polygon shows current mode/scale
- **Camelot shift**: Polygon rotates/shifts, showing relationship visually

### Visual Style (DaVinci/Itten inspired)
- **Outer**: Color wheel (Itten gradient, 12 colors for Camelot keys)
- **Inner**: Black polygon with glowing vertices (colored by notes)
- **Spectrogram**: Waveform inside polygon, pulsing with hit notes

---

## 🛠 Implementation Plan

### Libraries
- **react-konva** for canvas polygon drawing: `npm i react-konva`

### Component: CamelotModeWheel.tsx

```tsx
import { Stage, Layer, Circle, Line, Text, Arc } from 'react-konva';
import { SCALE_COLORS } from '../music/theory';

const CamelotModeWheel = ({ 
  currentCamelot, 
  currentMode, 
  scaleNotes 
}: { 
  currentCamelot: string;
  currentMode: string;
  scaleNotes: number[];
}) => {
  const outerRadius = 140;
  const innerRadius = 90;
  const centerX = 150;
  const centerY = 150;
  const segmentAngle = 360 / 12; // 30 degrees per semitone

  // Map scale notes to polygon vertices
  const polygonVertices = scaleNotes.map(midiNote => {
    const noteIndex = midiNote % 12; // 0-11 for C-B
    const angle = (noteIndex * segmentAngle - 90) * (Math.PI / 180); // -90 to start at top
    return {
      x: centerX + innerRadius * Math.cos(angle),
      y: centerY + innerRadius * Math.sin(angle),
      note: ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'][noteIndex],
      color: SCALE_COLORS[currentCamelot] || '#45B7D1'
    };
  });

  const polygonPoints = polygonVertices.flatMap(v => [v.x, v.y]);

  return (
    <Stage width={300} height={300}>
      <Layer>
        {/* Outer Camelot circle - 12 segments */}
        {Array.from({ length: 12 }).map((_, i) => {
          const angle = i * segmentAngle;
          const color = Object.values(SCALE_COLORS)[i] || '#45B7D1';
          return (
            <Arc
              key={i}
              x={centerX}
              y={centerY}
              innerRadius={outerRadius - 20}
              outerRadius={outerRadius}
              angle={segmentAngle}
              rotation={angle - 90}
              fill={color}
              opacity={currentCamelot === Object.keys(SCALE_COLORS)[i] ? 1 : 0.3}
            />
          );
        })}

        {/* Current key indicator */}
        <Circle
          x={centerX}
          y={centerY}
          radius={outerRadius - 25}
          stroke={SCALE_COLORS[currentCamelot]}
          strokeWidth={3}
        />

        {/* Inner polygon for scale */}
        {polygonVertices.length > 2 && (
          <>
            <Line
              points={[...polygonPoints, polygonPoints[0], polygonPoints[1]]}
              stroke="white"
              strokeWidth={2}
              closed
              dash={[5, 5]}
              opacity={0.8}
            />
            
            {/* Vertices with note names */}
            {polygonVertices.map((v, i) => (
              <Circle
                key={i}
                x={v.x}
                y={v.y}
                radius={8}
                fill={v.color}
                stroke="white"
                strokeWidth={2}
              />
            ))}
          </>
        )}

        {/* Center label */}
        <Text
          x={centerX - 20}
          y={centerY - 10}
          text={currentCamelot}
          fontSize={24}
          fontStyle="bold"
          fill="white"
        />
      </Layer>
    </Stage>
  );
};

export default CamelotModeWheel;
```

---

## 🎯 Features

### 1. Outer Circle (Camelot)
- 12 colored segments (one for each Camelot key)
- Current key highlighted (full opacity)
- Click to change key

### 2. Inner Polygon (Scale/Mode)
- Vertices = notes in current scale
- Lines connect to show intervals
- Glowing vertices with note names
- Shape changes with mode (major = 7-gon, pentatonic = 5-gon)

### 3. Animation
- On key change: smooth rotation
- On mode change: polygon morphs

### 4. Spectrogram Overlay
- Waveform visualization inside polygon
- Pulses with played notes

---

## 📦 Dependencies

```bash
npm install react-konva konva
```

---

## 🔄 Integration

In App.tsx:
```tsx
import CamelotModeWheel from './components/CamelotModeWheel';

// Use instead of static image
<CamelotModeWheel 
  currentCamelot={selectedScale}
  currentMode="Ionian"
  scaleNotes={CAMELOT_WHEEL[selectedScale]}
/>
```

---

*Design document created: 2026-02-23*
*Based on research: Polygon visualization of scales*
