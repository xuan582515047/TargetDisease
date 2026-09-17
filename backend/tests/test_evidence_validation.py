from app.services import evidence_validation as ev


class FakeStore:
    def __init__(self, candidates):
        self._candidates = candidates

    def candidates(self, disease_id):
        return self._candidates

    def evidence(self, disease_id, target_id=None):
        rows = []
        for c in self._candidates:
            if target_id is None or c["id"] == target_id:
                rows.extend(c.get("evidence", []))
        return rows


def make_candidate(tid, symbol, evidence_ids):
    return {
        "id": tid, "symbol": symbol, "name": f"name {symbol}", "association_score": 0.8,
        "evidence": [{"id": e, "target_id": tid, "summary": f"s {e}", "score": 0.9}
                     for e in evidence_ids],
    }


def test_validate_seeds_passed_partial_missing():
    store = FakeStore([
        make_candidate("ENSG1", "A", ["e1", "e2"]),
        make_candidate("ENSG2", "B", ["e3"]),
    ])
    seeds = [
        {"target_id": "ENSG1", "reason": "r", "evidence_ids": ["e1", "e2"], "hypotheses": []},
        {"target_id": "ENSG2", "reason": "r", "evidence_ids": ["e3", "e99"], "hypotheses": []},
        {"target_id": "ENSG1", "reason": "dup", "evidence_ids": [], "hypotheses": []},
    ]
    out = ev.validate_seeds(seeds, store, "d1")
    assert len(out) == 2  # ENSG1 去重
    assert out[0]["status"] == "passed"
    assert out[0]["status_label"] == "引用匹配通过"
    assert out[1]["status"] == "partial"
    assert out[1]["invalid_evidence_ids"] == ["e99"]


def test_validate_seeds_missing_and_id_mismatch():
    store = FakeStore([make_candidate("ENSG1", "A", ["e1"])])
    seeds = [
        {"target_id": "ENSG1", "reason": "r", "evidence_ids": [], "hypotheses": []},
        {"target_id": "ENSG_NOT_IN_POOL", "reason": "r", "evidence_ids": [], "hypotheses": []},
    ]
    out = ev.validate_seeds(seeds, store, "d1")
    assert out[0]["status"] == "missing"
    assert out[1]["status"] == "id_mismatch"
    assert out[1]["in_pool"] is False


def test_validate_seeds_reason_too_long():
    store = FakeStore([make_candidate("ENSG1", "A", ["e1"])])
    seeds = [{"target_id": "ENSG1", "reason": "x" * 900, "evidence_ids": ["e1"], "hypotheses": []}]
    out = ev.validate_seeds(seeds, store, "d1")
    assert out[0]["field_errors"] == ["reason 超长"]


class FakeNetworkStore:
    def has_node(self, node_id):
        return node_id.startswith("9606.")


def test_validate_extended_evidence_match():
    store = FakeStore([make_candidate("ENSG1", "A", ["e1"])])
    net = FakeNetworkStore()
    candidates = [
        {"id": "9606.ENSP1", "gene_id": "ENSG1"},
        {"id": "9606.ENSP2", "gene_id": None},
        {"id": "bad-node", "gene_id": "ENSG1"},
    ]
    out = ev.validate_extended(candidates, store, net, "d1")
    assert out[0]["has_evidence"] is True
    assert out[0]["in_network"] is True
    assert out[1]["has_evidence"] is False
    assert out[2]["in_network"] is False
