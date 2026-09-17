"""动态 STRING 客户端：分析时按需拉取种子基因的蛋白功能关联网络。

不做本地快照；每次分析实时调用 STRING TSV 接口，构建本次分析的节点、边与邻接表。
接口文档：https://string-db.org/cgi/help?sessionId=...（TSV API）。
"""
from __future__ import annotations

import csv
import io
from collections import defaultdict

import httpx

BASE = "https://string-db.org/api/tsv"
SPECIES = 9606


class StringError(Exception):
    """STRING 请求失败。"""


def _tsv(resp: httpx.Response) -> list[dict]:
    text = resp.text
    first_line = text.splitlines()[0] if text.strip() else ""
    if first_line.startswith("#"):
        text = text.lstrip("#")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    return [row for row in reader]


def _post(client: httpx.Client, endpoint: str, params: dict) -> list[dict]:
    resp = client.post(f"{BASE}/{endpoint}", data=params, timeout=60.0)
    if resp.status_code != 200:
        raise StringError(f"STRING {endpoint} 返回 {resp.status_code}")
    return _tsv(resp)


def map_symbols(symbols: list[str]) -> dict[str, str]:
    """gene symbol -> STRING protein id；仅接受唯一映射，歧义映射忽略。"""
    if not symbols:
        return {}
    with httpx.Client(follow_redirects=True) as client:
        rows = _post(client, "get_string_ids",
                     {"identifiers": "\n".join(symbols), "species": SPECIES,
                      "limit": 1, "echo_query": 1})
    mapping: dict[str, str] = {}
    seen: set[str] = set()
    for row in rows:
        query = (row.get("queryItem") or "").strip()
        string_id = (row.get("stringId") or "").strip()
        if not query or not string_id:
            continue
        if query in seen:
            mapping.pop(query, None)
            continue
        seen.add(query)
        mapping[query] = string_id
    return mapping


def fetch_network(seed_id_to_symbol: dict[str, str], threshold: float = 0.7,
                  hops: int = 1, max_nodes: int = 200) -> dict:
    """拉取种子的一跳邻居与边，返回 {nodes, edges, adjacency}。

    seed_id_to_symbol: STRING protein id -> gene symbol（用于给种子节点命名）。
    """
    if not seed_id_to_symbol:
        return {"nodes": [], "edges": [], "adjacency": {}}

    seed_ids = list(seed_id_to_symbol.keys())
    required_score = int(round(threshold * 1000))
    neighbor_symbols: dict[str, str] = {}
    pool: set[str] = set(seed_ids)
    frontier: list[str] = seed_ids

    with httpx.Client(follow_redirects=True) as client:
        for _ in range(hops):
            rows = _post(client, "interaction_partners",
                         {"identifiers": "\n".join(frontier), "species": SPECIES,
                          "required_score": required_score, "limit": 30})
            next_frontier: list[str] = []
            for row in rows:
                a = (row.get("stringId_A") or "").strip()
                b = (row.get("stringId_B") or "").strip()
                score = float(row.get("score") or 0)
                name_b = (row.get("preferredName_B") or "").strip()
                if not a or not b or score < threshold:
                    continue
                neighbor_symbols[b] = name_b or b
                if b not in pool and len(pool) < max_nodes:
                    pool.add(b)
                    next_frontier.append(b)
            frontier = next_frontier
            if not frontier:
                break

        edges_rows = _post(client, "network",
                           {"identifiers": "\n".join(sorted(pool)), "species": SPECIES,
                            "required_score": required_score})

    edges: list[dict] = []
    for row in edges_rows:
        a = (row.get("stringId_A") or "").strip()
        b = (row.get("stringId_B") or "").strip()
        score = float(row.get("score") or 0)
        if not a or not b or a == b or score < threshold:
            continue
        if a not in pool or b not in pool:
            continue
        edges.append({"source": a, "target": b, "score": round(score, 4)})

    adjacency: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for e in edges:
        adjacency[e["source"]].append((e["target"], e["score"]))
        adjacency[e["target"]].append((e["source"], e["score"]))

    symbols: dict[str, str] = dict(neighbor_symbols)
    for sid, sym in seed_id_to_symbol.items():
        symbols[sid] = sym or sid

    nodes = [{"id": sid, "symbol": symbols.get(sid) or sid} for sid in pool]
    return {"nodes": nodes, "edges": edges, "adjacency": dict(adjacency)}
