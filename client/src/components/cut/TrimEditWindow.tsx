// MARKER_TRIM_WINDOW: Floating two-up trim display (FCP7 Ch.45-46)
// Shows outgoing frame (left) + incoming frame (right) at edit point.
// Monochrome only. Position: fixed overlay.

import { useCutEditorStore } from '../../store/useCutEditorStore';
import { useEffect, useState, useCallback, type CSSProperties } from 'react';
import { useOverlayEscapeClose } from '../../hooks/useOverlayEscapeClose';

export default function TrimEditWindow() {
  const active = useCutEditorStore((s) => s.trimEditActive);
  const clipId = useCutEditorStore((s) => s.trimEditClipId);
  const editPoint = useCutEditorStore((s) => s.trimEditPoint);
  const lanes = useCutEditorStore((s) => s.lanes);
  const projectFramerate = useCutEditorStore((s) => s.projectFramerate);

  const [trimFrames, setTrimFrames] = useState(0);

  if (!active || !clipId) return null;

  // Find outgoing clip (ends at editPoint) and incoming clip (starts at editPoint)
  let outgoingClip: any = null, incomingClip: any = null;
  for (const lane of lanes) {
    for (let i = 0; i < lane.clips.length; i++) {
      const c = lane.clips[i];
      const cEnd = c.start_sec + c.duration_sec;
      if (Math.abs(cEnd - editPoint) < 0.05) {
        outgoingClip = c;
        if (i + 1 < lane.clips.length) incomingClip = lane.clips[i + 1];
      }
    }
  }

  const close = useCallback(() => useCutEditorStore.getState().setTrimEditActive(false), []);

  // MARKER_GAMMA-ESC-HOOK: Escape closes overlay + data-overlay prevents escapeContext from firing
  useOverlayEscapeClose(close);

  // Apply trim: shift edit point by trimFrames
  const applyTrim = () => {
    if (trimFrames === 0 || !outgoingClip) return;
    const deltaSec = trimFrames / (projectFramerate || 25);
    useCutEditorStore.getState().applyTimelineOps([
      { op: 'trim_clip', clip_id: outgoingClip.clip_id,
        duration_sec: outgoingClip.duration_sec + deltaSec }
    ]);
    close();
  };

  // Enter to apply (Escape handled by useOverlayEscapeClose above)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Enter') applyTrim();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  });

  const fps = projectFramerate || 25;
  const outTC = outgoingClip
    ? formatFrames(outgoingClip.start_sec + outgoingClip.duration_sec, fps)
    : '--:--:--:--';
  const inTC = incomingClip
    ? formatFrames(incomingClip.start_sec, fps)
    : '--:--:--:--';

  return (
    <div style={OVERLAY} data-overlay="1" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div style={WINDOW}>
        <div style={HEADER}>
          <span style={{ fontSize: 11, color: '#aaa' }}>TRIM EDIT</span>
          <button onClick={close} style={CLOSE_BTN}>X</button>
        </div>
        <div style={FRAMES_ROW}>
          <div style={FRAME_BOX}>
            <div style={FRAME_LABEL}>OUTGOING</div>
            <div style={FRAME_PREVIEW}>{outgoingClip?.clip_id?.split('/').pop() || '—'}</div>
            <div style={FRAME_TC}>{outTC}</div>
          </div>
          <div style={{ width: 2, background: '#333', alignSelf: 'stretch' }} />
          <div style={FRAME_BOX}>
            <div style={FRAME_LABEL}>INCOMING</div>
            <div style={FRAME_PREVIEW}>{incomingClip?.clip_id?.split('/').pop() || '—'}</div>
            <div style={FRAME_TC}>{inTC}</div>
          </div>
        </div>
        <div style={TRIM_INPUT_ROW}>
          <label style={{ fontSize: 10, color: '#888' }}>Trim offset (frames):</label>
          <input
            type="number"
            value={trimFrames}
            onChange={(e) => setTrimFrames(parseInt(e.target.value) || 0)}
            style={TRIM_INPUT}
            autoFocus
          />
          <button onClick={applyTrim} style={APPLY_BTN}>Apply</button>
        </div>
      </div>
    </div>
  );
}

function formatFrames(sec: number, fps: number): string {
  const totalFrames = Math.round(sec * fps);
  const f = totalFrames % fps;
  const s = Math.floor(totalFrames / fps) % 60;
  const m = Math.floor(totalFrames / fps / 60) % 60;
  const h = Math.floor(totalFrames / fps / 3600);
  return `${pad(h)}:${pad(m)}:${pad(s)}:${pad(f)}`;
}
function pad(n: number): string { return n.toString().padStart(2, '0'); }

// Styles — monochrome dark
const OVERLAY: CSSProperties = {
  position: 'fixed', inset: 0, zIndex: 9999,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  background: 'rgba(0,0,0,0.6)',
};
const WINDOW: CSSProperties = {
  background: '#1a1a1a', border: '1px solid #333',
  borderRadius: 4, padding: 12, minWidth: 420,
};
const HEADER: CSSProperties = {
  display: 'flex', justifyContent: 'space-between',
  alignItems: 'center', marginBottom: 8,
};
const CLOSE_BTN: CSSProperties = {
  background: 'none', border: 'none', color: '#888',
  cursor: 'pointer', fontSize: 12,
};
const FRAMES_ROW: CSSProperties = {
  display: 'flex', gap: 0, marginBottom: 10,
};
const FRAME_BOX: CSSProperties = {
  flex: 1, display: 'flex', flexDirection: 'column',
  alignItems: 'center', gap: 4,
};
const FRAME_LABEL: CSSProperties = {
  fontSize: 9, color: '#666', textTransform: 'uppercase', letterSpacing: 1,
};
const FRAME_PREVIEW: CSSProperties = {
  width: '100%', height: 120, background: '#0a0a0a',
  border: '1px solid #222', display: 'flex',
  alignItems: 'center', justifyContent: 'center',
  color: '#555', fontSize: 10,
};
const FRAME_TC: CSSProperties = {
  fontSize: 10, color: '#aaa', fontFamily: 'monospace',
};
const TRIM_INPUT_ROW: CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 8,
};
const TRIM_INPUT: CSSProperties = {
  width: 60, background: '#111', border: '1px solid #333',
  color: '#ddd', padding: '2px 6px', fontSize: 11,
  borderRadius: 2, textAlign: 'center',
};
const APPLY_BTN: CSSProperties = {
  background: '#333', border: '1px solid #555', color: '#ccc',
  padding: '3px 12px', fontSize: 10, borderRadius: 2, cursor: 'pointer',
};
