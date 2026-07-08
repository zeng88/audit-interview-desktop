import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

import config


def now_iso() -> str:
    """统一时间格式，便于前后端展示和排序。"""
    return datetime.now().isoformat(timespec="seconds")


def get_connection() -> sqlite3.Connection:
    config.ensure_storage_dirs()
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor() -> Iterator[sqlite3.Cursor]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _create_fts(conn: sqlite3.Connection) -> str:
    """优先使用 trigram；旧 SQLite 不支持时降级到 unicode61。"""
    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_text,
                search_text,
                content='chunks',
                content_rowid='id',
                tokenize='trigram'
            )
            """
        )
        return "trigram"
    except sqlite3.OperationalError:
        conn.execute("DROP TABLE IF EXISTS chunks_fts")
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_text,
                search_text,
                content='chunks',
                content_rowid='id',
                tokenize='unicode61'
            )
            """
        )
        return "unicode61"


def init_db() -> None:
    config.ensure_storage_dirs()
    conn = get_connection()
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                company_name TEXT,
                industry TEXT,
                audit_objective TEXT,
                audit_period TEXT,
                focus_areas TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                original_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                parse_status TEXT DEFAULT 'pending',
                parse_error TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS document_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                file_id INTEGER NOT NULL,
                page_number INTEGER,
                sheet_name TEXT,
                section_title TEXT,
                raw_text TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                file_id INTEGER NOT NULL,
                page_number INTEGER,
                sheet_name TEXT,
                section_title TEXT,
                clause_no TEXT,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                search_text TEXT,
                token_count INTEGER,
                embedding_model_config_id INTEGER,
                embedding_dimension INTEGER,
                embedding_status TEXT DEFAULT 'pending',
                embedding_error TEXT,
                embedding_created_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chunk_vectors_fallback (
                chunk_id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                embedding_model_config_id INTEGER,
                dimension INTEGER NOT NULL,
                embedding_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE CASCADE,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS model_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_name TEXT NOT NULL,
                config_type TEXT NOT NULL,
                provider TEXT NOT NULL,
                base_url TEXT NOT NULL,
                api_key TEXT,
                model TEXT NOT NULL,
                temperature REAL DEFAULT 0.2,
                max_tokens INTEGER DEFAULT 4096,
                embedding_dimension INTEGER,
                embedding_batch_size INTEGER DEFAULT 16,
                timeout_seconds INTEGER DEFAULT 120,
                is_default INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                question_id TEXT NOT NULL,
                module TEXT,
                interview_role TEXT,
                interview_question TEXT NOT NULL,
                expected_answer TEXT,
                source_file TEXT,
                source_location TEXT,
                evidence_quote TEXT,
                confidence TEXT,
                follow_up_question TEXT,
                risk_hint TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS missing_policy_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                module TEXT,
                issue TEXT NOT NULL,
                risk TEXT,
                suggested_interview_question TEXT,
                suggested_policy_improvement TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                task_type TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                progress_current INTEGER DEFAULT 0,
                progress_total INTEGER DEFAULT 0,
                progress_percent INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        for column, definition in (
            ("progress_current", "INTEGER DEFAULT 0"),
            ("progress_total", "INTEGER DEFAULT 0"),
            ("progress_percent", "INTEGER DEFAULT 0"),
        ):
            try:
                conn.execute(f"ALTER TABLE task_logs ADD COLUMN {column} {definition}")
            except sqlite3.OperationalError:
                # 兼容旧数据库：字段已存在时忽略。
                pass
        tokenizer = _create_fts(conn)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT OR REPLACE INTO app_meta(key, value) VALUES('fts_tokenizer', ?)",
            (tokenizer,),
        )
        conn.commit()
    finally:
        conn.close()


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def json_dumps(data: object) -> str:
    return json.dumps(data, ensure_ascii=False)


def safe_unlink(path: str | Path) -> None:
    """删除本应用保存的文件；不存在时不报错。"""
    try:
        Path(path).unlink(missing_ok=True)
    except IsADirectoryError:
        pass
