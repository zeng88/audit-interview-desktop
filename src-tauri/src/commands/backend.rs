use serde::Serialize;

#[derive(Serialize)]
pub struct BackendHealth {
    status: String,
    version: String,
}

#[tauri::command]
pub fn backend_health() -> Result<BackendHealth, String> {
    // Rust 侧只做轻量桥接；业务逻辑集中在 Python 后端，便于本地调试。
    let response = reqwest::blocking::get("http://127.0.0.1:8765/health")
        .map_err(|err| format!("后端未连接：{err}"))?;
    let value: serde_json::Value = response
        .json()
        .map_err(|err| format!("后端响应无法解析：{err}"))?;
    Ok(BackendHealth {
        status: value["status"].as_str().unwrap_or("unknown").to_string(),
        version: value["version"].as_str().unwrap_or("unknown").to_string(),
    })
}

