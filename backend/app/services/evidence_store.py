"""本地靶点证据快照的加载与查询。

快照由 backend/scripts/import_target_evidence.py 从 Open Targets 生成，目录
backend/data/target_evidence/ 下含 manifest.json、diseases.json、targets.json、
evidence.json。加载时校验完整性；无效快照抛 EvidenceSnapshotError，不允许激活。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "target_evidence"
FILES = ("diseases.json", "targets.json", "evidence.json")


class EvidenceSnapshotError(Exception):
    """证据快照缺失或校验失败。"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_unique_ids(rows, label, required_fields):
    ids = set()
    for row in rows:
        missing = [f for f in required_fields if row.get(f) in (None, "")]
        if missing:
            raise EvidenceSnapshotError(f"{label} 记录缺少字段 {missing}")
        rid = row["id"]
        if rid in ids:
            raise EvidenceSnapshotError(f"{label} 存在重复 ID {rid}")
        ids.add(rid)
    return ids


def load_snapshot(data_dir: Path) -> dict:
    """读取并校验快照，返回 {manifest, diseases, targets, evidence}。"""
    manifest_path = data_dir / "manifest.json"
    if not manifest_path.is_file():
        raise EvidenceSnapshotError("缺少 manifest.json，快照未激活")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if not manifest.get("version"):
        raise EvidenceSnapshotError("manifest 缺少 version")
    supported = manifest.get("supported_datatypes")
    if not isinstance(supported, list) or not supported:
        raise EvidenceSnapshotError("supported_datatypes 为空，快照不可用")
    files = manifest.get("files") or {}
    for name in FILES:
        if name not in files:
            raise EvidenceSnapshotError(f"manifest.files 缺少 {name}")

    loaded = {}
    for name in FILES:
        path = data_dir / name
        if not path.is_file():
            raise EvidenceSnapshotError(f"缺少 {name}")
        if _sha256(path) != files[name]:
            raise EvidenceSnapshotError(f"{name} 校验值不匹配，快照可能被篡改")
        loaded[name.split(".")[0]] = json.loads(path.read_text(encoding="utf-8"))

    diseases, targets, evidence = loaded["diseases"], loaded["targets"], loaded["evidence"]
    disease_ids = _check_unique_ids(diseases, "diseases", {"id", "name_zh", "name"})
    target_ids = _check_unique_ids(targets, "targets", {"id", "symbol", "name"})
    _check_unique_ids(evidence, "evidence", {"id", "disease_id", "target_id", "datatype", "datasource"})

    for row in evidence:
        if row["disease_id"] not in disease_ids:
            raise EvidenceSnapshotError(f"证据 {row['id']} 引用不存在的疾病 {row['disease_id']}")
        if row["target_id"] not in target_ids:
            raise EvidenceSnapshotError(f"证据 {row['id']} 引用不存在的靶点 {row['target_id']}")
        if row["datatype"] not in supported:
            raise EvidenceSnapshotError(f"证据 {row['id']} 数据类型 {row['datatype']} 不在 supported_datatypes 中")
        score = row.get("score")
        if score is not None and not (isinstance(score, (int, float)) and 0 <= score <= 1):
            raise EvidenceSnapshotError(f"证据 {row['id']} 的 score 超出 [0,1] 范围")

    return {"manifest": manifest, "diseases": diseases, "targets": targets, "evidence": evidence}


class EvidenceStore:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self._snapshot = load_snapshot(self.data_dir)

    @property
    def manifest(self):
        return self._snapshot["manifest"]

    def diseases(self):
        return self._snapshot["diseases"]

    def disease(self, disease_id):
        for d in self._snapshot["diseases"]:
            if d["id"] == disease_id:
                return d
        return None

    def candidates(self, disease_id):
        """返回该疾病的候选靶点列表，附关联分与证据卡片。"""
        by_id = {t["id"]: t for t in self._snapshot["targets"]}
        by_target = {}
        for row in self._snapshot["evidence"]:
            if row["disease_id"] == disease_id:
                by_target.setdefault(row["target_id"], []).append(row)
        result = []
        for target_id, rows in by_target.items():
            target = by_id[target_id]
            result.append({
                **target,
                "association_score": (target.get("disease_scores") or {}).get(disease_id),
                "evidence": rows,
            })
        return result

    def evidence(self, disease_id, target_id=None):
        rows = [r for r in self._snapshot["evidence"] if r["disease_id"] == disease_id]
        if target_id is not None:
            rows = [r for r in rows if r["target_id"] == target_id]
        return rows
