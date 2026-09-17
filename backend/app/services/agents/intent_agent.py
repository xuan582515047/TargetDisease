"""意图解析专家：把自由文本研究问题解析成结构化意图（疾病 / 机制 / 研究目标）。"""
from __future__ import annotations

from app.services.agents.base import AgentTrace, run_json_agent

PROMPT_VERSION = "agent-intent-v1"

SYSTEM_PROMPT = """你是「意图解析专家」，负责把用户的研究问题解析成结构化意图。

任务：
1. 识别研究问题关注的疾病，给出疾病名称与最可能的标准稳定标识（如 MONDO/EFO 编号）。
2. 提取与研究问题相关的机制关键词（2~5 个中文短语）。
3. 概括研究目标与问题意图。

硬性规则：
- 只输出一个 JSON 对象，不要输出解释文字或 Markdown 代码块。
- 疾病标准 ID 不确定时给出最可能的编号；完全无法判断时留空字符串，禁止编造。
- 机制关键词使用中文短语。

输出 JSON 结构：
{
  "disease": {"name": "疾病名称", "id": "MONDO_XXXXXXX"},
  "mechanism_keywords": ["机制1", "机制2"],
  "research_goal": "研究目标概述",
  "question_summary": "对研究问题的一句话概括"
}"""

SCHEMA_HINT = """{
  "disease": {"name": "疾病名称", "id": "MONDO_XXXXXXX"},
  "mechanism_keywords": ["机制1", "机制2"],
  "research_goal": "研究目标概述",
  "question_summary": "对研究问题的一句话概括"
}"""


def _normalize(payload: dict) -> dict:
    disease_raw = payload.get("disease")
    if not isinstance(disease_raw, dict):
        disease_raw = {}
    keywords = payload.get("mechanism_keywords")
    if not isinstance(keywords, list):
        keywords = []
    return {
        "disease": {
            "name": str(disease_raw.get("name") or ""),
            "id": str(disease_raw.get("id") or ""),
        },
        "mechanism_keywords": [str(k).strip() for k in keywords if str(k).strip()],
        "research_goal": str(payload.get("research_goal") or ""),
        "question_summary": str(payload.get("question_summary") or ""),
    }


def _summary(payload: dict) -> str:
    disease = payload.get("disease") or {}
    name = disease.get("name") or "未识别疾病"
    disease_id = f"（{disease['id']}）" if disease.get("id") else ""
    keywords = "、".join(payload.get("mechanism_keywords") or []) or "未提取到机制关键词"
    return f"识别疾病：{name}{disease_id}；机制关键词：{keywords}"


def run(question: str, user_keywords: list[str] | None, api_key: str,
        model: str = "deepseek-chat") -> tuple[dict, AgentTrace]:
    user = f"研究问题：{question}"
    if user_keywords:
        user += "\n用户填写的机制关键词：" + "、".join(user_keywords)

    def fallback(error: str) -> tuple[dict, str]:
        payload = {
            "disease": {"name": "", "id": ""},
            "mechanism_keywords": list(user_keywords or []),
            "research_goal": "",
            "question_summary": question.strip()[:80],
        }
        return payload, f"模型解析失败，已降级使用原始问题（{error}）"

    return run_json_agent(
        key="intent",
        name="意图解析专家",
        api_key=api_key,
        system=SYSTEM_PROMPT,
        user=user,
        schema_hint=SCHEMA_HINT,
        summary_fn=_summary,
        normalize_fn=_normalize,
        fallback_fn=fallback,
        model=model,
        temperature=0.1,
    )
