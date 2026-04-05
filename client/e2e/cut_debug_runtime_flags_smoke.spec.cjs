const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_DEBUG_FLAGS_PORT || 4183);
const DEV_ORIGIN = `http://127.0.0.1:${DEV_PORT}`;

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

function createProjectState(overrides = {}) {
  return {
    success: true,
    schema_version: 'cut_project_state_v1',
    project: {
      project_id: 'proj_flags_smoke',
      display_name: 'CUT Runtime Flags Smoke',
      source_path: '/tmp/cut/runtime_flags_source.mov',
      sandbox_root: '/tmp/cut-smoke',
      state: 'ready',
    },
    bootstrap_state: { last_stats: {} },
    timeline_state: { timeline_id: 'main', selection: { clip_ids: [], scene_ids: [] }, lanes: [] },
    scene_graph: { nodes: [] },
    waveform_bundle: { items: [] },
    transcript_bundle: { items: [] },
    thumbnail_bundle: { items: [] },
    audio_sync_result: { items: [] },
    slice_bundle: { items: [] },
    timecode_sync_result: { items: [] },
    sync_surface: { schema_version: 'cut_sync_surface_v1', items: [] },
    time_marker_bundle: { items: [] },
    recent_jobs: [],
    active_jobs: [],
    runtime_ready: false,
    graph_ready: true,
    waveform_ready: false,
    transcript_ready: true,
    thumbnail_ready: false,
    audio_sync_ready: true,
    slice_ready: false,
    timecode_sync_ready: true,
    sync_surface_ready: false,
    meta_sync_ready: false,
    time_markers_ready: true,
    ...overrides,
  };
}

async function installRuntimeFlagMocks(page, requestLog) {
  const first = createProjectState();
  const second = createProjectState({
      project: {
        project_id: 'proj_flags_smoke',
        display_name: 'CUT Runtime Flags Smoke v2',
        source_path: '/tmp/cut/runtime_flags_source_v2.mov',
        sandbox_root: '/tmp/cut-smoke',
        state: 'ready',
      },
      runtime_ready: true,
      graph_ready: true,
      waveform_ready: true,
      transcript_ready: false,
      thumbnail_ready: true,
      audio_sync_ready: false,
      slice_ready: true,
      timecode_sync_ready: false,
      sync_surface_ready: true,
      meta_sync_ready: true,
      time_markers_ready: false,
    });
  const snapshots = [first, first, second, second];
  let index = 0;

  await page.route(`${DEV_ORIGIN}/api/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    requestLog.push({ method: request.method(), pathname: url.pathname });

    if (url.pathname === '/api/cut/project-state') {
      const payload = snapshots[Math.min(index, snapshots.length - 1)];
      index += 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(payload),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true }),
    });
  });
}

test.describe.serial('phase170 cut debug runtime flags smoke', () => {
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('renders project overview and runtime flags, then updates after refresh', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    await installRuntimeFlagMocks(page, requestLog);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('proj_flags_smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByText('Source Browser').first()).toBeVisible();
    await page.locator('button[title="Toggle NLE / Debug view"]').click();
    await expect(page.getByText('VETKA CUT')).toBeVisible();
    await expect(page.getByText('Project Overview')).toBeVisible();
    await expect(page.getByText('CUT Runtime Flags Smoke')).toBeVisible();
    await expect(page.getByText('Runtime Flags', { exact: true })).toBeVisible();
    await expect(page.getByText('runtime_ready: false')).toBeVisible();
    await expect(page.getByText('graph_ready: true')).toBeVisible();
    await expect(page.getByText('waveform_ready: false')).toBeVisible();
    await expect(page.getByText('audio_sync_ready: true')).toBeVisible();
    await expect(page.getByText('time_markers_ready: true')).toBeVisible();

    await page.getByRole('button', { name: 'Refresh Project State' }).click();
    await expect.poll(() => requestLog.filter((entry) => entry.pathname === '/api/cut/project-state').length).toBeGreaterThan(1);
    await expect(page.getByText('CUT Runtime Flags Smoke v2')).toBeVisible();
    await expect(page.getByText('runtime_ready: true')).toBeVisible();
    await expect(page.getByText('waveform_ready: true')).toBeVisible();
    await expect(page.getByText('transcript_ready: false')).toBeVisible();
    await expect(page.getByText('slice_ready: true')).toBeVisible();
    await expect(page.getByText('sync_surface_ready: true')).toBeVisible();
    await expect(page.getByText('meta_sync_ready: true')).toBeVisible();
    await expect(page.getByText('time_markers_ready: false')).toBeVisible();

    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
    expect(await page.evaluate(() => window.localStorage.getItem('vetka_last_runtime_error'))).toBeNull();
  });
});
