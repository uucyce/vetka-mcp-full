/**
 * MARKER_180.10: CamelotWheel — SVG interactive Camelot key circle.
 *
 * Architecture doc §6.1:
 * "Camelot wheel = 12-key color circle, shows harmonic proximity.
 *  Click key → filter DAG by harmonic distance.
 *  Active key highlighted. Adjacent keys (±1) shown as compatible."
 *
 * 24 positions on the Camelot wheel:
 *   Outer ring: 1B-12B (major keys)
 *   Inner ring: 1A-12A (minor keys, relative minor = same number)
 *
 * Colors match the standard DJ Camelot wheel palette.
 * Used in PulseInspector and as standalone panel.
 */
import { useCallback, useMemo, type CSSProperties } from 'react';

// ─── Camelot data ───

interface CamelotKey {
  key: string;       // "8A", "3B", etc.
  note: string;      // "Am", "C", etc.
  angle: number;     // degrees (0° = 12 o'clock position)
  color: string;     // segment fill
  ring: 'inner' | 'outer';
}

// Inner ring = A (minor), Outer ring = B (major)
// Arranged so relative major/minor share same clock position
const CAMELOT_DATA: CamelotKey[] = [
  // Outer ring (B = major), clockwise from top
  { key: '1B',  note: 'B',   angle: 0,   color: '#E24B4A', ring: 'outer' },
  { key: '2B',  note: 'F#',  angle: 30,  color: '#E87D3E', ring: 'outer' },
  { key: '3B',  note: 'Db',  angle: 60,  color: '#EFA830', ring: 'outer' },
  { key: '4B',  note: 'Ab',  angle: 90,  color: '#D4C92A', ring: 'outer' },
  { key: '5B',  note: 'Eb',  angle: 120, color: '#7FC74D', ring: 'outer' },
  { key: '6B',  note: 'Bb',  angle: 150, color: '#5DCAA5', ring: 'outer' },
  { key: '7B',  note: 'F',   angle: 180, color: '#58B8D9', ring: 'outer' },
  { key: '8B',  note: 'C',   angle: 210, color: '#378ADD', ring: 'outer' },
  { key: '9B',  note: 'G',   angle: 240, color: '#6B6EDC', ring: 'outer' },
  { key: '10B', note: 'D',   angle: 270, color: '#7F77DD', ring: 'outer' },
  { key: '11B', note: 'A',   angle: 300, color: '#B064C8', ring: 'outer' },
  { key: '12B', note: 'E',   angle: 330, color: '#D94B8D', ring: 'outer' },
  // Inner ring (A = minor)
  { key: '1A',  note: 'Abm', angle: 0,   color: '#C43E3E', ring: 'inner' },
  { key: '2A',  note: 'Ebm', angle: 30,  color: '#C46A35', ring: 'inner' },
  { key: '3A',  note: 'Bbm', angle: 60,  color: '#C48E28', ring: 'inner' },
  { key: '4A',  note: 'Fm',  angle: 90,  color: '#B3A824', ring: 'inner' },
  { key: '5A',  note: 'Cm',  angle: 120, color: '#6BA640', ring: 'inner' },
  { key: '6A',  note: 'Gm',  angle: 150, color: '#4FA88A', ring: 'inner' },
  { key: '7A',  note: 'Dm',  angle: 180, color: '#4A9AB5', ring: 'inner' },
  { key: '8A',  note: 'Am',  angle: 210, color: '#2F72B8', ring: 'inner' },
  { key: '9A',  note: 'Em',  angle: 240, color: '#5A5CB8', ring: 'inner' },
  { key: '10A', note: 'Bm',  angle: 270, color: '#6A63B8', ring: 'inner' },
  { key: '11A', note: 'F#m', angle: 300, color: '#9454A6', ring: 'inner' },
  { key: '12A', note: 'C#m', angle: 330, color: '#B54078', ring: 'inner' },
];

// ─── Geometry ───

const SVG_SIZE = 200;
const CENTER = SVG_SIZE / 2;
const OUTER_R = 85;
const OUTER_R_INNER = 60;
const INNER_R = 55;
const INNER_R_INNER = 32;
const SEGMENT_ARC = 30; // degrees per segment
const LABEL_OUTER_R = 72;
const LABEL_INNER_R = 43;

// ─── Helper: arc path ───

function arcPath(cx: number, cy: number, r1: number, r2: number, startDeg: number, endDeg: number): string {
  const toRad = Math.PI / 180;
  // Offset by -90° so 0° = top
  const s = (startDeg - 90) * toRad;
  const e = (endDeg - 90) * toRad;

  const x1o = cx + Math.cos(s) * r1;
  const y1o = cy + Math.sin(s) * r1;
  const x2o = cx + Math.cos(e) * r1;
  const y2o = cy + Math.sin(e) * r1;
  const x1i = cx + Math.cos(e) * r2;
  const y1i = cy + Math.sin(e) * r2;
  const x2i = cx + Math.cos(s) * r2;
  const y2i = cy + Math.sin(s) * r2;

  const largeArc = endDeg - startDeg > 180 ? 1 : 0;

  return [
    `M ${x1o} ${y1o}`,
    `A ${r1} ${r1} 0 ${largeArc} 1 ${x2o} ${y2o}`,
    `L ${x1i} ${y1i}`,
    `A ${r2} ${r2} 0 ${largeArc} 0 ${x2i} ${y2i}`,
    'Z',
  ].join(' ');
}

// ─── Harmonic distance (simplified Camelot rule) ───

function camelotDistance(key1: string, key2: string): number {
  const num1 = parseInt(key1);
  const num2 = parseInt(key2);
  const letter1 = key1.slice(-1);
  const letter2 = key2.slice(-1);

  // Same key = 0
  if (key1 === key2) return 0;

  // Same number, different letter = 1 (relative major/minor)
  if (num1 === num2) return 1;

  // Adjacent numbers, same letter = 1
  const diff = Math.abs(num1 - num2);
  const circDiff = Math.min(diff, 12 - diff);
  if (letter1 === letter2 && circDiff === 1) return 1;

  return circDiff + (letter1 !== letter2 ? 1 : 0);
}

// ─── Component Props ───

interface CamelotWheelProps {
  /** Currently active Camelot key */
  activeKey?: string;
  /** Keys to highlight (e.g., scene keys in timeline) */
  highlightedKeys?: string[];
  /** Click handler for key selection */
  onKeyClick?: (key: string) => void;
  /** Size override */
  size?: number;
  /** Show note names instead of Camelot numbers */
  showNotes?: boolean;
}

// ─── Styles ───

const WRAPPER: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: '100%',
  height: '100%',
};

export default function CamelotWheel({
  activeKey,
  highlightedKeys = [],
  onKeyClick,
  size = SVG_SIZE,
  showNotes = false,
}: CamelotWheelProps) {
  // Compatible keys: distance ≤ 1
  const compatibleKeys = useMemo(() => {
    if (!activeKey) return new Set<string>();
    return new Set(
      CAMELOT_DATA
        .filter((ck) => camelotDistance(activeKey, ck.key) <= 1)
        .map((ck) => ck.key),
    );
  }, [activeKey]);

  const highlightSet = useMemo(() => new Set(highlightedKeys), [highlightedKeys]);

  const handleClick = useCallback(
    (key: string) => {
      onKeyClick?.(key);
    },
    [onKeyClick],
  );

  return (
    <div style={WRAPPER}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}
        style={{ overflow: 'visible' }}
      >
        {/* Segments */}
        {CAMELOT_DATA.map((ck) => {
          const isActive = ck.key === activeKey;
          const isCompatible = compatibleKeys.has(ck.key);
          const isHighlighted = highlightSet.has(ck.key);
          const isOuter = ck.ring === 'outer';

          const r1 = isOuter ? OUTER_R : INNER_R;
          const r2 = isOuter ? OUTER_R_INNER : INNER_R_INNER;
          const halfArc = SEGMENT_ARC / 2;
          const startDeg = ck.angle - halfArc + 1; // +1 gap
          const endDeg = ck.angle + halfArc - 1;

          // Opacity: active=1, compatible=0.7, highlighted=0.5, else=0.2
          let opacity = 0.2;
          if (isActive) opacity = 1.0;
          else if (isCompatible) opacity = 0.7;
          else if (isHighlighted) opacity = 0.5;
          else if (!activeKey) opacity = 0.35; // no active key → show all dimly

          // Label position
          const labelR = isOuter ? LABEL_OUTER_R : LABEL_INNER_R;
          const labelRad = (ck.angle - 90) * (Math.PI / 180);
          const lx = CENTER + Math.cos(labelRad) * labelR;
          const ly = CENTER + Math.sin(labelRad) * labelR;
          const label = showNotes ? ck.note : ck.key;

          return (
            <g
              key={ck.key}
              onClick={() => handleClick(ck.key)}
              style={{ cursor: onKeyClick ? 'pointer' : 'default' }}
            >
              {/* Segment arc */}
              <path
                d={arcPath(CENTER, CENTER, r1, r2, startDeg, endDeg)}
                fill={ck.color}
                opacity={opacity}
                stroke={isActive ? '#E0E0E0' : '#1A1A1A'}
                strokeWidth={isActive ? 1.5 : 0.5}
              />

              {/* Label */}
              <text
                x={lx}
                y={ly}
                textAnchor="middle"
                dominantBaseline="central"
                fill={opacity > 0.4 ? '#E0E0E0' : '#555'}
                fontSize={isOuter ? 7 : 6}
                fontFamily='"JetBrains Mono", monospace'
                fontWeight={isActive ? 700 : 400}
                style={{ pointerEvents: 'none', userSelect: 'none' }}
              >
                {label}
              </text>

              {/* Highlighted dot (scene present at this key) */}
              {isHighlighted && !isActive && (
                <circle
                  cx={lx}
                  cy={ly + (isOuter ? 9 : 8)}
                  r={2}
                  fill={ck.color}
                  opacity={0.8}
                />
              )}
            </g>
          );
        })}

        {/* Center info */}
        {activeKey && (
          <text
            x={CENTER}
            y={CENTER}
            textAnchor="middle"
            dominantBaseline="central"
            fill="#E0E0E0"
            fontSize={12}
            fontFamily='"JetBrains Mono", monospace'
            fontWeight={600}
            style={{ userSelect: 'none' }}
          >
            {activeKey}
          </text>
        )}
        {!activeKey && (
          <text
            x={CENTER}
            y={CENTER}
            textAnchor="middle"
            dominantBaseline="central"
            fill="#444"
            fontSize={9}
            fontFamily="Inter, system-ui, sans-serif"
            style={{ userSelect: 'none' }}
          >
            Camelot
          </text>
        )}
      </svg>
    </div>
  );
}
