#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use tauri::{LogicalSize, PhysicalSize, Size, WebviewWindow};

#[derive(Debug, Clone, Serialize)]
struct PlayerWindowTrace {
    scale_factor: f64,
    inner_physical_width: u32,
    inner_physical_height: u32,
    outer_physical_width: u32,
    outer_physical_height: u32,
    inner_logical_width: f64,
    inner_logical_height: f64,
    outer_logical_width: f64,
    outer_logical_height: f64,
}

fn trace_window(window: &WebviewWindow) -> Result<PlayerWindowTrace, String> {
    let scale_factor = window
        .scale_factor()
        .map_err(|e| format!("scale_factor failed: {e}"))?
        .max(1.0);
    let inner = window
        .inner_size()
        .map_err(|e| format!("inner_size failed: {e}"))?;
    let outer = window
        .outer_size()
        .map_err(|e| format!("outer_size failed: {e}"))?;

    Ok(PlayerWindowTrace {
        scale_factor,
        inner_physical_width: inner.width,
        inner_physical_height: inner.height,
        outer_physical_width: outer.width,
        outer_physical_height: outer.height,
        inner_logical_width: inner.width as f64 / scale_factor,
        inner_logical_height: inner.height as f64 / scale_factor,
        outer_logical_width: outer.width as f64 / scale_factor,
        outer_logical_height: outer.height as f64 / scale_factor,
    })
}

fn candidate_score(width: i32, height: i32, requested_width: i32, requested_height: i32) -> i32 {
    (width - requested_width).abs() + (height - requested_height).abs()
}

fn candidate_from_height(height: i32, ratio: f64) -> (i32, i32) {
    let width = ((height as f64) * ratio).round().max(1.0) as i32;
    (width, height)
}

fn candidate_from_width(width: i32, ratio: f64) -> (i32, i32) {
    let height = ((width as f64) / ratio).round().max(1.0) as i32;
    (width, height)
}

fn snap_logical_size_for_aspect(
    window: &WebviewWindow,
    width: f64,
    height: f64,
    aspect_width: f64,
    aspect_height: f64,
) -> Result<(f64, f64), String> {
    if !(aspect_width.is_finite() && aspect_height.is_finite()) || aspect_width <= 0.0 || aspect_height <= 0.0 {
        return Ok((width.max(240.0).round(), height.max(220.0).round()));
    }

    let scale_factor = window
        .scale_factor()
        .map_err(|e| format!("scale_factor failed: {e}"))?
        .max(1.0);
    let ratio = aspect_width / aspect_height;
    let requested_width = ((width.max(240.0)) * scale_factor).round().max(1.0) as i32;
    let requested_height = ((height.max(220.0)) * scale_factor).round().max(1.0) as i32;

    let height_candidates = [
        requested_height - 1,
        requested_height,
        requested_height + 1,
    ]
    .into_iter()
    .filter(|value| *value > 0)
    .map(|value| candidate_from_height(value, ratio));

    let width_candidates = [
        requested_width - 1,
        requested_width,
        requested_width + 1,
    ]
    .into_iter()
    .filter(|value| *value > 0)
    .map(|value| candidate_from_width(value, ratio));

    let mut best = (requested_width, requested_height);
    let mut best_score = candidate_score(best.0, best.1, requested_width, requested_height);

    for candidate in height_candidates.chain(width_candidates) {
        let score = candidate_score(candidate.0, candidate.1, requested_width, requested_height);
        if score < best_score {
            best = candidate;
            best_score = score;
        }
    }

    Ok((
        (best.0 as f64 / scale_factor).max(240.0),
        (best.1 as f64 / scale_factor).max(220.0),
    ))
}

fn set_window_logical_size(window: &WebviewWindow, width: f64, height: f64) -> Result<(), String> {
    window
        .set_size(Size::Logical(LogicalSize::new(width, height)))
        .map_err(|e| format!("set_size failed: {e}"))
}

fn snap_trace_to_aspect(
    trace: &PlayerWindowTrace,
    aspect_width: f64,
    aspect_height: f64,
) -> Option<PhysicalSize<u32>> {
    if !(aspect_width.is_finite() && aspect_height.is_finite()) || aspect_width <= 0.0 || aspect_height <= 0.0 {
        return None;
    }
    let ratio = aspect_width / aspect_height;
    let current_width = trace.inner_physical_width as i32;
    let current_height = trace.inner_physical_height as i32;
    if current_width <= 0 || current_height <= 0 {
        return None;
    }

    let from_height = candidate_from_height(current_height, ratio);
    let from_width = candidate_from_width(current_width, ratio);
    let current_score = candidate_score(current_width, current_height, current_width, current_height);
    let height_score = candidate_score(from_height.0, from_height.1, current_width, current_height);
    let width_score = candidate_score(from_width.0, from_width.1, current_width, current_height);

    let best = if height_score <= width_score {
        from_height
    } else {
        from_width
    };

    if height_score.min(width_score) >= current_score {
        return None;
    }

    let best_width = best.0.max(1) as u32;
    let best_height = best.1.max(1) as u32;
    if best_width == trace.inner_physical_width && best_height == trace.inner_physical_height {
        return None;
    }

    Some(PhysicalSize::new(best_width, best_height))
}

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
    let (width, height) =
        snap_logical_size_for_aspect(&window, width, height, aspect_width, aspect_height)?;
    set_window_logical_size(&window, width, height)?;

    set_content_aspect_ratio(&window, aspect_width, aspect_height)?;

    let trace = trace_window(&window)?;
    if let Some(snapped_physical) = snap_trace_to_aspect(&trace, aspect_width, aspect_height) {
        let corrected_width = snapped_physical.width as f64 / trace.scale_factor;
        let corrected_height = snapped_physical.height as f64 / trace.scale_factor;
        set_window_logical_size(&window, corrected_width, corrected_height)?;
    }
    Ok(true)
}

#[tauri::command]
fn toggle_player_fullscreen(window: WebviewWindow) -> Result<bool, String> {
    toggle_fullscreen_native(&window)
}

#[tauri::command]
fn trace_player_window(window: WebviewWindow) -> Result<PlayerWindowTrace, String> {
    trace_window(&window)
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            configure_player_window,
            toggle_player_fullscreen,
            trace_player_window
        ])
        .run(tauri::generate_context!())
        .expect("error while running VETKA Player Lab");
}
