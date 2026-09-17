import pytest

from app.services import network_propagation as np


def test_symmetric_nodes_get_same_score():
    adj = {
        "A": [("B", 1.0), ("C", 1.0)],
        "B": [("A", 1.0), ("C", 1.0)],
        "C": [("A", 1.0), ("B", 1.0)],
    }
    res = np.propagate(adj, ["A"])
    assert abs(res.scores["B"] - res.scores["C"]) < 1e-6
    # 分值归一化后最大为 1
    assert abs(res.normalized_scores["A"] - 1.0) < 1e-6
    # 原始分值之和约为 1
    assert abs(sum(res.scores.values()) - 1.0) < 1e-4


def test_extended_candidates_exclude_seeds():
    adj = {
        "A": [("B", 1.0), ("C", 1.0), ("D", 0.5)],
        "B": [("A", 1.0)],
        "C": [("A", 1.0)],
        "D": [("A", 0.5)],
    }
    res = np.propagate(adj, ["A"], top_k=2)
    assert len(res.extended_candidates) == 2
    assert all(c["node_id"] != "A" for c in res.extended_candidates)
    # 前两个非种子应为 B、C（与 A 强连接）
    top_ids = {c["node_id"] for c in res.extended_candidates}
    assert top_ids == {"B", "C"}


def test_no_mapped_seeds_raises():
    adj = {"A": [("B", 1.0)], "B": [("A", 1.0)]}
    with pytest.raises(np.PropagationError):
        np.propagate(adj, ["X"])


def test_unmapped_seeds_recorded():
    adj = {"A": [("B", 1.0)], "B": [("A", 1.0)]}
    res = np.propagate(adj, ["A", "X"])
    assert res.unmapped_seeds == ["X"]
    assert res.seeds == ["A"]


def test_invalid_alpha_raises():
    adj = {"A": [("B", 1.0)], "B": [("A", 1.0)]}
    with pytest.raises(np.PropagationError):
        np.propagate(adj, ["A"], alpha=1.5)


def test_disconnected_component_handled():
    adj = {
        "A": [("B", 1.0)],
        "B": [("A", 1.0)],
        "C": [("D", 1.0)],
        "D": [("C", 1.0)],
    }
    res = np.propagate(adj, ["A"])
    assert abs(sum(res.scores.values()) - 1.0) < 1e-4
