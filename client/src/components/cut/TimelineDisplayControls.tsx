/**
 * MARKER_DISPLAY-CTRL: Timeline Display Controls popup.
 * FCP7 Reference: Ch.9 "Timeline Basics" §141-148
 * Premiere Reference: Timeline Display popup (bottom-left)
 *
 * Three groups:
 * A. Clip Overlays — what is rendered on clip blocks
 * B. Track Layout — track size presets, show/hide V/A tracks
 * C. Display Mode — timecode format in ruler
 */
import { useState, useRef, useEffect, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

const POPUP_STYLE: CSSProperties = {
  position: 'absolute',
  bottom: '100%',
  left: 0,
  marginBottom: 4,
  background: '#1a1a1a',
  border: '1px solid #333',
  borderRadius: 4,
  padding: '6px 0',
  minWidth: 200,
  zIndex: 1000,
  boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
  fontSize: 11,
  color: '#ccc',
  userSelect: 'none',
};

const GROUP_LABEL: CSSProperties = {
  padding: '4px 12px 2px',
  fontSize: 9,
  fontWeight: 700,
  color: '#666',
  textTransform: 'uppercase',
  letterSpacing: 0.5,
};

const TOGGLE_ROW: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '3px 12px',
  cursor: 'pointer',
};

const SEPARATOR: CSSProperties = {
  height: 1,
  background: '#333',
  margin: '4px 0',
};

const TRACK_SIZE_ROW: CSSProperties = {
  display: 'flex',
  gap: 4,
  padding: '3px 12px',
};

const SIZE_BTN: CSSProperties = {
  padding: '2px 8px',
  borderRadius: 3,
  border: '1px solid #444',
  background: '#111',
  color: '#aaa',
  fontSize: 10,
  cursor: 'pointer',
};

function CheckMark({ checked }: { checked: boolean }) {
  return (
    <span style={{ width: 14, textAlign: 'center', color: checked ? '#999' : '#444' }}>
      {checked ? '✓' : ''}
    </span>
  );
}

export default function TimelineDisplayControls() {
  const [open, setOpen] = useState(false);
  const popupRef = useRef<HTMLDivElement>(null);

  const showClipNames = useCutEditorStore((s) => s.showClipNames);
  const showClipBorders = useCutEditorStore((s) => s.showClipBorders);
  const showWaveforms = useCutEditorStore((s) => s.showWaveforms);
  const showThroughEdits = useCutEditorStore((s) => s.showThroughEdits);
  const showClipLabels = useCutEditorStore((s) => s.showClipLabels);
  const showRubberBand = useCutEditorStore((s) => s.showRubberBand);
  const trackHeightPreset = useCutEditorStore((s) => s.trackHeightPreset);
  const cycleTrackHeights = useCutEditorStore((s) => s.cycleTrackHeights);
  const showVideoTracks = useCutEditorStore((s) => s.showVideoTracks);
  const showAudioTracks = useCutEditorStore((s) => s.showAudioTracks);
  const timecodeDisplayMode = useCutEditorStore((s) => s.timecodeDisplayMode);
  const proxyMode = useCutEditorStore((s) => s.proxyMode);
  const setProxyMode = useCutEditorStore((s) => s.setProxyMode);

  const toggleShowClipNames = useCutEditorStore((s) => s.toggleShowClipNames);
  const toggleShowClipBorders = useCutEditorStore((s) => s.toggleShowClipBorders);
  const toggleShowWaveforms = useCutEditorStore((s) => s.toggleShowWaveforms);
  const toggleShowThroughEdits = useCutEditorStore((s) => s.toggleShowThroughEdits);
  const toggleShowClipLabels = useCutEditorStore((s) => s.toggleShowClipLabels);
  const toggleShowRubberBand = useCutEditorStore((s) => s.toggleShowRubberBand);
  const toggleShowVideoTracks = useCutEditorStore((s) => s.toggleShowVideoTracks);
  const toggleShowAudioTracks = useCutEditorStore((s) => s.toggleShowAudioTracks);
  const setTimecodeDisplayMode = useCutEditorStore((s) => s.setTimecodeDisplayMode);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: globalThis.MouseEvent) => {
      if (popupRef.current && !popupRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const PRESET_LABELS: Record<number, string> = { 0: 'S', 1: 'M', 2: 'L' };

  return (
    <div ref={popupRef} style={{ position: 'relative' }}>
      <button
        data-testid="cut-display-controls-btn"
        onClick={() => setOpen((v) => !v)}
        title="Timeline Display Controls"
        style={{
          background: open ? '#1a1a1a' : 'none',
          border: 'none',
          cursor: 'pointer',
          padding: '2px 4px',
          display: 'flex',
          alignItems: 'center',
          borderRadius: 3,
        }}
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M2 4h12M2 8h12M2 12h12" stroke={open ? '#ccc' : '#666'} strokeWidth="1.5" strokeLinecap="round" />
          <circle cx="5" cy="4" r="1.5" fill={open ? '#ccc' : '#666'} />
          <circle cx="10" cy="8" r="1.5" fill={open ? '#ccc' : '#666'} />
          <circle cx="7" cy="12" r="1.5" fill={open ? '#ccc' : '#666'} />
        </svg>
      </button>

      {open && (
        <div style={POPUP_STYLE} data-testid="cut-display-controls-popup">
          {/* Group A: Clip Overlays */}
          <div style={GROUP_LABEL}>Clip Overlays</div>
          <div style={TOGGLE_ROW} onClick={toggleShowClipNames} data-testid="toggle-clip-names">
            <CheckMark checked={showClipNames} />
            <span>Show Clip Names</span>
          </div>
          <div style={TOGGLE_ROW} onClick={toggleShowClipBorders} data-testid="toggle-clip-borders">
            <CheckMark checked={showClipBorders} />
            <span>Show Clip Borders</span>
          </div>
          <div style={TOGGLE_ROW} onClick={toggleShowWaveforms} data-testid="toggle-waveforms">
            <CheckMark checked={showWaveforms} />
            <span>Show Audio Waveforms</span>
          </div>
          <div style={TOGGLE_ROW} onClick={toggleShowThroughEdits} data-testid="toggle-through-edits">
            <CheckMark checked={showThroughEdits} />
            <span>Show Through Edits</span>
          </div>
          <div style={TOGGLE_ROW} onClick={toggleShowClipLabels} data-testid="toggle-clip-labels">
            <CheckMark checked={showClipLabels} />
            <span>Show Clip Labels/Colors</span>
          </div>
          <div style={TOGGLE_ROW} onClick={toggleShowRubberBand} data-testid="toggle-rubber-band">
            <CheckMark checked={showRubberBand} />
            <span>Show Opacity/Volume Band</span>
          </div>

          <div style={SEPARATOR} />

          {/* Group B: Track Layout */}
          <div style={GROUP_LABEL}>Track Layout</div>
          <div style={{ padding: '3px 12px', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: '#888', fontSize: 10 }}>Track Size:</span>
            <div style={TRACK_SIZE_ROW}>
              {([0, 1, 2] as const).map((preset) => (
                <button
                  key={preset}
                  style={{
                    ...SIZE_BTN,
                    background: trackHeightPreset === preset ? '#222' : '#111',
                    borderColor: trackHeightPreset === preset ? '#999' : '#444',
                    color: trackHeightPreset === preset ? '#999' : '#aaa',
                  }}
                  onClick={() => {
                    // Cycle until we reach the target preset
                    const current = useCutEditorStore.getState().trackHeightPreset;
                    if (current !== preset) {
                      const steps = (preset - current + 3) % 3;
                      for (let i = 0; i < steps; i++) cycleTrackHeights();
                    }
                  }}
                >
                  {PRESET_LABELS[preset]}
                </button>
              ))}
            </div>
          </div>
          <div style={TOGGLE_ROW} onClick={toggleShowVideoTracks} data-testid="toggle-video-tracks">
            <CheckMark checked={showVideoTracks} />
            <span>Show Video Tracks</span>
          </div>
          <div style={TOGGLE_ROW} onClick={toggleShowAudioTracks} data-testid="toggle-audio-tracks">
            <CheckMark checked={showAudioTracks} />
            <span>Show Audio Tracks</span>
          </div>

          <div style={SEPARATOR} />

          {/* Group C: Display Mode */}
          <div style={GROUP_LABEL}>Display Mode</div>
          {(['timecode', 'frames', 'seconds'] as const).map((mode) => (
            <div
              key={mode}
              style={TOGGLE_ROW}
              onClick={() => setTimecodeDisplayMode(mode)}
              data-testid={`timecode-mode-${mode}`}
            >
              <CheckMark checked={timecodeDisplayMode === mode} />
              <span>
                {mode === 'timecode' ? 'Timecode (HH:MM:SS:FF)' : mode === 'frames' ? 'Frames' : 'Seconds'}
              </span>
            </div>
          ))}

          <div style={SEPARATOR} />

          {/* MARKER_B72: Group D: Playback Quality / Proxy toggle */}
          <div style={GROUP_LABEL}>Playback Quality</div>
          {(['full', 'proxy', 'auto'] as const).map((mode) => (
            <div
              key={mode}
              style={TOGGLE_ROW}
              onClick={() => setProxyMode(mode)}
              data-testid={`proxy-mode-${mode}`}
            >
              <CheckMark checked={proxyMode === mode} />
              <span>
                {mode === 'full' ? 'Full Resolution' : mode === 'proxy' ? 'Proxy (Performance)' : 'Auto (Proxy if needed)'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
