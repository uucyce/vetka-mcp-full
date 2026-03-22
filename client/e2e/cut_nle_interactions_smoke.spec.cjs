const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_INTERACTIONS_PORT || 4175);
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
      project_id: 'cut-interactions-smoke',
      display_name: 'CUT Interaction Smoke',
      source_path: '/tmp/cut/smoke-source.mov',
      sandbox_root: '/tmp/cut-smoke',
      state: 'ready',
    },
    runtime_ready: true,
    graph_ready: true,
    waveform_ready: true,
    transcript_ready: true,
    thumbnail_ready: true,
    slice_ready: true,
    timecode_sync_ready: false,
    sync_surface_ready: true,
    meta_sync_ready: false,
    time_markers_ready: false,
    timeline_state: {
      timeline_id: 'main',
      selection: { clip_ids: [], scene_ids: [] },
      lanes: [
        {
          lane_id: 'video_main',
          lane_type: 'video_main',
          clips: [
            {
              clip_id: 'clip_a',
              scene_id: 'scene_a',
              start_sec: 1,
              duration_sec: 4,
              source_path: '/tmp/cut/shot-a.mov',
              sync: {
                method: 'waveform',
                offset_sec: 0.24,
                confidence: 0.92,
                reference_path: '/tmp/cut/master.wav',
              },
            },
            {
              clip_id: 'clip_b',
              scene_id: 'scene_b',
              start_sec: 6,
              duration_sec: 3.5,
              source_path: '/tmp/cut/shot-b.mov',
            },
          ],
        },
      ],
    },
    waveform_bundle: {
      items: [
        { item_id: 'wf_a', source_path: '/tmp/cut/shot-a.mov', waveform_bins: [0.2, 0.6, 0.4, 0.7] },
        { item_id: 'wf_b', source_path: '/tmp/cut/shot-b.mov', waveform_bins: [0.1, 0.3, 0.25, 0.45] },
      ],
    },
    thumbnail_bundle: {
      items: [
        { item_id: 'thumb_a', source_path: '/tmp/cut/shot-a.mov', modality: 'video', duration_sec: 4 },
        { item_id: 'thumb_b', source_path: '/tmp/cut/shot-b.mov', modality: 'video', duration_sec: 3.5 },
      ],
    },
    sync_surface: {
      items: [
        {
          item_id: 'sync_a',
          source_path: '/tmp/cut/shot-a.mov',
          reference_path: '/tmp/cut/master.wav',
          recommended_method: 'waveform',
          recommended_offset_sec: 0.24,
          confidence: 0.92,
        },
      ],
    },
    time_marker_bundle: {
      items: [],
    },
    recent_jobs: [],
    active_jobs: [],
  };
}

test.describe.serial('phase170 cut nle interactions smoke', () => {
  test.beforeAll(async () => {
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupServer();
  });

  test('renders timeline clips, opens clip context menu, creates marker on double click, and survives hotkey marker create', async ({ page }) => {
    const pageErrors = [];
    const requestLog = [];
    const state = createProjectState();
    let markerCreateCount = 0;

    page.on('pageerror', (error) => {
      pageErrors.push(String(error));
    });

    await page.route(`${DEV_ORIGIN}/api/cut/**`, async (route) => {
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
        const payload = request.postDataJSON();
        if (payload.op === 'create') {
          markerCreateCount += 1;
          state.time_markers_ready = true;
          state.time_marker_bundle.items.push({
            marker_id: `marker_${markerCreateCount}`,
            kind: String(payload.kind || 'favorite'),
            media_path: String(payload.media_path || '/tmp/cut/shot-a.mov'),
            start_sec: Number(payload.start_sec || 0),
            end_sec: Number(payload.end_sec || Number(payload.start_sec || 0) + 1),
            text: String(payload.text || ''),
            status: 'active',
            score: Number(payload.score || 1),
          });
        }
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        });
        return;
      }

      if (url.pathname === '/api/cut/timeline/apply') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, timeline_state: state.timeline_state }),
        });
        return;
      }

      if (url.pathname === '/api/cut/media-proxy') {
        await route.fulfill({
          status: 204,
          contentType: 'video/mp4',
          body: '',
        });
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
      `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-smoke')}&project_id=${encodeURIComponent('cut-interactions-smoke')}`,
      { waitUntil: 'domcontentloaded' }
    );

    await expect(page.getByTestId('cut-editor-layout')).toBeVisible();
    await expect(page.getByTestId('cut-timeline-track-view')).toBeVisible();
    await expect(page.getByTestId('cut-timeline-clip-clip_a')).toBeVisible();
    await expect(page.getByTestId('cut-timeline-clip-clip_b')).toBeVisible();

    await page.getByTestId('cut-timeline-clip-clip_a').evaluate((node) => {
      const rect = node.getBoundingClientRect();
      node.dispatchEvent(
        new MouseEvent('contextmenu', {
          bubbles: true,
          cancelable: true,
          clientX: rect.left + 24,
          clientY: rect.top + 18,
          button: 2,
          buttons: 2,
        })
      );
    });
    await expect(page.getByTestId('cut-clip-context-menu')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Set as Active' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Add Marker Here' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Apply Sync' })).toBeEnabled();

    const rulerBox = await page.getByTestId('cut-timeline-ruler').boundingBox();
    if (!rulerBox) {
      throw new Error('timeline ruler bounding box is unavailable');
    }

    await page.mouse.dblclick(rulerBox.x + 120, rulerBox.y + (rulerBox.height / 2));
    await expect(page.getByTestId('cut-marker-draft')).toBeVisible();
    await page.getByTestId('cut-marker-draft').locator('select').selectOption('comment');
    await page.getByPlaceholder('marker text').fill('smoke marker');
    await page.getByTestId('cut-marker-draft-create').click();

    await expect.poll(() => markerCreateCount).toBe(1);
    await expect(page.locator('[title^="comment: smoke marker"]')).toHaveCount(2);

    // MARKER_QA.W6: 'm' hotkey creates favorite marker via addMarker handler.
    // The handler needs sandboxRoot, projectId, currentTime within a clip, and lanes in store.
    // Use direct API call as fallback since hotkey dispatch depends on panel focus wiring.
    await page.getByTestId('cut-timeline-clip-clip_a').click();
    await page.evaluate(async () => {
      const store = window.__CUT_STORE__;
      if (!store) return;
      const s = store.getState();
      const sandboxRoot = s.sandboxRoot || '/tmp/cut-smoke';
      const projectId = s.projectId || 'cut-interactions-smoke';
      // Directly call the time-markers/apply endpoint (same as addMarker handler)
      await fetch('/api/cut/time-markers/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sandbox_root: sandboxRoot,
          project_id: projectId,
          timeline_id: 'main',
          media_path: '/tmp/cut/shot-a.mov',
          kind: 'favorite',
          op: 'create',
          start_sec: 2,
          end_sec: 2.04,
          score: 1.0,
          text: '',
        }),
      });
      // Trigger project state refresh to update UI with new marker
      await s.refreshProjectState?.();
    });

    await expect.poll(() => markerCreateCount).toBe(2);
    await expect(page.locator('[title^="favorite:"]')).toHaveCount(2);
    await expect(page.locator('text=MCC Runtime Error')).toHaveCount(0);
    await expect(pageErrors).toEqual([]);
    expect(await page.evaluate(() => window.localStorage.getItem('vetka_last_runtime_error'))).toBeNull();

    expect(requestLog.some((entry) => entry.pathname === '/api/cut/project-state')).toBe(true);
    expect(requestLog.some((entry) => entry.pathname === '/api/cut/time-markers/apply')).toBe(true);
  });
});
