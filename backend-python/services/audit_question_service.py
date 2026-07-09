from prompts.question_generation_prompt import build_question_prompt
from services.llm_service import chat_json
from services.local_template_service import get_local_template_settings
from services.log_service import write_log
from services.model_config_service import get_model_config
from services.project_service import get_project


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
    questions: list[dict] = []
    for index in range(question_count):
        module = selected_modules[index % len(selected_modules)]
        template = templates[index % len(templates)]
        item = {
            "question_id": f"Q{index + 1:03d}",
            "module": module,
            "interview_role": template["interview_role"],
            "interview_question": template["question_template"].format(module=module),
            "search_keywords": [module, *template.get("keywords", [])],
            "_generation_source": "local_template",
            "_generation_note": f"问题由本地模板生成；原因：{reason}",
        }
        questions.append(item)
    return questions


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
    return questions[:question_count]
