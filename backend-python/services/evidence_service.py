from prompts.evidence_answer_prompt import build_evidence_prompt
from services.llm_service import chat_json
from services.log_service import write_log
from services.model_config_service import get_model_config
from services.retrieval_service import hybrid_search


MISSING_TEXT = "未在已提供制度片段中找到明确依据。"


def _fallback_answer(question: dict, evidence_chunks: list[dict]) -> dict:
    note_prefix = question.get("_generation_note") or "答案由本地规则根据检索片段归纳生成"
    if not evidence_chunks:
        return {
            "expected_answer": MISSING_TEXT,
            "source_file": "",
            "source_location": "",
            "evidence_quote": "",
            "confidence": "无依据",
            "follow_up_question": f"请被访谈人补充说明：{question.get('interview_question', '')}",
            "risk_hint": "风险提示：现有制度文件未覆盖该问题，需现场访谈和补充资料验证。",
            "is_missing_policy": True,
            "missing_policy_issue": question.get("interview_question", ""),
            "answer_source": "local_template",
            "generation_note": f"{note_prefix}；答案由本地规则生成，未检索到明确制度依据。",
        }
    best = evidence_chunks[0]
    quote = (best.get("chunk_text") or "")[:260]
    return {
        "expected_answer": f"根据检索到的制度片段，相关要求可概括为：{quote}",
        "source_file": best.get("source_file", ""),
        "source_location": best.get("source_location", ""),
        "evidence_quote": quote,
        "confidence": "中",
        "follow_up_question": "请被访谈人结合实际执行案例说明上述制度要求如何落地。",
        "risk_hint": "风险提示：该答案由制度片段归纳生成，现场需核验执行证据。",
        "is_missing_policy": False,
        "missing_policy_issue": "",
        "answer_source": "local_template",
        "generation_note": f"{note_prefix}；答案由本地规则根据检索片段生成。",
    }


def answer_question(
    project_id: int,
    question: dict,
    chat_model_config_id: int | None,
    embedding_model_config_id: int | None,
) -> tuple[dict, list[dict]]:
    query = " ".join(question.get("search_keywords") or []) or question.get("interview_question", "")
    evidence_chunks = hybrid_search(project_id, query, embedding_model_config_id, top_k=10)
    # chat_model_config_id=-1 是内部强制本地答案标记，用于上游模型失败后的快速降级。
    if chat_model_config_id == -1:
        config = None
    else:
        config = get_model_config(chat_model_config_id, "chat") if chat_model_config_id else get_model_config(None, "chat")
    if not config or not config.get("api_key"):
        return _fallback_answer(question, evidence_chunks), evidence_chunks
    try:
        prompt = build_evidence_prompt(question, evidence_chunks)
        answer = chat_json(prompt, config)
        answer["answer_source"] = "configured_model"
        answer["generation_note"] = (
            f"{question.get('_generation_note') or ''}；答案由配置推理模型生成："
            f"{config.get('config_name')} / {config.get('model')}"
        ).strip("；")
        return answer, evidence_chunks
    except Exception as exc:
        write_log(project_id, "checklist", "warning", f"配置推理模型生成答案失败，已使用本地规则降级：{exc}")
        return _fallback_answer(question, evidence_chunks), evidence_chunks
