import { expect, test } from "@playwright/test";

const VIDEO_FIXTURE = "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tools/back_to_ussr_app/docs/media/demo.mp4";

test("pure player shell expands with viewport resize without changing action mode", async ({ page }) => {
  await page.setViewportSize({ width: 980, height: 680 });
  await page.goto("/");
  await page.locator('input[type="file"]').setInputFiles(VIDEO_FIXTURE);

  await page.waitForFunction(() => {
    const snapshot = window.vetkaPlayerLab?.snapshot();
    return Boolean(snapshot?.ok && snapshot.viewerWidth > 0 && snapshot.sourceKind === "video");
  });

  const before = await page.evaluate(() => window.vetkaPlayerLab?.snapshot());
  expect(before?.activeContextAction).toBe("vetka");

  await page.setViewportSize({ width: 1320, height: 900 });
  await page.waitForFunction(() => {
    const snapshot = window.vetkaPlayerLab?.snapshot();
    return Boolean(snapshot && snapshot.windowInnerWidth >= 1320 && snapshot.viewerWidth > 0);
  });

  const after = await page.evaluate(() => window.vetkaPlayerLab?.snapshot());
  expect(after?.viewerWidth).toBeGreaterThan(before?.viewerWidth ?? 0);
  expect(after?.viewerHeight).toBeGreaterThan(before?.viewerHeight ?? 0);
  expect(after?.activeContextAction).toBe("vetka");
});

test("fullscreen button requests fullscreen in web sandbox", async ({ page }) => {
  await page.setViewportSize({ width: 1200, height: 840 });
  await page.goto("/");
  await page.locator('input[type="file"]').setInputFiles(VIDEO_FIXTURE);

  await page.waitForFunction(() => {
    const snapshot = window.vetkaPlayerLab?.snapshot();
    return Boolean(snapshot?.ok && snapshot.sourceKind === "video");
  });

  await page.getByTestId("fullscreen-button").click();
  await page.waitForFunction(() => Boolean(document.fullscreenElement));

  const isFullscreen = await page.evaluate(() => Boolean(document.fullscreenElement));
  expect(isFullscreen).toBe(true);
});

test("center play button toggles playback without seek jump", async ({ page }) => {
  await page.setViewportSize({ width: 1200, height: 840 });
  await page.goto("/");
  await page.locator('input[type="file"]').setInputFiles(VIDEO_FIXTURE);

  await page.waitForFunction(() => {
    const snapshot = window.vetkaPlayerLab?.snapshot();
    return Boolean(snapshot?.ok && snapshot?.sourceKind === "video");
  });

  const before = await page.evaluate(() => {
    const video = document.querySelector("video") as HTMLVideoElement | null;
    return Number(video?.currentTime || 0);
  });

  await page.locator(".hud-button").click();
  await page.waitForTimeout(150);

  const after = await page.evaluate(() => {
    const video = document.querySelector("video") as HTMLVideoElement | null;
    return Number(video?.currentTime || 0);
  });

  expect(Math.abs(after - before)).toBeLessThan(0.25);
});
