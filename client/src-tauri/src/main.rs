// VETKA Desktop App - Tauri Backend
// Phase 100.1: Foundation
// Phase 100.2: Native FS + Drag & Drop
// Phase 134: Multi-window MCC support

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod file_system;
mod heartbeat;

use tauri::{Manager, Emitter, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_deep_link::DeepLinkExt;

// MARKER_134.C34B: Mycelium Command Center window commands
#[tauri::command]
async fn open_mycelium(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("mycelium") {
        window.show().map_err(|e| e.to_string())?;
        window.set_focus().map_err(|e| e.to_string())?;
    } else {
        // Window not in config or was closed — recreate
        WebviewWindowBuilder::new(
            &app,
            "mycelium",
            WebviewUrl::App("/mycelium".into()),
        )
        .title("MYCELIUM")
        .inner_size(960.0, 680.0)
        .resizable(true)
        .always_on_top(false)
        .build()
        .map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
async fn close_mycelium(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("mycelium") {
        window.hide().map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn main() {
    env_logger::init();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_deep_link::init())
        .invoke_handler(tauri::generate_handler![
            // Phase 100.1: Basic commands
            commands::get_backend_url,
            commands::check_backend_health,
            commands::get_system_info,
            commands::trace_detached_media_geometry,
            commands::pick_folder_native,
            commands::pick_files_native,
            commands::set_window_fullscreen,
            commands::get_window_fullscreen,
            commands::toggle_current_window_fullscreen,
            commands::get_current_window_fullscreen,
            commands::set_current_window_fullscreen,
            commands::open_artifact_window,
            commands::open_artifact_media_window,
            commands::close_artifact_media_window,
            commands::open_research_browser,
            commands::open_external_webview,
            commands::open_direct_web_window,
            commands::get_direct_web_save_context,
            commands::save_webpage_from_direct_window,
            // Phase 100.2: Native file system
            file_system::read_file_native,
            file_system::write_file_native,
            file_system::remove_file_native,
            file_system::list_directory,
            file_system::watch_directory,
            file_system::handle_drop_paths,
            // MARKER_134.C34B: Mycelium window commands
            open_mycelium,
            close_mycelium,
        ])
        .setup(|app| {
            let handle = app.handle().clone();

            #[cfg(desktop)]
            {
                // MARKER_147_5_TAURI_DEEPLINK_EVENT: bridge native vetka://oauth/callback into frontend event stream.
                let main_handle = app.handle().clone();
                let _ = app.deep_link().on_open_url(move |event| {
                    let urls: Vec<String> = event.urls().iter().map(|u| u.to_string()).collect();
                    if let Some(window) = main_handle.get_webview_window("main") {
                        let _ = window.emit("oauth-deep-link", serde_json::json!({ "urls": urls }));
                    }
                });

                if let Ok(Some(current)) = app.deep_link().get_current() {
                    if !current.is_empty() {
                        let urls: Vec<String> = current.iter().map(|u| u.to_string()).collect();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.emit("oauth-deep-link", serde_json::json!({ "urls": urls }));
                        }
                    }
                }
            }

            // Start heartbeat service in background
            tauri::async_runtime::spawn(async move {
                heartbeat::start_heartbeat_loop(handle).await;
            });

            // Phase 100.2: Setup drag & drop listener via window events
            let window = app.get_webview_window("main").expect("main window not found");
            let window_handle = window.clone();

            window.on_window_event(move |event| {
                if let tauri::WindowEvent::DragDrop(drag_event) = event {
                    match drag_event {
                        tauri::DragDropEvent::Drop { paths, position } => {
                            let path_strings: Vec<String> = paths
                                .iter()
                                .map(|p| p.to_string_lossy().to_string())
                                .collect();

                            log::info!("[VETKA D&D] Files dropped at {:?}: {:?}", position, path_strings);

                            // Phase 100.5: Emit to frontend with explicit error logging
                            match window_handle.emit("files-dropped", &path_strings) {
                                Ok(_) => log::info!("[VETKA D&D] Event emitted successfully"),
                                Err(e) => log::error!("[VETKA D&D] Failed to emit event: {:?}", e),
                            }
                        }
                        tauri::DragDropEvent::Enter { paths, position: _ } => {
                            log::debug!("Drag enter: {} files", paths.len());
                        }
                        tauri::DragDropEvent::Over { position: _ } => {
                            // Continuous event while dragging over
                        }
                        tauri::DragDropEvent::Leave => {
                            log::debug!("Drag leave");
                        }
                        _ => {}
                    }
                }
            });

            log::info!("VETKA Desktop initialized (Phase 100.5)");
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running VETKA");
}
