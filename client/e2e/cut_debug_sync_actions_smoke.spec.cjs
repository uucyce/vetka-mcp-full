const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_DEBUG_SYNC_PORT || 4178);
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
      project_id: 'proj_sync_smoke',
      display_name: 'CUT Sync Smoke',
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
              clip_id: 'clip_sync_a',
              scene_id: 'scene_sync_a',
              start_sec: 2,
              duration_sec: 5,
              source_path: '/tmp/cut/clip_sync_a.mov',
            },
          ],
        },
      ],
    },
    scene_graph: { nodes: [{ node_id: 'scene_sync_a', node_type: 'scene', label: 'Scene Sync A' }] },
    waveform_bundle: { items: [] },
    transcript_bundle: { items: [] },
    thumbnail_bundle: {
      items: [
        {
          item_id: 'thumb_sync_a',
          source_path: '/tmp/cut/clip_sync_a.mov',
          modality: 'video',
          duration_sec: 5,
        },
      ],
    },
    audio_sync_result: {
      items: [
        {
          item_id: 'audio_sync_a',
          source_path: '/tmp/cut/clip_sync_a.mov',
          reference_path: '/tmp/cut/master.wav',
          detected_offset_sec: 0.24,
          confidence: 0.93,
          method: 'peaks+correlation',
        },
      ],
    },
    slice_bundle: { items: [] },
    timecode_sync_result: { items: [] },
    sync_surface: {
      schema_version: 'cut_sync_surface_v1',
      items: [
        {
          item_id: 'sync_surface_a',
          source_path: '/tmp/cut/clip_sync_a.mov',
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
    runtime_ready: true,
    graph_ready: true,
    waveform_ready: false,
    transcript_ready: false,
    thumbnail_ready: true,
    audio_sync_ready: true,
    slice_ready: false,
    timecode_sync_ready: false,
    sync_surface_ready: true,
    meta_sync_ready: false,
    time_markers_ready: false,
  };
}

async function installDebugSyncMocks(page, requestLog, applyBodies) {
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
      applyBodies.push(body);
      const ops = Array.isArray(body.ops) ? body.ops : [];
      const firstOp = ops[0] || {};
      if (firstOp.op === 'set_selection') {
        state.timeline_state.selection = {
          clip_ids: firstOp.clip_ids || [],
          scene_ids: firstOp.scene_ids || [],
        };
      }
      if (firstOp.op === 'apply_sync_offset') {
        state.timeline_state.lanes[0].clips[0].sync = {
          method: firstOp.method,
          offset_sec: firstOp.offset_sec,
          confidence: firstOp.confidence,
          reference_path: firstOp.reference_path,
        };
      }
      await new Promise((resolve) => setTimeout(resolve, 120));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, timeline_state: state.timeline_state }),
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

test.describe.serial('phase170 cut debug sync-actions smoke', () => {
  test.setTimeout(90000);

  test.beforeAll(async ({}, testInfo) => {
    testInfo.setTimeout(90000);
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('selected-shot sync actions call timeline apply and keep shell stable', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    const applyBodies = [];
    await installDebugSyncMocks(page, requestLog, applyBodies);
    page.on('pageerror', (error) => pageErrors.push(String(error)));

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('proj_sync_smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByText('Project').first()).toBeVisible();
    await page.click('button:text-is("View")'); await page.waitForTimeout(200); await page.click('text=Toggle NLE / Debug');
    await expect(page.getByText('VETKA CUT')).toBeVisible();

    await expect(page.getByText('clip_sync_a.mov', { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/timeline link:\s*clip_sync_a/)).toBeVisible();
    await expect(page.getByText(/sync hint:\s*0.240s via peaks\+correlation/)).toBeVisible();
    await expect(page.getByText(/recommended sync:\s*waveform 0.240s/)).toBeVisible();

    await page.getByRole('button', { name: 'Sync Timeline Selection' }).click();
    await expect(page.getByText('Syncing selected shot to timeline...')).toBeVisible();
    await expect(page.getByText('Runtime ready')).toBeVisible();

    await page.getByRole('button', { name: 'Apply Sync Offset' }).click();
    await expect(page.getByText('Applying sync offset to timeline...')).toBeVisible();
    await expect(page.getByText('Runtime ready')).toBeVisible();

    await page.getByRole('button', { name: /Apply All Syncs \(1\)/ }).click();
    await expect(page.getByText('Applying 1 sync offset(s)...')).toBeVisible();
    await expect(page.getByText('Applied 1 sync offset(s).')).toBeVisible();

    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
    expect(await page.evaluate(() => window.localStorage.getItem('vetka_last_runtime_error'))).toBeNull();

    expect(applyBodies).toHaveLength(3);
    expect(applyBodies[0].ops[0].op).toBe('set_selection');
    expect(applyBodies[0].ops[1].op).toBe('set_view');
    expect(applyBodies[1].ops[0].op).toBe('apply_sync_offset');
    expect(applyBodies[1].ops[0].clip_id).toBe('clip_sync_a');
    expect(applyBodies[2].ops).toHaveLength(1);
    expect(applyBodies[2].ops[0].op).toBe('apply_sync_offset');

    expect(requestLog.some((entry) => entry.pathname === '/api/cut/project-state')).toBe(true);
    expect(requestLog.filter((entry) => entry.pathname === '/api/cut/timeline/apply')).toHaveLength(3);
  });
});
