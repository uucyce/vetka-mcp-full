import { describe, expect, it } from "vitest";
import { computeSnapshot, SAMPLE_LIBRARY } from "./metrics";
import {
  buildPlateExportAssetsContract,
  buildPlateLayoutContract,
  recommendWorkflowRouting,
} from "./plateLayout";

describe("plateLayout", () => {
  it("routes stacks with special-clean and multiple visible plates to multi-plate", () => {
    const routing = recommendWorkflowRouting([
      {
        id: "plate_01",
        label: "subject",
        role: "foreground-subject",
        source: "auto",
        x: 0.18,
        y: 0.16,
        width: 0.38,
        height: 0.52,
        z: 18,
        depthPriority: 0.82,
        visible: true,
      },
      {
        id: "plate_02",
        label: "mid",
        role: "environment-mid",
        source: "manual",
        x: 0.1,
        y: 0.34,
        width: 0.74,
        height: 0.38,
        z: -6,
        depthPriority: 0.42,
        visible: true,
      },
      {
        id: "plate_03",
        label: "clean",
        role: "special-clean",
        source: "special-clean",
        x: 0.12,
        y: 0.18,
        width: 0.42,
        height: 0.48,
        z: 18,
        depthPriority: 0.82,
        visible: true,
        cleanVariant: "no-subject",
      },
    ]);

    expect(routing.mode).toBe("multi-plate");
    expect(routing.reasons).toContain("special-clean plates present");
  });

  it("suggests safer overscan and travel when camera-safe gate fails", () => {
    const sample = SAMPLE_LIBRARY.find((item) => item.id === "hover-politsia") ?? SAMPLE_LIBRARY[0];
    const motion = {
      travelXPct: 5.6,
      travelYPct: 2,
      zoom: 1.058,
      phase: 0.62,
      durationSec: 4,
      fps: 25,
      overscanPct: 12,
      layerGapPx: 22,
      layerCount: 2,
    };
    const snapshot = computeSnapshot(
      sample,
      1180,
      760,
      { x: 0.53, y: 0.46, width: 0.46, height: 0.48, feather: 0.14 },
      motion,
    );

    const layout = buildPlateLayoutContract({
      contractVersion: "1.0.0",
      sample,
      motion,
      snapshot,
      renderMode: "auto",
      plateStack: [
        {
          id: "plate_01",
          label: "vehicle",
          role: "foreground-subject",
          source: "auto",
          x: 0.28,
          y: 0.21,
          width: 0.5,
          height: 0.54,
          z: 26,
          depthPriority: 0.86,
          visible: true,
          cleanVariant: "no-vehicle",
        },
        {
          id: "plate_02",
          label: "walker",
          role: "secondary-subject",
          source: "manual",
          x: 0.02,
          y: 0.45,
          width: 0.16,
          height: 0.4,
          z: 14,
          depthPriority: 0.58,
          visible: true,
        },
        {
          id: "plate_03",
          label: "street steam",
          role: "environment-mid",
          source: "manual",
          x: 0.24,
          y: 0.55,
          width: 0.44,
          height: 0.28,
          z: -8,
          depthPriority: 0.36,
          visible: true,
        },
        {
          id: "plate_04",
          label: "background city",
          role: "background-far",
          source: "auto",
          x: 0.02,
          y: 0.02,
          width: 0.96,
          height: 0.96,
          z: -30,
          depthPriority: 0.14,
          visible: true,
        },
      ],
    });

    expect(layout.cameraSafe.ok).toBe(false);
    expect(layout.cameraSafe.warning).toBeTruthy();
    expect(layout.cameraSafe.adjustment.applied).toBe(false);
    expect(layout.cameraSafe.suggestion.overscanPct).toBeGreaterThan(motion.overscanPct);
    expect(layout.cameraSafe.suggestion.travelXPct).toBeLessThanOrEqual(motion.travelXPct);
    expect(layout.cameraSafe.suggestion.reason).toBeTruthy();
    expect(layout.camera.zoomPx).toBeGreaterThan(0);
    expect(layout.camera.zFar).toBeGreaterThan(layout.camera.zNear);
    expect(layout.camera.focalLengthMm).toBe(50);
  });

  it("records adjustment metadata when effective motion differs from requested motion", () => {
    const sample = SAMPLE_LIBRARY.find((item) => item.id === "hover-politsia") ?? SAMPLE_LIBRARY[0];
    const requestedMotion = {
      travelXPct: 5.6,
      travelYPct: 2,
      zoom: 1.058,
      phase: 0.62,
      durationSec: 4,
      fps: 25,
      overscanPct: 12,
      layerGapPx: 22,
      layerCount: 2,
    };
    const effectiveMotion = {
      ...requestedMotion,
      travelXPct: 4.2,
      travelYPct: 1.5,
      overscanPct: 18,
    };
    const snapshot = computeSnapshot(
      sample,
      1180,
      760,
      { x: 0.53, y: 0.46, width: 0.46, height: 0.48, feather: 0.14 },
      effectiveMotion,
    );

    const layout = buildPlateLayoutContract({
      contractVersion: "1.0.0",
      sample,
      motion: effectiveMotion,
      requestedMotion,
      snapshot,
      renderMode: "auto",
      plateStack: [
        {
          id: "plate_01",
          label: "vehicle",
          role: "foreground-subject",
          source: "auto",
          x: 0.28,
          y: 0.21,
          width: 0.5,
          height: 0.54,
          z: 26,
          depthPriority: 0.86,
          visible: true,
          cleanVariant: "no-vehicle",
        },
        {
          id: "plate_02",
          label: "background city",
          role: "background-far",
          source: "auto",
          x: 0.02,
          y: 0.02,
          width: 0.96,
          height: 0.96,
          z: -30,
          depthPriority: 0.14,
          visible: true,
        },
      ],
    });

    expect(layout.cameraSafe.adjustment.applied).toBe(true);
    expect(layout.cameraSafe.adjustment.requested.overscanPct).toBe(12);
    expect(layout.cameraSafe.adjustment.effective.overscanPct).toBe(18);
    expect(layout.cameraSafe.adjustment.effective.travelXPct).toBe(4.2);
    expect(layout.camera.cameraTx).not.toBe(0);
    expect(layout.camera.cameraTy).not.toBe(0);
  });

  it("builds export assets contract from layout and plate maps", () => {
    const sample = SAMPLE_LIBRARY.find((item) => item.id === "keyboard-hands") ?? SAMPLE_LIBRARY[0];
    const plateStack = [
      {
        id: "plate_01",
        label: "hands",
        role: "foreground-subject" as const,
        source: "manual" as const,
        x: 0.22,
        y: 0.34,
        width: 0.42,
        height: 0.36,
        z: 18,
        depthPriority: 0.74,
        visible: true,
      },
      {
        id: "plate_02",
        label: "keyboard",
        role: "environment-mid" as const,
        source: "auto" as const,
        x: 0.18,
        y: 0.48,
        width: 0.58,
        height: 0.28,
        z: -8,
        depthPriority: 0.34,
        visible: true,
      },
    ];
    const motion = {
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
    const snapshot = computeSnapshot(
      sample,
      1180,
      760,
      { x: 0.51, y: 0.58, width: 0.6, height: 0.52, feather: 0.18 },
      motion,
    );
    const layout = buildPlateLayoutContract({
      contractVersion: "1.0.0",
      sample,
      motion,
      snapshot,
      renderMode: "auto",
      plateStack,
    });

    const contract = buildPlateExportAssetsContract({
      contractVersion: "1.0.0",
      sample,
      plateStack,
      layout,
      proxyDepthUrl: "/depth.png",
      backgroundRgbaUrl: "/bg-rgba.png",
      backgroundMaskUrl: "/bg-mask.png",
      plateCoverage: { plate_01: 0.22, plate_02: 0.36 },
      plateRgbaUrls: { plate_01: "/plate_01.png", plate_02: "/plate_02.png" },
      plateMaskUrls: { plate_01: "/plate_01_mask.png", plate_02: "/plate_02_mask.png" },
      plateDepthUrls: { plate_01: "/plate_01_depth.png", plate_02: "/plate_02_depth.png" },
    });

    expect(contract.layout.sampleId).toBe(sample.id);
    expect(contract.plates).toHaveLength(2);
    expect(contract.plates[0].rgbaUrl).toBe("/plate_01.png");
    expect(contract.plates[1].coverage).toBe(0.36);
  });
});
