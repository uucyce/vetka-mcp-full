// @ts-check
const { test, expect } = require('@playwright/test');
const http = require('http');
const net = require('net');
const path = require('path');
const { spawn } = require('child_process');
const { createLoadedSceneGraphProjectState } = require('./fixtures/cutSceneGraphLoadedFixture.cjs');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
let DEV_PORT = Number(process.env.VETKA_CUT_SCENE_GRAPH_NODE_CLICK_PORT || 4193);
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
  }
  DEV_PORT = await findAvailablePort(DEV_PORT);
  serverStartedBySpec = true;
  serverProcess = spawn('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(DEV_PORT), '--strictPort'], {
    cwd: CLIENT_DIR,
    env: { ...process.env, BROWSER: 'none', CI: '1' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const capture = (chunk) => {
    serverLogs += chunk.toString();
    if (serverLogs.length > 20000) serverLogs = serverLogs.slice(-20000);
  };
  serverProcess.stdout.on('data', capture);
  serverProcess.stderr.on('data', capture);
  await waitForHttpOk(getDevOrigin(), 30000);
}

async function cleanupServer() {
  if (!serverProcess || !serverStartedBySpec) return;
  const proc = serverProcess;
  serverProcess = null;
  await new Promise((resolve) => {
    const done = () => resolve();
    proc.once('exit', done);
    proc.kill('SIGTERM');
    setTimeout(done, 2000);
  });
}

// MARKER_QA.W6: "Graph Ready" / "Scene Graph Surface" UI text removed from GraphPanelDock.
test.describe.serial('phase170 scene graph node-click smoke', () => {
  test.skip(true, 'Scene graph overlay UI removed — needs test rewrite');
  test.setTimeout(30000);

  test.beforeAll(async () => {
    await ensureDevServer();
  });

  test.afterAll(async () => {
    await cleanupServer();
  });

  test('clicking a scene-graph node triggers timeline focus request', async ({ page }) => {
    const requestLog = [];
    const pageErrors = [];
    const state = createLoadedSceneGraphProjectState();

    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.route(`${getDevOrigin()}/api/cut/**`, async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      requestLog.push({ method: request.method(), pathname: url.pathname });

      if (url.pathname === '/api/cut/project-state') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state) });
        return;
      }
      if (url.pathname === '/api/cut/timeline/apply') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, timeline_state: state.timeline_state }) });
        return;
      }
      if (url.pathname === '/api/cut/media-proxy') {
        await route.fulfill({ status: 204, contentType: 'video/mp4', body: '' });
        return;
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
    });

    await page.addInitScript(() => {
      window.localStorage.setItem('cut.scene_graph.pane_mode.v1', 'peer_pane');
    });

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`${getDevOrigin()}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-scene-graph-loaded')}&project_id=${encodeURIComponent('cut-scene-graph-loaded')}`, { waitUntil: 'domcontentloaded' });

    await expect(page.getByText('Graph Ready', { exact: true })).toBeVisible();
    await expect(page.getByText('Scene Graph Surface', { exact: true })).toBeVisible();

    await page.evaluate(async () => {
      const api = /** @type {any} */ (window).__VETKA_CUT_TEST__;
      if (!api) throw new Error('Missing CUT test hook');
      await api.triggerSceneGraphFocus('cut_graph:take_01_a');
    });

    await expect(page.getByText('Graph focus -> timeline: Take A', { exact: true })).toBeVisible({ timeout: 4000 });
    await expect.poll(() => requestLog.filter((entry) => entry.pathname === '/api/cut/timeline/apply').length, { timeout: 4000 }).toBeGreaterThan(0);
    await expect(pageErrors).toEqual([]);
  });
});
