"""轻量版靶点分析后台执行器（多智能体版）。

串联多智能体流水线：意图解析 → 种子推荐 → 评审 → 确定性网络扩展 → 报告。
使用 FastAPI BackgroundTasks 单进程后台任务，独立建立数据库会话。
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from app.core import encryption
from app.db.models import AnalysisRun, LlmProvider, RunStatus, UserLlmCredential
from app.db.session import SessionLocal
from app.services.agents import pipeline

WORKFLOW_VERSION = pipeline.WORKFLOW_VERSION
PROMPT_VERSION = pipeline.PROMPT_VERSION

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
        question = input_data["question"]
        mechanism_keywords = input_data.get("mechanism_keywords", [])

        # 多智能体流水线：整个过程占用一个模型并发额度
        with _MODEL_SEMAPHORE:
            results = pipeline.run(question, mechanism_keywords, api_key)
        results["generated_at"] = _now()

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
