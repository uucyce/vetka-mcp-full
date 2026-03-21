/**
 * MARKER_CC3WAY: Color Wheel — FCP7-style circular color balance control.
 *
 * FCP7 Reference: Ch.79 "Color Corrector 3-Way" — circular wheels for
 * Shadows (Lift), Midtones (Gamma), Highlights (Gain).
 *
 * Architecture:
 *   - Canvas-based rendering (no SVG overhead)
 *   - Drag the center indicator to shift color balance
 *   - X-axis maps to R shift (right=+R, left=-R/+cyan)
 *   - Y-axis maps to B shift (down=+B, up=-B/+yellow)
 *   - G is derived: G = -(R + B) (complementary)
 *   - Double-click to reset to center
 *   - Ring shows hue gradient for reference
 *
 * @phase CC3WAY
 * @task tb_1773996062_12
 */
import { useRef, useEffect, useCallback, useState, type CSSProperties } from 'react';

interface ColorWheelProps {
  label: string;
  r: number;  // -1..1
  g: number;  // -1..1
  b: number;  // -1..1
  size?: number;
  onChange: (r: number, g: number, b: number) => void;
}

const CONTAINER: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: 4,
  userSelect: 'none',
};

const LABEL_STYLE: CSSProperties = {
  fontSize: 9,
  fontWeight: 600,
  color: '#666',
  textTransform: 'uppercase',
  letterSpacing: 0.5,
};

const VALUES_ROW: CSSProperties = {
  display: 'flex',
  gap: 6,
  fontSize: 8,
  fontFamily: '"JetBrains Mono", monospace',
};

export default function ColorWheel({
  label,
  r,
  g,
  b,
  size = 100,
  onChange,
}: ColorWheelProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [dragging, setDragging] = useState(false);
  const dragRef = useRef(false);

  const radius = size / 2 - 4;
  const cx = size / 2;
  const cy = size / 2;

  // Map RGB correction values to indicator position
  // R → right, B → down, G is inverse (derived)
  const indicatorX = cx + r * radius * 0.85;
  const indicatorY = cy + b * radius * 0.85;

  // Draw wheel
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);

    // Clear
    ctx.clearRect(0, 0, size, size);

    // Outer hue ring
    const ringWidth = 6;
    const outerR = radius;
    const innerR = radius - ringWidth;

    for (let angle = 0; angle < 360; angle += 1) {
      const rad = (angle * Math.PI) / 180;
      ctx.beginPath();
      ctx.arc(cx, cy, outerR, rad, rad + (2 * Math.PI) / 360);
      ctx.arc(cx, cy, innerR, rad + (2 * Math.PI) / 360, rad, true);
      ctx.closePath();
      ctx.fillStyle = `hsl(${angle}, 70%, 50%)`;
      ctx.fill();
    }

    // Inner dark fill
    ctx.beginPath();
    ctx.arc(cx, cy, innerR - 1, 0, Math.PI * 2);
    ctx.fillStyle = '#111';
    ctx.fill();

    // Crosshair at center
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    ctx.moveTo(cx - innerR + 4, cy);
    ctx.lineTo(cx + innerR - 4, cy);
    ctx.moveTo(cx, cy - innerR + 4);
    ctx.lineTo(cx, cy + innerR - 4);
    ctx.stroke();

    // Center dot
    ctx.beginPath();
    ctx.arc(cx, cy, 2, 0, Math.PI * 2);
    ctx.fillStyle = '#444';
    ctx.fill();

    // Indicator dot
    const ix = indicatorX;
    const iy = indicatorY;

    // Line from center to indicator
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(ix, iy);
    ctx.stroke();

    // Indicator circle
    ctx.beginPath();
    ctx.arc(ix, iy, 5, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
    ctx.fill();
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Color tint on indicator
    const tintR = Math.round(128 + r * 127);
    const tintG = Math.round(128 + g * 127);
    const tintB = Math.round(128 + b * 127);
    ctx.beginPath();
    ctx.arc(ix, iy, 3, 0, Math.PI * 2);
    ctx.fillStyle = `rgb(${tintR}, ${tintG}, ${tintB})`;
    ctx.fill();
  }, [size, radius, cx, cy, r, g, b, indicatorX, indicatorY]);

  const positionToRGB = useCallback(
    (clientX: number, clientY: number) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = clientX - rect.left;
      const y = clientY - rect.top;

      // Normalize to -1..1 from center
      let nx = (x - cx) / (radius * 0.85);
      let ny = (y - cy) / (radius * 0.85);

      // Clamp to circle
      const dist = Math.sqrt(nx * nx + ny * ny);
      if (dist > 1) {
        nx /= dist;
        ny /= dist;
      }

      // R = x-axis, B = y-axis, G = derived (opposite)
      const newR = Math.round(nx * 100) / 100;
      const newB = Math.round(ny * 100) / 100;
      const newG = Math.round(-((newR + newB) / 2) * 100) / 100;

      onChange(
        Math.max(-1, Math.min(1, newR)),
        Math.max(-1, Math.min(1, newG)),
        Math.max(-1, Math.min(1, newB)),
      );
    },
    [cx, cy, radius, onChange],
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragRef.current = true;
      setDragging(true);
      positionToRGB(e.clientX, e.clientY);
    },
    [positionToRGB],
  );

  useEffect(() => {
    if (!dragging) return;

    const handleMove = (e: MouseEvent) => {
      if (dragRef.current) {
        positionToRGB(e.clientX, e.clientY);
      }
    };

    const handleUp = () => {
      dragRef.current = false;
      setDragging(false);
    };

    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
    };
  }, [dragging, positionToRGB]);

  const handleDoubleClick = useCallback(() => {
    onChange(0, 0, 0);
  }, [onChange]);

  return (
    <div style={CONTAINER}>
      <span style={LABEL_STYLE}>{label}</span>
      <canvas
        ref={canvasRef}
        style={{
          width: size,
          height: size,
          cursor: dragging ? 'grabbing' : 'grab',
          borderRadius: '50%',
        }}
        onMouseDown={handleMouseDown}
        onDoubleClick={handleDoubleClick}
        data-testid={`color-wheel-${label.toLowerCase()}`}
      />
      <div style={VALUES_ROW}>
        <span style={{ color: '#e55' }}>R {r > 0 ? '+' : ''}{r.toFixed(2)}</span>
        <span style={{ color: '#4ade80' }}>G {g > 0 ? '+' : ''}{g.toFixed(2)}</span>
        <span style={{ color: '#4a9eff' }}>B {b > 0 ? '+' : ''}{b.toFixed(2)}</span>
      </div>
    </div>
  );
}
