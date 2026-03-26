/**
 * MARKER_B26: ZebraOverlay — broadcast safe pixel detection overlay.
 *
 * Renders diagonal stripe patterns on out-of-range pixels:
 *   - Light grey stripes (45°) for over-white pixels (Y > 235)
 *   - Dark grey stripes (135°) for under-black pixels (Y < 16)
 *
 * Displays percentage readout: "OW: 2.3% | UB: 0.1%"
 *
 * MONOCHROME ONLY — zero color. Grey stripes, white text.
 *
 * @phase B26
 * @task tb_1774410744_1
 */
import { useEffect, useRef, useState, useCallback, type CSSProperties } from 'react';
import { API_BASE } from '../../config/api.config';

type ZebraData = {
  over_white_pct: number;
  under_black_pct: number;
  chroma_illegal_pct: number;
  total_illegal_pct: number;
  zebra_mask_b64: string;
  frame_w: number;
  frame_h: number;
};

type ZebraOverlayProps = {
  mediaPath: string;
  currentTime: number;
};

// Throttle zebra requests: max 1 per 500ms while paused, 1 per 2s while playing
const ZEBRA_FETCH_THROTTLE_MS = 500;

const OVERLAY_STYLE: CSSProperties = {
  position: 'absolute',
  inset: 0,
  pointerEvents: 'none',
  zIndex: 6,
};

const READOUT_STYLE: CSSProperties = {
  position: 'absolute',
  bottom: 30,
  left: 8,
  fontSize: 9,
  fontFamily: '"JetBrains Mono", "SF Mono", monospace',
  color: '#ccc',
  background: 'rgba(0,0,0,0.65)',
  padding: '2px 6px',
  borderRadius: 3,
  letterSpacing: 0.5,
  userSelect: 'none',
  zIndex: 11,
  pointerEvents: 'none',
};

/**
 * Draw zebra stripe pattern directly on canvas using the mask data from backend.
 * Mask pixel encoding (R channel): 200=over-white, 100=under-black, 150=chroma
 * Alpha channel: 255 for out-of-range, 0 for safe.
 *
 * We draw diagonal stripe patterns:
 *   over-white (R=200): light grey (45° stripes, #b0b0b0 on even diagonals)
 *   under-black (R=100): dark grey (135° stripes, #404040 on even diagonals)
 *   chroma-illegal (R=150): mid-grey checkerboard
 */
function drawZebraCanvas(
  canvas: HTMLCanvasElement,
  img: HTMLImageElement,
  maskW: number,
  maskH: number,
): void {
  // Draw mask image to offscreen canvas to read pixel data
  const offscreen = document.createElement('canvas');
  offscreen.width = maskW;
  offscreen.height = maskH;
  const offCtx = offscreen.getContext('2d');
  if (!offCtx) return;
  offCtx.drawImage(img, 0, 0, maskW, maskH);
  const maskPixels = offCtx.getImageData(0, 0, maskW, maskH);

  const dw = canvas.width;
  const dh = canvas.height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  ctx.clearRect(0, 0, dw, dh);

  // Scale factors from mask coordinates to canvas coordinates
  const scX = dw / maskW;
  const scY = dh / maskH;

  // Pre-create stripe patterns for over-white and under-black
  // Over-white: light grey 45° diagonal stripes
  const owPattern = createStripePattern(ctx, '#b8b8b8', '#1a1a1a', 45, 4);
  // Under-black: dark grey 135° diagonal stripes
  const ubPattern = createStripePattern(ctx, '#383838', '#0a0a0a', 135, 4);
  // Chroma illegal: mid-grey dots
  const ciPattern = createStripePattern(ctx, '#707070', '#111', 0, 3);

  const data = maskPixels.data;

  for (let y = 0; y < maskH; y++) {
    for (let x = 0; x < maskW; x++) {
      const idx = (y * maskW + x) * 4;
      const r = data[idx];
      const a = data[idx + 3];
      if (a === 0) continue; // safe pixel

      const px = x * scX;
      const py = y * scY;
      const pw = Math.max(1, scX);
      const ph = Math.max(1, scY);

      if (r === 200 && owPattern) {
        ctx.fillStyle = owPattern;
      } else if (r === 100 && ubPattern) {
        ctx.fillStyle = ubPattern;
      } else if (r === 150 && ciPattern) {
        ctx.fillStyle = ciPattern;
      } else {
        continue;
      }
      ctx.fillRect(px, py, pw, ph);
    }
  }
}

/**
 * Create a repeating diagonal stripe CanvasPattern.
 * angle: 45 = top-left → bottom-right, 135 = top-right → bottom-left, 0 = horizontal bands
 */
function createStripePattern(
  ctx: CanvasRenderingContext2D,
  stripeColor: string,
  bgColor: string,
  angle: number,
  stripeWidth: number,
): CanvasPattern | null {
  const size = stripeWidth * 4;
  const patCanvas = document.createElement('canvas');
  patCanvas.width = size;
  patCanvas.height = size;
  const pCtx = patCanvas.getContext('2d');
  if (!pCtx) return null;

  pCtx.fillStyle = bgColor;
  pCtx.fillRect(0, 0, size, size);

  pCtx.strokeStyle = stripeColor;
  pCtx.lineWidth = stripeWidth;

  if (angle === 45) {
    // 45° stripes: draw diagonal lines
    for (let i = -size; i < size * 2; i += stripeWidth * 2) {
      pCtx.beginPath();
      pCtx.moveTo(i, 0);
      pCtx.lineTo(i + size, size);
      pCtx.stroke();
    }
  } else if (angle === 135) {
    // 135° stripes: opposite diagonal
    for (let i = -size; i < size * 2; i += stripeWidth * 2) {
      pCtx.beginPath();
      pCtx.moveTo(i + size, 0);
      pCtx.lineTo(i, size);
      pCtx.stroke();
    }
  } else {
    // Horizontal bands
    for (let i = 0; i < size; i += stripeWidth * 2) {
      pCtx.fillStyle = stripeColor;
      pCtx.fillRect(0, i, size, stripeWidth);
    }
  }

  return ctx.createPattern(patCanvas, 'repeat');
}

export default function ZebraOverlay({ mediaPath, currentTime }: ZebraOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [zebraData, setZebraData] = useState<ZebraData | null>(null);
  const lastFetchRef = useRef<number>(0);
  const fetchTimerRef = useRef<number>(0);
  const mountedRef = useRef(true);

  const fetchZebra = useCallback(async (path: string, time: number) => {
    const now = Date.now();
    if (now - lastFetchRef.current < ZEBRA_FETCH_THROTTLE_MS) return;
    lastFetchRef.current = now;

    try {
      const res = await fetch(`${API_BASE}/cut/scopes/zebra`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_path: path, time, max_width: 512 }),
      });
      if (!res.ok) return;
      const data = await res.json() as ZebraData & { success?: boolean };
      if (!mountedRef.current || !data.success) return;
      setZebraData(data);
    } catch {
      // silently ignore — zebra is non-critical
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (fetchTimerRef.current) clearTimeout(fetchTimerRef.current);
    };
  }, []);

  // Debounced fetch on time/path changes
  useEffect(() => {
    if (!mediaPath) return;
    if (fetchTimerRef.current) clearTimeout(fetchTimerRef.current);
    fetchTimerRef.current = window.setTimeout(() => {
      void fetchZebra(mediaPath, currentTime);
    }, 300);
    return () => { if (fetchTimerRef.current) clearTimeout(fetchTimerRef.current); };
  }, [mediaPath, currentTime, fetchZebra]);

  // Render zebra stripes onto canvas when data arrives
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !zebraData?.zebra_mask_b64) {
      if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx?.clearRect(0, 0, canvas.width, canvas.height);
      }
      return;
    }

    const container = canvas.parentElement;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;

    const img = new Image();
    img.onload = () => {
      if (!mountedRef.current) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.scale(dpr, dpr);
      drawZebraCanvas(canvas, img, zebraData.frame_w || img.width, zebraData.frame_h || img.height);
    };
    img.src = `data:image/png;base64,${zebraData.zebra_mask_b64}`;
  }, [zebraData]);

  const owPct = zebraData?.over_white_pct ?? 0;
  const ubPct = zebraData?.under_black_pct ?? 0;
  const showReadout = owPct > 0 || ubPct > 0;

  return (
    <>
      <canvas ref={canvasRef} style={OVERLAY_STYLE} data-testid="zebra-canvas" />
      {showReadout && (
        <div style={READOUT_STYLE} data-testid="zebra-readout">
          {owPct > 0 && `OW: ${owPct.toFixed(1)}%`}
          {owPct > 0 && ubPct > 0 && '  |  '}
          {ubPct > 0 && `UB: ${ubPct.toFixed(1)}%`}
          {zebraData && zebraData.chroma_illegal_pct > 0 && `  CH: ${zebraData.chroma_illegal_pct.toFixed(1)}%`}
        </div>
      )}
    </>
  );
}
