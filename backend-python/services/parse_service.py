from pathlib import Path

from db import db_cursor, now_iso
from parsers.docx_parser import parse_docx
from parsers.excel_parser import parse_xlsx
from parsers.pdf_parser import parse_pdf
from parsers.text_parser import parse_csv, parse_txt
from services.file_service import list_files, update_parse_status
from services.log_service import write_log


def _parse_file(file_row: dict) -> list[dict]:
    path = Path(file_row["stored_path"])
    file_type = file_row["file_type"].lower()
    if file_type == "pdf":
        return parse_pdf(path)
    if file_type == "docx":
        return parse_docx(path)
    if file_type == "xlsx":
        return parse_xlsx(path)
    if file_type == "txt":
        return parse_txt(path)
    if file_type == "csv":
        return parse_csv(path)
    raise ValueError(f"不支持的文件类型：{file_type}")


def parse_project_files(project_id: int) -> dict:
    files = list_files(project_id)
    parsed_count = 0
    failed_count = 0
    page_count = 0
    for file_row in files:
        try:
            pages = _parse_file(file_row)
            with db_cursor() as cur:
                cur.execute("DELETE FROM document_pages WHERE file_id = ?", (file_row["id"],))
                cur.execute("DELETE FROM chunks WHERE file_id = ?", (file_row["id"],))
                for page in pages:
                    cur.execute(
                        """
                        INSERT INTO document_pages(
                            project_id, file_id, page_number, sheet_name, section_title, raw_text, created_at
                        ) VALUES(?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            project_id,
                            file_row["id"],
                            page.get("page_number"),
                            page.get("sheet_name"),
                            page.get("section_title"),
                            page.get("raw_text"),
                            now_iso(),
                        ),
                    )
            update_parse_status(file_row["id"], "parsed", None)
            parsed_count += 1
            page_count += len(pages)
            write_log(project_id, "parse", "success", f"解析成功：{file_row['original_name']}，{len(pages)} 个文本单元")
        except Exception as exc:
            failed_count += 1
            update_parse_status(file_row["id"], "failed", str(exc))
            write_log(project_id, "parse", "failed", f"解析失败：{file_row['original_name']}，{exc}")
    return {"parsed_count": parsed_count, "failed_count": failed_count, "page_count": page_count}

