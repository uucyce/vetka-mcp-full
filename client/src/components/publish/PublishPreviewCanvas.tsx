/**
 * MARKER_GAMMA-P2: Aspect ratio preview canvas.
 * Shows source frame with crop rectangle overlay for the target aspect ratio.
 * Monochrome — crop guides in white dashed lines.
 */
import { useMemo, type CSSProperties } from 'react';
import type { ReframeMode } from './types';

const CANVAS: CSSProperties = {
  position: 'relative',
  width: '100%',
  aspectRatio: '16/9',
  background: '#0a0a0a',
  borderRadius: 4,
  overflow: 'hidden',
  border: '1px solid #333',
};

/** Parse "W:H" string into numeric ratio */
function parseAspect(ar: string): number {
  if (ar === 'any') return 16 / 9;
  const [w, h] = ar.split(':').map(Number);
  return (w && h) ? w / h : 16 / 9;
}

interface Props {
  sourceAspect?: string;
  targetAspect: string;
  reframeMode: ReframeMode;
}

export function PublishPreviewCanvas({ sourceAspect = '16:9', targetAspect, reframeMode }: Props) {
  const sourceRatio = parseAspect(sourceAspect);
  const targetRatio = parseAspect(targetAspect);

  const cropStyle = useMemo((): CSSProperties => {
    if (targetAspect === 'any' || Math.abs(sourceRatio - targetRatio) < 0.01) {
      // No crop needed — full frame
      return { inset: 0, position: 'absolute' };
    }

    // Calculate crop rectangle
    let cropW: number, cropH: number, left: number, top: number;

    if (targetRatio < sourceRatio) {
      // Target is taller (e.g. 9:16) — crop sides
      cropH = 100;
      cropW = (targetRatio / sourceRatio) * 100;
      top = 0;
      left = reframeMode === 'center' ? (100 - cropW) / 2 : 0;
    } else {
      // Target is wider — crop top/bottom
      cropW = 100;
      cropH = (sourceRatio / targetRatio) * 100;
      left = 0;
      top = reframeMode === 'center' ? (100 - cropH) / 2 : 0;
    }

    return {
      position: 'absolute',
      left: `${left}%`,
      top: `${top}%`,
      width: `${cropW}%`,
      height: `${cropH}%`,
      border: '2px dashed rgba(255,255,255,0.6)',
      borderRadius: 2,
      pointerEvents: 'none',
    };
  }, [sourceRatio, targetRatio, targetAspect, reframeMode]);

  return (
    <div style={CANVAS} data-testid="publish-preview-canvas">
      {/* Source frame placeholder */}
      <div style={{
        position: 'absolute', inset: 0,
        background: '#111',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#444', fontSize: 11, fontFamily: 'monospace',
      }}>
        {sourceAspect} source
      </div>
      {/* Crop overlay */}
      <div style={cropStyle} data-testid="publish-crop-overlay" />
      {/* Crop border is the visual indicator — no complex clip-path needed */}
      {/* Mode label */}
      <div style={{
        position: 'absolute', bottom: 4, right: 6,
        color: '#666', fontSize: 9, textTransform: 'uppercase',
      }}>
        {reframeMode}
      </div>
    </div>
  );
}
