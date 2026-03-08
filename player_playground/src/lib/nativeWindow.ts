export async function isTauriRuntime() {
  try {
    return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
  } catch {
    return false;
  }
}

export async function setCurrentWindowLogicalSize(width: number, height: number): Promise<boolean> {
  if (!(await isTauriRuntime())) return false;
  try {
    const [{ getCurrentWindow }, { LogicalSize }] = await Promise.all([
      import("@tauri-apps/api/window"),
      import("@tauri-apps/api/dpi"),
    ]);
    const win = getCurrentWindow();
    await win.setSize(new LogicalSize(Math.max(240, Math.round(width)), Math.max(220, Math.round(height))));
    return true;
  } catch (error) {
    console.warn("[VETKA Player Lab] setCurrentWindowLogicalSize failed:", error);
    return false;
  }
}

export async function toggleFullscreen(): Promise<boolean | null> {
  if (await isTauriRuntime()) {
    try {
      const { getCurrentWindow } = await import("@tauri-apps/api/window");
      const win = getCurrentWindow();
      const current = await win.isFullscreen();
      await win.setFullscreen(!current);
      return !current;
    } catch (error) {
      console.warn("[VETKA Player Lab] native fullscreen failed:", error);
      return null;
    }
  }

  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
      return false;
    }
    await document.documentElement.requestFullscreen();
    return true;
  } catch (error) {
    console.warn("[VETKA Player Lab] DOM fullscreen failed:", error);
    return null;
  }
}
