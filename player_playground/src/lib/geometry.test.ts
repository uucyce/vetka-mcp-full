import { describe, expect, it } from "vitest";
import { computeDisplayedBox, computeDreamScore, LAB_FOOTER_HEIGHT, suggestShellSize } from "./geometry";

describe("player geometry math", () => {
  it("computes side letterboxing for a too-wide viewer", () => {
    const result = computeDisplayedBox(960, 400, 640, 480);
    expect(result.displayedWidth).toBeLessThan(960);
    expect(result.horizontalLetterboxPx).toBeGreaterThan(0);
    expect(result.verticalLetterboxPx).toBe(0);
  });

  it("computes top and bottom letterboxing for a too-tall viewer", () => {
    const result = computeDisplayedBox(640, 700, 640, 480);
    expect(result.displayedHeight).toBeLessThan(700);
    expect(result.verticalLetterboxPx).toBeGreaterThan(0);
  });

  it("suggests a 4:3 shell that includes footer reserve", () => {
    const shell = suggestShellSize(640, 480, 56, 960, 700);
    expect(shell.shellWidth).toBeGreaterThan(360);
    expect(shell.shellHeight).toBeGreaterThan(240);
    expect(shell.shellHeight).toBeGreaterThan(shell.shellWidth / (640 / 480));
  });

  it("suggested shell removes side letterboxing for a 4:3 probe", () => {
    const shell = suggestShellSize(640, 480, LAB_FOOTER_HEIGHT, 1200, 900);
    const viewerHeight = shell.shellHeight - LAB_FOOTER_HEIGHT;
    const result = computeDisplayedBox(shell.shellWidth, viewerHeight, 640, 480);
    expect(result.horizontalLetterboxPx).toBe(0);
  });

  it("suggests a portrait shell for portrait media", () => {
    const shell = suggestShellSize(288, 620, 0, 1400, 900);
    expect(shell.shellHeight).toBeGreaterThan(shell.shellWidth);
  });

  it("rewards low chrome and low letterboxing in dream score", () => {
    const strong = computeDreamScore({
      windowInnerWidth: 1280,
      windowInnerHeight: 760,
      topbarHeight: 40,
      footerHeight: 56,
      displayedWidth: 1040,
      displayedHeight: 585,
      horizontalLetterboxPx: 0.2,
      aspectError: 0.0002,
    });
    const weak = computeDreamScore({
      windowInnerWidth: 1280,
      windowInnerHeight: 760,
      topbarHeight: 96,
      footerHeight: 56,
      displayedWidth: 760,
      displayedHeight: 420,
      horizontalLetterboxPx: 18,
      aspectError: 0.02,
    });
    expect(strong.dreamScore).toBeGreaterThan(weak.dreamScore);
  });
});
