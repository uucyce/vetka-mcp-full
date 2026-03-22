/**
 * MARKER_B12: Motion Controls — per-clip position, scale, rotation, opacity.
 *
 * Renders as a section in ClipInspector or standalone panel.
 * Stores transform data in clip.motion metadata.
 * Preview via CSS transform on video element.
 * Render via FFmpeg pad/scale/rotate/colorchannelmixer filters.
 */
import { useState, useCallback, useEffect, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

// ─── Types ───

interface MotionState {
  posX: number;
  posY: number;
  scaleX: number;
  scaleY: number;
  uniform: boolean;
  rotation: number;
  anchorX: number;
  anchorY: number;
  opacity: number;
  // MARKER_B4.1: Crop (FCP7 Ch.16)
  cropLeft: number;
  cropRight: number;
  cropTop: number;
  cropBottom: number;
}

const DEFAULT_MOTION: MotionState = {
  posX: 0, posY: 0,
  scaleX: 1, scaleY: 1, uniform: true,
  rotation: 0,
  anchorX: 0.5, anchorY: 0.5,
  opacity: 1,
  cropLeft: 0, cropRight: 0, cropTop: 0, cropBottom: 0,
};

// ─── Styles ───

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
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};

const ROW: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  marginBottom: 6,
  gap: 6,
};

const LABEL: CSSProperties = {
  color: '#666',
  fontSize: 10,
  width: 55,
  flexShrink: 0,
};

const INPUT: CSSProperties = {
  background: '#1a1a1a',
  color: '#ccc',
  border: '1px solid #333',
  borderRadius: 3,
  padding: '3px 6px',
  fontSize: 11,
  fontFamily: '"JetBrains Mono", monospace',
  width: 60,
  textAlign: 'right' as const,
};

const SLIDER: CSSProperties = {
  flex: 1,
  minWidth: 0,
};

const LINK_BTN: CSSProperties = {
  background: 'none',
  border: '1px solid #333',
  borderRadius: 3,
  color: '#888',
  cursor: 'pointer',
  fontSize: 10,
  padding: '2px 4px',
  fontFamily: 'system-ui',
};

const RESET_BTN: CSSProperties = {
  background: 'none',
  border: 'none',
  color: '#555',
  cursor: 'pointer',
  fontSize: 9,
  fontFamily: 'system-ui',
};

// ─── Component ───

export default function MotionControls() {
  const selectedClipId = useCutEditorStore((s) => s.selectedClipId);
  const lanes = useCutEditorStore((s) => s.lanes);

  const selectedClip = lanes
    .flatMap((l) => l.clips || [])
    .find((c) => c.clip_id === selectedClipId);

  // Load motion state from clip metadata
  const clipMotion = (selectedClip as any)?.motion as Partial<MotionState> | undefined;

  const [motion, setMotion] = useState<MotionState>({ ...DEFAULT_MOTION, ...clipMotion });

  useEffect(() => {
    const m = (selectedClip as any)?.motion;
    setMotion({ ...DEFAULT_MOTION, ...(m || {}) });
  }, [selectedClipId, selectedClip]);

  const updateField = useCallback((field: keyof MotionState, value: number | boolean) => {
    setMotion((prev) => {
      const next = { ...prev, [field]: value };
      // Uniform scale: keep X and Y in sync
      if (field === 'scaleX' && prev.uniform) next.scaleY = value as number;
      if (field === 'scaleY' && prev.uniform) next.scaleX = value as number;
      return next;
    });
  }, []);

  const applyMotion = useCallback(() => {
    if (!selectedClipId) return;
    const store = useCutEditorStore.getState();
    const updatedLanes = store.lanes.map((lane) => ({
      ...lane,
      clips: (lane.clips || []).map((clip) => {
        if (clip.clip_id !== selectedClipId) return clip;
        return { ...clip, motion };
      }),
    }));
    store.setLanes(updatedLanes);
  }, [selectedClipId, motion]);

  const resetMotion = useCallback(() => {
    setMotion({ ...DEFAULT_MOTION });
  }, []);

  // Auto-apply on change (debounced feel — immediate for now)
  useEffect(() => {
    if (!selectedClipId) return;
    const timer = setTimeout(applyMotion, 150);
    return () => clearTimeout(timer);
  }, [motion, selectedClipId, applyMotion]);

  if (!selectedClipId || !selectedClip) {
    return (
      <div style={SECTION}>
        <div style={SECTION_TITLE}><span>Motion</span></div>
        <div style={{ color: '#444', fontSize: 10, textAlign: 'center', padding: 8 }}>
          Select a clip
        </div>
      </div>
    );
  }

  const isModified = motion.posX !== 0 || motion.posY !== 0 ||
    motion.scaleX !== 1 || motion.scaleY !== 1 ||
    motion.rotation !== 0 || motion.opacity !== 1 ||
    motion.cropLeft !== 0 || motion.cropRight !== 0 ||
    motion.cropTop !== 0 || motion.cropBottom !== 0;

  return (
    <>
      {/* Position */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>
          <span>Position</span>
          {isModified && <button style={RESET_BTN} onClick={resetMotion}>Reset All</button>}
        </div>
        <div style={ROW}>
          <span style={LABEL}>X</span>
          <input
            type="number"
            style={INPUT}
            value={motion.posX}
            onChange={(e) => updateField('posX', Number(e.target.value))}
            step={1}
          />
          <span style={{ ...LABEL, width: 20, textAlign: 'center' }}>Y</span>
          <input
            type="number"
            style={INPUT}
            value={motion.posY}
            onChange={(e) => updateField('posY', Number(e.target.value))}
            step={1}
          />
        </div>
      </div>

      {/* Scale */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>
          <span>Scale</span>
          <button
            style={{ ...LINK_BTN, color: motion.uniform ? '#999' : '#555' }}
            onClick={() => updateField('uniform', !motion.uniform)}
            title={motion.uniform ? 'Linked (uniform)' : 'Independent X/Y'}
          >
            {motion.uniform ? '\u{1F517}' : '\u2194'}
          </button>
        </div>
        <div style={ROW}>
          <span style={LABEL}>Scale X</span>
          <input
            type="range"
            style={SLIDER}
            min={0.01} max={4} step={0.01}
            value={motion.scaleX}
            onChange={(e) => updateField('scaleX', Number(e.target.value))}
          />
          <input
            type="number"
            style={{ ...INPUT, width: 50 }}
            value={Math.round(motion.scaleX * 100)}
            onChange={(e) => updateField('scaleX', Number(e.target.value) / 100)}
            step={1}
          />
          <span style={{ color: '#555', fontSize: 10 }}>%</span>
        </div>
        {!motion.uniform && (
          <div style={ROW}>
            <span style={LABEL}>Scale Y</span>
            <input
              type="range"
              style={SLIDER}
              min={0.01} max={4} step={0.01}
              value={motion.scaleY}
              onChange={(e) => updateField('scaleY', Number(e.target.value))}
            />
            <input
              type="number"
              style={{ ...INPUT, width: 50 }}
              value={Math.round(motion.scaleY * 100)}
              onChange={(e) => updateField('scaleY', Number(e.target.value) / 100)}
              step={1}
            />
            <span style={{ color: '#555', fontSize: 10 }}>%</span>
          </div>
        )}
      </div>

      {/* Rotation */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}><span>Rotation</span></div>
        <div style={ROW}>
          <span style={LABEL}>Degrees</span>
          <input
            type="range"
            style={SLIDER}
            min={-360} max={360} step={0.5}
            value={motion.rotation}
            onChange={(e) => updateField('rotation', Number(e.target.value))}
          />
          <input
            type="number"
            style={{ ...INPUT, width: 55 }}
            value={motion.rotation}
            onChange={(e) => updateField('rotation', Number(e.target.value))}
            step={0.5}
          />
          <span style={{ color: '#555', fontSize: 10 }}>&deg;</span>
        </div>
      </div>

      {/* Opacity — MARKER_B4.1: with keyframe button */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}>
          <span>Opacity</span>
          <button
            style={RESET_BTN}
            title="Add keyframe at playhead"
            onClick={() => {
              if (!selectedClipId) return;
              const s = useCutEditorStore.getState();
              const clip = s.lanes.flatMap((l) => l.clips).find((c) => c.clip_id === selectedClipId);
              if (clip) {
                const relTime = s.currentTime - clip.start_sec;
                if (relTime >= 0) s.addKeyframe(selectedClipId, 'opacity', relTime, motion.opacity);
              }
            }}
          >
            ◆ KF
          </button>
        </div>
        <div style={ROW}>
          <span style={LABEL}>Value</span>
          <input
            type="range"
            style={SLIDER}
            min={0} max={1} step={0.01}
            value={motion.opacity}
            onChange={(e) => {
              updateField('opacity', Number(e.target.value));
              // MARKER_B3.2: auto-keyframe in record mode
              if (selectedClipId) {
                useCutEditorStore.getState().recordPropertyChange(selectedClipId, 'opacity', Number(e.target.value));
              }
            }}
          />
          <input
            type="number"
            style={{ ...INPUT, width: 50 }}
            value={Math.round(motion.opacity * 100)}
            onChange={(e) => updateField('opacity', Number(e.target.value) / 100)}
            step={1}
          />
          <span style={{ color: '#555', fontSize: 10 }}>%</span>
        </div>
      </div>

      {/* Crop — MARKER_B4.1 (FCP7 Ch.16) */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}><span>Crop</span></div>
        {(['cropLeft', 'cropRight', 'cropTop', 'cropBottom'] as const).map((field) => (
          <div style={ROW} key={field}>
            <span style={LABEL}>{field.replace('crop', '')}</span>
            <input
              type="range"
              style={SLIDER}
              min={0} max={100} step={1}
              value={motion[field] * 100}
              onChange={(e) => updateField(field, Number(e.target.value) / 100)}
            />
            <input
              type="number"
              style={{ ...INPUT, width: 50 }}
              value={Math.round(motion[field] * 100)}
              onChange={(e) => updateField(field, Number(e.target.value) / 100)}
              step={1}
            />
            <span style={{ color: '#555', fontSize: 10 }}>%</span>
          </div>
        ))}
      </div>

      {/* Anchor Point */}
      <div style={SECTION}>
        <div style={SECTION_TITLE}><span>Anchor Point</span></div>
        <div style={ROW}>
          <span style={LABEL}>X</span>
          <input
            type="range"
            style={SLIDER}
            min={0} max={1} step={0.01}
            value={motion.anchorX}
            onChange={(e) => updateField('anchorX', Number(e.target.value))}
          />
          <span style={{ ...LABEL, width: 20, textAlign: 'center' }}>Y</span>
          <input
            type="range"
            style={SLIDER}
            min={0} max={1} step={0.01}
            value={motion.anchorY}
            onChange={(e) => updateField('anchorY', Number(e.target.value))}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 4, marginTop: 4 }}>
          {[
            { label: 'TL', x: 0, y: 0 }, { label: 'T', x: 0.5, y: 0 }, { label: 'TR', x: 1, y: 0 },
            { label: 'L', x: 0, y: 0.5 }, { label: 'C', x: 0.5, y: 0.5 }, { label: 'R', x: 1, y: 0.5 },
            { label: 'BL', x: 0, y: 1 }, { label: 'B', x: 0.5, y: 1 }, { label: 'BR', x: 1, y: 1 },
          ].map((pt) => (
            <button
              key={pt.label}
              style={{
                ...LINK_BTN,
                fontSize: 8,
                padding: '2px 3px',
                color: motion.anchorX === pt.x && motion.anchorY === pt.y ? '#999' : '#555',
              }}
              onClick={() => { updateField('anchorX', pt.x); updateField('anchorY', pt.y); }}
              title={`Anchor ${pt.label}`}
            >
              {pt.label}
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
