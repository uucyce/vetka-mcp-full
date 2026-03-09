import { useEffect, useMemo, useRef, useState } from "react";
import {
  computeDreamScore,
  computeDisplayedBox,
  GeometrySnapshot,
  LAB_FOOTER_HEIGHT,
  ShellVariant,
  suggestShellSize,
} from "./lib/geometry";
import { setCurrentWindowLogicalSize, toggleFullscreen } from "./lib/nativeWindow";

type PreviewQualityKey = "full" | "half" | "quarter" | "eighth" | "sixteenth" | "thirtysecond";

const PREVIEW_QUALITY_OPTIONS: { key: PreviewQualityKey; label: string; scale: number }[] = [
  { key: "full", label: "1x", scale: 1 },
  { key: "half", label: "1/2", scale: 0.5 },
  { key: "quarter", label: "1/4", scale: 0.25 },
  { key: "eighth", label: "1/8", scale: 0.125 },
  { key: "sixteenth", label: "1/16", scale: 0.0625 },
  { key: "thirtysecond", label: "1/32", scale: 0.03125 },
];

declare global {
  interface Window {
    vetkaPlayerLab?: {
      snapshot: () => GeometrySnapshot;
      print: () => GeometrySnapshot;
      setVariant: (variant: ShellVariant) => void;
      setSyntheticSize: (width: number, height: number) => void;
      setPreviewQuality: (quality: PreviewQualityKey) => void;
      applySuggestedShell: () => GeometrySnapshot;
      resetShell: () => void;
      toggleDebug: () => void;
      toggleFullscreen: () => Promise<boolean | null>;
    };
  }
}

function readQuery() {
  const params = new URLSearchParams(window.location.search);
  return {
    src: params.get("src") || "",
    variant: (params.get("variant") as ShellVariant | null) || "fixed-footer",
    mockWidth: Number(params.get("mockWidth") || 0),
    mockHeight: Number(params.get("mockHeight") || 0),
    applySuggestedShell: params.get("applySuggestedShell") === "1",
    debug: params.get("debug") === "1",
  };
}

function formatName(value: string) {
  if (!value) return "VETKA Player";
  const tail = value.split("/").pop() || value;
  return tail.length > 52 ? `${tail.slice(0, 49)}...` : tail;
}

function formatTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const total = Math.floor(seconds);
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function IconOpen() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 8.5A2.5 2.5 0 0 1 6.5 6H10l2 2h5.5A2.5 2.5 0 0 1 20 10.5v7A2.5 2.5 0 0 1 17.5 20h-11A2.5 2.5 0 0 1 4 17.5z" />
      <path d="M12 6V3.5M12 3.5l-2 2M12 3.5l2 2" />
    </svg>
  );
}

function IconFullscreen() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8 4H4v4M16 4h4v4M8 20H4v-4M20 20h-4v-4" />
    </svg>
  );
}

function IconFit() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="5" y="7" width="14" height="10" rx="2" />
      <path d="M9 10h6M9 14h6" />
    </svg>
  );
}

function IconPlay() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8 5.5v13l10-6.5z" />
    </svg>
  );
}

function IconPause() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8 5h3v14H8zM13 5h3v14h-3z" />
    </svg>
  );
}

function IconRewind() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M11.5 7 5 12l6.5 5zM18.5 7 12 12l6.5 5z" />
    </svg>
  );
}

function IconForward() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m12.5 7 6.5 5-6.5 5zM5.5 7 12 12l-6.5 5z" />
    </svg>
  );
}

function IconVolume({ isMuted }: { isMuted: boolean }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 14h4l5 4V6L8 10H4z" />
      {isMuted ? (
        <path d="m17 9 4 6M21 9l-4 6" />
      ) : (
        <path d="M17 9a4 4 0 0 1 0 6M19.5 6.5a7.5 7.5 0 0 1 0 11" />
      )}
    </svg>
  );
}

function IconStar({ active }: { active: boolean }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 3.7l2.6 5.2 5.8.8-4.2 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.2-4.1 5.8-.8z"
        fill={active ? "currentColor" : "none"}
      />
    </svg>
  );
}

function IconVetka() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <line x1="12" y1="6" x2="12" y2="18" />
      <path d="M12 12 L8 7" />
      <path d="M12 12 L16 7" />
    </svg>
  );
}

function IconQuality() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="4" y="6" width="16" height="12" rx="2" />
      <path d="M9 10h.01M12 10h.01M15 10h.01M9 14h.01M12 14h.01M15 14h.01" />
    </svg>
  );
}

function App() {
  const initialQuery = useMemo(readQuery, []);
  const [variant, setVariant] = useState<ShellVariant>(initialQuery.variant);
  const [src, setSrc] = useState<string>(initialQuery.src);
  const [fileName, setFileName] = useState<string>(formatName(initialQuery.src));
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
  const [syntheticSize, setSyntheticSize] = useState({
    width: initialQuery.mockWidth,
    height: initialQuery.mockHeight,
  });
  const [shellSizeOverride, setShellSizeOverride] = useState<{ width: number; height: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isDebugVisible, setIsDebugVisible] = useState(initialQuery.debug);
  const [geometryTick, setGeometryTick] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [showTransport, setShowTransport] = useState(true);
  const [previewQuality, setPreviewQuality] = useState<PreviewQualityKey>("full");
  const [showQualityMenu, setShowQualityMenu] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);
  const [isInVetka, setIsInVetka] = useState(false);
  const viewerRef = useRef<HTMLDivElement | null>(null);
  const shellRef = useRef<HTMLDivElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const topbarRef = useRef<HTMLElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const qualityMenuRef = useRef<HTMLDivElement | null>(null);
  const autoSizedKeyRef = useRef("");
  const transportTimerRef = useRef<number | null>(null);
  const intrinsicSize = naturalSize.width > 0 && naturalSize.height > 0 ? naturalSize : syntheticSize;
  const sourceKind: GeometrySnapshot["sourceKind"] = naturalSize.width > 0 && naturalSize.height > 0
    ? "video"
    : "synthetic";
  const footerReserve = sourceKind === "video" && !isDebugVisible ? 0 : LAB_FOOTER_HEIGHT;
  const isPureMode = !isDebugVisible;
  const previewQualityOption = PREVIEW_QUALITY_OPTIONS.find((option) => option.key === previewQuality) || PREVIEW_QUALITY_OPTIONS[0];
  const effectivePreviewScale = sourceKind === "video" ? previewQualityOption.scale : 1;

  useEffect(() => {
    const shellNode = shellRef.current;
    const viewerNode = viewerRef.current;
    if (!shellNode && !viewerNode) return;

    const observer = new ResizeObserver(() => {
      setGeometryTick((tick) => tick + 1);
    });

    if (shellNode) observer.observe(shellNode);
    if (viewerNode) observer.observe(viewerNode);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const onResize = () => setGeometryTick((tick) => tick + 1);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const snapshot = useMemo<GeometrySnapshot>(() => {
    const viewerRect = viewerRef.current?.getBoundingClientRect();
    const shellRect = shellRef.current?.getBoundingClientRect();
    const topbarRect = topbarRef.current?.getBoundingClientRect();
    const viewerWidth = Number(viewerRect?.width || 0);
    const viewerHeight = Number(viewerRect?.height || 0);
    const shellWidth = Number(shellRect?.width || 0);
    const shellHeight = Number(shellRect?.height || 0);
    const topbarHeight = Number(topbarRect?.height || 0);
    const displayed = computeDisplayedBox(
      viewerWidth,
      viewerHeight,
      intrinsicSize.width,
      intrinsicSize.height,
    );
    const suggested = suggestShellSize(
      intrinsicSize.width,
      intrinsicSize.height,
      footerReserve,
      Math.floor(window.innerWidth * 0.92),
      Math.floor(window.innerHeight * 0.92),
    );
    const review = computeDreamScore({
      windowInnerWidth: Number(window.innerWidth || 0),
      windowInnerHeight: Number(window.innerHeight || 0),
      topbarHeight,
      footerHeight: footerReserve,
      displayedWidth: displayed.displayedWidth,
      displayedHeight: displayed.displayedHeight,
      horizontalLetterboxPx: displayed.horizontalLetterboxPx,
      aspectError: displayed.aspectError,
    });

    return {
      ok: Boolean(viewerWidth > 0 && viewerHeight > 0 && intrinsicSize.width > 0 && intrinsicSize.height > 0),
      reason: intrinsicSize.width > 0 ? undefined : "video_metadata_unavailable",
      fileName: fileName || (sourceKind === "synthetic" ? "Synthetic probe" : "No file loaded"),
      devicePixelRatio: Number(window.devicePixelRatio || 1),
      windowInnerWidth: Number(window.innerWidth || 0),
      windowInnerHeight: Number(window.innerHeight || 0),
      topbarHeight: Number(topbarHeight.toFixed(2)),
      shellWidth: Number(shellWidth.toFixed(2)),
      shellHeight: Number(shellHeight.toFixed(2)),
      viewerWidth: Number(viewerWidth.toFixed(2)),
      viewerHeight: Number(viewerHeight.toFixed(2)),
      footerHeight: footerReserve,
      videoIntrinsicWidth: intrinsicSize.width,
      videoIntrinsicHeight: intrinsicSize.height,
      displayedWidth: displayed.displayedWidth,
      displayedHeight: displayed.displayedHeight,
      horizontalLetterboxPx: displayed.horizontalLetterboxPx,
      verticalLetterboxPx: displayed.verticalLetterboxPx,
      naturalAspectRatio: displayed.naturalAspectRatio,
      viewerAspectRatio: displayed.viewerAspectRatio,
      aspectError: displayed.aspectError,
      suggestedShellWidth: suggested.shellWidth,
      suggestedShellHeight: suggested.shellHeight,
      variant,
      sourceKind,
      dreamScore: review.dreamScore,
      viewerDominanceRatio: review.viewerDominanceRatio,
      chromeRatio: review.chromeRatio,
      previewQualityLabel: previewQualityOption.label,
      previewScale: effectivePreviewScale,
    };
  }, [
    effectivePreviewScale,
    fileName,
    geometryTick,
    intrinsicSize.height,
    intrinsicSize.width,
    footerReserve,
    previewQualityOption.label,
    sourceKind,
    variant,
  ]);

  useEffect(() => {
    try {
      localStorage.setItem("vetka_player_lab_snapshot", JSON.stringify(snapshot));
    } catch {
      // ignore storage errors
    }
  }, [snapshot]);

  useEffect(() => {
    const key = `${src}|${snapshot.videoIntrinsicWidth}x${snapshot.videoIntrinsicHeight}`;
    if (!snapshot.ok) return;
    if (!src && sourceKind !== "synthetic") return;
    if (autoSizedKeyRef.current === key) return;

    const next = {
      width: snapshot.suggestedShellWidth,
      height: snapshot.suggestedShellHeight,
    };
    autoSizedKeyRef.current = key;
    setShellSizeOverride(next);
    void setCurrentWindowLogicalSize(next.width, next.height);
  }, [
    snapshot.ok,
    snapshot.suggestedShellHeight,
    snapshot.suggestedShellWidth,
    snapshot.videoIntrinsicHeight,
    snapshot.videoIntrinsicWidth,
    sourceKind,
    src,
  ]);

  useEffect(() => {
    if (!initialQuery.applySuggestedShell) return;
    if (!snapshot.ok) return;
    setShellSizeOverride({
      width: snapshot.suggestedShellWidth,
      height: snapshot.suggestedShellHeight,
    });
  }, [initialQuery.applySuggestedShell, snapshot.ok, snapshot.suggestedShellHeight, snapshot.suggestedShellWidth]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === "i") {
        setIsDebugVisible((value) => !value);
      }
      if (event.key.toLowerCase() === "f") {
        void toggleFullscreen();
      }
      if (event.key.toLowerCase() === "q") {
        const currentIndex = PREVIEW_QUALITY_OPTIONS.findIndex((option) => option.key === previewQuality);
        const nextOption = PREVIEW_QUALITY_OPTIONS[(currentIndex + 1) % PREVIEW_QUALITY_OPTIONS.length];
        setPreviewQuality(nextOption.key);
      }
      if (event.key === " " && videoRef.current) {
        event.preventDefault();
        if (videoRef.current.paused) {
          void videoRef.current.play();
        } else {
          videoRef.current.pause();
        }
      }
      if (event.key === "ArrowLeft" && videoRef.current) {
        event.preventDefault();
        videoRef.current.currentTime = Math.max(0, videoRef.current.currentTime - 5);
      }
      if (event.key === "ArrowRight" && videoRef.current) {
        event.preventDefault();
        videoRef.current.currentTime = Math.min(duration || videoRef.current.duration || 0, videoRef.current.currentTime + 5);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [duration, previewQuality]);

  useEffect(() => {
    if (!showQualityMenu) return;
    const handlePointerDown = (event: MouseEvent) => {
      if (!qualityMenuRef.current?.contains(event.target as Node)) {
        setShowQualityMenu(false);
      }
    };
    window.addEventListener("mousedown", handlePointerDown);
    return () => window.removeEventListener("mousedown", handlePointerDown);
  }, [showQualityMenu]);

  useEffect(() => {
    if (!src) {
      setCurrentTime(0);
      setDuration(0);
      setIsPlaying(false);
      setShowTransport(true);
    }
  }, [src]);

  useEffect(() => {
    if (transportTimerRef.current) {
      window.clearTimeout(transportTimerRef.current);
      transportTimerRef.current = null;
    }
    if (!isPlaying || isDebugVisible) {
      setShowTransport(true);
      return;
    }
    transportTimerRef.current = window.setTimeout(() => {
      setShowTransport(false);
    }, 1800);
    return () => {
      if (transportTimerRef.current) {
        window.clearTimeout(transportTimerRef.current);
        transportTimerRef.current = null;
      }
    };
  }, [isDebugVisible, isPlaying, currentTime]);

  useEffect(() => {
    const api = {
      snapshot: () => snapshot,
      print: () => {
        console.info("MARKER_168.VIDEOPLAYER.LAB.SNAPSHOT", snapshot);
        return snapshot;
      },
      setVariant: (next: ShellVariant) => setVariant(next),
      setSyntheticSize: (width: number, height: number) => {
        setSyntheticSize({
          width: Math.max(0, Math.floor(width)),
          height: Math.max(0, Math.floor(height)),
        });
        setNaturalSize({ width: 0, height: 0 });
        setSrc("");
        setFileName("Synthetic probe");
        autoSizedKeyRef.current = "";
      },
      setPreviewQuality: (quality: PreviewQualityKey) => setPreviewQuality(quality),
      applySuggestedShell: () => {
        const next = {
          width: snapshot.suggestedShellWidth,
          height: snapshot.suggestedShellHeight,
        };
        setShellSizeOverride(next);
        void setCurrentWindowLogicalSize(next.width, next.height);
        return { ...snapshot, shellWidth: next.width, shellHeight: next.height };
      },
      resetShell: () => {
        setShellSizeOverride(null);
        autoSizedKeyRef.current = "";
      },
      toggleDebug: () => setIsDebugVisible((value) => !value),
      toggleFullscreen: () => toggleFullscreen(),
    };
    window.vetkaPlayerLab = api;
    return () => {
      if (window.vetkaPlayerLab === api) delete window.vetkaPlayerLab;
    };
  }, [snapshot]);

  function attachFile(file: File) {
    const nextUrl = URL.createObjectURL(file);
    setSrc((prev) => {
      if (prev.startsWith("blob:")) URL.revokeObjectURL(prev);
      return nextUrl;
    });
    setFileName(file.name);
    setNaturalSize({ width: 0, height: 0 });
    autoSizedKeyRef.current = "";
  }

  function syncVolume(nextVolume: number, nextMuted = false) {
    const video = videoRef.current;
    const safeVolume = Math.max(0, Math.min(1, nextVolume));
    setVolume(safeVolume);
    setIsMuted(nextMuted);
    if (!video) return;
    video.volume = safeVolume;
    video.muted = nextMuted;
  }

  function togglePlayback() {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      void video.play();
    } else {
      video.pause();
    }
  }

  return (
    <main
      className={`player-app ${isDebugVisible ? "debug-open" : ""} ${isPureMode ? "pure-mode" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        const file = event.dataTransfer.files?.[0];
        if (file) attachFile(file);
      }}
    >
      {isDebugVisible ? <div className="chrome-strip" /> : null}
      <section className="player-pane">
        {isDebugVisible ? (
          <header ref={topbarRef} className="topbar">
            <div className="title-block">
              <span className="eyebrow">VETKA Player</span>
              <strong className="media-title">{fileName || "Drop a video to begin"}</strong>
            </div>
            <div className="topbar-actions">
              <label className="ghost-button icon-chip">
                <IconOpen />
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/*"
                  style={{ display: "none" }}
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) attachFile(file);
                  }}
                />
              </label>
              <button className="ghost-button subtle" type="button" onClick={() => setIsDebugVisible(false)}>
                Hide Debug
              </button>
            </div>
          </header>
        ) : (
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            style={{ display: "none" }}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) attachFile(file);
            }}
          />
        )}

        <div className="stage-wrap">
          <div
            ref={shellRef}
            className={`viewer-shell player-shell ${variant} ${footerReserve === 0 ? "footerless" : ""}`}
            style={shellSizeOverride ? { width: `${shellSizeOverride.width}px`, height: `${shellSizeOverride.height}px` } : undefined}
          >
            <div ref={viewerRef} className="viewer-area player-canvas">
              {src ? (
                <>
                  <div className={`video-stage ${effectivePreviewScale < 1 ? "preview-scaled" : ""}`}>
                    <div
                      className="video-raster"
                      style={{
                        width: `${Math.max(1, snapshot.displayedWidth * effectivePreviewScale)}px`,
                        height: `${Math.max(1, snapshot.displayedHeight * effectivePreviewScale)}px`,
                        transform: `scale(${1 / effectivePreviewScale})`,
                      }}
                    >
                      <video
                        ref={videoRef}
                        className="viewer-video"
                        src={src}
                        controls={false}
                        playsInline
                        preload="metadata"
                        onClick={() => togglePlayback()}
                        onLoadedMetadata={(event) => {
                          const video = event.currentTarget;
                          setNaturalSize({
                            width: Number(video.videoWidth || 0),
                            height: Number(video.videoHeight || 0),
                          });
                          setDuration(Number(video.duration || 0));
                          setCurrentTime(Number(video.currentTime || 0));
                          setVolume(Number(video.volume || 1));
                          setIsMuted(Boolean(video.muted));
                          if (!fileName) setFileName(formatName(src));
                        }}
                        onPlay={() => setIsPlaying(true)}
                        onPause={() => setIsPlaying(false)}
                        onTimeUpdate={(event) => setCurrentTime(Number(event.currentTarget.currentTime || 0))}
                        onDurationChange={(event) => setDuration(Number(event.currentTarget.duration || 0))}
                        onVolumeChange={(event) => {
                          setVolume(Number(event.currentTarget.volume || 0));
                          setIsMuted(Boolean(event.currentTarget.muted));
                        }}
                      />
                    </div>
                  </div>
                  <div className={`media-label ${showTransport ? "media-label-visible" : "media-label-hidden"}`}>
                    <strong>{fileName}</strong>
                  </div>
                  <div className={`viewer-toolbar ${showTransport ? "viewer-toolbar-visible" : "viewer-toolbar-hidden"}`}>
                    <button
                      className={`icon-button ${isFavorite ? "icon-button-active" : ""}`}
                      type="button"
                      onClick={() => setIsFavorite((value) => !value)}
                      aria-label={isFavorite ? "Remove favorite" : "Add favorite"}
                      title={isFavorite ? "Remove favorite" : "Add favorite"}
                    >
                      <IconStar active={isFavorite} />
                    </button>
                    <button
                      className={`icon-button ${isInVetka ? "icon-button-active icon-button-vetka" : ""}`}
                      type="button"
                      onClick={() => setIsInVetka((value) => !value)}
                      aria-label={isInVetka ? "Saved in VETKA" : "Add to VETKA"}
                      title={isInVetka ? "Saved in VETKA" : "Add to VETKA"}
                    >
                      <IconVetka />
                    </button>
                    <button className="icon-button" type="button" onClick={() => fileInputRef.current?.click()} aria-label="Open file">
                      <IconOpen />
                    </button>
                    <button className="icon-button" type="button" onClick={() => window.vetkaPlayerLab?.applySuggestedShell()} aria-label="Fit shell">
                      <IconFit />
                    </button>
                    <div ref={qualityMenuRef} className="quality-menu-wrap">
                      <button
                        className={`icon-button quality-trigger ${showQualityMenu ? "icon-button-active" : ""}`}
                        type="button"
                        onClick={() => setShowQualityMenu((value) => !value)}
                        aria-label={`Preview quality ${previewQualityOption.label}`}
                        title={`Preview quality ${previewQualityOption.label}`}
                      >
                        <IconQuality />
                        <span className="quality-badge">{previewQualityOption.label}</span>
                      </button>
                      {showQualityMenu ? (
                        <div className="quality-menu">
                          <div className="quality-menu-title">Preview</div>
                          {PREVIEW_QUALITY_OPTIONS.map((option) => (
                            <button
                              key={option.key}
                              type="button"
                              className={`quality-option ${option.key === previewQuality ? "quality-option-active" : ""}`}
                              onClick={() => {
                                setPreviewQuality(option.key);
                                setShowQualityMenu(false);
                              }}
                            >
                              <span>{option.label}</span>
                              {option.scale < 1 ? <small>lighter render</small> : <small>full detail</small>}
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </div>
                    <button className="icon-button" type="button" onClick={() => void toggleFullscreen()} aria-label="Fullscreen">
                      <IconFullscreen />
                    </button>
                  </div>
                  <div
                    className={`transport-overlay ${showTransport ? "transport-visible" : "transport-hidden"}`}
                    onMouseMove={() => setShowTransport(true)}
                    onMouseLeave={() => {
                      if (isPlaying && !isDebugVisible) setShowTransport(false);
                    }}
                  >
                    <div className="transport-scrim" />
                    <div className="transport-bar">
                      <button className="transport-button" type="button" onClick={() => {
                        const video = videoRef.current;
                        if (!video) return;
                        video.currentTime = Math.max(0, video.currentTime - 5);
                      }} aria-label="Rewind 5 seconds">
                        <IconRewind />
                      </button>
                      <button className="transport-button transport-button-primary" type="button" onClick={() => togglePlayback()} aria-label={isPlaying ? "Pause" : "Play"}>
                        {isPlaying ? <IconPause /> : <IconPlay />}
                      </button>
                      <button className="transport-button" type="button" onClick={() => {
                        const video = videoRef.current;
                        if (!video) return;
                        video.currentTime = Math.min(duration || video.duration || 0, video.currentTime + 5);
                      }} aria-label="Forward 5 seconds">
                        <IconForward />
                      </button>
                      <span className="transport-time">{formatTime(currentTime)}</span>
                      <input
                        className="transport-progress"
                        type="range"
                        min={0}
                        max={Math.max(duration, 0.001)}
                        step={0.01}
                        value={Math.min(currentTime, duration || 0)}
                        onChange={(event) => {
                          const nextTime = Number(event.target.value || 0);
                          setCurrentTime(nextTime);
                          if (videoRef.current) videoRef.current.currentTime = nextTime;
                        }}
                        aria-label="Seek"
                      />
                      <span className="transport-time">{formatTime(duration)}</span>
                      <div className="transport-quality-chip" title="Preview quality">
                        {previewQualityOption.label}
                      </div>
                      <button className="transport-button" type="button" onClick={() => {
                        const nextMuted = !isMuted;
                        syncVolume(nextMuted ? volume : Math.max(volume, 0.6), nextMuted);
                      }} aria-label={isMuted || volume === 0 ? "Unmute" : "Mute"}>
                        <IconVolume isMuted={isMuted || volume === 0} />
                      </button>
                      <input
                        className="transport-volume"
                        type="range"
                        min={0}
                        max={1}
                        step={0.01}
                        value={isMuted ? 0 : volume}
                        onChange={(event) => {
                          const nextVolume = Number(event.target.value || 0);
                          syncVolume(nextVolume, nextVolume === 0);
                        }}
                        aria-label="Volume"
                      />
                      <button className="transport-button" type="button" onClick={() => void toggleFullscreen()} aria-label="Fullscreen">
                        <IconFullscreen />
                      </button>
                    </div>
                  </div>
                  <div className={`hud ${isPlaying ? "hud-hidden" : ""}`}>
                    <button className="hud-button" type="button" onClick={() => {
                      togglePlayback();
                    }} aria-label={isPlaying ? "Pause" : "Play"}>
                      {isPlaying ? <IconPause /> : <IconPlay />}
                    </button>
                  </div>
                </>
              ) : intrinsicSize.width > 0 && intrinsicSize.height > 0 ? (
                <div className="synthetic-stage">
                  <div
                    className="synthetic-frame"
                    style={{
                      width: `${snapshot.displayedWidth}px`,
                      height: `${snapshot.displayedHeight}px`,
                    }}
                  >
                    <div className="synthetic-label">
                      {intrinsicSize.width} × {intrinsicSize.height}
                    </div>
                  </div>
                </div>
              ) : (
                <div className={`dropzone player-dropzone ${isDragging ? "dragging" : ""}`}>
                  <div>
                    <strong>Drop a video here</strong>
                    <p className="dropzone-copy">
                      This shell auto-fits to the media once metadata is known.
                    </p>
                    <button className="dropzone-open" type="button" onClick={() => fileInputRef.current?.click()}>
                      Open video
                    </button>
                  </div>
                </div>
              )}
            </div>
            {footerReserve > 0 ? (
              <footer className="footer-bar player-footer">
                <span>{fileName || "No file loaded"}</span>
                {isDebugVisible ? (
                  <span className="small">
                    score {snapshot.dreamScore}
                    {" · "}
                    {sourceKind}
                    {" · "}
                    {Math.round(snapshot.horizontalLetterboxPx * 100) / 100}px side bars
                  </span>
                ) : null}
              </footer>
            ) : null}
          </div>
        </div>
      </section>

      {isDebugVisible ? (
        <aside className="lab-panel metrics-panel debug-drawer">
          <h2>Geometry Inspector</h2>
          <dl className="metrics-table">
            <dt>Status</dt>
            <dd className={snapshot.ok ? "good" : "danger"}>{snapshot.ok ? "ready" : snapshot.reason}</dd>
            <dt>Source</dt>
            <dd>{snapshot.sourceKind}</dd>
            <dt>Window</dt>
            <dd>{snapshot.windowInnerWidth} × {snapshot.windowInnerHeight}</dd>
            <dt>Topbar</dt>
            <dd>{snapshot.topbarHeight}px</dd>
            <dt>Shell</dt>
            <dd>{snapshot.shellWidth} × {snapshot.shellHeight}</dd>
            <dt>Viewer</dt>
            <dd>{snapshot.viewerWidth} × {snapshot.viewerHeight}</dd>
            <dt>Footer</dt>
            <dd>{snapshot.footerHeight}px</dd>
            <dt>Video intrinsic</dt>
            <dd>{snapshot.videoIntrinsicWidth} × {snapshot.videoIntrinsicHeight}</dd>
            <dt>Displayed</dt>
            <dd>{snapshot.displayedWidth} × {snapshot.displayedHeight}</dd>
            <dt>Horizontal letterbox</dt>
            <dd className={snapshot.horizontalLetterboxPx > 4 ? "danger" : "good"}>{snapshot.horizontalLetterboxPx}px</dd>
            <dt>Vertical letterbox</dt>
            <dd>{snapshot.verticalLetterboxPx}px</dd>
            <dt>Natural AR</dt>
            <dd>{snapshot.naturalAspectRatio}</dd>
            <dt>Viewer AR</dt>
            <dd>{snapshot.viewerAspectRatio}</dd>
            <dt>Aspect error</dt>
            <dd>{snapshot.aspectError}</dd>
            <dt>DPR</dt>
            <dd>{snapshot.devicePixelRatio}</dd>
            <dt>Dream score</dt>
            <dd className={snapshot.dreamScore >= 80 ? "good" : snapshot.dreamScore >= 60 ? "" : "danger"}>
              {snapshot.dreamScore}/100
            </dd>
            <dt>Viewer dominance</dt>
            <dd>{snapshot.viewerDominanceRatio}</dd>
            <dt>Chrome ratio</dt>
            <dd>{snapshot.chromeRatio}</dd>
          </dl>

          <div className="metrics-block">
            <h2>Suggested Shell</h2>
            <dl className="metrics-table">
              <dt>Suggested width</dt>
              <dd>{snapshot.suggestedShellWidth}</dd>
              <dt>Suggested height</dt>
              <dd>{snapshot.suggestedShellHeight}</dd>
            </dl>
          </div>

          <div className="metrics-block">
            <h2>Lab Controls</h2>
            <div className="player-controls">
              <select className="pill" value={variant} onChange={(event) => setVariant(event.target.value as ShellVariant)}>
                <option value="fixed-footer">fixed footer shell</option>
                <option value="flex-footer">flex remainder shell</option>
              </select>
              <button className="pill" type="button" onClick={() => window.vetkaPlayerLab?.print()}>
                print snapshot
              </button>
              <select
                className="pill"
                value={previewQuality}
                onChange={(event) => setPreviewQuality(event.target.value as PreviewQualityKey)}
              >
                {PREVIEW_QUALITY_OPTIONS.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.label} preview
                  </option>
                ))}
              </select>
              <button className="pill" type="button" onClick={() => setShellSizeOverride(null)}>
                reset shell
              </button>
            </div>
            <div className="player-controls metrics-row">
              <label className="metric-pill">
                synthetic width
                <input
                  type="number"
                  min={1}
                  value={syntheticSize.width || ""}
                  onChange={(event) =>
                    setSyntheticSize((prev) => ({
                      ...prev,
                      width: Number(event.target.value || 0),
                    }))
                  }
                />
              </label>
              <label className="metric-pill">
                synthetic height
                <input
                  type="number"
                  min={1}
                  value={syntheticSize.height || ""}
                  onChange={(event) =>
                    setSyntheticSize((prev) => ({
                      ...prev,
                      height: Number(event.target.value || 0),
                    }))
                  }
                />
              </label>
              <button
                className="pill"
                type="button"
                onClick={() => {
                  setSrc("");
                  setFileName("Synthetic probe");
                  setNaturalSize({ width: 0, height: 0 });
                  autoSizedKeyRef.current = "";
                }}
              >
                synthetic mode
              </button>
            </div>
          </div>
        </aside>
      ) : null}
    </main>
  );
}

export default App;
