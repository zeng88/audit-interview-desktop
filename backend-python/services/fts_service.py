from db import db_cursor


def _source_location(row: dict) -> str:
    parts: list[str] = []
    if row.get("page_number"):
        parts.append(f"第{row['page_number']}页")
    if row.get("sheet_name"):
        parts.append(f"Sheet：{row['sheet_name']}")
    if row.get("section_title"):
        parts.append(str(row["section_title"]))
    return "，".join(parts) or "未标注位置"


def search_fts(project_id: int, query: str, top_k: int = 30) -> list[dict]:
    if not query.strip():
        return []
    # trigram 对中文短词友好；MATCH 语法出错时转为普通 LIKE 兜底。
    with db_cursor() as cur:
        try:
            rows = cur.execute(
                """
                SELECT
                    c.*, f.original_name AS source_file,
                    bm25(chunks_fts) AS bm25_score
                FROM chunks_fts
                JOIN chunks c ON c.id = chunks_fts.rowid
                JOIN files f ON f.id = c.file_id
                WHERE chunks_fts MATCH ? AND c.project_id = ?
                ORDER BY bm25_score
                LIMIT ?
                """,
                (query, project_id, top_k),
            ).fetchall()
        except Exception:
            like = f"%{query}%"
            rows = cur.execute(
                """
                SELECT c.*, f.original_name AS source_file, 0.0 AS bm25_score
                FROM chunks c
                JOIN files f ON f.id = c.file_id
                WHERE c.project_id = ? AND (c.chunk_text LIKE ? OR c.search_text LIKE ?)
                LIMIT ?
                """,
                (project_id, like, like, top_k),
            ).fetchall()
    results: list[dict] = []
    for rank, row in enumerate(rows, start=1):
        item = dict(row)
        item["rank"] = rank
        item["source_location"] = _source_location(item)
        item["score"] = float(item.get("bm25_score") or 0)
        item["source"] = "fts"
        results.append(item)
    return results

