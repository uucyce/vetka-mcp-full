import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { getAlgorithmicMattePreset } from "./algorithmic_matte_presets";

test("export algorithmic matte contract", async ({ page }) => {
  const sampleId = process.env.PARALLAX_LAB_SAMPLE_ID || "cassette-closeup";
  const outputDir =
    process.env.PARALLAX_LAB_MATTE_CONTRACT_DIR ||
    `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/algorithmic_matte_contract/${sampleId}`;
  const preset = getAlgorithmicMattePreset(sampleId);

  fs.mkdirSync(outputDir, { recursive: true });

  await page.setViewportSize({ width: 1720, height: 1200 });
  await page.goto(`/?sample=${sampleId}&debug=1`);
  await page.waitForFunction(() => Boolean(window.vetkaParallaxLab?.snapshot()?.ok));

  const result = await page.evaluate(async (payload) => {
    const api = window.vetkaParallaxLab;
    if (!api) throw new Error("vetkaParallaxLab API is unavailable");

    const base = api.exportJobState();
    api.importJobState({
      ...base,
      stageTool: "matte",
      matteSeedMode: "add",
      hintStrokes: [],
      groupBoxes: [],
      manual: {
        ...base.manual,
        previewMode: "selection",
      },
      matteSettings: {
        ...base.matteSettings,
        ...payload.matte.matteSettings,
      },
      matteSeeds: [],
    });

    api.clearMatteSeeds();
    for (const seed of payload.matte.matteSeeds) {
      api.appendMatteSeed(seed.x, seed.y, seed.mode);
    }

    await new Promise((resolve) => window.setTimeout(resolve, 200));

    const currentApi = window.vetkaParallaxLab;
    if (!currentApi) throw new Error("vetkaParallaxLab API was lost after matte updates");

    return {
      snapshot: currentApi.snapshot(),
      state: currentApi.getState(),
      contract: currentApi.exportAlgorithmicMatte(),
      jobState: currentApi.exportJobState(),
      description: payload.description,
      note: payload.matte.note,
    };
  }, preset);

  expect(result.contract.sampleId).toBe(sampleId);
  expect(result.contract.matteSeeds.length).toBeGreaterThan(0);

  fs.writeFileSync(path.join(outputDir, "algorithmic_matte.json"), JSON.stringify(result.contract, null, 2), "utf8");
  fs.writeFileSync(path.join(outputDir, "algorithmic_matte_job_state.json"), JSON.stringify(result.jobState, null, 2), "utf8");
  fs.writeFileSync(path.join(outputDir, "algorithmic_matte_snapshot.json"), JSON.stringify(result.snapshot, null, 2), "utf8");
  fs.writeFileSync(path.join(outputDir, "algorithmic_matte_state.json"), JSON.stringify(result.state, null, 2), "utf8");
  fs.writeFileSync(
    path.join(outputDir, "algorithmic_matte_manifest.json"),
    JSON.stringify(
      {
        sampleId,
        description: result.description,
        note: result.note,
        files: {
          contract: "algorithmic_matte.json",
          jobState: "algorithmic_matte_job_state.json",
          snapshot: "algorithmic_matte_snapshot.json",
          state: "algorithmic_matte_state.json",
          screenshot: "algorithmic_matte_selection.png",
        },
      },
      null,
      2,
    ),
    "utf8",
  );

  await page.locator(".stage-shell").screenshot({
    path: path.join(outputDir, "algorithmic_matte_selection.png"),
  });
});
