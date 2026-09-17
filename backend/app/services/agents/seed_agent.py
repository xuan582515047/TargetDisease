"""种子推荐专家：根据研究问题与意图推荐候选靶点基因。"""
from __future__ import annotations

from app.services.agents.base import AgentTrace, run_json_agent

PROMPT_VERSION = "agent-seed-v1"
MAX_SEEDS = 10

SYSTEM_PROMPT = """你是「种子推荐专家」，根据研究问题与研究意图，推荐值得优先研究的候选靶点基因。

硬性规则：
1. 只推荐人类基因靶点，symbol 使用 HGNC 标准符号（如 LRRK2、SNCA、APP）。
2. 输出 5~10 个种子；依据不足时如实减少，禁止凑数。
3. relevance_score 为 0~1 的相关度分，表示该靶点与研究问题的匹配程度。
4. reason 是推荐理由；mechanism 是与该靶点相关的机制推测（属于假设，不是已证实结论）。
5. 只输出一个 JSON 对象，不要输出解释文字或 Markdown 代码块。

输出 JSON 结构：
{
  "seeds": [
    {"symbol": "LRRK2", "reason": "推荐理由", "relevance_score": 0.9, "mechanism": "机制推测"}
  ],
  "limitations": ["当前推荐的局限"]
}"""

SCHEMA_HINT = """{
  "seeds": [
    {"symbol": "基因符号", "reason": "推荐理由", "relevance_score": 0.9, "mechanism": "机制推测"}
  ],
  "limitations": ["当前推荐的局限"]
}"""


def _to_score(value) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, score))


def _normalize(payload: dict) -> dict:
    raw = payload.get("seeds")
    if not isinstance(raw, list):
        raw = []
    seeds = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or "").strip()
        if not symbol:
            continue
        seeds.append({
            "symbol": symbol,
            "reason": str(item.get("reason") or ""),
            "relevance_score": _to_score(item.get("relevance_score")),
            "mechanism": str(item.get("mechanism") or ""),
        })
    limitations = payload.get("limitations")
    if not isinstance(limitations, list):
        limitations = []
    return {"seeds": seeds[:MAX_SEEDS], "limitations": [str(x) for x in limitations]}


def _summary(payload: dict) -> str:
    seeds = payload.get("seeds") or []
    symbols = "、".join(s["symbol"] for s in seeds[:6])
    tail = "…" if len(seeds) > 6 else ""
    return f"推荐 {len(seeds)} 个候选种子：{symbols}{tail}"


def run(question: str, intent: dict, api_key: str,
        model: str = "deepseek-chat") -> tuple[dict, AgentTrace]:
    disease = intent.get("disease") or {}
    keywords = "、".join(intent.get("mechanism_keywords") or [])
    user = (
        f"研究问题：{question}\n"
        f"疾病：{disease.get('name') or '未明确'}（{disease.get('id') or '无标准ID'}）\n"
        f"机制关键词：{keywords or '无'}\n"
        f"研究目标：{intent.get('research_goal') or '未明确'}"
    )

    return run_json_agent(
        key="seed",
        name="种子推荐专家",
        api_key=api_key,
        system=SYSTEM_PROMPT,
        user=user,
        schema_hint=SCHEMA_HINT,
        summary_fn=_summary,
        normalize_fn=_normalize,
        fallback_fn=None,
        model=model,
        temperature=0.2,
    )
