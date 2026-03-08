export interface DetachedMediaDebugSnapshot {
  ok: boolean;
  reason?: string;
  src: string;
  path: string;
  devicePixelRatio: number;
  windowInnerWidth: number;
  windowInnerHeight: number;
  wrapperWidth: number;
  wrapperHeight: number;
  toolbarWidth: number;
  toolbarHeight: number;
  videoIntrinsicWidth: number;
  videoIntrinsicHeight: number;
  displayedWidth: number;
  displayedHeight: number;
  horizontalLetterboxPx: number;
  verticalLetterboxPx: number;
  expectedAspectRatio: number;
  wrapperAspectRatio: number;
  aspectError: number;
  nativeScaleFactor: number;
  nativeInnerPhysicalWidth: number;
  nativeInnerPhysicalHeight: number;
  nativeInnerLogicalWidth: number;
  nativeInnerLogicalHeight: number;
  nativeOuterPhysicalWidth: number;
  nativeOuterPhysicalHeight: number;
  capturedAt: string;
}

export interface DetachedMediaDebugAssertion extends DetachedMediaDebugSnapshot {
  pass: boolean;
  thresholdPx: number;
}

export interface DetachedMediaDebugApi {
  snapshot: () => DetachedMediaDebugSnapshot;
  assertNoSideLetterbox: (thresholdPx?: number) => DetachedMediaDebugAssertion;
  print: () => DetachedMediaDebugSnapshot;
  save: () => DetachedMediaDebugSnapshot;
  publish: () => Promise<DetachedMediaDebugSnapshot>;
}

declare global {
  interface Window {
    __VETKA_MEDIA_DEBUG__?: DetachedMediaDebugApi;
    debugMedia?: DetachedMediaDebugApi;
  }
}

const STORAGE_KEY = 'vetka_detached_media_debug_last';
const NATIVE_STORAGE_KEY = 'vetka_detached_media_native_geometry_last';

function readNativeGeometry(): {
  nativeScaleFactor: number;
  nativeInnerPhysicalWidth: number;
  nativeInnerPhysicalHeight: number;
  nativeInnerLogicalWidth: number;
  nativeInnerLogicalHeight: number;
  nativeOuterPhysicalWidth: number;
  nativeOuterPhysicalHeight: number;
} {
  try {
    const raw = localStorage.getItem(NATIVE_STORAGE_KEY);
    if (!raw) throw new Error('missing');
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    return {
      nativeScaleFactor: Number(parsed.scale_factor || 0),
      nativeInnerPhysicalWidth: Number(parsed.inner_physical_width || 0),
      nativeInnerPhysicalHeight: Number(parsed.inner_physical_height || 0),
      nativeInnerLogicalWidth: Number(parsed.inner_logical_width || 0),
      nativeInnerLogicalHeight: Number(parsed.inner_logical_height || 0),
      nativeOuterPhysicalWidth: Number(parsed.outer_physical_width || 0),
      nativeOuterPhysicalHeight: Number(parsed.outer_physical_height || 0),
    };
  } catch {
    return {
      nativeScaleFactor: 0,
      nativeInnerPhysicalWidth: 0,
      nativeInnerPhysicalHeight: 0,
      nativeInnerLogicalWidth: 0,
      nativeInnerLogicalHeight: 0,
      nativeOuterPhysicalWidth: 0,
      nativeOuterPhysicalHeight: 0,
    };
  }
}

function emptySnapshot(src: string, path: string, reason: string): DetachedMediaDebugSnapshot {
  return {
    ok: false,
    reason,
    src,
    path,
    devicePixelRatio: Number(window.devicePixelRatio || 1),
    windowInnerWidth: Number(window.innerWidth || 0),
    windowInnerHeight: Number(window.innerHeight || 0),
    wrapperWidth: 0,
    wrapperHeight: 0,
    toolbarWidth: 0,
    toolbarHeight: 0,
    videoIntrinsicWidth: 0,
    videoIntrinsicHeight: 0,
    displayedWidth: 0,
    displayedHeight: 0,
    horizontalLetterboxPx: 0,
    verticalLetterboxPx: 0,
    expectedAspectRatio: 0,
    wrapperAspectRatio: 0,
    aspectError: 0,
    ...readNativeGeometry(),
    capturedAt: new Date().toISOString(),
  };
}

export function createDetachedMediaDebugApi(params: {
  path: string;
  name: string;
}): DetachedMediaDebugApi {
  const srcLabel = params.name || params.path.split('/').pop() || 'media';

  const snapshot = (): DetachedMediaDebugSnapshot => {
    const video = document.querySelector('video') as HTMLVideoElement | null;
    const wrapper = (document.querySelector('[data-vetka-media-wrapper="1"]') as HTMLDivElement | null)
      || (video?.parentElement as HTMLDivElement | null)
      || null;
    const toolbar = document.querySelector('[data-artifact-toolbar="1"]') as HTMLDivElement | null;

    if (!video) return emptySnapshot(srcLabel, params.path, 'video_missing');
    if (!wrapper) return emptySnapshot(srcLabel, params.path, 'wrapper_missing');

    const wrapperRect = wrapper.getBoundingClientRect();
    const toolbarRect = toolbar?.getBoundingClientRect();
    const naturalWidth = Math.max(0, Number(video.videoWidth || 0));
    const naturalHeight = Math.max(0, Number(video.videoHeight || 0));

    if (naturalWidth <= 0 || naturalHeight <= 0) {
      return emptySnapshot(srcLabel, params.path, 'video_metadata_unavailable');
    }

    const scale = Math.min(
      wrapperRect.width / Math.max(1, naturalWidth),
      wrapperRect.height / Math.max(1, naturalHeight),
    );
    const displayedWidth = Number((naturalWidth * scale).toFixed(2));
    const displayedHeight = Number((naturalHeight * scale).toFixed(2));
    const expectedAspectRatio = Number((naturalWidth / naturalHeight).toFixed(6));
    const wrapperAspectRatio = Number((wrapperRect.width / Math.max(1, wrapperRect.height)).toFixed(6));
    const nativeGeometry = readNativeGeometry();

    return {
      ok: true,
      src: srcLabel,
      path: params.path,
      devicePixelRatio: Number(window.devicePixelRatio || 1),
      windowInnerWidth: Number(window.innerWidth || 0),
      windowInnerHeight: Number(window.innerHeight || 0),
      wrapperWidth: Number(wrapperRect.width.toFixed(2)),
      wrapperHeight: Number(wrapperRect.height.toFixed(2)),
      toolbarWidth: Number((toolbarRect?.width || 0).toFixed(2)),
      toolbarHeight: Number((toolbarRect?.height || 0).toFixed(2)),
      videoIntrinsicWidth: naturalWidth,
      videoIntrinsicHeight: naturalHeight,
      displayedWidth,
      displayedHeight,
      horizontalLetterboxPx: Number(Math.max(0, (wrapperRect.width - displayedWidth) / 2).toFixed(2)),
      verticalLetterboxPx: Number(Math.max(0, (wrapperRect.height - displayedHeight) / 2).toFixed(2)),
      expectedAspectRatio,
      wrapperAspectRatio,
      aspectError: Number(Math.abs(wrapperAspectRatio - expectedAspectRatio).toFixed(6)),
      ...nativeGeometry,
      capturedAt: new Date().toISOString(),
    };
  };

  const assertNoSideLetterbox = (thresholdPx: number = 4): DetachedMediaDebugAssertion => {
    const base = snapshot();
    return {
      ...base,
      thresholdPx,
      pass: Boolean(base.ok && base.horizontalLetterboxPx <= thresholdPx),
    };
  };

  const print = (): DetachedMediaDebugSnapshot => {
    const data = snapshot();
    console.info('MARKER_159.R15.DETACHED_MEDIA_DEBUG_SNAPSHOT', data);
    return data;
  };

  const save = (): DetachedMediaDebugSnapshot => {
    const data = snapshot();
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch {
      // ignore storage errors
    }
    return data;
  };

  const publish = async (): Promise<DetachedMediaDebugSnapshot> => {
    const data = save();
    try {
      await fetch('/api/debug/media-window-snapshot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    } catch {
      // ignore debug publish failures
    }
    return data;
  };

  return {
    snapshot,
    assertNoSideLetterbox,
    print,
    save,
    publish,
  };
}

export function installDetachedMediaDebug(params: {
  path: string;
  name: string;
}): () => void {
  const api = createDetachedMediaDebugApi(params);
  window.__VETKA_MEDIA_DEBUG__ = api;
  window.debugMedia = api;

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(api.snapshot()));
  } catch {
    // ignore storage errors
  }

  return () => {
    if (window.__VETKA_MEDIA_DEBUG__ === api) {
      delete window.__VETKA_MEDIA_DEBUG__;
    }
    if (window.debugMedia === api) {
      delete window.debugMedia;
    }
  };
}
