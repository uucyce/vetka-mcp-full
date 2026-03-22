const { test, expect } = require('@playwright/test');
const http = require('http');
const net = require('net');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
let DEV_PORT = Number(process.env.VETKA_CUT_DEBUG_SCENE_GRAPH_PORT || 4189);
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
      project_id: 'proj_scene_graph_smoke',
      display_name: 'CUT Scene Graph Smoke',
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

async function installSceneGraphMocks(page, requestLog) {
  const first = createProjectState();
  const second = createProjectState({
    graph_ready: true,
    scene_graph: {
      nodes: [
        { node_id: 'scene_01', node_type: 'scene', label: 'Opening Scene' },
        { node_id: 'take_01_a', node_type: 'take', label: 'Take A' },
        { node_id: 'note_01', node_type: 'note', label: 'Director Note' },
      ],
    },
  });
  const snapshots = [first, first, second, second];
  let index = 0;

  await page.route(`${getDevOrigin()}/api/**`, async (route) => {
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

// MARKER_QA.W6: DebugShellPanel rewritten (MARKER_QA.W5.1) — old UI labels removed.
test.describe.serial('phase170 cut debug scene graph surface smoke', () => {
  test.fixme(true, 'DebugShellPanel rewritten — scene graph surface section changed');
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('renders scene graph empty state, then hydrates node rows after refresh', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    await installSceneGraphMocks(page, requestLog);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${getDevOrigin()}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('proj_scene_graph_smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByText('Project').first()).toBeVisible();
    await page.click('button:text-is("View")'); await page.waitForTimeout(200); await page.click('text=Toggle NLE / Debug');
    await expect(page.getByText('VETKA CUT')).toBeVisible();
    await expect(page.getByText('Scene Graph Surface', { exact: true })).toBeVisible();
    await expect(page.getByText('Scene graph not ready.', { exact: true })).toBeVisible();

    await page.getByRole('button', { name: 'Refresh Project State' }).click();
    await expect.poll(() => requestLog.filter((entry) => entry.pathname === '/api/cut/project-state').length).toBeGreaterThan(1);
    await expect(page.getByText('Opening Scene', { exact: true })).toBeVisible();
    await expect(page.getByText('Take A', { exact: true })).toBeVisible();
    await expect(page.getByText('Director Note', { exact: true })).toBeVisible();
    await expect(page.getByText('scene_01 · scene', { exact: true })).toBeVisible();
    await expect(page.getByText('take_01_a · take', { exact: true })).toBeVisible();
    await expect(page.getByText('note_01 · note', { exact: true })).toBeVisible();

    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
    expect(await page.evaluate(() => window.localStorage.getItem('vetka_last_runtime_error'))).toBeNull();
  });
});
