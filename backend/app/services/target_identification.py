"""大模型自由选种：根据研究问题直接推荐候选靶点（基因）。

不再依赖候选池；模型凭自身知识给出种子基因、推荐理由、相关度分与机制推测。
输出固定 JSON 结构；解析失败时最多做一次格式修复调用，不进行循环自我辩论。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.services.deepseek import chat_completion

PROMPT_VERSION = "free-text-v1"
MAX_SEEDS = 10

SYSTEM_PROMPT = """你是生物医药研究助理，任务是根据用户的研究问题，直接推荐值得优先研究的候选靶点（人类基因）。

硬性规则：
1. 只推荐人类基因靶点，gene 符号使用 HGNC 标准符号（如 LRRK2、SNCA、APP）。
2. 输出 5~10 个种子靶点；没有足够依据时如实返回，禁止凑数。
3. disease.id 使用疾病的标准稳定标识（如 MONDO/EFO 编号，例如 MONDO_0004975）；不确定时给出最可能的 ID。
4. relevance_score 是 0~1 的相关度分，表示该靶点与研究问题的匹配程度。
5. reason 是推荐理由；mechanism 是与该靶点相关的机制推测（属于假设，不是已证实结论）。
6. 只输出一个 JSON 对象，不要输出任何解释文字、Markdown 或代码块。

输出 JSON 结构：
{
  "disease": {"name": "疾病名称", "id": "疾病标准ID"},
  "question_summary": "对用户研究意图的概括",
  "seeds": [
    {"symbol": "LRRK2", "reason": "推荐理由", "relevance_score": 0.9, "mechanism": "机制推测"}
  ],
  "limitations": ["当前分析的局限"]
}
"""

REPAIR_PROMPT = """你上次的输出无法被解析为合法 JSON。请只重新输出一个合法 JSON 对象，\
结构严格遵循以下要求，不要输出任何解释文字或 Markdown 代码块：

{
  "disease": {"name": "疾病名称", "id": "疾病标准ID"},
  "question_summary": "对用户研究意图的概括",
  "seeds": [
    {"symbol": "基因符号", "reason": "推荐理由", "relevance_score": 0.9, "mechanism": "机制推测"}
  ],
  "limitations": ["当前分析的局限"]
}

你上次的错误输出如下（供你修正）：
"""


class IdentificationError(Exception):
    """候选识别失败。"""


@dataclass
class IdentificationResult:
    disease: dict
    question_summary: str
    seeds: list[dict]
    limitations: list[str]
    raw_response: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    repair_attempted: bool = False


def build_prompt(question: str, mechanism_keywords: list[str] | None = None) -> str:
    """构造用户提示词。"""
    kw = ""
    if mechanism_keywords:
        kw = "机制关键词: " + "、".join(mechanism_keywords) + "\n"
    return f"研究问题: {question}\n{kw}"


def _extract_json(text: str) -> dict:
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
    raise IdentificationError("无法从模型输出中解析 JSON")


def _to_score(value) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, score))


def _normalize(parsed: dict) -> tuple[dict, str, list[dict], list[str]]:
    disease_raw = parsed.get("disease") or {}
    disease = {
        "name": str(disease_raw.get("name") or ""),
        "id": str(disease_raw.get("id") or ""),
    }
    question_summary = str(parsed.get("question_summary") or "")

    raw_seeds = parsed.get("seeds")
    if not isinstance(raw_seeds, list):
        raw_seeds = []
    seeds = []
    for s in raw_seeds:
        if not isinstance(s, dict):
            continue
        symbol = str(s.get("symbol") or "").strip()
        if not symbol:
            continue
        seeds.append({
            "symbol": symbol,
            "reason": str(s.get("reason") or ""),
            "relevance_score": _to_score(s.get("relevance_score")),
            "mechanism": str(s.get("mechanism") or ""),
        })

    limitations = parsed.get("limitations")
    if not isinstance(limitations, list):
        limitations = []
    return disease, question_summary, seeds[:MAX_SEEDS], [str(x) for x in limitations]


def identify(question: str, api_key: str,
             mechanism_keywords: list[str] | None = None,
             model: str = "deepseek-chat") -> IdentificationResult:
    """一次识别 + 最多一次格式修复。"""
    prompt = build_prompt(question, mechanism_keywords)
    completion = chat_completion(api_key, SYSTEM_PROMPT, prompt, temperature=0.1, model=model)

    repair_attempted = False
    raw = completion.content
    try:
        parsed = _extract_json(raw)
    except IdentificationError:
        repair_attempted = True
        repair_completion = chat_completion(
            api_key, SYSTEM_PROMPT, REPAIR_PROMPT + raw, temperature=0.1, model=model
        )
        raw = repair_completion.content
        completion = repair_completion
        parsed = _extract_json(raw)

    disease, question_summary, seeds, limitations = _normalize(parsed)
    return IdentificationResult(
        disease=disease,
        question_summary=question_summary,
        seeds=seeds,
        limitations=limitations,
        raw_response=raw,
        model=completion.model,
        prompt_tokens=completion.prompt_tokens,
        completion_tokens=completion.completion_tokens,
        total_tokens=completion.total_tokens,
        repair_attempted=repair_attempted,
    )
