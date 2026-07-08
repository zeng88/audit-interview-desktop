import shutil
from pathlib import Path

from fastapi import UploadFile

from config import FILES_DIR
from db import db_cursor, now_iso, safe_unlink


SUPPORTED_TYPES = {".pdf", ".docx", ".xlsx", ".txt", ".csv", ".md", ".markdown"}


def _project_file_dir(project_id: int) -> Path:
    path = FILES_DIR / str(project_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_name(file_name: str) -> str:
    # 保留中文文件名，同时去掉路径分隔符，防止越权写文件。
    return Path(file_name).name.replace("/", "_").replace("\\", "_")


def save_upload(project_id: int, upload: UploadFile) -> dict:
    original_name = _safe_name(upload.filename or "未命名文件")
    suffix = Path(original_name).suffix.lower()
    if suffix not in SUPPORTED_TYPES:
        raise ValueError(f"不支持的文件类型：{suffix}")
    target_dir = _project_file_dir(project_id)
    target_path = target_dir / f"{now_iso().replace(':', '-')}-{original_name}"
    with target_path.open("wb") as out:
        shutil.copyfileobj(upload.file, out)
    size = target_path.stat().st_size
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO files(project_id, original_name, stored_path, file_type, file_size, parse_status, created_at)
            VALUES(?, ?, ?, ?, ?, 'pending', ?)
            """,
            (project_id, original_name, str(target_path), suffix.lstrip("."), size, now_iso()),
        )
        file_id = cur.lastrowid
    return get_file(file_id)


def list_files(project_id: int) -> list[dict]:
    with db_cursor() as cur:
        rows = cur.execute(
            "SELECT * FROM files WHERE project_id = ? ORDER BY id DESC", (project_id,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_file(file_id: int) -> dict:
    with db_cursor() as cur:
        row = cur.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
        if not row:
            raise ValueError("文件不存在")
        return dict(row)


def delete_file(project_id: int, file_id: int) -> None:
    with db_cursor() as cur:
        row = cur.execute(
            "SELECT stored_path FROM files WHERE id = ? AND project_id = ?",
            (file_id, project_id),
        ).fetchone()
        if row:
            safe_unlink(row["stored_path"])
        cur.execute("DELETE FROM files WHERE id = ? AND project_id = ?", (file_id, project_id))


def update_parse_status(file_id: int, status: str, error: str | None = None) -> None:
    with db_cursor() as cur:
        cur.execute(
            "UPDATE files SET parse_status = ?, parse_error = ? WHERE id = ?",
            (status, error, file_id),
        )
