export function isTauriRuntimeSync() {
  try {
    return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
  } catch {
    return false;
  }
}

export interface PlayerNativeWindowTrace {
  scale_factor: number;
  inner_physical_width: number;
  inner_physical_height: number;
  outer_physical_width: number;
  outer_physical_height: number;
  inner_logical_width: number;
  inner_logical_height: number;
  outer_logical_width: number;
  outer_logical_height: number;
}

export async function isTauriRuntime() {
  try {
    return isTauriRuntimeSync();
  } catch {
    return false;
  }
}

async function getInvoke() {
  if (!(await isTauriRuntime())) return null;
  const core = await import("@tauri-apps/api/core");
  return core.invoke;
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

export async function configurePlayerWindow(
  width: number,
  height: number,
  aspectWidth: number,
  aspectHeight: number,
): Promise<boolean> {
  const safeWidth = Math.max(240, Math.round(width));
  const safeHeight = Math.max(220, Math.round(height));
  if (!(await isTauriRuntime())) return false;

  try {
    const invoke = await getInvoke();
    if (invoke) {
      await invoke("configure_player_window", {
        width: safeWidth,
        height: safeHeight,
        aspectWidth: Math.max(1, Math.round(aspectWidth || 1)),
        aspectHeight: Math.max(1, Math.round(aspectHeight || 1)),
      });
      return true;
    }
  } catch (error) {
    console.warn("[VETKA Player Lab] configure_player_window failed:", error);
  }

  return setCurrentWindowLogicalSize(safeWidth, safeHeight);
}

export async function tracePlayerWindow(): Promise<PlayerNativeWindowTrace | null> {
  if (!(await isTauriRuntime())) return null;
  try {
    const invoke = await getInvoke();
    if (!invoke) return null;
    return await invoke<PlayerNativeWindowTrace>("trace_player_window");
  } catch (error) {
    console.warn("[VETKA Player Lab] trace_player_window failed:", error);
    return null;
  }
}

export async function toggleFullscreen(): Promise<boolean | null> {
  if (await isTauriRuntime()) {
    try {
      const invoke = await getInvoke();
      if (invoke) {
        return await invoke<boolean>("toggle_player_fullscreen");
      }
    } catch (error) {
      console.warn("[VETKA Player Lab] native fullscreen command failed:", error);
    }

    try {
      const { getCurrentWindow } = await import("@tauri-apps/api/window");
      const win = getCurrentWindow();
      const current = await win.isFullscreen();
      await win.setFullscreen(!current);
      return !current;
    } catch (error) {
      console.warn("[VETKA Player Lab] native fullscreen api failed:", error);
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
