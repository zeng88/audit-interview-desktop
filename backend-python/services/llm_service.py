import json
import os
import re

import httpx

from prompts.system_prompt import SYSTEM_PROMPT


def _strip_json_markdown(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    return match.group(1).strip() if match else text


def parse_json_response(text: str) -> dict:
    cleaned = _strip_json_markdown(text)
    return json.loads(cleaned)


def chat_json(prompt: str, config: dict | None) -> dict:
    if not config or not config.get("api_key") or not config.get("base_url"):
        raise RuntimeError("未配置推理模型 API，当前应使用业务层本地降级生成")
    endpoint = config["base_url"].rstrip("/")
    headers = {"Authorization": f"Bearer {config['api_key']}"}
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": float(config.get("temperature") or 0.2),
        "max_tokens": int(config.get("max_tokens") or 4096),
        "response_format": {"type": "json_object"},
    }
    # 桌面端交互不能长时间无反馈，单次推理请求默认最多等待 20 秒；必要时可用环境变量放宽。
    timeout_cap = float(os.environ.get("AUDIT_LLM_TIMEOUT_CAP_SECONDS", "20"))
    timeout = min(float(config.get("timeout_seconds") or timeout_cap), timeout_cap)
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(f"{endpoint}/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return parse_json_response(content)
