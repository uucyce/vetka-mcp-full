// VETKA Heartbeat Service - JARVIS Proactive Mode
// Phase 100.3: Periodic check for open tasks

use tauri::Emitter;
use std::time::Duration;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HeartbeatPayload {
    pub timestamp: u64,
    pub open_tasks: usize,
    pub message: Option<String>,
    pub should_notify: bool,
}

#[derive(Debug, Deserialize)]
struct TasksResponse {
    tasks: Vec<serde_json::Value>,
}

/// Start the heartbeat loop
/// Checks for open tasks every 5 minutes
/// Sends notification if there are unfinished tasks
pub async fn start_heartbeat_loop(app: tauri::AppHandle) {
    let interval = Duration::from_secs(5 * 60); // 5 minutes

    log::info!("Heartbeat service started (interval: {:?})", interval);

    loop {
        tokio::time::sleep(interval).await;

        match check_open_tasks().await {
            Ok(payload) => {
                // Emit to frontend
                let _ = app.emit("heartbeat", &payload);

                // Show native notification if needed
                if payload.should_notify && payload.open_tasks > 0 {
                    show_notification(&app, &payload);
                }

                log::debug!("Heartbeat: {} open tasks", payload.open_tasks);
            }
            Err(e) => {
                log::warn!("Heartbeat check failed: {}", e);
            }
        }
    }
}

async fn check_open_tasks() -> Result<HeartbeatPayload, String> {
    let api_url = std::env::var("VETKA_API_URL")
        .unwrap_or_else(|_| "http://localhost:5001".to_string());

    let client = reqwest::Client::new();

    // Try to get open tasks from backend
    // Falls back to 0 if endpoint doesn't exist yet
    // MARKER_148.HEARTBEAT_NO_BLOCK_ON: never call block_on inside tokio runtime worker.
    let open_tasks = match client
        .get(format!("{}/api/tasks/open", api_url))
        .timeout(Duration::from_secs(10))
        .send()
        .await
    {
        Ok(resp) if resp.status().is_success() => match resp.json::<TasksResponse>().await {
            Ok(payload) => payload.tasks.len(),
            Err(_) => 0,
        },
        _ => 0,
    };

    let timestamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();

    let message = if open_tasks > 0 {
        Some(format!("You have {} open task(s). Continue?", open_tasks))
    } else {
        None
    };

    Ok(HeartbeatPayload {
        timestamp,
        open_tasks,
        message,
        should_notify: open_tasks > 0,
    })
}

fn show_notification(app: &tauri::AppHandle, payload: &HeartbeatPayload) {
    use tauri_plugin_notification::NotificationExt;

    if let Some(msg) = &payload.message {
        let _ = app.notification()
            .builder()
            .title("VETKA")
            .body(msg)
            .show();
    }
}
