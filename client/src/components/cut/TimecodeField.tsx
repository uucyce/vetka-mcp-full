/**
 * MARKER_W5.TC: TimecodeField — editable SMPTE timecode display.
 *
 * FCP7 Reference: Ch.8 "Navigating and Using Timecode", Ch.51 "Working with Timecode"
 * Click → edit mode → type timecode → Enter → seek to frame.
 *
 * Features:
 *   - HH:MM:SS:FF format with configurable FPS (23.976/24/25/29.97/30/50/59.94/60)
 *   - Drop-frame (;) vs non-drop (:) for 29.97/59.94
 *   - Relative entry: +10 = forward 10 frames, -1:00 = back 1 sec
 *   - Partial entry: 1419 → 00:00:14:19
 *   - Escape cancels edit
 */
import { useState, useRef, useCallback, useEffect, type CSSProperties } from 'react';

// ─── Pure functions (exported for testing) ────────────────────────

/**
 * Convert seconds to SMPTE timecode string.
 * Drop-frame only applies to 29.97 and 59.94 fps.
 */
export function formatTimecode(
  seconds: number,
  fps: number = 25,
  dropFrame: boolean = false,
): string {
  if (!isFinite(seconds) || seconds < 0) seconds = 0;

  const useDropFrame = dropFrame && (Math.abs(fps - 29.97) < 0.1 || Math.abs(fps - 59.94) < 0.1);
  const separator = useDropFrame ? ';' : ':';

  // Round to nearest frame
  const totalFrames = Math.round(seconds * fps);

  if (!useDropFrame) {
    // Non-drop-frame: straightforward division
    const roundFps = Math.round(fps);
    const f = totalFrames % roundFps;
    const totalSec = Math.floor(totalFrames / roundFps);
    const s = totalSec % 60;
    const totalMin = Math.floor(totalSec / 60);
    const m = totalMin % 60;
    const h = Math.floor(totalMin / 60);
    return `${pad2(h)}:${pad2(m)}:${pad2(s)}${separator}${pad2(f)}`;
  }

  // Drop-frame algorithm (SMPTE 12M)
  // For 29.97: drop 2 frame numbers per minute, except every 10th minute
  // For 59.94: drop 4 frame numbers per minute, except every 10th minute
  const dropFrames = Math.abs(fps - 29.97) < 0.1 ? 2 : 4;
  const framesPerMin = Math.round(fps) * 60 - dropFrames;
  const framesPer10Min = framesPerMin * 10 + dropFrames;

  let d = totalFrames;
  const d10 = Math.floor(d / framesPer10Min);
  let m10 = d % framesPer10Min;

  // Adjust for dropped frames at the start of non-10th minutes
  if (m10 < dropFrames) {
    m10 = dropFrames; // clamp to avoid negative
  }
  const frameAdjust = dropFrames * (Math.floor((m10 - dropFrames) / framesPerMin));
  d += d10 * dropFrames * 9 + frameAdjust;

  const roundFps = Math.round(fps);
  const f = d % roundFps;
  d = Math.floor(d / roundFps);
  const s = d % 60;
  d = Math.floor(d / 60);
  const m = d % 60;
  const h = Math.floor(d / 60);

  return `${pad2(h)}:${pad2(m)}:${pad2(s)}${separator}${pad2(f)}`;
}

/**
 * Parse timecode input string to seconds.
 *
 * Supports:
 *   - Full SMPTE: "01:02:03:04" or "01:02:03;04" (drop-frame)
 *   - Partial: "1419" → 14 sec + 19 frames
 *   - Relative: "+10" (forward 10 frames), "-1:00" (back 1 sec + 0 frames)
 *   - Seconds: "10.5" → 10.5 seconds
 *
 * Returns seconds, or null if unparseable.
 */
export function parseTimecodeInput(
  input: string,
  fps: number = 25,
  currentTime: number = 0,
): number | null {
  const trimmed = input.trim();
  if (!trimmed) return null;

  // Detect relative entry
  const isRelative = trimmed.startsWith('+') || trimmed.startsWith('-');
  const sign = trimmed.startsWith('-') ? -1 : 1;
  const body = isRelative ? trimmed.slice(1) : trimmed;

  // If contains a decimal point and no colons/semicolons, treat as raw seconds
  if (/^\d+\.\d+$/.test(body)) {
    const rawSec = parseFloat(body);
    if (isNaN(rawSec)) return null;
    return isRelative ? Math.max(0, currentTime + sign * rawSec) : rawSec;
  }

  // Split by : or ;
  const parts = body.split(/[:;]/);

  let h = 0, m = 0, s = 0, f = 0;

  if (parts.length === 1) {
    // Numeric-only input
    const num = parts[0];
    if (/^\d+$/.test(num)) {
      if (isRelative) {
        // Relative: treat as raw frame count (e.g. +10, -100)
        const rawFrames = parseInt(num, 10);
        return Math.max(0, currentTime + sign * rawFrames / fps);
      }
      if (num.length <= 3) {
        // Pure frame count
        f = parseInt(num, 10);
      } else {
        // FCP7-style: pad to 8 digits, split as HH MM SS FF
        const padded = num.padStart(8, '0');
        h = parseInt(padded.slice(0, 2), 10);
        m = parseInt(padded.slice(2, 4), 10);
        s = parseInt(padded.slice(4, 6), 10);
        f = parseInt(padded.slice(6, 8), 10);
      }
    } else {
      return null;
    }
  } else if (parts.length === 2) {
    // SS:FF
    s = parseInt(parts[0], 10) || 0;
    f = parseInt(parts[1], 10) || 0;
  } else if (parts.length === 3) {
    // MM:SS:FF
    m = parseInt(parts[0], 10) || 0;
    s = parseInt(parts[1], 10) || 0;
    f = parseInt(parts[2], 10) || 0;
  } else if (parts.length === 4) {
    // HH:MM:SS:FF
    h = parseInt(parts[0], 10) || 0;
    m = parseInt(parts[1], 10) || 0;
    s = parseInt(parts[2], 10) || 0;
    f = parseInt(parts[3], 10) || 0;
  } else {
    return null;
  }

  // Validate frame count
  const roundFps = Math.round(fps);
  if (f >= roundFps || f < 0) return null;
  if (s >= 60 || s < 0) return null;
  if (m >= 60 || m < 0) return null;
  if (h < 0) return null;

  const totalSeconds = h * 3600 + m * 60 + s + f / fps;

  if (isRelative) {
    return Math.max(0, currentTime + sign * totalSeconds);
  }
  return totalSeconds;
}

function pad2(n: number): string {
  return String(Math.abs(n)).padStart(2, '0');
}

// ─── Styles ───────────────────────────────────────────────────────

const FIELD_DISPLAY: CSSProperties = {
  fontFamily: '"JetBrains Mono", "SF Mono", "Consolas", monospace',
  fontSize: 11,
  color: '#fff',
  letterSpacing: 0.5,
  cursor: 'text',
  userSelect: 'none',
  padding: '1px 4px',
  borderRadius: 2,
  border: '1px solid transparent',
  background: 'transparent',
  lineHeight: '18px',
  whiteSpace: 'nowrap',
};

const FIELD_EDITING: CSSProperties = {
  ...FIELD_DISPLAY,
  background: '#1a1a2e',
  border: '1px solid #888',
  color: '#fff',
  cursor: 'text',
  outline: 'none',
  userSelect: 'auto',
  width: 90,
  textAlign: 'center',
};

// ─── Component ────────────────────────────────────────────────────

interface TimecodeFieldProps {
  /** Current time in seconds */
  seconds: number;
  /** Frames per second */
  fps?: number;
  /** Drop-frame mode (29.97/59.94 only) */
  dropFrame?: boolean;
  /** Called when user confirms a timecode entry */
  onSeek: (seconds: number) => void;
  /** Additional style overrides */
  style?: CSSProperties;
  /** CSS class name */
  className?: string;
  /** data-testid */
  testId?: string;
}

export default function TimecodeField({
  seconds,
  fps = 25,
  dropFrame = false,
  onSeek,
  style,
  className,
  testId = 'timecode-field',
}: TimecodeFieldProps) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const displayTC = formatTimecode(seconds, fps, dropFrame);

  const handleClick = useCallback(() => {
    setEditing(true);
    setEditValue('');
  }, []);

  // Auto-focus input when entering edit mode
  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const handleConfirm = useCallback(() => {
    const parsed = parseTimecodeInput(editValue, fps, seconds);
    if (parsed !== null) {
      onSeek(parsed);
    }
    setEditing(false);
  }, [editValue, fps, seconds, onSeek]);

  const handleCancel = useCallback(() => {
    setEditing(false);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleConfirm();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        handleCancel();
      }
      // Stop propagation so hotkeys don't fire while typing timecode
      e.stopPropagation();
    },
    [handleConfirm, handleCancel],
  );

  if (editing) {
    return (
      <input
        ref={inputRef}
        data-testid={`${testId}-input`}
        aria-label="timecode"
        type="text"
        value={editValue}
        placeholder={displayTC}
        onChange={(e) => setEditValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleConfirm}
        style={{ ...FIELD_EDITING, ...style }}
        className={className}
      />
    );
  }

  return (
    <span
      data-testid={testId}
      onClick={handleClick}
      style={{ ...FIELD_DISPLAY, ...style }}
      className={className}
      title="Click to type timecode"
    >
      {displayTC}
    </span>
  );
}
