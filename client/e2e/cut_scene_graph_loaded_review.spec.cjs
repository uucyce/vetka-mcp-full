const { test, expect } = require('@playwright/test');
const http = require('http');
const net = require('net');
const path = require('path');
const { spawn } = require('child_process');
const { createLoadedSceneGraphProjectState } = require('./fixtures/cutSceneGraphLoadedFixture.cjs');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
let DEV_PORT = Number(process.env.VETKA_CUT_SCENE_GRAPH_LOADED_PORT || 4191);
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
        reject(new Error(`Timed out waiting for ${url}\n${serverLogs}`));
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

async function cleanupServer() {
  if (!serverProcess || !serverStartedBySpec) {
    return;
  }
  const proc = serverProcess;
  serverProcess = null;
  await new Promise((resolve) => {
    const done = () => resolve();
    proc.once('exit', done);
    proc.kill('SIGTERM');
    setTimeout(done, 2000);
  });
}

test.describe.serial('phase170 cut scene graph loaded review', () => {
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    await cleanupServer();
  });

  test('renders loaded scene graph state inside NLE pane', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    const state = createLoadedSceneGraphProjectState();

    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.route(`${getDevOrigin()}/api/cut/**`, async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      requestLog.push({ method: request.method(), pathname: url.pathname });

      if (url.pathname === '/api/cut/project-state') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(state),
        });
        return;
      }

      if (url.pathname === '/api/cut/timeline/apply') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, timeline_state: state.timeline_state }),
        });
        return;
      }

      if (url.pathname === '/api/cut/media-proxy') {
        await route.fulfill({ status: 204, contentType: 'video/mp4', body: '' });
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });

    await page.addInitScript(() => {
      window.localStorage.setItem('cut.scene_graph.pane_mode.v1', 'peer_pane');
    });

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${getDevOrigin()}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-scene-graph-loaded')}&project_id=${encodeURIComponent('cut-scene-graph-loaded')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByText('Graph Ready', { exact: true })).toBeVisible();
    await expect(page.getByText('Scene Graph peer pane ready', { exact: true })).toBeVisible();
    await expect(page.getByText('Scene Graph Surface', { exact: true })).toBeVisible();
    await expect(page.getByText('Shared DAG viewport mounted inside NLE pane.', { exact: true })).toBeVisible();
    await expect(page.getByText('Compact Graph Card', { exact: true })).toBeVisible();
    await expect(page.getByText('clip-linked graph nodes: 3', { exact: true })).toBeVisible();
    await expect(page.getByText('active graph node: Take A · take', { exact: true })).toBeVisible();
    await expect(page.getByText('graph buckets: primary_structural, selected_shot, intel_overlay', { exact: true })).toBeVisible();
    await expect(page.getByText('sync waveform', { exact: true })).toBeVisible();
    await expect(page.getByText('bucket selected_shot', { exact: true })).toBeVisible();
    await expect(page.getByAltText('Take A')).toBeVisible();
    await expect(page.getByText('Focus Timeline From Graph', { exact: true })).toBeVisible();
    await expect(page.getByText('Focus Selected Shot', { exact: true })).toBeVisible();
    await page.locator('[data-testid="dag-node-label"][data-node-label="Take A"]').first().click();
    await expect
      .poll(() => requestLog.filter((entry) => entry.pathname === '/api/cut/timeline/apply').length)
      .toBeGreaterThan(0);
    await expect(page.getByText('focus source: timeline + storyboard crosslinks', { exact: true })).toBeVisible();
    await expect(page.getByText('pane inspector link: Opening Scene · Take A', { exact: true })).toBeVisible();
    await expect(pageErrors).toEqual([]);
    await expect.poll(() => requestLog.filter((entry) => entry.pathname === '/api/cut/project-state').length).toBeGreaterThan(0);
  });
});
