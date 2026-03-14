/**
 * Layout calculation utilities for positioning tree nodes in 3D space.
 *
 * @status active
 * @phase 96
 * @depends ../store/useStore
 * @used_by ./hooks/useTreeData, ./components/canvas
 */
import type { TreeNode } from '../store/useStore';

const LEVEL_HEIGHT = 20;
const HORIZONTAL_SPREAD = 30;
let _layoutBiasProfile: {
  vertical_separation_bias?: number;
  sibling_spacing_bias?: number;
  branch_compactness_bias?: number;
  confidence?: number;
} | null = null;

// MARKER_155.MEMORY.ENGRAM_DAG_PREFS.V1:
// Shared soft-prior for VETKA tree layout (no hardcoded coordinates).
export function setLayoutBiasProfile(profile: typeof _layoutBiasProfile): void {
  _layoutBiasProfile = profile || null;
}

export function calculateSimpleLayout(nodes: TreeNode[]): TreeNode[] {
  const conf = Math.max(0, Math.min(1, Number(_layoutBiasProfile?.confidence ?? 0)));
  const vBias = Math.max(-1, Math.min(1, Number(_layoutBiasProfile?.vertical_separation_bias ?? 0)));
  const sBias = Math.max(-1, Math.min(1, Number(_layoutBiasProfile?.sibling_spacing_bias ?? 0)));
  const cBias = Math.max(-1, Math.min(1, Number(_layoutBiasProfile?.branch_compactness_bias ?? 0)));
  const levelHeight = LEVEL_HEIGHT * (1 + vBias * 0.25 * conf);
  const spread = HORIZONTAL_SPREAD * (1 + sBias * 0.20 * conf - cBias * 0.14 * conf);

  const byDepth: Record<number, TreeNode[]> = {};
  nodes.forEach(node => {
    const d = node.depth;
    if (!byDepth[d]) byDepth[d] = [];
    byDepth[d].push(node);
  });

  Object.keys(byDepth).forEach(depth => {
    byDepth[Number(depth)].sort((a, b) => {
      if (a.parentId === b.parentId) {
        return a.name.localeCompare(b.name);
      }
      return (a.parentId || '').localeCompare(b.parentId || '');
    });
  });

  const positioned = nodes.map(node => {
    const siblings = byDepth[node.depth];
    const index = siblings.indexOf(node);
    const count = siblings.length;

    const totalWidth = (count - 1) * spread;
    const x = -totalWidth / 2 + index * spread;
    const y = node.depth * levelHeight;
    const z = 0;

    return {
      ...node,
      position: { x, y, z }
    };
  });

  return positioned;
}
