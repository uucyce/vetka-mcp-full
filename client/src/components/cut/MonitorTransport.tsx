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
import TimecodeField, { formatTimecode as formatTimecodeDisplay } from './TimecodeField';

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
  justifyContent: 'center',
  gap: 2,
  padding: '2px 8px',
  height: 28,
  position: 'relative',
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

// MARKER_W5.TC: formatTC replaced by TimecodeField component and formatTimecodeDisplay import

// ─── Component ───

interface MonitorTransportProps {
  feed: 'source' | 'program';
}

export default function MonitorTransport({ feed }: MonitorTransportProps) {
  const currentTime = useCutEditorStore((s) => s.currentTime);
  const duration = useCutEditorStore((s) => s.duration);
  const isPlaying = useCutEditorStore((s) => s.isPlaying);
  // MARKER_W1.4: Read correct marks based on feed
  const sourceMarkIn = useCutEditorStore((s) => s.sourceMarkIn);
  const sourceMarkOut = useCutEditorStore((s) => s.sourceMarkOut);
  const sequenceMarkIn = useCutEditorStore((s) => s.sequenceMarkIn);
  const sequenceMarkOut = useCutEditorStore((s) => s.sequenceMarkOut);
  const setSourceMarkIn = useCutEditorStore((s) => s.setSourceMarkIn);
  const setSourceMarkOut = useCutEditorStore((s) => s.setSourceMarkOut);
  const setSequenceMarkIn = useCutEditorStore((s) => s.setSequenceMarkIn);
  const setSequenceMarkOut = useCutEditorStore((s) => s.setSequenceMarkOut);

  const markIn = feed === 'source' ? sourceMarkIn : sequenceMarkIn;
  const markOut = feed === 'source' ? sourceMarkOut : sequenceMarkOut;
  const setMarkIn = feed === 'source' ? setSourceMarkIn : setSequenceMarkIn;
  const setMarkOut = feed === 'source' ? setSourceMarkOut : setSequenceMarkOut;

  const projectFramerate = useCutEditorStore((s) => s.projectFramerate);
  const dropFrame = useCutEditorStore((s) => s.dropFrame);

  const togglePlay = useCutEditorStore((s) => s.togglePlay);
  const seek = useCutEditorStore((s) => s.seek);

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  const handleSkipStart = useCallback(() => seek(0), [seek]);
  const handleSkipEnd = useCallback(() => seek(duration), [seek, duration]);
  const handleStepBack = useCallback(() => seek(Math.max(0, currentTime - 1 / projectFramerate)), [seek, currentTime, projectFramerate]);
  const handleStepForward = useCallback(() => seek(Math.min(duration, currentTime + 1 / projectFramerate)), [seek, currentTime, duration, projectFramerate]);

  // MARKER_FIX-MONITOR-1: Navigate edit points (clip boundaries)
  const lanes = useCutEditorStore((s) => s.lanes);
  const lockedLanes = useCutEditorStore((s) => s.lockedLanes);

  const handlePrevEdit = useCallback(() => {
    const pts = new Set<number>();
    for (const lane of lanes) {
      if (lockedLanes.has(lane.lane_id)) continue;
      for (const clip of lane.clips) {
        pts.add(clip.start_sec);
        pts.add(clip.start_sec + clip.duration_sec);
      }
    }
    const sorted = [...pts].sort((a, b) => a - b);
    for (let i = sorted.length - 1; i >= 0; i--) {
      if (sorted[i] < currentTime - 0.02) { seek(sorted[i]); return; }
    }
    seek(0);
  }, [lanes, lockedLanes, currentTime, seek]);

  const handleNextEdit = useCallback(() => {
    const pts = new Set<number>();
    for (const lane of lanes) {
      if (lockedLanes.has(lane.lane_id)) continue;
      for (const clip of lane.clips) {
        pts.add(clip.start_sec);
        pts.add(clip.start_sec + clip.duration_sec);
      }
    }
    const sorted = [...pts].sort((a, b) => a - b);
    for (const pt of sorted) {
      if (pt > currentTime + 0.02) { seek(pt); return; }
    }
  }, [lanes, lockedLanes, currentTime, seek]);

  // MARKER_FCP7.MON2: Mark Clip (X) — set IN/OUT to boundaries of clip under playhead
  const handleMarkClip = useCallback(() => {
    for (const lane of lanes) {
      for (const clip of lane.clips) {
        if (currentTime >= clip.start_sec && currentTime < clip.start_sec + clip.duration_sec) {
          setMarkIn(clip.start_sec);
          setMarkOut(clip.start_sec + clip.duration_sec);
          return;
        }
      }
    }
  }, [lanes, currentTime, setMarkIn, setMarkOut]);

  // MARKER_W5.MF: Match Frame (FCP7 Ch.50)
  // Find clip at playhead → load source in Source Monitor → seek to matching frame
  const handleMatchFrame = useCallback(() => {
    const state = useCutEditorStore.getState();
    for (const lane of lanes) {
      for (const clip of lane.clips) {
        if (currentTime >= clip.start_sec && currentTime < clip.start_sec + clip.duration_sec) {
          // Calculate source-relative time
          const sourceOffset = clip.source_in ?? 0;
          const sourceTime = (currentTime - clip.start_sec) + sourceOffset;
          // Load source into Source Monitor
          state.setSourceMedia(clip.source_path);
          // Set source mark IN to the matched frame so editor can see it
          state.setSourceMarkIn(sourceTime);
          // Focus Source Monitor
          state.setFocusedPanel('source');
          return;
        }
      }
    }
  }, [lanes, currentTime]);

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

      {/* MARKER_FIX-MONITOR-1: Controls row — FCP7/Premiere centered layout */}
      <div style={CONTROLS_ROW}>
        {/* Left: Editable Timecode (MARKER_W5.TC) */}
        <TimecodeField
          seconds={currentTime}
          fps={projectFramerate}
          dropFrame={dropFrame}
          onSeek={seek}
          style={{ position: 'absolute', left: 8 }}
          testId={`monitor-tc-${feed}`}
        />

        {/* Center: Transport [PrevEdit] [|◂] [◂] [Play] [▸] [▸|] [NextEdit] */}
        <button style={TRANSPORT_BTN} onClick={handlePrevEdit} title="Go to Previous Edit (Up)" aria-label="Previous Edit" data-testid="prev-edit">
          <span style={{ fontFamily: 'monospace', fontSize: 9 }}>{'|◂◂'}</span>
        </button>
        <button style={TRANSPORT_BTN} onClick={handleSkipStart} title="Go to start">
          <IconSkipStart size={14} />
        </button>
        <button style={{ ...TRANSPORT_BTN, fontSize: 10 }} onClick={handleStepBack} title="Step back 1 frame (Left)">
          <span style={{ fontFamily: 'monospace' }}>{'|◂'}</span>
        </button>
        <button style={{ ...TRANSPORT_BTN, color: isPlaying ? '#3b82f6' : '#ccc' }} onClick={togglePlay} title={isPlaying ? 'Pause (K)' : 'Play (Space)'}>
          {isPlaying ? <IconPause size={16} /> : <IconPlay size={16} />}
        </button>
        <button style={{ ...TRANSPORT_BTN, fontSize: 10 }} onClick={handleStepForward} title="Step forward 1 frame (Right)">
          <span style={{ fontFamily: 'monospace' }}>{'▸|'}</span>
        </button>
        <button style={TRANSPORT_BTN} onClick={handleSkipEnd} title="Go to end">
          <IconSkipEnd size={14} />
        </button>
        <button style={TRANSPORT_BTN} onClick={handleNextEdit} title="Go to Next Edit (Down)" aria-label="Next Edit" data-testid="next-edit">
          <span style={{ fontFamily: 'monospace', fontSize: 9 }}>{'▸▸|'}</span>
        </button>

        {/* Right: Duration + Marking (absolute positioned) */}
        <div style={{ position: 'absolute', right: 8, display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={DUR_STYLE}>{formatTimecodeDisplay(duration, projectFramerate, dropFrame)}</span>
          {/* IN / OUT + Match Frame — Source and Program both get marks */}
          <div style={{ width: 1, height: 14, background: '#333' }} />
          <button
            style={{ ...IO_BTN, color: markIn != null ? '#3b82f6' : '#666' }}
            onClick={() => setMarkIn(currentTime)}
            title={`Set ${feed === 'source' ? 'Source' : 'Sequence'} IN (I)`}
          >
            I
          </button>
          <button
            style={{ ...IO_BTN, color: markOut != null ? '#3b82f6' : '#666' }}
            onClick={() => setMarkOut(currentTime)}
            title={`Set ${feed === 'source' ? 'Source' : 'Sequence'} OUT (O)`}
          >
            O
          </button>
          <button
            style={IO_BTN}
            onClick={handleMarkClip}
            title="Mark Clip (X)"
            data-testid="mark-clip"
            aria-label="mark clip"
          >
            X
          </button>
          <button style={IO_BTN} onClick={handleMatchFrame} title="Match Frame (F)" data-testid="match-frame" aria-label="match frame">F</button>
        </div>
      </div>
    </div>
  );
}
