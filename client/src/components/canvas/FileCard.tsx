/**
 * FileCard - 3D card component for files and folders in the canvas view.
 * Implements Google Maps style LOD system with 10 levels of detail.
 * Supports hover preview, drag-to-move (Ctrl+drag), and Shift+Click pinning.
 *
 * @status active
 * @phase 96
 * @depends react, @react-three/fiber, @react-three/drei, three, zustand
 * @used_by Scene
 */

import { useRef, useMemo, useState, useCallback, useEffect, memo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import { useStore } from '../../store/useStore';

/**
 * LOD Levels (Google Maps style - 10 levels for smooth transitions):
 *
 * LOD 0 (distance > 300): Tiny dot - minimal rendering
 * LOD 1 (distance 200-300): Small shape - code/doc visible by form
 * LOD 2 (distance 150-200): Shape + file name starting to appear
 * LOD 3 (distance 100-150): Clear shape + visible file name
 * LOD 4 (distance 70-100): Larger card + clear name
 * LOD 5 (distance 50-70): Mini preview starts (3-5 lines)
 * LOD 6 (distance 35-50): Mini preview full
 * LOD 7 (distance 20-35): Large preview
 * LOD 8 (distance 10-20): Full preview
 * LOD 9 (distance < 10): Ultra close - full detail + extras
 *
 * File names: Always visible at TOP of card
 * Folder names: Floating labels only (Google Maps style)
 */

// Global cache for preview content (persists across component instances)
const previewCache = new Map<string, string>();

// Phase 112.4: Global texture cache to avoid regeneration when nodes re-enter viewport
// Key: "id:lodLevel:isSelected:isHighlighted" - only regenerate on meaningful changes
// Limit: 500 textures max to prevent memory bloat
const textureCache = new Map<string, THREE.CanvasTexture>();
const TEXTURE_CACHE_MAX = 500;

function getTextureCacheKey(
  id: string,
  lodLevel: number,
  isSelected: boolean,
  isHighlighted: boolean,
  artifactStatus?: string
): string {
  return `${id}:${lodLevel}:${isSelected ? 1 : 0}:${isHighlighted ? 1 : 0}:${artifactStatus || ''}`;
}

function cacheTexture(key: string, texture: THREE.CanvasTexture): void {
  // LRU-style: if at max, delete oldest entries
  if (textureCache.size >= TEXTURE_CACHE_MAX) {
    const firstKey = textureCache.keys().next().value;
    if (firstKey) {
      const oldTex = textureCache.get(firstKey);
      oldTex?.dispose();
      textureCache.delete(firstKey);
    }
  }
  textureCache.set(key, texture);
}

// Inject fade-in animation styles once
if (typeof document !== 'undefined' && !document.getElementById('preview-fade-styles')) {
  const style = document.createElement('style');
  style.id = 'preview-fade-styles';
  style.textContent = `
    @keyframes previewFadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `;
  document.head.appendChild(style);
}

/**
 * Determine file category for preview styling
 * @returns 'code' for programming files, 'doc' for documents
 */
const getFileCategory = (name: string): 'code' | 'doc' => {
  const codeExtensions = [
    'py', 'js', 'ts', 'tsx', 'jsx', 'json', 'yaml', 'yml',
    'sh', 'bash', 'css', 'scss', 'less', 'html', 'xml',
    'sql', 'java', 'cpp', 'c', 'h', 'hpp', 'go', 'rs',
    'rb', 'php', 'swift', 'kt', 'scala', 'vue', 'svelte'
  ];
  const ext = name.split('.').pop()?.toLowerCase() || '';
  return codeExtensions.includes(ext) ? 'code' : 'doc';
};

/**
 * Check if file is previewable (text-based)
 * Skip binary files like images, videos, fonts, etc.
 */
const isPreviewableFile = (name: string): boolean => {
  const binaryExtensions = [
    // Images
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'ico', 'svg', 'webp', 'tiff',
    // Videos
    'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv',
    // Audio
    'mp3', 'wav', 'ogg', 'flac', 'aac',
    // Fonts
    'ttf', 'otf', 'woff', 'woff2', 'eot',
    // Archives
    'zip', 'tar', 'gz', 'rar', '7z',
    // Binary
    'exe', 'dll', 'so', 'dylib', 'bin', 'dat',
    // Documents (non-text)
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    // Other
    'db', 'sqlite', 'pyc', 'class', 'o', 'a'
  ];
  const ext = name.split('.').pop()?.toLowerCase() || '';
  return !binaryExtensions.includes(ext);
};

/**
 * Hover preview styles
 */
const hoverPreviewStyles = {
  code: {
    background: '#1e1e1e',
    color: '#d4d4d4',
    fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace",
    borderRadius: '6px',
    overflow: 'hidden',
    boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
    border: '1px solid #333',
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-all' as const,
    width: 400,
    height: 300,
    fontSize: '11px',
    lineHeight: '1.3',
    padding: '12px',
  },
  doc: {
    background: '#fafafa',
    color: '#333',
    fontFamily: "'Georgia', 'Times New Roman', serif",
    borderRadius: '6px',
    overflow: 'hidden',
    boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
    border: '1px solid #e0e0e0',
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
    width: 350,
    height: 400,
    fontSize: '13px',
    lineHeight: '1.5',
    padding: '14px',
  },
};

function getBorderColor(
  isSelected: boolean,
  isDragging: boolean,
  isHighlighted: boolean,
  isPinned: boolean = false
): string {
  // Phase 61: Pinned files get blue border
  if (isPinned) return '#4a9eff';
  if (isDragging) return '#666666';
  if (isSelected) return '#888888';
  if (isHighlighted) return '#777777';
  return '#444444';
}

interface FileCardProps {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'folder' | 'chat' | 'artifact';
  position: [number, number, number];
  isSelected?: boolean;
  isHighlighted?: boolean;
  onClick?: () => void;
  // Phase 62: Children IDs for folder priority calculation
  children?: string[];
  // Phase 62.2: Depth for LOD importance scoring (Grok research)
  depth?: number;
  // MARKER_108_3_CHAT_METADATA: Phase 108.3 - Chat node metadata
  metadata?: {
    chat_id?: string; // Added for Phase 108.3
    message_count?: number;
    participants?: string[];
    decay_factor?: number;
    last_activity?: string;
    context_type?: string;
  };
  visual_hints?: {
    color?: string;
    opacity?: number;
  };
  // MARKER_108_ARTIFACT_VIZ: Phase 108.2 - Artifact metadata
  artifactType?: 'code' | 'document' | 'image' | 'data';
  artifactStatus?: 'streaming' | 'done' | 'error' | 'pending' | 'approved' | 'rejected';
  artifactProgress?: number; // 0-100
  // Phase 90.11 + Phase 108.3: Node opacity
  opacity?: number;
  // MARKER_108_4_APPROVE_UI: Phase 108.4 - Artifact approval metadata
  artifactId?: string;
  // MARKER_111.21_USEFRAME: Phase 112.3 - LOD level from parent (batch calculation)
  // If provided, skip internal LOD calculation (saves 2000+ distance calcs per frame)
  lodLevel?: number;
  // Phase 113.4: Label Championship — score-based label visibility
  showLabel?: boolean;
  // MARKER_119.2I: Phase 119.2 - Heat score for size scaling
  heatScore?: number;  // 0.0-1.0, from file watcher activity
}

function FileCardComponent({
  id,
  name,
  path,
  type,
  position,
  isSelected = false,
  isHighlighted = false,
  onClick,
  children = [],
  depth = 0,
  metadata = {},
  visual_hints = {},
  artifactType = 'code',
  artifactStatus = 'done',
  artifactProgress = 0,
  opacity = 1.0,
  artifactId,
  lodLevel: propLodLevel,  // Phase 112.3: LOD from parent (undefined = calculate locally)
  showLabel = false,       // Phase 113.4: Label Championship — score-based visibility
  heatScore = 0,           // Phase 119.2: Heat score for size scaling
}: FileCardProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  // Phase 61.1: Preview state
  const [isHoveredDebounced, setIsHoveredDebounced] = useState(false);
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  // Phase 62: LOD state
  // MARKER_111.21_USEFRAME: Phase 112.3 - Use prop if provided, else internal state
  const [internalLodLevel, setInternalLodLevel] = useState(0);
  const lodLevel = propLodLevel ?? internalLodLevel;  // Prefer parent-calculated LOD
  const lastLodUpdate = useRef(0);
  const { camera } = useThree();

  const updateNodePosition = useStore((state) => state.updateNodePosition);
  const moveNodeWithChildren = useStore((state) => state.moveNodeWithChildren);
  const setDraggingAny = useStore((state) => state.setDraggingAny);

  // Phase 61: Pinned files
  const isPinned = useStore((state) => state.pinnedFileIds.includes(id));
  // Phase 65: Smart pin (file → toggle, folder → subtree)
  const pinNodeSmart = useStore((state) => state.pinNodeSmart);
  // Phase 65: Grab mode for Blender-style drag
  const grabMode = useStore((state) => state.grabMode);
  // Phase 118.2: Camera command for double-click zoom
  const setCameraCommand = useStore((state) => state.setCameraCommand);

  const dragPlane = useRef(new THREE.Plane());
  const dragOffset = useRef(new THREE.Vector3());
  const intersection = useRef(new THREE.Vector3());

  // Phase 113.2: Smooth Drag Physics — spring refs
  const dragVelocity = useRef(new THREE.Vector3(0, 0, 0));
  const dragTarget = useRef(new THREE.Vector3(position[0], position[1], position[2]));
  const isSettling = useRef(false);
  const lastStoreSyncTime = useRef(0);

  // MARKER_108_3_SOCKETIO_UPDATE: Phase 108.3 - Smooth opacity animation
  const targetOpacity = useRef(opacity ?? 1.0);
  const currentOpacity = useRef(opacity ?? 1.0);

  useFrame((state) => {
    // Billboard effect - face camera
    if (meshRef.current) {
      meshRef.current.quaternion.copy(state.camera.quaternion);

      // MARKER_108_3_SOCKETIO_UPDATE: Phase 108.3 - Animate opacity changes smoothly
      // Lerp towards target opacity for smooth transition (0.1 = 10% per frame)
      targetOpacity.current = opacity ?? 1.0;
      const opacityDelta = targetOpacity.current - currentOpacity.current;

      if (Math.abs(opacityDelta) > 0.001) {
        currentOpacity.current += opacityDelta * 0.1; // Smooth lerp
        const material = meshRef.current.material as THREE.MeshBasicMaterial;
        if (material) {
          material.opacity = currentOpacity.current;
          material.needsUpdate = true;
        }
      }

      // Phase 113.2: Smooth Drag Physics — spring follow + settle
      if (isDragging || isSettling.current) {
        const current = meshRef.current.position;
        const target = dragTarget.current;
        const dx = target.x - current.x;
        const dy = target.y - current.y;
        const dz = target.z - current.z;
        const distSq = dx * dx + dy * dy + dz * dz;

        if (distSq > 0.0001) {
          // Spring force: k=0.12 (smooth), friction=0.92 (anti-tremble)
          // Tuned per Grok feedback: higher friction prevents oscillation
          dragVelocity.current.x += dx * 0.12;
          dragVelocity.current.y += dy * 0.12;
          dragVelocity.current.z += dz * 0.12;
          dragVelocity.current.multiplyScalar(0.92);

          // Velocity clamp: prevent overshoot trembling at any frame rate
          const MAX_VEL = 2.0;
          dragVelocity.current.x = Math.max(-MAX_VEL, Math.min(MAX_VEL, dragVelocity.current.x));
          dragVelocity.current.y = Math.max(-MAX_VEL, Math.min(MAX_VEL, dragVelocity.current.y));
          dragVelocity.current.z = Math.max(-MAX_VEL, Math.min(MAX_VEL, dragVelocity.current.z));

          current.x += dragVelocity.current.x;
          current.y += dragVelocity.current.y;
          current.z += dragVelocity.current.z;

          // Throttled store sync during drag (every 100ms)
          const now = state.clock.elapsedTime;
          if (now - lastStoreSyncTime.current > 0.1) {
            const pos = { x: current.x, y: current.y, z: current.z };
            if (type === 'folder') {
              moveNodeWithChildren(id, pos);
            } else {
              updateNodePosition(id, pos);
            }
            lastStoreSyncTime.current = now;
          }
        } else {
          // Settled — snap to target and stop
          current.copy(target);
          dragVelocity.current.set(0, 0, 0);

          if (isSettling.current) {
            isSettling.current = false;
            // Final sync to store
            const pos = { x: current.x, y: current.y, z: current.z };
            if (type === 'folder') {
              moveNodeWithChildren(id, pos);
            } else {
              updateNodePosition(id, pos);
            }
          }
        }
      }
    }

    // MARKER_111.21_USEFRAME: Phase 112.3 - Batch LOD DONE
    // If propLodLevel is provided, skip local calculation (parent handles it)
    // This saves 2000+ distance calculations per throttle cycle
    if (propLodLevel !== undefined) return;

    // Fallback: Calculate LOD locally if parent doesn't provide it
    const now = state.clock.elapsedTime;
    if (now - lastLodUpdate.current < 0.1) return;
    lastLodUpdate.current = now;

    const dist = camera.position.distanceTo(
      new THREE.Vector3(position[0], position[1], position[2])
    );

    // 10 LOD levels - preview ONLY when close, cards visible from far
    let newLod = 0;
    if (dist < 20) newLod = 9;         // Ultra close - full detail
    else if (dist < 40) newLod = 8;    // Very close - full preview
    else if (dist < 70) newLod = 7;    // Close - large preview
    else if (dist < 100) newLod = 6;   // Medium close - medium preview
    else if (dist < 150) newLod = 5;   // Medium - mini preview starts HERE
    else if (dist < 400) newLod = 4;   // Medium far - card only (NO preview)
    else if (dist < 800) newLod = 3;   // Far - shape + name visible
    else if (dist < 1500) newLod = 2;  // Farther - shape visible
    else if (dist < 2500) newLod = 1;  // Very far - small shape
    else newLod = 0;                    // Extra wide - tiny dot (>2500)

    if (newLod !== internalLodLevel) {
      setInternalLodLevel(newLod);
    }
  });

  // Phase 61.1: Debounce hover to prevent spam loading
  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;

    if (isHovered && type === 'file') {
      // Delay preview load by 300ms
      timeout = setTimeout(() => setIsHoveredDebounced(true), 300);
    } else {
      setIsHoveredDebounced(false);
      // Clear content when unhovered to save memory
      setPreviewContent(null);
    }

    return () => clearTimeout(timeout);
  }, [isHovered, type]);

  // Phase 62: Load file content for preview (at LOD 3+ - when card is visible)
  // Trigger: LOD >= 3 (card visible) OR hovered, only for previewable files
  const shouldLoadContent = (lodLevel >= 3 || isHoveredDebounced) && type === 'file' && isPreviewableFile(name);

  useEffect(() => {
    if (!shouldLoadContent) return;

    // Check cache first
    const cacheKey = path || id;
    if (previewCache.has(cacheKey)) {
      setPreviewContent(previewCache.get(cacheKey)!);
      return;
    }

    // Don't reload if already loading or have content
    if (loadingPreview || previewContent) return;

    const loadContent = async () => {
      setLoadingPreview(true);

      try {
        const response = await fetch('/api/files/read', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path }),
        });

        if (response.ok) {
          const data = await response.json();
          // Take first ~2000 chars for preview
          const content = data.content?.slice(0, 2000) || '';
          setPreviewContent(content);
          previewCache.set(cacheKey, content);
        } else {
          // Fallback: show file info
          const fallback = `// ${name}\n// Path: ${path}\n// Preview unavailable`;
          setPreviewContent(fallback);
          previewCache.set(cacheKey, fallback);
        }
      } catch (error) {
        const fallback = `// ${name}\n// Preview unavailable`;
        setPreviewContent(fallback);
        previewCache.set(cacheKey, fallback);
      } finally {
        setLoadingPreview(false);
      }
    };

    loadContent();
  }, [shouldLoadContent, path, id, name, type, loadingPreview, previewContent]);

  // Phase 62: Determine file category for card styling
  // Phase 108.2: Chat nodes get 'chat' category, Artifact nodes get 'artifact' category
  const cardCategory = type === 'chat' ? 'chat' : type === 'artifact' ? 'artifact' : (type === 'file' ? getFileCategory(name) : 'folder');

  // Phase 62: Card dimensions based on type
  // Code: horizontal (16:9), Doc: vertical (3:4), Folder: square-ish, Chat: horizontal like code
  // MARKER_108_ARTIFACT_VIZ: Artifact cards are smaller than chat cards
  const getCardSize = (): [number, number] => {
    if (type === 'folder') return [10, 8];
    if (type === 'chat') return [14, 8];  // Phase 108.2: Chat cards horizontal like code
    if (type === 'artifact') return [10, 6];  // Phase 108.2: Artifact cards smaller
    return cardCategory === 'code' ? [14, 8] : [8, 12];  // horizontal vs vertical
  };
  const cardSize = getCardSize();

  // MARKER_111.21_TEXTURE: Phase 112.4 - Texture caching DONE
  // Uses global textureCache to avoid regeneration when nodes re-enter viewport
  // Cache key: id + lodLevel + selection state (NOT hover/drag - those use material opacity)
  // Result: ~10x fewer texture generations during camera movement
  const texture = useMemo(() => {
    // Phase 112.4: Check cache first
    const cacheKey = getTextureCacheKey(id, lodLevel, isSelected, isHighlighted, artifactStatus);
    const cached = textureCache.get(cacheKey);
    if (cached) {
      return cached; // Cache hit - skip canvas generation!
    }
    const canvas = document.createElement('canvas');
    // Adjust canvas aspect ratio based on card type
    const isVertical = type === 'file' && cardCategory === 'doc';
    const isArtifact = type === 'artifact';
    canvas.width = isVertical ? 128 : isArtifact ? 200 : 256;
    canvas.height = isVertical ? 192 : isArtifact ? 96 : 128;
    const ctx = canvas.getContext('2d')!;
    const w = canvas.width;
    const h = canvas.height;

    // Clear canvas with transparency for folders
    ctx.clearRect(0, 0, w, h);

    // MARKER_108_ARTIFACT_VIZ: Phase 108.2 - Artifact node rendering
    // MARKER_108_4_APPROVE_UI: Phase 108.4 - Status-based visual feedback
    if (type === 'artifact') {
      // Get artifact-specific colors based on status
      let bgColor: string;
      let statusColor: string;
      let borderColorOverride: string | null = null;

      if (artifactStatus === 'error') {
        bgColor = '#ef4444'; // Red for error
        statusColor = '#dc2626';
      } else if (artifactStatus === 'streaming') {
        bgColor = '#4a9eff'; // Blue with animation
        statusColor = '#3b82f6';
      } else if (artifactStatus === 'pending') {
        // MARKER_108_4_APPROVE_UI: Pending = yellow
        bgColor = '#f59e0b'; // Yellow/amber for pending
        statusColor = '#d97706';
        borderColorOverride = '#fbbf24'; // Brighter yellow border
      } else if (artifactStatus === 'approved') {
        // MARKER_108_4_APPROVE_UI: Approved = green
        bgColor = '#10b981'; // Green for approved
        statusColor = '#059669';
        borderColorOverride = '#34d399'; // Brighter green border
      } else if (artifactStatus === 'rejected') {
        // MARKER_108_4_APPROVE_UI: Rejected = red
        bgColor = '#ef4444'; // Red for rejected
        statusColor = '#dc2626';
        borderColorOverride = '#f87171'; // Brighter red border
      } else {
        bgColor = '#4a9eff'; // Solid blue for done
        statusColor = '#2563eb';
      }

      // Apply opacity and selection state
      const artifactOpacity = visual_hints?.opacity ?? 1.0;
      if (isSelected) bgColor = statusColor;
      if (isHovered && artifactStatus !== 'error') bgColor = '#3b82f6';

      // Background with rounded corners
      ctx.fillStyle = bgColor;
      ctx.globalAlpha = artifactOpacity;
      ctx.beginPath();
      ctx.roundRect(0, 0, w, h, 6);
      ctx.fill();
      ctx.globalAlpha = 1.0;

      // Border (use status-specific color if available)
      const borderColor = borderColorOverride ?? getBorderColor(isSelected, isDragging, isHighlighted, isPinned);
      ctx.strokeStyle = borderColor;
      ctx.lineWidth = isPinned ? 3 : (isDragging ? 2 : (artifactStatus === 'pending' ? 3 : 2));
      ctx.beginPath();
      ctx.roundRect(0, 0, w, h, 6);
      ctx.stroke();

      // Artifact type icon at top-left
      ctx.font = '18px Arial';
      ctx.fillStyle = '#ffffff';
      const iconMap = {
        code: '📄',
        document: '📝',
        image: '🖼️',
        data: '📊',
      };
      ctx.fillText(iconMap[artifactType] || '📄', 6, 22);

      // Artifact name at top (next to icon)
      ctx.font = 'bold 12px Arial';
      ctx.fillStyle = '#ffffff';
      const maxNameLen = 14;
      const displayName = name.length > maxNameLen ? name.slice(0, maxNameLen - 3) + '...' : name;
      ctx.fillText(displayName, 30, 18);

      // MARKER_108_4_APPROVE_UI: Status indicator at LOD 5+ with approval states
      if (lodLevel >= 5) {
        ctx.font = '10px Arial';
        ctx.fillStyle = 'rgba(255,255,255,0.9)';
        const statusText =
          artifactStatus === 'streaming' ? 'Streaming...' :
          artifactStatus === 'error' ? 'Error' :
          artifactStatus === 'pending' ? 'Pending Review' :
          artifactStatus === 'approved' ? '✓ Approved' :
          artifactStatus === 'rejected' ? '✗ Rejected' : 'Done';
        ctx.fillText(statusText, 6, 38);
      }

      // Progress bar for streaming status at LOD 5+
      if (lodLevel >= 5 && artifactStatus === 'streaming' && artifactProgress !== undefined) {
        const barX = 6;
        const barY = h - 16;
        const barW = w - 12;
        const barH = 8;

        // Background bar
        ctx.fillStyle = 'rgba(255,255,255,0.2)';
        ctx.beginPath();
        ctx.roundRect(barX, barY, barW, barH, 4);
        ctx.fill();

        // Progress fill
        const fillW = (barW * artifactProgress) / 100;
        ctx.fillStyle = 'rgba(255,255,255,0.9)';
        ctx.beginPath();
        ctx.roundRect(barX, barY, fillW, barH, 4);
        ctx.fill();

        // Percentage text
        ctx.font = '9px Arial';
        ctx.fillStyle = '#ffffff';
        ctx.fillText(`${Math.round(artifactProgress)}%`, barX + barW + 4, barY + 7);
      }

      // Pin indicator
      if (isPinned) {
        ctx.font = '12px Arial';
        ctx.fillStyle = '#ffffff';
        ctx.fillText('📌', w - 22, 20);
      }

      // Drag indicator
      if (isDragging) {
        ctx.font = '14px Arial';
        ctx.fillStyle = 'rgba(255,255,255,0.8)';
        ctx.fillText('✋', w - 22, 40);
      }

      // Pulsing animation for streaming status (visual indicator)
      if (artifactStatus === 'streaming') {
        // Draw pulsing ring effect
        const pulseOpacity = 0.3 + 0.2 * Math.sin(Date.now() / 400);
        ctx.strokeStyle = `rgba(255,255,255,${pulseOpacity})`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(2, 2, w - 4, h - 4, 6);
        ctx.stroke();
      }
    } else if (type === 'chat') {
      // MARKER_108_CHAT_CARD: Phase 108.2 - Chat node rendering
      // Chat node rendering with blue theme
      const chatOpacity = visual_hints?.opacity ?? 1.0;
      const bgColor = isSelected ? '#3a7acc' : isHovered ? '#4a88dd' : '#4a9eff';

      // Background with rounded corners
      ctx.fillStyle = bgColor;
      ctx.globalAlpha = chatOpacity;
      ctx.beginPath();
      ctx.roundRect(0, 0, w, h, 8);
      ctx.fill();
      ctx.globalAlpha = 1.0;

      // Border
      const borderColor = getBorderColor(isSelected, isDragging, isHighlighted, isPinned);
      ctx.strokeStyle = borderColor;
      ctx.lineWidth = isPinned ? 3 : (isDragging ? 3 : 2);
      ctx.beginPath();
      ctx.roundRect(0, 0, w, h, 8);
      ctx.stroke();

      // Chat icon (speech bubble) at top-left
      ctx.font = '20px Arial';
      ctx.fillStyle = '#ffffff';
      ctx.fillText('\uD83D\uDCAC', 8, 26);  // 💬 emoji

      // Chat name at top (next to icon)
      ctx.font = 'bold 14px Arial';
      ctx.fillStyle = '#ffffff';
      const maxNameLen = 16;
      const displayName = name.length > maxNameLen ? name.slice(0, maxNameLen - 3) + '...' : name;
      ctx.fillText(displayName, 36, 20);

      // Message count badge at LOD 5+
      if (lodLevel >= 5 && metadata?.message_count !== undefined) {
        ctx.font = '12px Arial';
        ctx.fillStyle = 'rgba(255,255,255,0.9)';
        ctx.fillText(`${metadata.message_count} msgs`, 8, 46);
      }

      // Participants at LOD 7+
      if (lodLevel >= 7 && metadata?.participants && metadata.participants.length > 0) {
        ctx.font = '10px Arial';
        ctx.fillStyle = 'rgba(255,255,255,0.8)';
        const participantText = metadata.participants.slice(0, 3).join(', ');
        const maxParticipantLen = 28;
        const displayParticipants = participantText.length > maxParticipantLen
          ? participantText.slice(0, maxParticipantLen - 3) + '...'
          : participantText;
        ctx.fillText(displayParticipants, 8, 64);
      }

      // Pin indicator
      if (isPinned) {
        ctx.font = '14px Arial';
        ctx.fillStyle = '#ffffff';
        ctx.fillText('\uD83D\uDCCC', w - 28, 26);
      }

      // Drag indicator
      if (isDragging) {
        ctx.font = '16px Arial';
        ctx.fillStyle = 'rgba(255,255,255,0.8)';
        ctx.fillText('\u270B', w - 28, 50);
      }
    } else if (type === 'folder') {
      // Phase 62: Draw stylized FOLDER ICON with alpha channel (no square background)
      const folderColor = isSelected ? '#606060' : isHovered ? '#505050' : '#404040';
      const folderHighlight = isSelected ? '#707070' : isHovered ? '#606060' : '#505050';

      // Folder body (main rectangle with rounded corners)
      const bodyX = w * 0.1;
      const bodyY = h * 0.35;
      const bodyW = w * 0.8;
      const bodyH = h * 0.55;

      ctx.fillStyle = folderColor;
      ctx.beginPath();
      ctx.roundRect(bodyX, bodyY, bodyW, bodyH, 8);
      ctx.fill();

      // Folder tab (top part)
      const tabW = bodyW * 0.4;
      const tabH = h * 0.15;
      ctx.fillStyle = folderHighlight;
      ctx.beginPath();
      ctx.moveTo(bodyX, bodyY);
      ctx.lineTo(bodyX, bodyY - tabH * 0.6);
      ctx.quadraticCurveTo(bodyX, bodyY - tabH, bodyX + 8, bodyY - tabH);
      ctx.lineTo(bodyX + tabW - 8, bodyY - tabH);
      ctx.quadraticCurveTo(bodyX + tabW, bodyY - tabH, bodyX + tabW + 8, bodyY - tabH * 0.3);
      ctx.lineTo(bodyX + tabW + 16, bodyY);
      ctx.closePath();
      ctx.fill();

      // Folder edge highlight (subtle 3D effect)
      ctx.strokeStyle = 'rgba(255,255,255,0.1)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(bodyX + 4, bodyY + bodyH - 4);
      ctx.lineTo(bodyX + 4, bodyY + 4);
      ctx.lineTo(bodyX + bodyW - 4, bodyY + 4);
      ctx.stroke();

      // Pin indicator for folders
      if (isPinned) {
        ctx.fillStyle = '#4a9eff';
        ctx.beginPath();
        ctx.arc(bodyX + bodyW - 15, bodyY + 15, 8, 0, Math.PI * 2);
        ctx.fill();
      }
    } else {
      // FILE rendering (unchanged)
      let bgColor: string;
      if (cardCategory === 'code') {
        bgColor = isSelected ? '#404050' : isHovered ? '#353545' : '#2a2a35';
      } else {
        bgColor = isSelected ? '#e8e8e8' : isHovered ? '#f5f5f5' : '#ffffff';
      }

      ctx.fillStyle = bgColor;
      ctx.beginPath();
      ctx.roundRect(0, 0, w, h, 8);
      ctx.fill();

      // Border (Phase 61: blue for pinned)
      const borderColor = getBorderColor(isSelected, isDragging, isHighlighted, isPinned);
      ctx.strokeStyle = borderColor;
      ctx.lineWidth = isPinned ? 3 : (isDragging ? 3 : 2);
      ctx.beginPath();
      ctx.roundRect(0, 0, w, h, 8);
      ctx.stroke();

      // Drag indicator
      if (isDragging) {
        ctx.font = '16px Arial';
        ctx.fillStyle = '#aaaaaa';
        ctx.fillText('\u270B', w - 36, 30);
      }

      // Phase 61: Pin indicator
      if (isPinned) {
        ctx.font = '14px Arial';
        ctx.fillStyle = '#4a9eff';
        ctx.fillText('\uD83D\uDCCC', w - 36, 30);
      }

      // Phase 62: Show name on FILES at ALL LOD levels (always visible) - AT TOP
      const textColor = cardCategory === 'doc' ? '#333333' : '#ffffff';
      const fontSize = lodLevel >= 3 ? 16 : lodLevel >= 1 ? 14 : 12;
      ctx.font = `bold ${fontSize}px Arial`;
      ctx.fillStyle = textColor;
      const maxLen = isVertical ? 10 : 18;
      const displayName = name.length > maxLen ? name.slice(0, maxLen - 3) + '...' : name;
      ctx.fillText(displayName, 8, fontSize + 6);

      // Phase 62: Draw preview content INSIDE the card (small text)
      if (previewContent && lodLevel >= 3) {
        const previewColor = cardCategory === 'doc' ? '#555555' : '#888888';
        const previewFontSize = isVertical ? 7 : 8;
        ctx.font = `${previewFontSize}px monospace`;
        ctx.fillStyle = previewColor;

        // Split content into lines and draw inside card
        const lines = previewContent.split('\n').slice(0, isVertical ? 18 : 10);
        const startY = fontSize + 20;
        const lineHeight = previewFontSize + 2;
        const maxChars = isVertical ? 14 : 28;

        lines.forEach((line, i) => {
          const trimmedLine = line.slice(0, maxChars);
          ctx.fillText(trimmedLine, 6, startY + i * lineHeight);
        });
      }
    }

    const tex = new THREE.CanvasTexture(canvas);
    tex.needsUpdate = true;

    // Phase 112.4: Cache the texture for reuse
    cacheTexture(cacheKey, tex);

    return tex;
  // Phase 112.4: Reduced dependencies - hover/drag handled via material, not texture
  }, [id, name, path, type, isSelected, isHighlighted, isPinned, lodLevel, cardCategory, previewContent, metadata, visual_hints, artifactType, artifactStatus, artifactProgress]);

  const handlePointerDown = useCallback(
    (e: any) => {
      // Phase 65: Ctrl/Cmd+Drag OR grabMode active = node movement
      const isDragModifier = e.ctrlKey || e.metaKey || grabMode;
      if (isDragModifier && e.button === 0) {
        e.stopPropagation();
        setIsDragging(true);
        setDraggingAny(true);

        // Phase 113.2: Reset spring state on drag start
        dragVelocity.current.set(0, 0, 0);
        isSettling.current = false;

        e.target?.setPointerCapture?.(e.pointerId);

        const mesh = meshRef.current!;
        const camera = e.camera as THREE.Camera;

        // Phase 113.2: Initialize drag target to current mesh position
        dragTarget.current.copy(mesh.position);

        dragPlane.current.setFromNormalAndCoplanarPoint(
          camera.getWorldDirection(new THREE.Vector3()).negate(),
          mesh.position
        );

        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(e.pointer, camera);
        raycaster.ray.intersectPlane(dragPlane.current, intersection.current);
        dragOffset.current.copy(mesh.position).sub(intersection.current);
      }
    },
    [setDraggingAny, grabMode]
  );

  const handlePointerMove = useCallback(
    (e: any) => {
      if (!isDragging) return;

      e.stopPropagation();

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(e.pointer, e.camera);
      raycaster.ray.intersectPlane(dragPlane.current, intersection.current);

      const newPos = intersection.current.clone().add(dragOffset.current);

      // Phase 113.2: Set spring target instead of instant snap
      // useFrame spring physics will smoothly move mesh toward target
      dragTarget.current.copy(newPos);

      // Store updates handled by useFrame throttle (100ms)
    },
    [isDragging, id, type, updateNodePosition, moveNodeWithChildren]
  );

  const handlePointerUp = useCallback(
    (e: any) => {
      if (!isDragging) return;

      e.target?.releasePointerCapture?.(e.pointerId);
      setIsDragging(false);
      setDraggingAny(false);

      // Phase 113.2: Let spring settle after drag ends
      isSettling.current = true;

      // Final store sync at drag end position
      if (meshRef.current) {
        const pos = { x: meshRef.current.position.x, y: meshRef.current.position.y, z: meshRef.current.position.z };
        if (type === 'folder') {
          moveNodeWithChildren(id, pos);
        } else {
          updateNodePosition(id, pos);
        }
      }

      // Phase 113.1: Persist positions — DISABLED (Phase 113.3 cleanup)
      // useStore.getState().savePositions();
    },
    [isDragging, id, type, setDraggingAny, moveNodeWithChildren, updateNodePosition]
  );

  const handleClick = useCallback(
    (e: any) => {
      // Phase 65: Ctrl/Cmd+Click reserved for drag initiation
      if (e.ctrlKey || e.metaKey) return;

      e.stopPropagation();

      // Phase 65: Shift+Click = Smart Pin (file → toggle, folder → subtree)
      if (e.shiftKey) {
        pinNodeSmart(id);
        return;
      }

      // MARKER_108_3_CLICK_HANDLER: Phase 108.3 - Chat node click opens ChatPanel
      if (type === 'chat') {
        const chatId = metadata?.chat_id;
        if (chatId) {
          // Dispatch custom event to open ChatPanel with this chat
          window.dispatchEvent(new CustomEvent('vetka-open-chat', {
            detail: {
              chatId,
              fileName: name,
              filePath: path,
            },
          }));
          console.log('[FileCard] Phase 108.3: Opening chat', chatId, 'via event');
        }
        return;
      }

      // MARKER_108_4_APPROVE_UI: Phase 108.4 - Artifact node click opens ArtifactPanel
      if (type === 'artifact' && artifactId) {
        // Dispatch custom event to open ArtifactPanel with this artifact
        window.dispatchEvent(new CustomEvent('vetka-open-artifact', {
          detail: {
            artifactId,
            fileName: name,
            filePath: path,
            status: artifactStatus,
            artifactType,
          },
        }));
        console.log('[FileCard] Phase 108.4: Opening artifact', artifactId, 'via event');
        return;
      }

      // Normal click = Select
      onClick?.();
    },
    [onClick, id, pinNodeSmart, type, metadata, name, path, artifactId, artifactStatus, artifactType]
  );

  // Phase 118.2: Double-click handler
  // - File: Open artifact viewer
  // - Folder: Zoom camera to branch
  const handleDoubleClick = useCallback(
    (e: any) => {
      e.stopPropagation();

      if (type === 'file') {
        // Double-click on file = open artifact
        const ext = name.includes('.') ? name.split('.').pop() : undefined;
        window.dispatchEvent(new CustomEvent('vetka-open-artifact-file', {
          detail: {
            path,
            name,
            extension: ext,
          },
        }));
        console.log('[FileCard] Phase 118.2: Double-click opening artifact for', name);
      } else if (type === 'folder') {
        // Double-click on folder = zoom camera to it
        setCameraCommand({
          target: path,
          zoom: 'medium',
          highlight: true,
        });
        console.log('[FileCard] Phase 118.2: Double-click zooming to folder', name);
      }
      // chat and artifact types handled by single click
    },
    [type, name, path, setCameraCommand]
  );

  // Phase 61.1 + 62: File category for preview styling
  // Phase 62: Preview is drawn on texture, no floating previews needed

  return (
    <group>
      {/* Card mesh - always visible */}
      <mesh
        ref={meshRef}
        position={position}
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerOver={() => setIsHovered(true)}
        onPointerOut={() => {
          setIsHovered(false);
          if (isDragging) {
            setIsDragging(false);
            setDraggingAny(false);
          }
        }}
      >
        <planeGeometry args={cardSize} />
        <meshBasicMaterial
          map={texture}
          transparent
          side={THREE.DoubleSide}
          opacity={opacity ?? 1.0}
          // Phase 112.4: Fast hover/drag highlight via color tint (no texture regen)
          // MARKER_123.2C: Phase 123 - Heat-based glow tint (cold blue like Scanner Panel)
          color={
            isDragging ? '#88ff88' :
            isHovered ? '#aaffaa' :
            heatScore > 0.5 ? '#c8e4f4' :  // Strong activity = subtle cold blue
            heatScore > 0.2 ? '#e8f4fc' :  // Medium activity = very subtle blue
            '#ffffff'  // No activity = white
          }
        />
      </mesh>

      {/* MARKER_3D_NODE_RENDER: FileCard component - core 3D node visualization
          - Billboard effect: faces camera via quaternion copy (line 204)
          - LOD system: 10 levels based on camera distance (lines 217-227)
          - Texture: Canvas texture with dynamic rendering (lines 312-439)
          - Drag: Ctrl+drag or grabMode active (lines 443-467)
          - Pin: Shift+click toggles pin state via pinNodeSmart (lines 510-514)
          - Position: x,y,z coordinates updated on drag (line 485)
          - Integration: TreeNode type with position, isPinned state
      */}

      {/* TODO_CAM_PIN: Add pin-to-CAM button on file card hover (like favorites/bookmarks)
          When clicked: POST /api/cam/pin with { file_path, metadata }
          Visual feedback: highlight pin icon or show "Added to CAM" toast */}

      {/* Phase 61.1: Hover Preview - shows on 300ms hover (isHoveredDebounced) */}
      {type === 'file' && isHoveredDebounced && isPreviewableFile(name) && (
        <Html
          position={[position[0], position[1] + cardSize[1] / 2 + 3, position[2]]}
          center
          style={{
            pointerEvents: 'none',
            animation: 'previewFadeIn 0.2s ease forwards',
          }}
          // Phase 62.1: Lower z-index so previews appear BEHIND chat panels
          zIndexRange={[50, 0]}
        >
          <div style={hoverPreviewStyles[getFileCategory(name)]}>
            {loadingPreview ? (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: getFileCategory(name) === 'code' ? '#666' : '#999',
                }}
              >
                Loading...
              </div>
            ) : (
              <div style={{ height: '100%', overflow: 'hidden' }}>
                {/* File name header */}
                <div
                  style={{
                    borderBottom: getFileCategory(name) === 'code' ? '1px solid #333' : '1px solid #ddd',
                    paddingBottom: '6px',
                    marginBottom: '8px',
                    fontWeight: 'bold',
                    fontSize: getFileCategory(name) === 'code' ? '11px' : '13px',
                    color: getFileCategory(name) === 'code' ? '#9cdcfe' : '#1a1a1a',
                  }}
                >
                  {name}
                </div>
                {/* Content */}
                <div style={{ height: 'calc(100% - 30px)', overflow: 'hidden' }}>
                  {previewContent || '// Empty file'}
                </div>
              </div>
            )}
          </div>
        </Html>
      )}

      {/* MARKER_108_4_APPROVE_UI: Phase 108.4 - Status badge for approved/rejected artifacts (always visible) */}
      {type === 'artifact' && (artifactStatus === 'approved' || artifactStatus === 'rejected') && (
        <Html
          position={[position[0] + cardSize[0] / 2 + 1, position[1] + cardSize[1] / 2 - 1, position[2]]}
          style={{
            pointerEvents: 'none',
          }}
          zIndexRange={[100, 0]}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              background: artifactStatus === 'approved' ? '#10b981' : '#ef4444',
              color: '#ffffff',
              fontSize: '14px',
              fontWeight: 'bold',
              border: '2px solid rgba(255,255,255,0.9)',
              boxShadow: '0 2px 6px rgba(0,0,0,0.4)',
            }}
            title={artifactStatus === 'approved' ? 'Approved' : 'Rejected'}
          >
            {artifactStatus === 'approved' ? '✓' : '✗'}
          </div>
        </Html>
      )}

      {/* MARKER_108_4_APPROVE_UI: Phase 108.4 - Approve/Reject buttons for artifact nodes at LOD 5+ */}
      {type === 'artifact' && lodLevel >= 5 && artifactStatus === 'pending' && artifactId && (
        <Html
          position={[position[0], position[1] - cardSize[1] / 2 - 2, position[2]]}
          center
          style={{
            pointerEvents: 'auto',
          }}
          zIndexRange={[100, 0]}
        >
          <div
            style={{
              display: 'flex',
              gap: '6px',
              padding: '4px',
              background: 'rgba(0, 0, 0, 0.85)',
              borderRadius: '6px',
              border: '1px solid rgba(251, 191, 36, 0.5)',
              boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
            }}
          >
            {/* Approve button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                // Dispatch approve event
                window.dispatchEvent(new CustomEvent('vetka-approve-artifact', {
                  detail: { artifactId, nodeId: id, name, path },
                }));
                console.log('[FileCard] Phase 108.4: Approve artifact', artifactId);
              }}
              style={{
                padding: '6px 12px',
                background: '#10b981',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#059669';
                e.currentTarget.style.transform = 'scale(1.05)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#10b981';
                e.currentTarget.style.transform = 'scale(1)';
              }}
              title="Approve artifact"
            >
              ✓ Approve
            </button>

            {/* Reject button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                // Dispatch reject event
                window.dispatchEvent(new CustomEvent('vetka-reject-artifact', {
                  detail: { artifactId, nodeId: id, name, path },
                }));
                console.log('[FileCard] Phase 108.4: Reject artifact', artifactId);
              }}
              style={{
                padding: '6px 12px',
                background: '#ef4444',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#dc2626';
                e.currentTarget.style.transform = 'scale(1.05)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#ef4444';
                e.currentTarget.style.transform = 'scale(1)';
              }}
              title="Reject artifact"
            >
              ✗ Reject
            </button>
          </div>
        </Html>
      )}

      {/* TODO_CAM_INDICATOR: Show CAM activation level badge on folder label (hot/warm/cold)
          Query: GET /api/cam/activation?node_id={id} - returns { level: 'hot'|'warm'|'cold', weight: 0-1 }
          Display with color coding: hot=#ff6b6b, warm=#ffd93d, cold=#95a3a3 */}

      {/* Phase 62.2: Floating label for FOLDERS - Google Maps style LOD
          Based on Grok research: Semantic zoom with importance scoring

          Formula: importance = α(1/depth) + β(childCount) + γ(linkCount)
          - Depth: 40% weight - roots first (depth 0 = most important)
          - Size: 35% weight - more children = more important
          - Links: 25% weight - knowledge level (TODO: implement when tags ready)

          visibilityThreshold = importance * MAX_DISTANCE
          fontSize scales with importance, decays with distance
      */}
      {type === 'folder' && (() => {
        // Phase 113.4: Label Championship — score-based visibility from App.tsx
        // showLabel is computed in FrustumCulledNodes via labelScoring.ts
        // NO isRoot fallback — scoring formula decides everything
        if (!showLabel) return null;

        const childCount = children.length;

        // Get current distance to camera
        const currentPos = new THREE.Vector3(position[0], position[1], position[2]);
        const distToCamera = camera.position.distanceTo(currentPos);

        // === GROK LOD FORMULA (tuned for VETKA 1701 nodes) ===
        const MAX_CHILDREN = 200;
        const MAX_DISTANCE = 8000;

        // Weights
        const WEIGHT_DEPTH = 0.50;
        const WEIGHT_SIZE = 0.50;

        // Calculate scores (still used for font size + styling)
        const depthScore = 1 / Math.sqrt(depth + 1);
        const sizeScore = Math.min(1, Math.sqrt(childCount) / Math.sqrt(MAX_CHILDREN));

        // Combined importance (for styling, not visibility)
        const importance = depthScore * WEIGHT_DEPTH + sizeScore * WEIGHT_SIZE;

        // === DYNAMIC FONT SIZE ===
        // Base size + importance boost + heat boost, slight decay with distance
        // MARKER_119.2J: Phase 119.2 - Heat-based size scaling
        // MARKER_123.5A: Phase 123.5 - Even smaller labels to reduce overlap
        const BASE_FONT_SIZE = 10;   // Was 12, even smaller
        const MAX_FONT_SIZE = 20;    // Was 26, reduced max
        const importanceBoost = importance * 8;  // 0-8px bonus (was 10)
        const heatBoostPx = heatScore * 3;  // 0-3px bonus for active directories
        const distanceDecay = Math.max(0.5, 1 - (distToCamera / MAX_DISTANCE) * 0.3);
        const fontSize = Math.min(MAX_FONT_SIZE, (BASE_FONT_SIZE + importanceBoost + heatBoostPx) * distanceDecay);

        // Fixed position below folder
        const labelY = position[1] - cardSize[1] / 2 - 2;
        const labelZ = position[2] + 1;

        return (
          <Html
            position={[position[0], labelY, labelZ]}
            center
            style={{
              pointerEvents: 'auto',  // Phase 119.1: Enable click on folder labels
              whiteSpace: 'nowrap',
            }}
            // Phase 62.1: Lower z-index so labels appear BEHIND chat panels
            zIndexRange={[50, 0]}
          >
            <div
              onClick={(e) => {
                e.stopPropagation();
                // Phase 119.1: Click on folder label = zoom to folder
                setCameraCommand({
                  target: path,
                  zoom: 'medium',
                  highlight: true,
                });
                console.log('[FileCard] Phase 119.1: Label click zooming to folder', name);
              }}
              style={{
                // MARKER_123.5A: Phase 123.5 - Even smaller padding
                background: `rgba(0, 0, 0, ${0.7 + importance * 0.2})`,
                color: '#ffffff',
                padding: `${3 + importance * 3}px ${6 + importance * 5}px`,
                borderRadius: '4px',
                fontSize: `${fontSize}px`,
                fontWeight: importance > 0.5 ? '600' : '500',
                fontFamily: 'system-ui, -apple-system, sans-serif',
                boxShadow: `0 ${1 + importance * 2}px ${4 + importance * 6}px rgba(0,0,0,${0.3 + importance * 0.2})`,
                border: `1px solid rgba(255,255,255,${0.15 + importance * 0.2})`,
                cursor: 'pointer',  // Phase 119.1: Visual feedback
                transition: 'transform 0.15s ease, box-shadow 0.15s ease',
              }}
              onMouseEnter={(e) => {
                (e.target as HTMLElement).style.transform = 'scale(1.05)';
              }}
              onMouseLeave={(e) => {
                (e.target as HTMLElement).style.transform = 'scale(1)';
              }}
            >
              {name}
              {childCount > 0 && (
                <span style={{
                  marginLeft: '8px',
                  fontSize: `${fontSize * 0.65}px`,
                  opacity: 0.6,
                  fontWeight: 'normal',
                }}>
                  {childCount}
                </span>
              )}
            </div>
          </Html>
        );
      })()}
    </group>
  );
}

// MARKER_111.21_MEMO: React.memo with custom comparator - Phase 112.1 DONE
// Custom comparator: Compare only props that affect visual output
// Skip comparing: onClick (callback reference changes), children (array reference)
// Focus on: visual state (position, selection, opacity, artifact status)

function arePropsEqual(prev: FileCardProps, next: FileCardProps): boolean {
  // Identity check - if same node
  if (prev.id !== next.id) return false;
  if (prev.name !== next.name) return false;
  if (prev.path !== next.path) return false;
  if (prev.type !== next.type) return false;

  // Position check (array comparison)
  if (prev.position[0] !== next.position[0] ||
      prev.position[1] !== next.position[1] ||
      prev.position[2] !== next.position[2]) return false;

  // Visual state
  if (prev.isSelected !== next.isSelected) return false;
  if (prev.isHighlighted !== next.isHighlighted) return false;
  if (prev.opacity !== next.opacity) return false;
  if (prev.depth !== next.depth) return false;

  // Phase 112.3: LOD level from parent (triggers texture/detail changes)
  if (prev.lodLevel !== next.lodLevel) return false;

  // Phase 113.4: Label Championship
  if (prev.showLabel !== next.showLabel) return false;

  // Artifact state (for streaming/approval UI)
  if (prev.artifactStatus !== next.artifactStatus) return false;
  if (prev.artifactProgress !== next.artifactProgress) return false;
  if (prev.artifactType !== next.artifactType) return false;
  if (prev.artifactId !== next.artifactId) return false;

  // Metadata comparison (shallow - for decay_factor opacity)
  const prevDecay = prev.metadata?.decay_factor;
  const nextDecay = next.metadata?.decay_factor;
  if (prevDecay !== nextDecay) return false;

  // Visual hints comparison (shallow)
  if (prev.visual_hints?.opacity !== next.visual_hints?.opacity) return false;
  if (prev.visual_hints?.color !== next.visual_hints?.color) return false;

  // All relevant props are equal - skip re-render
  return true;
}

// Export memoized component
export const FileCard = memo(FileCardComponent, arePropsEqual);
