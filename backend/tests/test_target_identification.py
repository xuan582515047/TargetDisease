import pytest

from app.services import target_identification as ti
from app.services.deepseek import ChatCompletion


class FakeStore:
    def __init__(self, candidates):
        self._candidates = candidates

    def candidates(self, disease_id):
        return self._candidates


def make_candidate(tid, symbol, score, evidence_ids):
    return {
        "id": tid,
        "symbol": symbol,
        "name": f"name {symbol}",
        "association_score": score,
        "evidence": [{"id": e, "summary": f"summary {e}", "score": 0.9} for e in evidence_ids],
    }


def test_extract_json_plain():
    assert ti._extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced():
    assert ti._extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_embedded_text():
    assert ti._extract_json('模型输出如下：{"a": 1} 结束') == {"a": 1}


def test_extract_json_invalid_raises():
    with pytest.raises(ti.IdentificationError):
        ti._extract_json("这里没有 JSON")


def test_build_candidate_cards_sorts_and_truncates():
    store = FakeStore([make_candidate(f"ENSG{i}", f"G{i}", i, [f"e{i}"]) for i in range(60)])
    cards, truncated = ti.build_candidate_cards(store, "d1", limit=50)
    assert len(cards) == 50
    assert truncated == 10
    assert cards[0]["id"] == "ENSG59"  # 最高分优先


def test_build_prompt_length_controlled():
    store = FakeStore([make_candidate(f"ENSG{i}", f"G{i}", 0.9, [f"e{i}"]) for i in range(200)])
    cards, _ = ti.build_candidate_cards(store, "d1", limit=200)
    disease = {"name_zh": "阿尔茨海默病", "name": "Alzheimer disease", "id": "MONDO_0004975"}
    prompt = ti.build_prompt("研究问题" * 500, disease, cards)
    assert len(prompt) <= ti.MAX_INPUT_CHARS


def test_normalize_drops_bad_entries():
    parsed = {
        "question_summary": "q",
        "candidates": [
            {"target_id": "t1", "reason": "r", "evidence_ids": ["e1"], "hypotheses": ["h"]},
            "not-a-dict",
            {"target_id": "t2", "reason": "r2", "evidence_ids": "bad", "hypotheses": "bad"},
        ],
        "limitations": ["l"],
    }
    q, cands, lims = ti._normalize(parsed)
    assert q == "q"
    assert [c["target_id"] for c in cands] == ["t1", "t2"]
    assert cands[1]["evidence_ids"] == []
    assert lims == ["l"]


def _ok_completion(content):
    return ChatCompletion(content=content, model="deepseek-chat",
                          prompt_tokens=10, completion_tokens=5, total_tokens=15)


def test_identify_success(monkeypatch):
    raw = ('{"question_summary":"q","candidates":[{"target_id":"ENSG1","reason":"r",'
           '"evidence_ids":["e1"],"hypotheses":["h"]}],"limitations":["l"]}')
    monkeypatch.setattr(ti, "chat_completion", lambda *a, **k: _ok_completion(raw))
    disease = {"name_zh": "AD", "name": "Alzheimer", "id": "MONDO_1"}
    candidates = [make_candidate("ENSG1", "G1", 0.9, ["e1"])]
    result = ti.identify("研究问题", disease, candidates, "key")
    assert result.question_summary == "q"
    assert result.candidates[0]["target_id"] == "ENSG1"
    assert result.repair_attempted is False


def test_identify_repairs_invalid_json(monkeypatch):
    calls = []

    good = '{"question_summary":"q","candidates":[],"limitations":[]}'

    def fake_chat(*a, **k):
        user = a[2] if len(a) > 2 else k.get("user", "")
        # 首次调用返回坏 JSON，修复调用返回好 JSON。
        content = "bad json" if not user.startswith(ti.REPAIR_PROMPT) else good
        calls.append(content)
        return _ok_completion(content)

    monkeypatch.setattr(ti, "chat_completion", fake_chat)
    disease = {"name_zh": "AD", "name": "Alzheimer", "id": "MONDO_1"}
    result = ti.identify("研究问题", disease, [], "key")
    assert result.repair_attempted is True
    assert result.question_summary == "q"
    assert len(calls) == 2
