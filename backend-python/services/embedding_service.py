import hashlib
import math
from typing import Iterable

import httpx


def _fallback_embedding(text: str, dimension: int) -> list[float]:
    """无外部向量模型时使用确定性哈希向量，保证本地演示链路可跑通。"""
    vector = [0.0] * dimension
    for token in text:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def embed_texts(texts: list[str], config: dict | None, dimension: int | None = None) -> list[list[float]]:
    dim = int(dimension or (config or {}).get("embedding_dimension") or 64)
    if not config or not config.get("api_key") or not config.get("base_url"):
        return [_fallback_embedding(text, dim) for text in texts]

    endpoint = config["base_url"].rstrip("/")
    headers = {"Authorization": f"Bearer {config['api_key']}"}
    payload = {"model": config["model"], "input": texts}
    with httpx.Client(timeout=float(config.get("timeout_seconds") or 120)) as client:
        resp = client.post(f"{endpoint}/embeddings", headers=headers, json=payload)
        resp.raise_for_status()
    data = resp.json()
    vectors = [item["embedding"] for item in data.get("data", [])]
    if len(vectors) != len(texts):
        raise RuntimeError("向量模型返回数量与输入数量不一致")
    for vector in vectors:
        if len(vector) != dim:
            raise RuntimeError(f"向量维度不一致，期望 {dim}，实际 {len(vector)}")
    return vectors


def embed_query(query: str, config: dict | None, dimension: int | None = None) -> list[float]:
    return embed_texts([query], config, dimension)[0]

