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
