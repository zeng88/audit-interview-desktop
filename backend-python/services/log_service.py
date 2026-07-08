from db import db_cursor, now_iso


def write_log(project_id: int | None, task_type: str, status: str, message: str) -> None:
    """统一写任务日志，前端任务面板直接读取该表。"""
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO task_logs(project_id, task_type, status, message, created_at)
            VALUES(?, ?, ?, ?, ?)
            """,
            (project_id, task_type, status, message, now_iso()),
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

