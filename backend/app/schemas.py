import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: str
    status: str

    model_config = {"from_attributes": True}


class DeepSeekKeyIn(BaseModel):
    api_key: str = Field(min_length=1)


class DeepSeekKeyStatus(BaseModel):
    configured: bool
    validated: bool
    last4: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    primary_disease: str | None = None
    notes: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    primary_disease: str | None = None
    notes: str | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    primary_disease: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RunOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    current_step: str | None
    error_code: str | None
    error_message: str | None
    workflow_version: str | None
    results_json: dict[str, Any] | None
    intermediate_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
