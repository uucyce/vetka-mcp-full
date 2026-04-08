#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { chromium } from "@playwright/test";

const DEFAULT_HOST = "127.0.0.1";
const DEFAULT_PORT = 1434;
const DEFAULT_TIMEOUT_MS = 60_000;
const CONTRACT_VERSION = "1.0.0";
const REAL_DEPTH_BACKEND = "depth-pro";

function printHelp() {
  console.log(`Usage:
  node scripts/parallax_depth_export.mjs --sample <sample-id> [--output <dir>] [--base-url <url>]

Options:
  --sample <id>        Sample id from public/samples (required)
  --output <dir>       Output directory. Default: output/depth_exports/<sample-id>
  --base-url <url>     Existing app URL. Default: http://${DEFAULT_HOST}:${DEFAULT_PORT}
  --host <host>        Dev server host when auto-starting. Default: ${DEFAULT_HOST}
  --port <port>        Dev server port when auto-starting. Default: ${DEFAULT_PORT}
  --timeout-ms <ms>    Readiness timeout. Default: ${DEFAULT_TIMEOUT_MS}
  --keep-server        Keep auto-started Vite server alive after export
  --help               Show this message
`);
}

function parseArgs(argv) {
  const parsed = {
    sampleId: "",
    outputDir: "",
    baseUrl: "",
    host: DEFAULT_HOST,
    port: DEFAULT_PORT,
    timeoutMs: DEFAULT_TIMEOUT_MS,
    keepServer: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--help") {
      printHelp();
      process.exit(0);
    }
    if (arg === "--keep-server") {
      parsed.keepServer = true;
      continue;
    }
    const next = argv[index + 1];
    if (arg === "--sample" && next) {
      parsed.sampleId = next;
      index += 1;
      continue;
    }
    if (arg === "--output" && next) {
      parsed.outputDir = next;
      index += 1;
      continue;
    }
    if (arg === "--base-url" && next) {
      parsed.baseUrl = next;
      index += 1;
      continue;
    }
    if (arg === "--host" && next) {
      parsed.host = next;
      index += 1;
      continue;
    }
    if (arg === "--port" && next) {
      parsed.port = Number.parseInt(next, 10);
      index += 1;
      continue;
    }
    if (arg === "--timeout-ms" && next) {
      parsed.timeoutMs = Number.parseInt(next, 10);
      index += 1;
      continue;
    }
    throw new Error(`Unknown or incomplete argument: ${arg}`);
  }

  if (!parsed.sampleId) {
    throw new Error("--sample is required");
  }
  if (!Number.isFinite(parsed.port) || parsed.port <= 0) {
    throw new Error("--port must be a positive integer");
  }
  if (!Number.isFinite(parsed.timeoutMs) || parsed.timeoutMs <= 0) {
    throw new Error("--timeout-ms must be a positive integer");
  }

  parsed.baseUrl ||= `http://${parsed.host}:${parsed.port}`;
  parsed.outputDir ||= path.resolve(process.cwd(), "output", "depth_exports", parsed.sampleId);
  return parsed;
}

async function isServerReady(baseUrl) {
  try {
    const response = await fetch(baseUrl, { method: "GET" });
    return response.ok;
  } catch {
    return false;
  }
}

async function waitForServer(baseUrl, timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    if (await isServerReady(baseUrl)) return true;
    await delay(300);
  }
  return false;
}

function startDevServer({ host, cwd }) {
  const child = spawn("npm", ["run", "dev", "--", "--host", host], {
    cwd,
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env },
  });
  child.stdout?.on("data", () => {});
  child.stderr?.on("data", () => {});
  return child;
}

function decodeDataUrl(dataUrl) {
  const prefix = "data:image/png;base64,";
  if (!dataUrl || !dataUrl.startsWith(prefix)) {
    throw new Error("Expected PNG data URL");
  }
  return Buffer.from(dataUrl.slice(prefix.length), "base64");
}

async function exportDepth({
  sampleId,
  outputDir,
  baseUrl,
  timeoutMs,
}) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1720, height: 1200 } });
  const output = path.resolve(outputDir);
  fs.mkdirSync(output, { recursive: true });

  try {
    await page.goto(`${baseUrl}/?sample=${encodeURIComponent(sampleId)}&debug=1`, {
      waitUntil: "networkidle",
      timeout: timeoutMs,
    });
    await page.waitForFunction(() => Boolean(window.vetkaParallaxLab?.snapshot()?.ok), {
      timeout: timeoutMs,
    });

    const readinessStartedAt = Date.now();
    let attempts = 0;
    let sourceReady = false;
    let stageHydrateCalls = 0;
    let stageHydrateSuccesses = 0;
    let assetHydrateCalls = 0;
    let assetHydrateSuccesses = 0;

    while (Date.now() - readinessStartedAt < timeoutMs) {
      attempts += 1;
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
      if (stageHydrated) {
        stageHydrateSuccesses += 1;
      } else {
        assetHydrateCalls += 1;
        const assetHydrated = await page.evaluate(async () => {
          const api = window.vetkaParallaxLab;
          if (!api) throw new Error("vetkaParallaxLab API is unavailable");
          return api.hydrateSourceRasterFromAsset();
        });
        if (assetHydrated) assetHydrateSuccesses += 1;
      }
      await delay(250);
    }

    if (!sourceReady) {
      throw new Error(`sourceRasterReady=false after ${attempts} attempts`);
    }

    const realDepthPath = path.resolve(
      process.cwd(),
      "public",
      "depth_bakeoff",
      REAL_DEPTH_BACKEND,
      sampleId,
      "depth_preview.png",
    );
    const realDepthAssetExists = fs.existsSync(realDepthPath);
    let waitedForRealDepth = false;
    let realDepthReady = false;
    if (realDepthAssetExists) {
      waitedForRealDepth = true;
      try {
        await page.waitForFunction(() => Boolean(window.vetkaParallaxLab?.snapshot()?.usingRealDepth), {
          timeout: Math.min(timeoutMs, 5_000),
        });
        realDepthReady = true;
      } catch {
        realDepthReady = false;
      }
    }

    const result = await page.evaluate(async () => {
      const api = window.vetkaParallaxLab;
      if (!api) throw new Error("vetkaParallaxLab API is unavailable");
      api.setPreviewMode("depth");
      await new Promise((resolve) => window.setTimeout(resolve, 120));
      return {
        snapshot: api.snapshot(),
        state: api.getState(),
        jobState: api.exportJobState(),
        assets: api.exportPlateAssets(),
      };
    });

    const screenshotPath = path.join(output, "depth_export_preview.png");
    await page.locator(".stage-shell").screenshot({ path: screenshotPath });

    const manifest = {
      contract_version: CONTRACT_VERSION,
      sampleId,
      generatedAt: new Date().toISOString(),
      files: {
        depthPng: "global_depth_bw.png",
        previewPng: "depth_export_preview.png",
        manifest: "depth_export_manifest.json",
        state: "depth_export_state.json",
        snapshot: "depth_export_snapshot.json",
        jobState: "depth_export_job_state.json",
        readiness: "depth_export_readiness.json",
      },
      depth: {
        sourceUrl: result.assets.sourceUrl,
        depthFile: "global_depth_bw.png",
        usingRealDepth: Boolean(result.snapshot.usingRealDepth),
        realDepthAssetExists,
        waitedForRealDepth,
        realDepthReady,
      },
    };

    fs.writeFileSync(path.join(output, "global_depth_bw.png"), decodeDataUrl(result.assets.globalDepthUrl));
    fs.writeFileSync(path.join(output, "depth_export_manifest.json"), JSON.stringify(manifest, null, 2));
    fs.writeFileSync(path.join(output, "depth_export_state.json"), JSON.stringify(result.state, null, 2));
    fs.writeFileSync(path.join(output, "depth_export_snapshot.json"), JSON.stringify(result.snapshot, null, 2));
    fs.writeFileSync(path.join(output, "depth_export_job_state.json"), JSON.stringify(result.jobState, null, 2));
    fs.writeFileSync(
      path.join(output, "depth_export_readiness.json"),
      JSON.stringify(
        {
          sampleId,
          ready: sourceReady,
          attempts,
          elapsedMs: Date.now() - readinessStartedAt,
          stageHydrateCalls,
          stageHydrateSuccesses,
          assetHydrateCalls,
          assetHydrateSuccesses,
        },
        null,
        2,
      ),
    );

    return { output, manifest };
  } finally {
    await browser.close();
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  let server = null;
  let startedServer = false;

  try {
    const ready = await isServerReady(args.baseUrl);
    if (!ready) {
      server = startDevServer({ host: args.host, cwd: process.cwd() });
      startedServer = true;
      const serverReady = await waitForServer(args.baseUrl, args.timeoutMs);
      if (!serverReady) {
        throw new Error(`Timed out waiting for dev server at ${args.baseUrl}`);
      }
    }

    const result = await exportDepth(args);
    console.log(
      JSON.stringify(
        {
          ok: true,
          sampleId: args.sampleId,
          outputDir: result.output,
          manifest: path.join(result.output, "depth_export_manifest.json"),
        },
        null,
        2,
      ),
    );
  } finally {
    if (server && startedServer && !args.keepServer) {
      server.kill("SIGTERM");
    }
  }
}

main().catch((error) => {
  console.error(
    JSON.stringify(
      {
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      },
      null,
      2,
    ),
  );
  process.exit(1);
});
