// VETKA Tauri Commands - IPC Bridge
// Phase 100.1: Basic commands

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, LogicalSize, Manager, Size, WebviewUrl, WebviewWindow, WebviewWindowBuilder};
use tauri_plugin_dialog::DialogExt;
use url::Url;
use std::sync::{Mutex, OnceLock};

#[derive(Debug, Serialize, Deserialize)]
pub struct BackendConfig {
    pub api_url: String,
    pub socket_url: String,
    pub is_local: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SystemInfo {
    pub os: String,
    pub arch: String,
    pub tauri_version: String,
    pub app_version: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HealthStatus {
    pub backend_alive: bool,
    pub qdrant_alive: bool,
    pub latency_ms: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DetachedMediaGeometryTrace {
    pub src: String,
    pub dpr: f64,
    pub window_inner_width: f64,
    pub window_inner_height: f64,
    pub video_intrinsic_width: f64,
    pub video_intrinsic_height: f64,
    pub wrapper_width: f64,
    pub wrapper_height: f64,
    pub toolbar_width: f64,
    pub toolbar_height: f64,
}

#[derive(Debug, Serialize)]
struct MediaWindowMetadataRequest {
    path: String,
}

#[derive(Debug, Deserialize)]
struct MediaWindowMetadataResponse {
    success: bool,
    modality: Option<String>,
    width_px: Option<u32>,
    height_px: Option<u32>,
}

fn backend_api_url() -> String {
    std::env::var("VETKA_API_URL")
        .unwrap_or_else(|_| "http://localhost:5001".to_string())
}

async fn fetch_media_window_metadata(path: &str) -> Option<MediaWindowMetadataResponse> {
    let client = reqwest::Client::new();
    let response = client
        .post(format!("{}/api/artifacts/media/window-metadata", backend_api_url()))
        .timeout(std::time::Duration::from_secs(4))
        .json(&MediaWindowMetadataRequest {
            path: path.to_string(),
        })
        .send()
        .await
        .ok()?;

    if !response.status().is_success() {
        return None;
    }

    let payload = response.json::<MediaWindowMetadataResponse>().await.ok()?;
    if !payload.success {
        return None;
    }
    Some(payload)
}

fn preferred_monitor_size(app: &AppHandle) -> (f64, f64) {
    // MARKER_159.R12.MONITOR_LOGICAL_SIZE:
    // Tauri window inner/set_size APIs use logical units. Convert monitor physical pixels
    // to logical pixels via scale_factor before computing window bounds on Retina macOS.
    let to_logical = |size: tauri::PhysicalSize<u32>, scale: f64| -> (f64, f64) {
        let factor = if scale.is_finite() && scale > 0.0 { scale } else { 1.0 };
        (
            (size.width as f64 / factor).floor(),
            (size.height as f64 / factor).floor(),
        )
    };

    if let Some(main) = app.get_webview_window("main") {
        if let Ok(Some(monitor)) = main.current_monitor() {
            let size = monitor.size();
            return to_logical(*size, monitor.scale_factor());
        }
    }
    if let Ok(Some(monitor)) = app.primary_monitor() {
        let size = monitor.size();
        return to_logical(*size, monitor.scale_factor());
    }
    (1440.0, 900.0)
}

fn compute_detached_media_initial_inner_size(
    video_width: u32,
    video_height: u32,
    screen_width: f64,
    screen_height: f64,
) -> (f64, f64) {
    // MARKER_159.R9.ONE_SHOT_MEDIA_INITIAL_SIZE:
    // compute detached media window size once, before creation, from real media metadata.
    const DEFAULT_WINDOW_W: f64 = 960.0;
    const DEFAULT_WINDOW_H: f64 = 540.0;
    const MIN_WINDOW_W: f64 = 360.0;
    const MIN_WINDOW_H: f64 = 240.0;
    // MARKER_159.R12.DETACHED_MEDIA_TOOLBAR_OUTER:
    // compact detached media toolbar uses 36 content px + 12 vertical padding + 1 border.
    const TOOLBAR_H: f64 = 49.0;

    if video_width == 0 || video_height == 0 {
        return (DEFAULT_WINDOW_W, DEFAULT_WINDOW_H);
    }

    let max_window_w = (screen_width * 0.92).floor().max(MIN_WINDOW_W);
    let max_window_h = (screen_height * 0.9).floor().max(MIN_WINDOW_H);
    let ratio = (video_width as f64) / (video_height as f64);

    let mut window_h = DEFAULT_WINDOW_H.min(max_window_h).max(MIN_WINDOW_H);
    let mut viewer_h = (window_h - TOOLBAR_H).max(180.0);
    let mut window_w = (viewer_h * ratio).round().max(MIN_WINDOW_W);

    if window_w > max_window_w {
        window_w = max_window_w;
        viewer_h = (window_w / ratio).round();
        window_h = (viewer_h + TOOLBAR_H).round();
    }

    if window_h > max_window_h {
        window_h = max_window_h;
        viewer_h = (window_h - TOOLBAR_H).max(180.0);
        window_w = (viewer_h * ratio).round();
    }

    window_w = window_w.clamp(MIN_WINDOW_W, max_window_w);
    window_h = window_h.clamp(MIN_WINDOW_H, max_window_h);
    (window_w, window_h)
}

fn apply_detached_media_inner_size(
    window: &WebviewWindow,
    width: f64,
    height: f64,
) -> Result<(), String> {
    // MARKER_159.R10.ONE_SHOT_REUSE_PIXEL_SIZE:
    // apply the precomputed pixel size both on first create and when reusing
    // the singleton detached media window so stale wide bounds do not survive.
    window
        .set_size(Size::Logical(LogicalSize::new(width, height)))
        .map_err(|e| format!("set_size failed: {e}"))
}

/// Get backend URL configuration
/// Called by frontend to know where to connect
#[tauri::command]
pub fn get_backend_url() -> BackendConfig {
    // In production, this could read from config file or environment
    let api_url = std::env::var("VETKA_API_URL")
        .unwrap_or_else(|_| "http://localhost:5001".to_string());

    let socket_url = std::env::var("VETKA_SOCKET_URL")
        .unwrap_or_else(|_| "ws://localhost:5001".to_string());

    BackendConfig {
        api_url: api_url.clone(),
        socket_url,
        is_local: api_url.contains("localhost"),
    }
}

/// Check if FastAPI backend is healthy
#[tauri::command]
pub async fn check_backend_health() -> Result<HealthStatus, String> {
    let start = std::time::Instant::now();

    let api_url = std::env::var("VETKA_API_URL")
        .unwrap_or_else(|_| "http://localhost:5001".to_string());

    // Simple health check - just verify backend responds
    let client = reqwest::Client::new();
    let backend_alive = client
        .get(format!("{}/api/health", api_url))
        .timeout(std::time::Duration::from_secs(5))
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false);

    let latency = start.elapsed().as_millis() as u64;

    Ok(HealthStatus {
        backend_alive,
        qdrant_alive: backend_alive, // Assume if backend is up, qdrant is too
        latency_ms: latency,
    })
}

/// Get system information for debugging
#[tauri::command]
pub fn get_system_info() -> SystemInfo {
    SystemInfo {
        os: std::env::consts::OS.to_string(),
        arch: std::env::consts::ARCH.to_string(),
        tauri_version: "2.0".to_string(),
        app_version: env!("CARGO_PKG_VERSION").to_string(),
    }
}

/// MARKER_159.R14.DETACHED_MEDIA_TRACE_CMD:
/// Emit detached media geometry from the frontend into the native terminal logs.
#[tauri::command]
pub fn trace_detached_media_geometry(trace: DetachedMediaGeometryTrace) -> Result<bool, String> {
    log::info!(
        "MARKER_159.R14.DETACHED_MEDIA_TRACE src={} dpr={} window_inner={}x{} video_intrinsic={}x{} wrapper={}x{} toolbar={}x{}",
        trace.src,
        trace.dpr,
        trace.window_inner_width,
        trace.window_inner_height,
        trace.video_intrinsic_width,
        trace.video_intrinsic_height,
        trace.wrapper_width,
        trace.wrapper_height,
        trace.toolbar_width,
        trace.toolbar_height,
    );
    Ok(true)
}

/// MARKER_161.7.MULTIPROJECT.TAURI.NATIVE_FOLDER_PICKER.V1
/// Fallback native folder picker for MCC onboarding when JS plugin dialog bridge is unavailable.
#[tauri::command]
pub async fn pick_folder_native(app: AppHandle, title: Option<String>) -> Result<Option<String>, String> {
    let mut builder = app.dialog().file();
    if let Some(t) = title.as_deref().map(str::trim).filter(|v| !v.is_empty()) {
        builder = builder.set_title(t);
    }
    let selected = builder
        .blocking_pick_folder()
        .and_then(|p| p.into_path().ok())
        .map(|p| p.to_string_lossy().to_string());
    Ok(selected)
}

/// MARKER_159.WINFS.R1_CMD: Native window-level fullscreen toggle.
#[tauri::command]
pub fn set_window_fullscreen(
    app: AppHandle,
    window_label: Option<String>,
    fullscreen: bool,
) -> Result<bool, String> {
    let label = window_label
        .as_deref()
        .map(str::trim)
        .filter(|v| !v.is_empty())
        .unwrap_or("main")
        .to_string();

    let window = app
        .get_webview_window(&label)
        .ok_or_else(|| format!("Window not found: {label}"))?;

    window
        .set_fullscreen(fullscreen)
        .map_err(|e| format!("set_fullscreen failed: {e}"))?;

    if fullscreen {
        let _ = window.set_focus();
    }
    Ok(true)
}

/// MARKER_159.C2.WINFS.STATE_CMD: Read current native fullscreen state by window label.
#[tauri::command]
pub fn get_window_fullscreen(
    app: AppHandle,
    window_label: Option<String>,
) -> Result<bool, String> {
    let label = window_label
        .as_deref()
        .map(str::trim)
        .filter(|v| !v.is_empty())
        .unwrap_or("main")
        .to_string();

    let window = app
        .get_webview_window(&label)
        .ok_or_else(|| format!("Window not found: {label}"))?;

    window
        .is_fullscreen()
        .map_err(|e| format!("is_fullscreen failed: {e}"))
}

/// MARKER_159.C2.WINFS.TOGGLE_CURRENT: Toggle fullscreen for the current (calling) window.
#[tauri::command]
pub fn toggle_current_window_fullscreen(window: WebviewWindow) -> Result<bool, String> {
    let current = window
        .is_fullscreen()
        .map_err(|e| format!("is_fullscreen failed: {e}"))?;
    let next = !current;

    window
        .set_fullscreen(next)
        .map_err(|e| format!("set_fullscreen failed: {e}"))?;

    if next {
        let _ = window.set_focus();
    }
    Ok(next)
}

/// MARKER_159.C2.WINFS.GET_CURRENT: Read fullscreen state for current (calling) window.
#[tauri::command]
pub fn get_current_window_fullscreen(window: WebviewWindow) -> Result<bool, String> {
    window
        .is_fullscreen()
        .map_err(|e| format!("is_fullscreen failed: {e}"))
}

/// MARKER_159.C2.WINFS.SET_CURRENT: Set fullscreen state for current (calling) window.
#[tauri::command]
pub fn set_current_window_fullscreen(window: WebviewWindow, fullscreen: bool) -> Result<bool, String> {
    window
        .set_fullscreen(fullscreen)
        .map_err(|e| format!("set_fullscreen failed: {e}"))?;
    if fullscreen {
        let _ = window.set_focus();
    }
    window
        .is_fullscreen()
        .map_err(|e| format!("is_fullscreen verify failed: {e}"))
}

/// MARKER_159.WINFS.R2_CMD: Open/reuse detached artifact media window.
#[tauri::command]
pub async fn open_artifact_media_window(
    app: AppHandle,
    path: String,
    name: Option<String>,
    extension: Option<String>,
    artifact_id: Option<String>,
    in_vetka: Option<bool>,
    initial_seek_sec: Option<f64>,
    video_width: Option<u32>,
    video_height: Option<u32>,
    aspect_ratio: Option<String>,
) -> Result<bool, String> {
    let clean_path = path.trim();
    if clean_path.is_empty() {
        return Err("path is required".to_string());
    }

    let label = "artifact-media".to_string();
    let window_title = name
        .as_deref()
        .map(str::trim)
        .filter(|v| !v.is_empty())
        .unwrap_or("Artifact Media")
        .to_string();

    let mut route = format!("/artifact-media?path={}", urlencoding::encode(clean_path));
    if let Some(v) = name.as_deref().map(str::trim).filter(|v| !v.is_empty()) {
        route.push_str("&name=");
        route.push_str(&urlencoding::encode(v));
    }
    if let Some(v) = extension.as_deref().map(str::trim).filter(|v| !v.is_empty()) {
        route.push_str("&extension=");
        route.push_str(&urlencoding::encode(v));
    }
    if let Some(v) = artifact_id.as_deref().map(str::trim).filter(|v| !v.is_empty()) {
        route.push_str("&artifact_id=");
        route.push_str(&urlencoding::encode(v));
    }
    if let Some(v) = in_vetka {
        route.push_str("&in_vetka=");
        route.push_str(if v { "1" } else { "0" });
    }
    if let Some(seek) = initial_seek_sec.filter(|v| v.is_finite() && *v >= 0.0) {
        route.push_str("&seek=");
        route.push_str(&format!("{seek:.3}"));
    }

    let explicit_video_width = video_width.filter(|v| *v > 0);
    let explicit_video_height = video_height.filter(|v| *v > 0);
    let metadata = if explicit_video_width.is_some() && explicit_video_height.is_some() {
        None
    } else {
        fetch_media_window_metadata(clean_path).await
    };
    let (screen_width, screen_height) = preferred_monitor_size(&app);
    let sizing_video_width = explicit_video_width
        .or_else(|| metadata.as_ref().and_then(|m| m.width_px))
        .unwrap_or(0);
    let sizing_video_height = explicit_video_height
        .or_else(|| metadata.as_ref().and_then(|m| m.height_px))
        .unwrap_or(0);
    let sizing_is_video = sizing_video_width > 0 && sizing_video_height > 0;
    let (initial_width, initial_height) = if sizing_is_video {
        compute_detached_media_initial_inner_size(
            sizing_video_width,
            sizing_video_height,
            screen_width,
            screen_height,
        )
    } else {
        (960.0, 540.0)
    };

    log::info!(
        "MARKER_159.R12.DETACHED_MEDIA_SIZE_TRACE path={} screen_logical={}x{} metadata={}x{} explicit={}x{} aspect={} requested_inner={}x{}",
        clean_path,
        screen_width,
        screen_height,
        metadata.as_ref().and_then(|m| m.width_px).unwrap_or(0),
        metadata.as_ref().and_then(|m| m.height_px).unwrap_or(0),
        explicit_video_width.unwrap_or(0),
        explicit_video_height.unwrap_or(0),
        aspect_ratio.as_deref().unwrap_or(""),
        initial_width,
        initial_height,
    );

    if let Some(existing) = app.get_webview_window(&label) {
        // MARKER_159.R7.UNIFIED_WINDOW_NAV_REUSE:
        // reuse the same detached artifact window label and navigate in-place to avoid
        // close/recreate races on repeated media opens while preserving a single authority window.
        let _ = apply_detached_media_inner_size(&existing, initial_width, initial_height);
        if let Ok(inner) = existing.inner_size() {
            log::info!(
                "MARKER_159.R12.DETACHED_MEDIA_REUSE_INNER observed_inner_physical={}x{}",
                inner.width,
                inner.height,
            );
        }
        let route_json = serde_json::to_string(&route).map_err(|e| e.to_string())?;
        let nav_js = format!("window.location.replace({route_json});");
        existing.eval(&nav_js).map_err(|e| e.to_string())?;
        let _ = existing.set_title(&window_title);
        existing.show().map_err(|e| e.to_string())?;
        existing.set_always_on_top(true).map_err(|e| e.to_string())?;
        existing.set_focus().map_err(|e| e.to_string())?;
        return Ok(true);
    }

    let window = WebviewWindowBuilder::new(&app, label, WebviewUrl::App(route.into()))
        .title(window_title)
        .inner_size(initial_width, initial_height)
        .min_inner_size(360.0, 240.0)
        .always_on_top(true)
        .resizable(true)
        .focused(true)
        .build()
        .map_err(|e| e.to_string())?;

    if let Ok(inner) = window.inner_size() {
        log::info!(
            "MARKER_159.R12.DETACHED_MEDIA_CREATE_INNER observed_inner_physical={}x{}",
            inner.width,
            inner.height,
        );
    }

    window.set_always_on_top(true).map_err(|e| e.to_string())?;
    window.set_focus().map_err(|e| e.to_string())?;
    Ok(true)
}

/// MARKER_159.C1_OPEN_PATH: Open/reuse native artifact window (generic route).
#[tauri::command]
pub fn open_artifact_window(
    app: AppHandle,
    path: String,
    name: Option<String>,
    extension: Option<String>,
    artifact_id: Option<String>,
    in_vetka: Option<bool>,
    initial_seek_sec: Option<f64>,
    content_mode: Option<String>,
    window_label: Option<String>,
) -> Result<bool, String> {
    let clean_path = path.trim();
    if clean_path.is_empty() {
        return Err("path is required".to_string());
    }

    let label = window_label
        .as_deref()
        .map(str::trim)
        .filter(|v| !v.is_empty())
        .unwrap_or("artifact-main")
        .to_string();

    let window_title = name
        .as_deref()
        .map(str::trim)
        .filter(|v| !v.is_empty())
        .unwrap_or("Artifact")
        .to_string();

    let mode = content_mode
        .as_deref()
        .map(str::trim)
        .filter(|v| matches!(*v, "file" | "raw" | "web"))
        .unwrap_or("file")
        .to_string();

    let mut route = format!(
        "/artifact-window?path={}&content_mode={}&window_label={}",
        urlencoding::encode(clean_path),
        urlencoding::encode(&mode),
        urlencoding::encode(&label),
    );
    if let Some(v) = name.as_deref().map(str::trim).filter(|v| !v.is_empty()) {
        route.push_str("&name=");
        route.push_str(&urlencoding::encode(v));
    }
    if let Some(v) = extension.as_deref().map(str::trim).filter(|v| !v.is_empty()) {
        route.push_str("&extension=");
        route.push_str(&urlencoding::encode(v));
    }
    if let Some(v) = artifact_id.as_deref().map(str::trim).filter(|v| !v.is_empty()) {
        route.push_str("&artifact_id=");
        route.push_str(&urlencoding::encode(v));
    }
    if let Some(v) = in_vetka {
        route.push_str("&in_vetka=");
        route.push_str(if v { "1" } else { "0" });
    }
    if let Some(seek) = initial_seek_sec.filter(|v| v.is_finite() && *v >= 0.0) {
        route.push_str("&seek=");
        route.push_str(&format!("{seek:.3}"));
    }

    if let Some(existing) = app.get_webview_window(&label) {
        // MARKER_159.R7.UNIFIED_WINDOW_NAV_REUSE:
        // reuse the detached artifact shell so repeated opens keep one authority window.
        let route_json = serde_json::to_string(&route).map_err(|e| e.to_string())?;
        let nav_js = format!("window.location.replace({route_json});");
        existing.eval(&nav_js).map_err(|e| e.to_string())?;
        let _ = existing.set_title(&window_title);
        existing.show().map_err(|e| e.to_string())?;
        existing.set_always_on_top(true).map_err(|e| e.to_string())?;
        existing.set_focus().map_err(|e| e.to_string())?;
        return Ok(true);
    }

    let window = WebviewWindowBuilder::new(&app, label, WebviewUrl::App(route.into()))
        .title(window_title)
        .inner_size(960.0, 680.0)
        .min_inner_size(760.0, 460.0)
        .always_on_top(true)
        .resizable(true)
        .focused(true)
        .build()
        .map_err(|e| e.to_string())?;

    window.set_always_on_top(true).map_err(|e| e.to_string())?;
    window.set_focus().map_err(|e| e.to_string())?;
    Ok(true)
}

/// MARKER_159.WINFS.R2_CMD: Close detached artifact media window by label.
#[tauri::command]
pub fn close_artifact_media_window(
    app: AppHandle,
    window_label: Option<String>,
) -> Result<bool, String> {
    let label = window_label
        .as_deref()
        .map(str::trim)
        .filter(|v| !v.is_empty())
        .unwrap_or("artifact-media")
        .to_string();

    if let Some(window) = app.get_webview_window(&label) {
        window.close().map_err(|e| e.to_string())?;
        return Ok(true);
    }
    Ok(false)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct WebShellNavigatePayload {
    url: String,
    title: String,
    save_path: Option<String>,
    save_paths: Option<Vec<String>>,
}

#[derive(Debug, Clone, Default)]
struct DirectWebContext {
    save_path: Option<String>,
    save_paths: Vec<String>,
}

fn direct_web_context() -> &'static Mutex<DirectWebContext> {
    // MARKER_148.WEB_DIRECT_CONTEXT_STORE: shared save-path context for direct web window.
    static DIRECT_WEB_CONTEXT: OnceLock<Mutex<DirectWebContext>> = OnceLock::new();
    DIRECT_WEB_CONTEXT.get_or_init(|| Mutex::new(DirectWebContext::default()))
}

/// MARKER_128.9B_TAURI_CMD: Open native research browser window for any external URL
#[tauri::command]
pub fn open_research_browser(
    app: AppHandle,
    url: String,
    title: Option<String>,
    save_path: Option<String>,
    save_paths: Option<Vec<String>>,
) -> Result<bool, String> {
    let parsed = Url::parse(&url).map_err(|e| format!("Invalid URL: {e}"))?;
    if parsed.scheme() != "http" && parsed.scheme() != "https" {
        return Err("Only http/https URLs are supported".to_string());
    }

    let label = "vetka-web-shell".to_string();

    let window_title = title.unwrap_or_else(|| "VETKA Research Browser".to_string());

    // MARKER_146.STEP2_NATIVE_BROWSER_SHELL_TAURI:
    // Open internal app route to render VETKA browser shell UI, passing external URL as query param.
    let mut shell_route = format!("/web-shell?url={}", urlencoding::encode(parsed.as_str()));
    if let Some(path) = save_path.as_ref() {
        if !path.trim().is_empty() {
            shell_route.push_str("&save_path=");
            shell_route.push_str(&urlencoding::encode(path.trim()));
        }
    }
    if let Some(paths) = save_paths.as_ref() {
        let compact: Vec<String> = paths
            .iter()
            .map(|p| p.trim().to_string())
            .filter(|p| !p.is_empty())
            .take(24)
            .collect();
        if !compact.is_empty() {
            let json = serde_json::to_string(&compact).map_err(|e| e.to_string())?;
            shell_route.push_str("&save_paths=");
            shell_route.push_str(&urlencoding::encode(&json));
        }
    }
    if let Some(existing) = app.get_webview_window(&label) {
        let route_json = serde_json::to_string(&shell_route).map_err(|e| e.to_string())?;
        let nav_js = format!("window.location.replace({route_json});");
        existing.eval(&nav_js).map_err(|e| e.to_string())?;
        let _ = existing.set_title(&window_title);
        let payload = WebShellNavigatePayload {
            url: parsed.as_str().to_string(),
            title: window_title,
            save_path: save_path.clone(),
            save_paths: save_paths.clone(),
        };
        let _ = existing.emit("vetka:web-shell:navigate", payload);
        existing.show().map_err(|e| e.to_string())?;
        existing.set_focus().map_err(|e| e.to_string())?;
        return Ok(true);
    }

    let window = WebviewWindowBuilder::new(&app, label, WebviewUrl::App(shell_route.into()))
        .title(window_title)
        .inner_size(1280.0, 860.0)
        .min_inner_size(960.0, 640.0)
        .resizable(true)
        .focused(true)
        .build()
        .map_err(|e| e.to_string())?;

    window.set_focus().map_err(|e| e.to_string())?;
    Ok(true)
}

/// MARKER_146.STEP2_EXTERNAL_WEBVIEW_CMD: Open raw external webview for JS/CSP-heavy sites.
#[tauri::command]
pub fn open_external_webview(app: AppHandle, url: String, title: Option<String>) -> Result<bool, String> {
    let parsed = Url::parse(&url).map_err(|e| format!("Invalid URL: {e}"))?;
    if parsed.scheme() != "http" && parsed.scheme() != "https" {
        return Err("Only http/https URLs are supported".to_string());
    }

    let label = format!(
        "vetka-web-ext-{}-{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|e| e.to_string())?
            .as_millis(),
        fastrand::u16(..)
    );

    let window_title = title.unwrap_or_else(|| "VETKA External Web".to_string());

    let window = WebviewWindowBuilder::new(&app, label, WebviewUrl::External(parsed))
        .title(window_title)
        .inner_size(1280.0, 860.0)
        .min_inner_size(960.0, 640.0)
        .resizable(true)
        .focused(true)
        .build()
        .map_err(|e| e.to_string())?;

    window.set_focus().map_err(|e| e.to_string())?;
    Ok(true)
}

/// Open/reuse a dedicated direct web window for /web search results.
/// Unlike generic external webview, this one is single-instance and coerces target=_blank to same window.
#[tauri::command]
pub fn open_direct_web_window(
    app: AppHandle,
    url: String,
    title: Option<String>,
    save_path: Option<String>,
    save_paths: Option<Vec<String>>,
) -> Result<bool, String> {
    // MARKER_148.WEB_DIRECT_SINGLE_WINDOW: dedicated /web single-instance real webview.
    let parsed = Url::parse(&url).map_err(|e| format!("Invalid URL: {e}"))?;
    if parsed.scheme() != "http" && parsed.scheme() != "https" {
        return Err("Only http/https URLs are supported".to_string());
    }

    let label = "vetka-web-direct".to_string();
    let window_title = title.unwrap_or_else(|| "VETKA Web".to_string());
    {
        // MARKER_148.WEB_DIRECT_SAVE_CONTEXT_UPDATE: refresh suggested save targets per new /web result.
        let mut ctx = direct_web_context()
            .lock()
            .map_err(|_| "direct web context lock poisoned".to_string())?;
        let clean_path = save_path.map(|p| p.trim().to_string()).filter(|p| !p.is_empty());
        let clean_paths: Vec<String> = save_paths
            .unwrap_or_default()
            .into_iter()
            .map(|p| p.trim().to_string())
            .filter(|p| !p.is_empty())
            .take(24)
            .collect();
        ctx.save_path = clean_path;
        ctx.save_paths = clean_paths;
        log::info!(
            "[WEB_DIRECT_CTX] updated save_path={} save_paths_count={}",
            ctx.save_path.clone().unwrap_or_default(),
            ctx.save_paths.len()
        );
    }

    if let Some(existing) = app.get_webview_window(&label) {
        existing.navigate(parsed).map_err(|e| e.to_string())?;
        let _ = existing.set_title(&window_title);
        existing.show().map_err(|e| e.to_string())?;
        existing.set_focus().map_err(|e| e.to_string())?;
        return Ok(true);
    }

    // MARKER_148.WEB_DIRECT_NOLAN_BAR: inject Nolan-style top panel into direct webview.
    let init_script = r#"
(() => {
  try {
    const BAR_ID = '__vetka_nolan_bar__';
    const STYLE_ID = '__vetka_nolan_style__';
    if (!document.getElementById(STYLE_ID)) {
      const style = document.createElement('style');
      style.id = STYLE_ID;
      style.textContent = `
        #${BAR_ID}{
          position: fixed;
          top: 0; left: 0; right: 0;
          height: 46px;
          z-index: 2147483647;
          background: #080808;
          border-bottom: 1px solid #202020;
          display:flex; align-items:center; gap:8px;
          padding: 0 10px;
          font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
        }
        #${BAR_ID} button{
          width:30px;height:30px;border:1px solid #2d2d2d;background:#111;color:#e8e8e8;border-radius:6px;cursor:pointer;
          display:flex; align-items:center; justify-content:center;
          line-height:1; font-size:0; padding:0; box-sizing:border-box;
          flex:0 0 30px;
        }
        #${BAR_ID} button svg{ display:block; width:14px; height:14px; pointer-events:none; }
        #${BAR_ID} input{
          height:30px;border:1px solid #2d2d2d;background:#111;color:#ddd;border-radius:6px;padding:0 10px;font-size:12px;outline:none;
        }
        #${BAR_ID} .addr{ flex:1; min-width: 280px; }
        #${BAR_ID} .find{ width: 180px; }
        #${BAR_ID} .save{ border-radius: 50%; font-weight: 600; transition: opacity .15s ease; }
        #${BAR_ID} .save svg{ width:18px; height:18px; }
        #${BAR_ID} .save.vetka-saving{ opacity: 0.6; }
        /* MARKER_148.WEB_DIRECT_SAVE_MODAL_UI: in-webview modal instead of prompt/alert dialogs */
        #__vetka_save_overlay__{
          position: fixed; inset: 0; z-index: 2147483646;
          background: rgba(0,0,0,0.55);
          display:none; align-items:center; justify-content:center;
          font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
        }
        #__vetka_save_overlay__.show{ display:flex; }
        #__vetka_save_card__{
          width:min(620px,92vw); background:#0b0b0b; border:1px solid #2a2a2a; border-radius:12px;
          padding:16px; color:#eee;
        }
        #__vetka_save_card__ h3{ margin:0 0 10px 0; font-size:18px; }
        #__vetka_save_card__ .row{ display:flex; gap:10px; margin:8px 0; }
        #__vetka_save_card__ input, #__vetka_save_card__ select{
          width:100%; height:34px; border:1px solid #2d2d2d; background:#111; color:#ddd; border-radius:8px; padding:0 10px; font-size:13px;
        }
        #__vetka_save_card__ .actions{ display:flex; justify-content:flex-end; gap:10px; margin-top:12px; }
        #__vetka_save_card__ button{
          height:34px; border:1px solid #2d2d2d; background:#151515; color:#eee; border-radius:8px; padding:0 12px; cursor:pointer;
        }
        #__vetka_save_hint__{
          margin-top:6px; color:#a0a0a0; font-size:12px; line-height:1.35;
          max-height:108px; overflow:auto; white-space:pre-line;
        }
        #__vetka_save_suggest__{
          width:100%; min-height:96px; max-height:132px;
          border:1px solid #2d2d2d; background:#0f0f0f; color:#d8d8d8; border-radius:8px;
          margin-top:8px; padding:6px; font-size:12px;
        }
        #__vetka_save_suggest__ option{
          padding:4px 6px;
        }
        #__vetka_save_toast__{
          position: fixed; right: 12px; bottom: 12px; z-index: 2147483647;
          background:#0f0f0f; border:1px solid #2d2d2d; color:#eee; border-radius:8px;
          padding:8px 10px; font-size:12px; display:none;
        }
        #__vetka_save_toast__.show{ display:block; }
      `;
      document.documentElement.appendChild(style);
    }

    const ensureBar = () => {
      if (document.getElementById(BAR_ID)) return document.getElementById(BAR_ID);
      const bar = document.createElement('div');
      bar.id = BAR_ID;
      bar.innerHTML = `
        <button id="vetka-back" title="Back" aria-label="Back">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M15 18l-6-6 6-6"/>
          </svg>
        </button>
        <button id="vetka-forward" title="Forward" aria-label="Forward">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 18l6-6-6-6"/>
          </svg>
        </button>
        <input id="vetka-addr" class="addr" placeholder="https://..." />
        <input id="vetka-find" class="find" placeholder="find in page" />
        <button id="vetka-save" class="save" title="save to vetka" aria-label="save to vetka">
          <svg width="18" height="18" viewBox="0 0 1024 1024" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block">
            <circle cx="512" cy="512" r="428" stroke="white" stroke-width="66" />
            <path d="M512 250V776" stroke="white" stroke-width="66" stroke-linecap="round"/>
            <path d="M512 516L295 294" stroke="white" stroke-width="66" stroke-linecap="round"/>
            <path d="M512 516L729 294" stroke="white" stroke-width="66" stroke-linecap="round"/>
          </svg>
        </button>
      `;
      document.documentElement.appendChild(bar);

      const root = document.documentElement;
      const body = document.body;
      if (root) root.style.scrollPaddingTop = '52px';
      if (body && !body.dataset.vetkaOffsetApplied) {
        body.style.marginTop = '46px';
        body.dataset.vetkaOffsetApplied = '1';
      }
      return bar;
    };

    const bar = ensureBar();
    if (!bar) return;
    const addr = bar.querySelector('#vetka-addr');
    const find = bar.querySelector('#vetka-find');
    const back = bar.querySelector('#vetka-back');
    const forward = bar.querySelector('#vetka-forward');
    const save = bar.querySelector('#vetka-save');
    let saveOverlay = document.getElementById('__vetka_save_overlay__');
    if (!saveOverlay) {
      saveOverlay = document.createElement('div');
      saveOverlay.id = '__vetka_save_overlay__';
      saveOverlay.innerHTML = `
        <div id="__vetka_save_card__">
          <h3>Save to VETKA</h3>
          <div class="row">
            <input id="__vetka_save_name__" placeholder="File name" />
            <select id="__vetka_save_fmt__">
              <option value="md">MD</option>
              <option value="html">HTML</option>
            </select>
          </div>
          <div class="row">
            <input id="__vetka_save_path__" placeholder="Destination path (nearest viewport path by default)" />
          </div>
          <select id="__vetka_save_suggest__" size="5"></select>
          <div id="__vetka_save_hint__"></div>
          <div class="actions">
            <button id="__vetka_save_cancel__">Cancel</button>
            <button id="__vetka_save_submit__">Save</button>
          </div>
        </div>`;
      document.documentElement.appendChild(saveOverlay);
    }
    let saveToast = document.getElementById('__vetka_save_toast__');
    if (!saveToast) {
      saveToast = document.createElement('div');
      saveToast.id = '__vetka_save_toast__';
      document.documentElement.appendChild(saveToast);
    }

    const setAddr = () => { if (addr) addr.value = window.location.href; };
    setAddr();
    window.addEventListener('hashchange', setAddr);
    window.addEventListener('popstate', setAddr);

    if (addr && !addr.dataset.bound) {
      addr.dataset.bound = '1';
      addr.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter') return;
        const raw = (addr.value || '').trim();
        if (!raw) return;
        const normalized = /^https?:\/\//i.test(raw) ? raw : `https://${raw}`;
        window.location.assign(normalized);
      });
    }
    if (find && !find.dataset.bound) {
      find.dataset.bound = '1';
      find.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter') return;
        const q = (find.value || '').trim();
        if (!q) return;
        try { window.find(q, false, false, true, false, false, false); } catch (_) {}
      });
    }
    if (back && !back.dataset.bound) {
      back.dataset.bound = '1';
      back.addEventListener('click', () => { try { history.back(); } catch (_) {} });
    }
    if (forward && !forward.dataset.bound) {
      forward.dataset.bound = '1';
      forward.addEventListener('click', () => { try { history.forward(); } catch (_) {} });
    }
    const tauriInvoke =
      (window.__TAURI__ && window.__TAURI__.core && window.__TAURI__.core.invoke)
      || (window.__TAURI_INTERNALS__ && window.__TAURI_INTERNALS__.invoke)
      || null;

    const showToast = (text) => {
      if (!saveToast) return;
      saveToast.textContent = text;
      saveToast.classList.add('show');
      setTimeout(() => { try { saveToast.classList.remove('show'); } catch (_) {} }, 3200);
    };

    // MARKER_148.WEB_DIRECT_SAVE_MODAL_FLOW: two-step save interaction rendered inside Nolan bar context.
    if (save && !save.dataset.bound) {
      save.dataset.bound = '1';
      save.addEventListener('click', async () => {
        try {
          save.classList.add('vetka-saving');
          const defaultName = (document.title || window.location.hostname || 'web-page').slice(0, 140);
          let suggested = [];
          try {
            const ctx = await tauriInvoke('get_direct_web_save_context', {});
            const arr = Array.isArray(ctx && ctx.suggested_paths) ? ctx.suggested_paths : [];
            const single = ctx && typeof ctx.suggested_path === 'string' ? ctx.suggested_path : '';
            suggested = [single, ...arr].filter(Boolean).slice(0, 8);
          } catch (_) {}
          const nameEl = document.getElementById('__vetka_save_name__');
          const fmtEl = document.getElementById('__vetka_save_fmt__');
          const pathEl = document.getElementById('__vetka_save_path__');
          const suggestEl = document.getElementById('__vetka_save_suggest__');
          const hintEl = document.getElementById('__vetka_save_hint__');
          const cancelEl = document.getElementById('__vetka_save_cancel__');
          const submitEl = document.getElementById('__vetka_save_submit__');
          if (!nameEl || !fmtEl || !pathEl || !suggestEl || !hintEl || !cancelEl || !submitEl || !saveOverlay) {
            showToast('Save UI init failed');
            return;
          }
          nameEl.value = defaultName;
          pathEl.value = suggested.length > 0 ? suggested[0] : '';
          suggestEl.innerHTML = '';
          for (const p of suggested) {
            const opt = document.createElement('option');
            opt.value = p;
            opt.textContent = p;
            suggestEl.appendChild(opt);
          }
          if (suggested.length > 0) {
            hintEl.textContent = `Suggested paths: ${suggested.length}. Choose from list or edit manually.`;
          } else {
            hintEl.textContent = 'No viewport suggestions yet.';
          }
          suggestEl.onchange = () => {
            if (suggestEl.value) pathEl.value = suggestEl.value;
          };
          suggestEl.ondblclick = () => {
            if (suggestEl.value) {
              pathEl.value = suggestEl.value;
              submitEl.click();
            }
          };
          saveOverlay.classList.add('show');
          const closeOverlay = () => saveOverlay.classList.remove('show');
          const onCancel = () => closeOverlay();
          const onSubmit = async () => {
            const cleanName = String(nameEl.value || '').trim() || defaultName;
            const fmt = String(fmtEl.value || 'md').trim().toLowerCase() === 'html' ? 'html' : 'md';
            const chosenPath = String(pathEl.value || '').trim();
            const rawHtml = String(document.documentElement && document.documentElement.outerHTML ? document.documentElement.outerHTML : '').slice(0, 1200000);
            const rawText = String(document.body && document.body.innerText ? document.body.innerText : '').slice(0, 300000);
            try {
              if (tauriInvoke) {
                const result = await tauriInvoke('save_webpage_from_direct_window', {
                  url: window.location.href,
                  title: document.title || window.location.hostname || 'web-page',
                  fileName: cleanName,
                  outputFormat: fmt,
                  targetNodePath: chosenPath,
                  rawHtml: rawHtml,
                  rawText: rawText
                });
                if (!result || result.success !== true) {
                  const msg = (result && result.error) ? result.error : 'save failed';
                  showToast(`Save failed: ${msg}`);
                } else {
                  showToast(`Saved: ${result.file_path || '(saved)'}`);
                }
                closeOverlay();
                return;
              }
              // MARKER_148.WEB_DIRECT_SAVE_MODAL_NAV_FALLBACK: fallback save transport via intercepted nav.
              const qp = new URLSearchParams({
                url: window.location.href,
                title: document.title || window.location.hostname || 'web-page',
                file_name: cleanName,
                output_format: fmt,
                target_node_path: chosenPath
              });
              window.location.assign(`https://vetka.invalid/__save?${qp.toString()}`);
              closeOverlay();
            } catch (_) {
              showToast('Save failed');
            }
          };
          cancelEl.onclick = onCancel;
          submitEl.onclick = onSubmit;
          setTimeout(() => { try { nameEl.focus(); } catch (_) {} }, 0);

        } catch (_) {
        } finally {
          try { save.classList.remove('vetka-saving'); } catch (_) {}
        }
      });
    }

    if (!window.__vetkaSaveResultBound) {
      window.__vetkaSaveResultBound = true;
      try {
        const listen = window.__TAURI__ && window.__TAURI__.event && window.__TAURI__.event.listen;
        if (typeof listen === 'function') {
          listen('vetka:web-save-result', (event) => {
            const p = event && event.payload ? event.payload : {};
            if (p.success) {
              showToast(`Saved: ${p.file_path || '(saved)'}`);
            } else {
              showToast(`Save failed: ${p.error || 'unknown error'}`);
            }
          });
        }
      } catch (_) {}
    }

    window.open = function(url) {
      try {
        if (typeof url === 'string' && url.length > 0) window.location.assign(url);
      } catch (_) {}
      return window;
    };
    document.addEventListener('click', (event) => {
      const target = event.target;
      const anchor = target && target.closest ? target.closest('a[target="_blank"]') : null;
      if (!anchor) return;
      anchor.setAttribute('target', '_self');
    }, true);
  } catch (_) {}
})();
"#;
    let nav_app = app.clone();

    let window = WebviewWindowBuilder::new(&app, label, WebviewUrl::External(parsed))
        .title(window_title)
        .inner_size(1280.0, 860.0)
        .min_inner_size(960.0, 640.0)
        .resizable(true)
        .focused(true)
        .initialization_script(init_script)
        .on_navigation(move |url| {
            // MARKER_148.WEB_DIRECT_SAVE_NAV_BRIDGE: handle save intent via intercepted navigation when JS invoke is unavailable.
            let is_custom_scheme_save = url.scheme() == "vetka" && url.host_str() == Some("save");
            let is_https_bridge_save = url.scheme() == "https"
                && url.host_str() == Some("vetka.invalid")
                && url.path() == "/__save";
            if !is_custom_scheme_save && !is_https_bridge_save {
                return true;
            }
            if is_custom_scheme_save && url.host_str() != Some("save") {
                return false;
            }

            let parsed = match Url::parse(url.as_str()) {
                Ok(v) => v,
                Err(_) => return false,
            };
            let mut req_url = String::new();
            let mut req_title = String::new();
            let mut req_file_name = String::new();
            let mut req_format = "md".to_string();
            let mut req_target = String::new();

            for (k, v) in parsed.query_pairs() {
                match k.as_ref() {
                    "url" => req_url = v.to_string(),
                    "title" => req_title = v.to_string(),
                    "file_name" => req_file_name = v.to_string(),
                    "output_format" => req_format = v.to_string(),
                    "target_node_path" => req_target = v.to_string(),
                    _ => {}
                }
            }

            let app_handle = nav_app.clone();
            tauri::async_runtime::spawn(async move {
                log::info!(
                    "[WEB_DIRECT_SAVE] bridge request url={} format={} target={}",
                    req_url,
                    req_format,
                    req_target
                );
                let result = save_webpage_via_api(
                    req_url,
                    if req_title.is_empty() { "web-page".to_string() } else { req_title },
                    req_file_name,
                    if req_format == "html" { "html".to_string() } else { "md".to_string() },
                    req_target,
                    None,
                    None,
                ).await;
                if let Err(e) = &result {
                    log::error!("[WEB_DIRECT_SAVE] bridge error: {}", e);
                }
                let payload = match result {
                    Ok(ok) => serde_json::json!({
                        "success": ok.success,
                        "file_path": ok.file_path,
                        "target_node_path": ok.target_node_path,
                        "error": ok.error
                    }),
                    Err(e) => serde_json::json!({
                        "success": false,
                        "error": e
                    }),
                };
                if let Some(window) = app_handle.get_webview_window("vetka-web-direct") {
                    let _ = window.emit("vetka:web-save-result", &payload);
                }
                if let Some(main_window) = app_handle.get_webview_window("main") {
                    let _ = main_window.emit("vetka:web-artifact-saved", &payload);
                }
            });
            false
        })
        .build()
        .map_err(|e| e.to_string())?;

    window.set_focus().map_err(|e| e.to_string())?;
    Ok(true)
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SaveWebDirectResult {
    pub success: bool,
    pub file_path: Option<String>,
    pub target_node_path: Option<String>,
    pub error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DirectWebSaveContext {
    pub suggested_path: Option<String>,
    pub suggested_paths: Vec<String>,
}

async fn save_webpage_via_api(
    url: String,
    title: String,
    file_name: String,
    output_format: String,
    target_node_path: String,
    raw_html: Option<String>,
    raw_text: Option<String>,
) -> Result<SaveWebDirectResult, String> {
    let target_url = url.trim().to_string();
    if target_url.is_empty() {
        return Ok(SaveWebDirectResult {
            success: false,
            file_path: None,
            target_node_path: None,
            error: Some("URL is empty".to_string()),
        });
    }

    let api_url = std::env::var("VETKA_API_URL").unwrap_or_else(|_| "http://localhost:5001".to_string());
    let endpoint = format!("{}/api/artifacts/save-webpage", api_url.trim_end_matches('/'));
    let payload = serde_json::json!({
        "url": target_url,
        "title": title,
        "snippet": "",
        "raw_html": raw_html.unwrap_or_default(),
        "raw_text": raw_text.unwrap_or_default(),
        "output_format": output_format,
        "file_name": file_name,
        "target_node_path": target_node_path,
    });

    let client = reqwest::Client::new();
    let response = client
        .post(endpoint)
        .json(&payload)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let status_ok = response.status().is_success();
    let data: serde_json::Value = response
        .json()
        .await
        .unwrap_or_else(|_| serde_json::json!({}));

    if !status_ok || data.get("success").and_then(|v| v.as_bool()) != Some(true) {
        let err = data
            .get("error")
            .and_then(|v| v.as_str())
            .unwrap_or("save failed")
            .to_string();
        return Ok(SaveWebDirectResult {
            success: false,
            file_path: None,
            target_node_path: Some(target_node_path),
            error: Some(err),
        });
    }

    // MARKER_148.WEB_DIRECT_INDEX_AFTER_SAVE: best-effort immediate indexing for Qdrant/search freshness.
    if let Some(saved_path) = data.get("file_path").and_then(|v| v.as_str()) {
        let index_endpoint = format!("{}/api/watcher/index-file", api_url.trim_end_matches('/'));
        match client
            .post(index_endpoint)
            .json(&serde_json::json!({
                "path": saved_path,
                "recursive": false,
            }))
            .send()
            .await
        {
            Ok(resp) => {
                let status = resp.status();
                let body = resp.text().await.unwrap_or_default();
                log::info!(
                    "[WEB_DIRECT_INDEX] status={} path={} body={}",
                    status,
                    saved_path,
                    body.chars().take(220).collect::<String>()
                );
            }
            Err(e) => {
                log::error!("[WEB_DIRECT_INDEX] request failed for {}: {}", saved_path, e);
            }
        }
    }

    Ok(SaveWebDirectResult {
        success: true,
        file_path: data.get("file_path").and_then(|v| v.as_str()).map(|s| s.to_string()),
        target_node_path: data
            .get("target_node_path")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
            .or_else(|| {
                if target_node_path.trim().is_empty() {
                    None
                } else {
                    Some(target_node_path.clone())
                }
            }),
        error: None,
    })
}

#[tauri::command]
pub fn get_direct_web_save_context() -> Result<DirectWebSaveContext, String> {
    // MARKER_148.WEB_DIRECT_SAVE_CONTEXT_API: expose viewport-derived save suggestions to Nolan bar.
    let guard = direct_web_context()
        .lock()
        .map_err(|_| "direct web context lock poisoned".to_string())?;
    log::info!(
        "[WEB_DIRECT_CTX] read save_path={} save_paths_count={}",
        guard.save_path.clone().unwrap_or_default(),
        guard.save_paths.len()
    );
    Ok(DirectWebSaveContext {
        suggested_path: guard.save_path.clone(),
        suggested_paths: guard.save_paths.clone(),
    })
}

#[tauri::command]
pub async fn save_webpage_from_direct_window(
    app: AppHandle,
    url: String,
    title: Option<String>,
    file_name: Option<String>,
    output_format: Option<String>,
    target_node_path: Option<String>,
    raw_html: Option<String>,
    raw_text: Option<String>,
) -> Result<SaveWebDirectResult, String> {
    // MARKER_148.WEB_DIRECT_SAVE_BRIDGE: save current direct-web page into VETKA artifact API.
    let chosen_path = if let Some(path) = target_node_path.map(|p| p.trim().to_string()).filter(|p| !p.is_empty()) {
        path
    } else {
        let chosen = {
        let guard = direct_web_context()
            .lock()
            .map_err(|_| "direct web context lock poisoned".to_string())?;
        guard
            .save_path
            .clone()
            .or_else(|| guard.save_paths.first().cloned())
            .unwrap_or_default()
        };
        chosen
    };
    let result = save_webpage_via_api(
        url,
        title.unwrap_or_else(|| "web-page".to_string()),
        file_name.unwrap_or_default(),
        output_format.unwrap_or_else(|| "md".to_string()),
        chosen_path,
        raw_html,
        raw_text,
    ).await?;

    if result.success {
        let payload = serde_json::json!({
            "success": true,
            "file_path": result.file_path,
            "target_node_path": result.target_node_path,
            "error": result.error,
        });
        if let Some(main_window) = app.get_webview_window("main") {
            let _ = main_window.emit("vetka:web-artifact-saved", payload);
        }
    }

    Ok(result)
}
