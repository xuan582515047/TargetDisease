"""DeepSeek 大模型客户端。

只做最朴素的 HTTP 调用：chat 补全 + key 校验（/models）。
出错统一抛 DeepSeekError，由调用方决定如何落库/返回。
chat_completion 返回结构化结果并记录 token 用量；接口未返回用量时置为 None。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from app.core.config import settings


class DeepSeekError(Exception):
    pass


@dataclass
class ChatCompletion:
    content: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


def _post(url: str, api_key: str, payload: dict, timeout: float) -> httpx.Response:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            return client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as e:
        raise DeepSeekError(f"DeepSeek 网络请求失败：{e}") from e


def _clean_error(status_code: int, text: str) -> str:
    """只保留必要错误信息，不向前端透传完整上游响应。"""
    return f"DeepSeek 返回 {status_code}：{text[:300]}"


def chat_completion(
    api_key: str,
    system: str,
    user: str,
    temperature: float = 0.2,
    max_tokens: int = 4000,
    model: str = "deepseek-chat",
) -> ChatCompletion:
    url = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    resp = _post(url, api_key, payload, timeout=120.0)
    if resp.status_code != 200:
        raise DeepSeekError(_clean_error(resp.status_code, resp.text))
    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise DeepSeekError(_clean_error(resp.status_code, resp.text)) from e
    usage = data.get("usage") or {}
    return ChatCompletion(
        content=content,
        model=data.get("model") or model,
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        total_tokens=usage.get("total_tokens"),
    )


def chat(api_key: str, system: str, user: str, temperature: float = 0.2, max_tokens: int = 4000) -> str:
    return chat_completion(api_key, system, user, temperature, max_tokens).content


def validate_key(api_key: str) -> None:
    url = f"{settings.deepseek_base_url.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, headers=headers)
    except httpx.HTTPError as e:
        raise DeepSeekError(f"DeepSeek 连接失败：{e}") from e
    if resp.status_code != 200:
        raise DeepSeekError(_clean_error(resp.status_code, resp.text))
