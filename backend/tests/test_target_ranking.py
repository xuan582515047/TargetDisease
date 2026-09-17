from app.services import target_ranking as tr


def test_fusion_score_default_weights():
    # 文档验收：A=0.8、N=0.5、默认权重时得分为 71
    assert tr.fusion_score(0.8, 0.5, 0.7) == 71


def test_fusion_score_missing_a_returns_none():
    assert tr.fusion_score(None, 0.5) is None


def test_fusion_score_missing_n_returns_none():
    assert tr.fusion_score(0.8, None) is None


def test_rank_fusion_sorts_and_ties_by_id():
    candidates = [
        {"target_id": "B", "a_score": 0.8, "n_score": 0.5},
        {"target_id": "A", "a_score": 0.8, "n_score": 0.5},
        {"target_id": "C", "a_score": 0.5, "n_score": 0.5},
        {"target_id": "D", "a_score": None, "n_score": 0.9},
    ]
    ranking = tr.rank_fusion(candidates)
    assert [c["target_id"] for c in ranking] == ["A", "B", "C"]
    assert ranking[0]["fusion_score"] == 71
    assert all(c.get("a_score") is not None for c in ranking)


def test_rank_views():
    candidates = [
        {"target_id": "S1", "source": "seed", "a_score": 0.9, "n_score": 0.5},
        {"target_id": "E1", "source": "extended", "a_score": 0.8, "n_score": 0.9},
        {"target_id": "E2", "source": "extended", "a_score": None, "n_score": 0.7},
    ]
    result = tr.rank(candidates)
    assert [c["target_id"] for c in result["model"]] == ["S1"]
    assert len(result["fusion"]) == 2
    assert result["exploratory"][0]["target_id"] == "E2"
