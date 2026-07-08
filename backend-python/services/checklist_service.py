from db import db_cursor, now_iso
from services.audit_question_service import generate_questions
from services.evidence_service import answer_question
from services.log_service import write_log


def generate_checklist(
    project_id: int,
    chat_model_config_id: int | None,
    embedding_model_config_id: int | None,
    question_count: int,
    modules: list[str],
) -> dict:
    questions = generate_questions(project_id, chat_model_config_id, question_count, modules)
    created = 0
    missing = 0
    with db_cursor() as cur:
        cur.execute("DELETE FROM checklist_items WHERE project_id = ?", (project_id,))
        cur.execute("DELETE FROM missing_policy_items WHERE project_id = ?", (project_id,))
    for question in questions:
        try:
            answer, _chunks = answer_question(project_id, question, chat_model_config_id, embedding_model_config_id)
            with db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO checklist_items(
                        project_id, question_id, module, interview_role, interview_question,
                        expected_answer, source_file, source_location, evidence_quote,
                        confidence, follow_up_question, risk_hint, created_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        question.get("question_id"),
                        question.get("module"),
                        question.get("interview_role"),
                        question.get("interview_question"),
                        answer.get("expected_answer"),
                        answer.get("source_file"),
                        answer.get("source_location"),
                        answer.get("evidence_quote"),
                        answer.get("confidence"),
                        answer.get("follow_up_question"),
                        answer.get("risk_hint"),
                        now_iso(),
                    ),
                )
                created += 1
                if answer.get("is_missing_policy") or answer.get("confidence") == "无依据":
                    missing += 1
                    cur.execute(
                        """
                        INSERT INTO missing_policy_items(
                            project_id, module, issue, risk, suggested_interview_question,
                            suggested_policy_improvement, created_at
                        ) VALUES(?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            project_id,
                            question.get("module"),
                            answer.get("missing_policy_issue") or question.get("interview_question"),
                            answer.get("risk_hint"),
                            question.get("interview_question"),
                            "建议补充制度条款，明确职责、审批节点、资料留痕和例外处理要求。",
                            now_iso(),
                        ),
                    )
        except Exception as exc:
            write_log(project_id, "checklist", "failed", f"问题生成失败：{question.get('question_id')}，{exc}")
            continue
    write_log(project_id, "checklist", "success", f"生成访谈清单 {created} 条，无依据 {missing} 条")
    return {"created_count": created, "missing_count": missing}


def list_checklist(project_id: int) -> list[dict]:
    with db_cursor() as cur:
        rows = cur.execute(
            "SELECT * FROM checklist_items WHERE project_id = ? ORDER BY id",
            (project_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def update_checklist_item(project_id: int, item_id: int, payload: dict) -> dict:
    allowed = ["module", "interview_role", "interview_question", "expected_answer", "follow_up_question", "risk_hint"]
    fields = [key for key in allowed if key in payload and payload[key] is not None]
    if not fields:
        return get_checklist_item(project_id, item_id)
    assignments = ", ".join([f"{field} = ?" for field in fields])
    values = [payload[field] for field in fields]
    with db_cursor() as cur:
        cur.execute(
            f"UPDATE checklist_items SET {assignments} WHERE id = ? AND project_id = ?",
            (*values, item_id, project_id),
        )
    return get_checklist_item(project_id, item_id)


def get_checklist_item(project_id: int, item_id: int) -> dict:
    with db_cursor() as cur:
        row = cur.execute(
            "SELECT * FROM checklist_items WHERE id = ? AND project_id = ?",
            (item_id, project_id),
        ).fetchone()
        if not row:
            raise ValueError("清单项不存在")
        return dict(row)


def list_missing_policy_items(project_id: int) -> list[dict]:
    with db_cursor() as cur:
        rows = cur.execute(
            "SELECT * FROM missing_policy_items WHERE project_id = ? ORDER BY id",
            (project_id,),
        ).fetchall()
        return [dict(row) for row in rows]

