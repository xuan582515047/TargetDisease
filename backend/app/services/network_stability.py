"""稳定性与消融评估。

- 留一扰动：每次移除一个种子并重新传播，记录完整融合榜的排名范围与 Top5 出现次数。
- 权重敏感性：固定网络计算结果，评估 A 权重 0~1（步长 0.1）的 11 种配置。
- 度数基线：普通节点度数排序用于检查网络枢纽偏置。
"""
from __future__ import annotations

from app.services import network_propagation as np
from app.services import target_ranking as tr


def _rank_map(candidates: list[dict]) -> dict[str, int]:
    """返回 node_id -> 排名（1 起）。candidates 已按融合分降序。"""
    return {c["node_id"]: i + 1 for i, c in enumerate(candidates)}


def _aggregate(ranks_by_node: dict[str, list[int]], top_n: int = 5) -> list[dict]:
    result = []
    for node_id, ranks in ranks_by_node.items():
        result.append({
            "node_id": node_id,
            "ranks": ranks,
            "min_rank": min(ranks),
            "max_rank": max(ranks),
            "top5_count": sum(1 for r in ranks if r <= top_n),
        })
    result.sort(key=lambda c: (c["min_rank"], c["node_id"]))
    return result


def leave_one_out(adjacency: dict[str, list[tuple[str, float]]],
                  seeds: list[str],
                  a_scores: dict[str, float | None],
                  alpha: float = np.ALPHA,
                  max_iter: int = np.MAX_ITER,
                  tol: float = np.TOL) -> dict:
    """留一扰动。移除一个种子并重新传播，记录融合榜排名范围与 Top5 次数。"""
    mapped_seeds = [s for s in seeds if s in adjacency]
    if len(mapped_seeds) < 2:
        return {"applicable": False, "reason": "单种子或种子不足，留一扰动不适用", "candidates": []}

    def one_run(seed_subset: list[str]) -> dict[str, int]:
        res = np.propagate(adjacency, seed_subset, alpha, max_iter, tol)
        cands = []
        for node_id, a in a_scores.items():
            if a is None:
                continue
            cands.append({"node_id": node_id, "a_score": a,
                          "n_score": res.normalized_scores.get(node_id)})
        return _rank_map(tr.rank_fusion(cands, key="node_id"))

    ranks_by_node: dict[str, list[int]] = {}
    base = one_run(mapped_seeds)
    for node_id, rank in base.items():
        ranks_by_node.setdefault(node_id, []).append(rank)

    for removed in mapped_seeds:
        subset = [s for s in mapped_seeds if s != removed]
        for node_id, rank in one_run(subset).items():
            ranks_by_node.setdefault(node_id, []).append(rank)

    return {"applicable": True, "reason": None, "runs": len(mapped_seeds) + 1,
            "candidates": _aggregate(ranks_by_node)}


def weight_sensitivity(candidates: list[dict]) -> dict:
    """权重敏感性：A 权重 0~1（步长 0.1）共 11 种配置，不调用模型。

    candidates 每项需含 node_id、a_score、n_score（A、N 均需存在）。
    """
    ranked_candidates = [c for c in candidates
                         if c.get("a_score") is not None and c.get("n_score") is not None]
    ranks_by_node: dict[str, list[int]] = {}
    for w_a in [round(i / 10, 1) for i in range(11)]:
        ranking = tr.rank_fusion(ranked_candidates, w_a, key="node_id")
        for node_id, rank in _rank_map(ranking).items():
            ranks_by_node.setdefault(node_id, []).append(rank)
    return {"candidates": _aggregate(ranks_by_node), "configs": 11}


def degree_baseline(adjacency: dict[str, list[tuple[str, float]]]) -> list[dict]:
    """普通节点度数降序排序，用于检查网络枢纽偏置。"""
    degrees = [{"node_id": n, "degree": len(nbrs)} for n, nbrs in adjacency.items()]
    degrees.sort(key=lambda c: (-c["degree"], c["node_id"]))
    return degrees
