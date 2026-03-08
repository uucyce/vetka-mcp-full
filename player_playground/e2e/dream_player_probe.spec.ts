import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

test("capture player review screenshot and geometry snapshot", async ({ page }) => {
  const videoPath = process.env.PLAYER_LAB_VIDEO_PATH || "";
  const screenshotPath = process.env.PLAYER_LAB_SCREENSHOT_PATH || "";
  const snapshotPath = process.env.PLAYER_LAB_SNAPSHOT_PATH || "";
  const useSynthetic = !videoPath;

  await page.setViewportSize({ width: 1600, height: 1080 });
  await page.goto("/");

  if (useSynthetic) {
    await page.evaluate(() => {
      window.vetkaPlayerLab?.setSyntheticSize(1280, 720);
      window.vetkaPlayerLab?.applySuggestedShell();
    });
  } else {
    await page.locator('input[type="file"]').setInputFiles(videoPath);
  }

  await page.waitForFunction(() => {
    const snapshot = window.vetkaPlayerLab?.snapshot();
    return Boolean(snapshot?.ok && snapshot.viewerWidth > 0 && snapshot.viewerHeight > 0);
  });

  await page.waitForTimeout(700);

  const snapshot = await page.evaluate(() => window.vetkaPlayerLab?.snapshot());
  expect(snapshot).toBeTruthy();
  expect(snapshot?.ok).toBe(true);

  if (snapshotPath) {
    fs.mkdirSync(path.dirname(snapshotPath), { recursive: true });
    fs.writeFileSync(snapshotPath, JSON.stringify(snapshot, null, 2), "utf8");
  }

  if (screenshotPath) {
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath, fullPage: true });
  }
});
