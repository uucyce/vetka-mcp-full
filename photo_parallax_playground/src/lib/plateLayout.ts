import { clamp, MotionSettings, ParallaxSnapshot, SampleMeta } from "./metrics";

export type PlateRole =
  | "foreground-subject"
  | "secondary-subject"
  | "environment-mid"
  | "background-far"
  | "special-clean";

export type PlateSource = "auto" | "manual" | "special-clean" | "qwen-plan";
export type PlateAuthority = "system" | "draft" | "object";

export type PlateLike = {
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

export type WorkflowRouting = {
  mode: "portrait-base" | "multi-plate";
  visibleRenderableCount: number;
  specialCleanCount: number;
  reasons: string[];
};

export type PlateExportAssetsContract = {
  contract_version: string;
  sampleId: string;
  sourceUrl: string;
  globalDepthUrl: string;
  backgroundRgbaUrl: string;
  backgroundMaskUrl: string;
  plateStack: {
    sampleId: string;
    plates: PlateLike[];
  };
  layout: PlateAwareLayoutContract;
  plates: Array<{
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
  }>;
};

export type PlateAwareLayoutContract = {
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
    focalLengthMm: number;
    filmWidthMm: number;
    aovDeg: number;
    zoomPx: number;
    zNear: number;
    zFar: number;
    referenceZ: number;
    cameraTx: number;
    cameraTy: number;
    cameraTz: number;
    motionScale: number;
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
  routing: WorkflowRouting;
  transitions: Array<{
    fromId: string;
    toId: string;
    overlapArea: number;
    zGap: number;
    transitionRisk: number;
    cameraSafe: boolean;
  }>;
  plates: Array<{
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
  }>;
};

export function deriveParallaxStrength(plate: PlateLike, minZ: number, maxZ: number) {
  if (maxZ <= minZ) return Number(clamp(plate.depthPriority, 0.18, 0.9).toFixed(3));
  const normalized = (plate.z - minZ) / Math.max(1e-6, maxZ - minZ);
  return Number(clamp(0.22 + normalized * 0.58 + plate.depthPriority * 0.12, 0.18, 0.95).toFixed(3));
}

export function recommendWorkflowRouting(plates: PlateLike[]): WorkflowRouting {
  const visibleRenderable = plates.filter((plate) => plate.visible && plate.role !== "special-clean");
  const specialClean = plates.filter((plate) => plate.role === "special-clean");
  const reasons: string[] = [];
  if (specialClean.length > 0) reasons.push("special-clean plates present");
  if (visibleRenderable.length > 2) reasons.push("more than two visible renderable plates");
  return {
    mode: specialClean.length > 0 || visibleRenderable.length > 2 ? "multi-plate" : "portrait-base",
    visibleRenderableCount: visibleRenderable.length,
    specialCleanCount: specialClean.length,
    reasons: reasons.length > 0 ? reasons : ["single-subject / low plate complexity"],
  };
}

function intersectionArea(
  a: { x: number; y: number; width: number; height: number },
  b: { x: number; y: number; width: number; height: number },
) {
  const left = Math.max(a.x, b.x);
  const top = Math.max(a.y, b.y);
  const right = Math.min(a.x + a.width, b.x + b.width);
  const bottom = Math.min(a.y + a.height, b.y + b.height);
  return Math.max(0, right - left) * Math.max(0, bottom - top);
}

function deriveCameraGeometry(params: {
  sampleWidth: number;
  sampleHeight: number;
  travelXPct: number;
  travelYPct: number;
  zoom: number;
}) {
  const { sampleWidth, sampleHeight, travelXPct, travelYPct, zoom } = params;
  const focalLengthMm = 50;
  const filmWidthMm = 36;
  const aovRad = 2 * Math.atan(filmWidthMm / (2 * focalLengthMm));
  const zoomPx = sampleWidth / (2 * Math.tan(aovRad / 2));
  const zNear = 0.72;
  const zFar = 1.85;
  const referenceZ = Number(((zNear + zFar) / 2).toFixed(3));
  const motionScale = 0.42;
  const travelXPx = sampleWidth * (travelXPct / 100);
  const travelYPx = sampleHeight * (travelYPct / 100);
  const cameraTx = -((travelXPx * referenceZ * motionScale) / Math.max(1e-6, zoomPx));
  const cameraTy = -((travelYPx * referenceZ * motionScale) / Math.max(1e-6, zoomPx));
  const cameraTz = (zoom - 1) * referenceZ * 0.22;
  return {
    focalLengthMm: Number(focalLengthMm.toFixed(2)),
    filmWidthMm: Number(filmWidthMm.toFixed(2)),
    aovDeg: Number((aovRad * (180 / Math.PI)).toFixed(4)),
    zoomPx: Number(zoomPx.toFixed(4)),
    zNear: Number(zNear.toFixed(3)),
    zFar: Number(zFar.toFixed(3)),
    referenceZ,
    cameraTx: Number(cameraTx.toFixed(6)),
    cameraTy: Number(cameraTy.toFixed(6)),
    cameraTz: Number(cameraTz.toFixed(6)),
    motionScale: Number(motionScale.toFixed(3)),
  };
}

export function buildPlateLayoutContract(params: {
  contractVersion: string;
  sample: SampleMeta;
  plateStack: PlateLike[];
  motion: MotionSettings;
  snapshot: ParallaxSnapshot;
  requestedMotion?: MotionSettings;
  renderMode: "auto" | "safe" | "three-layer";
}): PlateAwareLayoutContract {
  const { contractVersion, sample, plateStack, motion, snapshot, requestedMotion, renderMode } = params;
  const workflowRouting = recommendWorkflowRouting(plateStack);
  const visibleRenderablePlates = plateStack.filter((plate) => plate.visible && plate.role !== "special-clean");
  const plateZValues = visibleRenderablePlates.map((plate) => plate.z);
  const plateZSpan =
    plateZValues.length <= 1 ? 0 : Math.max(...plateZValues) - Math.min(...plateZValues);
  const layoutMotion = {
    ...motion,
    layerCount: Math.max(motion.layerCount, Math.max(2, visibleRenderablePlates.length)),
    layerGapPx: Math.max(motion.layerGapPx, plateZSpan * 0.85),
  };

  const renderable = plateStack.filter((plate) => plate.visible && plate.role !== "special-clean");
  const zValues = renderable.map((plate) => plate.z);
  const minZ = zValues.length > 0 ? Math.min(...zValues) : 0;
  const maxZ = zValues.length > 0 ? Math.max(...zValues) : 0;
  const motionMagnitude = Math.sqrt(layoutMotion.travelXPct ** 2 + layoutMotion.travelYPct ** 2);
  const layoutPlates = plateStack.map((plate, index) => {
    const parallaxStrength = deriveParallaxStrength(plate, minZ, maxZ);
    const motionDamping = Number(clamp(1 - parallaxStrength * 0.62, 0.22, 0.88).toFixed(3));
    const plateCoverage = Number(clamp(plate.width * plate.height, 0, 1).toFixed(4));
    const motionLoad = motionMagnitude * parallaxStrength * Math.max(0.24, 1 - motionDamping * 0.35);
    const recommendedOverscanPct = Number(clamp(8 + motionLoad * 1.5 + plateCoverage * 18, 8, 32).toFixed(2));
    const minSafeOverscanPct = Number(clamp(6 + motionLoad * 1.2 + plateCoverage * 14, 6, 28).toFixed(2));
    const disocclusionRisk = Number(
      clamp(
        10 + motionLoad * 10 + plateCoverage * 52 - layoutMotion.overscanPct * 1.35 + (plate.cleanVariant ? -10 : 0),
        0,
        100,
      ).toFixed(2),
    );
    const cameraSafe = layoutMotion.overscanPct >= minSafeOverscanPct && disocclusionRisk < 55;
    return {
      id: plate.id,
      label: plate.label,
      role: plate.role,
      source: plate.source,
      authority: plate.authority,
      order: index,
      visible: plate.visible,
      z: plate.z,
      depthPriority: Number(plate.depthPriority.toFixed(3)),
      parallaxStrength,
      motionDamping,
      cleanVariant: plate.cleanVariant,
      targetPlate: plate.targetPlate,
      box: {
        x: Number(plate.x.toFixed(4)),
        y: Number(plate.y.toFixed(4)),
        width: Number(plate.width.toFixed(4)),
        height: Number(plate.height.toFixed(4)),
      },
      risk: {
        plateCoverage,
        recommendedOverscanPct,
        minSafeOverscanPct,
        disocclusionRisk,
        cameraSafe,
      },
    };
  });
  const visibleRiskPlates = layoutPlates.filter((plate) => plate.visible && plate.role !== "special-clean");
  const transitions = visibleRiskPlates
    .slice()
    .sort((a, b) => a.order - b.order)
    .slice(0, -1)
    .map((plate, index) => {
      const nextPlate = visibleRiskPlates[index + 1];
      const overlapArea = Number(intersectionArea(plate.box, nextPlate.box).toFixed(4));
      const zGap = Number(Math.abs(nextPlate.z - plate.z).toFixed(2));
      const strengthGap = Math.abs(nextPlate.parallaxStrength - plate.parallaxStrength);
      const transitionRisk = Number(
        clamp(
          8 + overlapArea * 70 + zGap * 0.25 + strengthGap * 32 + motionMagnitude * 4 - layoutMotion.overscanPct * 0.9,
          0,
          100,
        ).toFixed(2),
      );
      return {
        fromId: plate.id,
        toId: nextPlate.id,
        overlapArea,
        zGap,
        transitionRisk,
        cameraSafe: transitionRisk < 58,
      };
    });
  const highestDisocclusionRisk =
    visibleRiskPlates.length > 0 ? Math.max(...visibleRiskPlates.map((plate) => plate.risk.disocclusionRisk)) : 0;
  const worstTransitionRisk =
    transitions.length > 0 ? Math.max(...transitions.map((transition) => transition.transitionRisk)) : 0;
  const recommendedOverscanPct =
    visibleRiskPlates.length > 0
      ? Math.max(...visibleRiskPlates.map((plate) => plate.risk.recommendedOverscanPct))
      : snapshot.recommendedOverscanPct;
  const minSafeOverscanPct =
    visibleRiskPlates.length > 0
      ? Math.max(...visibleRiskPlates.map((plate) => plate.risk.minSafeOverscanPct))
      : snapshot.minSafeOverscanPct;
  const riskyPlateIds = visibleRiskPlates.filter((plate) => !plate.risk.cameraSafe).map((plate) => plate.id);
  const cameraSafeOk =
    riskyPlateIds.length === 0 &&
    transitions.every((transition) => transition.cameraSafe) &&
    layoutMotion.overscanPct >= minSafeOverscanPct;
  const cameraSafeWarning = cameraSafeOk
    ? null
    : layoutMotion.overscanPct < minSafeOverscanPct
      ? "overscan below plate-safe minimum"
      : riskyPlateIds.length > 0
        ? "one or more plates exceed safe disocclusion threshold"
        : "plate transition risk is above safe threshold";
  const overscanShortfall = Math.max(0, minSafeOverscanPct - layoutMotion.overscanPct);
  const transitionOver = Math.max(0, worstTransitionRisk - 58);
  const disocclusionOver = Math.max(0, highestDisocclusionRisk - 55);
  const motionRiskPressure = clamp(
    Math.max(overscanShortfall / Math.max(6, minSafeOverscanPct), transitionOver / 42, disocclusionOver / 45),
    0,
    0.82,
  );
  const suggestedTravelXPct = Number(clamp(layoutMotion.travelXPct * (1 - motionRiskPressure), 0.4, 10).toFixed(2));
  const suggestedTravelYPct = Number(clamp(layoutMotion.travelYPct * (1 - motionRiskPressure), 0.2, 5).toFixed(2));
  const suggestedOverscanPct = Number(
    clamp(Math.max(layoutMotion.overscanPct, recommendedOverscanPct, minSafeOverscanPct), 6, 32).toFixed(2),
  );
  const cameraSuggestionReason = cameraSafeOk
    ? null
    : overscanShortfall > 0
      ? "increase overscan to at least the plate-safe minimum before full travel"
      : transitionOver >= disocclusionOver
        ? "reduce camera travel to lower plate transition overlap risk"
        : "reduce camera travel to keep plate disocclusion within safe range";
  const requestedCameraMotion = requestedMotion ?? motion;
  const adjustmentApplied =
    Number(requestedCameraMotion.overscanPct.toFixed(2)) !== Number(layoutMotion.overscanPct.toFixed(2)) ||
    Number(requestedCameraMotion.travelXPct.toFixed(2)) !== Number(layoutMotion.travelXPct.toFixed(2)) ||
    Number(requestedCameraMotion.travelYPct.toFixed(2)) !== Number(layoutMotion.travelYPct.toFixed(2));
  const cameraGeometry = deriveCameraGeometry({
    sampleWidth: sample.width,
    sampleHeight: sample.height,
    travelXPct: layoutMotion.travelXPct,
    travelYPct: layoutMotion.travelYPct,
    zoom: layoutMotion.zoom,
  });

  return {
    contract_version: contractVersion,
    sampleId: sample.id,
    source: {
      width: sample.width,
      height: sample.height,
      fileName: sample.fileName,
    },
    metrics: {
      visiblePlateCount: visibleRenderablePlates.length,
      plateZSpan: Number(plateZSpan.toFixed(2)),
      effectiveLayerCount: layoutMotion.layerCount,
      effectiveLayerGapPx: Number(layoutMotion.layerGapPx.toFixed(2)),
      recommendedOverscanPct: snapshot.recommendedOverscanPct,
      minSafeOverscanPct: snapshot.minSafeOverscanPct,
    },
    camera: {
      motionType: renderMode === "three-layer" ? "plate-stack" : "portrait-base",
      travelXPct: Number(layoutMotion.travelXPct.toFixed(2)),
      travelYPct: Number(layoutMotion.travelYPct.toFixed(2)),
      zoom: Number(layoutMotion.zoom.toFixed(3)),
      phase: Number(layoutMotion.phase.toFixed(3)),
      durationSec: Number(layoutMotion.durationSec.toFixed(2)),
      fps: layoutMotion.fps,
      overscanPct: Number(layoutMotion.overscanPct.toFixed(2)),
      focalLengthMm: cameraGeometry.focalLengthMm,
      filmWidthMm: cameraGeometry.filmWidthMm,
      aovDeg: cameraGeometry.aovDeg,
      zoomPx: cameraGeometry.zoomPx,
      zNear: cameraGeometry.zNear,
      zFar: cameraGeometry.zFar,
      referenceZ: cameraGeometry.referenceZ,
      cameraTx: cameraGeometry.cameraTx,
      cameraTy: cameraGeometry.cameraTy,
      cameraTz: cameraGeometry.cameraTz,
      motionScale: cameraGeometry.motionScale,
    },
    cameraSafe: {
      ok: cameraSafeOk,
      recommendedOverscanPct,
      minSafeOverscanPct,
      highestDisocclusionRisk: Number(highestDisocclusionRisk.toFixed(2)),
      worstTransitionRisk: Number(worstTransitionRisk.toFixed(2)),
      riskyPlateIds,
      warning: cameraSafeWarning,
      adjustment: {
        applied: adjustmentApplied,
        requested: {
          overscanPct: Number(requestedCameraMotion.overscanPct.toFixed(2)),
          travelXPct: Number(requestedCameraMotion.travelXPct.toFixed(2)),
          travelYPct: Number(requestedCameraMotion.travelYPct.toFixed(2)),
        },
        effective: {
          overscanPct: Number(layoutMotion.overscanPct.toFixed(2)),
          travelXPct: Number(layoutMotion.travelXPct.toFixed(2)),
          travelYPct: Number(layoutMotion.travelYPct.toFixed(2)),
        },
        reason: adjustmentApplied ? cameraSuggestionReason : null,
      },
      suggestion: {
        overscanPct: cameraSafeOk ? Number(layoutMotion.overscanPct.toFixed(2)) : suggestedOverscanPct,
        travelXPct: cameraSafeOk ? Number(layoutMotion.travelXPct.toFixed(2)) : suggestedTravelXPct,
        travelYPct: cameraSafeOk ? Number(layoutMotion.travelYPct.toFixed(2)) : suggestedTravelYPct,
        reason: cameraSuggestionReason,
      },
    },
    routing: workflowRouting,
    transitions,
    plates: layoutPlates,
  };
}

export function buildPlateExportAssetsContract(params: {
  contractVersion: string;
  sample: SampleMeta;
  plateStack: PlateLike[];
  layout: PlateAwareLayoutContract;
  proxyDepthUrl: string;
  backgroundRgbaUrl: string;
  backgroundMaskUrl: string;
  plateCoverage: Record<string, number>;
  plateRgbaUrls: Record<string, string>;
  plateMaskUrls: Record<string, string>;
  plateDepthUrls: Record<string, string>;
}): PlateExportAssetsContract {
  const {
    contractVersion,
    sample,
    plateStack,
    layout,
    proxyDepthUrl,
    backgroundRgbaUrl,
    backgroundMaskUrl,
    plateCoverage,
    plateRgbaUrls,
    plateMaskUrls,
    plateDepthUrls,
  } = params;
  const layoutById = new Map(layout.plates.map((plate) => [plate.id, plate] as const));
  return {
    contract_version: contractVersion,
    sampleId: sample.id,
    sourceUrl: `/samples/${sample.fileName}`,
    globalDepthUrl: proxyDepthUrl,
    backgroundRgbaUrl,
    backgroundMaskUrl,
    plateStack: {
      sampleId: sample.id,
      plates: plateStack,
    },
    layout,
    plates: plateStack.map((plate) => {
      const layoutPlate = layoutById.get(plate.id);
      return {
        id: plate.id,
        label: plate.label,
        role: plate.role,
        source: plate.source,
        authority: layoutPlate?.authority ?? plate.authority,
        visible: plate.visible,
        z: layoutPlate?.z ?? plate.z,
        depthPriority: layoutPlate?.depthPriority ?? Number(plate.depthPriority.toFixed(3)),
        coverage: plateCoverage[plate.id] || 0,
        rgbaUrl: plateRgbaUrls[plate.id] || "",
        maskUrl: plateMaskUrls[plate.id] || "",
        depthUrl: plateDepthUrls[plate.id] || "",
        cleanUrl: plate.role === "special-clean" ? backgroundRgbaUrl : "",
        cleanVariant: plate.cleanVariant,
        targetPlate: plate.targetPlate,
      };
    }),
  };
}
