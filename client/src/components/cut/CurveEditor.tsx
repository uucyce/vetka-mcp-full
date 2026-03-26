/**
 * MARKER_B93: Interactive Curve Editor — HTML5 Canvas bezier spline editor.
 *
 * FCP7 Ch.80 reference. Per-channel curves (Master/R/G/B).
 * Click to add control point, drag to move, double-click to delete.
 * Outputs normalized {x, y}[] control points (0-1 range).
 */
import { useRef, useState, useCallback, useEffect, type CSSProperties } from 'react';

// ─── Types ───

export interface CurvePoint {
  x: number; // 0..1 (input luminance)
  y: number; // 0..1 (output luminance)
}

export type CurveChannel = 'master' | 'red' | 'green' | 'blue';

export interface CurveData {
  master: CurvePoint[];
  red: CurvePoint[];
  green: CurvePoint[];
  blue: CurvePoint[];
}

export const DEFAULT_CURVE: CurvePoint[] = [
  { x: 0, y: 0 },
  { x: 1, y: 1 },
];

export function createDefaultCurveData(): CurveData {
  return {
    master: [...DEFAULT_CURVE],
    red: [...DEFAULT_CURVE],
    green: [...DEFAULT_CURVE],
    blue: [...DEFAULT_CURVE],
  };
}

interface CurveEditorProps {
  curves: CurveData;
  onChange: (curves: CurveData) => void;
  size?: number;
}

// ─── Spline math ───

/** Monotone cubic interpolation through sorted points → 256-entry LUT */
function buildLUT(points: CurvePoint[]): number[] {
  const sorted = [...points].sort((a, b) => a.x - b.x);
  const n = sorted.length;
  if (n < 2) {
    return Array.from({ length: 256 }, (_, i) => i / 255);
  }

  // For 2 points, linear interpolation
  if (n === 2) {
    const lut: number[] = [];
    for (let i = 0; i < 256; i++) {
      const t = i / 255;
      const slope = (sorted[1].y - sorted[0].y) / (sorted[1].x - sorted[0].x || 1e-6);
      lut.push(Math.max(0, Math.min(1, sorted[0].y + slope * (t - sorted[0].x))));
    }
    return lut;
  }

  // Monotone cubic (Fritsch-Carlson)
  const xs = sorted.map((p) => p.x);
  const ys = sorted.map((p) => p.y);
  const dx: number[] = [];
  const dy: number[] = [];
  const m: number[] = [];

  for (let i = 0; i < n - 1; i++) {
    dx.push(xs[i + 1] - xs[i] || 1e-6);
    dy.push(ys[i + 1] - ys[i]);
    m.push(dy[i] / dx[i]);
  }

  const tangents: number[] = [m[0]];
  for (let i = 1; i < n - 1; i++) {
    if (m[i - 1] * m[i] <= 0) {
      tangents.push(0);
    } else {
      tangents.push((m[i - 1] + m[i]) / 2);
    }
  }
  tangents.push(m[n - 2]);

  // Fritsch-Carlson monotonicity constraints
  for (let i = 0; i < n - 1; i++) {
    if (Math.abs(m[i]) < 1e-6) {
      tangents[i] = 0;
      tangents[i + 1] = 0;
    } else {
      const a = tangents[i] / m[i];
      const b = tangents[i + 1] / m[i];
      const s = a * a + b * b;
      if (s > 9) {
        const tau = 3 / Math.sqrt(s);
        tangents[i] = tau * a * m[i];
        tangents[i + 1] = tau * b * m[i];
      }
    }
  }

  // Evaluate LUT
  const lut: number[] = [];
  for (let i = 0; i < 256; i++) {
    const t = i / 255;
    // Find segment
    let seg = 0;
    for (let j = 0; j < n - 1; j++) {
      if (t >= xs[j]) seg = j;
    }
    if (seg >= n - 1) seg = n - 2;

    const h = dx[seg];
    const tt = (t - xs[seg]) / h;
    const tt2 = tt * tt;
    const tt3 = tt2 * tt;

    // Hermite basis
    const h00 = 2 * tt3 - 3 * tt2 + 1;
    const h10 = tt3 - 2 * tt2 + tt;
    const h01 = -2 * tt3 + 3 * tt2;
    const h11 = tt3 - tt2;

    const val = h00 * ys[seg] + h10 * h * tangents[seg] + h01 * ys[seg + 1] + h11 * h * tangents[seg + 1];
    lut.push(Math.max(0, Math.min(1, val)));
  }

  return lut;
}

// ─── Styles ───

const CHANNEL_COLORS: Record<CurveChannel, string> = {
  master: '#ccc',
  red: '#aa6666',
  green: '#66aa66',
  blue: '#6688aa',
};

const TAB_STYLE: CSSProperties = {
  background: 'none',
  border: 'none',
  padding: '3px 8px',
  fontSize: 10,
  cursor: 'pointer',
  fontFamily: 'system-ui',
  borderRadius: 3,
};

const POINT_RADIUS = 5;
const HIT_RADIUS = 10;

// ─── Component ───

export default function CurveEditor({ curves, onChange, size = 200 }: CurveEditorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [activeChannel, setActiveChannel] = useState<CurveChannel>('master');
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const points = curves[activeChannel];

  // ─── Canvas coordinate helpers ───
  const toCanvas = useCallback((p: CurvePoint) => ({
    cx: p.x * size,
    cy: (1 - p.y) * size,
  }), [size]);

  const fromCanvas = useCallback((cx: number, cy: number): CurvePoint => ({
    x: Math.max(0, Math.min(1, cx / size)),
    y: Math.max(0, Math.min(1, 1 - cy / size)),
  }), [size]);

  const findPointAt = useCallback((cx: number, cy: number): number | null => {
    for (let i = 0; i < points.length; i++) {
      const { cx: px, cy: py } = toCanvas(points[i]);
      const dist = Math.sqrt((cx - px) ** 2 + (cy - py) ** 2);
      if (dist < HIT_RADIUS) return i;
    }
    return null;
  }, [points, toCanvas]);

  // ─── Drawing ───
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, size, size);

    // Background
    ctx.fillStyle = '#111';
    ctx.fillRect(0, 0, size, size);

    // Grid
    ctx.strokeStyle = '#222';
    ctx.lineWidth = 1;
    for (let i = 1; i < 4; i++) {
      const pos = (i / 4) * size;
      ctx.beginPath();
      ctx.moveTo(pos, 0);
      ctx.lineTo(pos, size);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, pos);
      ctx.lineTo(size, pos);
      ctx.stroke();
    }

    // Identity diagonal
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, size);
    ctx.lineTo(size, 0);
    ctx.stroke();

    // Draw inactive channel curves faintly
    const channels: CurveChannel[] = ['red', 'green', 'blue'];
    if (activeChannel !== 'master') {
      // Draw master faintly
      drawCurve(ctx, curves.master, '#555', 1);
    }
    for (const ch of channels) {
      if (ch !== activeChannel) {
        drawCurve(ctx, curves[ch], CHANNEL_COLORS[ch] + '44', 1);
      }
    }

    // Draw active channel curve
    const lut = buildLUT(points);
    const color = CHANNEL_COLORS[activeChannel];

    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let i = 0; i < 256; i++) {
      const cx = (i / 255) * size;
      const cy = (1 - lut[i]) * size;
      if (i === 0) ctx.moveTo(cx, cy);
      else ctx.lineTo(cx, cy);
    }
    ctx.stroke();

    // Control points
    const sorted = [...points].sort((a, b) => a.x - b.x);
    for (let i = 0; i < sorted.length; i++) {
      const { cx, cy } = toCanvas(sorted[i]);
      const origIdx = points.indexOf(sorted[i]);
      const isHover = hoverIndex === origIdx;
      const isDrag = dragIndex === origIdx;

      ctx.fillStyle = isDrag || isHover ? '#fff' : color;
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, isDrag ? POINT_RADIUS + 1 : POINT_RADIUS, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
  }, [size, points, activeChannel, curves, dragIndex, hoverIndex, toCanvas]);

  function drawCurve(ctx: CanvasRenderingContext2D, pts: CurvePoint[], color: string, width: number) {
    if (pts.length < 2) return;
    const lut = buildLUT(pts);
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.beginPath();
    for (let i = 0; i < 256; i++) {
      const cx = (i / 255) * size;
      const cy = (1 - lut[i]) * size;
      if (i === 0) ctx.moveTo(cx, cy);
      else ctx.lineTo(cx, cy);
    }
    ctx.stroke();
  }

  useEffect(() => { draw(); }, [draw]);

  // ─── Mouse handlers ───
  const getCanvasPos = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return { cx: 0, cy: 0 };
    return { cx: e.clientX - rect.left, cy: e.clientY - rect.top };
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const { cx, cy } = getCanvasPos(e);
    const idx = findPointAt(cx, cy);
    if (idx !== null) {
      setDragIndex(idx);
    } else {
      // Add new point
      const newPoint = fromCanvas(cx, cy);
      const newPoints = [...points, newPoint].sort((a, b) => a.x - b.x);
      onChange({ ...curves, [activeChannel]: newPoints });
    }
  }, [getCanvasPos, findPointAt, fromCanvas, points, curves, activeChannel, onChange]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const { cx, cy } = getCanvasPos(e);

    if (dragIndex !== null) {
      const newPoint = fromCanvas(cx, cy);
      // Don't allow moving endpoints' x position
      const isEndpoint = dragIndex === 0 || dragIndex === points.length - 1;
      const sorted = [...points].sort((a, b) => a.x - b.x);
      if (isEndpoint) {
        // Endpoints: lock x to 0 or 1
        if (sorted[0] === points[dragIndex]) {
          newPoint.x = 0;
        } else {
          newPoint.x = 1;
        }
      }
      const newPoints = [...points];
      newPoints[dragIndex] = newPoint;
      onChange({ ...curves, [activeChannel]: newPoints });
    } else {
      setHoverIndex(findPointAt(cx, cy));
    }
  }, [getCanvasPos, dragIndex, fromCanvas, points, curves, activeChannel, onChange, findPointAt]);

  const handleMouseUp = useCallback(() => {
    setDragIndex(null);
  }, []);

  const handleDoubleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const { cx, cy } = getCanvasPos(e);
    const idx = findPointAt(cx, cy);
    if (idx !== null && points.length > 2) {
      // Don't delete if it's one of the two base endpoints
      const sorted = [...points].sort((a, b) => a.x - b.x);
      const isFirst = sorted[0] === points[idx];
      const isLast = sorted[sorted.length - 1] === points[idx];
      if (!isFirst && !isLast) {
        const newPoints = points.filter((_, i) => i !== idx);
        onChange({ ...curves, [activeChannel]: newPoints });
      }
    }
  }, [getCanvasPos, findPointAt, points, curves, activeChannel, onChange]);

  const handleReset = useCallback(() => {
    onChange({ ...curves, [activeChannel]: [...DEFAULT_CURVE] });
  }, [curves, activeChannel, onChange]);

  const isIdentity = points.length === 2 &&
    Math.abs(points[0].x) < 0.01 && Math.abs(points[0].y) < 0.01 &&
    Math.abs(points[1].x - 1) < 0.01 && Math.abs(points[1].y - 1) < 0.01;

  return (
    <div>
      {/* Channel tabs */}
      <div style={{ display: 'flex', gap: 2, marginBottom: 4 }}>
        {(['master', 'red', 'green', 'blue'] as CurveChannel[]).map((ch) => (
          <button
            key={ch}
            style={{
              ...TAB_STYLE,
              color: CHANNEL_COLORS[ch],
              background: activeChannel === ch ? '#222' : 'transparent',
              fontWeight: activeChannel === ch ? 600 : 400,
            }}
            onClick={() => setActiveChannel(ch)}
          >
            {ch === 'master' ? 'M' : ch[0].toUpperCase()}
          </button>
        ))}
        {!isIdentity && (
          <button
            style={{ ...TAB_STYLE, color: '#555', marginLeft: 'auto', fontSize: 9 }}
            onClick={handleReset}
          >
            Reset
          </button>
        )}
      </div>

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        style={{
          width: size,
          height: size,
          cursor: dragIndex !== null ? 'grabbing' : hoverIndex !== null ? 'grab' : 'crosshair',
          borderRadius: 3,
          border: '1px solid #222',
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onDoubleClick={handleDoubleClick}
      />
    </div>
  );
}

/** Convert CurveData to FFmpeg-compatible point strings for the curves filter */
export function curveDataToFFmpegStrings(data: CurveData): {
  master: string;
  red: string;
  green: string;
  blue: string;
} {
  const toStr = (pts: CurvePoint[]): string => {
    const sorted = [...pts].sort((a, b) => a.x - b.x);
    // Skip if identity
    if (sorted.length === 2 &&
      Math.abs(sorted[0].x) < 0.01 && Math.abs(sorted[0].y) < 0.01 &&
      Math.abs(sorted[1].x - 1) < 0.01 && Math.abs(sorted[1].y - 1) < 0.01) {
      return '';
    }
    return sorted.map((p) => `${p.x.toFixed(3)}/${p.y.toFixed(3)}`).join(' ');
  };
  return {
    master: toStr(data.master),
    red: toStr(data.red),
    green: toStr(data.green),
    blue: toStr(data.blue),
  };
}
