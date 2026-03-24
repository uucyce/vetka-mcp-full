/**
 * MARKER_QA.GLOBAL_SETUP: Shared Vite dev server for all Playwright E2E specs.
 *
 * Starts ONE Vite server on VETKA_GLOBAL_PORT (default 3001) before any spec runs.
 * Individual specs that check VETKA_GLOBAL_PORT first will skip spawning their own
 * server, eliminating the ~6s startup overhead per spec.
 *
 * Usage:
 *   - playwright.config.ts references this as globalSetup
 *   - Specs can opt-in via: process.env.VETKA_GLOBAL_PORT
 *   - Existing specs with their own server logic are unaffected (additive)
 */
import { spawn, ChildProcess } from 'child_process';
import { resolve } from 'path';
import * as http from 'http';

let viteProcess: ChildProcess | null = null;

function waitForHttpOk(url: string, timeoutMs = 30000): Promise<void> {
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
        reject(new Error(`Timed out waiting for ${url}`));
        return;
      }
      setTimeout(tick, 200);
    };
    tick();
  });
}

async function globalSetup(): Promise<void> {
  const port = Number(process.env.VETKA_GLOBAL_PORT || 3001);
  const origin = `http://127.0.0.1:${port}`;
  const clientDir = resolve(__dirname, '..');

  // Check if a server is already running on this port
  try {
    await waitForHttpOk(origin, 1500);
    // Server already up — record port and return
    process.env.VETKA_GLOBAL_PORT = String(port);
    process.env.VETKA_GLOBAL_ORIGIN = origin;
    console.log(`[globalSetup] Reusing existing Vite server at ${origin}`);
    return;
  } catch {
    // Need to start our own
  }

  console.log(`[globalSetup] Starting shared Vite dev server on port ${port}...`);

  viteProcess = spawn(
    'npm',
    ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(port), '--strictPort'],
    {
      cwd: clientDir,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, BROWSER: 'none', CI: '1', NODE_ENV: 'test' },
    }
  );

  let serverLogs = '';
  const capture = (chunk: Buffer) => {
    serverLogs += chunk.toString();
    if (serverLogs.length > 20000) serverLogs = serverLogs.slice(-20000);
  };
  viteProcess.stdout?.on('data', capture);
  viteProcess.stderr?.on('data', capture);

  viteProcess.on('error', (err) => {
    console.error('[globalSetup] Vite spawn error:', err.message);
  });

  try {
    await waitForHttpOk(origin, 30000);
  } catch (err) {
    viteProcess.kill('SIGTERM');
    throw new Error(`[globalSetup] Vite server failed to start on ${origin}.\nLogs:\n${serverLogs}`);
  }

  // Store PID so globalTeardown can kill the process
  process.env.VETKA_GLOBAL_PORT = String(port);
  process.env.VETKA_GLOBAL_ORIGIN = origin;
  process.env.VETKA_VITE_PID = String(viteProcess.pid);

  console.log(`[globalSetup] Shared Vite server ready at ${origin} (pid=${viteProcess.pid})`);
}

export default globalSetup;
