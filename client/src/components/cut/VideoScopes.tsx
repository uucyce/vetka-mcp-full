/**
 * MARKER_B19: Video Scopes panel — Waveform, Parade, Vectorscope, Histogram.
 *
 * FCP7 Reference: Ch.78 "Measuring and Setting Video Levels"
 * MARKER_B27: SocketIO real-time scopes (scope_request → scope_data).
 * Falls back to HTTP GET /cut/scopes/analyze when socket disconnected.
 * MARKER_B26: Broadcast safe percentage readouts (over-white, under-black, chroma-illegal).
 *
 * Four modes (tabs):
 *   - Waveform: Y=luma (0-100 IRE), X=pixel column, green phosphor
 *   - Parade: R/G/B separate waveforms side by side
 *   - Vectorscope: circular CbCr plot with skin tone line
 *   - Histogram: stacked R/G/B curves
 *
 * @phase B27, B26
 * @task tb_1774165550_2, tb_1774410744_1
 */
import { useState, useEffect, useRef, useCallback, type CSSProperties } from 'react';
import { io, type Socket } from 'socket.io-client';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { API_BASE, getSocketUrl } from '../../config/api.config';

type ScopeMode = 'waveform' | 'parade' | 'vectorscope' | 'histogram';

const PANEL_STYLE: CSSProperties = {
  display: 'flex', flexDirection: 'column', width: '100%', height: '100%',
  background: '#0a0a0a', color: '#ccc', fontSize: 11, fontFamily: 'system-ui', overflow: 'hidden',
};
const TAB_BAR: CSSProperties = {
  display: 'flex', gap: 0, background: '#111', borderBottom: '1px solid #222', flexShrink: 0,
};
const TAB_BTN: CSSProperties = {
  padding: '4px 10px', background: 'none', border: 'none', borderBottom: '2px solid transparent',
  color: '#888', fontSize: 10, cursor: 'pointer', fontWeight: 500,
};
const TAB_ACTIVE: CSSProperties = { ...TAB_BTN, color: '#ccc', borderBottomColor: '#999' };
const CANVAS_WRAP: CSSProperties = {
  flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 8, minHeight: 0,
};
const STATUS_BAR: CSSProperties = {
  padding: '2px 8px', fontSize: 9, color: '#555', borderTop: '1px solid #1a1a1a', flexShrink: 0,
};

type BroadcastSafeData = {
  over_white_pct: number;
  under_black_pct: number;
  chroma_illegal_pct: number;
  total_illegal_pct: number;
};

type ScopeData = {
  histogram?: { r: number[]; g: number[]; b: number[] };
  waveform?: number[][];
  vectorscope?: number[][];
  parade?: { r: number[][]; g: number[][]; b: number[][] };
  broadcast_safe?: BroadcastSafeData;
  frame_w?: number;
  frame_h?: number;
};

// ─── Draw functions ───

function drawWaveform(ctx: CanvasRenderingContext2D, data: number[][], w: number, h: number) {
  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, w, h);
  if (!data.length) return;
  const sH = data.length, sW = data[0].length;
  const scX = w / sW, scY = h / sH;

  ctx.strokeStyle = '#222'; ctx.lineWidth = 1;
  for (const ire of [0, 25, 50, 75, 100]) {
    const y = h - (ire / 100) * h;
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
  }

  for (let sy = 0; sy < sH; sy++) {
    for (let sx = 0; sx < sW; sx++) {
      const val = data[sy][sx];
      if (val <= 0) continue;
      ctx.fillStyle = `rgba(0, 200, 80, ${Math.min(1, val / 180)})`;
      ctx.fillRect(sx * scX, sy * scY, Math.max(1, scX), Math.max(1, scY));
    }
  }

  ctx.fillStyle = '#555'; ctx.font = '9px system-ui';
  for (const ire of [0, 50, 100]) ctx.fillText(`${ire}`, 2, h - (ire / 100) * h - 2);
}

function drawParade(
  ctx: CanvasRenderingContext2D,
  data: { r: number[][]; g: number[][]; b: number[][] },
  w: number, h: number,
) {
  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, w, h);

  const channels: { d: number[][]; color: string }[] = [
    { d: data.r, color: '255, 60, 60' },
    { d: data.g, color: '60, 255, 60' },
    { d: data.b, color: '60, 100, 255' },
  ];

  const colW = w / 3;

  for (let ci = 0; ci < 3; ci++) {
    const ch = channels[ci];
    if (!ch.d.length) continue;
    const sH = ch.d.length, sW = ch.d[0].length;
    const scX = colW / sW, scY = h / sH;
    const offsetX = ci * colW;

    // Separator
    if (ci > 0) {
      ctx.strokeStyle = '#333'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(offsetX, 0); ctx.lineTo(offsetX, h); ctx.stroke();
    }

    for (let sy = 0; sy < sH; sy++) {
      for (let sx = 0; sx < sW; sx++) {
        const val = ch.d[sy][sx];
        if (val <= 0) continue;
        ctx.fillStyle = `rgba(${ch.color}, ${Math.min(1, val / 180)})`;
        ctx.fillRect(offsetX + sx * scX, sy * scY, Math.max(1, scX), Math.max(1, scY));
      }
    }
  }

  // Labels
  ctx.fillStyle = '#555'; ctx.font = '9px system-ui';
  ctx.fillText('R', 4, h - 4);
  ctx.fillText('G', colW + 4, h - 4);
  ctx.fillText('B', colW * 2 + 4, h - 4);
}

function drawVectorscope(ctx: CanvasRenderingContext2D, data: number[][], w: number, h: number) {
  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, w, h);
  if (!data.length) return;
  const sSize = data.length;
  const scale = Math.min(w, h) / sSize;
  const oX = (w - sSize * scale) / 2, oY = (h - sSize * scale) / 2;
  const cx = w / 2, cy = h / 2, radius = Math.min(w, h) / 2 - 4;

  // Graticule
  ctx.strokeStyle = '#222'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(cx, cy - radius); ctx.lineTo(cx, cy + radius);
  ctx.moveTo(cx - radius, cy); ctx.lineTo(cx + radius, cy); ctx.stroke();

  // Skin tone line
  ctx.strokeStyle = '#555'; ctx.lineWidth = 1;
  const skinAngle = (123 * Math.PI) / 180;
  ctx.beginPath(); ctx.moveTo(cx, cy);
  ctx.lineTo(cx + Math.cos(skinAngle) * radius, cy - Math.sin(skinAngle) * radius); ctx.stroke();

  for (let sy = 0; sy < sSize; sy++) {
    for (let sx = 0; sx < sSize; sx++) {
      const val = data[sy][sx];
      if (val <= 0) continue;
      ctx.fillStyle = `rgba(80, 180, 255, ${Math.min(1, val / 200)})`;
      ctx.fillRect(oX + sx * scale, oY + sy * scale, Math.max(1, scale), Math.max(1, scale));
    }
  }
}

function drawHistogram(
  ctx: CanvasRenderingContext2D,
  data: { r: number[]; g: number[]; b: number[] },
  w: number, h: number,
) {
  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, w, h);
  const maxVal = Math.max(...data.r.slice(1, 254), ...data.g.slice(1, 254), ...data.b.slice(1, 254), 1);
  const barW = w / 256;
  for (const ch of [
    { bins: data.r, color: 'rgba(255, 60, 60, 0.5)' },
    { bins: data.g, color: 'rgba(60, 255, 60, 0.5)' },
    { bins: data.b, color: 'rgba(60, 100, 255, 0.5)' },
  ]) {
    ctx.fillStyle = ch.color;
    for (let i = 0; i < 256; i++) {
      const barH = (ch.bins[i] / maxVal) * h;
      ctx.fillRect(i * barW, h - barH, Math.max(1, barW), barH);
    }
  }
  ctx.fillStyle = '#555'; ctx.font = '9px system-ui';
  ctx.fillText('0', 2, h - 2); ctx.fillText('255', w - 22, h - 2);
}

// ─── Shared scope socket (singleton across all VideoScopes instances) ───

let scopeSocket: Socket | null = null;
let scopeSocketConsumers = 0;

function getScopeSocket(): Socket {
  if (!scopeSocket) {
    scopeSocket = io(getSocketUrl(), {
      transports: ['websocket', 'polling'],
      autoConnect: true,
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 10,
    });
  }
  return scopeSocket;
}

// ─── Main component ───

export default function VideoScopes() {
  const [mode, setMode] = useState<ScopeMode>('waveform');
  const [postGrade, setPostGrade] = useState(true); // MARKER_B25: default post-grade
  const [scopeData, setScopeData] = useState<ScopeData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [socketConnected, setSocketConnected] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fetchTimerRef = useRef<number>(0);
  const mountedRef = useRef(true);

  const currentTime = useCutEditorStore((s) => s.currentTime);
  const isPlaying = useCutEditorStore((s) => s.isPlaying);
  const sourceMediaPath = useCutEditorStore((s) => s.sourceMediaPath);
  const programMediaPath = useCutEditorStore((s) => s.programMediaPath);
  const mediaPath = programMediaPath || sourceMediaPath;
  // MARKER_B37: Client-side throttle timestamp
  const lastEmitRef = useRef<number>(0);

  // MARKER_B25: Read color_correction from selected clip for post-grade scopes
  const selectedClipCC = useCutEditorStore((s) => {
    if (!s.selectedClipId) return null;
    for (const lane of s.lanes) {
      for (const clip of lane.clips || []) {
        if (clip.clip_id === s.selectedClipId) {
          return (clip as any).color_correction as { lutPath?: string; logProfile?: string } | null;
        }
      }
    }
    return null;
  });

  // MARKER_B27: SocketIO lifecycle — connect, listen, cleanup
  useEffect(() => {
    mountedRef.current = true;
    const socket = getScopeSocket();
    scopeSocketConsumers++;

    const onConnect = () => { if (mountedRef.current) setSocketConnected(true); };
    const onDisconnect = () => { if (mountedRef.current) setSocketConnected(false); };
    const onScopeData = (data: any) => {
      if (!mountedRef.current) return;
      setLoading(false);
      if (data.success) {
        setScopeData(data);
        setError(null);
      } else {
        setError(data.error || 'analysis_failed');
      }
    };

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('scope_data', onScopeData);
    if (socket.connected) setSocketConnected(true);

    return () => {
      mountedRef.current = false;
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('scope_data', onScopeData);
      scopeSocketConsumers--;
      if (scopeSocketConsumers <= 0 && scopeSocket) {
        scopeSocket.disconnect();
        scopeSocket = null;
        scopeSocketConsumers = 0;
      }
    };
  }, []);

  // MARKER_B27 + B37: Build scope request payload (fast mode during playback)
  const buildScopePayload = useCallback((path: string, time: number, playing: boolean) => {
    // MARKER_B37: During playback use fast mode (histogram only, 128px, ~2ms)
    if (playing) {
      return {
        source_path: path,
        time: time,
        mode: 'fast',
      };
    }
    const scopeParam = mode === 'parade' ? 'parade' : mode;
    const payload: Record<string, any> = {
      source_path: path,
      time: time,
      scopes: `${scopeParam},broadcast_safe`,
      size: 256,
      mode: 'full',
    };
    if (postGrade && selectedClipCC) {
      if (selectedClipCC.lutPath) payload.lut_path = selectedClipCC.lutPath;
      if (selectedClipCC.logProfile) payload.log_profile = selectedClipCC.logProfile;
    }
    return payload;
  }, [mode, postGrade, selectedClipCC]);

  // MARKER_B27: HTTP fallback (used when socket disconnected)
  const fetchScopesHttp = useCallback(async (path: string, time: number) => {
    setLoading(true); setError(null);
    try {
      const scopeParam = mode === 'parade' ? 'parade' : mode;
      const scopesList = `${scopeParam},broadcast_safe`;
      let url = `${API_BASE}/cut/scopes/analyze?source_path=${encodeURIComponent(path)}&time=${time}&scopes=${scopesList}&size=256`;
      if (postGrade && selectedClipCC) {
        if (selectedClipCC.lutPath) url += `&lut_path=${encodeURIComponent(selectedClipCC.lutPath)}`;
        if (selectedClipCC.logProfile) url += `&log_profile=${encodeURIComponent(selectedClipCC.logProfile)}`;
      }
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (mountedRef.current) {
        if (data.success) setScopeData(data);
        else setError(data.error || 'analysis_failed');
      }
    } catch (e: any) {
      if (mountedRef.current) setError(e.message || 'fetch_failed');
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [mode, postGrade, selectedClipCC]);

  // MARKER_B27 + B37: Emit scope_request via SocketIO with playback throttle
  useEffect(() => {
    if (!mediaPath) { setScopeData(null); return; }

    // MARKER_B37: Throttle during playback (max 10 updates/sec = 100ms interval)
    if (isPlaying) {
      const now = Date.now();
      if (now - lastEmitRef.current < 100) return; // skip if <100ms since last emit
      lastEmitRef.current = now;
    }

    if (socketConnected && scopeSocket) {
      // SocketIO path — server handles debounce
      setLoading(true);
      scopeSocket.emit('scope_request', buildScopePayload(mediaPath, currentTime, isPlaying));
    } else {
      // HTTP fallback with debounce (500ms paused, 200ms playing)
      if (fetchTimerRef.current) clearTimeout(fetchTimerRef.current);
      const delay = isPlaying ? 200 : 500;
      fetchTimerRef.current = window.setTimeout(() => {
        fetchScopesHttp(mediaPath, currentTime);
      }, delay);
    }

    return () => { if (fetchTimerRef.current) clearTimeout(fetchTimerRef.current); };
  }, [mediaPath, currentTime, mode, postGrade, selectedClipCC, socketConnected, isPlaying, buildScopePayload, fetchScopesHttp]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !scopeData) return;
    const rect = canvas.parentElement?.getBoundingClientRect();
    const w = rect ? Math.floor(rect.width - 16) : 256;
    const h = rect ? Math.floor(rect.height - 16) : 256;
    const size = Math.min(w, h, 512);

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr; canvas.height = size * dpr;
    canvas.style.width = `${size}px`; canvas.style.height = `${size}px`;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);

    if (mode === 'waveform' && scopeData.waveform) drawWaveform(ctx, scopeData.waveform, size, size);
    else if (mode === 'parade' && scopeData.parade) drawParade(ctx, scopeData.parade, size, size);
    else if (mode === 'vectorscope' && scopeData.vectorscope) drawVectorscope(ctx, scopeData.vectorscope, size, size);
    else if (mode === 'histogram' && scopeData.histogram) drawHistogram(ctx, scopeData.histogram, size, size);
  }, [scopeData, mode]);

  const bs = scopeData?.broadcast_safe;

  return (
    <div style={PANEL_STYLE} data-testid="cut-video-scopes">
      <div style={TAB_BAR}>
        {(['waveform', 'parade', 'vectorscope', 'histogram'] as const).map((m) => (
          <button key={m} style={mode === m ? TAB_ACTIVE : TAB_BTN} onClick={() => setMode(m)}
            data-testid={`scope-tab-${m}`}>
            {m === 'waveform' ? 'Waveform' : m === 'parade' ? 'Parade' : m === 'vectorscope' ? 'Vectorscope' : 'Histogram'}
          </button>
        ))}
      </div>
      <div style={CANVAS_WRAP}>
        {!mediaPath ? <span style={{ color: '#555', fontSize: 10 }}>No media selected</span>
          : error ? <span style={{ color: '#999', fontSize: 10 }}>{error}</span>
          : <canvas ref={canvasRef} data-testid="scope-canvas" />}
      </div>
      {/* MARKER_B26: Broadcast safe percentage readouts */}
      {bs && (
        <div
          style={{
            padding: '3px 8px',
            fontSize: 9,
            fontFamily: '"JetBrains Mono", "SF Mono", monospace',
            color: '#777',
            borderTop: '1px solid #1a1a1a',
            display: 'flex',
            gap: 10,
            flexShrink: 0,
            flexWrap: 'wrap',
          }}
          data-testid="broadcast-safe-readout"
        >
          <span
            style={{ color: bs.over_white_pct > 0 ? '#aaa' : '#444' }}
            title="Over-white: pixels with luma Y > 235 (broadcast illegal)"
          >
            OW: {bs.over_white_pct.toFixed(2)}%
          </span>
          <span
            style={{ color: bs.under_black_pct > 0 ? '#aaa' : '#444' }}
            title="Under-black: pixels with luma Y < 16 (broadcast illegal)"
          >
            UB: {bs.under_black_pct.toFixed(2)}%
          </span>
          <span
            style={{ color: bs.chroma_illegal_pct > 0 ? '#aaa' : '#444' }}
            title="Chroma-illegal: Cb/Cr outside 16-240 range"
          >
            CH: {bs.chroma_illegal_pct.toFixed(2)}%
          </span>
          <span
            style={{
              marginLeft: 'auto',
              color: bs.total_illegal_pct === 0 ? '#444' : bs.total_illegal_pct > 5 ? '#bbb' : '#888',
              fontWeight: bs.total_illegal_pct > 5 ? 600 : 400,
            }}
            title="Total illegal pixels"
          >
            {bs.total_illegal_pct === 0 ? 'SAFE' : bs.total_illegal_pct > 5 ? `ILLEGAL ${bs.total_illegal_pct.toFixed(1)}%` : `WARN ${bs.total_illegal_pct.toFixed(1)}%`}
          </span>
        </div>
      )}
      <div style={{ ...STATUS_BAR, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 4 }}>
        <span>
          {loading ? 'Analyzing...' : scopeData ? `${scopeData.frame_w}x${scopeData.frame_h} @ ${currentTime.toFixed(2)}s` : ''}
          {' '}<span style={{ color: socketConnected ? '#555' : '#777', fontSize: 8 }}>{socketConnected ? 'WS' : 'HTTP'}</span>
        </span>
        {/* MARKER_B25: Pre-grade / Post-grade toggle */}
        <button
          onClick={() => setPostGrade((v) => !v)}
          data-testid="scope-grade-toggle"
          style={{
            background: 'none', border: '1px solid #333', borderRadius: 3,
            padding: '1px 6px', cursor: 'pointer', fontSize: 8,
            color: postGrade ? '#999' : '#666',
          }}
          title={postGrade ? 'Showing post-grade (click for raw)' : 'Showing raw (click for post-grade)'}
        >
          {postGrade ? 'Post' : 'Raw'}
        </button>
      </div>
    </div>
  );
}
