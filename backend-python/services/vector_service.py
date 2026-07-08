import json
import math

from db import db_cursor, now_iso
from services.embedding_service import embed_query, embed_texts
from services.log_service import write_log
from services.model_config_service import get_model_config


def cosine_similarity(a: list[float], b: list[float]) -> float:
    total = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
    return total / (norm_a * norm_b)


def build_vector_index(project_id: int, config_id: int, batch_size: int = 16) -> dict:
    config = get_model_config(config_id, "embedding")
    if not config:
        raise ValueError("向量模型配置不存在")
    dimension = int(config.get("embedding_dimension") or 64)
    success = 0
    failed = 0
    with db_cursor() as cur:
        chunks = cur.execute(
            "SELECT id, chunk_text FROM chunks WHERE project_id = ? ORDER BY id",
            (project_id,),
        ).fetchall()
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        try:
            vectors = embed_texts([row["chunk_text"] for row in batch], config, dimension)
            with db_cursor() as cur:
                for row, vector in zip(batch, vectors):
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO chunk_vectors_fallback(
                            chunk_id, project_id, embedding_model_config_id, dimension, embedding_json, created_at
                        ) VALUES(?, ?, ?, ?, ?, ?)
                        """,
                        (row["id"], project_id, config_id, dimension, json.dumps(vector), now_iso()),
                    )
                    cur.execute(
                        """
                        UPDATE chunks
                        SET embedding_model_config_id = ?, embedding_dimension = ?,
                            embedding_status = 'done', embedding_error = NULL, embedding_created_at = ?
                        WHERE id = ?
                        """,
                        (config_id, dimension, now_iso(), row["id"]),
                    )
                    success += 1
        except Exception as exc:
            failed += len(batch)
            with db_cursor() as cur:
                for row in batch:
                    cur.execute(
                        "UPDATE chunks SET embedding_status = 'failed', embedding_error = ? WHERE id = ?",
                        (str(exc), row["id"]),
                    )
            write_log(project_id, "embedding", "failed", f"向量化批次失败：{exc}")
    write_log(project_id, "embedding", "success", f"向量索引完成：成功 {success}，失败 {failed}")
    return {"success_count": success, "failed_count": failed, "mode": "fallback-cosine"}


def search_vector(project_id: int, query: str, config_id: int | None, top_k: int = 30) -> list[dict]:
    config = get_model_config(config_id, "embedding") if config_id else get_model_config(None, "embedding")
    dimension = int((config or {}).get("embedding_dimension") or 64)
    query_vector = embed_query(query, config, dimension)
    with db_cursor() as cur:
        rows = cur.execute(
            """
            SELECT
                cv.embedding_json,
                c.*,
                f.original_name AS source_file
            FROM chunk_vectors_fallback cv
            JOIN chunks c ON c.id = cv.chunk_id
            JOIN files f ON f.id = c.file_id
            WHERE cv.project_id = ?
            """,
            (project_id,),
        ).fetchall()
    scored: list[dict] = []
    for row in rows:
        item = dict(row)
        vector = json.loads(item.pop("embedding_json"))
        score = cosine_similarity(query_vector, vector)
        item["score"] = score
        item["source"] = "vector"
        scored.append(item)
    scored.sort(key=lambda value: value["score"], reverse=True)
    results = scored[:top_k]
    for rank, item in enumerate(results, start=1):
        item["rank"] = rank
        location = []
        if item.get("page_number"):
            location.append(f"第{item['page_number']}页")
        if item.get("sheet_name"):
            location.append(f"Sheet：{item['sheet_name']}")
        if item.get("section_title"):
            location.append(str(item["section_title"]))
        item["source_location"] = "，".join(location) or "未标注位置"
    return results

