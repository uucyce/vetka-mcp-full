/**
 * MARKER_W6.1: Master Render / Export dialog.
 * MARKER_B6: Rewired to cut_render_engine.py — filter_complex, transitions, speed.
 *
 * Three export modes:
 * 1. Master Render — ProRes 422/4444 / H.264 / H.265 / DNxHD video file
 * 2. Editorial Export — Premiere XML / FCPXML / EDL / OTIO
 * 3. Publish — Platform presets (YouTube, Instagram, TikTok, Telegram)
 *
 * Backend: POST /cut/render/master → cut_render_engine.render_timeline() → async job.
 * Editorial: POST /cut/export/* endpoints (unchanged).
 */
import { useState, useCallback, useRef, useEffect, type CSSProperties } from 'react';
import { io, type Socket } from 'socket.io-client';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { API_BASE, getSocketUrl } from '../../config/api.config';

// ─── Types ───

type ExportTab = 'master' | 'editorial' | 'publish';

// MARKER_B6.1: Full ProRes family + codecs
type VideoCodec = 'prores_proxy' | 'prores_lt' | 'prores_422' | 'prores_422hq' | 'prores_4444' | 'prores_4444xq' | 'h264' | 'h265' | 'dnxhd';
type Resolution = '4k' | '1080p' | '720p' | 'source';
type EditorialFormat = 'premiere_xml' | 'fcpxml' | 'edl' | 'otio';
// MARKER_B6.2: Audio codec type
type AudioCodec = 'aac' | 'pcm_s24le' | 'libmp3lame' | 'flac';

interface CodecOption {
  id: VideoCodec;
  label: string;
  ext: string;
  description: string;
}

interface ResolutionOption {
  id: Resolution;
  label: string;
  width: number;
  height: number;
}

const CODECS: CodecOption[] = [
  // Delivery
  { id: 'h264', label: 'H.264', ext: '.mp4', description: 'Universal delivery codec. Good quality/size ratio.' },
  { id: 'h265', label: 'H.265 (HEVC)', ext: '.mp4', description: 'Better compression than H.264. Modern devices.' },
  // MARKER_B6.1: Full ProRes family
  { id: 'prores_proxy', label: 'ProRes Proxy', ext: '.mov', description: 'Smallest ProRes. Offline editing, proxy workflows.' },
  { id: 'prores_lt', label: 'ProRes LT', ext: '.mov', description: 'Lightweight. 70% of 422 size, good for field editing.' },
  { id: 'prores_422', label: 'ProRes 422', ext: '.mov', description: 'Standard broadcast quality. Industry workhorse.' },
  { id: 'prores_422hq', label: 'ProRes 422 HQ', ext: '.mov', description: 'High quality mastering. Visually lossless.' },
  { id: 'prores_4444', label: 'ProRes 4444', ext: '.mov', description: 'Maximum quality with alpha channel support.' },
  { id: 'prores_4444xq', label: 'ProRes 4444 XQ', ext: '.mov', description: 'Highest ProRes quality. HDR/wide gamut mastering.' },
  // Post-production
  { id: 'dnxhd', label: 'DNxHR HQ', ext: '.mxf', description: 'Avid-compatible. Broadcast and post-production.' },
];

// MARKER_B6.2: Audio codec options
const AUDIO_CODECS: { id: AudioCodec; label: string; description: string }[] = [
  { id: 'aac', label: 'AAC', description: 'Default for MP4/MOV. Universal compatibility.' },
  { id: 'pcm_s24le', label: 'PCM 24-bit', description: 'Uncompressed. Best for ProRes/DNxHR masters.' },
  { id: 'libmp3lame', label: 'MP3', description: 'Legacy delivery. Smaller files.' },
  { id: 'flac', label: 'FLAC', description: 'Lossless compression. Archive quality.' },
];

const RESOLUTIONS: ResolutionOption[] = [
  { id: 'source', label: 'Source', width: 0, height: 0 },
  { id: '4k', label: '4K UHD', width: 3840, height: 2160 },
  { id: '1080p', label: '1080p', width: 1920, height: 1080 },
  { id: '720p', label: '720p', width: 1280, height: 720 },
];

const EDITORIAL_FORMATS: { id: EditorialFormat; label: string; description: string }[] = [
  { id: 'premiere_xml', label: 'Premiere Pro XML', description: 'XMEML v5 for Adobe Premiere Pro' },
  { id: 'fcpxml', label: 'FCPXML', description: 'For Final Cut Pro / DaVinci Resolve' },
  { id: 'edl', label: 'EDL', description: 'Edit Decision List (CMX 3600)' },
  { id: 'otio', label: 'OpenTimelineIO', description: 'Universal timeline interchange' },
];

// MARKER_B4.3: Export preset type (fetched from backend GET /cut/render/presets)
type ExportPreset = {
  key: string;
  label: string;
  codec: string;
  resolution: string;
  fps: number;
  quality: number;
  aspect?: string;
};

const PUBLISH_PRESETS = [
  { id: 'youtube', label: 'YouTube', resolution: '1080p', codec: 'h264', bitrate: '12M' },
  { id: 'instagram_reels', label: 'Instagram Reels', resolution: '1080p', codec: 'h264', bitrate: '8M' },
  { id: 'tiktok', label: 'TikTok', resolution: '1080p', codec: 'h264', bitrate: '8M' },
  { id: 'telegram', label: 'Telegram', resolution: '720p', codec: 'h264', bitrate: '4M' },
];

// ─── Styles ───

const OVERLAY: CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0,0,0,0.7)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
};

const DIALOG: CSSProperties = {
  background: '#1a1a1a',
  border: '1px solid #333',
  borderRadius: 8,
  width: 480,
  maxHeight: '80vh',
  overflow: 'auto',
  fontFamily: 'system-ui',
  color: '#ccc',
};

const HEADER: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '12px 16px',
  borderBottom: '1px solid #333',
};

const TAB_BAR: CSSProperties = {
  display: 'flex',
  borderBottom: '1px solid #333',
};

const TAB: CSSProperties = {
  flex: 1,
  padding: '8px 0',
  textAlign: 'center',
  fontSize: 11,
  cursor: 'pointer',
  border: 'none',
  background: 'none',
  color: '#666',
  fontFamily: 'system-ui',
};

const TAB_ACTIVE: CSSProperties = {
  ...TAB,
  color: '#ccc',
  borderBottom: '2px solid #999',
};

const BODY: CSSProperties = {
  padding: 16,
};

const FIELD: CSSProperties = {
  marginBottom: 14,
};

const LABEL: CSSProperties = {
  fontSize: 10,
  color: '#888',
  marginBottom: 4,
  display: 'block',
};

const SELECT: CSSProperties = {
  width: '100%',
  padding: '6px 8px',
  fontSize: 11,
  background: '#111',
  border: '1px solid #333',
  borderRadius: 4,
  color: '#ccc',
  fontFamily: 'system-ui',
};

const SLIDER_ROW: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
};

const FOOTER: CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: 8,
  padding: '12px 16px',
  borderTop: '1px solid #333',
};

const BTN: CSSProperties = {
  padding: '6px 16px',
  fontSize: 11,
  border: 'none',
  borderRadius: 4,
  cursor: 'pointer',
  fontFamily: 'system-ui',
};

const BTN_PRIMARY: CSSProperties = {
  ...BTN,
  background: '#999',
  color: '#fff',
};

const BTN_SECONDARY: CSSProperties = {
  ...BTN,
  background: '#333',
  color: '#ccc',
};

const RADIO_ITEM: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 8,
  padding: '6px 8px',
  borderRadius: 4,
  cursor: 'pointer',
  transition: 'background 0.15s',
};

const PROGRESS_BAR: CSSProperties = {
  width: '100%',
  height: 6,
  background: '#222',
  borderRadius: 3,
  overflow: 'hidden',
  marginTop: 8,
};

// ─── Component ───

export default function ExportDialog() {
  const show = useCutEditorStore((s) => s.showExportDialog);
  const setShow = useCutEditorStore((s) => s.setShowExportDialog);
  const renderProgress = useCutEditorStore((s) => s.renderProgress);
  const renderStatus = useCutEditorStore((s) => s.renderStatus);
  const renderError = useCutEditorStore((s) => s.renderError);
  const setRenderProgress = useCutEditorStore((s) => s.setRenderProgress);
  const setRenderStatus = useCutEditorStore((s) => s.setRenderStatus);
  const setRenderError = useCutEditorStore((s) => s.setRenderError);
  const sandboxRoot = useCutEditorStore((s) => s.sandboxRoot);
  const projectId = useCutEditorStore((s) => s.projectId);
  const timelineId = useCutEditorStore((s) => s.timelineId);
  const projectFramerate = useCutEditorStore((s) => s.projectFramerate);
  // MARKER_W6.2: Sequence marks for selection export
  const sequenceMarkIn = useCutEditorStore((s) => s.sequenceMarkIn);
  const sequenceMarkOut = useCutEditorStore((s) => s.sequenceMarkOut);
  const lanes = useCutEditorStore((s) => s.lanes);

  const [tab, setTab] = useState<ExportTab>('master');
  const [codec, setCodec] = useState<VideoCodec>('h264');
  const [resolution, setResolution] = useState<Resolution>('1080p');
  const [quality, setQuality] = useState(80);
  // MARKER_B6.3: Bitrate mode
  const [bitrateMode, setBitrateMode] = useState<'crf' | 'cbr' | 'vbr'>('crf');
  const [targetBitrate, setTargetBitrate] = useState('12M');
  const [maxBitrate, setMaxBitrate] = useState('15M');
  const [audioCodec, setAudioCodec] = useState<AudioCodec>('aac');
  const [selectionOnly, setSelectionOnly] = useState(false);
  const [audioStems, setAudioStems] = useState(false);
  // MARKER_B51: Loudness normalization
  const [loudnessNorm, setLoudnessNorm] = useState(false);
  const [loudnessStandard, setLoudnessStandard] = useState('youtube');
  const [editorialFormat, setEditorialFormat] = useState<EditorialFormat>('premiere_xml');
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState<string | null>(null);
  // MARKER_B4.1: Track active job for cancel
  const activeJobIdRef = useRef<string | null>(null);
  // MARKER_B4.3: Export presets from backend
  const [presets, setPresets] = useState<ExportPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>('custom');
  // MARKER_B4.2: ETA + SocketIO progress
  const [etaSec, setEtaSec] = useState<number | null>(null);
  const [elapsedSec, setElapsedSec] = useState<number | null>(null);
  const socketRef = useRef<Socket | null>(null);
  const useSocketProgress = useRef(false);

  // MARKER_B4.2: SocketIO render_progress listener
  useEffect(() => {
    const jobId = activeJobIdRef.current;
    if (!jobId) {
      // No active job — disconnect socket if connected
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
      useSocketProgress.current = false;
      setEtaSec(null);
      setElapsedSec(null);
      return;
    }

    // Connect socket for progress events
    const socket = io(getSocketUrl(), {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
    });
    socketRef.current = socket;

    socket.on('connect', () => {
      useSocketProgress.current = true;
    });

    socket.on('render_progress', (data: any) => {
      if (data.job_id !== activeJobIdRef.current) return;
      const progress = data.progress ?? 0;
      setRenderProgress(progress);
      if (data.eta_sec != null) setEtaSec(Math.round(data.eta_sec));
      if (data.elapsed_sec != null) setElapsedSec(Math.round(data.elapsed_sec));
      if (data.message === 'done') {
        setRenderStatus('Complete');
      } else if (data.message === 'cancelled') {
        setRenderStatus('Cancelled');
        setRenderProgress(null);
      } else if (data.message?.startsWith('error:')) {
        setRenderError(data.message);
        setRenderProgress(null);
      } else if (data.message && data.message.startsWith('Encoding at')) {
        // MARKER_B51: Show speed + ETA from FFmpeg -progress pipe
        setRenderStatus(`${data.message} (${Math.round(progress * 100)}%)`);
      } else {
        setRenderStatus(`Encoding... ${Math.round(progress * 100)}%`);
      }
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
      useSocketProgress.current = false;
    };
  }, [renderProgress !== null ? activeJobIdRef.current : null]);

  // MARKER_B4.3: Fetch presets on mount
  useEffect(() => {
    fetch(`${API_BASE}/cut/render/presets`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data?.presets) setPresets(data.presets); })
      .catch(() => {});
  }, []);

  // MARKER_B4.3: Apply preset → auto-fill codec/resolution/quality
  const applyPreset = useCallback((presetKey: string) => {
    setSelectedPreset(presetKey);
    if (presetKey === 'custom') return;
    const p = presets.find((pr) => pr.key === presetKey);
    if (!p) return;
    // Map preset codec to our VideoCodec type
    const codecMap: Record<string, VideoCodec> = {
      h264: 'h264', h265: 'h265',
      prores_proxy: 'prores_proxy', prores_lt: 'prores_lt',
      prores_422: 'prores_422', prores_422hq: 'prores_422hq',
      prores_4444: 'prores_4444', prores_4444xq: 'prores_4444xq',
      dnxhr_hq: 'dnxhd', av1: 'h264', vp9: 'h264',
    };
    setCodec(codecMap[p.codec] || 'h264');
    setResolution((p.resolution || '1080p') as Resolution);
    setQuality(p.quality || 80);
  }, [presets]);

  const hasSelection = sequenceMarkIn !== null && sequenceMarkOut !== null;
  const audioLanes = lanes.filter((l) => l.lane_type.startsWith('audio'));

  const close = useCallback(() => {
    if (renderProgress !== null) return; // don't close while rendering
    setShow(false);
    setExportResult(null);
    setRenderError(null);
  }, [renderProgress, setShow, setRenderError]);

  // ─── Master render ───
  const startRender = useCallback(async () => {
    setRenderProgress(0);
    setRenderStatus('Starting render...');
    setRenderError(null);

    try {
      const res = await fetch(`${API_BASE}/cut/render/master`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot || '',
          project_id: projectId || 'project',
          timeline_id: timelineId,
          codec,
          resolution,
          quality,
          fps: projectFramerate,
          // MARKER_W6.2: Selection range + audio stems
          range_in: selectionOnly && hasSelection ? sequenceMarkIn : null,
          range_out: selectionOnly && hasSelection ? sequenceMarkOut : null,
          audio_stems: audioStems,
          audio_codec: audioCodec,
          bitrate_mode: bitrateMode,
          target_bitrate: bitrateMode !== 'crf' ? targetBitrate : '',
          max_bitrate: bitrateMode === 'vbr' ? maxBitrate : '',
        }),
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`HTTP ${res.status}: ${errText}`);
      }

      const data = await res.json();
      if (data.job_id) {
        // MARKER_B4.1: Store job_id for cancel
        activeJobIdRef.current = data.job_id;
        // Poll for progress (MARKER_B4.2: slower when SocketIO active, faster as fallback)
        setRenderStatus('Encoding...');
        for (let i = 0; i < 600; i++) {
          const pollInterval = useSocketProgress.current ? 2000 : 500;
          await new Promise((r) => setTimeout(r, pollInterval));
          const jobRes = await fetch(`${API_BASE}/cut/job/${encodeURIComponent(data.job_id)}`);
          if (!jobRes.ok) continue;
          const job = await jobRes.json();
          const state = job.job?.state;
          const progress = job.job?.progress ?? 0;
          // Only update UI from HTTP if socket isn't providing real-time updates
          if (!useSocketProgress.current) {
            setRenderProgress(progress);
            setRenderStatus(state === 'done' ? 'Complete' : `Encoding... ${Math.round(progress * 100)}%`);
          }
          if (state === 'done') {
            const result = job.job?.result;
            const sizeMB = result?.file_size_bytes ? `${(result.file_size_bytes / 1048576).toFixed(1)} MB` : '';
            const transitions = result?.transitions_count ? ` | ${result.transitions_count} transition(s)` : '';
            const fc = result?.used_filter_complex ? ' | filter_complex' : '';
            setExportResult(`${result?.output_path || 'Render complete'}${sizeMB ? ` (${sizeMB}${transitions}${fc})` : ''}`);
            activeJobIdRef.current = null;
            setRenderProgress(null);
            setRenderStatus(null);
            return;
          }
          if (state === 'error') {
            activeJobIdRef.current = null;
            throw new Error(job.job?.error?.message || 'Render failed');
          }
          if (state === 'cancelled') {
            activeJobIdRef.current = null;
            setRenderStatus('Cancelled');
            setRenderProgress(null);
            setTimeout(() => setRenderStatus(null), 1500);
            return;
          }
        }
        activeJobIdRef.current = null;
        throw new Error('Render timed out');
      } else if (data.output_path) {
        setExportResult(data.output_path);
        setRenderProgress(null);
        setRenderStatus(null);
      } else {
        throw new Error(data.error || 'Unknown render error');
      }
    } catch (err) {
      activeJobIdRef.current = null;
      setRenderError(err instanceof Error ? err.message : 'Render failed');
      setRenderProgress(null);
      setRenderStatus(null);
    }
  }, [sandboxRoot, projectId, timelineId, codec, resolution, quality, projectFramerate,
      setRenderProgress, setRenderStatus, setRenderError]);

  // ─── Editorial export ───
  const startEditorialExport = useCallback(async () => {
    setExporting(true);
    setExportResult(null);
    try {
      const endpointMap: Record<EditorialFormat, string> = {
        premiere_xml: '/cut/export/premiere-xml',
        fcpxml: '/cut/export/fcpxml',
        edl: '/cut/export/edl',
        otio: '/cut/export/otio',
      };
      const res = await fetch(`${API_BASE}${endpointMap[editorialFormat]}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot || '',
          project_id: projectId || 'project',
          timeline_id: timelineId,
          fps: projectFramerate,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setExportResult(data.file_path || data.output_path || 'Export complete');
    } catch (err) {
      setRenderError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  }, [sandboxRoot, projectId, timelineId, projectFramerate, editorialFormat, setRenderError]);

  // ─── MARKER_B6: Publish preset — async job with progress polling ───
  const startPublish = useCallback(async (presetId: string) => {
    setRenderProgress(0);
    setRenderStatus(`Publishing to ${presetId}...`);
    setRenderError(null);
    setExportResult(null);

    try {
      const res = await fetch(`${API_BASE}/cut/render/master`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot || '',
          project_id: projectId || 'project',
          timeline_id: timelineId,
          codec: 'h264',
          resolution: '1080p',
          quality: 80,
          fps: projectFramerate,
          preset: presetId,
          range_in: selectionOnly && hasSelection ? sequenceMarkIn : null,
          range_out: selectionOnly && hasSelection ? sequenceMarkOut : null,
          audio_stems: false,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      const data = await res.json();

      if (data.job_id) {
        activeJobIdRef.current = data.job_id;
        setRenderStatus(`Encoding for ${presetId}...`);
        for (let i = 0; i < 600; i++) {
          await new Promise((r) => setTimeout(r, 500));
          const jobRes = await fetch(`${API_BASE}/cut/job/${encodeURIComponent(data.job_id)}`);
          if (!jobRes.ok) continue;
          const job = await jobRes.json();
          const state = job.job?.state;
          const progress = job.job?.progress ?? 0;
          setRenderProgress(progress);
          setRenderStatus(state === 'done' ? 'Complete' : `Encoding for ${presetId}... ${Math.round(progress * 100)}%`);
          if (state === 'done') {
            const result = job.job?.result;
            const sizeMB = result?.file_size_bytes ? `${(result.file_size_bytes / 1048576).toFixed(1)} MB` : '';
            setExportResult(`${result?.output_path || 'Render complete'}${sizeMB ? ` (${sizeMB})` : ''}`);
            activeJobIdRef.current = null;
            setRenderProgress(null);
            setRenderStatus(null);
            return;
          }
          if (state === 'error') {
            activeJobIdRef.current = null;
            throw new Error(job.job?.error?.message || 'Publish render failed');
          }
          if (state === 'cancelled') {
            activeJobIdRef.current = null;
            setRenderStatus('Cancelled');
            setRenderProgress(null);
            setTimeout(() => setRenderStatus(null), 1500);
            return;
          }
        }
        activeJobIdRef.current = null;
        throw new Error('Publish render timed out');
      } else {
        throw new Error(data.error || 'Unknown publish error');
      }
    } catch (err) {
      activeJobIdRef.current = null;
      setRenderError(err instanceof Error ? err.message : 'Publish failed');
      setRenderProgress(null);
      setRenderStatus(null);
    }
  }, [sandboxRoot, projectId, timelineId, projectFramerate, selectionOnly, hasSelection,
      sequenceMarkIn, sequenceMarkOut, setRenderProgress, setRenderStatus, setRenderError]);

  // MARKER_B4.1: Cancel active render job
  const cancelRender = useCallback(async () => {
    const jobId = activeJobIdRef.current;
    if (!jobId) return;
    try {
      await fetch(`${API_BASE}/cut/job/${encodeURIComponent(jobId)}/cancel`, { method: 'POST' });
      setRenderStatus('Cancelling...');
    } catch {
      // Best-effort cancel — polling loop will detect state change
    }
  }, [setRenderStatus]);

  if (!show) return null;

  const selectedCodec = CODECS.find((c) => c.id === codec)!;
  const isRendering = renderProgress !== null;

  return (
    <div style={OVERLAY} onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div style={DIALOG} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={HEADER}>
          <span style={{ fontSize: 13, fontWeight: 500 }}>Export</span>
          <button
            style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer', fontSize: 16 }}
            onClick={close}
          >
            x
          </button>
        </div>

        {/* Tab bar */}
        <div style={TAB_BAR}>
          {(['master', 'editorial', 'publish'] as const).map((t) => (
            <button
              key={t}
              style={tab === t ? TAB_ACTIVE : TAB}
              onClick={() => setTab(t)}
            >
              {t === 'master' ? 'Master' : t === 'editorial' ? 'Editorial' : 'Publish'}
            </button>
          ))}
        </div>

        {/* Body */}
        <div style={BODY}>
          {tab === 'master' && (
            <>
              {/* MARKER_B4.3: Preset dropdown */}
              {presets.length > 0 && (
                <div style={FIELD}>
                  <label style={LABEL}>Preset</label>
                  <select
                    style={SELECT}
                    value={selectedPreset}
                    onChange={(e) => applyPreset(e.target.value)}
                    disabled={isRendering}
                    data-testid="export-preset-select"
                  >
                    <option value="custom">Custom settings</option>
                    {presets.map((p) => (
                      <option key={p.key} value={p.key}>{p.label}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Codec */}
              <div style={FIELD}>
                <label style={LABEL}>Codec</label>
                <select
                  style={SELECT}
                  value={codec}
                  onChange={(e) => { setCodec(e.target.value as VideoCodec); setSelectedPreset('custom'); }}
                  disabled={isRendering}
                >
                  {CODECS.map((c) => (
                    <option key={c.id} value={c.id}>{c.label} ({c.ext})</option>
                  ))}
                </select>
                <div style={{ fontSize: 9, color: '#555', marginTop: 3 }}>
                  {selectedCodec.description}
                </div>
              </div>

              {/* Resolution */}
              <div style={FIELD}>
                <label style={LABEL}>Resolution</label>
                <select
                  style={SELECT}
                  value={resolution}
                  onChange={(e) => { setResolution(e.target.value as Resolution); setSelectedPreset('custom'); }}
                  disabled={isRendering}
                >
                  {RESOLUTIONS.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.label}{r.width ? ` (${r.width}x${r.height})` : ''}
                    </option>
                  ))}
                </select>
              </div>

              {/* MARKER_B6.3: Quality / Bitrate mode */}
              <div style={FIELD}>
                <label style={LABEL}>Rate Control</label>
                <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
                  {(['crf', 'cbr', 'vbr'] as const).map((m) => (
                    <button
                      key={m}
                      style={{
                        ...BTN,
                        background: bitrateMode === m ? '#333' : '#1a1a1a',
                        color: bitrateMode === m ? '#ccc' : '#555',
                        fontSize: 9,
                        padding: '3px 10px',
                        border: bitrateMode === m ? '1px solid #555' : '1px solid #222',
                      }}
                      onClick={() => { setBitrateMode(m); setSelectedPreset('custom'); }}
                      disabled={isRendering}
                    >
                      {m.toUpperCase()}
                    </button>
                  ))}
                </div>
                {bitrateMode === 'crf' && (
                  <div style={SLIDER_ROW}>
                    <input
                      type="range"
                      min={10}
                      max={100}
                      value={quality}
                      onChange={(e) => { setQuality(Number(e.target.value)); setSelectedPreset('custom'); }}
                      disabled={isRendering}
                      style={{ flex: 1 }}
                    />
                    <span style={{ fontSize: 11, color: '#888', width: 30, textAlign: 'right' }}>
                      {quality}%
                    </span>
                  </div>
                )}
                {(bitrateMode === 'cbr' || bitrateMode === 'vbr') && (
                  <div style={{ display: 'flex', gap: 8 }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 9, color: '#555', marginBottom: 2 }}>Target Bitrate</div>
                      <input
                        type="text"
                        value={targetBitrate}
                        onChange={(e) => { setTargetBitrate(e.target.value); setSelectedPreset('custom'); }}
                        disabled={isRendering}
                        style={{ ...SELECT, width: '100%' }}
                        placeholder="12M"
                      />
                    </div>
                    {bitrateMode === 'vbr' && (
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 9, color: '#555', marginBottom: 2 }}>Max Bitrate</div>
                        <input
                          type="text"
                          value={maxBitrate}
                          onChange={(e) => { setMaxBitrate(e.target.value); setSelectedPreset('custom'); }}
                          disabled={isRendering}
                          style={{ ...SELECT, width: '100%' }}
                          placeholder="15M"
                        />
                      </div>
                    )}
                  </div>
                )}
                <div style={{ fontSize: 9, color: '#444', marginTop: 3 }}>
                  {bitrateMode === 'crf' ? 'Quality-based (variable file size)' : bitrateMode === 'cbr' ? 'Constant bitrate (predictable file size, streaming)' : 'Variable bitrate (target + max cap)'}
                </div>
              </div>

              {/* MARKER_B6.2: Audio codec */}
              <div style={FIELD}>
                <label style={LABEL}>Audio Codec</label>
                <select
                  style={SELECT}
                  value={audioCodec}
                  onChange={(e) => { setAudioCodec(e.target.value as AudioCodec); setSelectedPreset('custom'); }}
                  disabled={isRendering}
                  data-testid="export-audio-codec"
                >
                  {AUDIO_CODECS.map((ac) => (
                    <option key={ac.id} value={ac.id}>{ac.label}</option>
                  ))}
                </select>
                <div style={{ fontSize: 9, color: '#555', marginTop: 3 }}>
                  {AUDIO_CODECS.find((ac) => ac.id === audioCodec)?.description}
                </div>
              </div>

              {/* MARKER_B51: Loudness normalization toggle */}
              <div style={FIELD}>
                <label style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  fontSize: 11, color: '#aaa', cursor: 'pointer',
                }}>
                  <input
                    type="checkbox"
                    checked={loudnessNorm}
                    onChange={(e) => setLoudnessNorm(e.target.checked)}
                    disabled={isRendering}
                  />
                  Loudness normalization
                </label>
                {loudnessNorm && (
                  <select
                    value={loudnessStandard}
                    onChange={(e) => setLoudnessStandard(e.target.value)}
                    disabled={isRendering}
                    style={{ marginTop: 4, marginLeft: 24, background: '#1a1a1a', color: '#aaa', border: '1px solid #333', borderRadius: 2, fontSize: 10, padding: '2px 4px' }}
                  >
                    <option value="youtube">YouTube (-14 LUFS)</option>
                    <option value="ebu_r128">EBU R128 (-23 LUFS)</option>
                    <option value="atsc_a85">ATSC A/85 (-24 LUFS)</option>
                    <option value="netflix">Netflix (-27 LUFS)</option>
                    <option value="podcast">Podcast (-16 LUFS)</option>
                  </select>
                )}
              </div>

              {/* MARKER_W6.2: Selection range */}
              <div style={FIELD}>
                <label style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  fontSize: 11, color: hasSelection ? '#ccc' : '#555', cursor: 'pointer',
                }}>
                  <input
                    type="checkbox"
                    checked={selectionOnly}
                    onChange={(e) => setSelectionOnly(e.target.checked)}
                    disabled={isRendering || !hasSelection}
                  />
                  Selection only (IN/OUT range)
                </label>
                {hasSelection ? (
                  <div style={{ fontSize: 9, color: '#555', marginTop: 2, marginLeft: 24 }}>
                    {sequenceMarkIn?.toFixed(2)}s - {sequenceMarkOut?.toFixed(2)}s
                  </div>
                ) : (
                  <div style={{ fontSize: 9, color: '#444', marginTop: 2, marginLeft: 24 }}>
                    Set IN/OUT marks on timeline to enable
                  </div>
                )}
              </div>

              {/* MARKER_W6.2: Audio stems */}
              <div style={FIELD}>
                <label style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  fontSize: 11, color: audioLanes.length > 0 ? '#ccc' : '#555', cursor: 'pointer',
                }}>
                  <input
                    type="checkbox"
                    checked={audioStems}
                    onChange={(e) => setAudioStems(e.target.checked)}
                    disabled={isRendering || audioLanes.length === 0}
                  />
                  Export audio stems (per-track WAV)
                </label>
                {audioLanes.length > 0 ? (
                  <div style={{ fontSize: 9, color: '#555', marginTop: 2, marginLeft: 24 }}>
                    {audioLanes.length} audio track{audioLanes.length !== 1 ? 's' : ''} will be exported separately
                  </div>
                ) : (
                  <div style={{ fontSize: 9, color: '#444', marginTop: 2, marginLeft: 24 }}>
                    No audio tracks in timeline
                  </div>
                )}
              </div>

            </>
          )}

          {tab === 'editorial' && (
            <>
              {EDITORIAL_FORMATS.map((fmt) => (
                <div
                  key={fmt.id}
                  style={{
                    ...RADIO_ITEM,
                    background: editorialFormat === fmt.id ? '#1f1f2a' : 'transparent',
                  }}
                  onClick={() => setEditorialFormat(fmt.id)}
                >
                  <input
                    type="radio"
                    checked={editorialFormat === fmt.id}
                    readOnly
                    style={{ marginTop: 2 }}
                  />
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 500 }}>{fmt.label}</div>
                    <div style={{ fontSize: 9, color: '#666' }}>{fmt.description}</div>
                  </div>
                </div>
              ))}
            </>
          )}

          {tab === 'publish' && (
            <>
              {PUBLISH_PRESETS.map((preset) => (
                <div
                  key={preset.id}
                  style={{ ...RADIO_ITEM, opacity: isRendering ? 0.5 : 1, pointerEvents: isRendering ? 'none' : 'auto' }}
                  onClick={() => startPublish(preset.id)}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = '#1f1f2a'; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
                >
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 500 }}>{preset.label}</div>
                    <div style={{ fontSize: 9, color: '#666' }}>
                      {preset.resolution} / {preset.codec.toUpperCase()} / {preset.bitrate}
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}

          {/* MARKER_B6: Shared progress bar (Master + Publish) */}
          {isRendering && (
            <div style={{ marginTop: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: 10, color: '#999' }}>{renderStatus}</div>
                <div style={{ fontSize: 9, color: '#555' }}>
                  {(renderProgress ?? 0) < 0.1 ? 'Preparing...'
                    : (renderProgress ?? 0) < 0.3 ? 'Building graph...'
                    : (renderProgress ?? 0) < 0.85 ? 'Encoding...'
                    : (renderProgress ?? 0) < 1 ? 'Audio stems...'
                    : 'Finalizing...'}
                </div>
              </div>
              <div style={PROGRESS_BAR}>
                <div style={{
                  width: `${Math.round((renderProgress ?? 0) * 100)}%`,
                  height: '100%',
                  background: '#999',
                  borderRadius: 3,
                  transition: 'width 0.3s',
                }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 3 }}>
                <button
                  style={{ ...BTN, background: '#333', color: '#ccc', fontSize: 9, padding: '2px 10px' }}
                  onClick={cancelRender}
                  data-testid="export-cancel-render"
                >
                  Cancel Render
                </button>
                <span style={{ fontSize: 9, color: '#444' }}>
                  {Math.round((renderProgress ?? 0) * 100)}%
                  {etaSec != null && etaSec > 0 && ` — ${etaSec < 60 ? `${etaSec}s` : `${Math.floor(etaSec / 60)}m ${etaSec % 60}s`} remaining`}
                  {elapsedSec != null && elapsedSec > 0 && ` (${elapsedSec < 60 ? `${elapsedSec}s` : `${Math.floor(elapsedSec / 60)}m ${elapsedSec % 60}s`} elapsed)`}
                </span>
              </div>
            </div>
          )}

          {/* Error */}
          {renderError && (
            <div style={{ fontSize: 10, color: '#999', marginTop: 8 }}>
              {renderError}
            </div>
          )}

          {/* Result */}
          {exportResult && (
            <div style={{ fontSize: 10, color: '#ccc', marginTop: 8, wordBreak: 'break-all' }}>
              {exportResult}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={FOOTER}>
          <button style={BTN_SECONDARY} onClick={close} disabled={isRendering}>
            Cancel
          </button>
          {tab === 'master' && (
            <button
              style={{ ...BTN_PRIMARY, opacity: isRendering ? 0.5 : 1 }}
              onClick={startRender}
              disabled={isRendering}
            >
              {isRendering ? 'Rendering...' : 'Start Render'}
            </button>
          )}
          {tab === 'editorial' && (
            <button
              style={{ ...BTN_PRIMARY, opacity: exporting ? 0.5 : 1 }}
              onClick={startEditorialExport}
              disabled={exporting}
            >
              {exporting ? 'Exporting...' : 'Export'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
