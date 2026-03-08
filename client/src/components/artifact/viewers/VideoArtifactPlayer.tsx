import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getCurrentWindowFullscreen,
  isTauri,
  setCurrentWindowFullscreen,
  setWindowFullscreen,
} from "../../../config/tauri";

interface Props {
  src: string;
  mediaPath?: string;
  poster?: string;
  mimeType?: string;
  qualitySources?: Partial<Record<"Auto" | "Original" | "Preview", string>>;
  qualityScaleSources?: Partial<Record<"full" | "half" | "quarter" | "eighth" | "sixteenth", string>>;
  controlsOffsetBottom?: number;
  initialSpeed?: number;
  initialQuality?: "Auto" | "Original" | "Preview";
  windowMode?: "embedded" | "detached";
  windowLabel?: string;
  onFullscreenChange?: (active: boolean) => void;
}

const CONTROL_HIDE_MS = 1500;
const MEDIA_SESSION_CHANNEL = "vetka-media-session-v1";

type SessionQualityScale = "full" | "half" | "quarter" | "eighth" | "sixteenth";

interface ArtifactMediaSessionStateV1 {
  schema_version: "artifact_media_session_state_v1";
  path: string;
  window_mode: "embedded" | "detached";
  fullscreen_mode: "off" | "native_window" | "dom_fallback";
  current_time: number;
  is_playing: boolean;
  volume: number;
  is_muted: boolean;
  quality_scale: SessionQualityScale;
  playback_rate: number;
  duration_sec: number;
  updated_at_ms: number;
}

interface ArtifactMediaSyncEnvelopeV1 {
  schema_version: "artifact_media_window_contract_v1";
  action: "sync_playback_state";
  target_window: "main" | "detached";
  payload: {
    session_state: ArtifactMediaSessionStateV1;
  };
  trace: {
    source: string;
    has_focus: boolean;
    reason: string;
  };
}

export function VideoArtifactPlayer({
  src,
  mediaPath,
  poster,
  mimeType = "video/mp4",
  qualitySources,
  qualityScaleSources,
  controlsOffsetBottom = 0,
  initialSpeed = 1,
  initialQuality = "Auto",
  windowMode,
  windowLabel = "main",
  onFullscreenChange,
}: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const hideTimerRef = useRef<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(initialSpeed);
  const [selectedQualityScale, setSelectedQualityScale] = useState<"full" | "half" | "quarter" | "eighth" | "sixteenth">("full");
  const [playbackFailed, setPlaybackFailed] = useState(false);
  const [wrapperHeight, setWrapperHeight] = useState(0);
  const [naturalVideoSize, setNaturalVideoSize] = useState<{ width: number; height: number } | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isFallbackFullscreen, setIsFallbackFullscreen] = useState(false);
  const [isNativeWindowFullscreen, setIsNativeWindowFullscreen] = useState(false);
  const sessionIdRef = useRef(`media-${Math.random().toString(36).slice(2, 10)}`);
  const channelRef = useRef<BroadcastChannel | null>(null);
  const applyingRemoteRef = useRef(false);
  const fullscreenToggleLockRef = useRef(false);
  const lastAppliedRemoteTsRef = useRef(0);
  const mediaIdentity = useMemo(() => String(mediaPath || src || ""), [mediaPath, src]);
  const speedOptions = [0.5, 1, 1.25, 1.5, 2, 4];
  const resolvedQualitySources = useMemo(() => {
    const auto = qualitySources?.Auto || src;
    const original = qualitySources?.Original || src;
    const preview = qualitySources?.Preview || "";
    return { Auto: auto, Original: original, Preview: preview };
  }, [qualitySources, src]);
  const resolvedQualityScaleSources = useMemo(() => {
    const full = qualityScaleSources?.full || resolvedQualitySources.Original || src;
    const half = qualityScaleSources?.half || "";
    const quarter = qualityScaleSources?.quarter || "";
    const eighth = qualityScaleSources?.eighth || "";
    const sixteenth = qualityScaleSources?.sixteenth || "";
    return { full, half, quarter, eighth, sixteenth };
  }, [qualityScaleSources, resolvedQualitySources, src]);
  const effectiveSrc = resolvedQualityScaleSources[selectedQualityScale] || resolvedQualityScaleSources.full;
  const [sourceMaxDimension, setSourceMaxDimension] = useState(0);

  const qualityScaleOptions = useMemo(() => {
    const maxDim = sourceMaxDimension || 1920;
    const options: Array<{ key: "full" | "half" | "quarter" | "eighth" | "sixteenth"; label: string; enabled: boolean }> = [
      { key: "full", label: "Full", enabled: Boolean(resolvedQualityScaleSources.full) },
      { key: "half", label: "1/2", enabled: Boolean(resolvedQualityScaleSources.half) },
      { key: "quarter", label: "1/4", enabled: maxDim >= 1280 && Boolean(resolvedQualityScaleSources.quarter) },
      { key: "eighth", label: "1/8", enabled: maxDim >= 2560 && Boolean(resolvedQualityScaleSources.eighth) },
      { key: "sixteenth", label: "1/16", enabled: maxDim >= 5120 && Boolean(resolvedQualityScaleSources.sixteenth) },
    ];
    return options;
  }, [resolvedQualityScaleSources, sourceMaxDimension]);

  const currentWindowMode: "embedded" | "detached" =
    windowMode || (windowLabel === "artifact-media" ? "detached" : "embedded");
  const targetWindow: "main" | "detached" = currentWindowMode === "detached" ? "main" : "detached";
  const currentFullscreenMode: "off" | "native_window" | "dom_fallback" = isNativeWindowFullscreen
    ? "native_window"
    : (isFallbackFullscreen ? "dom_fallback" : "off");
  const isAnyFullscreen = isFullscreen || isFallbackFullscreen || isNativeWindowFullscreen;

  const buildSessionState = useCallback((): ArtifactMediaSessionStateV1 => ({
    schema_version: "artifact_media_session_state_v1",
    path: mediaIdentity,
    window_mode: currentWindowMode,
    fullscreen_mode: currentFullscreenMode,
    current_time: Number.isFinite(currentTime) ? currentTime : 0,
    is_playing: isPlaying,
    volume: Number.isFinite(volume) ? Math.max(0, Math.min(1, volume)) : 1,
    is_muted: isMuted,
    quality_scale: selectedQualityScale,
    playback_rate: Number.isFinite(playbackRate) ? playbackRate : 1,
    duration_sec: Number.isFinite(duration) ? Math.max(0, duration) : 0,
    updated_at_ms: Date.now(),
  }), [
    currentFullscreenMode,
    currentTime,
    currentWindowMode,
    duration,
    isMuted,
    isPlaying,
    mediaIdentity,
    playbackRate,
    selectedQualityScale,
    volume,
  ]);

  const shouldApplyRemoteState = useCallback((envelope: ArtifactMediaSyncEnvelopeV1): boolean => {
    const remote = envelope.payload.session_state;
    if (!remote || remote.path !== mediaIdentity) return false;
    const remoteTs = Number(remote.updated_at_ms || 0);
    const localHasFocus = document.hasFocus();
    const remoteHasFocus = Boolean(envelope.trace?.has_focus);

    // MARKER_159.WINFS.R3_AUTHORITY: active-focused window is authoritative.
    if (!localHasFocus && remoteHasFocus) return true;
    if (localHasFocus && !remoteHasFocus) return false;
    return remoteTs > lastAppliedRemoteTsRef.current;
  }, [mediaIdentity]);

  const applyRemoteSessionState = useCallback((state: ArtifactMediaSessionStateV1) => {
    const video = videoRef.current;
    if (!video) return;
    applyingRemoteRef.current = true;
    try {
      const nextTime = Number(state.current_time || 0);
      if (Number.isFinite(nextTime) && Math.abs((video.currentTime || 0) - nextTime) > 0.25) {
        video.currentTime = Math.max(0, nextTime);
        setCurrentTime(Math.max(0, nextTime));
      }

      if (typeof state.quality_scale === "string" && state.quality_scale !== selectedQualityScale) {
        setSelectedQualityScale(state.quality_scale);
      }

      const nextRate = Number(state.playback_rate || 1);
      if (Number.isFinite(nextRate) && nextRate > 0 && nextRate !== video.playbackRate) {
        video.playbackRate = nextRate;
        setPlaybackRate(nextRate);
      }

      const nextVolume = Number(state.volume);
      if (Number.isFinite(nextVolume)) {
        const v = Math.max(0, Math.min(1, nextVolume));
        video.volume = v;
        setVolume(v);
      }

      const nextMuted = Boolean(state.is_muted);
      if (video.muted !== nextMuted) {
        video.muted = nextMuted;
      }
      setIsMuted(nextMuted);

      if (state.is_playing) {
        const attempt = video.play();
        if (attempt && typeof attempt.catch === "function") {
          void attempt.catch(() => {});
        }
        setIsPlaying(true);
      } else {
        video.pause();
        setIsPlaying(false);
      }
    } finally {
      window.setTimeout(() => {
        applyingRemoteRef.current = false;
      }, 0);
    }
  }, [selectedQualityScale]);

  const broadcastSessionState = useCallback((reason: string) => {
    const channel = channelRef.current;
    if (!channel || applyingRemoteRef.current || !mediaIdentity) return;
    const envelope: ArtifactMediaSyncEnvelopeV1 = {
      schema_version: "artifact_media_window_contract_v1",
      action: "sync_playback_state",
      target_window: targetWindow,
      payload: {
        session_state: buildSessionState(),
      },
      trace: {
        source: sessionIdRef.current,
        has_focus: document.hasFocus(),
        reason,
      },
    };
    channel.postMessage(envelope);
  }, [buildSessionState, mediaIdentity, targetWindow]);

  useEffect(() => {
    const active = qualityScaleOptions.find((q) => q.key === selectedQualityScale);
    if (active?.enabled) return;
    const firstEnabled = qualityScaleOptions.find((q) => q.enabled);
    if (firstEnabled && firstEnabled.key !== selectedQualityScale) {
      setSelectedQualityScale(firstEnabled.key);
    }
  }, [qualityScaleOptions, selectedQualityScale]);

  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return;
    const channel = new BroadcastChannel(MEDIA_SESSION_CHANNEL);
    channelRef.current = channel;

    channel.onmessage = (event: MessageEvent<ArtifactMediaSyncEnvelopeV1>) => {
      const envelope = event.data;
      if (!envelope || envelope.schema_version !== "artifact_media_window_contract_v1") return;
      if (envelope.action !== "sync_playback_state") return;
      if (envelope.trace?.source === sessionIdRef.current) return;
      if (!shouldApplyRemoteState(envelope)) return;

      const remoteState = envelope.payload?.session_state;
      if (!remoteState) return;
      lastAppliedRemoteTsRef.current = Number(remoteState.updated_at_ms || 0);
      applyRemoteSessionState(remoteState);
    };

    return () => {
      channelRef.current = null;
      channel.close();
    };
  }, [applyRemoteSessionState, shouldApplyRemoteState]);

  useEffect(() => {
    if (!mediaIdentity) return;
    broadcastSessionState("mount");
  }, [broadcastSessionState, mediaIdentity]);

  useEffect(() => {
    const onFocus = () => broadcastSessionState("focus");
    const onBlur = () => broadcastSessionState("blur");
    const onBeforeUnload = () => broadcastSessionState("window-close");
    window.addEventListener("focus", onFocus);
    window.addEventListener("blur", onBlur);
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => {
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("blur", onBlur);
      window.removeEventListener("beforeunload", onBeforeUnload);
    };
  }, [broadcastSessionState]);

  const clearHideTimer = useCallback(() => {
    if (hideTimerRef.current !== null) {
      window.clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  }, [currentWindowMode, effectiveSrc, isAnyFullscreen]);

  useEffect(() => {
    if (!isFallbackFullscreen) return;
    const onEsc = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsFallbackFullscreen(false);
    };
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [isFallbackFullscreen]);

  const scheduleHideControls = useCallback(() => {
    clearHideTimer();
    hideTimerRef.current = window.setTimeout(() => {
      setShowControls(false);
      setShowSettings(false);
    }, CONTROL_HIDE_MS);
  }, [clearHideTimer]);

  useEffect(() => {
    return () => clearHideTimer();
  }, [clearHideTimer]);

  useEffect(() => {
    const node = wrapperRef.current;
    if (!node || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      const h = Math.round(entry?.contentRect?.height || 0);
      setWrapperHeight(h);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const onFsChange = () => {
      const doc = document as Document & { webkitFullscreenElement?: Element | null };
      const fullscreenElement = doc.fullscreenElement || doc.webkitFullscreenElement;
      setIsFullscreen(Boolean(fullscreenElement && wrapperRef.current && fullscreenElement === wrapperRef.current));
    };
    document.addEventListener("fullscreenchange", onFsChange);
    document.addEventListener("webkitfullscreenchange", onFsChange as EventListener);
    return () => {
      document.removeEventListener("fullscreenchange", onFsChange);
      document.removeEventListener("webkitfullscreenchange", onFsChange as EventListener);
    };
  }, []);

  useEffect(() => {
    onFullscreenChange?.(isAnyFullscreen);
  }, [isAnyFullscreen, onFullscreenChange]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    video.pause();
    video.currentTime = 0;
    video.load();
    setCurrentTime(0);
    setDuration(0);
    setIsPlaying(false);
    setShowSettings(false);
    setPlaybackFailed(false);
    setNaturalVideoSize(null);
  }, [effectiveSrc]);

  // MARKER_159.R8.AUTO_FIT_DISABLED:
  // automatic detached window resize-by-video-aspect was removed because repeated
  // resize attempts created visible jank and overrode user-controlled window sizing.

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    video.playbackRate = playbackRate;
  }, [playbackRate]);

  useEffect(() => {
    broadcastSessionState("playback-rate-change");
  }, [broadcastSessionState, playbackRate]);

  useEffect(() => {
    broadcastSessionState("quality-scale-change");
  }, [broadcastSessionState, selectedQualityScale]);

  useEffect(() => {
    broadcastSessionState("volume-change");
  }, [broadcastSessionState, volume, isMuted]);

  useEffect(() => {
    broadcastSessionState("play-state-change");
  }, [broadcastSessionState, isPlaying]);

  useEffect(() => {
    if (!Number.isFinite(currentTime)) return;
    broadcastSessionState("seek-time-update");
  }, [broadcastSessionState, currentTime]);

  const handleTogglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      const attempt = video.play();
      if (attempt && typeof attempt.catch === "function") {
        attempt
          .then(() => {
            setPlaybackFailed(false);
            setIsPlaying(true);
            scheduleHideControls();
          })
          .catch(() => {
            setPlaybackFailed(true);
            if (selectedQualityScale !== "full") {
              setSelectedQualityScale("full");
            }
          });
      } else {
        setIsPlaying(true);
        scheduleHideControls();
      }
    } else {
      video.pause();
      setIsPlaying(false);
      setShowControls(true);
      clearHideTimer();
    }
  }, [clearHideTimer, scheduleHideControls, selectedQualityScale]);

  const handleSeek = useCallback((next: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = next;
    setCurrentTime(next);
  }, []);

  const handleVolume = useCallback((next: number) => {
    const video = videoRef.current;
    if (!video) return;
    const v = Math.max(0, Math.min(1, next));
    video.volume = v;
    video.muted = v === 0;
    setVolume(v);
    setIsMuted(v === 0);
  }, []);

  const handleToggleMute = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    const nextMuted = !video.muted;
    video.muted = nextMuted;
    setIsMuted(nextMuted);
  }, []);

  const handleFullscreen = useCallback(() => {
    if (isTauri()) {
      if (fullscreenToggleLockRef.current) return;
      fullscreenToggleLockRef.current = true;
      void (async () => {
        try {
          // MARKER_159.C2.WINFS.SET_CURRENT:
          // Use actual current-window state to avoid occasional toggle desync/stick.
          const current = await getCurrentWindowFullscreen();
          const target = !(typeof current === "boolean" ? current : isNativeWindowFullscreen);
          let applied = await setCurrentWindowFullscreen(target);

          // Verify once after native transition animation.
          await new Promise((resolve) => window.setTimeout(resolve, 140));
          const observed = await getCurrentWindowFullscreen();
          if (typeof observed === "boolean" && observed !== target) {
            applied = await setCurrentWindowFullscreen(target);
          }

          const finalState = typeof applied === "boolean"
            ? applied
            : (typeof observed === "boolean" ? observed : target);
          setIsNativeWindowFullscreen(finalState);
          setIsFullscreen(finalState);
          if (finalState) {
            setIsFallbackFullscreen(false);
          } else {
            setIsFallbackFullscreen(false);
            setIsFullscreen(false);
            setIsNativeWindowFullscreen(false);
          }
        } catch {
          // Fallback to label-routed toggle path.
          const next = !isNativeWindowFullscreen;
          const requested = String(windowLabel || "main").trim() || "main";
          const labels = Array.from(new Set([
            requested,
            requested === "artifact-media" ? "artifact-main" : "artifact-media",
            "artifact-main",
            "artifact-media",
            "main",
          ]));
          for (const label of labels) {
            const ok = await setWindowFullscreen(next, label);
            if (!ok) continue;
            setIsNativeWindowFullscreen(next);
            setIsFullscreen(next);
            if (next) setIsFallbackFullscreen(false);
            break;
          }
        } finally {
          window.setTimeout(() => {
            fullscreenToggleLockRef.current = false;
          }, 220);
        }
      })();
      return;
    }
    const wrapper = wrapperRef.current;
    const video = videoRef.current;
    const doc = document as Document & {
      webkitExitFullscreen?: () => Promise<void> | void;
      webkitFullscreenElement?: Element | null;
    };
    if (!wrapper && !video) return;
    const activeFs = doc.fullscreenElement || doc.webkitFullscreenElement;
    if (activeFs) {
      if (typeof doc.exitFullscreen === "function") {
        void doc.exitFullscreen();
        return;
      }
      if (typeof doc.webkitExitFullscreen === "function") {
        void doc.webkitExitFullscreen();
        return;
      }
    }
    if (isFallbackFullscreen) {
      setIsFallbackFullscreen(false);
      return;
    }
    if (wrapper && typeof wrapper.requestFullscreen === "function") {
      void wrapper.requestFullscreen().catch(() => setIsFallbackFullscreen(true));
      return;
    }
    const webkitWrapper = wrapper as HTMLDivElement & { webkitRequestFullscreen?: () => Promise<void> | void };
    if (webkitWrapper && typeof webkitWrapper.webkitRequestFullscreen === "function") {
      try {
        void webkitWrapper.webkitRequestFullscreen();
      } catch {
        setIsFallbackFullscreen(true);
      }
      return;
    }
    const webkitVideo = video as HTMLVideoElement & { webkitEnterFullscreen?: () => void };
    if (webkitVideo && typeof webkitVideo.webkitEnterFullscreen === "function") {
      try {
        webkitVideo.webkitEnterFullscreen();
      } catch {
        setIsFallbackFullscreen(true);
      }
      return;
    }
    setIsFallbackFullscreen(true);
  }, [isFallbackFullscreen, isNativeWindowFullscreen, windowLabel]);

  const handleLoadedMeta = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    setPlaybackFailed(false);
    setDuration(Number(video.duration || 0));
    setVolume(Number(video.volume || 1));
    setIsMuted(Boolean(video.muted));
    const videoWidth = Number(video.videoWidth || 0);
    const videoHeight = Number(video.videoHeight || 0);
    const maxDim = Math.max(videoWidth, videoHeight);
    setSourceMaxDimension((prev) => Math.max(prev, maxDim));

    if (Number.isFinite(videoWidth) && Number.isFinite(videoHeight) && videoWidth > 0 && videoHeight > 0) {
      setNaturalVideoSize({ width: videoWidth, height: videoHeight });
    }

    if (currentWindowMode === "detached") {
      window.setTimeout(() => {
        const wrapperRect = wrapperRef.current?.getBoundingClientRect();
        const toolbarRect = document
          .querySelector('[data-artifact-toolbar="1"]')
          ?.getBoundingClientRect();
        console.info("MARKER_159.R12.DETACHED_MEDIA_DOM_GEOMETRY", {
          src: mediaIdentity,
          dpr: window.devicePixelRatio || 1,
          windowInner: {
            width: window.innerWidth,
            height: window.innerHeight,
          },
          videoIntrinsic: {
            width: videoWidth,
            height: videoHeight,
          },
          wrapperRect: wrapperRect
            ? {
                width: Math.round(wrapperRect.width),
                height: Math.round(wrapperRect.height),
              }
            : null,
          toolbarRect: toolbarRect
            ? {
                width: Math.round(toolbarRect.width),
                height: Math.round(toolbarRect.height),
              }
            : null,
        });
      }, 0);
    }
  }, []);

  const handlePlaybackError = useCallback(() => {
    setPlaybackFailed(true);
    if (selectedQualityScale !== "full") {
      setSelectedQualityScale("full");
    }
  }, [selectedQualityScale]);

  const timeLabel = useMemo(() => {
    const f = (value: number) => {
      const t = Math.max(0, Math.floor(value));
      const m = Math.floor(t / 60);
      const s = t % 60;
      return `${m}:${String(s).padStart(2, "0")}`;
    };
    return `${f(currentTime)} / ${f(duration)}`;
  }, [currentTime, duration]);

  const controlsBottom = useMemo(() => {
    if (isAnyFullscreen) return 0;
    let adaptiveInset = 2;
    if (wrapperHeight >= 520) adaptiveInset = 12;
    else if (wrapperHeight >= 420) adaptiveInset = 6;
    const fsInset = isFullscreen ? 8 : 0;
    return Math.max(0, controlsOffsetBottom + adaptiveInset + fsInset);
  }, [controlsOffsetBottom, isAnyFullscreen, isFullscreen, wrapperHeight]);

  return (
    <div
      ref={wrapperRef}
      style={
        isAnyFullscreen
          ? {
              position: "fixed",
              left: 0,
              top: 0,
              width: "100vw",
              height: "100vh",
              zIndex: 999999,
              background: "#000",
              borderRadius: 0,
              overflow: "hidden",
            }
          : {
              position: "relative",
              width: "100%",
              height: "100%",
              background: "#000",
              borderRadius: currentWindowMode === "detached" ? 0 : 6,
              overflow: "hidden",
            }
      }
      onMouseMove={() => {
        setShowControls(true);
        if (isPlaying) scheduleHideControls();
      }}
      onMouseLeave={() => {
        if (isPlaying) scheduleHideControls();
      }}
    >
      <video
        ref={videoRef}
        key={effectiveSrc}
        autoPlay={false}
        preload="metadata"
        poster={poster}
        playsInline
        onLoadedMetadata={handleLoadedMeta}
        onError={handlePlaybackError}
        onTimeUpdate={() => setCurrentTime(Number(videoRef.current?.currentTime || 0))}
        onPause={() => setIsPlaying(false)}
        onPlay={() => setIsPlaying(true)}
        style={
          isAnyFullscreen
            ? { width: "100%", height: "100%", display: "block", objectFit: "contain", background: "#000" }
            : (currentWindowMode === "detached"
                ? { width: "100%", height: "100%", display: "block", objectFit: "contain", background: "#000" }
                : { width: "100%", aspectRatio: "16 / 9", display: "block", background: "#000" })
        }
      >
        <source src={effectiveSrc} type={mimeType} />
      </video>

      {!isPlaying && (
        <button
          type="button"
          onClick={handleTogglePlay}
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            transform: "translate(-50%, -50%)",
            width: 64,
            height: 64,
            borderRadius: "50%",
            border: "1px solid #4a4a4a",
            background: "rgba(0,0,0,0.58)",
            color: "#f5f5f5",
            fontSize: 22,
            lineHeight: "64px",
            cursor: "pointer",
          }}
          title="Play"
        >
          ►
        </button>
      )}

      {playbackFailed && showControls && (
        <div
          style={{
            position: "absolute",
            left: 12,
            top: 12,
            background: "rgba(0,0,0,0.58)",
            border: "1px solid #3a3a3a",
            color: "#cfcfcf",
            fontSize: 11,
            borderRadius: 4,
            padding: "4px 8px",
          }}
        >
          playback fallback active
        </div>
      )}

      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          padding: isAnyFullscreen ? "8px 12px 12px" : "8px 12px 10px",
          background: "transparent",
          opacity: showControls ? 1 : 0,
          pointerEvents: showControls ? "auto" : "none",
          transition: "opacity 220ms ease",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <button type="button" onClick={handleTogglePlay} style={{ background: "transparent", border: "1px solid #3a3a3a", color: "#e5e7eb", borderRadius: 4, width: 30, height: 26 }}>
          {isPlaying ? "||" : ">"}
        </button>
        <input
          type="range"
          min={0}
          max={Math.max(0.001, duration)}
          step={0.01}
          value={Math.min(currentTime, duration || 0)}
          onChange={(e) => handleSeek(Number(e.target.value))}
          style={{ flex: 1 }}
        />
        <span style={{ color: "#d1d5db", fontSize: 12, minWidth: 74, textAlign: "right" }}>{timeLabel}</span>
        <button type="button" onClick={handleToggleMute} style={{ background: "transparent", border: "1px solid #3a3a3a", color: "#e5e7eb", borderRadius: 4, width: 30, height: 26 }}>
          {isMuted ? (
            <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
              <path d="M12 5l-4 4H5v6h3l4 4V5z" fill="currentColor" />
              <path d="M16 10l4 4M20 10l-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
              <path d="M12 5l-4 4H5v6h3l4 4V5z" fill="currentColor" />
              <path d="M16 9c1.6 1.3 1.6 4.7 0 6M18.5 7c2.9 2.4 2.9 7.6 0 10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" fill="none" />
            </svg>
          )}
        </button>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={isMuted ? 0 : volume}
          onChange={(e) => handleVolume(Number(e.target.value))}
          style={{ width: 80 }}
        />
        <button
          type="button"
          onClick={() => setShowSettings((v) => !v)}
          title="Settings"
          aria-label="Video settings"
          style={{ background: "transparent", border: "1px solid #3a3a3a", color: "#ffffff", borderRadius: 4, width: 34, height: 28 }}
        >
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <path
              d="M12 8.75a3.25 3.25 0 1 0 0 6.5 3.25 3.25 0 0 0 0-6.5Zm8.1 3.25-1.75-.78a6.4 6.4 0 0 0-.37-1.15l.98-1.64-1.85-1.85-1.64.98a6.4 6.4 0 0 0-1.15-.37L13.54 3h-3.08l-.78 1.75c-.4.08-.78.2-1.15.37l-1.64-.98-1.85 1.85.98 1.64c-.16.37-.29.75-.37 1.15L3 10.46v3.08l1.75.78c.08.4.2.78.37 1.15l-.98 1.64 1.85 1.85 1.64-.98c.37.16.75.29 1.15.37L10.46 21h3.08l.78-1.75c.4-.08.78-.2 1.15-.37l1.64.98 1.85-1.85-.98-1.64c.16-.37.29-.75.37-1.15l1.75-.78v-3.08Z"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinejoin="round"
            />
          </svg>
        </button>
        <button
          type="button"
          title="Fullscreen"
          aria-label="Toggle fullscreen"
          onClick={handleFullscreen}
          style={{ background: "transparent", border: "1px solid #3a3a3a", color: "#e5e7eb", borderRadius: 4, width: 30, height: 26 }}
        >
          <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
            <path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          </svg>
        </button>
      </div>

      {showControls && showSettings && (
        <div
          style={{
            position: "absolute",
            right: 12,
            bottom: controlsBottom + 56,
            width: 210,
            background: "rgba(15,15,15,0.94)",
            border: "1px solid #303030",
            borderRadius: 6,
            color: "#e5e7eb",
            padding: 10,
            display: "grid",
            gap: 8,
          }}
        >
          <label style={{ fontSize: 12, display: "grid", gap: 4 }}>
            <span>Quality</span>
            <select
              value={selectedQualityScale}
              onChange={(e) => setSelectedQualityScale(e.target.value as "full" | "half" | "quarter" | "eighth" | "sixteenth")}
              style={{ background: "#0f0f0f", color: "#e5e7eb", border: "1px solid #3a3a3a", borderRadius: 4, padding: "4px 6px" }}
            >
              {qualityScaleOptions.map((q) => (
                <option key={q.key} value={q.key} disabled={!q.enabled}>
                  {q.label}
                </option>
              ))}
            </select>
          </label>
          <label style={{ fontSize: 12, display: "grid", gap: 4 }}>
            <span>Speed</span>
            <select
              value={String(playbackRate)}
              onChange={(e) => setPlaybackRate(Number(e.target.value))}
              style={{ background: "#0f0f0f", color: "#e5e7eb", border: "1px solid #3a3a3a", borderRadius: 4, padding: "4px 6px" }}
            >
              {speedOptions.map((s) => (
                <option key={s} value={String(s)}>
                  {s}x
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
    </div>
  );
}
