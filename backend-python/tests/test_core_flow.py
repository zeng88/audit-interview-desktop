import os
import sys
from pathlib import Path

os.environ["AUDIT_BACKEND_PORT"] = "8765"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import config
from app import app
from db import init_db


def test_core_local_flow(tmp_path: Path) -> None:
    # 测试使用临时 storage，避免污染用户真实运行数据。
    config.STORAGE_DIR = tmp_path / "storage"
    config.FILES_DIR = config.STORAGE_DIR / "files"
    config.EXPORTS_DIR = config.STORAGE_DIR / "exports"
    config.LOGS_DIR = config.STORAGE_DIR / "logs"
    config.DB_PATH = config.STORAGE_DIR / "audit.db"
    init_db()
    client = TestClient(app)

    project = client.post(
        "/projects",
        json={
            "project_name": "测试项目",
            "company_name": "测试公司",
            "industry": "制造业",
            "audit_objective": "采购管理审计",
            "audit_period": "2026年",
            "focus_areas": "采购管理,合同管理",
        },
    ).json()
    project_id = project["id"]

    embedding_config = client.post(
        "/model-configs",
        json={
            "config_name": "本地向量",
            "config_type": "embedding",
            "provider": "local",
            "base_url": "",
            "api_key": "",
            "model": "local-hash",
            "embedding_dimension": 64,
            "is_default": 1,
        },
    ).json()

    chat_config = client.post(
        "/model-configs",
        json={
            "config_name": "本地推理",
            "config_type": "chat",
            "provider": "local",
            "base_url": "",
            "api_key": "",
            "model": "local-fallback",
            "is_default": 1,
        },
    ).json()

    content = "# 采购管理制度\n采购需求由使用部门提出，经部门负责人审批后提交采购部门。采购资料应归档留痕。"
    response = client.post(
        f"/projects/{project_id}/files",
        files={"file": ("采购管理制度.md", content.encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 200

    assert client.post(f"/projects/{project_id}/parse").json()["parsed_count"] == 1
    parse_progress = client.get(f"/projects/{project_id}/task-progress?task_type=parse").json()
    assert parse_progress["progress_percent"] == 100
    assert client.post(f"/projects/{project_id}/chunk", json={"chunk_size": 100, "overlap": 10}).json()["chunk_count"] >= 1
    chunk_progress = client.get(f"/projects/{project_id}/task-progress?task_type=chunk").json()
    assert "progress_current" in chunk_progress
    assert client.post(
        f"/projects/{project_id}/build-vector-index",
        json={"embedding_model_config_id": embedding_config["id"], "batch_size": 4},
    ).json()["success_count"] >= 1
    embedding_progress = client.get(f"/projects/{project_id}/task-progress?task_type=embedding").json()
    assert embedding_progress["progress_percent"] == 100

    search = client.post(
        f"/projects/{project_id}/search-test",
        json={"query": "采购需求审批", "embedding_model_config_id": embedding_config["id"], "top_k": 5},
    ).json()
    assert search["results"]

    generated = client.post(
        f"/projects/{project_id}/generate-checklist",
        json={
            "chat_model_config_id": chat_config["id"],
            "embedding_model_config_id": embedding_config["id"],
            "question_count": 3,
            "modules": ["采购管理"],
        },
    ).json()
    assert generated["created_count"] == 3
    assert client.get(f"/projects/{project_id}/checklist").json()

    for export_format in ("json", "xlsx", "docx"):
        exported = client.post(f"/projects/{project_id}/export", json={"format": export_format}).json()
        assert Path(exported["path"]).exists()
