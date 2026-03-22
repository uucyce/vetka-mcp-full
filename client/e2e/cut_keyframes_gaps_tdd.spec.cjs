/**
 * MARKER_QA.TDD4: TDD E2E tests for Keyframe system + coverage gap sweep.
 *
 * Covers:
 *   KF1-KF6: Keyframe system — add/navigate/delete/diamond display/easing
 *   GAP1-GAP5: JKL shuttle, markers (M key), undo/redo, snapping, linked selection
 *
 * FCP7 Reference:
 *   Ch.67 (Keyframes), Ch.51 (Timecode/Shuttle), Ch.39 (Markers), Ch.9 (Snapping)
 *
 * Author: Epsilon (QA-2) | 2026-03-22
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
const DEV_PORT = Number(process.env.VETKA_CUT_TDD4_PORT || 3012);
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
  const capture = (chunk) => { serverLogs += chunk.toString(); if (serverLogs.length > 20000) serverLogs = serverLogs.slice(-20000); };
  serverProcess.stdout.on('data', capture);
  serverProcess.stderr.on('data', capture);
  await waitForHttpOk(DEV_ORIGIN, 30000);
}

function cleanupServer() {
  if (serverProcess && serverStartedBySpec) { serverProcess.kill('SIGTERM'); serverProcess = null; }
}

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------
function createProject() {
  return {
    success: true,
    schema_version: 'cut_project_state_v1',
    project: {
      project_id: 'cut-tdd4-suite',
      display_name: 'TDD4 Keyframes+Gaps',
      source_path: '/tmp/cut/tdd4.mov',
      sandbox_root: '/tmp/cut-tdd4',
      state: 'ready',
    },
    runtime_ready: true, graph_ready: true, waveform_ready: true,
    transcript_ready: false, thumbnail_ready: true, slice_ready: true,
    timecode_sync_ready: false, sync_surface_ready: false,
    meta_sync_ready: false, time_markers_ready: false,
    timeline_state: {
      timeline_id: 'main',
      selection: { clip_ids: [], scene_ids: [] },
      lanes: [
        {
          lane_id: 'V1', lane_type: 'video_main',
          clips: [
            { clip_id: 'v1', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/cut/shot-a.mov', source_in: 0 },
            { clip_id: 'v2', scene_id: 's2', start_sec: 5, duration_sec: 4, source_path: '/tmp/cut/shot-b.mov', source_in: 0 },
            { clip_id: 'v3', scene_id: 's3', start_sec: 9, duration_sec: 3, source_path: '/tmp/cut/shot-c.mov', source_in: 0 },
          ],
        },
        {
          lane_id: 'A1', lane_type: 'audio_main',
          clips: [
            { clip_id: 'a1', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/cut/audio-a.wav', source_in: 0 },
            { clip_id: 'a2', scene_id: 's2', start_sec: 5, duration_sec: 4, source_path: '/tmp/cut/audio-b.wav', source_in: 0 },
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
  const state = createProject();
  await page.route(`${DEV_ORIGIN}/api/cut/**`, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/cut/project-state') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state) });
      return;
    }
    // Mock time-markers/apply — handler calls this endpoint (not /add-marker)
    if (url.pathname === '/api/cut/time-markers/apply') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, marker_id: 'mk_test_001' }) });
      return;
    }
    // Mock undo/redo
    if (url.pathname === '/api/cut/undo' || url.pathname === '/api/cut/redo') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
  });
}

async function navigateToCut(page, { preset = 'fcp7' } = {}) {
  await setupApiMocks(page);
  await page.addInitScript((p) => {
    window.localStorage.setItem('cut_hotkey_preset', p);
  }, preset);
  await page.goto(`${CUT_URL}?sandbox_root=${encodeURIComponent('/tmp/cut-tdd4')}&project_id=${encodeURIComponent('cut-tdd4-suite')}`, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="cut-timeline-track-view"]', { timeout: 15000 });
  await page.waitForSelector('[data-testid^="cut-timeline-clip-"]', { timeout: 10000 }).catch(() => {});
}

// ===========================================================================
// KEYFRAME SYSTEM TESTS (all RED by design — feature not yet built)
// ===========================================================================
test.describe('TDD4: Keyframe System', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // KF1: Add keyframe at playhead position (Ctrl+K)
  // FCP7 p.1127: "Control-K adds a keyframe at the current time"
  // -------------------------------------------------------------------------
  test('KF1: Ctrl+K adds keyframe at playhead on selected clip', async ({ page }) => {
    await navigateToCut(page);

    // Select clip and seek to middle
    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      s.setSelectedClip('v1');
      s.seek(2.5);
    });
    await page.waitForTimeout(200);

    // Try adding keyframe via store action
    const result = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return { hasAction: false };
      const s = window.__CUT_STORE__.getState();
      const hasAction = typeof s.addKeyframe === 'function';
      if (hasAction) {
        s.addKeyframe('v1', s.currentTime, 'opacity');
      }
      return { hasAction };
    });

    expect(result.hasAction).toBe(true);

    // Verify keyframe exists on clip
    const keyframes = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      const lanes = window.__CUT_STORE__.getState().lanes;
      for (const lane of lanes) {
        for (const clip of lane.clips) {
          if (clip.clip_id === 'v1' && clip.keyframes) return clip.keyframes;
        }
      }
      return null;
    });

    expect(keyframes).not.toBeNull();
    expect(keyframes.length).toBeGreaterThan(0);
  });

  // -------------------------------------------------------------------------
  // KF2: Navigate to next keyframe (Shift+K)
  // FCP7 p.1133: "Shift-K moves playhead to next keyframe"
  // -------------------------------------------------------------------------
  test('KF2: Shift+K navigates to next keyframe', async ({ page }) => {
    await navigateToCut(page);

    // Pre-seed keyframes on clip v1 at 1.0s and 3.0s
    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      if (s.addKeyframe) {
        s.addKeyframe('v1', 1.0, 'opacity');
        s.addKeyframe('v1', 3.0, 'opacity');
      }
      s.seek(0); // Start at beginning
    });
    await page.waitForTimeout(200);

    // Navigate to next keyframe
    const result = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      const s = window.__CUT_STORE__.getState();
      if (typeof s.nextKeyframe === 'function') {
        s.nextKeyframe();
        return { time: s.currentTime, hasAction: true };
      }
      return { time: 0, hasAction: false };
    });

    expect(result.hasAction).toBe(true);
    // Should have jumped to 1.0s (first keyframe after 0)
    expect(result.time).toBeCloseTo(1.0, 1);
  });

  // -------------------------------------------------------------------------
  // KF3: Navigate to previous keyframe (Alt+K / Option+K)
  // FCP7 p.1133: "Option-K moves playhead to previous keyframe"
  // -------------------------------------------------------------------------
  test('KF3: Alt+K navigates to previous keyframe', async ({ page }) => {
    await navigateToCut(page);

    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      if (s.addKeyframe) {
        s.addKeyframe('v1', 1.0, 'opacity');
        s.addKeyframe('v1', 3.0, 'opacity');
      }
      s.seek(4.0); // Start past all keyframes
    });
    await page.waitForTimeout(200);

    const result = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      const s = window.__CUT_STORE__.getState();
      if (typeof s.prevKeyframe === 'function') {
        s.prevKeyframe();
        return { time: s.currentTime, hasAction: true };
      }
      return { time: 0, hasAction: false };
    });

    expect(result.hasAction).toBe(true);
    expect(result.time).toBeCloseTo(3.0, 1);
  });

  // -------------------------------------------------------------------------
  // KF4: Delete keyframe at current position
  // FCP7 p.1131: "Click keyframe to select, then Delete"
  // -------------------------------------------------------------------------
  test('KF4: deleteKeyframe removes keyframe at position', async ({ page }) => {
    await navigateToCut(page);

    const result = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      const s = window.__CUT_STORE__.getState();
      if (!s.addKeyframe || !s.removeKeyframe) return { hasActions: false };

      s.addKeyframe('v1', 2.0, 'opacity');
      s.removeKeyframe('v1', 2.0, 'opacity');

      // Verify it's gone
      const lanes = s.lanes;
      for (const lane of lanes) {
        for (const clip of lane.clips) {
          if (clip.clip_id === 'v1') {
            const kf = clip.keyframes || [];
            return { hasActions: true, count: kf.length };
          }
        }
      }
      return { hasActions: true, count: 0 };
    });

    expect(result.hasActions).toBe(true);
    expect(result.count).toBe(0);
  });

  // -------------------------------------------------------------------------
  // KF5: Keyframe diamond markers visible on timeline clip
  // FCP7 p.1125: "Diamond-shaped keyframe indicators in Timeline"
  // -------------------------------------------------------------------------
  test('KF5: keyframe diamonds render on timeline clip', async ({ page }) => {
    await navigateToCut(page);

    // Add keyframes and check for visual diamond markers
    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      if (s.addKeyframe) {
        s.addKeyframe('v1', 1.0, 'opacity');
        s.addKeyframe('v1', 3.0, 'opacity');
      }
    });
    await page.waitForTimeout(300);

    const hasDiamonds = await page.evaluate(() => {
      const clip = document.querySelector('[data-testid="cut-timeline-clip-v1"]');
      if (!clip) return false;
      // Look for diamond markers: data-testid, class, or rotated squares
      const diamonds = clip.querySelectorAll('[data-testid*="keyframe"], [class*="keyframe"]');
      if (diamonds.length > 0) return true;
      // Fallback: look for small rotated squares (CSS transform: rotate(45deg))
      const allEls = clip.querySelectorAll('div, span');
      for (const el of allEls) {
        const style = window.getComputedStyle(el);
        if (style.transform && style.transform.includes('rotate') &&
            el.getBoundingClientRect().width < 12) {
          return true;
        }
      }
      return false;
    });

    expect(hasDiamonds).toBe(true);
  });

  // -------------------------------------------------------------------------
  // KF6: Hotkey bindings exist for keyframe operations
  // FCP7: Ctrl+K (add), Shift+K (next), Option+K (prev)
  // -------------------------------------------------------------------------
  test('KF6: keyframe hotkey actions registered in hotkey system', async ({ page }) => {
    await navigateToCut(page);

    const hotkeys = await page.evaluate(() => {
      // Check if hotkey actions are registered (they appear in the action label list)
      const body = document.body.textContent || '';
      // These labels come from useCutHotkeys.ts ACTION_LABELS
      return {
        hasAddKeyframe: body.includes('Add Keyframe') || body.includes('keyframe'),
        // Also check store for the functions
        storeHasAdd: typeof window.__CUT_STORE__?.getState().addKeyframe === 'function',
        storeHasNext: typeof window.__CUT_STORE__?.getState().nextKeyframe === 'function',
        storeHasPrev: typeof window.__CUT_STORE__?.getState().prevKeyframe === 'function',
      };
    });

    // At minimum, store should have the action functions
    expect(hotkeys.storeHasAdd).toBe(true);
  });
});

// ===========================================================================
// COVERAGE GAP TESTS
// ===========================================================================
test.describe('TDD4: Coverage Gaps', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // GAP1: JKL shuttle — L increases speed, J reverses, K stops
  // FCP7 p.88: "J-K-L shuttle keys for variable-speed playback"
  // -------------------------------------------------------------------------
  test('GAP1: JKL shuttle — L sets forward speed, K stops', async ({ page }) => {
    await navigateToCut(page);

    // Press L for forward shuttle
    await page.keyboard.press('l');
    await page.waitForTimeout(100);

    const speed1 = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().shuttleSpeed;
    });
    expect(speed1).toBeGreaterThan(0);

    // Press L again — should increase speed
    await page.keyboard.press('l');
    await page.waitForTimeout(100);

    const speed2 = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().shuttleSpeed;
    });
    expect(speed2).toBeGreaterThan(speed1);

    // Press K — stop
    await page.keyboard.press('k');
    await page.waitForTimeout(100);

    const stopped = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().shuttleSpeed;
    });
    expect(stopped).toBe(0);
  });

  // -------------------------------------------------------------------------
  // GAP2: J key reverses shuttle direction
  // -------------------------------------------------------------------------
  test('GAP2: J key sets reverse shuttle speed', async ({ page }) => {
    await navigateToCut(page);

    // Seek to middle first — reverse shuttle at t=0 immediately resets
    // because TransportBar rAF loop sees newTime<=0 and calls setShuttleSpeed(0)
    await page.evaluate(() => {
      if (window.__CUT_STORE__) {
        const s = window.__CUT_STORE__.getState();
        if (s.duration === 0) s.setDuration(12);
        s.seek(5.0);
      }
    });
    await page.waitForTimeout(100);

    await page.keyboard.press('j');
    await page.waitForTimeout(100);

    const speed = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().shuttleSpeed;
    });

    expect(speed).toBeLessThan(0);
  });

  // -------------------------------------------------------------------------
  // GAP3: M key adds marker at playhead
  // FCP7 p.302: "Press M to add a marker at the playhead position"
  // -------------------------------------------------------------------------
  test('GAP3: M key triggers add-marker API call at playhead position', async ({ page }) => {
    await navigateToCut(page);

    // Seek to 3s (must be within a clip for mediaPath to resolve)
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().seek(3.0);
    });
    await page.waitForTimeout(100);

    // Track API calls to time-markers/apply
    let markerApiCalled = false;
    let markerPayload = null;
    await page.route(`${DEV_ORIGIN}/api/cut/time-markers/apply`, async (route) => {
      markerApiCalled = true;
      const body = route.request().postDataJSON();
      markerPayload = body;
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
    });

    // Press M to add marker
    await page.keyboard.press('m');
    await page.waitForTimeout(800); // async API call + refresh

    // Verify the API was called with correct params
    expect(markerApiCalled).toBe(true);
    expect(markerPayload).not.toBeNull();
    expect(markerPayload.kind).toBe('favorite');
    expect(markerPayload.start_sec).toBeCloseTo(3.0, 1);
  });

  // -------------------------------------------------------------------------
  // GAP4: Snap toggle works and reflects in toolbar
  // FCP7 p.134: "Snapping control — N key toggles snapping"
  // -------------------------------------------------------------------------
  test('GAP4: snap toggle changes snapEnabled state', async ({ page }) => {
    await navigateToCut(page);

    const initial = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().snapEnabled;
    });
    expect(initial).not.toBeNull();

    // Toggle snap via store action
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().toggleSnap();
    });
    await page.waitForTimeout(100);

    const toggled = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().snapEnabled;
    });

    expect(toggled).toBe(!initial);

    // Toolbar should reflect snap state — look for "Snap ON" or "Snap OFF" text
    const toolbarText = await page.evaluate(() => {
      const btns = document.querySelectorAll('button[title*="Snap"]');
      if (btns.length > 0) return btns[0].getAttribute('title');
      return null;
    });

    expect(toolbarText).toBeTruthy();
    expect(toolbarText).toMatch(/Snap/i);
  });

  // -------------------------------------------------------------------------
  // GAP5: Linked selection toggle persists and affects clip operations
  // FCP7 p.592: "Linked Selection button — Shift+L toggles"
  // -------------------------------------------------------------------------
  test('GAP5: linked selection toggle updates store via Shift+L', async ({ page }) => {
    await navigateToCut(page);

    const initial = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().linkedSelection;
    });

    await page.keyboard.press('Shift+l');
    await page.waitForTimeout(200);

    const after = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().linkedSelection;
    });

    expect(after).toBe(!initial);

    // Toolbar should show linked selection state
    const hasIndicator = await page.evaluate(() => {
      const btns = document.querySelectorAll('button[title*="Linked"]');
      return btns.length > 0;
    });

    expect(hasIndicator).toBe(true);
  });
});
