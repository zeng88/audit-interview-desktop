from db import db_cursor, now_iso
from parsers.text_cleaner import clean_text, detect_clause
from services.log_service import write_log


def _window_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(text):
        part = text[start : start + chunk_size].strip()
        if part:
            chunks.append(part)
        start += step
    return chunks


def build_chunks(project_id: int, chunk_size: int = 800, overlap: int = 120) -> dict:
    with db_cursor() as cur:
        pages = cur.execute(
            """
            SELECT dp.*, f.original_name
            FROM document_pages dp
            JOIN files f ON f.id = dp.file_id
            WHERE dp.project_id = ?
            ORDER BY dp.file_id, dp.id
            """,
            (project_id,),
        ).fetchall()
        cur.execute("DELETE FROM chunks WHERE project_id = ?", (project_id,))
        try:
            cur.execute(
                "DELETE FROM chunks_fts WHERE rowid IN (SELECT id FROM chunks WHERE project_id = ?)",
                (project_id,),
            )
        except Exception:
            # FTS 外部内容表在 chunks 删除后可能无需额外清理，这里容错处理。
            pass
        chunk_total = 0
        for page in pages:
            for index, text in enumerate(_window_chunks(page["raw_text"] or "", chunk_size, overlap)):
                search_text = f"{page['original_name']} {page['section_title'] or ''} {text}"
                clause_no = detect_clause(text)
                cur.execute(
                    """
                    INSERT INTO chunks(
                        project_id, file_id, page_number, sheet_name, section_title,
                        clause_no, chunk_index, chunk_text, search_text, token_count, created_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        page["file_id"],
                        page["page_number"],
                        page["sheet_name"],
                        page["section_title"],
                        clause_no,
                        index,
                        text,
                        search_text,
                        len(text),
                        now_iso(),
                    ),
                )
                chunk_id = cur.lastrowid
                cur.execute(
                    "INSERT INTO chunks_fts(rowid, chunk_text, search_text) VALUES(?, ?, ?)",
                    (chunk_id, text, search_text),
                )
                chunk_total += 1
    write_log(project_id, "chunk", "success", f"生成切片 {chunk_total} 个")
    return {"chunk_count": chunk_total}

