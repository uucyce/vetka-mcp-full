/**
 * TreeEdges - Renders all edges between nodes in the 3D tree.
 * Computes edge positions from store and highlights selections.
 *
 * @status active
 * @phase 96
 * @depends react, ./Edge, useStore
 * @used_by Canvas3D
 */

import { useMemo, useState, useRef } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { Edge } from './Edge';
import { useStore } from '../../store/useStore';

export function TreeEdges() {
  const nodes = useStore((state) => state.nodes);
  const storeEdges = useStore((state) => state.edges);
  const selectedId = useStore((state) => state.selectedId);
  const highlightedId = useStore((state) => state.highlightedId);
  const showMediaChunks = useStore((state) => state.showMediaChunks);

  // Phase 112: Frustum culling for edges
  const { camera } = useThree();
  const [visibleEdgeIds, setVisibleEdgeIds] = useState<Set<string>>(() => new Set());
  const lastUpdateRef = useRef(0);
  const frustumRef = useRef(new THREE.Frustum());
  const projMatrixRef = useRef(new THREE.Matrix4());

  const edges = useMemo(() => {
    const result: Array<{
      id: string;
      start: [number, number, number];
      end: [number, number, number];
      isHighlighted: boolean;
      isAgentHighlighted: boolean;
      isChatEdge: boolean;  // Phase 108.2: Track chat edges for blue coloring
      edgeType?: string;
    }> = [];

    // If we have edges from store, use them
    if (storeEdges.length > 0) {
      storeEdges.forEach((edge) => {
        const sourceNode = nodes[edge.source];
        const targetNode = nodes[edge.target];
        const isMediaChunkEdge = edge.type === 'media_chunk' || edge.type === 'temporal_chunk';
        const sourceIsMediaChunk = sourceNode?.metadata?.artifact_type === 'media_chunk';
        const targetIsMediaChunk = targetNode?.metadata?.artifact_type === 'media_chunk';
        if (!showMediaChunks && (isMediaChunkEdge || sourceIsMediaChunk || targetIsMediaChunk)) {
          return;
        }

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
            edgeType: edge.type,
          });
        }
      });
    } else {
      // Fallback: compute edges from parentId
      Object.values(nodes).forEach((node) => {
        if (!showMediaChunks && node.metadata?.artifact_type === 'media_chunk') {
          return;
        }
        if (node.parentId && nodes[node.parentId]) {
          const parent = nodes[node.parentId];
          if (!showMediaChunks && parent?.metadata?.artifact_type === 'media_chunk') {
            return;
          }

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
            edgeType: undefined,
          });
        }
      });
    }

    return result;
  }, [nodes, storeEdges, selectedId, highlightedId, showMediaChunks]);

  // Phase 112: Frustum culling for edges (check midpoint visibility)
  useFrame((state) => {
    const now = state.clock.elapsedTime;
    if (now - lastUpdateRef.current < 0.25) return; // 250ms throttle (slower than nodes)
    lastUpdateRef.current = now;

    // Update frustum
    projMatrixRef.current.multiplyMatrices(
      camera.projectionMatrix,
      camera.matrixWorldInverse
    );
    frustumRef.current.setFromProjectionMatrix(projMatrixRef.current);

    // Check edge visibility (midpoint OR either endpoint in frustum)
    const visible = new Set<string>();
    const point = new THREE.Vector3();

    for (const edge of edges) {
      // Check start point
      point.set(edge.start[0], edge.start[1], edge.start[2]);
      if (frustumRef.current.containsPoint(point)) {
        visible.add(edge.id);
        continue;
      }
      // Check end point
      point.set(edge.end[0], edge.end[1], edge.end[2]);
      if (frustumRef.current.containsPoint(point)) {
        visible.add(edge.id);
        continue;
      }
      // Check midpoint (for long edges crossing the viewport)
      point.set(
        (edge.start[0] + edge.end[0]) / 2,
        (edge.start[1] + edge.end[1]) / 2,
        (edge.start[2] + edge.end[2]) / 2
      );
      if (frustumRef.current.containsPoint(point)) {
        visible.add(edge.id);
      }
    }

    // Update state if changed significantly
    const sizeDiff = Math.abs(visible.size - visibleEdgeIds.size);
    if (sizeDiff > 10 || (visible.size > 0 && visibleEdgeIds.size === 0)) {
      setVisibleEdgeIds(visible);
    }
  });

  // Filter to visible edges only
  const visibleEdges = useMemo(() => {
    if (visibleEdgeIds.size === 0) return edges; // Initial render: show all
    return edges.filter(e => visibleEdgeIds.has(e.id));
  }, [edges, visibleEdgeIds]);

  return (
    <group name="edges">
      {visibleEdges.map((edge) => {
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
        if (edge.edgeType === 'media_chunk') {
          color = '#f59e0b';
          opacity = 0.55;
          lineWidth = 1.8;
        } else if (edge.edgeType === 'temporal_chunk') {
          color = '#fbbf24';
          opacity = 0.45;
          lineWidth = 1.5;
        } else if (edge.isChatEdge) {
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
