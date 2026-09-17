"""图展示数据：由分析结果的动态网络构建类型化节点/边，做阈值/层数筛选。

计算与显示分离：图算法只用于分析时的传播；本模块只做展示层的节点/边
类型化与筛选，不重跑传播、不调模型、不改排名。
"""
from __future__ import annotations

from collections import defaultdict, deque


def build_typed_graph(results: dict) -> dict:
    """从 results 的动态网络构建类型化图（种子/扩展/背景节点 + 关联边）。"""
    net = results.get("network") or {"nodes": [], "edges": []}
    seed_meta = {s["node_id"]: s for s in results.get("seeds", []) if s.get("node_id")}
    extended_meta = {c["node_id"]: c for c in results.get("extended_candidates", []) if c.get("node_id")}

    nodes = []
    for n in net["nodes"]:
        nid = n["id"]
        if nid in seed_meta:
            ntype, meta = "seed", seed_meta[nid]
        elif nid in extended_meta:
            ntype, meta = "extended", extended_meta[nid]
        else:
            ntype, meta = "background", {}
        nodes.append({
            "id": nid, "type": ntype, "label": n.get("symbol") or nid, "gene_id": None,
            "n_score": meta.get("n_score"), "relevance_score": meta.get("relevance_score"),
        })

    edges = [
        {"id": f"{e['source']}::{e['target']}", "source": e["source"], "target": e["target"],
         "type": "association", "score": e["score"], "source_id": None, "version": None}
        for e in net["edges"]
    ]
    return {"nodes": nodes, "edges": edges}


def adjacency_from_edges(edges: list[dict]) -> dict[str, list[tuple[str, float]]]:
    """由边列表构建无向邻接表。"""
    adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for e in edges:
        adj[e["source"]].append((e["target"], e["score"]))
        adj[e["target"]].append((e["source"], e["score"]))
    return dict(adj)


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

    keep_nodes: set[str] = set()
    if adjacency is not None and seed_ids:
        keep_nodes |= _bfs_layers(adjacency, seed_ids, layers)
    else:
        keep_nodes |= {n["id"] for n in graph["nodes"] if n["type"] in ("seed", "extended")}

    edges = [e for e in graph["edges"] if e["type"] == "association" and e["score"] >= threshold]

    nodes = []
    for n in graph["nodes"]:
        if n["type"] in ("seed", "extended"):
            nodes.append(n)
        elif n["type"] == "background" and include_background and n["id"] in keep_nodes:
            nodes.append(n)

    node_ids = {n["id"] for n in nodes}
    edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]

    total_nodes = len(nodes)
    total_edges = len(edges)
    truncated = total_nodes > max_nodes or total_edges > max_edges
    priority = {"seed": 0, "extended": 1, "background": 2}
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
