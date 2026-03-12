// MARKER_175.5: MYCELIUM standalone — minimal Tauri shell for MCC
// No 3D commands, no file watcher, no deep-link, no artifact windows.
// MCC communicates entirely via REST API + WebSocket (no Tauri IPC needed).

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;

fn main() {
    env_logger::init();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            get_backend_url,
            check_backend_health,
            get_mycelium_info,
        ])
        .setup(|app| {
            // Log startup
            log::info!("MYCELIUM standalone starting...");

            // Auto-focus the main window
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_focus();
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running MYCELIUM");
}

/// Returns the backend URL for REST API calls.
/// MCC uses this to connect to FastAPI on port 5001.
#[tauri::command]
fn get_backend_url() -> String {
    std::env::var("VETKA_BACKEND_URL")
        .unwrap_or_else(|_| "http://localhost:5001".to_string())
}

/// Health check — pings FastAPI backend.
#[tauri::command]
async fn check_backend_health() -> Result<String, String> {
    let url = std::env::var("VETKA_BACKEND_URL")
        .unwrap_or_else(|_| "http://localhost:5001".to_string());

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .map_err(|e| e.to_string())?;

    match client.get(format!("{}/api/health", url)).send().await {
        Ok(resp) => Ok(format!("Backend: {} ({})", resp.status(), url)),
        Err(e) => Err(format!("Backend unreachable: {} — {}", url, e)),
    }
}

/// Returns MYCELIUM app metadata.
#[tauri::command]
fn get_mycelium_info() -> serde_json::Value {
    serde_json::json!({
        "app": "MYCELIUM",
        "version": env!("CARGO_PKG_VERSION"),
        "description": env!("CARGO_PKG_DESCRIPTION"),
        "standalone": true,
        "backend_url": get_backend_url(),
    })
}
