/**
 * MARKER_B11: Clip Speed Control — per-clip speed adjustment.
 *
 * Speed range: 0.25x to 4x + reverse.
 * Options: maintain audio pitch, reverse playback.
 * Stores speed in clip metadata, render engine handles via setpts/atempo.
 * Opens as popover/dialog for selected clip.
 */
import { useState, useCallback, useEffect, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

// ─── Presets ───

interface SpeedPreset {
  label: string;
  rate: number;
}

const SPEED_PRESETS: SpeedPreset[] = [
  { label: '0.25x', rate: 0.25 },
  { label: '0.5x', rate: 0.5 },
  { label: '0.75x', rate: 0.75 },
  { label: '1x', rate: 1.0 },
  { label: '1.5x', rate: 1.5 },
  { label: '2x', rate: 2.0 },
  { label: '3x', rate: 3.0 },
  { label: '4x', rate: 4.0 },
];

// ─── Styles ───

const PANEL: CSSProperties = {
  background: '#111',
  border: '1px solid #2a2a2a',
  borderRadius: 8,
  width: 320,
  fontFamily: 'system-ui',
  fontSize: 11,
  color: '#ccc',
  boxShadow: '0 12px 40px rgba(0,0,0,0.5)',
};

const HEADER: CSSProperties = {
  padding: '12px 14px 8px',
  borderBottom: '1px solid #1e1e1e',
  fontWeight: 600,
  fontSize: 13,
};

const SECTION: CSSProperties = {
  padding: '10px 14px',
  borderBottom: '1px solid #1a1a1a',
};

const SECTION_TITLE: CSSProperties = {
  fontSize: 10,
  color: '#555',
  textTransform: 'uppercase' as const,
  letterSpacing: 1,
  marginBottom: 8,
};

const ROW: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: 8,
};

const LABEL: CSSProperties = {
  color: '#888',
  fontSize: 11,
};

const VALUE: CSSProperties = {
  color: '#ccc',
  fontFamily: '"JetBrains Mono", monospace',
  fontSize: 12,
};

const PRESET_GRID: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(4, 1fr)',
  gap: 4,
};

const PRESET_BTN: CSSProperties = {
  padding: '6px 2px',
  fontSize: 10,
  border: '1px solid #333',
  borderRadius: 4,
  background: '#1a1a1a',
  color: '#888',
  cursor: 'pointer',
  textAlign: 'center' as const,
  fontFamily: '"JetBrains Mono", monospace',
  transition: 'all 0.15s',
};

const PRESET_BTN_ACTIVE: CSSProperties = {
  ...PRESET_BTN,
  border: '1px solid #4a9eff',
  background: '#1a1a2a',
  color: '#4a9eff',
};

const SLIDER_ROW: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
};

const FOOTER: CSSProperties = {
  padding: '10px 14px',
  display: 'flex',
  justifyContent: 'flex-end',
  gap: 8,
};

const BTN: CSSProperties = {
  padding: '6px 16px',
  fontSize: 11,
  border: 'none',
  borderRadius: 4,
  cursor: 'pointer',
  fontFamily: 'system-ui',
};

const BTN_PRIMARY: CSSProperties = { ...BTN, background: '#4a9eff', color: '#fff' };
const BTN_SECONDARY: CSSProperties = { ...BTN, background: '#333', color: '#ccc' };

// ─── Component ───

interface SpeedControlProps {
  onClose?: () => void;
}

export default function SpeedControl({ onClose }: SpeedControlProps) {
  const selectedClipId = useCutEditorStore((s) => s.selectedClipId);
  const lanes = useCutEditorStore((s) => s.lanes);

  // Find selected clip
  const selectedClip = lanes
    .flatMap((l) => l.clips || [])
    .find((c) => c.clip_id === selectedClipId);

  const currentSpeed = (selectedClip as any)?.speed ?? 1.0;
  const currentReverse = (selectedClip as any)?.reverse ?? false;

  const [speed, setSpeed] = useState(currentSpeed);
  const [reverse, setReverse] = useState(currentReverse);
  const [maintainPitch, setMaintainPitch] = useState(true);

  // Sync with selected clip
  useEffect(() => {
    setSpeed((selectedClip as any)?.speed ?? 1.0);
    setReverse((selectedClip as any)?.reverse ?? false);
  }, [selectedClipId, selectedClip]);

  // Computed new duration
  const originalDuration = (selectedClip as any)?.duration_sec ?? 0;
  const newDuration = speed > 0 ? originalDuration / speed : originalDuration;

  const applySpeed = useCallback(() => {
    if (!selectedClipId) return;
    const store = useCutEditorStore.getState();
    const updatedLanes = store.lanes.map((lane) => ({
      ...lane,
      clips: (lane.clips || []).map((clip) => {
        if (clip.clip_id !== selectedClipId) return clip;
        return {
          ...clip,
          speed,
          reverse,
          maintain_pitch: maintainPitch,
          duration_sec: newDuration,
        };
      }),
    }));
    store.setLanes(updatedLanes);
    onClose?.();
  }, [selectedClipId, speed, reverse, maintainPitch, newDuration, onClose]);

  const resetSpeed = useCallback(() => {
    setSpeed(1.0);
    setReverse(false);
  }, []);

  if (!selectedClipId || !selectedClip) {
    return (
      <div style={PANEL}>
        <div style={HEADER}>Speed / Duration</div>
        <div style={{ ...SECTION, color: '#555', textAlign: 'center', padding: 24 }}>
          Select a clip on the timeline
        </div>
      </div>
    );
  }

  return (
    <div style={PANEL}>
      <div style={HEADER}>Speed / Duration</div>

      {/* Speed presets */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Presets</div>
        <div style={PRESET_GRID}>
          {SPEED_PRESETS.map((p) => (
            <div
              key={p.rate}
              style={Math.abs(speed - p.rate) < 0.01 ? PRESET_BTN_ACTIVE : PRESET_BTN}
              onClick={() => setSpeed(p.rate)}
            >
              {p.label}
            </div>
          ))}
        </div>
      </div>

      {/* Custom speed slider */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Custom Speed</div>
        <div style={SLIDER_ROW}>
          <input
            type="range"
            min={0.25}
            max={4}
            step={0.05}
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
            style={{ flex: 1 }}
          />
          <span style={{ ...VALUE, width: 44, textAlign: 'right' }}>{speed.toFixed(2)}x</span>
        </div>
      </div>

      {/* Duration info */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Result</div>
        <div style={ROW}>
          <span style={LABEL}>Original</span>
          <span style={VALUE}>{originalDuration.toFixed(2)}s</span>
        </div>
        <div style={ROW}>
          <span style={LABEL}>New Duration</span>
          <span style={{ ...VALUE, color: speed !== 1 ? '#4a9eff' : '#ccc' }}>
            {newDuration.toFixed(2)}s
          </span>
        </div>
        <div style={ROW}>
          <span style={LABEL}>Speed Change</span>
          <span style={{ ...VALUE, color: speed > 1 ? '#4ade80' : speed < 1 ? '#facc15' : '#ccc' }}>
            {speed > 1 ? `${((speed - 1) * 100).toFixed(0)}% faster` :
             speed < 1 ? `${((1 - speed) * 100).toFixed(0)}% slower` : 'Normal'}
          </span>
        </div>
      </div>

      {/* Options */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Options</div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={reverse}
            onChange={(e) => setReverse(e.target.checked)}
          />
          <span style={{ color: '#ccc', fontSize: 11 }}>Reverse playback</span>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={maintainPitch}
            onChange={(e) => setMaintainPitch(e.target.checked)}
          />
          <span style={{ color: '#ccc', fontSize: 11 }}>Maintain audio pitch</span>
        </label>
      </div>

      {/* Footer */}
      <div style={FOOTER}>
        <button style={BTN_SECONDARY} onClick={resetSpeed}>Reset</button>
        <button style={BTN_SECONDARY} onClick={onClose}>Cancel</button>
        <button
          style={{ ...BTN_PRIMARY, opacity: speed !== currentSpeed || reverse !== currentReverse ? 1 : 0.5 }}
          onClick={applySpeed}
        >
          Apply
        </button>
      </div>
    </div>
  );
}
