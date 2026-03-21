const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_DEBUG_MARKER_FOCUS_PORT || 4180);
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
      project_id: 'proj_marker_focus_smoke',
      display_name: 'CUT Marker Focus Smoke',
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
              clip_id: 'clip_focus_a',
              scene_id: 'scene_focus_a',
              start_sec: 1,
              duration_sec: 5,
              source_path: '/tmp/cut/clip_focus_a.mov',
            },
          ],
        },
      ],
    },
    scene_graph: { nodes: [{ node_id: 'scene_focus_a', node_type: 'scene', label: 'Scene Focus A' }] },
    waveform_bundle: { items: [] },
    transcript_bundle: { items: [] },
    thumbnail_bundle: {
      items: [
        {
          item_id: 'thumb_focus_a',
          source_path: '/tmp/cut/clip_focus_a.mov',
          modality: 'video',
          duration_sec: 5,
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
          marker_id: 'marker_focus_active',
          kind: 'favorite',
          media_path: '/tmp/cut/clip_focus_a.mov',
          start_sec: 1.2,
          end_sec: 2.4,
          status: 'active',
          score: 1,
          text: '',
          context_slice: { mode: 'preview_fallback', derived_from: 'thumbnail_bundle' },
        },
        {
          marker_id: 'marker_global_cam_active',
          kind: 'cam',
          media_path: '/tmp/cut/clip_focus_a.mov',
          start_sec: 2.8,
          end_sec: 3.6,
          status: 'active',
          score: 0.85,
          text: 'cam note',
          context_slice: { mode: 'preview_fallback', derived_from: 'thumbnail_bundle' },
          cam_payload: { source: 'cut_shell', status: 'placeholder', hint: 'cam note' },
        },
        {
          marker_id: 'marker_comment_archived',
          kind: 'comment',
          media_path: '/tmp/cut/clip_focus_a.mov',
          start_sec: 3.7,
          end_sec: 4.1,
          status: 'archived',
          score: 0.7,
          text: 'archived note',
          context_slice: { mode: 'preview_fallback', derived_from: 'thumbnail_bundle' },
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

async function installMarkerArchiveFocusMocks(page, requestLog, timelineBodies, markerBodies) {
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

    if (url.pathname === '/api/cut/timeline/apply') {
      const body = request.postDataJSON();
      timelineBodies.push(body);
      const secondOp = Array.isArray(body.ops) ? body.ops[1] : null;
      if (secondOp?.op === 'set_view') {
        state.timeline_state.selection = {
          clip_ids: body.ops[0]?.clip_ids || [],
          scene_ids: body.ops[0]?.scene_ids || [],
        };
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, timeline_state: state.timeline_state }),
      });
      return;
    }

    if (url.pathname === '/api/cut/time-markers/apply') {
      const body = request.postDataJSON();
      markerBodies.push(body);
      if (body.op === 'archive') {
        const marker = state.time_marker_bundle.items.find((item) => item.marker_id === body.marker_id);
        if (marker) marker.status = 'archived';
      }
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

test.describe.serial('phase170 cut debug marker archive/focus smoke', () => {
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('focuses a selected-shot marker, archives a global marker, and toggles global visibility safely', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    const timelineBodies = [];
    const markerBodies = [];
    await installMarkerArchiveFocusMocks(page, requestLog, timelineBodies, markerBodies);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('proj_marker_focus_smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByText('Project').first()).toBeVisible();
    await page.click('button:text-is("View")'); await page.waitForTimeout(200); await page.click('text=Toggle NLE / Debug');
    await expect(page.getByText('VETKA CUT')).toBeVisible();
    await expect(page.getByText(/markers for shot:\s*2/).first()).toBeVisible();
    await expect(page.getByText(/favorite:\s*1 .* comment:\s*0 .* cam:\s*1/).first()).toBeVisible();
    await expect(page.getByText('Comment Markers')).toHaveCount(0);

    await page.getByRole('button', { name: 'Focus Marker In Timeline' }).first().click();
    await expect.poll(() => timelineBodies.length).toBe(1);
    await expect(page.getByText('Runtime ready')).toBeVisible();

    await page.getByRole('button', { name: 'Show All Global Markers' }).click();
    await expect(page.getByRole('button', { name: 'Show Active Global Only' })).toBeVisible();
    await expect(page.getByText(/favorite:\s*1 .* comment:\s*1 .* cam:\s*1/).first()).toBeVisible();
    await expect(page.getByText('Comment Markers').first()).toBeVisible();
    await expect(page.getByText('archived note').first()).toBeVisible();

    await page.getByRole('button', { name: 'Archive Marker' }).first().click();
    await expect.poll(() => markerBodies.length).toBe(1);
    await expect(page.getByText(/favorite:\s*1 .* comment:\s*1 .* cam:\s*1/).first()).toBeVisible();
    await expect(page.getByText(/1.2s - 2.4s .* archived/).first()).toBeVisible();

    await page.getByRole('button', { name: 'Show Active Global Only' }).click();
    await expect(page.getByRole('button', { name: 'Show All Global Markers' })).toBeVisible();
    await expect(page.getByText(/favorite:\s*0 .* comment:\s*0 .* cam:\s*1/).first()).toBeVisible();

    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
    expect(await page.evaluate(() => window.localStorage.getItem('vetka_last_runtime_error'))).toBeNull();

    expect(timelineBodies).toHaveLength(1);
    expect(timelineBodies[0].ops[0].op).toBe('set_selection');
    expect(timelineBodies[0].ops[1].op).toBe('set_view');
    expect(timelineBodies[0].ops[1].scroll_sec).toBe(1.2);

    expect(markerBodies).toHaveLength(1);
    expect(markerBodies[0].op).toBe('archive');
    expect(markerBodies[0].marker_id).toBe('marker_focus_active');
    expect(requestLog.some((entry) => entry.pathname === '/api/cut/project-state')).toBe(true);
    expect(requestLog.some((entry) => entry.pathname === '/api/cut/timeline/apply')).toBe(true);
    expect(requestLog.some((entry) => entry.pathname === '/api/cut/time-markers/apply')).toBe(true);
  });
});
