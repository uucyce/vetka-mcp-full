import { expect, test } from "@playwright/test";

test("synthetic marker bridge uses VETKA status gate and time markers", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto("/?debug=1&variant=fixed-footer&mockWidth=1280&mockHeight=720&applySuggestedShell=1");

  await page.waitForFunction(() => {
    const snapshot = window.vetkaPlayerLab?.snapshot();
    return Boolean(snapshot?.ok);
  });

  let snapshot = await page.evaluate(() => window.vetkaPlayerLab?.snapshot());
  expect(snapshot?.activeContextAction).toBe("vetka");
  expect(snapshot?.inVetka).toBe(false);
  expect(snapshot?.markerCount).toBe(0);

  await page.evaluate(() => {
    window.vetkaPlayerLab?.setInVetka(true);
    window.vetkaPlayerLab?.addMomentMarker("favorite");
    window.vetkaPlayerLab?.addMomentMarker("comment", "synthetic note");
  });

  await page.waitForFunction(() => {
    const snapshot = window.vetkaPlayerLab?.snapshot();
    return Boolean(
      snapshot?.inVetka &&
      snapshot?.favoriteMomentCount === 1 &&
      snapshot?.commentMomentCount === 1 &&
      snapshot?.markerCount === 2,
    );
  });

  snapshot = await page.evaluate(() => window.vetkaPlayerLab?.snapshot());
  const markers = await page.evaluate(() => window.vetkaPlayerLab?.markers());

  expect(snapshot?.inVetka).toBe(true);
  expect(snapshot?.activeContextAction).toBe("favorite");
  expect(snapshot?.favoriteMomentCount).toBe(1);
  expect(snapshot?.commentMomentCount).toBe(1);
  expect(snapshot?.markerCount).toBe(2);
  expect(markers).toHaveLength(2);
  expect(markers?.[0]?.schema_version).toBe("cut_time_marker_v1");
  expect(markers?.[0]?.kind).toBe("favorite");
  expect(markers?.[1]?.kind).toBe("comment");
});
