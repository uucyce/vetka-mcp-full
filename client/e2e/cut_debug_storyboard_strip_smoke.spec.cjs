const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_DEBUG_STORYBOARD_STRIP_PORT || 4187);
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
      project_id: 'proj_storyboard_strip_smoke',
      display_name: 'CUT Storyboard Strip Smoke',
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

async function installStoryboardMocks(page, requestLog) {
  const first = createProjectState();
  const second = createProjectState({
    thumbnail_bundle: {
      items: [
        {
          item_id: 'thumb_story_a',
          source_path: '/tmp/cut/clip_story_a.mov',
          modality: 'video',
          duration_sec: 12,
          poster_url: 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==',
          source_url: 'https://example.com/story-a',
        },
        {
          item_id: 'thumb_story_b',
          source_path: '/tmp/cut/clip_story_b.mov',
          modality: 'video',
          duration_sec: 15,
          source_url: 'https://example.com/story-b',
        },
      ],
    },
    slice_bundle: {
      items: [
        {
          item_id: 'slice_story_a',
          source_path: '/tmp/cut/clip_story_a.mov',
          method: 'energy_pause_v1',
          windows: [{ start_sec: 2, end_sec: 4, method: 'energy_pause_v1' }],
        },
        {
          item_id: 'slice_story_b',
          source_path: '/tmp/cut/clip_story_b.mov',
          method: 'energy_pause_v1',
          windows: [{ start_sec: 6, end_sec: 9, method: 'energy_pause_v1' }],
        },
      ],
    },
    sync_surface: {
      schema_version: 'cut_sync_surface_v1',
      items: [
        {
          item_id: 'sync_story_b',
          source_path: '/tmp/cut/clip_story_b.mov',
          reference_path: '/tmp/cut/master_story.wav',
          recommended_method: 'meta_sync',
          recommended_offset_sec: 0.48,
          confidence: 0.88,
        },
      ],
    },
    thumbnail_ready: true,
    slice_ready: true,
    sync_surface_ready: true,
    runtime_ready: true,
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

test.describe.serial('phase170 cut debug storyboard strip smoke', () => {
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('renders storyboard empty state, then hydrates cards and selection after refresh', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    await installStoryboardMocks(page, requestLog);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('proj_storyboard_strip_smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByText('Source Browser').first()).toBeVisible();
    await page.locator('button[title="Toggle NLE / Debug view"]').click();
    await expect(page.getByText('VETKA CUT')).toBeVisible();
    await expect(page.getByText('Storyboard Strip', { exact: true })).toBeVisible();
    await expect(page.getByText('No thumbnails yet. Run thumbnail build.', { exact: true })).toBeVisible();
    await expect(page.getByText('No storyboard item selected.', { exact: true })).toBeVisible();

    await page.getByRole('button', { name: 'Refresh Project State' }).click();
    await expect.poll(() => requestLog.filter((entry) => entry.pathname === '/api/cut/project-state').length).toBeGreaterThan(1);
    await expect(page.getByText('clip_story_a.mov', { exact: true })).toHaveCount(2);
    await expect(page.getByText('clip_story_b.mov', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Select Shot' })).toHaveCount(2);
    await expect(page.getByRole('link', { name: 'Open Preview' })).toHaveCount(2);
    await expect(page.getByText('Sync Badge meta_sync 0.480s (88%)', { exact: true })).toBeVisible();
    await expect(page.getByText('marker window 2s - 4s', { exact: true })).toHaveCount(2);
    await expect(page.getByText('marker window 6s - 9s', { exact: true })).toBeVisible();
    await expect(page.getByText('slice source: pause_slice_worker', { exact: true })).toBeVisible();

    await expect(page.getByText('clip_story_a.mov', { exact: true })).toHaveCount(2);
    await page.getByRole('button', { name: 'Select Shot' }).nth(1).click();
    await expect(page.getByText('clip_story_b.mov', { exact: true })).toHaveCount(2);
    await expect(page.getByText('recommended sync: meta_sync 0.480s', { exact: true })).toBeVisible();
    await expect(page.getByText('marker window 6s - 9s', { exact: true })).toHaveCount(2);

    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
    expect(await page.evaluate(() => window.localStorage.getItem('vetka_last_runtime_error'))).toBeNull();
  });
});
