// VETKA Native File System Access
// Phase 100.2: Direct file operations without HTTP overhead

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use tauri::Emitter;

#[derive(Debug, Serialize, Deserialize)]
pub struct FileInfo {
    pub name: String,
    pub path: String,
    pub is_dir: bool,
    pub size: u64,
    pub modified: Option<u64>,
    pub extension: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FileContent {
    pub path: String,
    pub content: String,
    pub size: u64,
    pub encoding: String,
}

/// Read file content directly (no HTTP roundtrip)
/// Much faster than going through FastAPI
#[tauri::command]
pub async fn read_file_native(path: String) -> Result<FileContent, String> {
    let file_path = PathBuf::from(&path);

    if !file_path.exists() {
        return Err(format!("File not found: {}", path));
    }

    let metadata = std::fs::metadata(&file_path)
        .map_err(|e| format!("Cannot read metadata: {}", e))?;

    if metadata.len() > 10 * 1024 * 1024 {
        return Err("File too large (>10MB)".to_string());
    }

    let content = std::fs::read_to_string(&file_path)
        .map_err(|e| format!("Cannot read file: {}", e))?;

    Ok(FileContent {
        path,
        content,
        size: metadata.len(),
        encoding: "utf-8".to_string(),
    })
}

/// List directory contents
#[tauri::command]
pub async fn list_directory(path: String) -> Result<Vec<FileInfo>, String> {
    let dir_path = PathBuf::from(&path);

    if !dir_path.is_dir() {
        return Err(format!("Not a directory: {}", path));
    }

    let mut entries = Vec::new();

    let read_dir = std::fs::read_dir(&dir_path)
        .map_err(|e| format!("Cannot read directory: {}", e))?;

    for entry in read_dir.flatten() {
        let metadata = entry.metadata().ok();
        let path_buf = entry.path();

        entries.push(FileInfo {
            name: entry.file_name().to_string_lossy().to_string(),
            path: path_buf.to_string_lossy().to_string(),
            is_dir: path_buf.is_dir(),
            size: metadata.as_ref().map(|m| m.len()).unwrap_or(0),
            modified: metadata.and_then(|m| {
                m.modified().ok()?.duration_since(std::time::UNIX_EPOCH).ok().map(|d| d.as_secs())
            }),
            extension: path_buf.extension().map(|e| e.to_string_lossy().to_string()),
        });
    }

    // Sort: directories first, then by name
    entries.sort_by(|a, b| {
        match (a.is_dir, b.is_dir) {
            (true, false) => std::cmp::Ordering::Less,
            (false, true) => std::cmp::Ordering::Greater,
            _ => a.name.to_lowercase().cmp(&b.name.to_lowercase()),
        }
    });

    Ok(entries)
}

/// Watch directory for changes (returns immediately, sends events via Tauri)
#[tauri::command]
pub async fn watch_directory(
    app: tauri::AppHandle,
    path: String,
) -> Result<String, String> {
    use notify::{Watcher, RecursiveMode, Event};
    use std::sync::mpsc::channel;

    let (tx, rx) = channel::<Result<Event, notify::Error>>();

    let mut watcher = notify::recommended_watcher(tx)
        .map_err(|e| format!("Cannot create watcher: {}", e))?;

    watcher.watch(std::path::Path::new(&path), RecursiveMode::Recursive)
        .map_err(|e| format!("Cannot watch path: {}", e))?;

    let watch_path = path.clone();

    // Spawn background task to emit events
    tauri::async_runtime::spawn(async move {
        // Keep watcher alive
        let _watcher = watcher;

        while let Ok(event) = rx.recv() {
            if let Ok(event) = event {
                let _ = app.emit("file-change", serde_json::json!({
                    "path": watch_path,
                    "kind": format!("{:?}", event.kind),
                    "paths": event.paths.iter().map(|p| p.to_string_lossy().to_string()).collect::<Vec<_>>(),
                }));
            }
        }
    });

    Ok(format!("Watching: {}", path))
}

// ============================================================
// Phase 100.2: Write & Drag-Drop Support
// ============================================================

/// Write file content directly (native, no HTTP)
/// Creates parent directories if they don't exist
#[tauri::command]
pub async fn write_file_native(path: String, content: String) -> Result<String, String> {
    use std::fs::{self, File};
    use std::io::Write;

    let file_path = PathBuf::from(&path);

    // Security: Basic path validation (only $HOME or /tmp)
    if !is_allowed_path(&file_path) {
        return Err("Path not allowed (security restriction)".to_string());
    }

    // Size check (10MB limit)
    if content.len() > 10 * 1024 * 1024 {
        return Err("Content too large (>10MB)".to_string());
    }

    // Create parent directories if needed
    if let Some(parent) = file_path.parent() {
        fs::create_dir_all(parent)
            .map_err(|e| format!("Cannot create directories: {}", e))?;
    }

    // Write file
    let mut file = File::create(&file_path)
        .map_err(|e| format!("Cannot create file: {}", e))?;
    file.write_all(content.as_bytes())
        .map_err(|e| format!("Cannot write file: {}", e))?;
    file.sync_all()
        .map_err(|e| format!("Cannot sync file: {}", e))?;

    log::info!("Written file: {} ({} bytes)", path, content.len());
    Ok(format!("Written: {} ({} bytes)", path, content.len()))
}

/// Remove file (for cleanup)
#[tauri::command]
pub async fn remove_file_native(path: String) -> Result<String, String> {
    let file_path = PathBuf::from(&path);

    if !is_allowed_path(&file_path) {
        return Err("Path not allowed (security restriction)".to_string());
    }

    std::fs::remove_file(&file_path)
        .map_err(|e| format!("Cannot remove file: {}", e))?;

    log::info!("Removed file: {}", path);
    Ok(format!("Removed: {}", path))
}

/// Handle drag & drop paths - process dropped files/folders
#[tauri::command]
pub async fn handle_drop_paths(paths: Vec<String>) -> Result<Vec<FileInfo>, String> {
    let mut results = Vec::new();

    for path_str in paths {
        let path = PathBuf::from(&path_str);

        if !path.exists() {
            continue;
        }

        let metadata = std::fs::metadata(&path).ok();
        let is_dir = path.is_dir();

        results.push(FileInfo {
            name: path.file_name()
                .map(|n| n.to_string_lossy().to_string())
                .unwrap_or_else(|| path_str.clone()),
            path: path_str,
            is_dir,
            size: metadata.as_ref().map(|m| m.len()).unwrap_or(0),
            modified: metadata.and_then(|m| {
                m.modified().ok()?.duration_since(std::time::UNIX_EPOCH).ok().map(|d| d.as_secs())
            }),
            extension: path.extension().map(|e| e.to_string_lossy().to_string()),
        });
    }

    log::info!("Processed {} dropped items", results.len());
    Ok(results)
}

/// Helper: Basic path validation
fn is_allowed_path(path: &PathBuf) -> bool {
    // Allow paths under $HOME or /tmp
    let home = std::env::var("HOME").unwrap_or_else(|_| "/Users".to_string());

    path.starts_with(&home)
        || path.starts_with("/tmp")
        || path.starts_with("/var/folders")  // macOS temp
}
