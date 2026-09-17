import hashlib
import json

import pytest

from app.services.evidence_store import EvidenceStore, EvidenceSnapshotError


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_snapshot(tmp_path, *, diseases=None, targets=None, evidence=None,
                    supported=("literature", "clinical"), version="1", tamper=None):
    diseases = diseases or [{"id": "MONDO_0004975", "source_id": "MONDO_0004975",
                             "name_zh": "阿尔茨海默病", "name": "Alzheimer disease", "aliases": []}]
    targets = targets or [{"id": "ENSG00000142192", "symbol": "APP",
                           "name": "amyloid beta precursor protein", "aliases": [],
                           "uniprot_id": "P05067", "disease_scores": {"MONDO_0004975": 0.87}}]
    evidence = evidence if evidence is not None else [
        {"id": "e1", "disease_id": "MONDO_0004975", "target_id": "ENSG00000142192",
         "datatype": "literature", "datasource": "europepmc", "source_id": "PMID:1",
         "summary": "literature 证据（europepmc）；PMID 1", "score": 0.9,
         "resource_score": 10, "date": None}]
    contents = {
        "diseases.json": json.dumps(diseases, ensure_ascii=False),
        "targets.json": json.dumps(targets, ensure_ascii=False),
        "evidence.json": json.dumps(evidence, ensure_ascii=False),
    }
    for name, text in contents.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    manifest = {
        "version": version,
        "supported_datatypes": list(supported),
        "files": {name: _sha256(text) for name, text in contents.items()},
    }
    if tamper:
        name, value = tamper
        (tmp_path / name).write_text(value, encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_valid_snapshot_loads_and_queries(tmp_path):
    store = EvidenceStore(_write_snapshot(tmp_path))
    assert store.manifest["version"] == "1"
    assert [d["id"] for d in store.diseases()] == ["MONDO_0004975"]
    candidates = store.candidates("MONDO_0004975")
    assert len(candidates) == 1
    assert candidates[0]["symbol"] == "APP"
    assert candidates[0]["association_score"] == 0.87
    assert len(candidates[0]["evidence"]) == 1
    assert len(store.evidence("MONDO_0004975")) == 1
    assert store.evidence("MONDO_0004975", "ENSG00000142192")[0]["datatype"] == "literature"


def test_missing_manifest_rejected(tmp_path):
    with pytest.raises(EvidenceSnapshotError):
        EvidenceStore(tmp_path)


def test_empty_supported_datatypes_rejected(tmp_path):
    with pytest.raises(EvidenceSnapshotError):
        EvidenceStore(_write_snapshot(tmp_path, supported=[]))


def test_duplicate_target_id_rejected(tmp_path):
    targets = [
        {"id": "ENSG00000142192", "symbol": "APP", "name": "a"},
        {"id": "ENSG00000142192", "symbol": "APP2", "name": "b"},
    ]
    with pytest.raises(EvidenceSnapshotError):
        EvidenceStore(_write_snapshot(tmp_path, targets=targets))


def test_dangling_evidence_target_rejected(tmp_path):
    evidence = [{"id": "e1", "disease_id": "MONDO_0004975", "target_id": "ENSG00000000000",
                 "datatype": "literature", "datasource": "x", "source_id": "", "summary": "",
                 "score": 0.5, "resource_score": None, "date": None}]
    with pytest.raises(EvidenceSnapshotError):
        EvidenceStore(_write_snapshot(tmp_path, evidence=evidence))


def test_score_out_of_range_rejected(tmp_path):
    evidence = [{"id": "e1", "disease_id": "MONDO_0004975", "target_id": "ENSG00000142192",
                 "datatype": "literature", "datasource": "x", "source_id": "", "summary": "",
                 "score": 1.5, "resource_score": None, "date": None}]
    with pytest.raises(EvidenceSnapshotError):
        EvidenceStore(_write_snapshot(tmp_path, evidence=evidence))


def test_checksum_mismatch_rejected(tmp_path):
    with pytest.raises(EvidenceSnapshotError):
        EvidenceStore(_write_snapshot(tmp_path, tamper=("targets.json", "[{}]")))
