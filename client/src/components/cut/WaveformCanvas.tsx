/**
 * MARKER_170.NLE.WAVEFORM: Canvas-based waveform renderer for timeline clips.
 * Renders normalized 0-1 bins as vertical bars on a canvas.
 * Used inside clip blocks on the timeline.
 */
import { useRef, useEffect, type CSSProperties } from 'react';

type WaveformCanvasProps = {
  bins: number[];
  width: number;
  height: number;
  color?: string;
  bgColor?: string;
  cursorRatio?: number | null;
  cursorColor?: string;
  style?: CSSProperties;
};

export default function WaveformCanvas({
  bins,
  width,
  height,
  color = '#888',
  bgColor = 'transparent',
  cursorRatio = null,
  cursorColor = 'rgba(255, 255, 255, 0.92)',
  style,
}: WaveformCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !bins.length || width <= 0 || height <= 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    // Clear
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, width, height);

    // Draw waveform bars
    const barWidth = width / bins.length;
    const centerY = height / 2;
    ctx.fillStyle = color;

    for (let i = 0; i < bins.length; i++) {
      const amplitude = Math.max(0, Math.min(1, bins[i]));
      const barHeight = amplitude * height * 0.9; // 90% max height
      const x = i * barWidth;
      const y = centerY - barHeight / 2;
      ctx.fillRect(x, y, Math.max(1, barWidth - 0.5), barHeight);
    }

    if (cursorRatio != null) {
      const cursorX = Math.max(0, Math.min(width - 1, cursorRatio * width));
      ctx.fillStyle = cursorColor;
      ctx.fillRect(cursorX, 0, 1, height);
    }
  }, [bins, width, height, color, bgColor, cursorRatio, cursorColor]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        width,
        height,
        display: 'block',
        ...style,
      }}
    />
  );
}
