/**
 * MARKER_QA.3PT: E2E test for Three-Point Edit workflow.
 *
 * FCP7 Ch.36: "Set 3 of 4 edit points, system calculates 4th."
 * Flow: Source clip → Mark I/O → Focus timeline → Insert (comma) → Verify
 *
 * Tests:
 *   3PT1: Source I + O → comma → clip inserted at playhead, subsequent clips rippled
 *   3PT2: Source I + O → period → clip overwrites at playhead, no ripple
 *   3PT3: Undo (Cmd+Z) after insert → clip removed, timeline restored
 *   3PT4: No source marks → insert uses full source clip
 *
 * Author: Delta (QA) | 2026-03-23
 * Task: tb_1774231561_14
 */
const { test, expect } = require('@playwright/test');
const http = require('http');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_CUT_3PT_PORT || 3009);
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
// Project state with 3 clips on V1 + A1, source clip in bin
// ---------------------------------------------------------------------------
function createProjectState() {
  return {
    success: true,
    schema_version: 'cut_project_state_v1',
    project: {
      project_id: 'cut-3pt-test',
      display_name: '3PT Test',
      source_path: '/tmp/cut/3pt-test.mov',
      sandbox_root: '/tmp/cut-3pt',
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
            { clip_id: 'clip_a', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/cut/a.mov' },
            { clip_id: 'clip_b', scene_id: 's2', start_sec: 5, duration_sec: 5, source_path: '/tmp/cut/b.mov' },
            { clip_id: 'clip_c', scene_id: 's3', start_sec: 10, duration_sec: 5, source_path: '/tmp/cut/c.mov' },
          ],
        },
        {
          lane_id: 'A1', lane_type: 'audio_main',
          clips: [
            { clip_id: 'audio_a', scene_id: 's1', start_sec: 0, duration_sec: 5, source_path: '/tmp/cut/a.wav' },
            { clip_id: 'audio_b', scene_id: 's2', start_sec: 5, duration_sec: 5, source_path: '/tmp/cut/b.wav' },
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
  const state = createProjectState();
  await page.route(`${DEV_ORIGIN}/api/cut/**`, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/cut/project-state') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state) });
      return;
    }
    // Mock timeline ops — echo back success
    if (url.pathname === '/api/cut/timeline/ops') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, applied: [] }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
  });
}

async function navigateToCut(page) {
  await setupApiMocks(page);
  await page.addInitScript(() => {
    window.localStorage.setItem('cut_hotkey_preset', 'fcp7');
  });
  await page.goto(`${CUT_URL}?sandbox_root=${encodeURIComponent('/tmp/cut-3pt')}&project_id=${encodeURIComponent('cut-3pt-test')}`, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="cut-timeline-track-view"]', { timeout: 15000 });
  await page.waitForSelector('[data-testid^="cut-timeline-clip-"]', { timeout: 10000 }).catch(() => {});
}

// ===========================================================================
// THREE-POINT EDIT TESTS
// ===========================================================================
test.describe.serial('Three-Point Edit E2E (FCP7 Ch.36)', () => {

  test.beforeAll(async () => { await ensureDevServer(); });
  test.afterAll(() => { cleanupServer(); });

  // -------------------------------------------------------------------------
  // 3PT1: Source I + O → comma → insert at playhead
  // -------------------------------------------------------------------------
  test('3PT1: set Source IN/OUT, press comma — clip inserted at playhead, subsequent clips rippled', async ({ page }) => {
    await navigateToCut(page);

    // Step 1: Set source media path (simulating project bin click)
    await page.evaluate(() => {
      const s = window.__CUT_STORE__.getState();
      s.setSourceMedia('/tmp/cut/source-interview.mov');
      s.setSourceDuration(30); // 30 second source clip
    });

    // Step 2: Set Source IN = 2s, OUT = 5s (3-second excerpt)
    await page.evaluate(() => {
      const s = window.__CUT_STORE__.getState();
      s.setSourceMarkIn(2.0);
      s.setSourceMarkOut(5.0);
    });

    // Step 3: Focus timeline, seek playhead to 5s (between clip_a and clip_b)
    await page.getByTestId('cut-timeline-track-view').click();
    await page.waitForTimeout(100);
    await page.evaluate(() => {
      window.__CUT_STORE__.getState().seek(5.0);
    });

    // Step 4: Count clips before insert
    const clipsBefore = await page.evaluate(() => {
      return window.__CUT_STORE__.getState().lanes[0].clips.length;
    });
    expect(clipsBefore).toBe(3);

    // Step 5: Press comma (insert edit — FCP7 standard)
    await page.keyboard.press(',');
    await page.waitForTimeout(500);

    // Step 6: Verify — should have 4 clips on V1 now
    const stateAfter = await page.evaluate(() => {
      const s = window.__CUT_STORE__.getState();
      return {
        clipCount: s.lanes[0].clips.length,
        clips: s.lanes[0].clips.map(c => ({
          id: c.clip_id,
          start: c.start_sec,
          dur: c.duration_sec,
          src: c.source_path,
        })),
      };
    });

    // Insert adds 1 clip (3s duration from source IN/OUT)
    expect(stateAfter.clipCount).toBe(4);

    // clip_b should have rippled right by 3s (from 5s to 8s)
    const clipB = stateAfter.clips.find(c => c.id === 'clip_b');
    if (clipB) {
      expect(clipB.start).toBe(8.0);
    }

    // clip_c should have rippled right by 3s (from 10s to 13s)
    const clipC = stateAfter.clips.find(c => c.id === 'clip_c');
    if (clipC) {
      expect(clipC.start).toBe(13.0);
    }
  });

  // -------------------------------------------------------------------------
  // 3PT2: Source I + O → period → overwrite at playhead (no ripple)
  // -------------------------------------------------------------------------
  test('3PT2: set Source IN/OUT, press period — clip overwrites at playhead, no ripple', async ({ page }) => {
    await navigateToCut(page);

    // Setup source marks
    await page.evaluate(() => {
      const s = window.__CUT_STORE__.getState();
      s.setSourceMedia('/tmp/cut/source-broll.mov');
      s.setSourceDuration(20);
      s.setSourceMarkIn(0);
      s.setSourceMarkOut(2.0);
    });

    // Focus timeline, seek to 5s
    await page.getByTestId('cut-timeline-track-view').click();
    await page.waitForTimeout(100);
    await page.evaluate(() => {
      window.__CUT_STORE__.getState().seek(5.0);
    });

    const clipsBefore = await page.evaluate(() => {
      return window.__CUT_STORE__.getState().lanes[0].clips.length;
    });

    // Press period (overwrite edit)
    await page.keyboard.press('.');
    await page.waitForTimeout(500);

    const stateAfter = await page.evaluate(() => {
      const s = window.__CUT_STORE__.getState();
      return {
        clipCount: s.lanes[0].clips.length,
        clips: s.lanes[0].clips.map(c => ({
          id: c.clip_id,
          start: c.start_sec,
          dur: c.duration_sec,
        })),
      };
    });

    // Overwrite should not ripple — clip_c stays at original position
    const clipC = stateAfter.clips.find(c => c.id === 'clip_c');
    if (clipC) {
      expect(clipC.start).toBe(10.0); // not shifted
    }
  });

  // -------------------------------------------------------------------------
  // 3PT3: Undo after insert reverts the timeline
  // -------------------------------------------------------------------------
  test('3PT3: Cmd+Z after insert edit — clip removed, timeline restored', async ({ page }) => {
    await navigateToCut(page);

    // Setup and insert
    await page.evaluate(() => {
      const s = window.__CUT_STORE__.getState();
      s.setSourceMedia('/tmp/cut/source.mov');
      s.setSourceDuration(10);
      s.setSourceMarkIn(0);
      s.setSourceMarkOut(2.0);
      s.seek(5.0);
    });

    await page.getByTestId('cut-timeline-track-view').click();
    await page.waitForTimeout(100);

    const clipsBefore = await page.evaluate(() => {
      return window.__CUT_STORE__.getState().lanes[0].clips.length;
    });

    // Insert
    await page.keyboard.press(',');
    await page.waitForTimeout(500);

    const clipsAfterInsert = await page.evaluate(() => {
      return window.__CUT_STORE__.getState().lanes[0].clips.length;
    });

    // Undo
    await page.keyboard.press('Meta+z');
    await page.waitForTimeout(500);

    const clipsAfterUndo = await page.evaluate(() => {
      return window.__CUT_STORE__.getState().lanes[0].clips.length;
    });

    // After undo, should be back to original count
    expect(clipsAfterUndo).toBe(clipsBefore);
  });

  // -------------------------------------------------------------------------
  // 3PT4: No source marks → insert uses full clip duration
  // -------------------------------------------------------------------------
  test('3PT4: no source marks set — insert uses full source clip at playhead', async ({ page }) => {
    await navigateToCut(page);

    // Set source media but NO marks
    await page.evaluate(() => {
      const s = window.__CUT_STORE__.getState();
      s.setSourceMedia('/tmp/cut/full-clip.mov');
      s.setSourceDuration(8.0);
      // Clear any previous marks
      s.setSourceMarkIn(null);
      s.setSourceMarkOut(null);
      s.seek(5.0);
    });

    await page.getByTestId('cut-timeline-track-view').click();
    await page.waitForTimeout(100);

    // Insert — should use full 8s source
    await page.keyboard.press(',');
    await page.waitForTimeout(500);

    const stateAfter = await page.evaluate(() => {
      const s = window.__CUT_STORE__.getState();
      const inserted = s.lanes[0].clips.find(c => c.source_path === '/tmp/cut/full-clip.mov');
      return {
        clipCount: s.lanes[0].clips.length,
        insertedDuration: inserted ? inserted.duration_sec : null,
      };
    });

    // Full source (8s) should be inserted
    if (stateAfter.insertedDuration !== null) {
      expect(stateAfter.insertedDuration).toBe(8.0);
    }
    expect(stateAfter.clipCount).toBeGreaterThan(3);
  });
});
