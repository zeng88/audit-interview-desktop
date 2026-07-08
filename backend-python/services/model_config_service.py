import httpx

from db import db_cursor, now_iso


def create_model_config(payload: dict) -> dict:
    now = now_iso()
    with db_cursor() as cur:
        if payload.get("is_default"):
            cur.execute(
                "UPDATE model_configs SET is_default = 0 WHERE config_type = ?",
                (payload["config_type"],),
            )
        cur.execute(
            """
            INSERT INTO model_configs(
                config_name, config_type, provider, base_url, api_key, model,
                temperature, max_tokens, embedding_dimension, embedding_batch_size,
                timeout_seconds, is_default, created_at, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["config_name"],
                payload["config_type"],
                payload.get("provider", "openai-compatible"),
                payload.get("base_url", ""),
                payload.get("api_key", ""),
                payload["model"],
                payload.get("temperature", 0.2),
                payload.get("max_tokens", 4096),
                payload.get("embedding_dimension"),
                payload.get("embedding_batch_size", 16),
                payload.get("timeout_seconds", 120),
                int(payload.get("is_default", 0)),
                now,
                now,
            ),
        )
        row = cur.execute("SELECT * FROM model_configs WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)


def list_model_configs(config_type: str | None = None) -> list[dict]:
    with db_cursor() as cur:
        if config_type:
            rows = cur.execute(
                "SELECT * FROM model_configs WHERE config_type = ? ORDER BY is_default DESC, id DESC",
                (config_type,),
            ).fetchall()
        else:
            rows = cur.execute(
                "SELECT * FROM model_configs ORDER BY config_type, is_default DESC, id DESC"
            ).fetchall()
        return [dict(row) for row in rows]


def get_model_config(config_id: int | None, config_type: str | None = None) -> dict | None:
    with db_cursor() as cur:
        if config_id:
            row = cur.execute("SELECT * FROM model_configs WHERE id = ?", (config_id,)).fetchone()
        elif config_type:
            row = cur.execute(
                "SELECT * FROM model_configs WHERE config_type = ? ORDER BY is_default DESC, id DESC LIMIT 1",
                (config_type,),
            ).fetchone()
        else:
            row = None
        return dict(row) if row else None


def update_model_config(config_id: int, payload: dict) -> dict:
    with db_cursor() as cur:
        if payload.get("is_default"):
            cur.execute(
                "UPDATE model_configs SET is_default = 0 WHERE config_type = ? AND id != ?",
                (payload["config_type"], config_id),
            )
        cur.execute(
            """
            UPDATE model_configs
            SET config_name = ?, config_type = ?, provider = ?, base_url = ?, api_key = ?,
                model = ?, temperature = ?, max_tokens = ?, embedding_dimension = ?,
                embedding_batch_size = ?, timeout_seconds = ?, is_default = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload["config_name"],
                payload["config_type"],
                payload.get("provider", "openai-compatible"),
                payload.get("base_url", ""),
                payload.get("api_key", ""),
                payload["model"],
                payload.get("temperature", 0.2),
                payload.get("max_tokens", 4096),
                payload.get("embedding_dimension"),
                payload.get("embedding_batch_size", 16),
                payload.get("timeout_seconds", 120),
                int(payload.get("is_default", 0)),
                now_iso(),
                config_id,
            ),
        )
    result = get_model_config(config_id)
    if not result:
        raise ValueError("模型配置不存在")
    return result


def delete_model_config(config_id: int) -> None:
    with db_cursor() as cur:
        cur.execute("DELETE FROM model_configs WHERE id = ?", (config_id,))


def set_default(config_id: int) -> dict:
    config = get_model_config(config_id)
    if not config:
        raise ValueError("模型配置不存在")
    with db_cursor() as cur:
        cur.execute(
            "UPDATE model_configs SET is_default = 0 WHERE config_type = ?",
            (config["config_type"],),
        )
        cur.execute("UPDATE model_configs SET is_default = 1 WHERE id = ?", (config_id,))
    return get_model_config(config_id) or config


def test_model_config(config_id: int) -> dict:
    config = get_model_config(config_id)
    if not config:
        raise ValueError("模型配置不存在")
    if not config.get("api_key") or not config.get("base_url"):
        # 允许无密钥本地开发，明确告诉用户实际模型未连通。
        return {"ok": True, "mode": "local-fallback", "message": "未配置 API Key，使用本地降级模式"}
    endpoint = config["base_url"].rstrip("/")
    headers = {"Authorization": f"Bearer {config['api_key']}"}
    timeout = float(config.get("timeout_seconds") or 30)
    try:
        with httpx.Client(timeout=timeout) as client:
            if config["config_type"] == "embedding":
                resp = client.post(
                    f"{endpoint}/embeddings",
                    headers=headers,
                    json={"model": config["model"], "input": ["连接测试"]},
                )
            else:
                resp = client.post(
                    f"{endpoint}/chat/completions",
                    headers=headers,
                    json={
                        "model": config["model"],
                        "messages": [{"role": "user", "content": "请只返回 ok"}],
                        "temperature": 0,
                        "max_tokens": 8,
                    },
                )
        return {"ok": resp.status_code < 400, "status_code": resp.status_code, "message": resp.text[:300]}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}
