from db import db_cursor, now_iso


def create_project(payload: dict) -> dict:
    now = now_iso()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO projects(
                project_name, company_name, industry, audit_objective,
                audit_period, focus_areas, created_at, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["project_name"],
                payload.get("company_name", ""),
                payload.get("industry", ""),
                payload.get("audit_objective", ""),
                payload.get("audit_period", ""),
                payload.get("focus_areas", ""),
                now,
                now,
            ),
        )
        row = cur.execute("SELECT * FROM projects WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)


def list_projects() -> list[dict]:
    with db_cursor() as cur:
        rows = cur.execute(
            """
            SELECT
                p.*,
                (SELECT COUNT(*) FROM files f WHERE f.project_id = p.id) AS file_count,
                (SELECT COUNT(*) FROM checklist_items c WHERE c.project_id = p.id) AS checklist_count
            FROM projects p
            ORDER BY p.updated_at DESC, p.id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_project(project_id: int) -> dict:
    with db_cursor() as cur:
        row = cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if not row:
            raise ValueError("项目不存在")
        return dict(row)


def update_project(project_id: int, payload: dict) -> dict:
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE projects
            SET project_name = ?, company_name = ?, industry = ?, audit_objective = ?,
                audit_period = ?, focus_areas = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload["project_name"],
                payload.get("company_name", ""),
                payload.get("industry", ""),
                payload.get("audit_objective", ""),
                payload.get("audit_period", ""),
                payload.get("focus_areas", ""),
                now_iso(),
                project_id,
            ),
        )
    return get_project(project_id)


def delete_project(project_id: int) -> None:
    # 文件实体由 file_service 删除；这里依赖外键清理数据库记录。
    with db_cursor() as cur:
        cur.execute("DELETE FROM projects WHERE id = ?", (project_id,))
