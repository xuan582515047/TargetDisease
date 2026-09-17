from app.services import network_stability as ns


def _triangle():
    return {
        "A": [("B", 1.0), ("C", 1.0)],
        "B": [("A", 1.0), ("C", 1.0)],
        "C": [("A", 1.0), ("B", 1.0)],
    }


def test_leave_one_out_single_seed_not_applicable():
    adj = _triangle()
    result = ns.leave_one_out(adj, ["A"], {"A": 0.9, "B": 0.8, "C": 0.7})
    assert result["applicable"] is False
    assert result["candidates"] == []


def test_leave_one_out_records_ranks():
    adj = _triangle()
    a_scores = {"A": 0.9, "B": 0.8, "C": 0.7}
    result = ns.leave_one_out(adj, ["A", "B"], a_scores)
    assert result["applicable"] is True
    assert result["runs"] == 3  # base + 2 次扰动
    ids = {c["node_id"] for c in result["candidates"]}
    assert ids == {"A", "B", "C"}
    for c in result["candidates"]:
        assert c["min_rank"] <= c["max_rank"]
        assert 0 <= c["top5_count"] <= result["runs"]


def test_weight_sensitivity_11_configs():
    candidates = [
        {"node_id": "A", "a_score": 0.9, "n_score": 0.5},
        {"node_id": "B", "a_score": 0.5, "n_score": 0.9},
    ]
    result = ns.weight_sensitivity(candidates)
    assert result["configs"] == 11
    assert len(result["candidates"]) == 2
    for c in result["candidates"]:
        assert len(c["ranks"]) == 11


def test_weight_sensitivity_skips_missing_scores():
    candidates = [
        {"node_id": "A", "a_score": 0.9, "n_score": 0.5},
        {"node_id": "B", "a_score": None, "n_score": 0.9},
    ]
    result = ns.weight_sensitivity(candidates)
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["node_id"] == "A"


def test_degree_baseline_sorted():
    adj = _triangle()
    adj["D"] = [("A", 1.0)]
    adj["A"].append(("D", 1.0))
    baseline = ns.degree_baseline(adj)
    assert baseline[0]["node_id"] == "A"
    assert baseline[0]["degree"] == 3
