from app.services import target_report as tr


def test_render_csv_escapes_formula_injection():
    candidates = [
        {"source": "seed", "target_id": "=cmd()", "symbol": "+SUM(A1)", "a_score": 0.8,
         "n_score": 0.5, "fusion_score": 71, "status_label": "引用匹配通过", "reason": "@import"},
    ]
    csv = tr.render_csv(candidates)
    assert "'=cmd()" in csv
    assert "'+SUM(A1)" in csv
    assert "'@import" in csv
    assert "引用匹配通过" in csv


def test_render_csv_has_header():
    csv = tr.render_csv([])
    assert "来源" in csv
    assert "融合分" in csv


def test_render_markdown_has_sections():
    data = {
        "question": "研究问题", "question_summary": "意图", "generated_at": "2026-09-16",
        "disease": {"name_zh": "阿尔茨海默病", "name": "Alzheimer disease", "id": "MONDO_0004975"},
        "evidence_snapshot_version": "1", "network_snapshot_version": "1",
        "model_name": "deepseek-chat", "prompt_version": "target-network-v1",
        "seeds": [{"target_id": "ENSG1", "symbol": "APP", "a_score": 0.87, "n_score": 0.9,
                   "status_label": "引用匹配通过", "reason": "理由"}],
        "extended_candidates": [{"target_id": "ENSG2", "symbol": "PSEN1", "a_score": 0.86,
                                 "n_score": 0.4, "has_evidence": True}],
        "hypotheses": ["推测"], "limitations": ["局限"],
        "params": {"alpha": 0.85, "max_iter": 200, "tol": 1e-8, "w_a": 0.7, "w_n": 0.3},
    }
    md = tr.render_markdown(data)
    assert "# 靶点优选研究报告" in md
    assert "研究问题" in md
    assert "APP" in md
    assert "PSEN1" in md
    assert "α=0.85" in md
