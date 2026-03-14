import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import {
  DEFAULT_COMPARE_SAMPLE_IDS,
  getAlgorithmicMattePreset,
} from "./algorithmic_matte_presets";

function buildSampleIds() {
  const raw = process.env.PARALLAX_LAB_COMPARE_SAMPLE_IDS;
  if (!raw) return DEFAULT_COMPARE_SAMPLE_IDS;
  return raw
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

test("compare algorithmic matte against brush and group presets", async ({ page }) => {
  const sampleIds = buildSampleIds();
  const rootDir =
    process.env.PARALLAX_LAB_MATTE_COMPARE_DIR ||
    "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/algorithmic_matte_compare";

  fs.mkdirSync(rootDir, { recursive: true });
  await page.setViewportSize({ width: 1720, height: 1200 });

  const summary: {
    sampleId: string;
    description: string;
    brushGroup: Record<string, unknown>;
    algorithmicMatte: Record<string, unknown>;
    deltas: Record<string, number>;
    files: Record<string, string>;
  }[] = [];

  for (const sampleId of sampleIds) {
    const preset = getAlgorithmicMattePreset(sampleId);
    const sampleDir = path.join(rootDir, sampleId);
    fs.mkdirSync(sampleDir, { recursive: true });

    await page.goto(`/?sample=${sampleId}&debug=1`);
    await page.waitForFunction(() => Boolean(window.vetkaParallaxLab?.snapshot()?.ok));

    const brushGroupResult = await page.evaluate(async (payload) => {
      const api = window.vetkaParallaxLab;
      if (!api) throw new Error("vetkaParallaxLab API is unavailable");

      const base = api.exportJobState();
      api.importJobState({
        ...base,
        stageTool: "group",
        matteSeedMode: "add",
        hintStrokes: payload.brushGroup.hintStrokes.map((stroke: any, index: number) => ({
          id: `brush-${index}`,
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
      if (!currentApi) throw new Error("vetkaParallaxLab API was lost after brush/group updates");

      return {
        state: currentApi.getState(),
        snapshot: currentApi.snapshot(),
        jobState: currentApi.exportJobState(),
        note: payload.brushGroup.note,
      };
    }, preset);

    await page.locator(".stage-shell").screenshot({
      path: path.join(sampleDir, "brush_group_selection.png"),
    });

    const matteResult = await page.evaluate(async (payload) => {
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
        state: currentApi.getState(),
        snapshot: currentApi.snapshot(),
        contract: currentApi.exportAlgorithmicMatte(),
        jobState: currentApi.exportJobState(),
        note: payload.matte.note,
      };
    }, preset);

    await page.locator(".stage-shell").screenshot({
      path: path.join(sampleDir, "algorithmic_matte_selection.png"),
    });

    expect(matteResult.contract.matteSeeds.length).toBeGreaterThan(0);

    fs.writeFileSync(path.join(sampleDir, "brush_group_job_state.json"), JSON.stringify(brushGroupResult.jobState, null, 2), "utf8");
    fs.writeFileSync(path.join(sampleDir, "brush_group_state.json"), JSON.stringify(brushGroupResult.state, null, 2), "utf8");
    fs.writeFileSync(path.join(sampleDir, "brush_group_snapshot.json"), JSON.stringify(brushGroupResult.snapshot, null, 2), "utf8");

    fs.writeFileSync(path.join(sampleDir, "algorithmic_matte.json"), JSON.stringify(matteResult.contract, null, 2), "utf8");
    fs.writeFileSync(path.join(sampleDir, "algorithmic_matte_job_state.json"), JSON.stringify(matteResult.jobState, null, 2), "utf8");
    fs.writeFileSync(path.join(sampleDir, "algorithmic_matte_state.json"), JSON.stringify(matteResult.state, null, 2), "utf8");
    fs.writeFileSync(path.join(sampleDir, "algorithmic_matte_snapshot.json"), JSON.stringify(matteResult.snapshot, null, 2), "utf8");

    const selectionCoverageDelta = Number(
      ((matteResult.state.selectionCoverage as number) - (brushGroupResult.state.selectionCoverage as number)).toFixed(4),
    );
    const midgroundCoverageDelta = Number(
      ((matteResult.state.midgroundCoverage as number) - (brushGroupResult.state.midgroundCoverage as number)).toFixed(4),
    );
    const matteCoverageDelta = Number(
      ((matteResult.state.matteCoverage as number) - (brushGroupResult.state.matteCoverage as number)).toFixed(4),
    );

    const record = {
      sampleId,
      description: preset.description,
      brushGroup: {
        note: brushGroupResult.note,
        selectionCoverage: brushGroupResult.state.selectionCoverage,
        midgroundCoverage: brushGroupResult.state.midgroundCoverage,
        matteCoverage: brushGroupResult.state.matteCoverage,
        hintStrokeCount: brushGroupResult.state.hintStrokeCount,
        groupBoxCount: brushGroupResult.state.groupBoxCount,
      },
      algorithmicMatte: {
        note: matteResult.note,
        selectionCoverage: matteResult.state.selectionCoverage,
        midgroundCoverage: matteResult.state.midgroundCoverage,
        matteCoverage: matteResult.state.matteCoverage,
        matteSeedCount: matteResult.state.matteSeedCount,
      },
      deltas: {
        selectionCoverageDelta,
        midgroundCoverageDelta,
        matteCoverageDelta,
      },
      files: {
        brushGroupPng: path.join(sampleDir, "brush_group_selection.png"),
        algorithmicMattePng: path.join(sampleDir, "algorithmic_matte_selection.png"),
        algorithmicMatteJson: path.join(sampleDir, "algorithmic_matte.json"),
      },
    };

    fs.writeFileSync(path.join(sampleDir, "compare_summary.json"), JSON.stringify(record, null, 2), "utf8");
    summary.push(record);
  }

  fs.writeFileSync(path.join(rootDir, "algorithmic_matte_compare_summary.json"), JSON.stringify(summary, null, 2), "utf8");
});
