/**
 * MARKER_170.NLE.LAYOUT: NLE editor layout — Premiere Pro-inspired 3-panel design.
 * Top: TransportBar
 * Middle: Source Browser (left) | VideoPreview (right)
 * Bottom: TimelineTrackView
 *
 * This replaces the debug shell layout when viewMode === 'nle'.
 */
import { useState, type CSSProperties, type ReactNode } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import TransportBar from './TransportBar';
import VideoPreview from './VideoPreview';
import TimelineTrackView from './TimelineTrackView';
import ClipInspector from './ClipInspector';
import MarkerNode from './nodes/MarkerNode';

// ─── Styles ───
const ROOT_STYLE: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100vh',
  background: '#000',
  color: '#ccc',
  fontFamily: 'system-ui',
  overflow: 'hidden',
};

const MIDDLE_ROW: CSSProperties = {
  display: 'flex',
  flex: 1,
  minHeight: 0,
  borderBottom: '1px solid #222',
};

const SOURCE_PANEL: CSSProperties = {
  width: 280,
  flexShrink: 0,
  borderRight: '1px solid #222',
  background: '#050505',
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
};

const SOURCE_HEADER: CSSProperties = {
  padding: '6px 10px',
  fontSize: 10,
  color: '#555',
  textTransform: 'uppercase',
  letterSpacing: 1,
  borderBottom: '1px solid #1a1a1a',
  userSelect: 'none',
};

const SOURCE_LIST: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: 4,
};

const SOURCE_BUCKET: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  marginBottom: 10,
};

const SOURCE_BUCKET_HEADER: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '6px 8px 2px',
  fontSize: 9,
  color: '#6b7280',
  letterSpacing: 0.8,
  textTransform: 'uppercase',
};

const SOURCE_ITEM: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '6px 8px',
  borderRadius: 3,
  cursor: 'pointer',
  fontSize: 11,
  transition: 'background 0.1s',
};

const THUMB_STYLE: CSSProperties = {
  width: 48,
  height: 32,
  borderRadius: 2,
  objectFit: 'cover',
  background: '#111',
  flexShrink: 0,
};

const SOURCE_META_ROW: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: 4,
  marginTop: 2,
};

const SOURCE_BADGE: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '1px 5px',
  borderRadius: 999,
  border: '1px solid #1f2937',
  background: '#111827',
  color: '#93c5fd',
  fontSize: 8,
  letterSpacing: 0.2,
};

const PREVIEW_PANEL: CSSProperties = {
  flex: 1,
  minWidth: 0,
  display: 'flex',
  flexDirection: 'column',
};

const PREVIEW_HEADER: CSSProperties = {
  padding: '4px 10px',
  fontSize: 10,
  color: '#555',
  textTransform: 'uppercase',
  letterSpacing: 1,
  borderBottom: '1px solid #1a1a1a',
  userSelect: 'none',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};

const PREVIEW_CONTENT: CSSProperties = {
  flex: 1,
  minHeight: 0,
  padding: 4,
};

const SCENE_GRAPH_PANE: CSSProperties = {
  width: 280,
  flexShrink: 0,
  borderLeft: '1px solid #1a1a1a',
  background: '#040404',
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
};

const SCENE_GRAPH_PANE_BODY: CSSProperties = {
  flex: 1,
  minHeight: 0,
  padding: 10,
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  fontSize: 11,
  color: '#777',
};

const TIMELINE_PANEL: CSSProperties = {
  height: '40%',
  minHeight: 120,
  maxHeight: '55%',
  flexShrink: 0,
  display: 'flex',
  flexDirection: 'column',
  borderTop: '1px solid #333',
};

const RESIZE_HANDLE: CSSProperties = {
  height: 4,
  cursor: 'row-resize',
  background: '#222',
  flexShrink: 0,
};

function basename(path: string): string {
  return path.split('/').pop()?.split('\\').pop() || path;
}

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

type SourceBucketKey = 'video' | 'boards' | 'music_track' | 'audio' | 'stills';

const SOURCE_BUCKET_ORDER: Array<{ key: SourceBucketKey; label: string }> = [
  { key: 'video', label: 'Video Clips' },
  { key: 'boards', label: 'Boards' },
  { key: 'music_track', label: 'Music Track' },
  { key: 'audio', label: 'Audio Assets' },
  { key: 'stills', label: 'Still Images' },
];

type SourceBrowserItem = {
  item_id: string;
  source_path: string;
  poster_url?: string;
  modality?: string;
  duration_sec?: number;
  bucketKey: SourceBucketKey;
  bucketLabel: string;
  badges: string[];
};

type CutEditorLayoutProps = {
  /** Inspector panel content (right side, from legacy shell) */
  inspector?: ReactNode;
  /** Shared Scene Graph surface content for NLE promotion */
  sceneGraphSurface?: ReactNode;
  /** Legacy debug view to show when viewMode === 'debug' */
  debugView?: ReactNode;
  /** Project status text */
  statusText?: string;
};

export default function CutEditorLayout({ inspector, sceneGraphSurface, debugView, statusText }: CutEditorLayoutProps) {
  const viewMode = useCutEditorStore((s) => s.viewMode);
  const thumbnails = useCutEditorStore((s) => s.thumbnails);
  const activeMediaPath = useCutEditorStore((s) => s.activeMediaPath);
  const lanes = useCutEditorStore((s) => s.lanes);
  const setActiveMedia = useCutEditorStore((s) => s.setActiveMedia);
  const setSelectedClip = useCutEditorStore((s) => s.setSelectedClip);
  const syncSurface = useCutEditorStore((s) => s.syncSurface);
  const markers = useCutEditorStore((s) => s.markers);
  const sceneGraphSurfaceMode = useCutEditorStore((s) => s.sceneGraphSurfaceMode);
  const [timelineHeight] = useState(300);

  // MARKER_170.8.SCENE_GRAPH_MARKERS: Music-sync marker stats
  const musicMarkers = markers.filter((m) => m.kind === 'music_sync');
  const musicMarkerCount = musicMarkers.length;
  const avgMusicScore = musicMarkerCount > 0
    ? musicMarkers.reduce((sum, m) => sum + (m.score ?? 0), 0) / musicMarkerCount
    : 0;

  // If debug mode, show legacy view
  if (viewMode === 'debug') {
    return (
      <div data-testid="cut-editor-layout" style={ROOT_STYLE}>
        <TransportBar />
        <div style={{ flex: 1, overflow: 'auto' }}>{debugView}</div>
      </div>
    );
  }

  // Source browser: combine thumbnails + clips from all lanes
  const mediaItems = thumbnails.length
    ? thumbnails
    : lanes.flatMap((l) =>
        l.clips.map((c) => ({
          item_id: c.clip_id,
          source_path: c.source_path,
          poster_url: undefined as string | undefined,
          modality: 'video' as string,
          duration_sec: c.duration_sec,
        }))
      );

  const laneTypesBySourcePath = new Map<string, Set<string>>();
  for (const lane of lanes) {
    for (const clip of lane.clips) {
      const laneTypes = laneTypesBySourcePath.get(clip.source_path) ?? new Set<string>();
      laneTypes.add(lane.lane_type);
      laneTypesBySourcePath.set(clip.source_path, laneTypes);
    }
  }

  const sourceItems: SourceBrowserItem[] = mediaItems.map((item) => {
    const sourcePathLower = item.source_path.toLowerCase();
    const laneTypes = laneTypesBySourcePath.get(item.source_path) ?? new Set<string>();
    const isBoard = sourcePathLower.includes('/boards/') || sourcePathLower.includes('\\boards\\');
    const isMusicTrack = (item.modality === 'audio' || laneTypes.has('audio_sync')) && laneTypes.has('audio_sync');

    let bucketKey: SourceBucketKey = 'video';
    let bucketLabel = 'Video Clips';
    if (isMusicTrack) {
      bucketKey = 'music_track';
      bucketLabel = 'Music Track';
    } else if (isBoard) {
      bucketKey = 'boards';
      bucketLabel = 'Boards';
    } else if (item.modality === 'audio') {
      bucketKey = 'audio';
      bucketLabel = 'Audio Assets';
    } else if (item.modality === 'image') {
      bucketKey = 'stills';
      bucketLabel = 'Still Images';
    }

    const badges: string[] = [];
    if (isMusicTrack) {
      badges.push('Primary music');
    } else if (item.modality === 'audio') {
      badges.push('Audio asset');
    }
    if (laneTypes.has('audio_sync')) {
      badges.push('Audio sync lane');
    }
    if (isBoard) {
      badges.push('Board still');
    } else if (item.modality === 'video') {
      badges.push('Camera clip');
    }

    return {
      ...item,
      bucketKey,
      bucketLabel,
      badges,
    };
  });

  const sourceBuckets = SOURCE_BUCKET_ORDER.map((bucket) => ({
    ...bucket,
    items: sourceItems.filter((item) => item.bucketKey === bucket.key),
  })).filter((bucket) => bucket.items.length > 0);

  // Click on media item in source browser
  const handleSourceClick = (sourcePath: string, itemId: string) => {
    setActiveMedia(sourcePath);
    // Find a matching clip on the timeline
    for (const lane of lanes) {
      const clip = lane.clips.find((c) => c.source_path === sourcePath);
      if (clip) {
        setSelectedClip(clip.clip_id);
        return;
      }
    }
    setSelectedClip(null);
  };

  return (
    <div data-testid="cut-editor-layout" style={ROOT_STYLE}>
      {/* Transport Bar */}
      <TransportBar />

      {/* Middle: Source Browser | Video Preview | Inspector */}
      <div style={MIDDLE_ROW}>
        {/* Source Browser (left) */}
        <div data-testid="cut-source-browser" style={SOURCE_PANEL}>
          <div style={SOURCE_HEADER}>
            Source Browser
            <span style={{ float: 'right', color: '#333' }}>{sourceItems.length} assets</span>
          </div>
          <div style={SOURCE_LIST}>
            {sourceBuckets.map((bucket) => (
              <div key={bucket.key} data-testid={`cut-source-bucket-${bucket.key}`} style={SOURCE_BUCKET}>
                <div style={SOURCE_BUCKET_HEADER}>
                  <span>{bucket.label}</span>
                  <span>{bucket.items.length}</span>
                </div>
                {bucket.items.map((item) => {
                  const isActive = item.source_path === activeMediaPath;
                  const syncItem = syncSurface.find((s) => s.source_path === item.source_path);
                  return (
                    <div
                      key={item.item_id}
                      data-testid={`cut-source-item-${item.item_id}`}
                      style={{
                        ...SOURCE_ITEM,
                        background: isActive ? '#1a1a2a' : 'transparent',
                        borderLeft: isActive ? '2px solid #4a9eff' : '2px solid transparent',
                      }}
                      onClick={() => handleSourceClick(item.source_path, item.item_id)}
                    >
                      {item.poster_url ? (
                        <img src={item.poster_url} style={THUMB_STYLE} alt="" />
                      ) : (
                        <div
                          style={{
                            ...THUMB_STYLE,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: 16,
                            color: '#333',
                          }}
                        >
                          {item.modality === 'audio' ? 'A' : 'V'}
                        </div>
                      )}

                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            fontSize: 11,
                            color: isActive ? '#fff' : '#aaa',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {basename(item.source_path)}
                        </div>
                        <div style={SOURCE_META_ROW}>
                          <span style={{ fontSize: 9, color: '#555' }}>
                            {item.duration_sec ? `${Number(item.duration_sec).toFixed(1)}s` : '—'}
                          </span>
                          {item.badges.map((badge) => (
                            <span
                              key={badge}
                              data-testid={`cut-source-item-badge-${item.item_id}-${slugify(badge)}`}
                              style={SOURCE_BADGE}
                            >
                              {badge}
                            </span>
                          ))}
                          {syncItem?.recommended_method ? (
                            <span style={{ ...SOURCE_BADGE, color: '#86efac', borderColor: '#14532d' }}>
                              Sync {syncItem.recommended_method}
                            </span>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}

            {!sourceItems.length && (
              <div style={{ padding: 20, color: '#333', textAlign: 'center', fontSize: 11 }}>
                No media loaded
                <br />
                Bootstrap a project first
              </div>
            )}
          </div>
        </div>

        {/* Video Preview (center) */}
        <div style={PREVIEW_PANEL}>
          <div style={PREVIEW_HEADER}>
            <span>Program Monitor</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {sceneGraphSurfaceMode === 'nle_ready' ? (
                <span style={{ color: '#22c55e', fontSize: 9 }}>Scene Graph peer pane ready</span>
              ) : null}
              {musicMarkerCount > 0 ? (
                <span
                  data-testid="music-marker-badge"
                  style={{
                    ...SOURCE_BADGE,
                    color: '#d8b4fe',
                    borderColor: '#7c3aed',
                    background: '#1e1033',
                    fontSize: 9,
                  }}
                >
                  🎵 {musicMarkerCount} markers (Sync {(avgMusicScore * 100).toFixed(0)}%)
                </span>
              ) : null}
              {statusText ? (
                <span style={{ fontSize: 10, color: '#555' }}>{statusText}</span>
              ) : null}
            </span>
          </div>
          <div style={PREVIEW_CONTENT}>
            <VideoPreview />
          </div>
        </div>

        {sceneGraphSurfaceMode === 'nle_ready' ? (
          <div style={SCENE_GRAPH_PANE}>
            <div style={SOURCE_HEADER}>Scene Graph Surface</div>
            <div style={SCENE_GRAPH_PANE_BODY}>
              {sceneGraphSurface || (
                <>
                  <div style={{ color: '#22c55e', fontSize: 10 }}>NLE pane insertion active</div>
                  {musicMarkerCount > 0 ? (
                    <div data-testid="scene-graph-markers" style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
                      <div style={{ fontSize: 9, color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                        Music Markers ({musicMarkerCount})
                      </div>
                      {musicMarkers.map((m) => (
                        <MarkerNode
                          key={m.marker_id}
                          data={{
                            markerId: m.marker_id,
                            label: m.text || `${m.start_sec.toFixed(1)}s`,
                            startSec: m.start_sec,
                            endSec: m.end_sec,
                            source: (m.kind === 'music_sync' ? 'energy_pause' : 'transcript_pause') as 'energy_pause',
                            confidence: m.score ?? 0.8,
                          }}
                        />
                      ))}
                    </div>
                  ) : (
                    <>
                      <div>Scene Graph is now promoted beyond shell-only readiness.</div>
                      <div>Next step: replace this placeholder with the shared DAG viewport using the same promoted state.</div>
                    </>
                  )}
                </>
              )}
            </div>
          </div>
        ) : null}

        {/* Inspector (right) — ClipInspector or custom content */}
        <div
          style={{
            width: 260,
            flexShrink: 0,
            borderLeft: '1px solid #222',
            background: '#050505',
            overflowY: 'auto',
            fontSize: 11,
          }}
        >
          {inspector || <ClipInspector />}
        </div>
      </div>

      {/* Resize handle */}
      <div style={RESIZE_HANDLE} />

      {/* Timeline (bottom) */}
      <div style={{ ...TIMELINE_PANEL, height: timelineHeight }}>
        <TimelineTrackView />
      </div>
    </div>
  );
}
