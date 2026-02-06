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

  // Type boost: folders = structural anchors, code = important, rest = lower
  const typeBoost =
    node.type === 'folder' ? 1.5 :
    (node.type === 'file' && isCodeFile(node.name)) ? 1.2 :
    0.8;

  // Depth: shallower = more important
  const depthScore = 1.0 / Math.sqrt(node.depth + 1);

  // Size: more children = more important (capped at √200)
  const childCount = node.children?.length ?? 0;
  const sizeScore = Math.min(1.0, Math.sqrt(childCount) / Math.sqrt(200));

  // Search boost
  const searchBoost = isHighlighted ? 0.3 : 0.0;

  // Weighted sum, clamped to [0, 1]
  return Math.min(1.0,
    (typeBoost / 1.5) * 0.4 +
    depthScore * 0.3 +
    sizeScore * 0.2 +
    searchBoost * 0.1
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
  // Adaptive maximum (Grok fix: min=5 for overview, max=30, softer scaling)
  // Overview (zoom~1, 200 visible): 5-10 labels
  // Medium  (zoom~5, 100 visible):  ~15 labels
  // Close   (zoom~8,  30 visible):  ~25 labels
  const adaptiveMax = Math.max(
    5,
    Math.min(30, Math.floor(visibleCount * 0.04 + zoomLevel * 1.5)),
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
