# Phase 122: Agent Activity Glow — Reconnaissance Report

**Date:** 2026-02-08
**Agent:** Claude Opus 4.5 (Claude Code)
**Status:** RECON COMPLETE
**Scouts:** 4 Haiku parallel missions

---

## Goal

Add **white glow with subtle cold blue tint** to files that agents are actively working on.
Color reference: Scanner Panel progress bar (`#5c8aaa` → `#7ab3d4`).

---

## MARKER INDEX

| Marker | Topic | Location |
|--------|-------|----------|
| MARKER_122.1A-J | MGCCache System | mgc_cache.py |
| MARKER_122.2A-K | Mycelium File Operations | agent_pipeline.py, disk_artifact_service.py |
| MARKER_122.3A-E | Scanner Panel Color | ScanPanel.css |
| MARKER_122.4A-K | Three.js Glow Effects | FileCard.tsx, App.tsx |

---

## 1. MGCCache System (MARKER_122.1A-J)

### MARKER_122.1A: Location
**File:** `src/memory/mgc_cache.py:81-462`

MGCCache is a 3-tier generational cache:
- **Gen 0 (RAM):** Hot data, O(1) access, max 100 entries
- **Gen 1 (Qdrant):** Warm data, vector storage
- **Gen 2 (JSON):** Cold archive, persistent files

### MARKER_122.1B: Data Tracked
```python
class MGCEntry:
    key: str
    value: Any
    access_count: int      # Times accessed
    created_at: datetime
    last_accessed: datetime
    generation: int        # 0=RAM, 1=Qdrant, 2=JSON
    size_bytes: int
```

### MARKER_122.1C: File Access Tracking
**Current state:** MGC tracks **cache entries**, not **file paths**.
- SpiralContextGenerator uses MGC for query results caching
- ARCSolverAgent caches graph state
- No per-file tracking exists

### MARKER_122.1D: Singleton Access
```python
from src.memory.mgc_cache import get_mgc_cache
mgc = get_mgc_cache()  # Global instance
```

### MARKER_122.1E: Sync Interface (Phase 119.1)
```python
# Gen0-only for sync callers
mgc.get_sync(key)
mgc.set_sync(key, value)
```

### MARKER_122.1F: Statistics
```python
mgc.get_stats() → {
    "gen0_size": 42,
    "hits": {"gen0": 100, "gen1": 20, "gen2": 5},
    "misses": 30,
    "hit_rate": 0.81
}
```

### MARKER_122.1G-J: See full scout report for integration details

---

## 2. Mycelium File Operations (MARKER_122.2A-K)

### MARKER_122.2B: File Read Operations
| Method | Location | Logging |
|--------|----------|---------|
| `vetka_read_file` MCP | read_file_tool.py | No logging |
| `read_artifact()` | disk_artifact_service.py:277 | Error only |
| `semantic_search()` | mycelium_auditor.py:481 | Results count |

### MARKER_122.2C: File Write Operations (KEY INJECTION POINTS)

| Method | Location | Event Emitted |
|--------|----------|---------------|
| `_extract_and_write_files()` | agent_pipeline.py:951 | `chat_response` |
| `create_disk_artifact()` | disk_artifact_service.py:114 | **`artifact_approval`** |
| `ApproveArtifactTool` | artifact_tools.py:269 | **`artifact_applied`** |
| `EditArtifactTool` | artifact_tools.py:155 | `artifact_approval` |

### MARKER_122.2E: Socket.IO Events (BEST FOR GLOW)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SOCKET.IO EVENT FLOW                             │
├─────────────────────────────────────────────────────────────────────┤
│  Agent writes file                                                   │
│       │                                                              │
│       ▼                                                              │
│  disk_artifact_service.create_disk_artifact()                       │
│       │                                                              │
│       ▼                                                              │
│  socketio.emit('artifact_approval', {                               │
│      artifact_id: "art_123",                                        │
│      filename: "feature.py",                                        │
│      filepath: "/src/spawn_output/feature.py",  ◄── FILE PATH!     │
│      status: "pending"                                              │
│  })                                                                 │
│       │                                                              │
│       ▼                                                              │
│  Frontend receives → Add to glowing files set → FileCard glows     │
└─────────────────────────────────────────────────────────────────────┘
```

### MARKER_122.2H: Recommended Injection Points

| Priority | Location | Change Required |
|----------|----------|-----------------|
| **1** | disk_artifact_service.py:204 | Add `glow: true` to event |
| **2** | artifact_tools.py:287 | Add `glow: true` to event |
| **3** | activity_emitter.py:96 | Extend activity metadata |

### MARKER_122.2I: Progress Hooks (UNUSED)
```python
# agent_pipeline.py:145
self.progress_hooks: List[Any] = []  # Initialized but never populated!

# Could register glow callback:
self.progress_hooks = [emit_glow_event]
```

---

## 3. Scanner Panel Color (MARKER_122.3A-E)

### MARKER_122.3A: Exact Color Found
**File:** `client/src/components/scanner/ScanPanel.css:172-179`

```css
.scan-progress-fill {
  background: linear-gradient(90deg, #5c8aaa 0%, #7ab3d4 100%);
  box-shadow: 0 0 8px rgba(122, 179, 212, 0.3);
}
```

### MARKER_122.3B: Color Values

| Element | Hex | RGB | Description |
|---------|-----|-----|-------------|
| Gradient Start | `#5c8aaa` | rgb(92, 138, 170) | Steel blue |
| Gradient End | `#7ab3d4` | rgb(122, 179, 212) | Light cyan |
| Glow Shadow | `rgba(122, 179, 212, 0.3)` | - | 30% opacity |

### MARKER_122.3D: Design Intent
- Cold blue tint (not warm)
- Subtle glow for depth
- Professional dark UI appearance
- Non-intrusive visibility

---

## 4. Three.js Glow Effects (MARKER_122.4A-K)

### MARKER_122.4A: Current State
**NO existing glow/bloom effects in VETKA.**
All rendering uses `MeshBasicMaterial` with canvas textures.

### MARKER_122.4B: FileCard Material
```typescript
// FileCard.tsx:1011-1018
<meshBasicMaterial
  map={texture}
  transparent
  opacity={opacity}
  color={isHovered ? '#aaffaa' : undefined}
  // NO emissive property
/>
```

### MARKER_122.4C: Available Libraries
All installed but unused:
- `three@0.170.0` — UnrealBloom, ShaderPass
- `@react-three/drei@10.0.0` — Bloom, Effects
- `@react-three/fiber@9.0.0` — useThree, extend

### MARKER_122.4D: Implementation Options

| Option | Complexity | Performance | Visual Quality |
|--------|------------|-------------|----------------|
| **1. Emissive Material** | Easy (5 lines) | None | Glow within mesh |
| **2. Bloom Postprocess** | Medium (20 lines) | -10-15% | Realistic bleed |
| **3. Custom Shader** | Hard | Variable | Maximum control |

### MARKER_122.4E: Recommended Approach

**Option 1 + Optional Option 2:**

```typescript
// FileCard.tsx — Add emissive for active files
<meshStandardMaterial
  map={texture}
  transparent
  opacity={opacity}
  emissive={isAgentActive ? '#7ab3d4' : '#000000'}
  emissiveIntensity={isAgentActive ? 0.5 : 0}
/>
```

For stronger glow, add Bloom postprocessing:
```typescript
// App.tsx — Optional bloom pass
import { EffectComposer, Bloom } from '@react-three/postprocessing'

<EffectComposer>
  <Bloom
    intensity={0.3}
    luminanceThreshold={0.8}
    luminanceSmoothing={0.9}
  />
</EffectComposer>
```

### MARKER_122.4F: Files to Modify
1. `FileCard.tsx` — Add emissive property
2. `App.tsx` — Optional Bloom (if needed)
3. `useStore.ts` — Add `glowingFiles: Set<string>`

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AGENT ACTIVITY GLOW SYSTEM                       │
├─────────────────────────────────────────────────────────────────────┤
│                           BACKEND                                    │
│                                                                      │
│  Mycelium Pipeline                                                  │
│       │                                                              │
│       ├── _extract_and_write_files()                                │
│       │        │                                                     │
│       │        ▼                                                     │
│       └── create_disk_artifact()                                    │
│                │                                                     │
│                ▼                                                     │
│       socketio.emit('artifact_approval', {                          │
│           filepath: "/src/spawn_output/feature.py",                 │
│           glow: { enabled: true, duration: 5000 }  ◄── NEW         │
│       })                                                            │
├─────────────────────────────────────────────────────────────────────┤
│                           FRONTEND                                   │
│                                                                      │
│  Socket.IO Handler                                                  │
│       │                                                              │
│       ▼                                                              │
│  useStore.addGlowingFile(filepath)                                  │
│       │                                                              │
│       ▼                                                              │
│  FileCard.tsx                                                       │
│       │                                                              │
│       ├── isGlowing = glowingFiles.has(node.path)                  │
│       │                                                              │
│       └── <meshStandardMaterial                                     │
│               emissive={isGlowing ? '#7ab3d4' : '#000'}            │
│               emissiveIntensity={isGlowing ? 0.5 : 0}              │
│           />                                                        │
│                                                                      │
│  Visual Result:                                                     │
│  ┌──────────────┐                                                   │
│  │ ✨ feature.py │  ← White glow with cold blue tint               │
│  └──────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 122.1: Backend Event Enhancement
1. Modify `disk_artifact_service.py:204` — add `glow` metadata to `artifact_approval` event
2. Modify `artifact_tools.py:287` — add `glow` metadata to `artifact_applied` event
3. Add decay timer (5-10 seconds) for glow duration

### Phase 122.2: Frontend State
1. Add `glowingFiles: Set<string>` to useStore.ts
2. Add `addGlowingFile(path)` and `removeGlowingFile(path)` actions
3. Socket.IO handler for `artifact_approval` event

### Phase 122.3: Visual Effect
1. Change `MeshBasicMaterial` to `MeshStandardMaterial` in FileCard.tsx
2. Add `emissive` and `emissiveIntensity` props
3. Color: `#7ab3d4` (Scanner Panel light cyan)
4. Optional: Add Bloom postprocessing for stronger effect

### Phase 122.4: Decay Animation
1. Use `setTimeout` or `useFrame` for decay
2. Smooth fade-out over 1-2 seconds
3. Remove from `glowingFiles` set after decay

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Performance (Bloom) | Medium | Medium | Start with emissive only, add Bloom if needed |
| Material change breaks textures | Low | High | Test thoroughly on all node types |
| Too many glowing files | Low | Medium | Max 10 concurrent, FIFO eviction |
| Glow not visible on light backgrounds | Low | Low | Increase emissiveIntensity |

---

## Summary

**Ready for implementation.** The architecture is clean:
1. Backend already emits Socket.IO events for file operations
2. Frontend has React Three Fiber with all needed libraries
3. Color is confirmed: `#7ab3d4` with `rgba(122, 179, 212, 0.3)` glow
4. Recommended approach: Emissive material (simple, performant)

**All markers documented. Awaiting approval to proceed.**

---

**Report by:** Claude Opus 4.5
**Haiku Scouts:** 4 parallel missions
**Total markers:** 26 (MARKER_122.1A-J, 122.2A-K, 122.3A-E, 122.4A-K)
