from pathlib import Path

from parsers.text_cleaner import clean_text


def parse_pdf(path: str | Path) -> list[dict]:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("缺少 PyMuPDF 依赖，请执行 pip install -r requirements.txt") from exc

    pages: list[dict] = []
    doc = fitz.open(str(path))
    for index, page in enumerate(doc, start=1):
        text = clean_text(page.get_text("text"))
        if text:
            pages.append(
                {
                    "page_number": index,
                    "sheet_name": None,
                    "section_title": "",
                    "raw_text": text,
                }
            )
    doc.close()
    return pages

