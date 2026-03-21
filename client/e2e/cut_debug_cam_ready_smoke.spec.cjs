const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_DEBUG_CAM_READY_PORT || 4185);
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
        reject(new Error(`Timed out waiting for ${url}
${serverLogs}`));
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
      project_id: 'proj_cam_ready_smoke',
      display_name: 'CUT CAM Ready Smoke',
      source_path: '/tmp/cut/source.mov',
      sandbox_root: '/tmp/cut-smoke',
      state: 'ready',
    },
    bootstrap_state: { last_stats: {} },
    timeline_state: { timeline_id: 'main', selection: { clip_ids: [], scene_ids: [] }, lanes: [] },
    scene_graph: { nodes: [] },
    waveform_bundle: { items: [] },
    transcript_bundle: { items: [] },
    thumbnail_bundle: {
      items: [
        {
          item_id: 'thumb_cam_a',
          source_path: '/tmp/cut/clip_cam.mov',
          modality: 'video',
          duration_sec: 18,
        },
      ],
    },
    audio_sync_result: { items: [] },
    slice_bundle: { items: [] },
    timecode_sync_result: { items: [] },
    sync_surface: { schema_version: 'cut_sync_surface_v1', items: [] },
    time_marker_bundle: { items: [] },
    recent_jobs: [],
    active_jobs: [],
    runtime_ready: true,
    graph_ready: false,
    waveform_ready: false,
    transcript_ready: false,
    thumbnail_ready: true,
    audio_sync_ready: false,
    slice_ready: false,
    timecode_sync_ready: false,
    sync_surface_ready: false,
    meta_sync_ready: false,
    time_markers_ready: true,
    ...overrides,
  };
}

async function installCamReadyMocks(page, requestLog) {
  const first = createProjectState();
  const second = createProjectState({
    time_marker_bundle: {
      items: [
        {
          marker_id: 'marker_cam_ready_a',
          kind: 'cam',
          media_path: '/tmp/cut/clip_cam.mov',
          start_sec: 10,
          end_sec: 14,
          status: 'active',
          score: 0.85,
          text: 'subject reveal',
          cam_payload: {
            source: 'cam_worker',
            status: 'ready',
            hint: 'dramatic beat on subject reveal',
          },
        },
      ],
    },
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

test.describe.serial('phase170 cut debug cam ready smoke', () => {
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('renders CAM Ready waiting state, then hydrates selected-shot cam payloads after refresh', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    await installCamReadyMocks(page, requestLog);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('proj_cam_ready_smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByText('Project').first()).toBeVisible();
    await page.locator('button[title="Toggle NLE / Debug view"]').click();
    await expect(page.getByText('VETKA CUT')).toBeVisible();
    await expect(page.getByText('Selected Shot', { exact: true })).toBeVisible();
    await expect(page.getByText('clip_cam.mov', { exact: true })).toHaveCount(2);
    await expect(page.getByText('CAM Ready', { exact: true })).toBeVisible();
    await expect(page.getByText('cam markers: 0', { exact: true })).toBeVisible();
    await expect(page.getByText('status: waiting for CAM payloads', { exact: true })).toBeVisible();
    await expect(page.getByText('next: attach `cam_payload` and contextual hints for this shot', { exact: true })).toBeVisible();

    await page.getByRole('button', { name: 'Refresh Project State' }).click();
    await expect.poll(() => requestLog.filter((entry) => entry.pathname === '/api/cut/project-state').length).toBeGreaterThan(1);
    await expect(page.getByText('cam markers: 1', { exact: true })).toBeVisible();
    await expect(page.getByText('status: context-linked markers detected', { exact: true })).toBeVisible();
    await expect(page.getByText('10s - 14s', { exact: true })).toBeVisible();
    await expect(page.getByText('source: cam_worker · status: ready', { exact: true })).toBeVisible();
    await expect(page.getByText('dramatic beat on subject reveal', { exact: true })).toBeVisible();

    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
    expect(await page.evaluate(() => window.localStorage.getItem('vetka_last_runtime_error'))).toBeNull();
  });
});
