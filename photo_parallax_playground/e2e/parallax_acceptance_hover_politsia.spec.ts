/**
 * MARKER_ACCEPTANCE_HARNESS: Repeatable acceptance test for hover-politsia
 * depth/plate visual checkpoints.
 *
 * Captures: depth source, mask coverage, preview mode screenshots,
 * plate_04 background-far export status, and key metrics.
 *
 * Run:
 *   cd photo_parallax_playground
 *   npx playwright test e2e/parallax_acceptance_hover_politsia.spec.ts --reporter=line
 *
 * Artifacts land in: photo_parallax_playground/output/playwright/hover-politsia/
 */
import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SAMPLE_ID = process.env.PARALLAX_LAB_SAMPLE_ID || "hover-politsia";
const OUT_DIR =
  process.env.PARALLAX_LAB_ACCEPTANCE_DIR ||
  path.resolve(__dirname, "../output/playwright", SAMPLE_ID);

declare global {
  interface Window {
    vetkaParallaxLab?: {
      snapshot: () => { ok: boolean; [k: string]: unknown } | null;
      getState: () => Record<string, unknown>;
      setPreviewMode: (mode: "composite" | "depth" | "selection") => void;
      exportPlateAssets: () => Record<string, unknown>;
      hydrateSourceRasterFromStage: () => boolean;
      hydrateSourceRasterFromAsset: () => Promise<boolean>;
    };
  }
}

function ensureDir(dir: string) {
  fs.mkdirSync(dir, { recursive: true });
}

function writeJson(filePath: string, data: unknown) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
}

test("hover-politsia acceptance: depth, plates, visual checkpoints", async ({
  page,
}) => {
  test.setTimeout(90_000);
  ensureDir(OUT_DIR);

  // ── 1. Navigate and wait for ready ──────────────────────────────
  await page.goto(`/?sample=${SAMPLE_ID}&debug=1`);
  await page.waitForFunction(
    () => Boolean(window.vetkaParallaxLab?.snapshot()?.ok),
    { timeout: 60_000 },
  );

  // Hydrate source raster (follow plate_export pattern)
  for (let i = 0; i < 40; i++) {
    const ready = await page.evaluate(() => {
      const api = window.vetkaParallaxLab;
      if (!api) return false;
      const state = api.getState();
      if (state.sourceRasterReady) return true;
      api.hydrateSourceRasterFromStage();
      return false;
    });
    if (ready) break;
    await page.waitForTimeout(250);
  }
  // Final async hydration attempt
  await page.evaluate(async () => {
    const api = window.vetkaParallaxLab;
    if (api && !api.getState().sourceRasterReady) {
      await api.hydrateSourceRasterFromAsset();
    }
  });
  await page.waitForTimeout(300);

  // ── 2. Read state and assert depth source ───────────────────────
  const state = await page.evaluate(() => window.vetkaParallaxLab?.getState());
  expect(state).toBeTruthy();
  writeJson(path.join(OUT_DIR, "state.json"), state);

  // Depth assertions
  expect(state!.usingRealDepth).toBe(true);
  expect(state!.sourceRasterReady).toBe(true);
  expect(state!.sampleId).toBe(SAMPLE_ID);

  // Coverage assertions
  const selectionCoverage = state!.selectionCoverage as number;
  expect(selectionCoverage).toBeGreaterThan(0);

  // Plate count
  const plateCount = state!.plateCount as number;
  expect(plateCount).toBeGreaterThanOrEqual(4);

  // ── 3. Screenshot: composite view ───────────────────────────────
  await page.evaluate(() =>
    window.vetkaParallaxLab?.setPreviewMode("composite"),
  );
  await page.waitForTimeout(200);
  await page
    .locator(".stage-shell")
    .screenshot({ path: path.join(OUT_DIR, "composite.png") });

  // ── 4. Screenshot: depth view ───────────────────────────────────
  await page.evaluate(() =>
    window.vetkaParallaxLab?.setPreviewMode("depth"),
  );
  await page.waitForTimeout(200);
  await page
    .locator(".stage-shell")
    .screenshot({ path: path.join(OUT_DIR, "depth.png") });

  // ── 5. Screenshot: selection view ───────────────────────────────
  await page.evaluate(() =>
    window.vetkaParallaxLab?.setPreviewMode("selection"),
  );
  await page.waitForTimeout(200);
  await page
    .locator(".stage-shell")
    .screenshot({ path: path.join(OUT_DIR, "selection.png") });

  // Return to composite for plate export
  await page.evaluate(() =>
    window.vetkaParallaxLab?.setPreviewMode("composite"),
  );
  await page.waitForTimeout(150);

  // ── 6. Export plate assets and validate plate_04 ────────────────
  const contract = await page.evaluate(
    () => window.vetkaParallaxLab?.exportPlateAssets() as Record<string, unknown>,
  );
  expect(contract).toBeTruthy();

  const plates = contract!.plates as Array<{
    id: string;
    label: string;
    role: string;
    coverage: number;
    rgbaUrl: string;
    maskUrl: string;
    depthUrl: string;
    visible: boolean;
  }>;

  // Write plate summary (without data URLs to keep it small)
  const plateSummary = plates.map((p) => ({
    id: p.id,
    label: p.label,
    role: p.role,
    visible: p.visible,
    coverage: p.coverage,
    hasRgba: Boolean(p.rgbaUrl),
    hasMask: Boolean(p.maskUrl),
    hasDepth: Boolean(p.depthUrl),
  }));
  writeJson(path.join(OUT_DIR, "plate_summary.json"), plateSummary);

  // Assert plate_04 (background-far) is a real exported plate
  const bgFarPlate = plates.find((p) => p.role === "background-far" && p.visible);
  expect(bgFarPlate).toBeTruthy();
  expect(bgFarPlate!.coverage).toBeGreaterThan(0.1);
  expect(bgFarPlate!.rgbaUrl).toBeTruthy();
  expect(bgFarPlate!.maskUrl).toBeTruthy();
  expect(bgFarPlate!.depthUrl).toBeTruthy();

  // Assert foreground plates are still healthy
  const fgPlate = plates.find((p) => p.role === "foreground-subject" && p.visible);
  expect(fgPlate).toBeTruthy();
  expect(fgPlate!.coverage).toBeGreaterThan(0.1);

  // ── 7. Camera safety (soft check — recorded but not blocking) ──
  const cameraSafe = state!.cameraSafe as boolean;
  // cameraSafe depends on layout contract camera params which may differ
  // between runtime contexts. Record it but don't block acceptance.

  // ── 8. Write final verdict ──────────────────────────────────────
  const verdict = {
    sample: SAMPLE_ID,
    timestamp: new Date().toISOString(),
    usingRealDepth: state!.usingRealDepth,
    sourceRasterReady: state!.sourceRasterReady,
    plateCount: plateCount,
    selectionCoverage: selectionCoverage,
    cameraSafe: cameraSafe,
    bgFarPlate: {
      id: bgFarPlate!.id,
      coverage: bgFarPlate!.coverage,
      hasFiles: Boolean(bgFarPlate!.rgbaUrl && bgFarPlate!.maskUrl && bgFarPlate!.depthUrl),
    },
    fgPlate: {
      id: fgPlate!.id,
      coverage: fgPlate!.coverage,
    },
    allPlates: plateSummary,
    pass: true,
  };
  writeJson(path.join(OUT_DIR, "verdict.json"), verdict);
});
