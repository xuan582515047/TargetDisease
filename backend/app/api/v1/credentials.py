from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import encryption
from app.db.models import LlmProvider, User, UserLlmCredential
from app.db.session import get_db
from app.deps import require_user
from app.schemas import DeepSeekKeyIn, DeepSeekKeyStatus
from app.services.deepseek import DeepSeekError, validate_key

router = APIRouter(prefix="/credentials", tags=["credentials"])


def _status(cred: UserLlmCredential) -> DeepSeekKeyStatus:
    return DeepSeekKeyStatus(
        configured=True, validated=cred.is_validated, last4=cred.key_last4,
        created_at=cred.created_at, updated_at=cred.updated_at,
    )


def _get_cred(db: Session, user: User) -> UserLlmCredential | None:
    return (
        db.query(UserLlmCredential)
        .filter(UserLlmCredential.user_id == user.id, UserLlmCredential.provider == LlmProvider.deepseek)
        .first()
    )


@router.get("/deepseek", response_model=DeepSeekKeyStatus)
def get_status(db: Session = Depends(get_db), user: User = Depends(require_user)):
    cred = _get_cred(db, user)
    if cred is None:
        return DeepSeekKeyStatus(configured=False, validated=False, last4=None)
    return _status(cred)


@router.put("/deepseek", response_model=DeepSeekKeyStatus)
def upsert_key(body: DeepSeekKeyIn, db: Session = Depends(get_db), user: User = Depends(require_user)):
    api_key = body.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key 不能为空")
    ciphertext, nonce = encryption.encrypt(api_key)
    last4 = api_key[-4:]

    cred = _get_cred(db, user)
    if cred is None:
        cred = UserLlmCredential(
            user_id=user.id,
            provider=LlmProvider.deepseek,
            api_key_ciphertext=ciphertext,
            nonce=nonce,
            key_last4=last4,
            is_validated=False,
        )
        db.add(cred)
    else:
        cred.api_key_ciphertext = ciphertext
        cred.nonce = nonce
        cred.key_last4 = last4
        cred.is_validated = False
        cred.validated_at = None
    db.commit()
    db.refresh(cred)
    return _status(cred)


@router.post("/deepseek/validate", response_model=DeepSeekKeyStatus)
def validate(db: Session = Depends(get_db), user: User = Depends(require_user)):
    cred = _get_cred(db, user)
    if cred is None:
        raise HTTPException(status_code=404, detail="尚未配置 DeepSeek API Key")
    try:
        api_key = encryption.decrypt(cred.api_key_ciphertext, cred.nonce)
    except Exception:
        cred.is_validated = False
        cred.validated_at = None
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="密钥解密失败，主密钥可能已变更，请删除后重新保存 API Key",
        ) from None
    try:
        validate_key(api_key)
    except DeepSeekError as e:
        cred.is_validated = False
        cred.validated_at = None
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))
    cred.is_validated = True
    cred.validated_at = datetime.now(timezone.utc)
    db.commit()
    return _status(cred)


@router.delete("/deepseek", response_model=DeepSeekKeyStatus)
def delete(db: Session = Depends(get_db), user: User = Depends(require_user)):
    cred = _get_cred(db, user)
    if cred is not None:
        db.delete(cred)
        db.commit()
    return DeepSeekKeyStatus(configured=False, validated=False, last4=None)
