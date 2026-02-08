/**
 * Label Scoring & Selection System for VETKA 3D
 * Phase 113.3: Labels Championship
 *
 * Adaptive top-N selection with golden angle jitter, hysteresis, and priority scoring.
 * Performance target: ~24 ops/node, ~0.15ms for 400 nodes.
 *
 * Architecture:
 *   Scores computed in useRef (zero re-renders)
 *   → applyHysteresis (smooth camera motion)
 *   → selectTopLabels (adaptive top-N)
 *   → arraysEqual guard → setSelectedLabels (Zustand, only when SET changes)
 *   → FileCard reads showLabel boolean → hard filter
 *
 * @phase 113.3
 */

import type { TreeNode } from '../store/useStore';

// ─── Constants ───────────────────────────────────────────────────────────────

/**
 * Golden angle (radians): 2π × (√5 − 1) / 2 ≈ 2.39996 rad ≈ 137.508°
 * Fibonacci spiral — optimal non-repeating distribution for anti-overlap.
 */
const GOLDEN_ANGLE = 2 * Math.PI * (Math.sqrt(5) - 1) / 2;

/**
 * Code file extensions for type-based scoring boost.
 */
const CODE_EXTENSIONS = new Set([
  'ts', 'tsx', 'js', 'jsx', 'py', 'go', 'rs', 'java',
  'cpp', 'c', 'rb', 'php', 'swift', 'kt', 'cs', 'scala',
]);

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Check if a filename belongs to a code file by extension.
 * O(1) via Set lookup.
 */
export function isCodeFile(filename: string): boolean {
  const dot = filename.lastIndexOf('.');
  if (dot === -1) return false;
  return CODE_EXTENSIONS.has(filename.slice(dot + 1).toLowerCase());
}

// ─── Scoring ─────────────────────────────────────────────────────────────────

/**
 * Compute priority score for a single node (0.0–1.0).
 *
 * Formula:
 *   Pinned → 1.0 (always top priority)
 *   typeBoost   = folder 1.5 | code 1.2 | other 0.8
 *   depthScore  = 1 / √(depth + 1)
 *   sizeScore   = √(children) / √200
 *   searchBoost = highlighted ? 0.3 : 0
 *   final = (typeBoost/1.5)*0.4 + depthScore*0.3 + sizeScore*0.2 + searchBoost*0.1
 *
 * ~24 ops per call. O(1).
 */
export function computeLabelScore(
  node: TreeNode,
  isPinned: boolean,
  isHighlighted: boolean,
): number {
  // Pinned always wins
  if (isPinned) return 1.0;

  // MARKER_123.4A: Phase 123.4 - Hardcode for artificial root "vetka"
  // This is a design element, always show it
  if (node.name.toLowerCase() === 'vetka') return 0.99;

  // Type boost: folders = structural anchors, code = important, rest = lower
  const typeBoost =
    node.type === 'folder' ? 1.5 :
    (node.type === 'file' && isCodeFile(node.name)) ? 1.2 :
    0.8;

  // Depth: shallower = more important (DOMINANT factor after chain gate)
  // Linear decay: depth 0→1.0, 1→0.5, 5→0.17, 6→0.14, 7→0.125, 10→0.09
  const depthScore = 1.0 / (node.depth + 1);

  // Size: more children = more important (capped at √200)
  // Phase 113.4 FIX: This is now the DOMINANT factor.
  // Linear chain folders (1 child) get nearly zero — prevents
  // root chain (VETKA→Users→danilagulin→...) from dominating top-N.
  const childCount = node.children?.length ?? 0;
  const sizeScore = Math.min(1.0, Math.sqrt(childCount) / Math.sqrt(200));

  // Phase 113.4 FIX: Branching bonus — folders with many children are structural
  // landmarks. Folders with 1 child are just path segments (not interesting).
  // ≤1 child → 0.0, 2-3 → 0.3, 5+ → 0.6, 10+ → 0.8, 20+ → 1.0
  const branchFactor = childCount <= 1 ? 0.0 :
    Math.min(1.0, Math.log2(childCount) / Math.log2(20));

  // Search boost
  const searchBoost = isHighlighted ? 0.3 : 0.0;

  // MARKER_119.2H: Phase 119.2 - Heat boost for active directories
  // Folders with recent file activity get visibility boost
  const heatBoost = (node.heatScore ?? 0) * 0.15;  // up to 15% boost

  // Weighted sum, clamped to [0, 1]
  // FIX: Combined depth×branch — shallowest branching folder wins overview
  // vetka_live_03 (depth 5, 10ch) beats docs (depth 7, 20ch) because shallower
  // Both beat VETKA→Users→danilagulin chain (1 child each → branchFactor=0)
  //
  // HARD GATE: Chain folders (≤1 child) get zero score — they are path
  // segments, not landmarks. This kills VETKA→Users→danilagulin→... chain.
  if (childCount <= 1) return 0.0;

  // All remaining folders have branching (2+ children) — they ARE landmarks.
  // depthScore STRONGLY dominates: shallower = more important (Google Maps principle)
  // branchFactor provides tiebreaker for folders at same depth level
  // Phase 119.2: heatBoost adds visibility for active directories
  return Math.min(1.0,
    depthScore * 0.42 +       // shallower branching folders WIN overview (reduced from 0.50)
    branchFactor * 0.13 +     // tiebreaker: more children = more important
    sizeScore * 0.10 +        // magnitude of subtree
    (typeBoost / 1.5) * 0.08 + // folder vs file type
    searchBoost * 0.12 +       // search highlight boost
    heatBoost                  // Phase 119.2: active directory boost
  );
}

// ─── Selection ───────────────────────────────────────────────────────────────

/**
 * Adaptive top-N label selection.
 *
 * Grok formula: adaptiveMax = max(15, min(50, visibleCount * 0.075 + zoomLevel * 2))
 * - Minimum 15 labels (sparse views)
 * - Maximum 50 labels (dense + zoomed in)
 * - Scales with both visible count and zoom
 *
 * Pinned files are ALWAYS included (override top-N).
 *
 * O(n log n) — sort dominates.
 */
export function selectTopLabels(
  scoresMap: Map<string, number>,
  pinnedIds: string[],
  visibleCount: number,
  zoomLevel: number,
): string[] {
  // Phase 113.4 FIX: Aggressive Google Maps-style scaling
  // Key insight: visibleCount should REDUCE labels (more nodes = less % labeled)
  // zoomLevel (0-10) should be the PRIMARY driver
  //
  // MARKER_123.4B: Phase 123.4 - Minimum 5 labels at overview (was 1)
  // Overview  (zoom 0-1, 400+ visible): 5 labels (vetka + top dirs)
  // Far       (zoom 2-3, 300 visible):  6-8 labels (top-level dirs)
  // Medium    (zoom 4-5, 200 visible):  10-14 labels
  // Close     (zoom 6-8,  50 visible):  18-22 labels
  // Very close(zoom 9-10, 20 visible):  up to 25 labels
  //
  // Formula: base from zoom² curve, penalty for high node density
  const zoomBase = Math.floor(zoomLevel * zoomLevel * 0.25); // 0,0,1,2,4,6,9,12,16,20,25
  const densityPenalty = Math.max(0, Math.floor(Math.log2(Math.max(1, visibleCount / 50))));
  const adaptiveMax = Math.max(
    5,  // MARKER_123.4B: Minimum 5 labels at overview
    Math.min(25, zoomBase - densityPenalty + 5),
  );

  // Sort entries by score descending, take top-N
  const sorted = Array.from(scoresMap.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, adaptiveMax)
    .map(([id]) => id);

  // Union with pinned (always visible)
  const result = new Set(sorted);
  for (const pid of pinnedIds) {
    result.add(pid);
  }

  return Array.from(result);
}

// ─── Store Guard ─────────────────────────────────────────────────────────────

/**
 * Set-based array equality check (order-independent).
 * Used as guard before setSelectedLabels() — prevents store churn.
 *
 * O(n) time, O(n) space.
 */
export function arraysEqual(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;

  const setA = new Set(a);
  for (const item of b) {
    if (!setA.has(item)) return false;
  }
  return true;
}

// ─── Anti-Overlap ────────────────────────────────────────────────────────────

/**
 * Golden angle jitter for Z-axis label positioning.
 *
 * Distributes labels in Fibonacci spiral to minimize z-fighting.
 * Rank 0 (highest score) → small offset, higher ranks → larger spread.
 *
 * Formula: sin(rank × GOLDEN_ANGLE) × (0.3 + rank/total × 0.5)
 * Range: approximately −0.8 to +0.8 units.
 * Deterministic: same rank → same offset (no flicker).
 *
 * O(1).
 */
export function goldenAngleJitterZ(rank: number, total: number): number {
  if (total <= 1) return 0;
  const angle = rank * GOLDEN_ANGLE;
  const amplitude = 0.3 + (rank / (total - 1)) * 0.5;
  return Math.sin(angle) * amplitude;
}

// ─── Hysteresis ──────────────────────────────────────────────────────────────

/**
 * Apply hysteresis to prevent label flicker during camera movement.
 *
 * Rules (Grok correction):
 *   newScore > prevScore × 1.1  → accept new (significant increase)
 *   otherwise                    → max(prevScore × 0.9, newScore) (gradual decay)
 *
 * This prevents rapid top-N set changes during camera pan/zoom.
 *
 * O(n) where n = currentScores.size.
 */
export function applyHysteresis(
  currentScores: Map<string, number>,
  prevScores: Map<string, number>,
  threshold: number = 0.1,
): Map<string, number> {
  const smoothed = new Map<string, number>();

  for (const [id, newScore] of currentScores) {
    const prevScore = prevScores.get(id);

    if (prevScore === undefined) {
      // New node in viewport → accept immediately
      smoothed.set(id, newScore);
    } else if (newScore > prevScore * (1 + threshold)) {
      // Significant increase → accept new score
      smoothed.set(id, newScore);
    } else {
      // Gradual change → smooth decay (prevents flicker)
      smoothed.set(id, Math.max(prevScore * 0.9, newScore));
    }
  }

  return smoothed;
}
