import json

from db import db_cursor


DEFAULT_LOCAL_TEMPLATE_SETTINGS = {
    "default_modules": ["采购管理", "合同管理", "付款管理", "供应商管理", "授权审批", "资料留痕"],
    "question_templates": [
        {
            "interview_role": "流程负责人",
            "question_template": "请说明{module}的主要流程、关键审批节点和职责分工。",
            "keywords": ["流程", "审批", "职责", "分工"],
        },
        {
            "interview_role": "业务经办人",
            "question_template": "请说明{module}相关资料如何提交、复核和归档留痕。",
            "keywords": ["资料", "复核", "归档", "留痕"],
        },
        {
            "interview_role": "部门负责人",
            "question_template": "请说明{module}发生例外事项时的审批和记录要求。",
            "keywords": ["例外", "审批", "记录", "要求"],
        },
        {
            "interview_role": "内控负责人",
            "question_template": "请说明公司如何监督检查{module}制度执行情况。",
            "keywords": ["监督", "检查", "执行", "制度"],
        },
    ],
}


def _normalize_settings(payload: dict) -> dict:
    """校验本地模板配置，保证模板可格式化且关键词为字符串列表。"""
    modules = [str(item).strip() for item in payload.get("default_modules", []) if str(item).strip()]
    templates = []
    for item in payload.get("question_templates", []):
        role = str(item.get("interview_role", "")).strip()
        question_template = str(item.get("question_template", "")).strip()
        if not role or not question_template:
            continue
        if "{module}" not in question_template:
            raise ValueError("本地问题模板必须包含 {module} 占位符")
        keywords = [str(keyword).strip() for keyword in item.get("keywords", []) if str(keyword).strip()]
        templates.append(
            {
                "interview_role": role,
                "question_template": question_template,
                "keywords": keywords,
            }
        )
    if not modules:
        raise ValueError("本地模板默认模块不能为空")
    if not templates:
        raise ValueError("至少需要配置一个本地问题模板")
    return {"default_modules": modules, "question_templates": templates}


def get_local_template_settings() -> dict:
    with db_cursor() as cur:
        row = cur.execute(
            "SELECT value FROM app_meta WHERE key = 'local_template_settings'"
        ).fetchone()
    if not row:
        return DEFAULT_LOCAL_TEMPLATE_SETTINGS
    try:
        return _normalize_settings(json.loads(row["value"]))
    except Exception:
        return DEFAULT_LOCAL_TEMPLATE_SETTINGS


def update_local_template_settings(payload: dict) -> dict:
    settings = _normalize_settings(payload)
    with db_cursor() as cur:
        cur.execute(
            "INSERT OR REPLACE INTO app_meta(key, value) VALUES('local_template_settings', ?)",
            (json.dumps(settings, ensure_ascii=False),),
        )
    return settings
