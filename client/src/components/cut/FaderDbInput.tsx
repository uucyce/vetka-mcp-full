/**
 * MARKER_B34: Fader dB Input — click-to-edit volume label with dB/% entry.
 *
 * FCP7 Ch.55 (p.888): Click the numeric field below a fader to type
 * an exact value. Supports both percentage and dB entry.
 *
 * Input parsing:
 *   - "85" or "85%" → 0.85 linear volume
 *   - "-6dB" or "-6" when ending with "dB" → convert from dB to linear
 *   - "+3.5dB" → 10^(3.5/20) ≈ 1.496
 *   - Enter to confirm, Escape to cancel
 *
 * @phase B34
 * @task tb_1773996025_9
 */
import { useState, useRef, useCallback, useEffect, type CSSProperties } from 'react';

interface FaderDbInputProps {
  /** Current volume (0.0 - 1.5) */
  volume: number;
  /** Called with new volume value */
  onVolumeChange: (v: number) => void;
  /** Display style */
  style?: CSSProperties;
}

/** Convert linear volume to dB string */
function volumeToDbStr(vol: number): string {
  if (vol <= 0) return '-inf';
  const db = 20 * Math.log10(vol);
  return `${db >= 0 ? '+' : ''}${db.toFixed(1)}dB`;
}

/** Parse user input to linear volume (0 - 1.5) */
function parseVolumeInput(input: string): number | null {
  const trimmed = input.trim().toLowerCase();
  if (!trimmed) return null;

  // dB input: "-6dB", "+3dB", "-6db", "0db"
  const dbMatch = trimmed.match(/^([+-]?\d+\.?\d*)\s*db$/);
  if (dbMatch) {
    const db = parseFloat(dbMatch[1]);
    if (isNaN(db)) return null;
    const linear = Math.pow(10, db / 20);
    return Math.max(0, Math.min(1.5, Math.round(linear * 100) / 100));
  }

  // Percentage input: "85", "85%", "150%"
  const pctMatch = trimmed.match(/^(\d+\.?\d*)\s*%?$/);
  if (pctMatch) {
    const pct = parseFloat(pctMatch[1]);
    if (isNaN(pct)) return null;
    return Math.max(0, Math.min(1.5, pct / 100));
  }

  return null;
}

const LABEL_STYLE: CSSProperties = {
  fontSize: 7,
  fontFamily: 'monospace',
  color: '#666',
  cursor: 'pointer',
  textAlign: 'center',
  userSelect: 'none',
  minWidth: 28,
};

const INPUT_STYLE: CSSProperties = {
  width: 36,
  fontSize: 7,
  fontFamily: 'monospace',
  color: '#ccc',
  background: '#1a1a1a',
  border: '1px solid #444',
  borderRadius: 2,
  textAlign: 'center',
  padding: '1px 2px',
  outline: 'none',
};

export default function FaderDbInput({
  volume,
  onVolumeChange,
  style,
}: FaderDbInputProps) {
  const [editing, setEditing] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when entering edit mode
  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.select();
    }
  }, [editing]);

  const startEdit = useCallback(() => {
    setInputValue(`${Math.round(volume * 100)}%`);
    setEditing(true);
  }, [volume]);

  const confirmEdit = useCallback(() => {
    const parsed = parseVolumeInput(inputValue);
    if (parsed !== null) {
      onVolumeChange(parsed);
    }
    setEditing(false);
  }, [inputValue, onVolumeChange]);

  const cancelEdit = useCallback(() => {
    setEditing(false);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      confirmEdit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      cancelEdit();
    }
  }, [confirmEdit, cancelEdit]);

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={confirmEdit}
        style={{ ...INPUT_STYLE, ...style }}
        data-testid="fader-db-input"
      />
    );
  }

  return (
    <div
      onClick={startEdit}
      style={{ ...LABEL_STYLE, ...style }}
      title={`${Math.round(volume * 100)}% (${volumeToDbStr(volume)}) — click to edit`}
      data-testid="fader-db-label"
    >
      {Math.round(volume * 100)}%
    </div>
  );
}

// Export for testing
export { parseVolumeInput, volumeToDbStr };
