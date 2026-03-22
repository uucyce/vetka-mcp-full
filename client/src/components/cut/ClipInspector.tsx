/**
 * MARKER_170.NLE.INSPECTOR: Right-side inspector panel showing selected clip properties.
 * Displays: filename, timing, sync info, waveform mini, transcript excerpt, markers.
 */
import { useMemo, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import WaveformCanvas from './WaveformCanvas';
import MotionControls from './MotionControls'; // MARKER_B4.1

// ─── Styles ───
const SECTION: CSSProperties = {
  padding: '8px 10px',
  borderBottom: '1px solid #1a1a1a',
};

const HEADER: CSSProperties = {
  fontSize: 10,
  color: '#555',
  textTransform: 'uppercase',
  letterSpacing: 1,
  marginBottom: 6,
  userSelect: 'none',
};

const ROW: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: 11,
  marginBottom: 3,
};

const LABEL: CSSProperties = {
  color: '#666',
};

const VALUE: CSSProperties = {
  color: '#ccc',
  fontFamily: '"JetBrains Mono", monospace',
  fontSize: 11,
};

const SYNC_BADGE: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 4,
  padding: '2px 6px',
  borderRadius: 3,
  fontSize: 10,
  fontWeight: 500,
};

const MARKER_ITEM: CSSProperties = {
  padding: '3px 0',
  borderBottom: '1px solid #111',
  fontSize: 10,
};

const EMPTY: CSSProperties = {
  padding: 20,
  color: '#333',
  textAlign: 'center',
  fontSize: 11,
  userSelect: 'none',
};

function basename(path: string): string {
  return path.split('/').pop()?.split('\\').pop() || path;
}

function formatTC(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  const ms = Math.floor((sec % 1) * 1000);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(3, '0')}`;
}

const SYNC_COLORS: Record<string, string> = {
  timecode: '#22c55e',
  waveform: '#3b82f6',
  meta_sync: '#a855f7',
};

const MARKER_COLORS: Record<string, string> = {
  favorite: '#f59e0b',
  comment: '#3b82f6',
  cam: '#a855f7',
  insight: '#22c55e',
};

export default function ClipInspector() {
  const selectedClipId = useCutEditorStore((s) => s.selectedClipId);
  const activeMediaPath = useCutEditorStore((s) => s.activeMediaPath);
  const lanes = useCutEditorStore((s) => s.lanes);
  const waveforms = useCutEditorStore((s) => s.waveforms);
  const syncSurface = useCutEditorStore((s) => s.syncSurface);
  const markers = useCutEditorStore((s) => s.markers);
  const thumbnails = useCutEditorStore((s) => s.thumbnails);

  // Find selected clip
  const clip = useMemo(() => {
    if (!selectedClipId) return null;
    for (const lane of lanes) {
      const found = lane.clips.find((c) => c.clip_id === selectedClipId);
      if (found) return { ...found, lane_type: lane.lane_type };
    }
    return null;
  }, [selectedClipId, lanes]);

  // Find waveform for this clip
  const waveformBins = useMemo(() => {
    if (!clip) return null;
    return waveforms.find((w) => w.source_path === clip.source_path)?.waveform_bins || null;
  }, [clip, waveforms]);

  // Find sync surface item
  const syncItem = useMemo(() => {
    if (!clip) return null;
    return syncSurface.find((s) => s.source_path === clip.source_path) || null;
  }, [clip, syncSurface]);

  // Find markers for this clip's media
  const clipMarkers = useMemo(() => {
    if (!clip) return [];
    return markers.filter((m) => m.media_path === clip.source_path);
  }, [clip, markers]);

  // Find thumbnail
  const thumb = useMemo(() => {
    if (!clip) return null;
    return thumbnails.find((t) => t.source_path === clip.source_path) || null;
  }, [clip, thumbnails]);

  if (!clip) {
    return (
      <div style={EMPTY}>
        {activeMediaPath ? (
          <>
            <div style={{ marginBottom: 4, color: '#555' }}>Media selected</div>
            <div style={{ fontSize: 10, color: '#444', wordBreak: 'break-all' }}>{basename(activeMediaPath)}</div>
          </>
        ) : (
          <>Select a clip to inspect</>
        )}
      </div>
    );
  }

  const syncColor = syncItem?.recommended_method ? SYNC_COLORS[syncItem.recommended_method] || '#888' : '#888';
  const endSec = clip.start_sec + clip.duration_sec;

  return (
    <div>
      {/* Header */}
      <div style={{ ...SECTION, background: '#0d0d0d' }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#fff', marginBottom: 2 }}>
          {basename(clip.source_path)}
        </div>
        <div style={{ fontSize: 10, color: '#555' }}>
          {clip.clip_id} · {(clip as any).lane_type || 'unknown'}
        </div>
      </div>

      {/* Timing */}
      <div style={SECTION}>
        <div style={HEADER}>Timing</div>
        <div style={ROW}><span style={LABEL}>In</span><span style={VALUE}>{formatTC(clip.start_sec)}</span></div>
        <div style={ROW}><span style={LABEL}>Out</span><span style={VALUE}>{formatTC(endSec)}</span></div>
        <div style={ROW}><span style={LABEL}>Duration</span><span style={VALUE}>{formatTC(clip.duration_sec)}</span></div>
        {clip.scene_id && (
          <div style={ROW}><span style={LABEL}>Scene</span><span style={VALUE}>{clip.scene_id}</span></div>
        )}
      </div>

      {/* MARKER_B4.1: Motion / Effects Inspector (Transform, Opacity, Crop) */}
      <MotionControls />

      {/* Sync Info */}
      {(syncItem || clip.sync) && (
        <div style={SECTION}>
          <div style={HEADER}>Sync</div>
          {clip.sync && (
            <div style={{ marginBottom: 4 }}>
              <span
                style={{
                  ...SYNC_BADGE,
                  background: `${SYNC_COLORS[clip.sync.method || ''] || '#888'}22`,
                  color: SYNC_COLORS[clip.sync.method || ''] || '#888',
                  border: `1px solid ${SYNC_COLORS[clip.sync.method || ''] || '#888'}44`,
                }}
              >
                ⟲ {clip.sync.method}
              </span>
              <div style={{ ...ROW, marginTop: 4 }}>
                <span style={LABEL}>Offset</span>
                <span style={VALUE}>{Number(clip.sync.offset_sec || 0).toFixed(3)}s</span>
              </div>
              <div style={ROW}>
                <span style={LABEL}>Confidence</span>
                <span style={VALUE}>{((clip.sync.confidence || 0) * 100).toFixed(0)}%</span>
              </div>
            </div>
          )}
          {syncItem && !clip.sync && (
            <div>
              <span
                style={{
                  ...SYNC_BADGE,
                  background: `${syncColor}22`,
                  color: syncColor,
                  border: `1px solid ${syncColor}44`,
                }}
              >
                ◎ {syncItem.recommended_method || 'none'}
              </span>
              <div style={{ ...ROW, marginTop: 4 }}>
                <span style={LABEL}>Suggested</span>
                <span style={VALUE}>{Number(syncItem.recommended_offset_sec).toFixed(3)}s</span>
              </div>
              <div style={ROW}>
                <span style={LABEL}>Confidence</span>
                <span style={VALUE}>{(syncItem.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Waveform Mini */}
      {waveformBins && waveformBins.length > 0 && (
        <div style={SECTION}>
          <div style={HEADER}>Waveform</div>
          <WaveformCanvas bins={waveformBins} width={240} height={40} color="#999" bgColor="#080808" />
        </div>
      )}

      {/* Thumbnail */}
      {thumb?.poster_url && (
        <div style={SECTION}>
          <div style={HEADER}>Preview</div>
          <img
            src={thumb.poster_url}
            alt=""
            style={{ width: '100%', borderRadius: 3, display: 'block' }}
          />
        </div>
      )}

      {/* Markers */}
      {clipMarkers.length > 0 && (
        <div style={SECTION}>
          <div style={HEADER}>Markers ({clipMarkers.length})</div>
          {clipMarkers.slice(0, 8).map((m) => (
            <div key={m.marker_id} style={MARKER_ITEM}>
              <span style={{ color: MARKER_COLORS[m.kind] || '#888', marginRight: 4 }}>●</span>
              <span style={{ color: '#aaa' }}>{m.kind}</span>
              <span style={{ color: '#555', marginLeft: 4 }}>{formatTC(m.start_sec)}</span>
              {m.text && <div style={{ color: '#666', fontSize: 9, marginTop: 1, paddingLeft: 12 }}>{m.text}</div>}
            </div>
          ))}
        </div>
      )}

      {/* Source Path */}
      <div style={SECTION}>
        <div style={HEADER}>Source</div>
        <div style={{ fontSize: 9, color: '#444', wordBreak: 'break-all', lineHeight: 1.3 }}>
          {clip.source_path}
        </div>
      </div>
    </div>
  );
}
