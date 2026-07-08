# 本地验证记录

验证日期：2026-07-08

## 已通过

```bash
python3 -m pytest backend-python/tests/test_core_flow.py -q
```

结果：`1 passed`。覆盖项目创建、模型配置、本地 TXT 上传、解析、切片、向量索引、混合检索、清单生成、JSON/Excel/Word 导出。

```bash
python3 -m py_compile app.py config.py db.py schemas.py services/*.py parsers/*.py exporters/*.py prompts/*.py
```

结果：通过。

```bash
npm run build
```

执行目录：`frontend`。结果：TypeScript 和 Vite 构建通过。

```bash
curl -s http://127.0.0.1:8765/health
```

结果：

```json
{"status":"ok","version":"0.1.0"}
```

```bash
curl -I -s http://127.0.0.1:5173/
```

结果：HTTP 200。

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy /Users/zeng88/.cargo/bin/cargo check
```

执行目录：`src-tauri`。结果：Tauri Rust 层编译检查通过。

```bash
npm run tauri:build
```

结果：macOS `.app` 构建成功。

```text
/Users/zeng88/Documents/Git/audit-interview-desktop/src-tauri/target/release/bundle/macos/审计访谈清单生成工具.app
```

曾执行默认 `tauri build`，应用二进制和 `.app` 已生成，但 DMG 打包脚本在当前环境失败。因此本地脚本改为 `tauri build --bundles app`，优先保证桌面应用本地可运行。

## 当前运行地址

- 后端：`http://127.0.0.1:8765`
- 前端：`http://127.0.0.1:5173`

## 说明

当前环境首次缺少 Rust，已通过 rustup 安装 minimal 工具链后完成 Tauri `cargo check`。Cargo 下载依赖时需要清理不可用的本地代理环境变量。
