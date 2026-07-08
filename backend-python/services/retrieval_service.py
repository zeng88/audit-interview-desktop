from services.fts_service import search_fts
from services.vector_service import search_vector


def _rrf_score(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)


def hybrid_search(
    project_id: int,
    query: str,
    embedding_model_config_id: int | None = None,
    top_k: int = 10,
) -> list[dict]:
    fts_results = search_fts(project_id, query, top_k=30)
    vector_results = search_vector(project_id, query, embedding_model_config_id, top_k=30)
    merged: dict[int, dict] = {}
    for result in fts_results:
        chunk_id = result["id"]
        merged.setdefault(chunk_id, result | {"fusion_score": 0.0, "sources": []})
        merged[chunk_id]["fusion_score"] += _rrf_score(result["rank"])
        merged[chunk_id]["sources"].append("fts")
    for result in vector_results:
        chunk_id = result["id"]
        merged.setdefault(chunk_id, result | {"fusion_score": 0.0, "sources": []})
        merged[chunk_id]["fusion_score"] += _rrf_score(result["rank"])
        merged[chunk_id]["sources"].append("vector")
    results = list(merged.values())
    results.sort(key=lambda value: value["fusion_score"], reverse=True)
    final = results[:top_k]
    for item in final:
        item["source"] = "+".join(sorted(set(item.get("sources", [])))) or "hybrid"
    return final

