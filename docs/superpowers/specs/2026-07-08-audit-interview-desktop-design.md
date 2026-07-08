# 审计访谈清单桌面应用设计说明

## 目标

在 `/Users/zeng88/Documents/Git/audit-interview-desktop` 实现一个本地可运行的桌面应用版本。应用面向审计师，支持上传制度文件，解析文本，构建全文与向量索引，生成审计访谈问题，并基于制度片段生成可追溯的制度依据答案，最终导出 Excel、Word 和 JSON。

## 范围边界

第一版目标是本地可运行 MVP，必须打通主链路：

1. 项目管理。
2. 模型配置。
3. PDF、DOCX、XLSX、TXT、CSV 上传与解析。
4. 文本切片。
5. SQLite FTS5 全文检索。
6. sqlite-vec 向量检索，若本机扩展不可用，则提供同接口的 SQLite BLOB 余弦检索降级实现，保证本地功能可用。
7. RRF 混合检索。
8. OpenAI-compatible 推理模型和向量模型调用。
9. 访谈问题生成、制度依据答案生成、制度缺失识别。
10. 结果查看、编辑、筛选。
11. Excel、Word、JSON 导出。
12. Python 后端、前端、Tauri 壳本地启动。

不承诺在第一轮本地验证中完成三平台安装包的真实构建结果，但会提供 GitHub Actions 和打包配置文件。

## 技术架构

整体采用计划书指定架构：

```text
Tauri v2 桌面壳
  -> React + TypeScript + Vite 前端
  -> Rust Tauri Command 桥接
  -> Python FastAPI 本地后端
  -> SQLite 本地数据库
  -> FTS5 + sqlite-vec/降级向量检索
  -> OpenAI-compatible 模型服务
```

Python 后端是业务核心，负责数据库、文件解析、切片、检索、模型调用和导出。Tauri 负责启动本地后端、提供桌面壳和必要的本地文件能力。前端通过统一 API 层访问后端。

## UI 与交互原型

采用“审计工作台式布局”。

1. 左侧固定导航：项目、文件、模型配置、索引构建、生成清单、结果查看。
2. 顶部状态栏：当前项目、后端连接状态、最近任务状态。
3. 主区域按流程分页面推进，每页只处理一个核心任务。
4. 结果页使用高密度表格，点击行后打开右侧证据抽屉。
5. 视觉风格为浅色背景、蓝灰主色、绿色/橙色/红色状态色，卡片圆角不超过 8px。

页面职责：

| 页面 | 主要能力 |
| --- | --- |
| ProjectList | 查看项目列表、新建项目、删除项目、进入项目 |
| ProjectCreate | 创建审计项目，录入公司、行业、审计目标、期间、关注模块 |
| FileUpload | 拖拽或选择文件、查看解析状态、删除文件、重新解析 |
| ModelSettings | 维护推理模型和向量模型配置，测试连接，设为默认 |
| IndexBuild | 解析文件、生成切片、构建向量索引、检索测试 |
| GenerateChecklist | 选择模型和模块，设置问题数量，启动生成并查看任务日志 |
| ResultViewer | 表格查看、筛选、编辑、查看证据抽屉、导出 |

## 数据设计

SQLite 数据库存放在运行时 storage 目录，核心表包括：

1. `projects`：项目基础信息。
2. `files`：上传文件记录和解析状态。
3. `document_pages`：解析后的页、Sheet 或章节文本。
4. `chunks`：切片文本和来源位置。
5. `chunks_fts`：FTS5 全文索引。
6. `chunk_vectors`：sqlite-vec 向量表，或降级实现中的向量 BLOB 表。
7. `model_configs`：推理模型和向量模型配置。
8. `checklist_items`：访谈清单结果。
9. `missing_policy_items`：制度缺失项。
10. `task_logs`：任务日志和错误日志。

数据库启动时启用 WAL 和 foreign_keys。

## 后端模块

后端按职责拆分：

| 模块 | 职责 |
| --- | --- |
| `db.py` | 初始化 SQLite 和连接管理 |
| `schemas.py` | Pydantic 请求响应模型 |
| `project_service.py` | 项目 CRUD |
| `file_service.py` | 文件保存、删除、状态维护 |
| `parse_service.py` | 调用不同解析器并写入 document_pages |
| `chunk_service.py` | 文本切片并写入 chunks、chunks_fts |
| `embedding_service.py` | 调用 OpenAI-compatible embeddings API |
| `fts_service.py` | FTS5 查询和 BM25 排序 |
| `vector_service.py` | sqlite-vec 初始化、写入、检索和降级检索 |
| `retrieval_service.py` | FTS + 向量 + RRF 混合检索 |
| `llm_service.py` | Chat Completions 调用、JSON 清洗和错误处理 |
| `audit_question_service.py` | 生成候选访谈问题 |
| `evidence_service.py` | 基于证据生成答案并识别无依据 |
| `checklist_service.py` | 编排完整生成流程 |
| `export_service.py` | 导出 xlsx、docx、json |

所有代码文件使用 UTF-8 编码。新增业务代码保留必要中文注释，用于说明非显然逻辑、业务约束和降级策略。

## 反幻觉策略

1. 证据答案 Prompt 明确只能依据检索片段回答。
2. 未找到明确依据时必须输出“未在已提供制度片段中找到明确依据。”。
3. 每条结果保存来源文件、页码或 Sheet、章节、原文摘录和置信度。
4. 模型返回 JSON 会做结构校验，失败时写入 task_logs。
5. 单个问题失败不终止整个清单生成任务。

## 错误处理

1. 文件解析失败：记录 `files.parse_error`，写 task_logs，前端展示错误原因。
2. 向量化失败：记录到 chunk 的 embedding 状态和错误字段，继续处理其他 chunk。
3. 模型调用失败：返回明确错误并写 task_logs。
4. 导出失败：返回错误消息，避免生成损坏文件。
5. sqlite-vec 不可用：自动降级到内置余弦相似度检索，前端显示检索模式。

## 验收标准

本地验收以 macOS 当前机器为准：

1. Python 后端可启动，`GET /health` 返回 `ok`。
2. 前端可启动并连接后端。
3. 可新建项目、配置模型、上传并解析制度文件。
4. 可生成 chunk 和 FTS5 索引。
5. 可构建向量索引或使用降级向量检索。
6. 检索测试返回来源文件、位置、片段和得分。
7. 可生成访谈清单，结果包含问题、答案、来源、摘录、置信度、追问和风险提示。
8. 无依据问题会被明确标记并进入制度缺失列表。
9. 可导出 Excel、Word 和 JSON，文件能正常打开。
10. Tauri 本地开发模式可启动桌面应用。

