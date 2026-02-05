/**
 * InstancedFileCards - GPU-batched rendering for distant nodes (LOD 0-3)
 * Phase 112.5: Hybrid LOD approach
 *
 * - Low LOD (far): InstancedMesh (1-10 draw calls for 1000+ nodes)
 * - High LOD (close): Regular FileCard (full interactivity)
 *
 * @status active
 * @phase 112.5
 * @depends react, @react-three/fiber, three
 */

import { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame, useThree } from '@react-three/fiber';
import type { TreeNode } from '../../store/useStore';

// Atlas configuration
const ATLAS_SIZE = 512;  // Smaller atlas for simple tiles
const TILE_SIZE = 64;

// Card category based on file type
type CardCategory = 'code' | 'doc';

// Determine if file is code or doc based on extension
function getCardCategory(name: string): CardCategory {
  const codeExtensions = ['ts', 'tsx', 'js', 'jsx', 'py', 'json', 'yaml', 'yml', 'sh', 'css', 'html'];
  const ext = name.split('.').pop()?.toLowerCase() || '';
  return codeExtensions.includes(ext) ? 'code' : 'doc';
}

// Generate a single tile for the atlas
function generateTile(category: CardCategory, state: string): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = TILE_SIZE;
  const ctx = canvas.getContext('2d')!;

  // Background based on category (matches FileCard LOD 0-3 visual)
  const isDoc = category === 'doc';
  ctx.fillStyle = isDoc ? '#e8e8e8' : '#1a1a1a';
  ctx.fillRect(0, 0, TILE_SIZE, TILE_SIZE);

  // Border
  ctx.strokeStyle = isDoc ? '#cccccc' : '#333333';
  ctx.lineWidth = 2;
  ctx.strokeRect(1, 1, TILE_SIZE - 2, TILE_SIZE - 2);

  // State overlay
  if (state === 'selected') {
    ctx.fillStyle = 'rgba(0, 255, 136, 0.3)';
    ctx.fillRect(0, 0, TILE_SIZE, TILE_SIZE);
  } else if (state === 'highlighted') {
    ctx.strokeStyle = '#4a9eff';
    ctx.lineWidth = 3;
    ctx.strokeRect(2, 2, TILE_SIZE - 4, TILE_SIZE - 4);
  } else if (state === 'pinned') {
    ctx.fillStyle = 'rgba(255, 204, 0, 0.2)';
    ctx.fillRect(0, 0, TILE_SIZE, TILE_SIZE);
  }

  return canvas;
}

// Generate the full texture atlas (only once)
let cachedAtlas: THREE.CanvasTexture | null = null;

function generateAtlas(): THREE.CanvasTexture {
  if (cachedAtlas) return cachedAtlas;

  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = ATLAS_SIZE;
  const ctx = canvas.getContext('2d')!;
  ctx.imageSmoothingEnabled = false;

  // Fill with transparent
  ctx.clearRect(0, 0, ATLAS_SIZE, ATLAS_SIZE);

  // Generate tiles for each category + state combination
  const categories: CardCategory[] = ['code', 'doc'];
  const states = ['normal', 'selected', 'highlighted', 'pinned'];

  categories.forEach((category, rowIdx) => {
    states.forEach((state, colIdx) => {
      const tile = generateTile(category, state);
      ctx.drawImage(tile, colIdx * TILE_SIZE, rowIdx * TILE_SIZE);
    });
  });

  cachedAtlas = new THREE.CanvasTexture(canvas);
  cachedAtlas.minFilter = THREE.NearestFilter;
  cachedAtlas.magFilter = THREE.NearestFilter;
  cachedAtlas.needsUpdate = true;

  return cachedAtlas;
}

// Props interface
interface InstancedFileCardsProps {
  nodes: TreeNode[];
  selectedId: string | null;
  highlightedId: string | null;
  pinnedIds: string[];
}

export function InstancedFileCards({
  nodes,
  selectedId,
  highlightedId,
  pinnedIds
}: InstancedFileCardsProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const { camera } = useThree();
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const pinnedSet = useMemo(() => new Set(pinnedIds), [pinnedIds]);

  // Shared geometry (code = wider, doc = taller - but for instancing we use uniform)
  const geometry = useMemo(() => new THREE.PlaneGeometry(1.2, 0.8), []);

  // Atlas texture
  const atlasTexture = useMemo(() => generateAtlas(), []);

  // Material with atlas
  const material = useMemo(() => {
    return new THREE.MeshBasicMaterial({
      map: atlasTexture,
      transparent: true,
      side: THREE.DoubleSide,
      alphaTest: 0.1,
    });
  }, [atlasTexture]);

  // Update instance matrices and colors each frame (throttled)
  const lastUpdateRef = useRef(0);

  useFrame((state) => {
    if (!meshRef.current || nodes.length === 0) return;

    const now = state.clock.elapsedTime;
    if (now - lastUpdateRef.current < 0.1) return; // 100ms throttle
    lastUpdateRef.current = now;

    const mesh = meshRef.current;

    nodes.forEach((node, i) => {
      // Position
      dummy.position.set(node.position.x, node.position.y, node.position.z);

      // Billboard - face camera
      dummy.quaternion.copy(camera.quaternion);

      // Scale based on distance (smaller when far)
      const dist = camera.position.distanceTo(dummy.position);
      const scale = Math.max(0.3, Math.min(1.0, 300 / dist));
      dummy.scale.setScalar(scale);

      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);

      // Color tint for type + state
      const isSelected = selectedId === node.id;
      const isHighlighted = highlightedId === node.id;
      const isPinned = pinnedSet.has(node.id);

      // Base color by file type (matches LOD visual)
      const category = node.type === 'folder' ? 'code' : getCardCategory(node.name);
      let color = new THREE.Color(category === 'doc' ? 0xe8e8e8 : 0x2a2a2a);

      // State overlay
      if (isSelected) color.setHex(0x88ff88);
      else if (isHighlighted) color.setHex(0x88aaff);
      else if (isPinned) color.lerp(new THREE.Color(0xffdd88), 0.3);

      mesh.setColorAt(i, color);
    });

    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    mesh.count = nodes.length;
  });

  // Cleanup
  // Note: geometry and material are memoized, will be GC'd when component unmounts

  if (nodes.length === 0) return null;

  return (
    <instancedMesh
      ref={meshRef}
      args={[geometry, material, Math.max(nodes.length, 100)]}
      frustumCulled={false}  // We handle culling in parent
    />
  );
}

export default InstancedFileCards;
