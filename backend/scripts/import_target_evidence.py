"""从 Open Targets 平台导入单个疾病的靶点证据快照。

用法（在 backend/ 目录下）：
    python -m scripts.import_target_evidence --disease MONDO_0004975 --name-zh 阿尔茨海默病
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

import httpx

ENDPOINT = "https://api.platform.opentargets.org/api/v4/graphql"
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "target_evidence"
SOURCE_URL = "https://platform.opentargets.org/"
LICENSE = "CC BY 4.0"

DISEASE_QUERY = """
query DiseaseTargets($diseaseId: String!, $size: Int!) {
  disease(efoId: $diseaseId) {
    id
    name
    associatedTargets(page: {index: 0, size: $size}) {
      rows {
        score
        target {
          id
          approvedSymbol
          approvedName
          synonyms { label source }
          proteinIds { id source }
        }
      }
    }
  }
}
"""

EVIDENCE_QUERY = """
query Evidence($diseaseId: String!, $targetId: String!, $size: Int!) {
  disease(efoId: $diseaseId) {
    evidences(size: $size, ensemblIds: [$targetId]) {
      rows {
        id
        score
        datatypeId
        datasourceId
        targetFromSourceId
        diseaseFromSource
        literature
        resourceScore
        target { id }
        disease { id }
      }
    }
  }
}
"""


def _gql(client, query, variables):
    resp = client.post(ENDPOINT, json={"query": query, "variables": variables})
    resp.raise_for_status()
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(f"GraphQL 错误：{payload['errors']}")
    return payload["data"]


def _uniprot(protein_ids):
    for source in ("uniprot_swissprot", "uniprot_trembl"):
        for p in protein_ids or []:
            if p.get("source") == source:
                return p["id"]
    return None


def _summary(datatype, datasource, literature, disease_from_source):
    parts = [f"{datatype} 证据（{datasource}）"]
    if literature:
        parts.append("PMID " + ", ".join(literature))
    elif disease_from_source:
        parts.append(str(disease_from_source))
    return "；".join(parts)


def build_snapshot(disease_id, name_zh, n_targets, n_evidence):
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        disease_data = _gql(client, DISEASE_QUERY,
                            {"diseaseId": disease_id, "size": n_targets})["disease"]
        if disease_data is None:
            raise RuntimeError(f"未找到疾病 {disease_id}")
        rows = disease_data["associatedTargets"]["rows"]

        diseases = [{"id": disease_id, "source_id": disease_id, "name_zh": name_zh,
                     "name": disease_data["name"], "aliases": []}]

        targets, evidence = [], []
        for row in rows:
            t = row["target"]
            targets.append({
                "id": t["id"],
                "symbol": t["approvedSymbol"],
                "name": t["approvedName"],
                "aliases": [s["label"] for s in (t.get("synonyms") or [])
                            if s.get("label") and s.get("label") != t["approvedSymbol"]],
                "uniprot_id": _uniprot(t.get("proteinIds")),
                "disease_scores": {disease_id: row["score"]},
            })

            ev_rows = _gql(client, EVIDENCE_QUERY,
                           {"diseaseId": disease_id, "targetId": t["id"], "size": n_evidence * 5}) \
                ["disease"]["evidences"]["rows"]
            # Open Targets 会返回映射到子疾病（如 MONDO_0011913）的证据；快照只含一个疾病，
            # 故只保留疾病标识与查询疾病一致的证据，避免悬空引用。
            ev_rows = [e for e in ev_rows if e["disease"]["id"] == disease_id]
            ev_rows = sorted(ev_rows, key=lambda r: -(r.get("score") or 0))[:n_evidence]
            for e in ev_rows:
                lit = e.get("literature") or []
                evidence.append({
                    "id": e["id"],
                    "disease_id": e["disease"]["id"],
                    "target_id": e["target"]["id"],
                    "datatype": e["datatypeId"],
                    "datasource": e["datasourceId"],
                    "source_id": ("PMID:" + lit[0]) if lit else (e.get("targetFromSourceId") or ""),
                    "summary": _summary(e["datatypeId"], e["datasourceId"], lit, e.get("diseaseFromSource")),
                    "score": e.get("score"),
                    "resource_score": e.get("resourceScore"),
                    "date": None,
                })

    supported = sorted({e["datatype"] for e in evidence})
    return {"diseases": diseases, "targets": targets, "evidence": evidence,
            "supported_datatypes": supported}


def _merge_snapshot(existing: dict, new: dict) -> dict:
    """把新疾病快照合并进现有快照，按稳定 ID 去重。"""
    disease_ids = {d["id"] for d in existing["diseases"]}
    new_diseases = [d for d in new["diseases"] if d["id"] not in disease_ids]

    # 合并靶点：同一基因出现在多个疾病时，合并 disease_scores 与别名
    targets = {t["id"]: t for t in existing["targets"]}
    for t in new["targets"]:
        if t["id"] in targets:
            old = targets[t["id"]]
            old.setdefault("disease_scores", {}).update(t.get("disease_scores", {}))
            aliases = old.setdefault("aliases", [])
            for a in t.get("aliases", []):
                if a not in aliases:
                    aliases.append(a)
        else:
            targets[t["id"]] = t

    # 合并证据：按证据 ID 去重
    evidence = {e["id"]: e for e in existing["evidence"]}
    for e in new["evidence"]:
        evidence.setdefault(e["id"], e)

    supported = sorted({e["datatype"] for e in evidence.values()})
    return {
        "diseases": existing["diseases"] + new_diseases,
        "targets": list(targets.values()),
        "evidence": list(evidence.values()),
        "supported_datatypes": supported,
    }


def _write_files(data_dir, snapshot):
    data_dir.mkdir(parents=True, exist_ok=True)
    contents = {
        "diseases.json": json.dumps(snapshot["diseases"], ensure_ascii=False, indent=2),
        "targets.json": json.dumps(snapshot["targets"], ensure_ascii=False, indent=2),
        "evidence.json": json.dumps(snapshot["evidence"], ensure_ascii=False, indent=2),
    }
    manifest = {
        "version": "1",
        "fetch_date": date.today().isoformat(),
        "source": "Open Targets Platform",
        "source_url": SOURCE_URL,
        "api_endpoint": ENDPOINT,
        "license": LICENSE,
        "supported_datatypes": snapshot["supported_datatypes"],
        "score_semantics": "evidence.score 为 Open Targets 0~1 归一化关联分；resource_score 为数据源原始分值，"
                           "含义因数据源而异；targets[].disease_scores 为疾病—靶点总体关联分（0~1）",
        "files": {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
                  for name, text in contents.items()},
    }
    contents["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2)
    for name, text in contents.items():
        # 用 write_bytes 避免 Windows 下换行符被翻译成 CRLF，导致 manifest 哈希与文件不一致
        (data_dir / name).write_bytes(text.encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="从 Open Targets 导入靶点证据快照")
    parser.add_argument("--disease", required=True, help="疾病稳定 ID（如 MONDO_0004975）")
    parser.add_argument("--name-zh", required=True, help="疾病中文展示名")
    parser.add_argument("--targets", type=int, default=40, help="候选靶点数量上限")
    parser.add_argument("--evidence-per-target", type=int, default=10, help="每靶点证据数量上限")
    parser.add_argument("--merge", action="store_true", help="合并进现有快照（默认覆盖）")
    parser.add_argument("--out", type=Path, default=DATA_DIR, help="输出目录")
    args = parser.parse_args()

    from app.services.evidence_store import EvidenceSnapshotError, load_snapshot  # noqa: E402

    snapshot = build_snapshot(args.disease, args.name_zh, args.targets, args.evidence_per_target)

    if args.merge:
        try:
            existing = load_snapshot(args.out)
        except EvidenceSnapshotError:
            existing = {"diseases": [], "targets": [], "evidence": []}
        snapshot = _merge_snapshot(existing, snapshot)

    _write_files(args.out, snapshot)

    load_snapshot(args.out)  # 激活前校验
    print(f"快照已激活：疾病 {len(snapshot['diseases'])} 个，候选 {len(snapshot['targets'])}，"
          f"证据 {len(snapshot['evidence'])} 条，类型 {snapshot['supported_datatypes']}")


if __name__ == "__main__":
    main()
