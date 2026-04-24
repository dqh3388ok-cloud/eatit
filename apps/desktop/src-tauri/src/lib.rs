mod backend;
mod llm_config;

use tauri::{Manager, RunEvent};

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to Eatit.", name)
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
