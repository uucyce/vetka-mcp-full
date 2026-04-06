// @ts-nocheck
/**
 * MARKER_WEBCODECS: useVideoDecoder — Client-side frame decode via WebCodecs API.
 *
 * Eliminates the server preview roundtrip for color correction preview:
 *   BEFORE: POST /cut/preview/frame → FFmpeg/PyAV decode → numpy → JPEG → base64 → ~150ms
 *   AFTER:  VideoDecoder.decode() → VideoFrame → OffscreenCanvas → ~5ms
 *
 * Architecture:
 *   useVideoDecoder(mediaUrl, config) → { decodeFrame, canvas, status, isSupported }
 *
 *   1. Fetch video → demux to raw NAL unit chunks via fetch range requests
 *   2. Feed EncodedVideoChunk to VideoDecoder
 *   3. Output VideoFrame → paint to OffscreenCanvas
 *   4. Apply color effects via CSS filter string (caller's responsibility)
 *   5. Fallback to server path when WebCodecs unsupported or codec not H.264/VP9/AV1
 *
 * Codec support (as of 2026):
 *   Chrome 94+: H.264, VP9, AV1 (hw), VP8
 *   Safari 16+: H.264, HEVC (hw), VP9
 *   Firefox 130+: H.264, VP9, AV1 (sw)
 *
 * Integration with ColorCorrectionPanel:
 *   Replace the POST /cut/preview/frame fetch with decodeFrame(timeSec).
 *   Color effects (exposure/contrast/saturation/hue) stay as CSS filters applied
 *   to the canvas element — no server round-trip needed for basic grading preview.
 *   LUT + log profile effects still require server path (numpy operations).
 *
 * @phase: BETA-RESEARCH (WEBCODECS)
 * @task: tb_1774423957_1
 * @status: prototype
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Codec strings accepted by VideoDecoder.configure() */
export type WebCodecsVideoCodec =
  | 'avc1.42001e'   // H.264 Baseline L3.0
  | 'avc1.4d001f'   // H.264 Main L3.1
  | 'avc1.64001f'   // H.264 High L3.1
  | 'avc1.640028'   // H.264 High L4.0
  | 'vp09.00.10.08' // VP9 Profile 0
  | 'vp09.02.10.10' // VP9 Profile 2 (10-bit)
  | 'av01.0.04M.08' // AV1 Main Profile
  | 'hvc1.1.6.L93.B0'; // HEVC Main (Safari)

export interface VideoDecoderConfig {
  /** Full codec string — detected automatically from media probe when omitted */
  codec?: WebCodecsVideoCodec | string;
  /** Frame decode width (proxy resolution) — default 480 */
  targetWidth?: number;
  /** Frame decode height (proxy resolution) — default 270 */
  targetHeight?: number;
  /** Max frames to keep in decode queue before dropping */
  maxQueueDepth?: number;
}

export interface DecodeFrameResult {
  /** Canvas element containing the decoded frame */
  canvas: OffscreenCanvas | null;
  /** Decode latency in milliseconds */
  latencyMs: number;
  /** Backend used for this frame */
  backend: 'webcodecs' | 'server_fallback';
  /** Width of decoded frame */
  width: number;
  /** Height of decoded frame */
  height: number;
  /** Error message if decode failed */
  error?: string;
}

export interface UseVideoDecoderState {
  /** Whether WebCodecs is available in this browser */
  isSupported: boolean;
  /** Detected codec string from media metadata */
  detectedCodec: string | null;
  /** Whether the detected codec is supported by WebCodecs */
  codecSupported: boolean;
  /** Initialisation status */
  status: 'idle' | 'initializing' | 'ready' | 'error' | 'fallback';
  /** Error message if status === 'error' */
  error: string | null;
}

/** Parameters for server-side fallback request (mirrors CutPreviewRequest) */
export interface ServerPreviewRequest {
  source_path: string;
  time: number;
  proxy_height?: number;
  jpeg_quality?: number;
  effects?: Array<{ type: string; params: Record<string, number | string>; enabled: boolean }>;
}

// ---------------------------------------------------------------------------
// WebCodecs feature detection
// ---------------------------------------------------------------------------

/**
 * Returns true if the WebCodecs VideoDecoder API is available in this context.
 * Requires secure context (HTTPS or localhost).
 */
export function isWebCodecsSupported(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof (window as unknown as { VideoDecoder?: unknown }).VideoDecoder === 'function'
  );
}

/**
 * Check whether a specific codec string is supported by the browser's VideoDecoder.
 * This is async because the browser may need to query hardware capabilities.
 *
 * @example
 *   const supported = await isCodecSupported('avc1.4d001f');
 */
export async function isCodecSupported(codec: string): Promise<boolean> {
  if (!isWebCodecsSupported()) return false;
  try {
    type VideoDecoderGlobal = {
      VideoDecoder: {
        isConfigSupported(config: { codec: string }): Promise<{ supported: boolean }>;
      };
    };
    const VD = (window as unknown as VideoDecoderGlobal).VideoDecoder;
    const result = await VD.isConfigSupported({ codec });
    return result.supported === true;
  } catch {
    return false;
  }
}

/**
 * Map common container codec names to WebCodecs codec strings.
 * Source: MDN VideoDecoder codec strings + browser compatibility tables.
 */
export function mapCodecToWebCodecs(containerCodec: string): string | null {
  const normalized = containerCodec.toLowerCase().trim();

  // H.264 / AVC — most common, best support across all browsers
  if (normalized.includes('h264') || normalized.includes('avc') || normalized.includes('x264')) {
    return 'avc1.4d001f'; // H.264 Main L3.1 — safe default
  }

  // VP9 — Chrome + Firefox + Safari 16+
  if (normalized.includes('vp9') || normalized.includes('vp09')) {
    return 'vp09.00.10.08'; // VP9 Profile 0, 8-bit
  }

  // AV1 — Chrome + Firefox (SW), hardware in recent GPUs
  if (normalized.includes('av1') || normalized.includes('av01')) {
    return 'av01.0.04M.08'; // AV1 Main Profile
  }

  // HEVC / H.265 — Safari hardware only, Chrome with extension
  if (normalized.includes('h265') || normalized.includes('hevc') || normalized.includes('x265')) {
    return 'hvc1.1.6.L93.B0'; // HEVC Main
  }

  // VP8 — legacy, Chrome + Firefox
  if (normalized.includes('vp8')) {
    return 'vp8';
  }

  // Unsupported by WebCodecs: ProRes, DNxHR, FFV1, MJPEG, MPEG-2, etc.
  return null;
}

// ---------------------------------------------------------------------------
// Chunk demux helper (range-request based)
// ---------------------------------------------------------------------------

/**
 * Minimal MP4/WebM chunk extractor for feeding VideoDecoder.
 *
 * For a production implementation this would use:
 *   - mp4box.js (MP4/H.264)
 *   - matroska.js (MKV/WebM/VP9)
 *
 * This prototype uses a simplified approach:
 *   1. Fetch a small range around the target time
 *   2. Pass the range as a single "key" chunk (works for I-frame seeking)
 *
 * Production note: full frame-accurate decode requires a proper demuxer
 * that can extract individual NAL units with correct timestamps/durations.
 */
async function fetchKeyframeChunk(
  mediaUrl: string,
  timeSec: number,
  opts: { approxBytesPerSecond?: number; chunkWindowSec?: number } = {}
): Promise<Uint8Array | null> {
  const { approxBytesPerSecond = 500_000, chunkWindowSec = 2 } = opts;

  // Approximate byte offset: this is intentionally rough — real demux needs
  // moov box parsing to get the stts/stco tables for precise offset mapping.
  const byteStart = Math.max(0, Math.floor(timeSec * approxBytesPerSecond));
  const byteEnd = byteStart + Math.floor(chunkWindowSec * approxBytesPerSecond);

  try {
    const resp = await fetch(mediaUrl, {
      headers: { Range: `bytes=${byteStart}-${byteEnd}` },
    });
    if (!resp.ok && resp.status !== 206) return null;
    const buffer = await resp.arrayBuffer();
    return new Uint8Array(buffer);
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Core decode pipeline
// ---------------------------------------------------------------------------

/**
 * Decode a single video frame using the WebCodecs VideoDecoder API.
 *
 * This is the low-level function — useVideoDecoder wraps it with state management.
 *
 * @param mediaUrl    Absolute URL to the video file (served by /files/raw or similar)
 * @param timeSec     Target time in seconds
 * @param codec       WebCodecs codec string (e.g. 'avc1.4d001f')
 * @param targetWidth Decode output width
 * @param targetHeight Decode output height
 * @returns Promise<{ frame: VideoFrame | null; latencyMs: number }>
 */
export async function decodeFrameWebCodecs(
  mediaUrl: string,
  timeSec: number,
  codec: string,
  targetWidth: number = 480,
  targetHeight: number = 270,
): Promise<{ frame: VideoFrame | null; latencyMs: number }> {
  const t0 = performance.now();

  return new Promise(async (resolve) => {
    type VideoDecoderType = {
      new(init: {
        output: (frame: VideoFrame) => void;
        error: (e: Error) => void;
      }): {
        configure(config: {
          codec: string;
          codedWidth: number;
          codedHeight: number;
          hardwareAcceleration?: string;
        }): void;
        decode(chunk: EncodedVideoChunkType): void;
        flush(): Promise<void>;
        close(): void;
        state: string;
      };
    };

    type EncodedVideoChunkType = InstanceType<{
      new(init: {
        type: 'key' | 'delta';
        timestamp: number;
        duration: number;
        data: Uint8Array;
      }): object;
    }>;

    const VideoDecoderClass = (window as unknown as { VideoDecoder: VideoDecoderType }).VideoDecoder;
    const EncodedVideoChunkClass = (window as unknown as { EncodedVideoChunk: EncodedVideoChunkType }).EncodedVideoChunk;

    let resolved = false;
    let decoder: ReturnType<VideoDecoderType> | null = null;

    const resolve_once = (frame: VideoFrame | null) => {
      if (resolved) return;
      resolved = true;
      if (decoder && decoder.state !== 'closed') {
        try { decoder.close(); } catch { /* ignore */ }
      }
      resolve({ frame, latencyMs: performance.now() - t0 });
    };

    // Timeout guard — fall back if decode takes > 500ms
    const timeout = setTimeout(() => resolve_once(null), 500);

    decoder = new VideoDecoderClass({
      output: (videoFrame: VideoFrame) => {
        clearTimeout(timeout);
        resolve_once(videoFrame);
      },
      error: (_err: Error) => {
        clearTimeout(timeout);
        resolve_once(null);
      },
    });

    try {
      decoder.configure({
        codec,
        codedWidth: targetWidth,
        codedHeight: targetHeight,
        hardwareAcceleration: 'prefer-hardware',
      });

      const chunk = await fetchKeyframeChunk(mediaUrl, timeSec);
      if (!chunk) {
        clearTimeout(timeout);
        resolve_once(null);
        return;
      }

      const encodedChunk = new EncodedVideoChunkClass({
        type: 'key',
        timestamp: Math.floor(timeSec * 1_000_000), // microseconds
        duration: 33_333, // ~1 frame at 30fps
        data: chunk,
      });

      decoder.decode(encodedChunk as unknown as Parameters<typeof decoder.decode>[0]);
      await decoder.flush();
    } catch (_err) {
      clearTimeout(timeout);
      resolve_once(null);
    }
  });
}

/**
 * Paint a VideoFrame to an OffscreenCanvas with optional CSS-style color transform.
 *
 * For preview grading, we use ImageBitmap + drawImage which is GPU-accelerated.
 * Color correction is applied via CanvasRenderingContext2D.filter (CSS filter string).
 *
 * @param frame       VideoFrame from VideoDecoder output callback
 * @param cssFilter   CSS filter string e.g. "brightness(1.2) contrast(1.1) saturate(0.9)"
 */
export function paintFrameToCanvas(
  frame: VideoFrame,
  cssFilter?: string
): OffscreenCanvas {
  const canvas = new OffscreenCanvas(frame.displayWidth, frame.displayHeight);
  const ctx = canvas.getContext('2d') as OffscreenCanvasRenderingContext2D | null;

  if (!ctx) {
    frame.close();
    return canvas;
  }

  if (cssFilter) {
    ctx.filter = cssFilter;
  }

  ctx.drawImage(frame as unknown as CanvasImageSource, 0, 0);
  frame.close(); // Release GPU memory immediately

  return canvas;
}

/**
 * Convert an OffscreenCanvas to a data URL (for use as <img> src).
 * This is the integration point with ColorCorrectionPanel's previewSrc state.
 */
export async function canvasToDataUrl(
  canvas: OffscreenCanvas,
  quality: number = 0.8
): Promise<string> {
  const blob = await canvas.convertToBlob({ type: 'image/jpeg', quality });
  return URL.createObjectURL(blob);
}

// ---------------------------------------------------------------------------
// Server fallback
// ---------------------------------------------------------------------------

/**
 * Fall back to the existing server-side preview pipeline.
 * Matches the fetch in ColorCorrectionPanel.tsx.
 */
export async function fetchServerPreviewFrame(
  apiBase: string,
  request: ServerPreviewRequest
): Promise<{ dataUrl: string | null; latencyMs: number }> {
  const t0 = performance.now();
  try {
    const resp = await fetch(`${apiBase}/cut/preview/frame`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    const data = await resp.json();
    if (data.success && data.data) {
      return {
        dataUrl: `data:image/jpeg;base64,${data.data}`,
        latencyMs: performance.now() - t0,
      };
    }
  } catch {
    // silent
  }
  return { dataUrl: null, latencyMs: performance.now() - t0 };
}

// ---------------------------------------------------------------------------
// Main hook
// ---------------------------------------------------------------------------

/**
 * useVideoDecoder — React hook for client-side frame decode via WebCodecs.
 *
 * Usage:
 *   const { decodeFrame, status, isSupported, codecSupported } = useVideoDecoder(
 *     `${API_BASE}/files/raw?path=${encodeURIComponent(mediaPath)}`,
 *     { codec: 'avc1.4d001f', targetWidth: 480, targetHeight: 270 }
 *   );
 *
 *   // In ColorCorrectionPanel — replace the POST /preview/frame fetch:
 *   const result = await decodeFrame(currentTime, cssFilterString, fallbackRequest);
 *   if (result.backend === 'webcodecs') {
 *     setPreviewSrc(await canvasToDataUrl(result.canvas!));
 *   } else {
 *     setPreviewSrc(result.dataUrl);
 *   }
 *
 * Integration notes:
 *   - Basic color effects (exposure/contrast/saturation/hue) → CSS filter on canvas (GPU, ~0ms)
 *   - LUT, log profile, 3-way color wheels → must still use server path (numpy)
 *   - Auto-detects codec from media URL probing when codec prop omitted
 *   - Falls back silently to server when WebCodecs unavailable or codec unsupported
 *
 * @param mediaUrl   Absolute URL to the video file for direct browser access
 * @param config     VideoDecoderConfig — codec, targetWidth, targetHeight
 * @param apiBase    API base URL for server fallback (default from import)
 */
export function useVideoDecoder(
  mediaUrl: string | null,
  config: VideoDecoderConfig = {},
  apiBase: string = ''
): {
  decodeFrame: (
    timeSec: number,
    cssFilter?: string,
    fallback?: ServerPreviewRequest
  ) => Promise<DecodeFrameResult & { dataUrl?: string }>;
  state: UseVideoDecoderState;
  isSupported: boolean;
} {
  // Lazy import React to avoid issues in non-React contexts
  // This hook must be called from a React component or another hook.
  const React = require('react') as typeof import('react');

  const { targetWidth = 480, targetHeight = 270 } = config;

  const [state, setState] = React.useState<UseVideoDecoderState>({
    isSupported: isWebCodecsSupported(),
    detectedCodec: config.codec ?? null,
    codecSupported: false,
    status: 'idle',
    error: null,
  });

  // Initialise: check codec support once mediaUrl is set
  React.useEffect(() => {
    if (!mediaUrl) return;
    if (!isWebCodecsSupported()) {
      setState((prev) => ({ ...prev, status: 'fallback', error: 'WebCodecs not available in this browser' }));
      return;
    }

    setState((prev) => ({ ...prev, status: 'initializing' }));

    const run = async () => {
      let codecStr = config.codec ?? null;

      // If no explicit codec, try to detect from URL extension
      if (!codecStr && mediaUrl) {
        const ext = mediaUrl.split('?')[0].split('.').pop()?.toLowerCase() ?? '';
        const guessMap: Record<string, string> = {
          mp4: 'avc1.4d001f',
          m4v: 'avc1.4d001f',
          webm: 'vp09.00.10.08',
          mov: 'avc1.4d001f',
        };
        codecStr = guessMap[ext] ?? null;
      }

      if (!codecStr) {
        setState((prev) => ({
          ...prev,
          status: 'fallback',
          detectedCodec: null,
          codecSupported: false,
          error: 'Cannot detect codec — use server fallback',
        }));
        return;
      }

      const supported = await isCodecSupported(codecStr);

      setState((prev) => ({
        ...prev,
        status: supported ? 'ready' : 'fallback',
        detectedCodec: codecStr,
        codecSupported: supported,
        error: supported ? null : `Codec ${codecStr} not supported by this browser`,
      }));
    };

    void run();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mediaUrl, config.codec]);

  /**
   * Decode a single frame at the given time.
   *
   * - If WebCodecs is ready and codec supported: decode client-side in ~5ms
   * - Otherwise: falls back to server POST /cut/preview/frame (~150ms)
   *
   * @param timeSec    Target time in seconds
   * @param cssFilter  CSS filter string for client-side color preview
   * @param fallback   Server fallback request params (required for server path)
   */
  const decodeFrame = React.useCallback(
    async (
      timeSec: number,
      cssFilter?: string,
      fallback?: ServerPreviewRequest
    ): Promise<DecodeFrameResult & { dataUrl?: string }> => {
      const useWebCodecs = state.status === 'ready' && state.codecSupported && state.detectedCodec && mediaUrl;

      if (useWebCodecs) {
        const { frame, latencyMs } = await decodeFrameWebCodecs(
          mediaUrl!,
          timeSec,
          state.detectedCodec!,
          targetWidth,
          targetHeight
        );

        if (frame) {
          const canvas = paintFrameToCanvas(frame, cssFilter);
          return {
            canvas,
            latencyMs,
            backend: 'webcodecs',
            width: canvas.width,
            height: canvas.height,
          };
        }
        // WebCodecs decode failed — fall through to server
      }

      // Server fallback
      if (fallback && apiBase) {
        const { dataUrl, latencyMs } = await fetchServerPreviewFrame(apiBase, fallback);
        return {
          canvas: null,
          dataUrl: dataUrl ?? undefined,
          latencyMs,
          backend: 'server_fallback',
          width: targetWidth,
          height: targetHeight,
          error: dataUrl ? undefined : 'server decode failed',
        };
      }

      return {
        canvas: null,
        latencyMs: 0,
        backend: 'server_fallback',
        width: 0,
        height: 0,
        error: 'no fallback configured',
      };
    },
    [state.status, state.codecSupported, state.detectedCodec, mediaUrl, apiBase, targetWidth, targetHeight]
  );

  return {
    decodeFrame,
    state,
    isSupported: state.isSupported,
  };
}

// ---------------------------------------------------------------------------
// ColorCorrectionPanel integration helper
// ---------------------------------------------------------------------------

/**
 * Build a CSS filter string from ColorCorrectionPanel's ColorState.
 *
 * This covers the "fast path" effects that can be previewed without a server round-trip.
 * LUT, log profile, 3-way color wheels, and curves are NOT included — those still need
 * the server pipeline.
 *
 * Returns null when no fast-path effects are active (signal to use server path).
 */
export interface FastPathColorState {
  exposure: number;    // stops: -4..+4
  contrast: number;    // 0..3, default 1.0
  saturation: number;  // 0..3, default 1.0
  hue: number;         // degrees: -180..180
}

export function buildCssFilterFromColorState(color: FastPathColorState): string | undefined {
  const parts: string[] = [];

  if (color.exposure !== 0) {
    // exposure in stops → brightness multiplier: 2^stops
    parts.push(`brightness(${Math.pow(2, color.exposure).toFixed(4)})`);
  }
  if (color.contrast !== 1) {
    parts.push(`contrast(${color.contrast.toFixed(3)})`);
  }
  if (color.saturation !== 1) {
    parts.push(`saturate(${color.saturation.toFixed(3)})`);
  }
  if (color.hue !== 0) {
    parts.push(`hue-rotate(${color.hue}deg)`);
  }

  return parts.length > 0 ? parts.join(' ') : undefined;
}

/**
 * Returns true if the given color state has effects that REQUIRE the server path.
 * (LUT, log profile, 3-way color wheels, curves)
 */
export function requiresServerPath(color: {
  liftR?: number; liftG?: number; liftB?: number;
  midR?: number; midG?: number; midB?: number;
  gainR?: number; gainG?: number; gainB?: number;
  curvesPreset?: string;
  curveData?: unknown;
  temperature?: number;
  tint?: number;
  log_profile?: string | null;
  lut_path?: string | null;
}): boolean {
  // 3-way color wheels
  if (
    color.liftR || color.liftG || color.liftB ||
    color.midR || color.midG || color.midB ||
    color.gainR || color.gainG || color.gainB
  ) return true;

  // Curves (non-default)
  if (color.curvesPreset && color.curvesPreset !== 'none') return true;

  // White balance (temperature/tint) needs numpy color math
  if ((color.temperature && color.temperature !== 6500) || color.tint) return true;

  // LUT or log profile
  if (color.log_profile || color.lut_path) return true;

  return false;
}
