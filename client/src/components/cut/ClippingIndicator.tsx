/**
 * MARKER_B32: Clipping Indicator — persistent red clip light for audio mixer.
 *
 * FCP7 Ch.55 (p.889): "The clipping indicator lights when the signal
 * exceeds 0 dBFS and stays lit until you click it or stop playback."
 *
 * Behavior:
 *   - Grey dot at rest
 *   - Red when level exceeds threshold (latched)
 *   - Stays red until clicked (reset) or onReset callback
 *   - Monochrome exception: red for clipping is functional, not decorative
 *
 * @phase B32
 * @task tb_1773996025_9
 */
import { useState, useEffect, useCallback, type CSSProperties } from 'react';

interface ClippingIndicatorProps {
  /** Current audio level (0.0 - 1.5+) */
  level: number;
  /** Threshold above which clipping is detected (default 0.95 = ~-0.4 dBFS) */
  threshold?: number;
  /** External reset trigger (e.g., playback stopped) */
  resetTrigger?: number;
  /** Size in pixels */
  size?: number;
}

export default function ClippingIndicator({
  level,
  threshold = 0.95,
  resetTrigger = 0,
  size = 6,
}: ClippingIndicatorProps) {
  const [clipped, setClipped] = useState(false);

  // Latch: once clipped, stays clipped until reset
  useEffect(() => {
    if (level >= threshold) {
      setClipped(true);
    }
  }, [level, threshold]);

  // Reset on external trigger (playback stop, etc.)
  useEffect(() => {
    if (resetTrigger > 0) {
      setClipped(false);
    }
  }, [resetTrigger]);

  // Click to reset
  const handleClick = useCallback(() => {
    setClipped(false);
  }, []);

  const style: CSSProperties = {
    width: size,
    height: size,
    borderRadius: '50%',
    background: clipped ? '#ef4444' : '#333',
    cursor: clipped ? 'pointer' : 'default',
    flexShrink: 0,
    transition: clipped ? 'none' : 'background 0.3s',
  };

  return (
    <div
      style={style}
      onClick={handleClick}
      title={clipped ? 'CLIP — click to reset' : 'No clipping'}
      data-testid="clipping-indicator"
    />
  );
}
