/**
 * TreeEdges - Renders all edges between nodes in the 3D tree.
 * Computes edge positions from store and highlights selections.
 * Phase 119: Added edge interactivity (click, double-click, shift+click, hover)
 *
 * @status active
 * @phase 119
 * @depends react, ./Edge, useStore
 * @used_by Canvas3D
 */

import { useMemo, useState, useRef, useCallback } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { Edge } from './Edge';
import { useStore } from '../../store/useStore';

export function TreeEdges() {
  const nodes = useStore((state) => state.nodes);
  const storeEdges = useStore((state) => state.edges);
  const selectedId = useStore((state) => state.selectedId);
  const highlightedId = useStore((state) => state.highlightedId);

  // Phase 119: Edge interactivity state
  const pinnedEdgeIds = useStore((state) => state.pinnedEdgeIds);
  const selectedEdgeId = useStore((state) => state.selectedEdgeId);
  const selectEdge = useStore((state) => state.selectEdge);
  const pinEdgeSmart = useStore((state) => state.pinEdgeSmart);
  const setHoveredEdge = useStore((state) => state.setHoveredEdge);

  // Phase 112: Frustum culling for edges
  const { camera } = useThree();
  const [visibleEdgeIds, setVisibleEdgeIds] = useState<Set<string>>(() => new Set());
  const lastUpdateRef = useRef(0);
  const frustumRef = useRef(new THREE.Frustum());
  const projMatrixRef = useRef(new THREE.Matrix4());

  // Phase 119: Build edges with source/target IDs for callbacks
  const edges = useMemo(() => {
    const result: Array<{
      id: string;
      sourceId: string;
      targetId: string;
      start: [number, number, number];
      end: [number, number, number];
      isHighlighted: boolean;
      isAgentHighlighted: boolean;
      isChatEdge: boolean;
    }> = [];

    // If we have edges from store, use them
    if (storeEdges.length > 0) {
      storeEdges.forEach((edge) => {
        const sourceNode = nodes[edge.source];
        const targetNode = nodes[edge.target];

        if (sourceNode && targetNode) {
          const isHighlighted = selectedId === edge.source || selectedId === edge.target;
          const isAgentHighlighted = highlightedId === edge.source || highlightedId === edge.target;
          const isChatEdge = (sourceNode as any).type === 'chat' || (targetNode as any).type === 'chat';

          result.push({
            id: edge.id,
            sourceId: edge.source,
            targetId: edge.target,
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
          const isChatEdge = (node as any).type === 'chat' || (parent as any).type === 'chat';

          result.push({
            id: `edge-${parent.id}-${node.id}`,
            sourceId: parent.id,
            targetId: node.id,
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

  // Phase 112: Frustum culling for edges (check midpoint visibility)
  useFrame((state) => {
    const now = state.clock.elapsedTime;
    if (now - lastUpdateRef.current < 0.25) return; // 250ms throttle
    lastUpdateRef.current = now;

    // Update frustum
    projMatrixRef.current.multiplyMatrices(
      camera.projectionMatrix,
      camera.matrixWorldInverse
    );
    frustumRef.current.setFromProjectionMatrix(projMatrixRef.current);

    // Check edge visibility
    const visible = new Set<string>();
    const point = new THREE.Vector3();

    for (const edge of edges) {
      point.set(edge.start[0], edge.start[1], edge.start[2]);
      if (frustumRef.current.containsPoint(point)) {
        visible.add(edge.id);
        continue;
      }
      point.set(edge.end[0], edge.end[1], edge.end[2]);
      if (frustumRef.current.containsPoint(point)) {
        visible.add(edge.id);
        continue;
      }
      point.set(
        (edge.start[0] + edge.end[0]) / 2,
        (edge.start[1] + edge.end[1]) / 2,
        (edge.start[2] + edge.end[2]) / 2
      );
      if (frustumRef.current.containsPoint(point)) {
        visible.add(edge.id);
      }
    }

    const sizeDiff = Math.abs(visible.size - visibleEdgeIds.size);
    if (sizeDiff > 10 || (visible.size > 0 && visibleEdgeIds.size === 0)) {
      setVisibleEdgeIds(visible);
    }
  });

  // Filter to visible edges only
  const visibleEdges = useMemo(() => {
    if (visibleEdgeIds.size === 0) return edges;
    return edges.filter(e => visibleEdgeIds.has(e.id));
  }, [edges, visibleEdgeIds]);

  // Phase 119: Edge click handlers
  const handleEdgeClick = useCallback((edgeId: string) => {
    selectEdge(edgeId);
    console.log('[TreeEdges] Phase 119: Edge selected:', edgeId);
  }, [selectEdge]);

  const handleEdgeDoubleClick = useCallback((edgeId: string, sourceId: string, targetId: string) => {
    // Dispatch event for App.tsx to handle zoom
    window.dispatchEvent(new CustomEvent('vetka-zoom-to-edge', {
      detail: { edgeId, sourceId, targetId }
    }));
    console.log('[TreeEdges] Phase 119: Double-click zoom to edge:', edgeId);
  }, []);

  const handleEdgeShiftClick = useCallback((edgeId: string, sourceId: string, targetId: string) => {
    pinEdgeSmart(edgeId, sourceId, targetId);
    console.log('[TreeEdges] Phase 119: Edge pinned:', edgeId);
  }, [pinEdgeSmart]);

  const handleEdgeHover = useCallback((edgeId: string | null) => {
    setHoveredEdge(edgeId);
  }, [setHoveredEdge]);

  return (
    <group name="edges">
      {visibleEdges.map((edge) => {
        // Calculate visual properties
        let color = '#6b7280';  // Gray
        let lineWidth = 1.5;
        let opacity = 0.6;

        if (edge.isChatEdge) {
          color = '#4a9eff';
          opacity = 0.75;
          lineWidth = 2;
        } else if (edge.isAgentHighlighted) {
          color = '#9ca3af';
          lineWidth = 2.5;
          opacity = 0.8;
        } else if (edge.isHighlighted) {
          color = '#d1d5db';
          lineWidth = 2;
          opacity = 0.75;
        }

        const isSelected = selectedEdgeId === edge.id;
        const isPinned = pinnedEdgeIds.includes(edge.id);

        return (
          <Edge
            key={edge.id}
            edgeId={edge.id}
            sourceId={edge.sourceId}
            targetId={edge.targetId}
            start={edge.start}
            end={edge.end}
            color={color}
            lineWidth={lineWidth}
            opacity={opacity}
            isSelected={isSelected}
            isPinned={isPinned}
            onClick={handleEdgeClick}
            onDoubleClick={handleEdgeDoubleClick}
            onShiftClick={handleEdgeShiftClick}
            onHover={handleEdgeHover}
          />
        );
      })}
    </group>
  );
}
