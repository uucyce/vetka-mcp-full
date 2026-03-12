import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { getAlgorithmicMattePreset } from "./algorithmic_matte_presets";

test("export manual hints and group boxes contracts", async ({ page }) => {
  const sampleId = process.env.PARALLAX_LAB_SAMPLE_ID || "cassette-closeup";
  const outputDir =
    process.env.PARALLAX_LAB_MANUAL_CONTRACT_DIR ||
    `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/manual_contracts/${sampleId}`;
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
      stageTool: "group",
      brushMode: "closer",
      hintStrokes: payload.brushGroup.hintStrokes.map((stroke: any, index: number) => ({
        id: `hint-${index}`,
        ...stroke,
      })),
      groupBoxes: payload.brushGroup.groupBoxes.map((box: any, index: number) => ({
        id: `group-${index}`,
        ...box,
      })),
      manual: {
        ...base.manual,
        previewMode: "selection",
      },
      matteSeeds: [],
    });

    await new Promise((resolve) => window.setTimeout(resolve, 200));

    const currentApi = window.vetkaParallaxLab;
    if (!currentApi) throw new Error("vetkaParallaxLab API was lost after manual contract updates");

    return {
      snapshot: currentApi.snapshot(),
      state: currentApi.getState(),
      jobState: currentApi.exportJobState(),
      manualHints: currentApi.exportManualHints(),
      groupBoxes: currentApi.exportGroupBoxes(),
      description: payload.description,
      note: payload.brushGroup.note,
    };
  }, preset);

  expect(result.manualHints.hintStrokes.length).toBeGreaterThan(0);
  expect(result.groupBoxes.groupBoxes.length).toBeGreaterThan(0);

  fs.writeFileSync(path.join(outputDir, "manual_hints.json"), JSON.stringify(result.manualHints, null, 2), "utf8");
  fs.writeFileSync(path.join(outputDir, "group_boxes.json"), JSON.stringify(result.groupBoxes, null, 2), "utf8");
  fs.writeFileSync(path.join(outputDir, "manual_contracts_job_state.json"), JSON.stringify(result.jobState, null, 2), "utf8");
  fs.writeFileSync(path.join(outputDir, "manual_contracts_snapshot.json"), JSON.stringify(result.snapshot, null, 2), "utf8");
  fs.writeFileSync(path.join(outputDir, "manual_contracts_state.json"), JSON.stringify(result.state, null, 2), "utf8");
  fs.writeFileSync(
    path.join(outputDir, "manual_contracts_manifest.json"),
    JSON.stringify(
      {
        sampleId,
        description: result.description,
        note: result.note,
        files: {
          manualHints: "manual_hints.json",
          groupBoxes: "group_boxes.json",
          jobState: "manual_contracts_job_state.json",
          snapshot: "manual_contracts_snapshot.json",
          state: "manual_contracts_state.json",
          screenshot: "manual_contracts_selection.png",
        },
      },
      null,
      2,
    ),
    "utf8",
  );

  await page.locator(".stage-shell").screenshot({
    path: path.join(outputDir, "manual_contracts_selection.png"),
  });
});
