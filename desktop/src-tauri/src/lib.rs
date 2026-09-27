//! PROSPECT Windows desktop shell (Tauri 2).
//!
//! On start-up it launches the bundled, PyInstaller-packaged FastAPI backend
//! (resources/PROSPECT-Backend/PROSPECT-Backend.exe) hidden and from its own folder, so the backend's
//! relative paths (./prospect.db, alembic.ini) resolve. It allows the desktop window's origin through the
//! backend's CORS check, reloads the page once the backend is listening on 127.0.0.1:8000 (the backend
//! needs a few seconds to start), and terminates the backend process tree when the app exits.
//! Start-up events are logged to %APPDATA%\com.prospect.desktop\startup.log.
use std::fs::OpenOptions;
use std::io::Write;
use std::process::{Child, Command};
use std::sync::Mutex;

use tauri::{Manager, RunEvent};

struct BackendProcess(Mutex<Option<Child>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            let log_path = app
                .path()
                .app_data_dir()
                .expect("failed to get app data directory")
                .join("startup.log");

            if let Some(parent) = log_path.parent() {
                let _ = std::fs::create_dir_all(parent);
            }

            let mut log = OpenOptions::new()
                .create(true)
                .append(true)
                .open(&log_path)
                .ok();

            macro_rules! log_line {
                ($($arg:tt)*) => {
                    if let Some(file) = log.as_mut() {
                        let _ = writeln!(file, $($arg)*);
                    }
                };
            }

            log_line!("=== PROSPECT startup ===");

            let resource_dir = app.path().resource_dir().map_err(|e| {
                log_line!("resource_dir ERROR: {:?}", e);
                e
            })?;
            log_line!("resource_dir = {:?}", resource_dir);

            // Installed layout: <install>\resources\PROSPECT-Backend\PROSPECT-Backend.exe
            let backend_dir = resource_dir.join("resources").join("PROSPECT-Backend");
            let backend_path = backend_dir.join("PROSPECT-Backend.exe");

            log_line!("backend_path = {:?}", backend_path);
            log_line!("backend exists = {}", backend_path.exists());

            if !backend_path.exists() {
                log_line!("ERROR: backend executable does not exist");
                return Ok(());
            }

            let mut cmd = Command::new(&backend_path);
            cmd.current_dir(&backend_dir);
            // Allow the desktop window's origin through the backend's CORS check.
            cmd.env(
                "CORS_ORIGINS",
                "http://tauri.localhost,https://tauri.localhost,http://localhost:5173",
            );

            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;
                const CREATE_NO_WINDOW: u32 = 0x0800_0000;
                cmd.creation_flags(CREATE_NO_WINDOW);
            }

            match cmd.spawn() {
                Ok(child) => {
                    log_line!("backend started successfully, PID = {}", child.id());
                    *app.state::<BackendProcess>().0.lock().unwrap() = Some(child);

                    // The window can load before the backend listens; reload once it is reachable so the
                    // first API calls succeed instead of showing "Cannot reach the PROSPECT server".
                    let handle = app.handle().clone();
                    std::thread::spawn(move || {
                        use std::net::{SocketAddr, TcpStream};
                        use std::time::{Duration, Instant};
                        let addr: SocketAddr = "127.0.0.1:8000".parse().unwrap();
                        let started = Instant::now();
                        while started.elapsed() < Duration::from_secs(60) {
                            if TcpStream::connect_timeout(&addr, Duration::from_millis(500)).is_ok() {
                                if let Some(window) = handle.get_webview_window("main") {
                                    let _ = window.eval("window.location.reload()");
                                }
                                return;
                            }
                            std::thread::sleep(Duration::from_millis(500));
                        }
                    });
                }
                Err(e) => {
                    log_line!("BACKEND START ERROR: {:?}", e);
                }
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app_handle, event| {
        if let RunEvent::Exit = event {
            if let Some(mut child) = app_handle.state::<BackendProcess>().0.lock().unwrap().take() {
                // Kill the whole process tree (PyInstaller launcher + server process).
                #[cfg(windows)]
                {
                    use std::os::windows::process::CommandExt;
                    let _ = Command::new("taskkill")
                        .args(["/PID", &child.id().to_string(), "/T", "/F"])
                        .creation_flags(0x0800_0000)
                        .status();
                }
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    });
}
