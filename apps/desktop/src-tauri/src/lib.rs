mod llm_config;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to Eatit.", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            greet,
            llm_config::save_llm_config,
            llm_config::load_llm_config,
            llm_config::delete_llm_config,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
