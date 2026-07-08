from pathlib import Path

from config import EXPORTS_DIR
from db import now_iso
from exporters.excel_exporter import export_xlsx
from exporters.json_exporter import export_json
from exporters.word_exporter import export_docx
from services.checklist_service import list_checklist, list_missing_policy_items
from services.log_service import write_log
from services.project_service import get_project


def export_project(project_id: int, export_format: str) -> dict:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    project = get_project(project_id)
    checklist = list_checklist(project_id)
    missing = list_missing_policy_items(project_id)
    timestamp = now_iso().replace(":", "-")
    suffix = export_format.lower()
    path = EXPORTS_DIR / f"project-{project_id}-checklist-{timestamp}.{suffix}"
    if suffix == "xlsx":
        export_xlsx(path, checklist, missing)
    elif suffix == "docx":
        export_docx(path, project, checklist, missing)
    elif suffix == "json":
        export_json(path, project, checklist, missing)
    else:
        raise ValueError("不支持的导出格式")
    write_log(project_id, "export", "success", f"导出成功：{path.name}")
    return {"path": str(path), "file_name": path.name}

