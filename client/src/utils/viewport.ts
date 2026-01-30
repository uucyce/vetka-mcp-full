/**
 * Phase 70: Viewport Context Bridge
 *
 * [PHASE70-M4] viewport.ts: Utility functions — IMPLEMENTED
 *
 * Provides spatial context for AI agents:
 * - Frustum culling to find visible nodes
 * - LOD levels matching FileCard.tsx
 * - ViewportContext with camera position, zoom, pinned/viewport separation
 *
 * @file viewport.ts
 * @status ACTIVE
 * @phase Phase 70 - Viewport Context Bridge
 * @lastUpdate 2026-01-19
 */

import * as THREE from 'three';
import type { TreeNode } from '../store/useStore';

// ============================================================
// TYPES
// ============================================================

export interface ViewportNode {
  id: string;
  path: string;
  name: string;
  type: 'file' | 'folder';
  position: { x: number; y: number; z: number };

  // Spatial metrics
  distance_to_camera: number;
  lod_level: number;  // 0-9, matches FileCard.tsx

  // Priority flags
  is_pinned: boolean;
  is_center: boolean;  // Close to camera center ray

  // Will be filled by backend (Phase 70.5+)
  dependency_score?: number;
  cam_activation?: number;
  knowledge_level?: number;
  summary?: string;
}

export interface ViewportContext {
  // Metadata
  camera_position: { x: number; y: number; z: number };
  camera_target: { x: number; y: number; z: number };
  zoom_level: number;  // Derived from average distance (0-9 LOD scale)

  // Nodes
  pinned_nodes: ViewportNode[];   // Explicit selection (highest priority)
  viewport_nodes: ViewportNode[]; // Implicit (visible in frustum)

  // Statistics
  total_visible: number;
  total_pinned: number;
}

// ============================================================
// LOD LEVELS (matches FileCard.tsx:9-28)
// ============================================================

/**
 * Get LOD level based on distance to camera.
 * Matches the 10-level system in FileCard.tsx.
 *
 * @param distance - Distance from camera to node
 * @returns LOD level 0-9 (0 = far, 9 = close)
 */
export function getLODLevel(distance: number): number {
  if (distance > 300) return 0;  // Tiny dot
  if (distance > 200) return 1;  // Small shape
  if (distance > 150) return 2;  // Shape + name starting
  if (distance > 100) return 3;  // Clear shape + name
  if (distance > 70) return 4;   // Larger card
  if (distance > 50) return 5;   // Mini preview starts
  if (distance > 35) return 6;   // Mini preview full
  if (distance > 20) return 7;   // Large preview
  if (distance > 10) return 8;   // Full preview
  return 9;                       // Ultra close
}

/**
 * Convert LOD level to detail level for summaries.
 * Used by backend to determine how much context to include.
 *
 * @param lod - LOD level 0-9
 * @returns Detail level for summary generation
 */
export function getLODDetailLevel(lod: number): 'minimal' | 'basic' | 'detailed' | 'full' {
  if (lod <= 2) return 'minimal';  // name + type only
  if (lod <= 5) return 'basic';    // + summary line
  if (lod <= 8) return 'detailed'; // + key exports
  return 'full';                    // full content if fits
}

// ============================================================
// FRUSTUM CULLING
// ============================================================

/**
 * Get all nodes visible in the camera frustum.
 *
 * @param nodesRecord - All nodes from Zustand store
 * @param camera - THREE.js PerspectiveCamera
 * @returns Array of ViewportNode sorted by distance (closest first)
 */
export function getVisibleNodes(
  nodesRecord: Record<string, TreeNode>,
  camera: THREE.PerspectiveCamera
): ViewportNode[] {
  const nodes = Object.values(nodesRecord);

  // Build frustum from camera
  const frustum = new THREE.Frustum();
  const projScreenMatrix = new THREE.Matrix4();
  projScreenMatrix.multiplyMatrices(
    camera.projectionMatrix,
    camera.matrixWorldInverse
  );
  frustum.setFromProjectionMatrix(projScreenMatrix);

  // Camera center ray for "is_center" calculation
  const cameraDir = new THREE.Vector3();
  camera.getWorldDirection(cameraDir);

  const visible: ViewportNode[] = [];

  for (const node of nodes) {
    const point = new THREE.Vector3(
      node.position.x,
      node.position.y,
      node.position.z
    );

    // Skip nodes outside frustum
    if (!frustum.containsPoint(point)) continue;

    const distance = camera.position.distanceTo(point);

    // Check if node is near camera center ray (foveated priority)
    const toNode = point.clone().sub(camera.position).normalize();
    const dotProduct = toNode.dot(cameraDir);
    const isCenter = dotProduct > 0.95; // Within ~18 degrees of center

    visible.push({
      id: node.id,
      path: node.path,
      name: node.name,
      type: node.type,
      position: node.position,
      distance_to_camera: Math.round(distance * 100) / 100,
      lod_level: getLODLevel(distance),
      is_pinned: false, // Will be set in merge
      is_center: isCenter,
    });
  }

  // Sort by distance (closest first)
  return visible.sort((a, b) => a.distance_to_camera - b.distance_to_camera);
}

// ============================================================
// MERGE PINNED + VIEWPORT
// ============================================================

/**
 * Build complete viewport context for AI agent.
 *
 * Merges:
 * - Pinned nodes (explicit user selection, highest priority)
 * - Viewport nodes (visible in frustum, implicit context)
 *
 * @param nodesRecord - All nodes from Zustand store
 * @param pinnedIds - Array of pinned node IDs
 * @param camera - THREE.js PerspectiveCamera
 * @returns Complete ViewportContext for backend
 */
export function buildViewportContext(
  nodesRecord: Record<string, TreeNode>,
  pinnedIds: string[],
  camera: THREE.PerspectiveCamera
): ViewportContext {
  const visibleNodes = getVisibleNodes(nodesRecord, camera);
  const pinnedSet = new Set(pinnedIds);

  // Mark pinned nodes in visible set
  const allNodes = visibleNodes.map(node => ({
    ...node,
    is_pinned: pinnedSet.has(node.id),
  }));

  // Add pinned nodes that are NOT visible (outside viewport)
  for (const id of pinnedIds) {
    if (allNodes.some(n => n.id === id)) continue;

    const node = nodesRecord[id];
    if (!node) continue;

    const point = new THREE.Vector3(
      node.position.x,
      node.position.y,
      node.position.z
    );
    const distance = camera.position.distanceTo(point);

    allNodes.push({
      id: node.id,
      path: node.path,
      name: node.name,
      type: node.type,
      position: node.position,
      distance_to_camera: Math.round(distance * 100) / 100,
      lod_level: getLODLevel(distance),
      is_pinned: true,
      is_center: false,
    });
  }

  // Separate pinned and viewport
  const pinnedNodes = allNodes.filter(n => n.is_pinned);
  const viewportNodes = allNodes.filter(n => !n.is_pinned);

  // Calculate zoom level (average distance of closest 5 nodes)
  const closestDistances = allNodes
    .map(n => n.distance_to_camera)
    .sort((a, b) => a - b)
    .slice(0, 5);
  const avgDistance = closestDistances.length > 0
    ? closestDistances.reduce((a, b) => a + b, 0) / closestDistances.length
    : 100;

  // Camera target (from OrbitControls if available)
  const controls = (window as any).__orbitControls;
  const target = controls?.target || new THREE.Vector3(0, 0, 0);

  return {
    camera_position: {
      x: Math.round(camera.position.x * 100) / 100,
      y: Math.round(camera.position.y * 100) / 100,
      z: Math.round(camera.position.z * 100) / 100,
    },
    camera_target: {
      x: Math.round(target.x * 100) / 100,
      y: Math.round(target.y * 100) / 100,
      z: Math.round(target.z * 100) / 100,
    },
    zoom_level: getLODLevel(avgDistance),
    pinned_nodes: pinnedNodes,
    viewport_nodes: viewportNodes,
    total_visible: viewportNodes.length,
    total_pinned: pinnedNodes.length,
  };
}

// ============================================================
// EXPORTS
// ============================================================

export type { TreeNode };
