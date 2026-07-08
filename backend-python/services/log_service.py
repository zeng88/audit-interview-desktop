from db import db_cursor, now_iso


def write_log(
    project_id: int | None,
    task_type: str,
    status: str,
    message: str,
    progress_current: int = 0,
    progress_total: int = 0,
) -> None:
    """统一写任务日志，前端任务面板直接读取该表。"""
    progress_percent = int(progress_current * 100 / progress_total) if progress_total else 0
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO task_logs(
                project_id, task_type, status, message,
                progress_current, progress_total, progress_percent, created_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                task_type,
                status,
                message,
                progress_current,
                progress_total,
                progress_percent,
                now_iso(),
            ),
        )


def list_logs(project_id: int | None = None, limit: int = 100) -> list[dict]:
    with db_cursor() as cur:
        if project_id:
            rows = cur.execute(
                """
                SELECT * FROM task_logs
                WHERE project_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (project_id, limit),
            ).fetchall()
        else:
            rows = cur.execute(
                "SELECT * FROM task_logs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]


def latest_progress(project_id: int, task_type: str | None = None) -> dict | None:
    """返回最近一条进度日志，前端轮询用。"""
    with db_cursor() as cur:
        if task_type:
            row = cur.execute(
                """
                SELECT * FROM task_logs
                WHERE project_id = ? AND task_type = ?
                ORDER BY id DESC LIMIT 1
                """,
                (project_id, task_type),
            ).fetchone()
        else:
            row = cur.execute(
                "SELECT * FROM task_logs WHERE project_id = ? ORDER BY id DESC LIMIT 1",
                (project_id,),
            ).fetchone()
        return dict(row) if row else None
