# 审计访谈清单生成工具

本项目是本地优先的审计访谈清单桌面应用。审计师可以上传制度文件，生成切片和检索索引，再基于制度证据生成访谈问题、制度依据答案、风险提示和制度缺失项。

## 本地运行

```bash
# 安装前端依赖
npm --prefix frontend install

# 安装后端依赖
python3 -m pip install -r backend-python/requirements.txt

# 启动后端
bash scripts/start_backend.sh

# 新开终端启动前端
npm --prefix frontend run dev
```

前端地址：`http://127.0.0.1:5173`  
后端健康检查：`http://127.0.0.1:8765/health`

## 本地降级模式

未配置模型 API Key 时，系统会使用本地确定性向量和模板生成逻辑，方便先跑通上传、解析、切片、检索、生成和导出流程。生产使用时请在页面里配置 OpenAI-compatible 推理模型和向量模型。

## 数据位置

运行时数据保存在 `backend-python/storage`，包括上传文件、SQLite 数据库和导出文件。该目录已加入 `.gitignore`。

