/**
 * MARKER_170.NLE.AUDIO_METER: Real-time audio level meter.
 * MARKER_B40: WebSocket backend as primary source, Web Audio API as fallback.
 *
 * Priority chain:
 *   1. WebSocket audio_scope_data from backend (server-side FFmpeg analysis)
 *   2. Web Audio API AnalyserNode from <video> element (client-side fallback)
 *
 * Shows VU-style vertical bars with peak hold. Monochrome FCP7 style.
 *
 * @phase B40
 * @task tb_1774241112_1
 */
import { useRef, useEffect, useCallback, useState, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import { getAudioScopeSocket } from './WaveformMinimap';
import { IconAudioBars } from './icons/CutIcons';

const METER_BG: CSSProperties = {
  display: 'flex',
  gap: 2,
  alignItems: 'flex-end',
  background: '#0a0a0a',
  border: '1px solid #222',
  borderRadius: 2,
  padding: 2,
  height: '100%',
  position: 'relative',
};

type AudioLevelMeterProps = {
  /** Video/audio element for Web Audio API fallback */
  mediaElement?: HTMLMediaElement | null;
  /** Number of VU channels (1=mono, 2=stereo) */
  channels?: number;
  /** Width of each channel bar in px */
  barWidth?: number;
  /** Orientation */
  vertical?: boolean;
  style?: CSSProperties;
};

// Color gradient: green → yellow → red
function levelColor(level: number): string {
  if (level < 0.6) return '#22c55e';
  if (level < 0.85) return '#eab308';
  return '#ef4444';
}

export default function AudioLevelMeter({
  mediaElement,
  channels = 2,
  barWidth = 6,
  vertical = true,
  style,
}: AudioLevelMeterProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef(0);
  const peakRef = useRef<number[]>([0, 0]);
  const peakDecayRef = useRef<number[]>([0, 0]);
  const mountedRef = useRef(true);

  // WebSocket state
  const wsLevelsRef = useRef<{ left: number; right: number } | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const lastEmitRef = useRef(0);

  // Web Audio API fallback state
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const [webAudioConnected, setWebAudioConnected] = useState(false);

  // Store state for WebSocket requests
  const currentTime = useCutEditorStore((s) => s.currentTime);
  const isPlaying = useCutEditorStore((s) => s.isPlaying);
  const sourceMediaPath = useCutEditorStore((s) => s.sourceMediaPath);
  const programMediaPath = useCutEditorStore((s) => s.programMediaPath);
  const mediaPath = programMediaPath || sourceMediaPath;

  // ─── WebSocket lifecycle (primary source) ───
  useEffect(() => {
    mountedRef.current = true;
    const socket = getAudioScopeSocket();

    const onConnect = () => { if (mountedRef.current) setWsConnected(true); };
    const onDisconnect = () => { if (mountedRef.current) setWsConnected(false); };
    const onData = (d: any) => {
      if (!mountedRef.current || !d.success) return;
      wsLevelsRef.current = { left: d.rms_left || 0, right: d.rms_right || 0 };
    };

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('audio_scope_data', onData);
    if (socket.connected) setWsConnected(true);

    return () => {
      mountedRef.current = false;
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('audio_scope_data', onData);
    };
  }, []);

  // Emit audio_scope_request on playhead change (throttled)
  useEffect(() => {
    if (!wsConnected || !mediaPath) return;
    const now = Date.now();
    const throttleMs = isPlaying ? 100 : 0;
    if (now - lastEmitRef.current < throttleMs) return;
    lastEmitRef.current = now;

    const socket = getAudioScopeSocket();
    socket.emit('audio_scope_request', {
      source_path: mediaPath,
      time: currentTime,
      mode: 'fast',
    });
  }, [wsConnected, mediaPath, currentTime, isPlaying]);

  // ─── Web Audio API fallback ───
  const connectWebAudio = useCallback(() => {
    if (!mediaElement || webAudioConnected) return;
    try {
      const ctx = new AudioContext();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;
      const source = ctx.createMediaElementSource(mediaElement);
      source.connect(analyser);
      analyser.connect(ctx.destination);
      contextRef.current = ctx;
      analyserRef.current = analyser;
      sourceRef.current = source;
      setWebAudioConnected(true);
    } catch {
      // Already connected or not supported
    }
  }, [mediaElement, webAudioConnected]);

  useEffect(() => {
    if (!mediaElement) return;
    const handlePlay = () => connectWebAudio();
    mediaElement.addEventListener('play', handlePlay);
    if (!mediaElement.paused) connectWebAudio();
    return () => mediaElement.removeEventListener('play', handlePlay);
  }, [mediaElement, connectWebAudio]);

  // ─── Animation loop: draw VU bars from best available source ───
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const totalWidth = channels * barWidth + (channels - 1) * 2 + 4;
    const height = canvas.clientHeight || 80;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = totalWidth * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    const analyser = analyserRef.current;
    const dataArray = analyser ? new Uint8Array(analyser.frequencyBinCount) : null;

    const draw = () => {
      const levels: number[] = [];

      // Priority 1: WebSocket backend levels
      const wsData = wsLevelsRef.current;
      if (wsData && wsConnected) {
        levels.push(Math.min(1, wsData.left * 2.5));
        levels.push(Math.min(1, wsData.right * 2.5));
      } else if (analyser && dataArray) {
        // Priority 2: Web Audio API fallback
        analyser.getByteFrequencyData(dataArray);
        const halfLen = Math.floor(dataArray.length / 2);
        for (let ch = 0; ch < channels; ch++) {
          const start = ch === 0 ? 0 : halfLen;
          const end = ch === 0 ? halfLen : dataArray.length;
          let sum = 0;
          for (let i = start; i < end; i++) {
            const v = dataArray[i] / 255;
            sum += v * v;
          }
          const rms = Math.sqrt(sum / (end - start));
          levels.push(Math.min(1, rms * 2.5));
        }
      } else {
        // No source — zero levels
        for (let ch = 0; ch < channels; ch++) levels.push(0);
      }

      // Update peak hold
      for (let ch = 0; ch < channels; ch++) {
        if (levels[ch] > peakRef.current[ch]) {
          peakRef.current[ch] = levels[ch];
          peakDecayRef.current[ch] = 0;
        } else {
          peakDecayRef.current[ch]++;
          if (peakDecayRef.current[ch] > 30) {
            peakRef.current[ch] = Math.max(0, peakRef.current[ch] - 0.02);
          }
        }
      }

      // Draw
      ctx.fillStyle = '#0a0a0a';
      ctx.fillRect(0, 0, totalWidth, height);

      for (let ch = 0; ch < channels; ch++) {
        const x = 2 + ch * (barWidth + 2);
        const level = levels[ch];
        const peak = peakRef.current[ch];
        const segmentCount = 20;
        const segHeight = (height - 4) / segmentCount;
        const activeSegments = Math.floor(level * segmentCount);
        const peakSegment = Math.floor(peak * segmentCount);

        for (let s = 0; s < segmentCount; s++) {
          const y = height - 2 - (s + 1) * segHeight;
          const segLevel = (s + 1) / segmentCount;

          if (s < activeSegments) {
            ctx.fillStyle = levelColor(segLevel);
            ctx.fillRect(x, y, barWidth, segHeight - 1);
          } else if (s === peakSegment && peak > 0.02) {
            ctx.fillStyle = levelColor(segLevel);
            ctx.globalAlpha = 0.8;
            ctx.fillRect(x, y, barWidth, 1.5);
            ctx.globalAlpha = 1;
          }
        }
      }

      animRef.current = requestAnimationFrame(draw);
    };

    animRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animRef.current);
  }, [wsConnected, webAudioConnected, channels, barWidth]);

  // Cleanup
  useEffect(() => {
    return () => { cancelAnimationFrame(animRef.current); };
  }, []);

  const totalWidth = channels * barWidth + (channels - 1) * 2 + 4;
  const hasSource = wsConnected || webAudioConnected;

  return (
    <div style={{ ...METER_BG, ...style }}>
      <canvas
        ref={canvasRef}
        style={{ width: totalWidth, height: '100%', display: 'block' }}
      />
      {!hasSource && (
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 8, color: '#333',
        }}>
          <IconAudioBars size={10} color="#333" />
        </div>
      )}
    </div>
  );
}
