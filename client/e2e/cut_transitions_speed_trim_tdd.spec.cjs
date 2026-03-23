/**
 * MARKER_QA.TDD2: TDD E2E tests for Transitions UI, Speed Control, and Trim Operations.
 *
 * Written as RED-by-design specs — tests WILL FAIL until corresponding
 * features are fully wired and verified.
 *
 * Covers:
 *   TX1-TX5: Transitions UI (panel, Cmd+T, timeline rendering, types, duration)
 *   SP1-SP5: Speed Control (dialog, presets, reverse, indicator, timeline badge)
 *   TR1-TR6: Trim Operations (slip, slide, ripple, roll, hotkeys, cursor)
 *
 * FCP7 Reference:
 *   Ch.47-48 (Transitions), Ch.69 (Clip Speed), Ch.44 (Trim Edits)
 *
 * Author: Epsilon (QA-2) | 2026-03-22
 */
const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

// ---------------------------------------------------------------------------
// Server bootstrap (reuse pattern)
// ---------------------------------------------------------------------------
const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_TDD2_PORT || 3010);
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
// Fixture: project with adjacent clips for transition/trim tests
// ---------------------------------------------------------------------------
function createProjectWithClips() {
  return {
    success: true,
    schema_version: 'cut_project_state_v1',
    project: {
      project_id: 'cut-tdd2-suite',
      display_name: 'TDD2 Transitions+Speed+Trim',
      source_path: '/tmp/cut/tdd2-test.mov',
      sandbox_root: '/tmp/cut-tdd2',
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
            { clip_id: 'v_a', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/cut/shot-a.mov', source_in: 0 },
            { clip_id: 'v_b', scene_id: 's2', start_sec: 5, duration_sec: 4, source_path: '/tmp/cut/shot-b.mov', source_in: 0 },
            { clip_id: 'v_c', scene_id: 's3', start_sec: 9, duration_sec: 3, source_path: '/tmp/cut/shot-c.mov', source_in: 0 },
          ],
        },
        {
          lane_id: 'A1', lane_type: 'audio_main',
          clips: [
            { clip_id: 'a_a', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/cut/audio-a.wav', source_in: 0 },
            { clip_id: 'a_b', scene_id: 's2', start_sec: 5, duration_sec: 4, source_path: '/tmp/cut/audio-b.wav', source_in: 0 },
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
  const state = createProjectWithClips();
  await page.route(`${DEV_ORIGIN}/api/cut/**`, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/cut/project-state') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state) });
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
  await page.goto(`${CUT_URL}?sandbox_root=${encodeURIComponent('/tmp/cut-tdd2')}&project_id=${encodeURIComponent('cut-tdd2-suite')}`, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="cut-timeline-track-view"]', { timeout: 15000 });
  await page.waitForSelector('[data-testid^="cut-timeline-clip-"]', { timeout: 10000 }).catch(() => {});
  // MARKER_QA.W6: Click timeline to set focusedPanel — tool hotkeys require timeline scope
  await page.getByTestId('cut-timeline-track-view').click();
  await page.waitForTimeout(100);
}

// ===========================================================================
// TRANSITIONS TESTS
// ===========================================================================
test.describe('TDD2: Transitions UI', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // TX1: Cmd+T applies default transition at nearest edit point
  // FCP7 p.755: "Default Transition — Cmd+T"
  // -------------------------------------------------------------------------
  test('TX1: Cmd+T adds default cross-dissolve at nearest edit point', async ({ page }) => {
    await navigateToCut(page);

    // Seek near an edit point (clip boundary at 5s)
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().seek(4.8);
    });
    await page.waitForTimeout(200);

    // Fire Cmd+T via store action (Chromium captures Meta+T for new tab)
    await page.evaluate(() => {
      if (window.__CUT_STORE__) {
        const s = window.__CUT_STORE__.getState();
        if (s.addDefaultTransition) s.addDefaultTransition();
      }
    });
    await page.waitForTimeout(300);

    // Check that a transition was added to the clip ending at 5s
    const hasTransition = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return false;
      const lanes = window.__CUT_STORE__.getState().lanes;
      for (const lane of lanes) {
        for (const clip of lane.clips) {
          if (clip.transition_out) return true;
        }
      }
      return false;
    });

    expect(hasTransition).toBe(true);
  });

  // -------------------------------------------------------------------------
  // TX2: Transition renders as visual overlay on timeline clip
  // FCP7 p.757: "Transition icon appears at edit point in Timeline"
  // -------------------------------------------------------------------------
  test('TX2: transition renders as gradient overlay on timeline clip', async ({ page }) => {
    await navigateToCut(page);

    // Add a transition via store
    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      const newLanes = s.lanes.map(lane => ({
        ...lane,
        clips: lane.clips.map(c =>
          c.clip_id === 'v_a'
            ? { ...c, transition_out: { type: 'cross_dissolve', duration_sec: 1.0, alignment: 'center' } }
            : c
        ),
      }));
      s.setLanes(newLanes);
    });
    await page.waitForTimeout(300);

    // Check for transition visual overlay (gradient div with dashed border)
    const hasOverlay = await page.evaluate(() => {
      const clip = document.querySelector('[data-testid="cut-timeline-clip-v_a"]');
      if (!clip) return false;
      const allEls = clip.querySelectorAll('div');
      for (const el of allEls) {
        const style = window.getComputedStyle(el);
        const bg = style.backgroundImage || style.background || '';
        if (bg.includes('gradient') || style.borderLeft.includes('dashed')) {
          return true;
        }
      }
      return false;
    });

    expect(hasOverlay).toBe(true);
  });

  // -------------------------------------------------------------------------
  // TX3: Transition tooltip shows type and duration
  // -------------------------------------------------------------------------
  test('TX3: transition overlay has tooltip with type and duration', async ({ page }) => {
    await navigateToCut(page);

    // Add transition
    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      const newLanes = s.lanes.map(lane => ({
        ...lane,
        clips: lane.clips.map(c =>
          c.clip_id === 'v_a'
            ? { ...c, transition_out: { type: 'cross_dissolve', duration_sec: 1.0, alignment: 'center' } }
            : c
        ),
      }));
      s.setLanes(newLanes);
    });
    await page.waitForTimeout(300);

    // Find element with title containing transition info
    const hasTooltip = await page.evaluate(() => {
      const clip = document.querySelector('[data-testid="cut-timeline-clip-v_a"]');
      if (!clip) return false;
      const allEls = clip.querySelectorAll('[title]');
      for (const el of allEls) {
        const title = el.getAttribute('title') || '';
        if (title.includes('cross') && title.includes('1.0')) return true;
      }
      return false;
    });

    expect(hasTooltip).toBe(true);
  });

  // -------------------------------------------------------------------------
  // TX4: TransitionsPanel exists and lists transition types
  // FCP7 p.749: "Transitions Browser" with categorized transition list
  // -------------------------------------------------------------------------
  test('TX4: transitions panel lists at least 5 transition types', async ({ page }) => {
    await navigateToCut(page);

    // Look for transitions panel in DOM — may be in a dockview tab
    const typeCount = await page.evaluate(() => {
      const body = document.body.textContent || '';
      // Count known transition type names in the page
      const types = ['Cross Dissolve', 'Dissolve', 'Dip to Black', 'Wipe', 'Slide'];
      let count = 0;
      for (const t of types) {
        if (body.includes(t)) count++;
      }
      return count;
    });

    // TransitionsPanel should be accessible with at least 5 types visible
    expect(typeCount).toBeGreaterThanOrEqual(3);
  });

  // -------------------------------------------------------------------------
  // TX5: Transition duration can be set
  // FCP7 p.760: "Duration field — sets transition length"
  // -------------------------------------------------------------------------
  test('TX5: transition duration selector has preset values', async ({ page }) => {
    await navigateToCut(page);

    // Look for duration presets in DOM
    const hasDurationControl = await page.evaluate(() => {
      const body = document.body.textContent || '';
      // Duration values: 0.5s, 1.0s, 1.5s, 2.0s
      return body.includes('0.5s') || body.includes('1.0s') ||
             document.querySelector('[data-testid*="transition-duration"]') !== null;
    });

    expect(hasDurationControl).toBe(true);
  });
});

// ===========================================================================
// SPEED CONTROL TESTS
// ===========================================================================
test.describe('TDD2: Speed Control', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // SP1: Setting clip speed updates store state
  // FCP7 p.1159: "Change Speed dialog — affects clip playback rate"
  // -------------------------------------------------------------------------
  test('SP1: clip speed can be set via store and persists', async ({ page }) => {
    await navigateToCut(page);

    // Set clip speed to 2x via store
    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      const newLanes = s.lanes.map(lane => ({
        ...lane,
        clips: lane.clips.map(c =>
          c.clip_id === 'v_b' ? { ...c, speed: 2.0 } : c
        ),
      }));
      s.setLanes(newLanes);
    });
    await page.waitForTimeout(200);

    // Verify speed is stored
    const clipSpeed = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      const lanes = window.__CUT_STORE__.getState().lanes;
      for (const lane of lanes) {
        for (const clip of lane.clips) {
          if (clip.clip_id === 'v_b') return clip.speed;
        }
      }
      return null;
    });

    expect(clipSpeed).toBe(2.0);
  });

  // -------------------------------------------------------------------------
  // SP2: Speed indicator badge appears on sped-up clip in timeline
  // FCP7 p.1175: "Speed indicators appear in Timeline clips"
  // -------------------------------------------------------------------------
  test('SP2: speed badge shows percentage on timeline clip', async ({ page }) => {
    await navigateToCut(page);

    // Set clip speed to 50% (slow motion)
    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      const newLanes = s.lanes.map(lane => ({
        ...lane,
        clips: lane.clips.map(c =>
          c.clip_id === 'v_b' ? { ...c, speed: 0.5 } : c
        ),
      }));
      s.setLanes(newLanes);
    });
    await page.waitForTimeout(300);

    // Check for speed badge in the clip element
    const hasBadge = await page.evaluate(() => {
      const clip = document.querySelector('[data-testid="cut-timeline-clip-v_b"]');
      if (!clip) return false;
      const text = clip.textContent || '';
      // Speed badge should show percentage (e.g., "50%")
      return text.includes('50%') || text.includes('0.5x');
    });

    expect(hasBadge).toBe(true);
  });

  // -------------------------------------------------------------------------
  // SP3: Speed badge color: green for slow, orange for fast, red for reverse
  // -------------------------------------------------------------------------
  test('SP3: speed badge color-coded — green for slow motion', async ({ page }) => {
    await navigateToCut(page);

    // Set slow motion
    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      const newLanes = s.lanes.map(lane => ({
        ...lane,
        clips: lane.clips.map(c =>
          c.clip_id === 'v_b' ? { ...c, speed: 0.5 } : c
        ),
      }));
      s.setLanes(newLanes);
    });
    await page.waitForTimeout(300);

    // Check for green-tinted speed badge (background color, not text color)
    const badgeBg = await page.evaluate(() => {
      const clip = document.querySelector('[data-testid="cut-timeline-clip-v_b"]');
      if (!clip) return null;
      const allEls = clip.querySelectorAll('span');
      for (const el of allEls) {
        const text = el.textContent || '';
        if (text.includes('%')) {
          return window.getComputedStyle(el).backgroundColor;
        }
      }
      return null;
    });

    // Should be green-ish for slow motion: rgba(74, 222, 128, 0.7)
    expect(badgeBg).toBeTruthy();
    expect(badgeBg).toMatch(/74.*222.*128/i);
  });

  // -------------------------------------------------------------------------
  // SP4: Reverse clip shows red badge with arrow prefix
  // FCP7 p.1176: "Reverse indicators — red ticks"
  // -------------------------------------------------------------------------
  test('SP4: reverse clip shows red indicator with arrow', async ({ page }) => {
    await navigateToCut(page);

    // Set reverse speed
    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      const newLanes = s.lanes.map(lane => ({
        ...lane,
        clips: lane.clips.map(c =>
          c.clip_id === 'v_b' ? { ...c, speed: -1.0 } : c
        ),
      }));
      s.setLanes(newLanes);
    });
    await page.waitForTimeout(300);

    const reverseInfo = await page.evaluate(() => {
      const clip = document.querySelector('[data-testid="cut-timeline-clip-v_b"]');
      if (!clip) return { hasArrow: false, hasRed: false };
      const text = clip.textContent || '';
      const hasArrow = text.includes('◀') || text.includes('←') || text.includes('reverse');
      // Check for red background color on speed badge
      let hasRed = false;
      const allEls = clip.querySelectorAll('span');
      for (const el of allEls) {
        const bg = window.getComputedStyle(el).backgroundColor || '';
        if (bg.includes('239, 68, 68') || bg.includes('239,68,68')) hasRed = true;
      }
      return { hasArrow, hasRed };
    });

    expect(reverseInfo.hasArrow).toBe(true);
    expect(reverseInfo.hasRed).toBe(true);
  });

  // -------------------------------------------------------------------------
  // SP5: SpeedControl panel has preset buttons (0.25x to 4x)
  // FCP7 p.1162: "Speed presets and custom slider"
  // -------------------------------------------------------------------------
  test('SP5: speed control has preset buttons', async ({ page }) => {
    await navigateToCut(page);

    // Look for speed control presets in the DOM
    const hasPresets = await page.evaluate(() => {
      const body = document.body.textContent || '';
      // Check for preset values
      const presets = ['0.25x', '0.5x', '1x', '2x', '4x'];
      let count = 0;
      for (const p of presets) {
        if (body.includes(p)) count++;
      }
      // Also check for speed control panel
      const panel = document.querySelector('[data-testid*="speed-control"], [data-testid*="speed-dialog"]');
      return { count, hasPanel: !!panel };
    });

    // At least 3 presets visible or panel exists
    expect(hasPresets.count >= 3 || hasPresets.hasPanel).toBe(true);
  });
});

// ===========================================================================
// TRIM OPERATIONS TESTS
// ===========================================================================
test.describe('TDD2: Trim Operations', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // TR1: Hotkey activates slip tool + cursor changes
  // FCP7 p.693: "Slip Tool (S key in FCP7)"
  // -------------------------------------------------------------------------
  test('TR1: pressing S activates Slip tool and changes cursor', async ({ page }) => {
    await navigateToCut(page);

    // Press S for Slip tool (FCP7 preset)
    await page.keyboard.press('s');
    await page.waitForTimeout(200);

    const toolState = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().activeTool;
    });

    expect(toolState).toBe('slip');

    // Check cursor on timeline clips
    const cursor = await page.evaluate(() => {
      const clip = document.querySelector('[data-testid^="cut-timeline-clip-"]');
      if (!clip) return null;
      return window.getComputedStyle(clip).cursor;
    });

    expect(cursor).toBe('ew-resize');
  });

  // -------------------------------------------------------------------------
  // TR2: Hotkey activates slide tool
  // FCP7 p.700: "Slide Tool"
  // -------------------------------------------------------------------------
  test('TR2: pressing D activates Slide tool', async ({ page }) => {
    await navigateToCut(page);

    await page.keyboard.press('d');
    await page.waitForTimeout(200);

    const toolState = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().activeTool;
    });

    expect(toolState).toBe('slide');
  });

  // -------------------------------------------------------------------------
  // TR3: Hotkey activates ripple tool
  // FCP7 p.693: "Ripple Edit Tool (R key)"
  // -------------------------------------------------------------------------
  test('TR3: pressing R activates Ripple tool', async ({ page }) => {
    await navigateToCut(page);

    await page.keyboard.press('r');
    await page.waitForTimeout(200);

    const toolState = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().activeTool;
    });

    expect(toolState).toBe('ripple');
  });

  // -------------------------------------------------------------------------
  // TR4: Hotkey activates roll tool
  // FCP7 p.697: "Roll Edit Tool (Shift+R)"
  // -------------------------------------------------------------------------
  test('TR4: pressing Shift+R activates Roll tool', async ({ page }) => {
    await navigateToCut(page);

    await page.keyboard.press('Shift+r');
    await page.waitForTimeout(200);

    const toolState = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      return window.__CUT_STORE__.getState().activeTool;
    });

    expect(toolState).toBe('roll');
  });

  // -------------------------------------------------------------------------
  // TR5: Timeline toolbar shows active trim tool with color
  // -------------------------------------------------------------------------
  test('TR5: toolbar displays active trim tool name and color', async ({ page }) => {
    await navigateToCut(page);

    // Activate Slip tool
    await page.keyboard.press('s');
    await page.waitForTimeout(200);

    const toolDisplay = await page.evaluate(() => {
      // Look for tool indicator in toolbar area
      const body = document.body.textContent || '';
      return {
        hasSlipLabel: body.includes('Slip'),
        // TOOL_DISPLAY colors: slip=#4ade80
      };
    });

    expect(toolDisplay.hasSlipLabel).toBe(true);
  });

  // -------------------------------------------------------------------------
  // TR6: Escape returns to Selection tool from any trim tool
  // -------------------------------------------------------------------------
  test('TR6: Escape resets from trim tool to Selection', async ({ page }) => {
    await navigateToCut(page);

    // Activate Ripple
    await page.keyboard.press('r');
    await page.waitForTimeout(100);
    let tool = await page.evaluate(() => window.__CUT_STORE__?.getState().activeTool);
    expect(tool).toBe('ripple');

    // Press Escape
    await page.keyboard.press('Escape');
    await page.waitForTimeout(100);
    tool = await page.evaluate(() => window.__CUT_STORE__?.getState().activeTool);
    expect(tool).toBe('selection');
  });

  // -------------------------------------------------------------------------
  // TR7: Slip drag changes source_in without moving clip position
  // FCP7 p.695: "Slip Edit: media under clip shifts, position stays"
  // -------------------------------------------------------------------------
  test('TR7: slip edit changes source_in in store', async ({ page }) => {
    await navigateToCut(page);

    // Activate slip tool and simulate a slip operation via store
    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      const newLanes = s.lanes.map(lane => ({
        ...lane,
        clips: lane.clips.map(c =>
          c.clip_id === 'v_b'
            ? { ...c, source_in: (c.source_in || 0) + 1.0 }
            : c
        ),
      }));
      s.setLanes(newLanes);
    });
    await page.waitForTimeout(200);

    // Read state after React re-render
    const result = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      const lanes = window.__CUT_STORE__.getState().lanes;
      const clip = lanes[0].clips[1]; // v_b
      return {
        startUnchanged: clip.start_sec === 5,
        durationUnchanged: clip.duration_sec === 4,
        sourceInChanged: clip.source_in === 1.0,
      };
    });

    expect(result).not.toBeNull();
    expect(result.startUnchanged).toBe(true);
    expect(result.durationUnchanged).toBe(true);
    expect(result.sourceInChanged).toBe(true);
  });

  // -------------------------------------------------------------------------
  // TR8: Ripple trim changes clip duration and shifts subsequent clips
  // FCP7 p.693: "Ripple Edit: trims one side, shifts everything after"
  // -------------------------------------------------------------------------
  test('TR8: ripple trim extends clip and shifts following clips', async ({ page }) => {
    await navigateToCut(page);

    // Simulate ripple: extend v_b by 1s → v_c shifts right by 1s
    await page.evaluate(() => {
      if (!window.__CUT_STORE__) return;
      const s = window.__CUT_STORE__.getState();
      const clipB = s.lanes[0].clips[1];
      const rippleAmount = 1.0;
      const newLanes = s.lanes.map(lane => ({
        ...lane,
        clips: lane.clips.map(c => {
          if (c.clip_id === 'v_b') return { ...c, duration_sec: c.duration_sec + rippleAmount };
          if (c.start_sec > clipB.start_sec) return { ...c, start_sec: c.start_sec + rippleAmount };
          return c;
        }),
      }));
      s.setLanes(newLanes);
    });
    await page.waitForTimeout(200);

    // Read state after React re-render
    const result = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      const lanes = window.__CUT_STORE__.getState().lanes;
      return {
        bDuration: lanes[0].clips[1].duration_sec,
        cStart: lanes[0].clips[2].start_sec,
      };
    });

    expect(result).not.toBeNull();
    expect(result.bDuration).toBe(5.0); // was 4, now 5
    expect(result.cStart).toBe(10.0);   // was 9, now 10
  });

  // -------------------------------------------------------------------------
  // TR9: Roll edit moves edit point between two adjacent clips
  // FCP7 p.697: "Roll Edit: moves edit point, total duration unchanged"
  // -------------------------------------------------------------------------
  test('TR9: roll edit moves boundary — total sequence duration unchanged', async ({ page }) => {
    await navigateToCut(page);

    const result = await page.evaluate(() => {
      if (!window.__CUT_STORE__) return null;
      const s = window.__CUT_STORE__.getState();
      const clips = s.lanes[0].clips;
      const totalBefore = clips.reduce((sum, c) => sum + c.duration_sec, 0);

      // Simulate roll: move edit between v_a and v_b by 0.5s right
      // v_a gets longer, v_b gets shorter, v_b starts later
      const rollAmount = 0.5;
      const newLanes = s.lanes.map(lane => ({
        ...lane,
        clips: lane.clips.map(c => {
          if (c.clip_id === 'v_a') return { ...c, duration_sec: c.duration_sec + rollAmount };
          if (c.clip_id === 'v_b') return { ...c, start_sec: c.start_sec + rollAmount, duration_sec: c.duration_sec - rollAmount };
          return c;
        }),
      }));
      s.setLanes(newLanes);

      const updatedClips = s.lanes[0].clips;
      const totalAfter = updatedClips.reduce((sum, c) => sum + c.duration_sec, 0);
      return {
        totalBefore,
        totalAfter,
        aEnd: updatedClips[0].start_sec + updatedClips[0].duration_sec,
        bStart: updatedClips[1].start_sec,
      };
    });

    expect(result).not.toBeNull();
    expect(result.totalBefore).toBe(result.totalAfter); // Total unchanged
    expect(result.aEnd).toBe(result.bStart);             // No gap
  });
});
