import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

const SAMPLES_WITH_REAL_DEPTH = new Set([
  "cassette-closeup",
  "keyboard-hands",
  "hover-politsia",
  "drone-portrait",
]);

test("capture parallax planning review screenshot and snapshot", async ({ page }) => {
  const sampleId = process.env.PARALLAX_LAB_SAMPLE_ID || "hover-politsia";
  const previewMode = process.env.PARALLAX_LAB_PREVIEW_MODE || "";
  const manualHintsPath = process.env.PARALLAX_LAB_MANUAL_HINTS_PATH || "";
  const screenshotPath = process.env.PARALLAX_LAB_SCREENSHOT_PATH || "";
  const snapshotPath = process.env.PARALLAX_LAB_SNAPSHOT_PATH || "";

  await page.setViewportSize({ width: 1720, height: 1200 });
  await page.goto(`/?sample=${sampleId}`);

  await page.waitForFunction(() => Boolean(window.vetkaParallaxLab?.snapshot()?.ok));
  await page.evaluate(() => {
    window.vetkaParallaxLab?.setMotion(3.1, 1.3, 1.052);
    window.vetkaParallaxLab?.setOverscan(16);
    window.vetkaParallaxLab?.setPhase(0.58);
  });
  if (previewMode) {
    await page.evaluate((mode) => {
      window.vetkaParallaxLab?.setPreviewMode(mode as "composite" | "depth" | "selection");
    }, previewMode);
  }
  if (manualHintsPath) {
    const payload = JSON.parse(fs.readFileSync(manualHintsPath, "utf8"));
    await page.evaluate((nextPayload) => {
      window.vetkaParallaxLab?.importManualHints(nextPayload);
    }, payload);
  }
  if (SAMPLES_WITH_REAL_DEPTH.has(sampleId)) {
    try {
      await page.waitForFunction(() => window.vetkaParallaxLab?.getState()?.usingRealDepth === true, undefined, {
        timeout: 5000,
      });
    } catch {
      // Review capture should not fail hard if baked depth arrives late.
    }
  }
  await page.waitForTimeout(250);

  const snapshot = await page.evaluate(() => window.vetkaParallaxLab?.print());
  const debugState = await page.evaluate(() => window.vetkaParallaxLab?.getState());
  expect(snapshot).toBeTruthy();
  expect(snapshot?.previewScore).toBeGreaterThan(0);

  if (snapshotPath) {
    fs.mkdirSync(path.dirname(snapshotPath), { recursive: true });
    fs.writeFileSync(
      snapshotPath,
      JSON.stringify(
        {
          ...snapshot,
          debugState,
          requestedPreviewMode: previewMode || null,
        },
        null,
        2,
      ),
      "utf8",
    );
  }

  if (screenshotPath) {
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath, fullPage: true });
  }
});
