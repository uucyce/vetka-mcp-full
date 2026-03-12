/**
 * MARKER_170.NLE.TRANSCRIPT_OVERLAY: Subtitles/transcript overlay on video preview.
 * Reads markers from useCutEditorStore, shows current speech segment as subtitle.
 * Supports speech/comment/insight markers with different styling.
 */
import { useMemo, type CSSProperties } from 'react';
import { useCutEditorStore } from '../../store/useCutEditorStore';

const OVERLAY_STYLE: CSSProperties = {
  position: 'absolute',
  bottom: 40,
  left: '5%',
  right: '5%',
  textAlign: 'center',
  pointerEvents: 'none',
  zIndex: 10,
};

const SUBTITLE_STYLE: CSSProperties = {
  display: 'inline-block',
  background: 'rgba(0, 0, 0, 0.75)',
  color: '#fff',
  fontSize: 15,
  fontFamily: 'system-ui, -apple-system, sans-serif',
  padding: '4px 14px',
  borderRadius: 4,
  maxWidth: '90%',
  lineHeight: 1.4,
  letterSpacing: 0.3,
  textShadow: '0 1px 3px rgba(0,0,0,0.5)',
};

const KIND_COLORS: Record<string, string> = {
  favorite: '#f59e0b',
  comment: '#06b6d4',
  cam: '#a855f7',
  insight: '#22c55e',
  speech: '#ffffff',
  chat: '#64748b',
};

type TranscriptOverlayProps = {
  /** Show speaker labels when available */
  showSpeaker?: boolean;
  /** Maximum number of visible lines */
  maxLines?: number;
};

export default function TranscriptOverlay({ showSpeaker = true, maxLines = 2 }: TranscriptOverlayProps) {
  const currentTime = useCutEditorStore((s) => s.currentTime);
  const markers = useCutEditorStore((s) => s.markers);

  // Find markers active at currentTime
  const activeMarkers = useMemo(() => {
    if (!markers.length) return [];
    return markers
      .filter(
        (m) =>
          m.text &&
          m.start_sec <= currentTime &&
          currentTime < m.end_sec
      )
      .slice(0, maxLines);
  }, [markers, currentTime, maxLines]);

  if (!activeMarkers.length) return null;

  return (
    <div style={OVERLAY_STYLE}>
      {activeMarkers.map((m) => {
        const kindColor = KIND_COLORS[m.kind] || '#fff';
        const isSpeech = m.kind === 'speech' || m.kind === 'comment' || m.kind === 'chat';
        return (
          <div
            key={m.marker_id}
            style={{
              ...SUBTITLE_STYLE,
              borderLeft: isSpeech ? 'none' : `3px solid ${kindColor}`,
              marginBottom: 4,
            }}
          >
            {showSpeaker && m.kind !== 'speech' && (
              <span
                style={{
                  color: kindColor,
                  fontSize: 10,
                  textTransform: 'uppercase',
                  letterSpacing: 1,
                  marginRight: 8,
                }}
              >
                {m.kind}
              </span>
            )}
            <span>{m.text}</span>
          </div>
        );
      })}
    </div>
  );
}
