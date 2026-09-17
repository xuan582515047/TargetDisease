"""排序：种子按模型输出顺序在前，扩展候选按网络分 N 降序在后。"""
from __future__ import annotations


def rank(seeds: list[dict], extended: list[dict]) -> list[dict]:
    """返回完整候选列表：种子保持模型顺序，扩展按 N 分降序。"""
    sorted_extended = sorted(
        extended,
        key=lambda c: (-(c.get("n_score") or 0), c.get("target_id") or ""),
    )
    return seeds + sorted_extended
