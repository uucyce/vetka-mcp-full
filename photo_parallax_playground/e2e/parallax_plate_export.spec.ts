import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

const CONTRACT_VERSION = "1.0.0";

function writeDataUrl(filePath: string, dataUrl: string | undefined) {
  if (!dataUrl || !dataUrl.startsWith("data:image/png;base64,")) return false;
  const base64 = dataUrl.slice("data:image/png;base64,".length);
  fs.writeFileSync(filePath, Buffer.from(base64, "base64"));
  return true;
}

function readEnvInt(name: string, fallback: number) {
  const raw = process.env[name];
  if (!raw) return fallback;
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

type SourceReadinessDiagnostics = {
  sampleId: string;
  ready: boolean;
  attempts: number;
  pollMs: number;
  maxPolls: number;
  stageHydrateCalls: number;
  stageHydrateSuccesses: number;
  assetHydrateCalls: number;
  assetHydrateSuccesses: number;
  elapsedMs: number;
  finalState: Record<string, unknown> | null;
  snapshot: Record<string, unknown> | null;
};

function expectObjectKeys(value: unknown, keys: string[], label: string) {
  expect(value, `${label} must be an object`).toBeTruthy();
  expect(typeof value, `${label} must be an object`).toBe("object");
  for (const key of keys) {
    expect((value as Record<string, unknown>)[key], `${label}.${key} is required`).not.toBeUndefined();
  }
}

function validatePlateLayoutContract(layout: Record<string, unknown>) {
  expect(layout.contract_version).toBe(CONTRACT_VERSION);
  expectObjectKeys(
    layout,
    ["contract_version", "sampleId", "source", "metrics", "camera", "cameraSafe", "routing", "transitions", "plates"],
    "plate_layout",
  );
  expectObjectKeys(
    layout.camera,
    [
      "motionType",
      "travelXPct",
      "travelYPct",
      "zoom",
      "phase",
      "durationSec",
      "fps",
      "overscanPct",
      "focalLengthMm",
      "filmWidthMm",
      "aovDeg",
      "zoomPx",
      "zNear",
      "zFar",
      "referenceZ",
      "cameraTx",
      "cameraTy",
      "cameraTz",
      "motionScale",
    ],
    "plate_layout.camera",
  );
  expectObjectKeys(
    layout.cameraSafe,
    ["ok", "recommendedOverscanPct", "minSafeOverscanPct", "highestDisocclusionRisk", "worstTransitionRisk", "riskyPlateIds", "warning", "suggestion"],
    "plate_layout.cameraSafe",
  );
  expectObjectKeys(
    (layout.cameraSafe as Record<string, unknown>).suggestion,
    ["overscanPct", "travelXPct", "travelYPct", "reason"],
    "plate_layout.cameraSafe.suggestion",
  );
}

function validatePlateExportManifest(manifest: Record<string, unknown>) {
  expect(manifest.contract_version).toBe(CONTRACT_VERSION);
  expectObjectKeys(manifest, ["contract_version", "sampleId", "files", "exportedPlates"], "plate_export_manifest");
  expectObjectKeys(
    manifest.files,
    [
      "plateStack",
      "plateLayout",
      "jobState",
      "snapshot",
      "readinessDiagnostics",
      "compositeState",
      "depthState",
      "globalDepth",
      "backgroundRgba",
      "backgroundMask",
      "compositeScreenshot",
      "depthScreenshot",
    ],
    "plate_export_manifest.files",
  );
  const exportedPlates = manifest.exportedPlates as Array<Record<string, unknown>>;
  expect(Array.isArray(exportedPlates), "plate_export_manifest.exportedPlates must be an array").toBeTruthy();
  expect(exportedPlates.length, "plate_export_manifest.exportedPlates must not be empty").toBeGreaterThan(0);
  for (const [index, plate] of exportedPlates.entries()) {
    expectObjectKeys(
      plate,
      ["index", "id", "label", "role", "visible", "coverage", "z", "depthPriority", "cleanVariant", "files"],
      `plate_export_manifest.exportedPlates[${index}]`,
    );
  }
}

function validateQwenPlateGateContract(gate: Record<string, unknown>, sampleId: string) {
  expect(gate.contract_version).toBe(CONTRACT_VERSION);
  expect(gate.sample_id).toBe(sampleId);
  expectObjectKeys(
    gate,
    ["contract_version", "sample_id", "decision", "confidence", "metrics", "added_special_clean_variants", "reasons", "gated_plate_stack", "created_at"],
    `qwen_plate_gate.${sampleId}`,
  );
  expectObjectKeys(
    gate.metrics,
    ["manual_visible_count", "qwen_visible_count", "manual_special_clean_count", "qwen_special_clean_count", "visible_overlap_ratio"],
    `qwen_plate_gate.${sampleId}.metrics`,
  );
  expectObjectKeys(gate.gated_plate_stack, ["sampleId", "plates"], `qwen_plate_gate.${sampleId}.gated_plate_stack`);
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
  const sourceReadyMaxPolls = readEnvInt("PARALLAX_LAB_SOURCE_READY_MAX_POLLS", 200);
  const sourceReadyPollMs = readEnvInt("PARALLAX_LAB_SOURCE_READY_POLL_MS", 250);
  const sourceReadyAssetEvery = readEnvInt("PARALLAX_LAB_SOURCE_READY_ASSET_EVERY", 4);
  const sourceReadyFinalAssetRetries = readEnvInt("PARALLAX_LAB_SOURCE_READY_FINAL_ASSET_RETRIES", 3);
  const sourceReadyFinalWaitMs = readEnvInt("PARALLAX_LAB_SOURCE_READY_FINAL_WAIT_MS", 1200);
  await page.evaluate(() => {
    const api = window.vetkaParallaxLab;
    if (!api) throw new Error("vetkaParallaxLab API is unavailable");
    api.setPreviewMode("composite");
  });
  const readinessStartedAt = Date.now();
  let stageHydrateCalls = 0;
  let stageHydrateSuccesses = 0;
  let assetHydrateCalls = 0;
  let assetHydrateSuccesses = 0;
  let attempts = 0;
  let sourceReady = false;
  for (let index = 0; index < sourceReadyMaxPolls; index += 1) {
    attempts = index + 1;
    sourceReady = await page.evaluate(() => {
      const api = window.vetkaParallaxLab;
      if (!api) throw new Error("vetkaParallaxLab API is unavailable");
      return api.getState().sourceRasterReady;
    });
    if (sourceReady) break;
    stageHydrateCalls += 1;
    const stageHydrated = await page.evaluate(() => {
      const api = window.vetkaParallaxLab;
      if (!api) throw new Error("vetkaParallaxLab API is unavailable");
      return api.hydrateSourceRasterFromStage();
    });
    if (stageHydrated) stageHydrateSuccesses += 1;
    if (!stageHydrated && index % sourceReadyAssetEvery === sourceReadyAssetEvery - 1) {
      assetHydrateCalls += 1;
      await page.evaluate(async () => {
        const api = window.vetkaParallaxLab;
        if (!api) throw new Error("vetkaParallaxLab API is unavailable");
        return api.hydrateSourceRasterFromAsset();
      });
      assetHydrateSuccesses += 1;
    }
    await page.waitForTimeout(sourceReadyPollMs);
  }
  if (!sourceReady) {
    for (let retry = 0; retry < sourceReadyFinalAssetRetries; retry += 1) {
      assetHydrateCalls += 1;
      const finalHydrateOk = await page.evaluate(async () => {
        const api = window.vetkaParallaxLab;
        if (!api) throw new Error("vetkaParallaxLab API is unavailable");
        return api.hydrateSourceRasterFromAsset();
      });
      if (finalHydrateOk) assetHydrateSuccesses += 1;
      await page.waitForTimeout(sourceReadyFinalWaitMs);
      sourceReady = await page.evaluate(() => {
        const api = window.vetkaParallaxLab;
        if (!api) throw new Error("vetkaParallaxLab API is unavailable");
        return api.getState().sourceRasterReady;
      });
      if (sourceReady) break;
    }
  }
  const readinessDiagnostics = await page.evaluate(
    ({ sampleId }) => {
      const api = window.vetkaParallaxLab;
      if (!api) throw new Error("vetkaParallaxLab API is unavailable");
      return {
        sampleId,
        finalState: api.getState(),
        snapshot: api.snapshot(),
      };
    },
    { sampleId },
  );
  const readinessReport: SourceReadinessDiagnostics = {
    sampleId,
    ready: sourceReady,
    attempts,
    pollMs: sourceReadyPollMs,
    maxPolls: sourceReadyMaxPolls,
    stageHydrateCalls,
    stageHydrateSuccesses,
    assetHydrateCalls,
    assetHydrateSuccesses,
    elapsedMs: Date.now() - readinessStartedAt,
    finalState: readinessDiagnostics.finalState,
    snapshot: readinessDiagnostics.snapshot,
  };
  fs.writeFileSync(path.join(outputDir, "plate_export_readiness_diagnostics.json"), JSON.stringify(readinessReport, null, 2), "utf8");
  expect(sourceReady, `sourceRasterReady=false; see ${path.join(outputDir, "plate_export_readiness_diagnostics.json")}`).toBeTruthy();
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
  expect(result.assets.contract_version).toBe(CONTRACT_VERSION);
  expect(result.assets.layout.plates.length).toBeGreaterThan(0);
  validatePlateLayoutContract(result.assets.layout as Record<string, unknown>);

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

  const manifest = {
    contract_version: CONTRACT_VERSION,
    sampleId,
    files: {
      plateStack: "plate_stack.json",
      plateLayout: "plate_layout.json",
      jobState: "plate_export_job_state.json",
      snapshot: "plate_export_snapshot.json",
      readinessDiagnostics: "plate_export_readiness_diagnostics.json",
      compositeState: "plate_export_composite_state.json",
      depthState: "plate_export_depth_state.json",
      globalDepth: "global_depth_bw.png",
      backgroundRgba: "background_rgba.png",
      backgroundMask: "background_mask.png",
      compositeScreenshot: "plate_export_composite.png",
      depthScreenshot: "plate_export_depth.png",
    },
    exportedPlates,
  };
  validatePlateExportManifest(manifest as Record<string, unknown>);
  fs.writeFileSync(path.join(outputDir, "plate_export_manifest.json"), JSON.stringify(manifest, null, 2), "utf8");

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

test("qwen plate gate fixtures satisfy v1 contract", async () => {
  const gateDir = path.join(process.cwd(), "public", "qwen_plate_gates");
  const sampleIds = ["hover-politsia", "keyboard-hands", "truck-driver"];
  for (const sampleId of sampleIds) {
    const gate = JSON.parse(fs.readFileSync(path.join(gateDir, `${sampleId}.json`), "utf8")) as Record<string, unknown>;
    validateQwenPlateGateContract(gate, sampleId);
  }
});
