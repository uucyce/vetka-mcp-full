const { test, expect } = require('@playwright/test');
const fs = require('fs');
const http = require('http');
const net = require('net');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const FIXTURE_PATH = path.join(__dirname, 'fixtures', 'cut_berlin_fixture_state.json');
const DEV_PORT = Number(process.env.VETKA_CUT_BERLIN_PORT || 3211);
const DEV_ORIGIN = `http://127.0.0.1:${DEV_PORT}`;
const SANDBOX_HINT = 'codex54_cut_fixture_sandbox';
const PROJECT_ID = 'cut_berlin_fixture_demo';

let serverProcess = null;
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

function portIsBusy(port) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host: '127.0.0.1', port });
    socket.once('connect', () => {
      socket.destroy();
      resolve(true);
    });
    socket.once('error', () => resolve(false));
  });
}

async function ensureReservedDevServer() {
  if (await portIsBusy(DEV_PORT)) {
    throw new Error(`Reserved CUT fixture port ${DEV_PORT} is already busy. Refusing to attach to another lane.`);
  }

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
  if (serverProcess) {
    serverProcess.kill('SIGTERM');
    serverProcess = null;
  }
}

test.describe.serial('phase170 berlin fixture smoke lane', () => {
  test.beforeAll(async () => {
    await ensureReservedDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('loads berlin fixture only on reserved port and sandbox hint', async ({ page }) => {
    const fixture = JSON.parse(fs.readFileSync(FIXTURE_PATH, 'utf-8'));
    const projectStateRequests = [];

    await page.route(`${DEV_ORIGIN}/api/cut/**`, async (route) => {
      const request = route.request();
      const url = new URL(request.url());

      if (url.pathname === '/api/cut/project-state') {
        projectStateRequests.push({
          sandbox_root: url.searchParams.get('sandbox_root'),
          project_id: url.searchParams.get('project_id'),
        });
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(fixture),
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

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent(`/tmp/${SANDBOX_HINT}`)}&project_id=${encodeURIComponent(PROJECT_ID)}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByTestId('cut-editor-layout')).toBeVisible();
    // MARKER_QA.W6: DockviewLayout defaults to GRAPH tab — click PROJECT to activate source browser
    await page.getByText('Project', { exact: true }).first().click();
    await page.waitForTimeout(300);
    const sourceBrowser = page.getByTestId('cut-source-browser');

    await expect(sourceBrowser).toBeVisible();
    await expect(page.getByTestId('cut-timeline-track-view')).toBeVisible();
    await expect(sourceBrowser.getByText('take_01.mov')).toBeVisible();
    await expect(sourceBrowser.getByText('frame_01.png')).toBeVisible();
    await expect(sourceBrowser.getByText('250623_vanpticdanyana_berlin_Punch.m4a')).toBeVisible();

    await expect.poll(() => projectStateRequests.length).toBeGreaterThan(0);
    await expect(projectStateRequests[0]).toEqual({
      sandbox_root: `/tmp/${SANDBOX_HINT}`,
      project_id: PROJECT_ID,
    });
  });
});
