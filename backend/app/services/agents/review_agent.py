"""评审专家：对候选种子逐个给出保留或剔除的决定（只 keep/drop，不新增不修改）。"""
from __future__ import annotations

from app.services.agents.base import AgentTrace, run_json_agent

PROMPT_VERSION = "agent-review-v1"

SYSTEM_PROMPT = """你是「评审专家」，负责审查种子推荐专家给出的候选靶点，逐个给出保留或剔除的决定。

评审标准：
- 与该疾病/机制的相关性是否成立；
- 推荐理由是否具体、是否存在明显错误；
- 是否推荐了与研究问题无关的基因。

硬性规则：
1. 对每个种子给出 decision（keep 或 drop）与简短理由 comment。
2. 只能保留或剔除，不能新增候选、不能修改候选的分数。
3. 只输出一个 JSON 对象，不要输出解释文字或 Markdown 代码块。

输出 JSON 结构：
{
  "reviews": [{"symbol": "LRRK2", "decision": "keep", "comment": "评审理由"}],
  "overall": "整体评审意见"
}"""

SCHEMA_HINT = """{
  "reviews": [{"symbol": "基因符号", "decision": "keep", "comment": "评审理由"}],
  "overall": "整体评审意见"
}"""


def _normalize(payload: dict) -> dict:
    raw = payload.get("reviews")
    if not isinstance(raw, list):
        raw = []
    reviews = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or "").strip()
        if not symbol:
            continue
        decision = str(item.get("decision") or "").strip().lower()
        reviews.append({
            "symbol": symbol,
            "decision": "drop" if decision == "drop" else "keep",
            "comment": str(item.get("comment") or ""),
        })
    return {"reviews": reviews, "overall": str(payload.get("overall") or "")}


def _summary(payload: dict) -> str:
    reviews = payload.get("reviews") or []
    kept = sum(1 for r in reviews if r["decision"] == "keep")
    return f"评审 {len(reviews)} 个候选：保留 {kept} 个，剔除 {len(reviews) - kept} 个"


def run(question: str, seeds: list[dict], api_key: str,
        model: str = "deepseek-chat") -> tuple[dict, AgentTrace]:
    lines = [
        f"- {s['symbol']}（相关度分 {s.get('relevance_score')}）：{s.get('reason') or '无理由'}"
        for s in seeds
    ]
    user = f"研究问题：{question}\n待评审的候选种子：\n" + "\n".join(lines)

    def fallback(error: str) -> tuple[dict, str]:
        payload = {
            "reviews": [
                {"symbol": s["symbol"], "decision": "keep", "comment": "评审失败，默认保留"}
                for s in seeds
            ],
            "overall": f"评审专家调用失败，已跳过过滤（{error}）",
        }
        return payload, f"评审失败，已跳过过滤，保留全部 {len(seeds)} 个候选"

    return run_json_agent(
        key="review",
        name="评审专家",
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
