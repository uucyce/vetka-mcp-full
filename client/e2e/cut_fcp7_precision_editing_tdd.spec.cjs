/**
 * MARKER_QA.FCP7_PRECISION: TDD E2E tests for FCP7 Ch.41-115 precision editing.
 *
 * Written BEFORE implementation — tests WILL FAIL (RED) until
 * corresponding build tasks are completed by Alpha/implementation agents.
 *
 * Delta-2 territory (Ch.41-115 + Appendix A):
 *   TOOL1-3: Tool state machine (A/B/R/S keys, cursor changes)
 *   TRIM1-4: Ripple, Roll, Slip, Slide edit operations
 *   JKL1-3:  Progressive shuttle (not ±5s jumps)
 *   MATCH1-2: Match Frame (F key), Q toggle
 *   SPLIT1-2: Split edits (L-cut/J-cut), Extend Edit (E)
 *   SPEED1-2: Speed indicators, Cmd+J shortcut
 *
 * Reference tasks:
 *   tb_1773995983_4  (tool state machine)
 *   tb_1773995970_1  (ripple edit)
 *   tb_1773995974_2  (roll edit)
 *   tb_1773995978_3  (slip/slide)
 *   tb_1773995989_5  (JKL progressive)
 *   tb_1773996014_7  (match frame)
 *   tb_1773996008_6  (wire missing handlers)
 *   tb_1773996067_13 (split edits)
 *   tb_1773996056_11 (speed indicators)
 *
 * FCP7 Manual: Ch.44 (Trim), Ch.50 (Match Frame), App A (Shortcuts)
 *
 * @phase 196
 * @agent delta-2
 * @status red (TDD — all tests expected to fail)
 */
const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

// ---------------------------------------------------------------------------
// Server bootstrap (shared pattern with Delta-1 specs)
// ---------------------------------------------------------------------------
const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_PRECISION_PORT || 3009);
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
// Fixture: project with multiple clips for precision editing tests
// Includes clips with "media handles" (source longer than used portion)
// ---------------------------------------------------------------------------
function createPrecisionProject() {
  return {
    success: true,
    schema_version: 'cut_project_state_v1',
    project: {
      project_id: 'cut-precision-tdd',
      display_name: 'Precision Editing TDD',
      source_path: '/tmp/cut/precision.mov',
      sandbox_root: '/tmp/cut-precision',
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
            // Clips with media handles: source_duration > duration_sec
            { clip_id: 'v_a', scene_id: 's1', start_sec: 0, duration_sec: 5,
              source_path: '/tmp/cut/interview-a.mov', source_in: 2, source_duration: 30 },
            { clip_id: 'v_b', scene_id: 's2', start_sec: 5, duration_sec: 4,
              source_path: '/tmp/cut/interview-b.mov', source_in: 0, source_duration: 20 },
            { clip_id: 'v_c', scene_id: 's3', start_sec: 9, duration_sec: 3,
              source_path: '/tmp/cut/broll-c.mov', source_in: 5, source_duration: 15 },
            { clip_id: 'v_d', scene_id: 's4', start_sec: 12, duration_sec: 6,
              source_path: '/tmp/cut/interview-d.mov', source_in: 0, source_duration: 25 },
          ],
        },
        {
          lane_id: 'A1', lane_type: 'audio_main',
          clips: [
            { clip_id: 'a_a', scene_id: 's1', start_sec: 0, duration_sec: 5,
              source_path: '/tmp/cut/audio-a.wav', linked_to: 'v_a' },
            { clip_id: 'a_b', scene_id: 's2', start_sec: 5, duration_sec: 4,
              source_path: '/tmp/cut/audio-b.wav', linked_to: 'v_b' },
            { clip_id: 'a_c', scene_id: 's3', start_sec: 9, duration_sec: 3,
              source_path: '/tmp/cut/audio-c.wav', linked_to: 'v_c' },
            { clip_id: 'a_d', scene_id: 's4', start_sec: 12, duration_sec: 6,
              source_path: '/tmp/cut/audio-d.wav', linked_to: 'v_d' },
          ],
        },
        {
          lane_id: 'A2', lane_type: 'audio_main',
          clips: [
            { clip_id: 'a_music', scene_id: 's1', start_sec: 0, duration_sec: 18,
              source_path: '/tmp/cut/music-bed.wav' },
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
  const state = createPrecisionProject();
  await page.route(`${DEV_ORIGIN}/api/cut/**`, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/cut/project-state') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state) });
      return;
    }
    // For timeline operations, return success with modified state
    if (url.pathname === '/api/cut/timeline/apply') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
  });
}

async function navigateToCut(page) {
  await setupApiMocks(page);
  // MARKER_QA.W6: Set FCP7 hotkey preset since these tests verify FCP7 key bindings
  await page.addInitScript(() => {
    window.localStorage.setItem('cut_hotkey_preset', 'fcp7');
  });
  await page.goto(CUT_URL, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="cut-timeline-track-view"]', { timeout: 15000 });
}

// Helper: get store state safely
async function getStoreState(page, field) {
  return page.evaluate((f) => {
    if (window.__CUT_STORE__) return window.__CUT_STORE__.getState()[f];
    return null;
  }, field);
}

// ===========================================================================
// TOOL STATE MACHINE (FCP7 App A + Ch.44)
// ===========================================================================
test.describe.serial('FCP7 Precision: Tool State Machine (TDD)', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // TOOL1: activeTool state exists in store
  // FCP7 App A: Tool selection keys change the active editing tool.
  // -------------------------------------------------------------------------
  test('TOOL1: store has activeTool field with valid tool names', async ({ page }) => {
    await navigateToCut(page);

    const activeTool = await getStoreState(page, 'activeTool');

    // activeTool should exist and be one of valid tool names
    expect(activeTool).toBeTruthy();
    // MARKER_QA.W6: store uses 'selection' not 'select'
    expect(['selection', 'select', 'razor', 'blade', 'ripple', 'roll', 'slip', 'slide', 'hand', 'zoom', 'speed'])
      .toContain(activeTool);
  });

  // -------------------------------------------------------------------------
  // TOOL2: pressing A sets selection tool, B sets razor
  // FCP7: A = Arrow/Selection tool, B = Blade/Razor tool
  // -------------------------------------------------------------------------
  test('TOOL2a: pressing A activates selection tool', async ({ page }) => {
    await navigateToCut(page);

    // First press B to ensure we're not on select
    await page.keyboard.press('b');
    await page.waitForTimeout(150);

    // Press A for selection tool (FCP7 standard)
    await page.keyboard.press('a');
    await page.waitForTimeout(150);

    const activeTool = await getStoreState(page, 'activeTool');
    // MARKER_QA.W6: store uses 'selection' not 'select'
    expect(['selection', 'select']).toContain(activeTool);
  });

  test('TOOL2b: pressing B activates razor/blade tool', async ({ page }) => {
    await navigateToCut(page);

    await page.keyboard.press('b');
    await page.waitForTimeout(150);

    const activeTool = await getStoreState(page, 'activeTool');
    expect(['razor', 'blade', 'cut']).toContain(activeTool);
  });

  // -------------------------------------------------------------------------
  // TOOL3: cursor changes based on active tool
  // FCP7: Each tool has a distinct cursor (arrow, crosshair, bracket, etc.)
  // -------------------------------------------------------------------------
  test('TOOL3: timeline cursor changes when tool is switched', async ({ page }) => {
    await navigateToCut(page);

    // Get cursor with selection tool
    await page.keyboard.press('a');
    await page.waitForTimeout(150);
    const selectCursor = await page.evaluate(() => {
      const timeline = document.querySelector('[data-testid="cut-timeline-track-view"]');
      return timeline ? window.getComputedStyle(timeline).cursor : 'unknown';
    });

    // Switch to razor tool
    await page.keyboard.press('b');
    await page.waitForTimeout(150);
    const razorCursor = await page.evaluate(() => {
      const timeline = document.querySelector('[data-testid="cut-timeline-track-view"]');
      return timeline ? window.getComputedStyle(timeline).cursor : 'unknown';
    });

    // Cursors should be different (e.g., 'default' vs 'crosshair')
    expect(razorCursor).not.toBe(selectCursor);
  });

  // -------------------------------------------------------------------------
  // TOOL4: tool indicator visible in UI
  // FCP7: Tool palette shows active tool, toolbar has tool buttons
  // -------------------------------------------------------------------------
  test('TOOL4: active tool is visually indicated in toolbar', async ({ page }) => {
    await navigateToCut(page);

    const hasToolIndicator = await page.evaluate(() => {
      // Look for tool indicator in toolbar/timeline area
      const indicators = document.querySelectorAll(
        '[data-testid*="tool-indicator"], [data-testid*="active-tool"], ' +
        '[aria-label*="Selection Tool"], [aria-label*="Razor"], ' +
        '[data-testid*="toolbar-tool"], .tool-palette'
      );
      return indicators.length > 0;
    });

    expect(hasToolIndicator).toBe(true);
  });
});

// ===========================================================================
// TRIM TOOLS (FCP7 Ch.44 — Slip, Slide, Ripple, Roll)
// ===========================================================================
test.describe.serial('FCP7 Precision: Trim Tools (TDD)', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // TRIM1: Ripple Edit — trim clip, shift subsequent clips
  // FCP7 Ch.44 p.693: "trims the Out point of one clip and moves the
  //   In point of the adjacent clip to compensate"
  // Key: RR (press R twice in FCP7 tool palette cycle)
  // -------------------------------------------------------------------------
  test('TRIM1: ripple edit tool is available (R key or tool palette)', async ({ page }) => {
    await navigateToCut(page);

    // Try activating ripple edit tool
    // FCP7: R key cycles through edit tools (Ripple → Roll)
    await page.keyboard.press('r');
    await page.waitForTimeout(150);

    const activeTool = await getStoreState(page, 'activeTool');

    // Should be either 'ripple' or 'roll' (R cycles between them)
    expect(['ripple', 'roll']).toContain(activeTool);
  });

  test('TRIM1b: ripple edit at clip boundary shifts subsequent clips', async ({ page }) => {
    await navigateToCut(page);

    // Get total sequence duration before ripple
    const beforeDuration = await page.evaluate(() => {
      const clips = document.querySelectorAll('[data-testid^="cut-timeline-clip-"]');
      let maxEnd = 0;
      clips.forEach(c => {
        const rect = c.getBoundingClientRect();
        if (rect.right > maxEnd) maxEnd = rect.right;
      });
      return maxEnd;
    });

    // Activate ripple edit tool
    await page.keyboard.press('r');
    await page.waitForTimeout(150);

    // Drag the Out point of first clip (right edge) to make it shorter
    const firstClip = page.locator('[data-testid="cut-timeline-clip-v_a"]');
    const box = await firstClip.boundingBox().catch(() => null);

    if (box) {
      // Drag right edge 50px to the left (shorten clip)
      const rightEdge = box.x + box.width - 2;
      const midY = box.y + box.height / 2;

      await page.mouse.move(rightEdge, midY);
      await page.mouse.down();
      await page.mouse.move(rightEdge - 50, midY, { steps: 5 });
      await page.mouse.up();
      await page.waitForTimeout(300);
    }

    // After ripple edit, total sequence duration should have DECREASED
    // (because subsequent clips shifted left to fill the gap)
    const afterDuration = await page.evaluate(() => {
      const clips = document.querySelectorAll('[data-testid^="cut-timeline-clip-"]');
      let maxEnd = 0;
      clips.forEach(c => {
        const rect = c.getBoundingClientRect();
        if (rect.right > maxEnd) maxEnd = rect.right;
      });
      return maxEnd;
    });

    // Ripple = duration changes (unlike roll where duration stays same)
    expect(afterDuration).toBeLessThan(beforeDuration);
  });

  // -------------------------------------------------------------------------
  // TRIM2: Roll Edit — move edit point, total duration unchanged
  // FCP7 Ch.44 p.698: "Rolling edit adjusts the Out point of one clip
  //   and the In point of the adjacent clip simultaneously"
  // -------------------------------------------------------------------------
  test('TRIM2: roll edit at boundary preserves total sequence duration', async ({ page }) => {
    await navigateToCut(page);

    // Get total sequence duration
    const totalBefore = await page.evaluate(() => {
      if (window.__CUT_STORE__) return window.__CUT_STORE__.getState().duration;
      return 18; // sum of our test clips
    });

    // Activate roll edit (press R twice to cycle from ripple→roll)
    await page.keyboard.press('r');
    await page.waitForTimeout(100);
    await page.keyboard.press('r');
    await page.waitForTimeout(150);

    const activeTool = await getStoreState(page, 'activeTool');
    expect(activeTool).toBe('roll');

    // Drag edit point between clip A and clip B
    // The edit point is at x=5sec boundary
    const editPointX = await page.evaluate(() => {
      const clipA = document.querySelector('[data-testid="cut-timeline-clip-v_a"]');
      const clipB = document.querySelector('[data-testid="cut-timeline-clip-v_b"]');
      if (clipA && clipB) {
        const aRect = clipA.getBoundingClientRect();
        return aRect.right; // right edge of A = edit point
      }
      return null;
    });

    if (editPointX) {
      const timeline = await page.locator('[data-testid="cut-timeline-track-view"]').boundingBox();
      if (timeline) {
        const y = timeline.y + 30; // approximate track position
        await page.mouse.move(editPointX, y);
        await page.mouse.down();
        await page.mouse.move(editPointX + 30, y, { steps: 5 });
        await page.mouse.up();
        await page.waitForTimeout(300);
      }
    }

    // After roll edit, total duration should be UNCHANGED
    const totalAfter = await page.evaluate(() => {
      if (window.__CUT_STORE__) return window.__CUT_STORE__.getState().duration;
      return 18;
    });

    expect(totalAfter).toBe(totalBefore);
  });

  // -------------------------------------------------------------------------
  // TRIM3: Slip Edit — change clip content without moving position
  // FCP7 Ch.44 p.702: "changes the In and Out points of a clip simultaneously
  //   by the same amount, in the same direction"
  // -------------------------------------------------------------------------
  test('TRIM3: slip edit changes clip In/Out without moving position', async ({ page }) => {
    await navigateToCut(page);

    // Get clip B position and In/Out before slip
    const before = await page.evaluate(() => {
      const clip = document.querySelector('[data-testid="cut-timeline-clip-v_b"]');
      if (!clip) return null;
      const rect = clip.getBoundingClientRect();
      return { left: rect.left, width: rect.width };
    });

    // Activate slip tool (S twice in FCP7)
    // Our implementation: specific key or tool button
    await page.keyboard.press('s');
    await page.waitForTimeout(100);
    await page.keyboard.press('s');
    await page.waitForTimeout(150);

    const activeTool = await getStoreState(page, 'activeTool');
    expect(activeTool).toBe('slip');

    // Drag clip B to the right (slip = scroll source within fixed position)
    const clipB = page.locator('[data-testid="cut-timeline-clip-v_b"]');
    const box = await clipB.boundingBox().catch(() => null);

    if (box) {
      const centerX = box.x + box.width / 2;
      const centerY = box.y + box.height / 2;
      await page.mouse.move(centerX, centerY);
      await page.mouse.down();
      await page.mouse.move(centerX + 30, centerY, { steps: 5 });
      await page.mouse.up();
      await page.waitForTimeout(300);
    }

    // After slip: clip position and duration should be UNCHANGED
    const after = await page.evaluate(() => {
      const clip = document.querySelector('[data-testid="cut-timeline-clip-v_b"]');
      if (!clip) return null;
      const rect = clip.getBoundingClientRect();
      return { left: rect.left, width: rect.width };
    });

    if (before && after) {
      expect(after.left).toBeCloseTo(before.left, 0);
      expect(after.width).toBeCloseTo(before.width, 0);
    }

    // But source_in should have changed (the content shifted within the clip)
    // This is the key assertion for slip
    const sourceInChanged = await page.evaluate(() => {
      if (window.__CUT_STORE__) {
        const state = window.__CUT_STORE__.getState();
        // Check if the clip's source_in has shifted
        const clips = state.clips || state.timeline_state?.lanes?.[0]?.clips || [];
        const clipB = clips.find(c => c.clip_id === 'v_b');
        return clipB ? clipB.source_in !== 0 : false;
      }
      return false;
    });

    // source_in should have changed (content scrolled within clip)
    expect(sourceInChanged).toBe(true);
  });

  // -------------------------------------------------------------------------
  // TRIM4: Slide Edit — move clip, adjust neighbors' durations
  // FCP7 Ch.44 p.706: "moves a clip in the Timeline, shortening or
  //   extending adjacent clips to accommodate the move"
  // -------------------------------------------------------------------------
  test('TRIM4: slide edit moves clip between neighbors', async ({ page }) => {
    await navigateToCut(page);

    // Get clip B and neighbors' positions before slide
    const before = await page.evaluate(() => {
      const a = document.querySelector('[data-testid="cut-timeline-clip-v_a"]');
      const b = document.querySelector('[data-testid="cut-timeline-clip-v_b"]');
      const c = document.querySelector('[data-testid="cut-timeline-clip-v_c"]');
      if (!a || !b || !c) return null;
      return {
        aWidth: a.getBoundingClientRect().width,
        bLeft: b.getBoundingClientRect().left,
        bWidth: b.getBoundingClientRect().width,
        cWidth: c.getBoundingClientRect().width,
      };
    });

    // Activate slide tool (S three times in FCP7)
    await page.keyboard.press('s');
    await page.waitForTimeout(80);
    await page.keyboard.press('s');
    await page.waitForTimeout(80);
    await page.keyboard.press('s');
    await page.waitForTimeout(150);

    const activeTool = await getStoreState(page, 'activeTool');
    expect(activeTool).toBe('slide');

    // Drag clip B to the right (slide it later in time)
    const clipB = page.locator('[data-testid="cut-timeline-clip-v_b"]');
    const box = await clipB.boundingBox().catch(() => null);

    if (box) {
      const centerX = box.x + box.width / 2;
      const centerY = box.y + box.height / 2;
      await page.mouse.move(centerX, centerY);
      await page.mouse.down();
      await page.mouse.move(centerX + 40, centerY, { steps: 5 });
      await page.mouse.up();
      await page.waitForTimeout(300);
    }

    // After slide: clip B width UNCHANGED, but position MOVED
    // Clip A should be LONGER, Clip C should be SHORTER (they accommodate)
    const after = await page.evaluate(() => {
      const a = document.querySelector('[data-testid="cut-timeline-clip-v_a"]');
      const b = document.querySelector('[data-testid="cut-timeline-clip-v_b"]');
      const c = document.querySelector('[data-testid="cut-timeline-clip-v_c"]');
      if (!a || !b || !c) return null;
      return {
        aWidth: a.getBoundingClientRect().width,
        bLeft: b.getBoundingClientRect().left,
        bWidth: b.getBoundingClientRect().width,
        cWidth: c.getBoundingClientRect().width,
      };
    });

    if (before && after) {
      // Clip B width unchanged (slide doesn't change the moved clip)
      expect(after.bWidth).toBeCloseTo(before.bWidth, 0);
      // Clip B position should have moved right
      expect(after.bLeft).toBeGreaterThan(before.bLeft);
      // Clip A should be longer (expanded to fill)
      expect(after.aWidth).toBeGreaterThan(before.aWidth);
    }
  });
});

// ===========================================================================
// JKL PROGRESSIVE SHUTTLE (FCP7 App A + CUT_HOTKEY_ARCHITECTURE §5.3)
// ===========================================================================
test.describe.serial('FCP7 Precision: JKL Progressive Shuttle (TDD)', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // JKL1: pressing L once starts 1x forward playback
  // FCP7: L = play forward at 1x, LL = 2x, LLL = 4x, LLLL = 8x
  // Current CUT: L = seek(+5s) — WRONG
  // -------------------------------------------------------------------------
  test('JKL1: pressing L starts forward playback (not ±5s jump)', async ({ page }) => {
    await navigateToCut(page);

    // Seek to a known position
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().seek(3);
    });
    await page.waitForTimeout(100);

    const posBefore = await getStoreState(page, 'currentTime');

    // Press L — should start continuous playback, not jump +5s
    await page.keyboard.press('l');
    await page.waitForTimeout(500); // wait 500ms

    const posAfter = await getStoreState(page, 'currentTime');
    const delta = posAfter - posBefore;

    // Should have moved ~0.5s (500ms at 1x speed), NOT 5s
    // Allow range: 0.3s to 1.5s (accounting for frame timing)
    expect(delta).toBeGreaterThan(0.1);
    expect(delta).toBeLessThan(2.0);

    // Press K to stop
    await page.keyboard.press('k');
  });

  // -------------------------------------------------------------------------
  // JKL2: pressing L multiple times increases speed progressively
  // FCP7: L = 1x, LL = 2x, LLL = 4x, LLLL = 8x
  // -------------------------------------------------------------------------
  test('JKL2: pressing L twice doubles playback speed (2x)', async ({ page }) => {
    await navigateToCut(page);

    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().seek(2);
    });
    await page.waitForTimeout(100);

    // Press L twice for 2x speed
    await page.keyboard.press('l');
    await page.waitForTimeout(50);
    await page.keyboard.press('l');
    await page.waitForTimeout(50);

    // Check shuttle speed state
    const shuttleSpeed = await page.evaluate(() => {
      if (window.__CUT_STORE__) {
        const state = window.__CUT_STORE__.getState();
        return state.shuttleSpeed || state.playbackRate || state.rate || null;
      }
      return null;
    });

    // Should be 2x (or close to it)
    expect(shuttleSpeed).toBe(2);

    await page.keyboard.press('k'); // stop
  });

  // -------------------------------------------------------------------------
  // JKL3: pressing J plays in reverse, K stops
  // FCP7: J = reverse at 1x, JJ = 2x reverse, K = stop
  //        KL held together = slow forward, JK = slow reverse
  // -------------------------------------------------------------------------
  test('JKL3: pressing J starts reverse playback', async ({ page }) => {
    await navigateToCut(page);

    // Seek to middle so we have room to go backwards
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().seek(10);
    });
    await page.waitForTimeout(100);

    const posBefore = await getStoreState(page, 'currentTime');

    // Press J — should play in reverse
    await page.keyboard.press('j');
    await page.waitForTimeout(500);

    const posAfter = await getStoreState(page, 'currentTime');

    // Position should have DECREASED (reverse playback)
    expect(posAfter).toBeLessThan(posBefore);

    // Press K to stop
    await page.keyboard.press('k');
  });
});

// ===========================================================================
// MATCH FRAME (FCP7 Ch.50)
// ===========================================================================
test.describe.serial('FCP7 Precision: Match Frame (TDD)', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // MATCH1: pressing F opens source clip at same frame in Source Monitor
  // FCP7 Ch.50 p.810: "opens the master clip in the Viewer at the same
  //   frame as shown in the Canvas"
  // -------------------------------------------------------------------------
  test('MATCH1: F key triggers match frame action', async ({ page }) => {
    await navigateToCut(page);

    // Seek to middle of clip B (at ~7 seconds)
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().seek(7);
    });
    await page.waitForTimeout(200);

    // Press F — should open source clip in Source Monitor
    await page.keyboard.press('f');
    await page.waitForTimeout(300);

    // Source monitor should now show the source clip for v_b
    const sourceMediaPath = await page.evaluate(() => {
      if (window.__CUT_STORE__) {
        const state = window.__CUT_STORE__.getState();
        return state.sourceMediaPath || state.sourceClipPath || null;
      }
      return null;
    });

    // Source should be set to the clip under playhead
    expect(sourceMediaPath).toBeTruthy();
    // Should match clip B's source path
    expect(sourceMediaPath).toContain('interview-b');
  });

  // -------------------------------------------------------------------------
  // MATCH2: Q key toggles focus between Source and Program monitors
  // FCP7 Ch.50 p.809: "Press the Q key" to switch between Viewer and Canvas
  // -------------------------------------------------------------------------
  test('MATCH2: Q key toggles focus between Source and Program', async ({ page }) => {
    await navigateToCut(page);

    // Get initial focused panel
    const initialFocus = await getStoreState(page, 'focusedPanel');

    // Press Q — should toggle between source and program
    await page.keyboard.press('q');
    await page.waitForTimeout(200);

    const newFocus = await getStoreState(page, 'focusedPanel');

    // Focus should have changed
    if (initialFocus === 'program' || initialFocus === 'canvas') {
      expect(newFocus).toBe('source');
    } else if (initialFocus === 'source' || initialFocus === 'viewer') {
      expect(['program', 'canvas']).toContain(newFocus);
    } else {
      // If focusedPanel doesn't exist yet, just verify the key does something
      expect(newFocus).toBeTruthy();
    }
  });
});

// ===========================================================================
// SPLIT EDITS (FCP7 Ch.41 — L-cut / J-cut)
// ===========================================================================
test.describe.serial('FCP7 Precision: Split Edits (TDD)', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // SPLIT1: Cmd+L toggles linked selection
  // FCP7 Ch.40 p.591: "Linked Selection button" or Cmd+L
  // When off, video and audio can be edited independently
  // -------------------------------------------------------------------------
  test('SPLIT1: Cmd+L toggles linked selection', async ({ page }) => {
    await navigateToCut(page);

    const before = await getStoreState(page, 'linkedSelection');

    await page.keyboard.press('Meta+l');
    await page.waitForTimeout(200);

    const after = await getStoreState(page, 'linkedSelection');

    // Should have toggled
    if (before !== null) {
      expect(after).toBe(!before);
    } else {
      // Field must exist in store
      expect(after).not.toBeNull();
    }
  });

  // -------------------------------------------------------------------------
  // SPLIT2: Extend Edit (E key) — extend clip to playhead
  // FCP7: E key extends the nearest edit point to the playhead position
  // -------------------------------------------------------------------------
  test('SPLIT2: E key extends edit to playhead position', async ({ page }) => {
    await navigateToCut(page);

    // Get clip A duration before
    const clipABefore = await page.evaluate(() => {
      const clip = document.querySelector('[data-testid="cut-timeline-clip-v_a"]');
      return clip ? clip.getBoundingClientRect().width : 0;
    });

    // Seek to position within clip A but past its current Out point
    // Clip A is 0-5s, seek to 6s (past it, into clip B)
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().seek(6);
    });
    await page.waitForTimeout(200);

    // Select clip A's Out point (click near right edge)
    const clipA = page.locator('[data-testid="cut-timeline-clip-v_a"]');
    const box = await clipA.boundingBox().catch(() => null);
    if (box) {
      await page.mouse.click(box.x + box.width - 3, box.y + box.height / 2);
      await page.waitForTimeout(100);
    }

    // Press E to extend edit to playhead
    await page.keyboard.press('e');
    await page.waitForTimeout(300);

    // Clip A should now be wider (extended to playhead at 6s)
    const clipAAfter = await page.evaluate(() => {
      const clip = document.querySelector('[data-testid="cut-timeline-clip-v_a"]');
      return clip ? clip.getBoundingClientRect().width : 0;
    });

    expect(clipAAfter).toBeGreaterThan(clipABefore);
  });
});

// ===========================================================================
// SPEED CONTROLS (FCP7 Ch.69)
// ===========================================================================
test.describe.serial('FCP7 Precision: Speed Controls (TDD)', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // SPEED1: Cmd+J opens Change Speed dialog
  // FCP7 Ch.69 p.1165: "Choose Modify > Change Speed (or press Command-J)"
  // -------------------------------------------------------------------------
  test('SPEED1: Cmd+J opens speed control dialog/panel', async ({ page }) => {
    await navigateToCut(page);

    // Select a clip first
    const clip = page.locator('[data-testid^="cut-timeline-clip-"]').first();
    await clip.click();
    await page.waitForTimeout(200);

    // Press Cmd+J
    await page.keyboard.press('Meta+j');
    await page.waitForTimeout(300);

    // Speed control dialog/panel should appear
    const speedVisible = await page.evaluate(() => {
      // Look for speed control UI
      const speedPanel = document.querySelector(
        '[data-testid*="speed-control"], [data-testid*="speed-dialog"], ' +
        '[aria-label*="Speed"], [role="dialog"]:has(*:text("Speed"))'
      );
      if (speedPanel) return true;

      // Check if SpeedControl panel was activated/shown
      const text = document.body.textContent || '';
      return text.includes('Change Speed') || text.includes('Speed %') || text.includes('speed-rate');
    });

    expect(speedVisible).toBe(true);
  });

  // -------------------------------------------------------------------------
  // SPEED2: Speed indicators visible in timeline clips
  // FCP7 Ch.69 p.1176: "speed indicators — tick marks" showing playback speed
  // Normal = evenly spaced, slow = wide, fast = tight, reverse = red
  // -------------------------------------------------------------------------
  test('SPEED2: clips with modified speed show speed indicators', async ({ page }) => {
    await navigateToCut(page);

    // Apply a speed change to a clip via store (simulate)
    await page.evaluate(() => {
      if (window.__CUT_STORE__) {
        const state = window.__CUT_STORE__.getState();
        // Try to modify clip speed
        if (state.setClipSpeed) {
          state.setClipSpeed('v_c', 50); // 50% = slow motion
        }
      }
    });
    await page.waitForTimeout(300);

    // Look for speed indicator elements on the clip
    const hasSpeedIndicator = await page.evaluate(() => {
      const clipC = document.querySelector('[data-testid="cut-timeline-clip-v_c"]');
      if (!clipC) return false;

      // Speed indicators can be: tick marks, percentage badge, colored bar
      const indicators = clipC.querySelectorAll(
        '[data-testid*="speed-indicator"], [class*="speed-tick"], ' +
        '[class*="speed-badge"], span:has-text("%")'
      );
      if (indicators.length > 0) return true;

      // Check for speed percentage text in clip
      const text = clipC.textContent || '';
      return text.includes('%') || text.includes('50') || text.includes('speed');
    });

    expect(hasSpeedIndicator).toBe(true);
  });
});

// ===========================================================================
// THREE-POINT EDITING INTEGRATION (Alpha's P0 task — cross-check)
// ===========================================================================
test.describe.serial('FCP7 Precision: Three-Point Editing System (TDD)', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // 3PT1: Insert edit (,) places source between In/Out into timeline
  // FCP7 Ch.36: Source In/Out + Sequence position = Insert edit
  // This tests Alpha's CUT-3PT task — should work once they implement it
  // -------------------------------------------------------------------------
  test('3PT1: comma key performs insert edit from source', async ({ page }) => {
    await navigateToCut(page);

    // Set source In/Out marks (if source monitor is available)
    await page.evaluate(() => {
      if (window.__CUT_STORE__) {
        const state = window.__CUT_STORE__.getState();
        if (state.setSourceMarkIn) state.setSourceMarkIn(1);
        if (state.setSourceMarkOut) state.setSourceMarkOut(3);
      }
    });
    await page.waitForTimeout(100);

    const clipsBefore = await page.evaluate(() =>
      document.querySelectorAll('[data-testid^="cut-timeline-clip-"]').length
    );

    // Press , (comma) for insert edit
    await page.keyboard.press(',');
    await page.waitForTimeout(300);

    const clipsAfter = await page.evaluate(() =>
      document.querySelectorAll('[data-testid^="cut-timeline-clip-"]').length
    );

    // Insert should add a new clip (clip count increases)
    expect(clipsAfter).toBeGreaterThan(clipsBefore);
  });

  // -------------------------------------------------------------------------
  // 3PT2: Overwrite edit (.) replaces content at playhead
  // FCP7: . = overwrite edit (replace, don't shift)
  // -------------------------------------------------------------------------
  test('3PT2: period key performs overwrite edit from source', async ({ page }) => {
    await navigateToCut(page);

    // Set source marks
    await page.evaluate(() => {
      if (window.__CUT_STORE__) {
        const state = window.__CUT_STORE__.getState();
        if (state.setSourceMarkIn) state.setSourceMarkIn(0);
        if (state.setSourceMarkOut) state.setSourceMarkOut(2);
        // Seek to middle of timeline
        state.seek(7);
      }
    });
    await page.waitForTimeout(100);

    // Get total duration before overwrite
    const durationBefore = await getStoreState(page, 'duration');

    // Press . (period) for overwrite edit
    await page.keyboard.press('.');
    await page.waitForTimeout(300);

    // Overwrite should NOT change total duration (it replaces in-place)
    const durationAfter = await getStoreState(page, 'duration');

    if (durationBefore && durationAfter) {
      expect(durationAfter).toBe(durationBefore);
    }
  });
});
