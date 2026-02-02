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
      isChatEdge: boolean;  // Phase 108.2: Track chat edges for blue coloring
    }> = [];

    // If we have edges from store, use them
    if (storeEdges.length > 0) {
      storeEdges.forEach((edge) => {
        const sourceNode = nodes[edge.source];
        const targetNode = nodes[edge.target];

        if (sourceNode && targetNode) {
          const isHighlighted = selectedId === edge.source || selectedId === edge.target;
          const isAgentHighlighted = highlightedId === edge.source || highlightedId === edge.target;
          // Phase 108.2: Edge is chat-related if either node is a chat type
          const isChatEdge = (sourceNode as any).type === 'chat' || (targetNode as any).type === 'chat';

          result.push({
            id: edge.id,
            start: [sourceNode.position.x, sourceNode.position.y, sourceNode.position.z],
            end: [targetNode.position.x, targetNode.position.y, targetNode.position.z],
            isHighlighted,
            isAgentHighlighted,
            isChatEdge,
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
          // Phase 108.2: Edge is chat-related if either node is a chat type
          const isChatEdge = (node as any).type === 'chat' || (parent as any).type === 'chat';

          result.push({
            id: `edge-${parent.id}-${node.id}`,
            start: [parent.position.x, parent.position.y, parent.position.z],
            end: [node.position.x, node.position.y, node.position.z],
            isHighlighted,
            isAgentHighlighted,
            isChatEdge,
          });
        }
      });
    }

    return result;
  }, [nodes, storeEdges, selectedId, highlightedId]);

  return (
    <group name="edges">
      {edges.map((edge) => {
        // MARKER_3D_EDGE_STYLE: Edge rendering with monochrome color scheme
        // - Default color: '#6b7280' (gray, opacity 0.6, lineWidth 1.5)
        // - Agent highlight: '#9ca3af' (lighter gray, opacity 0.8, lineWidth 2.5)
        // - Selection highlight: '#d1d5db' (even lighter, opacity 0.75, lineWidth 2)
        // - Curve: CatmullRomCurve3 with midpoint (Edge.tsx line 41)
        // - Implementation: @react-three/drei Line component with depthTest=true, depthWrite=false
        // - Phase 108.2: Chat edges use '#4a9eff' (blue) with higher opacity to distinguish from file tree
        // Phase 54.5: Monochrome colors (Batman Nolan style)
        let color = '#6b7280';  // Gray
        let lineWidth = 1.5;
        let opacity = 0.6;

        // MARKER_108_CHAT_EDGE: Phase 108.2 - Chat edge coloring
        if (edge.isChatEdge) {
          color = '#4a9eff';  // Blue for chat edges
          opacity = 0.75;
          lineWidth = 2;
        } else if (edge.isAgentHighlighted) {
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
