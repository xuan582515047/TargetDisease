"""轻量版靶点分析路由。

接口挂在 /api/v1/target-analysis：
- GET  /catalog
- POST /runs
- GET  /runs/{id}
- POST /runs/{id}/rerank
- GET  /runs/{id}/network
- GET  /runs/{id}/stability
- GET  /runs/{id}/report
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.models import AnalysisRun, Project, RunStatus, User
from app.db.session import get_db
from app.deps import require_user
from app.schemas import RunOut
from app.services import network_view as nv
from app.services import target_analysis as ta
from app.services import target_ranking as tr
from app.services.evidence_store import EvidenceStore
from app.services.network_store import NetworkSnapshotError, NetworkStore
from app.target_analysis_schemas import (
    CatalogOut,
    DiseaseInfo,
    NetworkOut,
    RerankRequest,
    TargetAnalysisCreate,
)

router = APIRouter(prefix="/target-analysis", tags=["target-analysis"])

ACTIVE_STATUSES = (RunStatus.queued, RunStatus.running)


def _owned_run(db: Session, user: User, run_id: uuid.UUID) -> AnalysisRun:
    run = db.get(AnalysisRun, run_id)
    if run is None or run.user_id != user.id:
        raise HTTPException(status_code=404, detail="分析记录不存在")
    return run


@router.get("/catalog", response_model=CatalogOut)
def catalog(db: Session = Depends(get_db), user: User = Depends(require_user)):
    store = EvidenceStore()
    return CatalogOut(
        version=store.manifest.get("version"),
        diseases=[DiseaseInfo(**d) for d in store.diseases()],
    )


@router.post("/runs", response_model=RunOut, status_code=202)
def create_run(body: TargetAnalysisCreate, background_tasks: BackgroundTasks,
               db: Session = Depends(get_db), user: User = Depends(require_user)):
    store = EvidenceStore()
    if store.disease(body.disease_id) is None:
        raise HTTPException(status_code=400, detail="不支持的疾病，请从目录中选择")

    project = db.get(Project, body.project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="项目不存在")

    try:
        api_key = ta.decrypt_credential(db, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.query(User).filter(User.id == user.id).with_for_update().first()
    active = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.user_id == user.id, AnalysisRun.status.in_(ACTIVE_STATUSES))
        .first()
    )
    if active is not None:
        raise HTTPException(status_code=409, detail="已有分析正在进行，请等待其完成")

    global_active = db.query(AnalysisRun).filter(AnalysisRun.status.in_(ACTIVE_STATUSES)).count()
    if global_active >= ta.GLOBAL_MAX_ACTIVE:
        raise HTTPException(status_code=429, detail="系统繁忙，请稍后再试")

    run = AnalysisRun(
        project_id=project.id,
        user_id=user.id,
        status=RunStatus.queued,
        current_step="load_data",
        workflow_version=ta.WORKFLOW_VERSION,
        model_name="deepseek-chat",
        intermediate_json={
            "disease_id": body.disease_id,
            "question": body.question,
            "mechanism_keywords": body.mechanism_keywords,
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(ta.execute, run.id, api_key)
    return run


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return _owned_run(db, user, run_id)


@router.post("/runs/{run_id}/rerank", response_model=dict)
def rerank(run_id: uuid.UUID, body: RerankRequest, db: Session = Depends(get_db),
           user: User = Depends(require_user)):
    run = _owned_run(db, user, run_id)
    if not run.results_json:
        raise HTTPException(status_code=409, detail="尚无结果，无法重排")
    candidates = run.results_json.get("candidates", [])
    rankings = tr.rank(candidates, body.w_a)
    run.results_json["rankings"] = rankings
    run.results_json["params"] = {**(run.results_json.get("params") or {}),
                                  "w_a": body.w_a, "w_n": body.w_n}
    db.commit()
    return rankings


@router.get("/runs/{run_id}/network", response_model=NetworkOut)
def get_network(run_id: uuid.UUID, threshold: float = Query(0.7, ge=0, le=1),
                layers: int = Query(2, ge=1, le=2),
                include_background: bool = Query(False),
                db: Session = Depends(get_db), user: User = Depends(require_user)):
    run = _owned_run(db, user, run_id)
    if not run.results_json:
        raise HTTPException(status_code=404, detail="尚无网络结果")
    try:
        network_store = NetworkStore()
    except NetworkSnapshotError:
        raise HTTPException(status_code=404, detail="网络快照未激活") from None
    evidence_store = EvidenceStore()
    graph = nv.build_typed_graph(network_store, evidence_store,
                                 run.results_json["disease_id"], run.results_json)
    view = nv.filter_view(graph, network_store.adjacency(), threshold=threshold,
                          layers=layers, include_background=include_background)
    return NetworkOut(**view)


@router.get("/runs/{run_id}/stability")
def get_stability(run_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_user)):
    run = _owned_run(db, user, run_id)
    stability = (run.results_json or {}).get("stability")
    if stability is None:
        raise HTTPException(status_code=404, detail="尚无稳定性结果")
    return stability


@router.get("/runs/{run_id}/report")
def get_report(run_id: uuid.UUID, format: str = Query("md"),
               db: Session = Depends(get_db), user: User = Depends(require_user)):
    run = _owned_run(db, user, run_id)
    if not run.results_json:
        raise HTTPException(status_code=404, detail="尚无报告")
    if format == "md":
        content = run.results_json.get("report_markdown", "")
        return Response(content=content, media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="report_{run_id}.md"'})
    if format == "csv":
        content = run.results_json.get("candidates_csv", "")
        return Response(content=content, media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="candidates_{run_id}.csv"'})
    raise HTTPException(status_code=400, detail="format 仅支持 md 或 csv")
