mod commands;

use commands::backend::backend_health;
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};
use tauri::Manager;
use tauri_plugin_shell::{process::CommandChild, ShellExt};

struct BackendProcess {
    child: Mutex<Option<CommandChild>>,
    shutdown_token: Option<String>,
}

impl BackendProcess {
    fn terminate(&self) {
        if let Some(token) = &self.shutdown_token {
            // PyInstaller onefile 在 macOS/Windows 可能有子进程，先让真实后端进程主动退出。
            let _ = reqwest::blocking::Client::new()
                .post("http://127.0.0.1:8765/shutdown")
                .header("x-shutdown-token", token)
                .send();
        }

        if let Ok(mut child) = self.child.lock() {
            if let Some(child) = child.take() {
                // 应用退出时同步关闭内置后端，避免端口被残留进程占用。
                let _ = child.kill();
            }
        }
    }
}

impl Drop for BackendProcess {
    fn drop(&mut self) {
        self.terminate();
    }
}

fn backend_is_running() -> bool {
    reqwest::blocking::get("http://127.0.0.1:8765/health")
        .and_then(|response| response.error_for_status())
        .is_ok()
}

fn shutdown_token() -> String {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|value| value.as_nanos())
        .unwrap_or_default();
    format!("{}-{now}", std::process::id())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            if backend_is_running() {
                app.manage(BackendProcess {
                    child: Mutex::new(None),
                    shutdown_token: None,
                });
                return Ok(());
            }

            // 桌面安装包内置 Python 后端 sidecar，普通用户打开应用即可直接使用。
            let token = shutdown_token();
            let (mut receiver, child) = app
                .shell()
                .sidecar("audit-backend")?
                .env("AUDIT_BACKEND_SHUTDOWN_TOKEN", &token)
                .spawn()?;
            tauri::async_runtime::spawn(async move {
                while let Some(event) = receiver.recv().await {
                    eprintln!("backend sidecar event: {event:?}");
                }
            });
            app.manage(BackendProcess {
                child: Mutex::new(Some(child)),
                shutdown_token: Some(token),
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![backend_health])
        .build(tauri::generate_context!())
        .expect("构建 Tauri 应用失败")
        .run(|app_handle, event| match event {
            tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit => {
                app_handle.state::<BackendProcess>().terminate();
            }
            _ => {}
        });
}
