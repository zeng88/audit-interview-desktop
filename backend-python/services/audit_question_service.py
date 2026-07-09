from prompts.question_generation_prompt import build_question_prompt
from services.llm_service import chat_json
from services.local_template_service import get_local_template_settings
from services.log_service import write_log
from services.model_config_service import get_model_config
from services.project_service import get_project


def _question_key(question: dict) -> tuple[str, str, str]:
    """用核心业务字段判断重复问题，避免靠编号凑数量。"""
    return (
        str(question.get("module") or "").strip(),
        str(question.get("interview_role") or "").strip(),
        str(question.get("interview_question") or "").strip(),
    )


def _dedupe_and_limit_questions(project_id: int, questions: list[dict], requested_count: int, source_label: str) -> list[dict]:
    unique: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for question in questions:
        key = _question_key(question)
        if not key[2] or key in seen:
            continue
        seen.add(key)
        item = dict(question)
        item["question_id"] = f"Q{len(unique) + 1:03d}"
        unique.append(item)
        if len(unique) >= requested_count:
            break
    if len(unique) < requested_count:
        write_log(project_id, "checklist", "warning", f"{source_label}只生成了 {len(unique)} 个不重复问题，少于用户选择的 {requested_count} 个；系统不会重复凑数。", len(unique), requested_count)
    return unique


def _local_template_questions(
    project: dict,
    question_count: int,
    modules: list[str],
    reason: str,
) -> list[dict]:
    settings = get_local_template_settings()
    selected_modules = (
        modules
        or [item.strip() for item in (project.get("focus_areas") or "").replace("，", ",").split(",") if item.strip()]
        or settings["default_modules"]
    )
    templates = settings["question_templates"]
    questions = [
        {
            "module": module,
            "interview_role": template["interview_role"],
            "interview_question": template["question_template"].format(module=module),
            "search_keywords": [module, *template.get("keywords", [])],
            "_generation_source": "local_template",
            "_generation_note": f"问题由本地模板生成；原因：{reason}",
        }
        for module in selected_modules
        for template in templates
    ]
    return _dedupe_and_limit_questions(project["id"], questions, question_count, "本地模板")


def generate_questions(project_id: int, chat_model_config_id: int | None, question_count: int, modules: list[str]) -> list[dict]:
    project = get_project(project_id)
    config = get_model_config(chat_model_config_id, "chat") if chat_model_config_id else get_model_config(None, "chat")
    if not config:
        reason = "未配置默认推理模型"
        write_log(project_id, "checklist", "warning", f"{reason}，已使用本地模板生成访谈问题", 0, question_count)
        return _local_template_questions(project, question_count, modules, reason)
    if not config.get("api_key") or not config.get("base_url"):
        reason = f"推理模型 {config.get('config_name')} 未配置 API Key 或 Base URL"
        write_log(project_id, "checklist", "warning", f"{reason}，已使用本地模板生成访谈问题", 0, question_count)
        return _local_template_questions(project, question_count, modules, reason)

    write_log(project_id, "checklist", "running", f"使用配置推理模型生成访谈问题：{config.get('config_name')} / {config.get('model')}", 0, question_count)
    prompt = build_question_prompt(project, question_count, modules)
    try:
        data = chat_json(prompt, config)
    except Exception as exc:
        reason = f"推理模型 {config.get('config_name')} 调用失败：{exc}"
        write_log(project_id, "checklist", "warning", f"{reason}；已使用本地模板生成访谈问题", 0, question_count)
        return _local_template_questions(project, question_count, modules, reason)
    questions = data.get("questions", [])
    if not isinstance(questions, list) or not questions:
        reason = f"推理模型 {config.get('config_name')} 未返回有效问题"
        write_log(project_id, "checklist", "warning", f"{reason}，已使用本地模板生成访谈问题", 0, question_count)
        return _local_template_questions(project, question_count, modules, reason)

    for question in questions:
        question["_generation_source"] = "configured_model"
        question["_generation_note"] = f"问题由配置推理模型生成：{config.get('config_name')} / {config.get('model')}"
    return _dedupe_and_limit_questions(project_id, questions, question_count, "配置模型")
