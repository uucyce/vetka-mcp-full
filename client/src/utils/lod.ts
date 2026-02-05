/**
 * Unified LOD (Level of Detail) System for VETKA 3D
 * Phase 112.6: Adaptive Foveated Spot
 *
 * Combines distance-based LOD with screen-position LOD (foveated rendering).
 * Spot radius adapts to viewport size: larger on mobile, smaller on 4K.
 *
 * @status active
 * @phase 112.6
 */

import * as THREE from 'three';

/**
 * Smoothstep hermite interpolation (GLSL standard)
 * Creates smooth transition without hard edges
 */
function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = Math.max(0, Math.min(1, (x - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
}

/**
 * Distance-based LOD calculation
 * 10 levels: 0 (far/simple) to 9 (close/detailed)
 *
 * Used standalone for backend/viewport context where screen-space isn't available
 */
export function calculateDistanceLOD(distance: number): number {
  if (distance < 20) return 9;         // Ultra close - full detail
  if (distance < 40) return 8;         // Very close - full preview
  if (distance < 70) return 7;         // Close - large preview
  if (distance < 100) return 6;        // Medium close - medium preview
  if (distance < 150) return 5;        // Medium - mini preview starts
  if (distance < 400) return 4;        // Medium far - card only
  if (distance < 800) return 3;        // Far - shape + name
  if (distance < 1500) return 2;       // Farther - shape visible
  if (distance < 2500) return 1;       // Very far - small shape
  return 0;                             // Extra wide - tiny dot
}

/**
 * Get adaptive spot radius based on viewport width
 * Phase 112.8: Expanded radius (+10-15%) for less edge flicker
 * - Mobile: almost full screen (95%) - minimal edge processing
 * - Desktop: large spot (85%) - most nodes in stable zone
 * - 4K: generous spot (75%) - still saves GPU on true edges
 */
function getAdaptiveRadius(width: number): number {
  if (width < 768) return 0.95;   // Mobile: 95% coverage (almost full screen)
  if (width < 2560) return 0.85;  // 1080p/1440p: 85% coverage
  return 0.75;                     // 4K+: 75% coverage
}

/**
 * Position interface for node coordinates
 */
export interface NodePosition {
  x: number;
  y: number;
  z: number;
}

/**
 * Viewport size interface
 */
export interface ViewportSize {
  width: number;
  height: number;
}

/**
 * Adaptive Foveated LOD: Combines distance + screen-space position
 *
 * Algorithm:
 * 1. Calculate distance-based LOD (0-9)
 * 2. Project node to screen space (NDC: -1 to 1)
 * 3. Calculate normalized distance from screen center (0=center, 1=corner)
 * 4. Apply adaptive radius based on viewport size
 * 5. Smooth falloff using smoothstep (no hard edges)
 * 6. Combine: finalLOD = distLOD * screenFactor
 *
 * @param nodePosition - World position of the node
 * @param camera - Three.js camera (for projection + distance)
 * @param size - Viewport size {width, height}
 * @returns LOD level 0-9
 */
export function calculateAdaptiveLOD(
  nodePosition: NodePosition,
  camera: THREE.Camera,
  size: ViewportSize
): number {
  const worldPos = new THREE.Vector3(nodePosition.x, nodePosition.y, nodePosition.z);

  // 1. Distance LOD (base)
  const dist = camera.position.distanceTo(worldPos);
  const distLOD = calculateDistanceLOD(dist);

  // 2. Project to NDC (-1..1)
  const screenPos = worldPos.clone().project(camera);

  // Check if behind camera (z > 1 means behind)
  if (screenPos.z > 1) {
    return 0; // Behind camera = lowest LOD
  }

  const normX = Math.abs(screenPos.x);  // 0..1+ (center→edge)
  const normY = Math.abs(screenPos.y);

  // 3. Normalized screen distance (0=center, 1=corner, aspect-invariant)
  // Corner distance: sqrt(1² + 1²) / √2 = 1
  const screenDist = Math.sqrt(normX * normX + normY * normY) / Math.SQRT2;

  // 4. Adaptive radius based on viewport
  const radius = getAdaptiveRadius(size.width);

  // 5. Smooth falloff: 1=center, 0=periphery
  const t = screenDist / radius;
  const screenFactor = 1.0 - smoothstep(0.0, 1.0, t);

  // 6. Combine: modulate distLOD by screen position
  // Center of screen: full distLOD
  // Edges: reduced LOD (cheaper rendering)
  const finalLOD = Math.floor(distLOD * screenFactor);

  return Math.max(0, Math.min(9, finalLOD));
}

/**
 * Calculate LOD with minimum floor
 * Useful when you want peripheral nodes to still have some detail
 *
 * @param nodePosition - World position
 * @param camera - Three.js camera
 * @param size - Viewport size
 * @param minLOD - Minimum LOD floor (default 0)
 * @returns LOD level minLOD-9
 */
export function calculateAdaptiveLODWithFloor(
  nodePosition: NodePosition,
  camera: THREE.Camera,
  size: ViewportSize,
  minLOD: number = 0
): number {
  const lod = calculateAdaptiveLOD(nodePosition, camera, size);
  return Math.max(minLOD, lod);
}
