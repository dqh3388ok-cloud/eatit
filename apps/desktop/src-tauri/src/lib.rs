mod backend;
mod llm_config;

use tauri::{Manager, RunEvent};

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to Eatit.", name)
}

/// Open a macOS URL scheme via the `open` CLI.
///
/// WKWebView's default navigation handler drops unknown URL schemes on the
/// floor (setting `window.location.href = "x-apple.systempreferences:..."`
/// just silently no-ops), so the frontend can't jump to System Settings on
/// its own. We shell out to `/usr/bin/open`, which always respects URL
/// handlers registered with LaunchServices.
///
/// Tight allow-list: only `x-apple.systempreferences:` so a compromised
/// frontend can't ask us to launch arbitrary schemes (`file://`,
/// `javascript:`, etc).
#[tauri::command]
fn open_system_url(url: String) -> Result<(), String> {
    if !url.starts_with("x-apple.systempreferences:") {
        return Err("scheme not allowed".into());
    }
    std::process::Command::new("open")
        .arg(&url)
        .spawn()
        .map_err(|e| format!("failed to spawn open: {e}"))?;
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .setup(|app| {
            app.manage(backend::BackendState::new());
            let handle = app.handle().clone();
            // Spawn on a worker thread so window creation doesn't block
            // waiting for the bundled backend to print its ready line
            // (up to 30s on first launch, though it's usually a couple
            // of seconds).
            std::thread::spawn(move || {
                backend::spawn_backend(handle);
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            open_system_url,
            backend::get_backend_port,
            llm_config::save_llm_config,
            llm_config::load_llm_config,
            llm_config::delete_llm_config,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
            backend::shutdown_backend(app_handle);
        }
    });
}
