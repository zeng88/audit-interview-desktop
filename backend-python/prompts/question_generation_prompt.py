def build_question_prompt(project: dict, question_count: int, modules: list[str]) -> str:
    module_text = "、".join(modules) if modules else project.get("focus_areas", "")
    return f"""请根据以下信息生成审计访谈问题清单。

公司名称：{project.get("company_name", "")}
行业：{project.get("industry", "")}
审计目标：{project.get("audit_objective", "")}
审计期间：{project.get("audit_period", "")}
关注模块：{module_text}

要求：
1. 生成 {question_count} 个问题。
2. 问题要适合现场访谈。
3. 每个问题要指定建议访谈对象。
4. 每个问题要给出 search_keywords。
5. 输出 JSON。
"""

