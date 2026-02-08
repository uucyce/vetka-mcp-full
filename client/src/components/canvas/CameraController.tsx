/**
 * Camera Controller - Phase 52.6
 * Handles camera animations and focus based on commands from the store.
 *
 * @file CameraController.tsx
 * @status ACTIVE
 * @phase Phase 52.6 - Simple Smooth Camera Movement
 * @lastUpdate 2026-01-07
 *
 * Features:
 * - Simple direct camera movement (no 3-phase complexity)
 * - Smooth ease-in-out transitions
 * - Always frontal approach to target
 * - OrbitControls synchronization
 * - Context switch on camera focus
 */

import { useEffect, useRef } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useStore } from '../../store/useStore';

// Global reference to OrbitControls (set in App.tsx)
declare global {
  interface Window {
    __orbitControls?: any;
  }
}

// [PHASE70-M2] CameraController.tsx: Set camera ref — IMPLEMENTED

export function CameraController() {
  const { camera } = useThree();
  const cameraCommand = useStore((state) => state.cameraCommand);
  const setCameraCommand = useStore((state) => state.setCameraCommand);
  const nodes = useStore((state) => state.nodes);
  const selectNode = useStore((state) => state.selectNode);
  const highlightNode = useStore((state) => state.highlightNode);
  // Phase 70: Camera ref setter for viewport context
  const setCameraRef = useStore((state) => state.setCameraRef);

  const animationRef = useRef<{
    active: boolean;
    startPos: THREE.Vector3;
    targetPos: THREE.Vector3;
    startQuaternion: THREE.Quaternion;
    targetQuaternion: THREE.Quaternion;
    lookAt: THREE.Vector3;
    progress: number;
    nodeId: string;
  } | null>(null);

  // Helper to find node by path or name
  const findNode = (target: string): [string, typeof nodes[string]] | null => {
    // 1. Exact path match
    let entry = Object.entries(nodes).find(([_, n]) => n.path === target);
    if (entry) {
      // console.log('[CameraController] Found by exact path:', entry[1].name);
      return entry as [string, typeof nodes[string]];
    }

    // 2. Filename match (main.py → /full/path/main.py)
    entry = Object.entries(nodes).find(([_, n]) =>
      n.path?.endsWith('/' + target) || n.name === target
    );
    if (entry) {
      // console.log('[CameraController] Found by filename:', entry[1].name);
      return entry as [string, typeof nodes[string]];
    }

    // 3. Partial path match (docs/file.md → /full/path/docs/file.md)
    entry = Object.entries(nodes).find(([_, n]) =>
      n.path?.includes(target)
    );
    if (entry) {
      // console.log('[CameraController] Found by partial path:', entry[1].name);
      return entry as [string, typeof nodes[string]];
    }

    return null;
  };

  // Phase 54.4: Handle camera-fly-to-folder event from global drag & drop
  useEffect(() => {
    const handleFlyToFolder = (e: CustomEvent<{ folderName: string; filesCount: number }>) => {
      const { folderName } = e.detail;
      // console.log(`[CameraController] Fly to folder: ${folderName} (${filesCount} files)`);

      // Try to find the folder node in the tree
      const nodeEntry = findNode(folderName);
      if (nodeEntry) {
        // Use store to trigger camera animation
        useStore.getState().setCameraCommand({
          target: folderName,
          zoom: 'medium',
          highlight: true
        });
      } else {
        // Folder not yet in tree - just zoom out to see new content
        // console.log('[CameraController] Folder not in tree yet, zooming to root');
        // Optionally fly to root or just leave camera as is
      }
    };

    window.addEventListener('camera-fly-to-folder', handleFlyToFolder as EventListener);
    return () => {
      window.removeEventListener('camera-fly-to-folder', handleFlyToFolder as EventListener);
    };
  }, [nodes]);

  // Phase 70: Set camera ref in store for viewport context
  useEffect(() => {
    setCameraRef(camera as THREE.PerspectiveCamera);
    console.log('[VIEWPORT] Camera ref set');

    return () => {
      setCameraRef(null);
      console.log('[VIEWPORT] Camera ref cleared');
    };
  }, [camera, setCameraRef]);

  // Handle camera commands
  useEffect(() => {
    if (!cameraCommand) return;

    console.log('[CameraController] Processing command:', cameraCommand);

    // Find node by path or name
    const nodeEntry = findNode(cameraCommand.target);

    if (!nodeEntry) {
      console.warn('[CameraController] Node not found:', cameraCommand.target);
      setCameraCommand(null);
      return;
    }

    const [nodeId, node] = nodeEntry;

    // Highlight the node immediately
    if (cameraCommand.highlight) {
      highlightNode(nodeId);
      setTimeout(() => highlightNode(null), 3000);
    }

    // Target node position
    const nodePos = new THREE.Vector3(
      node.position.x,
      node.position.y,
      node.position.z
    );

    // Final distance based on zoom (Phase 52.6.3: increased for comfortable view)
    // MARKER_124.2A: Phase 124.2 - Adjusted medium to 70 for better overview on new files
    const finalDistance = cameraCommand.zoom === 'close' ? 30
                        : cameraCommand.zoom === 'medium' ? 70 : 100;

    // Phase 52.6.2: Simple frontal positioning (ALWAYS approach from Z+ direction)
    // MARKER_124.2B: Phase 124.2 - Subtle elevation, no tilt (space for preview popup)
    const targetPos = new THREE.Vector3(
      nodePos.x,
      nodePos.y + 5,  // Subtle: just enough for preview space below
      nodePos.z + finalDistance  // In front on Z axis
    );

    // console.log('[CameraController] Simple animation:');
    // console.log('  Node:', node.name);
    // console.log('  Node position:', nodePos);
    // console.log('  Target camera:', targetPos);
    // console.log('  Distance:', finalDistance);

    // Calculate target camera orientation (looking at node)
    const tempCamera = camera.clone();
    tempCamera.position.copy(targetPos);
    tempCamera.lookAt(nodePos);

    // Phase 52.6.3: Disable OrbitControls during animation to prevent conflicts
    const controls = window.__orbitControls;
    if (controls) {
      controls.enabled = false;
      // CRITICAL: Adjust minDistance to allow close zoom
      controls.minDistance = 10;
      // console.log('[CameraController] OrbitControls disabled for animation, minDistance set to 10');
    }

    // Setup smooth animation with quaternion interpolation
    animationRef.current = {
      active: true,
      startPos: camera.position.clone(),
      targetPos,
      startQuaternion: camera.quaternion.clone(),
      targetQuaternion: tempCamera.quaternion.clone(),
      lookAt: nodePos.clone(),
      progress: 0,
      nodeId
    };

    // Clear command after setup
    setCameraCommand(null);
  }, [cameraCommand, nodes, selectNode, highlightNode, setCameraCommand]);

  // Simple smooth animation with quaternion slerp
  useFrame((_, delta) => {
    if (!animationRef.current?.active) return;

    const anim = animationRef.current;

    // Progress speed (2.5s total animation - slightly slower for smoothness)
    anim.progress = Math.min(anim.progress + delta * 0.4, 1);

    const t = anim.progress;

    // Ease-in-out interpolation (smoother curve)
    const eased = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

    // Interpolate position
    const currentPos = new THREE.Vector3().lerpVectors(
      anim.startPos,
      anim.targetPos,
      eased
    );

    // Interpolate rotation (quaternion slerp for smooth rotation)
    const currentQuat = new THREE.Quaternion().slerpQuaternions(
      anim.startQuaternion,
      anim.targetQuaternion,
      eased
    );

    // Update camera
    camera.position.copy(currentPos);
    camera.quaternion.copy(currentQuat);

    // Animation complete
    if (anim.progress >= 1.0) {
      // console.log('[CameraController] Animation complete');

      // Re-enable OrbitControls and sync target
      const controls = window.__orbitControls;
      if (controls) {
        controls.target.copy(anim.lookAt);
        controls.enabled = true;
        controls.update();
        // console.log('[CameraController] OrbitControls re-enabled and synced');
      }

      // Switch chat context
      selectNode(anim.nodeId);
      // console.log('[CameraController] Context switched to:', anim.nodeId);

      // Stop animation (camera already at target from last frame)
      animationRef.current = null;
    }
  });

  return null; // This component only handles logic, no visual output
}
