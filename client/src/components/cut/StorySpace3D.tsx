/**
 * MARKER_180.9: StorySpace3D — Three.js Camelot × McKee × Film DAG visualization.
 *
 * Architecture doc §6:
 * "StorySpace3D shows the complete story space.
 *  Horizontal plane = Camelot wheel (12 keys, mood/color).
 *  Vertical axis    = McKee triangle (arch top, mini/anti bottom).
 *  Film DAG         = trajectory through this 3D space."
 *
 * Renders:
 * 1. Camelot Wheel — horizontal ring of 12 keys at Y=0
 * 2. McKee Triangle — 3 vertex labels (Archplot top, Miniplot/Antiplot bottom)
 * 3. Scene dots — colored by pendulum, sized by energy, connected by trajectory line
 * 4. Active dot — highlighted for currently selected scene (from sync store)
 *
 * Uses @react-three/fiber for Three.js integration (matches existing VETKA pattern).
 * Designed to work as floating mini-window or expanded panel via PanelShell.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Html, Line } from '@react-three/drei';
import * as THREE from 'three';
import { API_BASE } from '../../config/api.config';
import { usePanelSyncStore } from '../../store/usePanelSyncStore';

// ─── Types ───

interface StoryPoint {
  camelot_key: string;
  camelot_angle: number;     // 0-360°
  triangle: { arch: number; mini: number; anti: number };
  mckee_height: number;      // 0-1 (arch strength)
  pendulum: number;          // -1..+1
  energy: number;            // 0-1
  confidence: number;
  scene_index: number;
  scene_label: string;
  scale: string;
}

// ─── Camelot wheel config ───

const CAMELOT_KEYS = [
  { key: '1B', note: 'C',  color: '#E24B4A' },
  { key: '2B', note: 'G',  color: '#E87D3E' },
  { key: '3B', note: 'D',  color: '#EFA830' },
  { key: '4B', note: 'A',  color: '#D4C92A' },
  { key: '5B', note: 'E',  color: '#7FC74D' },
  { key: '6B', note: 'B',  color: '#5DCAA5' },
  { key: '7B', note: 'F#', color: '#58B8D9' },
  { key: '8B', note: 'Db', color: '#378ADD' },
  { key: '9B', note: 'Ab', color: '#6B6EDC' },
  { key: '10B', note: 'Eb', color: '#7F77DD' },
  { key: '11B', note: 'Bb', color: '#B064C8' },
  { key: '12B', note: 'F', color: '#D94B8D' },
];

const WHEEL_RADIUS = 3;
const TRIANGLE_HEIGHT = 4;    // Y axis height for archplot vertex

// ─── Helper: convert StoryPoint to 3D position ───

function pointToPosition(p: StoryPoint): [number, number, number] {
  // Horizontal plane: Camelot angle → X/Z on ring
  const rad = (p.camelot_angle * Math.PI) / 180;
  // Scale radius by energy (more energy → further from center)
  const r = WHEEL_RADIUS * 0.3 + WHEEL_RADIUS * 0.7 * p.energy;
  const x = Math.cos(rad) * r;
  const z = Math.sin(rad) * r;
  // Vertical: McKee height (arch = top)
  const y = p.mckee_height * TRIANGLE_HEIGHT;
  return [x, y, z];
}

// ─── Helper: pendulum → color ───

function pendulumToColor(pendulum: number): string {
  // -1 = cool blue, 0 = neutral white, +1 = warm orange
  if (pendulum >= 0) {
    const t = pendulum;
    const r = Math.round(224 + (255 - 224) * t);
    const g = Math.round(224 - (224 - 159) * t);
    const b = Math.round(224 - (224 - 67) * t);
    return `rgb(${r},${g},${b})`;
  } else {
    const t = -pendulum;
    const r = Math.round(224 - (224 - 55) * t);
    const g = Math.round(224 - (224 - 138) * t);
    const b = Math.round(224 + (221 - 224) * t);
    return `rgb(${r},${g},${b})`;
  }
}

// ─── Camelot Wheel Ring ───

function CamelotWheel() {
  const segments = useMemo(() => {
    const pts: [number, number, number][] = [];
    for (let i = 0; i <= 24; i++) {
      const angle = (i / 24) * Math.PI * 2;
      pts.push([Math.cos(angle) * WHEEL_RADIUS, 0, Math.sin(angle) * WHEEL_RADIUS]);
    }
    return pts;
  }, []);

  const labels = useMemo(() => {
    return CAMELOT_KEYS.map((ck, i) => {
      const angle = (i / 12) * Math.PI * 2;
      const lx = Math.cos(angle) * (WHEEL_RADIUS + 0.6);
      const lz = Math.sin(angle) * (WHEEL_RADIUS + 0.6);
      return { ...ck, pos: [lx, 0, lz] as [number, number, number] };
    });
  }, []);

  return (
    <group>
      {/* Ring outline */}
      <Line
        points={segments}
        color="#444"
        lineWidth={1}
        opacity={0.5}
        transparent
      />

      {/* Key segment dots + labels */}
      {labels.map((ck) => (
        <group key={ck.key} position={ck.pos}>
          <mesh>
            <sphereGeometry args={[0.08, 8, 8]} />
            <meshBasicMaterial color={ck.color} />
          </mesh>
          <Html
            position={[0, 0.3, 0]}
            center
            style={{
              fontSize: 7,
              color: '#666',
              fontFamily: '"JetBrains Mono", monospace',
              whiteSpace: 'nowrap',
              userSelect: 'none',
              pointerEvents: 'none',
            }}
          >
            {ck.key}
          </Html>
        </group>
      ))}
    </group>
  );
}

// ─── McKee Triangle Vertices ───

function McKeeTriangle() {
  // Archplot at top, Miniplot bottom-left, Antiplot bottom-right
  const vertices: { label: string; pos: [number, number, number]; color: string }[] = [
    { label: 'ARCH', pos: [0, TRIANGLE_HEIGHT, 0], color: '#E24B4A' },
    { label: 'MINI', pos: [-WHEEL_RADIUS * 0.7, 0, -WHEEL_RADIUS * 0.7], color: '#378ADD' },
    { label: 'ANTI', pos: [WHEEL_RADIUS * 0.7, 0, -WHEEL_RADIUS * 0.7], color: '#7F77DD' },
  ];

  const edgePoints: [number, number, number][] = [
    vertices[0].pos, vertices[1].pos, vertices[2].pos, vertices[0].pos,
  ];

  return (
    <group>
      {/* Triangle edges */}
      <Line
        points={edgePoints}
        color="#333"
        lineWidth={0.5}
        opacity={0.3}
        transparent
        dashed
        dashSize={0.2}
        gapSize={0.1}
      />

      {/* Vertex labels */}
      {vertices.map((v) => (
        <group key={v.label} position={v.pos}>
          <mesh>
            <sphereGeometry args={[0.06, 8, 8]} />
            <meshBasicMaterial color={v.color} opacity={0.6} transparent />
          </mesh>
          <Html
            position={[0, 0.25, 0]}
            center
            style={{
              fontSize: 8,
              color: v.color,
              fontFamily: 'Inter, system-ui, sans-serif',
              fontWeight: 600,
              letterSpacing: '0.5px',
              whiteSpace: 'nowrap',
              userSelect: 'none',
              pointerEvents: 'none',
              opacity: 0.7,
            }}
          >
            {v.label}
          </Html>
        </group>
      ))}
    </group>
  );
}

// ─── Scene Dots (Film DAG trajectory) ───

interface SceneDotsProps {
  points: StoryPoint[];
  activeSceneIndex: number | null;
  onDotClick: (point: StoryPoint) => void;
}

function SceneDots({ points, activeSceneIndex, onDotClick }: SceneDotsProps) {
  const positions = useMemo(() => points.map(pointToPosition), [points]);
  const groupRef = useRef<THREE.Group>(null);

  // Slow idle rotation
  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.05;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Trajectory line connecting scenes in order */}
      {positions.length >= 2 && (
        <Line
          points={positions}
          color="#5DCAA5"
          lineWidth={1.5}
          opacity={0.4}
          transparent
        />
      )}

      {/* Scene dots */}
      {points.map((p, i) => {
        const pos = positions[i];
        const isActive = activeSceneIndex === p.scene_index;
        const dotColor = pendulumToColor(p.pendulum);
        // Size scales with energy, active dot is larger
        const radius = isActive ? 0.18 : 0.08 + p.energy * 0.08;

        return (
          <group key={p.scene_index} position={pos}>
            <mesh
              onClick={(e) => {
                e.stopPropagation();
                onDotClick(p);
              }}
            >
              <sphereGeometry args={[radius, 12, 12]} />
              <meshBasicMaterial
                color={dotColor}
                opacity={isActive ? 1.0 : 0.8}
                transparent
              />
            </mesh>

            {/* Active highlight ring */}
            {isActive && (
              <mesh>
                <ringGeometry args={[radius + 0.04, radius + 0.08, 16]} />
                <meshBasicMaterial
                  color="#4a9eff"
                  side={THREE.DoubleSide}
                  opacity={0.6}
                  transparent
                />
              </mesh>
            )}

            {/* Scene label on hover/active */}
            {(isActive || points.length <= 12) && p.scene_label && (
              <Html
                position={[0, radius + 0.2, 0]}
                center
                style={{
                  fontSize: 8,
                  color: isActive ? '#E0E0E0' : '#888',
                  fontFamily: 'Inter, system-ui, sans-serif',
                  whiteSpace: 'nowrap',
                  userSelect: 'none',
                  pointerEvents: 'none',
                  textShadow: '0 1px 3px rgba(0,0,0,0.8)',
                }}
              >
                {p.scene_label}
              </Html>
            )}
          </group>
        );
      })}
    </group>
  );
}

// ─── Camera Controller for StorySpace ───

function StorySpaceCamera() {
  const { camera } = useThree();

  useEffect(() => {
    camera.position.set(5, 4, 5);
    camera.lookAt(0, TRIANGLE_HEIGHT * 0.4, 0);
  }, [camera]);

  return null;
}

// ─── Main Component ───

const CONTAINER: CSSProperties = {
  width: '100%',
  height: '100%',
  background: '#0D0D0D',
  position: 'relative',
  overflow: 'hidden',
};

const INFO_OVERLAY: CSSProperties = {
  position: 'absolute',
  bottom: 4,
  left: 4,
  fontSize: 9,
  fontFamily: '"JetBrains Mono", monospace',
  color: '#555',
  userSelect: 'none',
  pointerEvents: 'none',
  zIndex: 1,
};

interface StorySpace3DProps {
  /** Timeline ID for fetching story space data */
  timelineId?: string;
  /** Script text for story space computation */
  scriptText?: string;
  /** Pre-loaded points (skip fetch) */
  points?: StoryPoint[];
  /** Whether the panel is in mini mode (simplified rendering) */
  mini?: boolean;
}

export default function StorySpace3D({
  timelineId = 'main',
  scriptText = '',
  points: pointsProp,
  mini = false,
}: StorySpace3DProps) {
  const [fetchedPoints, setFetchedPoints] = useState<StoryPoint[]>([]);
  const points = pointsProp || fetchedPoints;

  // Sync store
  const activeSceneId = usePanelSyncStore((s) => s.activeSceneId);
  const syncFromStorySpace = usePanelSyncStore((s) => s.syncFromStorySpace);

  // Find active scene index from scene ID
  const activeSceneIndex = useMemo(() => {
    if (!activeSceneId) return null;
    const p = points.find((pt) => `sc_${pt.scene_index}` === activeSceneId);
    return p ? p.scene_index : null;
  }, [activeSceneId, points]);

  // ─── Fetch points from backend ───
  useEffect(() => {
    if (pointsProp) return; // skip fetch if points provided
    let cancelled = false;

    async function fetchPoints() {
      try {
        // Try timeline-based first, fall back to script-based
        let url = `${API_BASE}/cut/pulse/story-space/${timelineId}`;
        let method = 'POST';
        let body: string | undefined = undefined;

        if (scriptText) {
          url = `${API_BASE}/cut/pulse/story-space`;
          body = JSON.stringify({ script_text: scriptText });
        }

        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          ...(body ? { body } : {}),
        });
        if (!res.ok) return;
        const json = await res.json();
        if (!cancelled && json.success && json.points) {
          setFetchedPoints(json.points);
        }
      } catch {
        // StorySpace is non-critical — silent fail
      }
    }

    fetchPoints();
    return () => { cancelled = true; };
  }, [timelineId, scriptText, pointsProp]);

  // ─── Click dot → sync store ───
  const handleDotClick = useCallback(
    (p: StoryPoint) => {
      syncFromStorySpace(`sc_${p.scene_index}`, p.scene_index * 4); // ~4 sec per scene
    },
    [syncFromStorySpace],
  );

  return (
    <div style={CONTAINER}>
      <Canvas
        camera={{ fov: 45, near: 0.1, far: 100 }}
        dpr={Math.min(window.devicePixelRatio, 2)}
        style={{ background: '#0D0D0D' }}
      >
        <StorySpaceCamera />

        {/* Ambient lighting only — §11: no glow, minimal light */}
        <ambientLight intensity={0.8} />

        {/* Camelot Wheel (horizontal ring) */}
        {!mini && <CamelotWheel />}

        {/* McKee Triangle vertices */}
        {!mini && <McKeeTriangle />}

        {/* Scene dots + trajectory */}
        {points.length > 0 && (
          <SceneDots
            points={points}
            activeSceneIndex={activeSceneIndex}
            onDotClick={handleDotClick}
          />
        )}

        {/* Orbit controls */}
        <OrbitControls
          enablePan={!mini}
          enableZoom={!mini}
          enableRotate
          minDistance={2}
          maxDistance={15}
          target={[0, TRIANGLE_HEIGHT * 0.3, 0]}
          autoRotate={mini}
          autoRotateSpeed={0.5}
        />
      </Canvas>

      {/* Info overlay */}
      <div style={INFO_OVERLAY}>
        {points.length > 0
          ? `${points.length} scenes`
          : 'No data'}
      </div>

      {/* Empty state */}
      {points.length === 0 && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            fontSize: 11,
            color: '#444',
            fontFamily: 'Inter, system-ui, sans-serif',
            textAlign: 'center',
            pointerEvents: 'none',
          }}
        >
          Import media → PULSE analyzes → story space renders
        </div>
      )}
    </div>
  );
}
