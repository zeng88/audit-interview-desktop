import os

from prompts.question_generation_prompt import build_question_prompt
from services.llm_service import chat_json
from services.log_service import write_log
from services.model_config_service import get_model_config
from services.project_service import get_project


DEFAULT_MODULES = ["采购管理", "合同管理", "付款管理", "供应商管理", "授权审批", "资料留痕"]


def _fallback_questions(project: dict, question_count: int, modules: list[str], local_fallback: bool = False) -> list[dict]:
    selected_modules = modules or [item.strip() for item in (project.get("focus_areas") or "").split(",") if item.strip()] or DEFAULT_MODULES
    templates = [
        ("流程负责人", "请说明{module}的主要流程、关键审批节点和职责分工。", ["流程", "审批", "职责", "分工"]),
        ("业务经办人", "请说明{module}相关资料如何提交、复核和归档留痕。", ["资料", "复核", "归档", "留痕"]),
        ("部门负责人", "请说明{module}发生例外事项时的审批和记录要求。", ["例外", "审批", "记录", "要求"]),
        ("内控负责人", "请说明公司如何监督检查{module}制度执行情况。", ["监督", "检查", "执行", "制度"]),
    ]
    questions: list[dict] = []
    for index in range(question_count):
        module = selected_modules[index % len(selected_modules)]
        role, text, keywords = templates[index % len(templates)]
        item = {
            "question_id": f"Q{index + 1:03d}",
            "module": module,
            "interview_role": role,
            "interview_question": text.format(module=module),
            "search_keywords": [module, *keywords],
        }
        if local_fallback:
            item["_local_fallback"] = True
        questions.append(item)
    return questions


def generate_questions(project_id: int, chat_model_config_id: int | None, question_count: int, modules: list[str]) -> list[dict]:
    project = get_project(project_id)
    config = get_model_config(chat_model_config_id, "chat") if chat_model_config_id else get_model_config(None, "chat")
    if os.environ.get("AUDIT_USE_REMOTE_QUESTION_GENERATION") != "1":
        # 本地桌面交互优先保证立即产出可见结果；远程推理生成可通过环境变量显式开启。
        write_log(project_id, "checklist", "running", "使用本地模板生成访谈问题", 0, question_count)
        return _fallback_questions(project, question_count, modules, local_fallback=True)
    if not config or not config.get("api_key"):
        return _fallback_questions(project, question_count, modules)
    prompt = build_question_prompt(project, question_count, modules)
    try:
        data = chat_json(prompt, config)
    except Exception as exc:
        # 推理模型不可用时不阻断清单生成，降级模板保证用户能看到可用结果。
        write_log(project_id, "checklist", "warning", f"推理模型生成问题失败，已使用本地模板降级：{exc}", 0, question_count)
        return _fallback_questions(project, question_count, modules, local_fallback=True)
    questions = data.get("questions", [])
    if not isinstance(questions, list) or not questions:
        write_log(project_id, "checklist", "warning", "推理模型未返回有效问题，已使用本地模板降级", 0, question_count)
        return _fallback_questions(project, question_count, modules, local_fallback=True)
    return questions[:question_count]
