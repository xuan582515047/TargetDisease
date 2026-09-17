"""轻量版靶点分析路由。

接口挂在 /api/v1/target-analysis：
- GET  /catalog
- POST /runs
- GET  /runs/{id}
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
from app.services.evidence_store import EvidenceStore
from app.services.opentargets_client import OpenTargetsError, search_diseases
from app.services.deepseek import DeepSeekError
from app.services.disease_translate import is_chinese, translate_to_english
from app.target_analysis_schemas import (
    CatalogOut,
    DiseaseInfo,
    DiseaseSearchHit,
    DiseaseSearchOut,
    NetworkOut,
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


@router.get("/disease-search", response_model=DiseaseSearchOut)
def disease_search(
    q: str = Query(min_length=1, max_length=128),
    size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """按名称实时检索 Open Targets 疾病，用于发现尚未收录的疾病。

    中文输入先经 DeepSeek 翻译为英文标准名再检索；未配置模型凭据或翻译
    失败时，回退到用原始输入检索。
    """
    search_q = q
    translated_query = None
    if is_chinese(q):
        try:
            api_key = ta.decrypt_credential(db, user.id)
            search_q = translate_to_english(api_key, q)
            if search_q and search_q != q:
                translated_query = search_q
        except (ValueError, DeepSeekError):
            search_q = q

    try:
        hits = search_diseases(search_q, size)
    except OpenTargetsError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    imported = {d["id"] for d in EvidenceStore().diseases()}
    return DiseaseSearchOut(
        query=q,
        translated_query=translated_query,
        diseases=[
            DiseaseSearchHit(
                id=h.get("id", ""),
                name=h.get("name") or h.get("id", ""),
                description=h.get("description"),
                imported=h.get("id") in imported,
            )
            for h in hits
        ],
    )


@router.post("/runs", response_model=RunOut, status_code=202)
def create_run(body: TargetAnalysisCreate, background_tasks: BackgroundTasks,
               db: Session = Depends(get_db), user: User = Depends(require_user)):
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


@router.get("/runs/{run_id}/network", response_model=NetworkOut)
def get_network(run_id: uuid.UUID, threshold: float = Query(0.7, ge=0, le=1),
                layers: int = Query(2, ge=1, le=2),
                include_background: bool = Query(False),
                db: Session = Depends(get_db), user: User = Depends(require_user)):
    run = _owned_run(db, user, run_id)
    if not run.results_json:
        raise HTTPException(status_code=404, detail="尚无网络结果")
    graph = nv.build_typed_graph(run.results_json)
    adjacency = nv.adjacency_from_edges((run.results_json.get("network") or {}).get("edges", []))
    view = nv.filter_view(graph, adjacency, threshold=threshold,
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
