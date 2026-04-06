/**
 * MARKER_GAMMA-TRACKS: Insert / Delete Tracks dialogs (FCP7 Sequence menu).
 *
 * Insert mode: choose count (1-4) + type (video/audio) → appends empty lanes.
 * Delete mode: list all lanes with clip count, checkboxes to select deletion.
 *
 * Lane naming convention:
 *   video → lane_type: 'video', lane_id: 'V{n}'
 *   audio → lane_type: 'audio', lane_id: 'A{n}'
 */
import { useState, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../../store/useCutEditorStore';
import { useOverlayEscapeClose } from '../../../hooks/useOverlayEscapeClose';

// ─── Styles ───

const OVERLAY: CSSProperties = {
  position: 'fixed', inset: 0, zIndex: 9999,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  background: 'rgba(0,0,0,0.6)',
};

const DIALOG: CSSProperties = {
  background: '#111', border: '1px solid #2a2a2a', borderRadius: 6,
  width: 320, fontFamily: 'system-ui', fontSize: 11, color: '#ccc',
  boxShadow: '0 12px 40px rgba(0,0,0,0.5)',
};

const HEADER: CSSProperties = {
  padding: '12px 14px 10px', borderBottom: '1px solid #1e1e1e',
  fontWeight: 600, fontSize: 13,
};

const BODY: CSSProperties = {
  padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10,
};

const LABEL: CSSProperties = {
  fontSize: 9, color: '#666', textTransform: 'uppercase', letterSpacing: 0.5,
  marginBottom: 4,
};

const ROW: CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
};

const SELECT: CSSProperties = {
  background: '#1a1a1a', color: '#ccc', border: '1px solid #333',
  borderRadius: 3, fontSize: 11, padding: '4px 8px', outline: 'none',
};

const NUMBER_INPUT: CSSProperties = {
  ...SELECT, width: 56, textAlign: 'right' as const,
};

const FOOTER: CSSProperties = {
  display: 'flex', justifyContent: 'flex-end', gap: 6,
  padding: '8px 14px', borderTop: '1px solid #1e1e1e',
};

const BTN: CSSProperties = {
  padding: '5px 14px', border: '1px solid #333', borderRadius: 4,
  background: '#1a1a1a', color: '#aaa', fontSize: 10, cursor: 'pointer',
};

const BTN_PRIMARY: CSSProperties = {
  ...BTN, background: '#222', color: '#ccc',
};

const LANE_ROW: CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 8,
  padding: '4px 0', borderBottom: '1px solid #1a1a1a', cursor: 'pointer',
};

const BADGE: CSSProperties = {
  fontSize: 8, padding: '1px 5px', borderRadius: 2,
  border: '1px solid #333', color: '#666', flexShrink: 0,
};

const WARN: CSSProperties = {
  fontSize: 9, color: '#666', padding: '6px 8px',
  background: '#0e0e0e', borderRadius: 3, marginTop: 4,
};

// ─── Helpers ───

function nextVideoId(lanes: { lane_id: string; lane_type: string }[]): string {
  const nums = lanes
    .filter((l) => l.lane_type.startsWith('video'))
    .map((l) => parseInt(l.lane_id.replace(/^V/, ''), 10))
    .filter((n) => !isNaN(n));
  return `V${nums.length > 0 ? Math.max(...nums) + 1 : 1}`;
}

function nextAudioId(lanes: { lane_id: string; lane_type: string }[]): string {
  const nums = lanes
    .filter((l) => l.lane_type.startsWith('audio'))
    .map((l) => parseInt(l.lane_id.replace(/^A/, ''), 10))
    .filter((n) => !isNaN(n));
  return `A${nums.length > 0 ? Math.max(...nums) + 1 : 1}`;
}

// ─── Insert mode ───

function InsertMode({ onClose }: { onClose: () => void }) {
  const [count, setCount] = useState(1);
  const [trackType, setTrackType] = useState<'video' | 'audio'>('video');

  const handleInsert = useCallback(() => {
    const s = useCutEditorStore.getState();
    const newLanes = [...s.lanes];
    for (let i = 0; i < count; i++) {
      const id = trackType === 'video'
        ? nextVideoId(newLanes)
        : nextAudioId(newLanes);
      newLanes.push({ lane_id: id, lane_type: trackType, clips: [] });
    }
    s.setLanes(newLanes);
    onClose();
  }, [count, trackType, onClose]);

  return (
    <>
      <div style={BODY}>
        <div>
          <div style={LABEL}>Number of tracks</div>
          <input
            type="number"
            style={NUMBER_INPUT}
            value={count}
            min={1}
            max={4}
            onChange={(e) => setCount(Math.max(1, Math.min(4, parseInt(e.target.value) || 1)))}
            data-testid="insert-tracks-count"
          />
        </div>
        <div>
          <div style={LABEL}>Track type</div>
          <div style={ROW}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
              <input
                type="radio"
                name="track-type"
                value="video"
                checked={trackType === 'video'}
                onChange={() => setTrackType('video')}
              />
              <span>Video</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
              <input
                type="radio"
                name="track-type"
                value="audio"
                checked={trackType === 'audio'}
                onChange={() => setTrackType('audio')}
              />
              <span>Audio</span>
            </label>
          </div>
        </div>
      </div>
      <div style={FOOTER}>
        <button style={BTN} onClick={onClose}>Cancel</button>
        <button style={BTN_PRIMARY} onClick={handleInsert} data-testid="insert-tracks-ok">
          Insert {count} track{count !== 1 ? 's' : ''}
        </button>
      </div>
    </>
  );
}

// ─── Delete mode ───

function DeleteMode({ onClose }: { onClose: () => void }) {
  const lanes = useCutEditorStore((s) => s.lanes);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggle = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const hasClips = (laneId: string) => {
    const lane = lanes.find((l) => l.lane_id === laneId);
    return (lane?.clips.length ?? 0) > 0;
  };

  const selectedWithClips = [...selected].filter(hasClips).length;

  const handleDelete = useCallback(() => {
    const s = useCutEditorStore.getState();
    s.setLanes(s.lanes.filter((l) => !selected.has(l.lane_id)));
    onClose();
  }, [selected, onClose]);

  return (
    <>
      <div style={BODY}>
        {lanes.length === 0 ? (
          <div style={{ color: '#555', fontSize: 11, textAlign: 'center', padding: 12 }}>
            No tracks to delete.
          </div>
        ) : (
          <>
            <div style={LABEL}>Select tracks to delete</div>
            <div style={{ maxHeight: 200, overflowY: 'auto' }}>
              {lanes.map((lane) => {
                const clipCount = lane.clips.length;
                const checked = selected.has(lane.lane_id);
                return (
                  <div
                    key={lane.lane_id}
                    style={{ ...LANE_ROW, opacity: checked ? 1 : 0.7 }}
                    onClick={() => toggle(lane.lane_id)}
                    data-testid={`delete-track-row-${lane.lane_id}`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle(lane.lane_id)}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <span style={{ flex: 1, fontFamily: 'monospace', fontSize: 11 }}>
                      {lane.lane_id}
                    </span>
                    <span style={BADGE}>{lane.lane_type}</span>
                    {clipCount > 0 && (
                      <span style={{ ...BADGE, color: '#888' }}>
                        {clipCount} clip{clipCount !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
            {selectedWithClips > 0 && (
              <div style={WARN}>
                {selectedWithClips} track{selectedWithClips !== 1 ? 's have' : ' has'} clips — they will be deleted.
              </div>
            )}
          </>
        )}
      </div>
      <div style={FOOTER}>
        <button style={BTN} onClick={onClose}>Cancel</button>
        <button
          style={selected.size > 0 ? BTN_PRIMARY : { ...BTN, opacity: 0.4, cursor: 'default' }}
          onClick={selected.size > 0 ? handleDelete : undefined}
          disabled={selected.size === 0}
          data-testid="delete-tracks-ok"
        >
          Delete {selected.size > 0 ? `${selected.size} track${selected.size !== 1 ? 's' : ''}` : '...'}
        </button>
      </div>
    </>
  );
}

// ─── Main export ───

export function InsertTracksDialog() {
  const show = useCutEditorStore((s) => s.showInsertTracksDialog);
  const close = useCallback(() => useCutEditorStore.getState().setShowInsertTracksDialog(false), []);
  // MARKER_GAMMA-ESC-HOOK: Escape closes overlay + data-overlay prevents escapeContext from firing
  useOverlayEscapeClose(close);
  if (!show) return null;
  return (
    <div style={OVERLAY} data-overlay="1" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div style={DIALOG} data-testid="insert-tracks-dialog">
        <div style={HEADER}>Insert Tracks</div>
        <InsertMode onClose={close} />
      </div>
    </div>
  );
}

export function DeleteTracksDialog() {
  const show = useCutEditorStore((s) => s.showDeleteTracksDialog);
  const close = useCallback(() => useCutEditorStore.getState().setShowDeleteTracksDialog(false), []);
  // MARKER_GAMMA-ESC-HOOK: Escape closes overlay + data-overlay prevents escapeContext from firing
  useOverlayEscapeClose(close);
  if (!show) return null;
  return (
    <div style={OVERLAY} data-overlay="1" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div style={DIALOG} data-testid="delete-tracks-dialog">
        <div style={HEADER}>Delete Tracks</div>
        <DeleteMode onClose={close} />
      </div>
    </div>
  );
}
