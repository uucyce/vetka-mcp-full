/**
 * MARKER_GAMMA-P2: Reframe mode selector — center / ai-track / manual.
 * Monochrome button group.
 */
import type { CSSProperties } from 'react';
import type { ReframeMode } from './types';

const GROUP: CSSProperties = {
  display: 'flex',
  gap: 1,
  borderRadius: 4,
  overflow: 'hidden',
};

const MODES: { value: ReframeMode; label: string }[] = [
  { value: 'center', label: 'Center' },
  { value: 'ai-track', label: 'AI Track' },
  { value: 'manual', label: 'Manual' },
];

interface Props {
  mode: ReframeMode;
  onChange: (mode: ReframeMode) => void;
  disabled?: boolean;
}

export function PublishReframeControls({ mode, onChange, disabled }: Props) {
  return (
    <div style={GROUP} data-testid="publish-reframe-controls">
      {MODES.map((m) => {
        const active = m.value === mode;
        const btnStyle: CSSProperties = {
          background: active ? '#555' : '#222',
          border: 'none',
          color: active ? '#fff' : '#888',
          fontSize: 11,
          padding: '5px 12px',
          cursor: disabled ? 'default' : 'pointer',
          opacity: disabled ? 0.4 : 1,
          fontFamily: 'system-ui, -apple-system, sans-serif',
        };
        return (
          <button
            key={m.value}
            style={btnStyle}
            onClick={() => !disabled && onChange(m.value)}
            data-testid={`reframe-${m.value}`}
          >
            {m.label}
          </button>
        );
      })}
    </div>
  );
}
