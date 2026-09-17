"""多智能体串联流水线（纯串联、无回退）。

① 意图解析专家 → ② 种子推荐专家 → ③ 评审专家（keep/drop）
        ↓
④ 确定性算法：STRING 动态拉取 + 个性化 PageRank → 扩展候选
        ↓
⑤ 报告专家（固定章节 Markdown）

各步失败按约定降级：意图解析失败→用原始问题；评审失败→不过滤；
报告失败→回退固定模板。种子推荐失败则整体终止。
"""
from __future__ import annotations

from app.services import network_propagation as np
from app.services import string_client as sc
from app.services import target_ranking as tr
from app.services.agents import intent_agent, report_agent, review_agent, seed_agent
from app.services.target_report import render_csv

WORKFLOW_VERSION = "multi-agent-v1"
PROMPT_VERSION = "multi-agent-v1"

# 动态 STRING 拉取参数
STRING_THRESHOLD = 0.7
STRING_HOPS = 1
STRING_MAX_NODES = 200

# 评审兜底：过滤后至少保留的种子数
MIN_SEEDS_AFTER_REVIEW = 3


def run(question: str, mechanism_keywords: list[str], api_key: str) -> dict:
    """执行完整多智能体流水线，返回可直接落库的结果字典。"""
    traces: list = []

    # ① 意图解析专家
    intent, t_intent = intent_agent.run(question, mechanism_keywords, api_key)
    traces.append(t_intent)

    # ② 种子推荐专家
    seed_payload, t_seed = seed_agent.run(question, intent, api_key)
    traces.append(t_seed)
    seeds_raw = seed_payload.get("seeds") or []
    if not seeds_raw:
        raise ValueError("种子推荐专家未产出任何候选靶点，分析终止")

    # ③ 评审专家
    review_payload, t_review = review_agent.run(question, seeds_raw, api_key)
    traces.append(t_review)
    seeds, review_map = _apply_review(seeds_raw, review_payload)

    # ④ 确定性算法：STRING 动态拉取 + PageRank
    symbol_to_string = sc.map_symbols([s["symbol"] for s in seeds])
    id_to_symbol = {sid: sym for sym, sid in symbol_to_string.items()}
    network = {"nodes": [], "edges": []}
    propagation = None
    n_scores: dict = {}
    network_error = None
    seed_node_ids = list(id_to_symbol.keys())

    if seed_node_ids:
        try:
            fetched = sc.fetch_network(id_to_symbol, threshold=STRING_THRESHOLD,
                                       hops=STRING_HOPS, max_nodes=STRING_MAX_NODES)
            network = {"nodes": fetched["nodes"], "edges": fetched["edges"]}
            propagation = np.propagate(fetched["adjacency"], seed_node_ids)
            n_scores = propagation.normalized_scores
        except (sc.StringError, np.PropagationError) as exc:
            network_error = str(exc)
    else:
        network_error = "种子未能映射到 STRING 网络"

    node_symbol = {n["id"]: n["symbol"] for n in network["nodes"]}

    seeds_out = []
    unmapped: list[str] = []
    for s in seeds:
        symbol = s["symbol"]
        sid = symbol_to_string.get(symbol)
        if sid is None:
            unmapped.append(symbol)
        review = review_map.get(symbol) or {}
        seeds_out.append({
            "target_id": symbol,
            "symbol": symbol,
            "node_id": sid,
            "n_score": n_scores.get(sid) if sid else None,
            "in_network": sid is not None,
            "reason": s.get("reason"),
            "relevance_score": s.get("relevance_score"),
            "mechanism": s.get("mechanism"),
            "review_decision": review.get("decision"),
            "review_comment": review.get("comment"),
            "source": "seed",
        })

    extended = []
    if propagation is not None:
        for c in propagation.extended_candidates:
            symbol = node_symbol.get(c["node_id"]) or c["node_id"]
            extended.append({
                "target_id": symbol,
                "symbol": symbol,
                "node_id": c["node_id"],
                "n_score": c["n_score"],
                "source": "extended",
            })

    all_candidates = tr.rank(seeds_out, extended)
    rankings = {"model": seeds_out, "extended": extended, "all": all_candidates}

    disease = intent.get("disease") or {"name": "", "id": ""}
    structured = {
        "disease": disease,
        "question": question,
        "question_summary": intent.get("question_summary") or "",
        "mechanism_keywords": intent.get("mechanism_keywords") or [],
        "research_goal": intent.get("research_goal") or "",
        "seeds": seeds_out,
        "extended_candidates": extended,
        "limitations": seed_payload.get("limitations") or [],
        "hypotheses": [s["mechanism"] for s in seeds_out if s.get("mechanism")],
        "review_overall": review_payload.get("overall") or "",
        "network_error": network_error,
        "params": {
            "alpha": np.ALPHA,
            "max_iter": np.MAX_ITER,
            "tol": np.TOL,
            "string_threshold": STRING_THRESHOLD,
            "string_hops": STRING_HOPS,
            "max_nodes": STRING_MAX_NODES,
        },
    }

    # ⑤ 报告专家
    report_text, t_report = report_agent.run(structured, api_key)
    traces.append(t_report)

    total_tokens = sum(t.total_tokens or 0 for t in traces)
    return {
        **structured,
        "candidates": all_candidates,
        "rankings": rankings,
        "network": network,
        "unmapped_seeds": unmapped,
        "model_name": "deepseek-chat",
        "workflow_version": WORKFLOW_VERSION,
        "prompt_version": PROMPT_VERSION,
        "report_markdown": report_text,
        "candidates_csv": render_csv(all_candidates),
        "agents": [t.to_dict() for t in traces],
        "usage": {"total_tokens": total_tokens},
    }


def _apply_review(seeds_raw: list[dict], review_payload: dict) -> tuple[list[dict], dict]:
    """按评审结果过滤种子；若保留数不足 MIN_SEEDS_AFTER_REVIEW，按相关度分补齐。"""
    review_map = {r["symbol"]: r for r in (review_payload.get("reviews") or [])}
    kept: list[dict] = []
    for s in seeds_raw:
        review = review_map.get(s["symbol"]) or {}
        if review.get("decision") != "drop":
            kept.append(s)

    if len(kept) < MIN_SEEDS_AFTER_REVIEW:
        by_score = sorted(seeds_raw, key=lambda s: (-(s.get("relevance_score") or 0), s["symbol"]))
        kept_symbols = {s["symbol"] for s in kept}
        for s in by_score:
            if len(kept) >= MIN_SEEDS_AFTER_REVIEW:
                break
            if s["symbol"] not in kept_symbols:
                kept.append(s)
                kept_symbols.add(s["symbol"])
    return kept, review_map
