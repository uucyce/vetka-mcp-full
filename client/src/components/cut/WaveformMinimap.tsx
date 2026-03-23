/**
 * MARKER_B40: Real-time audio waveform minimap via WebSocket.
 *
 * Shows rolling stereo waveform bins received from backend audio_scope_data.
 * Designed for Source Monitor area — compact, monochrome, FCP7 style.
 *
 * Architecture:
 *   Client emits "audio_scope_request" on playhead change (throttled).
 *   Server extracts PCM window, computes RMS bins, emits "audio_scope_data".
 *   This component renders L/R waveform from those bins.
 *
 * @phase B40
 * @task tb_1774241112_1
 */
import { useState, useEffect, useRef, useCallback, type CSSProperties } from 'react';
import { io, type Socket } from 'socket.io-client';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { getSocketUrl } from '../../config/api.config';

// ─── Shared audio scope socket (singleton) ───

let audioScopeSocket: Socket | null = null;
let audioScopeConsumers = 0;

function getAudioScopeSocket(): Socket {
  if (!audioScopeSocket) {
    audioScopeSocket = io(getSocketUrl(), {
      transports: ['websocket', 'polling'],
      autoConnect: true,
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 10,
    });
  }
  return audioScopeSocket;
}

/** Exported for AudioLevelMeter to share the same socket */
export { getAudioScopeSocket };

// ─── Types ───

type AudioScopeData = {
  success: boolean;
  rms_left: number;
  rms_right: number;
  peak_left: number;
  peak_right: number;
  waveform_left?: number[];
  waveform_right?: number[];
  time_sec: number;
  source_path: string;
};

// ─── Component ───

type WaveformMinimapProps = {
  /** Number of waveform bins to request from backend */
  bins?: number;
  style?: CSSProperties;
};

const CONTAINER: CSSProperties = {
  background: '#0a0a0a',
  border: '1px solid #222',
  borderRadius: 2,
  overflow: 'hidden',
  position: 'relative',
};

export default function WaveformMinimap({ bins = 32, style }: WaveformMinimapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mountedRef = useRef(true);
  const lastEmitRef = useRef(0);
  const [socketConnected, setSocketConnected] = useState(false);
  const [data, setData] = useState<AudioScopeData | null>(null);

  const currentTime = useCutEditorStore((s) => s.currentTime);
  const isPlaying = useCutEditorStore((s) => s.isPlaying);
  const sourceMediaPath = useCutEditorStore((s) => s.sourceMediaPath);
  const programMediaPath = useCutEditorStore((s) => s.programMediaPath);
  const mediaPath = programMediaPath || sourceMediaPath;

  // SocketIO lifecycle
  useEffect(() => {
    mountedRef.current = true;
    const socket = getAudioScopeSocket();
    audioScopeConsumers++;

    const onConnect = () => { if (mountedRef.current) setSocketConnected(true); };
    const onDisconnect = () => { if (mountedRef.current) setSocketConnected(false); };
    const onData = (d: AudioScopeData) => {
      if (mountedRef.current && d.success) setData(d);
    };

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('audio_scope_data', onData);
    if (socket.connected) setSocketConnected(true);

    return () => {
      mountedRef.current = false;
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('audio_scope_data', onData);
      audioScopeConsumers--;
      if (audioScopeConsumers <= 0 && audioScopeSocket) {
        audioScopeSocket.disconnect();
        audioScopeSocket = null;
        audioScopeConsumers = 0;
      }
    };
  }, []);

  // Emit audio_scope_request on playhead change (throttled)
  const emitRequest = useCallback(() => {
    if (!socketConnected || !mediaPath) return;
    const now = Date.now();
    const throttleMs = isPlaying ? 100 : 0; // 10/sec during playback
    if (now - lastEmitRef.current < throttleMs) return;
    lastEmitRef.current = now;

    const socket = getAudioScopeSocket();
    socket.emit('audio_scope_request', {
      source_path: mediaPath,
      time: currentTime,
      mode: isPlaying ? 'fast' : 'full',
      waveform_bins: bins,
    });
  }, [socketConnected, mediaPath, currentTime, isPlaying, bins]);

  useEffect(() => {
    emitRequest();
  }, [emitRequest]);

  // Draw waveform on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    // Background
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, w, h);

    const binsL = data.waveform_left;
    const binsR = data.waveform_right;

    if (binsL && binsR && binsL.length > 0) {
      // Stereo mirrored: L top half, R bottom half
      const midY = h / 2;
      const binW = w / binsL.length;

      // Center line
      ctx.strokeStyle = '#222';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(0, midY);
      ctx.lineTo(w, midY);
      ctx.stroke();

      // Left channel (upward from center)
      ctx.fillStyle = '#888';
      for (let i = 0; i < binsL.length; i++) {
        const barH = binsL[i] * midY * 0.9;
        ctx.fillRect(i * binW, midY - barH, Math.max(1, binW - 0.5), barH);
      }

      // Right channel (downward from center)
      ctx.fillStyle = '#666';
      for (let i = 0; i < binsR.length; i++) {
        const barH = binsR[i] * midY * 0.9;
        ctx.fillRect(i * binW, midY, Math.max(1, binW - 0.5), barH);
      }
    } else {
      // No waveform bins — show RMS bars as fallback
      const rmsL = data.rms_left || 0;
      const rmsR = data.rms_right || 0;
      const barW = w / 2 - 2;
      ctx.fillStyle = '#888';
      ctx.fillRect(1, h - rmsL * h, barW, rmsL * h);
      ctx.fillStyle = '#666';
      ctx.fillRect(w / 2 + 1, h - rmsR * h, barW, rmsR * h);
    }

    // L/R labels
    ctx.fillStyle = '#444';
    ctx.font = '8px system-ui';
    ctx.fillText('L', 2, 9);
    ctx.fillText('R', 2, h - 2);
  }, [data]);

  return (
    <div style={{ ...CONTAINER, ...style }}>
      <canvas
        ref={canvasRef}
        style={{ width: '100%', height: '100%', display: 'block' }}
      />
      {!socketConnected && (
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 9, color: '#333',
        }}>
          No audio scope
        </div>
      )}
    </div>
  );
}
