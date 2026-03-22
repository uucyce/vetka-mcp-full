/**
 * MARKER_170.NLE.PLAYER: HTML5 video preview (program monitor).
 * Reads activeMediaPath from useCutEditorStore, syncs currentTime.
 * Displays poster from thumbnail_bundle when paused.
 * MARKER_170.PLAYBACK.A2: Error overlay + loading indicator (Opus Sprint).
 */
import { useRef, useEffect, useCallback, useState, type CSSProperties } from 'react';
import { API_BASE } from '../../config/api.config';
import { useCutEditorStore } from '../../store/useCutEditorStore';
import AudioLevelMeter from './AudioLevelMeter';
import TranscriptOverlay from './TranscriptOverlay';

const CONTAINER_STYLE: CSSProperties = {
  position: 'relative',
  width: '100%',
  height: '100%',
  background: '#000',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  overflow: 'hidden',
  borderRadius: 4,
};

const VIDEO_STYLE: CSSProperties = {
  maxWidth: '100%',
  maxHeight: '100%',
  objectFit: 'contain',
};

const TIMECODE_STYLE: CSSProperties = {
  position: 'absolute',
  bottom: 8,
  right: 12,
  fontFamily: '"JetBrains Mono", "SF Mono", monospace',
  fontSize: 13,
  color: '#fff',
  background: 'rgba(0,0,0,0.7)',
  padding: '2px 8px',
  borderRadius: 3,
  letterSpacing: 1,
  userSelect: 'none',
};

const EMPTY_STYLE: CSSProperties = {
  color: '#555',
  fontSize: 14,
  fontFamily: 'system-ui',
  textAlign: 'center',
  userSelect: 'none',
};

// MARKER_170.PLAYBACK.A2: Error overlay style (matches VideoArtifactPlayer pattern)
const ERROR_OVERLAY_STYLE: CSSProperties = {
  position: 'absolute',
  left: 12,
  top: 12,
  background: 'rgba(180,40,40,0.85)',
  border: '1px solid #c44',
  color: '#fff',
  fontSize: 11,
  fontFamily: 'system-ui',
  borderRadius: 4,
  padding: '6px 10px',
  maxWidth: '80%',
  zIndex: 5,
  userSelect: 'none',
};

const LOADING_STYLE: CSSProperties = {
  position: 'absolute',
  left: '50%',
  top: '50%',
  transform: 'translate(-50%, -50%)',
  color: '#888',
  fontSize: 12,
  fontFamily: 'system-ui',
  userSelect: 'none',
  zIndex: 3,
};

const NATIVE_PLAYABLE_VIDEO_EXT = new Set(['mp4', 'm4v', 'webm', 'ogg', 'mov']);
const HEAVY_CODEC_EXT = new Set(['mxf', 'r3d', 'braw', 'mkv', 'avi', 'mts', 'm2ts', 'dpx', 'exr']);

function formatTimecode(seconds: number, fps = 25): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const f = Math.floor((seconds % 1) * fps);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}:${String(f).padStart(2, '0')}`;
}

// MARKER_170.PLAYBACK.A2: Classify HTML5 MediaError codes
function classifyVideoError(video: HTMLVideoElement): string {
  const error = video.error;
  if (!error) return 'Unknown playback error';
  switch (error.code) {
    case MediaError.MEDIA_ERR_ABORTED: return 'Playback aborted';
    case MediaError.MEDIA_ERR_NETWORK: return 'Network error — check media path';
    case MediaError.MEDIA_ERR_DECODE: return 'Cannot decode — unsupported format';
    case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED: return 'Format not supported by browser';
    default: return 'Unknown playback error';
  }
}

// MARKER_170.NLE.AUDIO_VU: Style for the audio meter strip beside the video
const METER_STRIP_STYLE: CSSProperties = {
  position: 'absolute',
  right: 4,
  top: 8,
  bottom: 32,
  width: 22,
  zIndex: 2,
};

/**
 * MARKER_W1.3: feed prop controls which media path this monitor reads.
 * feed='source' → sourceMediaPath (raw clip from DAG/Project click)
 * feed='program' → programMediaPath (timeline playback)
 * Default (no prop) → activeMediaPath (legacy behavior)
 */
type VideoPreviewProps = {
  feed?: 'source' | 'program';
};

export default function VideoPreview({ feed }: VideoPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const animFrameRef = useRef(0);
  const [videoEl, setVideoEl] = useState<HTMLVideoElement | null>(null);
  const prevMediaRef = useRef<string | null>(null);
  const [resolvedSrc, setResolvedSrc] = useState<string>('');
  const [sourceHint, setSourceHint] = useState<string>('');

  // MARKER_W1.3: Select media path based on feed prop
  const sourceMediaPath = useCutEditorStore((s) => s.sourceMediaPath);
  const programMediaPath = useCutEditorStore((s) => s.programMediaPath);
  const legacyMediaPath = useCutEditorStore((s) => s.activeMediaPath);
  const activeMediaPath = feed === 'source' ? sourceMediaPath
    : feed === 'program' ? programMediaPath
    : legacyMediaPath;
  // MARKER_DUAL-VIDEO: Source monitor uses its own playback state, program uses timeline's
  const isSource = feed === 'source';
  const isPlaying = useCutEditorStore((s) => isSource ? s.sourceIsPlaying : s.isPlaying);
  const currentTime = useCutEditorStore((s) => isSource ? s.sourceCurrentTime : s.currentTime);
  const playbackRate = useCutEditorStore((s) => s.playbackRate);
  const thumbnails = useCutEditorStore((s) => s.thumbnails);
  const sandboxRoot = useCutEditorStore((s) => s.sandboxRoot);
  const mediaError = useCutEditorStore((s) => s.mediaError);
  const mediaLoading = useCutEditorStore((s) => s.mediaLoading);
  const seek = useCutEditorStore((s) => isSource ? s.seekSource : s.seek);
  const setDuration = useCutEditorStore((s) => isSource ? s.setSourceDuration : s.setDuration);
  const play = useCutEditorStore((s) => isSource ? s.playSource : s.play);
  const pause = useCutEditorStore((s) => isSource ? s.pauseSource : s.pause);
  const setMediaError = useCutEditorStore((s) => s.setMediaError);
  const setMediaLoading = useCutEditorStore((s) => s.setMediaLoading);

  // MARKER_W5.2: Monitor overlay state
  const showTitleSafe = useCutEditorStore((s) => s.showTitleSafe);
  const showActionSafe = useCutEditorStore((s) => s.showActionSafe);
  const showMonitorOverlays = useCutEditorStore((s) => s.showMonitorOverlays);

  // MARKER_B22: Live grading — read color_correction from selected clip for CSS filter preview
  const ccForCssFilter = useCutEditorStore((s) => {
    if (!s.selectedClipId) return null;
    for (const lane of s.lanes) {
      for (const clip of lane.clips || []) {
        if (clip.clip_id === s.selectedClipId) {
          return (clip as any).color_correction as { exposure?: number; contrast?: number; saturation?: number; hue?: number } | null;
        }
      }
    }
    return null;
  });

  const videoCssFilter = (() => {
    if (!ccForCssFilter) return undefined;
    const parts: string[] = [];
    if (ccForCssFilter.exposure && ccForCssFilter.exposure !== 0) {
      parts.push(`brightness(${Math.pow(2, ccForCssFilter.exposure).toFixed(3)})`);
    }
    if (ccForCssFilter.contrast !== undefined && ccForCssFilter.contrast !== 1) {
      parts.push(`contrast(${ccForCssFilter.contrast.toFixed(3)})`);
    }
    if (ccForCssFilter.saturation !== undefined && ccForCssFilter.saturation !== 1) {
      parts.push(`saturate(${ccForCssFilter.saturation.toFixed(3)})`);
    }
    if (ccForCssFilter.hue && ccForCssFilter.hue !== 0) {
      parts.push(`hue-rotate(${ccForCssFilter.hue}deg)`);
    }
    return parts.length > 0 ? parts.join(' ') : undefined;
  })();

  const extension = (activeMediaPath?.split('.').pop() || '').toLowerCase();

  // Find poster for current media
  const activeThumbnail = activeMediaPath
    ? thumbnails.find((t) => t.source_path === activeMediaPath)
    : null;

  // Sync video → store (requestAnimationFrame loop)
  const syncVideoToStore = useCallback(() => {
    const video = videoRef.current;
    if (video && !video.paused) {
      seek(video.currentTime);
      animFrameRef.current = requestAnimationFrame(syncVideoToStore);
    }
  }, [seek]);

  // MARKER_170.PLAYBACK.A3: Reset state on media switch (debounce race conditions)
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    if (activeMediaPath === prevMediaRef.current) return;
    prevMediaRef.current = activeMediaPath;

    // Cancel any ongoing playback
    video.pause();
    cancelAnimationFrame(animFrameRef.current);

    if (!activeMediaPath) return;

    // Reset video element for clean load
    video.currentTime = 0;
    video.load();
    // Store loading flag is already set by setActiveMedia()
  }, [activeMediaPath]);

  useEffect(() => {
    let cancelled = false;
    const resolvePlayableSource = async () => {
      if (!activeMediaPath) {
        setResolvedSrc('');
        setSourceHint('');
        return;
      }
      const sourceUrl = `${API_BASE}/files/raw?path=${encodeURIComponent(activeMediaPath)}`;
      const wantsProxy = HEAVY_CODEC_EXT.has(extension) || !NATIVE_PLAYABLE_VIDEO_EXT.has(extension);
      if (!sandboxRoot || !wantsProxy) {
        setResolvedSrc(activeThumbnail?.source_url || sourceUrl);
        setSourceHint(wantsProxy ? 'proxy unavailable, trying source' : '');
        return;
      }
      try {
        const resp = await fetch(
          `${API_BASE}/cut/proxy/path?sandbox_root=${encodeURIComponent(sandboxRoot)}&source_path=${encodeURIComponent(activeMediaPath)}`
        );
        const payload = (await resp.json()) as { success?: boolean; exists?: boolean; proxy_path?: string | null };
        if (cancelled) return;
        if (payload.success && payload.exists && payload.proxy_path) {
          setResolvedSrc(`${API_BASE}/files/raw?path=${encodeURIComponent(payload.proxy_path)}`);
          setSourceHint('proxy playback');
          return;
        }
      } catch {
        // fallback to raw source
      }
      if (cancelled) return;
      setResolvedSrc(activeThumbnail?.source_url || sourceUrl);
      setSourceHint(wantsProxy ? 'proxy recommended' : '');
    };
    void resolvePlayableSource();
    return () => {
      cancelled = true;
    };
  }, [activeMediaPath, activeThumbnail?.source_url, extension, sandboxRoot]);

  // Play/pause control
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !video.src) return;
    if (isPlaying) {
      video.play()
        .then(() => {
          setMediaError(null);
        })
        .catch(() => {/* user gesture required */});
      animFrameRef.current = requestAnimationFrame(syncVideoToStore);
    } else {
      video.pause();
      cancelAnimationFrame(animFrameRef.current);
    }
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [isPlaying, syncVideoToStore, setMediaError]);

  // Seek from store → video
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !video.src) return;
    if (Math.abs(video.currentTime - currentTime) > 0.15) {
      video.currentTime = currentTime;
    }
  }, [currentTime]);

  // Playback rate
  useEffect(() => {
    const video = videoRef.current;
    if (video) video.playbackRate = playbackRate;
  }, [playbackRate]);

  // Handle video metadata loaded — clears error + loading
  const handleLoadedMetadata = useCallback(() => {
    const video = videoRef.current;
    if (video && video.duration && Number.isFinite(video.duration)) {
      setDuration(video.duration);
      setMediaError(null);
      setMediaLoading(false);
    }
  }, [setDuration, setMediaError, setMediaLoading]);

  // MARKER_170.PLAYBACK.A2: Error handler for <video> element
  const handleError = useCallback(() => {
    const video = videoRef.current;
    if (video) {
      const msg = classifyVideoError(video);
      setMediaError(msg);
      pause();
    }
  }, [setMediaError, pause]);

  const handleEnded = useCallback(() => {
    pause();
    seek(0);
  }, [pause, seek]);

  const handleClick = useCallback(() => {
    if (mediaError) {
      // Click on error state → clear and retry
      setMediaError(null);
      setMediaLoading(true);
      const video = videoRef.current;
      if (video) video.load();
      return;
    }
    if (isPlaying) pause();
    else play();
  }, [isPlaying, play, pause, mediaError, setMediaError, setMediaLoading]);

  // MARKER_170.NLE.AUDIO_VU: Capture video element for AudioLevelMeter
  useEffect(() => {
    setVideoEl(videoRef.current);
  }, [activeMediaPath]);

  // No active media — show empty state
  if (!activeMediaPath) {
    return (
      <div style={CONTAINER_STYLE}>
        <div style={EMPTY_STYLE}>
          {feed === 'source' ? 'Select a clip to preview' : feed === 'program' ? 'No timeline playback' : 'Select a clip to preview'}
          <br />
          <span style={{ fontSize: 11, color: '#333' }}>{feed === 'source' ? 'SOURCE' : feed === 'program' ? 'PROGRAM' : 'Monitor'}</span>
        </div>
      </div>
    );
  }

  return (
    <div style={CONTAINER_STYLE}>
      <video
        ref={videoRef}
        src={resolvedSrc}
        poster={activeThumbnail?.poster_url || undefined}
        style={{ ...VIDEO_STYLE, filter: videoCssFilter }}
        onLoadedMetadata={handleLoadedMetadata}
        onError={handleError}
        onEnded={handleEnded}
        onClick={handleClick}
        preload="metadata"
        playsInline
      />
      {/* MARKER_170.PLAYBACK.A2: Error overlay */}
      {mediaError && (
        <div style={ERROR_OVERLAY_STYLE}>
          {mediaError}
          <div style={{ fontSize: 10, opacity: 0.7, marginTop: 2 }}>click to retry</div>
        </div>
      )}
      {/* MARKER_170.PLAYBACK.A3: Loading indicator */}
      {mediaLoading && !mediaError && (
        <div style={LOADING_STYLE}>loading…</div>
      )}
      {sourceHint ? (
        <div style={{ position: 'absolute', top: 12, right: 12, fontSize: 10, color: '#bbb', background: 'rgba(0,0,0,0.6)', padding: '2px 6px', borderRadius: 3 }}>
          {sourceHint}
        </div>
      ) : null}
      {/* MARKER_W2.3: Monitor label overlay — top-left corner */}
      {feed && (
        <div style={{
          position: 'absolute',
          top: 6,
          left: 8,
          fontSize: 10,
          fontFamily: 'system-ui',
          color: '#888',
          letterSpacing: 1,
          textTransform: 'uppercase',
          userSelect: 'none',
          zIndex: 3,
        }}>
          {feed === 'source' ? 'SOURCE' : 'PROGRAM'}
        </div>
      )}
      <TranscriptOverlay />
      {/* MARKER_W5.2: Safe margins overlay */}
      {(showTitleSafe || showActionSafe) && (
        <svg
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 4 }}
          viewBox="0 0 1000 1000"
          preserveAspectRatio="xMidYMid meet"
        >
          {showActionSafe && (
            <rect x="50" y="50" width="900" height="900" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="1" strokeDasharray="6 4" />
          )}
          {showTitleSafe && (
            <rect x="100" y="100" width="800" height="800" fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="1" strokeDasharray="3 3" />
          )}
          {showActionSafe && (
            <text x="55" y="45" fill="rgba(255,255,255,0.3)" fontSize="14" fontFamily="system-ui">ACTION SAFE</text>
          )}
          {showTitleSafe && (
            <text x="105" y="95" fill="rgba(255,255,255,0.25)" fontSize="14" fontFamily="system-ui">TITLE SAFE</text>
          )}
        </svg>
      )}
      {/* MARKER_W5.2: Monitor overlay (clip name) */}
      {showMonitorOverlays && activeMediaPath && (
        <div style={{
          position: 'absolute', top: 6, left: '50%', transform: 'translateX(-50%)',
          fontSize: 10, fontFamily: 'system-ui', color: '#aaa',
          background: 'rgba(0,0,0,0.6)', padding: '1px 8px', borderRadius: 3,
          userSelect: 'none', zIndex: 3, maxWidth: '60%', overflow: 'hidden',
          textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {activeMediaPath.split('/').pop()}
        </div>
      )}
      {/* MARKER_170.NLE.AUDIO_VU: VU meter strip on right edge */}
      <AudioLevelMeter
        mediaElement={videoEl}
        channels={2}
        barWidth={6}
        style={METER_STRIP_STYLE}
      />
      <div style={TIMECODE_STYLE}>{formatTimecode(currentTime)}</div>
    </div>
  );
}
