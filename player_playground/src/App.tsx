import { useEffect, useMemo, useRef, useState } from "react";
import {
  computeDisplayedBox,
  GeometrySnapshot,
  LAB_FOOTER_HEIGHT,
  ShellVariant,
  suggestShellSize,
} from "./lib/geometry";

declare global {
  interface Window {
    vetkaPlayerLab?: {
      snapshot: () => GeometrySnapshot;
      print: () => GeometrySnapshot;
      setVariant: (variant: ShellVariant) => void;
      setSyntheticSize: (width: number, height: number) => void;
      applySuggestedShell: () => GeometrySnapshot;
      resetShell: () => void;
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
  };
}

function App() {
  const initialQuery = useMemo(readQuery, []);
  const [variant, setVariant] = useState<ShellVariant>(initialQuery.variant);
  const [src, setSrc] = useState<string>(initialQuery.src);
  const [fileName, setFileName] = useState<string>("");
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
  const [syntheticSize, setSyntheticSize] = useState({
    width: initialQuery.mockWidth,
    height: initialQuery.mockHeight,
  });
  const [shellSizeOverride, setShellSizeOverride] = useState<{
    width: number;
    height: number;
  } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [geometryTick, setGeometryTick] = useState(0);
  const viewerRef = useRef<HTMLDivElement | null>(null);
  const shellRef = useRef<HTMLDivElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const intrinsicSize = naturalSize.width > 0 && naturalSize.height > 0 ? naturalSize : syntheticSize;
  const sourceKind: GeometrySnapshot["sourceKind"] = naturalSize.width > 0 && naturalSize.height > 0
    ? "video"
    : "synthetic";

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

  const snapshot = useMemo<GeometrySnapshot>(() => {
    const viewerRect = viewerRef.current?.getBoundingClientRect();
    const shellRect = shellRef.current?.getBoundingClientRect();
    const viewerWidth = Number(viewerRect?.width || 0);
    const viewerHeight = Number(viewerRect?.height || 0);
    const shellWidth = Number(shellRect?.width || 0);
    const shellHeight = Number(shellRect?.height || 0);
    const displayed = computeDisplayedBox(
      viewerWidth,
      viewerHeight,
      intrinsicSize.width,
      intrinsicSize.height,
    );
    const suggested = suggestShellSize(
      intrinsicSize.width,
      intrinsicSize.height,
      LAB_FOOTER_HEIGHT,
      Math.floor(window.innerWidth * 0.92),
      Math.floor(window.innerHeight * 0.92),
    );

    return {
      ok: Boolean(viewerWidth > 0 && viewerHeight > 0 && intrinsicSize.width > 0 && intrinsicSize.height > 0),
      reason: intrinsicSize.width > 0 ? undefined : "video_metadata_unavailable",
      fileName: fileName || (sourceKind === "synthetic" ? "Synthetic probe" : "No file loaded"),
      devicePixelRatio: Number(window.devicePixelRatio || 1),
      windowInnerWidth: Number(window.innerWidth || 0),
      windowInnerHeight: Number(window.innerHeight || 0),
      shellWidth: Number(shellWidth.toFixed(2)),
      shellHeight: Number(shellHeight.toFixed(2)),
      viewerWidth: Number(viewerWidth.toFixed(2)),
      viewerHeight: Number(viewerHeight.toFixed(2)),
      footerHeight: LAB_FOOTER_HEIGHT,
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
    };
  }, [
    fileName,
    geometryTick,
    intrinsicSize.height,
    intrinsicSize.width,
    sourceKind,
    variant,
  ]);

  useEffect(() => {
    if (initialQuery.applySuggestedShell && snapshot.suggestedShellWidth > 0 && snapshot.suggestedShellHeight > 0) {
      setShellSizeOverride({
        width: snapshot.suggestedShellWidth,
        height: snapshot.suggestedShellHeight,
      });
    }
  }, [initialQuery.applySuggestedShell, snapshot.suggestedShellHeight, snapshot.suggestedShellWidth]);

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
      },
      applySuggestedShell: () => {
        const next = {
          width: snapshot.suggestedShellWidth,
          height: snapshot.suggestedShellHeight,
        };
        setShellSizeOverride(next);
        return { ...snapshot, shellWidth: next.width, shellHeight: next.height };
      },
      resetShell: () => setShellSizeOverride(null),
    };
    window.vetkaPlayerLab = api;
    return () => {
      if (window.vetkaPlayerLab === api) {
        delete window.vetkaPlayerLab;
      }
    };
  }, [snapshot]);

  useEffect(() => {
    try {
      localStorage.setItem("vetka_player_lab_snapshot", JSON.stringify(snapshot));
    } catch {
      // ignore storage errors
    }
  }, [snapshot]);

  function attachFile(file: File) {
    const nextUrl = URL.createObjectURL(file);
    setSrc((prev) => {
      if (prev.startsWith("blob:")) URL.revokeObjectURL(prev);
      return nextUrl;
    });
    setFileName(file.name);
    setNaturalSize({ width: 0, height: 0 });
  }

  function onDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) attachFile(file);
  }

  return (
    <main
      className="lab-shell"
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
    >
      <div className="lab-grid">
        <section className="lab-panel player-stage">
          <div className="player-header">
            <div>
              <h1 className="player-title">VETKA Video Player Lab</h1>
              <p className="player-subtitle">
                MARKER_168.VIDEOPLAYER.LAB.SHELL
                {" · "}
                web-first sandbox for geometry, shell contract, and editor-grade playback ergonomics
              </p>
            </div>
            <div className="player-controls">
              <label className="pill">
                Open file
                <input
                  type="file"
                  accept="video/*"
                  style={{ display: "none" }}
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) attachFile(file);
                  }}
                />
              </label>
              <select
                className="pill"
                value={variant}
                onChange={(event) => setVariant(event.target.value as ShellVariant)}
              >
                <option value="fixed-footer">fixed footer shell</option>
                <option value="flex-footer">flex remainder shell</option>
              </select>
              <button className="pill" type="button" onClick={() => window.vetkaPlayerLab?.print()}>
                print snapshot
              </button>
              <button
                className="pill"
                type="button"
                onClick={() => window.vetkaPlayerLab?.applySuggestedShell()}
              >
                apply suggested shell
              </button>
            </div>
          </div>

          <div className="player-controls" style={{ marginBottom: 14 }}>
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
                setFileName("");
                setNaturalSize({ width: 0, height: 0 });
              }}
            >
              synthetic mode
            </button>
            <button className="pill" type="button" onClick={() => setShellSizeOverride(null)}>
              reset shell size
            </button>
          </div>

          <div
            ref={shellRef}
            className={`viewer-shell ${variant}`}
            style={shellSizeOverride ? {
              width: `${shellSizeOverride.width}px`,
              height: `${shellSizeOverride.height}px`,
            } : undefined}
          >
            <div ref={viewerRef} className="viewer-area">
              {src ? (
                <video
                  ref={videoRef}
                  className="viewer-video"
                  src={src}
                  controls
                  playsInline
                  preload="metadata"
                  onLoadedMetadata={(event) => {
                    const video = event.currentTarget;
                    setNaturalSize({
                      width: Number(video.videoWidth || 0),
                      height: Number(video.videoHeight || 0),
                    });
                    if (!fileName) {
                      const tail = src.split("/").pop() || "video";
                      setFileName(tail);
                    }
                  }}
                />
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
                <div className="dropzone" style={{ outline: isDragging ? "2px solid #58beff" : "none" }}>
                  <div>
                    <strong>Drop a video here</strong>
                    Drag a local file into the lab or use the file picker above.
                    <div className="small" style={{ marginTop: 12 }}>
                      This sandbox exists to prove shell geometry before we re-import it into VETKA.
                    </div>
                  </div>
                </div>
              )}
            </div>
            <footer className="footer-bar">
              <span>{fileName || (sourceKind === "synthetic" ? "Synthetic probe" : "No file loaded")}</span>
              <span className="small">
                {variant}
                {" · "}
                {sourceKind}
              </span>
            </footer>
          </div>
        </section>

        <aside className="lab-panel metrics-panel">
          <h2>Geometry Inspector</h2>
          <dl className="metrics-table">
            <dt>Status</dt>
            <dd className={snapshot.ok ? "good" : "danger"}>{snapshot.ok ? "ready" : snapshot.reason}</dd>
            <dt>Source</dt>
            <dd>{snapshot.sourceKind}</dd>
            <dt>Window</dt>
            <dd>{snapshot.windowInnerWidth} × {snapshot.windowInnerHeight}</dd>
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
          </dl>

          <div className="metrics-block">
            <h2>Suggested Shell</h2>
            <dl className="metrics-table">
              <dt>Suggested width</dt>
              <dd>{snapshot.suggestedShellWidth}</dd>
              <dt>Suggested height</dt>
              <dd>{snapshot.suggestedShellHeight}</dd>
            </dl>
            <p className="small">
              This is the shell size the lab would request for a metadata-first detached window.
            </p>
          </div>

          <div className="metrics-block">
            <h2>Console API</h2>
            <p className="small">
              Use <code>window.vetkaPlayerLab.print()</code>,{" "}
              <code>window.vetkaPlayerLab.snapshot()</code>,{" "}
              <code>window.vetkaPlayerLab.setVariant("fixed-footer")</code>.
            </p>
          </div>
        </aside>
      </div>
    </main>
  );
}

export default App;
