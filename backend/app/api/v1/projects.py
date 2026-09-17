import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import AnalysisRun, Project, RunStatus, User
from app.db.session import get_db
from app.deps import require_user
from app.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])

ACTIVE_STATUSES = (RunStatus.queued, RunStatus.running)


def _get_owned(db: Session, user: User, project_id: uuid.UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(require_user)):
    return db.query(Project).filter(Project.user_id == user.id).order_by(Project.updated_at.desc()).all()


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(require_user)):
    project = Project(user_id=user.id, name=body.name, primary_disease=body.primary_disease, notes=body.notes)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return _get_owned(db, user, project_id)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: uuid.UUID, body: ProjectUpdate, db: Session = Depends(get_db), user: User = Depends(require_user)):
    project = _get_owned(db, user, project_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(project, k, v)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_user)):
    db.query(User).filter(User.id == user.id).with_for_update().first()
    project = _get_owned(db, user, project_id)
    if db.query(AnalysisRun).filter(AnalysisRun.project_id == project_id,
                                  AnalysisRun.status.in_(ACTIVE_STATUSES)).first():
        raise HTTPException(status_code=409, detail="项目仍有进行中的任务，请先取消任务再删除")
    # 先删除该项目关联的所有分析运行，避免外键约束冲突
    db.query(AnalysisRun).filter(AnalysisRun.project_id == project_id).delete()
    db.delete(project)
    db.commit()
