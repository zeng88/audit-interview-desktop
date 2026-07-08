# v0.1.0 发布前功能完善设计

## 目标

在 `main` 分支完成 v0.1.0 发布前完善：支持 Markdown 文件、耗时任务进度反馈、模型配置表单修正、应用用户提供的 logo/favicon/桌面图标，并关联远端仓库后发布 `v0.1.0` tag。

## 功能设计

### Markdown 文件支持

上传白名单增加 `.md` 和 `.markdown`。Markdown 使用文本解析器读取 UTF-8/GBK 等常见编码，解析时保留原文内容，并从一级或二级标题提取 `section_title`。切片和检索沿用现有 TXT 流程，保证 Markdown 中的制度条款可以进入 FTS 和向量索引。

### 耗时任务进度反馈

复用 `task_logs` 表，增加进度字段：

- `progress_current`
- `progress_total`
- `progress_percent`

解析文件、生成切片、构建向量索引、生成访谈清单时写入阶段性日志。前端在索引构建和生成清单页显示进度条、最近状态和日志列表；操作按钮执行期间显示“执行中”，避免用户等待时无法判断是否卡住。

### 模型配置修正

推理模型不展示向量维度和 batch size，只展示：

- 配置名称
- Provider
- Base URL
- API Key
- Model
- Temperature
- Max Tokens
- Timeout

向量模型展示：

- 配置名称
- Provider
- Base URL
- API Key
- Model
- 向量维度
- Batch Size
- Timeout

向量维度使用下拉选项：`64`、`384`、`768`、`1024`、`1536`、`2048`、`3072`。其中 `64` 用于本地降级测试，其余为常见 embedding 模型维度。

### Logo 和图标

用户提供的图片复制到：

- `frontend/public/logo.png`
- `frontend/public/favicon.png`
- `src-tauri/icons/icon.png`

后台左侧品牌区域使用 `logo.png`，浏览器 favicon 使用 `favicon.png`，Tauri 打包使用同一图标资源。图标文件保持 PNG 格式，适配网页和 macOS `.app` 构建。

### Git 发布

完成后：

1. 确保代码在 `main` 分支。
2. 添加远端 `origin = https://github.com/zeng88/audit-interview-desktop.git`。
3. 验证后提交。
4. Push `main`。
5. 创建并 push `v0.1.0` tag。

