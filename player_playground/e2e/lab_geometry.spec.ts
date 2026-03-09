import { expect, test } from "@playwright/test";

test("fixed-footer suggested shell eliminates side letterboxing for 4:3 synthetic probe", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto("/?debug=1&variant=fixed-footer&mockWidth=640&mockHeight=480&applySuggestedShell=1");

  await page.waitForFunction(() => {
    const snapshot = window.vetkaPlayerLab?.snapshot();
    return Boolean(snapshot?.ok && snapshot.horizontalLetterboxPx <= 1);
  });

  const snapshot = await page.evaluate(() => window.vetkaPlayerLab?.snapshot());
  expect(snapshot).toBeTruthy();
  expect(snapshot?.sourceKind).toBe("synthetic");
  expect(snapshot?.variant).toBe("fixed-footer");
  expect(snapshot?.horizontalLetterboxPx).toBeLessThanOrEqual(1);
});

test("default flex-footer shell still introduces measurable side drift for a 4:3 synthetic probe", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto("/?debug=1&variant=flex-footer&mockWidth=640&mockHeight=480");

  await page.waitForFunction(() => {
    const snapshot = window.vetkaPlayerLab?.snapshot();
    return Boolean(snapshot?.ok && snapshot.horizontalLetterboxPx > 0);
  });

  const flexSnapshot = await page.evaluate(() => window.vetkaPlayerLab?.snapshot());
  expect(flexSnapshot).toBeTruthy();
  expect(flexSnapshot?.variant).toBe("flex-footer");
  expect(flexSnapshot?.horizontalLetterboxPx).toBeGreaterThan(0);
});
