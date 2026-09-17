"""多智能体公共运行时：LLM 调用、JSON 解析、格式修复、耗时与状态记录。

每个智能体统一返回 (数据, AgentTrace)，trace 用于前端展示「多智能体协作过程」。
status 取值：completed（正常）/ fallback（失败后降级）/ failed（失败且无兜底）。
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Callable

from app.services.deepseek import DeepSeekError, chat_completion


class AgentError(Exception):
    """智能体执行失败。"""


@dataclass
class AgentTrace:
    key: str
    name: str
    status: str
    summary: str
    output: dict | list | str | None = None
    model: str | None = None
    duration_ms: int = 0
    total_tokens: int | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "output": self.output,
            "model": self.model,
            "duration_ms": self.duration_ms,
            "total_tokens": self.total_tokens,
            "error": self.error,
        }


def extract_json(text: str) -> dict:
    """从模型输出中提取 JSON 对象。"""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise AgentError("无法从模型输出中解析 JSON")


REPAIR_TEMPLATE = """你上次的输出无法被解析为合法 JSON。请只重新输出一个合法 JSON 对象，\
不要输出任何解释文字或 Markdown 代码块。结构要求如下：

{schema}

你上次的错误输出如下（供你修正）：
"""


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def run_json_agent(
    *,
    key: str,
    name: str,
    api_key: str,
    system: str,
    user: str,
    schema_hint: str,
    summary_fn: Callable[[dict], str],
    normalize_fn: Callable[[dict], dict] | None = None,
    fallback_fn: Callable[[str], tuple[dict, str]] | None = None,
    model: str = "deepseek-chat",
    temperature: float = 0.2,
    max_tokens: int = 4000,
) -> tuple[dict, AgentTrace]:
    """执行一个 JSON 输出型智能体：调用 → 解析（失败最多修一次）→ 兜底。"""
    started = time.perf_counter()
    trace = AgentTrace(key=key, name=name, status="completed", summary="", model=model)
    completion = None
    last_error: str | None = None

    try:
        completion = chat_completion(api_key, system, user, temperature=temperature,
                                     max_tokens=max_tokens, model=model)
        raw = completion.content
        try:
            payload = extract_json(raw)
        except AgentError:
            repair_prompt = REPAIR_TEMPLATE.format(schema=schema_hint) + raw
            completion = chat_completion(api_key, system, repair_prompt, temperature=temperature,
                                        max_tokens=max_tokens, model=model)
            payload = extract_json(completion.content)
    except (DeepSeekError, AgentError) as exc:
        last_error = str(exc)
        payload = None

    if payload is not None:
        if normalize_fn is not None:
            payload = normalize_fn(payload)
        trace.status = "completed"
        trace.output = payload
        trace.summary = summary_fn(payload)
        trace.model = completion.model if completion else model
        trace.total_tokens = completion.total_tokens if completion else None
        trace.duration_ms = _elapsed_ms(started)
        return payload, trace

    if fallback_fn is not None:
        payload, summary = fallback_fn(last_error or "未知错误")
        if normalize_fn is not None:
            payload = normalize_fn(payload)
        trace.status = "fallback"
        trace.output = payload
        trace.summary = summary
        trace.error = last_error
        trace.duration_ms = _elapsed_ms(started)
        return payload, trace

    trace.status = "failed"
    trace.error = last_error
    trace.duration_ms = _elapsed_ms(started)
    raise AgentError(last_error or "智能体执行失败")


def run_text_agent(
    *,
    key: str,
    name: str,
    api_key: str,
    system: str,
    user: str,
    summary_fn: Callable[[str], str],
    fallback_fn: Callable[[str], tuple[str, str]] | None = None,
    model: str = "deepseek-chat",
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> tuple[str, AgentTrace]:
    """执行一个文本输出型智能体（如报告撰写）：调用 → 兜底。"""
    started = time.perf_counter()
    trace = AgentTrace(key=key, name=name, status="completed", summary="", model=model)
    completion = None
    last_error: str | None = None
    text = ""

    try:
        completion = chat_completion(api_key, system, user, temperature=temperature,
                                     max_tokens=max_tokens, model=model)
        text = (completion.content or "").strip()
        if not text:
            raise AgentError("模型返回空文本")
    except DeepSeekError as exc:
        last_error = str(exc)
    except AgentError as exc:
        last_error = str(exc)

    if text and not last_error:
        trace.status = "completed"
        trace.output = text
        trace.summary = summary_fn(text)
        trace.model = completion.model if completion else model
        trace.total_tokens = completion.total_tokens if completion else None
        trace.duration_ms = _elapsed_ms(started)
        return text, trace

    if fallback_fn is not None:
        text, summary = fallback_fn(last_error or "未知错误")
        trace.status = "fallback"
        trace.output = text
        trace.summary = summary
        trace.error = last_error
        trace.duration_ms = _elapsed_ms(started)
        return text, trace

    trace.status = "failed"
    trace.error = last_error
    trace.duration_ms = _elapsed_ms(started)
    raise AgentError(last_error or "智能体执行失败")
