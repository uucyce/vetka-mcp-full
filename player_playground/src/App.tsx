import { useEffect, useMemo, useRef, useState } from "react";
import {
  computeDreamScore,
  computeDisplayedBox,
  GeometrySnapshot,
  LAB_FOOTER_HEIGHT,
  ShellVariant,
  suggestShellSize,
} from "./lib/geometry";
import { configurePlayerWindow, isTauriRuntimeSync, toggleFullscreen } from "./lib/nativeWindow";
import MycoProbeApp from "./MycoProbeApp";

type PreviewQualityKey = "full" | "half" | "quarter" | "eighth" | "sixteenth" | "thirtysecond";
type PlayerMediaKind = "video" | "image" | null;

const PREVIEW_QUALITY_OPTIONS: { key: PreviewQualityKey; label: string; scale: number }[] = [
  { key: "full", label: "1x", scale: 1 },
  { key: "half", label: "1/2", scale: 0.5 },
  { key: "quarter", label: "1/4", scale: 0.25 },
  { key: "eighth", label: "1/8", scale: 0.125 },
  { key: "sixteenth", label: "1/16", scale: 0.0625 },
  { key: "thirtysecond", label: "1/32", scale: 0.03125 },
];

type PlayerMarkerKind = "favorite" | "comment";

type ProvisionalEventType = "vetka_logo_capture";

interface ProvisionalCaptureEvent {
  provisional_event_id: string;
  event_type: ProvisionalEventType;
  media_path: string;
  start_sec: number;
  end_sec: number;
  text: string;
  created_at: string;
  export_mode: "srt_comment";
  migration_status: "local_only" | "migrated";
  migrated_to_marker_id: string | null;
}

interface PlayerTimeMarker {
  marker_id: string;
  schema_version: "cut_time_marker_v1";
  project_id: string;
  timeline_id: string;
  media_path: string;
  kind: PlayerMarkerKind;
  start_sec: number;
  end_sec: number;
  anchor_sec: number;
  score: number;
  label: string;
  text: string;
  author: string;
  context_slice: null;
  cam_payload: null;
  chat_thread_id: null;
  comment_thread_id: null;
  source_engine: string;
  status: "active";
  created_at: string;
  updated_at: string;
}

const MARKERS_STORAGE_KEY = "vetka_player_lab_markers_v1";
const PROVISIONAL_EVENTS_STORAGE_KEY = "vetka_player_lab_provisional_events_v1";
const VETKA_STATUS_STORAGE_KEY = "vetka_player_lab_in_vetka_v1";

declare global {
  interface Window {
    vetkaPlayerLab?: {
      snapshot: () => GeometrySnapshot;
      print: () => GeometrySnapshot;
      markers: () => PlayerTimeMarker[];
      provisionalEvents: () => ProvisionalCaptureEvent[];
      setVariant: (variant: ShellVariant) => void;
      setSyntheticSize: (width: number, height: number) => void;
      setPreviewQuality: (quality: PreviewQualityKey) => void;
      setInVetka: (next: boolean) => void;
      addMomentMarker: (kind?: PlayerMarkerKind, text?: string) => PlayerTimeMarker | null;
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
    mode: params.get("mode") || "player",
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

function formatOverlayTitle(value: string) {
  if (!value) return "VETKA Player";
  if (value.length <= 34) return value;
  const dotIndex = value.lastIndexOf(".");
  const extension = dotIndex > 0 ? value.slice(dotIndex) : "";
  const head = value.slice(0, 12);
  const tail = extension ? value.slice(Math.max(dotIndex - 8, 12)) : value.slice(-12);
  return `${head}…${tail}`;
}

function formatTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const total = Math.floor(seconds);
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function getSeekStep(seconds: number) {
  if (!Number.isFinite(seconds) || seconds <= 0) return 0.1;
  return Math.max(0.1, Number((seconds / 100).toFixed(2)));
}

function inferMediaKind(fileName: string, mimeType = ""): PlayerMediaKind {
  const lowerMime = mimeType.toLowerCase();
  if (lowerMime.startsWith("video/")) return "video";
  if (lowerMime.startsWith("image/")) return "image";

  const lowerName = fileName.toLowerCase();
  if (/\.(png|jpe?g|webp|gif|bmp|tiff?|avif|heic|heif)$/.test(lowerName)) return "image";
  if (/\.(mp4|mov|m4v|webm|avi|mkv|mpeg|mpg|wmv)$/.test(lowerName)) return "video";
  return null;
}

function getAvailableScreenBounds() {
  const availWidth = Math.max(
    360,
    Math.floor(
      window.screen?.availWidth ||
        window.screen?.width ||
        window.innerWidth ||
        360,
    ),
  );
  const availHeight = Math.max(
    240,
    Math.floor(
      window.screen?.availHeight ||
        window.screen?.height ||
        window.innerHeight ||
        240,
    ),
  );

  return { availWidth, availHeight };
}

function createMarkerId() {
  return `marker_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function readStoredMarkers(): PlayerTimeMarker[] {
  try {
    const raw = localStorage.getItem(MARKERS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function readStoredProvisionalEvents(): ProvisionalCaptureEvent[] {
  try {
    const raw = localStorage.getItem(PROVISIONAL_EVENTS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function readStoredVetkaStatusMap(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(VETKA_STATUS_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
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

function App() {
  const initialQuery = useMemo(readQuery, []);
  if (initialQuery.mode === "myco") {
    return <MycoProbeApp />;
  }
  const [variant, setVariant] = useState<ShellVariant>(initialQuery.variant);
  const [src, setSrc] = useState<string>(initialQuery.src);
  const [fileName, setFileName] = useState<string>(formatName(initialQuery.src));
  const [mediaKind, setMediaKind] = useState<PlayerMediaKind>(
    initialQuery.src ? inferMediaKind(initialQuery.src) : null,
  );
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
  const [vetkaStatusMap, setVetkaStatusMap] = useState<Record<string, boolean>>(readStoredVetkaStatusMap);
  const [markers, setMarkers] = useState<PlayerTimeMarker[]>(readStoredMarkers);
  const [provisionalEvents, setProvisionalEvents] = useState<ProvisionalCaptureEvent[]>(readStoredProvisionalEvents);
  const [contextToast, setContextToast] = useState("");
  const viewerRef = useRef<HTMLDivElement | null>(null);
  const shellRef = useRef<HTMLDivElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const topbarRef = useRef<HTMLElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const autoSizedKeyRef = useRef("");
  const transportTimerRef = useRef<number | null>(null);
  const firstFramePrimedRef = useRef(false);
  const intrinsicSize = naturalSize.width > 0 && naturalSize.height > 0 ? naturalSize : syntheticSize;
  const sourceKind: GeometrySnapshot["sourceKind"] =
    naturalSize.width > 0 && naturalSize.height > 0
      ? mediaKind === "image"
        ? "image"
        : "video"
      : "synthetic";
  const footerReserve = sourceKind !== "synthetic" && !isDebugVisible ? 0 : LAB_FOOTER_HEIGHT;
  const isPureMode = !isDebugVisible;
  const previewQualityOption = PREVIEW_QUALITY_OPTIONS.find((option) => option.key === previewQuality) || PREVIEW_QUALITY_OPTIONS[0];
  const effectivePreviewScale = sourceKind === "video" ? previewQualityOption.scale : 1;
  const currentMediaKey = src && !src.startsWith("blob:") ? src : fileName;
  const overlayTitle = formatOverlayTitle(fileName);
  const isInVetka = Boolean(currentMediaKey && vetkaStatusMap[currentMediaKey]);
  const mediaMarkers = useMemo(
    () => markers.filter((marker) => marker.media_path === currentMediaKey),
    [currentMediaKey, markers],
  );
  const mediaProvisionalEvents = useMemo(
    () => provisionalEvents.filter((event) => event.media_path === currentMediaKey),
    [currentMediaKey, provisionalEvents],
  );
  const favoriteMomentCount = useMemo(
    () => mediaMarkers.filter((marker) => marker.kind === "favorite").length,
    [mediaMarkers],
  );
  const commentMomentCount = useMemo(
    () => mediaMarkers.filter((marker) => marker.kind === "comment").length,
    [mediaMarkers],
  );

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
    const availableScreen = isTauriRuntimeSync()
      ? getAvailableScreenBounds()
      : {
          availWidth: Math.max(360, Math.floor(window.innerWidth || 360)),
          availHeight: Math.max(240, Math.floor(window.innerHeight || 240)),
        };
    const suggested = suggestShellSize(
      intrinsicSize.width,
      intrinsicSize.height,
      footerReserve,
      Math.floor(availableScreen.availWidth * 0.92),
      Math.floor(availableScreen.availHeight * 0.92),
      isPureMode ? 0 : 2,
      isPureMode ? 0 : 2,
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
      inVetka: isInVetka,
      markerCount: mediaMarkers.length,
      provisionalEventCount: mediaProvisionalEvents.length,
      favoriteMomentCount,
      commentMomentCount,
      activeContextAction: isInVetka ? "favorite" : "vetka",
    };
  }, [
    commentMomentCount,
    effectivePreviewScale,
    fileName,
    favoriteMomentCount,
    geometryTick,
    isInVetka,
    intrinsicSize.height,
    intrinsicSize.width,
    footerReserve,
    mediaMarkers.length,
    mediaProvisionalEvents.length,
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
    try {
      localStorage.setItem(MARKERS_STORAGE_KEY, JSON.stringify(markers));
    } catch {
      // ignore storage errors
    }
  }, [markers]);

  useEffect(() => {
    try {
      localStorage.setItem(PROVISIONAL_EVENTS_STORAGE_KEY, JSON.stringify(provisionalEvents));
    } catch {
      // ignore storage errors
    }
  }, [provisionalEvents]);

  useEffect(() => {
    try {
      localStorage.setItem(VETKA_STATUS_STORAGE_KEY, JSON.stringify(vetkaStatusMap));
    } catch {
      // ignore storage errors
    }
  }, [vetkaStatusMap]);

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
    void configurePlayerWindow(next.width, next.height, snapshot.videoIntrinsicWidth, snapshot.videoIntrinsicHeight);
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
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "f") {
        event.preventDefault();
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
        const step = getSeekStep(duration || videoRef.current.duration || 0);
        videoRef.current.currentTime = Math.max(0, videoRef.current.currentTime - step);
      }
      if (event.key === "ArrowRight" && videoRef.current) {
        event.preventDefault();
        const step = getSeekStep(duration || videoRef.current.duration || 0);
        videoRef.current.currentTime = Math.min(duration || videoRef.current.duration || 0, videoRef.current.currentTime + step);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [duration, previewQuality]);

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
    if (!contextToast) return;
    const timer = window.setTimeout(() => setContextToast(""), 2200);
    return () => window.clearTimeout(timer);
  }, [contextToast]);

  useEffect(() => {
    const api = {
      snapshot: () => snapshot,
      print: () => {
        console.info("MARKER_168.VIDEOPLAYER.LAB.SNAPSHOT", snapshot);
        return snapshot;
      },
      markers: () => markers,
      provisionalEvents: () => provisionalEvents,
      setVariant: (next: ShellVariant) => setVariant(next),
      setSyntheticSize: (width: number, height: number) => {
        setSyntheticSize({
          width: Math.max(0, Math.floor(width)),
          height: Math.max(0, Math.floor(height)),
        });
        setNaturalSize({ width: 0, height: 0 });
        setMediaKind(null);
        setSrc("");
        setFileName("Synthetic probe");
        autoSizedKeyRef.current = "";
      },
      setPreviewQuality: (quality: PreviewQualityKey) => setPreviewQuality(quality),
      setInVetka: (next: boolean) => {
        if (!currentMediaKey) return;
        setVetkaStatusMap((prev) => ({ ...prev, [currentMediaKey]: next }));
      },
      addMomentMarker: (kind: PlayerMarkerKind = "favorite", text = "") => addMomentMarker(kind, text),
      applySuggestedShell: () => {
        const next = {
          width: snapshot.suggestedShellWidth,
          height: snapshot.suggestedShellHeight,
        };
        setShellSizeOverride(next);
        void configurePlayerWindow(next.width, next.height, snapshot.videoIntrinsicWidth, snapshot.videoIntrinsicHeight);
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
  }, [currentMediaKey, markers, provisionalEvents, snapshot]);

  function attachFile(file: File) {
    const nextUrl = URL.createObjectURL(file);
    setSrc((prev) => {
      if (prev.startsWith("blob:")) URL.revokeObjectURL(prev);
      return nextUrl;
    });
    setMediaKind(inferMediaKind(file.name, file.type));
    setFileName(file.name);
    setNaturalSize({ width: 0, height: 0 });
    setCurrentTime(0);
    setDuration(0);
    setIsPlaying(false);
    firstFramePrimedRef.current = false;
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
      if (video.currentTime > 0 && video.currentTime < 0.05) {
        video.currentTime = 0;
      }
      void video.play();
    } else {
      video.pause();
    }
  }

  function seekBy(direction: -1 | 1) {
    const video = videoRef.current;
    if (!video) return;
    const limit = duration || video.duration || 0;
    const step = getSeekStep(limit);
    video.currentTime = Math.min(limit, Math.max(0, video.currentTime + direction * step));
    setShowTransport(true);
  }

  function buildMarker(kind: PlayerMarkerKind, text = ""): PlayerTimeMarker | null {
    if (!currentMediaKey) return null;
    const anchor = Math.max(0, Number(videoRef.current?.currentTime ?? currentTime ?? 0));
    const start = Math.max(0, Number((anchor - 0.5).toFixed(2)));
    const end = Number((anchor + 0.5).toFixed(2));
    const now = new Date().toISOString();
    return {
      marker_id: createMarkerId(),
      schema_version: "cut_time_marker_v1",
      project_id: "cut_demo",
      timeline_id: "main",
      media_path: currentMediaKey,
      kind,
      start_sec: start,
      end_sec: end,
      anchor_sec: Number(anchor.toFixed(2)),
      score: kind === "favorite" ? 0.85 : 0.6,
      label: kind === "favorite" ? "Starred moment" : "Comment moment",
      text,
      author: "player_lab",
      context_slice: null,
      cam_payload: null,
      chat_thread_id: null,
      comment_thread_id: null,
      source_engine: "player_lab",
      status: "active",
      created_at: now,
      updated_at: now,
    };
  }

  function addMomentMarker(kind: PlayerMarkerKind, text = "") {
    const marker = buildMarker(kind, text);
    if (!marker) return null;
    setMarkers((prev) => [...prev, marker]);
    return marker;
  }

  function addProvisionalVetkaCapture() {
    if (!currentMediaKey) return null;
    const anchor = Math.max(0, Number(videoRef.current?.currentTime ?? currentTime ?? 0));
    const start = Math.max(0, Number((anchor - 0.5).toFixed(2)));
    const end = Number((anchor + 0.5).toFixed(2));
    const event: ProvisionalCaptureEvent = {
      provisional_event_id: createMarkerId(),
      event_type: "vetka_logo_capture",
      media_path: currentMediaKey,
      start_sec: start,
      end_sec: end,
      text: "Moment registered locally. Connect VETKA Core/CUT for full workflow.",
      created_at: new Date().toISOString(),
      export_mode: "srt_comment",
      migration_status: "local_only",
      migrated_to_marker_id: null,
    };
    setProvisionalEvents((prev) => [...prev, event]);
    return event;
  }

  function handleContextAction() {
    if (!isInVetka) {
      const event = addProvisionalVetkaCapture();
      if (event) {
        setContextToast("Moment registered locally. VETKA Core/CUT is needed for full workflow.");
      }
      return;
    }
    addMomentMarker("favorite");
    setContextToast("Moment saved as a favorite marker.");
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
                  accept="video/*,image/*"
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
            accept="video/*,image/*"
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
            style={shellSizeOverride && !isPureMode ? { width: `${shellSizeOverride.width}px`, height: `${shellSizeOverride.height}px` } : undefined}
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
                      {mediaKind === "image" ? (
                        <img
                          ref={imageRef}
                          className="viewer-video viewer-image"
                          src={src}
                          alt={fileName || "Image preview"}
                          draggable={false}
                          onLoad={(event) => {
                            const image = event.currentTarget;
                            setNaturalSize({
                              width: Number(image.naturalWidth || 0),
                              height: Number(image.naturalHeight || 0),
                            });
                            setCurrentTime(0);
                            setDuration(0);
                            setIsPlaying(false);
                            if (!fileName) setFileName(formatName(src));
                          }}
                        />
                      ) : (
                        <video
                          ref={videoRef}
                          className="viewer-video"
                          src={src}
                          controls={false}
                          playsInline
                          preload="auto"
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
                          onLoadedData={(event) => {
                            const video = event.currentTarget;
                            if (firstFramePrimedRef.current) return;
                            firstFramePrimedRef.current = true;
                            if (video.paused && Number(video.currentTime || 0) === 0 && Number(video.duration || 0) > 0) {
                              const epsilon = Math.min(0.033, Math.max(0.001, Number(video.duration || 0) / 1000));
                              try {
                                video.currentTime = epsilon;
                              } catch {
                                // ignore seek priming failures
                              }
                            }
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
                      )}
                    </div>
                  </div>
                  <div className={`media-label ${showTransport ? "media-label-visible" : "media-label-hidden"}`}>
                    <strong title={fileName}>{overlayTitle}</strong>
                  </div>
                  <div className={`viewer-toolbar ${showTransport ? "viewer-toolbar-visible" : "viewer-toolbar-hidden"}`}>
                    <button
                      className={`icon-button ${isInVetka ? "icon-button-active" : "icon-button-vetka"}`}
                      type="button"
                      onClick={() => handleContextAction()}
                      data-testid="context-action"
                      aria-label={isInVetka ? "Favorite this moment" : "Add to VETKA"}
                      title={isInVetka ? `Favorite this moment (${favoriteMomentCount})` : "Add to VETKA"}
                    >
                      {isInVetka ? <IconStar active={true} /> : <IconVetka />}
                    </button>
                  </div>
                  {contextToast ? <div className="context-toast">{contextToast}</div> : null}
                  {mediaKind === "video" ? (
                    <>
                      <div
                        className={`transport-overlay ${showTransport ? "transport-visible" : "transport-hidden"}`}
                        onMouseMove={() => setShowTransport(true)}
                        onMouseLeave={() => {
                          if (isPlaying && !isDebugVisible) setShowTransport(false);
                        }}
                      >
                        <div className="transport-scrim" />
                        <div className="transport-bar">
                          <button className="transport-button transport-button-primary" type="button" onClick={() => togglePlayback()} aria-label={isPlaying ? "Pause" : "Play"}>
                            {isPlaying ? <IconPause /> : <IconPlay />}
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
                          <button className="transport-button" type="button" onClick={() => void toggleFullscreen()} aria-label="Fullscreen" data-testid="fullscreen-button">
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
                      <button
                        className="seek-zone seek-zone-left"
                        type="button"
                        aria-label="Seek backward"
                        onClick={() => seekBy(-1)}
                      />
                      <button
                        className="seek-zone seek-zone-right"
                        type="button"
                        aria-label="Seek forward"
                        onClick={() => seekBy(1)}
                      />
                    </>
                  ) : null}
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
                    <strong>Drop media here</strong>
                    <p className="dropzone-copy">
                      This shell auto-fits to video and images once dimensions are known.
                    </p>
                    <button className="dropzone-open" type="button" onClick={() => fileInputRef.current?.click()}>
                      Open media
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
            <dt>In VETKA</dt>
            <dd>{snapshot.inVetka ? "yes" : "no"}</dd>
            <dt>Context action</dt>
            <dd>{snapshot.activeContextAction}</dd>
            <dt>Markers</dt>
            <dd>{snapshot.markerCount}</dd>
            <dt>Favorite moments</dt>
            <dd>{snapshot.favoriteMomentCount}</dd>
            <dt>Comment moments</dt>
            <dd>{snapshot.commentMomentCount}</dd>
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
