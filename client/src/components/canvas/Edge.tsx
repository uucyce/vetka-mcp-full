/**
 * Edge - 3D curved line connecting nodes in the tree visualization.
 * Uses Three.js CatmullRomCurve3 for smooth connections.
 *
 * @status active
 * @phase 96
 * @depends react, three, @react-three/drei
 * @used_by TreeEdges
 */

import { useMemo } from 'react';
import * as THREE from 'three';
import { Line } from '@react-three/drei';

interface EdgeProps {
  start: [number, number, number];
  end: [number, number, number];
  color?: string;
  lineWidth?: number;
  opacity?: number;
}

export function Edge({
  start,
  end,
  color = '#4b5563',
  lineWidth = 1.5,
  opacity = 0.6
}: EdgeProps) {
  // MARKER_3D_EDGE_RENDER: Edge component - 3D curved line rendering
  // - Curve: CatmullRomCurve3 with 3 control points (startVec, midPoint, endVec)
  // - Samples: 20 points along curve for smooth rendering
  // - Props: start, end (3D coordinates), color, lineWidth, opacity
  // - Rendering: @react-three/drei Line with depthTest=true, depthWrite=false
  // - Default color: '#4b5563' (dark gray/blue)
  // - For chat edges: Pass color='#4a9eff' (blue) from parent component
  // - Opacity behavior: transparent prop automatically set if opacity < 1

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

  // Phase 54.4: Ensure edges are visible with proper rendering
  return (
    <Line
      points={points}
      color={color}
      lineWidth={lineWidth}
      transparent={opacity < 1}
      opacity={opacity}
      depthTest={true}
      depthWrite={false}
    />
  );
}
