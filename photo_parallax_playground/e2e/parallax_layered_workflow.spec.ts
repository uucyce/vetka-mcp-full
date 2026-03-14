import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import {
  DEFAULT_COMPARE_SAMPLE_IDS,
  getAlgorithmicMattePreset,
} from "./algorithmic_matte_presets";

function buildSampleIds() {
  const raw = process.env.PARALLAX_LAB_LAYERED_SAMPLE_IDS;
  if (!raw) return DEFAULT_COMPARE_SAMPLE_IDS;
  return raw
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

function writeDataUrlImage(targetPath: string, dataUrl: string) {
  const [, payload = ""] = dataUrl.split(",", 2);
  fs.writeFileSync(targetPath, Buffer.from(payload, "base64"));
}

test("export layered workflow bundle with hints groups matte and ai blend", async ({ page }) => {
  const sampleIds = buildSampleIds();
  const rootDir =
    process.env.PARALLAX_LAB_LAYERED_DIR ||
    "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow";

  fs.mkdirSync(rootDir, { recursive: true });
  await page.setViewportSize({ width: 1720, height: 1200 });

  const summary: {
    sampleId: string;
    aiSuggestionFound: boolean;
    layered: Record<string, unknown>;
    files: Record<string, string>;
  }[] = [];

  for (const sampleId of sampleIds) {
    const preset = getAlgorithmicMattePreset(sampleId);
    const sampleDir = path.join(rootDir, sampleId);
    fs.mkdirSync(sampleDir, { recursive: true });

    await page.goto(`/?sample=${sampleId}&debug=1`);
    await page.waitForFunction(() => Boolean(window.vetkaParallaxLab?.snapshot()?.ok));

    const result = await page.evaluate(async (payload) => {
      const api = window.vetkaParallaxLab;
      if (!api) throw new Error("vetkaParallaxLab API is unavailable");

      const base = api.exportJobState();
      api.importJobState({
        ...base,
        stageTool: "matte",
        brushMode: "closer",
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

      const currentApi = () => {
        const nextApi = window.vetkaParallaxLab;
        if (!nextApi) throw new Error("vetkaParallaxLab API became unavailable");
        return nextApi;
      };

      currentApi().importManualHints({
        sampleId: payload.sampleId,
        brushMode: "closer",
        brushSize: payload.brushGroup.hintStrokes[0]?.size ?? 0.03,
        hintStrokes: payload.brushGroup.hintStrokes.map((stroke: any, index: number) => ({
          id: `hint-${index}`,
          ...stroke,
        })),
      });

      currentApi().importGroupBoxes({
        sampleId: payload.sampleId,
        groupMode: "foreground-group",
        groupBoxes: payload.brushGroup.groupBoxes.map((box: any, index: number) => ({
          id: `group-${index}`,
          ...box,
        })),
      });

      currentApi().importAlgorithmicMatte({
        sampleId: payload.sampleId,
        matteSettings: {
          ...base.matteSettings,
          ...payload.matte.matteSettings,
        },
        matteSeeds: [],
      });
      currentApi().clearMatteSeeds();
      for (const seed of payload.matte.matteSeeds) {
        currentApi().appendMatteSeed(seed.x, seed.y, seed.mode);
      }

      await new Promise((resolve) => window.setTimeout(resolve, 250));

      const beforeAi = {
        state: currentApi().getState(),
        snapshot: currentApi().snapshot(),
        hints: currentApi().exportManualHints(),
        groups: currentApi().exportGroupBoxes(),
        matte: currentApi().exportAlgorithmicMatte(),
        proxyAssets: currentApi().exportProxyAssets(),
      };

      const aiGroupCount = currentApi().applyAiAssistSuggestion();
      await new Promise((resolve) => window.setTimeout(resolve, 250));

      const afterAi = {
        state: currentApi().getState(),
        snapshot: currentApi().snapshot(),
        jobState: currentApi().exportJobState(),
        hints: currentApi().exportManualHints(),
        groups: currentApi().exportGroupBoxes(),
        matte: currentApi().exportAlgorithmicMatte(),
        proxyAssets: currentApi().exportProxyAssets(),
      };

      return {
        description: payload.description,
        brushNote: payload.brushGroup.note,
        matteNote: payload.matte.note,
        aiGroupCount,
        beforeAi,
        afterAi,
      };
    }, preset);

    expect(result.afterAi.matte.matteSeeds.length).toBeGreaterThan(0);
    expect(result.afterAi.hints.hintStrokes.length).toBeGreaterThan(0);
    expect(result.afterAi.groups.groupBoxes.length).toBeGreaterThan(0);

    await page.locator(".stage-shell").screenshot({
      path: path.join(sampleDir, "layered_after_ai.png"),
    });

    await page.evaluate((payload) => {
      const api = window.vetkaParallaxLab;
      if (!api) throw new Error("vetkaParallaxLab API is unavailable");
      api.importManualHints(payload.beforeAi.hints);
      api.importGroupBoxes(payload.beforeAi.groups);
      api.importAlgorithmicMatte(payload.beforeAi.matte);
    }, { beforeAi: result.beforeAi });

    await page.waitForTimeout(200);

    await page.locator(".stage-shell").screenshot({
      path: path.join(sampleDir, "layered_before_ai.png"),
    });

    writeDataUrlImage(path.join(sampleDir, "selection_mask_before_ai.png"), result.beforeAi.proxyAssets.selectionMaskUrl);
    writeDataUrlImage(path.join(sampleDir, "selection_overlay_before_ai.png"), result.beforeAi.proxyAssets.overlayUrl);
    writeDataUrlImage(path.join(sampleDir, "depth_before_ai.png"), result.beforeAi.proxyAssets.depthUrl);
    writeDataUrlImage(path.join(sampleDir, "selection_mask_after_ai.png"), result.afterAi.proxyAssets.selectionMaskUrl);
    writeDataUrlImage(path.join(sampleDir, "selection_overlay_after_ai.png"), result.afterAi.proxyAssets.overlayUrl);
    writeDataUrlImage(path.join(sampleDir, "depth_after_ai.png"), result.afterAi.proxyAssets.depthUrl);

    fs.writeFileSync(path.join(sampleDir, "manual_hints.json"), JSON.stringify(result.afterAi.hints, null, 2), "utf8");
    fs.writeFileSync(path.join(sampleDir, "group_boxes.json"), JSON.stringify(result.afterAi.groups, null, 2), "utf8");
    fs.writeFileSync(path.join(sampleDir, "algorithmic_matte.json"), JSON.stringify(result.afterAi.matte, null, 2), "utf8");
    fs.writeFileSync(path.join(sampleDir, "layered_job_state.json"), JSON.stringify(result.afterAi.jobState, null, 2), "utf8");
    fs.writeFileSync(path.join(sampleDir, "layered_before_ai.json"), JSON.stringify(result.beforeAi, null, 2), "utf8");
    fs.writeFileSync(path.join(sampleDir, "layered_after_ai.json"), JSON.stringify(result.afterAi, null, 2), "utf8");

    const selectionCoverageDelta = Number(
      (result.afterAi.state.selectionCoverage - result.beforeAi.state.selectionCoverage).toFixed(4),
    );
    const midgroundCoverageDelta = Number(
      (result.afterAi.state.midgroundCoverage - result.beforeAi.state.midgroundCoverage).toFixed(4),
    );
    const decision =
      result.aiGroupCount <= 0
        ? "keep-manual"
        : selectionCoverageDelta < -0.05
          ? "reject"
          : Math.abs(selectionCoverageDelta) <= 0.05
            ? "accept"
            : "keep-manual";
    const decisionReason =
      result.aiGroupCount <= 0
        ? "No AI groups were added."
        : selectionCoverageDelta < -0.05
          ? "AI blend shrank selection coverage too aggressively."
          : Math.abs(selectionCoverageDelta) <= 0.05
            ? "AI blend stayed within the safe coverage delta window."
            : "AI blend expanded coverage beyond the current safe window.";

    const record = {
      sampleId,
      aiSuggestionFound: result.aiGroupCount > 0,
      description: result.description,
      brushNote: result.brushNote,
      matteNote: result.matteNote,
      layered: {
        aiGroupCount: result.aiGroupCount,
        selectionCoverageBeforeAi: result.beforeAi.state.selectionCoverage,
        selectionCoverageAfterAi: result.afterAi.state.selectionCoverage,
        selectionCoverageDelta,
        midgroundCoverageBeforeAi: result.beforeAi.state.midgroundCoverage,
        midgroundCoverageAfterAi: result.afterAi.state.midgroundCoverage,
        midgroundCoverageDelta,
        groupBoxCountBeforeAi: result.beforeAi.state.groupBoxCount,
        groupBoxCountAfterAi: result.afterAi.state.groupBoxCount,
        hintStrokeCountAfterAi: result.afterAi.state.hintStrokeCount,
        matteSeedCountAfterAi: result.afterAi.state.matteSeedCount,
        aiCompareMode: result.afterAi.state.aiCompareMode,
        gateDecision: decision,
        gateReason: decisionReason,
      },
      files: {
        beforeAiScreenshot: path.join(sampleDir, "layered_before_ai.png"),
        afterAiScreenshot: path.join(sampleDir, "layered_after_ai.png"),
        beforeAiMask: path.join(sampleDir, "selection_mask_before_ai.png"),
        afterAiMask: path.join(sampleDir, "selection_mask_after_ai.png"),
        hints: path.join(sampleDir, "manual_hints.json"),
        groups: path.join(sampleDir, "group_boxes.json"),
        matte: path.join(sampleDir, "algorithmic_matte.json"),
        jobState: path.join(sampleDir, "layered_job_state.json"),
      },
    };

    fs.writeFileSync(path.join(sampleDir, "layered_summary.json"), JSON.stringify(record, null, 2), "utf8");
    summary.push(record);
  }

  fs.writeFileSync(path.join(rootDir, "layered_edit_flow_summary.json"), JSON.stringify(summary, null, 2), "utf8");
});
