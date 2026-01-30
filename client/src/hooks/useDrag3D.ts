/**
 * Hook for 3D node dragging in the tree visualization.
 * Supports Ctrl/Cmd drag and grab mode for node positioning.
 *
 * @status active
 * @phase 96
 * @depends @react-three/fiber, three, zustand
 * @used_by TreeNode3D, FileCard
 */

import { useRef, useCallback } from 'react';
import { useThree, ThreeEvent } from '@react-three/fiber';
import * as THREE from 'three';
import { useStore } from '../store/useStore';

interface UseDrag3DOptions {
  onDragStart?: () => void;
  onDrag?: (position: THREE.Vector3) => void;
  onDragEnd?: (position: THREE.Vector3) => void;
}

export function useDrag3D(options: UseDrag3DOptions = {}) {
  const { camera, raycaster, pointer } = useThree();
  const isDragging = useRef(false);
  const dragPlane = useRef(new THREE.Plane(new THREE.Vector3(0, 0, 1), 0));
  const intersection = useRef(new THREE.Vector3());
  const offset = useRef(new THREE.Vector3());

  // Phase 65: Get grabMode from store
  const grabMode = useStore((state) => state.grabMode);

  const handlePointerDown = useCallback((e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();

    if (e.button !== 0) return;
    // Phase 65: Ctrl/Cmd+Drag OR grabMode = node movement (was Shift)
    const isDragModifier = e.ctrlKey || e.metaKey || grabMode;
    if (!isDragModifier) return;

    isDragging.current = true;
    (e.target as any)?.setPointerCapture?.(e.pointerId);

    const meshPosition = e.object.position;
    dragPlane.current.setFromNormalAndCoplanarPoint(
      camera.getWorldDirection(new THREE.Vector3()).negate(),
      meshPosition
    );

    raycaster.setFromCamera(pointer, camera);
    raycaster.ray.intersectPlane(dragPlane.current, intersection.current);
    offset.current.copy(meshPosition).sub(intersection.current);

    options.onDragStart?.();
  }, [camera, pointer, raycaster, options, grabMode]);

  const handlePointerMove = useCallback((e: ThreeEvent<PointerEvent>) => {
    if (!isDragging.current) return;

    e.stopPropagation();

    raycaster.setFromCamera(pointer, camera);
    raycaster.ray.intersectPlane(dragPlane.current, intersection.current);

    const newPosition = intersection.current.clone().add(offset.current);
    options.onDrag?.(newPosition);
  }, [camera, pointer, raycaster, options]);

  const handlePointerUp = useCallback((e: ThreeEvent<PointerEvent>) => {
    if (!isDragging.current) return;

    isDragging.current = false;

    (e.target as any)?.releasePointerCapture?.(e.pointerId);

    raycaster.setFromCamera(pointer, camera);
    raycaster.ray.intersectPlane(dragPlane.current, intersection.current);
    const finalPosition = intersection.current.clone().add(offset.current);

    options.onDragEnd?.(finalPosition);
  }, [camera, pointer, raycaster, options]);

  return {
    isDragging: isDragging.current,
    bind: {
      onPointerDown: handlePointerDown,
      onPointerMove: handlePointerMove,
      onPointerUp: handlePointerUp,
    }
  };
}
