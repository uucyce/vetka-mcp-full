/**
 * Edge - 3D curved line connecting nodes in the tree visualization.
 * Uses MeshLine for clickable edges with proper raycasting.
 *
 * @status active
 * @phase 119
 * @depends react, three, meshline, @react-three/fiber
 * @used_by TreeEdges
 */

import { useMemo, memo, useRef, useState } from 'react';
import { useThree, extend } from '@react-three/fiber';
import * as THREE from 'three';
import { MeshLineGeometry, MeshLineMaterial, raycast } from 'meshline';

// Phase 119: Extend r3f with meshline components
extend({ MeshLineGeometry, MeshLineMaterial });

// Phase 119: Extended props with interactivity
interface EdgeProps {
  start: [number, number, number];
  end: [number, number, number];
  color?: string;
  lineWidth?: number;
  opacity?: number;
  // Phase 119: New interactive props
  edgeId?: string;
  sourceId?: string;
  targetId?: string;
  onClick?: (edgeId: string) => void;
  onDoubleClick?: (edgeId: string, sourceId: string, targetId: string) => void;
  onShiftClick?: (edgeId: string, sourceId: string, targetId: string) => void;
  onHover?: (edgeId: string | null) => void;
  isSelected?: boolean;
  isPinned?: boolean;
}

// Phase 119: Interactive edge with MeshLine
function EdgeComponent({
  start,
  end,
  color = '#4b5563',
  lineWidth = 1.5,
  opacity = 0.6,
  edgeId = '',
  sourceId = '',
  targetId = '',
  onClick,
  onDoubleClick,
  onShiftClick,
  onHover,
  isSelected = false,
  isPinned = false,
}: EdgeProps) {
  const { size } = useThree();
  const meshRef = useRef<THREE.Mesh>(null);
  const [isHovered, setIsHovered] = useState(false);

  // Calculate curve points
  const points = useMemo(() => {
    const startVec = new THREE.Vector3(...start);
    const endVec = new THREE.Vector3(...end);

    const midY = (start[1] + end[1]) / 2;
    const midPoint = new THREE.Vector3(
      (start[0] + end[0]) / 2,
      midY,
      (start[2] + end[2]) / 2
    );

    const curve = new THREE.CatmullRomCurve3([startVec, midPoint, endVec]);
    return curve.getPoints(20);
  }, [start, end]);

  // Phase 119: Flatten points for meshline
  const flatPoints = useMemo(() => {
    return points.flatMap(p => [p.x, p.y, p.z]);
  }, [points]);

  // Phase 119: Calculate visual properties based on state
  const visualColor = useMemo(() => {
    if (isPinned) return '#4a9eff';  // Blue for pinned
    if (isSelected) return '#d1d5db';  // Light gray for selected
    if (isHovered) return '#9ca3af';  // Medium gray for hover
    return color;
  }, [color, isSelected, isPinned, isHovered]);

  const visualWidth = useMemo(() => {
    if (isPinned || isSelected) return lineWidth * 2;
    if (isHovered) return lineWidth * 1.5;
    return lineWidth;
  }, [lineWidth, isSelected, isPinned, isHovered]);

  const visualOpacity = useMemo(() => {
    if (isPinned || isSelected || isHovered) return Math.min(opacity + 0.2, 1);
    return opacity;
  }, [opacity, isSelected, isPinned, isHovered]);

  // Phase 119: Click handler with modifier key support
  const handleClick = (e: any) => {
    e.stopPropagation();

    if (e.shiftKey && onShiftClick) {
      // Shift+Click = pin edge
      onShiftClick(edgeId, sourceId, targetId);
    } else if (onClick) {
      // Normal click = select edge
      onClick(edgeId);
    }
  };

  // Phase 119: Double-click handler for zoom
  const handleDoubleClick = (e: any) => {
    e.stopPropagation();
    if (onDoubleClick) {
      onDoubleClick(edgeId, sourceId, targetId);
    }
  };

  // Phase 119: Hover handlers
  const handlePointerOver = () => {
    setIsHovered(true);
    onHover?.(edgeId);
  };

  const handlePointerOut = () => {
    setIsHovered(false);
    onHover?.(null);
  };

  return (
    <mesh
      ref={meshRef}
      raycast={raycast}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onPointerOver={handlePointerOver}
      onPointerOut={handlePointerOut}
    >
      {/* @ts-ignore - meshline types */}
      <meshLineGeometry points={flatPoints} />
      {/* @ts-ignore - meshline types */}
      <meshLineMaterial
        lineWidth={visualWidth * 0.015}  // MeshLine uses different scale
        color={visualColor}
        opacity={visualOpacity}
        transparent={true}
        depthTest={true}
        depthWrite={false}
        resolution={[size.width, size.height]}
      />
    </mesh>
  );
}

// Phase 119: Export memoized component with extended comparison
export const Edge = memo(EdgeComponent, (prev, next) => {
  return (
    prev.start[0] === next.start[0] &&
    prev.start[1] === next.start[1] &&
    prev.start[2] === next.start[2] &&
    prev.end[0] === next.end[0] &&
    prev.end[1] === next.end[1] &&
    prev.end[2] === next.end[2] &&
    prev.color === next.color &&
    prev.lineWidth === next.lineWidth &&
    prev.opacity === next.opacity &&
    prev.edgeId === next.edgeId &&
    prev.isSelected === next.isSelected &&
    prev.isPinned === next.isPinned
  );
});
