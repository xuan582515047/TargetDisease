"""轻量版靶点分析后台执行器。

串联：加载证据与网络 → 模型识别 → 种子核查 → 网络传播 → 扩展候选核查 →
稳定性 → 报告。使用 FastAPI BackgroundTasks 单进程后台任务，独立建立数据库会话。
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from app.core import encryption
from app.db.models import AnalysisRun, LlmProvider, RunStatus, UserLlmCredential
from app.db.session import SessionLocal
from app.services import evidence_validation as ev
from app.services import network_propagation as np
from app.services import network_stability as ns
from app.services import target_identification as ti
from app.services import target_ranking as tr
from app.services.evidence_store import EvidenceStore
from app.services.network_store import NetworkSnapshotError, NetworkStore
from app.services.target_report import render_csv, render_markdown

WORKFLOW_VERSION = "target-network-v1"
PROMPT_VERSION = ti.PROMPT_VERSION

GLOBAL_MAX_ACTIVE = 10
GLOBAL_MAX_MODEL_CONCURRENT = 2
TOTAL_TIMEOUT_SECONDS = 300

_MODEL_SEMAPHORE = threading.Semaphore(GLOBAL_MAX_MODEL_CONCURRENT)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def execute(run_id: uuid.UUID, api_key: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(AnalysisRun, run_id)
        if run is None:
            return
        run.status = RunStatus.running
        run.started_at = datetime.now(timezone.utc)
        db.commit()

        input_data = run.intermediate_json or {}
        disease_id = input_data["disease_id"]
        question = input_data["question"]
        mechanism_keywords = input_data.get("mechanism_keywords", [])

        evidence_store, network_store, disease = _load_evidence_network(disease_id)

        # 1. 模型识别
        cards, truncated = ti.build_candidate_cards(evidence_store, disease_id)
        with _MODEL_SEMAPHORE:
            identification = ti.identify(question, disease, cards, api_key, mechanism_keywords)

        # 2. 种子核查
        seeds = ev.validate_seeds(identification.candidates, evidence_store, disease_id)

        # 3. 网络映射与传播
        a_by_gene = {c["id"]: c.get("association_score") for c in evidence_store.candidates(disease_id)}
        nodes = network_store.nodes() if network_store else []
        node_by_gene = {n["gene_id"]: n for n in nodes if n.get("gene_id")}

        for s in seeds:
            node = node_by_gene.get(s["target_id"])
            s["node_id"] = node["id"] if node else None
            s["a_score"] = a_by_gene.get(s["target_id"])
            s["symbol"] = s.get("symbol") or (node or {}).get("symbol")
            s["in_network"] = s["node_id"] is not None

        seed_node_ids = [s["node_id"] for s in seeds if s["node_id"]]

        propagation = None
        extended = []
        n_scores: dict = {}
        network_error = None
        if network_store is not None and seed_node_ids:
            try:
                propagation = np.propagate(network_store.adjacency(), seed_node_ids)
                n_scores = propagation.normalized_scores
                raw_extended = []
                for c in propagation.extended_candidates:
                    node = network_store.node(c["node_id"]) or {}
                    raw_extended.append({"id": c["node_id"], "node_id": c["node_id"],
                                         "gene_id": node.get("gene_id"),
                                         "symbol": node.get("symbol"),
                                         "n_score": c["n_score"]})
                extended = ev.validate_extended(raw_extended, evidence_store, network_store, disease_id)
                for e in extended:
                    e["a_score"] = a_by_gene.get(e["gene_id"])
                    e["symbol"] = e.get("symbol") or (node_by_gene.get(e["gene_id"]) or {}).get("symbol")
            except np.PropagationError as exc:
                network_error = str(exc)
        elif network_store is None:
            network_error = "网络快照未激活"
        elif not seed_node_ids:
            network_error = "种子未映射到网络"

        for s in seeds:
            if s.get("node_id"):
                s["n_score"] = n_scores.get(s["node_id"])

        # 4. 融合排序
        all_candidates = _build_candidates(seeds, extended)
        rankings = tr.rank(all_candidates)

        # 5. 稳定性
        stability: dict = {"leave_one_out": None, "weight_sensitivity": None}
        if network_store is not None and propagation is not None:
            adjacency = network_store.adjacency()
            a_scores_by_node = {c["node_id"]: c["a_score"] for c in all_candidates if c.get("node_id")}
            stability["leave_one_out"] = ns.leave_one_out(adjacency, seed_node_ids, a_scores_by_node)
            stability["weight_sensitivity"] = ns.weight_sensitivity(
                [c for c in all_candidates if c.get("a_score") is not None and c.get("n_score") is not None]
            )
            stability["degree_baseline"] = ns.degree_baseline(adjacency)

        # 6. 结果与报告
        results = {
            "disease_id": disease_id,
            "disease": disease,
            "question": question,
            "question_summary": identification.question_summary,
            "seeds": seeds,
            "extended_candidates": extended,
            "candidates": all_candidates,
            "rankings": rankings,
            "stability": stability,
            "limitations": identification.limitations,
            "hypotheses": [h for s in seeds for h in s.get("hypotheses", [])],
            "truncated_candidates": truncated,
            "network_error": network_error,
            "model_name": identification.model,
            "prompt_version": PROMPT_VERSION,
            "evidence_snapshot_version": evidence_store.manifest.get("version"),
            "network_snapshot_version": network_store.manifest.get("version") if network_store else None,
            "network_stats": network_store.statistics() if network_store else None,
            "params": {"alpha": np.ALPHA, "max_iter": np.MAX_ITER, "tol": np.TOL,
                       "w_a": tr.DEFAULT_W_A, "w_n": tr.DEFAULT_W_N},
            "usage": {"prompt_tokens": identification.prompt_tokens,
                      "completion_tokens": identification.completion_tokens,
                      "total_tokens": identification.total_tokens},
            "unmapped_seeds": propagation.unmapped_seeds if propagation else [],
            "generated_at": _now(),
        }
        results["report_markdown"] = render_markdown(results)
        results["candidates_csv"] = render_csv(all_candidates)

        run.status = RunStatus.completed
        run.completed_at = datetime.now(timezone.utc)
        run.current_step = "report"
        run.results_json = results
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        run = db.get(AnalysisRun, run_id)
        if run is not None:
            run.status = RunStatus.failed
            run.failed_at = datetime.now(timezone.utc)
            run.error_message = str(exc)[:2000]
            db.commit()
    finally:
        db.close()


def _build_candidates(seeds: list[dict], extended: list[dict]) -> list[dict]:
    all_candidates = []
    for s in seeds:
        all_candidates.append({
            "target_id": s["target_id"],
            "node_id": s.get("node_id"),
            "symbol": s.get("symbol"),
            "source": "seed",
            "reason": s.get("reason"),
            "evidence_ids": s.get("evidence_ids", []),
            "valid_evidence_ids": s.get("valid_evidence_ids", []),
            "status": s.get("status"),
            "status_label": s.get("status_label"),
            "a_score": s.get("a_score"),
            "n_score": s.get("n_score"),
            "has_evidence": bool(s.get("valid_evidence_ids")),
            "in_network": s.get("in_network"),
        })
    for c in extended:
        all_candidates.append({
            "target_id": c["target_id"],
            "node_id": c.get("node_id"),
            "symbol": c.get("symbol"),
            "source": "extended",
            "reason": None,
            "evidence_ids": [],
            "valid_evidence_ids": [],
            "status": None,
            "status_label": None,
            "a_score": c.get("a_score"),
            "n_score": c.get("n_score"),
            "has_evidence": c.get("has_evidence"),
            "in_network": c.get("in_network"),
        })
    return all_candidates


def _load_evidence_network(disease_id: str):
    evidence_store = EvidenceStore()
    disease = evidence_store.disease(disease_id)
    if disease is None:
        raise ValueError(f"未知疾病 {disease_id}")
    network_store = None
    try:
        network_store = NetworkStore()
    except NetworkSnapshotError:
        network_store = None
    return evidence_store, network_store, disease


def decrypt_credential(db, user_id: uuid.UUID) -> str:
    cred = (
        db.query(UserLlmCredential)
        .filter(UserLlmCredential.user_id == user_id, UserLlmCredential.provider == LlmProvider.deepseek)
        .first()
    )
    if cred is None:
        raise ValueError("请先在设置中配置 DeepSeek API Key")
    try:
        return encryption.decrypt(cred.api_key_ciphertext, cred.nonce)
    except Exception as exc:
        raise ValueError("API Key 解密失败，请重新配置") from exc
