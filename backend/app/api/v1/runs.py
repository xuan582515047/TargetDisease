"""分析记录只读接口：列表、详情与受控文件下载。

轻量版新建分析通过 /api/v1/target-analysis/runs 发起；本路由只保留旧记录
（含历史科学结果）的读取与文件下载，不再提供任何写操作。
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.models import AnalysisRun, User
from app.db.session import get_db
from app.deps import require_user
from app.schemas import RunOut

router = APIRouter(prefix="/runs", tags=["runs"])


def _get_owned_run(db: Session, user: User, run_id: uuid.UUID) -> AnalysisRun:
    run = db.get(AnalysisRun, run_id)
    if run is None or run.user_id != user.id:
        raise HTTPException(status_code=404, detail="分析记录不存在")
    return run


@router.get("", response_model=list[RunOut])
def list_runs(project_id: uuid.UUID | None = None,
              db: Session = Depends(get_db), user: User = Depends(require_user)):
    q = db.query(AnalysisRun).filter(AnalysisRun.user_id == user.id)
    if project_id:
        q = q.filter(AnalysisRun.project_id == project_id)
    return q.order_by(AnalysisRun.created_at.desc()).all()


@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return _get_owned_run(db, user, run_id)


def _artifact_root(run_id: uuid.UUID):
    base = Path(os.environ.get("PHARMAGENTS_ARTIFACT_ROOT", "/app/artifacts")).resolve()
    root = (base / str(run_id)).resolve()
    if not root.is_relative_to(base) or root == base:
        raise HTTPException(status_code=404, detail="文件不存在")
    return root


@router.get("/{run_id}/artifacts")
def list_artifacts(run_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_user)):
    _get_owned_run(db, user, run_id)
    root = _artifact_root(run_id)
    if not root.is_dir():
        return []
    result = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root):
            result.append({"path": path.relative_to(root).as_posix(), "size": path.stat().st_size})
    return result


@router.get("/{run_id}/artifacts/download")
def download_artifact(run_id: uuid.UUID, path: str, db: Session = Depends(get_db),
                      user: User = Depends(require_user)):
    _get_owned_run(db, user, run_id)
    root = _artifact_root(run_id)
    supplied = Path(path)
    if supplied.is_absolute() or ".." in supplied.parts:
        raise HTTPException(status_code=404, detail="文件不存在")
    file = (root / supplied).resolve()
    if not file.is_relative_to(root) or not file.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(file, filename=file.name, media_type="application/octet-stream")
