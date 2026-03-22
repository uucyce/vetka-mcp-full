/**
 * MARKER_B10: Transitions Panel — apply transitions between adjacent clips.
 *
 * Transition types: crossfade, dissolve, dip-to-black, dip-to-white,
 * wipe (left/right/up/down). Duration adjustable 0.1-5s.
 * Click transition type → applies to selected cut point on timeline.
 * Renders via FFmpeg xfade/acrossfade in cut_render_engine.py.
 */
import { useState, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

// ─── Types ───

interface TransitionType {
  id: string;
  label: string;
  icon: string;        // unicode icon
  ffmpeg: string;      // FFmpeg xfade transition name
  description: string;
}

const TRANSITIONS: TransitionType[] = [
  { id: 'crossfade', label: 'Cross Dissolve', icon: '\u25A7', ffmpeg: 'fade', description: 'Smooth blend between clips' },
  { id: 'dissolve', label: 'Dissolve', icon: '\u25A8', ffmpeg: 'dissolve', description: 'Film-style dissolve' },
  { id: 'dip_to_black', label: 'Dip to Black', icon: '\u25A0', ffmpeg: 'fadeblack', description: 'Fade out to black, then in' },
  { id: 'dip_to_white', label: 'Dip to White', icon: '\u25A1', ffmpeg: 'fadewhite', description: 'Fade out to white, then in' },
  { id: 'wipe_left', label: 'Wipe Left', icon: '\u25C0', ffmpeg: 'wipeleft', description: 'Horizontal wipe left to right' },
  { id: 'wipe_right', label: 'Wipe Right', icon: '\u25B6', ffmpeg: 'wiperight', description: 'Horizontal wipe right to left' },
  { id: 'wipe_up', label: 'Wipe Up', icon: '\u25B2', ffmpeg: 'wipeup', description: 'Vertical wipe bottom to top' },
  { id: 'wipe_down', label: 'Wipe Down', icon: '\u25BC', ffmpeg: 'wipedown', description: 'Vertical wipe top to bottom' },
  { id: 'slide_left', label: 'Slide Left', icon: '\u21E0', ffmpeg: 'slideleft', description: 'Push slide left' },
  { id: 'slide_right', label: 'Slide Right', icon: '\u21E2', ffmpeg: 'slideright', description: 'Push slide right' },
];

const DURATIONS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0];

// ─── Styles ───

const PANEL: CSSProperties = {
  height: '100%',
  overflow: 'auto',
  background: '#0d0d0d',
  fontFamily: 'system-ui',
  fontSize: 11,
  color: '#ccc',
};

const SECTION: CSSProperties = {
  padding: '8px 10px',
  borderBottom: '1px solid #1a1a1a',
};

const SECTION_TITLE: CSSProperties = {
  fontSize: 10,
  color: '#555',
  textTransform: 'uppercase' as const,
  letterSpacing: 1,
  marginBottom: 8,
};

const GRID: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, 1fr)',
  gap: 4,
};

const TRANSITION_ITEM: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  padding: '8px 4px',
  borderRadius: 4,
  cursor: 'pointer',
  border: '1px solid transparent',
  transition: 'all 0.15s',
  background: '#111',
};

const TRANSITION_ITEM_SELECTED: CSSProperties = {
  ...TRANSITION_ITEM,
  border: '1px solid #4a9eff',
  background: '#1a1a2a',
};

const ICON: CSSProperties = {
  fontSize: 18,
  marginBottom: 4,
  color: '#888',
};

const LABEL: CSSProperties = {
  fontSize: 9,
  color: '#666',
  textAlign: 'center' as const,
};

const ROW: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: 8,
};

const SELECT: CSSProperties = {
  background: '#1a1a1a',
  color: '#ccc',
  border: '1px solid #333',
  borderRadius: 4,
  padding: '4px 8px',
  fontSize: 11,
  fontFamily: 'system-ui',
  cursor: 'pointer',
};

const BTN: CSSProperties = {
  width: '100%',
  padding: '8px',
  fontSize: 11,
  border: 'none',
  borderRadius: 4,
  cursor: 'pointer',
  fontFamily: 'system-ui',
  background: '#4a9eff',
  color: '#fff',
};

const BTN_REMOVE: CSSProperties = {
  ...BTN,
  background: '#333',
  color: '#888',
};

// ─── Component ───

export default function TransitionsPanel() {
  const selectedClipId = useCutEditorStore((s) => s.selectedClipId);
  const lanes = useCutEditorStore((s) => s.lanes);

  const [selectedTransition, setSelectedTransition] = useState('crossfade');
  const [duration, setDuration] = useState(1.0);

  // Find adjacent clip pairs for selected clip
  const selectedClip = lanes
    .flatMap((l) => l.clips || [])
    .find((c) => c.clip_id === selectedClipId);

  const applyTransition = useCallback(() => {
    if (!selectedClipId || !selectedClip) return;
    // Store transition in clip metadata via store action
    // This will be read by render engine's build_render_plan
    const store = useCutEditorStore.getState();
    const updatedLanes = store.lanes.map((lane) => ({
      ...lane,
      clips: (lane.clips || []).map((clip) => {
        if (clip.clip_id !== selectedClipId) return clip;
        return {
          ...clip,
          transition: {
            type: selectedTransition,
            duration_sec: duration,
            ffmpeg: TRANSITIONS.find((t) => t.id === selectedTransition)?.ffmpeg || 'fade',
          },
        };
      }),
    }));
    store.setLanes(updatedLanes);
  }, [selectedClipId, selectedClip, selectedTransition, duration]);

  const removeTransition = useCallback(() => {
    if (!selectedClipId) return;
    const store = useCutEditorStore.getState();
    const updatedLanes = store.lanes.map((lane) => ({
      ...lane,
      clips: (lane.clips || []).map((clip) => {
        if (clip.clip_id !== selectedClipId) return clip;
        const { transition: _, ...rest } = clip as any;
        return rest;
      }),
    }));
    store.setLanes(updatedLanes);
  }, [selectedClipId]);

  const currentTransition = (selectedClip as any)?.transition;

  return (
    <div style={PANEL} data-testid="transitions-panel">
      {/* Header */}
      <div style={{ ...SECTION, background: '#0d0d0d' }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#fff' }}>Transitions</div>
        <div style={{ fontSize: 9, color: '#444', marginTop: 2 }}>
          {selectedClipId ? `Clip: ${selectedClipId.slice(0, 12)}...` : 'Select a clip on timeline'}
        </div>
      </div>

      {/* Duration */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Duration</div>
        <div style={ROW}>
          <span style={{ color: '#888' }}>Length</span>
          <select
            style={SELECT}
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            data-testid="transition-duration"
          >
            {DURATIONS.map((d) => (
              <option key={d} value={d}>{d}s</option>
            ))}
          </select>
        </div>
      </div>

      {/* Transition grid */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>Type</div>
        <div style={GRID}>
          {TRANSITIONS.map((t) => (
            <div
              key={t.id}
              data-testid={`transition-type-${t.id}`}
              style={selectedTransition === t.id ? TRANSITION_ITEM_SELECTED : TRANSITION_ITEM}
              onClick={() => setSelectedTransition(t.id)}
              title={t.description}
              onMouseEnter={(e) => {
                if (selectedTransition !== t.id) {
                  (e.currentTarget as HTMLDivElement).style.background = '#1a1a1a';
                }
              }}
              onMouseLeave={(e) => {
                if (selectedTransition !== t.id) {
                  (e.currentTarget as HTMLDivElement).style.background = '#111';
                }
              }}
            >
              <span style={ICON}>{t.icon}</span>
              <span style={LABEL}>{t.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Current transition info */}
      {currentTransition && (
        <div style={SECTION}>
          <div style={SECTION_TITLE}>Applied</div>
          <div style={ROW}>
            <span style={{ color: '#888' }}>Type</span>
            <span style={{ color: '#4a9eff' }}>
              {TRANSITIONS.find((t) => t.id === currentTransition.type)?.label || currentTransition.type}
            </span>
          </div>
          <div style={ROW}>
            <span style={{ color: '#888' }}>Duration</span>
            <span style={{ color: '#ccc' }}>{currentTransition.duration_sec}s</span>
          </div>
        </div>
      )}

      {/* Apply / Remove buttons */}
      <div style={{ ...SECTION, display: 'flex', flexDirection: 'column', gap: 6 }}>
        <button
          style={{ ...BTN, opacity: selectedClipId ? 1 : 0.4 }}
          onClick={applyTransition}
          disabled={!selectedClipId}
        >
          Apply {TRANSITIONS.find((t) => t.id === selectedTransition)?.label}
        </button>
        {currentTransition && (
          <button style={BTN_REMOVE} onClick={removeTransition}>
            Remove Transition
          </button>
        )}
      </div>
    </div>
  );
}
