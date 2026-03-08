const { test, expect } = require('playwright/test');
const fs = require('fs');
const http = require('http');
const os = require('os');
const path = require('path');
const { execFileSync, spawn, spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const CLIENT_DIR = path.join(ROOT, 'client');
const DEV_PORT = Number(process.env.VETKA_MEDIA_DEBUG_PORT || 4173);
const DEV_ORIGIN = `http://127.0.0.1:${DEV_PORT}`;
const HAS_FFMPEG = hasCommand('ffmpeg');

let serverProcess = null;
let serverStartedBySpec = false;
let serverLogs = '';
let tempDir = null;
let clipPath = '';
let clipBuffer = null;

function hasCommand(command) {
  const probe = spawnSync(command, ['-version'], { stdio: 'ignore' });
  return probe.status === 0;
}

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

function ensureProbeClip() {
  tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vetka-media-aspect-'));
  clipPath = path.join(tempDir, 'probe-4x3.mp4');
  execFileSync('ffmpeg', [
    '-hide_banner',
    '-loglevel',
    'error',
    '-f',
    'lavfi',
    '-i',
    'testsrc=size=640x480:rate=24',
    '-t',
    '2',
    '-pix_fmt',
    'yuv420p',
    '-movflags',
    '+faststart',
    '-c:v',
    'libx264',
    '-y',
    clipPath,
  ]);
  clipBuffer = fs.readFileSync(clipPath);
}

async function ensureDevServer() {
  try {
    await waitForHttpOk(DEV_ORIGIN, 1500);
    return;
  } catch {
    // start local server below
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

function cleanupArtifacts() {
  if (serverProcess && serverStartedBySpec) {
    serverProcess.kill('SIGTERM');
    serverProcess = null;
  }
  if (tempDir) {
    fs.rmSync(tempDir, { recursive: true, force: true });
    tempDir = null;
  }
}

function fulfillVideo(route) {
  const request = route.request();
  const range = request.headers().range;
  if (range) {
    const match = /bytes=(\d*)-(\d*)/.exec(range);
    if (match) {
      const start = match[1] ? Number(match[1]) : 0;
      const end = match[2] ? Number(match[2]) : (clipBuffer.length - 1);
      const safeEnd = Math.min(end, clipBuffer.length - 1);
      const body = clipBuffer.subarray(start, safeEnd + 1);
      return route.fulfill({
        status: 206,
        headers: {
          'content-type': 'video/mp4',
          'accept-ranges': 'bytes',
          'content-length': String(body.length),
          'content-range': `bytes ${start}-${safeEnd}/${clipBuffer.length}`,
        },
        body,
      });
    }
  }

  return route.fulfill({
    status: 200,
    headers: {
      'content-type': 'video/mp4',
      'accept-ranges': 'bytes',
      'content-length': String(clipBuffer.length),
    },
    body: clipBuffer,
  });
}

async function installApiMocks(page) {
  await page.route(`${DEV_ORIGIN}/api/**`, async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/files/read') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          path: clipPath,
          content: '',
          mimeType: 'video/mp4',
          encoding: 'binary',
          size: clipBuffer.length,
        }),
      });
      return;
    }
    if (url.pathname === '/api/files/raw') {
      await fulfillVideo(route);
      return;
    }
    if (url.pathname === '/api/artifacts/media/preview') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: false }),
      });
      return;
    }
    if (url.pathname === '/api/tree/favorites') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ favorites: {} }),
      });
      return;
    }
    if (url.pathname === '/api/artifacts') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ artifacts: [] }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: '{}',
    });
  });
}

test.describe.serial('phase159 detached media aspect ratio probe', () => {
  test.skip(!HAS_FFMPEG, 'ffmpeg is required for media aspect ratio probe');

  test.beforeAll(async () => {
    ensureProbeClip();
    await ensureDevServer();
  });

  test.afterAll(async () => {
    cleanupArtifacts();
  });

  test('4:3 detached video converges without side letterboxing after fit', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 960, height: 540 });
    await page.exposeFunction('vetkaSetViewportSize', async ({ width, height }) => {
      await page.setViewportSize({
        width: Math.max(240, Math.round(Number(width) || 0)),
        height: Math.max(224, Math.round(Number(height) || 0)),
      });
      return true;
    });
    await page.addInitScript(() => {
      let fakeFullscreen = false;
      window.__vetkaResizeLog = [];
      window.__VETKA_TAURI_TEST__ = {
        isTauri: true,
        async getCurrentWindowFullscreen() {
          return fakeFullscreen;
        },
        async setCurrentWindowFullscreen(fullscreen) {
          fakeFullscreen = Boolean(fullscreen);
          return fakeFullscreen;
        },
        async setWindowFullscreen(fullscreen) {
          fakeFullscreen = Boolean(fullscreen);
          return true;
        },
        async setCurrentWindowLogicalSize(width, height) {
          window.__vetkaResizeLog.push({
            width: Math.round(Number(width) || 0),
            height: Math.round(Number(height) || 0),
            at: Date.now(),
          });
          await window.vetkaSetViewportSize({ width, height });
          return true;
        },
      };
    });

    await installApiMocks(page);

    await page.goto(
      `${DEV_ORIGIN}/artifact-media?path=${encodeURIComponent(clipPath)}&name=probe-4x3.mp4&extension=mp4`,
      { waitUntil: 'domcontentloaded' }
    );

    await page.waitForFunction(() => {
      const video = document.querySelector('video');
      return Boolean(video && video.videoWidth > 0 && video.videoHeight > 0);
    }, undefined, { timeout: 15000 });

    await page.waitForFunction(() => {
      const log = window.__vetkaResizeLog || [];
      if (!log.length) return false;
      return Date.now() - log[log.length - 1].at > 250;
    }, undefined, { timeout: 12000 });

    const metrics = await page.evaluate(() => {
      const video = document.querySelector('video');
      const wrapper = video?.parentElement;
      const toolbar = document.querySelector('[data-artifact-toolbar="1"]');
      if (!video || !wrapper) return null;

      const wrapperRect = wrapper.getBoundingClientRect();
      const naturalWidth = Math.max(1, video.videoWidth);
      const naturalHeight = Math.max(1, video.videoHeight);
      const scale = Math.min(wrapperRect.width / naturalWidth, wrapperRect.height / naturalHeight);
      const displayedWidth = naturalWidth * scale;
      const displayedHeight = naturalHeight * scale;
      const renderedRatio = displayedWidth / Math.max(1, displayedHeight);
      const naturalRatio = naturalWidth / naturalHeight;

      return {
        naturalWidth,
        naturalHeight,
        wrapperWidth: wrapperRect.width,
        wrapperHeight: wrapperRect.height,
        displayedWidth,
        displayedHeight,
        horizontalLetterboxPx: Math.max(0, (wrapperRect.width - displayedWidth) / 2),
        verticalLetterboxPx: Math.max(0, (wrapperRect.height - displayedHeight) / 2),
        aspectError: Math.abs(renderedRatio - naturalRatio),
        innerWidth: window.innerWidth,
        innerHeight: window.innerHeight,
        toolbarHeight: toolbar ? toolbar.getBoundingClientRect().height : 0,
        resizeRequests: window.__vetkaResizeLog || [],
      };
    });

    await page.screenshot({
      path: testInfo.outputPath('detached-media-aspect-ratio.png'),
      fullPage: true,
    });
    await testInfo.attach('detached-media-aspect-ratio-metrics', {
      body: Buffer.from(JSON.stringify(metrics, null, 2)),
      contentType: 'application/json',
    });
    console.log('[phase159.aspect-probe]', JSON.stringify(metrics));

    expect(metrics).not.toBeNull();
    expect(metrics.resizeRequests.length).toBeGreaterThan(0);
    expect(metrics.innerWidth).toBeLessThan(760);
    expect(metrics.horizontalLetterboxPx).toBeLessThanOrEqual(4);
    expect(metrics.verticalLetterboxPx).toBeLessThanOrEqual(4);
    expect(metrics.aspectError).toBeLessThan(0.02);
    expect(Math.abs(metrics.displayedHeight - metrics.wrapperHeight)).toBeLessThanOrEqual(4);
  });
});
