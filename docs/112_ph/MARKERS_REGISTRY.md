# Phase 112: Markers Registry

**Purpose:** Complete list of code markers for Sonnet verification
**Date:** 2026-02-05

---

## Frontend Markers (client/src/)

### FileCard.tsx
| Marker | Line | Status | Description |
|--------|------|--------|-------------|
| `MARKER_111.21_USEFRAME` | 254-290 | **DONE** | Batch LOD (Phase 112.3) - prop from parent |
| `MARKER_111.21_TEXTURE` | 368 | PENDING | Split texture layers |
| `MARKER_111.21_MEMO` | 1150-1193 | **DONE** | React.memo + custom comparator (Phase 112.1) |
| `MARKER_108_3_CHAT_METADATA` | 159 | DONE | Chat node metadata |
| `MARKER_108_ARTIFACT_VIZ` | 172, 359, 387 | DONE | Artifact rendering |
| `MARKER_108_4_APPROVE_UI` | 178, 388, 460, 803, 920, 951 | DONE | Approval UI |
| `MARKER_108_CHAT_CARD` | 524 | DONE | Chat card rendering |
| `MARKER_111_DRAG` | 749 | DONE | Folder drag with children |
| `MARKER_3D_NODE_RENDER` | 856 | INFO | FileCard documentation |

### App.tsx
| Marker | Line | Status | Description |
|--------|------|--------|-------------|
| `MARKER_111.21_FRUSTUM` | 34-113 | **DONE** | FrustumCulledNodes component (Phase 112.2) |
| `MARKER_109_DEVPANEL` | 362 | DONE | DevPanel integration |

### useSocket.ts
| Marker | Line | Status | Description |
|--------|------|--------|-------------|
| `MARKER_109_4_VIEWPORT` | 409-413 | DONE | viewport_update event defined |
| `MARKER_108_3_SOCKETIO_UPDATE` | 267, 1106 | DONE | Real-time chat node opacity |
| `MARKER_103_GC4` | 978 | DONE | group_participant_updated handler |
| `MARKER_104_FRONTEND` | 1303 | DONE | Voice & room events |
| `MARKER_104_VISUAL` | 222, 1387 | DONE | Artifact approval L2 |
| `MARKER_110_FIX` | 495 | DONE | Socket exposed globally |
| `MARKER_109_14` | 1451, 1507 | DONE | displayName for chat naming |

### useTreeData.ts
| Marker | Line | Status | Description |
|--------|------|--------|-------------|
| `MARKER_108_CHAT_FRONTEND` | 39 | DONE | Chat tree store |
| `MARKER_110_FIX` | 42, 202 | DONE | Manual tree refresh |
| `MARKER_111_DEBUG` | 75, 165 | INFO | Debug logging |
| `MARKER_111_FIX` | 126, 159 | DONE | Backend positions preserved |
| `MARKER_109_DEVPANEL` | 121, 142 | DONE | Threshold-based fallback |

### TreeEdges.tsx
| Marker | Line | Status | Description |
|--------|------|--------|-------------|
| `MARKER_3D_EDGE_STYLE` | 82 | INFO | Edge styling documentation |
| `MARKER_108_CHAT_EDGE` | 94 | DONE | Chat edge coloring |

### useStore.ts
| Marker | Line | Status | Description |
|--------|------|--------|-------------|
| `MARKER_108_3_CHAT_METADATA` | 37 | DONE | Chat node metadata interface |

---

## Backend Markers (src/)

### fan_layout.py
| Marker | Line | Status | Description |
|--------|------|--------|-------------|
| `MARKER_111_5` | 19 | DONE | Phase sorting for folders |
| `MARKER_109_Y_FLOOR` | 35-37 | DONE | Position protection constants |
| `MARKER_110_BACKEND_CONFIG` | 40-67 | DONE | Dynamic config getter |
| `MARKER_110_Y_FORMULA` | 557, 573 | DONE | Y-axis blend weights |
| `MARKER_111_FIX` | 501 | DONE | Simple tree layout |
| `MARKER_111_SPREAD` | 535 | DONE | Siblings spread by angle |
| `MARKER_111_4` | 770 | DONE | Compact tree params |

---

## P0 Markers (Implementation Status)

| Priority | Marker | File | Line | Status |
|----------|--------|------|------|--------|
| **P0-1** | `MARKER_111.21_MEMO` | FileCard.tsx | 1150-1193 | **DONE** Phase 112.1 |
| **P0-2** | `MARKER_111.21_FRUSTUM` | App.tsx | 34-113 | **DONE** Phase 112.2 |
| **P0-3** | `MARKER_111.21_USEFRAME` | App.tsx + FileCard.tsx | 47-130, 254 | **DONE** Phase 112.3 |
| **P0-4** | `MARKER_111.21_TEXTURE` | FileCard.tsx | 368 | PENDING - Split layers |
| **P0-5** | - | NEW | - | PENDING - InstancedMesh |

---

## Phase 109.4 Verification

**Status:** WORKING

**Evidence:**
1. `useSocket.ts:409-413` - `viewport_update` ClientToServerEvent defined
2. `useSocket.ts:1473-1504` - Viewport context built and sent with `user_message`
3. `useSocket.ts:1581-1582` - Comment: "No separate viewport_update needed - bundled with each message"

**Conclusion:** Phase 109.4 is correctly implemented. Viewport sync works by bundling context with each user message, not as separate events.

---

## Sonnet Verification Checklist

### Group 1: Performance + Layout + Modes
- [ ] MARKER_111.21_MEMO verified
- [ ] MARKER_111.21_FRUSTUM verified
- [ ] MARKER_111.21_USEFRAME verified
- [ ] MARKER_111.21_TEXTURE verified
- [ ] MARKER_111_FIX (useTreeData) verified
- [ ] fan_layout.py markers verified

### Group 2: Socket + State + Three.js
- [ ] MARKER_109_4_VIEWPORT verified
- [ ] MARKER_108_3_SOCKETIO_UPDATE verified
- [ ] useStore.ts structure verified
- [ ] No memory leaks in Three.js objects

### Group 3: Edge + Backend + Camera + UI
- [ ] MARKER_3D_EDGE_STYLE verified
- [ ] MARKER_108_CHAT_EDGE verified
- [ ] Backend layout markers verified
- [ ] DevPanel controls working
