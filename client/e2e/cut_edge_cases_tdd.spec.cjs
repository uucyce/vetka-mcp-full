/**
 * MARKER_QA.EDGE: TDD tests for edge-case bugs found during Epsilon bug hunt.
 *
 * Tests document bugs that exist NOW — they will turn GREEN when Alpha fixes them.
 *
 * Bugs covered:
 *   SEEK-CLAMP: seek() beyond duration should clamp to max
 *   SEEK-NEG: seek(-10) should clamp to 0 (already works)
 *   DBLCLICK: double-click clip should open in Source Monitor
 *   EMPTY-SRC: video element should not have src="" (causes re-download)
 *   EMPTY-LANES: timeline with 0 clips should not crash
 *   RAPID-TOOL: rapid tool switching should not race
 *
 * @phase 196
 * @agent Epsilon (QA-2)
 * @task tb_1774243820_22
 */
const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_EDGE_PORT || 4201);
const DEV_ORIGIN = `http://127.0.0.1:${DEV_PORT}`;
const CUT_URL = `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-edge')}&project_id=edge-tdd`;

let serverProcess = null;
let serverStartedBySpec = false;
let serverLogs = '';

function waitForHttpOk(url, timeoutMs = 30000) {
  const startedAt = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => { const req = http.get(url, (res) => { res.resume(); if ((res.statusCode || 0) < 500) resolve(); else retry(); }); req.on('error', retry); };
    const retry = () => { if (Date.now() - startedAt >= timeoutMs) reject(new Error(`Timed out\n${serverLogs}`)); else setTimeout(tick, 200); };
    tick();
  });
}

async function ensureDevServer() {
  try { await waitForHttpOk(DEV_ORIGIN, 1500); return; } catch { /* start */ }
  serverStartedBySpec = true;
  serverProcess = spawn('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(DEV_PORT)],
    { cwd: CLIENT_DIR, env: { ...process.env, BROWSER: 'none', CI: '1' }, stdio: ['ignore', 'pipe', 'pipe'] });
  const cap = (c) => { serverLogs += c.toString(); if (serverLogs.length > 20000) serverLogs = serverLogs.slice(-20000); };
  serverProcess.stdout.on('data', cap); serverProcess.stderr.on('data', cap);
  await waitForHttpOk(DEV_ORIGIN, 30000);
}

function cleanupServer() { if (serverProcess && serverStartedBySpec) { serverProcess.kill('SIGTERM'); serverProcess = null; } }

function createProject() {
  return {
    success: true, schema_version: 'cut_project_state_v1',
    project: { project_id: 'edge-tdd', display_name: 'Edge TDD', source_path: '/tmp/edge.mov', sandbox_root: '/tmp/cut-edge', state: 'ready', framerate: 25 },
    runtime_ready: true, graph_ready: true, waveform_ready: true,
    transcript_ready: false, thumbnail_ready: true, slice_ready: true,
    timecode_sync_ready: false, sync_surface_ready: false, meta_sync_ready: false, time_markers_ready: false,
    timeline_state: {
      timeline_id: 'main', selection: { clip_ids: [], scene_ids: [] },
      lanes: [
        { lane_id: 'V1', lane_type: 'video_main', clips: [
          { clip_id: 'e_v1', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/a.mov' },
          { clip_id: 'e_v2', scene_id: 's2', start_sec: 5, duration_sec: 4, source_path: '/tmp/b.mov' },
        ]},
        { lane_id: 'A1', lane_type: 'audio_main', clips: [
          { clip_id: 'e_a1', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/a.wav' },
        ]},
      ],
    },
    waveform_bundle: { items: [] }, thumbnail_bundle: { items: [] },
    sync_surface: { items: [] }, time_marker_bundle: { items: [] },
    recent_jobs: [], active_jobs: [],
  };
}

async function setupMocks(page) {
  const state = createProject();
  await page.route(`${DEV_ORIGIN}/api/cut/**`, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/cut/project-state') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{"success":true}' });
  });
}

async function navigateToCut(page) {
  await setupMocks(page);
  await page.goto(CUT_URL, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="cut-timeline-track-view"]', { timeout: 15000 });
  await page.waitForSelector('[data-testid^="cut-timeline-clip-"]', { timeout: 10000 }).catch(() => {});
}

// ===========================================================================
// SEEK EDGE CASES
// ===========================================================================
test.describe('EDGE: Seek Boundary', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  test('EDGE-SEEK1: seek beyond duration clamps to duration', async ({ page }) => {
    await navigateToCut(page);
    // Set a known duration
    await page.evaluate(() => {
      const s = window.__CUT_STORE__?.getState();
      if (s) { s.setDuration(12.0); s.seek(99999); }
    });
    await page.waitForTimeout(100);
    const time = await page.evaluate(() => window.__CUT_STORE__?.getState().currentTime);
    // Should be clamped to duration (12.0), not 99999
    expect(time).toBeLessThanOrEqual(12.0);
  });

  test('EDGE-SEEK2: seek negative clamps to 0', async ({ page }) => {
    await navigateToCut(page);
    await page.evaluate(() => {
      const s = window.__CUT_STORE__?.getState();
      if (s) s.seek(-100);
    });
    await page.waitForTimeout(100);
    const time = await page.evaluate(() => window.__CUT_STORE__?.getState().currentTime);
    expect(time).toBe(0);
  });

  test('EDGE-SEEK3: seek to exactly 0 works', async ({ page }) => {
    await navigateToCut(page);
    await page.evaluate(() => {
      const s = window.__CUT_STORE__?.getState();
      if (s) { s.seek(5.0); s.seek(0); }
    });
    await page.waitForTimeout(100);
    const time = await page.evaluate(() => window.__CUT_STORE__?.getState().currentTime);
    expect(time).toBe(0);
  });
});

// ===========================================================================
// DOUBLE-CLICK CLIP
// ===========================================================================
test.describe('EDGE: Double-Click Clip', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  test('EDGE-DBLCLICK1: double-click clip opens it in Source Monitor', async ({ page }) => {
    await navigateToCut(page);
    const clip = page.locator('[data-testid="cut-timeline-clip-e_v1"]');
    if (await clip.isVisible().catch(() => false)) {
      await clip.dblclick();
      await page.waitForTimeout(500);
      const activeMedia = await page.evaluate(() => window.__CUT_STORE__?.getState().activeMedia);
      // Should set activeMedia to clip's source_path
      expect(activeMedia).not.toBeNull();
      expect(activeMedia).not.toBe('');
    }
  });
});

// ===========================================================================
// VIDEO ELEMENT SRC
// ===========================================================================
test.describe('EDGE: Video Element', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  test('EDGE-SRC1: no video element has empty src="" attribute', async ({ page }) => {
    await navigateToCut(page);
    const emptySrcCount = await page.evaluate(() => {
      const videos = document.querySelectorAll('video');
      let count = 0;
      videos.forEach(v => {
        if (v.hasAttribute('src') && v.getAttribute('src') === '') count++;
      });
      return count;
    });
    expect(emptySrcCount).toBe(0);
  });
});

// ===========================================================================
// EMPTY TIMELINE
// ===========================================================================
test.describe('EDGE: Empty Timeline', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  test('EDGE-EMPTY1: timeline with 0 clips does not crash', async ({ page }) => {
    await navigateToCut(page);
    // Remove all clips via store
    await page.evaluate(() => {
      const s = window.__CUT_STORE__?.getState();
      if (s?.setLanes) s.setLanes([
        { lane_id: 'V1', lane_type: 'video_main', clips: [] },
        { lane_id: 'A1', lane_type: 'audio_main', clips: [] },
      ]);
    });
    await page.waitForTimeout(300);

    // Timeline should still be visible (not crashed)
    const tlVisible = await page.locator('[data-testid="cut-timeline-track-view"]').isVisible();
    expect(tlVisible).toBe(true);

    // No clips rendered
    const clipCount = await page.evaluate(() =>
      document.querySelectorAll('[data-testid^="cut-timeline-clip-"]').length
    );
    expect(clipCount).toBe(0);
  });

  test('EDGE-EMPTY2: hotkeys work on empty timeline without crash', async ({ page }) => {
    await navigateToCut(page);
    await page.evaluate(() => {
      const s = window.__CUT_STORE__?.getState();
      if (s?.setLanes) s.setLanes([{ lane_id: 'V1', lane_type: 'video_main', clips: [] }]);
      if (s?.setFocusedPanel) s.setFocusedPanel('timeline');
    });
    await page.waitForTimeout(200);

    // These should not throw
    await page.keyboard.press('Space');
    await page.keyboard.press('i');
    await page.keyboard.press('o');
    await page.keyboard.press('Delete');
    await page.keyboard.press('Meta+k');
    await page.waitForTimeout(200);

    // Page still alive
    const alive = await page.evaluate(() => !!window.__CUT_STORE__);
    expect(alive).toBe(true);
  });
});

// ===========================================================================
// RAPID TOOL SWITCHING
// ===========================================================================
test.describe('EDGE: Rapid Tool Switching', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  test('EDGE-RAPID1: rapid V/C alternation settles on last key pressed', async ({ page }) => {
    await navigateToCut(page);
    await page.evaluate(() => window.__CUT_STORE__?.getState().setFocusedPanel('timeline'));

    // Rapid alternation: 8 key presses, last is 'c' (razor)
    for (const key of ['v', 'c', 'v', 'c', 'v', 'c', 'v', 'c']) {
      await page.keyboard.press(key);
    }
    await page.waitForTimeout(100);

    const tool = await page.evaluate(() => window.__CUT_STORE__?.getState().activeTool);
    expect(tool).toBe('razor');
  });

  test('EDGE-RAPID2: 20 rapid tool switches without crash', async ({ page }) => {
    await navigateToCut(page);
    await page.evaluate(() => window.__CUT_STORE__?.getState().setFocusedPanel('timeline'));

    const keys = ['v', 'c', 'y', 'u', 'b', 'n', 'v', 'c', 'y', 'u', 'b', 'n', 'v', 'c', 'y', 'u', 'b', 'n', 'v', 'c'];
    for (const k of keys) {
      await page.keyboard.press(k);
    }
    await page.waitForTimeout(100);

    // Last key = 'c' = razor
    const tool = await page.evaluate(() => window.__CUT_STORE__?.getState().activeTool);
    expect(tool).toBe('razor');

    // Page still alive
    const alive = await page.evaluate(() => !!window.__CUT_STORE__);
    expect(alive).toBe(true);
  });
});
