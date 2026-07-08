# API 说明

后端默认监听 `127.0.0.1:8765`。

主要接口：

- `GET /health`
- `POST /projects`
- `GET /projects`
- `POST /model-configs`
- `GET /model-configs`
- `POST /projects/{project_id}/files`
- `POST /projects/{project_id}/parse`
- `POST /projects/{project_id}/chunk`
- `POST /projects/{project_id}/build-vector-index`
- `POST /projects/{project_id}/search-test`
- `POST /projects/{project_id}/generate-checklist`
- `GET /projects/{project_id}/checklist`
- `POST /projects/{project_id}/export`

