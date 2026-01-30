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

export function calculateSimpleLayout(nodes: TreeNode[]): TreeNode[] {
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

    const totalWidth = (count - 1) * HORIZONTAL_SPREAD;
    const x = -totalWidth / 2 + index * HORIZONTAL_SPREAD;
    const y = node.depth * LEVEL_HEIGHT;
    const z = 0;

    return {
      ...node,
      position: { x, y, z }
    };
  });

  return positioned;
}
