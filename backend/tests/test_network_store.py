import hashlib
import json

import pytest

from app.services.network_store import NetworkStore, NetworkSnapshotError


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_snapshot(tmp_path, *, nodes=None, edges=None, version="1", tamper=None):
    nodes = nodes or [
        {"id": "9606.ENSP00000284967", "gene_id": "ENSG00000142192", "symbol": "APP", "name": "amyloid beta precursor protein"},
        {"id": "9606.ENSP00000350990", "gene_id": "ENSG00000080815", "symbol": "PSEN1", "name": "presenilin 1"},
        {"id": "9606.ENSP00000252486", "gene_id": None, "symbol": "APOE", "name": "apolipoprotein E"},
    ]
    edges = edges if edges is not None else [
        {"source": "9606.ENSP00000284967", "target": "9606.ENSP00000350990", "score": 0.9, "string_score": 900},
        {"source": "9606.ENSP00000284967", "target": "9606.ENSP00000252486", "score": 0.75, "string_score": 750},
    ]
    contents = {
        "nodes.json": json.dumps(nodes, ensure_ascii=False),
        "edges.json": json.dumps(edges, ensure_ascii=False),
    }
    for name, text in contents.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    manifest = {
        "version": version,
        "source": "STRING",
        "source_version": "12.0",
        "threshold": 0.7,
        "hops": 2,
        "files": {name: _sha256(text) for name, text in contents.items()},
    }
    if tamper:
        name, value = tamper
        (tmp_path / name).write_text(value, encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_valid_snapshot_loads_and_queries(tmp_path):
    store = NetworkStore(_write_snapshot(tmp_path))
    assert store.manifest["version"] == "1"
    assert len(store.nodes()) == 3
    assert len(store.edges()) == 2
    assert store.node("9606.ENSP00000284967")["symbol"] == "APP"
    assert store.by_gene_id("ENSG00000080815")["symbol"] == "PSEN1"
    assert store.by_gene_id("NOT_EXIST") is None
    assert ("9606.ENSP00000350990", 0.9) in store.neighbors("9606.ENSP00000284967")
    assert store.statistics()["node_count"] == 3
    assert store.statistics()["edge_count"] == 2


def test_missing_manifest_rejected(tmp_path):
    with pytest.raises(NetworkSnapshotError):
        NetworkStore(tmp_path)


def test_duplicate_node_id_rejected(tmp_path):
    nodes = [
        {"id": "9606.ENSP1", "gene_id": "ENSG1", "symbol": "A", "name": "a"},
        {"id": "9606.ENSP1", "gene_id": "ENSG2", "symbol": "B", "name": "b"},
    ]
    with pytest.raises(NetworkSnapshotError):
        NetworkStore(_write_snapshot(tmp_path, nodes=nodes))


def test_same_gene_merged_into_multiple_nodes_rejected(tmp_path):
    nodes = [
        {"id": "9606.ENSP1", "gene_id": "ENSG1", "symbol": "A", "name": "a"},
        {"id": "9606.ENSP2", "gene_id": "ENSG1", "symbol": "A2", "name": "b"},
    ]
    with pytest.raises(NetworkSnapshotError):
        NetworkStore(_write_snapshot(tmp_path, nodes=nodes))


def test_self_loop_rejected(tmp_path):
    edges = [{"source": "9606.ENSP00000284967", "target": "9606.ENSP00000284967", "score": 0.9}]
    with pytest.raises(NetworkSnapshotError):
        NetworkStore(_write_snapshot(tmp_path, edges=edges))


def test_dangling_edge_rejected(tmp_path):
    edges = [{"source": "9606.ENSP00000284967", "target": "9606.ENSP99999999", "score": 0.9}]
    with pytest.raises(NetworkSnapshotError):
        NetworkStore(_write_snapshot(tmp_path, edges=edges))


def test_score_out_of_range_rejected(tmp_path):
    edges = [{"source": "9606.ENSP00000284967", "target": "9606.ENSP00000350990", "score": 1.5}]
    with pytest.raises(NetworkSnapshotError):
        NetworkStore(_write_snapshot(tmp_path, edges=edges))


def test_duplicate_undirected_edge_rejected(tmp_path):
    edges = [
        {"source": "9606.ENSP00000284967", "target": "9606.ENSP00000350990", "score": 0.9},
        {"source": "9606.ENSP00000350990", "target": "9606.ENSP00000284967", "score": 0.8},
    ]
    with pytest.raises(NetworkSnapshotError):
        NetworkStore(_write_snapshot(tmp_path, edges=edges))


def test_checksum_mismatch_rejected(tmp_path):
    with pytest.raises(NetworkSnapshotError):
        NetworkStore(_write_snapshot(tmp_path, tamper=("nodes.json", "[{}]")))


def test_isolated_node_counted(tmp_path):
    nodes = [
        {"id": "9606.ENSP00000284967", "gene_id": "ENSG1", "symbol": "A", "name": "a"},
        {"id": "9606.ENSP00000350990", "gene_id": "ENSG2", "symbol": "B", "name": "b"},
        {"id": "9606.ENSP00000252486", "gene_id": None, "symbol": "C", "name": "c"},
    ]
    edges = [{"source": "9606.ENSP00000284967", "target": "9606.ENSP00000350990", "score": 0.9}]
    store = NetworkStore(_write_snapshot(tmp_path, nodes=nodes, edges=edges))
    stats = store.statistics()
    assert stats["isolated_count"] == 1
    assert stats["isolated_nodes"] == ["9606.ENSP00000252486"]
