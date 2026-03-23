/**
 * MARKER_B6.5: CodecProbeDetail — full stream list from ffprobe.
 *
 * Shows all video, audio, and subtitle streams in a media file.
 * Professional media often has multiple audio tracks (stereo + 5.1 + commentary),
 * subtitle tracks, and timecode tracks.
 *
 * Fetches from GET /cut/probe/streams?source_path=...
 * Gamma wires into ClipInspector as expandable section below MediaInfoPanel.
 *
 * @phase B6.5
 * @task tb_1774235798_21
 */
import { useState, useEffect, useRef, type CSSProperties } from 'react';
import { API_BASE } from '../../config/api.config';

// ─── Types ───

interface StreamInfo {
  index: number;
  type: 'video' | 'audio' | 'subtitle';
  codec: string;
  // Video
  profile?: string;
  width?: number;
  height?: number;
  fps?: number;
  pix_fmt?: string;
  bit_depth?: number;
  color_primaries?: string;
  color_transfer?: string;
  // Audio
  channels?: number;
  sample_rate?: number;
}

interface ProbeStreamsData {
  container: string;
  duration_sec: number;
  file_size_bytes: number;
  streams: StreamInfo[];
  video_count: number;
  audio_count: number;
}

interface CodecProbeDetailProps {
  sourcePath: string | null;
  /** Start collapsed */
  defaultExpanded?: boolean;
}

// ─── Styles ───

const PANEL: CSSProperties = {
  fontSize: 9,
  fontFamily: 'monospace',
  color: '#888',
  padding: '4px 8px',
  background: '#0a0a0a',
};

const HEADER_BTN: CSSProperties = {
  background: 'none',
  border: 'none',
  color: '#666',
  fontSize: 9,
  fontFamily: 'monospace',
  cursor: 'pointer',
  padding: '2px 0',
  textAlign: 'left',
  width: '100%',
};

const STREAM_ROW: CSSProperties = {
  display: 'flex',
  gap: 6,
  padding: '2px 0',
  borderBottom: '1px solid #151515',
  alignItems: 'baseline',
};

const BADGE: CSSProperties = {
  fontSize: 7,
  fontWeight: 700,
  padding: '1px 4px',
  borderRadius: 2,
  textTransform: 'uppercase',
  flexShrink: 0,
  width: 28,
  textAlign: 'center',
};

const VIDEO_BADGE: CSSProperties = { ...BADGE, background: '#1a2a1a', color: '#6a8a6a' };
const AUDIO_BADGE: CSSProperties = { ...BADGE, background: '#1a1a2a', color: '#6a6a8a' };
const SUB_BADGE: CSSProperties = { ...BADGE, background: '#2a2a1a', color: '#8a8a6a' };

// ─── Component ───

export default function CodecProbeDetail({
  sourcePath,
  defaultExpanded = false,
}: CodecProbeDetailProps) {
  const [data, setData] = useState<ProbeStreamsData | null>(null);
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [loading, setLoading] = useState(false);
  const lastPathRef = useRef<string | null>(null);

  useEffect(() => {
    if (!sourcePath || sourcePath === lastPathRef.current) return;
    lastPathRef.current = sourcePath;

    if (!expanded) return; // lazy fetch — only when expanded

    setLoading(true);
    fetch(`${API_BASE}/cut/probe/streams?source_path=${encodeURIComponent(sourcePath)}`)
      .then((r) => r.ok ? r.json() : null)
      .then((json) => {
        if (json?.success) setData(json);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [sourcePath, expanded]);

  // Fetch on expand if not yet loaded
  useEffect(() => {
    if (expanded && sourcePath && !data && lastPathRef.current !== sourcePath) {
      lastPathRef.current = sourcePath;
      setLoading(true);
      fetch(`${API_BASE}/cut/probe/streams?source_path=${encodeURIComponent(sourcePath)}`)
        .then((r) => r.ok ? r.json() : null)
        .then((json) => { if (json?.success) setData(json); })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [expanded, sourcePath, data]);

  if (!sourcePath) return null;

  return (
    <div style={PANEL} data-testid="codec-probe-detail">
      <button
        style={HEADER_BTN}
        onClick={() => setExpanded((v) => !v)}
      >
        {expanded ? '- ' : '+ '}Streams{data ? ` (${data.streams.length})` : ''}
      </button>

      {expanded && loading && <div style={{ color: '#444', padding: 2 }}>Probing...</div>}

      {expanded && data && (
        <div style={{ marginTop: 2 }}>
          {data.streams.map((stream) => (
            <div key={stream.index} style={STREAM_ROW}>
              <span style={
                stream.type === 'video' ? VIDEO_BADGE :
                stream.type === 'audio' ? AUDIO_BADGE : SUB_BADGE
              }>
                {stream.type === 'video' ? 'V' : stream.type === 'audio' ? 'A' : 'S'}
                {stream.index}
              </span>
              <span style={{ color: '#999' }}>{stream.codec}</span>
              {stream.type === 'video' && (
                <span style={{ color: '#666' }}>
                  {stream.width}x{stream.height} {stream.fps}fps {stream.pix_fmt}
                  {stream.profile ? ` [${stream.profile}]` : ''}
                </span>
              )}
              {stream.type === 'audio' && (
                <span style={{ color: '#666' }}>
                  {stream.channels === 1 ? 'Mono' : stream.channels === 2 ? 'Stereo' : `${stream.channels}ch`}
                  {' '}{stream.sample_rate ? `${(stream.sample_rate / 1000).toFixed(1)}kHz` : ''}
                  {stream.bit_depth ? ` ${stream.bit_depth}bit` : ''}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
