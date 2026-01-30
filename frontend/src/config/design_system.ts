/**
 * VETKA Phase 10 Design System Configuration
 * ==========================================
 *
 * Design system constants for Three.js 3D visualization.
 * Based on specification Section 13: Phase 10 UI Design Hints.
 *
 * Author: AI Council + Opus 4.5 (Kimi K2 contribution)
 * Date: December 13, 2025
 */

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT COLORS
// ═══════════════════════════════════════════════════════════════════════════════

export const AGENT_COLORS = {
  PM: '#FFB347',       // warm orange
  Dev: '#6495ED',      // cold blue
  QA: '#9370DB',       // purple
  ARC: '#32CD32',      // green
  Human: '#FFD700',    // gold
  System: '#A9A9A9',   // gray
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// TYPOGRAPHY
// ═══════════════════════════════════════════════════════════════════════════════

export const TYPOGRAPHY = {
  fontFamily: 'Inter, system-ui, sans-serif',
  headers: {
    size: '18px',
    weight: 600,
  },
  body: {
    size: '14px',
    weight: 400,
  },
  metadata: {
    size: '12px',
    weight: 300,
    opacity: 0.7,
  },
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// SPACING GRID
// ═══════════════════════════════════════════════════════════════════════════════

export const SPACING = {
  baseUnit: 8,                    // 8px grid
  nodePadding: 16,                // 2 × baseUnit
  interNodeSpacing: 50,           // MIN_DISTANCE
  layerHeight: 100,               // LAYER_HEIGHT
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// ANIMATION PARAMETERS
// ═══════════════════════════════════════════════════════════════════════════════

export const ANIMATION_PARAMS = {
  static: {
    scale: [1.0, 1.0] as [number, number],
    opacity: [1.0, 1.0] as [number, number],
    period_ms: 0,
  },
  pulse: {
    scale: [1.0, 1.1] as [number, number],
    opacity: [1.0, 1.0] as [number, number],
    period_ms: 2000,
  },
  glow: {
    scale: [1.0, 1.0] as [number, number],
    opacity: [0.7, 1.0] as [number, number],
    period_ms: 1500,
  },
  flicker: {
    scale: [1.0, 1.0] as [number, number],
    opacity: [0.3, 1.0] as [number, number],
    period_ms: 500,
  },
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// LAYOUT CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

export const LAYOUT_CONSTANTS = {
  layer_height: 100,        // Y distance between tree levels
  min_distance: 50,         // Minimum X/Z distance between siblings
  golden_angle: 137.5,      // Phylotaxis spiral angle
  max_deviation: 15,        // Maximum random offset in degrees
  gravity_pull: 0.8,        // How strongly nodes stay near parent axis
  base_unit: 8,             // UI spacing base (8px grid)
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// LOD DISTANCE THRESHOLDS
// ═══════════════════════════════════════════════════════════════════════════════

export const LOD_THRESHOLDS = {
  cluster: 500,   // Very far: show as meta-node cluster
  dot: 200,       // Far: show as simple colored dot
  icon: 50,       // Medium: show icon + label
  full: 0,        // Close: show full content with preview
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT-SPECIFIC LOD DEFAULTS
// ═══════════════════════════════════════════════════════════════════════════════

export const AGENT_LOD_DEFAULTS = {
  PM: {
    default_level: 'FOREST',
    max_depth: 3,
    focus_types: ['memory', 'task'],
  },
  Dev: {
    default_level: 'BRANCH',
    max_depth: 10,
    focus_types: ['task', 'data'],
  },
  QA: {
    default_level: 'BRANCH',
    max_depth: 8,
    focus_types: ['task', 'data'],
    filter_tags: ['test', 'bug', 'quality'],
  },
  ARC: {
    default_level: 'TREE',
    max_depth: 5,
    focus_types: ['control', 'task'],
  },
  Human: {
    default_level: 'FOREST',
    max_depth: 3,
    focus_types: ['memory'],
  },
  System: {
    default_level: 'FOREST',
    max_depth: 2,
    focus_types: ['memory', 'control'],
  },
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// KEYBOARD NAVIGATION (Accessibility)
// ═══════════════════════════════════════════════════════════════════════════════

export const KEYBOARD_NAV = {
  Tab: 'nextNode',
  'Shift+Tab': 'prevNode',
  Enter: 'select/dive',
  Escape: 'goBack',
  ArrowUp: 'parent',
  ArrowDown: 'firstChild',
  ArrowLeft: 'prevSibling',
  ArrowRight: 'nextSibling',
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// INTERACTION STATES
// ═══════════════════════════════════════════════════════════════════════════════

export const HOVER_STYLE = {
  transform: 'scale(1.05)',
  filter: 'brightness(1.1)',
  transition: 'all 0.2s ease-out',
} as const;

export const CLICK_BEHAVIOR = {
  single: 'select',               // Select node
  double: 'dive',                 // Promote trigger / enter branch
  rightClick: 'contextMenu',      // Show options
  drag: 'reposition',             // Manual repositioning
} as const;

export const CAMERA_CONTROLS = {
  // FIX_95.9.5: Changed default from orbit to pan (Divstral recommendation)
  orbit: false,                   // Disabled by default - use Right-Click to orbit
  pan: { bounds: 'tree_bbox × 1.2', default: true },  // Left-Click drag = pan
  zoom: { min: 0.1, max: 10 },
  roll: false,                    // camera.up always (0,1,0)
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR VISUAL FEEDBACK
// ═══════════════════════════════════════════════════════════════════════════════

export const ERROR_STYLES = {
  loading: {
    animation: 'pulse',
    opacity: 0.5,
  },
  error: {
    border: '2px solid #FF0000',
    tooltip: true,
  },
  warning: {
    accent: '#FFD700',
  },
  success: {
    overlay: '✓',
    color: '#32CD32',
  },
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// PERFORMANCE OPTIMIZATIONS
// ═══════════════════════════════════════════════════════════════════════════════

export const PERFORMANCE = {
  frustumCulling: true,           // Don't render off-screen
  lodSwitching: true,             // Distance-based detail
  siblingClustering: 20,          // Cluster if >20 siblings
  virtualScrolling: 1000,         // Virtual list if >1000 trees
  lazyLoading: true,              // Load deep branches on demand
  maxVisibleNodes: 500,           // Soft cap for visible nodes
  updateThrottleMs: 16,           // ~60fps target
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// PROMOTE ANIMATION SEQUENCE
// ═══════════════════════════════════════════════════════════════════════════════

export const PROMOTE_ANIMATION = {
  totalDuration: 1800,            // Total animation duration in ms
  phases: {
    seedForms: {
      duration: 300,
      description: 'Small sphere appears at branch tip',
    },
    seedDetaches: {
      duration: 500,
      description: 'Sphere separates, starts falling',
    },
    rootsSpread: {
      duration: 400,
      description: 'Lines extend from seed into ground (Y < 0)',
    },
    treeGrows: {
      duration: 800,
      description: 'Trunk and branches emerge upward',
    },
  },
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// THREE.JS SPECIFIC CONFIG
// ═══════════════════════════════════════════════════════════════════════════════

export const THREEJS_CONFIG = {
  // Renderer settings
  renderer: {
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance',
  },

  // Camera defaults
  camera: {
    fov: 60,
    near: 0.1,
    far: 10000,
    initialPosition: { x: 0, y: 200, z: 400 },
  },

  // Lighting
  lighting: {
    ambient: {
      color: 0xffffff,
      intensity: 0.6,
    },
    directional: {
      color: 0xffffff,
      intensity: 0.8,
      position: { x: 100, y: 200, z: 100 },
    },
  },

  // Branch geometry
  branch: {
    tubeSegments: 20,
    tubeRadialSegments: 8,
    baseRadius: 0.5,
    radiusMultiplier: 0.5, // radius = baseRadius + entropy * radiusMultiplier
  },

  // Node geometry
  node: {
    sphereSegments: 32,
    baseSize: 10,
    sizeMultiplierMax: 1.5,
  },

  // Edge geometry
  edge: {
    curveSegments: 50,
    defaultCurvature: 0.3,
  },
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// ORGANIC CURVES HELPER
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Configuration for Catmull-Rom spline generation
 * Used for natural-looking branch curves in Three.js
 */
export const ORGANIC_CURVE_CONFIG = {
  tension: 0.5,
  curveType: 'catmullrom' as const,
  organicDeviation: {
    min: -10,
    max: 10,
  },
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// COLOR BLIND SUPPORT
// ═══════════════════════════════════════════════════════════════════════════════

export const COLORBLIND_SUPPORT = {
  // Texture patterns for additional differentiation
  patterns: {
    PM: 'horizontal-stripes',
    Dev: 'vertical-stripes',
    QA: 'dots',
    ARC: 'diagonal-stripes',
    Human: 'crosshatch',
    System: 'none',
  },

  // Shape coding
  shapes: {
    Human: 'square',
    AI: 'circle',        // PM, Dev, QA, ARC
    System: 'diamond',
  },

  // High contrast mode colors
  highContrast: {
    PM: '#FF6600',
    Dev: '#0066FF',
    QA: '#9900CC',
    ARC: '#00CC00',
    Human: '#FFCC00',
    System: '#666666',
  },
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// EDGE STYLES
// ═══════════════════════════════════════════════════════════════════════════════

export const EDGE_STYLES = {
  informs: {
    color: '#FFB347',
    thickness: 1.0,
    style: 'dashed' as const,
    dashSize: 5,
    gapSize: 3,
    arrow_type: null,
  },
  influences: {
    color: '#DC143C',
    thickness: 2.0,
    style: 'solid' as const,
    arrow_type: null,
  },
  creates: {
    color: '#8B4513',
    thickness: 3.0,
    style: 'solid' as const,
    arrow_type: null,
  },
  depends: {
    color: '#4169E1',
    thickness: 1.5,
    style: 'solid' as const,
    arrow_type: 'triangle' as const,
    arrowSize: 8,
  },
  supersedes: {
    color: '#808080',
    thickness: 1.0,
    style: 'dotted' as const,
    dashSize: 2,
    gapSize: 2,
    arrow_type: null,
  },
  references: {
    color: '#9370DB',
    thickness: 0.5,
    style: 'dashed' as const,
    dashSize: 3,
    gapSize: 5,
    arrow_type: null,
  },
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// ICON MAPPING
// ═══════════════════════════════════════════════════════════════════════════════

export const BRANCH_TYPE_ICONS = {
  memory: 'document',
  task: 'code',
  data: 'file',
  control: 'suggestion',
} as const;

export const FILE_EXTENSION_ICONS: Record<string, string> = {
  '.py': 'code',
  '.js': 'code',
  '.ts': 'code',
  '.tsx': 'code',
  '.jsx': 'code',
  '.json': 'file',
  '.yaml': 'file',
  '.yml': 'file',
  '.md': 'document',
  '.txt': 'document',
  '.png': 'file',
  '.jpg': 'file',
  '.svg': 'file',
};

// ═══════════════════════════════════════════════════════════════════════════════
// PROMOTE THRESHOLDS
// ═══════════════════════════════════════════════════════════════════════════════

export const PROMOTE_THRESHOLDS = {
  node_count: 50,        // Trigger if tree has > 50 nodes
  entropy: 0.8,          // Trigger if branch entropy > 0.8
  user_actions: ['dive'] as const,
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// EXPORT ALL
// ═══════════════════════════════════════════════════════════════════════════════

export const DESIGN_SYSTEM = {
  AGENT_COLORS,
  TYPOGRAPHY,
  SPACING,
  ANIMATION_PARAMS,
  LAYOUT_CONSTANTS,
  LOD_THRESHOLDS,
  AGENT_LOD_DEFAULTS,
  KEYBOARD_NAV,
  HOVER_STYLE,
  CLICK_BEHAVIOR,
  CAMERA_CONTROLS,
  ERROR_STYLES,
  PERFORMANCE,
  PROMOTE_ANIMATION,
  THREEJS_CONFIG,
  ORGANIC_CURVE_CONFIG,
  COLORBLIND_SUPPORT,
  EDGE_STYLES,
  BRANCH_TYPE_ICONS,
  FILE_EXTENSION_ICONS,
  PROMOTE_THRESHOLDS,
} as const;

export default DESIGN_SYSTEM;
