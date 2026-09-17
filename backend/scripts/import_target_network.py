"""从 STRING 构建围绕证据候选的两跳蛋白功能关联子图快照。

用法（在 backend/ 目录下，需已先生成证据快照）：
    python -m scripts.import_target_network --threshold 0.7 --hops 2

流程：
  1. 读取 target_evidence/targets.json 的候选基因（ENSG）。
  2. 通过 get_string_ids 将 ENSG 映射到代表蛋白（STRING id）。
  3. 用 interaction_partners 扩展一跳、两跳邻居。
  4. 用 network 获取这些蛋白之间的关联边。
  5. 规范化分值到 0~1、去自环、去重、按上限裁剪。
  6. 写 nodes.json / edges.json / manifest.json 并激活校验。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import httpx

BASE = "https://string-db.org/api/tsv"
SPECIES = 9606
EVIDENCE_DIR = Path(__file__).resolve().parents[1] / "data" / "target_evidence"
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "target_network"
SOURCE_URL = "https://string-db.org/"
LICENSE = "CC BY 4.0"
STRING_VERSION = "12.0"


def _tsv(resp: httpx.Response) -> list[dict]:
    text = resp.text
    # STRING 表头有时带 "#" 前缀，统一去掉。
    first_line = text.splitlines()[0] if text.strip() else ""
    if first_line.startswith("#"):
        text = text.lstrip("#")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    return [row for row in reader]


def _post(client: httpx.Client, endpoint: str, params: dict) -> list[dict]:
    """STRING 的 TSV 接口支持 POST，避免大量标识符导致 GET URL 过长。"""
    resp = client.post(f"{BASE}/{endpoint}", data=params, timeout=120.0)
    resp.raise_for_status()
    return _tsv(resp)


def load_seed_genes() -> list[dict]:
    targets_path = EVIDENCE_DIR / "targets.json"
    if not targets_path.is_file():
        raise RuntimeError("缺少证据快照 targets.json，请先运行 import_target_evidence")
    targets = json.loads(targets_path.read_text(encoding="utf-8"))
    return [{"gene_id": t["id"], "symbol": t["symbol"], "name": t["name"],
             "aliases": t.get("aliases", [])} for t in targets]


def map_to_string(client: httpx.Client, genes: list[dict]) -> dict:
    """ENSG -> {string_id, symbol} 映射；歧义/未映射基因返回时忽略。"""
    identifiers = "\n".join(g["gene_id"] for g in genes)
    rows = _post(client, "get_string_ids",
                 {"identifiers": identifiers, "species": SPECIES, "limit": 1, "echo_query": 1})
    mapping = {}
    ambiguous = []
    for row in rows:
        query = (row.get("queryItem") or "").strip()
        string_id = (row.get("stringId") or "").strip()
        if not query or not string_id:
            continue
        # 一个查询项可能映射到多个 STRING id（歧义），只接受唯一代表蛋白。
        if query in mapping:
            ambiguous.append(query)
        else:
            mapping[query] = {"string_id": string_id,
                              "symbol": (row.get("preferredName") or "").strip()}
    for q in ambiguous:
        mapping.pop(q, None)
    return mapping


def fetch_partners(client: httpx.Client, string_ids: list[str], threshold: float) -> dict:
    """STRING id -> {neighbors: {string_id: {symbol, score}}}。

    注意：STRING REST API 的 required_score 参数为 0~1000，但响应 score 字段为 0~1。
    """
    required_score = int(round(threshold * 1000))
    result = defaultdict(dict)
    rows = _post(client, "interaction_partners",
                 {"identifiers": "\n".join(string_ids), "species": SPECIES,
                  "required_score": required_score, "limit": 30})
    for row in rows:
        a = (row.get("stringId_A") or "").strip()
        b = (row.get("stringId_B") or "").strip()
        score = float(row.get("score") or 0)
        name_b = (row.get("preferredName_B") or "").strip()
        if not a or not b or score < threshold:
            continue
        result[a][b] = {"symbol": name_b, "score": round(score, 4)}
    return result


def fetch_edges(client: httpx.Client, string_ids: list[str], threshold: float) -> list[dict]:
    required_score = int(round(threshold * 1000))
    edges = []
    rows = _post(client, "network",
                 {"identifiers": "\n".join(string_ids), "species": SPECIES,
                  "required_score": required_score})
    for row in rows:
        a = (row.get("stringId_A") or "").strip()
        b = (row.get("stringId_B") or "").strip()
        score = float(row.get("score") or 0)
        if not a or not b or a == b or score < threshold:
            continue
        edges.append({
            "source": a,
            "target": b,
            "string_score": round(score * 1000),
            "score": round(score, 4),
            "channels": {
                "neighborhood": round(float(row.get("nscore") or 0), 4),
                "fusion": round(float(row.get("fscore") or 0), 4),
                "cooccurrence": round(float(row.get("pscore") or 0), 4),
                "coexpression": round(float(row.get("ascore") or 0), 4),
                "experimental": round(float(row.get("escore") or 0), 4),
                "database": round(float(row.get("dscore") or 0), 4),
                "textmining": round(float(row.get("tscore") or 0), 4),
            },
        })
    return edges


def dedup_edges(edges: list[dict]) -> list[dict]:
    """去自环、去重复无向边（保留更高分值）。"""
    best = {}
    for e in edges:
        key = tuple(sorted((e["source"], e["target"])))
        if key not in best or e["score"] > best[key]["score"]:
            best[key] = e
    return list(best.values())


def build_snapshot(threshold: float, hops: int, max_nodes: int, max_edges: int):
    genes = load_seed_genes()
    with httpx.Client(follow_redirects=True) as client:
        mapping = map_to_string(client, genes)
        if not mapping:
            raise RuntimeError("没有任何候选基因能映射到 STRING 蛋白")
        seed_nodes = {}
        for g in genes:
            m = mapping.get(g["gene_id"])
            if m:
                seed_nodes[m["string_id"]] = {"gene_id": g["gene_id"],
                                              "symbol": g["symbol"], "name": g["name"]}

        # 两跳扩展
        frontier = list(seed_nodes.keys())
        neighbor_pool = set(seed_nodes.keys())
        partner_names: dict[str, str] = {}
        for hop in range(hops):
            partners = fetch_partners(client, frontier, threshold)
            next_frontier = []
            for a, nbrs in partners.items():
                for b, meta in nbrs.items():
                    partner_names[b] = meta["symbol"]
                    if b not in neighbor_pool:
                        neighbor_pool.add(b)
                        next_frontier.append(b)
                        if len(neighbor_pool) >= max_nodes:
                            break
                if len(neighbor_pool) >= max_nodes:
                    break
            frontier = next_frontier
            if not frontier or len(neighbor_pool) >= max_nodes:
                break

        # 仅取与证据候选同名的背景节点来解析 gene_id（其余为探索性节点）。
        symbol_to_gene: dict[str, str] = {}
        name_to_gene: dict[str, str] = {}
        for g in genes:
            symbol_to_gene[g["symbol"].lower()] = g["gene_id"]
            name_to_gene[g["name"].lower()] = g["gene_id"]
            for a in g["aliases"]:
                symbol_to_gene[a.lower()] = g["gene_id"]

        edges = dedup_edges(fetch_edges(client, sorted(neighbor_pool), threshold))
        edge_nodes = {e["source"] for e in edges} | {e["target"] for e in edges}

        nodes = {}
        for sid in edge_nodes:
            if sid in seed_nodes:
                nodes[sid] = dict(seed_nodes[sid])
            else:
                symbol = partner_names.get(sid, "")
                gene_id = symbol_to_gene.get(symbol.lower())
                nodes[sid] = {"gene_id": gene_id, "symbol": symbol or sid, "name": None}

        # 优先保留种子及其邻居，再按边分值确定性裁剪。
        ordered = sorted(nodes.keys(), key=lambda n: (0 if n in seed_nodes else 1, n))
        keep = set(ordered[:max_nodes])
        edges = [e for e in edges if e["source"] in keep and e["target"] in keep]
        edges = sorted(edges, key=lambda e: (-e["score"], e["source"], e["target"]))[:max_edges]
        keep_edges = {e["source"] for e in edges} | {e["target"] for e in edges}

        final_nodes = []
        for sid in ordered:
            if sid in keep and (sid in keep_edges or sid in seed_nodes):
                n = nodes[sid]
                final_nodes.append({"id": sid, "gene_id": n["gene_id"],
                                    "symbol": n["symbol"], "name": n["name"]})

    ambiguous = [g["gene_id"] for g in genes if g["gene_id"] not in mapping]
    return {"nodes": final_nodes, "edges": edges, "ambiguous_mappings": ambiguous,
            "threshold": threshold, "hops": hops}


def _write_files(data_dir: Path, snapshot: dict):
    data_dir.mkdir(parents=True, exist_ok=True)
    contents = {
        "nodes.json": json.dumps(snapshot["nodes"], ensure_ascii=False, indent=2),
        "edges.json": json.dumps(snapshot["edges"], ensure_ascii=False, indent=2),
    }
    manifest = {
        "version": "1",
        "fetch_date": date.today().isoformat(),
        "source": "STRING",
        "source_version": STRING_VERSION,
        "source_url": SOURCE_URL,
        "api_endpoint": BASE,
        "license": LICENSE,
        "species": SPECIES,
        "threshold": snapshot["threshold"],
        "hops": snapshot["hops"],
        "ambiguous_mappings": snapshot["ambiguous_mappings"],
        "score_semantics": "edges[].score 为 STRING combined_score 归一化到 0~1 的功能关联置信分，"
                           "表示功能关联概率估计，不等于物理结合、药理效应或疾病因果关系；"
                           "channels 为各证据渠道归一化分值",
        "files": {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
                  for name, text in contents.items()},
    }
    contents["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2)
    for name, text in contents.items():
        (data_dir / name).write_bytes(text.encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="从 STRING 导入蛋白功能关联子图快照")
    parser.add_argument("--threshold", type=float, default=0.7, help="保留边的置信分阈值（0~1）")
    parser.add_argument("--hops", type=int, default=2, help="围绕候选扩展的跳数")
    parser.add_argument("--max-nodes", type=int, default=2000, help="节点数上限")
    parser.add_argument("--max-edges", type=int, default=20000, help="边数上限")
    parser.add_argument("--out", type=Path, default=DATA_DIR, help="输出目录")
    args = parser.parse_args()

    snapshot = build_snapshot(args.threshold, args.hops, args.max_nodes, args.max_edges)
    _write_files(args.out, snapshot)

    from app.services.network_store import load_snapshot  # 激活前校验
    load_snapshot(args.out)
    print(f"网络快照已激活：节点 {len(snapshot['nodes'])}，边 {len(snapshot['edges'])}，"
          f"歧义映射 {len(snapshot['ambiguous_mappings'])} 个")


if __name__ == "__main__":
    main()
