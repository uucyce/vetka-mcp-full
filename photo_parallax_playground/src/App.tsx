import { useEffect, useMemo, useRef, useState } from "react";
import { installDebugBridge } from "./lib/debugBridge";
import {
  buildPlateExportAssetsContract as buildPlateExportAssetsContractModel,
  buildPlateLayoutContract as buildPlateLayoutContractModel,
  recommendWorkflowRouting,
} from "./lib/plateLayout";
import {
  clamp,
  computeSnapshot,
  FocusSettings,
  MotionSettings,
  ParallaxSnapshot,
  SAMPLE_LIBRARY,
  SampleMeta,
} from "./lib/metrics";

declare global {
  interface Window {
    vetkaParallaxLab?: {
      snapshot: () => ParallaxSnapshot;
      print: () => ParallaxSnapshot;
      getState: () => {
        sampleId: string;
        focus: FocusSettings;
        motion: MotionSettings;
        manual: ManualSettings;
        stageTool: StageTool;
        brushMode: BrushMode;
        brushSize: number;
        hintStrokeCount: number;
        groupMode: GroupMode;
        groupBoxCount: number;
        plateCount: number;
        matteSeedMode: MatteSeedMode;
        matteSeedCount: number;
        debugOpen: boolean;
        guidedHintsVisible: boolean;
        aiAssistVisible: boolean;
        aiCompareMode: AiCompareMode;
        selectionCoverage: number;
        midgroundCoverage: number;
        matteCoverage: number;
        nearMean: number;
        sourceRasterReady: boolean;
        closerCoverage: number;
        fartherCoverage: number;
        protectCoverage: number;
        foregroundGroupCoverage: number;
        midgroundGroupCoverage: number;
      };
      setSample: (sampleId: string) => string;
      setMotion: (travelXPct: number, travelYPct: number, zoom?: number) => void;
      setFocus: (x: number, y: number, width: number, height: number, feather?: number) => void;
      setPreviewMode: (mode: PreviewMode) => PreviewMode;
      setRenderMode: (mode: RenderMode) => RenderMode;
      setStageTool: (mode: StageTool) => StageTool;
      hydrateSourceRasterFromStage: () => boolean;
      hydrateSourceRasterFromAsset: () => Promise<boolean>;
      setBrushMode: (mode: BrushMode) => BrushMode;
      setMatteSeedMode: (mode: MatteSeedMode) => MatteSeedMode;
      clearManualHints: () => number;
      exportManualHints: () => ManualHintsContract;
      importManualHints: (payload: string | ManualHintsContract) => boolean;
      setGroupMode: (mode: GroupMode) => GroupMode;
      clearGroupBoxes: () => number;
      exportGroupBoxes: () => GroupBoxesContract;
      importGroupBoxes: (payload: string | GroupBoxesContract) => boolean;
      exportPlateStack: () => PlateStackContract;
      importPlateStack: (payload: string | PlateStackContract) => boolean;
      exportPlateLayout: () => PlateAwareLayoutContract;
      exportPlateAssets: () => PlateExportAssetsContract;
      setPlateVisibility: (plateId: string, visible: boolean) => boolean;
      movePlate: (plateId: string, direction: -1 | 1) => boolean;
      nudgePlateZ: (plateId: string, delta: number) => number | null;
      clearMatteSeeds: () => number;
      appendMatteSeed: (x: number, y: number, mode?: MatteSeedMode) => number;
      removeLastMatteSeed: () => number;
      toggleMatteOverlay: () => boolean;
      exportProxyAssets: () => ProxyAssetsContract;
      exportAlgorithmicMatte: () => AlgorithmicMatteContract;
      importAlgorithmicMatte: (payload: string | AlgorithmicMatteContract) => boolean;
      setOverscan: (overscanPct: number) => void;
      setPhase: (phase: number) => void;
      setLayerCount: (layerCount: number) => void;
      setGuidedHintsVisible: (value: boolean) => boolean;
      toggleGuidedHints: () => boolean;
      toggleDebug: () => boolean;
      exportJobState: () => ManualJobState;
      importJobState: (payload: string | ManualJobState) => boolean;
      clearStoredJobState: () => boolean;
      toggleAiAssistOverlay: () => boolean;
      applyAiAssistSuggestion: () => number;
      applyRecommendedPreset: () => ParallaxSnapshot;
      applyQwenPlatePlan: () => number;
      applyQwenPlateGate: () => number;
    };
  }
}

type PreviewMode = "composite" | "depth" | "selection";
type RenderMode = "auto" | "safe" | "three-layer";
type BrushMode = "closer" | "farther" | "protect" | "erase";
type StageTool = "brush" | "group" | "matte";
type GroupMode = "foreground-group" | "midground-group" | "erase-group";
type MatteView = "rgb" | "depth";
type MatteSeedMode = "add" | "subtract" | "protect";

type ManualSettings = {
  previewMode: PreviewMode;
  renderMode: RenderMode;
  invertDepth: boolean;
  nearLimit: number;
  farLimit: number;
  gamma: number;
  targetDepth: number;
  range: number;
  foregroundBias: number;
  backgroundBias: number;
  softness: number;
  expandShrink: number;
  blurPx: number;
  postFilter: number;
};

type HintPoint = {
  x: number;
  y: number;
};

type HintStroke = {
  id: string;
  mode: BrushMode;
  size: number;
  points: HintPoint[];
};

type ManualHintsContract = {
  sampleId: string;
  brushMode: BrushMode;
  brushSize: number;
  hintStrokes: HintStroke[];
};

type GroupBox = {
  id: string;
  mode: Exclude<GroupMode, "erase-group">;
  x: number;
  y: number;
  width: number;
  height: number;
};

type GroupBoxesContract = {
  sampleId: string;
  groupMode: GroupMode;
  groupBoxes: GroupBox[];
};

type PlateRole =
  | "foreground-subject"
  | "secondary-subject"
  | "environment-mid"
  | "background-far"
  | "special-clean";

type PlateSource = "auto" | "manual" | "special-clean" | "qwen-plan";

type Plate = {
  id: string;
  label: string;
  role: PlateRole;
  source: PlateSource;
  x: number;
  y: number;
  width: number;
  height: number;
  z: number;
  depthPriority: number;
  visible: boolean;
  cleanVariant?: string;
  targetPlate?: string;
};

type PlateStackContract = {
  sampleId: string;
  plates: Plate[];
};

type PlateLayoutLayer = {
  id: string;
  label: string;
  role: PlateRole;
  source: PlateSource;
  order: number;
  visible: boolean;
  z: number;
  depthPriority: number;
  parallaxStrength: number;
  motionDamping: number;
  cleanVariant?: string;
  targetPlate?: string;
  box: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  risk: {
    plateCoverage: number;
    recommendedOverscanPct: number;
    minSafeOverscanPct: number;
    disocclusionRisk: number;
    cameraSafe: boolean;
  };
};

type PlateAwareLayoutContract = {
  contract_version: string;
  sampleId: string;
  source: {
    width: number;
    height: number;
    fileName: string;
  };
  metrics: {
    visiblePlateCount: number;
    plateZSpan: number;
    effectiveLayerCount: number;
    effectiveLayerGapPx: number;
    recommendedOverscanPct: number;
    minSafeOverscanPct: number;
  };
  camera: {
    motionType: string;
    travelXPct: number;
    travelYPct: number;
    zoom: number;
    phase: number;
    durationSec: number;
    fps: number;
    overscanPct: number;
  };
  cameraSafe: {
    ok: boolean;
    recommendedOverscanPct: number;
    minSafeOverscanPct: number;
    highestDisocclusionRisk: number;
    worstTransitionRisk: number;
    riskyPlateIds: string[];
    warning: string | null;
    adjustment: {
      applied: boolean;
      requested: {
        overscanPct: number;
        travelXPct: number;
        travelYPct: number;
      };
      effective: {
        overscanPct: number;
        travelXPct: number;
        travelYPct: number;
      };
      reason: string | null;
    };
    suggestion: {
      overscanPct: number;
      travelXPct: number;
      travelYPct: number;
      reason: string | null;
    };
  };
  routing: {
    mode: "portrait-base" | "multi-plate";
    visibleRenderableCount: number;
    specialCleanCount: number;
    reasons: string[];
  };
  transitions: Array<{
    fromId: string;
    toId: string;
    overlapArea: number;
    zGap: number;
    transitionRisk: number;
    cameraSafe: boolean;
  }>;
  plates: PlateLayoutLayer[];
};

type ProxyMaps = {
  width: number;
  height: number;
  depthUrl: string;
  selectionMaskUrl: string;
  overlayUrl: string;
  midgroundMaskUrl: string;
  selectionCoverage: number;
  midgroundCoverage: number;
  nearMean: number;
  hintOverlayUrl: string;
  closerCoverage: number;
  fartherCoverage: number;
  protectCoverage: number;
  groupOverlayUrl: string;
  foregroundGroupCoverage: number;
  midgroundGroupCoverage: number;
  matteOverlayUrl: string;
  matteCoverage: number;
  usingRealDepth: boolean;
  depthValues: Float32Array;
  selectionValues: Float32Array;
  midgroundValues: Float32Array;
};

type ProxyAssetsContract = {
  sampleId: string;
  sourceUrl: string;
  depthUrl: string;
  selectionMaskUrl: string;
  overlayUrl: string;
  midgroundMaskUrl: string;
  hintOverlayUrl: string;
  groupOverlayUrl: string;
  matteOverlayUrl: string;
};

type PlateExportAsset = {
  id: string;
  label: string;
  role: PlateRole;
  source: PlateSource;
  visible: boolean;
  z: number;
  depthPriority: number;
  coverage: number;
  rgbaUrl: string;
  maskUrl: string;
  depthUrl: string;
  cleanUrl?: string;
  cleanVariant?: string;
  targetPlate?: string;
};

type PlateExportAssetsContract = {
  contract_version: string;
  sampleId: string;
  sourceUrl: string;
  globalDepthUrl: string;
  backgroundRgbaUrl: string;
  backgroundMaskUrl: string;
  plateStack: PlateStackContract;
  layout: PlateAwareLayoutContract;
  plates: PlateExportAsset[];
};

type PlateCompositeMaps = {
  width: number;
  height: number;
  backgroundMaskUrl: string;
  backgroundRgbaUrl: string;
  plateMaskUrls: Record<string, string>;
  plateRgbaUrls: Record<string, string>;
  plateDepthUrls: Record<string, string>;
  plateCoverage: Record<string, number>;
};

type RealDepthRaster = {
  sampleId: string;
  width: number;
  height: number;
  values: Float32Array;
};

type SourceRaster = {
  sampleId: string;
  width: number;
  height: number;
  values: Uint8ClampedArray;
};

type MatteSettings = {
  visible: boolean;
  view: MatteView;
  growRadius: number;
  edgeSnap: number;
  opacity: number;
};

type MatteSeed = {
  id: string;
  mode: MatteSeedMode;
  x: number;
  y: number;
  depth: number;
};

type AlgorithmicMatteContract = {
  sampleId: string;
  matteSettings: MatteSettings;
  matteSeeds: MatteSeed[];
};

type ManualJobState = {
  sampleId: string;
  focus: FocusSettings;
  motion: MotionSettings;
  manual: ManualSettings;
  stageTool: StageTool;
  brushMode: BrushMode;
  brushSize: number;
  hintStrokes: HintStroke[];
  groupMode: GroupMode;
  groupBoxes: GroupBox[];
  matteSeedMode: MatteSeedMode;
  matteSettings: MatteSettings;
  matteSeeds: MatteSeed[];
  guidedHintsVisible: boolean;
  aiAssistVisible: boolean;
  plateStack: Plate[];
};

type GroupDraft = {
  start: HintPoint;
  end: HintPoint;
};

type AiAssistGroup = {
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  reason: string;
  area: number;
};

type AiAssistSuggestion = {
  sample_id: string;
  title: string;
  model: string;
  scene_summary: string;
  primary_subject: string;
  background_note: string;
  warnings: string[];
  accepted_foreground_groups: AiAssistGroup[];
  accepted_midground_groups: AiAssistGroup[];
  sanitation_flags: string[];
  confidence: number;
  error: string | null;
};

type AiCompareMode = "manual" | "ai" | "blend";

type QwenPlatePlan = {
  sample_id: string;
  title: string;
  model: string;
  scene_summary: string;
  recommended_plate_count: number;
  special_clean_plates: Array<{
    name: string;
    target_plate?: string | null;
    reason?: string;
  }>;
  confidence: number;
  error: string | null;
  plate_stack_proposal?: PlateStackContract;
};

type QwenPlateGate = {
  contract_version?: string;
  sample_id: string;
  decision: "keep-current-stack" | "enrich-current-stack" | "replace-current-stack";
  confidence: number;
  metrics: {
    manual_visible_count: number;
    qwen_visible_count: number;
    manual_special_clean_count: number;
    qwen_special_clean_count: number;
    visible_overlap_ratio: number;
  };
  added_special_clean_variants: string[];
  reasons: string[];
  gated_plate_stack: PlateStackContract;
};

const JOB_STATE_STORAGE_KEY = "marker_180.photo_parallax.job_state";
const REAL_DEPTH_BACKEND = "depth-pro";
const PARALLAX_CONTRACT_VERSION = "1.0.0";

function getRealDepthPreviewUrl(sampleId: string) {
  return `/depth_bakeoff/${REAL_DEPTH_BACKEND}/${sampleId}/depth_preview.png`;
}

function readQuery() {
  const params = new URLSearchParams(window.location.search);
  return {
    sampleId: params.get("sample") || "hover-politsia",
    debugOpen: params.get("debug") === "1",
  };
}

function findSample(sampleId: string): SampleMeta {
  return SAMPLE_LIBRARY.find((sample) => sample.id === sampleId) || SAMPLE_LIBRARY[0];
}

function formatPct(value: number) {
  return `${value.toFixed(2)}%`;
}

function smoothstep(edge0: number, edge1: number, value: number) {
  const width = Math.max(0.0001, edge1 - edge0);
  const t = clamp((value - edge0) / width, 0, 1);
  return t * t * (3 - 2 * t);
}

function normalizeBox(start: HintPoint, end: HintPoint) {
  const left = Math.min(start.x, end.x);
  const top = Math.min(start.y, end.y);
  const right = Math.max(start.x, end.x);
  const bottom = Math.max(start.y, end.y);
  return {
    x: left,
    y: top,
    width: right - left,
    height: bottom - top,
  };
}

function intersectsBox(a: GroupBox, b: { x: number; y: number; width: number; height: number }) {
  return !(
    a.x + a.width < b.x ||
    b.x + b.width < a.x ||
    a.y + a.height < b.y ||
    b.y + b.height < a.y
  );
}

function getDefaultFocus(sampleId: string): FocusSettings {
  switch (sampleId) {
    case "cassette-closeup":
      return { x: 0.5, y: 0.51, width: 0.48, height: 0.56, feather: 0.16 };
    case "keyboard-hands":
      return { x: 0.51, y: 0.58, width: 0.6, height: 0.52, feather: 0.18 };
    case "drone-portrait":
      return { x: 0.5, y: 0.44, width: 0.42, height: 0.72, feather: 0.18 };
    case "punk-rooftop":
      return { x: 0.32, y: 0.5, width: 0.42, height: 0.64, feather: 0.16 };
    case "truck-driver":
      return { x: 0.56, y: 0.46, width: 0.5, height: 0.58, feather: 0.16 };
    case "hover-politsia":
    default:
      return { x: 0.53, y: 0.46, width: 0.46, height: 0.48, feather: 0.14 };
  }
}

function getDefaultMotion(sampleId: string): MotionSettings {
  switch (sampleId) {
    case "cassette-closeup":
      return {
        travelXPct: 4.2,
        travelYPct: 1.4,
        zoom: 1.052,
        phase: 0.62,
        durationSec: 4,
        fps: 25,
        overscanPct: 16,
        layerGapPx: 18,
        layerCount: 2,
      };
    case "keyboard-hands":
      return {
        travelXPct: 4.8,
        travelYPct: 1.6,
        zoom: 1.056,
        phase: 0.6,
        durationSec: 4,
        fps: 25,
        overscanPct: 17,
        layerGapPx: 22,
        layerCount: 2,
      };
    case "drone-portrait":
      return {
        travelXPct: 5.8,
        travelYPct: 2.2,
        zoom: 1.066,
        phase: 0.68,
        durationSec: 4,
        fps: 25,
        overscanPct: 18,
        layerGapPx: 26,
        layerCount: 2,
      };
    case "punk-rooftop":
      return {
        travelXPct: 5.4,
        travelYPct: 1.8,
        zoom: 1.054,
        phase: 0.62,
        durationSec: 4,
        fps: 25,
        overscanPct: 18,
        layerGapPx: 24,
        layerCount: 2,
      };
    case "truck-driver":
      return {
        travelXPct: 4.0,
        travelYPct: 1.2,
        zoom: 1.048,
        phase: 0.6,
        durationSec: 4,
        fps: 25,
        overscanPct: 15,
        layerGapPx: 18,
        layerCount: 2,
      };
    case "hover-politsia":
    default:
      return {
        travelXPct: 5.6,
        travelYPct: 2.0,
        zoom: 1.058,
        phase: 0.62,
        durationSec: 4,
        fps: 25,
        overscanPct: 19,
        layerGapPx: 28,
        layerCount: 2,
      };
  }
}

function getDefaultManual(sampleId: string): ManualSettings {
  switch (sampleId) {
    case "cassette-closeup":
      return {
        previewMode: "composite",
        renderMode: "auto",
        invertDepth: false,
        nearLimit: 0.76,
        farLimit: 0.15,
        gamma: 1.12,
        targetDepth: 0.72,
        range: 0.24,
        foregroundBias: 0.22,
        backgroundBias: 0.1,
        softness: 0.11,
        expandShrink: 0.04,
        blurPx: 0.6,
        postFilter: 0.18,
      };
    case "keyboard-hands":
      return {
        previewMode: "composite",
        renderMode: "auto",
        invertDepth: false,
        nearLimit: 0.7,
        farLimit: 0.18,
        gamma: 1.18,
        targetDepth: 0.58,
        range: 0.3,
        foregroundBias: 0.18,
        backgroundBias: 0.14,
        softness: 0.12,
        expandShrink: 0.06,
        blurPx: 0.8,
        postFilter: 0.24,
      };
    case "drone-portrait":
      return {
        previewMode: "composite",
        renderMode: "auto",
        invertDepth: false,
        nearLimit: 0.78,
        farLimit: 0.12,
        gamma: 1.06,
        targetDepth: 0.7,
        range: 0.22,
        foregroundBias: 0.16,
        backgroundBias: 0.08,
        softness: 0.09,
        expandShrink: 0.05,
        blurPx: 0.7,
        postFilter: 0.16,
      };
    case "punk-rooftop":
      return {
        previewMode: "composite",
        renderMode: "auto",
        invertDepth: false,
        nearLimit: 0.72,
        farLimit: 0.15,
        gamma: 1.14,
        targetDepth: 0.62,
        range: 0.28,
        foregroundBias: 0.18,
        backgroundBias: 0.12,
        softness: 0.12,
        expandShrink: 0.03,
        blurPx: 0.7,
        postFilter: 0.2,
      };
    case "truck-driver":
      return {
        previewMode: "composite",
        renderMode: "auto",
        invertDepth: false,
        nearLimit: 0.74,
        farLimit: 0.14,
        gamma: 1.08,
        targetDepth: 0.64,
        range: 0.24,
        foregroundBias: 0.17,
        backgroundBias: 0.1,
        softness: 0.1,
        expandShrink: 0.05,
        blurPx: 0.7,
        postFilter: 0.18,
      };
    case "hover-politsia":
    default:
      return {
        previewMode: "composite",
        renderMode: "auto",
        invertDepth: false,
        nearLimit: 0.96,
        farLimit: 0.44,
        gamma: 1.02,
        targetDepth: 0.82,
        range: 0.28,
        foregroundBias: 0.12,
        backgroundBias: 0.14,
        softness: 0.13,
        expandShrink: 0.02,
        blurPx: 0.5,
        postFilter: 0.22,
      };
  }
}

function buildPlate(
  id: string,
  label: string,
  role: PlateRole,
  source: PlateSource,
  box: { x: number; y: number; width: number; height: number },
  z: number,
  depthPriority: number,
  cleanVariant?: string,
): Plate {
  return {
    id,
    label,
    role,
    source,
    x: box.x,
    y: box.y,
    width: box.width,
    height: box.height,
    z,
    depthPriority,
    visible: true,
    cleanVariant,
  };
}

function getDefaultPlateStack(sampleId: string, focus: FocusSettings): Plate[] {
  const focusBox = {
    x: clamp(focus.x - focus.width / 2, 0, 1),
    y: clamp(focus.y - focus.height / 2, 0, 1),
    width: clamp(focus.width, 0.08, 1),
    height: clamp(focus.height, 0.08, 1),
  };
  const backgroundBox = { x: 0.02, y: 0.02, width: 0.96, height: 0.96 };

  switch (sampleId) {
    case "hover-politsia":
      return [
        buildPlate("plate_01", "vehicle", "foreground-subject", "auto", { x: 0.28, y: 0.21, width: 0.5, height: 0.54 }, 26, 0.86, "no-vehicle"),
        buildPlate("plate_02", "walker", "secondary-subject", "manual", { x: 0.02, y: 0.45, width: 0.16, height: 0.4 }, 14, 0.58),
        buildPlate("plate_03", "street steam", "environment-mid", "manual", { x: 0.24, y: 0.55, width: 0.44, height: 0.28 }, -8, 0.36),
        buildPlate("plate_04", "background city", "background-far", "auto", backgroundBox, -30, 0.14),
        { ...buildPlate("plate_05", "no vehicle", "special-clean", "special-clean", backgroundBox, -34, 0.08, "no-vehicle"), visible: false, targetPlate: "plate_01" },
      ];
    case "keyboard-hands":
      return [
        buildPlate("plate_01", "hands+note", "foreground-subject", "auto", { x: 0.14, y: 0.26, width: 0.54, height: 0.52 }, 24, 0.78, "no-hands"),
        buildPlate("plate_02", "keyboard", "environment-mid", "manual", { x: 0.28, y: 0.42, width: 0.44, height: 0.34 }, 10, 0.52),
        buildPlate("plate_03", "monitors+background", "background-far", "auto", backgroundBox, -24, 0.18),
        { ...buildPlate("plate_04", "no hands", "special-clean", "special-clean", backgroundBox, -28, 0.08, "no-hands"), visible: false, targetPlate: "plate_01" },
      ];
    case "cassette-closeup":
      return [
        buildPlate("plate_01", "cassette+hands", "foreground-subject", "auto", { x: 0.16, y: 0.24, width: 0.68, height: 0.52 }, 22, 0.8),
        buildPlate("plate_02", "tunnel", "background-far", "auto", backgroundBox, -20, 0.2),
      ];
    case "truck-driver":
      return [
        buildPlate("plate_01", "driver", "foreground-subject", "auto", focusBox, 18, 0.74, "no-driver"),
        buildPlate("plate_02", "truck cabin", "environment-mid", "manual", { x: 0.24, y: 0.18, width: 0.56, height: 0.64 }, 8, 0.44),
        buildPlate("plate_03", "roadside", "background-far", "auto", backgroundBox, -22, 0.16),
        { ...buildPlate("plate_04", "no driver", "special-clean", "special-clean", backgroundBox, -26, 0.08, "no-driver"), visible: false, targetPlate: "plate_01" },
      ];
    case "punk-rooftop":
      return [
        buildPlate("plate_01", "punk subject", "foreground-subject", "auto", focusBox, 18, 0.72),
        buildPlate("plate_02", "roofline", "environment-mid", "manual", { x: 0.12, y: 0.46, width: 0.7, height: 0.28 }, 4, 0.4),
        buildPlate("plate_03", "city background", "background-far", "auto", backgroundBox, -18, 0.18),
      ];
    case "drone-portrait":
    default:
      return [
        buildPlate("plate_01", "main subject", "foreground-subject", "auto", focusBox, 20, 0.78),
        buildPlate("plate_02", "background clean", "background-far", "auto", backgroundBox, -18, 0.18),
      ];
  }
}

function normalizeImportedPlateStack(plates: Plate[] | undefined, fallback: Plate[] = []): Plate[] {
  if (!plates || plates.length === 0) return fallback;
  return plates.map((plate, index) => {
    const source: PlateSource =
      plate.source === "auto" ||
      plate.source === "manual" ||
      plate.source === "special-clean" ||
      plate.source === "qwen-plan"
        ? plate.source
        : "manual";
    const role: PlateRole =
      plate.role === "foreground-subject" ||
      plate.role === "secondary-subject" ||
      plate.role === "environment-mid" ||
      plate.role === "background-far" ||
      plate.role === "special-clean"
        ? plate.role
        : "environment-mid";
    return {
      id: plate.id || `plate_${String(index + 1).padStart(2, "0")}`,
      label: plate.label || `plate ${index + 1}`,
      role,
      source,
      x: clamp(Number(plate.x) || 0.02, 0, 0.98),
      y: clamp(Number(plate.y) || 0.02, 0, 0.98),
      width: clamp(Number(plate.width) || 0.4, 0.02, 0.98),
      height: clamp(Number(plate.height) || 0.4, 0.02, 0.98),
      z: clamp(Number(plate.z) || 0, -64, 64),
      depthPriority: clamp(Number(plate.depthPriority) || 0.2, 0.02, 0.98),
      visible: plate.visible !== false,
      cleanVariant: plate.cleanVariant || undefined,
      targetPlate: plate.targetPlate || undefined,
    };
  });
}

function buildHintMaps(strokes: HintStroke[], width: number, height: number) {
  const buildCanvas = () => {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    return canvas;
  };
  const closerCanvas = buildCanvas();
  const fartherCanvas = buildCanvas();
  const protectCanvas = buildCanvas();
  const overlayCanvas = buildCanvas();
  const closerCtx = closerCanvas.getContext("2d");
  const fartherCtx = fartherCanvas.getContext("2d");
  const protectCtx = protectCanvas.getContext("2d");
  const overlayCtx = overlayCanvas.getContext("2d");
  if (!closerCtx || !fartherCtx || !protectCtx || !overlayCtx) {
    return {
      closer: new Float32Array(width * height),
      farther: new Float32Array(width * height),
      protect: new Float32Array(width * height),
      overlayUrl: "",
      closerCoverage: 0,
      fartherCoverage: 0,
      protectCoverage: 0,
    };
  }

  const drawStroke = (ctx: CanvasRenderingContext2D, stroke: HintStroke) => {
    if (stroke.points.length === 0) return;
    ctx.beginPath();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineWidth = Math.max(6, stroke.size * Math.min(width, height));
    ctx.strokeStyle = "rgba(255,255,255,1)";
    const first = stroke.points[0];
    ctx.moveTo(first.x * width, first.y * height);
    for (const point of stroke.points.slice(1)) {
      ctx.lineTo(point.x * width, point.y * height);
    }
    if (stroke.points.length === 1) {
      ctx.lineTo(first.x * width + 0.01, first.y * height + 0.01);
    }
    ctx.stroke();
  };

  const contexts = [closerCtx, fartherCtx, protectCtx];
  for (const stroke of strokes) {
    if (stroke.mode === "erase") {
      for (const ctx of contexts) {
        ctx.save();
        ctx.globalCompositeOperation = "destination-out";
        drawStroke(ctx, stroke);
        ctx.restore();
      }
      continue;
    }
    const ctx = stroke.mode === "closer" ? closerCtx : stroke.mode === "farther" ? fartherCtx : protectCtx;
    drawStroke(ctx, stroke);
  }

  const readAlpha = (ctx: CanvasRenderingContext2D) => {
    const data = ctx.getImageData(0, 0, width, height).data;
    const out = new Float32Array(width * height);
    let coverage = 0;
    for (let idx = 0; idx < width * height; idx += 1) {
      const alpha = data[idx * 4 + 3] / 255;
      out[idx] = alpha;
      coverage += alpha;
    }
    return { values: out, coverage: Number((coverage / (width * height)).toFixed(4)) };
  };

  overlayCtx.drawImage(closerCanvas, 0, 0);
  const closerData = overlayCtx.getImageData(0, 0, width, height);
  overlayCtx.clearRect(0, 0, width, height);
  const fartherData = fartherCtx.getImageData(0, 0, width, height);
  const protectData = protectCtx.getImageData(0, 0, width, height);
  const overlayImage = overlayCtx.createImageData(width, height);
  for (let idx = 0; idx < width * height; idx += 1) {
    const closerAlpha = closerData.data[idx * 4 + 3];
    const fartherAlpha = fartherData.data[idx * 4 + 3];
    const protectAlpha = protectData.data[idx * 4 + 3];
    const base = idx * 4;
    if (closerAlpha >= fartherAlpha && closerAlpha >= protectAlpha && closerAlpha > 0) {
      overlayImage.data[base] = 241;
      overlayImage.data[base + 1] = 88;
      overlayImage.data[base + 2] = 72;
      overlayImage.data[base + 3] = closerAlpha;
    } else if (fartherAlpha >= protectAlpha && fartherAlpha > 0) {
      overlayImage.data[base] = 62;
      overlayImage.data[base + 1] = 134;
      overlayImage.data[base + 2] = 247;
      overlayImage.data[base + 3] = fartherAlpha;
    } else if (protectAlpha > 0) {
      overlayImage.data[base] = 72;
      overlayImage.data[base + 1] = 194;
      overlayImage.data[base + 2] = 96;
      overlayImage.data[base + 3] = protectAlpha;
    }
  }
  overlayCtx.putImageData(overlayImage, 0, 0);

  const closer = readAlpha(closerCtx);
  const farther = readAlpha(fartherCtx);
  const protect = readAlpha(protectCtx);
  return {
    closer: closer.values,
    farther: farther.values,
    protect: protect.values,
    overlayUrl: overlayCanvas.toDataURL("image/png"),
    closerCoverage: closer.coverage,
    fartherCoverage: farther.coverage,
    protectCoverage: protect.coverage,
  };
}

function movePlateInStack(plates: Plate[], plateId: string, direction: -1 | 1) {
  const index = plates.findIndex((plate) => plate.id === plateId);
  if (index < 0) return plates;
  const targetIndex = index + direction;
  if (targetIndex < 0 || targetIndex >= plates.length) return plates;
  const next = [...plates];
  const [plate] = next.splice(index, 1);
  next.splice(targetIndex, 0, plate);
  return next;
}

function smoothBoxMask(nx: number, ny: number, plate: Plate) {
  const feather = 0.035;
  const left = smoothstep(plate.x - feather, plate.x + feather, nx);
  const right = 1 - smoothstep(plate.x + plate.width - feather, plate.x + plate.width + feather, nx);
  const top = smoothstep(plate.y - feather, plate.y + feather, ny);
  const bottom = 1 - smoothstep(plate.y + plate.height - feather, plate.y + plate.height + feather, ny);
  return clamp(left * right * top * bottom, 0, 1);
}

function buildPlateCompositeMaps(
  proxyMaps: ProxyMaps,
  sourceRaster: SourceRaster | null,
  plateStack: Plate[],
): PlateCompositeMaps {
  const { width, height } = proxyMaps;
  const buildCanvas = () => {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    return canvas;
  };

  const renderablePlates = plateStack.filter((plate) => plate.visible && plate.role !== "background-far" && plate.role !== "special-clean");
  const backgroundFarPlates = plateStack.filter((plate) => plate.visible && plate.role === "background-far");
  const allExportablePlates = [...renderablePlates, ...backgroundFarPlates];
  const plateCanvases = new Map<string, HTMLCanvasElement>();
  const plateContexts = new Map<string, CanvasRenderingContext2D>();
  const plateImages = new Map<string, ImageData>();
  const plateRgbaImages = new Map<string, ImageData>();
  const plateDepthImages = new Map<string, ImageData>();
  const plateCoverage = new Map<string, number>();

  for (const plate of allExportablePlates) {
    const canvas = buildCanvas();
    const ctx = canvas.getContext("2d");
    if (!ctx) continue;
    plateCanvases.set(plate.id, canvas);
    plateContexts.set(plate.id, ctx);
    plateImages.set(plate.id, ctx.createImageData(width, height));
    plateRgbaImages.set(plate.id, ctx.createImageData(width, height));
    plateDepthImages.set(plate.id, ctx.createImageData(width, height));
    plateCoverage.set(plate.id, 0);
  }

  const backgroundCanvas = buildCanvas();
  const backgroundCtx = backgroundCanvas.getContext("2d");
  if (!backgroundCtx) {
    return { width, height, backgroundMaskUrl: "", backgroundRgbaUrl: "", plateMaskUrls: {}, plateRgbaUrls: {}, plateDepthUrls: {}, plateCoverage: {} };
  }
  const backgroundImage = backgroundCtx.createImageData(width, height);
  const backgroundRgbaImage = backgroundCtx.createImageData(width, height);

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const nx = x / Math.max(1, width - 1);
      const ny = y / Math.max(1, height - 1);
      const pixelIndex = y * width + x;
      const remapped = proxyMaps.depthValues[pixelIndex] ?? 0;
      const selection = proxyMaps.selectionValues[pixelIndex] ?? 0;
      const midground = proxyMaps.midgroundValues[pixelIndex] ?? 0;
      const sourceColor = sampleSourceColor(sourceRaster, nx, ny);

      let unionAlpha = 0;

      for (const plate of renderablePlates) {
        const boxMask = smoothBoxMask(nx, ny, plate);
        if (boxMask <= 0.001) continue;

        let roleAlpha = 0;
        if (plate.role === "foreground-subject") {
          roleAlpha = Math.max(selection, remapped * 0.92);
        } else if (plate.role === "secondary-subject") {
          roleAlpha = Math.max(selection * 0.82, remapped * 0.68);
        } else if (plate.role === "environment-mid") {
          // Keep atmospheric plates driven by actual midground/depth signal,
          // not by a broad soft box that turns the whole region into a proxy slab.
          const midSignal = clamp((midground - 0.18) / 0.55, 0, 1);
          const depthBand = clamp(1 - Math.abs(remapped - 0.42) * 3.6, 0, 1);
          const atmospheric = Math.max(midSignal, depthBand * 0.45);
          roleAlpha = atmospheric * atmospheric;
        }

        const alpha = clamp(roleAlpha * boxMask, 0, 1);
        unionAlpha = Math.max(unionAlpha, alpha);
        const image = plateImages.get(plate.id);
        const rgbaImage = plateRgbaImages.get(plate.id);
        const depthImage = plateDepthImages.get(plate.id);
        if (!image || !rgbaImage || !depthImage) continue;
        const index = (y * width + x) * 4;
        image.data[index] = 255;
        image.data[index + 1] = 255;
        image.data[index + 2] = 255;
        image.data[index + 3] = Math.round(alpha * 255);
        rgbaImage.data[index] = sourceColor.r;
        rgbaImage.data[index + 1] = sourceColor.g;
        rgbaImage.data[index + 2] = sourceColor.b;
        rgbaImage.data[index + 3] = Math.round(alpha * sourceColor.a);
        const gray = Math.round(remapped * 255);
        depthImage.data[index] = gray;
        depthImage.data[index + 1] = gray;
        depthImage.data[index + 2] = gray;
        depthImage.data[index + 3] = Math.round(alpha * 255);
        plateCoverage.set(plate.id, (plateCoverage.get(plate.id) || 0) + alpha);
      }

      // MARKER_P2_BGFAR: Export background-far plates as real plates with complement alpha
      for (const plate of backgroundFarPlates) {
        const bgFarAlpha = clamp(1 - unionAlpha * 0.94, 0.06, 1);
        const image = plateImages.get(plate.id);
        const rgbaImage = plateRgbaImages.get(plate.id);
        const depthImage = plateDepthImages.get(plate.id);
        if (!image || !rgbaImage || !depthImage) continue;
        const index = (y * width + x) * 4;
        image.data[index] = 255;
        image.data[index + 1] = 255;
        image.data[index + 2] = 255;
        image.data[index + 3] = Math.round(bgFarAlpha * 255);
        rgbaImage.data[index] = sourceColor.r;
        rgbaImage.data[index + 1] = sourceColor.g;
        rgbaImage.data[index + 2] = sourceColor.b;
        rgbaImage.data[index + 3] = Math.round(bgFarAlpha * sourceColor.a);
        const gray = Math.round(remapped * 255);
        depthImage.data[index] = gray;
        depthImage.data[index + 1] = gray;
        depthImage.data[index + 2] = gray;
        depthImage.data[index + 3] = Math.round(bgFarAlpha * 255);
        plateCoverage.set(plate.id, (plateCoverage.get(plate.id) || 0) + bgFarAlpha);
      }

      const backgroundAlpha = clamp(1 - unionAlpha * 0.94, 0.06, 1);
      const bgIndex = (y * width + x) * 4;
      backgroundImage.data[bgIndex] = 255;
      backgroundImage.data[bgIndex + 1] = 255;
      backgroundImage.data[bgIndex + 2] = 255;
      backgroundImage.data[bgIndex + 3] = Math.round(backgroundAlpha * 255);
      backgroundRgbaImage.data[bgIndex] = sourceColor.r;
      backgroundRgbaImage.data[bgIndex + 1] = sourceColor.g;
      backgroundRgbaImage.data[bgIndex + 2] = sourceColor.b;
      backgroundRgbaImage.data[bgIndex + 3] = Math.round(backgroundAlpha * sourceColor.a);
    }
  }

  const plateMaskUrls: Record<string, string> = {};
  const plateRgbaUrls: Record<string, string> = {};
  const plateDepthUrls: Record<string, string> = {};
  const plateCoverageOut: Record<string, number> = {};
  for (const plate of allExportablePlates) {
    const ctx = plateContexts.get(plate.id);
    const image = plateImages.get(plate.id);
    const rgbaImage = plateRgbaImages.get(plate.id);
    const depthImage = plateDepthImages.get(plate.id);
    if (!ctx || !image || !rgbaImage || !depthImage) continue;
    ctx.putImageData(image, 0, 0);
    plateMaskUrls[plate.id] = plateCanvases.get(plate.id)?.toDataURL("image/png") || "";
    ctx.clearRect(0, 0, width, height);
    ctx.putImageData(rgbaImage, 0, 0);
    plateRgbaUrls[plate.id] = plateCanvases.get(plate.id)?.toDataURL("image/png") || "";
    ctx.clearRect(0, 0, width, height);
    ctx.putImageData(depthImage, 0, 0);
    plateDepthUrls[plate.id] = plateCanvases.get(plate.id)?.toDataURL("image/png") || "";
    plateCoverageOut[plate.id] = Number(((plateCoverage.get(plate.id) || 0) / (width * height)).toFixed(4));
  }

  backgroundCtx.putImageData(backgroundImage, 0, 0);
  const backgroundMaskUrl = backgroundCanvas.toDataURL("image/png");
  backgroundCtx.clearRect(0, 0, width, height);
  backgroundCtx.putImageData(backgroundRgbaImage, 0, 0);
  return {
    width,
    height,
    backgroundMaskUrl,
    backgroundRgbaUrl: backgroundCanvas.toDataURL("image/png"),
    plateMaskUrls,
    plateRgbaUrls,
    plateDepthUrls,
    plateCoverage: plateCoverageOut,
  };
}


function computeBaseDepth(sampleId: string, focus: FocusSettings, nx: number, ny: number) {
  const dx = (nx - focus.x) / Math.max(0.12, focus.width * 0.72);
  const dy = (ny - focus.y) / Math.max(0.12, focus.height * 0.72);
  const ellipse = dx * dx + dy * dy;
  const subjectField = Math.exp(-ellipse * 1.9);
  const broadField = Math.exp(-ellipse * 0.72);
  const centerField = 1 - Math.min(1, Math.abs(nx - 0.5) * 1.8);
  const lowerField = ny;

  switch (sampleId) {
    case "cassette-closeup":
      return subjectField * 0.72 + broadField * 0.18 + centerField * 0.1;
    case "keyboard-hands":
      return subjectField * 0.44 + lowerField * 0.34 + centerField * 0.22;
    case "drone-portrait":
      return subjectField * 0.78 + broadField * 0.14 + centerField * 0.08;
    case "punk-rooftop":
      return subjectField * 0.63 + broadField * 0.16 + centerField * 0.08 + (1 - nx) * 0.13;
    case "truck-driver":
      return subjectField * 0.74 + broadField * 0.16 + centerField * 0.1;
    case "hover-politsia":
    default:
      return subjectField * 0.36 + lowerField * 0.46 + broadField * 0.18;
  }
}

function sampleRealDepth(realDepth: RealDepthRaster | null, nx: number, ny: number) {
  if (!realDepth || realDepth.width <= 0 || realDepth.height <= 0) return null;
  const x = Math.max(0, Math.min(realDepth.width - 1, Math.round(nx * (realDepth.width - 1))));
  const y = Math.max(0, Math.min(realDepth.height - 1, Math.round(ny * (realDepth.height - 1))));
  return realDepth.values[y * realDepth.width + x] ?? null;
}

function sampleSourceColor(sourceRaster: SourceRaster | null, nx: number, ny: number) {
  if (!sourceRaster || sourceRaster.width <= 0 || sourceRaster.height <= 0) {
    return { r: 255, g: 255, b: 255, a: 255 };
  }
  const x = Math.max(0, Math.min(sourceRaster.width - 1, Math.round(nx * (sourceRaster.width - 1))));
  const y = Math.max(0, Math.min(sourceRaster.height - 1, Math.round(ny * (sourceRaster.height - 1))));
  const index = (y * sourceRaster.width + x) * 4;
  return {
    r: sourceRaster.values[index] ?? 255,
    g: sourceRaster.values[index + 1] ?? 255,
    b: sourceRaster.values[index + 2] ?? 255,
    a: sourceRaster.values[index + 3] ?? 255,
  };
}

function computeResolvedDepth(
  sample: SampleMeta,
  focus: FocusSettings,
  manual: ManualSettings,
  nx: number,
  ny: number,
  realDepth: RealDepthRaster | null,
) {
  const nearLimit = Math.max(manual.nearLimit, manual.farLimit + 0.05);
  const farLimit = Math.min(manual.farLimit, nearLimit - 0.05);
  const baseDepth = sampleRealDepth(realDepth, nx, ny) ?? computeBaseDepth(sample.id, focus, nx, ny);
  let remapped = clamp((baseDepth - farLimit) / Math.max(0.05, nearLimit - farLimit), 0, 1);
  remapped = Math.pow(remapped, 1 / Math.max(0.2, manual.gamma));
  if (manual.invertDepth) remapped = 1 - remapped;
  return remapped;
}

function buildGroupOverlay(groupBoxes: GroupBox[], width: number, height: number) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return {
      overlayUrl: "",
      foregroundGroupCoverage: 0,
      midgroundGroupCoverage: 0,
    };
  }

  let foregroundCoverage = 0;
  let midgroundCoverage = 0;
  for (const box of groupBoxes) {
    const x = box.x * width;
    const y = box.y * height;
    const w = box.width * width;
    const h = box.height * height;
    ctx.fillStyle = box.mode === "foreground-group" ? "rgba(241, 88, 72, 0.18)" : "rgba(65, 152, 255, 0.18)";
    ctx.strokeStyle = box.mode === "foreground-group" ? "rgba(241, 88, 72, 0.88)" : "rgba(65, 152, 255, 0.88)";
    ctx.lineWidth = 2;
    ctx.fillRect(x, y, w, h);
    ctx.strokeRect(x, y, w, h);
    if (box.mode === "foreground-group") foregroundCoverage += box.width * box.height;
    if (box.mode === "midground-group") midgroundCoverage += box.width * box.height;
  }
  return {
    overlayUrl: canvas.toDataURL("image/png"),
    foregroundGroupCoverage: Number(clamp(foregroundCoverage, 0, 1).toFixed(4)),
    midgroundGroupCoverage: Number(clamp(midgroundCoverage, 0, 1).toFixed(4)),
  };
}

function buildProxyMaps(
  sample: SampleMeta,
  focus: FocusSettings,
  manual: ManualSettings,
  realDepth: RealDepthRaster | null,
  strokes: HintStroke[],
  groupBoxes: GroupBox[],
  matteSeeds: MatteSeed[],
  matteSettings: MatteSettings,
): ProxyMaps {
  const width = 640;
  const height = Math.max(360, Math.round((sample.height / sample.width) * width));
  const depthCanvas = document.createElement("canvas");
  depthCanvas.width = width;
  depthCanvas.height = height;
  const maskCanvas = document.createElement("canvas");
  maskCanvas.width = width;
  maskCanvas.height = height;
  const midCanvas = document.createElement("canvas");
  midCanvas.width = width;
  midCanvas.height = height;
  const overlayCanvas = document.createElement("canvas");
  overlayCanvas.width = width;
  overlayCanvas.height = height;
  const matteCanvas = document.createElement("canvas");
  matteCanvas.width = width;
  matteCanvas.height = height;

  const depthCtx = depthCanvas.getContext("2d");
  const maskCtx = maskCanvas.getContext("2d");
  const midCtx = midCanvas.getContext("2d");
  const overlayCtx = overlayCanvas.getContext("2d");
  const matteCtx = matteCanvas.getContext("2d");
  if (!depthCtx || !maskCtx || !midCtx || !overlayCtx || !matteCtx) {
    return {
      width,
      height,
      depthUrl: "",
      selectionMaskUrl: "",
      overlayUrl: "",
      midgroundMaskUrl: "",
      selectionCoverage: 0,
      midgroundCoverage: 0,
      nearMean: 0,
      hintOverlayUrl: "",
      closerCoverage: 0,
      fartherCoverage: 0,
      protectCoverage: 0,
      groupOverlayUrl: "",
      foregroundGroupCoverage: 0,
      midgroundGroupCoverage: 0,
      matteOverlayUrl: "",
      matteCoverage: 0,
      usingRealDepth: false,
      depthValues: new Float32Array(0),
      selectionValues: new Float32Array(0),
      midgroundValues: new Float32Array(0),
    };
  }

  const hintMaps = buildHintMaps(strokes, width, height);
  const groupOverlay = buildGroupOverlay(groupBoxes, width, height);

  const depthImage = depthCtx.createImageData(width, height);
  const maskImage = maskCtx.createImageData(width, height);
  const midImage = midCtx.createImageData(width, height);
  const overlayImage = overlayCtx.createImageData(width, height);
  const matteImage = matteCtx.createImageData(width, height);
  const effectiveSoftness = manual.softness + manual.postFilter * 0.12;
  const halfRange = Math.max(0.04, manual.range / 2);

  let selectionSum = 0;
  let midgroundSum = 0;
  let nearSum = 0;
  let matteSum = 0;
  const depthValues = new Float32Array(width * height);
  const selectionValues = new Float32Array(width * height);
  const midgroundValues = new Float32Array(width * height);

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const nx = x / Math.max(1, width - 1);
      const ny = y / Math.max(1, height - 1);
      let remapped = computeResolvedDepth(sample, focus, manual, nx, ny, realDepth);
      const pixelIndex = y * width + x;
      const closerHint = hintMaps.closer[pixelIndex];
      const fartherHint = hintMaps.farther[pixelIndex];
      const protectHint = hintMaps.protect[pixelIndex];
      const forceForeground = groupBoxes.some(
        (box) =>
          box.mode === "foreground-group" &&
          nx >= box.x &&
          nx <= box.x + box.width &&
          ny >= box.y &&
          ny <= box.y + box.height,
      );
      const forceMidground = groupBoxes.some(
        (box) =>
          box.mode === "midground-group" &&
          nx >= box.x &&
          nx <= box.x + box.width &&
          ny >= box.y &&
          ny <= box.y + box.height,
      );

      remapped = clamp(remapped + closerHint * 0.26 - fartherHint * 0.26, 0, 1);

      const distance = Math.abs(remapped - manual.targetDepth);
      let selection = 1 - smoothstep(halfRange, halfRange + effectiveSoftness, distance);
      if (remapped >= manual.targetDepth) {
        selection += manual.foregroundBias * 0.18;
      } else {
        selection -= manual.backgroundBias * 0.14;
      }
      selection = clamp(selection + manual.expandShrink * 0.22, 0, 1);
      selection = Math.pow(selection, clamp(1.16 - manual.postFilter * 0.38, 0.68, 1.4));
      selection = clamp(selection + closerHint * 0.72 - fartherHint * 0.58, 0, 1);
      if (protectHint > 0) {
        selection = Math.max(selection, protectHint * 0.42);
      }

      const broader = 1 - smoothstep(
        halfRange + effectiveSoftness * 0.32,
        halfRange * 2.35 + effectiveSoftness * 1.65,
        distance,
      );
      let midground = clamp((broader - selection * 0.94) * (manual.renderMode === "three-layer" ? 1 : 0.72), 0, 1);
      midground = Math.pow(midground, 0.92);
      midground = clamp(midground + fartherHint * 0.36 - closerHint * 0.26, 0, 1);

      if (forceForeground) {
        selection = Math.max(selection, 0.96);
        midground = Math.min(midground, 0.04);
        remapped = Math.max(remapped, clamp(manual.targetDepth + halfRange * 0.7, 0, 1));
      }
      if (forceMidground) {
        selection = Math.min(selection, 0.18);
        midground = Math.max(midground, 0.88);
      }

      let addMatte = 0;
      let subtractMatte = 0;
      let protectMatte = 0;
      if (matteSeeds.length > 0) {
        const radius = Math.max(0.04, matteSettings.growRadius);
        const depthWindow = Math.max(0.05, matteSettings.edgeSnap);
        for (const seed of matteSeeds) {
          const localDx = (nx - seed.x) / radius;
          const localDy = (ny - seed.y) / radius;
          const spatial = Math.exp(-(localDx * localDx + localDy * localDy) * 1.75);
          const depthSimilarity = 1 - smoothstep(depthWindow, depthWindow + 0.18, Math.abs(remapped - seed.depth));
          const strength = spatial * depthSimilarity;
          if (seed.mode === "add") addMatte = Math.max(addMatte, strength);
          if (seed.mode === "subtract") subtractMatte = Math.max(subtractMatte, strength);
          if (seed.mode === "protect") protectMatte = Math.max(protectMatte, strength);
        }
        addMatte = clamp(Math.pow(addMatte, 0.92), 0, 1);
        subtractMatte = clamp(Math.pow(subtractMatte, 0.92), 0, 1);
        protectMatte = clamp(Math.pow(protectMatte, 0.92), 0, 1);
      }

      let combinedSelection = Math.max(selection, addMatte * 0.96);
      combinedSelection = clamp(combinedSelection - subtractMatte * (0.86 - protectMatte * 0.5), 0, 1);
      if (protectMatte > 0) {
        combinedSelection = Math.max(combinedSelection, selection * (0.58 + protectMatte * 0.42));
      }
      const gray = Math.round(remapped * 255);
      const selectionAlpha = Math.round(combinedSelection * 255);
      const midAlpha = Math.round(midground * 255);
      depthValues[pixelIndex] = remapped;
      selectionValues[pixelIndex] = combinedSelection;
      midgroundValues[pixelIndex] = midground;
      const index = (y * width + x) * 4;

      depthImage.data[index] = gray;
      depthImage.data[index + 1] = gray;
      depthImage.data[index + 2] = gray;
      depthImage.data[index + 3] = 255;

      maskImage.data[index] = 255;
      maskImage.data[index + 1] = 255;
      maskImage.data[index + 2] = 255;
      maskImage.data[index + 3] = selectionAlpha;

      midImage.data[index] = 255;
      midImage.data[index + 1] = 255;
      midImage.data[index + 2] = 255;
      midImage.data[index + 3] = midAlpha;

      overlayImage.data[index] = 255;
      overlayImage.data[index + 1] = 186;
      overlayImage.data[index + 2] = 68;
      overlayImage.data[index + 3] = Math.round(combinedSelection * 164);
      if (midAlpha > overlayImage.data[index + 3]) {
        overlayImage.data[index] = 65;
        overlayImage.data[index + 1] = 152;
        overlayImage.data[index + 2] = 255;
        overlayImage.data[index + 3] = Math.round(midground * 138);
      }

      const matteStrength = Math.max(addMatte, subtractMatte, protectMatte);
      const matteAlpha = Math.round(matteStrength * 255 * matteSettings.opacity);
      if (matteSettings.view === "depth") {
        matteImage.data[index] = gray;
        matteImage.data[index + 1] = gray;
        matteImage.data[index + 2] = gray;
        matteImage.data[index + 3] = matteAlpha;
      } else if (subtractMatte >= addMatte && subtractMatte >= protectMatte && subtractMatte > 0) {
        matteImage.data[index] = 255;
        matteImage.data[index + 1] = 96;
        matteImage.data[index + 2] = 124;
        matteImage.data[index + 3] = matteAlpha;
      } else if (protectMatte >= addMatte && protectMatte > 0) {
        matteImage.data[index] = 112;
        matteImage.data[index + 1] = 216;
        matteImage.data[index + 2] = 96;
        matteImage.data[index + 3] = matteAlpha;
      } else {
        matteImage.data[index] = 84;
        matteImage.data[index + 1] = 230;
        matteImage.data[index + 2] = 182;
        matteImage.data[index + 3] = matteAlpha;
      }

      selectionSum += combinedSelection;
      midgroundSum += midground;
      nearSum += remapped;
      matteSum += matteStrength;
    }
  }

  depthCtx.putImageData(depthImage, 0, 0);
  maskCtx.putImageData(maskImage, 0, 0);
  midCtx.putImageData(midImage, 0, 0);
  overlayCtx.putImageData(overlayImage, 0, 0);
  matteCtx.putImageData(matteImage, 0, 0);

  const maskSource = manual.blurPx > 0.05 ? document.createElement("canvas") : maskCanvas;
  if (maskSource !== maskCanvas) {
    maskSource.width = width;
    maskSource.height = height;
    const ctx = maskSource.getContext("2d");
    if (ctx) {
      ctx.filter = `blur(${manual.blurPx}px)`;
      ctx.drawImage(maskCanvas, 0, 0);
    }
  }

  return {
    width,
    height,
    depthUrl: depthCanvas.toDataURL("image/png"),
    selectionMaskUrl: maskSource.toDataURL("image/png"),
    overlayUrl: overlayCanvas.toDataURL("image/png"),
    midgroundMaskUrl: midCanvas.toDataURL("image/png"),
    selectionCoverage: Number((selectionSum / (width * height)).toFixed(4)),
    midgroundCoverage: Number((midgroundSum / (width * height)).toFixed(4)),
    nearMean: Number((nearSum / (width * height)).toFixed(4)),
    hintOverlayUrl: hintMaps.overlayUrl,
    closerCoverage: hintMaps.closerCoverage,
    fartherCoverage: hintMaps.fartherCoverage,
    protectCoverage: hintMaps.protectCoverage,
    groupOverlayUrl: groupOverlay.overlayUrl,
    foregroundGroupCoverage: groupOverlay.foregroundGroupCoverage,
    midgroundGroupCoverage: groupOverlay.midgroundGroupCoverage,
    matteOverlayUrl: matteCanvas.toDataURL("image/png"),
    matteCoverage: Number((matteSum / (width * height)).toFixed(4)),
    usingRealDepth: Boolean(realDepth),
    depthValues,
    selectionValues,
    midgroundValues,
  };
}

function App() {
  const initialQuery = useMemo(readQuery, []);
  const [sampleId, setSampleId] = useState(initialQuery.sampleId);
  const [debugOpen, setDebugOpen] = useState(initialQuery.debugOpen);
  const [focus, setFocus] = useState<FocusSettings>(() => getDefaultFocus(initialQuery.sampleId));
  const [motion, setMotion] = useState<MotionSettings>(() => getDefaultMotion(initialQuery.sampleId));
  const [manual, setManual] = useState<ManualSettings>(() => getDefaultManual(initialQuery.sampleId));
  const [stageTool, setStageTool] = useState<StageTool>("brush");
  const [brushMode, setBrushMode] = useState<BrushMode>("closer");
  const [brushSize, setBrushSize] = useState(0.045);
  const [hintStrokes, setHintStrokes] = useState<HintStroke[]>([]);
  const [groupMode, setGroupMode] = useState<GroupMode>("foreground-group");
  const [groupBoxes, setGroupBoxes] = useState<GroupBox[]>([]);
  const [plateStack, setPlateStack] = useState<Plate[]>(() =>
    getDefaultPlateStack(initialQuery.sampleId, getDefaultFocus(initialQuery.sampleId)),
  );
  const [groupDraft, setGroupDraft] = useState<GroupDraft | null>(null);
  const [matteSettings, setMatteSettings] = useState<MatteSettings>({
    visible: true,
    view: "rgb",
    growRadius: 0.16,
    edgeSnap: 0.12,
    opacity: 0.62,
  });
  const [matteSeedMode, setMatteSeedMode] = useState<MatteSeedMode>("add");
  const [matteSeeds, setMatteSeeds] = useState<MatteSeed[]>([]);
  const [aiAssistSuggestion, setAiAssistSuggestion] = useState<AiAssistSuggestion | null>(null);
  const [qwenPlatePlan, setQwenPlatePlan] = useState<QwenPlatePlan | null>(null);
  const [qwenPlateGate, setQwenPlateGate] = useState<QwenPlateGate | null>(null);
  const [aiAssistVisible, setAiAssistVisible] = useState(false);
  const [manualGroupBaseline, setManualGroupBaseline] = useState<GroupBox[]>([]);
  const [aiCompareMode, setAiCompareMode] = useState<AiCompareMode>("manual");
  const [guidedHintsVisible, setGuidedHintsVisible] = useState(false);
  const [realDepth, setRealDepth] = useState<RealDepthRaster | null>(null);
  const [sourceRaster, setSourceRaster] = useState<SourceRaster | null>(null);
  const [stageSize, setStageSize] = useState({ width: 1180, height: 760 });
  const stageRef = useRef<HTMLDivElement | null>(null);
  const drawingStrokeIdRef = useRef<string | null>(null);

  const sample = useMemo(() => findSample(sampleId), [sampleId]);
  const visiblePlates = useMemo(() => plateStack.filter((plate) => plate.visible), [plateStack]);
  const visibleRenderablePlates = useMemo(
    () => visiblePlates.filter((plate) => plate.role !== "special-clean"),
    [visiblePlates],
  );
  const workflowRouting = useMemo(() => recommendWorkflowRouting(plateStack), [plateStack]);
  const plateZSpan = useMemo(() => {
    if (visibleRenderablePlates.length <= 1) return 0;
    const values = visibleRenderablePlates.map((plate) => plate.z);
    return Math.max(...values) - Math.min(...values);
  }, [visibleRenderablePlates]);
  const layoutMotion = useMemo(
    () => ({
      ...motion,
      layerCount: Math.max(motion.layerCount, Math.max(2, visibleRenderablePlates.length)),
      layerGapPx: Math.max(motion.layerGapPx, plateZSpan * 0.85),
    }),
    [motion, visibleRenderablePlates.length, plateZSpan],
  );
  useEffect(() => {
    let cancelled = false;
    const image = new Image();
    image.onload = () => {
      if (cancelled) return;
      const canvas = document.createElement("canvas");
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        setRealDepth(null);
        return;
      }
      ctx.drawImage(image, 0, 0);
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const values = new Float32Array(canvas.width * canvas.height);
      for (let index = 0; index < values.length; index += 1) {
        values[index] = imageData.data[index * 4] / 255;
      }
      setRealDepth({ sampleId, width: canvas.width, height: canvas.height, values });
    };
    image.onerror = () => {
      if (!cancelled) setRealDepth(null);
    };
    image.src = getRealDepthPreviewUrl(sampleId);
    return () => {
      cancelled = true;
    };
  }, [sampleId]);
  useEffect(() => {
    let cancelled = false;
    setSourceRaster(null);

    const loadSourceRaster = async () => {
      try {
        const response = await fetch(`/samples/${sample.fileName}`, { cache: "no-store" });
        if (!response.ok) throw new Error(`source fetch failed: ${response.status}`);
        const blob = await response.blob();
        const bitmap = await createImageBitmap(blob);
        if (cancelled) return;
        const canvas = document.createElement("canvas");
        canvas.width = bitmap.width;
        canvas.height = bitmap.height;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          setSourceRaster(null);
          return;
        }
        ctx.drawImage(bitmap, 0, 0);
        bitmap.close();
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        setSourceRaster({
          sampleId,
          width: canvas.width,
          height: canvas.height,
          values: imageData.data,
        });
      } catch {
        if (!cancelled) setSourceRaster(null);
      }
    };

    void loadSourceRaster();
    return () => {
      cancelled = true;
    };
  }, [sampleId, sample.fileName]);
  const snapshot = useMemo(
    () => computeSnapshot(sample, stageSize.width, stageSize.height, focus, layoutMotion),
    [sample, stageSize.width, stageSize.height, focus, layoutMotion],
  );
  const proxyMaps = useMemo(
    () => buildProxyMaps(sample, focus, manual, realDepth, hintStrokes, groupBoxes, matteSeeds, matteSettings),
    [sample, focus, manual, realDepth, hintStrokes, groupBoxes, matteSeeds, matteSettings],
  );
  const plateCompositeMaps = useMemo(
    () => buildPlateCompositeMaps(proxyMaps, sourceRaster, plateStack),
    [proxyMaps, sourceRaster, plateStack],
  );

  useEffect(() => {
    const node = stageRef.current;
    if (!node) return;

    const update = () => {
      const rect = node.getBoundingClientRect();
      setStageSize({
        width: Math.max(360, Math.round(rect.width)),
        height: Math.max(260, Math.round(rect.height)),
      });
    };

    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    window.addEventListener("resize", update);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", update);
    };
  }, []);

  useEffect(() => {
    console.info("MARKER_180.PARALLAX.SAMPLE", {
      sampleId,
      previewScore: snapshot.previewScore,
      overscanPct: snapshot.overscanPct,
    });
  }, [sampleId, snapshot.previewScore, snapshot.overscanPct]);

  useEffect(() => {
    let cancelled = false;
    setAiAssistSuggestion(null);
    fetch(`/ai_assist_suggestions/${sampleId}.json`)
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (!cancelled) setAiAssistSuggestion(payload);
      })
      .catch(() => {
        if (!cancelled) setAiAssistSuggestion(null);
      });
    return () => {
      cancelled = true;
    };
  }, [sampleId]);

  useEffect(() => {
    let cancelled = false;
    setQwenPlatePlan(null);
    fetch(`/qwen_plate_plans/${sampleId}.json`)
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (!cancelled) setQwenPlatePlan(payload);
      })
      .catch(() => {
        if (!cancelled) setQwenPlatePlan(null);
      });
    return () => {
      cancelled = true;
    };
  }, [sampleId]);

  useEffect(() => {
    let cancelled = false;
    setQwenPlateGate(null);
    fetch(`/qwen_plate_gates/${sampleId}.json`)
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (!cancelled) setQwenPlateGate(payload);
      })
      .catch(() => {
        if (!cancelled) setQwenPlateGate(null);
      });
    return () => {
      cancelled = true;
    };
  }, [sampleId]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(JOB_STATE_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as ManualJobState;
      if (!parsed || typeof parsed !== "object" || !parsed.sampleId) return;
      applyJobState(parsed);
    } catch (error) {
      console.warn("MARKER_180.PARALLAX.JOB_STATE.READ_FAILED", error);
    }
  }, []);

  const buildJobState = (): ManualJobState => ({
    sampleId,
    focus,
    motion,
    manual,
    stageTool,
    brushMode,
    brushSize,
    hintStrokes,
    groupMode,
    groupBoxes,
    matteSeedMode,
    matteSettings,
    matteSeeds,
    guidedHintsVisible,
    aiAssistVisible,
    plateStack,
  });

  const buildAlgorithmicMatteContract = (): AlgorithmicMatteContract => ({
    sampleId,
    matteSettings,
    matteSeeds,
  });

  const buildManualHintsContract = (): ManualHintsContract => ({
    sampleId,
    brushMode,
    brushSize,
    hintStrokes,
  });

  const buildGroupBoxesContract = (): GroupBoxesContract => ({
    sampleId,
    groupMode,
    groupBoxes,
  });

  const buildPlateStackContract = (): PlateStackContract => ({
    sampleId,
    plates: plateStack,
  });

  const buildSnapshotMotion = (baseMotion: MotionSettings): MotionSettings => ({
    ...baseMotion,
    layerCount: Math.max(baseMotion.layerCount, Math.max(2, visibleRenderablePlates.length)),
    layerGapPx: Math.max(baseMotion.layerGapPx, plateZSpan * 0.85),
  });

  const buildPreviewPlateLayoutContract = (): PlateAwareLayoutContract =>
    buildPlateLayoutContractModel({
      contractVersion: PARALLAX_CONTRACT_VERSION,
      sample,
      plateStack,
      motion,
      snapshot,
      renderMode: manual.renderMode,
    });

  const buildEffectiveExportLayoutState = () => {
    let candidateMotion = { ...motion };
    let candidateSnapshot = computeSnapshot(
      sample,
      stageSize.width,
      stageSize.height,
      focus,
      buildSnapshotMotion(candidateMotion),
    );
    let candidateLayout = buildPlateLayoutContractModel({
      contractVersion: PARALLAX_CONTRACT_VERSION,
      sample,
      plateStack,
      motion: candidateMotion,
      snapshot: candidateSnapshot,
      requestedMotion: motion,
      renderMode: manual.renderMode,
    });

    for (let attempt = 0; attempt < 3 && !candidateLayout.cameraSafe.ok; attempt += 1) {
      const suggestedMotion: MotionSettings = {
        ...candidateMotion,
        overscanPct: candidateLayout.cameraSafe.suggestion.overscanPct,
        travelXPct: candidateLayout.cameraSafe.suggestion.travelXPct,
        travelYPct: candidateLayout.cameraSafe.suggestion.travelYPct,
      };

      const motionUnchanged =
        Number(suggestedMotion.overscanPct.toFixed(2)) === Number(candidateMotion.overscanPct.toFixed(2)) &&
        Number(suggestedMotion.travelXPct.toFixed(2)) === Number(candidateMotion.travelXPct.toFixed(2)) &&
        Number(suggestedMotion.travelYPct.toFixed(2)) === Number(candidateMotion.travelYPct.toFixed(2));
      if (motionUnchanged) break;

      candidateMotion = suggestedMotion;
      candidateSnapshot = computeSnapshot(
        sample,
        stageSize.width,
        stageSize.height,
        focus,
        buildSnapshotMotion(candidateMotion),
      );
      candidateLayout = buildPlateLayoutContractModel({
        contractVersion: PARALLAX_CONTRACT_VERSION,
        sample,
        plateStack,
        motion: candidateMotion,
        snapshot: candidateSnapshot,
        requestedMotion: motion,
        renderMode: manual.renderMode,
      });
    }

    return {
      motion: candidateMotion,
      snapshot: candidateSnapshot,
      layout: candidateLayout,
    };
  };

  const buildPlateLayoutContract = (): PlateAwareLayoutContract => buildEffectiveExportLayoutState().layout;

  const buildProxyAssetsContract = (): ProxyAssetsContract => ({
    sampleId,
    sourceUrl: `/samples/${sample.fileName}`,
    depthUrl: proxyMaps.depthUrl,
    selectionMaskUrl: proxyMaps.selectionMaskUrl,
    overlayUrl: proxyMaps.overlayUrl,
    midgroundMaskUrl: proxyMaps.midgroundMaskUrl,
    hintOverlayUrl: proxyMaps.hintOverlayUrl,
    groupOverlayUrl: proxyMaps.groupOverlayUrl,
    matteOverlayUrl: proxyMaps.matteOverlayUrl,
  });

  const buildPlateExportAssetsContract = (): PlateExportAssetsContract => {
    const { layout } = buildEffectiveExportLayoutState();
    return buildPlateExportAssetsContractModel({
      contractVersion: PARALLAX_CONTRACT_VERSION,
      sample,
      plateStack,
      layout,
      proxyDepthUrl: proxyMaps.depthUrl,
      backgroundRgbaUrl: plateCompositeMaps.backgroundRgbaUrl,
      backgroundMaskUrl: plateCompositeMaps.backgroundMaskUrl,
      plateCoverage: plateCompositeMaps.plateCoverage,
      plateRgbaUrls: plateCompositeMaps.plateRgbaUrls,
      plateMaskUrls: plateCompositeMaps.plateMaskUrls,
      plateDepthUrls: plateCompositeMaps.plateDepthUrls,
    });
  };

  const applyJobState = (jobState: ManualJobState) => {
    const nextSample = findSample(jobState.sampleId);
    setSampleId(nextSample.id);
    setFocus(jobState.focus);
    setMotion(jobState.motion);
    setManual(jobState.manual);
    setStageTool(jobState.stageTool);
    setBrushMode(jobState.brushMode);
    setBrushSize(jobState.brushSize);
    setHintStrokes(jobState.hintStrokes || []);
    setGroupMode(jobState.groupMode);
    setMatteSeedMode(jobState.matteSeedMode || "add");
    setMatteSettings(jobState.matteSettings || { visible: true, view: "rgb", growRadius: 0.16, edgeSnap: 0.12, opacity: 0.62 });
    setMatteSeeds(jobState.matteSeeds || []);
    setPlateStack(
      normalizeImportedPlateStack(
        jobState.plateStack,
        getDefaultPlateStack(nextSample.id, jobState.focus),
      ),
    );
    const nextGroups = jobState.groupBoxes || [];
    setGroupBoxes(nextGroups);
    setManualGroupBaseline(nextGroups.filter((box) => !box.id.startsWith("ai-")));
    setGroupDraft(null);
    setGuidedHintsVisible(Boolean(jobState.guidedHintsVisible));
    setAiAssistVisible(Boolean(jobState.aiAssistVisible));
    setAiCompareMode("manual");
  };

  const loadSample = (nextSampleId: string) => {
    const nextSample = findSample(nextSampleId);
    setSampleId(nextSample.id);
    setFocus(getDefaultFocus(nextSample.id));
    setMotion(getDefaultMotion(nextSample.id));
    setManual(getDefaultManual(nextSample.id));
    setHintStrokes([]);
    setGroupBoxes([]);
    setPlateStack(getDefaultPlateStack(nextSample.id, getDefaultFocus(nextSample.id)));
    setGroupDraft(null);
    setMatteSeedMode("add");
    setMatteSeeds([]);
    setManualGroupBaseline([]);
    setAiCompareMode("manual");
    return nextSample.id;
  };

  const setPlateVisibility = (plateId: string, visible: boolean) => {
    setPlateStack((prev) =>
      prev.map((plate) => (plate.id === plateId ? { ...plate, visible } : plate)),
    );
    return visible;
  };

  const movePlate = (plateId: string, direction: -1 | 1) => {
    let changed = false;
    setPlateStack((prev) => {
      const next = movePlateInStack(prev, plateId, direction);
      changed = next !== prev;
      return next;
    });
    return changed;
  };

  const nudgePlateZ = (plateId: string, delta: number) => {
    let nextValue: number | null = null;
    setPlateStack((prev) =>
      prev.map((plate) => {
        if (plate.id !== plateId) return plate;
        nextValue = clamp(plate.z + delta, -64, 64);
        return { ...plate, z: nextValue };
      }),
    );
    return nextValue;
  };

  const applyAiAssistSuggestion = (mode: AiCompareMode = "blend") => {
    if (!aiAssistSuggestion) return 0;
    const manualBoxes = groupBoxes.filter((box) => !box.id.startsWith("ai-"));
    setManualGroupBaseline(manualBoxes);
    const nextBoxes: GroupBox[] = [];
    for (const box of aiAssistSuggestion.accepted_foreground_groups) {
      nextBoxes.push({
        id: `ai-fg-${box.label}-${box.x}-${box.y}`,
        mode: "foreground-group",
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
      });
    }
    for (const box of aiAssistSuggestion.accepted_midground_groups) {
      nextBoxes.push({
        id: `ai-mid-${box.label}-${box.x}-${box.y}`,
        mode: "midground-group",
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
      });
    }
    setGroupBoxes(mode === "ai" ? nextBoxes : [...manualBoxes, ...nextBoxes]);
    setAiAssistVisible(true);
    setAiCompareMode(mode);
    return nextBoxes.length;
  };

  const applyQwenPlatePlan = () => {
    const proposal = qwenPlatePlan?.plate_stack_proposal;
    if (!proposal?.plates?.length) return 0;
    const nextPlates = normalizeImportedPlateStack(
      proposal.plates as Plate[],
      getDefaultPlateStack(sampleId, focus),
    );
    setPlateStack(nextPlates);
    return nextPlates.length;
  };

  const applyQwenPlateGate = () => {
    const proposal = qwenPlateGate?.gated_plate_stack;
    if (!proposal?.plates?.length) return 0;
    const nextPlates = normalizeImportedPlateStack(
      proposal.plates as Plate[],
      getDefaultPlateStack(sampleId, focus),
    );
    setPlateStack(nextPlates);
    return nextPlates.length;
  };

  const restoreManualGroups = () => {
    const fallbackManual = groupBoxes.filter((box) => !box.id.startsWith("ai-"));
    const nextManual = manualGroupBaseline.length > 0 ? manualGroupBaseline : fallbackManual;
    setGroupBoxes(nextManual);
    setAiCompareMode("manual");
    return nextManual.length;
  };

  const applyRecommendedPreset = () => {
    setMotion((prev) => ({
      ...prev,
      overscanPct: snapshot.recommendedOverscanPct,
      travelXPct: snapshot.safeTravelXPct,
      travelYPct: snapshot.safeTravelYPct,
      zoom: clamp(prev.zoom, 1.035, 1.06),
    }));
    return snapshot;
  };

  const applyRenderMode = (mode: RenderMode) => {
    setManual((prev) => ({ ...prev, renderMode: mode }));
    if (mode === "safe") {
      setMotion((prev) => ({
        ...prev,
        overscanPct: snapshot.recommendedOverscanPct,
        travelXPct: snapshot.safeTravelXPct,
        travelYPct: snapshot.safeTravelYPct,
        zoom: clamp(prev.zoom, 1.02, 1.048),
        layerCount: 2,
      }));
    } else if (mode === "three-layer") {
      setMotion((prev) => ({
        ...prev,
        overscanPct: Math.max(prev.overscanPct, snapshot.recommendedOverscanPct),
        layerCount: Math.max(3, prev.layerCount),
        layerGapPx: Math.max(prev.layerGapPx, 18),
      }));
    } else {
      setMotion(getDefaultMotion(sample.id));
    }
    return mode;
  };

  const pointerToNormalized = (clientX: number, clientY: number) => {
    const rect = stageRef.current?.getBoundingClientRect();
    if (!rect) return null;
    const x = clamp((clientX - rect.left) / Math.max(1, rect.width), 0, 1);
    const y = clamp((clientY - rect.top) / Math.max(1, rect.height), 0, 1);
    return { x, y };
  };

  const beginStroke = (clientX: number, clientY: number) => {
    const point = pointerToNormalized(clientX, clientY);
    if (!point) return;
    const id = `stroke-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    drawingStrokeIdRef.current = id;
    setHintStrokes((prev) => [...prev, { id, mode: brushMode, size: brushSize, points: [point] }]);
  };

  const extendStroke = (clientX: number, clientY: number) => {
    const point = pointerToNormalized(clientX, clientY);
    const strokeId = drawingStrokeIdRef.current;
    if (!point || !strokeId) return;
    setHintStrokes((prev) =>
      prev.map((stroke) =>
        stroke.id === strokeId
          ? {
              ...stroke,
              points: [...stroke.points, point],
            }
          : stroke,
      ),
    );
  };

  const endStroke = () => {
    drawingStrokeIdRef.current = null;
  };

  const appendMatteSeed = (point: HintPoint, mode: MatteSeedMode = matteSeedMode) => {
    const depth = computeResolvedDepth(sample, focus, manual, point.x, point.y, realDepth);
    setMatteSeeds((prev) => [
      ...prev,
      { id: `matte-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, mode, x: point.x, y: point.y, depth },
    ]);
    setMatteSettings((prev) => ({ ...prev, visible: true }));
  };

  const addMatteSeed = (clientX: number, clientY: number) => {
    const point = pointerToNormalized(clientX, clientY);
    if (!point) return;
    appendMatteSeed(point);
  };

  const beginGroupDraft = (clientX: number, clientY: number) => {
    const point = pointerToNormalized(clientX, clientY);
    if (!point) return;
    setGroupDraft({ start: point, end: point });
  };

  const extendGroupDraft = (clientX: number, clientY: number) => {
    const point = pointerToNormalized(clientX, clientY);
    if (!point) return;
    setGroupDraft((prev) => (prev ? { ...prev, end: point } : prev));
  };

  const endGroupDraft = () => {
    setGroupDraft((draft) => {
      if (!draft) return null;
      const normalized = normalizeBox(draft.start, draft.end);
      if (normalized.width < 0.02 || normalized.height < 0.02) {
        return null;
      }
      if (groupMode === "erase-group") {
        setGroupBoxes((prev) => prev.filter((box) => !intersectsBox(box, normalized)));
      } else {
        const nextBox: GroupBox = {
          id: `group-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          mode: groupMode,
          x: normalized.x,
          y: normalized.y,
          width: normalized.width,
          height: normalized.height,
        };
        setGroupBoxes((prev) => [...prev, nextBox]);
      }
      return null;
    });
  };

  useEffect(() => {
    try {
      window.localStorage.setItem(JOB_STATE_STORAGE_KEY, JSON.stringify(buildJobState()));
    } catch (error) {
      console.warn("MARKER_180.PARALLAX.JOB_STATE.WRITE_FAILED", error);
    }
  }, [
    sampleId,
    focus,
    motion,
    manual,
    stageTool,
    brushMode,
    brushSize,
    hintStrokes,
    groupMode,
    groupBoxes,
    matteSeedMode,
    matteSettings,
    matteSeeds,
    guidedHintsVisible,
    aiAssistVisible,
    plateStack,
  ]);

  useEffect(() => {
    const api = {
      snapshot: () => snapshot,
      print: () => {
        console.info("MARKER_180.PARALLAX.SNAPSHOT", snapshot);
        return snapshot;
      },
      getState: () => ({
        sampleId,
        focus,
        motion,
        manual,
        previewMode: manual.previewMode,
        stageTool,
        brushMode,
        brushSize,
        hintStrokeCount: hintStrokes.length,
        groupMode,
        groupBoxCount: groupBoxes.length,
        plateCount: plateStack.length,
        workflowRoutingMode: workflowRouting.mode,
        workflowRoutingReasons: workflowRouting.reasons,
        cameraSafe: plateLayout.cameraSafe.ok,
        cameraSafeWarning: plateLayout.cameraSafe.warning,
        riskyPlateCount: plateLayout.cameraSafe.riskyPlateIds.length,
        worstTransitionRisk: plateLayout.cameraSafe.worstTransitionRisk,
        cameraSafeSuggestedOverscanPct: plateLayout.cameraSafe.suggestion.overscanPct,
        cameraSafeSuggestedTravelXPct: plateLayout.cameraSafe.suggestion.travelXPct,
        cameraSafeSuggestedTravelYPct: plateLayout.cameraSafe.suggestion.travelYPct,
        cameraSafeSuggestionReason: plateLayout.cameraSafe.suggestion.reason,
        matteSeedMode,
        matteSeedCount: matteSeeds.length,
        debugOpen,
        guidedHintsVisible,
        aiAssistVisible,
        aiCompareMode,
        selectionCoverage: proxyMaps.selectionCoverage,
        midgroundCoverage: proxyMaps.midgroundCoverage,
        matteCoverage: proxyMaps.matteCoverage,
        nearMean: proxyMaps.nearMean,
        sourceRasterReady: Boolean(sourceRaster),
        usingRealDepth: proxyMaps.usingRealDepth,
        closerCoverage: proxyMaps.closerCoverage,
        fartherCoverage: proxyMaps.fartherCoverage,
        protectCoverage: proxyMaps.protectCoverage,
        foregroundGroupCoverage: proxyMaps.foregroundGroupCoverage,
        midgroundGroupCoverage: proxyMaps.midgroundGroupCoverage,
      }),
      setSample: (nextSampleId: string) => loadSample(nextSampleId),
      setMotion: (travelXPct: number, travelYPct: number, zoom?: number) => {
        setMotion((prev) => ({
          ...prev,
          travelXPct: clamp(travelXPct, 0, 10),
          travelYPct: clamp(travelYPct, 0, 5),
          zoom: clamp(zoom ?? prev.zoom, 1, 1.1),
        }));
      },
      setFocus: (x: number, y: number, width: number, height: number, feather = focus.feather) => {
        setFocus({
          x: clamp(x, 0.2, 0.8),
          y: clamp(y, 0.2, 0.8),
          width: clamp(width, 0.15, 0.8),
          height: clamp(height, 0.2, 0.9),
          feather: clamp(feather, 0.02, 0.35),
        });
      },
      setPreviewMode: (mode: PreviewMode) => {
        setManual((prev) => ({ ...prev, previewMode: mode }));
        return mode;
      },
      setRenderMode: (mode: RenderMode) => applyRenderMode(mode),
      setStageTool: (mode: StageTool) => {
        setStageTool(mode);
        return mode;
      },
      hydrateSourceRasterFromStage: () => hydrateSourceRasterFromStage(),
      hydrateSourceRasterFromAsset: () => hydrateSourceRasterFromAsset(),
      setBrushMode: (mode: BrushMode) => {
        setBrushMode(mode);
        return mode;
      },
      setMatteSeedMode: (mode: MatteSeedMode) => {
        setMatteSeedMode(mode);
        return mode;
      },
      clearManualHints: () => {
        setHintStrokes([]);
        return 0;
      },
      exportManualHints: () => buildManualHintsContract(),
      importManualHints: (payload: string | ManualHintsContract) => {
        try {
          const nextState = typeof payload === "string" ? (JSON.parse(payload) as ManualHintsContract) : payload;
          if (nextState.sampleId && nextState.sampleId !== sampleId) {
            setSampleId(findSample(nextState.sampleId).id);
          }
          setBrushMode(nextState.brushMode || "closer");
          setBrushSize(clamp(nextState.brushSize ?? brushSize, 0.01, 0.12));
          setHintStrokes(nextState.hintStrokes || []);
          return true;
        } catch (error) {
          console.warn("MARKER_180.PARALLAX.HINTS.IMPORT_FAILED", error);
          return false;
        }
      },
      setGroupMode: (mode: GroupMode) => {
        setGroupMode(mode);
        return mode;
      },
      clearGroupBoxes: () => {
        setGroupBoxes([]);
        setGroupDraft(null);
        setAiCompareMode("manual");
        return 0;
      },
      exportGroupBoxes: () => buildGroupBoxesContract(),
      importGroupBoxes: (payload: string | GroupBoxesContract) => {
        try {
          const nextState = typeof payload === "string" ? (JSON.parse(payload) as GroupBoxesContract) : payload;
          if (nextState.sampleId && nextState.sampleId !== sampleId) {
            setSampleId(findSample(nextState.sampleId).id);
          }
          setGroupMode(nextState.groupMode || "foreground-group");
          setGroupBoxes(nextState.groupBoxes || []);
          setGroupDraft(null);
          setAiCompareMode("manual");
          return true;
        } catch (error) {
          console.warn("MARKER_180.PARALLAX.GROUPS.IMPORT_FAILED", error);
          return false;
        }
      },
      exportPlateStack: () => buildPlateStackContract(),
      exportPlateLayout: () => buildPlateLayoutContract(),
      exportPlateAssets: () => buildPlateExportAssetsContract(),
      importPlateStack: (payload: string | PlateStackContract) => {
        try {
          const nextState = typeof payload === "string" ? (JSON.parse(payload) as PlateStackContract) : payload;
          if (nextState.sampleId && nextState.sampleId !== sampleId) {
            const nextSample = findSample(nextState.sampleId);
            setSampleId(nextSample.id);
          }
          setPlateStack(
            normalizeImportedPlateStack(
              nextState.plates,
              getDefaultPlateStack(sampleId, focus),
            ),
          );
          return true;
        } catch (error) {
          console.warn("MARKER_180.PARALLAX.PLATES.IMPORT_FAILED", error);
          return false;
        }
      },
      setPlateVisibility: (plateId: string, visible: boolean) => setPlateVisibility(plateId, visible),
      movePlate: (plateId: string, direction: -1 | 1) => movePlate(plateId, direction),
      nudgePlateZ: (plateId: string, delta: number) => nudgePlateZ(plateId, delta),
      clearMatteSeeds: () => {
        setMatteSeeds([]);
        return 0;
      },
      appendMatteSeed: (x: number, y: number, mode = matteSeedMode) => {
        appendMatteSeed({ x: clamp(x, 0, 1), y: clamp(y, 0, 1) }, mode);
        return matteSeeds.length + 1;
      },
      removeLastMatteSeed: () => {
        setMatteSeeds((prev) => prev.slice(0, -1));
        return Math.max(0, matteSeeds.length - 1);
      },
      toggleMatteOverlay: () => {
        setMatteSettings((prev) => ({ ...prev, visible: !prev.visible }));
        return !matteSettings.visible;
      },
      exportProxyAssets: () => buildProxyAssetsContract(),
      exportAlgorithmicMatte: () => buildAlgorithmicMatteContract(),
      importAlgorithmicMatte: (payload: string | AlgorithmicMatteContract) => {
        try {
          const nextState = typeof payload === "string" ? (JSON.parse(payload) as AlgorithmicMatteContract) : payload;
          if (nextState.sampleId && nextState.sampleId !== sampleId) {
            setSampleId(findSample(nextState.sampleId).id);
          }
          setMatteSettings({ ...nextState.matteSettings, visible: true });
          setMatteSeeds(nextState.matteSeeds || []);
          return true;
        } catch (error) {
          console.warn("MARKER_180.PARALLAX.MATTE.IMPORT_FAILED", error);
          return false;
        }
      },
      setOverscan: (overscanPct: number) => {
        setMotion((prev) => ({ ...prev, overscanPct: clamp(overscanPct, 4, 32) }));
      },
      setPhase: (phase: number) => {
        setMotion((prev) => ({ ...prev, phase: clamp(phase, 0, 1) }));
      },
      setLayerCount: (layerCount: number) => {
        setMotion((prev) => ({ ...prev, layerCount: Math.round(clamp(layerCount, 2, 5)) }));
      },
      setGuidedHintsVisible: (value: boolean) => {
        setGuidedHintsVisible(value);
        return value;
      },
      toggleGuidedHints: () => {
        setGuidedHintsVisible((value) => !value);
        return !guidedHintsVisible;
      },
      toggleDebug: () => {
        setDebugOpen((value) => !value);
        return !debugOpen;
      },
      exportJobState: () => buildJobState(),
      importJobState: (payload: string | ManualJobState) => {
        try {
          const nextState = typeof payload === "string" ? (JSON.parse(payload) as ManualJobState) : payload;
          applyJobState(nextState);
          return true;
        } catch (error) {
          console.warn("MARKER_180.PARALLAX.JOB_STATE.IMPORT_FAILED", error);
          return false;
        }
      },
      clearStoredJobState: () => {
        try {
          window.localStorage.removeItem(JOB_STATE_STORAGE_KEY);
          return true;
        } catch (error) {
          console.warn("MARKER_180.PARALLAX.JOB_STATE.CLEAR_FAILED", error);
          return false;
        }
      },
      toggleAiAssistOverlay: () => {
        setAiAssistVisible((value) => !value);
        return !aiAssistVisible;
      },
      applyAiAssistSuggestion: () => applyAiAssistSuggestion(),
      applyRecommendedPreset,
      applyQwenPlatePlan,
      applyQwenPlateGate,
    };

    window.vetkaParallaxLab = api;
    installDebugBridge({
      getSnapshot: () => snapshot,
      getApis: () => ({ vetkaParallaxLab: api }),
    });

    return () => {
      if (window.vetkaParallaxLab === api) delete window.vetkaParallaxLab;
    };
  }, [sampleId, focus, motion, manual, stageTool, brushMode, brushSize, hintStrokes.length, groupMode, groupBoxes.length, plateStack, matteSeeds.length, debugOpen, guidedHintsVisible, aiAssistVisible, snapshot, aiAssistSuggestion, matteSettings.visible, aiCompareMode, qwenPlatePlan, qwenPlateGate]);

  const sourceUrl = `/samples/${sample.fileName}`;
  const hintUrl = `/sample_hints/${sample.id}.png`;
  const depthMaskImage = `url("${proxyMaps.selectionMaskUrl}")`;
  const backgroundMaskImage = `url("${plateCompositeMaps.backgroundMaskUrl}")`;
  const backgroundRgbaUrl = plateCompositeMaps.backgroundRgbaUrl;
  const effectiveBackgroundSourceUrl = sourceRaster ? backgroundRgbaUrl || sourceUrl : sourceUrl;
  const groupDraftBox = groupDraft ? normalizeBox(groupDraft.start, groupDraft.end) : null;
  const midMaskImage = `url("${proxyMaps.midgroundMaskUrl}")`;
  const showSelectionOverlays = manual.previewMode === "selection";
  const backgroundOffsetX = Number((-snapshot.travelXPct * motion.phase * 0.22).toFixed(3));
  const backgroundOffsetY = Number((-snapshot.travelYPct * motion.phase * 0.22).toFixed(3));
  const foregroundOffsetX = Number((snapshot.travelXPct * motion.phase * 0.78).toFixed(3));
  const foregroundOffsetY = Number((snapshot.travelYPct * motion.phase * 0.84).toFixed(3));
  const foregroundFrame = {
    left: `${(focus.x - focus.width / 2) * 100}%`,
    top: `${(focus.y - focus.height / 2) * 100}%`,
    width: `${focus.width * 100}%`,
    height: `${focus.height * 100}%`,
  };

  const captureSourceRasterFromImage = (image: HTMLImageElement) => {
    if (sourceRaster || image.naturalWidth <= 0 || image.naturalHeight <= 0) return;
    const canvas = document.createElement("canvas");
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(image, 0, 0);
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    setSourceRaster({
      sampleId,
      width: canvas.width,
      height: canvas.height,
      values: imageData.data,
    });
  };

  const hydrateSourceRasterFromStage = () => {
    const candidates = [
      stageRef.current?.querySelector(".background-plane img") as HTMLImageElement | null,
      ...(Array.from(document.querySelectorAll("img")) as HTMLImageElement[]),
    ].filter((image): image is HTMLImageElement => Boolean(image));
    const image = candidates.find(
      (entry) =>
        entry.complete &&
        entry.naturalWidth > 0 &&
        entry.naturalHeight > 0 &&
        entry.currentSrc.includes(sample.fileName),
    );
    if (!image) return false;
    captureSourceRasterFromImage(image);
    return true;
  };

  const hydrateSourceRasterFromAsset = async () => {
    try {
      const response = await fetch(`/samples/${sample.fileName}`, { cache: "no-store" });
      if (!response.ok) return false;
      const blob = await response.blob();
      const bitmap = await createImageBitmap(blob);
      const canvas = document.createElement("canvas");
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        bitmap.close();
        return false;
      }
      ctx.drawImage(bitmap, 0, 0);
      bitmap.close();
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      setSourceRaster({
        sampleId,
        width: canvas.width,
        height: canvas.height,
        values: imageData.data,
      });
      return true;
    } catch {
      return false;
    }
  };
  const exportTargets = [
    { label: "Depth BW", value: "PNG 16/8-bit" },
    { label: "Layers RGBA", value: "PNG + alpha" },
    { label: "Preview", value: "MP4 / 25 fps" },
  ];
  const renderPolicy = `25 out / 50 internal / tmix 3`;
  const plateLayout = buildPreviewPlateLayoutContract();
  const exportLayout = buildPlateLayoutContract();
  const previewPlateLayers = plateLayout.plates.filter(
    (plate) => plate.visible && plate.role !== "background-far" && plate.role !== "special-clean",
  );
  const effectivePreviewPlateLayers = previewPlateLayers.filter(
    (plate) => (plateCompositeMaps.plateCoverage[plate.id] || 0) > 0.002,
  );
  return (
    <div className={`parallax-app ${debugOpen ? "debug-open" : ""}`}>
      <aside className="left-rail">
        <div className="brand-card">
          <div className="brand-topline">
            <div>
              <div className="eyebrow">VETKA / MCC / PARALLAX</div>
              <h1>Photo Parallax Lab</h1>
            </div>
            <button className="ghost-button" type="button" onClick={() => setDebugOpen((value) => !value)}>
              {debugOpen ? "hide debug" : "show debug"}
            </button>
          </div>
          <p>Depth-first monochrome control surface for photo-to-parallax shots.</p>
          <div className="brand-metrics">
            <span className="chip">25 fps base</span>
            <span className="chip">50 internal</span>
            <span className="chip">tmix 3</span>
          </div>
        </div>

        <section className="panel panel-compact">
          <div className="panel-header">
            <div className="panel-title-wrap">
              <Icon name="import" />
              <div>
                <h2>Import</h2>
                <div className="panel-subtitle">Source frame and sample scene</div>
              </div>
            </div>
          </div>
          <div className="sample-grid">
            {SAMPLE_LIBRARY.map((entry) => (
              <button
                key={entry.id}
                className={`sample-button ${entry.id === sample.id ? "active" : ""}`}
                type="button"
                onClick={() => loadSample(entry.id)}
              >
                <img src={`/samples/${entry.fileName}`} alt={entry.title} />
                <span>{entry.title}</span>
              </button>
            ))}
          </div>
          <div className="sample-note">
            <strong>{sample.scenario}</strong>
            {debugOpen ? <p>{sample.notes}</p> : null}
            <div className="sample-meta-row">
              <span>{sample.width} × {sample.height}</span>
              <span>{sample.tags.slice(0, 2).join(" / ")}</span>
            </div>
          </div>
        </section>

        <section className="panel panel-compact">
          <div className="panel-header">
            <div className="panel-title-wrap">
              <Icon name="preview" />
              <div>
                <h2>View</h2>
                <div className="panel-subtitle">Preview mode and render path</div>
              </div>
            </div>
          </div>
          <InlineSegmentedControl
            value={manual.previewMode}
            options={[
              { label: "composite", value: "composite" },
              { label: "depth", value: "depth" },
              { label: "selection", value: "selection" },
            ]}
            onChange={(value) => setManual((prev) => ({ ...prev, previewMode: value as PreviewMode }))}
          />
          <InlineSegmentedControl
            value={manual.renderMode}
            options={[
              { label: "auto", value: "auto" },
              { label: "safe", value: "safe" },
              { label: "3-layer", value: "three-layer" },
            ]}
            onChange={(value) => applyRenderMode(value as RenderMode)}
          />
          <ToggleButton
            active={manual.invertDepth}
            label="invert depth"
            onClick={() => setManual((prev) => ({ ...prev, invertDepth: !prev.invertDepth }))}
          />
        </section>

        {debugOpen ? (
          <>
            <section className="panel">
              <div className="panel-header">
                <h2>Focus Proxy</h2>
              </div>
              <RangeControl label="focus x" value={focus.x} min={0.2} max={0.8} step={0.01} onChange={(value) => setFocus((prev) => ({ ...prev, x: value }))} />
              <RangeControl label="focus y" value={focus.y} min={0.2} max={0.8} step={0.01} onChange={(value) => setFocus((prev) => ({ ...prev, y: value }))} />
              <RangeControl label="focus width" value={focus.width} min={0.15} max={0.8} step={0.01} onChange={(value) => setFocus((prev) => ({ ...prev, width: value }))} />
              <RangeControl label="focus height" value={focus.height} min={0.2} max={0.9} step={0.01} onChange={(value) => setFocus((prev) => ({ ...prev, height: value }))} />
              <RangeControl label="focus feather" value={focus.feather} min={0.02} max={0.35} step={0.01} onChange={(value) => setFocus((prev) => ({ ...prev, feather: value }))} />
              <div className="panel-copy">
                Depth preview prefers real baked depth when available. Samples without baked depth still fall back to the focus-driven proxy map.
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <h2>Guided Hints</h2>
                <button className="ghost-button" type="button" onClick={() => setGuidedHintsVisible((value) => !value)}>
                  {guidedHintsVisible ? "hide hints" : "show hints"}
                </button>
              </div>
              <p className="guided-note">
                `mask_hint.png` contract for assisted mode. Red marks closer subject regions, blue pushes background, green protects ambiguous detail.
              </p>
              <div className="chip-row">
                <span className="chip hint-chip hint-red">closer</span>
                <span className="chip hint-chip hint-blue">farther</span>
                <span className="chip hint-chip hint-green">protect</span>
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <h2>Stage Tools</h2>
              </div>
              <SegmentedControl
                label="tool"
                value={stageTool}
                options={[
                  { label: "brush", value: "brush" },
                  { label: "group", value: "group" },
                  { label: "matte", value: "matte" },
                ]}
                onChange={(value) => setStageTool(value as StageTool)}
              />
              <div className="panel-copy">
                `brush` nudges local depth. `group` locks a whole region into foreground or midground. `matte` drops click seeds and grows a roto-style matte.
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <h2>Algorithmic Matte</h2>
                <button className="ghost-button" type="button" onClick={() => setMatteSeeds([])}>
                  clear
                </button>
              </div>
              <SegmentedControl
                label="matte mode"
                value={matteSeedMode}
                options={[
                  { label: "add", value: "add" },
                  { label: "subtract", value: "subtract" },
                  { label: "protect", value: "protect" },
                ]}
                onChange={(value) => setMatteSeedMode(value as MatteSeedMode)}
              />
              <SegmentedControl
                label="matte view"
                value={matteSettings.view}
                options={[
                  { label: "rgb", value: "rgb" },
                  { label: "depth", value: "depth" },
                ]}
                onChange={(value) => setMatteSettings((prev) => ({ ...prev, view: value as MatteView }))}
              />
              <ToggleButton active={matteSettings.visible} label="show matte overlay" onClick={() => setMatteSettings((prev) => ({ ...prev, visible: !prev.visible }))} />
              <RangeControl label="grow radius" value={matteSettings.growRadius} min={0.05} max={0.28} step={0.005} onChange={(value) => setMatteSettings((prev) => ({ ...prev, growRadius: value }))} />
              <RangeControl label="edge snap" value={matteSettings.edgeSnap} min={0.04} max={0.28} step={0.005} onChange={(value) => setMatteSettings((prev) => ({ ...prev, edgeSnap: value }))} />
              <RangeControl label="matte opacity" value={matteSettings.opacity} min={0.2} max={0.95} step={0.01} onChange={(value) => setMatteSettings((prev) => ({ ...prev, opacity: value }))} />
              <div className="mini-stat-grid">
                <MiniStat label="seeds" value={`${matteSeeds.length}`} />
                <MiniStat label="coverage" value={formatPct(proxyMaps.matteCoverage * 100)} />
                <MiniStat label="mode" value={matteSeedMode} />
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <h2>Hint Brushes</h2>
                <button className="ghost-button" type="button" onClick={() => setHintStrokes([])}>
                  clear
                </button>
              </div>
              <SegmentedControl
                label="brush"
                value={brushMode}
                options={[
                  { label: "closer", value: "closer" },
                  { label: "farther", value: "farther" },
                  { label: "protect", value: "protect" },
                  { label: "erase", value: "erase" },
                ]}
                onChange={(value) => setBrushMode(value as BrushMode)}
              />
              <RangeControl label="brush size" value={brushSize} min={0.01} max={0.12} step={0.005} onChange={(value) => setBrushSize(value)} />
              <div className="mini-stat-grid">
                <MiniStat label="strokes" value={`${hintStrokes.length}`} />
                <MiniStat label="closer" value={formatPct(proxyMaps.closerCoverage * 100)} />
                <MiniStat label="farther" value={formatPct(proxyMaps.fartherCoverage * 100)} />
                <MiniStat label="protect" value={formatPct(proxyMaps.protectCoverage * 100)} />
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <h2>Merge Groups</h2>
                <button className="ghost-button" type="button" onClick={() => {
                  setGroupBoxes([]);
                  setGroupDraft(null);
                }}>
                  clear
                </button>
              </div>
              <SegmentedControl
                label="group mode"
                value={groupMode}
                options={[
                  { label: "fg group", value: "foreground-group" },
                  { label: "mid group", value: "midground-group" },
                  { label: "erase", value: "erase-group" },
                ]}
                onChange={(value) => setGroupMode(value as GroupMode)}
              />
              <div className="mini-stat-grid">
                <MiniStat label="boxes" value={`${groupBoxes.length}`} />
                <MiniStat label="fg area" value={formatPct(proxyMaps.foregroundGroupCoverage * 100)} />
                <MiniStat label="mid area" value={formatPct(proxyMaps.midgroundGroupCoverage * 100)} />
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <h2>AI Assist</h2>
                <button className="ghost-button" type="button" onClick={() => setAiAssistVisible((value) => !value)}>
                  {aiAssistVisible ? "hide" : "show"}
                </button>
              </div>
              <div className="panel-copy">
                Local `qwen2.5vl:3b` suggests coarse semantic groups. Suggestions are filtered before they can affect the stage.
              </div>
              <div className="mini-stat-grid">
                <MiniStat label="model" value={aiAssistSuggestion?.model || "offline"} />
                <MiniStat label="confidence" value={aiAssistSuggestion ? `${Math.round(aiAssistSuggestion.confidence * 100)}%` : "n/a"} />
                <MiniStat label="compare" value={aiCompareMode} />
              </div>
              {aiAssistSuggestion ? (
                <>
                  <div className="panel-copy">
                    {aiAssistSuggestion.primary_subject || aiAssistSuggestion.scene_summary || "No semantic summary yet."}
                  </div>
                  <div className="chip-row">
                    {aiAssistSuggestion.sanitation_flags.map((flag) => (
                      <span className="chip" key={flag}>{flag}</span>
                    ))}
                  </div>
                  <div className="action-row">
                    <button className="ghost-button" type="button" onClick={() => setAiAssistVisible((value) => !value)}>
                      {aiAssistVisible ? "hide overlay" : "show overlay"}
                    </button>
                    <button className="ghost-button" type="button" onClick={() => applyAiAssistSuggestion("ai")}>
                      ai only
                    </button>
                    <button className="ghost-button" type="button" onClick={() => applyAiAssistSuggestion("blend")}>
                      blend
                    </button>
                    <button className="ghost-button" type="button" onClick={restoreManualGroups}>
                      restore manual
                    </button>
                  </div>
                </>
              ) : (
                <div className="panel-copy">No cached AI suggestion found for this sample.</div>
              )}
            </section>
          </>
        ) : null}
      </aside>

      <main className="main-pane">
        <div className="stage-header">
          <div>
            <div className="eyebrow">Proxy Preview</div>
            <h2>{sample.title}</h2>
          </div>
          <div className="metric-strip">
            <MetricPill label="preview" value={`${snapshot.previewScore}/100`} tone={snapshot.previewScore >= 72 ? "good" : snapshot.previewScore >= 50 ? "mid" : "bad"} />
            <MetricPill label="disocclusion" value={`${snapshot.disocclusionRisk}`} tone={snapshot.disocclusionRisk < 35 ? "good" : snapshot.disocclusionRisk < 60 ? "mid" : "bad"} />
            <MetricPill label="cardboard" value={`${snapshot.cardboardRisk}`} tone={snapshot.cardboardRisk < 35 ? "good" : snapshot.cardboardRisk < 60 ? "mid" : "bad"} />
            <MetricPill label="overscan" value={formatPct(snapshot.overscanPct)} tone={snapshot.overscanPct >= snapshot.minSafeOverscanPct ? "good" : "bad"} />
          </div>
        </div>

        <div className="stage-shell" ref={stageRef}>
          <div className="stage-grid" />
          <div
            className={`hint-editor-surface ${stageTool === "group" ? "group-mode" : stageTool === "matte" ? "matte-mode" : "brush-mode"}`}
            onPointerDown={(event) => {
              event.preventDefault();
              if (stageTool === "brush") {
                beginStroke(event.clientX, event.clientY);
                return;
              }
              if (stageTool === "matte") {
                addMatteSeed(event.clientX, event.clientY);
                return;
              }
              beginGroupDraft(event.clientX, event.clientY);
            }}
            onPointerMove={(event) => {
              if ((event.buttons & 1) !== 1) return;
              if (stageTool === "brush") {
                extendStroke(event.clientX, event.clientY);
                return;
              }
              if (stageTool === "matte") {
                return;
              }
              extendGroupDraft(event.clientX, event.clientY);
            }}
            onPointerUp={() => {
              if (stageTool === "brush") {
                endStroke();
                return;
              }
              if (stageTool === "matte") {
                return;
              }
              endGroupDraft();
            }}
            onPointerLeave={() => {
              if (stageTool === "brush") {
                endStroke();
                return;
              }
              if (stageTool === "matte") {
                return;
              }
              endGroupDraft();
            }}
          />
          {manual.previewMode === "depth" ? (
            <div className="depth-preview-plane">
              <img src={proxyMaps.depthUrl} alt={`${sample.title} depth preview`} />
            </div>
          ) : null}
          {manual.previewMode !== "depth" && guidedHintsVisible && showSelectionOverlays ? (
            <div className="guided-hint-plane">
              <img src={hintUrl} alt={`${sample.title} guided hint overlay`} />
            </div>
          ) : null}
          {manual.previewMode !== "depth" ? (
            <>
              <div
                className="parallax-plane background-plane"
                style={{
                  transform: `translate3d(${backgroundOffsetX}%, ${backgroundOffsetY}%, ${-layoutMotion.layerGapPx}px) scale(${1 + motion.overscanPct / 100})`,
                  WebkitMaskImage:
                    effectivePreviewPlateLayers.length > 0 && !backgroundRgbaUrl ? backgroundMaskImage : undefined,
                  maskImage:
                    effectivePreviewPlateLayers.length > 0 && !backgroundRgbaUrl ? backgroundMaskImage : undefined,
                  WebkitMaskRepeat: effectivePreviewPlateLayers.length > 0 && !backgroundRgbaUrl ? "no-repeat" : undefined,
                  maskRepeat: effectivePreviewPlateLayers.length > 0 && !backgroundRgbaUrl ? "no-repeat" : undefined,
                  WebkitMaskSize: effectivePreviewPlateLayers.length > 0 && !backgroundRgbaUrl ? "100% 100%" : undefined,
                  maskSize: effectivePreviewPlateLayers.length > 0 && !backgroundRgbaUrl ? "100% 100%" : undefined,
                }}
              >
                <img
                  src={effectiveBackgroundSourceUrl}
                  alt={sample.title}
                  onLoad={(event) => {
                    if (!sourceRaster && event.currentTarget.currentSrc.endsWith(sample.fileName)) {
                      captureSourceRasterFromImage(event.currentTarget);
                    }
                  }}
                />
              </div>
              {effectivePreviewPlateLayers.length > 0 ? (
                effectivePreviewPlateLayers.map((plate) => {
                  const xOffset = foregroundOffsetX * plate.parallaxStrength;
                  const yOffset = foregroundOffsetY * plate.parallaxStrength * 0.92;
                  const scale = 1 + (motion.zoom - 1) * plate.parallaxStrength;
                  const blurPx = manual.blurPx * plate.motionDamping * 0.42;
                  const plateMaskUrl = plateCompositeMaps.plateMaskUrls[plate.id];
                  const plateRgbaUrl = plateCompositeMaps.plateRgbaUrls[plate.id];
                  return (
                    <div
                      key={plate.id}
                      className={`parallax-plane plate-render-plane role-${plate.role}`}
                      style={{
                        zIndex: 3 + plate.order,
                        transform: `translate3d(${xOffset}%, ${yOffset}%, ${plate.z}px) scale(${scale})`,
                        filter: `blur(${blurPx}px)`,
                        WebkitMaskImage: plateMaskUrl && !plateRgbaUrl ? `url("${plateMaskUrl}")` : undefined,
                        maskImage: plateMaskUrl && !plateRgbaUrl ? `url("${plateMaskUrl}")` : undefined,
                        WebkitMaskRepeat: plateMaskUrl && !plateRgbaUrl ? "no-repeat" : undefined,
                        maskRepeat: plateMaskUrl && !plateRgbaUrl ? "no-repeat" : undefined,
                        WebkitMaskSize: plateMaskUrl && !plateRgbaUrl ? "100% 100%" : undefined,
                        maskSize: plateMaskUrl && !plateRgbaUrl ? "100% 100%" : undefined,
                      }}
                    >
                      <img src={plateRgbaUrl || sourceUrl} alt={`${sample.title} ${plate.label}`} />
                    </div>
                  );
                })
              ) : manual.renderMode === "three-layer" ? (
                <div
                  className="parallax-plane midground-plane"
                  style={{
                    transform: `translate3d(${foregroundOffsetX * 0.48}%, ${foregroundOffsetY * 0.48}%, ${motion.layerGapPx * 0.28}px) scale(${1 + (motion.zoom - 1) * 0.36})`,
                    WebkitMaskImage: midMaskImage,
                    maskImage: midMaskImage,
                    filter: `blur(${manual.blurPx * 0.3}px)`,
                  }}
                >
                  <img src={sourceUrl} alt={`${sample.title} midground proxy`} />
                </div>
              ) : null}

              {effectivePreviewPlateLayers.length === 0 ? (
                <div
                  className="parallax-plane foreground-plane"
                  style={{
                    transform: `translate3d(${foregroundOffsetX}%, ${foregroundOffsetY}%, ${motion.layerGapPx}px) scale(${motion.zoom})`,
                    WebkitMaskImage: depthMaskImage,
                    maskImage: depthMaskImage,
                    filter: `saturate(1.04) blur(${manual.blurPx * 0.12}px)`,
                  }}
                >
                  <img src={sourceUrl} alt={`${sample.title} foreground proxy`} />
                </div>
              ) : null}
            </>
          ) : null}

          {manual.previewMode === "selection" ? (
            <div className="selection-overlay">
              <img src={proxyMaps.overlayUrl} alt={`${sample.title} isolated depth preview`} />
            </div>
          ) : null}
          {hintStrokes.length > 0 && showSelectionOverlays ? (
            <div className="manual-hint-plane">
              <img src={proxyMaps.hintOverlayUrl} alt={`${sample.title} manual hint overlay`} />
            </div>
          ) : null}
          {groupBoxes.length > 0 && showSelectionOverlays ? (
            <div className="group-box-plane">
              <img src={proxyMaps.groupOverlayUrl} alt={`${sample.title} group overlay`} />
            </div>
          ) : null}
          {matteSettings.visible && matteSeeds.length > 0 && showSelectionOverlays ? (
            <div className="matte-plane">
              <img src={proxyMaps.matteOverlayUrl} alt={`${sample.title} matte overlay`} />
              {matteSeeds.map((seed) => (
                <div key={seed.id} className={`matte-seed-marker ${seed.mode}`} style={{ left: `${seed.x * 100}%`, top: `${seed.y * 100}%` }} />
              ))}
            </div>
          ) : null}
          {aiAssistVisible && aiAssistSuggestion && showSelectionOverlays ? (
            <div className="ai-suggestion-plane">
              {aiAssistSuggestion.accepted_foreground_groups.map((box, index) => (
                <div key={`ai-fg-${index}`} className="ai-suggestion-box foreground" style={{ left: `${box.x * 100}%`, top: `${box.y * 100}%`, width: `${box.width * 100}%`, height: `${box.height * 100}%` }}>
                  <span>{box.label}</span>
                </div>
              ))}
              {aiAssistSuggestion.accepted_midground_groups.map((box, index) => (
                <div key={`ai-mid-${index}`} className="ai-suggestion-box midground" style={{ left: `${box.x * 100}%`, top: `${box.y * 100}%`, width: `${box.width * 100}%`, height: `${box.height * 100}%` }}>
                  <span>{box.label}</span>
                </div>
              ))}
            </div>
          ) : null}
          {debugOpen ? (
            <div className="plate-stack-plane">
              {plateStack.filter((plate) => plate.visible).map((plate) => (
                <div
                  key={plate.id}
                  className={`plate-stack-box role-${plate.role}`}
                  style={{
                    left: `${plate.x * 100}%`,
                    top: `${plate.y * 100}%`,
                    width: `${plate.width * 100}%`,
                    height: `${plate.height * 100}%`,
                  }}
                >
                  <span>{plate.label}</span>
                </div>
              ))}
            </div>
          ) : null}
          {groupDraftBox ? (
            <div
              className={`group-draft-box ${groupMode}`}
              style={{
                left: `${groupDraftBox.x * 100}%`,
                top: `${groupDraftBox.y * 100}%`,
                width: `${groupDraftBox.width * 100}%`,
                height: `${groupDraftBox.height * 100}%`,
              }}
            />
          ) : null}
          <div className="focus-frame" style={foregroundFrame} />
          <div className="stage-badges">
            <span className="chip">{manual.renderMode}</span>
            <span className="chip">{manual.previewMode} preview</span>
            <span className="chip">{proxyMaps.usingRealDepth ? "real depth" : "proxy depth"}</span>
            <span className="chip">mask {formatPct(proxyMaps.selectionCoverage * 100)}</span>
            {debugOpen ? (
              <>
                <span className="chip">tool {stageTool}</span>
                {stageTool === "brush" ? <span className="chip">brush {brushMode}</span> : stageTool === "group" ? <span className="chip">group {groupMode}</span> : <span className="chip">matte {matteSettings.view}</span>}
                {groupBoxes.length > 0 ? <span className="chip">groups {groupBoxes.length}</span> : null}
                {matteSeeds.length > 0 ? <span className="chip">matte seeds {matteSeeds.length}</span> : null}
                {aiAssistVisible && aiAssistSuggestion ? <span className="chip">ai assist overlay</span> : null}
                <span className="chip">compare {aiCompareMode}</span>
                {guidedHintsVisible ? <span className="chip">guided hints visible</span> : null}
              </>
            ) : null}
          </div>
          <div className="stage-footer">
            <span>{sample.width} × {sample.height}</span>
            <span>motion {formatPct(snapshot.travelXPct)} / {formatPct(snapshot.travelYPct)}</span>
            <span>target {manual.targetDepth.toFixed(2)} ± {(manual.range / 2).toFixed(2)}</span>
          </div>
        </div>

        <section className="workflow-dock">
          <article className="panel panel-compact workflow-card">
            <div className="panel-header">
              <div className="panel-title-wrap">
                <Icon name="depth" />
                <div>
                  <h2>Depth</h2>
                  <div className="panel-subtitle">B/W map remap and cleanup</div>
                </div>
              </div>
            </div>
            <div className="workflow-card-grid">
              <RangeControl
                label="near limit"
                value={manual.nearLimit}
                min={0.4}
                max={0.95}
                step={0.01}
                onChange={(value) =>
                  setManual((prev) => ({
                    ...prev,
                    nearLimit: clamp(value, prev.farLimit + 0.05, 0.95),
                  }))
                }
              />
              <RangeControl
                label="far limit"
                value={manual.farLimit}
                min={0}
                max={0.6}
                step={0.01}
                onChange={(value) =>
                  setManual((prev) => ({
                    ...prev,
                    farLimit: clamp(value, 0, prev.nearLimit - 0.05),
                  }))
                }
              />
              <RangeControl
                label="gamma"
                value={manual.gamma}
                min={0.4}
                max={2.2}
                step={0.01}
                onChange={(value) => setManual((prev) => ({ ...prev, gamma: value }))}
              />
              <RangeControl
                label="softness"
                value={manual.softness}
                min={0.02}
                max={0.28}
                step={0.01}
                onChange={(value) => setManual((prev) => ({ ...prev, softness: value }))}
              />
              <RangeControl
                label="expand / shrink"
                value={manual.expandShrink}
                min={-0.18}
                max={0.18}
                step={0.01}
                onChange={(value) => setManual((prev) => ({ ...prev, expandShrink: value }))}
              />
              <RangeControl
                label="blur"
                value={manual.blurPx}
                min={0}
                max={4}
                step={0.1}
                onChange={(value) => setManual((prev) => ({ ...prev, blurPx: value }))}
                suffix="px"
              />
            </div>
            <div className="mini-stat-grid">
              <MiniStat label="depth src" value={proxyMaps.usingRealDepth ? "real" : "proxy"} />
              <MiniStat label="near mean" value={proxyMaps.nearMean.toFixed(3)} />
            </div>
          </article>

          <article className="panel panel-compact workflow-card">
            <div className="panel-header">
              <div className="panel-title-wrap">
                <Icon name="isolate" />
                <div>
                  <h2>Isolate</h2>
                  <div className="panel-subtitle">Foreground band from depth</div>
                </div>
              </div>
            </div>
            <div className="workflow-card-grid">
              <RangeControl
                label="target depth"
                value={manual.targetDepth}
                min={0}
                max={1}
                step={0.01}
                onChange={(value) => setManual((prev) => ({ ...prev, targetDepth: value }))}
              />
              <RangeControl
                label="range"
                value={manual.range}
                min={0.08}
                max={0.6}
                step={0.01}
                onChange={(value) => setManual((prev) => ({ ...prev, range: value }))}
              />
              <RangeControl
                label="foreground bias"
                value={manual.foregroundBias}
                min={0}
                max={0.5}
                step={0.01}
                onChange={(value) => setManual((prev) => ({ ...prev, foregroundBias: value }))}
              />
              <RangeControl
                label="background bias"
                value={manual.backgroundBias}
                min={0}
                max={0.5}
                step={0.01}
                onChange={(value) => setManual((prev) => ({ ...prev, backgroundBias: value }))}
              />
              <RangeControl
                label="post-filter"
                value={manual.postFilter}
                min={0}
                max={0.45}
                step={0.01}
                onChange={(value) => setManual((prev) => ({ ...prev, postFilter: value }))}
              />
              <div className="mini-stat-grid mini-stat-grid-compact">
                <MiniStat label="mask cover" value={formatPct(proxyMaps.selectionCoverage * 100)} />
                <MiniStat label="midground" value={formatPct(proxyMaps.midgroundCoverage * 100)} />
              </div>
            </div>
          </article>

          <article className="panel panel-compact workflow-card">
            <div className="panel-header">
              <div className="panel-title-wrap">
                <Icon name="camera" />
                <div>
                  <h2>Camera</h2>
                  <div className="panel-subtitle">Motion, timing and render</div>
                </div>
              </div>
              <button className="ghost-button" type="button" onClick={applyRecommendedPreset}>
                safe preset
              </button>
            </div>
            <div className="workflow-card-grid">
              <RangeControl
                label="travel x"
                value={motion.travelXPct}
                min={0}
                max={10}
                step={0.1}
                onChange={(value) => setMotion((prev) => ({ ...prev, travelXPct: value }))}
                suffix="%"
              />
              <RangeControl
                label="travel y"
                value={motion.travelYPct}
                min={0}
                max={5}
                step={0.1}
                onChange={(value) => setMotion((prev) => ({ ...prev, travelYPct: value }))}
                suffix="%"
              />
              <RangeControl
                label="zoom"
                value={motion.zoom}
                min={1}
                max={1.1}
                step={0.001}
                onChange={(value) => setMotion((prev) => ({ ...prev, zoom: value }))}
              />
              <RangeControl
                label="phase"
                value={motion.phase}
                min={0}
                max={1}
                step={0.01}
                onChange={(value) => setMotion((prev) => ({ ...prev, phase: value }))}
              />
              <RangeControl
                label="overscan"
                value={motion.overscanPct}
                min={4}
                max={32}
                step={0.5}
                onChange={(value) => setMotion((prev) => ({ ...prev, overscanPct: value }))}
                suffix="%"
              />
              <div className="mini-stat-grid mini-stat-grid-compact">
                <MiniStat label="travel" value={`${formatPct(snapshot.travelXPct)} / ${formatPct(snapshot.travelYPct)}`} />
                <MiniStat label="render" value={renderPolicy} />
              </div>
              <div className="mini-stat-grid mini-stat-grid-compact">
                <MiniStat
                  label="safe x / y"
                  value={`${formatPct(plateLayout.cameraSafe.suggestion.travelXPct)} / ${formatPct(plateLayout.cameraSafe.suggestion.travelYPct)}`}
                />
                <MiniStat label="safe overscan" value={formatPct(plateLayout.cameraSafe.suggestion.overscanPct)} />
              </div>
              <div className="panel-copy">
                {plateLayout.cameraSafe.warning
                  ? `Camera-safe warning: ${plateLayout.cameraSafe.warning}.`
                  : "Camera-safe check: no warning."}
                {plateLayout.cameraSafe.suggestion.reason ? ` Suggested motion tweak: ${plateLayout.cameraSafe.suggestion.reason}.` : ""}
              </div>
            </div>
          </article>

          <article className="panel panel-compact workflow-card export-card">
            <div className="panel-header">
              <div className="panel-title-wrap">
                <Icon name="export" />
                <div>
                  <h2>Export</h2>
                  <div className="panel-subtitle">Final assets and preview outputs</div>
                </div>
              </div>
            </div>
            <div className="export-stack">
              {exportTargets.map((target) => (
                <div className="export-item" key={target.label}>
                  <strong>{target.label}</strong>
                  <span>{target.value}</span>
                </div>
              ))}
            </div>
            <div className="panel-copy">
              {exportLayout.cameraSafe.adjustment.applied
                ? `Export auto-adjusts motion to ${formatPct(exportLayout.cameraSafe.adjustment.effective.travelXPct)} / ${formatPct(exportLayout.cameraSafe.adjustment.effective.travelYPct)} with ${formatPct(exportLayout.cameraSafe.adjustment.effective.overscanPct)} overscan.`
                : "Export uses the current camera motion as-is."}
            </div>
          </article>
        </section>

        {debugOpen ? (
          <section className="bottom-panels">
            <article className="info-card">
              <div className="eyebrow">Manual Pro</div>
              <h3>What changed in this wave</h3>
              <p>
                The sandbox now has two intervention types: local depth brushes and region-level merge groups. The new group boxes are a proxy for `same layer / merge group`, so split subjects can be forced back into one plane.
              </p>
            </article>
            <article className="info-card">
              <div className="eyebrow">Next step</div>
              <h3>What comes after this</h3>
              <ul>
                <li>Turn plate decomposition into the main path for complex scenes.</li>
                <li>Give each plate its own local depth or depth priority.</li>
                <li>Introduce special clean plates like `no people` and `no trees`.</li>
                <li>Make camera layout plate-aware instead of just foreground/background.</li>
                <li>Keep portrait mode fast while multi-plate mode gets richer authoring.</li>
              </ul>
            </article>
            <article className="info-card">
              <div className="eyebrow">Plate Stack</div>
              <h3>Current sample decomposition</h3>
              <div className="mini-stat-grid">
                <MiniStat label="visible plates" value={`${visibleRenderablePlates.length}`} />
                <MiniStat label="z span" value={`${plateZSpan.toFixed(1)}`} />
                <MiniStat label="effective layers" value={`${layoutMotion.layerCount}`} />
                <MiniStat label="layout gap" value={`${layoutMotion.layerGapPx.toFixed(1)}px`} />
              </div>
              <ul className="plate-stack-list plate-stack-editor">
                {plateStack.map((plate, index) => (
                  <li key={plate.id}>
                    <strong>{plate.label}</strong>
                    <span>{plate.role}</span>
                    <span>z {plate.z}</span>
                    <span>{plate.visible ? "visible" : "hidden"}</span>
                    <div className="plate-stack-actions">
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => movePlate(plate.id, -1)}
                        disabled={index === 0}
                      >
                        up
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => movePlate(plate.id, 1)}
                        disabled={index === plateStack.length - 1}
                      >
                        down
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => nudgePlateZ(plate.id, 4)}
                      >
                        z+
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => nudgePlateZ(plate.id, -4)}
                      >
                        z-
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => setPlateVisibility(plate.id, !plate.visible)}
                      >
                        {plate.visible ? "hide" : "show"}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </article>
            <article className="info-card">
              <div className="eyebrow">Qwen Plate Plan</div>
              <h3>Automatic object-layer proposal</h3>
              {qwenPlatePlan ? (
                <>
                  <div className="mini-stat-grid">
                    <MiniStat label="model" value={qwenPlatePlan.model || "offline"} />
                    <MiniStat label="plates" value={`${qwenPlatePlan.recommended_plate_count || 0}`} />
                    <MiniStat label="confidence" value={`${Math.round((qwenPlatePlan.confidence || 0) * 100)}%`} />
                    <MiniStat label="special clean" value={`${qwenPlatePlan.special_clean_plates?.length || 0}`} />
                  </div>
                  <p>
                    {qwenPlatePlan.scene_summary || "No scene summary yet."}
                  </p>
                  <div className="action-row">
                    <button className="ghost-button" type="button" onClick={applyQwenPlatePlan}>
                      apply qwen plan
                    </button>
                    {qwenPlateGate ? (
                      <button className="ghost-button" type="button" onClick={applyQwenPlateGate}>
                        apply gated stack
                      </button>
                    ) : null}
                  </div>
                  {qwenPlateGate ? (
                    <>
                      <div className="mini-stat-grid">
                        <MiniStat label="gate" value={qwenPlateGate.decision} />
                        <MiniStat label="overlap" value={`${Math.round(qwenPlateGate.metrics.visible_overlap_ratio * 100)}%`} />
                        <MiniStat label="added clean" value={`${qwenPlateGate.added_special_clean_variants.length}`} />
                      </div>
                      <p>{qwenPlateGate.reasons[0] || "No gate rationale yet."}</p>
                    </>
                  ) : null}
                </>
              ) : (
                <p>No cached Qwen plate plan found for this sample.</p>
              )}
            </article>
          </section>
        ) : null}
      </main>

      {debugOpen ? (
        <aside className="debug-pane">
          <div className="panel-header">
            <h2>Debug Snapshot</h2>
            <button className="ghost-button" type="button" onClick={() => window.vetkaParallaxLab?.print()}>
              print snapshot
            </button>
          </div>
          <dl className="debug-list">
            <DebugRow label="sample" value={snapshot.sampleId} />
            <DebugRow label="preview mode" value={manual.previewMode} />
            <DebugRow label="render mode" value={manual.renderMode} />
            <DebugRow label="stage tool" value={stageTool} />
            <DebugRow label="brush" value={brushMode} />
            <DebugRow label="group mode" value={groupMode} />
            <DebugRow label="hint strokes" value={`${hintStrokes.length}`} />
            <DebugRow label="group boxes" value={`${groupBoxes.length}`} />
            <DebugRow label="plate count" value={`${plateStack.length}`} />
            <DebugRow label="visible plates" value={`${visibleRenderablePlates.length}`} />
            <DebugRow label="plate z span" value={`${plateZSpan.toFixed(1)}`} />
            <DebugRow label="effective layers" value={`${layoutMotion.layerCount}`} />
            <DebugRow label="layout gap" value={`${layoutMotion.layerGapPx.toFixed(1)}px`} />
            <DebugRow label="matte seeds" value={`${matteSeeds.length}`} />
            <DebugRow label="matte cover" value={formatPct(proxyMaps.matteCoverage * 100)} />
            <DebugRow label="guided hints" value={guidedHintsVisible ? "visible" : "hidden"} />
            <DebugRow label="ai assist" value={aiAssistVisible ? "visible" : "hidden"} />
            <DebugRow label="ai compare" value={aiCompareMode} />
            <DebugRow label="job state" value="localStorage sync" />
            <DebugRow label="selection cover" value={formatPct(proxyMaps.selectionCoverage * 100)} />
            <DebugRow label="midground cover" value={formatPct(proxyMaps.midgroundCoverage * 100)} />
            <DebugRow label="depth source" value={proxyMaps.usingRealDepth ? "real" : "proxy"} />
            <DebugRow label="fg group cover" value={formatPct(proxyMaps.foregroundGroupCoverage * 100)} />
            <DebugRow label="mid group cover" value={formatPct(proxyMaps.midgroundGroupCoverage * 100)} />
            <DebugRow label="near mean" value={proxyMaps.nearMean.toFixed(3)} />
            <DebugRow label="displayed box" value={`${snapshot.displayedWidth} × ${snapshot.displayedHeight}`} />
            <DebugRow label="stage coverage" value={`${snapshot.stageCoverageRatio}`} />
            <DebugRow label="foreground coverage" value={`${snapshot.foregroundCoverage}`} />
            <DebugRow label="travel x" value={formatPct(snapshot.travelXPct)} tone={snapshot.travelXPct <= snapshot.safeTravelXPct ? "good" : "bad"} />
            <DebugRow label="travel y" value={formatPct(snapshot.travelYPct)} tone={snapshot.travelYPct <= snapshot.safeTravelYPct ? "good" : "bad"} />
            <DebugRow label="recommended overscan" value={formatPct(snapshot.recommendedOverscanPct)} tone={snapshot.overscanPct >= snapshot.recommendedOverscanPct ? "good" : "mid"} />
            <DebugRow label="min safe overscan" value={formatPct(snapshot.minSafeOverscanPct)} tone={snapshot.overscanPct >= snapshot.minSafeOverscanPct ? "good" : "bad"} />
            <DebugRow
              label="camera-safe travel"
              value={`${formatPct(plateLayout.cameraSafe.suggestion.travelXPct)} / ${formatPct(plateLayout.cameraSafe.suggestion.travelYPct)}`}
              tone={plateLayout.cameraSafe.ok ? "good" : "mid"}
            />
            <DebugRow
              label="camera-safe overscan"
              value={formatPct(plateLayout.cameraSafe.suggestion.overscanPct)}
              tone={snapshot.overscanPct >= plateLayout.cameraSafe.suggestion.overscanPct ? "good" : "mid"}
            />
            {plateLayout.cameraSafe.warning ? (
              <DebugRow label="camera-safe warning" value={plateLayout.cameraSafe.warning} tone="bad" />
            ) : null}
            {plateLayout.cameraSafe.suggestion.reason ? (
              <DebugRow label="camera-safe suggestion" value={plateLayout.cameraSafe.suggestion.reason} tone="mid" />
            ) : null}
            <DebugRow label="disocclusion risk" value={`${snapshot.disocclusionRisk}`} tone={snapshot.disocclusionRisk < 35 ? "good" : snapshot.disocclusionRisk < 60 ? "mid" : "bad"} />
            <DebugRow label="cardboard risk" value={`${snapshot.cardboardRisk}`} tone={snapshot.cardboardRisk < 35 ? "good" : snapshot.cardboardRisk < 60 ? "mid" : "bad"} />
            <DebugRow label="preview score" value={`${snapshot.previewScore}/100`} tone={snapshot.previewScore >= 72 ? "good" : snapshot.previewScore >= 50 ? "mid" : "bad"} />
            <DebugRow label="duration" value={`${snapshot.durationSec}s @ ${snapshot.fps} fps`} />
            <DebugRow label="total frames" value={`${snapshot.totalFrames}`} />
          </dl>
          <div className="debug-tip">
            Browser helpers: `debug.logs()`, `debug.inspect("overscan")`, `debug.watch("setMotion")`.
            Job state helpers: `window.vetkaParallaxLab?.exportJobState()` and `window.vetkaParallaxLab?.importJobState(payload)`.
            Layout helper: `window.vetkaParallaxLab?.exportPlateLayout()`.
          </div>
        </aside>
      ) : null}
    </div>
  );
}

function RangeControl(props: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix?: string;
  onChange: (value: number) => void;
}) {
  const { label, value, min, max, step, suffix, onChange } = props;
  return (
    <label className="range-control">
      <div className="range-header">
        <span>{label}</span>
        <strong>
          {value.toFixed(step >= 1 ? 0 : step >= 0.1 ? 1 : step >= 0.01 ? 2 : 3)}
          {suffix || ""}
        </strong>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

function Icon(props: { name: "import" | "preview" | "depth" | "isolate" | "camera" | "export" }) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.6,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  const paths = {
    import: (
      <>
        <path {...common} d="M4 6.5h16v11H4z" />
        <path {...common} d="M12 4v9" />
        <path {...common} d="M9.5 10.5 12 13l2.5-2.5" />
      </>
    ),
    preview: (
      <>
        <path {...common} d="M3.5 6.5h17v11h-17z" />
        <path {...common} d="m10 9 5 3-5 3z" />
      </>
    ),
    depth: (
      <>
        <rect {...common} x="4" y="4" width="16" height="16" rx="3" />
        <path {...common} d="M8 16c1.3-2.7 3-4 4.9-4S16.9 13.3 18 16" />
        <path {...common} d="M8 9h.01M16 9h.01" />
      </>
    ),
    isolate: (
      <>
        <path {...common} d="M4 12c2.5-4.5 5.2-6.7 8-6.7s5.5 2.2 8 6.7c-2.5 4.5-5.2 6.7-8 6.7S6.5 16.5 4 12Z" />
        <circle {...common} cx="12" cy="12" r="2.6" />
      </>
    ),
    camera: (
      <>
        <rect {...common} x="4" y="7" width="11" height="10" rx="2" />
        <path {...common} d="m15 10 5-2.5v9L15 14" />
        <path {...common} d="M8 5.5h3" />
      </>
    ),
    export: (
      <>
        <path {...common} d="M4 17.5h16" />
        <path {...common} d="M12 6v9" />
        <path {...common} d="m9.5 12.5 2.5 2.5 2.5-2.5" />
      </>
    ),
  };

  return (
    <span className="panel-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24">{paths[props.name]}</svg>
    </span>
  );
}

function InlineSegmentedControl(props: {
  value: string;
  options: { label: string; value: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <div className="inline-segmented">
      {props.options.map((option) => (
        <button
          key={option.value}
          className={`inline-segmented-button ${props.value === option.value ? "active" : ""}`}
          type="button"
          onClick={() => props.onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function SegmentedControl(props: {
  label: string;
  value: string;
  options: { label: string; value: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <div className="segmented-control">
      <div className="range-header">
        <span>{props.label}</span>
        <strong>{props.value}</strong>
      </div>
      <div className="segmented-row">
        {props.options.map((option) => (
          <button
            key={option.value}
            className={`segmented-button ${option.value === props.value ? "active" : ""}`}
            type="button"
            onClick={() => props.onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function ToggleButton(props: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button className={`toggle-button ${props.active ? "active" : ""}`} type="button" onClick={props.onClick}>
      {props.label}
    </button>
  );
}

function MiniStat(props: { label: string; value: string }) {
  return (
    <div className="mini-stat">
      <span>{props.label}</span>
      <strong>{props.value}</strong>
    </div>
  );
}

function MetricPill(props: { label: string; value: string; tone: "good" | "mid" | "bad" }) {
  return (
    <div className={`metric-pill ${props.tone}`}>
      <span>{props.label}</span>
      <strong>{props.value}</strong>
    </div>
  );
}

function DebugRow(props: { label: string; value: string; tone?: "good" | "mid" | "bad" }) {
  return (
    <>
      <dt>{props.label}</dt>
      <dd className={props.tone ? `tone-${props.tone}` : ""}>{props.value}</dd>
    </>
  );
}

export default App;
