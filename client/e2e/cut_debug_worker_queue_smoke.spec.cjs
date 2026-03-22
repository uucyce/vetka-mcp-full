const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_DEBUG_QUEUE_PORT || 4181);
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

function createProjectState() {
  return {
    success: true,
    schema_version: 'cut_project_state_v1',
    project: {
      project_id: 'proj_queue_smoke',
      display_name: 'CUT Queue Smoke',
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
    active_jobs: [
      {
        job_id: 'job_waveform_active_12345678',
        job_type: 'waveform_build',
        state: 'running',
        progress: 0.42,
      },
    ],
    recent_jobs: [
      {
        job_id: 'job_audio_recent_87654321',
        job_type: 'audio_sync',
        state: 'done',
        progress: 1,
      },
    ],
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
  };
}

async function installWorkerQueueMocks(page, requestLog, cancelBodies) {
  const state = createProjectState();

  await page.route(`${DEV_ORIGIN}/api/**`, async (route) => {
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

    if (url.pathname === '/api/cut/job/job_waveform_active_12345678/cancel') {
      cancelBodies.push({ method: request.method(), pathname: url.pathname });
      const activeJob = state.active_jobs.shift();
      if (activeJob) {
        state.recent_jobs.unshift({
          ...activeJob,
          state: 'cancelled',
          progress: activeJob.progress,
        });
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, job: { state: 'cancelled' } }),
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

// MARKER_QA.W6: Rewritten to match current DebugShellPanel (MARKER_QA.W5.1).
test.describe.serial('phase170 cut debug worker queue smoke', () => {
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('shows queue card, cancels an active job, and refreshes counts safely', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    const cancelBodies = [];
    await installWorkerQueueMocks(page, requestLog, cancelBodies);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('proj_queue_smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByText('Project').first()).toBeVisible({ timeout: 10000 });
    await page.click('button:text-is("View")'); await page.waitForTimeout(200); await page.click('text=Toggle NLE / Debug');
    await expect(page.getByText('VETKA CUT')).toBeVisible();
    // MARKER_QA.W6: DebugShellPanel uses "active:" / "recent:" labels (not "active_jobs:")
    await expect(page.getByText('Worker Queue')).toBeVisible();
    await expect(page.getByText(/active:\s*1/)).toBeVisible();
    await expect(page.getByText(/recent:\s*1/)).toBeVisible();
    // Job row: "{job_id_prefix}... {state}" — job_id starts with "job_wave"
    await expect(page.getByText('job_wave...')).toBeVisible();
    await expect(page.getByText('running')).toBeVisible();

    // Cancel button text is just "Cancel"
    await page.getByRole('button', { name: 'Cancel' }).click();
    await expect.poll(() => cancelBodies.length).toBe(1);
    // After cancel: active job moves to recent
    await page.getByRole('button', { name: 'Refresh Project State' }).click();
    await expect.poll(() => requestLog.filter((e) => e.pathname === '/api/cut/project-state').length).toBeGreaterThan(1);
    await expect(page.getByText(/active:\s*0/)).toBeVisible();
    await expect(page.getByText(/recent:\s*2/)).toBeVisible();

    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
    expect(await page.evaluate(() => window.localStorage.getItem('vetka_last_runtime_error'))).toBeNull();

    expect(cancelBodies[0].method).toBe('POST');
    expect(requestLog.some((entry) => entry.pathname === '/api/cut/project-state')).toBe(true);
    expect(requestLog.some((entry) => entry.pathname === '/api/cut/job/job_waveform_active_12345678/cancel')).toBe(true);
  });
});
