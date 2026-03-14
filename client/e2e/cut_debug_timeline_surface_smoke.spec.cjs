const { test, expect } = require('@playwright/test');
const http = require('http');
const net = require('net');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
let DEV_PORT = Number(process.env.VETKA_CUT_DEBUG_TIMELINE_SURFACE_PORT || 4188);
const getDevOrigin = () => `http://127.0.0.1:${DEV_PORT}`;

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
        reject(new Error(`Timed out waiting for ${url}
${serverLogs}`));
        return;
      }
      setTimeout(tick, 200);
    };

    tick();
  });
}

function findAvailablePort(startPort) {
  return new Promise((resolve, reject) => {
    const tryPort = (port, attemptsLeft) => {
      const server = net.createServer();
      server.unref();
      server.on('error', () => {
        if (attemptsLeft <= 0) {
          reject(new Error(`Unable to find free port near ${startPort}`));
          return;
        }
        tryPort(port + 1, attemptsLeft - 1);
      });
      server.listen(port, '127.0.0.1', () => {
        const address = server.address();
        const freePort = typeof address === 'object' && address ? address.port : port;
        server.close(() => resolve(freePort));
      });
    };
    tryPort(startPort, 20);
  });
}

async function ensureDevServer() {
  try {
    await waitForHttpOk(getDevOrigin(), 1500);
    return;
  } catch {
    // Start local server below.
  }

  DEV_PORT = await findAvailablePort(DEV_PORT);

  serverStartedBySpec = true;
  serverProcess = spawn(
    'npm',
    ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(DEV_PORT), '--strictPort'],
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

  await waitForHttpOk(getDevOrigin(), 30000);
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
      project_id: 'proj_timeline_surface_smoke',
      display_name: 'CUT Timeline Surface Smoke',
      source_path: '/tmp/cut/source.mov',
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
    graph_ready: false,
    waveform_ready: false,
    transcript_ready: false,
    thumbnail_ready: false,
    audio_sync_ready: false,
    slice_ready: false,
    timecode_sync_ready: false,
    sync_surface_ready: false,
    meta_sync_ready: false,
    time_markers_ready: false,
    ...overrides,
  };
}

async function installTimelineSurfaceMocks(page, requestLog, timelineBodies) {
  const first = createProjectState();
  const hydrated = createProjectState({
    timeline_state: {
      timeline_id: 'main',
      selection: { clip_ids: [], scene_ids: [] },
      lanes: [
        {
          lane_id: 'v1',
          lane_type: 'video',
          clips: [
            { clip_id: 'clip_v1_a', source_path: '/tmp/cut/clip_v1_a.mov', start_sec: 0, duration_sec: 4 },
            { clip_id: 'clip_v1_b', source_path: '/tmp/cut/clip_v1_b.mov', start_sec: 4.5, duration_sec: 3.5 },
          ],
        },
        {
          lane_id: 'a1',
          lane_type: 'audio',
          clips: [
            { clip_id: 'clip_a1_a', source_path: '/tmp/cut/clip_a1_a.wav', start_sec: 0, duration_sec: 8 },
          ],
        },
      ],
    },
    runtime_ready: true,
  });
  let selectionClipIds = [];

  await page.route(`${getDevOrigin()}/api/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    requestLog.push({ method: request.method(), pathname: url.pathname });

    if (url.pathname === '/api/cut/project-state') {
      const payload = requestLog.filter((entry) => entry.pathname === '/api/cut/project-state').length <= 2
        ? first
        : createProjectState({
            ...hydrated,
            timeline_state: {
              ...hydrated.timeline_state,
              selection: { clip_ids: selectionClipIds, scene_ids: selectionClipIds.length ? ['scene_01'] : [] },
            },
          });
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(payload),
      });
      return;
    }

    if (url.pathname === '/api/cut/timeline/apply') {
      const body = JSON.parse(request.postData() || '{}');
      timelineBodies.push(body);
      const selectionOp = (body.ops || []).find((op) => op.op === 'set_selection');
      selectionClipIds = Array.isArray(selectionOp?.clip_ids) ? selectionOp.clip_ids : [];
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
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

test.describe.serial('phase170 cut debug timeline surface smoke', () => {
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('renders timeline empty state, then hydrates lanes and selection after Select First Clip', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    const timelineBodies = [];
    await installTimelineSurfaceMocks(page, requestLog, timelineBodies);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${getDevOrigin()}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('proj_timeline_surface_smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByText('Source Browser').first()).toBeVisible();
    await page.locator('button[title="Toggle NLE / Debug view"]').click();
    await expect(page.getByText('VETKA CUT')).toBeVisible();
    await expect(page.getByText('Timeline Surface', { exact: true })).toBeVisible();
    await expect(page.getByText('Timeline not ready. Run scene assembly.', { exact: true })).toBeVisible();

    await page.getByRole('button', { name: 'Refresh Project State' }).click();
    await expect.poll(() => requestLog.filter((entry) => entry.pathname === '/api/cut/project-state').length).toBeGreaterThan(2);
    await expect(page.getByText('v1 / video', { exact: true })).toBeVisible();
    await expect(page.getByText('a1 / audio', { exact: true })).toBeVisible();
    await expect(page.getByText('clip_v1_a', { exact: true })).toBeVisible();
    await expect(page.getByText('clip_v1_b', { exact: true })).toBeVisible();
    await expect(page.getByText('clip_a1_a', { exact: true })).toBeVisible();
    await expect(page.getByText('start 0s · duration 4s', { exact: true })).toBeVisible();
    await expect(page.getByText('start 4.5s · duration 3.5s', { exact: true })).toBeVisible();

    await page.getByRole('button', { name: 'Select First Clip' }).click();
    await expect.poll(() => timelineBodies.length).toBe(1);
    await expect.poll(() => requestLog.filter((entry) => entry.pathname === '/api/cut/project-state').length).toBeGreaterThan(3);
    await expect(page.getByText('timeline selected', { exact: true })).toBeVisible();
    expect(timelineBodies[0].ops[0].clip_ids).toEqual(['clip_v1_a']);

    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
    expect(await page.evaluate(() => window.localStorage.getItem('vetka_last_runtime_error'))).toBeNull();
  });
});
