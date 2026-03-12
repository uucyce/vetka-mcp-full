const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_EXPORT_FAILURE_PORT || 4176);
const DEV_ORIGIN = `http://127.0.0.1:${DEV_PORT}`;
const IDLE_COLOR = 'rgb(204, 204, 204)';
const ERROR_COLOR = 'rgb(239, 68, 68)';

let serverProcess = null;
let serverStartedBySpec = false;
let serverLogs = '';

function waitForHttpOk(url, timeoutMs = 30000) {
  const startedAt = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(url, (res) => {
        res.resume();
        if ((res.statusCode || 0) < 500) {
          resolve();
          return;
        }
        retry();
      });
      req.on('error', retry);
    };

    const retry = () => {
      if (Date.now() - startedAt >= timeoutMs) {
        reject(new Error(`Timed out waiting for ${url}\n${serverLogs}`));
        return;
      }
      setTimeout(tick, 200);
    };

    tick();
  });
}

async function ensureDevServer() {
  try {
    await waitForHttpOk(DEV_ORIGIN, 1500);
    return;
  } catch {
    // Start local server below.
  }

  serverStartedBySpec = true;
  serverProcess = spawn(
    'npm',
    ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(DEV_PORT)],
    {
      cwd: CLIENT_DIR,
      env: { ...process.env, BROWSER: 'none', CI: '1' },
      stdio: ['ignore', 'pipe', 'pipe'],
    }
  );

  const capture = (chunk) => {
    serverLogs += chunk.toString();
    if (serverLogs.length > 20000) {
      serverLogs = serverLogs.slice(-20000);
    }
  };
  serverProcess.stdout.on('data', capture);
  serverProcess.stderr.on('data', capture);

  await waitForHttpOk(DEV_ORIGIN, 30000);
}

function cleanupServer() {
  if (serverProcess && serverStartedBySpec) {
    serverProcess.kill('SIGTERM');
    serverProcess = null;
  }
}

async function installCutExportFailureMocks(page, calls) {
  await page.route(`${DEV_ORIGIN}/api/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (url.pathname === '/api/cut/project-state') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          runtime_ready: false,
          project: {
            project_id: 'proj_export_failure_smoke',
            project_name: 'Export Failure Smoke Demo',
          },
          timeline_state: {
            timeline_id: 'main',
            lanes: [],
            selection: { clip_ids: [], scene_ids: [] },
          },
          waveform_bundle: { items: [] },
          thumbnail_bundle: { items: [] },
          transcript_bundle: { items: [] },
          audio_sync_result: null,
          timecode_sync_result: null,
          sync_surface: { schema_version: 'cut_sync_surface_v1', items: [] },
          time_marker_bundle: { items: [] },
          recent_jobs: [],
          active_jobs: [],
        }),
      });
      return;
    }

    if (url.pathname === '/api/cut/export/premiere-xml') {
      calls.push({ endpoint: 'premiere-xml', body: request.postDataJSON() });
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          error: { message: 'Premiere export blocked in smoke failure path' },
        }),
      });
      return;
    }

    if (url.pathname === '/api/cut/export/fcpxml') {
      calls.push({ endpoint: 'fcpxml', body: request.postDataJSON() });
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          error: { message: 'FCPXML export blocked in smoke failure path' },
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: '{}',
    });
  });
}

async function getColor(locator) {
  return locator.evaluate((node) => window.getComputedStyle(node).color);
}

test.describe.serial('phase170 cut export failure smoke', () => {
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('premiere export failure still routes to premiere endpoint and shows red error state', async ({ page }) => {
    const calls = [];
    const pageErrors = [];
    await installCutExportFailureMocks(page, calls);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.goto(
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('proj_export_failure_smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    const exportToggle = page.getByTitle('Click to switch export format');
    const exportButton = page.locator('button[title^="Export to "]');

    await expect(exportToggle).toHaveText('PPro');
    await expect(await getColor(exportButton)).toBe(IDLE_COLOR);

    await exportButton.click();

    await expect.poll(() => calls.length).toBe(1);
    await expect.poll(() => calls[0]?.endpoint).toBe('premiere-xml');
    await expect.poll(() => calls[0]?.body?.project_id).toBe('proj_export_failure_smoke');
    await expect.poll(() => getColor(exportButton)).toBe(ERROR_COLOR);
    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
  });

  test('fcpxml export failure follows toggle and resets back to idle color', async ({ page }) => {
    const calls = [];
    const pageErrors = [];
    await installCutExportFailureMocks(page, calls);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.goto(
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('proj_export_failure_smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    const exportToggle = page.getByTitle('Click to switch export format');
    const exportButton = page.locator('button[title^="Export to "]');

    await exportToggle.click();
    await expect(exportToggle).toHaveText('FCP/DR');
    await expect(exportButton).toHaveAttribute('title', /FCPXML/);

    await exportButton.click();

    await expect.poll(() => calls.length).toBe(1);
    await expect.poll(() => calls[0]?.endpoint).toBe('fcpxml');
    await expect.poll(() => calls[0]?.body?.sandbox_root).toBe('/tmp/cut-smoke');
    await expect.poll(() => getColor(exportButton)).toBe(ERROR_COLOR);
    await expect.poll(() => getColor(exportButton), { timeout: 4500 }).toBe(IDLE_COLOR);
    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
  });
});
