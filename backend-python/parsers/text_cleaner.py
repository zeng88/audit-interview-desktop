import re


def clean_text(text: str) -> str:
    """清理多余空白，保留中文制度条款的自然换行。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_clause(text: str) -> str:
    match = re.search(r"(第[一二三四五六七八九十百千万0-9]+[章节条]|[0-9]+[.、][0-9.、]*)", text)
    return match.group(1) if match else ""

