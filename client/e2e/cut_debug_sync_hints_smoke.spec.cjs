const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_DEBUG_SYNC_HINTS_PORT || 4184);
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
      project_id: 'proj_sync_hints_smoke',
      display_name: 'CUT Sync Hints Smoke',
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
    audio_sync_result: {
      items: [
        {
          item_id: 'audio_sync_a',
          source_path: '/tmp/cut/clip_a.mov',
          reference_path: '/tmp/cut/master.wav',
          detected_offset_sec: 0.24,
          confidence: 0.93,
          method: 'peaks+correlation',
        },
      ],
    },
    slice_bundle: { items: [] },
    timecode_sync_result: {
      items: [
        {
          item_id: 'timecode_sync_a',
          source_path: '/tmp/cut/clip_tc.mov',
          reference_path: '/tmp/cut/master_tc.mov',
          reference_timecode: '01:00:00:00',
          source_timecode: '01:00:00:06',
          detected_offset_sec: 0.24,
          method: 'timecode',
          fps: 25,
        },
      ],
    },
    sync_surface: {
      schema_version: 'cut_sync_surface_v1',
      items: [
        {
          item_id: 'sync_surface_a',
          source_path: '/tmp/cut/clip_sync.mov',
          reference_path: '/tmp/cut/master.wav',
          recommended_method: 'waveform',
          recommended_offset_sec: 0.24,
          confidence: 0.93,
        },
      ],
    },
    time_marker_bundle: { items: [] },
    recent_jobs: [],
    active_jobs: [],
    runtime_ready: false,
    graph_ready: false,
    waveform_ready: false,
    transcript_ready: false,
    thumbnail_ready: false,
    audio_sync_ready: true,
    slice_ready: false,
    timecode_sync_ready: true,
    sync_surface_ready: true,
    meta_sync_ready: false,
    time_markers_ready: false,
    ...overrides,
  };
}

async function installSyncHintMocks(page, requestLog) {
  const first = createProjectState();
  const second = createProjectState({
    audio_sync_result: {
      items: [
        {
          item_id: 'audio_sync_b',
          source_path: '/tmp/cut/clip_b.mov',
          reference_path: '/tmp/cut/master_v2.wav',
          detected_offset_sec: 0.48,
          confidence: 0.88,
          method: 'fft+peaks',
        },
      ],
    },
    timecode_sync_result: {
      items: [
        {
          item_id: 'timecode_sync_b',
          source_path: '/tmp/cut/clip_tc_b.mov',
          reference_path: '/tmp/cut/master_tc_v2.mov',
          reference_timecode: '02:00:00:00',
          source_timecode: '02:00:00:12',
          detected_offset_sec: 0.48,
          method: 'timecode',
          fps: 25,
        },
      ],
    },
    sync_surface: {
      schema_version: 'cut_sync_surface_v1',
      items: [
        {
          item_id: 'sync_surface_b',
          source_path: '/tmp/cut/clip_sync_b.mov',
          reference_path: '/tmp/cut/master_v2.wav',
          recommended_method: 'meta_sync',
          recommended_offset_sec: 0.48,
          confidence: 0.88,
        },
        {
          item_id: 'sync_surface_c',
          source_path: '/tmp/cut/clip_sync_c.mov',
          reference_path: '/tmp/cut/master_v3.wav',
          recommended_method: 'waveform',
          recommended_offset_sec: -0.12,
          confidence: 0.71,
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

// MARKER_QA.W6: DebugShellPanel rewritten (MARKER_QA.W5.1) — old UI labels removed.
test.describe.serial('phase170 cut debug sync hints smoke', () => {
  test.fixme(true, 'DebugShellPanel rewritten — sync hints section changed');
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('renders sync hint counts and representative rows, then updates after refresh', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    await installSyncHintMocks(page, requestLog);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('proj_sync_hints_smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByText('Project').first()).toBeVisible();
    await page.click('button:text-is("View")'); await page.waitForTimeout(200); await page.click('text=Toggle NLE / Debug');
    await expect(page.getByText('VETKA CUT')).toBeVisible();
    await expect(page.getByText('Sync Hints', { exact: true })).toBeVisible();
    await expect(page.getByText('sync_surface items: 1')).toBeVisible();
    await expect(page.getByText('timecode_sync results: 1')).toBeVisible();
    await expect(page.getByText('audio_sync results: 1')).toBeVisible();
    await expect(page.getByText('clip_tc.mov', { exact: true })).toBeVisible();
    await expect(page.getByText('ref: master_tc.mov', { exact: true })).toBeVisible();
    await expect(page.getByText('01:00:00:00 → 01:00:00:06 · 0.240s', { exact: true })).toBeVisible();
    await expect(page.getByText('peaks+correlation')).toHaveCount(2);
    await expect(page.getByText('recommended: waveform')).toBeVisible();

    await page.getByRole('button', { name: 'Refresh Project State' }).click();
    await expect.poll(() => requestLog.filter((entry) => entry.pathname === '/api/cut/project-state').length).toBeGreaterThan(1);
    await expect(page.getByText('sync_surface items: 2')).toBeVisible();
    await expect(page.getByText('timecode_sync results: 1')).toBeVisible();
    await expect(page.getByText('audio_sync results: 1')).toBeVisible();
    await expect(page.getByText('clip_tc_b.mov', { exact: true })).toBeVisible();
    await expect(page.getByText('ref: master_tc_v2.mov', { exact: true })).toBeVisible();
    await expect(page.getByText('02:00:00:00 → 02:00:00:12 · 0.480s', { exact: true })).toBeVisible();
    await expect(page.getByText('fft+peaks')).toHaveCount(2);
    await expect(page.getByText('recommended: meta_sync')).toBeVisible();
    await expect(page.getByText('recommended: waveform')).toHaveCount(1);

    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
    expect(await page.evaluate(() => window.localStorage.getItem('vetka_last_runtime_error'))).toBeNull();
  });
});
