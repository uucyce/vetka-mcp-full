const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_DEBUG_MARKERS_PORT || 4179);
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
      project_id: 'proj_marker_smoke',
      display_name: 'CUT Marker Smoke',
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
          lane_id: 'video_main',
          lane_type: 'video_main',
          clips: [
            {
              clip_id: 'clip_marker_a',
              scene_id: 'scene_marker_a',
              start_sec: 1,
              duration_sec: 4,
              source_path: '/tmp/cut/clip_marker_a.mov',
            },
          ],
        },
      ],
    },
    scene_graph: { nodes: [{ node_id: 'scene_marker_a', node_type: 'scene', label: 'Scene Marker A' }] },
    waveform_bundle: { items: [] },
    transcript_bundle: { items: [] },
    thumbnail_bundle: {
      items: [
        {
          item_id: 'thumb_marker_a',
          source_path: '/tmp/cut/clip_marker_a.mov',
          modality: 'video',
          duration_sec: 4,
        },
      ],
    },
    audio_sync_result: { items: [] },
    slice_bundle: { items: [] },
    timecode_sync_result: { items: [] },
    sync_surface: { schema_version: 'cut_sync_surface_v1', items: [] },
    time_marker_bundle: {
      items: [
        {
          marker_id: 'marker_favorite_active',
          kind: 'favorite',
          media_path: '/tmp/cut/clip_marker_a.mov',
          start_sec: 1.1,
          end_sec: 2.2,
          status: 'active',
          score: 1,
          text: '',
        },
        {
          marker_id: 'marker_comment_archived',
          kind: 'comment',
          media_path: '/tmp/cut/clip_marker_a.mov',
          start_sec: 2.3,
          end_sec: 3.0,
          status: 'archived',
          score: 0.7,
          text: 'archived note',
        },
      ],
    },
    recent_jobs: [],
    active_jobs: [],
    runtime_ready: true,
    graph_ready: true,
    waveform_ready: false,
    transcript_ready: false,
    thumbnail_ready: true,
    audio_sync_ready: false,
    slice_ready: false,
    timecode_sync_ready: false,
    sync_surface_ready: false,
    meta_sync_ready: false,
    time_markers_ready: true,
  };
}

async function installDebugMarkerMocks(page, requestLog, markerBodies) {
  const state = createProjectState();
  let markerCounter = 0;

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

    if (url.pathname === '/api/cut/time-markers/apply') {
      const body = request.postDataJSON();
      markerBodies.push(body);
      if (body.op === 'create') {
        markerCounter += 1;
        state.time_marker_bundle.items.push({
          marker_id: `marker_created_${markerCounter}`,
          kind: body.kind,
          media_path: body.media_path,
          start_sec: body.start_sec,
          end_sec: body.end_sec,
          status: 'active',
          score: body.score,
          text: body.text || '',
          context_slice: body.context_slice || null,
          cam_payload: body.cam_payload || null,
        });
      }
      await new Promise((resolve) => setTimeout(resolve, 120));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
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

test.describe.serial('phase170 cut debug marker-actions smoke', () => {
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('creates selected-shot markers and toggles archived marker visibility safely', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    const markerBodies = [];
    await installDebugMarkerMocks(page, requestLog, markerBodies);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('proj_marker_smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByText('Project').first()).toBeVisible();
    await page.locator('button[title="Toggle NLE / Debug view"]').click();
    await expect(page.getByText('VETKA CUT')).toBeVisible();
    await expect(page.getByText('clip_marker_a.mov', { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/markers for shot:\s*1/)).toBeVisible();
    await expect(page.getByText('Favorite Markers').first()).toBeVisible();
    await expect(page.getByText('Comment Markers')).toHaveCount(0);

    await page.getByRole('button', { name: 'Show All Markers' }).click();
    await expect(page.getByRole('button', { name: 'Show Active Only' })).toBeVisible();
    await expect(page.getByText(/markers for shot:\s*2/)).toBeVisible();
    await expect(page.getByText('Comment Markers').first()).toBeVisible();

    await page.getByRole('button', { name: 'Show Active Only' }).click();
    await expect(page.getByRole('button', { name: 'Show All Markers' })).toBeVisible();
    await expect(page.getByText(/markers for shot:\s*1/)).toBeVisible();

    await page.getByRole('button', { name: 'Favorite Selected' }).click();
    await expect(page.getByText('Creating favorite moment...')).toBeVisible();

    page.once('dialog', (dialog) => dialog.accept('smoke comment'));
    await page.getByRole('button', { name: 'Comment Selected' }).click();
    await expect(page.getByText('Creating comment marker...')).toBeVisible();

    page.once('dialog', (dialog) => dialog.accept('cam context'));
    await page.getByRole('button', { name: 'CAM Selected' }).click();
    await expect(page.getByText('Creating CAM marker...')).toBeVisible();

    await expect(page.getByText(/markers for shot:\s*4/)).toBeVisible();
    await expect(page.getByText('Favorite Markers').first()).toBeVisible();
    await expect(page.getByText('Comment Markers').first()).toBeVisible();
    await expect(page.getByText('CAM Markers').first()).toBeVisible();
    await expect(page.getByText(/cam markers:\s*1/)).toBeVisible();
    await expect(page.getByText(/status:\s*context-linked markers detected/)).toBeVisible();
    await expect(page.getByText('smoke comment').first()).toBeVisible();
    await expect(page.getByText('cam context').first()).toBeVisible();

    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
    expect(await page.evaluate(() => window.localStorage.getItem('vetka_last_runtime_error'))).toBeNull();

    expect(markerBodies).toHaveLength(3);
    expect(markerBodies.map((body) => body.kind)).toEqual(['favorite', 'comment', 'cam']);
    expect(markerBodies.every((body) => body.op === 'create')).toBe(true);
    expect(markerBodies[1].text).toBe('smoke comment');
    expect(markerBodies[2].cam_payload.hint).toBe('cam context');
    expect(requestLog.some((entry) => entry.pathname === '/api/cut/project-state')).toBe(true);
    expect(requestLog.filter((entry) => entry.pathname === '/api/cut/time-markers/apply')).toHaveLength(3);
  });
});
