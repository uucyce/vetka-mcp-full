// VETKA Desktop App - Tauri Backend
// Phase 100.1: Foundation
// Phase 100.2: Native FS + Drag & Drop

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod file_system;
mod heartbeat;

use tauri::{Manager, Emitter};

fn main() {
    env_logger::init();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_notification::init())
        .invoke_handler(tauri::generate_handler![
            // Phase 100.1: Basic commands
            commands::get_backend_url,
            commands::check_backend_health,
            commands::get_system_info,
            // Phase 100.2: Native file system
            file_system::read_file_native,
            file_system::write_file_native,
            file_system::remove_file_native,
            file_system::list_directory,
            file_system::watch_directory,
            file_system::handle_drop_paths,
        ])
        .setup(|app| {
            let handle = app.handle().clone();

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
