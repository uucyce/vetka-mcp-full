/**
 * MARKER_CUT_0.3: MonitorTransport — compact transport controls under each monitor.
 *
 * Renders UNDER video in Source Monitor and Program Monitor.
 * Contains: scrubber bar, timecode display, transport buttons, total duration.
 * Source Monitor additionally: IN / OUT buttons.
 * Max height: 60px. Style: dark #0a0a0a, white text, like Premiere.
 *
 * Props:
 *   feed: 'source' | 'program'
 *     Source → reads sourceMediaPath (future), shows IN/OUT
 *     Program → reads programMediaPath (future), shows timeline position
 */
import { useCallback, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import {
  IconSkipStart, IconPlay, IconPause, IconSkipEnd,
} from './icons/CutIcons';

// ─── Styles ───

const ROOT: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  background: '#0a0a0a',
  borderTop: '1px solid #1a1a1a',
  flexShrink: 0,
  maxHeight: 60,
  userSelect: 'none',
};

const SCRUBBER_ROW: CSSProperties = {
  width: '100%',
  height: 3,
  background: '#222',
  cursor: 'pointer',
  flexShrink: 0,
};

const SCRUBBER_FILL: CSSProperties = {
  height: '100%',
  background: '#3b82f6',
  borderRadius: 1,
  transition: 'width 0.05s linear',
};

const CONTROLS_ROW: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  padding: '2px 8px',
  height: 28,
};

const TC_STYLE: CSSProperties = {
  fontFamily: '"JetBrains Mono", "SF Mono", monospace',
  fontSize: 11,
  color: '#fff',
  letterSpacing: 0.5,
  minWidth: 80,
  textAlign: 'center',
};

const DUR_STYLE: CSSProperties = {
  ...TC_STYLE,
  color: '#666',
  fontSize: 10,
};

const TRANSPORT_BTN: CSSProperties = {
  background: 'none',
  border: 'none',
  color: '#999',
  cursor: 'pointer',
  padding: '2px 4px',
  fontSize: 14,
  lineHeight: 1,
  display: 'flex',
  alignItems: 'center',
};

const IO_BTN: CSSProperties = {
  ...TRANSPORT_BTN,
  fontSize: 9,
  fontWeight: 700,
  color: '#666',
  border: '1px solid #333',
  borderRadius: 2,
  padding: '1px 6px',
};

// ─── Helpers ───

function formatTC(seconds: number, fps = 25): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const f = Math.floor((seconds % 1) * fps);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}:${String(f).padStart(2, '0')}`;
}

// ─── Component ───

interface MonitorTransportProps {
  feed: 'source' | 'program';
}

export default function MonitorTransport({ feed }: MonitorTransportProps) {
  const currentTime = useCutEditorStore((s) => s.currentTime);
  const duration = useCutEditorStore((s) => s.duration);
  const isPlaying = useCutEditorStore((s) => s.isPlaying);
  const markIn = useCutEditorStore((s) => s.markIn);
  const markOut = useCutEditorStore((s) => s.markOut);
  const togglePlay = useCutEditorStore((s) => s.togglePlay);
  const seek = useCutEditorStore((s) => s.seek);
  const setMarkIn = useCutEditorStore((s) => s.setMarkIn);
  const setMarkOut = useCutEditorStore((s) => s.setMarkOut);

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  const handleSkipStart = useCallback(() => seek(0), [seek]);
  const handleSkipEnd = useCallback(() => seek(duration), [seek, duration]);
  const handleStepBack = useCallback(() => seek(Math.max(0, currentTime - 1 / 25)), [seek, currentTime]);
  const handleStepForward = useCallback(() => seek(Math.min(duration, currentTime + 1 / 25)), [seek, currentTime, duration]);

  const handleScrubberClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (duration <= 0) return;
      const rect = e.currentTarget.getBoundingClientRect();
      const fraction = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      seek(fraction * duration);
    },
    [seek, duration],
  );

  return (
    <div style={ROOT}>
      {/* Scrubber bar */}
      <div style={SCRUBBER_ROW} onClick={handleScrubberClick}>
        <div style={{ ...SCRUBBER_FILL, width: `${progress}%` }} />
      </div>

      {/* Controls row */}
      <div style={CONTROLS_ROW}>
        {/* Timecode */}
        <span style={TC_STYLE}>{formatTC(currentTime)}</span>

        {/* Transport buttons */}
        <button style={TRANSPORT_BTN} onClick={handleSkipStart} title="Go to start">
          <IconSkipStart size={14} />
        </button>
        <button style={{ ...TRANSPORT_BTN, fontSize: 10 }} onClick={handleStepBack} title="Step back 1 frame">
          <span style={{ fontFamily: 'monospace' }}>{'|◂'}</span>
        </button>
        <button style={{ ...TRANSPORT_BTN, color: isPlaying ? '#3b82f6' : '#ccc' }} onClick={togglePlay} title={isPlaying ? 'Pause' : 'Play'}>
          {isPlaying ? <IconPause size={16} /> : <IconPlay size={16} />}
        </button>
        <button style={{ ...TRANSPORT_BTN, fontSize: 10 }} onClick={handleStepForward} title="Step forward 1 frame">
          <span style={{ fontFamily: 'monospace' }}>{'▸|'}</span>
        </button>
        <button style={TRANSPORT_BTN} onClick={handleSkipEnd} title="Go to end">
          <IconSkipEnd size={14} />
        </button>

        {/* Total duration — Premiere style: no label, just timecode */}
        <span style={DUR_STYLE}>{formatTC(duration)}</span>

        {/* Source-only: IN / OUT buttons */}
        {feed === 'source' && (
          <>
            <div style={{ width: 1, height: 16, background: '#333', margin: '0 4px' }} />
            <button
              style={{ ...IO_BTN, color: markIn != null ? '#3b82f6' : '#666' }}
              onClick={() => setMarkIn(currentTime)}
              title="Set IN point (I)"
            >
              I
            </button>
            <button
              style={{ ...IO_BTN, color: markOut != null ? '#3b82f6' : '#666' }}
              onClick={() => setMarkOut(currentTime)}
              title="Set OUT point (O)"
            >
              O
            </button>
          </>
        )}
      </div>
    </div>
  );
}
