import os
import sqlite3
import sys
from pathlib import Path

os.environ["AUDIT_BACKEND_PORT"] = "8765"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import config
from app import app
from db import init_db


def _set_storage_paths(storage_dir: Path) -> None:
    """测试中切换后端存储目录，避免污染真实用户数据。"""
    config.STORAGE_DIR = storage_dir
    config.FILES_DIR = config.STORAGE_DIR / "files"
    config.EXPORTS_DIR = config.STORAGE_DIR / "exports"
    config.LOGS_DIR = config.STORAGE_DIR / "logs"
    config.DB_PATH = config.STORAGE_DIR / "audit.db"


def test_init_db_migrates_legacy_storage_when_current_has_no_projects(tmp_path: Path) -> None:
    legacy_storage = tmp_path / "legacy-storage"
    current_storage = tmp_path / "current-storage"

    config.LEGACY_STORAGE_DIR = legacy_storage
    _set_storage_paths(legacy_storage)
    init_db()

    old_file = legacy_storage / "files" / "1" / "制度.md"
    old_file.parent.mkdir(parents=True, exist_ok=True)
    old_file.write_text("# 制度", encoding="utf-8")
    with sqlite3.connect(config.DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO projects(project_name, company_name, industry, audit_objective, audit_period, focus_areas, created_at, updated_at)
            VALUES('旧项目', '', '', '', '', '', '2026-07-09T10:00:00', '2026-07-09T10:00:00')
            """
        )
        conn.execute(
            """
            INSERT INTO files(project_id, original_name, stored_path, file_type, file_size, parse_status, created_at)
            VALUES(1, '制度.md', ?, 'md', 6, 'pending', '2026-07-09T10:00:00')
            """,
            (str(old_file),),
        )

    _set_storage_paths(current_storage)
    init_db()

    with sqlite3.connect(config.DB_PATH) as conn:
        project_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        stored_path = conn.execute("SELECT stored_path FROM files LIMIT 1").fetchone()[0]

    assert project_count == 1
    assert stored_path.startswith(str(current_storage))
    assert Path(stored_path).exists()


def test_generate_checklist_falls_back_when_chat_model_fails(monkeypatch, tmp_path: Path) -> None:
    config.LEGACY_STORAGE_DIR = tmp_path / "legacy-storage"
    _set_storage_paths(tmp_path / "storage")
    init_db()
    client = TestClient(app)

    def broken_chat_json(*_args, **_kwargs):
        raise RuntimeError("模型连接失败")

    monkeypatch.setattr("services.audit_question_service.chat_json", broken_chat_json)
    monkeypatch.setattr("services.evidence_service.chat_json", broken_chat_json)

    project = client.post("/projects", json={"project_name": "异常降级项目"}).json()
    chat_config = client.post(
        "/model-configs",
        json={
            "config_name": "不可用推理",
            "config_type": "chat",
            "provider": "openai-compatible",
            "base_url": "http://127.0.0.1:9/v1",
            "api_key": "test-key",
            "model": "bad-chat",
            "is_default": 1,
        },
    ).json()
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

    result = client.post(
        f"/projects/{project['id']}/generate-checklist",
        json={
            "chat_model_config_id": chat_config["id"],
            "embedding_model_config_id": embedding_config["id"],
            "question_count": 2,
            "modules": ["采购管理"],
        },
    ).json()

    logs = client.get(f"/projects/{project['id']}/logs").json()
    checklist = client.get(f"/projects/{project['id']}/checklist").json()

    assert result["created_count"] == 2
    assert len(checklist) == 2
    assert any(log["status"] == "running" and "本地模板生成访谈问题" in log["message"] for log in logs)


def test_core_local_flow(tmp_path: Path) -> None:
    # 测试使用临时 storage，避免污染用户真实运行数据。
    config.LEGACY_STORAGE_DIR = tmp_path / "legacy-storage"
    _set_storage_paths(tmp_path / "storage")
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
    storage_location = client.get("/storage-location").json()
    assert storage_location["files_dir"] == str(config.FILES_DIR)

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
