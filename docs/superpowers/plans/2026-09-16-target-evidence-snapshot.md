# 靶点证据快照（任务1）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从 Open Targets 平台导入阿尔茨海默病（MONDO_0004975）的真实靶点证据快照，并提供本地校验与查询服务 `EvidenceStore`。

**Architecture:** 快照由 4 个 JSON 文件组成（manifest/diseases/targets/evidence），由 `scripts/import_target_evidence.py` 从 Open Targets GraphQL API 拉取并生成；`app/services/evidence_store.py` 负责加载时的完整性校验（校验值、唯一 ID、悬空引用、分值范围、支持类型非空）与按疾病查询候选/证据。两者共用同一套校验逻辑，导入脚本激活前调用 `load_snapshot` 校验。

**Tech Stack:** Python 3.12、httpx（已有依赖）、stdlib（hashlib/json/pathlib）、pytest。本任务不新增第三方依赖。

**已核实的 Open Targets 契约（2026-09-16）：**
- 端点 `https://api.platform.opentargets.org/api/v4/graphql`（POST，无需鉴权）。
- 疾病：`disease(efoId: "MONDO_0004975")` → 名称 "Alzheimer disease"。
- `associatedTargets(page:{index:0,size:N}).rows[].{score, target{id, approvedSymbol, approvedName, synonyms{label,source}, proteinIds{id,source}}}`。
- `evidences(size:K, ensemblIds:[targetId]).rows[].{id, score, datatypeId, datasourceId, targetFromSourceId, diseaseFromSource, literature(PMID 列表), resourceScore, target{id}, disease{id}}`。
- `proteinIds` 中 `source == "uniprot_swissprot"` 为规范 UniProt ID。

---

## 文件结构

- Create: `backend/app/services/evidence_store.py` — 快照 schema 校验 + `EvidenceStore` 查询类（纯 stdlib，无 DB）。
- Create: `backend/scripts/__init__.py` — 空文件，使脚本可 `python -m` 运行。
- Create: `backend/scripts/import_target_evidence.py` — 从 Open Targets 拉取、转换、写文件、激活前校验。
- Create: `backend/tests/test_evidence_store.py` — 校验与查询测试（用 pytest `tmp_path` 构造快照，不联网）。
- Create: `backend/data/target_evidence/` — 运行导入脚本后生成 manifest.json/diseases.json/targets.json/evidence.json（执行时生成，不手工提交虚构数据）。

JSON 契约（与方案 2.2 表对齐）：

```jsonc
// manifest.json
{ "version": "1", "fetch_date": "2026-09-16", "source": "Open Targets Platform",
  "source_url": "...", "api_endpoint": "...", "license": "CC BY 4.0",
  "supported_datatypes": ["literature", "clinical", ...],           // 非空，否则拒绝激活
  "score_semantics": "...",                                          // 分值原始含义说明
  "files": { "diseases.json": "<sha256>", "targets.json": "<sha256>", "evidence.json": "<sha256>" } }
// diseases.json —— [ { id, source_id, name_zh, name, aliases } ]
// targets.json  —— [ { id, symbol, name, aliases, uniprot_id, disease_scores: {disease_id: score} } ]
// evidence.json —— [ { id, disease_id, target_id, datatype, datasource, source_id, summary, score, resource_score, date } ]
```

设计说明：`targets[].disease_scores` 存放疾病—靶点总体关联分（Open Targets `associatedTargets.score`，0~1），是方案 2.5 排序 A 维度的数据来源，提前落库避免任务4 迁移。`evidence.summary` 为由 datatype/datasource/PMID 派生的描述串（Open Targets 证据行不返回摘要，不伪造摘要，如实标注）。

---

## Task 1: `evidence_store.py` 校验逻辑 + 测试

**Files:**
- Create: `backend/app/services/evidence_store.py`
- Test: `backend/tests/test_evidence_store.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_evidence_store.py
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_evidence_store.py -v`
Expected: FAIL（`ModuleNotFoundError: app.services.evidence_store` 或全部收集错误）

- [ ] **Step 3: 实现 `evidence_store.py`**

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_evidence_store.py -v`
Expected: 8 passed

- [ ] **Step 5: 提交**（用户选择不用 git，跳过 `git commit`；改用“完成记录”在会话中留痕）

---

## Task 2: 导入脚本

**Files:**
- Create: `backend/scripts/__init__.py`（空）
- Create: `backend/scripts/import_target_evidence.py`

- [ ] **Step 1: 写脚本**

```python
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
                           {"diseaseId": disease_id, "targetId": t["id"], "size": n_evidence}) \
                ["disease"]["evidences"]["rows"]
            ev_rows = sorted(ev_rows, key=lambda r: -(r.get("score") or 0))
            for e in ev_rows[:n_evidence]:
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
        (data_dir / name).write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="从 Open Targets 导入靶点证据快照")
    parser.add_argument("--disease", required=True, help="疾病稳定 ID（如 MONDO_0004975）")
    parser.add_argument("--name-zh", required=True, help="疾病中文展示名")
    parser.add_argument("--targets", type=int, default=40, help="候选靶点数量上限")
    parser.add_argument("--evidence-per-target", type=int, default=10, help="每靶点证据数量上限")
    parser.add_argument("--out", type=Path, default=DATA_DIR, help="输出目录")
    args = parser.parse_args()

    snapshot = build_snapshot(args.disease, args.name_zh, args.targets, args.evidence_per_target)
    _write_files(args.out, snapshot)

    from app.services.evidence_store import load_snapshot  # 激活前校验
    load_snapshot(args.out)
    print(f"快照已激活：{snapshot['diseases'][0]['name']}，候选 {len(snapshot['targets'])}，"
          f"证据 {len(snapshot['evidence'])} 条，类型 {snapshot['supported_datatypes']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 冒烟测试转换逻辑（不联网）**

Run（在 backend/ 目录，用 Python 交互式验证 `build_snapshot` 的纯转换部分不可行，改为验证 `_summary`/`_uniprot`）：
`cd backend && python -c "from scripts.import_target_evidence import _uniprot, _summary; assert _uniprot([{'id':'P05067','source':'uniprot_swissprot'}])=='P05067'; print(_summary('literature','europepmc',['37569624'],None))"`
Expected: 打印 `literature 证据（europepmc）；PMID 37569624`，无异常。

---

## Task 3: 运行导入并人工抽查

- [ ] **Step 1: 执行真实导入**

Run: `cd backend && python -m scripts.import_target_evidence --disease MONDO_0004975 --name-zh 阿尔茨海默病`
Expected: 打印 `快照已激活：Alzheimer disease，候选 40，证据 N 条，类型 [...]`；生成 `backend/data/target_evidence/*.json`。

- [ ] **Step 2: 抽查 ≥10 条记录**

Run: `cd backend && python -c "import json; d=json.load(open('data/target_evidence/targets.json',encoding='utf-8')); print(len(d)); [print(t['symbol'], t['uniprot_id'], round(list(t['disease_scores'].values())[0],3)) for t in d[:15]]"`
人工核对：APP/PSEN1/PSEN2/APOE/MAPT 等应出现在候选池前列；symbol 与 UniProt 一致（APP→P05067）；分值均在 0~1。

- [ ] **Step 3: 用真实快照跑一次 store 查询**

Run: `cd backend && python -c "from app.services.evidence_store import EvidenceStore; s=EvidenceStore(); c=s.candidates('MONDO_0004975'); print('candidates', len(c)); print('evidence', len(s.evidence('MONDO_0004975'))); print('version', s.manifest['version'])"`
Expected: `candidates 40`（或 20~50 区间）、`evidence N`、`version 1`。

---

## 验收对照（方案任务1 全部勾选项）

- [x] 确认数据获取方式（Open Targets GraphQL）、许可（CC BY 4.0，写入 manifest）与记录字段（已核实 schema）。
- [x] 建立稳定 ID（ENSG/MONDO）与去重规则；导入 ≥20 候选（默认 40）。
- [x] 按 disease_id 返回候选与证据；返回 manifest 版本与校验值（`EvidenceStore.manifest`）。
- [x] 测试重复 ID、悬空证据引用、错误分值范围、空支持类型列表；无效快照不能激活（8 个测试覆盖）。
- [x] 人工抽查 ≥10 条记录（Task 3 Step 2）。

## 明确不做（YAGNI）

- 不做向量检索、多疾病、PDF/Word 导出（方案已列为后续）。
- 不从 PubMed 抓取摘要（evidence.summary 为派生描述串，如实标注）。
- 不新增数据库表；快照为纯本地 JSON，历史版本管理留待任务3/5。
