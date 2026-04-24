//! Bundled backend supervisor.
//!
//! On app startup we spawn the PyInstaller-packaged `eatit-backend`
//! executable (bundled as a resource under `Eatit.app/Contents/Resources/
//! resources/backend/`) as a child process. The backend picks a free
//! TCP port and prints `EATIT_BACKEND_READY port=<N>` to stdout after
//! uvicorn has finished starting. We parse that line, stash the port in
//! app state, and expose it to the webview via a Tauri command so the
//! React layer's axios / WebSocket wrappers can target the right URL.
//!
//! On app shutdown (RunEvent::ExitRequested / RunEvent::Exit) we send
//! SIGTERM to the child so it tears down uvicorn cleanly; a 2s grace
//! before SIGKILL as a safety net.

use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager, State};

/// Default when the bundled binary is missing or failed to emit a ready line.
/// Matches the `uv run uvicorn` port so `pnpm tauri dev` keeps working.
const DEV_FALLBACK_PORT: u16 = 8000;

/// How long we wait for the backend to emit its ready line before giving
/// up and falling back to DEV_FALLBACK_PORT. The WebView just hangs on
/// "connection refused" if neither ends up listening.
const BACKEND_READY_TIMEOUT_SECS: u64 = 30;

#[derive(Default)]
pub struct BackendState {
    pub port: Mutex<Option<u16>>,
    pub child: Mutex<Option<Child>>,
}

impl BackendState {
    pub fn new() -> Self {
        Self::default()
    }
}

/// Locate the bundled backend executable under the app resource dir.
/// Returns None in dev mode (`tauri dev`) where the bundled binary
/// doesn't exist and the developer runs uvicorn separately.
fn locate_backend_binary(app: &AppHandle) -> Option<PathBuf> {
    let resource_dir = app.path().resource_dir().ok()?;
    let candidate = resource_dir
        .join("resources")
        .join("backend")
        .join("eatit-backend");
    if candidate.exists() {
        Some(candidate)
    } else {
        None
    }
}

/// Spawn the backend, parse its stdout for the ready line, and record the
/// chosen port in BackendState. Runs on the Tauri setup thread; blocks up
/// to BACKEND_READY_TIMEOUT_SECS waiting for the ready signal.
pub fn spawn_backend(app: AppHandle) {
    let Some(binary) = locate_backend_binary(&app) else {
        // Dev mode: pretend backend is on 8000 (the `uv run uvicorn` default).
        let state = app.state::<BackendState>();
        if let Ok(mut guard) = state.port.lock() {
            *guard = Some(DEV_FALLBACK_PORT);
        }
        eprintln!(
            "[eatit-backend] bundled binary not found, using dev fallback :{DEV_FALLBACK_PORT}"
        );
        return;
    };

    eprintln!("[eatit-backend] spawning {}", binary.display());
    let spawn_result = Command::new(&binary)
        .env("APP_ENV", "production")
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn();

    let mut child = match spawn_result {
        Ok(child) => child,
        Err(err) => {
            eprintln!("[eatit-backend] spawn failed: {err}");
            return;
        }
    };

    let stdout = match child.stdout.take() {
        Some(s) => s,
        None => {
            eprintln!("[eatit-backend] child had no stdout");
            return;
        }
    };

    // Keep the Child handle so we can kill it on exit. Done before we
    // spawn the stdout reader thread so a fast-failing child doesn't
    // race with this write. The explicit `;` on the if-let forces the
    // lock() result's temporary to drop before `state` goes out of scope.
    {
        let state = app.state::<BackendState>();
        if let Ok(mut guard) = state.child.lock() {
            *guard = Some(child);
        };
    }

    let ready_flag = Arc::new(Mutex::new(false));
    let ready_flag_reader = ready_flag.clone();
    let app_for_reader = app.clone();

    thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            let line = match line {
                Ok(l) => l,
                Err(err) => {
                    eprintln!("[eatit-backend] stdout read error: {err}");
                    break;
                }
            };
            eprintln!("[eatit-backend] {line}");
            if let Some(port) = parse_ready_line(&line) {
                let state = app_for_reader.state::<BackendState>();
                if let Ok(mut guard) = state.port.lock() {
                    *guard = Some(port);
                }
                if let Ok(mut flag) = ready_flag_reader.lock() {
                    *flag = true;
                }
                // Don't break — keep echoing uvicorn lines to the parent
                // terminal for debugging. If the child exits, `lines()`
                // will return None and the loop ends naturally.
            }
        }
    });

    // Block this setup thread until the ready flag is flipped or we time
    // out. We're on a background thread created by Tauri's builder, not
    // the main runtime thread, so blocking briefly here is safe.
    let deadline = Instant::now() + Duration::from_secs(BACKEND_READY_TIMEOUT_SECS);
    loop {
        if let Ok(flag) = ready_flag.lock() {
            if *flag {
                break;
            }
        }
        if Instant::now() >= deadline {
            eprintln!(
                "[eatit-backend] timed out waiting for ready line after {}s",
                BACKEND_READY_TIMEOUT_SECS
            );
            break;
        }
        thread::sleep(Duration::from_millis(100));
    }
}

fn parse_ready_line(line: &str) -> Option<u16> {
    let marker = "EATIT_BACKEND_READY port=";
    let idx = line.find(marker)?;
    let rest = &line[idx + marker.len()..];
    let port_str: String = rest.chars().take_while(|c| c.is_ascii_digit()).collect();
    port_str.parse().ok()
}

/// Send SIGTERM, then SIGKILL after a grace period, to the backend child.
pub fn shutdown_backend(app: &AppHandle) {
    let state = app.state::<BackendState>();
    let mut guard = match state.child.lock() {
        Ok(g) => g,
        Err(_) => return,
    };
    let Some(mut child) = guard.take() else {
        return;
    };

    #[cfg(unix)]
    unsafe {
        let pid = child.id() as libc::pid_t;
        if pid > 0 {
            libc::kill(pid, libc::SIGTERM);
        }
    }

    // Wait up to 2s for a graceful exit, then force kill.
    let deadline = Instant::now() + Duration::from_secs(2);
    loop {
        match child.try_wait() {
            Ok(Some(_)) => return,
            Ok(None) => {
                if Instant::now() >= deadline {
                    break;
                }
                thread::sleep(Duration::from_millis(50));
            }
            Err(_) => return,
        }
    }
    let _ = child.kill();
    let _ = child.wait();
}

#[tauri::command]
pub fn get_backend_port(state: State<'_, BackendState>) -> Result<u16, String> {
    // Copy out of the lock eagerly so we don't carry the guard lifetime
    // into the Result — `ok_or_else` is called on Option<u16> directly,
    // not on a Deref'd reference.
    let port_opt = {
        let guard = state.port.lock().map_err(|e| e.to_string())?;
        *guard
    };
    port_opt.ok_or_else(|| "backend not ready".to_string())
}

#[cfg(test)]
mod tests {
    use super::parse_ready_line;

    #[test]
    fn parse_ready_line_happy_path() {
        assert_eq!(
            parse_ready_line("EATIT_BACKEND_READY port=58732"),
            Some(58732)
        );
    }

    #[test]
    fn parse_ready_line_ignores_surrounding_noise() {
        assert_eq!(
            parse_ready_line("[INFO] EATIT_BACKEND_READY port=1024 extra"),
            Some(1024)
        );
    }

    #[test]
    fn parse_ready_line_returns_none_without_marker() {
        assert_eq!(parse_ready_line("hello world"), None);
    }
}
