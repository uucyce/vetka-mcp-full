/**
 * MARKER_B19: Video Scopes panel — Waveform, Parade, Vectorscope, Histogram.
 *
 * FCP7 Reference: Ch.78 "Measuring and Setting Video Levels"
 * Canvas-based rendering from backend GET /cut/scopes/analyze.
 *
 * Four modes (tabs):
 *   - Waveform: Y=luma (0-100 IRE), X=pixel column, green phosphor
 *   - Parade: R/G/B separate waveforms side by side
 *   - Vectorscope: circular CbCr plot with skin tone line
 *   - Histogram: stacked R/G/B curves
 *
 * Debounced 200ms on playhead change.
 *
 * @phase B19
 * @task tb_1773995025_4
 */
import { useState, useEffect, useRef, useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { API_BASE } from '../../config/api.config';

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
const TAB_ACTIVE: CSSProperties = { ...TAB_BTN, color: '#ccc', borderBottomColor: '#4a9eff' };
const CANVAS_WRAP: CSSProperties = {
  flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 8, minHeight: 0,
};
const STATUS_BAR: CSSProperties = {
  padding: '2px 8px', fontSize: 9, color: '#555', borderTop: '1px solid #1a1a1a', flexShrink: 0,
};

type ScopeData = {
  histogram?: { r: number[]; g: number[]; b: number[] };
  waveform?: number[][];
  vectorscope?: number[][];
  parade?: { r: number[][]; g: number[][]; b: number[][] };
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
  ctx.strokeStyle = '#553300'; ctx.lineWidth = 1;
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

// ─── Main component ───

export default function VideoScopes() {
  const [mode, setMode] = useState<ScopeMode>('waveform');
  const [scopeData, setScopeData] = useState<ScopeData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fetchTimerRef = useRef<number>(0);

  const currentTime = useCutEditorStore((s) => s.currentTime);
  const sourceMediaPath = useCutEditorStore((s) => s.sourceMediaPath);
  const programMediaPath = useCutEditorStore((s) => s.programMediaPath);
  const mediaPath = programMediaPath || sourceMediaPath;

  const fetchScopes = useCallback((path: string, time: number) => {
    if (fetchTimerRef.current) clearTimeout(fetchTimerRef.current);
    fetchTimerRef.current = window.setTimeout(async () => {
      setLoading(true); setError(null);
      try {
        const scopeParam = mode === 'parade' ? 'parade' : mode;
        const url = `${API_BASE}/cut/scopes/analyze?source_path=${encodeURIComponent(path)}&time=${time}&scopes=${scopeParam}&size=256`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.success) setScopeData(data);
        else setError(data.error || 'analysis_failed');
      } catch (e: any) {
        setError(e.message || 'fetch_failed');
      } finally {
        setLoading(false);
      }
    }, 200);
  }, [mode]);

  useEffect(() => {
    if (!mediaPath) { setScopeData(null); return; }
    fetchScopes(mediaPath, currentTime);
    return () => { if (fetchTimerRef.current) clearTimeout(fetchTimerRef.current); };
  }, [mediaPath, currentTime, mode, fetchScopes]);

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
          : error ? <span style={{ color: '#ef4444', fontSize: 10 }}>{error}</span>
          : <canvas ref={canvasRef} data-testid="scope-canvas" />}
      </div>
      <div style={STATUS_BAR}>
        {loading ? 'Analyzing...' : scopeData ? `${scopeData.frame_w}x${scopeData.frame_h} @ ${currentTime.toFixed(2)}s` : ''}
      </div>
    </div>
  );
}
