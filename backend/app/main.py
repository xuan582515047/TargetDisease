from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import api_router
from app.core.config import settings
from app.db.models import AnalysisRun, RunStatus
from app.db.session import SessionLocal


def _interrupt_stale_runs() -> None:
    """启动时将旧 queued/running 标记为中断失败，允许用户重新发起。"""
    db = SessionLocal()
    try:
        rows = db.query(AnalysisRun).filter(
            AnalysisRun.status.in_((RunStatus.queued, RunStatus.running))
        ).all()
        for run in rows:
            run.status = RunStatus.failed
            run.error_message = "服务重启，任务中断，请重新发起分析"
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _interrupt_stale_runs()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
