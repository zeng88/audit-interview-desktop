import json
from pathlib import Path


def export_json(path: Path, project: dict, checklist: list[dict], missing: list[dict]) -> None:
    data = {"project": project, "checklist": checklist, "missing_policy_items": missing}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

