/**
 * MARKER_B7.4: MediaInfoPanel — display codec/resolution/duration/channels for selected clip.
 *
 * Fetches metadata from GET /cut/probe/log-detect?source_path=...
 * Displays: video codec, resolution, frame rate, pixel format,
 *           audio codec, channels, sample rate, duration, file size.
 *
 * Monochrome table layout, NLE-style. Gamma wires into ClipInspector.
 *
 * @phase B7.4
 * @task tb_1774233388_15
 */
import { useState, useEffect, useRef, type CSSProperties } from 'react';
import { API_BASE } from '../../config/api.config';

interface MediaInfoPanelProps {
  /** Path to the media file to probe */
  sourcePath: string | null;
}

interface ProbeData {
  video_codec?: string;
  video_profile?: string;
  width?: number;
  height?: number;
  fps?: number;
  pix_fmt?: string;
  audio_codec?: string;
  audio_channels?: number;
  audio_sample_rate?: number;
  duration_sec?: number;
  file_size_bytes?: number;
  format?: string;
  bit_rate?: number;
  color_primaries?: string;
  color_transfer?: string;
  log_profile?: string;
  log_confidence?: string;
}

// ─── Styles ───

const PANEL: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 0,
  fontSize: 10,
  fontFamily: 'monospace',
  color: '#888',
  padding: 8,
  background: '#0a0a0a',
  overflow: 'auto',
};

const ROW: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  padding: '2px 0',
  borderBottom: '1px solid #1a1a1a',
};

const LABEL_S: CSSProperties = {
  color: '#555',
  flexShrink: 0,
  width: 90,
};

const VALUE_S: CSSProperties = {
  color: '#999',
  textAlign: 'right',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

const SECTION: CSSProperties = {
  fontSize: 9,
  color: '#666',
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: 0.5,
  padding: '6px 0 2px 0',
  borderBottom: '1px solid #222',
};

// ─── Helpers ───

function formatDuration(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  const f = Math.round((sec % 1) * 100);
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(f).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}.${String(f).padStart(2, '0')}`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MB`;
  return `${(bytes / 1073741824).toFixed(2)} GB`;
}

function formatBitrate(bps: number): string {
  if (bps < 1000) return `${bps} bps`;
  if (bps < 1000000) return `${(bps / 1000).toFixed(0)} Kbps`;
  return `${(bps / 1000000).toFixed(1)} Mbps`;
}

// ─── Component ───

export default function MediaInfoPanel({ sourcePath }: MediaInfoPanelProps) {
  const [data, setData] = useState<ProbeData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastPathRef = useRef<string | null>(null);

  useEffect(() => {
    if (!sourcePath || sourcePath === lastPathRef.current) return;
    lastPathRef.current = sourcePath;
    setLoading(true);
    setError(null);

    fetch(`${API_BASE}/cut/probe/log-detect?source_path=${encodeURIComponent(sourcePath)}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((json) => {
        if (!json.ok && !json.probe) {
          setError(json.error || 'probe_failed');
          return;
        }
        const p = json.probe || json;
        setData({
          video_codec: p.video_codec,
          video_profile: p.video_profile,
          width: p.width,
          height: p.height,
          fps: p.fps,
          pix_fmt: p.pix_fmt,
          audio_codec: p.audio_codec,
          audio_channels: p.audio_channels,
          audio_sample_rate: p.audio_sample_rate,
          duration_sec: p.duration_sec,
          file_size_bytes: p.file_size_bytes,
          format: p.format_name || p.format,
          bit_rate: p.bit_rate,
          color_primaries: p.color_primaries,
          color_transfer: p.color_transfer,
          log_profile: json.log_detection?.profile,
          log_confidence: json.log_detection?.confidence,
        });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sourcePath]);

  if (!sourcePath) {
    return (
      <div style={PANEL} data-testid="media-info-panel">
        <span style={{ color: '#444', fontSize: 10 }}>No clip selected</span>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={PANEL} data-testid="media-info-panel">
        <span style={{ color: '#555' }}>Probing...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={PANEL} data-testid="media-info-panel">
        <span style={{ color: '#666' }}>Probe failed: {error}</span>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div style={PANEL} data-testid="media-info-panel">
      {/* Video */}
      {data.video_codec && (
        <>
          <div style={SECTION}>Video</div>
          <div style={ROW}><span style={LABEL_S}>Codec</span><span style={VALUE_S}>{data.video_codec}{data.video_profile ? ` (${data.video_profile})` : ''}</span></div>
          {data.width && data.height && (
            <div style={ROW}><span style={LABEL_S}>Resolution</span><span style={VALUE_S}>{data.width}x{data.height}</span></div>
          )}
          {data.fps && (
            <div style={ROW}><span style={LABEL_S}>Frame Rate</span><span style={VALUE_S}>{data.fps.toFixed(2)} fps</span></div>
          )}
          {data.pix_fmt && (
            <div style={ROW}><span style={LABEL_S}>Pixel Format</span><span style={VALUE_S}>{data.pix_fmt}</span></div>
          )}
          {data.color_primaries && (
            <div style={ROW}><span style={LABEL_S}>Color</span><span style={VALUE_S}>{data.color_primaries} / {data.color_transfer}</span></div>
          )}
          {data.log_profile && (
            <div style={ROW}><span style={LABEL_S}>Log Profile</span><span style={VALUE_S}>{data.log_profile} ({data.log_confidence})</span></div>
          )}
        </>
      )}

      {/* Audio */}
      {data.audio_codec && (
        <>
          <div style={SECTION}>Audio</div>
          <div style={ROW}><span style={LABEL_S}>Codec</span><span style={VALUE_S}>{data.audio_codec}</span></div>
          {data.audio_channels && (
            <div style={ROW}><span style={LABEL_S}>Channels</span><span style={VALUE_S}>{data.audio_channels === 1 ? 'Mono' : data.audio_channels === 2 ? 'Stereo' : `${data.audio_channels}ch`}</span></div>
          )}
          {data.audio_sample_rate && (
            <div style={ROW}><span style={LABEL_S}>Sample Rate</span><span style={VALUE_S}>{(data.audio_sample_rate / 1000).toFixed(1)} kHz</span></div>
          )}
        </>
      )}

      {/* File */}
      <div style={SECTION}>File</div>
      {data.duration_sec != null && (
        <div style={ROW}><span style={LABEL_S}>Duration</span><span style={VALUE_S}>{formatDuration(data.duration_sec)}</span></div>
      )}
      {data.file_size_bytes != null && (
        <div style={ROW}><span style={LABEL_S}>Size</span><span style={VALUE_S}>{formatFileSize(data.file_size_bytes)}</span></div>
      )}
      {data.bit_rate != null && (
        <div style={ROW}><span style={LABEL_S}>Bitrate</span><span style={VALUE_S}>{formatBitrate(data.bit_rate)}</span></div>
      )}
      {data.format && (
        <div style={ROW}><span style={LABEL_S}>Container</span><span style={VALUE_S}>{data.format}</span></div>
      )}
    </div>
  );
}
