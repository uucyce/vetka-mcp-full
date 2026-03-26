/**
 * MARKER_QA.MULTICAM_TDD: TDD E2E tests for MulticamViewer.
 *
 * Verifies Beta's MulticamViewer (MARKER_MULTICAM_VIEWER):
 *   MC1: Empty state — no grid when multicamMode=false
 *   MC2: Grid renders with angle cells after setMulticam
 *   MC3: Active angle border highlight
 *   MC4: Click switches active angle
 *   MC5: Grid columns scale (2-col ≤4, 3-col >4)
 *   MC6: clearMulticam hides grid
 *
 * @phase 198
 * @agent epsilon
 * @verifies tb_1774419069_1 (DELTA-QA: Replace vacuous multicam test)
 */
const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

// ---------------------------------------------------------------------------
// Server bootstrap
// ---------------------------------------------------------------------------
const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_MULTICAM_PORT || 3012);
const DEV_ORIGIN = `http://127.0.0.1:${DEV_PORT}`;
const CUT_URL = `${DEV_ORIGIN}/cut`;

let serverProcess = null;
let serverStartedBySpec = false;
let serverLogs = '';

function waitForHttpOk(url, timeoutMs = 30000) {
  const startedAt = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(url, (res) => {
        res.resume();
        if ((res.statusCode || 0) < 500) { resolve(); return; }
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
  try { await waitForHttpOk(DEV_ORIGIN, 1500); return; } catch { /* start below */ }
  serverStartedBySpec = true;
  serverProcess = spawn(
    'npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(DEV_PORT)],
    { cwd: CLIENT_DIR, env: { ...process.env, BROWSER: 'none', CI: '1' }, stdio: ['ignore', 'pipe', 'pipe'] }
  );
  const capture = (chunk) => {
    serverLogs += chunk.toString();
    if (serverLogs.length > 20000) serverLogs = serverLogs.slice(-20000);
  };
  serverProcess.stdout.on('data', capture);
  serverProcess.stderr.on('data', capture);
  await waitForHttpOk(DEV_ORIGIN, 30000);
}

function cleanupServer() {
  if (serverProcess && serverStartedBySpec) { serverProcess.kill('SIGTERM'); serverProcess = null; }
}

// ---------------------------------------------------------------------------
// Project fixture
// ---------------------------------------------------------------------------
function createMulticamTestProject() {
  return {
    success: true,
    schema_version: 'cut_project_state_v1',
    project: {
      project_id: 'cut-multicam-tdd',
      display_name: 'Multicam Viewer TDD',
      source_path: '/tmp/cut/multicam.mov',
      sandbox_root: '/tmp/cut-multicam',
      state: 'ready',
    },
    runtime_ready: true, graph_ready: true, waveform_ready: true,
    transcript_ready: false, thumbnail_ready: true, slice_ready: true,
    timecode_sync_ready: false, sync_surface_ready: false,
    meta_sync_ready: false, time_markers_ready: false,
    timeline_state: {
      timeline_id: 'main',
      selection: { clip_ids: ['v_a'], scene_ids: [] },
      lanes: [
        {
          lane_id: 'V1', lane_type: 'video_main',
          clips: [
            { clip_id: 'v_a', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/a.mov' },
            { clip_id: 'v_b', scene_id: 's2', start_sec: 5, duration_sec: 4, source_path: '/tmp/b.mov' },
          ],
        },
        {
          lane_id: 'A1', lane_type: 'audio_main',
          clips: [
            { clip_id: 'a_a', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/a.wav' },
          ],
        },
      ],
    },
    waveform_bundle: { items: [] },
    thumbnail_bundle: { items: [] },
    sync_surface: { items: [] },
    time_marker_bundle: { items: [] },
    recent_jobs: [], active_jobs: [],
  };
}

async function setupApiMocks(page) {
  const state = createMulticamTestProject();
  await page.route(`${DEV_ORIGIN}/api/cut/**`, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/cut/project-state') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
  });
}

async function navigateToCut(page) {
  await setupApiMocks(page);
  await page.goto(CUT_URL, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="cut-timeline-track-view"]', { timeout: 15000 });
}

// ===========================================================================
// Multicam Viewer TDD
// ===========================================================================
test.describe.serial('Multicam Viewer TDD', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  /**
   * MC1: Empty state — no multicam grid when mode is off.
   *
   * MulticamViewer should NOT render its grid container when
   * multicamMode=false (the default store state).
   */
  test('MC1: no multicam-viewer-grid when multicamMode=false', async ({ page }) => {
    await navigateToCut(page);

    // Ensure store is in clean state — call clearMulticam if available
    await page.evaluate(() => {
      if (window.__CUT_STORE__) {
        const state = window.__CUT_STORE__.getState();
        if (typeof state.clearMulticam === 'function') {
          state.clearMulticam();
        }
      }
    });
    await page.waitForTimeout(200);

    const gridCount = await page.locator('[data-testid="multicam-viewer-grid"]').count();
    expect(gridCount).toBe(0);
  });

  /**
   * MC2: Grid renders after setMulticam with 2 angles.
   *
   * After calling setMulticam('mc-test', [{...}, {...}]), the viewer
   * should mount its grid and two angle cells.
   */
  test('MC2: grid renders with angle cells after setMulticam(2 angles)', async ({ page }) => {
    await navigateToCut(page);

    await page.evaluate(() => {
      window.__CUT_STORE__.getState().setMulticam('mc-test', [
        { source_path: '/tmp/cam1.mov', label: 'CAM1', offset_sec: 0 },
        { source_path: '/tmp/cam2.mov', label: 'CAM2', offset_sec: 0 },
      ]);
    });
    await page.waitForTimeout(200);

    await expect(page.locator('[data-testid="multicam-viewer-grid"]')).toBeVisible();
    await expect(page.locator('[data-testid="multicam-angle-0"]')).toBeVisible();
    await expect(page.locator('[data-testid="multicam-angle-1"]')).toBeVisible();
  });

  /**
   * MC3: Active angle (index 0) has highlight border; inactive has transparent border.
   *
   * MulticamViewer uses:
   *   active:   border: 1px solid #999  (rgb(153, 153, 153))
   *   inactive: border: 1px solid transparent
   */
  test('MC3: active angle has highlight border, inactive has transparent border', async ({ page }) => {
    await navigateToCut(page);

    await page.evaluate(() => {
      window.__CUT_STORE__.getState().setMulticam('mc-test', [
        { source_path: '/tmp/cam1.mov', label: 'CAM1', offset_sec: 0 },
        { source_path: '/tmp/cam2.mov', label: 'CAM2', offset_sec: 0 },
      ]);
    });
    await page.waitForTimeout(200);

    // Angle 0 is active by default — should have #999 / rgb(153, 153, 153) border
    const angle0Border = await page.evaluate(() => {
      const el = document.querySelector('[data-testid="multicam-angle-0"]');
      if (!el) return '';
      return window.getComputedStyle(el).borderColor;
    });
    const angle0Active = angle0Border.includes('153, 153, 153') || angle0Border.includes('#999');
    expect(angle0Active).toBe(true);

    // Angle 1 is inactive — transparent border resolves to rgba(0, 0, 0, 0)
    const angle1Border = await page.evaluate(() => {
      const el = document.querySelector('[data-testid="multicam-angle-1"]');
      if (!el) return '';
      return window.getComputedStyle(el).borderColor;
    });
    const angle1Inactive = angle1Border.includes('0, 0, 0, 0') || angle1Border.includes('transparent');
    expect(angle1Inactive).toBe(true);
  });

  /**
   * MC4: Clicking an angle calls multicamSwitchAngle and updates multicamActiveAngle.
   *
   * After clicking angle-1, the store's multicamActiveAngle should be 1.
   */
  test('MC4: clicking angle-1 sets multicamActiveAngle=1', async ({ page }) => {
    await navigateToCut(page);

    await page.evaluate(() => {
      window.__CUT_STORE__.getState().setMulticam('mc-test', [
        { source_path: '/tmp/cam1.mov', label: 'CAM1', offset_sec: 0 },
        { source_path: '/tmp/cam2.mov', label: 'CAM2', offset_sec: 0 },
      ]);
    });
    await page.waitForTimeout(200);

    await page.locator('[data-testid="multicam-angle-1"]').click();
    await page.waitForTimeout(200);

    const activeAngle = await page.evaluate(() => {
      return window.__CUT_STORE__.getState().multicamActiveAngle;
    });
    expect(activeAngle).toBe(1);
  });

  /**
   * MC5: Grid columns scale with angle count.
   *
   * >4 angles should use repeat(3, ...) in gridTemplateColumns.
   * <=4 angles should use repeat(2, ...).
   */
  test('MC5: grid uses 3 columns for >4 angles', async ({ page }) => {
    await navigateToCut(page);

    await page.evaluate(() => {
      window.__CUT_STORE__.getState().setMulticam('mc-test-5', [
        { source_path: '/tmp/cam1.mov', label: 'CAM1', offset_sec: 0 },
        { source_path: '/tmp/cam2.mov', label: 'CAM2', offset_sec: 0 },
        { source_path: '/tmp/cam3.mov', label: 'CAM3', offset_sec: 0 },
        { source_path: '/tmp/cam4.mov', label: 'CAM4', offset_sec: 0 },
        { source_path: '/tmp/cam5.mov', label: 'CAM5', offset_sec: 0 },
      ]);
    });
    await page.waitForTimeout(200);

    const colCount = await page.evaluate(() => {
      const el = document.querySelector('[data-testid="multicam-viewer-grid"]');
      if (!el) return 0;
      // getComputedStyle returns resolved values like "100px 100px 100px"
      const cols = window.getComputedStyle(el).gridTemplateColumns;
      return cols.split(/\s+/).length;
    });

    // For 5 angles (>4), should be 3-column layout
    expect(colCount).toBe(3);
  });

  /**
   * MC6: clearMulticam hides the grid.
   *
   * After clearMulticam(), multicamMode resets to false and the grid
   * should no longer be in the DOM.
   */
  test('MC6: clearMulticam hides multicam-viewer-grid', async ({ page }) => {
    await navigateToCut(page);

    // First set multicam so the grid is visible
    await page.evaluate(() => {
      window.__CUT_STORE__.getState().setMulticam('mc-test', [
        { source_path: '/tmp/cam1.mov', label: 'CAM1', offset_sec: 0 },
        { source_path: '/tmp/cam2.mov', label: 'CAM2', offset_sec: 0 },
      ]);
    });
    await page.waitForTimeout(200);

    // Verify grid is present before clearing
    await expect(page.locator('[data-testid="multicam-viewer-grid"]')).toBeVisible();

    // Now clear
    await page.evaluate(() => {
      window.__CUT_STORE__.getState().clearMulticam();
    });
    await page.waitForTimeout(200);

    const gridCount = await page.locator('[data-testid="multicam-viewer-grid"]').count();
    expect(gridCount).toBe(0);
  });
});
