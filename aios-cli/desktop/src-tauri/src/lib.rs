use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager, Emitter,
};
use std::{
    fs::OpenOptions,
    net::{SocketAddr, TcpStream},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::Mutex,
    thread,
    time::Duration,
};

#[derive(Default)]
struct CoreProcess(Mutex<Option<Child>>);

#[derive(Default)]
struct OverlayProcess(Mutex<Option<Child>>);

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|p| p.parent())
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."))
}

fn core_is_running() -> bool {
    let addr: SocketAddr = match "127.0.0.1:8765".parse() {
        Ok(addr) => addr,
        Err(_) => return false,
    };
    TcpStream::connect_timeout(&addr, Duration::from_millis(250)).is_ok()
}

/// Общий хелпер spawn'а Python-модуля как child-процесса.
/// Используется и для ядра (aios_core), и для оверлей-демона (aios_overlay).
fn spawn_python_module(
    module: &str,
    work_dir: PathBuf,
    pythonpath: PathBuf,
    log_name: &str,
) -> std::io::Result<Child> {
    let root = repo_root();
    let log_dir = root.join("logs");
    let _ = std::fs::create_dir_all(&log_dir);
    let stderr_path = log_dir.join(format!("{}.log", log_name));

    let stderr_file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&stderr_path)?;

    let python_exe = if cfg!(windows) {
        root.join(".venv").join("Scripts").join("python.exe")
    } else {
        root.join(".venv").join("bin").join("python")
    };
    let mut cmd = if python_exe.exists() {
        Command::new(python_exe)
    } else {
        Command::new("python")
    };
    cmd.arg("-m")
        .arg(module)
        .current_dir(&work_dir)
        .env("PYTHONPATH", &pythonpath)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(stderr_file);

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    cmd.spawn()
}

fn start_core(app: &tauri::App) {
    if core_is_running() {
        return;
    }

    let root = repo_root();
    let core_dir = root;
    let core_src = core_dir.join("src");
    if !core_src.exists() {
        log::warn!("AIOS src not found at {}", core_src.display());
        return;
    }

    match spawn_python_module("aios.desktop", core_dir, core_src, "aios-core") {
        Ok(child) => {
            if let Some(state) = app.try_state::<CoreProcess>() {
                *state.0.lock().expect("core process lock") = Some(child);
            }
            log::info!("AIOS CLI core started from desktop shell");
        }
        Err(err) => log::error!("Failed to start AIOS core: {err}"),
    }
}

fn stop_core(app_handle: &tauri::AppHandle) {
    if let Some(state) = app_handle.try_state::<CoreProcess>() {
        if let Some(mut child) = state.0.lock().expect("core process lock").take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

/// Запуск оверлей-демона в фоне (глобальные хоткеи + Perplexity-style overlay).
/// Ждёт готовности ядра до 10 секунд, затем запускает процесс.
fn start_overlay(app: &tauri::App) {
    let root = repo_root();
    let overlay_dir = root.join("modules").join("overlay");
    if !overlay_dir.exists() {
        log::warn!("AIOS overlay module not found at {}", overlay_dir.display());
        return;
    }

    let overlay_dir2 = overlay_dir.clone();
    let handle = app.handle().clone();

    thread::spawn(move || {
        // Ждём готовности ядра (до 10 с)
        for i in 0..40 {
            let addr: SocketAddr = match "127.0.0.1:8765".parse() {
                Ok(a) => a,
                Err(_) => return,
            };
            if TcpStream::connect_timeout(&addr, Duration::from_millis(250)).is_ok() {
                break;
            }
            if i == 39 {
                log::warn!("Core not ready after 10s — overlay not started");
                return;
            }
            thread::sleep(Duration::from_millis(250));
        }

        match spawn_python_module("aios_overlay", overlay_dir2, overlay_dir, "aios-overlay") {
            Ok(child) => {
                if let Some(state) = handle.try_state::<OverlayProcess>() {
                    *state.0.lock().expect("overlay process lock") = Some(child);
                }
                log::info!("AIOS overlay daemon started");
            }
            Err(err) => log::error!("Failed to start AIOS overlay: {err}"),
        }
    });
}

fn stop_overlay(app_handle: &tauri::AppHandle) {
    if let Some(state) = app_handle.try_state::<OverlayProcess>() {
        if let Some(mut child) = state.0.lock().expect("overlay process lock").take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

#[tauri::command]
fn exit_app(app_handle: tauri::AppHandle) {
    stop_overlay(&app_handle);
    stop_core(&app_handle);
    app_handle.exit(0);
}

#[tauri::command]
fn minimize_to_tray(app_handle: tauri::AppHandle) {
    if let Some(window) = app_handle.get_webview_window("main") {
        let _ = window.hide();
    }
}

fn create_tray(app: &tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    let show = MenuItem::with_id(app, "show", "Show", true, None::<&str>)?;
    let hide = MenuItem::with_id(app, "hide", "Hide", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&show, &hide, &quit])?;

    let _tray = TrayIconBuilder::new()
        .menu(&menu)
        .tooltip("AIOS — Personal AI Agent")
        .on_menu_event(|app, event| match event.id.as_ref() {
            "show" => {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
            "hide" => {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.hide();
                }
            }
            "quit" => {
                stop_overlay(app);
                stop_core(app);
                app.exit(0);
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                if let Some(window) = tray.app_handle().get_webview_window("main") {
                    if window.is_visible().unwrap_or(false) {
                        let _ = window.hide();
                    } else {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
            }
        })
        .build(app)?;

    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec!["--silent"]),
        ))
        .invoke_handler(tauri::generate_handler![exit_app, minimize_to_tray])
        .setup(|app| {
            app.manage(CoreProcess::default());
            app.manage(OverlayProcess::default());
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            create_tray(app)?;
            start_core(app);
            start_overlay(app);

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                // Emit event to frontend to show the exit modal
                let _ = window.emit("close-requested", ());
                api.prevent_close();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
