// VETKA Tauri Commands - IPC Bridge
// Phase 100.1: Basic commands

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, WebviewUrl, WebviewWindowBuilder};
use url::Url;

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

/// MARKER_128.9B_TAURI_CMD: Open native research browser window for any external URL
#[tauri::command]
pub fn open_research_browser(app: AppHandle, url: String, title: Option<String>) -> Result<bool, String> {
    let parsed = Url::parse(&url).map_err(|e| format!("Invalid URL: {e}"))?;
    if parsed.scheme() != "http" && parsed.scheme() != "https" {
        return Err("Only http/https URLs are supported".to_string());
    }

    let label = format!(
        "vetka-web-{}-{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|e| e.to_string())?
            .as_millis(),
        fastrand::u16(..)
    );

    let window_title = title.unwrap_or_else(|| "VETKA Research Browser".to_string());

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
