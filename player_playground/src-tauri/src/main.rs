#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{LogicalSize, Size, WebviewWindow};

#[cfg(target_os = "macos")]
fn set_content_aspect_ratio(
    window: &WebviewWindow,
    aspect_width: f64,
    aspect_height: f64,
) -> Result<(), String> {
    use objc2::runtime::AnyObject;
    use objc2_app_kit::NSWindow;
    use objc2_foundation::NSSize;

    if !(aspect_width.is_finite() && aspect_height.is_finite()) {
        return Ok(());
    }
    if aspect_width <= 0.0 || aspect_height <= 0.0 {
        return Ok(());
    }

    let ns_window = window
        .ns_window()
        .map_err(|e| format!("ns_window failed: {e}"))? as usize;

    let aspect_width = aspect_width.max(1.0);
    let aspect_height = aspect_height.max(1.0);

    window
        .run_on_main_thread(move || unsafe {
            let ns_window: &NSWindow = &*((ns_window as *mut AnyObject).cast::<NSWindow>());
            let aspect = NSSize::new(aspect_width, aspect_height);
            ns_window.setContentAspectRatio(aspect);
        })
        .map_err(|e| format!("run_on_main_thread failed: {e}"))
}

#[cfg(not(target_os = "macos"))]
fn set_content_aspect_ratio(
    _window: &WebviewWindow,
    _aspect_width: f64,
    _aspect_height: f64,
) -> Result<(), String> {
    Ok(())
}

#[cfg(target_os = "macos")]
fn toggle_fullscreen_native(window: &WebviewWindow) -> Result<bool, String> {
    use objc2::runtime::AnyObject;
    use objc2_app_kit::NSWindow;

    let current = window
        .is_fullscreen()
        .map_err(|e| format!("is_fullscreen failed: {e}"))?;
    let ns_window = window
        .ns_window()
        .map_err(|e| format!("ns_window failed: {e}"))? as usize;

    window
        .run_on_main_thread(move || unsafe {
            let ns_window: &NSWindow = &*((ns_window as *mut AnyObject).cast::<NSWindow>());
            ns_window.toggleFullScreen(None);
        })
        .map_err(|e| format!("run_on_main_thread failed: {e}"))?;

    Ok(!current)
}

#[cfg(not(target_os = "macos"))]
fn toggle_fullscreen_native(window: &WebviewWindow) -> Result<bool, String> {
    let current = window
        .is_fullscreen()
        .map_err(|e| format!("is_fullscreen failed: {e}"))?;
    let next = !current;
    window
        .set_fullscreen(next)
        .map_err(|e| format!("set_fullscreen failed: {e}"))?;
    Ok(next)
}

#[tauri::command]
fn configure_player_window(
    window: WebviewWindow,
    width: f64,
    height: f64,
    aspect_width: f64,
    aspect_height: f64,
) -> Result<bool, String> {
    let width = width.max(240.0).round();
    let height = height.max(220.0).round();

    window
        .set_size(Size::Logical(LogicalSize::new(width, height)))
        .map_err(|e| format!("set_size failed: {e}"))?;

    set_content_aspect_ratio(&window, aspect_width, aspect_height)?;
    Ok(true)
}

#[tauri::command]
fn toggle_player_fullscreen(window: WebviewWindow) -> Result<bool, String> {
    toggle_fullscreen_native(&window)
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            configure_player_window,
            toggle_player_fullscreen
        ])
        .run(tauri::generate_context!())
        .expect("error while running VETKA Player Lab");
}
