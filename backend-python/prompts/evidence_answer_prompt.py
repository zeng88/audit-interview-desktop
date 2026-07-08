def build_evidence_prompt(question: dict, evidence_chunks: list[dict]) -> str:
    evidence_text = "\n\n".join(
        [
            f"来源：{item.get('source_file')} / {item.get('source_location')}\n原文：{item.get('chunk_text')}"
            for item in evidence_chunks
        ]
    )
    return f"""请根据访谈问题和检索到的制度片段，生成制度依据答案。

访谈问题：{question.get("interview_question")}

检索到的制度片段：
{evidence_text}

要求：
1. 只能根据制度片段回答。
2. 如果没有明确依据，回答“未在已提供制度片段中找到明确依据。”。
3. 必须给出最相关的原文摘录。
4. 必须给出来源文件和来源位置。
5. 判断置信度：高 / 中 / 低 / 无依据。
6. 输出合法 JSON。
"""

