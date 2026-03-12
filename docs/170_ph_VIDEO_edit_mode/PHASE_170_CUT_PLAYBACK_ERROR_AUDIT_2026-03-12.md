# Phase 170 — Playback Error Path Audit (A1)

> **Task:** tb_1773300000_201
> **Owner:** Opus
> **Date:** 2026-03-12

## Media Error Points Map

### 1. VideoPreview.tsx — HTML5 `<video>` element
| Error Point | Current Behavior | Required Behavior |
|-------------|-----------------|-------------------|
| `<video>` network error (404) | Silent black frame | Error overlay with message |
| `<video>` decode error (bad codec) | Silent black frame | "Unsupported format" overlay |
| `<video>` src empty/null | "Select a clip" shown | OK (already handled) |
| `video.play()` rejected (no gesture) | Silently caught | OK (browser policy) |
| `video.play()` rejected (corrupt file) | Silently caught | Should show error |

### 2. Media Proxy Endpoint
- **Endpoint used:** `${API_BASE}/cut/media-proxy?sandbox_root=...&path=...`
- **Note:** Scout found NO `/api/cut/media-proxy` in backend routes!
- **Actual endpoint:** `/api/files/raw?path=...` serves files
- **Possible disconnect:** VideoPreview may be hitting a non-existent endpoint
- **Action:** Verify if `cut/media-proxy` route exists in cut_routes.py or if it's a missing endpoint

| Error | HTTP Code | Current UI | Required UI |
|-------|-----------|-----------|-------------|
| File not found | 404 | Black frame | Error overlay: "Media not found" |
| Path is directory | 400 | Black frame | Error overlay: "Invalid media path" |
| Server error | 500 | Black frame | Error overlay: "Server error" |

### 3. Poster/Thumbnail Resolution
| Error Point | Current Behavior | Fix |
|-------------|-----------------|-----|
| No thumbnail match (exact path) | No poster, black until metadata | Fuzzy path matching |
| poster_url is broken/404 | Shows nothing | poster onError fallback |

### 4. Media Switching Race Conditions
| Scenario | Current Behavior | Fix |
|----------|-----------------|-----|
| Rapid clip clicks (5 in 1 sec) | Multiple loads queued, last wins eventually | Debounce + abort previous |
| Click during load | New load starts, old continues | Cancel old load (`video.src = ''`) |
| Switch while playing | Continues playing old, switches abruptly | Pause → reset → load → optionally auto-play |

## Patterns from VideoArtifactPlayer.tsx (to reuse)

1. **`playbackFailed` state flag** + subtle overlay badge
2. **`handlePlaybackError` callback** attached to `onError`
3. **Full state reset on src change** (pause, currentTime=0, load(), clear errors)
4. **Promise-wrapped `.play()` catch** → set error state
5. **`loadedmetadata` clears error** — successful load resets failure flag

## Implementation Plan

### Store changes (useCutEditorStore.ts)
```typescript
mediaError: string | null          // null = no error
mediaLoading: boolean              // true while switching
setMediaError: (err: string | null) => void
setMediaLoading: (loading: boolean) => void
```

### VideoPreview.tsx changes
1. Add `onError` handler → `setMediaError(classifyError(event))`
2. Add loading state → show spinner during media switch
3. Add `useEffect` on `activeMediaPath` → reset state, cancel previous load
4. Add error overlay UI (subtle badge, top-left, like VideoArtifactPlayer)
5. `handleLoadedMetadata` → clear error + loading

### Error Classification
```typescript
function classifyVideoError(event: React.SyntheticEvent<HTMLVideoElement>): string {
  const video = event.currentTarget;
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
```
