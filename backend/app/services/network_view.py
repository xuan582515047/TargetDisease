"""图展示数据：类型化节点/边、阈值/层数筛选、统计。

计算与显示分离：图算法只用固定快照与计算参数；本模块只做展示层的节点/边
类型化与筛选，不重跑传播、不调模型、不改排名。
"""
from __future__ import annotations

from collections import deque

DISEASE_NODE_PREFIX = "disease:"


def build_typed_graph(network_store, evidence_store, disease_id: str, results: dict) -> dict:
    """构建完整类型化图（疾病 + 种子/扩展/背景节点 + 证据/关联边）。"""
    disease = evidence_store.disease(disease_id)
    disease_node = f"{DISEASE_NODE_PREFIX}{disease_id}"
    nodes = [{"id": disease_node, "type": "disease",
              "label": (disease or {}).get("name_zh", disease_id),
              "gene_id": None, "a_score": None, "n_score": None,
              "fusion_score": None, "status": None}]

    seed_meta = {s["node_id"]: s for s in results.get("seeds", []) if s.get("node_id")}
    extended_meta = {c["node_id"]: c for c in results.get("extended_candidates", []) if c.get("node_id")}

    for n in network_store.nodes():
        nid = n["id"]
        if nid in seed_meta:
            ntype, meta = "seed", seed_meta[nid]
        elif nid in extended_meta:
            ntype, meta = "extended", extended_meta[nid]
        else:
            ntype, meta = "background", {}
        nodes.append({
            "id": nid, "type": ntype, "label": n["symbol"], "gene_id": n.get("gene_id"),
            "a_score": meta.get("a_score"), "n_score": meta.get("n_score"),
            "fusion_score": meta.get("fusion_score"), "status": meta.get("status"),
        })

    edges = []
    # 证据边：疾病节点 → 有疾病证据的靶点节点
    for nid, meta in {**seed_meta, **extended_meta}.items():
        if meta.get("has_evidence") and meta.get("a_score") is not None:
            edges.append({"id": f"ev:{disease_id}:{nid}", "source": disease_node, "target": nid,
                          "type": "evidence", "score": meta["a_score"], "source_id": None,
                          "version": None})
    # 关联边：蛋白功能关联
    for e in network_store.edges():
        edges.append({"id": f"{e['source']}::{e['target']}", "source": e["source"],
                      "target": e["target"], "type": "association", "score": e["score"],
                      "source_id": None, "version": network_store.manifest.get("source_version")})

    return {"nodes": nodes, "edges": edges}


def _bfs_layers(adjacency: dict, seed_ids: set[str], max_layer: int) -> set[str]:
    """从种子出发计算层数不超过 max_layer 的节点集合。"""
    visited: set[str] = set()
    queue = deque((sid, 0) for sid in seed_ids if sid in adjacency)
    while queue:
        node, layer = queue.popleft()
        if node in visited or layer > max_layer:
            continue
        visited.add(node)
        for neighbor, _ in adjacency.get(node, []):
            if neighbor not in visited:
                queue.append((neighbor, layer + 1))
    return visited


def filter_view(graph: dict, adjacency: dict | None, *,
                threshold: float = 0.7, layers: int = 2,
                include_background: bool = False,
                max_nodes: int = 100, max_edges: int = 500) -> dict:
    """应用显示筛选：阈值、层数、背景开关与显示上限。"""
    seed_ids = {n["id"] for n in graph["nodes"] if n["type"] == "seed"}
    disease_ids = {n["id"] for n in graph["nodes"] if n["type"] == "disease"}

    keep_nodes = set(disease_ids)
    if adjacency is not None and seed_ids:
        keep_nodes |= _bfs_layers(adjacency, seed_ids, layers)
    else:
        keep_nodes |= {n["id"] for n in graph["nodes"] if n["type"] in ("seed", "extended")}

    # 先按阈值过滤关联边
    edges = [e for e in graph["edges"]
             if e["type"] == "evidence" or (e["type"] == "association" and e["score"] >= threshold)]

    nodes = []
    for n in graph["nodes"]:
        if n["type"] == "disease" or n["type"] == "seed" or n["type"] == "extended":
            nodes.append(n)
        elif n["type"] == "background" and include_background and n["id"] in keep_nodes:
            nodes.append(n)

    node_ids = {n["id"] for n in nodes}
    edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]

    total_nodes = len(nodes)
    total_edges = len(edges)
    truncated = total_nodes > max_nodes or total_edges > max_edges
    # 优先保留种子/扩展/疾病，再按边分值确定性裁剪
    priority = {"disease": 0, "seed": 1, "extended": 2, "background": 3}
    nodes.sort(key=lambda n: (priority.get(n["type"], 9), n["id"]))
    nodes = nodes[:max_nodes]
    keep = {n["id"] for n in nodes}
    edges = [e for e in edges if e["source"] in keep and e["target"] in keep]
    edges = sorted(edges, key=lambda e: (-e["score"], e["id"]))[:max_edges]

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "display_nodes": len(nodes),
        "display_edges": len(edges),
        "truncated": truncated,
        "threshold": threshold,
        "min_score": min((e["score"] for e in graph["edges"] if e["type"] == "association"), default=None),
    }
