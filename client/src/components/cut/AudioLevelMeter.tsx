/**
 * MARKER_170.NLE.AUDIO_METER: Real-time audio level meter using Web Audio API.
 * Analyzes the audio from the <video> element via AnalyserNode.
 * Shows VU-style vertical bars with peak hold.
 */
import { useRef, useEffect, useCallback, useState, type CSSProperties } from 'react';
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
};

type AudioLevelMeterProps = {
  /** CSS selector or ref for the video/audio element to analyze */
  mediaElement?: HTMLMediaElement | null;
  /** Number of VU channels to display (1=mono, 2=stereo) */
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
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const animRef = useRef(0);
  const peakRef = useRef<number[]>([0, 0]);
  const peakDecayRef = useRef<number[]>([0, 0]);
  const [connected, setConnected] = useState(false);

  // Connect Web Audio analyser to media element
  const connect = useCallback(() => {
    if (!mediaElement || connected) return;
    try {
      const ctx = new AudioContext();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;

      const source = ctx.createMediaElementSource(mediaElement);
      source.connect(analyser);
      analyser.connect(ctx.destination); // pass-through to speakers

      contextRef.current = ctx;
      analyserRef.current = analyser;
      sourceRef.current = source;
      setConnected(true);
    } catch {
      // Already connected or not supported
    }
  }, [mediaElement, connected]);

  // Auto-connect when media starts playing
  useEffect(() => {
    if (!mediaElement) return;
    const handlePlay = () => connect();
    mediaElement.addEventListener('play', handlePlay);
    // If already playing
    if (!mediaElement.paused) connect();
    return () => mediaElement.removeEventListener('play', handlePlay);
  }, [mediaElement, connect]);

  // Animation loop: read levels and draw
  useEffect(() => {
    const canvas = canvasRef.current;
    const analyser = analyserRef.current;
    if (!canvas || !analyser) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const totalWidth = channels * barWidth + (channels - 1) * 2 + 4;
    const height = canvas.clientHeight || 80;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = totalWidth * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    const draw = () => {
      analyser.getByteFrequencyData(dataArray);

      // Calculate RMS level per channel (approximate stereo split)
      const halfLen = Math.floor(dataArray.length / 2);
      const levels: number[] = [];
      for (let ch = 0; ch < channels; ch++) {
        const start = ch === 0 ? 0 : halfLen;
        const end = ch === 0 ? halfLen : dataArray.length;
        let sum = 0;
        for (let i = start; i < end; i++) {
          const v = dataArray[i] / 255;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / (end - start));
        levels.push(Math.min(1, rms * 2.5)); // boost for visibility
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
            // Peak hold indicator
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
  }, [connected, channels, barWidth]);

  // Cleanup
  useEffect(() => {
    return () => {
      cancelAnimationFrame(animRef.current);
    };
  }, []);

  const totalWidth = channels * barWidth + (channels - 1) * 2 + 4;

  return (
    <div style={{ ...METER_BG, ...style }}>
      <canvas
        ref={canvasRef}
        style={{
          width: totalWidth,
          height: '100%',
          display: 'block',
        }}
      />
      {!connected && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 8,
            color: '#333',
          }}
        >
          <IconAudioBars size={10} color="#333" />
        </div>
      )}
    </div>
  );
}
