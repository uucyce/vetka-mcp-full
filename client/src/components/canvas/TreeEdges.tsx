/**
 * TreeEdges - Renders all edges between nodes in the 3D tree.
 * Computes edge positions from store and highlights selections.
 *
 * @status active
 * @phase 96
 * @depends react, ./Edge, useStore
 * @used_by Canvas3D
 */

import { useMemo } from 'react';
import { Edge } from './Edge';
import { useStore } from '../../store/useStore';

export function TreeEdges() {
  const nodes = useStore((state) => state.nodes);
  const storeEdges = useStore((state) => state.edges);
  const selectedId = useStore((state) => state.selectedId);
  const highlightedId = useStore((state) => state.highlightedId);

  const edges = useMemo(() => {
    const result: Array<{
      id: string;
      start: [number, number, number];
      end: [number, number, number];
      isHighlighted: boolean;
      isAgentHighlighted: boolean;
    }> = [];

    // If we have edges from store, use them
    if (storeEdges.length > 0) {
      storeEdges.forEach((edge) => {
        const sourceNode = nodes[edge.source];
        const targetNode = nodes[edge.target];

        if (sourceNode && targetNode) {
          const isHighlighted = selectedId === edge.source || selectedId === edge.target;
          const isAgentHighlighted = highlightedId === edge.source || highlightedId === edge.target;

          result.push({
            id: edge.id,
            start: [sourceNode.position.x, sourceNode.position.y, sourceNode.position.z],
            end: [targetNode.position.x, targetNode.position.y, targetNode.position.z],
            isHighlighted,
            isAgentHighlighted,
          });
        }
      });
    } else {
      // Fallback: compute edges from parentId
      Object.values(nodes).forEach((node) => {
        if (node.parentId && nodes[node.parentId]) {
          const parent = nodes[node.parentId];

          const isHighlighted = selectedId === node.id || selectedId === parent.id;
          const isAgentHighlighted = highlightedId === node.id || highlightedId === parent.id;

          result.push({
            id: `edge-${parent.id}-${node.id}`,
            start: [parent.position.x, parent.position.y, parent.position.z],
            end: [node.position.x, node.position.y, node.position.z],
            isHighlighted,
            isAgentHighlighted,
          });
        }
      });
    }

    return result;
  }, [nodes, storeEdges, selectedId, highlightedId]);

  return (
    <group name="edges">
      {edges.map((edge) => {
        // Phase 54.5: Monochrome colors (Batman Nolan style)
        let color = '#6b7280';  // Gray
        let lineWidth = 1.5;
        let opacity = 0.6;

        if (edge.isAgentHighlighted) {
          color = '#9ca3af';  // Lighter gray for agent highlight
          lineWidth = 2.5;
          opacity = 0.8;
        } else if (edge.isHighlighted) {
          color = '#d1d5db';  // Even lighter for selection highlight
          lineWidth = 2;
          opacity = 0.75;
        }

        return (
          <Edge
            key={edge.id}
            start={edge.start}
            end={edge.end}
            color={color}
            lineWidth={lineWidth}
            opacity={opacity}
          />
        );
      })}
    </group>
  );
}
