"""大模型引导的网络传播：带重启的个性化 PageRank。

p(t+1) = α × Wᵀ × p(t) + (1-α) × s

W 为由有效关联边权重按行归一化的转移矩阵；s 在通过核查且成功映射到图的种子间
均匀分配权重。默认 α=0.85、max_iter=200、tol=1e-8。悬空节点按种子分布回流。
从非种子节点中选取前 top_k 个作为扩展候选。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
from networkx.exception import PowerIterationFailedConvergence

ALPHA = 0.85
MAX_ITER = 200
TOL = 1e-8
MAX_EXTENDED = 20


class PropagationError(Exception):
    """网络传播失败。"""


@dataclass
class PropagationResult:
    scores: dict[str, float] = field(default_factory=dict)
    normalized_scores: dict[str, float] = field(default_factory=dict)
    max_score: float = 0.0
    alpha: float = ALPHA
    max_iter: int = MAX_ITER
    tol: float = TOL
    seeds: list[str] = field(default_factory=list)
    unmapped_seeds: list[str] = field(default_factory=list)
    extended_candidates: list[dict] = field(default_factory=list)


def build_graph(adjacency: dict[str, list[tuple[str, float]]]) -> nx.Graph:
    """由邻接表构建无向加权图。"""
    G = nx.Graph()
    for node, neighbors in adjacency.items():
        G.add_node(node)
        for neighbor, weight in neighbors:
            G.add_edge(node, neighbor, weight=weight)
    return G


def propagate(adjacency: dict[str, list[tuple[str, float]]],
              seed_node_ids: list[str],
              alpha: float = ALPHA,
              max_iter: int = MAX_ITER,
              tol: float = TOL,
              top_k: int = MAX_EXTENDED) -> PropagationResult:
    """执行个性化 PageRank 并返回扩展候选。"""
    G = build_graph(adjacency)
    mapped = [s for s in seed_node_ids if s in G]
    unmapped = [s for s in seed_node_ids if s not in G]

    if not mapped:
        raise PropagationError("没有任何种子映射到网络，网络阶段失败")

    if not (0 < alpha < 1):
        raise PropagationError(f"alpha 必须在 (0,1) 之间，得到 {alpha}")

    # 种子间均匀分配重启权重
    personalization = {node: (1.0 / len(mapped) if node in set(mapped) else 0.0)
                       for node in G.nodes()}

    try:
        raw = nx.pagerank(
            G, alpha=alpha, personalization=personalization,
            max_iter=max_iter, tol=tol, weight="weight", dangling=personalization,
        )
    except PowerIterationFailedConvergence as exc:
        raise PropagationError(f"PageRank 未收敛：{exc}") from exc

    max_score = max(raw.values()) if raw else 0.0
    normalized = {n: (s / max_score if max_score > 0 else 0.0) for n, s in raw.items()}

    seed_set = set(mapped)
    candidates = [
        {"node_id": n, "n_score": normalized[n], "raw_score": raw[n]}
        for n in raw if n not in seed_set
    ]
    candidates.sort(key=lambda c: (-c["n_score"], c["node_id"]))
    extended = candidates[:top_k]

    return PropagationResult(
        scores=raw,
        normalized_scores=normalized,
        max_score=max_score,
        alpha=alpha,
        max_iter=max_iter,
        tol=tol,
        seeds=mapped,
        unmapped_seeds=unmapped,
        extended_candidates=extended,
    )
