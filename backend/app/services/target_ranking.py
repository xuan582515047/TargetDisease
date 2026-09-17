"""融合排序：A/N 双维度可解释融合评分。

A：来源提供的疾病—靶点关联分值（0~1）；N：归一化 PageRank 分值（0~1）。
融合分 = 100 × (w_a × A + w_n × N)，w_a + w_n = 1。
A 缺失的网络候选归入探索性候选，不填零、不进入完整融合榜；
N 缺失的靶点保留疾病证据排序，标记网络覆盖缺失，不捏造 N。
"""
from __future__ import annotations

DEFAULT_W_A = 0.7
DEFAULT_W_N = 0.3


def fusion_score(a: float | None, n: float | None, w_a: float = DEFAULT_W_A) -> float | None:
    """计算融合分。A 或 N 任一缺失返回 None（不进入完整融合榜）。"""
    if a is None or n is None:
        return None
    return round(100 * (w_a * a + (1 - w_a) * n), 4)


def rank_evidence(candidates: list[dict], key: str = "target_id") -> list[dict]:
    """按疾病证据分 A 降序排序，A 缺失的排后，同分按稳定 ID 升序。"""
    def sort_key(c):
        a = c.get("a_score")
        return (-a if a is not None else 1, c.get(key) or "")
    return sorted(candidates, key=sort_key)


def rank_fusion(candidates: list[dict], w_a: float = DEFAULT_W_A, key: str = "target_id") -> list[dict]:
    """按融合分降序排序，仅包含 A、N 均存在的候选；同分按稳定 ID 升序。"""
    scored = []
    for c in candidates:
        score = fusion_score(c.get("a_score"), c.get("n_score"), w_a)
        if score is not None:
            scored.append({**c, "fusion_score": score})
    return sorted(scored, key=lambda c: (-c["fusion_score"], c.get(key) or ""))


def rank(candidates: list[dict], w_a: float = DEFAULT_W_A) -> dict:
    """返回三种视图 + 探索性候选分组。

    candidates 每项需含 target_id、a_score、n_score（可为 None）与 source（seed/extended）。
    """
    model = [c for c in candidates if c.get("source") == "seed"]
    evidence = rank_evidence(candidates)
    fusion = rank_fusion(candidates, w_a)
    exploratory = sorted(
        [c for c in candidates if c.get("a_score") is None],
        key=lambda c: (-(c.get("n_score") or 0), c.get("target_id") or ""),
    )
    return {"model": model, "evidence": evidence, "fusion": fusion, "exploratory": exploratory}
