from fastapi import APIRouter

from app.api.v1 import auth, credentials, projects, runs, target_analysis

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(credentials.router)
api_router.include_router(projects.router)
api_router.include_router(runs.router)
api_router.include_router(target_analysis.router)
