import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock

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
    assert all(item["expected_answer"] for item in checklist)
    assert all(item["generation_source"] == "local_template" for item in checklist)
    assert all("本地" in item["generation_note"] for item in checklist)
    assert any(log["status"] == "warning" and "模型连接失败" in log["message"] for log in logs)


def test_generate_checklist_marks_configured_model_when_model_succeeds(monkeypatch, tmp_path: Path) -> None:
    config.LEGACY_STORAGE_DIR = tmp_path / "legacy-storage"
    _set_storage_paths(tmp_path / "storage")
    init_db()
    client = TestClient(app)

    def fake_question_json(*_args, **_kwargs):
        return {
            "questions": [
                {
                    "question_id": "Q001",
                    "module": "采购管理",
                    "interview_role": "采购负责人",
                    "interview_question": "请说明采购审批如何执行。",
                    "search_keywords": ["采购", "审批"],
                }
            ]
        }

    def fake_answer_json(*_args, **_kwargs):
        return {
            "expected_answer": "配置模型生成的答案",
            "source_file": "模型依据",
            "source_location": "模型输出",
            "evidence_quote": "模型引用",
            "confidence": "中",
            "follow_up_question": "配置模型追问",
            "risk_hint": "配置模型风险提示",
            "is_missing_policy": False,
            "missing_policy_issue": "",
        }

    monkeypatch.setattr("services.audit_question_service.chat_json", fake_question_json)
    monkeypatch.setattr("services.evidence_service.chat_json", fake_answer_json)

    project = client.post("/projects", json={"project_name": "配置模型项目"}).json()
    chat_config = client.post(
        "/model-configs",
        json={
            "config_name": "可用推理",
            "config_type": "chat",
            "provider": "openai-compatible",
            "base_url": "http://model.test/v1",
            "api_key": "test-key",
            "model": "good-chat",
            "is_default": 1,
        },
    ).json()

    result = client.post(
        f"/projects/{project['id']}/generate-checklist",
        json={"chat_model_config_id": chat_config["id"], "question_count": 1, "modules": ["采购管理"]},
    ).json()
    checklist = client.get(f"/projects/{project['id']}/checklist").json()

    assert result["created_count"] == 1
    assert checklist[0]["generation_source"] == "configured_model"
    assert "可用推理" in checklist[0]["generation_note"]


def test_generate_checklist_does_not_pad_duplicate_local_questions(monkeypatch, tmp_path: Path) -> None:
    config.LEGACY_STORAGE_DIR = tmp_path / "legacy-storage"
    _set_storage_paths(tmp_path / "storage")
    init_db()
    client = TestClient(app)

    def broken_chat_json(*_args, **_kwargs):
        raise RuntimeError("模型连接失败")

    monkeypatch.setattr("services.audit_question_service.chat_json", broken_chat_json)

    project = client.post("/projects", json={"project_name": "不重复问题项目"}).json()
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

    result = client.post(
        f"/projects/{project['id']}/generate-checklist",
        json={"chat_model_config_id": chat_config["id"], "question_count": 20, "modules": ["采购管理"]},
    ).json()
    checklist = client.get(f"/projects/{project['id']}/checklist").json()
    questions = [item["interview_question"] for item in checklist]
    logs = client.get(f"/projects/{project['id']}/logs").json()

    assert result["created_count"] == 4
    assert len(questions) == len(set(questions))
    assert any("不会重复凑数" in log["message"] for log in logs)


def test_vector_index_caps_remote_batch_size(monkeypatch, tmp_path: Path) -> None:
    config.LEGACY_STORAGE_DIR = tmp_path / "legacy-storage"
    _set_storage_paths(tmp_path / "storage")
    init_db()

    from db import db_cursor
    from services.vector_service import build_vector_index

    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO projects(project_name, created_at, updated_at) VALUES('向量批量项目', '2026-07-09T10:00:00', '2026-07-09T10:00:00')"
        )
        project_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO files(project_id, original_name, stored_path, file_type, file_size, created_at)
            VALUES(?, '制度.md', '/tmp/制度.md', 'md', 1, '2026-07-09T10:00:00')
            """,
            (project_id,),
        )
        file_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO model_configs(config_name, config_type, provider, base_url, api_key, model, embedding_dimension, embedding_batch_size, timeout_seconds, is_default, created_at, updated_at)
            VALUES('远程向量', 'embedding', 'openai-compatible', 'https://example.test/v1', 'key', 'embedding-model', 4, 16, 30, 1, '2026-07-09T10:00:00', '2026-07-09T10:00:00')
            """
        )
        model_id = cur.lastrowid
        for index in range(12):
            cur.execute(
                """
                INSERT INTO chunks(project_id, file_id, chunk_index, chunk_text, created_at)
                VALUES(?, ?, ?, ?, '2026-07-09T10:00:00')
                """,
                (project_id, file_id, index, f"切片 {index}"),
            )

    batch_sizes: list[int] = []

    def fake_embed_texts(texts, _config, dimension):
        batch_sizes.append(len(texts))
        return [[0.1] * int(dimension) for _ in texts]

    monkeypatch.setattr("services.vector_service.embed_texts", fake_embed_texts)
    result = build_vector_index(project_id, model_id, batch_size=16)

    assert result["success_count"] == 12
    assert max(batch_sizes) == 10


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


def test_chat_json_omits_response_format_for_openrouter(monkeypatch) -> None:
    """OpenRouter 不支持 OpenAI 的 response_format，应避免在 payload 中发送。"""
    from services.llm_service import chat_json

    captured: dict = {}

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["payload"] = json
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "choices": [{"message": {"content": '{"ok": true}'}}]
            }
            return resp

    monkeypatch.setattr("services.llm_service.httpx.Client", _FakeClient)
    openrouter_config = {
        "provider": "openai-compatible",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "sk-test",
        "model": "anthropic/claude-3.5-sonnet",
    }
    result = chat_json("hello", openrouter_config)

    assert result == {"ok": True}
    assert "response_format" not in captured["payload"]
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"


def test_chat_json_keeps_response_format_for_openai_official(monkeypatch) -> None:
    """OpenAI 官方端点原生支持 response_format，应保留以约束 JSON 输出。"""
    from services.llm_service import chat_json

    captured: dict = {}

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["payload"] = json
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "choices": [{"message": {"content": '{"ok": true}'}}]
            }
            return resp

    monkeypatch.setattr("services.llm_service.httpx.Client", _FakeClient)
    openai_config = {
        "provider": "openai-compatible",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-test",
        "model": "gpt-4o-mini",
    }
    chat_json("hello", openai_config)

    assert captured["payload"].get("response_format") == {"type": "json_object"}


def test_chat_json_surfaces_upstream_error_body(monkeypatch) -> None:
    """当 OpenRouter 返回 4xx 时，应把上游错误体透传到异常文本中便于排查。"""
    from services.llm_service import chat_json

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, json=None):
            resp = MagicMock()
            resp.status_code = 400
            resp.text = '{"error":{"message":"Provider returned error","code":400}}'
            return resp

    monkeypatch.setattr("services.llm_service.httpx.Client", _FakeClient)
    openrouter_config = {
        "provider": "openai-compatible",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "sk-test",
        "model": "anthropic/claude-3.5-sonnet",
    }
    try:
        chat_json("hello", openrouter_config)
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("chat_json 应该抛出 RuntimeError")

    assert "400" in message
    assert "Provider returned error" in message
    assert "openai-compatible" in message
