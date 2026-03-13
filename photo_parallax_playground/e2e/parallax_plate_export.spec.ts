import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

function writeDataUrl(filePath: string, dataUrl: string | undefined) {
  if (!dataUrl || !dataUrl.startsWith("data:image/png;base64,")) return false;
  const base64 = dataUrl.slice("data:image/png;base64,".length);
  fs.writeFileSync(filePath, Buffer.from(base64, "base64"));
  return true;
}

test("export plate-wise png alpha and depth assets", async ({ page }) => {
  test.setTimeout(90000);
  const sampleId = process.env.PARALLAX_LAB_SAMPLE_ID || "hover-politsia";
  const outputDir =
    process.env.PARALLAX_LAB_PLATE_EXPORT_DIR ||
    `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports/${sampleId}`;

  fs.mkdirSync(outputDir, { recursive: true });

  await page.setViewportSize({ width: 1720, height: 1200 });
  await page.goto(`/?sample=${sampleId}&debug=1`);
  await page.waitForFunction(() => Boolean(window.vetkaParallaxLab?.snapshot()?.ok), { timeout: 60000 });
  const applyQwenPlan = process.env.PARALLAX_LAB_APPLY_QWEN_PLAN === "1";
  const applyQwenGate = process.env.PARALLAX_LAB_APPLY_QWEN_GATE === "1";
  await page.evaluate(() => {
    const api = window.vetkaParallaxLab;
    if (!api) throw new Error("vetkaParallaxLab API is unavailable");
    api.setPreviewMode("composite");
  });
  let sourceReady = false;
  for (let index = 0; index < 160; index += 1) {
    sourceReady = await page.evaluate(() => {
      const api = window.vetkaParallaxLab;
      if (!api) throw new Error("vetkaParallaxLab API is unavailable");
      return api.getState().sourceRasterReady;
    });
    if (sourceReady) break;
    const stageHydrated = await page.evaluate(() => {
      const api = window.vetkaParallaxLab;
      if (!api) throw new Error("vetkaParallaxLab API is unavailable");
      return api.hydrateSourceRasterFromStage();
    });
    if (!stageHydrated && index % 4 === 3) {
      await page.evaluate(async () => {
        const api = window.vetkaParallaxLab;
        if (!api) throw new Error("vetkaParallaxLab API is unavailable");
        await api.hydrateSourceRasterFromAsset();
      });
    }
    await page.waitForTimeout(250);
  }
  if (!sourceReady) {
    await page.evaluate(async () => {
      const api = window.vetkaParallaxLab;
      if (!api) throw new Error("vetkaParallaxLab API is unavailable");
      await api.hydrateSourceRasterFromAsset();
    });
    await page.waitForTimeout(1200);
    sourceReady = await page.evaluate(() => {
      const api = window.vetkaParallaxLab;
      if (!api) throw new Error("vetkaParallaxLab API is unavailable");
      return api.getState().sourceRasterReady;
    });
  }
  expect(sourceReady).toBeTruthy();
  if (applyQwenGate) {
    await page.waitForFunction(() => Boolean((window as any).vetkaParallaxLab), { timeout: 15000 });
    await page.evaluate(async () => {
      const api = window.vetkaParallaxLab;
      if (!api) throw new Error("vetkaParallaxLab API is unavailable");
      await new Promise((resolve) => window.setTimeout(resolve, 150));
      api.applyQwenPlateGate();
    });
    await page.waitForTimeout(150);
  } else if (applyQwenPlan) {
    await page.waitForFunction(() => Boolean((window as any).vetkaParallaxLab), { timeout: 15000 });
    await page.evaluate(async () => {
      const api = window.vetkaParallaxLab;
      if (!api) throw new Error("vetkaParallaxLab API is unavailable");
      await new Promise((resolve) => window.setTimeout(resolve, 150));
      api.applyQwenPlatePlan();
    });
    await page.waitForTimeout(150);
  }

  const result = await page.evaluate(async () => {
    const api = window.vetkaParallaxLab;
    if (!api) throw new Error("vetkaParallaxLab API is unavailable");
    api.setPreviewMode("composite");
    await new Promise((resolve) => window.setTimeout(resolve, 120));
    const compositeState = api.getState();
    const assets = api.exportPlateAssets();
    api.setPreviewMode("depth");
    await new Promise((resolve) => window.setTimeout(resolve, 120));
    const depthState = api.getState();
    return {
      snapshot: api.snapshot(),
      assets,
      compositeState,
      depthState,
      jobState: api.exportJobState(),
    };
  });

  expect(result.assets.sampleId).toBe(sampleId);
  expect(result.assets.layout.plates.length).toBeGreaterThan(0);

  fs.writeFileSync(path.join(outputDir, "plate_stack.json"), JSON.stringify(result.assets.plateStack, null, 2), "utf8");
  fs.writeFileSync(path.join(outputDir, "plate_layout.json"), JSON.stringify(result.assets.layout, null, 2), "utf8");
  fs.writeFileSync(path.join(outputDir, "plate_export_job_state.json"), JSON.stringify(result.jobState, null, 2), "utf8");
  fs.writeFileSync(path.join(outputDir, "plate_export_snapshot.json"), JSON.stringify(result.snapshot, null, 2), "utf8");
  fs.writeFileSync(path.join(outputDir, "plate_export_composite_state.json"), JSON.stringify(result.compositeState, null, 2), "utf8");
  fs.writeFileSync(path.join(outputDir, "plate_export_depth_state.json"), JSON.stringify(result.depthState, null, 2), "utf8");

  writeDataUrl(path.join(outputDir, "global_depth_bw.png"), result.assets.globalDepthUrl);
  writeDataUrl(path.join(outputDir, "background_rgba.png"), result.assets.backgroundRgbaUrl);
  writeDataUrl(path.join(outputDir, "background_mask.png"), result.assets.backgroundMaskUrl);

  const exportedPlates = result.assets.plates.map((plate, index: number) => {
    const baseName = `plate_${String(index + 1).padStart(2, "0")}`;
    const files: Record<string, string> = {};
    if (writeDataUrl(path.join(outputDir, `${baseName}_rgba.png`), plate.rgbaUrl)) {
      files.rgba = `${baseName}_rgba.png`;
    }
    if (writeDataUrl(path.join(outputDir, `${baseName}_mask.png`), plate.maskUrl)) {
      files.mask = `${baseName}_mask.png`;
    }
    if (writeDataUrl(path.join(outputDir, `${baseName}_depth.png`), plate.depthUrl)) {
      files.depth = `${baseName}_depth.png`;
    }
    if (writeDataUrl(path.join(outputDir, `${baseName}_clean.png`), plate.cleanUrl)) {
      files.clean = `${baseName}_clean.png`;
    }
    return {
      index: index + 1,
      id: plate.id,
      label: plate.label,
      role: plate.role,
      visible: plate.visible,
      coverage: plate.coverage,
      z: plate.z,
      depthPriority: plate.depthPriority,
      cleanVariant: plate.cleanVariant || null,
      files,
    };
  });

  fs.writeFileSync(
    path.join(outputDir, "plate_export_manifest.json"),
    JSON.stringify(
      {
        sampleId,
        files: {
          plateStack: "plate_stack.json",
          plateLayout: "plate_layout.json",
          jobState: "plate_export_job_state.json",
          snapshot: "plate_export_snapshot.json",
          compositeState: "plate_export_composite_state.json",
          depthState: "plate_export_depth_state.json",
          globalDepth: "global_depth_bw.png",
          backgroundRgba: "background_rgba.png",
          backgroundMask: "background_mask.png",
          compositeScreenshot: "plate_export_composite.png",
          depthScreenshot: "plate_export_depth.png",
        },
        exportedPlates,
      },
      null,
      2,
    ),
    "utf8",
  );

  await page.setViewportSize({ width: 1720, height: 1200 });
  await page.locator(".stage-shell").screenshot({
    path: path.join(outputDir, "plate_export_depth.png"),
  });
  await page.evaluate(() => {
    const api = window.vetkaParallaxLab;
    if (!api) throw new Error("vetkaParallaxLab API is unavailable");
    api.setPreviewMode("composite");
  });
  await page.waitForTimeout(120);
  await page.locator(".stage-shell").screenshot({
    path: path.join(outputDir, "plate_export_composite.png"),
  });
});
