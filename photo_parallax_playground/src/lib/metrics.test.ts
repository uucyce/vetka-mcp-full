import { describe, expect, it } from "vitest";
import { computeDisplayedBox, computeSnapshot, SAMPLE_LIBRARY } from "./metrics";

describe("metrics", () => {
  it("computes displayed box inside stage", () => {
    const box = computeDisplayedBox(1200, 700, 2560, 1440);
    expect(box.displayedWidth).toBeGreaterThan(0);
    expect(box.displayedHeight).toBeLessThanOrEqual(700);
    expect(box.stageCoverageRatio).toBeGreaterThan(0.8);
  });

  it("penalizes two-layer high-motion setups", () => {
    const snapshot = computeSnapshot(
      SAMPLE_LIBRARY[2],
      1180,
      760,
      { x: 0.5, y: 0.48, width: 0.34, height: 0.6, feather: 0.16 },
      {
        travelXPct: 4.4,
        travelYPct: 2.1,
        zoom: 1.07,
        phase: 0.5,
        durationSec: 4,
        fps: 24,
        overscanPct: 12,
        layerGapPx: 26,
        layerCount: 2,
      },
    );
    expect(snapshot.cardboardRisk).toBeGreaterThan(40);
    expect(snapshot.previewScore).toBeLessThan(90);
  });
});
