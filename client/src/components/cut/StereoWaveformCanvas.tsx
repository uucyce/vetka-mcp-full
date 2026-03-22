/**
 * MARKER_B31: Stereo waveform canvas — L/R mirrored display for timeline clips.
 *
 * Renders left channel in top half (growing upward from center) and
 * right channel in bottom half (growing downward from center).
 * Like Premiere Pro / Logic Pro stereo waveform display.
 *
 * Uses same API pattern as WaveformCanvas for easy swap.
 *
 * @phase B31
 * @task tb_1774217997_6
 */
import { useRef, useEffect, type CSSProperties } from 'react';

type StereoWaveformCanvasProps = {
  /** Left channel bins (normalized 0-1) */
  binsLeft: number[];
  /** Right channel bins (normalized 0-1) */
  binsRight: number[];
  width: number;
  height: number;
  /** Left channel color */
  colorLeft?: string;
  /** Right channel color */
  colorRight?: string;
  bgColor?: string;
  /** Hover/seek cursor position 0-1 */
  cursorRatio?: number | null;
  cursorColor?: string;
  /** MARKER_B36: Playback cursor position 0-1 */
  playbackRatio?: number | null;
  playbackColor?: string;
  /** Show center divider line */
  showCenterLine?: boolean;
  /** Show L/R labels */
  showLabels?: boolean;
  style?: CSSProperties;
};

export default function StereoWaveformCanvas({
  binsLeft,
  binsRight,
  width,
  height,
  colorLeft = '#888',
  colorRight = '#888',
  bgColor = 'transparent',
  cursorRatio = null,
  cursorColor = 'rgba(255, 255, 255, 0.92)',
  playbackRatio = null,
  playbackColor = 'rgba(255, 255, 255, 0.55)',
  showCenterLine = true,
  showLabels = false,
  style,
}: StereoWaveformCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || width <= 0 || height <= 0) return;
    if (!binsLeft.length && !binsRight.length) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    // Clear
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, width, height);

    const centerY = height / 2;
    const halfH = centerY - 1; // 1px gap for center line
    const bins = Math.max(binsLeft.length, binsRight.length);
    if (bins === 0) return;
    const barWidth = width / bins;

    // Left channel — top half, growing upward from center
    ctx.fillStyle = colorLeft;
    for (let i = 0; i < binsLeft.length; i++) {
      const amplitude = Math.max(0, Math.min(1, binsLeft[i]));
      const barH = amplitude * halfH * 0.9;
      const x = i * barWidth;
      ctx.fillRect(x, centerY - barH, Math.max(1, barWidth - 0.5), barH);
    }

    // Right channel — bottom half, growing downward from center
    ctx.fillStyle = colorRight;
    for (let i = 0; i < binsRight.length; i++) {
      const amplitude = Math.max(0, Math.min(1, binsRight[i]));
      const barH = amplitude * halfH * 0.9;
      const x = i * barWidth;
      ctx.fillRect(x, centerY, Math.max(1, barWidth - 0.5), barH);
    }

    // Center divider line
    if (showCenterLine) {
      ctx.strokeStyle = '#444';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(0, centerY);
      ctx.lineTo(width, centerY);
      ctx.stroke();
    }

    // L/R labels (small, top-left / bottom-left)
    if (showLabels && width > 30 && height > 20) {
      ctx.fillStyle = '#555';
      ctx.font = '7px system-ui';
      ctx.fillText('L', 2, 8);
      ctx.fillText('R', 2, height - 2);
    }

    // MARKER_B36: Playback cursor
    if (playbackRatio != null) {
      const pbX = Math.max(0, Math.min(width - 1, playbackRatio * width));
      ctx.fillStyle = playbackColor;
      ctx.fillRect(pbX, 0, 1, height);
    }

    // Hover/seek cursor (on top)
    if (cursorRatio != null) {
      const cursorX = Math.max(0, Math.min(width - 1, cursorRatio * width));
      ctx.fillStyle = cursorColor;
      ctx.fillRect(cursorX, 0, 1, height);
    }
  }, [binsLeft, binsRight, width, height, colorLeft, colorRight, bgColor, cursorRatio, cursorColor, playbackRatio, playbackColor, showCenterLine, showLabels]);

  return (
    <canvas
      ref={canvasRef}
      data-testid="stereo-waveform-canvas"
      style={{
        width,
        height,
        display: 'block',
        ...style,
      }}
    />
  );
}
