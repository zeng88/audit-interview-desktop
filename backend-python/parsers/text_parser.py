import csv
from pathlib import Path

from parsers.text_cleaner import clean_text


def _read_text(path: Path) -> str:
    # 中文制度文件常见编码按顺序尝试，优先 UTF-8。
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_txt(path: str | Path) -> list[dict]:
    text = clean_text(_read_text(Path(path)))
    return [
        {
            "page_number": None,
            "sheet_name": None,
            "section_title": "文本文件",
            "raw_text": text,
        }
    ] if text else []


def parse_markdown(path: str | Path) -> list[dict]:
    text = clean_text(_read_text(Path(path)))
    if not text:
        return []
    section_title = "Markdown 文档"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            section_title = stripped.lstrip("#").strip() or section_title
            break
    return [
        {
            "page_number": None,
            "sheet_name": None,
            "section_title": section_title,
            "raw_text": text,
        }
    ]


def parse_csv(path: str | Path) -> list[dict]:
    file_path = Path(path)
    content = _read_text(file_path)
    rows: list[str] = []
    dialect = csv.Sniffer().sniff(content[:2048]) if content.strip() else csv.excel
    for row in csv.reader(content.splitlines(), dialect):
        values = [cell.strip() for cell in row if cell.strip()]
        if values:
            rows.append(" | ".join(values))
    text = clean_text("\n".join(rows))
    return [
        {
            "page_number": None,
            "sheet_name": file_path.stem,
            "section_title": "CSV 文件",
            "raw_text": text,
        }
    ] if text else []
