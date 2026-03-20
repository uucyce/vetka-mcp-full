/**
 * MARKER_QA.FCP7_DEEP: TDD E2E tests for FCP7 deep compliance fixes.
 *
 * Written BEFORE implementation — tests WILL FAIL until corresponding
 * fix tasks are completed by Alpha/Gamma agents.
 *
 * Covers:
 *   TL1: Track height resize — Shift-T cycles sizes, drag divider
 *   TL2: Track visibility toggle — eye icon per track
 *   TL3: Timeline editable timecode field
 *   TL4: Timeline display controls (overlays, waveform toggle)
 *   MON1: Monitor transport centered, Go to Edit buttons present
 *   MON2: Monitor marking controls complete (Mark Clip X, Match Frame F)
 *   EDIT1: Razor Blade tool (B/C key) + Add Edit (⌘K = Ctrl-V in FCP7)
 *   EDIT2: Linked clip names underlined, out-of-sync indicators
 *   EDIT3: Through edit indicators (red triangles)
 *
 * Reference tasks:
 *   tb_1773992497_7  (track height)
 *   tb_1773992503_8  (track visibility)
 *   tb_1773992510_9  (timecode field)
 *   tb_1773992517_10 (display controls)
 *   tb_1773992489_6  (monitor transport)
 *
 * FCP7 Manual: Ch.6 (Viewer), Ch.7 (Canvas), Ch.9 (Timeline), Ch.39 (Cutting), Ch.40 (Linking)
 */
const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

// ---------------------------------------------------------------------------
// Server bootstrap (reuse pattern from layout tests)
// ---------------------------------------------------------------------------
const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_FCP7_PORT || 3009);
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
// Fixture: project with clips for editing tests
// ---------------------------------------------------------------------------
function createProjectWithClips() {
  return {
    success: true,
    schema_version: 'cut_project_state_v1',
    project: {
      project_id: 'cut-fcp7-compliance',
      display_name: 'FCP7 Deep Compliance',
      source_path: '/tmp/cut/fcp7-test.mov',
      sandbox_root: '/tmp/cut-fcp7',
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
            { clip_id: 'v_clip_a', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/cut/shot-a.mov' },
            { clip_id: 'v_clip_b', scene_id: 's2', start_sec: 5, duration_sec: 4, source_path: '/tmp/cut/shot-b.mov' },
            { clip_id: 'v_clip_c', scene_id: 's3', start_sec: 9, duration_sec: 3, source_path: '/tmp/cut/shot-c.mov' },
          ],
        },
        {
          lane_id: 'A1', lane_type: 'audio_main',
          clips: [
            { clip_id: 'a_clip_a', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/cut/audio-a.wav' },
            { clip_id: 'a_clip_b', scene_id: 's2', start_sec: 5, duration_sec: 4, source_path: '/tmp/cut/audio-b.wav' },
          ],
        },
        {
          lane_id: 'A2', lane_type: 'audio_main',
          clips: [
            { clip_id: 'a_music', scene_id: 's1', start_sec: 0, duration_sec: 12, source_path: '/tmp/cut/music.wav' },
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

async function navigateToCut(page) {
  await setupApiMocks(page);
  await page.goto(CUT_URL, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="cut-timeline-track-view"]', { timeout: 15000 });
}

// ===========================================================================
// TIMELINE TESTS
// ===========================================================================
test.describe.serial('FCP7 Deep Compliance: Timeline (TDD)', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // TL1: Track height resize
  // FCP7 p.146: Track Height controls — Reduced, Small, Medium, Large
  // FCP7 p.142: Track Size option in Sequence Settings
  // -------------------------------------------------------------------------
  test('TL1: track height can be changed via keyboard shortcut (Shift-T)', async ({ page }) => {
    await navigateToCut(page);

    // Get initial track height
    const initialHeight = await page.evaluate(() => {
      const lane = document.querySelector('[data-testid^="cut-timeline-lane-"]');
      return lane ? lane.getBoundingClientRect().height : 0;
    });
    expect(initialHeight).toBeGreaterThan(0);

    // Press Shift-T to cycle track height
    await page.keyboard.press('Shift+t');
    await page.waitForTimeout(300);

    const newHeight = await page.evaluate(() => {
      const lane = document.querySelector('[data-testid^="cut-timeline-lane-"]');
      return lane ? lane.getBoundingClientRect().height : 0;
    });

    // Height should have changed (either bigger or smaller depending on cycle direction)
    expect(newHeight).not.toBe(initialHeight);
  });

  test('TL1b: track divider between video and audio is draggable', async ({ page }) => {
    await navigateToCut(page);

    // Look for a draggable divider between video and audio tracks
    // FCP7 p.132: "divider between the two regions. You can drag the divider"
    const hasDivider = await page.evaluate(() => {
      // Search for elements that look like track dividers (cursor: row-resize or ns-resize)
      const allEls = document.querySelectorAll('[data-testid="cut-timeline-track-view"] *');
      for (const el of allEls) {
        const style = window.getComputedStyle(el);
        if (style.cursor === 'row-resize' || style.cursor === 'ns-resize' || style.cursor === 'n-resize') {
          return true;
        }
      }
      return false;
    });

    expect(hasDivider).toBe(true);
  });

  // -------------------------------------------------------------------------
  // TL2: Track visibility toggle (eye icon)
  // FCP7 p.131: "Track Visibility control: Determines whether the contents
  //   of a track are displayed and rendered"
  // -------------------------------------------------------------------------
  test('TL2: each track has a visibility toggle (eye icon)', async ({ page }) => {
    await navigateToCut(page);

    // Find visibility toggles in track headers
    const visibilityToggles = await page.evaluate(() => {
      const headers = document.querySelectorAll('[data-testid^="cut-timeline-lane-"]');
      let count = 0;
      headers.forEach(h => {
        // Look for eye icon button, or button with aria-label containing "visibility"
        const eyeBtn = h.querySelector('[aria-label*="visib"], [data-testid*="visibility"], [title*="Visibility"], button:has(svg[data-icon="eye"])');
        if (eyeBtn) count++;
      });
      return count;
    });

    // Should have at least one visibility toggle (for V1 track at minimum)
    expect(visibilityToggles).toBeGreaterThanOrEqual(1);
  });

  test('TL2b: clicking visibility toggle dims track content', async ({ page }) => {
    await navigateToCut(page);

    // Find and click visibility toggle on first track
    const clicked = await page.evaluate(() => {
      const lane = document.querySelector('[data-testid^="cut-timeline-lane-"]');
      if (!lane) return false;
      const eyeBtn = lane.querySelector('[aria-label*="visib"], [data-testid*="visibility"], [title*="Visibility"]');
      if (eyeBtn) { eyeBtn.click(); return true; }
      return false;
    });

    expect(clicked).toBe(true);
    await page.waitForTimeout(200);

    // Track content should be dimmed (reduced opacity)
    const isDimmed = await page.evaluate(() => {
      const lane = document.querySelector('[data-testid^="cut-timeline-lane-"]');
      if (!lane) return false;
      const style = window.getComputedStyle(lane);
      return parseFloat(style.opacity) < 0.9;
    });

    expect(isDimmed).toBe(true);
  });

  // -------------------------------------------------------------------------
  // TL3: Editable timecode field above timeline ruler
  // FCP7 p.134: "Current Timecode field: Indicates the timecode position of
  //   the playhead. Typing a new timecode number moves the playhead."
  // -------------------------------------------------------------------------
  test('TL3: editable timecode field exists above timeline ruler', async ({ page }) => {
    await navigateToCut(page);

    // Look for an editable timecode input in the timeline area
    const tcField = page.locator('input[data-testid="cut-timeline-timecode"], input[aria-label*="timecode"], input[placeholder*="00:00"]');
    const isVisible = await tcField.first().isVisible().catch(() => false);

    if (!isVisible) {
      // Fallback: look for a clickable timecode display that becomes editable
      const clickableTc = page.locator('[data-testid="cut-timeline-timecode-display"]');
      const clickableVisible = await clickableTc.first().isVisible().catch(() => false);
      expect(clickableVisible).toBe(true);
    } else {
      expect(isVisible).toBe(true);
    }
  });

  test('TL3b: typing timecode navigates playhead', async ({ page }) => {
    await navigateToCut(page);

    // Get initial playhead position
    const initialTime = await page.evaluate(() => {
      if (window.__CUT_STORE__) return window.__CUT_STORE__.getState().currentTime;
      return 0;
    });

    // Click timecode field and type a timecode (e.g., "500" = 5 seconds at 24fps)
    const tcField = page.locator('input[data-testid="cut-timeline-timecode"], input[aria-label*="timecode"]').first();
    const exists = await tcField.isVisible().catch(() => false);

    if (exists) {
      await tcField.click();
      await tcField.fill('00:00:05:00');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(300);

      const newTime = await page.evaluate(() => {
        if (window.__CUT_STORE__) return window.__CUT_STORE__.getState().currentTime;
        return 0;
      });

      // Playhead should have moved to ~5 seconds
      expect(newTime).toBeGreaterThan(initialTime);
    } else {
      // Field doesn't exist yet — TDD fail expected
      expect(false).toBe(true);
    }
  });

  // -------------------------------------------------------------------------
  // TL4: Timeline display controls
  // FCP7 p.145-146: Clip Keyframes, Clip Overlays, Track Height controls
  // FCP7 p.141: Track Layout popup menu
  // -------------------------------------------------------------------------
  test('TL4: timeline has display controls area (overlays, waveform toggle)', async ({ page }) => {
    await navigateToCut(page);

    // Look for timeline display controls area
    const hasDisplayControls = await page.evaluate(() => {
      const timeline = document.querySelector('[data-testid="cut-timeline-track-view"]');
      if (!timeline) return false;

      // Look for known display control elements
      const parent = timeline.closest('[style], .timeline-panel, [data-testid="cut-panel-timeline"]') || timeline.parentElement;
      if (!parent) return false;

      const text = parent.textContent || '';
      // Should have at least one of: waveform toggle, overlay toggle, track height selector
      return text.includes('Waveform') ||
             text.includes('Overlay') ||
             text.includes('Track Height') ||
             parent.querySelector('[data-testid*="display-control"], [aria-label*="waveform"], [aria-label*="overlay"]') !== null;
    });

    expect(hasDisplayControls).toBe(true);
  });
});

// ===========================================================================
// MONITOR TESTS
// ===========================================================================
test.describe.serial('FCP7 Deep Compliance: Monitors (TDD)', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // MON1: Transport controls centered
  // FCP7 p.92,109: Transport buttons are centered in Viewer/Canvas
  // Buttons: [Prev Edit] [Play In-Out] [Play] [Play Around] [Next Edit]
  // -------------------------------------------------------------------------
  test('MON1: transport buttons are horizontally centered in source monitor', async ({ page }) => {
    await navigateToCut(page);

    const alignment = await page.evaluate(() => {
      // Find the transport controls row (contains Play button)
      const allButtons = document.querySelectorAll('button');
      let transportRow = null;

      for (const btn of allButtons) {
        // Play button typically has an SVG play icon or ► character
        if (btn.closest('[data-testid="cut-timeline-track-view"]')) continue; // skip timeline buttons
        const svg = btn.querySelector('svg');
        const text = btn.textContent || '';
        if (svg || text.includes('▶') || text.includes('►')) {
          transportRow = btn.parentElement;
          break;
        }
      }

      if (!transportRow) return { centered: false, reason: 'no transport row found' };

      const rowRect = transportRow.getBoundingClientRect();
      const parentRect = transportRow.parentElement.getBoundingClientRect();

      // Calculate centering: row center should be within 20% of parent center
      const rowCenter = rowRect.left + rowRect.width / 2;
      const parentCenter = parentRect.left + parentRect.width / 2;
      const offset = Math.abs(rowCenter - parentCenter);
      const tolerance = parentRect.width * 0.2;

      return {
        centered: offset < tolerance,
        offset: Math.round(offset),
        tolerance: Math.round(tolerance),
        rowCenter: Math.round(rowCenter),
        parentCenter: Math.round(parentCenter),
      };
    });

    expect(alignment.centered).toBe(true);
  });

  test('MON1b: Go to Previous/Next Edit buttons exist in transport', async ({ page }) => {
    await navigateToCut(page);

    // FCP7 p.92: Go to Previous Edit (Up Arrow) and Go to Next Edit (Down Arrow)
    // These should be visible buttons, not just hotkeys
    const hasEditNav = await page.evaluate(() => {
      const body = document.body.textContent || '';
      // Look for edit navigation buttons by various selectors
      const prevEdit = document.querySelector(
        '[aria-label*="previous edit"], [aria-label*="prev edit"], [title*="Previous Edit"], [data-testid*="prev-edit"]'
      );
      const nextEdit = document.querySelector(
        '[aria-label*="next edit"], [title*="Next Edit"], [data-testid*="next-edit"]'
      );
      return { hasPrev: !!prevEdit, hasNext: !!nextEdit };
    });

    expect(hasEditNav.hasPrev).toBe(true);
    expect(hasEditNav.hasNext).toBe(true);
  });

  // -------------------------------------------------------------------------
  // MON2: Source monitor marking controls
  // FCP7 p.95: Mark Clip (X), Mark In (I), Mark Out (O), Add Marker (M),
  //            Add Motion Keyframe (Ctrl-K), Show Match Frame (F)
  // -------------------------------------------------------------------------
  test('MON2: source monitor has Mark Clip (X) and Match Frame (F) buttons', async ({ page }) => {
    await navigateToCut(page);

    const hasMarkingButtons = await page.evaluate(() => {
      // Look in Source monitor area (not timeline)
      const sourcePanel = document.querySelector('[data-testid="cut-panel-source"]') ||
                          document.querySelector('.dv-groupview:has(span:text("SOURCE"))');
      if (!sourcePanel) return { markClip: false, matchFrame: false, reason: 'no source panel' };

      const text = sourcePanel.textContent || '';
      const markClip = sourcePanel.querySelector(
        '[aria-label*="mark clip"], [title*="Mark Clip"], [data-testid*="mark-clip"], button:has-text("X")'
      );
      const matchFrame = sourcePanel.querySelector(
        '[aria-label*="match frame"], [title*="Match Frame"], [data-testid*="match-frame"]'
      );

      return {
        markClip: !!markClip || text.includes('Mark Clip'),
        matchFrame: !!matchFrame || text.includes('Match Frame'),
      };
    });

    expect(hasMarkingButtons.markClip).toBe(true);
    expect(hasMarkingButtons.matchFrame).toBe(true);
  });
});

// ===========================================================================
// EDITING OPERATION TESTS
// ===========================================================================
test.describe.serial('FCP7 Deep Compliance: Editing (TDD)', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // EDIT1: Razor Blade tool
  // FCP7 p.585-587: Razor Blade (B key) cuts a single clip,
  //   Razor Blade All cuts all tracks. Add Edit (⌘K) cuts at playhead.
  // -------------------------------------------------------------------------
  test('EDIT1: pressing B activates Razor tool, clicking clip splits it', async ({ page }) => {
    await navigateToCut(page);

    // Count clips before
    const clipsBefore = await page.evaluate(() => {
      return document.querySelectorAll('[data-testid^="cut-timeline-clip-"]').length;
    });

    // Activate Razor tool
    await page.keyboard.press('b');
    await page.waitForTimeout(200);

    // Verify tool state changed (cursor should change or tool indicator visible)
    const toolActive = await page.evaluate(() => {
      if (window.__CUT_STORE__) {
        const state = window.__CUT_STORE__.getState();
        return state.activeTool === 'razor' || state.activeTool === 'cut' || state.activeTool === 'blade';
      }
      return null;
    });

    // Tool should be razor/blade/cut
    expect(toolActive).toBeTruthy();

    // Click on a clip to split it (click middle of first clip)
    const firstClip = page.locator('[data-testid^="cut-timeline-clip-"]').first();
    const box = await firstClip.boundingBox();
    if (box) {
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(300);
    }

    // Count clips after — should have one more
    const clipsAfter = await page.evaluate(() => {
      return document.querySelectorAll('[data-testid^="cut-timeline-clip-"]').length;
    });

    expect(clipsAfter).toBe(clipsBefore + 1);

    // Switch back to selection tool
    await page.keyboard.press('v');
  });

  // -------------------------------------------------------------------------
  // EDIT2: Linked clips — underlined names + out-of-sync indicators
  // FCP7 p.592: "The names of the linked clip items are underlined"
  // FCP7 p.592: Out-of-sync indicators (red badge with offset)
  // -------------------------------------------------------------------------
  test('EDIT2: linked video+audio clip names are underlined in timeline', async ({ page }) => {
    await navigateToCut(page);

    const hasUnderlinedClips = await page.evaluate(() => {
      const clips = document.querySelectorAll('[data-testid^="cut-timeline-clip-"]');
      for (const clip of clips) {
        // Look for text-decoration: underline on clip name elements
        const nameEls = clip.querySelectorAll('span, div');
        for (const el of nameEls) {
          const style = window.getComputedStyle(el);
          if (style.textDecoration.includes('underline') || style.textDecorationLine?.includes('underline')) {
            return true;
          }
        }
      }
      return false;
    });

    // Clips from same source (video + audio) should have underlined names
    expect(hasUnderlinedClips).toBe(true);
  });

  // -------------------------------------------------------------------------
  // EDIT3: Through edit indicators
  // FCP7 p.588: "through edit indicators — two red triangles"
  // When you razor blade a clip, edit point shows through edit markers
  // -------------------------------------------------------------------------
  test('EDIT3: through edits shown as red triangles after razor cut', async ({ page }) => {
    await navigateToCut(page);

    // After a razor cut, adjacent clips from same source show through edit indicators
    // This is a display feature — look for red triangle markers at edit points
    const hasThroughEditIndicator = await page.evaluate(() => {
      const timeline = document.querySelector('[data-testid="cut-timeline-track-view"]');
      if (!timeline) return false;

      // Look for through edit markers (red triangles, typically SVG or CSS borders)
      const redElements = timeline.querySelectorAll('[data-testid*="through-edit"], [class*="through-edit"]');
      if (redElements.length > 0) return true;

      // Fallback: look for red-colored triangle elements near clip boundaries
      const allEls = timeline.querySelectorAll('*');
      for (const el of allEls) {
        const style = window.getComputedStyle(el);
        const color = style.color || style.borderColor || style.backgroundColor || '';
        // Red colors: #f00, #ef4444, #c44, rgb(239,68,68), etc.
        if ((color.includes('239, 68, 68') || color.includes('244, 63, 63') || color.includes('255, 0, 0')) &&
            el.getBoundingClientRect().width < 20 && el.getBoundingClientRect().height < 20) {
          return true;
        }
      }
      return false;
    });

    // Through edit indicators should exist (at minimum as a feature capability)
    // This will fail until the feature is implemented
    expect(hasThroughEditIndicator).toBe(true);
  });
});

// ===========================================================================
// SNAPPING KEY COMPLIANCE
// ===========================================================================
test.describe('FCP7 Deep Compliance: Keyboard Mapping (TDD)', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // FCP7 uses N for snapping, CUT uses S. This is intentional (Premiere uses S).
  // But FCP7's Linked Selection is Shift-L. CUT should support both.
  test('KEYS: Linked Selection toggles with Shift-L (FCP7 standard)', async ({ page }) => {
    await navigateToCut(page);

    // Get initial linked selection state
    const initialState = await page.evaluate(() => {
      if (window.__CUT_STORE__) return window.__CUT_STORE__.getState().linkedSelection;
      return null;
    });

    // Press Shift-L (FCP7 standard for linked selection toggle)
    await page.keyboard.press('Shift+l');
    await page.waitForTimeout(200);

    const newState = await page.evaluate(() => {
      if (window.__CUT_STORE__) return window.__CUT_STORE__.getState().linkedSelection;
      return null;
    });

    // If store is accessible, state should have toggled
    if (initialState !== null) {
      expect(newState).not.toBe(initialState);
    }
  });

  // FCP7 p.587: Add Edit = Control-V (FCP7) / ⌘K (Premiere/CUT)
  // Both should work
  test('KEYS: Add Edit works via ⌘K (Premiere) — split at playhead', async ({ page }) => {
    await navigateToCut(page);

    const clipsBefore = await page.evaluate(() => {
      return document.querySelectorAll('[data-testid^="cut-timeline-clip-"]').length;
    });

    // Seek to middle of a clip first
    await page.evaluate(() => {
      if (window.__CUT_STORE__) window.__CUT_STORE__.getState().seek(2.5);
    });
    await page.waitForTimeout(200);

    // ⌘K = Add Edit / Split at playhead
    await page.keyboard.press('Meta+k');
    await page.waitForTimeout(300);

    const clipsAfter = await page.evaluate(() => {
      return document.querySelectorAll('[data-testid^="cut-timeline-clip-"]').length;
    });

    // Should have split one clip into two
    expect(clipsAfter).toBe(clipsBefore + 1);
  });
});
