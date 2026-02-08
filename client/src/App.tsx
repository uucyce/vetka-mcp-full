/**
 * Main application component with 3D canvas, chat panel, and artifact viewer.
 * Handles file tree visualization, search, and user interactions.
 *
 * @status active
 * @phase 100.4
 * @depends react, @react-three/fiber, @react-three/drei, three, lucide-react
 * @depends ./components/canvas/FileCard, ./components/canvas/TreeEdges, ./components/canvas/CameraController
 * @depends ./components/chat, ./components/artifact, ./components/search/UnifiedSearchBar
 * @depends ./components/DropZoneRouter
 * @depends ./store/useStore, ./hooks/useTreeData, ./hooks/useSocket
 * @used_by ./main.tsx
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Canvas, useThree, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { MessageSquare } from 'lucide-react';
import { FileCard } from './components/canvas/FileCard';
import { TreeEdges } from './components/canvas/TreeEdges';
import { CameraController } from './components/canvas/CameraController';
import { ChatPanel } from './components/chat';
import { ArtifactWindow } from './components/artifact';
import { UnifiedSearchBar } from './components/search/UnifiedSearchBar';
import { DevPanel } from './components/panels/DevPanel';
import { DropZoneRouter, type DropZoneEvent } from './components/DropZoneRouter';
import JarvisWave from './components/jarvis/JarvisWave';
import { useJarvis } from './hooks/useJarvis';
import { useStore, type TreeNode } from './store/useStore';
import { useTreeData } from './hooks/useTreeData';
import { useSocket } from './hooks/useSocket';
import type { SearchResult } from './types/chat';
import { calculateAdaptiveLODWithFloor } from './utils/lod';
import {
  computeLabelScore,
  selectTopLabels,
  applyHysteresis,
} from './utils/labelScoring';

// ============================================================================
// MARKER_111.21_FRUSTUM: Phase 112.2 - Frustum Culling Component
// Phase 112.6: Adaptive Foveated Spot - screen-position LOD
// Filters 2000+ nodes to only render those visible in camera frustum
// Expected improvement: 50-80% reduction in rendered components
// ============================================================================

interface FrustumCulledNodesProps {
  nodes: TreeNode[];
  selectedId: string | null;
  highlightedId: string | null;
  selectNode: (id: string | null) => void;
}

function FrustumCulledNodes({ nodes, selectedId, highlightedId, selectNode }: FrustumCulledNodesProps) {
  // Phase 112.6: Get viewport size for adaptive foveated LOD
  const { camera, size } = useThree();
  const [visibleNodeIds, setVisibleNodeIds] = useState<Set<string>>(() => new Set(nodes.map(n => n.id)));
  // Phase 112.3: Batch LOD calculation
  const [nodeLodLevels, setNodeLodLevels] = useState<Map<string, number>>(() => new Map());
  const lastUpdateRef = useRef(0);
  const frustumRef = useRef(new THREE.Frustum());
  const projMatrixRef = useRef(new THREE.Matrix4());

  // Phase 113.4: Label Championship — score-based label selection
  const scoresRef = useRef<Map<string, number>>(new Map());
  const prevScoresRef = useRef<Map<string, number>>(new Map());
  const pinnedFileIds = useStore(s => s.pinnedFileIds);
  const highlightedIds = useStore(s => s.highlightedIds);
  // Phase 113.4 FIX: Labels stored as Set in ref — zero re-renders on label change!
  // useStore subscription for selectedLabelIds was causing full FrustumCulledNodes
  // re-render (400+ FileCard children) every time labels changed.
  // Instead: ref updated in useFrame, Set computed once in render from store snapshot.
  const labelSetRef = useRef<Set<string>>(new Set());
  const [labelGeneration, setLabelGeneration] = useState(0);

  // Update frustum culling + LOD every 200ms (5 FPS, saves CPU)
  useFrame((state) => {
    const now = state.clock.elapsedTime;
    if (now - lastUpdateRef.current < 0.2) return; // 200ms throttle
    lastUpdateRef.current = now;

    // Update projection matrix and frustum
    projMatrixRef.current.multiplyMatrices(
      camera.projectionMatrix,
      camera.matrixWorldInverse
    );
    frustumRef.current.setFromProjectionMatrix(projMatrixRef.current);

    // Filter visible nodes AND calculate LOD in single pass
    const visible = new Set<string>();
    const lodLevels = new Map<string, number>();
    const point = new THREE.Vector3();

    for (const node of nodes) {
      point.set(node.position.x, node.position.y, node.position.z);
      if (frustumRef.current.containsPoint(point)) {
        visible.add(node.id);
        // Phase 112.7: Adaptive Foveated LOD with minimum floor
        // Center of screen = high LOD, edges = low LOD (but min LOD 1)
        // Spot radius adapts to viewport size (mobile 80%, desktop 70%, 4K 60%)
        // minLOD=1 prevents edge flickering between LOD 0 and 1
        const lod = calculateAdaptiveLODWithFloor(node.position, camera, size, 1);
        lodLevels.set(node.id, lod);
      }
    }

    // Phase 113.4: Label Championship — compute scores for folder labels
    // FIX: Pre-compute pinnedSet for O(1) lookups (was O(N) per node)
    const pinnedSet = new Set(pinnedFileIds);
    scoresRef.current.clear();
    for (const node of nodes) {
      if (!visible.has(node.id)) continue;
      if (node.type !== 'folder') continue;
      const isPinned = pinnedSet.has(node.id);
      const isHL = highlightedIds.has(node.id);
      const score = computeLabelScore(node, isPinned, isHL);
      scoresRef.current.set(node.id, score);
    }

    // Apply hysteresis (anti-flicker) and select top-N
    const smoothed = applyHysteresis(scoresRef.current, prevScoresRef.current, 0.1);
    // FIX: Use camera distance to OrbitControls target (not origin)
    // OrbitControls stored in window.__orbitControls (set in App.tsx line 453)
    const orbitControls = (window as any).__orbitControls;
    const target = orbitControls?.target ?? new THREE.Vector3(0, 0, 0);
    const camDist = camera.position.distanceTo(target);
    const zoomLevel = Math.max(0, Math.min(10, 10 - Math.log2(Math.max(1, camDist / 50))));
    const topLabels = selectTopLabels(smoothed, pinnedFileIds, visible.size, zoomLevel);
    prevScoresRef.current = smoothed;

    // FIX: Update label set via ref — NO store subscription, NO re-render cascade
    // Only trigger minimal re-render when the SET actually changes
    const prevLabelSet = labelSetRef.current;
    const newLabelSet = new Set(topLabels);
    // Quick check: same size + all items match
    let labelsChanged = prevLabelSet.size !== newLabelSet.size;
    if (!labelsChanged) {
      for (const id of newLabelSet) {
        if (!prevLabelSet.has(id)) { labelsChanged = true; break; }
      }
    }
    if (labelsChanged) {
      labelSetRef.current = newLabelSet;
      setLabelGeneration(g => g + 1); // minimal re-render trigger
    }

    // Only update state if visibility changed significantly
    const sizeDiff = Math.abs(visible.size - visibleNodeIds.size);
    const needsUpdate = sizeDiff > 5 ||
      (visible.size > 0 && visibleNodeIds.size === 0) ||
      (visible.size === 0 && visibleNodeIds.size > 0);

    if (needsUpdate) {
      setVisibleNodeIds(visible);
      setNodeLodLevels(lodLevels);
    } else {
      // Even if visibility didn't change, update LOD levels (camera zoom)
      setNodeLodLevels(lodLevels);
    }
  });

  // Memoize visible nodes array
  const visibleNodes = useMemo(() => {
    return nodes.filter(n => visibleNodeIds.has(n.id));
  }, [nodes, visibleNodeIds]);

  // Phase 113.4: labelGeneration drives re-render when label set changes
  // Capture current label snapshot keyed to generation (ensures React sees the change)
  const currentLabelSet = useMemo(() => labelSetRef.current, [labelGeneration]);

  return (
    <>
      {visibleNodes.map((node) => (
        <FileCard
          key={node.id}
          id={node.id}
          name={node.name}
          path={node.path}
          type={node.type}
          position={[node.position.x, node.position.y, node.position.z]}
          isSelected={selectedId === node.id}
          isHighlighted={highlightedId === node.id}
          onClick={() => selectNode(node.id)}
          children={node.children}
          depth={node.depth}
          metadata={node.metadata}
          opacity={node.opacity}
          lodLevel={nodeLodLevels.get(node.id) ?? 4}
          showLabel={currentLabelSet.has(node.id)}
        />
      ))}
    </>
  );
}

export default function App() {
  useTreeData();  // Initialize tree data
  useSocket();    // Initialize socket connection

  // Phase 104: Jarvis voice interface
  const jarvis = useJarvis();
  const [isArtifactOpen, setIsArtifactOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [leftPanel, setLeftPanel] = useState<'none' | 'history' | 'models'>('none');

  // MARKER_109_DEVPANEL: Dev panel state
  const [isDevPanelOpen, setIsDevPanelOpen] = useState(false);

  // Phase 68.2: Artifact content for search preview
  const [artifactFile, setArtifactFile] = useState<{ path: string; name: string; extension?: string } | null>(null);
  const [artifactContent, setArtifactContent] = useState<{ content: string; title: string; type?: 'text' | 'markdown' | 'code' } | null>(null);

  const nodes = useStore((state) => Object.values(state.nodes));
  const selectedId = useStore((state) => state.selectedId);
  const selectNode = useStore((state) => state.selectNode);
  const selectedNode = useStore((state) =>
    state.selectedId ? state.nodes[state.selectedId] : null
  );
  const isDraggingAny = useStore((state) => state.isDraggingAny);
  const highlightedId = useStore((state) => state.highlightedId);

  // Phase 65: Grab mode for Blender-style node movement
  const grabMode = useStore((state) => state.grabMode);
  const setGrabMode = useStore((state) => state.setGrabMode);

  // Phase 54.6: Show path selector for multiple matches
  const [pathSelectorData, setPathSelectorData] = useState<{
    filename: string;
    candidates: string[];
    onSelect: (path: string) => void;
  } | null>(null);

  // Phase 52.4: Handle click on empty space to deselect
  const handleCanvasClick = () => {
    // console.log('[App] Click on empty space - clearing selection');
    selectNode(null);
    // Note: Chat will be cleared by ChatPanel's useEffect when selectedNode becomes null
  };

  // Phase 118: getIconsLeft REMOVED - floating icons moved to ChatPanel header

  // Phase 68: Search handlers for standalone search bar
  const setCameraCommand = useStore((state) => state.setCameraCommand);
  const togglePinFile = useStore((state) => state.togglePinFile);
  const allNodes = useStore((state) => state.nodes);

  const handleSearchSelect = useCallback((result: SearchResult) => {
    // Find node by path and select it
    const nodeId = Object.keys(allNodes).find(id => allNodes[id]?.path === result.path);
    if (nodeId) {
      selectNode(nodeId);
    }
    // Fly camera to result
    setCameraCommand({ target: result.path, zoom: 'close', highlight: true });
  }, [allNodes, selectNode, setCameraCommand]);

  const handleSearchPin = useCallback((result: SearchResult) => {
    // Find node by path and toggle pin
    const nodeId = Object.keys(allNodes).find(id => allNodes[id]?.path === result.path);
    if (nodeId) {
      togglePinFile(nodeId);
    }
  }, [allNodes, togglePinFile]);

  // Phase 100.4: Drop zone handlers
  const handleDropToTree = useCallback(async (event: DropZoneEvent) => {
    // console.log('[App] Drop to tree:', event);
    const { files, paths } = event;
    if (files.length === 0) return;

    // Open chat to show scan results
    if (!isChatOpen) {
      setIsChatOpen(true);
    }

    // For real file paths (Tauri mode), use index-file endpoint
    const realPaths = paths.filter(p => !p.startsWith('browser://'));

    if (realPaths.length > 0) {
      // Index files via backend
      for (const filePath of realPaths) {
        try {
          const response = await fetch('/api/watcher/index-file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              path: filePath,
              recursive: files.find(f => f.path === filePath)?.is_dir || false,
            }),
          });

          if (response.ok) {
            // console.log('[App] Indexed file:', filePath);
          }
        } catch (err) {
          console.error('[App] Failed to index file:', err);
        }
      }

      // Fly camera to first file's parent
      const firstName = files[0]?.name || 'dropped';
      window.dispatchEvent(new CustomEvent('camera-fly-to-folder', {
        detail: { folderName: firstName, filesCount: files.length },
      }));

      // Switch to scanner tab
      window.dispatchEvent(new CustomEvent('vetka-switch-to-scanner'));
    } else {
      // Browser mode - use virtual paths
      const rootName = files[0]?.name || 'browser-drop';
      try {
        const response = await fetch('/api/watcher/add-from-browser', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            rootName,
            files: files.map(f => ({
              name: f.name,
              relativePath: f.path.replace('browser://', ''),
              size: f.size,
              type: 'application/octet-stream',
              lastModified: f.modified || Date.now(),
            })),
            timestamp: Date.now(),
          }),
        });

        if (response.ok) {
          window.dispatchEvent(new CustomEvent('camera-fly-to-folder', {
            detail: { folderName: rootName, filesCount: files.length },
          }));
          window.dispatchEvent(new CustomEvent('vetka-switch-to-scanner'));
        }
      } catch (err) {
        console.error('[App] Error indexing dropped files:', err);
      }
    }
  }, [isChatOpen]);

  const handleDropToChat = useCallback(async (event: DropZoneEvent) => {
    // console.log('[App] Drop to chat:', event);
    const { files } = event;
    if (files.length === 0) return;

    // Open chat if not open
    if (!isChatOpen) {
      setIsChatOpen(true);
    }

    // Dispatch event for ChatPanel to handle pinning
    // The actual pinning will be implemented in I5
    window.dispatchEvent(new CustomEvent('vetka-chat-drop', {
      detail: { files },
    }));
  }, [isChatOpen]);

  // MARKER_108_3_CLICK_HANDLER: Phase 108.3 - Listen for chat panel open requests
  useEffect(() => {
    const handleToggleChatPanel = () => {
      if (!isChatOpen) {
        setIsChatOpen(true);
      }
    };

    window.addEventListener('vetka-toggle-chat-panel', handleToggleChatPanel);
    return () => window.removeEventListener('vetka-toggle-chat-panel', handleToggleChatPanel);
  }, [isChatOpen]);

  // Phase 65: G key for grab mode (Blender-style node movement)
  // MARKER_109_DEVPANEL: Cmd+Shift+D for dev panel
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      // MARKER_109_DEVPANEL: Cmd+Shift+D = Toggle Dev Panel
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && (e.key === 'd' || e.key === 'D')) {
        e.preventDefault();
        setIsDevPanelOpen(prev => !prev);
        return;
      }

      // G = Toggle grab mode (also Russian 'п')
      if (e.key === 'g' || e.key === 'G' || e.key === 'п' || e.key === 'П') {
        e.preventDefault();
        setGrabMode(!grabMode);
      }

      // Escape = Cancel grab mode
      if (e.key === 'Escape' && grabMode) {
        setGrabMode(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [grabMode, setGrabMode]);

  // Phase 50.2: ChestIcon component
  // MARKER_118.1B: ChestIcon — иконка артефакта (сундук)
  const ChestIcon = ({ isOpen }: { isOpen: boolean }) => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      {isOpen ? (
        <>
          <path d="M4 14 L4 11 Q4 8 12 8 Q20 8 20 11 L20 14" />
          <path d="M4 11 L4 8 Q4 5 12 3 Q20 5 20 8 L20 11" />
          <rect x="3" y="14" width="18" height="6" rx="1" />
        </>
      ) : (
        <>
          <path d="M4 10 L4 7 Q4 4 12 4 Q20 4 20 7 L20 10" />
          <rect x="3" y="10" width="18" height="8" rx="1" />
          <circle cx="12" cy="14" r="1.5" fill="currentColor" />
        </>
      )}
    </svg>
  );

  return (
    <DropZoneRouter
      isChatOpen={isChatOpen}
      chatPanelWidth={420}
      chatPosition="left"
      onDropToTree={handleDropToTree}
      onDropToChat={handleDropToChat}
    >
    <div style={{ width: '100vw', height: '100vh', background: '#0a0a0a' }}>
      <Canvas
        camera={{
          position: [0, 500, 1000],
          fov: 60,
          near: 0.1,
          far: 10000  // Phase 27.10: Extended far plane for large trees
        }}
        gl={{ antialias: true, powerPreference: 'default' }}
        onPointerMissed={handleCanvasClick}
      >
        <color attach="background" args={['#0a0a0a']} />
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1} />

        <OrbitControls
          ref={(controls) => {
            // Phase 52.4: Store ref for CameraController sync
            if (controls) {
              (window as any).__orbitControls = controls;
            }
          }}
          enabled={!isDraggingAny}
          enableDamping
          dampingFactor={0.05}
          enableZoom={true}
          zoomSpeed={1.2}
          minDistance={50}      // Phase 27.10: Close enough to inspect files
          maxDistance={5000}    // Phase 27.10: Far enough to see whole forest
          target={[0, 200, 0]}
          // FIX_95.9.5: Pan by default (left mouse), Rotate on right mouse (Divstral recommendation)
          mouseButtons={{
            LEFT: THREE.MOUSE.PAN,
            MIDDLE: THREE.MOUSE.DOLLY,
            RIGHT: THREE.MOUSE.ROTATE
          }}
        />

        {/* Phase 52.2: Camera controller for smooth focus animations */}
        <CameraController />

        {/* Phase 27.10: Larger grid for bigger trees */}
        <gridHelper args={[2000, 100, '#1a1a1a', '#1a1a1a']} position={[0, -5, 0]} />

        <TreeEdges />

        {/* MARKER_111.21_FRUSTUM: Phase 112.2 - Frustum culling DONE */}
        {/* Filters 2000+ nodes to only render those visible in camera */}
        {/* Expected improvement: 50-80% reduction in rendered components */}
        <FrustumCulledNodes
          nodes={nodes}
          selectedId={selectedId}
          highlightedId={highlightedId}
          selectNode={selectNode}
        />
      </Canvas>

      <ChatPanel
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        leftPanel={leftPanel}
        setLeftPanel={setLeftPanel}
      />
      <ArtifactWindow
        isOpen={isArtifactOpen}
        onClose={() => {
          setIsArtifactOpen(false);
          setArtifactFile(null);
          setArtifactContent(null);
        }}
        file={artifactFile}
        rawContent={artifactContent}
      />

      {/* MARKER_109_DEVPANEL: Dev Panel */}
      <DevPanel
        isOpen={isDevPanelOpen}
        onClose={() => setIsDevPanelOpen(false)}
      />

      {/* Phase 104: Jarvis Wave in center top */}
      <div style={{
        position: 'fixed',
        top: 16,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 150,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <JarvisWave
          state={jarvis.state}
          audioLevel={jarvis.audioLevel}
          onClick={() => jarvis.toggle()}
          width={200}
          height={48}
        />
        {jarvis.error && (
          <span style={{ color: '#ef4444', fontSize: 11 }}>{jarvis.error}</span>
        )}
      </div>

      {/* Phase 68.3: Search bar + icons container (top-left) */}
      {/* MARKER_118.2A: Контейнер когда чат ЗАКРЫТ — SearchBar + иконки справа */}
      {!isChatOpen && (
        <div style={{
          position: 'fixed',
          top: 16,
          left: 16,
          display: 'flex',
          alignItems: 'flex-start',
          gap: 12,
          zIndex: 100,
        }}>
          {/* Search bar */}
          <div style={{ width: 360 }}>
            <UnifiedSearchBar
              onSelectResult={handleSearchSelect}
              onPinResult={handleSearchPin}
              onOpenArtifact={(result) => {
                // Phase 68.2: Open artifact viewer with file from search
                const ext = result.name.includes('.') ? result.name.split('.').pop() : undefined;
                setArtifactFile({
                  path: result.path,
                  name: result.name,
                  extension: ext
                });
                setArtifactContent(null); // Clear any raw content
                setIsArtifactOpen(true);
              }}
              placeholder="Search..."
              contextPrefix="vetka/"
              compact={false}
            />
          </div>

          {/* Icons next to search bar */}
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            paddingTop: 4,
          }}>
            {/* Chat toggle button */}
            <button
              onClick={() => {
                if (!isChatOpen) {
                  setLeftPanel('none');
                }
                setIsChatOpen(!isChatOpen);
              }}
              style={{
                width: 36,
                height: 36,
                borderRadius: '50%',
                background: '#1a1a1a',
                border: '1px solid #333',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s',
                color: '#888',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#252525';
                e.currentTarget.style.color = '#fff';
                e.currentTarget.style.borderColor = '#444';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#1a1a1a';
                e.currentTarget.style.color = '#888';
                e.currentTarget.style.borderColor = '#333';
              }}
              title="Open chat"
            >
              <MessageSquare size={16} />
            </button>

            {/* Artifact/Chest button */}
            <button
              onClick={() => setIsArtifactOpen(!isArtifactOpen)}
              disabled={!selectedNode}
              style={{
                width: 36,
                height: 36,
                borderRadius: '50%',
                background: selectedNode ? '#1a1a1a' : 'transparent',
                border: `1px solid ${selectedNode ? '#333' : '#222'}`,
                cursor: selectedNode ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s',
                color: selectedNode ? '#888' : '#444',
                opacity: selectedNode ? 1 : 0.5,
              }}
              onMouseEnter={(e) => {
                if (selectedNode) {
                  e.currentTarget.style.background = '#252525';
                  e.currentTarget.style.color = '#fff';
                  e.currentTarget.style.borderColor = '#444';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = selectedNode ? '#1a1a1a' : 'transparent';
                e.currentTarget.style.color = selectedNode ? '#888' : '#444';
                e.currentTarget.style.borderColor = selectedNode ? '#333' : '#222';
              }}
              title={selectedNode ? 'View artifact' : 'Select a file first'}
            >
              <ChestIcon isOpen={isArtifactOpen} />
            </button>
          </div>
        </div>
      )}

      {/* MARKER_118.2B: REMOVED - floating icons moved to ChatPanel header */}

      {/* Phase 65: Grab mode indicator */}
      {grabMode && (
        <div style={{
          position: 'fixed',
          top: 10,
          left: '50%',
          transform: 'translateX(-50%)',
          background: 'rgba(74, 158, 255, 0.9)',
          color: 'white',
          padding: '8px 16px',
          borderRadius: '4px',
          fontSize: '14px',
          fontWeight: 'bold',
          zIndex: 1000,
          boxShadow: '0 2px 10px rgba(74, 158, 255, 0.4)',
        }}>
          🖐️ GRAB MODE (G to toggle, Esc to cancel)
        </div>
      )}

      {/* Phase 50.3: Minimal info panel in top right - one line */}
      <div style={{
        position: 'fixed',
        top: 16,
        right: 16,
        color: '#888',
        fontSize: 13,
        zIndex: 10,
        display: 'flex',
        gap: 16,
        alignItems: 'center',
        whiteSpace: 'nowrap'
      }}>
        <span style={{ color: '#999' }}>Nodes: {nodes.length}</span>
        <span style={{ color: '#666', fontSize: 12 }}>Click=Select • Shift+Click=Pin • Ctrl+Drag/G=Move • Drag=Pan • RightDrag=Rotate</span>
      </div>

      {/* Phase 54.6: Path Selector Modal */}
      {pathSelectorData && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 2000,
        }}>
          <div style={{
            background: '#1a1a1a',
            borderRadius: 12,
            padding: 24,
            maxWidth: 600,
            width: '90%',
            maxHeight: '70vh',
            overflow: 'auto',
            border: '1px solid #333',
          }}>
            <h3 style={{ color: '#fff', marginTop: 0, marginBottom: 16 }}>
              Multiple files found: "{pathSelectorData.filename}"
            </h3>
            <p style={{ color: '#888', marginBottom: 16 }}>
              Select the correct file location:
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {pathSelectorData.candidates.map((path, i) => (
                <button
                  key={i}
                  onClick={() => pathSelectorData.onSelect(path)}
                  style={{
                    background: '#252525',
                    border: '1px solid #444',
                    borderRadius: 8,
                    padding: '12px 16px',
                    color: '#fff',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'background 0.2s',
                    fontSize: 13,
                    fontFamily: 'monospace',
                    wordBreak: 'break-all',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#333'}
                  onMouseLeave={(e) => e.currentTarget.style.background = '#252525'}
                >
                  {path}
                </button>
              ))}
            </div>
            <button
              onClick={() => setPathSelectorData(null)}
              style={{
                marginTop: 16,
                background: 'transparent',
                border: '1px solid #666',
                borderRadius: 8,
                padding: '8px 16px',
                color: '#888',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
    </DropZoneRouter>
  );
}
