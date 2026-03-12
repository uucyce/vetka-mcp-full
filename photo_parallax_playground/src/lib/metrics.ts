export interface SampleMeta {
  id: string;
  title: string;
  fileName: string;
  width: number;
  height: number;
  scenario: string;
  notes: string;
  tags: string[];
}

export interface FocusSettings {
  x: number;
  y: number;
  width: number;
  height: number;
  feather: number;
}

export interface MotionSettings {
  travelXPct: number;
  travelYPct: number;
  zoom: number;
  phase: number;
  durationSec: number;
  fps: number;
  overscanPct: number;
  layerGapPx: number;
  layerCount: number;
}

export interface ParallaxSnapshot {
  ok: boolean;
  sampleId: string;
  fileName: string;
  sourceWidth: number;
  sourceHeight: number;
  sourceAspectRatio: number;
  stageWidth: number;
  stageHeight: number;
  displayedWidth: number;
  displayedHeight: number;
  focusX: number;
  focusY: number;
  focusWidth: number;
  focusHeight: number;
  focusFeather: number;
  foregroundCoverage: number;
  travelXPct: number;
  travelYPct: number;
  zoom: number;
  phase: number;
  overscanPct: number;
  recommendedOverscanPct: number;
  minSafeOverscanPct: number;
  layerGapPx: number;
  layerCount: number;
  durationSec: number;
  fps: number;
  totalFrames: number;
  motionMagnitude: number;
  disocclusionRisk: number;
  cardboardRisk: number;
  previewScore: number;
  safeTravelXPct: number;
  safeTravelYPct: number;
  stageCoverageRatio: number;
  notes: string;
}

export const SAMPLE_LIBRARY: SampleMeta[] = [
  {
    id: "cassette-closeup",
    title: "Cassette close-up",
    fileName: "cassette-closeup.png",
    width: 2560,
    height: 1440,
    scenario: "large foreground object with fingers and transparent edges",
    notes: "Stress test for disocclusion and transparent object boundaries.",
    tags: ["close-up", "hands", "transparent", "foreground-heavy"],
  },
  {
    id: "keyboard-hands",
    title: "Keyboard hands",
    fileName: "keyboard-hands.png",
    width: 2560,
    height: 1440,
    scenario: "mid-shot with fingers, keyboard, monitor glow and layered depth",
    notes: "Good for mild parallax and multi-surface separation.",
    tags: ["mid-shot", "hands", "multi-depth", "tech"],
  },
  {
    id: "hover-politsia",
    title: "Hover Politsia street",
    fileName: "hover-politsia.jpg",
    width: 2560,
    height: 1440,
    scenario: "wide cinematic street scene with floating vehicle",
    notes: "Good for overscan planning and background plate pressure.",
    tags: ["wide", "street", "vehicle", "background-complex"],
  },
  {
    id: "drone-portrait",
    title: "Drone portrait",
    fileName: "drone-portrait.webp",
    width: 1024,
    height: 1024,
    scenario: "strong portrait subject with blurred city background",
    notes: "Low-risk sample for subject-isolation tests.",
    tags: ["portrait", "bokeh", "subject-centric", "square"],
  },
  {
    id: "punk-rooftop",
    title: "Punk rooftop",
    fileName: "punk-rooftop.png",
    width: 2560,
    height: 1440,
    scenario: "single seated figure on rooftop with deep urban background",
    notes: "Good for foreground human grouping against a complex wide city backdrop.",
    tags: ["wide", "human", "city", "foreground-left"],
  },
  {
    id: "truck-driver",
    title: "Truck driver",
    fileName: "truck-driver.png",
    width: 2560,
    height: 1440,
    scenario: "subject inside a vehicle cabin framed by window geometry",
    notes: "Good for testing object grouping inside hard frame boundaries.",
    tags: ["driver", "vehicle", "framed-subject", "interior"],
  },
];

export function clamp(value: number, minimum: number, maximum: number) {
  return Math.max(minimum, Math.min(maximum, value));
}

export function computeDisplayedBox(
  stageWidth: number,
  stageHeight: number,
  sourceWidth: number,
  sourceHeight: number,
) {
  if (stageWidth <= 0 || stageHeight <= 0 || sourceWidth <= 0 || sourceHeight <= 0) {
    return {
      displayedWidth: 0,
      displayedHeight: 0,
      stageCoverageRatio: 0,
    };
  }

  const scale = Math.min(stageWidth / sourceWidth, stageHeight / sourceHeight);
  const displayedWidth = Number((sourceWidth * scale).toFixed(2));
  const displayedHeight = Number((sourceHeight * scale).toFixed(2));
  return {
    displayedWidth,
    displayedHeight,
    stageCoverageRatio: Number(
      ((displayedWidth * displayedHeight) / Math.max(1, stageWidth * stageHeight)).toFixed(4),
    ),
  };
}

export function computeSnapshot(
  sample: SampleMeta,
  stageWidth: number,
  stageHeight: number,
  focus: FocusSettings,
  motion: MotionSettings,
): ParallaxSnapshot {
  const sourceAspectRatio = Number((sample.width / sample.height).toFixed(4));
  const { displayedWidth, displayedHeight, stageCoverageRatio } = computeDisplayedBox(
    stageWidth,
    stageHeight,
    sample.width,
    sample.height,
  );

  const foregroundCoverage = Number((focus.width * focus.height).toFixed(4));
  const motionMagnitude = Number(
    Math.sqrt(motion.travelXPct ** 2 + motion.travelYPct ** 2).toFixed(3),
  );
  const recommendedOverscanPct = Number(
    clamp(10 + motionMagnitude * 2.4 + foregroundCoverage * 14, 10, 26).toFixed(2),
  );
  const minSafeOverscanPct = Number(
    clamp(8 + motionMagnitude * 1.9 + foregroundCoverage * 10, 8, 22).toFixed(2),
  );
  const disocclusionRisk = Number(
    clamp(
      18 + motionMagnitude * 10 + foregroundCoverage * 65 - motion.overscanPct * 1.7,
      0,
      100,
    ).toFixed(2),
  );
  const cardboardRisk = Number(
    clamp(
      22 + motionMagnitude * 8 + (3 - motion.layerCount) * 18 + (motion.layerGapPx / 32) * 10,
      0,
      100,
    ).toFixed(2),
  );

  const previewScore = Math.round(
    clamp(
      100
        - disocclusionRisk * 0.42
        - cardboardRisk * 0.31
        + stageCoverageRatio * 24
        + (motion.overscanPct - minSafeOverscanPct) * 1.2,
      0,
      100,
    ),
  );

  const safeTravelXPct = Number(
    clamp(5.1 - foregroundCoverage * 4.8 - motion.layerGapPx / 42, 1.2, 5.1).toFixed(2),
  );
  const safeTravelYPct = Number(clamp(safeTravelXPct * 0.55, 0.7, 2.8).toFixed(2));

  return {
    ok: stageWidth > 0 && stageHeight > 0,
    sampleId: sample.id,
    fileName: sample.fileName,
    sourceWidth: sample.width,
    sourceHeight: sample.height,
    sourceAspectRatio,
    stageWidth: Math.round(stageWidth),
    stageHeight: Math.round(stageHeight),
    displayedWidth,
    displayedHeight,
    focusX: Number(focus.x.toFixed(3)),
    focusY: Number(focus.y.toFixed(3)),
    focusWidth: Number(focus.width.toFixed(3)),
    focusHeight: Number(focus.height.toFixed(3)),
    focusFeather: Number(focus.feather.toFixed(3)),
    foregroundCoverage,
    travelXPct: Number(motion.travelXPct.toFixed(2)),
    travelYPct: Number(motion.travelYPct.toFixed(2)),
    zoom: Number(motion.zoom.toFixed(3)),
    phase: Number(motion.phase.toFixed(3)),
    overscanPct: Number(motion.overscanPct.toFixed(2)),
    recommendedOverscanPct,
    minSafeOverscanPct,
    layerGapPx: Number(motion.layerGapPx.toFixed(1)),
    layerCount: motion.layerCount,
    durationSec: Number(motion.durationSec.toFixed(2)),
    fps: motion.fps,
    totalFrames: Math.round(motion.durationSec * motion.fps),
    motionMagnitude,
    disocclusionRisk,
    cardboardRisk,
    previewScore,
    safeTravelXPct,
    safeTravelYPct,
    stageCoverageRatio,
    notes: sample.notes,
  };
}
