"""证据核查：校验种子/扩展候选的结构、标识与引用归属。

对模型种子：检查是否来自候选池、按稳定标识去重、引用是否存在且关联当前疾病与靶点；
对网络扩展候选：检查是否来自固定网络、独立匹配疾病证据。
状态标记：引用匹配通过 / 部分引用无效 / 缺少可核查依据 / 标识不一致。
"""
from __future__ import annotations

MAX_REASON_LEN = 800


def _status_parts(valid: list, invalid: list) -> str:
    if not valid and not invalid:
        return "missing"  # 缺少可核查依据
    if invalid and not valid:
        return "missing"
    if invalid:
        return "partial"  # 部分引用无效
    return "passed"  # 引用匹配通过


def validate_seeds(seeds: list[dict], evidence_store, disease_id: str) -> list[dict]:
    """校验模型返回的种子列表。"""
    pool = {c["id"]: c for c in evidence_store.candidates(disease_id)}
    pool_evidence_ids = {tid: {e["id"] for e in c.get("evidence", [])} for tid, c in pool.items()}

    result = []
    seen = set()
    for seed in seeds:
        target_id = seed.get("target_id") or ""
        field_errors = []
        if len(seed.get("reason") or "") > MAX_REASON_LEN:
            field_errors.append("reason 超长")

        if not target_id or target_id not in pool:
            result.append({
                **seed,
                "in_pool": False,
                "valid_evidence_ids": [],
                "invalid_evidence_ids": [],
                "status": "id_mismatch",
                "status_label": "标识不一致",
                "field_errors": field_errors,
            })
            continue

        if target_id in seen:
            continue  # 按稳定标识去重
        seen.add(target_id)

        evidence_ids = [str(e) for e in (seed.get("evidence_ids") or [])]
        valid_ids = [e for e in evidence_ids if e in pool_evidence_ids[target_id]]
        invalid_ids = [e for e in evidence_ids if e not in pool_evidence_ids[target_id]]

        result.append({
            **seed,
            "in_pool": True,
            "valid_evidence_ids": valid_ids,
            "invalid_evidence_ids": invalid_ids,
            "status": _status_parts(valid_ids, invalid_ids),
            "status_label": {
                "passed": "引用匹配通过",
                "partial": "部分引用无效",
                "missing": "缺少可核查依据",
            }[_status_parts(valid_ids, invalid_ids)],
            "field_errors": field_errors,
        })
    return result


def validate_extended(candidates: list[dict], evidence_store, network_store, disease_id: str) -> list[dict]:
    """校验网络扩展候选：确认在固定网络中，并独立匹配疾病证据。

    candidates 为网络节点（含 gene_id 字段）。gene_id 能匹配疾病证据的标记为有证据，
    否则为探索性候选（A 缺失，不填零）。
    """
    disease_evidence = {}
    for e in evidence_store.evidence(disease_id):
        disease_evidence.setdefault(e["target_id"], []).append(e)

    result = []
    for cand in candidates:
        node_id = cand.get("id") or cand.get("target_id")
        gene_id = cand.get("gene_id")
        in_network = network_store.has_node(node_id) if network_store is not None else True
        evidence = disease_evidence.get(gene_id) if gene_id else []
        result.append({
            "target_id": gene_id or node_id,
            "node_id": node_id,
            "gene_id": gene_id,
            "in_network": in_network,
            "has_evidence": bool(evidence),
            "evidence": evidence,
        })
    return result
