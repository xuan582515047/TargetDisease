"""大模型候选识别：从本地候选池中选择种子靶点。

负责提示词、结构化输出和候选解析。模型只能从提供的候选池中选择种子靶点，
输出固定 JSON 结构；解析失败时最多做一次格式修复调用，不进行循环自我辩论。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.services.deepseek import chat_completion

PROMPT_VERSION = "target-network-v1"
MAX_SEEDS = 10
MAX_CANDIDATE_CARDS = 50
MAX_INPUT_CHARS = 12000

SYSTEM_PROMPT = """你是生物医药研究助理，任务是从给定的候选靶点池中，为用户的疾病研究问题挑选种子靶点。

硬性规则：
1. 只能从提供的候选池中选择靶点，target_id 必须逐字复制候选池中的"靶点ID"，禁止自造。
2. 只能引用输入中真实出现的证据ID（evidence_ids），禁止编造文献或证据。
3. 最多输出 10 个种子靶点，目标 5~10 个；有效种子不足时如实返回，禁止凑数。
4. reason 是与研究问题相关的推荐理由；hypotheses 是尚待研究验证的机制推测，与事实陈述分开。
5. limitations 说明当前证据或数据范围的限制。
6. 只输出一个 JSON 对象，不要输出任何解释文字、Markdown 或代码块。

输出 JSON 结构：
{
  "question_summary": "对用户研究意图的概括",
  "candidates": [
    {
      "target_id": "候选池中的稳定标识",
      "reason": "与研究问题相关的推荐理由",
      "evidence_ids": ["输入中存在的证据标识"],
      "hypotheses": ["尚待研究验证的机制推测"]
    }
  ],
  "limitations": ["当前证据或数据范围的限制"]
}
"""

REPAIR_PROMPT = """你上次的输出无法被解析为合法 JSON。请只重新输出一个合法 JSON 对象，\
结构严格遵循以下要求，不要输出任何解释文字或 Markdown 代码块：

{
  "question_summary": "对用户研究意图的概括",
  "candidates": [
    {
      "target_id": "候选池中的稳定标识",
      "reason": "与研究问题相关的推荐理由",
      "evidence_ids": ["输入中存在的证据标识"],
      "hypotheses": ["尚待研究验证的机制推测"]
    }
  ],
  "limitations": ["当前证据或数据范围的限制"]
}

你上次的错误输出如下（供你修正）：
"""


class IdentificationError(Exception):
    """候选识别失败。"""


@dataclass
class IdentificationResult:
    question_summary: str
    candidates: list[dict]
    limitations: list[str]
    raw_response: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    repair_attempted: bool = False
    truncated_candidates: int = 0


def build_candidate_cards(store, disease_id: str, limit: int = MAX_CANDIDATE_CARDS) -> tuple[list[dict], int]:
    """构造候选证据卡片，按关联分降序取前 limit 个。返回 (cards, 被裁剪数量)。"""
    candidates = store.candidates(disease_id)
    candidates = sorted(
        candidates,
        key=lambda c: (c.get("association_score") or 0),
        reverse=True,
    )
    truncated = max(0, len(candidates) - limit)
    return candidates[:limit], truncated


def _format_card(c: dict) -> str:
    lines = [f"- 靶点ID: {c['id']}", f"  基因: {c['symbol']}", f"  名称: {c['name']}"]
    score = c.get("association_score")
    if score is not None:
        lines.append(f"  疾病关联分: {round(score, 4)}")
    evs = c.get("evidence", [])
    if evs:
        lines.append("  证据:")
        for e in evs[:5]:
            summary = (e.get("summary") or "").strip()[:160]
            s = e.get("score")
            score_txt = f" ({round(s, 3)})" if s is not None else ""
            lines.append(f"    [{e['id']}] {summary}{score_txt}")
    return "\n".join(lines)


def build_prompt(question: str, disease: dict, candidates: list[dict], mechanism_keywords: list[str] | None = None) -> str:
    """构造用户提示词，按固定规则控制总长度。"""
    disease_info = f"疾病: {disease['name_zh']}（{disease['name']}，ID: {disease['id']}）"
    kw = ""
    if mechanism_keywords:
        kw = "机制关键词: " + "、".join(mechanism_keywords) + "\n"
    cards = "\n".join(_format_card(c) for c in candidates)
    prompt = (
        f"{disease_info}\n"
        f"研究问题: {question}\n"
        f"{kw}"
        f"候选靶点池（共 {len(candidates)} 个）:\n{cards}"
    )
    if len(prompt) > MAX_INPUT_CHARS:
        prompt = prompt[:MAX_INPUT_CHARS]
    return prompt


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


def _normalize(parsed: dict) -> tuple[str, list[dict], list[str]]:
    question_summary = str(parsed.get("question_summary") or "")
    raw_candidates = parsed.get("candidates")
    if not isinstance(raw_candidates, list):
        raw_candidates = []
    candidates = []
    for c in raw_candidates:
        if not isinstance(c, dict):
            continue
        candidates.append({
            "target_id": str(c.get("target_id") or ""),
            "reason": str(c.get("reason") or ""),
            "evidence_ids": c.get("evidence_ids") if isinstance(c.get("evidence_ids"), list) else [],
            "hypotheses": c.get("hypotheses") if isinstance(c.get("hypotheses"), list) else [],
        })
    limitations = parsed.get("limitations")
    if not isinstance(limitations, list):
        limitations = []
    return question_summary, candidates, [str(x) for x in limitations]


def identify(question: str, disease: dict, candidates: list[dict], api_key: str,
             mechanism_keywords: list[str] | None = None,
             model: str = "deepseek-chat") -> IdentificationResult:
    """一次识别 + 最多一次格式修复。"""
    prompt = build_prompt(question, disease, candidates, mechanism_keywords)
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

    question_summary, candidates_out, limitations = _normalize(parsed)
    return IdentificationResult(
        question_summary=question_summary,
        candidates=candidates_out[:MAX_SEEDS],
        limitations=limitations,
        raw_response=raw,
        model=completion.model,
        prompt_tokens=completion.prompt_tokens,
        completion_tokens=completion.completion_tokens,
        total_tokens=completion.total_tokens,
        repair_attempted=repair_attempted,
    )
