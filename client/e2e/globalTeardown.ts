/**
 * MARKER_QA.GLOBAL_TEARDOWN: Kills the shared Vite dev server started by globalSetup.
 *
 * Only kills the server if this process started it (VETKA_VITE_PID is set).
 * If globalSetup reused an existing server, teardown is a no-op.
 */
async function globalTeardown(): Promise<void> {
  const pid = process.env.VETKA_VITE_PID;
  if (pid) {
    console.log(`[globalTeardown] Stopping shared Vite server (pid=${pid})...`);
    try {
      process.kill(Number(pid), 'SIGTERM');
    } catch {
      // Process already exited — nothing to do
    }
  } else {
    console.log('[globalTeardown] No owned Vite process to stop (reused external server).');
  }
}

export default globalTeardown;
