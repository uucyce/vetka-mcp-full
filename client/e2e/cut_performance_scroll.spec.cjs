/**
 * MARKER_QA.PERF: Performance baseline — Timeline Scroll FPS.
 *
 * Measures frame rate during horizontal scroll of timeline with many clips.
 * Uses requestAnimationFrame inside page to count frames and measure deltas.
 *
 * Metrics captured:
 *   - min/avg/max FPS during scroll
 *   - jank count (frames > 16.7ms)
 *   - total frames rendered
 *   - 95th percentile frame time
 *
 * Target: 60fps sustained, <5% jank frames.
 *
 * @phase 196
 * @agent Epsilon (QA-2)
 * @task tb_1774237484_7
 */
const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_PERF_PORT || 4197);
const DEV_ORIGIN = `http://127.0.0.1:${DEV_PORT}`;
const CUT_URL = `${DEV_ORIGIN}/cut?sandbox_root=${encodeURIComponent('/tmp/cut-perf')}&project_id=perf-scroll`;

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
      if (Date.now() - startedAt >= timeoutMs) reject(new Error(`Timed out\n${serverLogs}`));
      else setTimeout(tick, 200);
    };
    tick();
  });
}

async function ensureDevServer() {
  try { await waitForHttpOk(DEV_ORIGIN, 1500); return; } catch { /* start */ }
  serverStartedBySpec = true;
  serverProcess = spawn('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(DEV_PORT)],
    { cwd: CLIENT_DIR, env: { ...process.env, BROWSER: 'none', CI: '1' }, stdio: ['ignore', 'pipe', 'pipe'] });
  const cap = (c) => { serverLogs += c.toString(); if (serverLogs.length > 20000) serverLogs = serverLogs.slice(-20000); };
  serverProcess.stdout.on('data', cap);
  serverProcess.stderr.on('data', cap);
  await waitForHttpOk(DEV_ORIGIN, 30000);
}

function cleanupServer() { if (serverProcess && serverStartedBySpec) { serverProcess.kill('SIGTERM'); serverProcess = null; } }

// ---------------------------------------------------------------------------
// Generate N clips across 2 lanes for stress test
// ---------------------------------------------------------------------------
function generateClips(count) {
  const videoClips = [];
  const audioClips = [];
  for (let i = 0; i < count; i++) {
    const start = i * 3; // 3s per clip, no gaps
    videoClips.push({
      clip_id: `perf_v${i}`, scene_id: `s${i}`,
      start_sec: start, duration_sec: 3,
      source_path: `/tmp/clip_${i}.mov`,
    });
    if (i % 2 === 0) {
      audioClips.push({
        clip_id: `perf_a${i}`, scene_id: `s${i}`,
        start_sec: start, duration_sec: 3,
        source_path: `/tmp/audio_${i}.wav`,
      });
    }
  }
  return [
    { lane_id: 'V1', lane_type: 'video_main', clips: videoClips },
    { lane_id: 'A1', lane_type: 'audio_main', clips: audioClips },
  ];
}

function makeProjectState(clipCount) {
  return {
    success: true,
    schema_version: 'cut_project_state_v1',
    project: { project_id: 'perf-scroll', display_name: 'Perf Scroll', source_path: '/tmp/perf.mov', sandbox_root: '/tmp/cut-perf', state: 'ready', framerate: 25 },
    runtime_ready: true, graph_ready: true, waveform_ready: true,
    transcript_ready: false, thumbnail_ready: true, slice_ready: true,
    timecode_sync_ready: false, sync_surface_ready: false, meta_sync_ready: false, time_markers_ready: false,
    timeline_state: { timeline_id: 'main', selection: { clip_ids: [], scene_ids: [] }, lanes: generateClips(clipCount) },
    waveform_bundle: { items: [] }, thumbnail_bundle: { items: [] },
    sync_surface: { items: [] }, time_marker_bundle: { items: [] },
    recent_jobs: [], active_jobs: [],
  };
}

async function setupMocks(page, clipCount) {
  const state = makeProjectState(clipCount);
  await page.route(`${DEV_ORIGIN}/api/cut/**`, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/cut/project-state') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{"success":true}' });
  });
}

async function navigateToCut(page, clipCount = 50) {
  await setupMocks(page, clipCount);
  await page.goto(CUT_URL, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="cut-timeline-track-view"]', { timeout: 15000 });
  await page.waitForSelector('[data-testid^="cut-timeline-clip-"]', { timeout: 10000 }).catch(() => {});
}

/**
 * Inject FPS counter into page. Returns a handle to start/stop measurement.
 * Uses rAF loop to measure frame deltas.
 */
async function injectFpsCounter(page) {
  await page.evaluate(() => {
    window.__PERF__ = {
      frames: [],
      running: false,
      rafId: null,
      lastTime: 0,
      start() {
        this.frames = [];
        this.running = true;
        this.lastTime = performance.now();
        const tick = (now) => {
          if (!this.running) return;
          const delta = now - this.lastTime;
          if (delta > 0) this.frames.push(delta);
          this.lastTime = now;
          this.rafId = requestAnimationFrame(tick);
        };
        this.rafId = requestAnimationFrame(tick);
      },
      stop() {
        this.running = false;
        if (this.rafId) cancelAnimationFrame(this.rafId);
      },
      getReport() {
        const frames = this.frames.filter(d => d > 0 && d < 500); // filter outliers
        if (!frames.length) return { fps_avg: 0, fps_min: 0, fps_max: 0, jank_count: 0, jank_pct: 0, total_frames: 0, p95_ms: 0 };
        const sorted = [...frames].sort((a, b) => a - b);
        const fps = frames.map(d => 1000 / d);
        const fpsAvg = fps.reduce((a, b) => a + b, 0) / fps.length;
        const fpsMin = Math.min(...fps);
        const fpsMax = Math.max(...fps);
        const jankCount = frames.filter(d => d > 16.7).length;
        const jankPct = (jankCount / frames.length) * 100;
        const p95Idx = Math.floor(sorted.length * 0.95);
        const p95 = sorted[p95Idx] || sorted[sorted.length - 1];
        return {
          fps_avg: Math.round(fpsAvg * 10) / 10,
          fps_min: Math.round(fpsMin * 10) / 10,
          fps_max: Math.round(fpsMax * 10) / 10,
          jank_count: jankCount,
          jank_pct: Math.round(jankPct * 10) / 10,
          total_frames: frames.length,
          p95_ms: Math.round(p95 * 100) / 100,
        };
      },
    };
  });
}

// ===========================================================================
// PERF TESTS
// ===========================================================================
test.describe('PERF: Timeline Scroll FPS', () => {
  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  test('PERF-SCROLL1: 50 clips — horizontal scroll FPS baseline', async ({ page }) => {
    await navigateToCut(page, 50);
    await injectFpsCounter(page);

    const clipCount = await page.evaluate(() =>
      document.querySelectorAll('[data-testid^="cut-timeline-clip-"]').length
    );
    // Timeline virtualizes — only visible clips are rendered
    expect(clipCount).toBeGreaterThanOrEqual(3);

    // Find the scrollable timeline container
    const timeline = page.locator('[data-testid="cut-timeline-track-view"]');
    const box = await timeline.boundingBox();
    expect(box).not.toBeNull();

    // Start FPS measurement
    await page.evaluate(() => window.__PERF__.start());

    // Simulate horizontal scroll: 20 wheel events over 2 seconds
    for (let i = 0; i < 20; i++) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.wheel(120, 0); // deltaX = 120 (scroll right)
      await page.waitForTimeout(100);
    }

    // Stop and collect
    await page.evaluate(() => window.__PERF__.stop());
    await page.waitForTimeout(100);

    const report = await page.evaluate(() => window.__PERF__.getReport());

    // Log results for baseline
    console.log('\n=== SCROLL PERF BASELINE (50 clips) ===');
    console.log(`FPS: avg=${report.fps_avg}, min=${report.fps_min}, max=${report.fps_max}`);
    console.log(`Jank: ${report.jank_count}/${report.total_frames} frames (${report.jank_pct}%)`);
    console.log(`P95 frame time: ${report.p95_ms}ms`);
    console.log('========================================\n');

    // Baseline assertions (lenient — establishing, not enforcing)
    expect(report.total_frames).toBeGreaterThan(10);
    expect(report.fps_avg).toBeGreaterThan(0);
    // Target: avg FPS > 30 (half of 60fps target — headless may not hit 60)
    // This is a BASELINE test — we record, not enforce strictly
    expect(report.fps_avg).toBeGreaterThan(15);
  });

  test('PERF-SCROLL2: 100 clips — stress test', async ({ page }) => {
    await navigateToCut(page, 100);
    await injectFpsCounter(page);

    const clipCount = await page.evaluate(() =>
      document.querySelectorAll('[data-testid^="cut-timeline-clip-"]').length
    );

    const timeline = page.locator('[data-testid="cut-timeline-track-view"]');
    const box = await timeline.boundingBox();

    await page.evaluate(() => window.__PERF__.start());

    // Longer scroll: 30 events over 3 seconds
    for (let i = 0; i < 30; i++) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.wheel(150, 0);
      await page.waitForTimeout(100);
    }

    await page.evaluate(() => window.__PERF__.stop());
    await page.waitForTimeout(100);

    const report = await page.evaluate(() => window.__PERF__.getReport());

    console.log('\n=== SCROLL PERF STRESS (100 clips) ===');
    console.log(`Clips rendered: ${clipCount}`);
    console.log(`FPS: avg=${report.fps_avg}, min=${report.fps_min}, max=${report.fps_max}`);
    console.log(`Jank: ${report.jank_count}/${report.total_frames} frames (${report.jank_pct}%)`);
    console.log(`P95 frame time: ${report.p95_ms}ms`);
    console.log('======================================\n');

    expect(report.total_frames).toBeGreaterThan(10);
    expect(report.fps_avg).toBeGreaterThan(10);
  });

  test('PERF-SCROLL3: page load time measurement', async ({ page }) => {
    const startTime = Date.now();
    await navigateToCut(page, 30);
    const loadTime = Date.now() - startTime;

    // Also measure via Performance API
    const perfTiming = await page.evaluate(() => {
      const nav = performance.getEntriesByType('navigation')[0];
      if (!nav) return null;
      return {
        domContentLoaded: Math.round(nav.domContentLoadedEventEnd - nav.startTime),
        loadComplete: Math.round(nav.loadEventEnd - nav.startTime),
        firstPaint: Math.round((performance.getEntriesByName('first-paint')[0]?.startTime) || 0),
        firstContentfulPaint: Math.round((performance.getEntriesByName('first-contentful-paint')[0]?.startTime) || 0),
      };
    });

    console.log('\n=== PAGE LOAD BASELINE ===');
    console.log(`Total navigation time: ${loadTime}ms`);
    if (perfTiming) {
      console.log(`DOM Content Loaded: ${perfTiming.domContentLoaded}ms`);
      console.log(`Load Complete: ${perfTiming.loadComplete}ms`);
      console.log(`First Paint: ${perfTiming.firstPaint}ms`);
      console.log(`First Contentful Paint: ${perfTiming.firstContentfulPaint}ms`);
    }
    console.log('==========================\n');

    // Baseline: load should complete within 10s (very lenient for dev server + headless)
    expect(loadTime).toBeLessThan(10000);
    // Target is <2s but dev server + Playwright overhead makes this unreliable
  });

  test('PERF-SCROLL4: zoom in/out during scroll — combined stress', async ({ page }) => {
    await navigateToCut(page, 50);
    await injectFpsCounter(page);

    const timeline = page.locator('[data-testid="cut-timeline-track-view"]');
    const box = await timeline.boundingBox();

    // Focus timeline for keyboard
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().setFocusedPanel('timeline');
    });

    await page.evaluate(() => window.__PERF__.start());

    // Interleave scroll + zoom
    for (let i = 0; i < 15; i++) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.wheel(100, 0);
      await page.waitForTimeout(50);
      // Zoom every 5th iteration
      if (i % 5 === 0) {
        await page.keyboard.press('=');
        await page.waitForTimeout(50);
      }
    }

    // Zoom back out
    for (let i = 0; i < 3; i++) {
      await page.keyboard.press('-');
      await page.waitForTimeout(50);
    }

    await page.evaluate(() => window.__PERF__.stop());
    await page.waitForTimeout(100);

    const report = await page.evaluate(() => window.__PERF__.getReport());

    console.log('\n=== SCROLL+ZOOM COMBINED STRESS ===');
    console.log(`FPS: avg=${report.fps_avg}, min=${report.fps_min}, max=${report.fps_max}`);
    console.log(`Jank: ${report.jank_count}/${report.total_frames} frames (${report.jank_pct}%)`);
    console.log(`P95 frame time: ${report.p95_ms}ms`);
    console.log('===================================\n');

    expect(report.total_frames).toBeGreaterThan(5);
  });
});
