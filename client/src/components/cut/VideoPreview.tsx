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

export default function VideoPreview() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const animFrameRef = useRef(0);
  const [videoEl, setVideoEl] = useState<HTMLVideoElement | null>(null);
  const prevMediaRef = useRef<string | null>(null);

  const activeMediaPath = useCutEditorStore((s) => s.activeMediaPath);
  const isPlaying = useCutEditorStore((s) => s.isPlaying);
  const currentTime = useCutEditorStore((s) => s.currentTime);
  const playbackRate = useCutEditorStore((s) => s.playbackRate);
  const thumbnails = useCutEditorStore((s) => s.thumbnails);
  const sandboxRoot = useCutEditorStore((s) => s.sandboxRoot);
  const mediaError = useCutEditorStore((s) => s.mediaError);
  const mediaLoading = useCutEditorStore((s) => s.mediaLoading);
  const seek = useCutEditorStore((s) => s.seek);
  const setDuration = useCutEditorStore((s) => s.setDuration);
  const play = useCutEditorStore((s) => s.play);
  const pause = useCutEditorStore((s) => s.pause);
  const setMediaError = useCutEditorStore((s) => s.setMediaError);
  const setMediaLoading = useCutEditorStore((s) => s.setMediaLoading);

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
          Select a clip to preview
          <br />
          <span style={{ fontSize: 11, color: '#333' }}>Program Monitor</span>
        </div>
      </div>
    );
  }

  // MARKER_170.NLE.MEDIA_PROXY: Build video URL via media-proxy endpoint
  const videoSrc = sandboxRoot
    ? `${API_BASE}/cut/media-proxy?sandbox_root=${encodeURIComponent(sandboxRoot)}&path=${encodeURIComponent(activeMediaPath)}`
    : activeThumbnail?.source_url || activeMediaPath;

  return (
    <div style={CONTAINER_STYLE}>
      <video
        ref={videoRef}
        src={videoSrc}
        poster={activeThumbnail?.poster_url || undefined}
        style={VIDEO_STYLE}
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
      <TranscriptOverlay />
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
