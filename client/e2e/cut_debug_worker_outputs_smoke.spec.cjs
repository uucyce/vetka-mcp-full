const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_DEBUG_WORKER_OUTPUTS_PORT || 4186);
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
      project_id: 'proj_worker_outputs_smoke',
      display_name: 'CUT Worker Outputs Smoke',
      source_path: '/tmp/cut/source.mov',
      sandbox_root: '/tmp/cut-smoke',
      state: 'ready',
    },
    bootstrap_state: { last_stats: {} },
    timeline_state: {
      timeline_id: 'main',
      selection: { clip_ids: [], scene_ids: [] },
      lanes: [
        {
          lane_id: 'v1',
          lane_type: 'video',
          clips: [
            {
              clip_id: 'clip_thumb_lane',
              start_sec: 0,
              duration_sec: 6,
              source_path: '/tmp/cut/clip_thumb.mov',
            },
          ],
        },
      ],
    },
    scene_graph: { nodes: [] },
    waveform_bundle: {
      items: [
        { item_id: 'wf_a', source_path: '/tmp/cut/clip_wf.mov' },
      ],
    },
    transcript_bundle: {
      items: [
        { item_id: 'tx_a', source_path: '/tmp/cut/clip_tx.mov', degraded_mode: true, degraded_reason: 'proxy transcript' },
      ],
    },
    thumbnail_bundle: {
      items: [
        { item_id: 'thumb_a', source_path: '/tmp/cut/clip_thumb.mov', duration_sec: 6 },
      ],
    },
    audio_sync_result: {
      items: [
        { item_id: 'sync_a', source_path: '/tmp/cut/clip_sync.mov', reference_path: '/tmp/cut/master.wav', detected_offset_sec: 0.24, confidence: 0.93, method: 'peaks+correlation' },
      ],
    },
    slice_bundle: {
      items: [
        { item_id: 'slice_a', source_path: '/tmp/cut/clip_slice.mov' },
      ],
    },
    timecode_sync_result: {
      items: [
        { item_id: 'tc_a', source_path: '/tmp/cut/clip_tc.mov', reference_path: '/tmp/cut/master_tc.mov', reference_timecode: '01:00:00:00', source_timecode: '01:00:00:06', detected_offset_sec: 0.24, fps: 25 },
      ],
    },
    sync_surface: { schema_version: 'cut_sync_surface_v1', items: [] },
    time_marker_bundle: {
      items: [
        { marker_id: 'marker_a', media_path: '/tmp/cut/clip_thumb.mov', kind: 'favorite', start_sec: 1.2, end_sec: 2.4, status: 'active', text: 'beat' },
      ],
    },
    recent_jobs: [],
    active_jobs: [],
    runtime_ready: true,
    graph_ready: false,
    waveform_ready: true,
    transcript_ready: true,
    thumbnail_ready: true,
    audio_sync_ready: true,
    slice_ready: true,
    timecode_sync_ready: true,
    sync_surface_ready: false,
    meta_sync_ready: false,
    time_markers_ready: true,
    ...overrides,
  };
}

async function installWorkerOutputMocks(page, requestLog) {
  const first = createProjectState();
  const second = createProjectState({
    timeline_state: {
      timeline_id: 'main',
      selection: { clip_ids: [], scene_ids: [] },
      lanes: [
        {
          lane_id: 'v1',
          lane_type: 'video',
          clips: [
            {
              clip_id: 'clip_thumb_lane_b',
              start_sec: 0,
              duration_sec: 8,
              source_path: '/tmp/cut/clip_thumb_b.mov',
            },
          ],
        },
      ],
    },
    waveform_bundle: {
      items: [
        { item_id: 'wf_b', source_path: '/tmp/cut/clip_wf_b.mov', degraded_mode: true, degraded_reason: 'spectral proxy' },
        { item_id: 'wf_c', source_path: '/tmp/cut/clip_wf_c.mov' },
      ],
    },
    transcript_bundle: {
      items: [
        { item_id: 'tx_b', source_path: '/tmp/cut/clip_tx_b.mov' },
        { item_id: 'tx_c', source_path: '/tmp/cut/clip_tx_c.mov', degraded_mode: true, degraded_reason: 'draft diarization' },
      ],
    },
    thumbnail_bundle: {
      items: [
        { item_id: 'thumb_b', source_path: '/tmp/cut/clip_thumb_b.mov', duration_sec: 8 },
        { item_id: 'thumb_c', source_path: '/tmp/cut/clip_thumb_c.mov', duration_sec: 4 },
      ],
    },
    audio_sync_result: {
      items: [
        { item_id: 'sync_b', source_path: '/tmp/cut/clip_sync_b.mov', reference_path: '/tmp/cut/master_b.wav', detected_offset_sec: -0.12, confidence: 0.71, method: 'fft+peaks' },
      ],
    },
    slice_bundle: {
      items: [
        { item_id: 'slice_b', source_path: '/tmp/cut/clip_slice_b.mov' },
        { item_id: 'slice_c', source_path: '/tmp/cut/clip_slice_c.mov' },
      ],
    },
    timecode_sync_result: {
      items: [
        { item_id: 'tc_b', source_path: '/tmp/cut/clip_tc_b.mov', reference_path: '/tmp/cut/master_tc_b.mov', reference_timecode: '02:00:00:00', source_timecode: '02:00:00:12', detected_offset_sec: 0.48, fps: 25 },
      ],
    },
    time_marker_bundle: {
      items: [
        { marker_id: 'marker_b', media_path: '/tmp/cut/clip_thumb_b.mov', kind: 'favorite', start_sec: 0.8, end_sec: 1.6, status: 'active', text: 'entry' },
        { marker_id: 'marker_c', media_path: '/tmp/cut/clip_thumb_c.mov', kind: 'comment', start_sec: 2.1, end_sec: 3.5, status: 'active', text: 'note' },
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

test.describe.serial('phase170 cut debug worker outputs smoke', () => {
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('renders worker-output counts and representative rows, then updates after refresh', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    await installWorkerOutputMocks(page, requestLog);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('proj_worker_outputs_smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByText('Project').first()).toBeVisible();
    await page.waitForTimeout(300);
    await page.locator('button[title="Toggle NLE / Debug view"]').click();
    await expect(page.getByText('VETKA CUT')).toBeVisible();
    await expect(page.getByText('Worker Outputs', { exact: true })).toBeVisible();
    await expect(page.getByText('waveforms: 1', { exact: true })).toBeVisible();
    await expect(page.getByText('transcripts: 1', { exact: true })).toBeVisible();
    await expect(page.getByText('thumbnails: 1', { exact: true })).toBeVisible();
    await expect(page.getByText('timecode_sync: 1', { exact: true })).toBeVisible();
    await expect(page.getByText('audio_sync: 1', { exact: true })).toBeVisible();
    await expect(page.getByText('pause_slices: 1', { exact: true })).toBeVisible();
    await expect(page.getByText('time_markers: 1', { exact: true })).toBeVisible();
    await expect(page.getByText('WF · clip_wf.mov', { exact: true })).toBeVisible();
    await expect(page.getByText('proxy transcript', { exact: true })).toBeVisible();
    await expect(page.getByText('SYNC · clip_sync.mov', { exact: true })).toBeVisible();
    await expect(page.getByText('offset 0.240s · conf 0.93', { exact: true })).toHaveCount(2);
    await expect(page.getByText('TC · clip_tc.mov', { exact: true })).toBeVisible();
    await expect(page.getByText('01:00:00:00 → 01:00:00:06', { exact: true })).toBeVisible();

    await page.getByRole('button', { name: 'Refresh Project State' }).click();
    await expect.poll(() => requestLog.filter((entry) => entry.pathname === '/api/cut/project-state').length).toBeGreaterThan(1);
    await expect(page.getByText('waveforms: 2', { exact: true })).toBeVisible();
    await expect(page.getByText('transcripts: 2', { exact: true })).toBeVisible();
    await expect(page.getByText('thumbnails: 2', { exact: true })).toBeVisible();
    await expect(page.getByText('pause_slices: 2', { exact: true })).toBeVisible();
    await expect(page.getByText('time_markers: 2', { exact: true })).toBeVisible();
    await expect(page.getByText('WF · clip_wf_b.mov', { exact: true })).toBeVisible();
    await expect(page.getByText('spectral proxy', { exact: true })).toBeVisible();
    await expect(page.getByText('SYNC · clip_sync_b.mov', { exact: true })).toBeVisible();
    await expect(page.getByText('offset -0.120s · conf 0.71', { exact: true })).toHaveCount(2);
    await expect(page.getByText('fft+peaks')).toHaveCount(2);
    await expect(page.getByText('TC · clip_tc_b.mov', { exact: true })).toBeVisible();
    await expect(page.getByText('02:00:00:00 → 02:00:00:12', { exact: true })).toBeVisible();

    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
    expect(await page.evaluate(() => window.localStorage.getItem('vetka_last_runtime_error'))).toBeNull();
  });
});
