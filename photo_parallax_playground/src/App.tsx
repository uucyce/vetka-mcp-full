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
type PlateAuthority = "system" | "draft" | "object";

type Plate = {
  id: string;
  label: string;
  role: PlateRole;
  source: PlateSource;
  authority?: PlateAuthority;
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
  authority?: PlateAuthority;
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
  authority?: PlateAuthority;
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
type SceneType = "portrait_close" | "single_subject" | "group_midshot" | "wide_scene" | "synthetic_ai_scene";
type AssistAction = "protect" | "silhouette" | "widen-depth" | "narrow-depth" | "reassign-role";

type AssistRecommendation = {
  title: string;
  detail: string;
  action: AssistAction;
  tone: "good" | "mid" | "bad";
};

type AssistPlan = {
  summary: string;
  focusAction: AssistAction;
  recommendations: AssistRecommendation[];
  roleSuggestion: PlateRole | null;
};

type GuidePlateSuggestion = {
  guideMode: Exclude<GroupMode, "erase-group">;
  plateId: string;
  plateLabel: string;
  overlapScore: number;
};

type MissingObjectCandidate = {
  id: string;
  label: string;
  suggestedRole: PlateRole;
  reason: string;
};

type ProvisionalObjectCandidate = MissingObjectCandidate & {
  x: number;
  y: number;
};

type DraftPlatePreset = {
  width: number;
  height: number;
  z: number;
  depthPriority: number;
};

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

function formatRoleLabel(role: PlateRole) {
  return role.replace(/-/g, " ");
}

function formatGroupModeLabel(mode: GroupMode) {
  switch (mode) {
    case "foreground-group":
      return "discover subject";
    case "midground-group":
      return "discover mid layer";
    case "erase-group":
      return "clear guide";
  }
}

function getBoxOverlapArea(
  first: { x: number; y: number; width: number; height: number },
  second: { x: number; y: number; width: number; height: number },
) {
  const left = Math.max(first.x, second.x);
  const top = Math.max(first.y, second.y);
  const right = Math.min(first.x + first.width, second.x + second.width);
  const bottom = Math.min(first.y + first.height, second.y + second.height);
  return Math.max(0, right - left) * Math.max(0, bottom - top);
}

function getMissingObjectCandidates(sampleId: string, plates: PlateLayoutLayer[]): MissingObjectCandidate[] {
  const labels = plates.map((plate) => plate.label.toLowerCase());
  const isRepresented = (keywords: string[]) => keywords.some((keyword) => labels.some((label) => label.includes(keyword)));

  if (sampleId === "hover-politsia") {
    const candidates: MissingObjectCandidate[] = [];
    if (!isRepresented(["cat", "kitten"])) {
      candidates.push({
        id: "hover-cat-right",
        label: "right-side cat",
        suggestedRole: "secondary-subject",
        reason: "Visible foreground detail at the curb, but no dedicated object plate currently tracks it.",
      });
    }
    if (!isRepresented(["parked car", "rust car", "right car"])) {
      candidates.push({
        id: "hover-rust-car-right",
        label: "right-side parked car",
        suggestedRole: "environment-mid",
        reason: "Background vehicle shape is visible behind the cat, but the current stack folds it into broader scene plates.",
      });
    }
    return candidates;
  }

  return [];
}

function getDraftPlateId(candidateId: string) {
  return `draft-${candidateId}`;
}

function getAuthoritativePlateId(candidateId: string) {
  return `object-${candidateId}`;
}

function parseCandidateIdFromPlateId(plateId: string) {
  if (plateId.startsWith("draft-")) return plateId.slice("draft-".length);
  if (plateId.startsWith("object-")) return plateId.slice("object-".length);
  return null;
}

function getPlateAuthority(plate: { id: string; authority?: PlateAuthority }) {
  if (plate.authority === "draft" || plate.authority === "object" || plate.authority === "system") {
    return plate.authority;
  }
  if (plate.id.startsWith("object-")) return "object";
  if (plate.id.startsWith("draft-")) return "draft";
  return "system";
}

function isDraftPlate(plate: { id: string }) {
  return getPlateAuthority(plate) === "draft";
}

function formatPlateAuthorityLabel(authority: PlateAuthority) {
  switch (authority) {
    case "draft":
      return "draft pick";
    case "object":
      return "object layer";
    case "system":
    default:
      return "base layer";
  }
}

function getDraftPlatePreset(candidate: MissingObjectCandidate): DraftPlatePreset {
  switch (candidate.id) {
    case "hover-cat-right":
      return {
        width: 0.14,
        height: 0.18,
        z: 12,
        depthPriority: 0.56,
      };
    case "hover-rust-car-right":
      return {
        width: 0.24,
        height: 0.18,
        z: -6,
        depthPriority: 0.34,
      };
    default:
      if (candidate.suggestedRole === "foreground-subject") {
        return { width: 0.24, height: 0.28, z: 18, depthPriority: 0.72 };
      }
      if (candidate.suggestedRole === "secondary-subject") {
        return { width: 0.16, height: 0.2, z: 10, depthPriority: 0.54 };
      }
      if (candidate.suggestedRole === "background-far") {
        return { width: 0.38, height: 0.28, z: -22, depthPriority: 0.18 };
      }
      return { width: 0.24, height: 0.18, z: -6, depthPriority: 0.34 };
  }
}

function buildDraftPlate(candidate: MissingObjectCandidate, point: HintPoint): Plate {
  const preset = getDraftPlatePreset(candidate);
  const width = preset.width;
  const height = preset.height;
  const x = clamp(point.x - width / 2, 0.01, 0.99 - width);
  const y = clamp(point.y - height / 2, 0.01, 0.99 - height);
  return buildPlate(
    getDraftPlateId(candidate.id),
    `draft: ${candidate.label}`,
    candidate.suggestedRole,
    "manual",
    { x, y, width, height },
    preset.z,
    preset.depthPriority,
    undefined,
    "draft",
  );
}

function refineDraftPlateBox(plate: Plate, mode: "tighten" | "widen"): Plate {
  const scale = mode === "tighten" ? 0.88 : 1.14;
  const centerX = plate.x + plate.width / 2;
  const centerY = plate.y + plate.height / 2;
  const nextWidth = clamp(plate.width * scale, 0.08, 0.42);
  const nextHeight = clamp(plate.height * scale, 0.08, 0.38);
  return {
    ...plate,
    x: clamp(centerX - nextWidth / 2, 0.01, 0.99 - nextWidth),
    y: clamp(centerY - nextHeight / 2, 0.01, 0.99 - nextHeight),
    width: nextWidth,
    height: nextHeight,
    source: "manual",
  };
}

function inferSceneType(sample: SampleMeta, routingMode: "portrait-base" | "multi-plate"): SceneType {
  const tags = sample.tags.join(" ").toLowerCase();
  const title = `${sample.title} ${sample.scenario}`.toLowerCase();
  if (tags.includes("ai") || title.includes("synthetic")) return "synthetic_ai_scene";
  if (tags.includes("portrait") || title.includes("close-up")) return "portrait_close";
  if (tags.includes("group")) return "group_midshot";
  if (tags.includes("wide") || tags.includes("street") || routingMode === "multi-plate") return "wide_scene";
  return "single_subject";
}

function buildAssistPlan(params: {
  sceneType: SceneType;
  plate: PlateLayoutLayer | null;
  transitionRisk: number | null;
  workflowRouting: PlateAwareLayoutContract["routing"];
  cameraSafe: PlateAwareLayoutContract["cameraSafe"];
}): AssistPlan {
  const { sceneType, plate, transitionRisk, workflowRouting, cameraSafe } = params;
  if (!plate) {
    return {
      summary: "Select a visible plate to get cleanup guidance.",
      focusAction: "protect",
      recommendations: [],
      roleSuggestion: null,
    };
  }

  const recommendations: AssistRecommendation[] = [];
  let roleSuggestion: PlateRole | null = null;

  if (plate.cleanVariant || plate.role === "special-clean" || plate.source === "special-clean") {
    recommendations.push({
      title: "Protect the cleanup island",
      detail: plate.targetPlate
        ? `This plate targets ${plate.targetPlate}, so lock the protected region before changing depth or role.`
        : "Keep this cleanup plate isolated before changing depth or role.",
      action: "protect",
      tone: "bad",
    });
  }

  if ((transitionRisk ?? 0) >= 45 || plate.risk.disocclusionRisk >= 45) {
    recommendations.push({
      title: "Refine the plate silhouette",
      detail:
        (transitionRisk ?? 0) >= 45
          ? `Neighbor transition risk is ${transitionRisk}, so edge cleanup is the next high-leverage move.`
          : `Disocclusion risk is ${plate.risk.disocclusionRisk}, so silhouette cleanup should come before deeper routing changes.`,
      action: "silhouette",
      tone: (transitionRisk ?? plate.risk.disocclusionRisk) >= 60 ? "bad" : "mid",
    });
  }

  if (cameraSafe.riskyPlateIds.includes(plate.id) || !plate.risk.cameraSafe) {
    const shouldWiden = plate.role === "foreground-subject" || plate.role === "secondary-subject";
    recommendations.push({
      title: shouldWiden ? "Widen the active depth band" : "Narrow the depth band",
      detail: shouldWiden
        ? "This plate is part of the camera-safe risk set, so give the subject a softer depth transition before export."
        : "This plate sits in the camera-safe risk set, so tighten the background band to reduce travel conflicts.",
      action: shouldWiden ? "widen-depth" : "narrow-depth",
      tone: "mid",
    });
  }

  if (sceneType === "portrait_close" && plate.role === "environment-mid" && plate.risk.plateCoverage <= 0.18) {
    roleSuggestion = "secondary-subject";
  } else if (
    (sceneType === "group_midshot" || sceneType === "wide_scene") &&
    plate.role === "foreground-subject" &&
    plate.risk.plateCoverage <= 0.12
  ) {
    roleSuggestion = "secondary-subject";
  } else if (
    sceneType === "single_subject" &&
    plate.role === "secondary-subject" &&
    plate.risk.plateCoverage >= 0.28
  ) {
    roleSuggestion = "foreground-subject";
  }

  if (roleSuggestion) {
    recommendations.push({
      title: "Re-check the plate role",
      detail: `Current scene class suggests ${formatRoleLabel(roleSuggestion)} for this coverage and routing profile.`,
      action: "reassign-role",
      tone: workflowRouting.mode === "multi-plate" ? "mid" : "good",
    });
  }

  if (sceneType === "synthetic_ai_scene" && !recommendations.some((item) => item.action === "protect")) {
    recommendations.push({
      title: "Anchor the synthetic edge first",
      detail: "AI-generated scenes tend to drift at object boundaries, so protect the region before depth tuning.",
      action: "protect",
      tone: "mid",
    });
  }

  if (recommendations.length === 0) {
    recommendations.push({
      title: "Routing looks stable",
      detail: `No extra cleanup trigger fired for this plate. Keep the current ${workflowRouting.mode} route and review camera-safe export.`,
      action: "narrow-depth",
      tone: "good",
    });
  }

  return {
    summary: `${plate.label} is currently treated as ${formatRoleLabel(plate.role)} in ${workflowRouting.mode} mode.`,
    focusAction: recommendations[0]?.action ?? "protect",
    recommendations: recommendations.slice(0, 3),
    roleSuggestion,
  };
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
  authority: PlateAuthority = "system",
): Plate {
  return {
    id,
    label,
    role,
    source,
    authority,
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
    const authority = getPlateAuthority(plate);
    return {
      id: plate.id || `plate_${String(index + 1).padStart(2, "0")}`,
      label: plate.label || `plate ${index + 1}`,
      role,
      source,
      authority,
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
  const plateCanvases = new Map<string, HTMLCanvasElement>();
  const plateContexts = new Map<string, CanvasRenderingContext2D>();
  const plateImages = new Map<string, ImageData>();
  const plateRgbaImages = new Map<string, ImageData>();
  const plateDepthImages = new Map<string, ImageData>();
  const plateCoverage = new Map<string, number>();

  for (const plate of renderablePlates) {
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
  for (const plate of renderablePlates) {
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
    ctx.setLineDash([10, 6]);
    ctx.fillStyle = box.mode === "foreground-group" ? "rgba(241, 88, 72, 0.1)" : "rgba(65, 152, 255, 0.1)";
    ctx.strokeStyle = box.mode === "foreground-group" ? "rgba(241, 88, 72, 0.74)" : "rgba(65, 152, 255, 0.72)";
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
        selection = Math.max(selection, 0.74);
        midground = Math.min(midground, 0.18);
        remapped = Math.max(remapped, clamp(manual.targetDepth + halfRange * 0.38, 0, 1));
      }
      if (forceMidground) {
        selection = Math.min(selection, 0.34);
        midground = Math.max(midground, 0.7);
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
  const initialSample = useMemo(() => findSample(initialQuery.sampleId), [initialQuery.sampleId]);
  const [sampleId, setSampleId] = useState(initialQuery.sampleId);
  const [debugOpen, setDebugOpen] = useState(initialQuery.debugOpen);
  const [cleanupOpen, setCleanupOpen] = useState(false);
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const [assistStatus, setAssistStatus] = useState<string | null>(null);
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
  const [aiCompareMode, setAiCompareMode] = useState<AiCompareMode>("manual");
  const [guidedHintsVisible, setGuidedHintsVisible] = useState(false);
  const [sceneType, setSceneType] = useState<SceneType>(() => inferSceneType(initialSample, "multi-plate"));
  const [foregroundOverscalePct, setForegroundOverscalePct] = useState(4);
  const [depthIsolateOpen, setDepthIsolateOpen] = useState(false);
  const [depthRefineOpen, setDepthRefineOpen] = useState(false);
  const [depthAdvancedOpen, setDepthAdvancedOpen] = useState(false);
  const [cameraTuningOpen, setCameraTuningOpen] = useState(false);
  const [activeEffectPanel, setActiveEffectPanel] = useState<"depth" | "extract" | "camera" | null>(null);
  const [exportPanelOpen, setExportPanelOpen] = useState(false);
  const [activeCleanupTool, setActiveCleanupTool] = useState<"focus" | "hints" | "stage" | "matte" | "brushes" | null>(null);
  const [inspectorQueuesOpen, setInspectorQueuesOpen] = useState(false);
  const [inspectorDetailsOpen, setInspectorDetailsOpen] = useState(false);
  const [assistDetailsOpen, setAssistDetailsOpen] = useState(false);
  const [supportPanelsOpen, setSupportPanelsOpen] = useState(false);
  const [selectedInspectorPlateId, setSelectedInspectorPlateId] = useState<string | null>(null);
  const [armedMissingCandidateId, setArmedMissingCandidateId] = useState<string | null>(null);
  const [provisionalObjectCandidates, setProvisionalObjectCandidates] = useState<ProvisionalObjectCandidate[]>([]);
  const [realDepth, setRealDepth] = useState<RealDepthRaster | null>(null);
  const [sourceRaster, setSourceRaster] = useState<SourceRaster | null>(null);
  const [stageSize, setStageSize] = useState({ width: 1180, height: 760 });
  const stageRef = useRef<HTMLDivElement | null>(null);
  const drawingStrokeIdRef = useRef<string | null>(null);

  const sample = useMemo(() => findSample(sampleId), [sampleId]);
  const stageEditingActive = cleanupOpen || armedMissingCandidateId !== null;
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
    setSceneType(inferSceneType(sample, workflowRouting.mode));
  }, [sample, workflowRouting.mode]);
  useEffect(() => {
    const nextVisiblePlate = plateStack.find((plate) => plate.visible)?.id ?? plateStack[0]?.id ?? null;
    if (!selectedInspectorPlateId || !plateStack.some((plate) => plate.id === selectedInspectorPlateId)) {
      setSelectedInspectorPlateId(nextVisiblePlate);
    }
  }, [plateStack, selectedInspectorPlateId]);
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
    if (!exportStatus) return;
    const timeoutId = window.setTimeout(() => setExportStatus(null), 2200);
    return () => window.clearTimeout(timeoutId);
  }, [exportStatus]);
  useEffect(() => {
    if (!assistStatus) return;
    const timeoutId = window.setTimeout(() => setAssistStatus(null), 2200);
    return () => window.clearTimeout(timeoutId);
  }, [assistStatus]);
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

  const placeMissingCandidate = (clientX: number, clientY: number) => {
    if (!armedMissingCandidateId) return false;
    const point = pointerToNormalized(clientX, clientY);
    if (!point) return false;
    const candidate = missingObjectCandidates.find((item) => item.id === armedMissingCandidateId);
    if (!candidate) return false;
    const draftPlate = buildDraftPlate(candidate, point);
    setProvisionalObjectCandidates((prev) => [
      ...prev.filter((item) => item.id !== candidate.id),
      { ...candidate, x: point.x, y: point.y },
    ]);
    setPlateStack((prev) => {
      const withoutCurrentDraft = prev.filter((plate) => plate.id !== draftPlate.id);
      return [...withoutCurrentDraft, draftPlate];
    });
    setSelectedInspectorPlateId(draftPlate.id);
    setArmedMissingCandidateId(null);
    setAssistStatus(`${candidate.label} placed as a draft plate.`);
    return true;
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
  const backgroundScale = Number((1 + motion.overscanPct / 220).toFixed(3));
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
  const inspectorPlates = plateLayout.plates.filter((plate) => plate.visible).sort((a, b) => a.order - b.order);
  const plateStateById = useMemo(
    () => new Map(plateStack.map((plate) => [plate.id, plate] as const)),
    [plateStack],
  );
  const missingObjectCandidates = useMemo(
    () => getMissingObjectCandidates(sampleId, inspectorPlates),
    [sampleId, inspectorPlates],
  );
  const draftInspectorPlates = useMemo(
    () => inspectorPlates.filter((plate) => isDraftPlate(plateStateById.get(plate.id) ?? plate)),
    [inspectorPlates, plateStateById],
  );
  const selectedInspectorPlate =
    inspectorPlates.find((plate) => plate.id === selectedInspectorPlateId) ?? inspectorPlates[0] ?? null;
  const selectedPlateState = selectedInspectorPlate ? plateStateById.get(selectedInspectorPlate.id) ?? null : null;
  const selectedPlateAuthority = selectedInspectorPlate
    ? getPlateAuthority(selectedPlateState ?? selectedInspectorPlate)
    : "system";
  const selectedDraftPlate = selectedInspectorPlate && selectedPlateAuthority === "draft" ? selectedInspectorPlate : null;
  const guidePlateSuggestion = useMemo<GuidePlateSuggestion | null>(() => {
    if (groupBoxes.length === 0 || inspectorPlates.length === 0) return null;

    let bestMatch: GuidePlateSuggestion | null = null;
    for (const guide of groupBoxes) {
      const guideArea = Math.max(0.0001, guide.width * guide.height);
      for (const plate of inspectorPlates) {
        const overlapArea = getBoxOverlapArea(guide, plate.box);
        if (overlapArea <= 0) continue;
        const overlapScore = overlapArea / guideArea;
        if (!bestMatch || overlapScore > bestMatch.overlapScore) {
          bestMatch = {
            guideMode: guide.mode,
            plateId: plate.id,
            plateLabel: plate.label,
            overlapScore: Number(overlapScore.toFixed(2)),
          };
        }
      }
    }
    return bestMatch;
  }, [groupBoxes, inspectorPlates]);
  const selectedInspectorTransition = selectedInspectorPlate
    ? plateLayout.transitions.find(
        (transition) =>
          transition.fromId === selectedInspectorPlate.id || transition.toId === selectedInspectorPlate.id,
      ) ?? null
    : null;
  const assistPlan = useMemo(
    () =>
      buildAssistPlan({
        sceneType,
        plate: selectedInspectorPlate,
        transitionRisk: selectedInspectorTransition?.transitionRisk ?? null,
        workflowRouting,
        cameraSafe: plateLayout.cameraSafe,
      }),
    [sceneType, selectedInspectorPlate, selectedInspectorTransition, workflowRouting, plateLayout.cameraSafe],
  );
  const downloadJson = (fileName: string, payload: unknown) => {
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  };

  const handleExportLayout = () => {
    downloadJson(`${sampleId}-plate-layout.json`, exportLayout);
    setExportStatus("Layout JSON downloaded.");
  };

  const handleExportAssets = () => {
    downloadJson(`${sampleId}-plate-assets.json`, buildPlateExportAssetsContract());
    setExportStatus("Plate assets contract downloaded.");
  };

  const handleExportJobState = async () => {
    const payload = JSON.stringify(buildJobState(), null, 2);
    try {
      await navigator.clipboard.writeText(payload);
      setExportStatus("Job state copied to clipboard.");
    } catch {
      downloadJson(`${sampleId}-job-state.json`, buildJobState());
      setExportStatus("Clipboard unavailable. Job state downloaded.");
    }
  };

  const updateSelectedPlateRole = (role: PlateRole) => {
    if (!selectedInspectorPlateId) return;
    setPlateStack((current) =>
      current.map((plate) =>
        plate.id === selectedInspectorPlateId
          ? {
              ...plate,
              role,
              source: "manual",
            }
          : plate,
      ),
    );
  };

  const refineSelectedDraftPlate = (mode: "tighten" | "widen") => {
    if (!selectedDraftPlate) return;
    let nextLabel = selectedDraftPlate.label;
    setPlateStack((current) =>
      current.map((plate) => {
        if (plate.id !== selectedDraftPlate.id) return plate;
        const nextPlate = refineDraftPlateBox(plate, mode);
        nextLabel = nextPlate.label;
        return nextPlate;
      }),
    );
    setAssistStatus(
      `${nextLabel.replace(/^draft:\s*/i, "")} ${mode === "tighten" ? "tightened" : "widened"} as a draft fit.`,
    );
  };

  const promoteSelectedDraftPlate = () => {
    if (!selectedDraftPlate) return;
    const nextId = getAuthoritativePlateId(parseCandidateIdFromPlateId(selectedDraftPlate.id) ?? selectedDraftPlate.id);
    const nextLabel = selectedDraftPlate.label.replace(/^draft:\s*/i, "");
    setPlateStack((current) =>
      current.map((plate) =>
        plate.id === selectedDraftPlate.id
          ? {
              ...plate,
              id: nextId,
              label: nextLabel,
              source: "manual",
              authority: "object",
            }
          : plate,
      ),
    );
    const candidateId = parseCandidateIdFromPlateId(selectedDraftPlate.id);
    if (candidateId) {
      setProvisionalObjectCandidates((prev) => prev.filter((candidate) => candidate.id !== candidateId));
    }
    setSelectedInspectorPlateId(nextId);
    setAssistStatus(`${nextLabel} promoted into an authoritative object layer.`);
  };

  const openProtectRegionAssist = () => {
    setCleanupOpen(true);
    setActiveCleanupTool("brushes");
    setStageTool("brush");
    setBrushMode("protect");
    setGuidedHintsVisible(true);
  };

  const openSilhouetteAssist = () => {
    setCleanupOpen(true);
    setActiveCleanupTool("matte");
    setStageTool("matte");
    setMatteSeedMode("protect");
    setMatteSettings((prev) => ({ ...prev, visible: true, view: "rgb" }));
  };

  const adjustDepthBand = (delta: number) => {
    setManual((prev) => ({
      ...prev,
      range: clamp(prev.range + delta, 0.08, 0.6),
    }));
  };

  const applyAssistRecommendation = () => {
    switch (assistPlan.focusAction) {
      case "protect":
        openProtectRegionAssist();
        setAssistStatus("Protect-region assist armed.");
        return;
      case "silhouette":
        openSilhouetteAssist();
        setAssistStatus("Silhouette refinement opened.");
        return;
      case "widen-depth":
        adjustDepthBand(0.04);
        setAssistStatus("Depth band widened for the selected plate.");
        return;
      case "narrow-depth":
        adjustDepthBand(-0.04);
        setAssistStatus("Depth band narrowed for the selected plate.");
        return;
      case "reassign-role":
        if (assistPlan.roleSuggestion && selectedInspectorPlate) {
          setSelectedInspectorPlateId(selectedInspectorPlate.id);
          updateSelectedPlateRole(assistPlan.roleSuggestion);
          setAssistStatus(`Plate role moved to ${formatRoleLabel(assistPlan.roleSuggestion)}.`);
          return;
        }
        setAssistStatus("No role reassignment suggested for this plate.");
        return;
    }
  };

  const focusGuideSuggestion = () => {
    if (!guidePlateSuggestion) return;
    setSelectedInspectorPlateId(guidePlateSuggestion.plateId);
    setAssistStatus(
      `${formatGroupModeLabel(guidePlateSuggestion.guideMode)} now focused on ${guidePlateSuggestion.plateLabel}.`,
    );
  };

  const focusStagePlate = (plateId: string) => {
    const plate = inspectorPlates.find((item) => item.id === plateId);
    setSelectedInspectorPlateId(plateId);
    if (plate) {
      setAssistStatus(`${plate.label.replace(/^draft:\s*/i, "")} selected on the stage.`);
    }
  };

  const focusGuideBox = (guide: GroupBox) => {
    let bestPlate: PlateLayoutLayer | null = null;
    let bestOverlap = 0;
    const guideArea = Math.max(0.0001, guide.width * guide.height);
    for (const plate of inspectorPlates) {
      const overlapArea = getBoxOverlapArea(guide, plate.box);
      if (overlapArea <= 0) continue;
      const overlapScore = overlapArea / guideArea;
      if (!bestPlate || overlapScore > bestOverlap) {
        bestPlate = plate;
        bestOverlap = overlapScore;
      }
    }
    if (!bestPlate) {
      setAssistStatus(`${formatGroupModeLabel(guide.mode)} has no routed plate under this guide yet.`);
      return;
    }
    setSelectedInspectorPlateId(bestPlate.id);
    setAssistStatus(
      `${formatGroupModeLabel(guide.mode)} focused on ${bestPlate.label} from the stage guide.`,
    );
  };

  const armMissingCandidate = (candidateId: string) => {
    setArmedMissingCandidateId(candidateId);
    setAssistStatus("Click the scene to place a provisional object candidate.");
  };

  const focusPlacedCandidate = (candidateId: string) => {
    const nextPlateId = [getAuthoritativePlateId(candidateId), getDraftPlateId(candidateId)].find((plateId) =>
      inspectorPlates.some((plate) => plate.id === plateId),
    );
    if (!nextPlateId) return;
    const plate = inspectorPlates.find((item) => item.id === nextPlateId);
    setSelectedInspectorPlateId(nextPlateId);
    if (plate) {
      const authority = getPlateAuthority(plateStateById.get(plate.id) ?? plate);
      setAssistStatus(
        authority === "object"
          ? `${plate.label.replace(/^draft:\s*/i, "")} selected as an authoritative object layer.`
          : `${plate.label.replace(/^draft:\s*/i, "")} selected as a draft layer.`,
      );
    }
  };

  const openPlateSilhouetteAssist = (plateId: string) => {
    const plate = inspectorPlates.find((item) => item.id === plateId);
    setSelectedInspectorPlateId(plateId);
    openSilhouetteAssist();
    setAssistStatus(
      plate
        ? `Silhouette cleanup opened for ${plate.label.replace(/^draft:\s*/i, "")}.`
        : "Silhouette cleanup opened for the selected layer.",
    );
  };

  const stageAspectRatio = sample.width / sample.height;
  const stageShellStyle = {
    width: `min(100%, calc(min(78vh, 920px) * ${stageAspectRatio}))`,
    aspectRatio: `${sample.width} / ${sample.height}`,
  } as const;
  const cleanupToolOptions = [
    { id: "focus", label: "focus proxy" },
    { id: "hints", label: "guided hints" },
    { id: "stage", label: "stage tools" },
    { id: "matte", label: "algorithmic matte" },
    { id: "brushes", label: "hint brushes" },
  ] as const;
  const activeCleanupToolLabel =
    cleanupToolOptions.find((tool) => tool.id === activeCleanupTool)?.label ?? null;
  const closeCleanupContext = () => {
    setActiveCleanupTool(null);
    setCleanupOpen(false);
  };

  const renderCleanupContextPanel = () => {
    if (!cleanupOpen || activeCleanupTool === null) return null;

    switch (activeCleanupTool) {
      case "focus":
        return (
          <section className="panel panel-compact cleanup-context-panel">
            <div className="panel-header cleanup-context-header">
              <div>
                <h2>Focus Proxy</h2>
                <div className="panel-subtitle">Rescue focus framing when depth fallback is still too loose</div>
              </div>
              <button className="ghost-button" type="button" onClick={closeCleanupContext}>
                done
              </button>
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
        );
      case "hints":
        return (
          <section className="panel panel-compact cleanup-context-panel">
            <div className="panel-header cleanup-context-header">
              <div>
                <h2>Guided Hints</h2>
                <div className="panel-subtitle">Show hint overlay only while rescue guidance is needed</div>
              </div>
              <div className="panel-header-actions">
                <button className="ghost-button" type="button" onClick={() => setGuidedHintsVisible((value) => !value)}>
                  {guidedHintsVisible ? "hide hints" : "show hints"}
                </button>
                <button className="ghost-button" type="button" onClick={closeCleanupContext}>
                  done
                </button>
              </div>
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
        );
      case "stage":
        return (
          <section className="panel panel-compact cleanup-context-panel">
            <div className="panel-header cleanup-context-header">
              <div>
                <h2>Stage Tools</h2>
                <div className="panel-subtitle">Pick the stage interaction you want to use on the image</div>
              </div>
              <button className="ghost-button" type="button" onClick={closeCleanupContext}>
                done
              </button>
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
        );
      case "matte":
        return (
          <section className="panel panel-compact cleanup-context-panel">
            <div className="panel-header cleanup-context-header">
              <div>
                <h2>Algorithmic Matte</h2>
                <div className="panel-subtitle">Seed add/subtract/protect regions directly on the stage</div>
              </div>
              <div className="panel-header-actions">
                <button className="ghost-button" type="button" onClick={() => setMatteSeeds([])}>
                  clear
                </button>
                <button className="ghost-button" type="button" onClick={closeCleanupContext}>
                  done
                </button>
              </div>
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
        );
      case "brushes":
        return (
          <section className="panel panel-compact cleanup-context-panel">
            <div className="panel-header cleanup-context-header">
              <div>
                <h2>Hint Brushes</h2>
                <div className="panel-subtitle">Paint closer, farther, protect, or erase directly on the stage</div>
              </div>
              <div className="panel-header-actions">
                <button className="ghost-button" type="button" onClick={() => setHintStrokes([])}>
                  clear
                </button>
                <button className="ghost-button" type="button" onClick={closeCleanupContext}>
                  done
                </button>
              </div>
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
        );
      default:
        return null;
    }
  };
  const cleanupContextPanel = renderCleanupContextPanel();

  return (
    <div className="parallax-app">
      <aside className="left-rail">
        <div className="brand-card">
          <div className="brand-topline">
            <div>
              <div className="eyebrow">VETKA / MCC / PARALLAX</div>
              <h1>Photo Parallax Lab</h1>
              <div className="brand-caption">Parallax workspace</div>
            </div>
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
          <div className="sample-list">
            {SAMPLE_LIBRARY.map((entry) => (
              <button
                key={entry.id}
                className={`sample-row ${entry.id === sample.id ? "active" : ""}`}
                type="button"
                onClick={() => loadSample(entry.id)}
              >
                <img src={`/samples/${entry.fileName}`} alt={entry.title} />
                <span className="sample-row-copy">
                  <strong>{entry.title}</strong>
                  <span>{entry.tags.slice(0, 2).join(" / ")}</span>
                </span>
                <span className="sample-row-meta">{entry.width} × {entry.height}</span>
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

        <section className="panel panel-compact accordion-section support-shell rail-support-shell">
          <button className="accordion-toggle" type="button" onClick={() => setSupportPanelsOpen((value) => !value)}>
            <div className="panel-title-wrap">
              <Icon name="preview" />
              <div>
                <h2>Objects and Route Notes</h2>
                <div className="panel-subtitle">Open only if you need object checks or route detail</div>
              </div>
            </div>
            <div className="accordion-actions">
              <span className="accordion-chevron">{supportPanelsOpen ? "−" : "+"}</span>
            </div>
          </button>
          <div className="panel-copy">
            Contains object review and route notes. It stays folded so the first screen can stay focused on preview, depth, camera, and export.
          </div>
          <div className="utility-summary support-summary-copy">
            <span>{plateLayout.metrics.visiblePlateCount} visible objects</span>
            <span>
              {plateLayout.cameraSafe.riskyPlateIds.length > 0
                ? `${plateLayout.cameraSafe.riskyPlateIds.length} object risks still need review.`
                : "No object risk is currently flagged."}
              {missingObjectCandidates.length > 0 ? ` ${missingObjectCandidates.length} possible missing objects are waiting in the watchlist.` : ""}
            </span>
          </div>
          {supportPanelsOpen ? (
            <section className="inspector-shell">
              <article className="panel panel-compact inspector-card">
                <div className="panel-header">
                  <div className="panel-title-wrap">
                    <Icon name="preview" />
                    <div>
                      <h2>Objects</h2>
                      <div className="panel-subtitle">click a frame on the image to inspect and route it</div>
                    </div>
                  </div>
                  <div className="panel-header-actions">
                    <button className="ghost-button" type="button" onClick={() => setInspectorDetailsOpen((value) => !value)}>
                      {inspectorDetailsOpen ? "hide details" : "show details"}
                    </button>
                    <button className="ghost-button" type="button" onClick={() => setInspectorQueuesOpen((value) => !value)}>
                      {inspectorQueuesOpen ? "hide watchlist" : "open watchlist"}
                    </button>
                  </div>
                </div>
                <div className="assist-focus-strip">
                  <span className="chip">visible {plateLayout.metrics.visiblePlateCount}</span>
                  <span className="chip">risk {plateLayout.cameraSafe.riskyPlateIds.length}</span>
                  {draftInspectorPlates.length > 0 ? <span className="chip">drafts {draftInspectorPlates.length}</span> : null}
                  {missingObjectCandidates.length > 0 ? <span className="chip">watchlist {missingObjectCandidates.length}</span> : null}
                </div>
                {selectedInspectorPlate ? (
                  <div className="selected-plate-summary">
                    <strong>{selectedInspectorPlate.label}</strong>
                    <span>{formatRoleLabel(selectedInspectorPlate.role)}</span>
                    <span className={`plate-authority-tag ${selectedPlateAuthority}`}>{formatPlateAuthorityLabel(selectedPlateAuthority)}</span>
                    <span>{selectedInspectorPlate.source}</span>
                  </div>
                ) : null}
                <div className="plate-chip-list">
                  {inspectorPlates.map((plate) => {
                    const plateAuthority = getPlateAuthority(plateStateById.get(plate.id) ?? plate);
                    return (
                    <button
                      key={plate.id}
                      className={`plate-chip-button ${selectedInspectorPlate?.id === plate.id ? "active" : ""} ${plateAuthority === "draft" ? "draft" : ""} ${plateAuthority === "object" ? "authoritative" : ""}`}
                      type="button"
                      onClick={() => setSelectedInspectorPlateId(plate.id)}
                    >
                      <strong>{plate.label}</strong>
                      <span>{formatRoleLabel(plate.role)}</span>
                      <span>{formatPlateAuthorityLabel(plateAuthority)}</span>
                      <span>risk {plate.risk.disocclusionRisk}</span>
                    </button>
                    );
                  })}
                </div>
                {selectedInspectorPlate ? (
                  <>
                    <div className="mini-stat-grid mini-stat-grid-compact">
                      <MiniStat label="coverage" value={formatPct(selectedInspectorPlate.risk.plateCoverage * 100)} />
                      <MiniStat label="safe overscan" value={formatPct(selectedInspectorPlate.risk.minSafeOverscanPct)} />
                    </div>
                    <SegmentedControl
                      label="layer role"
                      value={selectedInspectorPlate.role}
                      valueLabel={formatRoleLabel(selectedInspectorPlate.role)}
                      options={[
                        { label: "fg", value: "foreground-subject" },
                        { label: "secondary", value: "secondary-subject" },
                        { label: "mid", value: "environment-mid" },
                        { label: "back", value: "background-far" },
                        { label: "clean", value: "special-clean" },
                      ]}
                      onChange={(value) => updateSelectedPlateRole(value as PlateRole)}
                    />
                    <div className="panel-copy compact-note">
                      Click a frame on the image to pick an object. The stage box is only a handle; the actual cut follows the silhouette and depth mask.
                    </div>
                    {inspectorDetailsOpen ? (
                      <>
                        <div className="inspector-detail-grid">
                          <MiniStat label="parallax" value={selectedInspectorPlate.parallaxStrength.toFixed(3)} />
                          <MiniStat label="damping" value={selectedInspectorPlate.motionDamping.toFixed(3)} />
                          <MiniStat label="source" value={selectedInspectorPlate.source} />
                          <MiniStat label="transition" value={selectedInspectorTransition ? `${selectedInspectorTransition.transitionRisk}` : "none"} />
                        </div>
                        <div className="panel-copy">
                          {selectedInspectorPlate.cleanVariant
                            ? `Cleanup variant: ${selectedInspectorPlate.cleanVariant}. `
                            : "Cleanup variant: none. "}
                          {selectedInspectorPlate.targetPlate ? `Targets ${selectedInspectorPlate.targetPlate}. ` : ""}
                          {guidePlateSuggestion
                            ? `Guide focus currently points at ${guidePlateSuggestion.plateLabel}.`
                            : "No active layer guide match yet."}
                        </div>
                      </>
                    ) : null}
                    {selectedDraftPlate ? (
                      <div className="draft-refine-box">
                        <strong>Draft plate refine</strong>
                        <span>
                          This stage pick is still a draft. Tighten if the box is too loose, widen if the object is clipped, then promote it into a real object layer.
                        </span>
                        <div className="action-row">
                          <button className="ghost-button" type="button" onClick={() => refineSelectedDraftPlate("tighten")}>
                            tighten fit
                          </button>
                          <button className="ghost-button" type="button" onClick={() => refineSelectedDraftPlate("widen")}>
                            widen fit
                          </button>
                          <button className="ghost-button active" type="button" onClick={promoteSelectedDraftPlate}>
                            promote to layer
                          </button>
                        </div>
                      </div>
                    ) : null}
                  </>
                ) : null}
                {inspectorQueuesOpen ? (
                  <div className="inspector-queues">
                    {draftInspectorPlates.length > 0 ? (
                      <div className="queue-block">
                        <strong>Draft plates</strong>
                        <span>{draftInspectorPlates.map((plate) => plate.label.replace(/^draft:\s*/i, "")).join(", ")}</span>
                      </div>
                    ) : null}
                    {missingObjectCandidates.length > 0 ? (
                      <div className="candidate-object-list">
                        {missingObjectCandidates.map((candidate) => (
                          <div className="candidate-object-card" key={candidate.id}>
                            <strong>{candidate.label}</strong>
                            <span>{formatRoleLabel(candidate.suggestedRole)}</span>
                            <span>{candidate.reason}</span>
                            <div className="action-row">
                              <button className={`ghost-button ${armedMissingCandidateId === candidate.id ? "active" : ""}`} type="button" onClick={() => armMissingCandidate(candidate.id)}>
                                {armedMissingCandidateId === candidate.id ? "click scene now" : "pick on stage"}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </article>

              <article className="panel panel-compact inspector-card">
                <div className="panel-header">
                  <div className="panel-title-wrap">
                    <Icon name="isolate" />
                    <div>
                      <h2>Scene Plan</h2>
                      <div className="panel-subtitle">routing and quick fixes</div>
                    </div>
                  </div>
                  <button className="ghost-button" type="button" onClick={() => setAssistDetailsOpen((value) => !value)}>
                    {assistDetailsOpen ? "hide details" : "more detail"}
                  </button>
                </div>
                <SegmentedControl
                  label="scene type"
                  value={sceneType}
                  options={[
                    { label: "portrait", value: "portrait_close" },
                    { label: "single", value: "single_subject" },
                    { label: "group", value: "group_midshot" },
                    { label: "wide", value: "wide_scene" },
                    { label: "synthetic", value: "synthetic_ai_scene" },
                  ]}
                  onChange={(value) => setSceneType(value as SceneType)}
                />
                <div className="scene-plan-list">
                  <div className="scene-plan-item">
                    <strong>Route</strong>
                    <span>{workflowRouting.mode}. {workflowRouting.reasons[0] || "No route note."}</span>
                  </div>
                  <div className="scene-plan-item">
                    <strong>Risk</strong>
                    <span>
                      {plateLayout.cameraSafe.ok
                        ? "Camera-safe check is clear."
                        : plateLayout.cameraSafe.warning || "Camera-safe tuning still needed."}
                    </span>
                  </div>
                  <div className="scene-plan-item">
                    <strong>Next</strong>
                    <span>{assistPlan.recommendations[0]?.detail || assistPlan.summary}</span>
                  </div>
                </div>
                <div className="assist-focus-strip">
                  <span className="chip">clean plates {workflowRouting.specialCleanCount}</span>
                  <span className="chip">edge risk {plateLayout.cameraSafe.worstTransitionRisk}</span>
                  <span className="chip">{guidePlateSuggestion ? `guide ${guidePlateSuggestion.plateLabel}` : "guide idle"}</span>
                </div>
                <div className="action-row">
                  <button className="ghost-button active" type="button" onClick={applyAssistRecommendation}>
                    apply next action
                  </button>
                  {guidePlateSuggestion ? (
                    <button className="ghost-button" type="button" onClick={focusGuideSuggestion}>
                      focus guide match
                    </button>
                  ) : null}
                </div>
                {assistStatus ? <div className="assist-status">{assistStatus}</div> : null}
                {assistDetailsOpen ? (
                  <div className="assist-secondary">
                    <div className="assist-recommendation-list">
                      {assistPlan.recommendations.map((recommendation) => (
                        <div className={`assist-recommendation tone-${recommendation.tone}`} key={recommendation.title}>
                          <strong>{recommendation.title}</strong>
                          <span>{recommendation.detail}</span>
                        </div>
                      ))}
                    </div>
                    <div className="action-row">
                      <button
                        className={`ghost-button ${assistPlan.focusAction === "protect" ? "active" : ""}`}
                        type="button"
                        onClick={openProtectRegionAssist}
                      >
                        protect region
                      </button>
                      <button
                        className={`ghost-button ${assistPlan.focusAction === "silhouette" ? "active" : ""}`}
                        type="button"
                        onClick={openSilhouetteAssist}
                      >
                        refine silhouette
                      </button>
                      <button
                        className={`ghost-button ${assistPlan.focusAction === "widen-depth" ? "active" : ""}`}
                        type="button"
                        onClick={() => adjustDepthBand(0.04)}
                      >
                        widen depth band
                      </button>
                      <button
                        className={`ghost-button ${assistPlan.focusAction === "narrow-depth" ? "active" : ""}`}
                        type="button"
                        onClick={() => adjustDepthBand(-0.04)}
                      >
                        narrow depth band
                      </button>
                    </div>
                    {missingObjectCandidates.length > 0 ? (
                      <div className="panel-copy">
                        Missing detail watchlist: {missingObjectCandidates.map((candidate) => candidate.label).join(", ")}.
                      </div>
                    ) : null}
                    {draftInspectorPlates.length > 0 ? (
                      <div className="panel-copy">
                        Draft plates: {draftInspectorPlates.map((plate) => plate.label.replace(/^draft:\s*/i, "")).join(", ")}.
                      </div>
                    ) : null}
                    <div className="panel-copy">
                      {guidePlateSuggestion
                        ? `Layer guide suggests focusing ${guidePlateSuggestion.plateLabel} before the next cleanup move.`
                        : "Layer guides can promote a candidate plate into focus before you apply cleanup or role changes."}
                    </div>
                    <RangeControl
                      label="hero object scale"
                      value={foregroundOverscalePct}
                      min={0}
                      max={12}
                      step={0.5}
                      onChange={setForegroundOverscalePct}
                      suffix="%"
                    />
                  </div>
                ) : null}
                {assistPlan.roleSuggestion && selectedInspectorPlate && assistPlan.roleSuggestion !== selectedInspectorPlate.role ? (
                  <div className="panel-copy">
                    Suggested role for this plate: {formatRoleLabel(assistPlan.roleSuggestion)}.
                  </div>
                ) : null}
              </article>
            </section>
          ) : null}
        </section>

        <section className="panel panel-compact accordion-section">
          <button className="accordion-toggle" type="button" onClick={() => setCleanupOpen((value) => !value)}>
            <div className="panel-title-wrap">
              <Icon name="isolate" />
              <div>
                <h2>After Extract: Manual Cleanup</h2>
                <div className="panel-subtitle">Optional rescue tools, not part of Import</div>
              </div>
            </div>
            <div className="accordion-actions">
              <span className="accordion-chevron">{cleanupOpen ? "−" : "+"}</span>
            </div>
          </button>
          <div className="panel-copy">
            This block belongs after `Extract`. Keep it closed for normal shots. Open it only when masking, routing, or cleanup starts failing.
          </div>
          <div className="utility-summary">
            <span>Stage: post-extract rescue</span>
            <span>
              {cleanupOpen
                ? activeCleanupToolLabel
                  ? `Active tool: ${activeCleanupToolLabel}. Controls moved next to the viewer.`
                  : "Pick one rescue tool. Controls appear next to the viewer, not as a left-rail sheet."
                : "Closed by default, so no settings are shown until you open it."}
            </span>
          </div>
          {cleanupOpen ? (
            <div className="accordion-body">
              <div className="cleanup-tool-picker">
                {cleanupToolOptions.map((tool) => (
                  <button
                    key={tool.id}
                    className={`ghost-button cleanup-tool-button ${activeCleanupTool === tool.id ? "active" : ""}`}
                    type="button"
                    onClick={() =>
                      setActiveCleanupTool((value) => (value === tool.id ? null : (tool.id as "focus" | "hints" | "stage" | "matte" | "brushes")))
                    }
                  >
                    {tool.label}
                  </button>
                ))}
              </div>
              <div className="cleanup-tools-footer">
                <div className="panel-copy">
                  {activeCleanupToolLabel
                    ? `Only ${activeCleanupToolLabel} stays open. All rescue controls live next to the viewer while the tool is active.`
                    : "Select a rescue tool only when cleanup actually starts failing."}
                </div>
                <div className="panel-header-actions">
                  {activeCleanupTool !== null ? (
                    <button className="ghost-button" type="button" onClick={closeCleanupContext}>
                      close active tool
                    </button>
                  ) : null}
                  <button className="ghost-button" type="button" onClick={() => setDebugOpen((value) => !value)}>
                    {debugOpen ? "hide debug tools" : "open debug tools"}
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </section>

      </aside>

      <main className="main-pane">
        <div className="stage-header">
          <div>
            <div className="eyebrow">Preview</div>
            <h2>{sample.title}</h2>
          </div>
        </div>

        <section className="main-workspace">
        <div className="stage-monitor-row">
        <div className="stage-workspace" style={{ width: stageShellStyle.width }}>
        <div className="stage-shell" ref={stageRef} style={stageShellStyle}>
          <div className="stage-grid" />
          <div
            className={`hint-editor-surface ${stageEditingActive ? "is-active" : ""} ${stageTool === "group" ? "group-mode" : stageTool === "matte" ? "matte-mode" : "brush-mode"}`}
            onPointerDown={(event) => {
              if (!stageEditingActive) return;
              event.preventDefault();
              if (armedMissingCandidateId) {
                placeMissingCandidate(event.clientX, event.clientY);
                return;
              }
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
              if (!stageEditingActive) return;
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
              if (!stageEditingActive) return;
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
              if (!stageEditingActive) return;
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
              <div className="depth-preview-meta">
                <span>Depth map</span>
                <strong>white = near · black = far</strong>
                <span>{proxyMaps.usingRealDepth ? "real depth source" : "proxy depth source"}</span>
              </div>
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
                  transform: `translate3d(${backgroundOffsetX}%, ${backgroundOffsetY}%, ${-layoutMotion.layerGapPx}px) scale(${backgroundScale})`,
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
                  const overscaleBoost =
                    plate.role === "foreground-subject" ? foregroundOverscalePct / 100 : 0;
                  const scale = 1 + (motion.zoom - 1) * plate.parallaxStrength + overscaleBoost;
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
          {groupBoxes.length > 0 ? (
            <div className="group-box-plane">
              <img src={proxyMaps.groupOverlayUrl} alt={`${sample.title} group overlay`} />
              {groupBoxes.map((box) => (
                <button
                  key={box.id}
                  className={`group-guide-box ${box.mode}`}
                  type="button"
                  style={{
                    left: `${box.x * 100}%`,
                    top: `${box.y * 100}%`,
                    width: `${box.width * 100}%`,
                    height: `${box.height * 100}%`,
                  }}
                  onClick={() => focusGuideBox(box)}
                >
                  <span>{formatGroupModeLabel(box.mode)}</span>
                </button>
              ))}
            </div>
          ) : null}
          {manual.previewMode !== "depth" && inspectorPlates.length > 0 ? (
            <div className="stage-object-plane">
              {inspectorPlates.map((plate) => {
                const isSelected = selectedInspectorPlate?.id === plate.id;
                const plateAuthority = getPlateAuthority(plateStateById.get(plate.id) ?? plate);
                const isDraft = plateAuthority === "draft";
                const isAuthoritative = plateAuthority === "object";
                const riskLevel =
                  plate.risk.disocclusionRisk >= 60
                    ? "high"
                    : plate.risk.disocclusionRisk >= 35
                      ? "medium"
                      : "low";
                return (
                  <div
                    key={plate.id}
                    className={`stage-object-box ${isSelected ? "is-selected" : ""} ${isDraft ? "is-draft" : ""} ${isAuthoritative ? "is-authoritative" : ""} ${riskLevel === "high" ? "is-risk-high" : riskLevel === "medium" ? "is-risk-medium" : "is-risk-low"}`}
                    style={{
                      left: `${plate.box.x * 100}%`,
                      top: `${plate.box.y * 100}%`,
                      width: `${plate.box.width * 100}%`,
                      height: `${plate.box.height * 100}%`,
                    }}
                  >
                    <button className="stage-object-hit" type="button" onClick={() => focusStagePlate(plate.id)}>
                      <span className="stage-object-badge">
                        <strong>{plate.label.replace(/^draft:\s*/i, "")}</strong>
                        <span>{formatRoleLabel(plate.role)}</span>
                        <span className={`plate-authority-chip ${plateAuthority}`}>{formatPlateAuthorityLabel(plateAuthority)}</span>
                      </span>
                    </button>
                    {isSelected ? (
                      <div className="stage-object-actions">
                        {isDraft ? (
                          <button className="ghost-button active" type="button" onClick={promoteSelectedDraftPlate}>
                            make layer
                          </button>
                        ) : null}
                        <button className="ghost-button" type="button" onClick={() => focusStagePlate(plate.id)}>
                          inspect layer
                        </button>
                        <button className="ghost-button" type="button" onClick={() => openPlateSilhouetteAssist(plate.id)}>
                          silhouette
                        </button>
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          ) : null}
          {provisionalObjectCandidates.length > 0 ? (
            <div className="candidate-marker-plane">
              {provisionalObjectCandidates.map((candidate) => (
                <button
                  key={candidate.id}
                  className="candidate-marker"
                  type="button"
                  style={{ left: `${candidate.x * 100}%`, top: `${candidate.y * 100}%` }}
                  onClick={() => focusPlacedCandidate(candidate.id)}
                >
                  <span>{candidate.label}</span>
                </button>
              ))}
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
          {debugOpen && aiAssistVisible && aiAssistSuggestion && showSelectionOverlays ? (
            <div className="ai-suggestion-plane">
              {aiAssistSuggestion.accepted_foreground_groups.map((box, index) => (
                <div key={`ai-fg-${index}`} className="ai-suggestion-box foreground" style={{ left: `${box.x * 100}%`, top: `${box.y * 100}%`, width: `${box.width * 100}%`, height: `${box.height * 100}%` }}>
                  <span>{`${formatGroupModeLabel("foreground-group")} · ${box.label}`}</span>
                </div>
              ))}
              {aiAssistSuggestion.accepted_midground_groups.map((box, index) => (
                <div key={`ai-mid-${index}`} className="ai-suggestion-box midground" style={{ left: `${box.x * 100}%`, top: `${box.y * 100}%`, width: `${box.width * 100}%`, height: `${box.height * 100}%` }}>
                  <span>{`${formatGroupModeLabel("midground-group")} · ${box.label}`}</span>
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
            >
              <span>{formatGroupModeLabel(groupMode)}</span>
            </div>
          ) : null}
          <div className="focus-frame" style={foregroundFrame} />
          <div className="stage-footer">
            <span>{sample.width} × {sample.height}</span>
            <span>motion {formatPct(snapshot.travelXPct)} / {formatPct(snapshot.travelYPct)}</span>
            <span>overscan {formatPct(snapshot.overscanPct)}</span>
          </div>
          </div>
        </div>
        </div>
        {cleanupContextPanel ? <section className="cleanup-context-shell">{cleanupContextPanel}</section> : null}

        <section className="workflow-dock">
          <article className={`panel panel-compact workflow-card depth-card effect-panel ${activeEffectPanel === "depth" ? "is-open" : "is-collapsed"}`}>
            <button className="accordion-toggle effect-panel-toggle" type="button" onClick={() => setActiveEffectPanel((value) => (value === "depth" ? null : "depth"))}>
              <div className="panel-header">
              <div className="panel-title-wrap">
                <Icon name="depth" />
                <div>
                  <h2>Depth</h2>
                  <div className="panel-subtitle">Step 2 · shape the B/W depth map</div>
                </div>
              </div>
              </div>
              <div className="accordion-actions">
                <span className="effect-summary-inline">{manual.previewMode === "composite" ? "shot" : manual.previewMode === "depth" ? "depth map" : "mask"}</span>
                <span className="accordion-chevron">{activeEffectPanel === "depth" ? "−" : "+"}</span>
              </div>
            </button>
            <div className="effect-summary-strip">
              <span>near {manual.nearLimit.toFixed(2)}</span>
              <span>far {manual.farLimit.toFixed(2)}</span>
              <span>gamma {manual.gamma.toFixed(2)}</span>
            </div>
            {activeEffectPanel === "depth" ? (
              <>
            <div className="depth-toolbar">
              <InlineSegmentedControl
                value={manual.previewMode}
                options={[
                  { label: "shot", value: "composite" },
                  { label: "depth map", value: "depth" },
                  { label: "mask", value: "selection" },
                ]}
                onChange={(value) => setManual((prev) => ({ ...prev, previewMode: value as PreviewMode }))}
              />
              <span className="chip">{proxyMaps.usingRealDepth ? "real depth source" : "proxy depth source"}</span>
            </div>
            <div className="panel-copy depth-card-copy">
              B/W depth base. White reads near, black reads far.
            </div>
            <div className="workflow-card-grid">
              <RangeControl
                label="near"
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
                label="far"
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
              <div className="depth-primary-stack">
                <RangeControl
                  label="gamma"
                  value={manual.gamma}
                  min={0.4}
                  max={2.2}
                  step={0.01}
                  onChange={(value) => setManual((prev) => ({ ...prev, gamma: value }))}
                />
                <ToggleButton
                  active={manual.invertDepth}
                  label={manual.invertDepth ? "invert depth on" : "invert depth off"}
                  onClick={() => setManual((prev) => ({ ...prev, invertDepth: !prev.invertDepth }))}
                />
              </div>
            </div>
            <section className="panel panel-compact depth-subsection">
              <button className="accordion-toggle" type="button" onClick={() => setDepthIsolateOpen((value) => !value)}>
                <div className="panel-title-wrap">
                  <div>
                    <h3>Isolate Depth Band</h3>
                    <div className="panel-subtitle">Pick the usable subject band</div>
                  </div>
                </div>
                <div className="accordion-actions">
                  <span className="accordion-chevron">{depthIsolateOpen ? "−" : "+"}</span>
                </div>
              </button>
              <div className="depth-subsection-summary">
                <span>target {manual.targetDepth.toFixed(2)}</span>
                <span>range {manual.range.toFixed(2)}</span>
              </div>
              {depthIsolateOpen ? (
                <div className="accordion-body">
                  <div className="workflow-card-secondary">
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
                  </div>
                </div>
              ) : null}
            </section>
            <section className="panel panel-compact depth-subsection">
              <button className="accordion-toggle" type="button" onClick={() => setDepthRefineOpen((value) => !value)}>
                <div className="panel-title-wrap">
                  <div>
                    <h3>Refine Depth Map</h3>
                    <div className="panel-subtitle">Soften or tighten the remap</div>
                  </div>
                </div>
                <div className="accordion-actions">
                  <span className="accordion-chevron">{depthRefineOpen ? "−" : "+"}</span>
                </div>
              </button>
              <div className="depth-subsection-summary">
                <span>softness {manual.softness.toFixed(2)}</span>
                <span>blur {manual.blurPx.toFixed(1)}px</span>
              </div>
              {depthRefineOpen ? (
                <div className="accordion-body">
                  <div className="workflow-card-secondary">
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
                </div>
              ) : null}
            </section>
            <section className="panel panel-compact depth-subsection">
              <button className="accordion-toggle" type="button" onClick={() => setDepthAdvancedOpen((value) => !value)}>
                <div className="panel-title-wrap">
                  <div>
                    <h3>Advanced Depth Shaping</h3>
                    <div className="panel-subtitle">Bias and post-filter only if the base breaks down</div>
                  </div>
                </div>
                <div className="accordion-actions">
                  <span className="accordion-chevron">{depthAdvancedOpen ? "−" : "+"}</span>
                </div>
              </button>
              {depthAdvancedOpen ? (
                <div className="accordion-body">
                  <div className="workflow-card-secondary">
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
                  </div>
                </div>
              ) : null}
            </section>
              </>
            ) : null}
          </article>

          <article className={`panel panel-compact workflow-card extract-card effect-panel ${activeEffectPanel === "extract" ? "is-open" : "is-collapsed"}`}>
            <button className="accordion-toggle effect-panel-toggle" type="button" onClick={() => setActiveEffectPanel((value) => (value === "extract" ? null : "extract"))}>
              <div className="panel-header">
              <div className="panel-title-wrap">
                <Icon name="isolate" />
                <div>
                  <h2>Extract</h2>
                  <div className="panel-subtitle">Step 2 · isolate subject and split layers</div>
                </div>
              </div>
              </div>
              <div className="accordion-actions">
                <span className="effect-summary-inline">subject split</span>
                <span className="accordion-chevron">{activeEffectPanel === "extract" ? "−" : "+"}</span>
              </div>
            </button>
            <div className="effect-summary-strip">
              <span>mask {formatPct(proxyMaps.selectionCoverage * 100)}</span>
              <span>mid {formatPct(proxyMaps.midgroundCoverage * 100)}</span>
            </div>
            {activeEffectPanel === "extract" ? (
              <>
            <div className="panel-copy extract-card-copy">
              Extract decides what stays in the subject layer, what drops to midground, and when the shot needs cleanup help.
            </div>
            <div className="workflow-card-grid">
              <div className="mini-stat-grid mini-stat-grid-compact">
                <MiniStat label="subject mask" value={formatPct(proxyMaps.selectionCoverage * 100)} />
                <MiniStat label="midground split" value={formatPct(proxyMaps.midgroundCoverage * 100)} />
              </div>
            </div>
            <div className="workflow-card-secondary">
              <div className="panel-copy">
                Use `Depth` to shape the black-and-white map. Use this card to read the isolation result and decide whether the shot is clean enough or needs manual cleanup.
              </div>
              <button className="ghost-button" type="button" onClick={() => setCleanupOpen(true)}>
                open manual cleanup
              </button>
            </div>
            <div className="panel-copy">
              Layer split: {workflowRouting.mode}. {workflowRouting.reasons[0] || "No routing warning."}
              {workflowRouting.reasons[1] ? ` ${workflowRouting.reasons[1]}` : ""}
            </div>
              </>
            ) : null}
          </article>

          <article className={`panel panel-compact workflow-card camera-card effect-panel ${activeEffectPanel === "camera" ? "is-open" : "is-collapsed"}`}>
            <button className="accordion-toggle effect-panel-toggle" type="button" onClick={() => setActiveEffectPanel((value) => (value === "camera" ? null : "camera"))}>
              <div className="panel-header">
              <div className="panel-title-wrap">
                <Icon name="camera" />
                <div>
                  <h2>Camera</h2>
                  <div className="panel-subtitle">Step 3 · move and keep it safe</div>
                </div>
              </div>
              </div>
              <div className="accordion-actions">
                <span className="effect-summary-inline">one safe move</span>
                <span className="accordion-chevron">{activeEffectPanel === "camera" ? "−" : "+"}</span>
              </div>
            </button>
            <div className="effect-summary-strip">
              <span>x {formatPct(snapshot.travelXPct)}</span>
              <span>y {formatPct(snapshot.travelYPct)}</span>
              <span>overscan {formatPct(snapshot.overscanPct)}</span>
            </div>
            {activeEffectPanel === "camera" ? (
              <>
            <div className="panel-copy camera-card-copy">
              This build uses one safe camera move for the whole shot. Use this card to tune travel and overscan; the tray below is only a keyframe reserve for a later pass.
            </div>
            <div className="panel-header-actions camera-header-actions">
              <button className="ghost-button" type="button" onClick={() => setCameraTuningOpen((value) => !value)}>
                {cameraTuningOpen ? "hide tuning" : "show tuning"}
              </button>
              <button className="ghost-button" type="button" onClick={applyRecommendedPreset}>
                apply safe move
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
                label="overscan"
                value={motion.overscanPct}
                min={4}
                max={32}
                step={0.5}
                onChange={(value) => setMotion((prev) => ({ ...prev, overscanPct: value }))}
                suffix="%"
              />
              <div className="render-mode-wrap">
                <span className="mini-label">output mode</span>
                <InlineSegmentedControl
                  value={manual.renderMode}
                  options={[
                    { label: "auto", value: "auto" },
                    { label: "safer", value: "safe" },
                    { label: "guided", value: "three-layer" },
                  ]}
                  onChange={(value) => applyRenderMode(value as RenderMode)}
                />
              </div>
            </div>
            {cameraTuningOpen ? (
              <div className="workflow-card-secondary">
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
              </div>
            ) : null}
            <div className="workflow-card-grid">
              <div className="mini-stat-grid mini-stat-grid-compact">
                <MiniStat label="current move" value={`${formatPct(snapshot.travelXPct)} / ${formatPct(snapshot.travelYPct)}`} />
                <MiniStat label="render mode" value={renderPolicy} />
              </div>
              <div className="mini-stat-grid mini-stat-grid-compact">
                <MiniStat
                  label="safe move"
                  value={`${formatPct(plateLayout.cameraSafe.suggestion.travelXPct)} / ${formatPct(plateLayout.cameraSafe.suggestion.travelYPct)}`}
                />
                <MiniStat label="safe overscan" value={formatPct(plateLayout.cameraSafe.suggestion.overscanPct)} />
              </div>
              <div className="panel-copy">
                {plateLayout.cameraSafe.warning
                  ? `Camera warning: ${plateLayout.cameraSafe.warning}.`
                  : "Camera check: no warning."}
                {plateLayout.cameraSafe.suggestion.reason ? ` Safe move note: ${plateLayout.cameraSafe.suggestion.reason}.` : ""}
              </div>
            </div>
              </>
            ) : null}
          </article>

        </section>
        </section>

      </main>

      <aside className="export-pane">
        <article className={`panel panel-compact export-card effect-panel ${exportPanelOpen ? "is-open" : "is-collapsed"}`}>
          <button className="accordion-toggle effect-panel-toggle" type="button" onClick={() => setExportPanelOpen((value) => !value)}>
            <div className="panel-header">
              <div className="panel-title-wrap">
                <Icon name="export" />
                <div>
                  <h2>Export</h2>
                  <div className="panel-subtitle">Step 4 · save layers and preview</div>
                </div>
              </div>
            </div>
            <div className="accordion-actions">
              <span className="effect-summary-inline">
                {exportLayout.metrics.visiblePlateCount} plates · {exportLayout.routing.mode}
              </span>
              <span className="accordion-chevron">{exportPanelOpen ? "−" : "+"}</span>
            </div>
          </button>
          <div className="effect-summary-strip">
            <span>{exportTargets[0].label}</span>
            <span>{exportTargets[1].label}</span>
            <span>{exportTargets[2].label}</span>
          </div>
          <div className="action-row export-actions export-actions-compact">
            <button className="ghost-button" type="button" onClick={handleExportLayout}>
              download layout
            </button>
            <button className="ghost-button" type="button" onClick={handleExportAssets}>
              download assets
            </button>
            <button className="ghost-button" type="button" onClick={handleExportJobState}>
              copy job state
            </button>
          </div>
          {exportStatus ? <div className="export-status">{exportStatus}</div> : null}
          {exportPanelOpen ? (
            <>
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
              <div className="panel-copy">
                Visible plates: {exportLayout.metrics.visiblePlateCount}. Routing stays {exportLayout.routing.mode}.
              </div>
            </>
          ) : (
            <div className="panel-copy export-collapsed-note">
              {exportLayout.cameraSafe.adjustment.applied
                ? `Safe export will auto-adjust motion and overscan.`
                : `Current camera move exports as-is.`}
            </div>
          )}
        </article>
      </aside>
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
  valueLabel?: string;
  options: { label: string; value: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <div className="segmented-control">
      <div className="range-header">
        <span>{props.label}</span>
        <strong>{props.valueLabel ?? props.value}</strong>
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

export default App;
