# 架构说明

系统由 React 前端、Tauri 壳和 Python FastAPI 后端组成。Python 后端负责业务逻辑，SQLite 保存项目、文件、切片、索引、模型配置和生成结果。

检索链路：

1. 文件解析为 `document_pages`。
2. 文本切片写入 `chunks`。
3. 同步写入 `chunks_fts`。
4. 向量写入 `chunk_vectors_fallback`。
5. 查询时执行 FTS 和向量检索，再用 RRF 融合。

当 `sqlite-vec` 不可用时，系统使用 Python 余弦相似度降级，保证本地版本可运行。

