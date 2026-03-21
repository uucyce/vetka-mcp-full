const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_DEBUG_SMOKE_PORT || 4177);
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
      project_id: 'proj_debug_smoke',
      display_name: 'CUT Debug Smoke',
      source_path: '/tmp/cut/source.mov',
      sandbox_root: '/tmp/cut-smoke',
      state: 'ready',
    },
    bootstrap_state: { last_stats: {} },
    timeline_state: {
      timeline_id: 'main',
      selection: { clip_ids: [], scene_ids: [] },
      lanes: [],
    },
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
  };
}

async function installDebugShellMocks(page, requestLog) {
  const state = createProjectState();
  const pendingJobs = new Map();
  let jobCounter = 0;

  const applyJobResult = (jobType) => {
    if (jobType === 'scene_assembly') {
      state.runtime_ready = true;
      state.graph_ready = true;
      state.timeline_state.lanes = [
        {
          lane_id: 'video_main',
          lane_type: 'video_main',
          clips: [
            {
              clip_id: 'clip_debug_a',
              scene_id: 'scene_debug_a',
              start_sec: 0,
              duration_sec: 4,
              source_path: '/tmp/cut/clip_debug_a.mov',
            },
          ],
        },
      ];
      state.scene_graph.nodes = [
        { node_id: 'scene_debug_a', node_type: 'scene', label: 'Scene Debug A' },
      ];
      return;
    }
    if (jobType === 'waveform_build') {
      state.waveform_ready = true;
      state.waveform_bundle.items = [
        {
          item_id: 'wf_debug_a',
          source_path: '/tmp/cut/clip_debug_a.mov',
          waveform_bins: [0.2, 0.5, 0.3, 0.7],
        },
      ];
      return;
    }
    if (jobType === 'audio_sync') {
      state.audio_sync_ready = true;
      state.audio_sync_result.items = [
        {
          item_id: 'audio_sync_debug_a',
          source_path: '/tmp/cut/clip_debug_a.mov',
          reference_path: '/tmp/cut/master.wav',
          detected_offset_sec: 0.24,
          confidence: 0.93,
          method: 'peaks+correlation',
        },
      ];
    }
  };

  await page.route(`${DEV_ORIGIN}/api/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    requestLog.push({ method: request.method(), pathname: url.pathname });

    if (url.pathname === '/api/cut/bootstrap') {
      const body = request.postDataJSON();
      state.project.project_id = 'proj_debug_smoke';
      state.project.display_name = body.project_name || 'CUT Debug Smoke';
      state.project.source_path = body.source_path || '/tmp/cut/source.mov';
      state.project.sandbox_root = body.sandbox_root || '/tmp/cut-smoke';
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          project: {
            project_id: 'proj_debug_smoke',
            display_name: state.project.display_name,
            source_path: state.project.source_path,
            sandbox_root: state.project.sandbox_root,
          },
        }),
      });
      return;
    }

    if (url.pathname === '/api/cut/project-state') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(state),
      });
      return;
    }

    const workerRoutes = new Map([
      ['/api/cut/scene-assembly-async', 'scene_assembly'],
      ['/api/cut/worker/waveform-build-async', 'waveform_build'],
      ['/api/cut/worker/audio-sync-async', 'audio_sync'],
    ]);
    if (workerRoutes.has(url.pathname)) {
      jobCounter += 1;
      const jobId = `job_${workerRoutes.get(url.pathname)}_${jobCounter}`;
      pendingJobs.set(jobId, workerRoutes.get(url.pathname));
      state.active_jobs = [{ job_id: jobId, job_type: workerRoutes.get(url.pathname), state: 'running', progress: 0.5 }];
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          schema_version: 'cut_mcp_job_v1',
          job_id: jobId,
          job: { job_id: jobId, state: 'running' },
        }),
      });
      return;
    }

    if (url.pathname.startsWith('/api/cut/job/')) {
      const parts = url.pathname.split('/');
      const jobId = parts[parts.length - 1];
      const jobType = pendingJobs.get(jobId);
      if (jobType) {
        applyJobResult(jobType);
        pendingJobs.delete(jobId);
      }
      state.active_jobs = [];
      state.recent_jobs = [{ job_id: jobId, job_type: jobType || 'unknown', state: 'done', progress: 1 }];
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          schema_version: 'cut_mcp_job_v1',
          job_id: jobId,
          job: { state: 'done', result: { ok: true } },
        }),
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

test.describe.serial('phase170 cut debug shell worker-actions smoke', () => {
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('toggles into debug shell, bootstraps project, and runs async worker actions', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    await installDebugShellMocks(page, requestLog);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&source_path=${encodeURIComponent('/tmp/cut/source.mov')}&project_name=${encodeURIComponent('CUT Debug Smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByText('Project').first()).toBeVisible();
    await page.click('button:text-is("View")'); await page.waitForTimeout(200); await page.click('text=Toggle NLE / Debug');

    await expect(page.getByText('VETKA CUT')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Open CUT Project' })).toBeEnabled();

    await page.getByRole('button', { name: 'Open CUT Project' }).click();
    await expect(page.getByText('Project loaded')).toBeVisible();
    await expect(page.getByText('proj_debug_smoke')).toBeVisible();

    await page.getByRole('button', { name: 'Start Scene Assembly' }).click();
    await expect(page.getByText('Running scene assembly...')).toBeVisible();
    await expect(page.getByText('Runtime ready')).toBeVisible();
    await expect(page.getByText('video_main / video_main')).toBeVisible();
    await expect(page.getByText('Scene Debug A')).toBeVisible();
    await expect(page.getByText('runtime_ready: true')).toBeVisible();

    await page.getByRole('button', { name: 'Build Waveforms' }).click();
    await expect(page.getByText('Building waveform bundle...')).toBeVisible();
    await expect(page.getByText('waveforms: 1')).toBeVisible();

    await page.getByRole('button', { name: 'Build Audio Sync' }).click();
    await expect(page.getByText('Building audio sync offsets...')).toBeVisible();
    await expect(page.getByText('audio_sync: 1')).toBeVisible();
    await expect(page.getByText('SYNC · clip_debug_a.mov')).toBeVisible();

    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
    expect(await page.evaluate(() => window.localStorage.getItem('vetka_last_runtime_error'))).toBeNull();

    expect(requestLog.some((entry) => entry.pathname === '/api/cut/bootstrap')).toBe(true);
    expect(requestLog.some((entry) => entry.pathname === '/api/cut/scene-assembly-async')).toBe(true);
    expect(requestLog.some((entry) => entry.pathname === '/api/cut/worker/waveform-build-async')).toBe(true);
    expect(requestLog.some((entry) => entry.pathname === '/api/cut/worker/audio-sync-async')).toBe(true);
    expect(requestLog.some((entry) => entry.pathname.startsWith('/api/cut/job/'))).toBe(true);
  });
});
