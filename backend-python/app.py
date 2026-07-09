import os
import threading
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import config
from config import APP_VERSION
from db import db_cursor, init_db
from schemas import (
    BuildVectorRequest,
    ChecklistUpdate,
    ChunkRequest,
    ExportRequest,
    GenerateChecklistRequest,
    ModelConfigIn,
    ProjectCreate,
    ProjectUpdate,
    SearchRequest,
)
from services import file_service, model_config_service, project_service
from services.checklist_service import (
    generate_checklist,
    list_checklist,
    list_missing_policy_items,
    update_checklist_item,
)
from services.chunk_service import build_chunks
from services.export_service import export_project
from services.log_service import latest_progress, list_logs, write_log
from services.parse_service import parse_project_files
from services.retrieval_service import hybrid_search
from services.vector_service import build_vector_index


app = FastAPI(title="Audit Interview Desktop Backend", version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def _handle_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": APP_VERSION}


@app.post("/shutdown")
def shutdown(x_shutdown_token: str | None = Header(default=None)) -> dict:
    expected_token = os.environ.get("AUDIT_BACKEND_SHUTDOWN_TOKEN")
    if not expected_token or x_shutdown_token != expected_token:
        raise HTTPException(status_code=403, detail="shutdown token invalid")

    # 先返回响应，再异步退出进程，避免 Tauri 端收到连接中断误判为失败。
    threading.Timer(0.2, lambda: os._exit(0)).start()
    return {"ok": True}


@app.get("/stats")
def stats() -> dict:
    with db_cursor() as cur:
        return {
            "projects": cur.execute("SELECT COUNT(*) AS c FROM projects").fetchone()["c"],
            "files": cur.execute("SELECT COUNT(*) AS c FROM files").fetchone()["c"],
            "chunks": cur.execute("SELECT COUNT(*) AS c FROM chunks").fetchone()["c"],
        }


@app.get("/storage-location")
def storage_location() -> dict:
    # 返回后端实际使用的绝对目录，前端据此展示给用户，避免不同系统路径说明不清。
    return {
        "storage_dir": str(config.STORAGE_DIR),
        "files_dir": str(config.FILES_DIR),
        "exports_dir": str(config.EXPORTS_DIR),
    }


@app.post("/projects")
def create_project(payload: ProjectCreate) -> dict:
    try:
        return project_service.create_project(payload.model_dump())
    except Exception as exc:
        raise _handle_error(exc)


@app.get("/projects")
def list_projects() -> list[dict]:
    return project_service.list_projects()


@app.get("/projects/{project_id}")
def get_project(project_id: int) -> dict:
    try:
        return project_service.get_project(project_id)
    except Exception as exc:
        raise _handle_error(exc)


@app.put("/projects/{project_id}")
def update_project(project_id: int, payload: ProjectUpdate) -> dict:
    try:
        return project_service.update_project(project_id, payload.model_dump())
    except Exception as exc:
        raise _handle_error(exc)


@app.delete("/projects/{project_id}")
def delete_project(project_id: int) -> dict:
    project_service.delete_project(project_id)
    return {"ok": True}


@app.post("/model-configs")
def create_model_config(payload: ModelConfigIn) -> dict:
    try:
        return model_config_service.create_model_config(payload.model_dump())
    except Exception as exc:
        raise _handle_error(exc)


@app.get("/model-configs")
def list_model_configs(config_type: str | None = None) -> list[dict]:
    return model_config_service.list_model_configs(config_type)


@app.put("/model-configs/{config_id}")
def update_model_config(config_id: int, payload: ModelConfigIn) -> dict:
    try:
        return model_config_service.update_model_config(config_id, payload.model_dump())
    except Exception as exc:
        raise _handle_error(exc)


@app.delete("/model-configs/{config_id}")
def delete_model_config(config_id: int) -> dict:
    model_config_service.delete_model_config(config_id)
    return {"ok": True}


@app.post("/model-configs/{config_id}/default")
def set_default_model(config_id: int) -> dict:
    try:
        return model_config_service.set_default(config_id)
    except Exception as exc:
        raise _handle_error(exc)


@app.post("/model-configs/{config_id}/test")
def test_model_config(config_id: int) -> dict:
    return model_config_service.test_model_config(config_id)


@app.post("/projects/{project_id}/files")
def upload_file(project_id: int, file: UploadFile) -> dict:
    try:
        saved = file_service.save_upload(project_id, file)
        write_log(project_id, "upload", "success", f"上传文件：{saved['original_name']}")
        return saved
    except Exception as exc:
        write_log(project_id, "upload", "failed", str(exc))
        raise _handle_error(exc)


@app.get("/projects/{project_id}/files")
def list_files(project_id: int) -> list[dict]:
    return file_service.list_files(project_id)


@app.delete("/projects/{project_id}/files/{file_id}")
def delete_file(project_id: int, file_id: int) -> dict:
    file_service.delete_file(project_id, file_id)
    return {"ok": True}


@app.post("/projects/{project_id}/parse")
def parse_files(project_id: int) -> dict:
    return parse_project_files(project_id)


@app.post("/projects/{project_id}/chunk")
def chunk_files(project_id: int, payload: ChunkRequest) -> dict:
    return build_chunks(project_id, payload.chunk_size, payload.overlap)


@app.post("/projects/{project_id}/build-vector-index")
def build_vectors(project_id: int, payload: BuildVectorRequest) -> dict:
    return build_vector_index(project_id, payload.embedding_model_config_id, payload.batch_size)


@app.post("/projects/{project_id}/search-test")
def search_test(project_id: int, payload: SearchRequest) -> dict:
    results = hybrid_search(project_id, payload.query, payload.embedding_model_config_id, payload.top_k)
    return {"results": results}


@app.post("/projects/{project_id}/generate-checklist")
def generate(project_id: int, payload: GenerateChecklistRequest) -> dict:
    try:
        return generate_checklist(
            project_id,
            payload.chat_model_config_id,
            payload.embedding_model_config_id,
            payload.question_count,
            payload.modules,
        )
    except Exception as exc:
        write_log(project_id, "checklist", "failed", f"生成清单失败：{exc}")
        raise _handle_error(exc)


@app.get("/projects/{project_id}/checklist")
def checklist(project_id: int) -> list[dict]:
    return list_checklist(project_id)


@app.put("/projects/{project_id}/checklist/{item_id}")
def update_checklist(project_id: int, item_id: int, payload: ChecklistUpdate) -> dict:
    return update_checklist_item(project_id, item_id, payload.model_dump(exclude_unset=True))


@app.get("/projects/{project_id}/missing-policy-items")
def missing_policy_items(project_id: int) -> list[dict]:
    return list_missing_policy_items(project_id)


@app.post("/projects/{project_id}/export")
def export(project_id: int, payload: ExportRequest) -> dict:
    try:
        return export_project(project_id, payload.format)
    except Exception as exc:
        write_log(project_id, "export", "failed", str(exc))
        raise _handle_error(exc)


@app.get("/projects/{project_id}/logs")
def logs(project_id: int, limit: int = 100) -> list[dict]:
    return list_logs(project_id, limit)


@app.get("/projects/{project_id}/task-progress")
def task_progress(project_id: int, task_type: str | None = None) -> dict:
    return latest_progress(project_id, task_type) or {}


if __name__ == "__main__":
    # 直接传入 FastAPI 实例，避免 PyInstaller 单文件环境无法重新导入 "app:app"。
    port = int(os.environ.get("AUDIT_BACKEND_PORT", "8765"))
    uvicorn.run(app, host="127.0.0.1", port=port, reload=False)
