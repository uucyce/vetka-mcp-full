/**
 * MARKER_GAMMA-P2: Schedule publish date-time picker.
 * Uses native datetime-local input — monochrome styling.
 */
import type { CSSProperties } from 'react';

const ROW: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  marginTop: 8,
};

const LABEL: CSSProperties = {
  color: '#888',
  fontSize: 10,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  flexShrink: 0,
};

const INPUT: CSSProperties = {
  background: '#111',
  border: '1px solid #333',
  borderRadius: 3,
  padding: '5px 8px',
  color: '#eee',
  fontSize: 12,
  fontFamily: 'inherit',
  outline: 'none',
  colorScheme: 'dark',
};

interface Props {
  value: Date | null;
  onChange: (date: Date | null) => void;
}

export function PublishScheduler({ value, onChange }: Props) {
  const isoValue = value
    ? new Date(value.getTime() - value.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
    : '';

  return (
    <div style={ROW} data-testid="publish-scheduler">
      <label style={LABEL}>Schedule</label>
      <input
        type="datetime-local"
        style={INPUT}
        value={isoValue}
        onChange={(e) => {
          onChange(e.target.value ? new Date(e.target.value) : null);
        }}
      />
      {value && (
        <button
          onClick={() => onChange(null)}
          style={{
            background: 'none',
            border: 'none',
            color: '#666',
            cursor: 'pointer',
            fontSize: 11,
          }}
        >
          Clear
        </button>
      )}
    </div>
  );
}
