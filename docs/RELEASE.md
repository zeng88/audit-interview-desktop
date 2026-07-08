# 发布说明

推送形如 `v0.1.0` 的 tag 会触发 `.github/workflows/release.yml`。

当前本地机器缺少 Rust 工具链时，无法本机验证 Tauri 编译。安装 Rust 后可执行：

```bash
npm install
npm --prefix frontend install
cargo --version
npm run tauri
```

