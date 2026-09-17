"""本地生物关联网络快照的加载与查询。

快照由 backend/scripts/import_target_network.py 从 STRING 生成，目录
backend/data/target_network/ 下含 manifest.json、nodes.json、edges.json。
加载时校验完整性；无效快照抛 NetworkSnapshotError，不允许激活。

节点身份：按来源蛋白 ID（STRING protein id，如 "9606.ENSP..."）计算；
节点附带标准基因名（symbol）与稳定基因 ID（gene_id，即 Ensembl ENSG）。
首版只接受一个基因对应一个代表蛋白的明确映射，同一基因多蛋白不合并。
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "target_network"
FILES = ("nodes.json", "edges.json")


class NetworkSnapshotError(Exception):
    """网络快照缺失或校验失败。"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_unique(rows, label, key):
    seen = set()
    for row in rows:
        value = row.get(key)
        if value is None:
            raise NetworkSnapshotError(f"{label} 记录缺少 {key}")
        if value in seen:
            raise NetworkSnapshotError(f"{label} 存在重复 {key} {value}")
        seen.add(value)
    return seen


def load_snapshot(data_dir: Path) -> dict:
    """读取并校验快照，返回 {manifest, nodes, edges}。"""
    manifest_path = data_dir / "manifest.json"
    if not manifest_path.is_file():
        raise NetworkSnapshotError("缺少 manifest.json，快照未激活")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if not manifest.get("version"):
        raise NetworkSnapshotError("manifest 缺少 version")
    files = manifest.get("files") or {}
    for name in FILES:
        if name not in files:
            raise NetworkSnapshotError(f"manifest.files 缺少 {name}")

    loaded = {}
    for name in FILES:
        path = data_dir / name
        if not path.is_file():
            raise NetworkSnapshotError(f"缺少 {name}")
        if _sha256(path) != files[name]:
            raise NetworkSnapshotError(f"{name} 校验值不匹配，快照可能被篡改")
        loaded[name.split(".")[0]] = json.loads(path.read_text(encoding="utf-8"))

    nodes, edges = loaded["nodes"], loaded["edges"]
    node_ids = _check_unique(nodes, "nodes", "id")
    gene_ids = set()
    for row in nodes:
        if not row.get("symbol"):
            raise NetworkSnapshotError(f"节点 {row['id']} 缺少 symbol")
        gene_id = row.get("gene_id")
        if gene_id is not None:
            if gene_id in gene_ids:
                raise NetworkSnapshotError(f"同一基因 {gene_id} 被多个蛋白节点合并")
            gene_ids.add(gene_id)

    for row in edges:
        src, dst = row.get("source"), row.get("target")
        if src is None or dst is None:
            raise NetworkSnapshotError("边缺少 source/target")
        if src == dst:
            raise NetworkSnapshotError(f"存在自环边 {src}")
        if src not in node_ids or dst not in node_ids:
            raise NetworkSnapshotError(f"边 {src}-{dst} 引用不存在的节点")
        score = row.get("score")
        if score is None or not (isinstance(score, (int, float)) and 0 <= score <= 1):
            raise NetworkSnapshotError(f"边 {src}-{dst} 的 score 超出 [0,1] 范围")

    # 去重无向边（同 source/target 成对只允许出现一次）
    seen_pairs = set()
    for row in edges:
        pair = tuple(sorted((row["source"], row["target"])))
        if pair in seen_pairs:
            raise NetworkSnapshotError(f"存在重复无向边 {pair}")
        seen_pairs.add(pair)

    return {"manifest": manifest, "nodes": nodes, "edges": edges}


class NetworkStore:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        snapshot = load_snapshot(self.data_dir)
        self._manifest = snapshot["manifest"]
        self._nodes = {n["id"]: n for n in snapshot["nodes"]}
        self._edges = snapshot["edges"]
        self._adj = defaultdict(list)
        for e in self._edges:
            self._adj[e["source"]].append((e["target"], e["score"]))
            self._adj[e["target"]].append((e["source"], e["score"]))

    @property
    def manifest(self) -> dict:
        return self._manifest

    def nodes(self) -> list[dict]:
        return list(self._nodes.values())

    def edges(self) -> list[dict]:
        return self._edges

    def node(self, node_id: str) -> dict | None:
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def by_gene_id(self, gene_id: str) -> dict | None:
        """按稳定基因 ID（ENSG）查找节点。"""
        for n in self._nodes.values():
            if n.get("gene_id") == gene_id:
                return n
        return None

    def neighbors(self, node_id: str) -> list[tuple[str, float]]:
        """返回 (邻居节点 id, 边分值) 列表。"""
        return self._adj.get(node_id, [])

    def adjacency(self) -> dict[str, list[tuple[str, float]]]:
        return dict(self._adj)

    def statistics(self) -> dict:
        """返回节点数、边数、孤立节点数等统计。"""
        connected = {e["source"] for e in self._edges} | {e["target"] for e in self._edges}
        isolated = [n for n in self._nodes if n not in connected]
        return {
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "isolated_count": len(isolated),
            "isolated_nodes": isolated,
            "min_edge_score": min((e["score"] for e in self._edges), default=None),
            "max_edge_score": max((e["score"] for e in self._edges), default=None),
        }
